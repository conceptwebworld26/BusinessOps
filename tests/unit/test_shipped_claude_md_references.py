"""BOPS-R14 (BusinessOps M4A.1): nothing in the installable package needs `CLAUDE.md`.

`CLAUDE.md` is development governance for this repository and is deliberately not shipped (ADR-0055).
Commands, skills and reference documents therefore cite the shipped reference documents for the rules
they used to cite it for: the approval matrix (`reference/analysis-framework.md`), the disclosure tiers
(`reference/research-policy.md`) and data privacy in output (`reference/output-standards.md`).

Builds the package into a temporary directory with `scripts/build_distribution.py`. Offline, stdlib only.
"""

import ast
import importlib.util
import os
import re
import shutil
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEVELOPMENT_REPOSITORY = "https://github.com/conceptwebworld26/BusinessOps/blob/main/CLAUDE.md"
#: Everything Claude reads as an instruction or policy at runtime, and every user-facing document.
INSTRUCTION_AREAS = ("commands", "skills", "agents", "reference", "hooks", "config", ".claude-plugin")
USER_DOCUMENTS = ("LICENSE", "EULA.md", "PRIVACY.md", "CONNECTORS.md", ".mcp.json")
READ_INSTRUCTION = re.compile(r"(read|consult|follow|see|per|under|according to)[^.\n]{0,60}CLAUDE\.md", re.I)


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_distribution", os.path.join(REPO, "scripts", "build_distribution.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class TheShippedPackage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="bops-r14-")
        cls.out = os.path.join(cls.tmp, "businessops")
        summary = _builder().build(cls.out)
        assert summary["problems"] == [], summary["problems"]
        cls.files = {}
        for directory, _dirs, names in os.walk(cls.out):
            for name in names:
                path = os.path.join(directory, name)
                cls.files[os.path.relpath(path, cls.out).replace(os.sep, "/")] = path

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_claude_md_is_not_shipped(self):
        self.assertNotIn("CLAUDE.md", self.files)

    def test_no_instruction_or_policy_file_names_claude_md(self):
        for rel, path in sorted(self.files.items()):
            if rel.split("/")[0] in INSTRUCTION_AREAS or rel in USER_DOCUMENTS:
                with self.subTest(path=rel):
                    # Bytes, not text: `.claude-plugin/` also holds the listing icon, a PNG.
                    with open(path, "rb") as handle:
                        self.assertNotIn(b"CLAUDE.md", handle.read())

    def test_no_command_or_skill_tells_claude_to_read_claude_md(self):
        for rel, path in sorted(self.files.items()):
            if rel.startswith(("commands/", "skills/", "agents/")):
                with self.subTest(path=rel):
                    self.assertIsNone(READ_INSTRUCTION.search(_read(path)))

    def test_the_policies_they_cite_ship_in_the_reference_documents(self):
        for rel, heading in (("reference/analysis-framework.md", "## Approval follows consequence"),
                             ("reference/research-policy.md", "## The disclosure tiers"),
                             ("reference/output-standards.md", "## Data privacy in output")):
            with self.subTest(document=rel):
                self.assertIn(heading, _read(self.files[rel]))

    def test_the_readme_mentions_claude_md_only_as_a_link_into_the_development_repository(self):
        """A development-only pointer for contributors is allowed; it is not a runtime dependency."""
        for line in _read(self.files["README.md"]).splitlines():
            if "CLAUDE.md" in line:
                with self.subTest(line=line[:80]):
                    self.assertIn(DEVELOPMENT_REPOSITORY, line)
                    self.assertNotIn("](CLAUDE.md)", line)

    def test_the_engine_mentions_claude_md_only_in_developer_comments_and_docstrings(self):
        """No string the engine can emit names it; comments and docstrings are developer text."""
        for rel, path in sorted(self.files.items()):
            if not (rel.startswith("lib/") and rel.endswith(".py")):
                continue
            tree = ast.parse(_read(path))
            docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                          if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                                               ast.ClassDef))
                          and node.body and isinstance(node.body[0], ast.Expr)
                          and isinstance(node.body[0].value, ast.Constant)}
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                        and id(node) not in docstrings:
                    with self.subTest(path=rel, text=node.value[:60]):
                        self.assertNotIn("CLAUDE.md", node.value)


class TheDevelopmentRepository(unittest.TestCase):
    """Development and historical references stay where they belong."""

    def test_claude_md_remains_the_development_governance_document(self):
        text = _read(os.path.join(REPO, "CLAUDE.md"))
        self.assertIn("## 8. Data privacy requirements", text)
        self.assertIn("## 9. Permission model", text)

    def test_historical_records_keep_their_original_references(self):
        """Records are append-only; M4A.1 changes no historical CLAUDE.md citation."""
        for rel in ("docs/decisions/ADR-0010-consequence-based-approval-model.md",
                    "docs/development/2026-09-08-foundation.md"):
            with self.subTest(record=rel):
                self.assertIn("CLAUDE.md", _read(os.path.join(REPO, *rel.split("/"))))


if __name__ == "__main__":
    unittest.main()
