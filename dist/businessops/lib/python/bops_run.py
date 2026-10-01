"""The one BusinessOps engine entry (ADR-0042), reached through the runtime resolver (ADR-0045).

Every command and skill runs engine code as:

    sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "<code>"

`lib/bops_run.sh` is the one place an interpreter is chosen. It resolves a Python 3.9+ executable
and hands off here, unchanged:

    exec <interpreter> -I "<plugin root>/lib/python/bops_run.py" -c "<code>"

The split is deliberate. Choosing the interpreter is what must happen before Python runs, so it
cannot happen in Python; everything after that is this file's job and is unaffected by which
interpreter was chosen. Until 2026-09-22 the command bodies named `python` directly, and a host
that ships Python 3 only as `python3` could not enter the engine at all (M13-DEF-08).

The platform substitutes `${CLAUDE_PLUGIN_ROOT}` in the command or skill body with the loaded
plugin's absolute path before the model sees it (verified at runtime, 2026-09-19). This file then
establishes a trusted import boundary and runs `<code>`:

1. its own location, from `__file__`, is the engine directory `<plugin root>/lib/python`;
2. the plugin root must hold `lib/python/bops/__init__.py` and a `.claude-plugin/plugin.json`
   naming `businessops`;
3. Python must be in isolated mode (`-I`): no `PYTHON*` environment variables, no user
   site-packages, and neither the working directory nor the script directory on `sys.path`;
4. `sys.path` is rebuilt with the engine directory first and without the working directory;
5. `bops` is imported and must come from this engine directory.

Any failure stops with a message on stderr and exit status 2; there is no fallback. The resolver
uses exit status 78 for "no usable interpreter", so the two failure domains stay distinguishable.
The process working directory is never changed, so a user's relative file paths keep resolving
where the user is. `--where` prints the resolved locations as JSON.

The write boundary (ADR-0051) has its two entries here, so that it needs no second interpreter
choice and no second import boundary:

- before `-c` code runs, the engine's execution guard is installed (`bops.writeguard.engine`),
  so no engine process writes, starts a process or connects anywhere its policy does not admit;
- `--guard <event>` is the Claude Code hook entry, run by `hooks/hooks.json` with the event's
  JSON on stdin; it runs no caller-supplied code.

`--handback` is the plugin's `PostToolUse` hook entry for scout dispatches (ADR-0053). It reads
the event JSON on stdin and stores the scout's reply verbatim for `close_retrieval()`, so the reply
never passes through a model copy. It runs no caller-supplied code, and the write guard refuses it
from any tool call.

`--verifier` is the entry `.mcp.json` declares for the local `bops-verifier` MCP server
(ADR-0035, launched through the resolver by ADR-0052). It runs no caller-supplied code: it serves
`bops.verification_server` over stdio exactly as that module's own `main()` does, now behind the
same interpreter resolution and import boundary as every other entry. Until 2026-09-27 the server
was declared as a bare `python` command, so a host with only `python3` could not start it (R-13).

Standard library only. It adds no behaviour beyond the boundary and the write guard, and runs
exactly the code given.
"""

import sys

USAGE = ('usage: sh "<plugin root>/lib/bops_run.sh" '
         '(-c CODE [ARG ...] | --where | --guard EVENT | --verifier | --handback), '
         'which runs this launcher as <interpreter> -I "<plugin root>/lib/python/bops_run.py" ...')
PLUGIN_NAME = "businessops"


def _fail(message):
    sys.stderr.write("bops_run: %s\n" % message)
    raise SystemExit(2)


# Isolation is checked before anything else is imported, so that no module can be resolved
# through a working directory, PYTHONPATH or user site-packages that isolation would exclude.
if not sys.flags.isolated:
    _fail("refusing to run: Python must be started in isolated mode (python -I ...) so that "
          "the working directory and PYTHON* environment variables cannot shadow the engine. "
          + USAGE)

import builtins  # noqa: E402  (imported only after the isolation check)
import json  # noqa: E402
import os  # noqa: E402

ENGINE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(os.path.dirname(ENGINE))
PACKAGE = os.path.join(ENGINE, "bops")


def _check_layout():
    """The launcher must sit at <plugin root>/lib/python beside the bops package."""
    if os.path.basename(ENGINE) != "python" or \
            os.path.basename(os.path.dirname(ENGINE)) != "lib":
        _fail("launcher is not at <plugin root>/lib/python/bops_run.py: %s" % ENGINE)
    if not os.path.isfile(os.path.join(PACKAGE, "__init__.py")):
        _fail("engine package not found beside the launcher: %s" % PACKAGE)
    manifest = os.path.join(ROOT, ".claude-plugin", "plugin.json")
    try:
        with open(manifest, encoding="utf-8") as handle:
            name = json.load(handle).get("name")
    except (OSError, ValueError, AttributeError) as error:
        _fail("plugin manifest unreadable at %s: %s" % (manifest, error))
    if name != PLUGIN_NAME:
        _fail("plugin manifest at %s names %r, not %r" % (manifest, name, PLUGIN_NAME))


def _is_cwd(entry, cwd):
    if entry in ("", "."):
        return True
    try:
        return os.path.realpath(entry) == cwd
    except (OSError, ValueError):
        return True


def _establish_boundary():
    """Engine directory first; the working directory nowhere; then import and verify bops."""
    if "bops" in sys.modules:
        _fail("a module named 'bops' was imported before the launcher ran")
    cwd = os.path.realpath(os.getcwd())      # only to exclude it, never to find the engine
    engine = os.path.normcase(ENGINE)
    kept = [entry for entry in sys.path
            if not _is_cwd(entry, cwd) and os.path.normcase(os.path.realpath(entry)) != engine]
    sys.path[:] = [ENGINE] + kept
    import bops
    origin = os.path.realpath(getattr(bops, "__file__", "") or "")
    expected = os.path.join(PACKAGE, "__init__.py")
    if os.path.normcase(origin) != os.path.normcase(expected):
        _fail("imported bops from %s, expected %s" % (origin or "<no file>", expected))
    return bops


def _where(bops):
    return {"bops_module": os.path.realpath(bops.__file__), "engine": ENGINE,
            "isolated": bool(sys.flags.isolated), "plugin": PLUGIN_NAME,
            "plugin_root": ROOT, "python": sys.version.split()[0]}


def main(argv):
    if argv == ["--where"]:
        mode, code, extra = "where", None, []
    elif len(argv) >= 2 and argv[0] == "-c":
        mode, code, extra = "run", argv[1], argv[2:]
    elif len(argv) == 2 and argv[0] == "--guard":
        mode, code, extra = "guard", None, []
    elif argv == ["--verifier"]:
        mode, code, extra = "verifier", None, []
    elif argv == ["--handback"]:
        mode, code, extra = "handback", None, []
    else:
        _fail(USAGE)
    _check_layout()
    bops = _establish_boundary()
    if mode == "where":
        sys.stdout.write(json.dumps(_where(bops), sort_keys=True) + "\n")
        return 0
    if mode == "guard":
        from bops.writeguard import hook
        return hook.main(argv[1])
    if mode == "handback":
        from bops.research import handback
        return handback.main()
    if mode == "verifier":
        from bops import verification_server
        verification_server.main()
        return 0
    from bops.writeguard import engine as write_guard
    write_guard.install()
    sys.argv[:] = ["-c"] + extra
    namespace = {"__name__": "__main__", "__doc__": None, "__builtins__": builtins}
    exec(compile(code, "<businessops>", "exec"), namespace)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
