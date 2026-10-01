"""M13-DEF-12: under WSL the resolver must not select a Windows Python (ADR-0046).

The defect: WSL puts the host's Windows directories on `PATH` through interop, so the resolver's
Windows suffix search reached `/mnt/c/Python313/python.exe`. That interpreter **passes** the version
probe, because it genuinely is Python 3.9+, and then cannot open a Linux path — it reads
`/mnt/d/...` as `D:\\mnt\\d\\...`. The engine was never entered.

The assertion that matters is **not** "a `.exe` is skipped" but "with both discoverable, and the
Windows one first on `PATH`, the resolver selects the native interpreter". Every test here puts a
working Windows-suffixed stub **ahead** of the native one, so a resolver that lost the exclusion
would select the stub and be caught — the stubs are deliberately functional, not broken.

Platform coverage. This host is WSL, so the WSL cases run the **shipped** `lib/bops_run.sh`
unmodified. The native-Linux and native-Windows cases cannot be produced on a WSL kernel, so they
run a copy whose **only** edit is the procfs path the detection reads, redirected at a fixture. The
copy is rebuilt from the shipped file on every run, so a change to the real logic is reflected in
those tests too; nothing about the selection logic is mocked.

It starts `sh` and stub processes, runs no evaluation, and touches no repository file.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESOLVER = os.path.join(REPO, "lib", "bops_run.sh")
SH = shutil.which("sh") or "/bin/sh"
TIMEOUT = 300
NO_INTERPRETER = 78
#: The procfs path the resolver reads to decide whether it is on WSL.
OSRELEASE = "/proc/sys/kernel/osrelease"
#: Every Windows executable suffix the resolver knows.
WINDOWS_SUFFIXES = (".exe", ".com", ".bat", ".cmd")

#: A stub that is a real, working Python: it delegates to the interpreter running these tests and
#: records that it was chosen. Deliberately functional, so a resolver that selects it succeeds and
#: the test catches the *selection* rather than a downstream error.
GOOD = '#!/bin/sh\nprintf \'%s\\n\' "$0" >> "{log}"\nexec "{real}" "$@"\n'


def host_is_wsl():
    try:
        with open(OSRELEASE, encoding="utf-8") as handle:
            release = handle.read()
    except OSError:
        return False
    return "icrosoft" in release or "WSL" in release


@unittest.skipUnless(shutil.which("sh"), "the resolver is a POSIX shell script")
class ResolverCase(unittest.TestCase):

    def setUp(self):
        self.world = os.path.realpath(tempfile.mkdtemp(prefix="bops-def12-"))
        self.addCleanup(shutil.rmtree, self.world, True)
        self.log = os.path.join(self.world, "chosen.log")
        self.run_dir = os.path.join(self.world, "run")
        os.makedirs(self.run_dir)

    def stub(self, directory, name):
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, name)
        with open(path, "w", encoding="ascii", newline="\n") as handle:
            handle.write(GOOD.format(real=sys.executable, log=self.log))
        os.chmod(path, 0o755)
        return path

    def resolver_for(self, osrelease=None):
        """The shipped resolver, or a copy whose only edit redirects the detection's procfs read.

        `osrelease=None` means use the shipped file as it ships. Otherwise the text of a fixture is
        written and the copy reads that instead, which is the only way to exercise a platform this
        kernel is not.
        """
        if osrelease is None:
            return RESOLVER
        fixture = os.path.join(self.world, "osrelease")
        if osrelease is False:                      # simulate no procfs at all (native Windows)
            fixture = os.path.join(self.world, "absent-osrelease")
        else:
            with open(fixture, "w", encoding="ascii", newline="\n") as handle:
                handle.write(osrelease + "\n")
        with open(RESOLVER, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn(OSRELEASE, source, "the resolver no longer reads the procfs release string")
        copy_dir = os.path.join(self.world, "lib")
        os.makedirs(copy_dir, exist_ok=True)
        os.symlink(os.path.join(REPO, "lib", "python"), os.path.join(copy_dir, "python"))
        copy = os.path.join(copy_dir, "bops_run.sh")
        with open(copy, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(source.replace(OSRELEASE, fixture))
        return copy

    def run_resolver(self, *args, path, resolver=None, env=None, expect=None):
        environment = {"PATH": path, "HOME": self.world, "TMPDIR": self.world}
        if env:
            environment.update(env)
        result = subprocess.run([SH, resolver or RESOLVER, *args], cwd=self.run_dir,
                                env=environment, capture_output=True, text=True,
                                errors="replace", timeout=TIMEOUT)
        if expect is not None:
            self.assertEqual(result.returncode, expect,
                             "stdout=%r stderr=%r" % (result.stdout, result.stderr))
        return result

    def chosen(self):
        if not os.path.isfile(self.log):
            return []
        with open(self.log, encoding="utf-8") as handle:
            seen, order = set(), []
            for line in handle:
                name = os.path.basename(line.strip())
                if name and name not in seen:
                    seen.add(name)
                    order.append(name)
            return order

    def windows_first_path(self, suffix):
        """A PATH where a working Windows-suffixed stub precedes a native `python3`."""
        windows = os.path.join(self.world, "mnt-c-Python313")
        native = os.path.join(self.world, "usr-bin")
        self.stub(windows, "python" + suffix)
        self.stub(native, "python3")
        return os.pathsep.join([windows, native])


@unittest.skipUnless(host_is_wsl(), "the WSL cases need a WSL kernel; this host is not WSL")
class OnWslTheNativeInterpreterWins(ResolverCase):
    """The shipped resolver, on a real WSL kernel. No substitution anywhere."""

    def test_the_exact_regression_windows_python_first_native_still_chosen(self):
        """python.exe ahead of python3 on PATH, both working. Native must win."""
        report = json.loads(self.run_resolver(
            "--where", path=self.windows_first_path(".exe"), expect=0).stdout)
        self.assertEqual(report["plugin"], "businessops")
        self.assertEqual(self.chosen(), ["python3"])
        self.assertNotIn("python.exe", self.chosen())

    def test_every_windows_suffix_is_skipped_in_favour_of_the_native_name(self):
        for suffix in WINDOWS_SUFFIXES:
            with self.subTest(suffix=suffix):
                self.setUp()
                self.run_resolver("--where", path=self.windows_first_path(suffix), expect=0)
                self.assertEqual(self.chosen(), ["python3"])

    def test_with_only_windows_candidates_it_refuses_rather_than_choose_one(self):
        windows = os.path.join(self.world, "mnt-c-Python313")
        for suffix in WINDOWS_SUFFIXES:
            self.stub(windows, "python" + suffix)
        result = self.run_resolver("--where", path=windows, expect=NO_INTERPRETER)
        self.assertIn("no usable Python interpreter found", result.stderr)
        self.assertEqual(self.chosen(), [], "a Windows candidate was executed")

    def test_a_bare_native_name_in_a_windows_directory_is_still_eligible(self):
        """The rule is about suffixes, not about where a directory happens to live."""
        windows = os.path.join(self.world, "mnt-c-tools")
        self.stub(windows, "python3")
        self.assertEqual(json.loads(self.run_resolver(
            "--where", path=windows, expect=0).stdout)["plugin"], "businessops")
        self.assertEqual(self.chosen(), ["python3"])

    def test_the_explicit_override_may_still_name_a_windows_suffixed_interpreter(self):
        """Automatic selection excludes them; an explicit absolute override is not automatic."""
        override = self.stub(os.path.join(self.world, "elsewhere"), "my-python.exe")
        result = self.run_resolver("--where", path="", env={"BOPS_PYTHON": override}, expect=0)
        self.assertIn("BOPS_PYTHON", result.stderr)
        self.assertEqual(self.chosen(), ["my-python.exe"])

    def test_an_invalid_override_still_fails_without_falling_back(self):
        native = os.path.join(self.world, "usr-bin")
        self.stub(native, "python3")
        result = self.run_resolver("--where", path=native,
                                   env={"BOPS_PYTHON": "python3"}, expect=NO_INTERPRETER)
        self.assertIn("absolute path", result.stderr)
        self.assertEqual(self.chosen(), [], "the override fell back to PATH")

    def test_relative_and_empty_path_elements_are_still_rejected(self):
        hostile = self.stub(self.run_dir, "python3")
        self.assertTrue(os.path.isfile(hostile))
        native = os.path.join(self.world, "usr-bin")
        self.stub(native, "python3")
        self.run_resolver("--where", path=os.pathsep.join([".", "", "./bin", native]), expect=0)
        # Only the absolute element's stub may have run.
        self.assertEqual(self.chosen(), ["python3"])
        with open(self.log, encoding="utf-8") as handle:
            for line in handle:
                self.assertNotIn(self.run_dir, line)

    def test_isolated_mode_and_the_probe_token_are_untouched(self):
        native = os.path.join(self.world, "usr-bin")
        self.stub(native, "python3")
        report = json.loads(self.run_resolver("--where", path=native, expect=0).stdout)
        self.assertIs(report["isolated"], True)
        with open(RESOLVER, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("BOPS_PROBE_TOKEN=BOPS_RUNTIME_OK", source)
        self.assertIn(" -I ", source)


class OnOtherPlatformsBehaviourIsUnchanged(ResolverCase):
    """Native Linux and native Windows, reached by redirecting only the detection's procfs read."""

    def test_native_linux_keeps_the_windows_suffixes_eligible(self):
        """A kernel release with no Microsoft marker is not WSL, so nothing is excluded."""
        resolver = self.resolver_for("6.8.0-generic")
        path = self.windows_first_path(".exe")
        self.run_resolver("--where", path=path, resolver=resolver, expect=0)
        self.assertEqual(self.chosen(), ["python.exe"],
                         "native Linux behaviour changed: the suffix was excluded")

    def test_native_windows_with_no_procfs_keeps_them_eligible(self):
        """A native Windows shell has no procfs; the detection must fail safe to 'not WSL'."""
        resolver = self.resolver_for(False)
        path = self.windows_first_path(".exe")
        self.run_resolver("--where", path=path, resolver=resolver, expect=0)
        self.assertEqual(self.chosen(), ["python.exe"],
                         "native Windows behaviour changed: the suffix was excluded")

    def test_a_wsl_marker_excludes_them_even_on_this_copy(self):
        """The same copy, with a WSL release string, must exclude. Proves the branch is the cause."""
        for release in ("6.18.33.2-microsoft-standard-WSL2", "4.4.0-19041-Microsoft"):
            with self.subTest(release=release):
                self.setUp()
                resolver = self.resolver_for(release)
                self.run_resolver("--where", path=self.windows_first_path(".exe"),
                                  resolver=resolver, expect=0)
                self.assertEqual(self.chosen(), ["python3"])

    def test_an_unreadable_marker_fails_safe_rather_than_erroring(self):
        resolver = self.resolver_for(False)
        native = os.path.join(self.world, "usr-bin")
        self.stub(native, "python3")
        self.assertEqual(json.loads(self.run_resolver(
            "--where", path=native, resolver=resolver, expect=0).stdout)["plugin"], "businessops")


class TheExclusionIsLoadBearing(unittest.TestCase):
    """Mutation cover: removing the WSL exclusion must break a test, not pass quietly."""

    def test_the_shipped_resolver_carries_the_exclusion(self):
        with open(RESOLVER, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("bops_is_wsl=no", source)
        self.assertIn(OSRELEASE, source)
        self.assertIn("*icrosoft*|*WSL*) bops_is_wsl=yes ;;", source)
        self.assertIn('if [ "$bops_is_wsl" = yes ]; then', source)
        self.assertIn("bops_suffixes='-'", source)

    def test_the_default_suffix_list_is_still_the_full_one(self):
        """The exclusion narrows a list that otherwise keeps every platform's behaviour."""
        with open(RESOLVER, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("bops_suffixes='- .exe .com .bat .cmd'", source)

    def test_the_detection_uses_no_external_command(self):
        with open(RESOLVER, encoding="utf-8") as handle:
            lines = [l for l in handle if "osrelease" in l and not l.lstrip().startswith("#")]
        self.assertTrue(lines)
        for line in lines:
            for external in ("uname", "grep", "sed", "awk", "cat ", "cut ", "tr "):
                with self.subTest(line=line.strip(), external=external):
                    self.assertNotIn(external, line)


if __name__ == "__main__":
    unittest.main()
