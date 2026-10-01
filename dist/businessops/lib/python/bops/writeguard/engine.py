"""The engine's execution guard: layer 2 of the write boundary (ADR-0051).

The pre-execution hook sees a tool call; it cannot see what Python does once the engine runs.
This module closes that gap for every process started through `lib/python/bops_run.py`: the
launcher calls `install()` before it runs any engine code, and from then on a CPython audit
hook (PEP 578) sees each filesystem mutation, process start and network connection at the
moment it is attempted, and stops it unless it lands where the engine is allowed to write:

- BusinessOps's own runtime state: the managed runtime (`~/.claude/businessops/runtime/`), the
  working directory's `./.businessops/` (verification and connector records, ADR-0035,
  ADR-0037) and the verification directory the environment names;
- a new file or directory under `./businessops-output/`;
- the approval store's `pending/` and `consumed/` areas, for the export API's own records
  (never `granted/`: only the user's prompt grants);
- a write the export API (`writeguard.export`) has just authorised with a redeemed capability,
  exactly once, for exactly that path.

Everything else raises `WriteBlockedError` before the operation happens. Processes are limited
to the fixed argument shapes the reader runtime uses (ADR-0008); network connections are
refused outright, because the engine makes none (`CLAUDE.md` section 4).

**What this does and does not protect against.** An audit hook cannot be removed once added,
but Python cannot sandbox Python: code that can rebind the guard's own dependencies could
evade it. That is why the pre-execution hook only lets *confined* engine code through without
approval (`writeguard.pyscan`): no private names, no reflection, no attribute assignment, no
unlisted imports. Unconfined engine code needs the user's approval first, and the approval
message says that it runs arbitrary code.

Standard library only.
"""

import os
import sys

from ..errors import WriteBlockedError
from . import policy as P

_INSTALLED = []
_AUTHORISED = []           # one-shot (kind, path) pairs from the export API

_PATH_EVENTS = {
    "os.remove": ("delete", (0,)), "os.rmdir": ("delete", (0,)), "shutil.rmtree": ("delete", (0,)),
    "os.mkdir": ("mkdir", (0,)), "os.truncate": ("modify", (0,)),
    "os.chmod": ("modify", (0,)), "os.chown": ("modify", (0,)), "os.utime": ("modify", (0,)),
    "os.chflags": ("modify", (0,)), "os.lchflags": ("modify", (0,)), "os.lchmod": ("modify", (0,)),
    "os.setxattr": ("modify", (0,)), "os.removexattr": ("modify", (0,)),
    "os.mkfifo": ("create", (0,)), "os.mknod": ("create", (0,)),
    "os.link": ("create", (1,)), "os.symlink": ("create", (1,)),
}
_DIR_FD_INDEX = {"os.remove": 1, "os.rmdir": 1, "shutil.rmtree": 1, "os.mkdir": 2,
                 "os.chmod": 2, "os.chown": 3, "os.utime": 3, "os.symlink": 2, "os.link": 2,
                 "os.rename": 2}
_PROCESS_EVENTS = frozenset(("subprocess.Popen", "os.system", "os.exec", "os.spawn",
                             "os.posix_spawn", "os.forkpty", "pty.spawn"))
_NETWORK_EVENTS = frozenset(("socket.connect", "socket.sendto", "socket.sendmsg", "socket.bind",
                             "urllib.Request", "http.client.connect", "ftplib.connect",
                             "smtplib.connect", "imaplib.open", "poplib.connect",
                             "nntplib.connect", "telnetlib.Telnet.open", "webbrowser.open"))
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND


class EnginePolicy:
    """Where the engine may write without an approval, fixed at install time."""

    def __init__(self, cwd=None, home=None, guard=None, runtime_dir=None, plugin=None,
                 extra_state=()):
        from ..runtime import tiers
        self.cwd = os.path.realpath(cwd or os.getcwd())
        home = home or P.default_home()
        self.guard = os.path.realpath(guard or P.guard_root(home))
        self.runtime = os.path.realpath(runtime_dir or tiers.RUNTIME_DIR)
        self.plugin = os.path.realpath(plugin or P.plugin_root())
        self.state = tuple(os.path.realpath(p) for p in
                           (os.path.join(self.cwd, ".businessops"),) + tuple(extra_state) if p)
        self.output = os.path.join(self.cwd, P.OUTPUT_DIRNAME)
        self.executable = os.path.realpath(sys.executable)
        self.worker = os.path.join(self.plugin, "lib", "python", "bops", "ingest", "_managed_read.py")
        self.engine_root = os.path.join(self.plugin, "lib", "python")
        self.pin = tiers.OPENPYXL_PIN
        self.bases = tuple(os.path.dirname(p) for p in (self.guard, self.runtime))

    def resolve(self, path):
        if isinstance(path, bytes):
            path = os.fsdecode(path)
        path = os.fspath(path)
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
        return os.path.realpath(path)

    def allows(self, kind, path):
        """Whether the engine may perform `kind` on canonical `path` without an approval."""
        if P.Policy.is_device(path):
            return True
        if P.within(path, self.guard):
            area = os.path.relpath(path, self.guard).split(os.sep)[0]
            if kind == "mkdir":
                return True
            if area == "pending":
                return kind in ("create", "delete")
            if area == "consumed":
                return kind in ("create", "delete")
            if area == "granted":
                return kind in ("move_source", "delete")
            return False
        if kind == "mkdir" and any(P.within(base, path) for base in self.bases) and \
                P.within(path, os.path.dirname(os.path.dirname(self.guard))):
            return True             # ~/.claude/businessops and ~/.claude, on the way to the store
        if P.within(path, self.runtime) or any(P.within(path, s) for s in self.state):
            return True
        if P.within(path, self.output) and kind in ("create", "mkdir") and not os.path.lexists(path):
            return True
        if (kind, path) in _AUTHORISED:
            _AUTHORISED.remove((kind, path))
            return True
        return False

    def allows_process(self, event, args):
        if event != "subprocess.Popen":
            return False
        argv = args[1] if len(args) > 1 else None
        if isinstance(argv, (str, bytes)) or not argv:
            return False
        argv = [os.fsdecode(a) if isinstance(a, bytes) else str(a) for a in argv]
        if not os.path.isabs(argv[0]):
            return False
        program, rest = os.path.abspath(argv[0]), argv[1:]
        # The managed interpreter first: a venv's python is usually a symlink to the system one.
        if P.within(program, self.runtime):
            if rest == ["-c", "import openpyxl; print(openpyxl.__version__)"]:
                return True
            if rest == ["-m", "pip", "install", "--disable-pip-version-check", self.pin]:
                return True
            return len(rest) in (3, 4) and os.path.realpath(rest[0]) == self.worker and \
                os.path.realpath(rest[1]) == os.path.realpath(self.engine_root)
        if os.path.realpath(program) == self.executable:
            if rest == ["-m", "pip", "--version"]:
                return True
            return len(rest) == 3 and rest[:2] == ["-m", "venv"] and \
                P.within(os.path.realpath(rest[2]), self.runtime)
        return False


def _has_dir_fd(value):
    """CPython reports an absent `dir_fd` as None or -1."""
    return value is not None and value != -1


def _is_write_open(mode, flags):
    if isinstance(mode, str) and set(mode) & set("wax+"):
        return True
    return isinstance(flags, int) and bool(flags & _WRITE_FLAGS)


def _blocked(what):
    raise WriteBlockedError(
        "BusinessOps's engine blocked %s before it happened. The engine writes only its own "
        "runtime state and new files under ./businessops-output/; any other write goes through "
        "the export API (bops.writeguard.export), which asks the user for approval first." % what)


def audit(policy, event, args):
    """The audit-hook body: return to allow, raise WriteBlockedError to stop the operation."""
    if event == "open":
        path, mode, flags = (tuple(args) + (None, None, None))[:3]
        if isinstance(path, int) or not _is_write_open(mode, flags):
            return
        target = policy.resolve(path)
        kind = "create" if not os.path.lexists(target) else "overwrite"
        if not policy.allows(kind, target):
            _blocked("a write to %s" % target)
        return
    if event == "os.rename":
        src, dst = args[0], args[1]
        if _has_dir_fd(args[2]) or _has_dir_fd(args[3]):
            _blocked("a rename relative to a directory descriptor")
        source, target = policy.resolve(src), policy.resolve(dst)
        kind = "create" if not os.path.lexists(target) else "overwrite"
        if not (policy.allows("move_source", source) and policy.allows(kind, target)):
            _blocked("renaming %s to %s" % (source, target))
        return
    spec = _PATH_EVENTS.get(event)
    if spec is not None:
        kind, (index,) = spec
        fd_index = _DIR_FD_INDEX.get(event)
        if fd_index is not None and len(args) > fd_index and _has_dir_fd(args[fd_index]):
            _blocked("%s relative to a directory descriptor" % event)
        path = args[index]
        if isinstance(path, int):
            _blocked("%s on an open file descriptor" % event)
        if not policy.allows(kind, policy.resolve(path)):
            _blocked("%s on %s" % (event, policy.resolve(path)))
        return
    if event == "sqlite3.connect":
        database = args[0] if args else None
        if database in (":memory:", "", b":memory:", b""):
            return
        _blocked("opening a database file")
    if event in _PROCESS_EVENTS:
        if not policy.allows_process(event, args):
            _blocked("starting a process (%s)" % event)
        return
    if event in _NETWORK_EVENTS:
        _blocked("a network operation (%s)" % event)
    if event.startswith("ctypes."):
        _blocked("a foreign-function call (%s)" % event)


def install(policy=None):
    """Add the audit hook to this process. Idempotent; cannot be undone (PEP 578)."""
    if _INSTALLED:
        return _INSTALLED[0]
    policy = policy or EnginePolicy(extra_state=_verification_override())
    sys.dont_write_bytecode = True        # no .pyc writes into the plugin's own tree

    def hook(event, args, _policy=policy, _audit=audit):
        if event == "open" or event in _WATCHED:
            _audit(_policy, event, args)

    sys.addaudithook(hook)
    _INSTALLED.append(policy)
    return policy


def installed():
    return bool(_INSTALLED)


def _verification_override():
    from .. import verification
    override = os.environ.get(verification.ENV_DIRECTORY)
    return (os.path.abspath(override),) if override else ()


def _authorise(kind, path):
    """The export API's one-shot permission for the audit hook: one operation on one path."""
    _AUTHORISED.append((kind, path))


def _revoke(kind, path):
    while (kind, path) in _AUTHORISED:
        _AUTHORISED.remove((kind, path))


_WATCHED = frozenset(set(_PATH_EVENTS) | _PROCESS_EVENTS | _NETWORK_EVENTS |
                     {"os.rename", "sqlite3.connect", "ctypes.dlopen", "ctypes.dlsym",
                      "ctypes.call_function", "ctypes.cdata", "ctypes.addressof",
                      "ctypes.PyObj_FromPtr", "ctypes.string_at", "ctypes.wstring_at",
                      "ctypes.set_errno", "ctypes.set_last_error", "ctypes.get_errno",
                      "ctypes.get_last_error", "ctypes.seh_exception"})
