"""M13-DEF-04 remediation: the plugin-root-anchored, isolated engine entry (ADR-0042).

Every command and skill enters the engine as

    python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/bops_run.py" -c "<code>"

These tests run that entry from **real command and skill text**. They reproduce two things:

- the platform's body substitution: `${CLAUDE_PLUGIN_ROOT}` is replaced by the plugin path, with
  `/` separators, as verified at runtime on 2026-09-19;
- the argument bash would pass: the text between the opening `"` and the closing `"`, or the
  quoted heredoc body.

They then run it as a subprocess, with no shell, from temporary working directories outside the
repository. No Claude session, eval, web or MCP is involved.

| ADR-0042 id | Class |
|---|---|
| T-A external working directory | `ExternalWorkingDirectory` |
| T-B repository root | `RepositoryRoot` |
| T-C cache-like copy | `CacheLikeCopy` (a local packaging test, **not** marketplace equivalence) |
| T-D five bare-import skills | `BareImportSkills` |
| T-E representative commands | `RepresentativeCommands` |
| T-F working-directory shadowing | `WorkingDirectoryShadowing` |
| T-G hostile `PYTHONPATH` / non-isolated | `EnvironmentAndIsolation` |
| T-H working-directory independence | `WorkingDirectoryIndependence` |
| T-J M13.2 prerequisite | `M132ExternalWorkingDirectoryPrerequisite` |

T-K, the static guard, is `tests/unit/test_m13_def04_static_guard.py`. T-I is the full suite.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from fixtures import build_m13_large_fixtures as large

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
#: The boundary a shipped block now names (ADR-0045): the shell resolver, not an interpreter.
LAUNCHER_LINE = 'sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "'
HEREDOC_OPEN = LAUNCHER_LINE + "$(cat <<'PY'"
OPENER = re.compile(r'^sh "([^"]+)" -c "')
BARE_IMPORT_SKILLS = ("bops-benchmark-comparison", "bops-decision-support", "bops-executive-report",
                      "bops-strategy-recommendations", "bops-swot")
REPRESENTATIVE = ("sales-analysis", "revenue-forecast", "anomaly-detection", "business-health")
#: The shipped layout a cache-like copy carries (no tests, docs, evals, assets or .git).
SHIPPED = (".claude-plugin", ".mcp.json", "agents", "commands", "config", "lib", "reference", "skills")
TIMEOUT = 300


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def launcher_blocks(relative):
    """[(opener, code)] for every launcher block in one command or skill file."""
    blocks = []
    for match in re.finditer(r"^```bash\n(.*?)^```", _read(os.path.join(REPO, relative)),
                             re.M | re.S):
        lines = match.group(1).split("\n")
        if lines[0] == LAUNCHER_LINE:
            blocks.append((lines[0], "\n".join(lines[1:lines.index('"')])))
        elif lines[0] == HEREDOC_OPEN:
            blocks.append((lines[0], "\n".join(lines[1:lines.index("PY")]) + "\n"))
    return blocks


def substitute(opener, plugin_root):
    """The platform's body substitution, then the ADR-0042 launcher the resolver hands off to.

    This module's subject is the launcher's import boundary, so it keeps invoking that launcher
    directly with `sys.executable`: the interpreter must be a known, present one for these tests
    to say anything about imports. The resolver that chooses the interpreter in a real run is the
    subject of `integration.test_m13_def08_runtime_resolution`, which drives this same block
    through `lib/bops_run.sh` end to end. The mapping here is the one the resolver performs.
    """
    text = opener.replace("${CLAUDE_PLUGIN_ROOT}", plugin_root.replace("\\", "/"))
    resolver = OPENER.match(text).group(1)
    assert resolver.endswith("/lib/bops_run.sh"), resolver
    return resolver[: -len("/bops_run.sh")] + "/python/bops_run.py"


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env.update(extra)
    return env


def run_entry(opener, code, plugin_root, cwd, isolated=True, env=None):
    argv = [sys.executable] + (["-I"] if isolated else []) + \
        [substitute(opener, plugin_root), "-c", code]
    # The child writes in the platform's default stdout encoding (under -I no PYTHON* variable
    # can change it), which text mode also uses; `replace` keeps a stray byte from masking a result.
    return subprocess.run(argv, cwd=cwd, env=env or clean_env(), capture_output=True,
                          text=True, errors="replace", timeout=TIMEOUT)


def where(plugin_root, cwd, env=None):
    argv = [sys.executable, "-I", os.path.join(plugin_root, "lib", "python", "bops_run.py"),
            "--where"]
    result = subprocess.run(argv, cwd=cwd, env=env or clean_env(), capture_output=True,
                            text=True, timeout=TIMEOUT)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def same(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def outside_repo_tempdir(test, prefix):
    directory = os.path.realpath(tempfile.mkdtemp(prefix=prefix))
    test.addCleanup(shutil.rmtree, directory, True)
    if os.path.normcase(directory).startswith(os.path.normcase(REPO)):
        test.skipTest("the temporary directory is inside the repository")
    return directory


def write_input(directory, rows=1200, name="input.csv"):
    """A deterministic synthetic sales CSV of 24 monthly periods."""
    return large.large_csv(directory, rows, name=name)


def command_block(command):
    return launcher_blocks("commands/%s.md" % command)[0]


def copy_shipped(destination):
    for name in SHIPPED:
        source = os.path.join(REPO, name)
        target = os.path.join(destination, name)
        if os.path.isdir(source):
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, target)
    return destination


def plant_hostile(directory, sentinels):
    """Modules that would write a sentinel if imported, as a user's working directory might hold."""
    def module(name):
        return "open(%r, 'a').write('imported')\n" % os.path.join(sentinels, name)
    os.makedirs(os.path.join(directory, "bops"))
    os.makedirs(os.path.join(directory, "lib", "python", "bops"))
    files = {"bops.py": module("bops.py"), os.path.join("bops", "__init__.py"): module("bops-dir"),
             os.path.join("lib", "python", "bops", "__init__.py"): module("lib-python-bops"),
             "json.py": module("json.py"), "decimal.py": module("decimal.py")}
    for relative, text in files.items():
        with open(os.path.join(directory, relative), "w", encoding="utf-8") as handle:
            handle.write(text)


ORIGINS = ("import json, decimal, os, bops\n"
           "print('ORIGINS ' + json.dumps({'bops': bops.__file__, 'json': json.__file__, "
           "'decimal': decimal.__file__, 'cwd': os.getcwd()}))\n")


def origins(output):
    line = [l for l in output.splitlines() if l.startswith("ORIGINS ")][-1]
    return json.loads(line[len("ORIGINS "):])


class ExternalWorkingDirectory(unittest.TestCase):
    """T-A: the central defect. From outside the repository the engine loads and runs."""

    def test_a_command_runs_from_an_external_working_directory(self):
        cwd = outside_repo_tempdir(self, "bops-ta-")
        write_input(cwd)
        opener, code = command_block("sales-analysis")
        self.assertNotIn("sys.path", code, "the command still manipulates the import path")
        result = run_entry(opener, code.replace("<path>", "input.csv"), REPO, cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# Sales Analysis", result.stdout)
        self.assertIn("**Status:** ok", result.stdout)

    def test_the_engine_comes_from_the_plugin_and_relative_paths_from_the_user(self):
        cwd = outside_repo_tempdir(self, "bops-ta-")
        write_input(cwd)
        code = (ORIGINS + "import os\nprint('INPUT', os.path.abspath('input.csv'))\n")
        result = run_entry(LAUNCHER_LINE, code, REPO, cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        found = origins(result.stdout)
        self.assertTrue(same(found["bops"], os.path.join(REPO, "lib", "python", "bops", "__init__.py")))
        self.assertTrue(same(found["cwd"], cwd), "the launcher changed the working directory")
        self.assertIn(os.path.normcase(cwd), os.path.normcase(result.stdout.split("INPUT ")[1]))

    def test_the_old_entry_fails_there_so_the_test_is_live(self):
        cwd = outside_repo_tempdir(self, "bops-ta-")
        legacy = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'lib/python'); "
                                 "from bops import commands"], cwd=cwd, env=clean_env(),
                                capture_output=True, text=True, timeout=TIMEOUT)
        self.assertNotEqual(legacy.returncode, 0)
        self.assertIn("No module named 'bops'", legacy.stderr)


class RepositoryRoot(unittest.TestCase):
    """T-B: development-style execution from the repository root still works."""

    def test_a_command_runs_from_the_repository_root(self):
        data = outside_repo_tempdir(self, "bops-tb-")
        path = write_input(data)
        opener, code = command_block("sales-analysis")
        result = run_entry(opener, code.replace("<path>", path.replace("\\", "/")), REPO, REPO)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# Sales Analysis", result.stdout)

    def test_where_reports_the_repository_plugin(self):
        found = where(REPO, REPO)
        self.assertTrue(same(found["plugin_root"], REPO))
        self.assertEqual((found["plugin"], found["isolated"]), ("businessops", True))


class CacheLikeCopy(unittest.TestCase):
    """T-C: a copy laid out like an installed plugin, at a path containing a space.

    A local packaging test. It proves that the launcher derives its location and that no
    repository path is fixed. It does **not** claim marketplace-installation equivalence.
    """

    @classmethod
    def setUpClass(cls):
        cls.base = os.path.realpath(tempfile.mkdtemp(prefix="bops-tc-"))
        cls.root = copy_shipped(os.path.join(cls.base, "plugin cache", "businessops", "0.1.0"))
        os.makedirs(cls.root, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, True)

    def test_where_reports_the_copy_not_the_repository(self):
        cwd = outside_repo_tempdir(self, "bops-tc-cwd-")
        found = where(self.root, cwd)
        self.assertTrue(same(found["plugin_root"], self.root))
        self.assertTrue(same(found["bops_module"],
                             os.path.join(self.root, "lib", "python", "bops", "__init__.py")))
        self.assertFalse(same(found["plugin_root"], REPO))

    def test_a_command_from_the_copy_runs_from_an_external_working_directory(self):
        cwd = outside_repo_tempdir(self, "bops-tc-cwd-")
        write_input(cwd)
        opener, code = command_block("business-health")
        result = run_entry(opener, code.replace("<path>", "input.csv") + "\n" + ORIGINS,
                           self.root, cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# Business Health Snapshot", result.stdout)
        self.assertTrue(same(origins(result.stdout)["bops"],
                             os.path.join(self.root, "lib", "python", "bops", "__init__.py")))

    def test_a_copy_without_a_businessops_manifest_is_refused(self):
        other = copy_shipped(os.path.join(outside_repo_tempdir(self, "bops-tc-bad-"), "p"))
        with open(os.path.join(other, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as handle:
            json.dump({"name": "not-businessops"}, handle)
        result = run_entry(LAUNCHER_LINE, "print('ran')", other, outside_repo_tempdir(self, "bops-tc-"))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("ran", result.stdout)
        self.assertIn("not-businessops", result.stderr)


class BareImportSkills(unittest.TestCase):
    """T-D: the five skills whose flows imported `bops` with no path setup."""

    def test_each_skills_engine_imports_resolve_only_through_the_launcher(self):
        cwd = outside_repo_tempdir(self, "bops-td-")
        engine = os.path.join(REPO, "lib", "python")
        for skill in BARE_IMPORT_SKILLS:
            blocks = launcher_blocks("skills/%s/SKILL.md" % skill)
            with self.subTest(skill=skill):
                self.assertTrue(blocks, "no launcher block")
                for opener, code in blocks:
                    imports = "\n".join(l for l in code.split("\n")
                                        if re.match(r"^(from \S+ import [^(]+|import \S.*)$", l))
                    self.assertIn("bops", imports)
                    probe = imports + ("\nimport sys\nprint('BOPS ' + repr(sorted(set("
                                       "m.__file__ for n, m in sys.modules.items() "
                                       "if (n == 'bops' or n.startswith('bops.')) and "
                                       "getattr(m, '__file__', None)))))\n")
                    ok = run_entry(opener, probe, REPO, cwd)
                    self.assertEqual(ok.returncode, 0, ok.stderr)
                    files = eval(ok.stdout.split("BOPS ", 1)[1].strip())  # noqa: S307 (own output)
                    self.assertTrue(files)
                    for path in files:
                        self.assertTrue(os.path.normcase(os.path.realpath(path)).startswith(
                            os.path.normcase(os.path.realpath(engine))), path)
                    bare = subprocess.run([sys.executable, "-I", "-c", imports], cwd=cwd,
                                          env=clean_env(), capture_output=True, text=True,
                                          timeout=TIMEOUT)
                    self.assertNotEqual(bare.returncode, 0, "the imports resolved without the launcher")
                    self.assertIn("No module named 'bops'", bare.stderr)


class RepresentativeCommands(unittest.TestCase):
    """T-E: representative command families reach the engine from an external working directory."""

    def test_each_representative_command_runs(self):
        cwd = outside_repo_tempdir(self, "bops-te-")
        write_input(cwd)
        headings = {"sales-analysis": "# Sales Analysis", "revenue-forecast": "# Revenue Forecast",
                    "anomaly-detection": "# Anomaly Detection",
                    "business-health": "# Business Health Snapshot"}
        for command in REPRESENTATIVE:
            opener, code = command_block(command)
            with self.subTest(command=command):
                result = run_entry(opener, code.replace("<path>", "input.csv"), REPO, cwd)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(headings[command], result.stdout)
                self.assertNotIn("Analysis stopped", result.stdout)

    def test_a_skill_block_runs_the_connector_resolution(self):
        cwd = outside_repo_tempdir(self, "bops-te-")
        blocks = launcher_blocks("skills/bops-data-ingestion/SKILL.md")
        opener, code = [b for b in blocks if "registry.resolve" in b[1]][0]
        result = run_entry(opener, code, REPO, cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CSV or Excel", result.stdout)


class WorkingDirectoryShadowing(unittest.TestCase):
    """T-F: modules planted in the working directory are never imported."""

    def setUp(self):
        self.cwd = outside_repo_tempdir(self, "bops-tf-")
        self.sentinels = outside_repo_tempdir(self, "bops-tf-sentinel-")
        plant_hostile(self.cwd, self.sentinels)
        write_input(self.cwd)

    def planted(self):
        return sorted(os.listdir(self.sentinels))

    def test_the_fixture_is_live_under_the_old_entry(self):
        legacy = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'lib/python'); "
                                 "import bops"], cwd=self.cwd, env=clean_env(), capture_output=True,
                                text=True, timeout=TIMEOUT)
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        self.assertIn("lib-python-bops", self.planted(), "control: the old entry ran the planted bops")

    def test_the_launcher_imports_nothing_planted(self):
        opener, code = command_block("sales-analysis")
        result = run_entry(opener, code.replace("<path>", "input.csv") + "\n" + ORIGINS,
                           REPO, self.cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# Sales Analysis", result.stdout)
        self.assertEqual(self.planted(), [], "a planted module was imported")
        found = origins(result.stdout)
        self.assertTrue(same(found["bops"], os.path.join(REPO, "lib", "python", "bops", "__init__.py")))
        for name in ("json", "decimal"):
            self.assertFalse(same(os.path.dirname(found[name]), self.cwd), name)


class EnvironmentAndIsolation(unittest.TestCase):
    """T-G: a hostile PYTHONPATH cannot redirect the engine; non-isolated runs are refused."""

    def setUp(self):
        self.cwd = outside_repo_tempdir(self, "bops-tg-")
        self.hostile = outside_repo_tempdir(self, "bops-tg-path-")
        self.sentinels = outside_repo_tempdir(self, "bops-tg-sentinel-")
        plant_hostile(self.hostile, self.sentinels)
        self.env = clean_env(PYTHONPATH=self.hostile)

    def test_the_fixture_is_live_without_isolation(self):
        control = subprocess.run([sys.executable, "-c", "import bops"], cwd=self.cwd, env=self.env,
                                 capture_output=True, text=True, timeout=TIMEOUT)
        self.assertEqual(control.returncode, 0, control.stderr)
        self.assertTrue(os.listdir(self.sentinels), "control: PYTHONPATH supplied the planted bops")

    def test_a_hostile_pythonpath_cannot_redirect_the_engine(self):
        result = run_entry(LAUNCHER_LINE, ORIGINS, REPO, self.cwd, env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(os.listdir(self.sentinels), [])
        self.assertTrue(same(origins(result.stdout)["bops"],
                             os.path.join(REPO, "lib", "python", "bops", "__init__.py")))

    def test_a_non_isolated_run_is_refused_before_any_import(self):
        result = run_entry(LAUNCHER_LINE, "print('ran')", REPO, self.cwd, isolated=False, env=self.env)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("ran", result.stdout)
        self.assertIn("isolated mode", result.stderr)
        self.assertEqual(os.listdir(self.sentinels), [])

    def test_malformed_arguments_are_refused(self):
        for argv in ([], ["-c"], ["--where", "extra"], ["-x", "print(1)"]):
            with self.subTest(argv=argv):
                result = subprocess.run([sys.executable, "-I", os.path.join(
                    REPO, "lib", "python", "bops_run.py")] + argv, cwd=self.cwd, env=clean_env(),
                    capture_output=True, text=True, timeout=TIMEOUT)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage:", result.stderr)


class WorkingDirectoryIndependence(unittest.TestCase):
    """T-H: import resolution is independent of the working directory; input resolution is not."""

    def test_the_same_input_gives_the_same_result_from_different_directories(self):
        first, second = (outside_repo_tempdir(self, "bops-th-a-"), outside_repo_tempdir(self, "bops-th-b-"))
        opener, code = command_block("sales-analysis")
        outputs = []
        for cwd in (first, second):
            write_input(cwd)
            result = run_entry(opener, code.replace("<path>", "input.csv"), REPO, cwd)
            self.assertEqual(result.returncode, 0, result.stderr)
            outputs.append(result.stdout)
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(where(REPO, first), where(REPO, second))

    def test_a_different_input_in_another_directory_gives_a_different_result(self):
        first, other = (outside_repo_tempdir(self, "bops-th-a-"), outside_repo_tempdir(self, "bops-th-c-"))
        write_input(first, rows=1200)
        write_input(other, rows=2400)
        opener, code = command_block("sales-analysis")
        a = run_entry(opener, code.replace("<path>", "input.csv"), REPO, first)
        c = run_entry(opener, code.replace("<path>", "input.csv"), REPO, other)
        self.assertEqual((a.returncode, c.returncode), (0, 0), a.stderr + c.stderr)
        self.assertNotEqual(a.stdout, c.stdout, "the relative input did not resolve per directory")
        self.assertEqual(where(REPO, first), where(REPO, other))


class M132ExternalWorkingDirectoryPrerequisite(unittest.TestCase):
    """T-J: the M13-DEF-04 prerequisite for resuming M13.2's G-2 manual observations.

    This is readiness evidence only, not a manual observation. It establishes that:

    - every engine-reaching command and skill uses the accepted substitution mechanism;
    - one command and one skill block run from a cache-like copy, at a path with a space,
      from an external working directory holding planted modules;
    - the engine comes from that copy, nothing planted is imported, and no
      repository-root dependency remains.
    """

    def test_every_engine_block_uses_the_substituted_launcher(self):
        files = [os.path.join("commands", n) for n in os.listdir(os.path.join(REPO, "commands"))]
        files += [os.path.join("skills", n, "SKILL.md") for n in os.listdir(os.path.join(REPO, "skills"))]
        total = 0
        for relative in files:
            text = _read(os.path.join(REPO, relative))
            for match in re.finditer(r"^```(\w*)\n(.*?)^```", text, re.M | re.S):
                if re.search(r"lib/python|^\s*(from|import) bops\b", match.group(2), re.M):
                    total += 1
                    with self.subTest(file=relative):
                        self.assertIn(match.group(2).split("\n")[0], (LAUNCHER_LINE, HEREDOC_OPEN))
        self.assertGreaterEqual(total, 34)

    def test_command_and_skill_run_from_a_copy_under_hostile_conditions(self):
        base = outside_repo_tempdir(self, "bops-tj-")
        root = copy_shipped(os.path.join(base, "installed copy", "businessops"))
        cwd = outside_repo_tempdir(self, "bops-tj-cwd-")
        sentinels = outside_repo_tempdir(self, "bops-tj-sentinel-")
        plant_hostile(cwd, sentinels)
        write_input(cwd)
        opener, code = command_block("revenue-forecast")
        command = run_entry(opener, code.replace("<path>", "input.csv") + "\n" + ORIGINS, root, cwd)
        self.assertEqual(command.returncode, 0, command.stderr)
        self.assertIn("# Revenue Forecast", command.stdout)
        opener, code = [b for b in launcher_blocks("skills/bops-data-ingestion/SKILL.md")
                        if "data_profile" in b[1]][0]
        skill = run_entry(opener, code.replace("<path>", "input.csv") + "\n" + ORIGINS, root, cwd)
        self.assertEqual(skill.returncode, 0, skill.stderr)
        for result in (command, skill):
            self.assertTrue(same(origins(result.stdout)["bops"],
                                 os.path.join(root, "lib", "python", "bops", "__init__.py")))
        self.assertEqual(os.listdir(sentinels), [])
        self.assertTrue(same(where(root, cwd)["plugin_root"], root))


if __name__ == "__main__":
    unittest.main()
