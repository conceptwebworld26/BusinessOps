"""BusinessOps M3 (ADR-0055): the installable package is built from an allowlist and holds only the plugin.

Builds the package into a temporary directory with `scripts/build_distribution.py` and checks the
boundary: the plugin root is the package root, every runtime file a shipped component names is present,
and nothing developer-only, historical or oversized is included. Offline, deterministic, stdlib only.
"""

import importlib.util
import json
import os
import shutil
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_distribution", os.path.join(REPO, "scripts", "build_distribution.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TheDistributionPackage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.builder = _builder()
        cls.tmp = tempfile.mkdtemp(prefix="bops-dist-")
        cls.out = os.path.join(cls.tmp, "businessops")
        cls.summary = cls.builder.build(cls.out)
        cls.files = set()
        for directory, _dirs, names in os.walk(cls.out):
            for name in names:
                cls.files.add(os.path.relpath(os.path.join(directory, name), cls.out).replace(os.sep, "/"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_package_passes_its_own_checks(self):
        self.assertEqual(self.summary["problems"], [])

    def test_the_plugin_root_is_the_package_root(self):
        self.assertIn(".claude-plugin/plugin.json", self.files)
        with open(os.path.join(self.out, ".claude-plugin", "plugin.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["name"], "businessops")
        self.assertEqual(manifest["displayName"], "BusinessOps")

    def test_the_packaged_manifest_names_no_path_that_is_not_shipped(self):
        """`evals/` is not shipped, so `experimental.evals` must not be either."""
        with open(os.path.join(self.out, ".claude-plugin", "plugin.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertNotIn("evals", manifest.get("experimental", {}))
        with open(os.path.join(REPO, ".claude-plugin", "plugin.json"), encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["experimental"]["evals"], "evals")

    def test_every_runtime_component_is_shipped(self):
        for rel in (".mcp.json", "hooks/hooks.json", "hooks/bops_guard.sh", "lib/bops_run.sh",
                    "lib/python/bops_run.py", "lib/python/bops/__init__.py",
                    "config/businessops.defaults.json", "config/vocabulary.json",
                    "agents/bops-analysis-verifier.md", "agents/bops-research-scout.md",
                    "README.md", "LICENSE", "EULA.md", "PRIVACY.md"):
            self.assertIn(rel, self.files)
        for name in os.listdir(os.path.join(REPO, "commands")):
            self.assertIn("commands/" + name, self.files)
        for name in os.listdir(os.path.join(REPO, "skills")):
            self.assertIn("skills/%s/SKILL.md" % name, self.files)
        for name in os.listdir(os.path.join(REPO, "reference")):
            self.assertIn("reference/" + name, self.files)
        for name in os.listdir(os.path.join(REPO, "lib", "schemas")):
            self.assertIn("lib/schemas/" + name, self.files)

    def test_nothing_developer_only_or_historical_is_shipped(self):
        for rel in self.files:
            with self.subTest(path=rel):
                self.assertFalse(rel.startswith(("tests/", "evals/", "docs/", "dev/", "scripts/", ".claude/")))
                self.assertNotIn(rel, ("CLAUDE.md", "architecture.md", "project_plan.md", ".gitignore",
                                       "assets/demo-data/generate_demo_data.py",
                                       "assets/demo-data/northwind_sales.xlsx"))
                self.assertNotIn("__pycache__", rel)
                self.assertFalse(rel.endswith(".pyc"))

    def test_the_internal_harness_is_not_shipped(self):
        self.assertFalse(any("retrieval-slice" in rel for rel in self.files))

    def test_the_package_is_within_the_directory_file_limits(self):
        self.assertLessEqual(len(self.files), 512)
        for rel in self.files:
            with self.subTest(path=rel):
                self.assertLessEqual(os.path.getsize(os.path.join(self.out, rel)), 256 * 1024)

    def test_a_link_to_an_unshipped_document_points_at_the_repository(self):
        with open(os.path.join(self.out, "README.md"), encoding="utf-8") as handle:
            readme = handle.read()
        self.assertNotIn("](docs/", readme)
        self.assertIn("](https://github.com/conceptwebworld26/BusinessOps/", readme)
        self.assertIn("](PRIVACY.md)", readme)
        self.assertIn("](EULA.md)", readme)

    def test_a_directory_that_is_not_a_previous_build_is_never_replaced(self):
        target = os.path.join(self.tmp, "not-a-build")
        os.makedirs(target)
        with open(os.path.join(target, "keep.txt"), "w") as handle:
            handle.write("keep")
        with self.assertRaises(SystemExit):
            self.builder.build(target)
        self.assertTrue(os.path.exists(os.path.join(target, "keep.txt")))


if __name__ == "__main__":
    unittest.main()
