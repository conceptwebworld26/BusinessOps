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
                self.assertNotIn(rel, ("CLAUDE.md", "architecture.md", "project_plan.md",
                                       "assets/demo-data/generate_demo_data.py",
                                       "assets/demo-data/northwind_sales.xlsx"))
                self.assertNotIn("__pycache__", rel)
                self.assertFalse(rel.endswith(".pyc"))

    def test_the_package_gitignore_is_the_generated_hygiene_file_not_the_repository_one(self):
        """BOPS-R16: the distribution repository ignores Python bytecode, and nothing else."""
        with open(os.path.join(self.out, ".gitignore"), encoding="utf-8") as handle:
            shipped = handle.read()
        self.assertEqual(shipped, self.builder.DISTRIBUTION_GITIGNORE)
        rules = [line for line in shipped.splitlines() if line and not line.startswith("#")]
        self.assertEqual(rules, ["__pycache__/", "*.py[cod]"])
        with open(os.path.join(REPO, ".gitignore"), encoding="utf-8") as handle:
            self.assertNotEqual(shipped, handle.read())

    def test_no_plugin_component_depends_on_the_gitignore(self):
        for rel in self.files:
            if rel == ".gitignore":
                continue
            with self.subTest(path=rel):
                with open(os.path.join(self.out, rel), encoding="utf-8") as handle:
                    self.assertNotIn(".gitignore", handle.read())

    def test_the_build_check_rejects_python_bytecode_and_a_foreign_gitignore(self):
        copy = os.path.join(self.tmp, "bytecode-check")
        shutil.copytree(self.out, copy)
        os.makedirs(os.path.join(copy, "lib", "python", "bops", "__pycache__"))
        with open(os.path.join(copy, "lib", "python", "bops", "__pycache__", "x.cpython-313.pyc"), "w") as handle:
            handle.write("x")
        with open(os.path.join(copy, ".gitignore"), "w") as handle:
            handle.write("*\n")
        problems, _files = self.builder.check(copy)
        self.assertTrue(any(p.startswith("python bytecode:") for p in problems), problems)
        self.assertIn("not the generated file: .gitignore", problems)

    def test_the_packaged_manifests_name_the_one_businessops_repository(self):
        """Single-repository architecture: the package's manifests are the source's, URLs included."""
        import json
        url = "https://github.com/conceptwebworld26/BusinessOps"
        with open(os.path.join(self.out, ".claude-plugin", "plugin.json"), encoding="utf-8") as handle:
            packaged = json.load(handle)
        with open(os.path.join(REPO, ".claude-plugin", "plugin.json"), encoding="utf-8") as handle:
            source = json.load(handle)
        self.assertEqual((packaged["homepage"], packaged["repository"]), (url, url))
        source.get("experimental", {}).pop("evals", None)
        if not source.get("experimental", True):
            del source["experimental"]
        self.assertEqual(packaged, source)
        with open(os.path.join(self.out, ".claude-plugin", "marketplace.json"), encoding="utf-8") as handle:
            marketplace = json.load(handle)
        with open(os.path.join(REPO, ".claude-plugin", "marketplace.json"), encoding="utf-8") as handle:
            self.assertEqual(marketplace, json.load(handle))
        self.assertEqual([entry["homepage"] for entry in marketplace["plugins"]], [url])

    def test_the_committed_package_is_exactly_a_fresh_build(self):
        """`dist/businessops/` is committed for review; it must never drift from its source.

        Line endings are normalised: a Windows checkout with core.autocrlf converts them, and git
        stores the files with LF either way.
        """
        committed = os.path.join(REPO, "dist", "businessops")
        if not os.path.isdir(committed):
            self.skipTest("dist/businessops/ is not present in this checkout")
        found = set()
        for directory, dirs, names in os.walk(committed):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in names:
                if not name.endswith((".pyc", ".pyo", ".pyd")):
                    found.add(os.path.relpath(os.path.join(directory, name), committed).replace(os.sep, "/"))
        self.assertEqual(found, self.files)
        for rel in sorted(self.files):
            with self.subTest(path=rel):
                with open(os.path.join(committed, rel), "rb") as left, \
                        open(os.path.join(self.out, rel), "rb") as right:
                    self.assertEqual(left.read().replace(b"\r\n", b"\n"), right.read().replace(b"\r\n", b"\n"))

    def test_the_readme_presents_businessops_alone(self):
        """No predecessor product is presented in the public README (the listing description)."""
        with open(os.path.join(self.out, "README.md"), encoding="utf-8") as handle:
            readme = handle.read()
        for name in ("BusinessIQ", "businessiq", "Project lineage"):
            self.assertNotIn(name, readme)

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
