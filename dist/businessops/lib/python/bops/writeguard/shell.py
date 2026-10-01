"""A conservative POSIX-shell reader for the write classifier (ADR-0051).

This is not a shell. It reads a command string far enough to answer one question: which
simple commands run, with which words and which redirections. It never evaluates anything.

It is deliberately partial. The constructs it does not model - command substitution,
process substitution, subshells, arithmetic, backticks, `case` - raise `ShellParseError`,
and the classifier treats a command it cannot read as one it cannot prove read-only. That is
the whole security property: an unreadable command is never assumed safe.

What it does model:

- quoting: single quotes, double quotes, backslash escapes, line continuations;
- the list and pipeline operators `;` `&` `&&` `||` `|` `|&` and newlines;
- redirections `<` `>` `>>` `>|` `<>` `&>` `&>>` `N>` `N>>` `N<` `N>&M` `>&word`, here-strings
  `<<<` and here-documents `<<` / `<<-`, whose bodies are data rather than commands;
- expansions, only far enough to know that a word is *not* literal (`$NAME`, `${...}`,
  `$'...'`, unquoted globs, a leading `~`);
- exactly one command-substitution shape, the one every BusinessOps command and skill uses to
  pass engine code: `"$(cat <<'PY' ... PY\n)"`. Its quoted delimiter means the body is not
  expanded, so its value is the body itself.

Standard library only.
"""

import re


class ShellParseError(ValueError):
    """The command uses a construct this reader does not model."""


class Word:
    """One shell word after quote removal.

    `literal` is False when any part of the word would be expanded by the shell (a variable,
    an unquoted glob, `~user`), so its runtime value is not the text read here. A leading `~`
    or `~/` sets `tilde` instead: the caller expands it against the home it trusts.
    """

    __slots__ = ("text", "literal", "glob", "tilde")

    def __init__(self, text, literal=True, glob=False, tilde=False):
        self.text = text
        self.literal = literal
        self.glob = glob
        self.tilde = tilde

    def __repr__(self):
        return "Word(%r%s)" % (self.text, "" if self.literal else ", expanded")


class Redirect:
    """One redirection. `target` is a Word, or None for a here-document or an fd duplicate.

    A here-document keeps its `body` and whether its delimiter was quoted: an unquoted body is
    expanded by the shell, so it is literal only when it contains no `$`.
    """

    __slots__ = ("op", "fd", "target", "dup", "body", "body_literal")

    def __init__(self, op, fd, target=None, dup=False):
        self.op = op
        self.fd = fd
        self.target = target
        self.dup = dup
        self.body = None
        self.body_literal = False

    def __repr__(self):
        return "Redirect(%r, %r, %r)" % (self.op, self.fd, self.target)


class Command:
    """One simple command: leading assignments, words and redirections.

    `connector` is the operator that preceded it (`None` for the first command), and
    `piped`/`background` say whether it runs as part of a pipeline or in the background, which
    matters for `cd`: a `cd` there does not change the directory of what follows.
    """

    __slots__ = ("assignments", "words", "redirects", "connector", "piped", "background")

    def __init__(self):
        self.assignments = []
        self.words = []
        self.redirects = []
        self.connector = None
        self.piped = False
        self.background = False

    def __repr__(self):
        return "Command(%r, %r, %r)" % ([w.text for w in self.words], self.assignments,
                                        self.redirects)


_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
_ASSIGNMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\+?=")
_ENGINE_SUBSTITUTION = re.compile(r"\$\(cat <<(?:'([A-Za-z_][A-Za-z0-9_]*)'|\"([A-Za-z_][A-Za-z0-9_]*)\")\n")
_GLOB = frozenset("*?[")
_META = frozenset(" \t\n;&|<>()")
_KEYWORDS = frozenset(("if", "then", "else", "elif", "fi", "for", "while", "until", "do",
                       "done", "case", "esac", "select", "function", "coproc", "[[", "]]"))


class _Reader:

    def __init__(self, source):
        self.s = source
        self.i = 0
        self.n = len(source)
        self.commands = []
        self.current = Command()
        self.pending_heredocs = []
        self.expect_redirect = None
        self.next_connector = None

    # -- words ---------------------------------------------------------------------------

    def read_word(self):
        """Read one word starting at self.i. Returns a Word, or None if no word starts here."""
        parts = []
        literal = True
        glob = False
        tilde = False
        start = self.i
        s = self.s
        while self.i < self.n:
            c = s[self.i]
            if c in _META:
                break
            if c == "\\":
                if self.i + 1 < self.n and s[self.i + 1] == "\n":
                    self.i += 2
                    continue
                if self.i + 1 < self.n:
                    parts.append(s[self.i + 1])
                self.i += 2
                continue
            if c == "'":
                end = s.find("'", self.i + 1)
                if end < 0:
                    raise ShellParseError("unterminated single quote")
                parts.append(s[self.i + 1:end])
                self.i = end + 1
                continue
            if c == '"':
                text, lit = self.read_double_quoted()
                parts.append(text)
                literal = literal and lit
                continue
            if c == "`":
                raise ShellParseError("backtick command substitution")
            if c == "$":
                nxt = s[self.i + 1] if self.i + 1 < self.n else ""
                if nxt == "(":
                    raise ShellParseError("command substitution")
                if nxt == "'":
                    end = self._find_ansi_end(self.i + 2)
                    parts.append(s[self.i:end + 1])
                    self.i = end + 1
                    literal = False
                    continue
                if nxt == "{" or nxt == "_" or nxt.isalnum() or nxt in "@*#?-$!":
                    parts.append(self._read_expansion())
                    literal = False
                    continue
                parts.append("$")
                self.i += 1
                continue
            if c in _GLOB:
                glob = True
                literal = False
            if c == "~" and self.i == start:
                tilde = True
            if c in "{}" and self.i == start and (self.i + 1 >= self.n or s[self.i + 1] in _META):
                parts.append(c)
                self.i += 1
                break
            parts.append(c)
            self.i += 1
        if self.i == start:
            return None
        text = "".join(parts)
        if tilde and not (text == "~" or text.startswith("~/")):
            tilde, literal = False, False       # ~user: another user's home, not resolved here
        return Word(text, literal, glob, tilde)

    def _find_ansi_end(self, j):
        while j < self.n:
            if self.s[j] == "\\":
                j += 2
                continue
            if self.s[j] == "'":
                return j
            j += 1
        raise ShellParseError("unterminated $'...' quote")

    def _read_expansion(self):
        s = self.s
        j = self.i + 1
        if s[j] == "{":
            depth = 1
            j += 1
            while j < self.n and depth:
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                elif s[j] in "`" or s.startswith("$(", j):
                    raise ShellParseError("substitution inside a parameter expansion")
                j += 1
            if depth:
                raise ShellParseError("unterminated ${...}")
        elif s[j] == "_" or s[j].isalpha():
            while j < self.n and (s[j] == "_" or s[j].isalnum()):
                j += 1
        else:
            j += 1
        text = s[self.i:j]
        self.i = j
        return text

    def read_double_quoted(self):
        """Read "..." starting at the opening quote. Returns (text, literal)."""
        s = self.s
        self.i += 1
        parts = []
        literal = True
        while True:
            if self.i >= self.n:
                raise ShellParseError("unterminated double quote")
            c = s[self.i]
            if c == '"':
                self.i += 1
                return "".join(parts), literal
            if c == "\\":
                nxt = s[self.i + 1] if self.i + 1 < self.n else ""
                if nxt == "\n":
                    self.i += 2
                    continue
                if nxt in '$`"\\':
                    parts.append(nxt)
                    self.i += 2
                    continue
                parts.append(c)
                self.i += 1
                continue
            if c == "`":
                raise ShellParseError("backtick command substitution")
            if c == "$":
                nxt = s[self.i + 1] if self.i + 1 < self.n else ""
                if nxt == "(":
                    parts.append(self._read_engine_substitution())
                    continue
                if nxt == "{" or nxt == "_" or nxt.isalnum() or nxt in "@*#?-$!":
                    parts.append(self._read_expansion())
                    literal = False
                    continue
            parts.append(c)
            self.i += 1

    def _read_engine_substitution(self):
        """The one admitted substitution: "$(cat <<'DELIM'\\n<body>\\nDELIM\\n)". Its value is <body>."""
        match = _ENGINE_SUBSTITUTION.match(self.s, self.i)
        if not match:
            raise ShellParseError("command substitution")
        delimiter = match.group(1) or match.group(2)
        body_start = match.end()
        pos = body_start
        while True:
            line_end = self.s.find("\n", pos)
            if line_end < 0:
                raise ShellParseError("unterminated here-document in substitution")
            if self.s[pos:line_end] == delimiter:
                break
            pos = line_end + 1
        body = self.s[body_start:pos]
        close = re.compile(r"[ \t\n]*\)").match(self.s, line_end + 1)
        if not close:
            raise ShellParseError("unexpected text after the substituted here-document")
        self.i = close.end()
        return body[:-1] if body.endswith("\n") else body

    # -- structure -----------------------------------------------------------------------

    def finish_command(self, connector=None):
        cmd = self.current
        if self.expect_redirect is not None:
            raise ShellParseError("redirection without a target")
        if cmd.words or cmd.redirects or cmd.assignments:
            cmd.connector = self.next_connector
            self.commands.append(cmd)
        elif connector not in (None, "\n"):
            if connector in ("|", "|&", "&&", "||") or self.commands == []:
                raise ShellParseError("operator %r without a command" % connector)
        self.current = Command()
        self.next_connector = connector
        return cmd

    def read_heredoc_bodies(self):
        for strip_tabs, delimiter, quoted, redirect in self.pending_heredocs:
            lines = []
            while True:
                if self.i >= self.n:
                    raise ShellParseError("unterminated here-document")
                line_end = self.s.find("\n", self.i)
                if line_end < 0:
                    line_end = self.n
                line = self.s[self.i:line_end]
                self.i = min(line_end + 1, self.n)
                check = line.lstrip("\t") if strip_tabs else line
                if check == delimiter:
                    break
                if not quoted and ("`" in line or "$(" in line):
                    raise ShellParseError("substitution inside an unquoted here-document")
                lines.append(check if strip_tabs else line)
            redirect.body = "\n".join(lines) + ("\n" if lines else "")
            redirect.body_literal = quoted or "$" not in redirect.body
        self.pending_heredocs = []

    def add_word(self, word):
        cmd = self.current
        if self.expect_redirect is not None:
            op, fd = self.expect_redirect
            self.expect_redirect = None
            if op in ("<<", "<<-"):
                redirect = Redirect(op, fd)
                self.pending_heredocs.append((op == "<<-", word.text,
                                              self._delimiter_was_quoted, redirect))
                cmd.redirects.append(redirect)
                return
            if op in (">&", "<&") and (word.text.isdigit() or word.text == "-"):
                cmd.redirects.append(Redirect(op, fd, dup=True))
                return
            cmd.redirects.append(Redirect(op, fd, word))
            return
        if not cmd.words:
            match = _ASSIGNMENT.match(word.text)
            if match:
                cmd.assignments.append((match.group(1), word))
                return
            if word.text in _KEYWORDS and word.literal:
                raise ShellParseError("shell keyword %r" % word.text)
        cmd.words.append(word)

    def run(self):
        s = self.s
        while self.i < self.n:
            c = s[self.i]
            if c in " \t":
                self.i += 1
                continue
            if c == "\n":
                self.i += 1
                self.finish_command("\n")
                self.read_heredoc_bodies()
                continue
            if c == "#" and self._at_word_start():
                end = s.find("\n", self.i)
                self.i = self.n if end < 0 else end
                continue
            if c in "()":
                raise ShellParseError("subshell or grouping")
            if s.startswith("&&", self.i) or s.startswith("||", self.i):
                self.finish_command(s[self.i:self.i + 2])
                self.i += 2
                continue
            if s.startswith(";;", self.i):
                raise ShellParseError("case terminator")
            if c == ";":
                self.finish_command(";")
                self.i += 1
                continue
            if s.startswith("|&", self.i):
                self._pipe("|&")
                continue
            if c == "|":
                self._pipe("|")
                continue
            if s.startswith("&>>", self.i) or s.startswith("&>", self.i):
                op = "&>>" if s.startswith("&>>", self.i) else "&>"
                self._redirect(op, None, len(op))
                continue
            if c == "&":
                self.current.background = True
                self.finish_command("&")
                self.i += 1
                continue
            if c in "<>":
                self._read_redirect_operator(None)
                continue
            # A word, possibly an fd number that prefixes a redirection (2>, 1>>).
            match = re.compile(r"\d+(?=[<>])").match(s, self.i)
            if match and self.expect_redirect is None:
                self.i = match.end()
                self._read_redirect_operator(int(match.group(0)))
                continue
            self._delimiter_was_quoted = False
            if self.expect_redirect is not None and self.expect_redirect[0] in ("<<", "<<-"):
                word_start = self.i
                word = self.read_word()
                self._delimiter_was_quoted = any(q in s[word_start:self.i] for q in "'\"\\")
            else:
                word = self.read_word()
            if word is None:
                raise ShellParseError("unexpected character %r" % c)
            self.add_word(word)
        self.finish_command(None)
        if self.pending_heredocs:
            raise ShellParseError("unterminated here-document")
        return self.commands

    def _at_word_start(self):
        return self.i == 0 or self.s[self.i - 1] in " \t\n;&|"

    def _pipe(self, op):
        self.current.piped = True
        self.finish_command(op)
        self.current.piped = True
        self.i += len(op)

    def _redirect(self, op, fd, length):
        if self.expect_redirect is not None:
            raise ShellParseError("redirection without a target")
        self.i += length
        self.expect_redirect = (op, fd)

    def _read_redirect_operator(self, fd):
        s = self.s
        for op in ("<<<", "<<-", "<<", "<>", "<&", ">>", ">&", ">|", "<", ">"):
            if s.startswith(op, self.i):
                if op in ("<", ">") and s.startswith("(", self.i + 1):
                    raise ShellParseError("process substitution")
                if op == "<<<":                     # a here-string: stdin data, no file
                    self.i += 3
                    while self.i < self.n and s[self.i] in " \t":
                        self.i += 1
                    if self.read_word() is None:
                        raise ShellParseError("here-string without a word")
                    return
                self._redirect(op, fd, len(op))
                return
        raise ShellParseError("unreadable redirection")


def parse(source):
    """Split `source` into simple commands. Raises ShellParseError for anything unmodelled."""
    if "\x00" in source:
        raise ShellParseError("NUL byte in command")
    reader = _Reader(source)
    reader._delimiter_was_quoted = False
    return reader.run()


def is_assignment_name(name):
    return bool(_NAME.match(name))
