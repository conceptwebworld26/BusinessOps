"""The M13.2 eval scaffold actually stages its input (ADR-0039 F.6; M13-DEF-07).

`tests/unit/test_m13_eval_cases.Scaffold` reads the script and asserts it does nothing but copy
repository synthetic inputs. That is the static half. This module runs it, because the property
that matters cannot be read off the text: after the scaffold, the path the case prompt names
must resolve relative to the run's working directory.

It reproduces the invocation Claude Code 2.1.278 performs -- `bash <script>`, working directory
set to the run's own directory, and an environment of PATH, HOME, USERPROFILE, TMPDIR, TMP,
TEMP, TERM, GIT_CONFIG_NOSYSTEM, USER_TYPE and NODE_ENV only. It starts one `bash`, reads only
the repository and one temporary directory, and runs no evaluation: no model is invoked, no
network is touched and nothing is published.
"""

import filecmp
import os
import shutil
import importlib.util
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CASE_DIR = os.path.join(REPO, "evals", "approval", "a01-read-only-anomaly-detection")
SCAFFOLD = os.path.join(CASE_DIR, "scaffold.sh")
#: The input the case declares, and the path its prompt names.
STAGED = "assets/demo-data/northwind_sales.csv"

#: Exactly the variables the harness passes a scaffold. Anything the script needs beyond these
#: would work here and fail in a real run, so the test withholds everything else.
HARNESS_ENV = ("PATH", "HOME", "USERPROFILE", "TMPDIR", "TMP", "TEMP", "TERM",
               "GIT_CONFIG_NOSYSTEM", "USER_TYPE", "NODE_ENV")


@unittest.skipUnless(shutil.which("bash"), "the scaffold runs under bash, as the harness runs it")
class TheScaffoldStagesTheDeclaredInput(unittest.TestCase):

    def setUp(self):
        self.workspace = tempfile.mkdtemp(prefix="bops-eval-scaffold-")
        self.addCleanup(shutil.rmtree, self.workspace, True)

    def run_scaffold(self, cwd=None):
        """Run it the way the harness does, and return the completed process."""
        home = os.path.join(self.workspace, "home")
        temp = os.path.join(self.workspace, "tmp")
        for path in (home, temp):
            os.makedirs(path, exist_ok=True)
        values = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": home,
                  "USERPROFILE": home, "TMPDIR": temp, "TMP": temp, "TEMP": temp,
                  "TERM": "dumb", "GIT_CONFIG_NOSYSTEM": "1", "USER_TYPE": "external",
                  "NODE_ENV": "production"}
        self.assertEqual(sorted(values), sorted(HARNESS_ENV))
        return subprocess.run(["bash", SCAFFOLD], cwd=cwd or self.run_dir(),
                              env=values, capture_output=True, text=True, timeout=120)

    def run_dir(self):
        path = os.path.join(self.workspace, "run")
        os.makedirs(path, exist_ok=True)
        return path

    def test_it_succeeds_and_the_declared_path_resolves_in_the_run_directory(self):
        result = self.run_scaffold()
        self.assertEqual(result.returncode, 0, result.stderr)
        staged = os.path.join(self.run_dir(), STAGED)
        self.assertTrue(os.path.isfile(staged),
                        "the path the prompt names does not resolve: %s" % STAGED)

    def test_the_staged_file_is_byte_identical_to_the_repository_input(self):
        self.assertEqual(self.run_scaffold().returncode, 0)
        self.assertTrue(filecmp.cmp(os.path.join(self.run_dir(), STAGED),
                                    os.path.join(REPO, STAGED), shallow=False))

    def test_it_stages_that_file_and_nothing_else(self):
        self.assertEqual(self.run_scaffold().returncode, 0)
        run = self.run_dir()
        found = sorted(os.path.relpath(os.path.join(root, name), run).replace(os.sep, "/")
                       for root, _dirs, files in os.walk(run) for name in files)
        self.assertEqual(found, [STAGED])

    def test_it_carries_no_shebang_because_the_harness_chooses_the_shell(self):
        """The harness runs `bash <script>`, so the mode bits and any shebang are irrelevant.

        Every other test here invokes it that way, which is the proof it needs no executable
        bit. Asserting the absence of a shebang keeps the file honest about that: a `#!` line
        would suggest an interpreter the harness never consults.
        """
        with open(SCAFFOLD, "rb") as handle:
            self.assertFalse(handle.read(2) == b"#!")

    def test_running_it_twice_leaves_the_same_result(self):
        """A rerun of a case must not fail on a directory or file that already exists."""
        self.assertEqual(self.run_scaffold().returncode, 0)
        second = self.run_scaffold()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertTrue(filecmp.cmp(os.path.join(self.run_dir(), STAGED),
                                    os.path.join(REPO, STAGED), shallow=False))

    def test_it_writes_nothing_into_the_repository(self):
        before = os.stat(os.path.join(REPO, STAGED))
        self.assertEqual(self.run_scaffold().returncode, 0)
        after = os.stat(os.path.join(REPO, STAGED))
        self.assertEqual((before.st_size, before.st_mtime), (after.st_size, after.st_mtime))

    def test_it_does_not_depend_on_the_working_directory_being_named(self):
        """The harness chooses the run directory; the script may not assume anything about it."""
        odd = os.path.join(self.workspace, "a dir with spaces")
        os.makedirs(odd, exist_ok=True)
        result = self.run_scaffold(cwd=odd)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.isfile(os.path.join(odd, STAGED)))

    def test_it_runs_no_interpreter_and_reaches_no_network(self):
        """The static guard owns this; asserted here too, against the file the run executes."""
        with open(SCAFFOLD, encoding="ascii") as handle:
            text = handle.read()
        for forbidden in ("python", "curl", "wget", "http", "pip", "nc ", "ssh"):
            self.assertNotIn(forbidden, text)


@unittest.skipUnless(shutil.which("bash"), "the scaffold runs under bash, as the harness runs it")
class EveryBusinessFileCaseStagesItsOwnFixture(unittest.TestCase):
    """The same proof, across all 38 `requires_business_file` cases (2026-09-23).

    The fine-grained properties -- rerun safety, an odd working-directory name, no write into the
    repository, no shebang, no interpreter -- are asserted once above against the pilot case, which
    is byte-for-byte the same generated script as the other 37 apart from its fixture path. What
    this class adds is breadth: every case's own scaffold is executed, and its own declared input
    must arrive byte-identical with nothing else alongside it.
    """

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "m13_eval_cases_for_scaffold",
            os.path.join(REPO, "tests", "unit", "test_m13_eval_cases.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.cases = module.load_cases()
        cls.module = module
        cls.staged = sorted(module.staged_cases(cls.cases))
        cls.expected_count = module.BUSINESS_FILE_COUNT

    def run_scaffold(self, case_dir, run_dir):
        """Run one case's scaffold exactly as the harness does."""
        home = os.path.join(run_dir, "..", "home")
        os.makedirs(home, exist_ok=True)
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": home,
               "USERPROFILE": home, "TMPDIR": run_dir, "TMP": run_dir, "TEMP": run_dir,
               "TERM": "dumb", "GIT_CONFIG_NOSYSTEM": "1", "USER_TYPE": "external",
               "NODE_ENV": "production"}
        self.assertEqual(sorted(env), sorted(HARNESS_ENV))
        return subprocess.run(["bash", os.path.join(REPO, case_dir, "scaffold.sh")],
                              cwd=run_dir, env=env, capture_output=True, text=True, timeout=120)

    def test_the_set_is_the_whole_business_file_set(self):
        self.assertEqual(len(self.staged), self.expected_count)

    def test_every_scaffold_stages_its_declared_input_byte_identically_and_nothing_else(self):
        for case_dir in self.staged:
            declared = self.cases[case_dir]["inputs"]
            self.assertEqual(len(declared), 1, case_dir)
            wanted = declared[0]
            with self.subTest(case=case_dir):
                workspace = tempfile.mkdtemp(prefix="bops-scaffold-all-")
                self.addCleanup(shutil.rmtree, workspace, True)
                run_dir = os.path.join(workspace, "cwd")
                os.makedirs(run_dir)
                result = self.run_scaffold(case_dir, run_dir)
                self.assertEqual(result.returncode, 0, result.stderr)
                landed = os.path.join(run_dir, wanted)
                self.assertTrue(os.path.isfile(landed), "%s did not resolve" % wanted)
                self.assertTrue(filecmp.cmp(landed, os.path.join(REPO, wanted), shallow=False),
                                "staged bytes differ from the repository fixture")
                found = sorted(
                    os.path.relpath(os.path.join(root, name), run_dir).replace(os.sep, "/")
                    for root, _dirs, files in os.walk(run_dir) for name in files)
                # ADR-0048: a declared precondition fixture is staged at its declared path, and
                # nothing else joins the input.
                copies = self.module.staged_copies(self.cases[case_dir])
                for source, destination in copies[1:]:
                    self.assertTrue(filecmp.cmp(os.path.join(run_dir, destination),
                                                os.path.join(REPO, source), shallow=False))
                self.assertEqual(found, sorted(d for _s, d in copies), "extra files were staged")

    def test_no_scaffold_writes_into_the_repository(self):
        """The fixtures are the user's source data; staging must be one-directional."""
        before = {p: os.stat(os.path.join(REPO, p))
                  for p in {self.cases[d]["inputs"][0] for d in self.staged}}
        for case_dir in self.staged:
            workspace = tempfile.mkdtemp(prefix="bops-scaffold-ro-")
            self.addCleanup(shutil.rmtree, workspace, True)
            run_dir = os.path.join(workspace, "cwd")
            os.makedirs(run_dir)
            self.assertEqual(self.run_scaffold(case_dir, run_dir).returncode, 0)
        for path, stat_before in before.items():
            after = os.stat(os.path.join(REPO, path))
            with self.subTest(fixture=path):
                self.assertEqual((stat_before.st_size, stat_before.st_mtime),
                                 (after.st_size, after.st_mtime))


if __name__ == "__main__":
    unittest.main()
