"""T-K: static guard for the ADR-0042 engine entry (M13-DEF-04).

Fails if the working-directory-relative engine entry, or any other way of reaching the engine,
comes back into a shipped command or skill. It reads the files as text and imports nothing from
them.

- A. `sys.path.insert(0, 'lib/python')`, and any `sys.path` manipulation, is gone from every
  command and skill.
- B. Every code block that reaches the engine opens with the canonical launcher line, in its
  plain form or its heredoc form.
- C. No command or skill imports `bops` outside such a block.
- D. The launcher uses only the standard library, and opens no process, socket or URL.
- E. Exactly one launcher exists.
- F. No command or skill finds the plugin any other way: no `os.getcwd()`, `$PWD`, `$(pwd)`,
  `%CD%`, environment lookup, or `${CLAUDE_PLUGIN_ROOT}` outside the launcher line.
- G. No working-directory-relative fallback: `lib/python` appears in a code block only inside
  the launcher line.
- H. The launcher's logic is not duplicated into a command or skill.
- I. The five bare-import skills are covered; the delegating commands carry no engine block.
"""

import ast
import glob
import os
import re
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
#: BusinessOps M3 moved the M9-B harness from commands/ to dev/harness/ (ADR-0055); it is still
#: enumerated with the commands so every check keeps covering it at its new location.
LAUNCHER = os.path.join(REPO, "lib", "python", "bops_run.py")
#: The runtime-resolution boundary (ADR-0045). Since 2026-09-22 a command or skill names the
#: shell resolver, which chooses an interpreter and hands off to LAUNCHER with `-I` unchanged.
#: Before that the line named `python` directly, which is the defect M13-DEF-08 records: the
#: interpreter name was hard-coded, and a host that ships Python 3 only as `python3` could not
#: enter the engine at all. The launcher and its import boundary are untouched by that change.
RESOLVER = os.path.join(REPO, "lib", "bops_run.sh")
LAUNCHER_LINE = 'sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "'
#: The form this replaced. No shipped file may go back to it.
RETIRED_LAUNCHER_LINE = 'python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/bops_run.py" -c "'
HEREDOC_OPEN = LAUNCHER_LINE + "$(cat <<'PY'"

#: ADR-0056 amends ADR-0042's rule that the plugin root appears only in the launcher line by exactly one
#: form: a backticked plugin-root path to one of the shipped policy documents in `reference/`, written in
#: prose (never in a code block). It names a file for Claude to read and is not a way into the engine;
#: a relative `reference/...` path does not resolve in an installed plugin (BusinessOps M3.1, live test).
REFERENCE_TOKEN = re.compile(r"`\$\{CLAUDE_PLUGIN_ROOT\}/reference/([a-z-]+\.md)`")
REFERENCE_FILES = frozenset(os.listdir(os.path.join(REPO, "reference")))


def without_reference_tokens(line):
    """`line` with each permitted reference token removed; an unknown file name is left in place."""
    return REFERENCE_TOKEN.sub(lambda m: "" if m.group(1) in REFERENCE_FILES else m.group(0), line)
BARE_IMPORT_SKILLS = ("bops-benchmark-comparison", "bops-decision-support", "bops-executive-report",
                      "bops-strategy-recommendations", "bops-swot")
ENGINE_REFERENCE = re.compile(r"lib/python|lib/bops_run\.sh|^\s*from bops\b|^\s*import bops\b",
                              re.M)
BLOCK = re.compile(r"^```(\w*)\n(.*?)^```", re.M | re.S)
STDLIB_ONLY = {"sys", "builtins", "json", "os"}


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def shipped_markdown():
    paths = sorted((glob.glob(os.path.join(REPO, "commands", "*.md"))
         + glob.glob(os.path.join(REPO, "dev", "harness", "*.md"))) +
                   glob.glob(os.path.join(REPO, "skills", "*", "SKILL.md")))
    return {os.path.relpath(p, REPO).replace(os.sep, "/"): _read(p) for p in paths}


def engine_blocks(text):
    return [(m.group(1), m.group(2)) for m in BLOCK.finditer(text)
            if ENGINE_REFERENCE.search(m.group(2))]


def launcher_opened(body):
    first = body.split("\n", 1)[0]
    return first in (LAUNCHER_LINE, HEREDOC_OPEN)


class NoRelativeEntryRemains(unittest.TestCase):
    """A and G."""

    @classmethod
    def setUpClass(cls):
        cls.files = shipped_markdown()

    def test_the_old_entry_is_gone(self):
        for path, text in self.files.items():
            with self.subTest(path=path):
                self.assertNotIn("sys.path.insert(0, 'lib/python')", text)
                self.assertIsNone(re.search(r"sys\.path\s*(\.|\[|=)", text))

    def test_no_code_block_names_the_engine_directory_at_all(self):
        """The boundary line names `lib/bops_run.sh`; nothing names `lib/python` any more."""
        for path, text in self.files.items():
            for _lang, body in engine_blocks(text):
                for line in body.split("\n"):
                    with self.subTest(path=path, line=line):
                        self.assertNotIn("lib/python", line)

    def test_the_boundary_path_appears_only_on_the_boundary_line(self):
        for path, text in self.files.items():
            for _lang, body in engine_blocks(text):
                for line in body.split("\n")[1:]:
                    with self.subTest(path=path, line=line):
                        self.assertNotIn("bops_run.sh", line)

    def test_no_shipped_file_returns_to_the_hard_coded_interpreter(self):
        """M13-DEF-08 must not come back: no command or skill may name an interpreter itself."""
        for path, text in self.files.items():
            with self.subTest(path=path):
                self.assertNotIn(RETIRED_LAUNCHER_LINE, text)
                for _lang, body in engine_blocks(text):
                    for line in body.split("\n"):
                        self.assertIsNone(re.match(r"\s*(python|python3|py)\b", line),
                                          "a code line names an interpreter: %r" % line)


class EveryEngineBlockUsesTheLauncher(unittest.TestCase):
    """B, C and I."""

    @classmethod
    def setUpClass(cls):
        cls.files = shipped_markdown()

    def test_each_engine_block_opens_with_the_launcher(self):
        total = 0
        for path, text in self.files.items():
            for lang, body in engine_blocks(text):
                total += 1
                with self.subTest(path=path, first=body.split("\n", 1)[0]):
                    self.assertEqual(lang, "bash")
                    self.assertTrue(launcher_opened(body))
                    if body.startswith(HEREDOC_OPEN):
                        self.assertTrue(body.rstrip("\n").endswith('PY\n)"'))
                    else:
                        self.assertTrue(body.rstrip("\n").endswith('"'))
        self.assertGreaterEqual(total, 34)

    def test_no_bops_import_outside_a_launcher_block(self):
        for path, text in self.files.items():
            outside = BLOCK.sub("", text)
            with self.subTest(path=path):
                self.assertIsNone(re.search(r"^\s*(from bops\b|import bops\b)", outside, re.M))
            for _lang, body in (m.groups() for m in BLOCK.finditer(text)):
                if re.search(r"^\s*(from bops\b|import bops\b)", body, re.M):
                    with self.subTest(path=path, block=body.split("\n", 1)[0]):
                        self.assertTrue(launcher_opened(body))

    def test_the_five_bare_import_skills_run_through_the_launcher(self):
        for skill in BARE_IMPORT_SKILLS:
            text = self.files["skills/%s/SKILL.md" % skill]
            blocks = engine_blocks(text)
            with self.subTest(skill=skill):
                self.assertTrue(blocks)
                self.assertTrue(all(launcher_opened(body) for _l, body in blocks))
                self.assertNotIn("```python", text)

    def test_every_skill_and_every_engine_command_reaches_the_engine_only_through_it(self):
        with_engine = sorted(p for p, t in self.files.items() if engine_blocks(t))
        skills = [p for p in with_engine if p.startswith("skills/")]
        self.assertEqual(len(skills), len(glob.glob(os.path.join(REPO, "skills", "*", "SKILL.md"))))
        commands = [p for p in with_engine if p.startswith(("commands/", "dev/harness/"))]
        self.assertEqual(len(commands), 10)

    def test_delegating_commands_carry_no_engine_block(self):
        delegating = ("benchmark-comparison", "company-analysis", "competitor-analysis",
                      "decision-support", "executive-report", "industry-research",
                      "market-analysis", "strategy-analysis", "swot-analysis")
        for command in delegating:
            with self.subTest(command=command):
                text = self.files["commands/%s.md" % command]
                self.assertEqual(engine_blocks(text), [])
                self.assertNotIn("bops_run.py", text)
                self.assertNotIn("bops_run.sh", text)


class NoOtherPluginRootDiscovery(unittest.TestCase):
    """F and H."""

    @classmethod
    def setUpClass(cls):
        cls.files = shipped_markdown()

    def test_no_working_directory_or_environment_lookup(self):
        forbidden = re.compile(r"os\.getcwd\(|\$PWD\b|\$\(pwd\)|%CD%|os\.environ|getenv\(|"
                               r"\$CLAUDE_PLUGIN_ROOT\b|CLAUDE_SKILL_DIR")
        for path, text in self.files.items():
            for _lang, body in (m.groups() for m in BLOCK.finditer(text)):
                with self.subTest(path=path, block=body.split("\n", 1)[0]):
                    self.assertIsNone(forbidden.search(body))

    def test_the_plugin_root_appears_only_in_the_launcher_line(self):
        """Except for ADR-0056's reference tokens, which are removed before the check."""
        for path, text in self.files.items():
            for line in text.split("\n"):
                if "${CLAUDE_PLUGIN_ROOT}" in without_reference_tokens(line):
                    with self.subTest(path=path, line=line):
                        self.assertTrue(line in (LAUNCHER_LINE, HEREDOC_OPEN))

    def test_a_reference_token_names_a_shipped_document_and_is_never_in_a_code_block(self):
        """ADR-0056: the one permitted non-launcher use of the plugin root is prose, never code."""
        for path, text in self.files.items():
            for name in REFERENCE_TOKEN.findall(text):
                with self.subTest(path=path, file=name):
                    self.assertIn(name, REFERENCE_FILES)
            for _lang, body in (m.groups() for m in BLOCK.finditer(text)):
                with self.subTest(path=path, block=body.split("\n", 1)[0]):
                    self.assertNotIn("${CLAUDE_PLUGIN_ROOT}/reference/", body)

    def test_no_command_or_skill_duplicates_the_launcher(self):
        for path, text in self.files.items():
            with self.subTest(path=path):
                for marker in ("sys.flags.isolated", "realpath(__file__)", "__file__"):
                    self.assertNotIn(marker, text)


class TheLauncher(unittest.TestCase):
    """D and E."""

    def test_exactly_one_launcher_exists(self):
        # `dist/` holds the gitignored package built by scripts/build_distribution.py (ADR-0055):
        # a build copy of this launcher, not a second one in the repository.
        found = [p for p in glob.glob(os.path.join(REPO, "**", "bops_run.py"), recursive=True)
                 if not {".git", "dist"} & set(os.path.relpath(p, REPO).split(os.sep))]
        self.assertEqual([os.path.realpath(p) for p in found], [os.path.realpath(LAUNCHER)])
        for path in glob.glob(os.path.join(REPO, "lib", "python", "**", "*.py"), recursive=True):
            if os.path.realpath(path) != os.path.realpath(LAUNCHER):
                with self.subTest(path=path):
                    self.assertNotIn("sys.flags.isolated", _read(path))

    def test_the_launcher_is_standard_library_only(self):
        tree = ast.parse(_read(LAUNCHER))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        imported.discard("bops")          # the engine it verifies, imported after the boundary
        self.assertEqual(imported, STDLIB_ONLY)
        source = _read(LAUNCHER)
        for word in ("subprocess", "socket", "urllib", "http", "chdir", "environ[", "putenv"):
            with self.subTest(word=word):
                self.assertNotIn(word, source.split('"""', 2)[2])

    def test_isolation_is_checked_before_any_other_import(self):
        tree = ast.parse(_read(LAUNCHER))
        body = [n for n in tree.body if not (isinstance(n, ast.Expr) and
                                            isinstance(getattr(n, "value", None), ast.Constant))]
        imports_before_check = []
        for node in body:
            if isinstance(node, ast.If) and "isolated" in ast.dump(node.test):
                break
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports_before_check += [a.name for a in node.names]
        else:
            self.fail("no isolation check at module level")
        self.assertEqual(imports_before_check, ["sys"])

    def test_the_launcher_contains_no_fixed_path(self):
        source = _read(LAUNCHER).split('"""', 2)[2]
        self.assertIsNone(re.search(r"[A-Za-z]:[\\/]|/home/|/Users/|\.claude/plugins", source))
        self.assertNotIn(REPO, source)


if __name__ == "__main__":
    unittest.main()
