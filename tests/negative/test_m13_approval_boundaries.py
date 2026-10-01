"""M13.1 deterministic gap closure for the `architecture.md` section 8 approval matrix.

Coverage-matrix row **S5-12** - *Repository*: "`git commit` on request; `git push`" -
"Commit on request; **never push** unless instructed".

Whether a session commits is the user's decision and the model's behaviour. The product half
is deterministic: no BusinessOps component - no command, skill, agent, reference document or
engine module - instructs, scripts or executes a repository write, so nothing the plugin ships
can commit, push, tag or rewrite history on its own.

The engine's only process launches are the Tier-2 reader bootstrap and the managed read
(ADR-0008); the last test pins that neither is a `git` invocation.

Amended 2026-09-26 by the M13-DEF-24 remediation (ADR-0051). The write guard
(`bops/writeguard/`) must *recognise* `git push` and `git commit` in the model's tool calls in
order to deny them, so its source necessarily names them. It is excluded from the two textual
scans, and in their place a stricter structural test pins that the write guard launches no
process at all: no process-launching or network import, and no process-launching `os` call.
"""

import ast
import glob
import os
import re
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

SHIPPED_MARKDOWN = ("commands/*.md", "skills/*/SKILL.md", "skills/*/*.md", "agents/*.md",
                    "reference/*.md")
ENGINE = os.path.join(REPO, "lib", "python", "bops")

REPOSITORY_WRITE = re.compile(
    r"\bgit\s+(push|commit|tag|reset|rebase|merge|cherry-pick|revert|am|filter-branch)\b",
    re.IGNORECASE)


def _shipped_markdown():
    paths = set()
    for pattern in SHIPPED_MARKDOWN:
        paths.update(glob.glob(os.path.join(REPO, pattern)))
    return sorted(paths)


WRITE_GUARD = os.path.join(ENGINE, "writeguard")
PROCESS_LAUNCH = re.compile(r"\bsubprocess\b|\bos\.(system|popen|exec\w*|spawn\w*|posix_spawn\w*|fork\w*)\b"
                            r"|\bpty\b|\bmultiprocessing\b")


def _engine_modules():
    """Every engine module except the write guard, which recognises git commands to deny them."""
    return sorted(p for p in glob.glob(os.path.join(ENGINE, "**", "*.py"), recursive=True)
                  if not p.startswith(WRITE_GUARD + os.sep))


def _write_guard_modules():
    return sorted(glob.glob(os.path.join(WRITE_GUARD, "*.py")))


class NoComponentWritesTheRepository(unittest.TestCase):

    def test_the_scan_covers_the_shipped_components(self):
        paths = _shipped_markdown()
        for directory in ("commands", "skills", "agents", "reference"):
            with self.subTest(directory=directory):
                self.assertTrue(any(os.sep + directory + os.sep in p for p in paths))

    def test_no_shipped_markdown_instructs_a_repository_write(self):
        for path in _shipped_markdown():
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            with self.subTest(path=os.path.relpath(path, REPO)):
                self.assertIsNone(REPOSITORY_WRITE.search(text))

    def test_no_engine_module_scripts_a_repository_write(self):
        for path in _engine_modules():
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            with self.subTest(path=os.path.relpath(path, REPO)):
                self.assertIsNone(REPOSITORY_WRITE.search(text))

    def test_no_engine_process_launch_is_a_git_invocation(self):
        offenders = []
        for path in _engine_modules():
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), filename=path)
            for node in ast.walk(tree):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and node.value.strip().lower() == "git"):
                    offenders.append("%s:%d" % (os.path.relpath(path, REPO), node.lineno))
        self.assertEqual(offenders, [])

    def test_the_write_guard_launches_no_process(self):
        """The replacement for the two textual scans over `bops/writeguard/` (ADR-0051)."""
        modules = _write_guard_modules()
        self.assertGreaterEqual(len(modules), 8)
        for path in modules:
            with open(path, encoding="utf-8") as handle:
                source = handle.read()
            tree = ast.parse(source, filename=path)
            with self.subTest(path=os.path.relpath(path, REPO)):
                imported = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported |= {a.name.split(".")[0] for a in node.names}
                    elif isinstance(node, ast.ImportFrom) and not node.level:
                        imported.add((node.module or "").split(".")[0])
                    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                            and isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
                        self.assertNotRegex("os." + node.func.attr, PROCESS_LAUNCH)
                self.assertFalse(imported & {"subprocess", "pty", "multiprocessing", "socket"})
