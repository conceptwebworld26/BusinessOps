"""Static reading of Python code handed to an interpreter on a command line (ADR-0051).

Two questions, answered from the syntax tree without running anything:

1. **Is the code confined?** Confined code can reach the filesystem, processes and the
   network only through modules on an allowlist, and cannot reach around that allowlist by
   reflection, dynamic code or monkeypatching. The test is an allowlist, not a search for
   bad calls: an import outside the list, any name or attribute beginning with `_`, a
   reflective builtin (`getattr`, `vars`, `exec` ...), or an assignment to an attribute makes
   the code unconfined, whatever it appears to do.

   - Plain confined code (`PURE_MODULES`) can only compute and print. The classifier lets it
     run like any other read-only command.
   - Engine-confined code may also import `bops`. Everything it can do to the filesystem then
     goes through the engine, where the execution guard (`writeguard.engine`) decides at run
     time. Forbidding attribute assignment and private names is what stops the code from
     patching that guard out.

2. **Which files does it obviously write?** A best-effort list of literal targets (`open(p,
   "w")`, `Path(p).write_text`, `os.remove(p)` ...), used only to *name* the target in an
   approval request. It never makes code look safer: unconfined code needs approval whether
   or not a target was found.

Standard library only.
"""

import ast

PURE_MODULES = frozenset((
    "json", "decimal", "datetime", "math", "statistics", "collections", "re", "textwrap",
    "fractions", "itertools", "functools", "pprint", "sys", "csv", "hashlib", "base64",
    "calendar", "numbers", "bisect", "heapq", "difflib", "unicodedata",
))

# Reflection, dynamic code and direct file access. Referenced at all, they make code unconfined -
# except `open` called directly with no mode or a literal read-only one, which cannot write.
BLOCKED_BUILTINS = frozenset((
    "open", "exec", "eval", "compile", "__import__", "getattr", "setattr", "delattr",
    "globals", "locals", "vars", "breakpoint", "input", "help", "memoryview", "classmethod",
    "staticmethod", "property", "super", "type", "object",
))

# Attribute names that reach an unlisted module through one that is listed (`bops.x.os`), or
# that name a filesystem mutation. Blocked for engine code as defence in depth; the execution
# guard still decides at run time. (`write_text` is not listed: it is also the name of the
# export API, `bops.writeguard.export.write_text`, and the execution guard stops any other.)
BLOCKED_ATTRIBUTES = frozenset((
    "os", "io", "shutil", "subprocess", "pathlib", "socket", "ctypes", "importlib", "builtins",
    "tempfile", "sqlite3", "modules", "system", "popen", "spawn", "remove", "unlink", "rmdir",
    "rmtree", "rename", "makedirs", "mkdir", "write_bytes", "truncate", "chmod",
    "symlink", "symlink_to", "hardlink_to", "link", "touch", "writeguard", "runtime", "posix",
    "nt", "audit", "addaudithook", "settrace", "setprofile", "meta_path", "path_hooks",
    "stdin_fd", "dup2", "fdopen",
))

SYS_ATTRIBUTES = frozenset((
    "argv", "stdin", "stdout", "stderr", "exit", "version", "version_info", "maxsize",
    "byteorder", "platform", "float_info", "int_info", "getrecursionlimit", "getsizeof",
))

_WRITE_MODE_CHARS = frozenset("wax+")
_PATH_WRITE_METHODS = {"write_text": "overwrite", "write_bytes": "overwrite",
                       "unlink": "delete", "rmdir": "delete", "touch": "create",
                       "mkdir": "mkdir", "rename": "rename", "replace": "rename"}
_MODULE_WRITE_CALLS = {
    ("os", "remove"): "delete", ("os", "unlink"): "delete", ("os", "rmdir"): "delete",
    ("os", "rename"): "rename", ("os", "replace"): "rename", ("os", "truncate"): "truncate",
    ("os", "mkdir"): "mkdir", ("os", "makedirs"): "mkdir", ("shutil", "rmtree"): "delete",
    ("shutil", "copy"): "copy", ("shutil", "copyfile"): "copy", ("shutil", "copy2"): "copy",
    ("shutil", "move"): "rename",
}


class Finding:
    """Why code is not confined, or a write it obviously performs."""

    __slots__ = ("reason", "line")

    def __init__(self, reason, line):
        self.reason = reason
        self.line = line

    def __repr__(self):
        return "Finding(%r, line %s)" % (self.reason, self.line)


EXPORT_MODULE = "bops.writeguard.export"


def _module_allowed(name, engine):
    root = name.split(".")[0]
    if engine and root == "bops":
        if name.startswith("bops.writeguard") and name not in ("bops.writeguard", EXPORT_MODULE):
            return False         # the guard's own machinery is not callable from engine code
        return not any(part.startswith("_") for part in name.split("."))
    return name in PURE_MODULES


def _read_only_open(node):
    """`open(path)` or `open(path, <literal read-only mode>)`: a call that cannot write."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"):
        return False
    if len(node.args) > 2 or any(k.arg not in ("mode", "encoding", "errors", "newline")
                                 for k in node.keywords):
        return False
    modes = [node.args[1]] if len(node.args) > 1 else []
    modes += [k.value for k in node.keywords if k.arg == "mode"]
    return all(isinstance(m, ast.Constant) and isinstance(m.value, str) and
               set(m.value) <= set("rbt") for m in modes)


def confinement_findings(code, engine=False):
    """Every reason `code` is not confined. An empty list means confined.

    `engine=True` admits `bops` and its public submodules. Code that does not parse is not
    confined.
    """
    try:
        tree = ast.parse(code, mode="exec")
    except (SyntaxError, ValueError) as error:
        return [Finding("does not parse as Python (%s)" % error.__class__.__name__,
                        getattr(error, "lineno", None))]
    findings = []
    sys_names = set()
    read_opens = {id(node.func) for node in ast.walk(tree) if _read_only_open(node)}

    def add(reason, node):
        findings.append(Finding(reason, getattr(node, "lineno", None)))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "bops.writeguard":
                    add("imports bops.writeguard", node)
                elif not _module_allowed(alias.name, engine):
                    add("imports %s" % alias.name, node)
                elif alias.name == "sys":
                    sys_names.add(alias.asname or "sys")
                if alias.asname and alias.asname.startswith("_"):
                    add("binds a private name", node)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                add("uses a relative import", node)
            elif not _module_allowed(module, engine):
                add("imports from %s" % module, node)
            for alias in node.names:
                if alias.name == "*":
                    add("uses a star import", node)
                elif alias.name.startswith("_") or (alias.asname or "").startswith("_"):
                    add("imports a private name", node)
                elif module == "sys" and alias.name not in SYS_ATTRIBUTES:
                    add("imports sys.%s" % alias.name, node)
                elif engine and module.split(".")[0] == "bops" and alias.name in BLOCKED_ATTRIBUTES:
                    add("imports %s from %s" % (alias.name, module), node)
                elif module == "bops.writeguard" and alias.name != "export":
                    add("imports %s from bops.writeguard" % alias.name, node)
        elif isinstance(node, ast.Name):
            if node.id.startswith("_") and node.id != "_":
                add("uses the private name %s" % node.id, node)
            elif node.id in BLOCKED_BUILTINS and id(node) not in read_opens:
                add("uses %s" % node.id, node)
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                add("uses the private attribute %s" % node.attr, node)
            elif node.attr in BLOCKED_ATTRIBUTES:
                add("uses the attribute %s" % node.attr, node)
            elif isinstance(node.value, ast.Name) and node.value.id in sys_names \
                    and node.attr not in SYS_ATTRIBUTES:
                add("uses sys.%s" % node.attr, node)
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                add("assigns to an attribute", node)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            add("rebinds a global name", node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.decorator_list:
                add("uses a decorator", node)
            if node.name.startswith("_"):
                add("defines a private name", node)
        elif isinstance(node, (ast.AsyncFunctionDef, ast.Await, ast.AsyncWith, ast.AsyncFor)):
            add("uses async code", node)
    return findings


def is_confined(code, engine=False):
    return not confinement_findings(code, engine=engine)


def _literal_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def write_targets(code):
    """Best-effort `(kind, literal target or None)` for writes the code obviously performs."""
    try:
        tree = ast.parse(code, mode="exec")
    except (SyntaxError, ValueError):
        return []
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "open" and node.args:
            mode = _literal_str(node.args[1]) if len(node.args) > 1 else None
            for keyword in node.keywords:
                if keyword.arg == "mode":
                    mode = _literal_str(keyword.value)
            if mode is None and (len(node.args) > 1 or any(k.arg == "mode" for k in node.keywords)):
                found.append(("unknown_write", _literal_str(node.args[0])))
            elif mode and _WRITE_MODE_CHARS & set(mode):
                kind = "append" if "a" in mode else "create" if "x" in mode else \
                    "modify" if "+" in mode and "w" not in mode else "overwrite"
                found.append((kind, _literal_str(node.args[0])))
        elif isinstance(func, ast.Attribute):
            owner = func.value
            if isinstance(owner, ast.Name) and (owner.id, func.attr) in _MODULE_WRITE_CALLS:
                kind = _MODULE_WRITE_CALLS[(owner.id, func.attr)]
                index = 1 if kind in ("rename", "copy") else 0     # the path that changes
                target = _literal_str(node.args[index]) if len(node.args) > index else None
                found.append((kind, target))
            elif func.attr in _PATH_WRITE_METHODS and func.attr != "replace":
                target = None
                if isinstance(owner, ast.Call) and owner.args:
                    target = _literal_str(owner.args[0])
                found.append((_PATH_WRITE_METHODS[func.attr], target))
            elif func.attr == "truncate":
                found.append(("truncate", None))
    return found
