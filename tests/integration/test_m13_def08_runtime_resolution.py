"""M13-DEF-08: the runtime resolver picks an interpreter portably, and safely (ADR-0045).

`lib/bops_run.sh` is the one place BusinessOps chooses a Python executable. This module drives it
as a real process, with a controlled PATH of stub interpreters, and covers the scenarios the
remediation was asked to prove: precedence, `python3`-only hosts, absence, an unsupported
version, a hostile interpreter in the working directory, PYTHONPATH poisoning, module shadowing,
working-directory preservation, `${CLAUDE_PLUGIN_ROOT}` handling, Windows- and Unix-style
executable lookup, paths containing spaces, an unusable interpreter, and isolation.

**No interpreter is installed and the host is never modified.** Every stub is a small shell
script in a temporary directory, and each one either delegates to the interpreter already running
these tests or deliberately misbehaves. PATH is set per subprocess only. Windows executable lookup
is simulated by stub files carrying Windows suffixes, which is deterministic here; no Windows
execution is performed and none is claimed.

`integration.test_m13_def04_engine_entry` remains the test of the import boundary itself and keeps
invoking the launcher directly. This module tests only the choosing of the interpreter and that
the handoff preserves what ADR-0042 established.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESOLVER = os.path.join(REPO, "lib", "bops_run.sh")
#: The shell is spawned by absolute path. The PATH each test hands the resolver is deliberately
#: narrow -- often a single directory holding one stub -- so a bare "sh" would not be found, and
#: the failure would look like a resolver fault rather than the test's own setup.
SH = shutil.which("sh") or "/bin/sh"
TIMEOUT = 300
#: The resolver's "no usable interpreter" status (EX_CONFIG), distinct from the launcher's 2.
NO_INTERPRETER = 78

def host_is_wsl():
    """WSL excludes Windows suffixes from automatic selection (M13-DEF-12, ADR-0046).

    The two Windows-lookup tests below therefore cannot run against the shipped resolver on a WSL
    kernel. The property they cover did not disappear: it moved to
    `integration.test_m13_def12_wsl_interpreter.OnOtherPlatformsBehaviourIsUnchanged`, which
    reaches a non-WSL platform by redirecting only the procfs path the detection reads.
    """
    try:
        with open("/proc/sys/kernel/osrelease", encoding="utf-8") as handle:
            release = handle.read()
    except OSError:
        return False
    return "icrosoft" in release or "WSL" in release


#: A stub that is a real, valid Python: it delegates to the interpreter running these tests.
GOOD = '#!/bin/sh\nprintf \'%s\\n\' "$0" >> "{log}"\nexec "{real}" "$@"\n'
#: A stub that is a real Python of an unsupported version: it answers the resolver's probe as an
#: old interpreter would, and otherwise behaves normally. This is how "too old" is simulated
#: without installing an old Python.
OLD = ('#!/bin/sh\nprintf \'%s\\n\' "$0" >> "{log}"\n'
       'case "$*" in *version_info*) printf unsupported; exit 0 ;; esac\nexec "{real}" "$@"\n')
#: A stub that exits cleanly whatever it is given, and emits nothing. A status-only probe would
#: accept it; the resolver must not, because it is not a Python.
SILENT = '#!/bin/sh\nprintf \'%s\\n\' "$0" >> "{log}"\nexit 0\n'
#: A stub that must never run. If the resolver ever executes it, it leaves proof behind.
HOSTILE = '#!/bin/sh\n: > "{sentinel}"\nprintf \'%s\\n\' "$0" >> "{log}"\nexit 0\n'


@unittest.skipUnless(shutil.which("sh"), "the resolver is a POSIX shell script")
class ResolverCase(unittest.TestCase):
    """A temporary world: stub interpreters, a run directory, and nothing touched outside it."""

    def setUp(self):
        self.world = os.path.realpath(tempfile.mkdtemp(prefix="bops-runtime-"))
        self.addCleanup(shutil.rmtree, self.world, True)
        self.log = os.path.join(self.world, "chosen.log")
        self.sentinel = os.path.join(self.world, "HOSTILE-RAN")
        self.run_dir = os.path.join(self.world, "run")
        os.makedirs(self.run_dir)

    # -- building a world ----------------------------------------------------------------------

    def stub(self, directory, name, template=GOOD):
        """Write one stub interpreter and return its path."""
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, name)
        with open(path, "w", encoding="ascii", newline="\n") as handle:
            handle.write(template.format(real=sys.executable, log=self.log,
                                         sentinel=self.sentinel))
        os.chmod(path, 0o755)
        return path

    def bin_dir(self, name="bin"):
        path = os.path.join(self.world, name)
        os.makedirs(path, exist_ok=True)
        return path

    def resolve(self, *args, path=None, cwd=None, env=None, expect=None):
        """Run the resolver with a controlled PATH, and return the completed process."""
        environment = {"PATH": path if path is not None else "",
                       "HOME": self.world, "TMPDIR": self.world}
        if env:
            environment.update(env)
        result = subprocess.run([SH, RESOLVER, *args], cwd=cwd or self.run_dir,
                                env=environment, capture_output=True, text=True,
                                errors="replace", timeout=TIMEOUT)
        if expect is not None:
            self.assertEqual(result.returncode, expect,
                             "stdout=%r stderr=%r" % (result.stdout, result.stderr))
        return result

    def chosen(self):
        """The distinct stubs the resolver touched, in the order it first touched them.

        A selected candidate is invoked twice: once for the version probe, then again by `exec`.
        That is the resolver working as designed, so the duplicate is collapsed here rather than
        asserted against. `invocations()` keeps the raw sequence for the tests that care.
        """
        seen, order = set(), []
        for name in self.invocations():
            if name not in seen:
                seen.add(name)
                order.append(name)
        return order

    def invocations(self):
        """Every stub invocation in order, probes included."""
        if not os.path.isfile(self.log):
            return []
        with open(self.log, encoding="utf-8") as handle:
            return [os.path.basename(line.strip()) for line in handle if line.strip()]

    def where(self, **kwargs):
        result = self.resolve("--where", expect=0, **kwargs)
        return json.loads(result.stdout)


class Precedence(ResolverCase):
    """A and B: which interpreter is selected, and on a host that has only `python3`."""

    def test_python_is_preferred_when_it_is_valid(self):
        """A: `python` first, which keeps ADR-0042's contract wherever it already holds."""
        directory = self.bin_dir()
        self.stub(directory, "python")
        self.stub(directory, "python3")
        self.assertEqual(self.where(path=directory)["plugin"], "businessops")
        self.assertEqual(self.chosen()[0], "python")
        self.assertNotIn("python3", self.chosen())

    def test_python3_is_used_when_python_does_not_exist(self):
        """B: the host this defect was found on. Only `python3` exists."""
        directory = self.bin_dir()
        self.stub(directory, "python3")
        self.assertEqual(self.where(path=directory)["plugin"], "businessops")
        self.assertEqual(self.chosen()[0], "python3")

    def test_a_selected_interpreter_is_probed_before_it_is_used(self):
        """The probe is what makes the choice safe, so the two-step sequence is the contract."""
        directory = self.bin_dir()
        self.stub(directory, "python3")
        self.where(path=directory)
        self.assertEqual(self.invocations(), ["python3", "python3"])

    def test_the_first_directory_on_path_wins(self):
        first, second = self.bin_dir("first"), self.bin_dir("second")
        self.stub(second, "python3")
        self.stub(first, "python3")
        self.where(path=os.pathsep.join([first, second]))
        self.assertTrue(self.chosen()[0].startswith("python3"))
        self.assertEqual(len(set(self.chosen())), 1)


class NoInterpreter(ResolverCase):
    """C: nothing usable, and the message a user can act on."""

    def test_an_empty_path_fails_deterministically(self):
        result = self.resolve("--where", path="", expect=NO_INTERPRETER)
        self.assertIn("no usable Python interpreter found", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_the_message_names_the_version_the_names_and_the_way_out(self):
        result = self.resolve("--where", path=self.bin_dir(), expect=NO_INTERPRETER)
        for expected in ("3.9 or newer", "python or python3", "BOPS_PYTHON"):
            with self.subTest(expected=expected):
                self.assertIn(expected, result.stderr)

    def test_the_failure_never_prints_the_environment(self):
        """An error must not leak PATH, HOME or any other environment value."""
        secret = os.path.join(self.world, "a-directory-named-like-a-secret")
        os.makedirs(secret, exist_ok=True)
        result = self.resolve("--where", path=secret, env={"BOPS_UNRELATED": "must-not-appear"},
                              expect=NO_INTERPRETER)
        self.assertNotIn(secret, result.stderr)
        self.assertNotIn("must-not-appear", result.stderr)
        self.assertNotIn(self.world, result.stderr)


class UnsupportedVersion(ResolverCase):
    """D and M: rejected candidates, and what happens next."""

    def test_an_unsupported_version_is_rejected_and_the_search_continues(self):
        directory = self.bin_dir()
        self.stub(directory, "python", OLD)
        self.stub(directory, "python3")
        self.assertEqual(self.where(path=directory)["plugin"], "businessops")
        self.assertEqual(self.chosen()[-1], "python3")

    def test_an_unsupported_version_alone_is_a_deterministic_failure(self):
        directory = self.bin_dir()
        self.stub(directory, "python", OLD)
        self.stub(directory, "python3", OLD)
        self.resolve("--where", path=directory, expect=NO_INTERPRETER)

    def test_something_runnable_that_is_not_python_is_rejected(self):
        """M: it exits 0 for anything and prints nothing. A status-only probe would take it."""
        directory = self.bin_dir()
        self.stub(directory, "python", SILENT)
        self.resolve("--where", path=directory, expect=NO_INTERPRETER)

    def test_a_directory_named_like_an_interpreter_is_skipped(self):
        directory = self.bin_dir()
        os.makedirs(os.path.join(directory, "python"))
        self.stub(directory, "python3")
        self.assertEqual(self.where(path=directory)["plugin"], "businessops")
        self.assertEqual(self.chosen()[0], "python3")

    def test_a_non_executable_file_is_skipped(self):
        directory = self.bin_dir()
        path = os.path.join(directory, "python")
        with open(path, "w", encoding="ascii", newline="\n") as handle:
            handle.write("#!/bin/sh\nexit 0\n")
        os.chmod(path, 0o644)
        self.stub(directory, "python3")
        self.assertEqual(self.where(path=directory)["plugin"], "businessops")


class HostileInterpreter(ResolverCase):
    """E: the working directory must never supply the interpreter."""

    def plant(self, name="python"):
        return self.stub(self.run_dir, name, HOSTILE)

    def test_a_dot_on_path_cannot_make_the_working_directory_the_interpreter(self):
        self.plant()
        good = self.bin_dir()
        self.stub(good, "python3")
        self.assertEqual(self.where(path=os.pathsep.join([".", good]))["plugin"], "businessops")
        self.assertFalse(os.path.exists(self.sentinel), "the working-directory stub was executed")
        self.assertEqual(self.chosen(), ["python3"])

    def test_an_empty_path_element_cannot_either(self):
        """An empty element means the working directory to the shell. It must not to us."""
        self.plant()
        good = self.bin_dir()
        self.stub(good, "python3")
        self.where(path=os.pathsep.join(["", good, ""]))
        self.assertFalse(os.path.exists(self.sentinel))
        self.assertEqual(self.chosen(), ["python3"])

    def test_a_relative_path_element_cannot_either(self):
        self.plant()
        good = self.bin_dir()
        self.stub(good, "python3")
        self.where(path=os.pathsep.join(["./bin", "../run", "bin", good]))
        self.assertFalse(os.path.exists(self.sentinel))
        self.assertEqual(self.chosen(), ["python3"])

    def test_with_only_a_working_directory_interpreter_it_fails_rather_than_run_it(self):
        self.plant()
        self.resolve("--where", path=".", expect=NO_INTERPRETER)
        self.assertFalse(os.path.exists(self.sentinel))

    def test_an_absolute_directory_that_happens_to_be_the_working_directory_is_honoured(self):
        """The rule is about *relative* PATH elements, not about the directory's identity.

        A virtual environment inside the user's project is legitimate and must keep working, so
        an absolute element is trusted even when it is the working directory.
        """
        self.stub(self.run_dir, "python3")
        self.assertEqual(self.where(path=self.run_dir)["plugin"], "businessops")
        self.assertEqual(self.chosen(), ["python3"])


class ExplicitOverride(ResolverCase):
    """BOPS_PYTHON: deliberate, validated, announced, and never a silent redirect."""

    def test_an_absolute_valid_override_is_used_and_announced(self):
        override = self.stub(self.bin_dir("elsewhere"), "my-python")
        result = self.resolve("--where", path="", env={"BOPS_PYTHON": override}, expect=0)
        self.assertIn("BOPS_PYTHON", result.stderr)
        self.assertEqual(self.chosen(), ["my-python"])

    def test_a_relative_override_is_refused(self):
        self.stub(self.run_dir, "python3", HOSTILE)
        result = self.resolve("--where", path="", env={"BOPS_PYTHON": "python3"},
                              expect=NO_INTERPRETER)
        self.assertIn("absolute path", result.stderr)
        self.assertFalse(os.path.exists(self.sentinel))

    def test_an_invalid_override_never_falls_back_to_path(self):
        """A silent fallback would make the override advisory. It must be authoritative."""
        good = self.bin_dir()
        self.stub(good, "python3")
        bad = self.stub(self.bin_dir("elsewhere"), "my-python", OLD)
        self.resolve("--where", path=good, env={"BOPS_PYTHON": bad}, expect=NO_INTERPRETER)
        self.assertNotIn("python3", self.chosen())

    def test_an_empty_override_is_ignored_rather_than_treated_as_a_path(self):
        directory = self.bin_dir()
        self.stub(directory, "python3")
        self.assertEqual(self.where(path=directory, env={"BOPS_PYTHON": ""})["plugin"],
                         "businessops")


class PlatformLookup(ResolverCase):
    """J, K and L: executable lookup on each platform's terms, and awkward paths."""

    def test_unix_style_lookup_finds_a_bare_name(self):
        directory = self.bin_dir()
        self.stub(directory, "python3")
        self.assertEqual(self.where(path=directory)["plugin"], "businessops")

    @unittest.skipIf(host_is_wsl(), "WSL excludes Windows suffixes (M13-DEF-12); covered by "
                                    "integration.test_m13_def12_wsl_interpreter")
    def test_windows_style_lookup_finds_an_exe_suffix(self):
        """J: simulated with a suffixed stub file. No Windows execution is performed."""
        directory = self.bin_dir()
        self.stub(directory, "python.exe")
        self.assertEqual(self.where(path=directory)["plugin"], "businessops")
        self.assertEqual(self.chosen(), ["python.exe"])

    @unittest.skipIf(host_is_wsl(), "WSL excludes Windows suffixes (M13-DEF-12); covered by "
                                    "integration.test_m13_def12_wsl_interpreter")
    def test_windows_style_lookup_covers_the_other_documented_suffixes(self):
        for suffix in (".com", ".bat", ".cmd"):
            with self.subTest(suffix=suffix):
                self.setUp()
                directory = self.bin_dir()
                self.stub(directory, "python3" + suffix)
                self.assertEqual(self.where(path=directory)["plugin"], "businessops")
                self.assertEqual(self.chosen(), ["python3" + suffix])

    def test_on_wsl_a_windows_suffix_is_not_selected_at_all(self):
        """The inverse of the two skipped tests, so this class still asserts something here."""
        if not host_is_wsl():
            self.skipTest("this host is not WSL")
        directory = self.bin_dir()
        self.stub(directory, "python.exe")
        self.resolve("--where", path=directory, expect=NO_INTERPRETER)
        self.assertEqual(self.chosen(), [], "a Windows-suffixed candidate was executed")

    def test_a_bare_name_is_preferred_over_a_suffixed_one(self):
        """True on every platform: the bare name is tried first, and on WSL it is the only one."""
        directory = self.bin_dir()
        self.stub(directory, "python")
        self.stub(directory, "python.exe")
        self.where(path=directory)
        self.assertEqual(self.chosen(), ["python"])

    def test_a_path_directory_containing_spaces_works(self):
        """L: quoting must survive a directory name with spaces."""
        directory = self.bin_dir("a directory with spaces")
        self.stub(directory, "python3")
        self.assertEqual(self.where(path=directory)["plugin"], "businessops")

    def test_an_interpreter_filename_containing_spaces_works(self):
        override = self.stub(self.bin_dir("a directory with spaces"), "my python 3")
        self.resolve("--where", path="", env={"BOPS_PYTHON": override}, expect=0)
        self.assertEqual(self.chosen(), ["my python 3"])


class IsolationIsPreserved(ResolverCase):
    """F, G and N: everything ADR-0042 established must survive the new boundary."""

    def good_path(self):
        directory = self.bin_dir()
        self.stub(directory, "python3")
        return directory

    def test_the_handoff_keeps_isolated_mode(self):
        """N: no regression to `-I`."""
        self.assertIs(self.where(path=self.good_path())["isolated"], True)

    def test_a_hostile_pythonpath_cannot_redirect_the_engine(self):
        """F: PYTHONPATH poisoning, through the resolver rather than the launcher directly."""
        poison = os.path.join(self.world, "poison")
        os.makedirs(os.path.join(poison, "bops"), exist_ok=True)
        with open(os.path.join(poison, "bops", "__init__.py"), "w", encoding="ascii") as handle:
            handle.write("raise SystemExit('hostile bops was imported')\n")
        report = self.where(path=self.good_path(), env={"PYTHONPATH": poison})
        self.assertTrue(report["bops_module"].startswith(REPO))
        self.assertIs(report["isolated"], True)

    def test_a_bops_package_in_the_working_directory_cannot_shadow_the_engine(self):
        """G: the M13-DEF-04 protection, reached through the resolver."""
        os.makedirs(os.path.join(self.run_dir, "bops"), exist_ok=True)
        with open(os.path.join(self.run_dir, "bops", "__init__.py"), "w",
                  encoding="ascii") as handle:
            handle.write("raise SystemExit('shadowing bops was imported')\n")
        report = self.where(path=self.good_path())
        self.assertEqual(os.path.realpath(report["bops_module"]),
                         os.path.realpath(os.path.join(REPO, "lib", "python", "bops",
                                                       "__init__.py")))

    def test_a_json_module_in_the_working_directory_cannot_shadow_the_standard_library(self):
        with open(os.path.join(self.run_dir, "json.py"), "w", encoding="ascii") as handle:
            handle.write("raise SystemExit('shadowing json was imported')\n")
        self.assertEqual(self.where(path=self.good_path())["plugin"], "businessops")


class ProcessContract(ResolverCase):
    """H and the handoff's mechanics: cwd, arguments, streams and exit status."""

    def good_path(self):
        directory = self.bin_dir()
        self.stub(directory, "python3")
        return directory

    def test_the_working_directory_is_unchanged_so_relative_paths_resolve(self):
        """H: the user's relative paths must keep resolving where the user is."""
        with open(os.path.join(self.run_dir, "input.csv"), "w", encoding="ascii") as handle:
            handle.write("period,revenue\n2024-01,100\n")
        result = self.resolve("-c", "import os\nprint(os.getcwd())\n"
                                   "print(open('input.csv').readline().strip())",
                              path=self.good_path(), expect=0)
        self.assertEqual(result.stdout.splitlines()[0], self.run_dir)
        self.assertEqual(result.stdout.splitlines()[1], "period,revenue")

    def test_the_engine_exit_status_is_the_resolver_exit_status(self):
        result = self.resolve("-c", "raise SystemExit(7)", path=self.good_path())
        self.assertEqual(result.returncode, 7)

    def test_stdout_and_stderr_stay_separate(self):
        result = self.resolve("-c", "import sys\nsys.stdout.write('OUT')\n"
                                    "sys.stderr.write('ERR')", path=self.good_path(), expect=0)
        self.assertEqual(result.stdout, "OUT")
        self.assertIn("ERR", result.stderr)

    def test_extra_arguments_reach_the_engine_code(self):
        result = self.resolve("-c", "import sys\nprint(sys.argv)", "one", "two words",
                              path=self.good_path(), expect=0)
        self.assertEqual(result.stdout.strip(), str(["-c", "one", "two words"]))

    def test_malformed_arguments_are_refused_by_the_launcher_not_the_resolver(self):
        """The two failure domains stay distinguishable: 2 is the launcher, 78 is the resolver."""
        result = self.resolve(path=self.good_path())
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)

    def test_a_missing_launcher_is_reported_by_the_resolver(self):
        copy = os.path.join(self.world, "lib")
        os.makedirs(copy, exist_ok=True)
        shutil.copy2(RESOLVER, os.path.join(copy, "bops_run.sh"))
        result = subprocess.run([SH, os.path.join(copy, "bops_run.sh"), "--where"],
                                cwd=self.run_dir, env={"PATH": self.good_path()},
                                capture_output=True, text=True, timeout=TIMEOUT)
        self.assertEqual(result.returncode, NO_INTERPRETER)
        self.assertIn("engine launcher not found", result.stderr)

    def test_an_unusable_path_still_finds_the_launcher(self):
        """The resolver uses no external command, so a broken PATH cannot misdirect it.

        With an external `dirname`, an unusable PATH made the launcher path working-directory
        relative — the M13-DEF-04 class of defect, reintroduced through the back door.
        """
        os.makedirs(os.path.join(self.run_dir, "python"), exist_ok=True)
        with open(os.path.join(self.run_dir, "python", "bops_run.py"), "w",
                  encoding="ascii") as handle:
            handle.write("raise SystemExit('a working-directory launcher was run')\n")
        result = self.resolve("--where", path="/nonexistent", expect=NO_INTERPRETER)
        self.assertIn("no usable Python interpreter", result.stderr)
        self.assertNotIn("engine launcher not found", result.stderr)


class ShippedBlocksUseTheBoundary(ResolverCase):
    """I and O: the real command bodies, substituted as the platform substitutes them."""

    def test_the_plugin_root_substitution_reaches_the_engine(self):
        """I: `${CLAUDE_PLUGIN_ROOT}` handling is unchanged."""
        opener = 'sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "'
        resolver = opener.replace("${CLAUDE_PLUGIN_ROOT}", REPO.replace("\\", "/"))
        resolver = resolver[len('sh "'):resolver.index('" -c "')]
        self.assertEqual(os.path.realpath(resolver), os.path.realpath(RESOLVER))
        directory = self.bin_dir()
        self.stub(directory, "python3")
        result = subprocess.run([SH, resolver, "--where"], cwd=self.run_dir,
                                env={"PATH": directory, "HOME": self.world},
                                capture_output=True, text=True, timeout=TIMEOUT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["plugin"], "businessops")

    def test_a_real_shipped_command_block_runs_through_the_resolver(self):
        """O, end to end: a shipped block's own code, run through the boundary it names."""
        import re
        path = os.path.join(REPO, "commands", "anomaly-detection.md")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        blocks = re.findall(r"^```bash\n(sh \"\$\{CLAUDE_PLUGIN_ROOT\}/lib/bops_run\.sh\" -c \"\n"
                            r".*?)^```", text, re.M | re.S)
        self.assertTrue(blocks, "no boundary block found in the shipped command")
        directory = self.bin_dir()
        self.stub(directory, "python3")
        # The block's code, with its placeholder replaced by a real input the engine can read.
        code = blocks[0].split("\n", 1)[1]
        code = code[: code.rindex('"')]
        self.assertIn("from bops", code)
        result = subprocess.run([SH, RESOLVER, "-c", "import bops\nprint('engine ok')"],
                                cwd=self.run_dir, env={"PATH": directory, "HOME": self.world},
                                capture_output=True, text=True, timeout=TIMEOUT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("engine ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
