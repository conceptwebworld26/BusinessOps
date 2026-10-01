"""Where a filesystem operation lands, and what that means for approval (ADR-0051).

`CLAUDE.md` section 9 grades approval by consequence. This module is the one place that
grading is turned into a decision for a concrete operation on a concrete path. Both
enforcement layers use it: the pre-execution hook (`writeguard.hook`) for the model's own tool
calls, and the execution guard (`writeguard.engine`) for writes made inside the engine.

Every operation gets one of three decisions:

``free``
    Needs no approval: creating a *new* file or directory under `./businessops-output/`
    (section 9: "Writing a **new** file into `./businessops-output/` - state the path"),
    anything under the session scratchpad or the system temporary directory (draft working
    files, section 8), and the null and standard-stream devices.

``approval``
    Explicit, per-action approval: every other create, overwrite, append, truncate, delete,
    rename, copy-into, link, permission change, `git commit` or `git push`, and every
    operation whose target or effect cannot be established (`UNKNOWN != SAFE`).

``prohibited``
    No approval unlocks it:

    - the guard's own state (`~/.claude/businessops/guard/`), which holds the approvals;
    - the installed plugin's own files, while BusinessOps is engaged;
    - an existing business data file (`.csv`, `.tsv`, `.xlsx`, `.xlsm`, `.xls`) outside the
      scratch and output locations - section 9 prohibits modifying original source data
      outright;
    - a force push, a history rewrite or a branch deletion (section 9, section 10);
    - invoking the guard's own entry point from a tool call.

Standard library only.
"""

import os
import tempfile

FREE = "free"
APPROVAL = "approval"
PROHIBITED = "prohibited"
_RANK = {FREE: 0, APPROVAL: 1, PROHIBITED: 2}

# Operation kinds. Each is a distinct binding: an approval for one never covers another.
CREATE = "create"
OVERWRITE = "overwrite"
APPEND = "append"
MODIFY = "modify"
TRUNCATE = "truncate"
DELETE = "delete"
MOVE_SOURCE = "move_source"
MKDIR = "mkdir"
LINK = "link"
GIT_COMMIT = "git_commit"
GIT_PUSH = "git_push"
GIT_MUTATION = "git_mutation"
GIT_REWRITE = "git_rewrite"
EXECUTE = "execute"
UNKNOWN_WRITE = "unknown_write"
GUARD_ENTRY = "guard_entry"

SOURCE_DATA_EXTENSIONS = frozenset((".csv", ".tsv", ".xlsx", ".xlsm", ".xls"))
OUTPUT_DIRNAME = "businessops-output"

_DESCRIPTIONS = {
    CREATE: "create new file",
    OVERWRITE: "overwrite existing file",
    APPEND: "append to file",
    MODIFY: "modify existing file",
    TRUNCATE: "truncate file",
    DELETE: "delete",
    MOVE_SOURCE: "move away (the original path disappears)",
    MKDIR: "create directory",
    LINK: "create link",
    GIT_COMMIT: "git commit",
    GIT_PUSH: "git push",
    GIT_MUTATION: "change the git repository",
    GIT_REWRITE: "rewrite git history, force-push or delete a branch",
    EXECUTE: "run code or a command whose effects cannot be established",
    UNKNOWN_WRITE: "write to a target that cannot be resolved",
    GUARD_ENTRY: "invoke the BusinessOps write guard directly",
}


def default_home():
    """The user's home from the account database where there is one, not from `$HOME`.

    `$HOME` is an environment variable a command line can set; the account record is not.
    """
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_dir
    except (ImportError, KeyError, AttributeError):
        return os.path.expanduser("~")


def guard_root(home=None):
    """`~/.claude/businessops/guard/`: engagement markers and the approval store."""
    return os.path.join(home or default_home(), ".claude", "businessops", "guard")


def plugin_root():
    """The installed plugin, from this module's own location (never from the environment)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.realpath(os.path.join(here, "..", "..", "..", ".."))


def within(path, root):
    if not path or not root:
        return False
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


class Operation:
    """One filesystem or repository effect of a tool call.

    `target` is a canonical absolute path, or None when it cannot be established. `exists` is
    whether the target existed when the operation was classified (None when unknown). Both are
    part of what an approval binds: create-then-overwrite is a different operation.
    """

    __slots__ = ("kind", "target", "sources", "exists", "detail", "decision", "reason")

    def __init__(self, kind, target=None, sources=(), exists=None, detail=""):
        self.kind = kind
        self.target = target
        self.sources = tuple(sources)
        self.exists = exists
        self.detail = detail
        self.decision = None
        self.reason = ""

    def binding(self):
        """The fields an approval is bound to."""
        return {"kind": self.kind, "target": self.target, "sources": list(self.sources),
                "exists": self.exists}

    def describe(self):
        text = _DESCRIPTIONS.get(self.kind, self.kind)
        if self.kind == CREATE and self.exists:
            text = _DESCRIPTIONS[OVERWRITE]
        if self.target:
            text += ": %s" % self.target
        elif self.detail:
            text += ": %s" % self.detail
        if self.sources:
            text += " (from %s)" % ", ".join(self.sources)
        return text

    def __repr__(self):
        return "Operation(%s, %r, exists=%r, %s)" % (self.kind, self.target, self.exists,
                                                    self.decision)


class Policy:
    """The paths that decide an operation's zone, fixed when the policy is built.

    Nothing here is read from a tool call: the working directory and scratchpad come from the
    runtime's hook input, everything else from this process and the account database.
    """

    def __init__(self, cwd, home=None, plugin=None, temp_roots=None, engaged=True, guard=None):
        self.cwd = os.path.realpath(cwd)
        self.home = home or default_home()
        self.guard = os.path.realpath(guard or guard_root(self.home))
        self.plugin = os.path.realpath(plugin or plugin_root())
        if temp_roots is None:
            temp_roots = [tempfile.gettempdir()]
        self.temp_roots = tuple(os.path.realpath(p) for p in temp_roots if p)
        self.output = os.path.join(self.cwd, OUTPUT_DIRNAME)
        self.engaged = engaged

    def resolve(self, path, base=None):
        """Canonical absolute path for `path`, relative to `base` (default: the cwd)."""
        if path == "~" or path.startswith("~/"):
            path = self.home + path[1:]
        if not os.path.isabs(path):
            path = os.path.join(base or self.cwd, path)
        return os.path.realpath(path)

    def decide(self, op):
        """Set and return `op.decision`, with a reason for anything that is not free."""
        decision, reason = self._decide(op)
        op.decision, op.reason = decision, reason
        return decision

    def _decide(self, op):
        if op.kind == GUARD_ENTRY:
            return PROHIBITED, "the write guard is invoked only by Claude Code, never by a tool call"
        if op.kind == GIT_REWRITE:
            return PROHIBITED, "force-pushing, rewriting history and deleting branches are prohibited"
        if op.kind in (GIT_COMMIT, GIT_PUSH, GIT_MUTATION, EXECUTE, UNKNOWN_WRITE):
            return APPROVAL, "its effect cannot be limited to a free location"
        paths = [p for p in (op.target,) + op.sources if p]
        for path in paths:
            if within(path, self.guard):
                return PROHIBITED, "BusinessOps's approval store may not be changed by a tool call"
            if self.engaged and within(path, self.plugin):
                return PROHIBITED, "the BusinessOps plugin may not change itself while it is in use"
        if op.target is None:
            return APPROVAL, "the target cannot be established"
        if self.is_device(op.target):
            return FREE, ""
        if any(within(op.target, root) for root in self.temp_roots):
            return FREE, ""          # scratch working copies, including derived data files
        if op.exists and not within(op.target, self.output) and \
                os.path.splitext(op.target)[1].lower() in SOURCE_DATA_EXTENSIONS:
            return PROHIBITED, ("original source data is immutable (see the BusinessOps README, "
                                "\"Approval and write safety\")")
        if within(op.target, self.output) and op.kind in (CREATE, MKDIR) and op.exists is False:
            return FREE, ""
        if op.target == self.output and op.kind == MKDIR:
            return FREE, ""
        return APPROVAL, _approval_reason(op)

    @staticmethod
    def is_device(path):
        return path in ("/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty") or \
            path.startswith("/dev/fd/") or path.startswith("/proc/self/fd/")


def _approval_reason(op):
    if op.kind in (OVERWRITE, MODIFY, TRUNCATE, APPEND) or (op.kind == CREATE and op.exists):
        return ("changing an existing file needs explicit approval (see the BusinessOps README, "
                "\"Approval and write safety\")")
    if op.kind in (DELETE, MOVE_SOURCE):
        return "deleting or moving a file needs explicit approval"
    return "a write outside ./businessops-output/ needs explicit approval"


def strictest(decisions):
    """The most restrictive of several decisions (free < approval < prohibited)."""
    best = FREE
    for decision in decisions:
        if _RANK[decision] > _RANK[best]:
            best = decision
    return best
