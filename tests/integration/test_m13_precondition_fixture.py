"""M13-DEF-19 (ADR-0048): the `a20` scaffold stages the declared precondition fixture as README.md.

Runs the case's real scaffold under bash exactly as the harness does (the working directory set
to a fresh run directory, only the harness's environment variables), and reads the scaffold and
fixture statically for what they must never do. No evaluation, model or network is involved.
"""

import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CASE = "evals/approval/a20-overwrite-names-file"
SCAFFOLD = os.path.join(REPO, CASE, "scaffold.sh")


def _module(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = _module("tests/unit/test_m13_eval_cases.py", "m13_cases_for_precondition")
BUILDER = _module("tests/fixtures/build_eval_inputs.py", "m13_builder_for_precondition")
CONTRACT = _module("tests/unit/test_m13_grader_contract.py", "m13_contract_for_precondition")
CASES = VALIDATOR.load_cases()
ENTRY = {e["id"]: e for e in VALIDATOR.load_manifest()["fixtures"]}["EVI-04"]


def _read(path):
    with open(os.path.join(REPO, path), "rb") as handle:
        return handle.read()


def _effective(text):
    return [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


@unittest.skipUnless(shutil.which("bash"), "the scaffold runs under bash, as the harness runs it")
class TheScaffoldStagesTheDeclaredPrecondition(unittest.TestCase):

    def run_scaffold(self):
        workspace = tempfile.mkdtemp(prefix="bops-precondition-")
        self.addCleanup(shutil.rmtree, workspace, True)
        run_dir, home = os.path.join(workspace, "cwd"), os.path.join(workspace, "home")
        os.makedirs(run_dir)
        os.makedirs(home)
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": home, "USERPROFILE": home,
               "TMPDIR": run_dir, "TMP": run_dir, "TEMP": run_dir, "TERM": "dumb",
               "GIT_CONFIG_NOSYSTEM": "1", "USER_TYPE": "external", "NODE_ENV": "production"}
        result = subprocess.run(["bash", SCAFFOLD], cwd=run_dir, env=env,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        return run_dir

    @staticmethod
    def tree(run_dir):
        return sorted(os.path.relpath(os.path.join(root, name), run_dir).replace(os.sep, "/")
                      for root, _dirs, files in os.walk(run_dir) for name in files)

    def test_a_the_file_exists_before_the_agent_starts(self):
        self.assertTrue(os.path.isfile(os.path.join(self.run_scaffold(), "README.md")))

    def test_b_it_holds_exactly_the_synthetic_baseline(self):
        with open(os.path.join(self.run_scaffold(), "README.md"), "rb") as handle:
            staged = handle.read()
        self.assertEqual(hashlib.sha256(staged).hexdigest(), ENTRY["sha256"])
        self.assertEqual(len(staged), ENTRY["bytes"])
        directory = tempfile.mkdtemp(prefix="bops-precondition-build-")
        self.addCleanup(shutil.rmtree, directory, True)
        with open(BUILDER.s5_05_existing_readme(directory), "rb") as handle:
            self.assertEqual(staged, handle.read())
        self.assertNotEqual(staged, _read("README.md"), "the repository README must never be staged")

    def test_c_nothing_undeclared_is_staged(self):
        self.assertEqual(self.tree(self.run_scaffold()),
                         ["README.md", "assets/demo-data/northwind_sales.csv"])

    def test_d_it_is_deterministic(self):
        first, second = self.run_scaffold(), self.run_scaffold()
        self.assertEqual(self.tree(first), self.tree(second))
        for path in self.tree(first):
            with open(os.path.join(first, path), "rb") as a, open(os.path.join(second, path), "rb") as b:
                self.assertEqual(a.read(), b.read(), path)

    def test_j_an_overwrite_is_a_detectable_change_and_the_write_grader_sees_it(self):
        run_dir = self.run_scaffold()
        target = os.path.join(run_dir, "README.md")
        with open(target, "wb") as handle:
            handle.write(b"# Sales Analysis\n\nreplacement summary\n")
        with open(target, "rb") as handle:
            self.assertNotEqual(hashlib.sha256(handle.read()).hexdigest(), ENTRY["sha256"])
        names = ("g-not-overwritten-write", "g-not-overwritten-edit",
                 "g-not-overwritten-notebookedit", "g-not-overwritten-bash")
        self.assertFalse(CONTRACT.passes("a20-overwrite-names-file", names,
                                         CONTRACT.trace(CONTRACT.RESOLVER, CONTRACT.OVERWRITE)))
        self.assertTrue(CONTRACT.passes("a20-overwrite-names-file", names,
                                        CONTRACT.trace(CONTRACT.INSPECT, CONTRACT.RESOLVER)))


class TheScaffoldAndFixtureAreSafe(unittest.TestCase):

    def setUp(self):
        self.lines = _effective(_read(os.path.relpath(SCAFFOLD, REPO)).decode("utf-8"))
        self.fixture = _read(ENTRY["path"]).decode("ascii")

    def test_e_no_absolute_path(self):
        for line in self.lines:
            with self.subTest(line=line):
                self.assertIsNone(re.search(r"(^|\s)/[A-Za-z]|~/|\b[A-Za-z]:[\\\\/]", line))

    def test_f_no_network_operation(self):
        pattern = re.compile(r"(?i)\b(curl|wget|nc|ssh|scp|rsync|ftp)\b|https?://")
        for text in self.lines + [self.fixture]:
            self.assertIsNone(pattern.search(text), text)

    def test_g_no_package_installation(self):
        pattern = re.compile(r"(?i)\b(pip3?|apt(-get)?|npm|yarn|brew|conda|uv|gem|cargo|install)\b")
        for line in self.lines:
            self.assertIsNone(pattern.search(line), line)

    def test_h_no_authentication(self):
        pattern = re.compile(r"(?i)\b(login|auth\w*|token|password|credential\w*|gh|secret|key)\b")
        for text in self.lines + [self.fixture]:
            self.assertIsNone(pattern.search(text), text)

    def test_i_no_mcp_or_web_tool(self):
        pattern = re.compile(r"(?i)mcp|websearch|webfetch|claude\b")
        for text in self.lines + [self.fixture]:
            self.assertIsNone(pattern.search(text), text)

    def test_every_line_is_a_permitted_form_and_each_copy_is_declared(self):
        permitted = VALIDATOR.Scaffold.PERMITTED
        for line in self.lines:
            with self.subTest(line=line):
                self.assertTrue(any(form.match(line) for form in permitted))
        copies = [(m.group("src"), m.group("dst")) for m in
                  (permitted[3].match(line) for line in self.lines) if m]
        self.assertEqual(copies, VALIDATOR.staged_copies(CASES[CASE]))

    def test_the_declaration_is_narrow(self):
        """ADR-0048: one case, one bare file name in the run directory, named by the prompt."""
        declaring = sorted(d for d, c in CASES.items() if "precondition_fixture" in c)
        self.assertEqual(declaring, list(VALIDATOR.PRECONDITION_CASES))
        case = CASES[CASE]
        self.assertEqual((case["precondition_fixture"], case["precondition_path"]),
                         ("EVI-04", ENTRY["stage_as"]))
        self.assertRegex(case["precondition_path"], r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
        self.assertNotIn(case["precondition_path"], case["inputs"])
        self.assertIn(case["precondition_path"], case["prompt"])
        self.assertEqual(ENTRY["cases"], [CASE])
        self.assertEqual(ENTRY["format"], "markdown")


if __name__ == "__main__":
    unittest.main()
