"""What a Claude Code tool call would do to the filesystem, decided before it runs (ADR-0051).

`classify_tool_call()` turns one tool call - the exact `tool_input` the runtime is about to
execute - into a list of `policy.Operation`s, each decided `free`, `approval` or
`prohibited` by `policy.Policy`.

The shell classifier is an **allowlist**. A command is read-only only if every simple command
in it is on the read-only list, with arguments that keep it read-only, and every redirection
goes to a stream or a device. A command with known write semantics (`cp`, `mv`, `rm`, `tee`,
`touch` ...) yields operations on its resolved targets. Anything else - an unknown program, an
interpreter running a script, a construct the reader does not model - yields an `execute`
operation that needs approval. There is no list of dangerous strings to evade: `cat file.txt`
is read-only because `cat` with no redirection is, and `cat > file.txt` writes because the
parsed command carries an output redirection, not because the text contains `>`.

Paths are resolved against the hook input's working directory. After any `cd`, `pushd` or
`popd`, a relative path is treated as unresolved, because whether the `cd` succeeded is not
knowable in advance.

Standard library only.
"""

import hashlib
import json
import os
import re

from . import policy as P
from . import pyscan
from .shell import ShellParseError, Word, parse

WRITE_TOOLS = ("Bash", "Write", "Edit", "MultiEdit", "NotebookEdit", "PowerShell")

READ_ONLY_COMMANDS = frozenset((
    "cat", "head", "tail", "wc", "ls", "pwd", "echo", "printf", "grep", "egrep", "fgrep", "rg",
    "stat", "file", "du", "df", "which", "whoami", "id", "uname", "basename", "dirname",
    "realpath", "readlink", "cut", "tr", "nl", "od", "hexdump", "cmp", "diff", "comm",
    "column", "jq", "sha256sum", "sha1sum", "sha512sum", "md5sum", "cksum", "true", "false",
    "test", "[", "sleep", "tree", "printenv", "less", "more", "strings", "fold", "fmt", "rev",
    "seq", "expand", "unexpand", "paste", "join", "type", "nproc", "locale", "getconf",
    "tac", "numfmt", "look", "ldd", "lsb_release", "whereis", "command", "sort",
))

# Setting one of these changes which program a later word runs, or what it loads.
DANGEROUS_VARIABLES = frozenset(("PATH", "IFS", "ENV", "BASH_ENV", "CDPATH", "SHELLOPTS",
                                 "BASHOPTS", "PROMPT_COMMAND", "HOME", "TMPDIR", "PS4"))
DANGEROUS_PREFIXES = ("LD_", "DYLD_", "PYTHON", "BASH_FUNC", "GIT_", "CLAUDE", "BOPS_")

SHELLS = frozenset(("sh", "bash", "dash", "zsh", "ksh"))
#: Native Windows, where the Bash tool is Git Bash (BOPS-R11). A module seam so tests can exercise
#: both platforms' path handling on either host.
_WINDOWS = os.name == "nt"
_PYTHON = re.compile(r"python(\d+(\.\d+)*)?$|py$")
_PYTHON_FLAGS = frozenset(("-I", "-E", "-s", "-S", "-B", "-u", "-O", "-OO", "-q", "-b", "-bb"))

GIT_READ = frozenset(("status", "diff", "log", "show", "rev-parse", "ls-files", "ls-tree",
                      "blame", "describe", "shortlog", "grep", "cat-file", "whatchanged",
                      "rev-list", "merge-base", "name-rev", "count-objects", "check-ignore",
                      "version", "help"))
GIT_REWRITE = frozenset(("rebase", "filter-branch", "filter-repo", "replace", "update-ref"))
_FORCE_PUSH = re.compile(r"-f$|--force|--mirror$|--delete$|-d$|--prune$|-[A-Za-z]*f[A-Za-z]*$")
INJECTION_TOOLS = frozenset(("ScheduleWakeup", "CronCreate", "SendMessage", "RemoteTrigger",
                             "Agent", "Task"))

# The bound fields of each tool's input. A retry that changes only a tool's free-text
# description is the same operation; one that changes any of these is not.
BOUND_FIELDS = {
    "Bash": ("command",),
    "PowerShell": ("command",),
    "Write": ("file_path", "content"),
    "Edit": ("file_path", "old_string", "new_string", "replace_all"),
    "MultiEdit": ("file_path", "edits"),
    "NotebookEdit": ("notebook_path", "cell_id", "new_source", "cell_type", "edit_mode"),
}


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def input_digest(tool_name, tool_input):
    """sha256 of the bound fields of the tool input: the content an approval is bound to."""
    fields = BOUND_FIELDS.get(tool_name)
    if fields is None or not isinstance(tool_input, dict):
        bound = tool_input
    else:
        bound = dict((k, tool_input.get(k)) for k in fields)
    return hashlib.sha256(canonical_json([tool_name, bound]).encode("utf-8")).hexdigest()


class Classification:
    """The operations one tool call would perform, and whether it enters the BusinessOps engine."""

    __slots__ = ("tool", "operations", "engine")

    def __init__(self, tool, operations, engine=False):
        self.tool = tool
        self.operations = list(operations)
        self.engine = engine

    @property
    def decision(self):
        return P.strictest(op.decision for op in self.operations)

    def needing(self, decision):
        return [op for op in self.operations if op.decision == decision]

    def __repr__(self):
        return "Classification(%s, %s, %r)" % (self.tool, self.decision, self.operations)


# ---------------------------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------------------------

class _Context:
    """Per-command-line state: the policy, and the base for relative paths (None after a cd)."""

    def __init__(self, policy):
        self.policy = policy
        self.base = policy.cwd
        # True only while classifying a Bash command line: a device name there is a shell device.
        self.shell = False
        self.ops = []
        self.engine = False

    def resolve(self, word):
        """Canonical path for a word, or None when its runtime value is not knowable here."""
        if word.glob or not (word.literal or word.tilde):
            return None
        text = word.text
        if not text:
            return None
        if self.shell and _WINDOWS and word.literal and P.Policy.is_device(text):
            # BOPS-R11. On native Windows the Bash tool is Git Bash, which maps `/dev/null` and the
            # other POSIX device names to devices; os.path.realpath() would instead turn them into
            # drive paths such as C:\dev\null, which read as new files. Only a shell word, only the
            # exact device names Policy.is_device() admits, only on Windows: a file tool's path
            # (Write, Edit, NotebookEdit) still resolves to the real file it would create.
            return text
        if word.tilde or os.path.isabs(text):
            return self.policy.resolve(text)
        if self.base is None:
            return None
        return self.policy.resolve(text, self.base)

    def write(self, word, kind, detail, sources=()):
        target = self.resolve(word)
        if target is None:
            self.ops.append(P.Operation(P.UNKNOWN_WRITE, detail="%s %s" % (detail, _short(word.text)),
                                        sources=sources))
            return
        exists = os.path.lexists(target)
        if kind in (P.OVERWRITE, P.CREATE):
            kind = P.OVERWRITE if exists else P.CREATE
        elif kind in (P.APPEND, P.MODIFY, P.TRUNCATE) and not exists:
            kind = P.CREATE
        self.ops.append(P.Operation(kind, target, sources, exists, detail))

    def execute(self, detail):
        self.ops.append(P.Operation(P.EXECUTE, detail=_short(detail, 160)))


def _short(text, limit=80):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


# ---------------------------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------------------------

_REDIRECT_KIND = {">": P.OVERWRITE, ">|": P.OVERWRITE, "&>": P.OVERWRITE, ">&": P.OVERWRITE,
                  ">>": P.APPEND, "&>>": P.APPEND, "<>": P.MODIFY}


def _positionals(args, takes_value=()):
    """Split args into (options, positionals), honouring `--` and options that take a value."""
    options, positionals, it, done = [], [], iter(args), False
    for word in it:
        text = word.text
        if done or not text.startswith("-") or text == "-":
            positionals.append(word)
            continue
        if text == "--":
            done = True
            continue
        options.append(text)
        if text in takes_value:
            value = next(it, None)
            if value is not None:
                options.append(value.text)
    return options, positionals


def _copy_like(ctx, name, args):
    takes = {"cp": ("-t", "-S", "--target-directory"), "mv": ("-t", "-S", "--target-directory"),
             "install": ("-t", "-m", "-o", "-g", "-S", "--target-directory"),
             "ln": ("-t", "-S", "--target-directory")}[name]
    options, positionals = _positionals(args, takes)
    target_dir, no_target_dir = None, "-T" in options or "--no-target-directory" in options
    for i, opt in enumerate(options):
        if opt in ("-t", "--target-directory") and i + 1 < len(options):
            target_dir = options[i + 1]
        elif opt.startswith("--target-directory="):
            target_dir = opt.split("=", 1)[1]
    if target_dir is not None:
        dest, sources = Word(target_dir), positionals
        dest_is_dir = True
    else:
        if len(positionals) < 2:
            return
        dest, sources = positionals[-1], positionals[:-1]
        resolved = ctx.resolve(dest)
        dest_is_dir = bool(resolved) and os.path.isdir(resolved) and not no_target_dir
        if len(sources) > 1:
            dest_is_dir = True
    source_paths = [ctx.resolve(s) for s in sources]
    for word, path in zip(sources, source_paths):
        label = path or _short(word.text)
        if name == "mv":
            if path is None:
                ctx.ops.append(P.Operation(P.UNKNOWN_WRITE, detail="mv %s" % label))
            else:
                ctx.ops.append(P.Operation(P.MOVE_SOURCE, path, (), os.path.lexists(path), "mv"))
        kind = P.LINK if name == "ln" else P.OVERWRITE
        if dest_is_dir:
            base = ctx.resolve(dest)
            if base is None or path is None:
                ctx.ops.append(P.Operation(P.UNKNOWN_WRITE, detail="%s into %s" % (
                    name, _short(dest.text)), sources=(label,)))
                continue
            target = os.path.join(base, os.path.basename(path.rstrip(os.sep)))
            exists = os.path.lexists(target)
            if kind == P.OVERWRITE and not exists:
                kind = P.CREATE
            ctx.ops.append(P.Operation(kind, target, (label,), exists, name))
        else:
            ctx.write(dest, kind, name, sources=(label,))


def _git(ctx, args):
    words = list(args)
    while words and words[0].text.startswith("-"):
        flag = words.pop(0).text
        if flag == "-C" and words:
            path = ctx.resolve(words.pop(0))
            ctx.base = path
        elif flag in ("-c", "--exec-path") or flag.startswith(("-c", "--config-env")):
            ctx.execute("git %s (configuration can run programs)" % flag)
            return
    if not words:
        return
    sub, rest = words[0].text, [w.text for w in words[1:]]
    command = "git " + " ".join([sub] + rest)
    if sub in GIT_READ:
        for i, text in enumerate(rest):
            if text.startswith("--output"):
                if "=" in text:
                    ctx.write(Word(text.split("=", 1)[1]), P.OVERWRITE, "git --output")
                elif i + 1 < len(rest):
                    ctx.write(words[i + 2], P.OVERWRITE, "git --output")
        if sub == "grep" and any(t in ("-O", "--open-files-in-pager") or
                                 t.startswith("--open-files-in-pager") for t in rest):
            ctx.execute(command)
        return
    listing = {"branch": ("-a", "-r", "-v", "-vv", "-l", "--list", "--all", "--remotes",
                          "--show-current", "--verbose", "--no-color", "--color"),
               "tag": ("-l", "--list", "-n"), "remote": ("-v", "--verbose"),
               "config": ("--get", "--list", "-l", "--get-all", "--get-regexp", "--show-origin")}
    if sub in ("branch", "tag", "remote") and all(t in listing[sub] for t in rest):
        return
    if sub == "config" and rest and rest[0] in listing["config"]:
        return
    if sub == "stash" and rest[:1] in (["list"], ["show"]):
        return
    if sub == "reflog" and rest[:1] in ([], ["show"]):
        return
    if sub == "branch" and any(t in ("-d", "-D", "--delete") or t.startswith("--delete") for t in rest):
        kind = P.GIT_REWRITE
    elif sub == "push" and any(_FORCE_PUSH.match(t) or t.startswith(("+", ":")) for t in rest):
        kind = P.GIT_REWRITE
    elif sub == "push":
        kind = P.GIT_PUSH
    elif sub == "commit" and "--amend" in rest:
        kind = P.GIT_REWRITE
    elif sub == "commit":
        kind = P.GIT_COMMIT
    elif sub in GIT_REWRITE:
        kind = P.GIT_REWRITE
    else:
        kind = P.GIT_MUTATION
    ctx.ops.append(P.Operation(kind, detail=_short(command, 160)))


_PYTHON_KINDS = {"overwrite": P.OVERWRITE, "append": P.APPEND, "create": P.CREATE,
                 "modify": P.MODIFY, "truncate": P.TRUNCATE, "delete": P.DELETE,
                 "mkdir": P.MKDIR}


def _python(ctx, cmd, args):
    code, it = None, iter(args)
    for word in it:
        text = word.text
        if text in _PYTHON_FLAGS:
            continue
        if text == "-c":
            value = next(it, None)
            code = value.text if value is not None and value.literal else None
            if code is None:
                ctx.execute("python -c with code that is expanded by the shell")
                return
            break
        if text == "-":
            heredocs = [r for r in cmd.redirects if r.body is not None]
            if heredocs and heredocs[-1].body_literal:
                code = heredocs[-1].body
                break
            ctx.execute("python reading code from standard input")
            return
        ctx.execute("python %s" % text)
        return
    if code is None:
        ctx.execute("an interactive or piped Python interpreter")
        return
    findings = pyscan.confinement_findings(code)
    if not findings:
        return
    for kind, literal in pyscan.write_targets(code):
        if literal is None:
            ctx.ops.append(P.Operation(P.UNKNOWN_WRITE, detail="Python %s" % kind))
        else:
            ctx.write(Word(literal), _PYTHON_KINDS.get(kind, P.OVERWRITE), "Python")
    ctx.execute("Python code that is not confined (%s)" % findings[0].reason)


def _launcher(ctx):
    return os.path.join(ctx.policy.plugin, "lib", "bops_run.sh")


def _mentions_guard(words):
    return any("bops_run" in w.text or "writeguard" in w.text for w in words)


#: Launcher entries only the harness may run: the write guard (ADR-0051) and the verbatim
#: capture of the scout's reply (ADR-0053). From a tool call either would let a model forge
#: what the harness alone is trusted to record, so both are refused outright.
_HARNESS_ENTRIES = ("--guard", "--handback")


def _harness_entry(words):
    return next((w for w in words if w in _HARNESS_ENTRIES), None)


def _shell_program(ctx, cmd, name, args, depth):
    words = [w.text for w in args]
    launcher = _launcher(ctx)
    first = args[0] if args else None
    if first is not None and first.literal and ctx.resolve(first) == os.path.realpath(launcher):
        if _harness_entry(words):
            ctx.ops.append(P.Operation(P.GUARD_ENTRY, detail="bops_run %s" % _harness_entry(words)))
            return
        if name != "sh" or cmd.assignments:
            ctx.execute("the BusinessOps engine launched with a changed environment or shell")
            return
        if words[1:] == ["--where"]:
            ctx.engine = True
            return
        if len(args) >= 3 and words[1] == "-c":
            if not args[2].literal:
                ctx.execute("BusinessOps engine code that is expanded by the shell")
                return
            findings = pyscan.confinement_findings(args[2].text, engine=True)
            ctx.engine = True
            if findings:
                ctx.execute("BusinessOps engine code that is not confined (%s)" % findings[0].reason)
            return
        ctx.execute("the BusinessOps engine launcher with unexpected arguments")
        return
    if _harness_entry(words) and _mentions_guard(args):
        ctx.ops.append(P.Operation(P.GUARD_ENTRY, detail="%s %s" % (name, _harness_entry(words))))
        return
    if len(args) >= 2 and words[0] == "-c" and args[1].literal and depth < 2 and \
            not cmd.assignments:
        _bash(ctx, args[1].text, depth + 1)
        return
    ctx.execute("%s %s" % (name, " ".join(words)))


def _simple(ctx, cmd, depth):
    for name, word in cmd.assignments:
        if name in DANGEROUS_VARIABLES or name.startswith(DANGEROUS_PREFIXES):
            ctx.execute("setting %s changes what later commands run" % name)
    for redirect in cmd.redirects:
        kind = _REDIRECT_KIND.get(redirect.op)
        if kind is None or redirect.dup:
            continue
        ctx.write(redirect.target, kind, "shell %s" % redirect.op)
    if not cmd.words:
        return
    head = cmd.words[0]
    args = cmd.words[1:]
    if not head.literal or head.tilde or "/" in head.text:
        if _mentions_guard(cmd.words) and _harness_entry([w.text for w in cmd.words]):
            ctx.ops.append(P.Operation(P.GUARD_ENTRY,
                                       detail=_harness_entry([w.text for w in cmd.words])))
            return
        ctx.execute("the program %s" % _short(head.text))
        return
    name = head.text
    if name in ("cd", "pushd", "popd"):
        ctx.base = None          # whether it succeeded, and where it went, is not knowable here
        return
    if name in READ_ONLY_COMMANDS:
        _read_only_arguments(ctx, name, args)
        return
    if name in SHELLS:
        _shell_program(ctx, cmd, name, args, depth)
        return
    if _PYTHON.match(name):
        if _mentions_guard(args) and _harness_entry([w.text for w in args]):
            ctx.ops.append(P.Operation(P.GUARD_ENTRY,
                                       detail="python %s" % _harness_entry([w.text for w in args])))
            return
        _python(ctx, cmd, args)
        return
    handler = _WRITERS.get(name)
    if handler is not None:
        handler(ctx, name, args)
        return
    if name == "git":
        _git(ctx, args)
        return
    ctx.execute("the program %s" % name)


def _read_only_arguments(ctx, name, args):
    texts = [w.text for w in args]
    if name == "sort":
        for i, text in enumerate(texts):
            if text in ("-o", "--output") and i + 1 < len(args):
                ctx.write(args[i + 1], P.OVERWRITE, "sort -o")
            elif text.startswith("--output="):
                ctx.write(Word(text.split("=", 1)[1]), P.OVERWRITE, "sort --output")
            elif text.startswith("-o") and len(text) > 2:
                ctx.write(Word(text[2:]), P.OVERWRITE, "sort -o")
    elif name == "command" and texts and not texts[0].startswith("-"):
        ctx.execute("command %s" % " ".join(texts))
    elif name == "date" and any(t.startswith(("-s", "--set")) for t in texts):
        ctx.execute("date --set")


def _sed(ctx, name, args):
    texts = [w.text for w in args]
    in_place = any(t == "--in-place" or t.startswith("--in-place=") or
                   (t.startswith("-") and not t.startswith("--") and "i" in t[1:]) for t in texts)
    scripted = any(t in ("-e", "--expression") or t.startswith("--expression=") for t in texts)
    if any(t in ("-f", "--file") or t.startswith("--file=") for t in texts):
        ctx.execute("sed with a script file")
        return
    options, positionals = _positionals(args, ("-e", "--expression", "-l", "--line-length"))
    scripts = [options[i + 1] for i, o in enumerate(options) if o in ("-e", "--expression")
               and i + 1 < len(options)]
    if not scripted and positionals:
        scripts.append(positionals[0].text)
        positionals = positionals[1:]
    for script in scripts:
        if re.search(r"(^|[;{}\n]|/[A-Za-z0-9]*)\s*[wWe](\s|$)", script) or \
                re.search(r"(^|[;{}\n])\s*[wWe]\s*\S", script):
            ctx.execute("a sed script that can write or execute")
            return
    if in_place:
        for word in positionals:
            ctx.write(word, P.OVERWRITE, "sed -i")


def _tee(ctx, name, args):
    options, positionals = _positionals(args)
    append = any(o in ("-a", "--append") for o in options)
    for word in positionals:
        ctx.write(word, P.APPEND if append else P.OVERWRITE, "tee")


def _touch(ctx, name, args):
    _options, positionals = _positionals(args, ("-d", "-t", "-r", "--date", "--reference"))
    for word in positionals:
        ctx.write(word, P.MODIFY, "touch")


def _mkdir(ctx, name, args):
    _options, positionals = _positionals(args, ("-m", "--mode"))
    for word in positionals:
        target = ctx.resolve(word)
        if target is None:
            ctx.ops.append(P.Operation(P.UNKNOWN_WRITE, detail="mkdir %s" % _short(word.text)))
        else:
            ctx.ops.append(P.Operation(P.MKDIR, target, (), os.path.lexists(target), "mkdir"))


def _delete(ctx, name, args):
    _options, positionals = _positionals(args)
    for word in positionals:
        target = ctx.resolve(word)
        if target is None:
            ctx.ops.append(P.Operation(P.UNKNOWN_WRITE, detail="%s %s" % (name, _short(word.text))))
        else:
            ctx.ops.append(P.Operation(P.DELETE, target, (), os.path.lexists(target), name))


def _truncate(ctx, name, args):
    options, positionals = _positionals(args, ("-s", "-r", "--size", "--reference"))
    for word in positionals:
        ctx.write(word, P.TRUNCATE, "truncate")


def _dd(ctx, name, args):
    notrunc = any(w.text.startswith("conv=") and "notrunc" in w.text for w in args)
    for word in args:
        if word.text.startswith("of="):
            ctx.write(Word(word.text[3:], word.literal, word.glob, word.tilde),
                      P.MODIFY if notrunc else P.OVERWRITE, "dd")


def _attributes(ctx, name, args):
    options, positionals = _positionals(args)
    if not any(o.startswith("--reference") for o in options):
        positionals = positionals[1:]
    for word in positionals:
        ctx.write(word, P.MODIFY, name)


def _uniq_like(ctx, name, args):
    """`uniq IN OUT` and `xxd IN OUT` write their second operand."""
    takes = ("-f", "-s", "-w") if name == "uniq" else ("-c", "-l", "-o", "-g", "-s", "-C", "-n")
    options, positionals = _positionals(args, takes)
    if len(positionals) >= 2:
        ctx.write(positionals[1], P.OVERWRITE, name)


def _find(ctx, name, args):
    texts = [w.text for w in args]
    if "-delete" in texts:
        ctx.ops.append(P.Operation(P.UNKNOWN_WRITE, detail="find -delete"))
    if any(t in ("-exec", "-execdir", "-ok", "-okdir") for t in texts):
        ctx.execute("find -exec")
    for i, text in enumerate(texts):
        if text in ("-fprint", "-fprint0", "-fprintf", "-fls") and i + 1 < len(args):
            ctx.write(args[i + 1], P.OVERWRITE, "find %s" % text)


def _env(ctx, name, args):
    if args:
        ctx.execute("env %s" % " ".join(w.text for w in args))


_WRITERS = {
    "cp": _copy_like, "mv": _copy_like, "install": _copy_like, "ln": _copy_like,
    "rm": _delete, "unlink": _delete, "rmdir": _delete, "shred": _delete,
    "tee": _tee, "touch": _touch, "mkdir": _mkdir, "truncate": _truncate, "dd": _dd,
    "chmod": _attributes, "chown": _attributes, "chgrp": _attributes,
    "uniq": _uniq_like, "xxd": _uniq_like, "find": _find, "sed": _sed, "env": _env,
}


def _bash(ctx, command, depth=0):
    try:
        commands = parse(command)
    except ShellParseError as error:
        ctx.execute("a shell command that cannot be classified (%s)" % error)
        return
    for cmd in commands:
        _simple(ctx, cmd, depth)


# ---------------------------------------------------------------------------------------------
# Tool calls
# ---------------------------------------------------------------------------------------------

def classify_tool_call(tool_name, tool_input, policy):
    """Classify the exact tool input about to run. Every operation leaves with a decision."""
    ctx = _Context(policy)
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    if tool_name == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str):
            ctx.execute("a Bash call without a command string")
        else:
            ctx.shell = True
            _bash(ctx, command)
    elif tool_name == "Write":
        _file_tool(ctx, tool_input.get("file_path"), P.OVERWRITE, "Write tool")
    elif tool_name in ("Edit", "MultiEdit"):
        _file_tool(ctx, tool_input.get("file_path"), P.MODIFY, "%s tool" % tool_name)
    elif tool_name == "NotebookEdit":
        _file_tool(ctx, tool_input.get("notebook_path"), P.MODIFY, "NotebookEdit tool")
    elif tool_name == "PowerShell":
        ctx.execute("a PowerShell command, which BusinessOps cannot classify")
    for op in ctx.ops:
        policy.decide(op)
    return Classification(tool_name, ctx.ops, engine=ctx.engine)


def _file_tool(ctx, path, kind, detail):
    if not isinstance(path, str) or not path:
        ctx.ops.append(P.Operation(P.UNKNOWN_WRITE, detail="%s without a path" % detail))
        return
    ctx.write(Word(path), kind, detail)


_APPROVAL_PHRASE = re.compile(r"approve\s+BOPS-W-[A-Z0-9]{8}", re.IGNORECASE)


def carries_approval_phrase(tool_input):
    """Whether a tool input contains an approval phrase (only the user may send one)."""
    try:
        text = json.dumps(tool_input, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(tool_input)
    return bool(_APPROVAL_PHRASE.search(text.replace("\\n", " ")))
