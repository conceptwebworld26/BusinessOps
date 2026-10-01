"""Manifest structure and repository layout (ADR-0001)."""

import json
import os
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load(*parts):
    with open(os.path.join(REPO, *parts), "r", encoding="utf-8") as fh:
        return json.load(fh)


class TestPluginManifest(unittest.TestCase):
    def setUp(self):
        self.manifest = load(".claude-plugin", "plugin.json")

    def test_required_fields_present(self):
        for field in ("name", "version", "description", "author"):
            self.assertIn(field, self.manifest)

    def test_name_matches_plugin_identity(self):
        self.assertEqual(self.manifest["name"], "businessops")

    def test_version_is_semver(self):
        parts = self.manifest["version"].split(".")
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(p.isdigit() for p in parts))

    def test_declares_eval_directory(self):
        self.assertEqual(self.manifest.get("experimental", {}).get("evals"), "evals")

    def test_no_unsupported_component_fields(self):
        # Every component type is auto-discovered; listing one is unnecessary.
        for field in ("commands", "skills", "hooks", "mcpServers"):
            self.assertNotIn(field, self.manifest,
                             "%s should rely on auto-discovery" % field)

    def test_agents_are_not_declared_explicitly(self):
        """Declaring `agents` suppresses discovery, and the agent then does not ship.

        Measured against `claude plugin details businessops` on 2026-09-10: with
        `"agents": ["./agents/bops-research-scout.md"]` the installed inventory reported
        **Agents (0)**; with the key removed it reported **Agents (1) bops-research-scout**.
        The manifest validated either way, so nothing else in the suite would notice - and
        an agent that does not ship cannot be dispatched, which is precisely the M9-B
        failure this assertion exists to prevent recurring.
        """
        self.assertNotIn("agents", self.manifest,
                         "declaring `agents` stops the agent shipping; rely on "
                         "auto-discovery from agents/ (ADR-0015)")

    def test_no_secrets_in_manifest(self):
        blob = json.dumps(self.manifest).lower()
        for token in ("api_key", "apikey", "secret", "password", "token"):
            self.assertNotIn(token, blob)


class TestMarketplaceManifest(unittest.TestCase):
    def setUp(self):
        self.marketplace = load(".claude-plugin", "marketplace.json")

    def test_has_owner_and_plugins(self):
        self.assertIn("owner", self.marketplace)
        self.assertTrue(self.marketplace["plugins"])

    def test_plugin_entry_agrees_with_plugin_manifest(self):
        plugin = load(".claude-plugin", "plugin.json")
        entry = self.marketplace["plugins"][0]
        self.assertEqual(entry["name"], plugin["name"])
        self.assertEqual(entry["version"], plugin["version"])

    def test_source_points_at_the_committed_package(self):
        """BOPS-R18: adding this repository as a marketplace installs `dist/businessops/`, not the
        development tree. The package's own marketplace entry points at its root (the builder sets it)."""
        self.assertEqual(self.marketplace["plugins"][0]["source"], "./dist/businessops")
        # `claude plugin validate` does not check that a relative source exists; this does.
        self.assertTrue(os.path.isfile(os.path.join(REPO, "dist", "businessops", ".claude-plugin", "plugin.json")))


class TestRepositoryLayout(unittest.TestCase):
    def test_governance_documents_exist(self):
        for name in ("CLAUDE.md", "architecture.md", "project_plan.md",
                     "README.md", "CONNECTORS.md", "LICENSE"):
            self.assertTrue(os.path.exists(os.path.join(REPO, name)), name)

    def test_six_reference_documents_exist(self):
        expected = {
            "analysis-framework.md", "evidence-ledger.md", "materiality-policy.md",
            "output-standards.md", "ambiguity-protocol.md", "research-policy.md",
        }
        present = set(os.listdir(os.path.join(REPO, "reference")))
        self.assertEqual(expected - present, set(), "missing reference documents")

    def test_gitignore_protects_confidential_paths(self):
        with open(os.path.join(REPO, ".gitignore"), "r", encoding="utf-8") as fh:
            lines = {ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")}
        for pattern in (".businessops/", "businessops-output/", ".env"):
            self.assertIn(pattern, lines)

    def test_gitignore_has_no_trailing_comments(self):
        # git treats a trailing "# comment" as part of the pattern, silently breaking it.
        with open(os.path.join(REPO, ".gitignore"), "r", encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    self.assertNotIn(" #", stripped,
                                     "line %d has a trailing comment" % number)

    def test_managed_runtime_is_outside_the_repository(self):
        from bops import runtime
        self.assertFalse(
            os.path.abspath(runtime.RUNTIME_DIR).startswith(REPO + os.sep),
            "the managed runtime must never live inside the repository")


if __name__ == "__main__":
    unittest.main()
