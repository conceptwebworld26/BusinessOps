"""M13-DEF-08 static guard: what `lib/bops_run.sh` may and may not contain (ADR-0045).

`integration.test_m13_def08_runtime_resolution` proves what the resolver does. This module reads
it as text and holds the properties that a passing behavioural test would not notice going away:
that it stays POSIX, needs no external command, touches no network, installs nothing, changes no
PATH or shell profile, keeps `-I` on both handoffs, and keeps its version floor equal to the one
`CLAUDE.md` states. It also asserts that every shipped command and skill reaches the engine
through it and that none of them names an interpreter again.

It starts no process and imports nothing from the repository.
"""

import glob
import os
import re
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
#: BusinessOps M3 moved the M9-B harness from commands/ to dev/harness/ (ADR-0055); it is still
#: enumerated with the commands so every check keeps covering it at its new location.
RESOLVER = os.path.join(REPO, "lib", "bops_run.sh")
LAUNCHER = os.path.join(REPO, "lib", "python", "bops_run.py")
CLAUDE_MD = os.path.join(REPO, "CLAUDE.md")
BOUNDARY_LINE = 'sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "'
HEREDOC_OPEN = BOUNDARY_LINE + "$(cat <<'PY'"
#: ADR-0056 amends ADR-0042's rule that the plugin root appears only in the launcher line by exactly one
#: form: a backticked plugin-root path to one of the shipped policy documents in `reference/`, written in
#: prose (never in a code block; `test_m13_def04_static_guard` asserts that). It names a file for Claude
#: to read and is not a way into the engine; a relative `reference/...` path does not resolve in an
#: installed plugin (BusinessOps M3.1, live test).
REFERENCE_TOKEN = re.compile(r"`\$\{CLAUDE_PLUGIN_ROOT\}/reference/([a-z-]+\.md)`")
REFERENCE_FILES = frozenset(os.listdir(os.path.join(REPO, "reference")))


def without_reference_tokens(line):
    """`line` with each permitted reference token removed; an unknown file name is left in place."""
    return REFERENCE_TOKEN.sub(lambda m: "" if m.group(1) in REFERENCE_FILES else m.group(0), line)
RETIRED_LINE = 'python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/bops_run.py" -c "'
#: The count the repository carries today: 10 engine commands and 16 skills, 38 blocks in all
#: (34, plus the inline close each of the four research skills documents since M14-6, ADR-0053).
ENGINE_COMMANDS = 10
ENGINE_SKILLS = 16
ENGINE_BLOCKS = 38

#: Constructs that would make the script depend on bash. It runs under `sh`, so none may appear.
BASHISMS = ("[[", "((", "function ", "local ", "declare ", "typeset ", "source ",
            "echo -e", "echo -n", "$'", "&>", "|&", "+=", "<<<")
#: External commands. The resolver must need none: with an unusable PATH an external command
#: fails, and a failed `dirname` once made the launcher path working-directory relative, which is
#: the M13-DEF-04 class of defect. Everything it uses is a shell built-in.
EXTERNAL = ("dirname", "basename", "which ", "command -v", "sed", "awk", "grep", "cut ", "tr ",
            "uname", "expr ", "readlink", "realpath", "env ", "xargs", "head ", "tail ")
#: Anything that would reach the network or change the machine.
FORBIDDEN = ("curl", "wget", "http://", "https://", "ftp:", "pip ", "pip3", "apt-get", "apt ",
             "yum ", "dnf ", "brew ", "choco", "winget", "conda", "ensurepip", "get-pip",
             "download", "sudo", ".bashrc", ".bash_profile", ".profile", ".zshrc", "crontab")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def shipped_markdown():
    paths = sorted((glob.glob(os.path.join(REPO, "commands", "*.md"))
         + glob.glob(os.path.join(REPO, "dev", "harness", "*.md"))) +
                   glob.glob(os.path.join(REPO, "skills", "*", "SKILL.md")))
    return {os.path.relpath(p, REPO).replace(os.sep, "/"): read(p) for p in paths}


def code_lines(text):
    """Every line of the resolver that is not blank and not a comment."""
    return [line for line in text.split("\n") if line.strip() and not line.lstrip().startswith("#")]


class TheResolverExists(unittest.TestCase):

    def test_exactly_one_resolver_exists_and_it_is_beside_the_engine_directory(self):
        # `dist/` holds the gitignored package built by scripts/build_distribution.py (ADR-0055):
        # a build copy of this launcher, not a second one in the repository.
        found = [p for p in glob.glob(os.path.join(REPO, "**", "bops_run.sh"), recursive=True)
                 if not {".git", "dist"} & set(os.path.relpath(p, REPO).split(os.sep))]
        self.assertEqual([os.path.realpath(p) for p in found], [os.path.realpath(RESOLVER)])
        self.assertTrue(os.path.isdir(os.path.join(os.path.dirname(RESOLVER), "python")))
        self.assertTrue(os.path.isfile(LAUNCHER))

    def test_it_is_ascii_with_unix_line_endings_and_a_final_newline(self):
        with open(RESOLVER, "rb") as handle:
            raw = handle.read()
        self.assertNotIn(b"\r", raw)
        self.assertTrue(raw.endswith(b"\n"))
        raw.decode("ascii")

    def test_it_carries_no_shebang_because_the_caller_names_the_shell(self):
        """Every shipped block invokes `sh <script>`, so the mode bits never matter."""
        with open(RESOLVER, "rb") as handle:
            self.assertNotEqual(handle.read(2), b"#!")

    def test_it_fails_early_on_an_unset_variable_or_an_error(self):
        self.assertIn("set -eu", code_lines(read(RESOLVER))[0])


class ItStaysPortable(unittest.TestCase):

    def setUp(self):
        self.text = read(RESOLVER)
        self.code = "\n".join(code_lines(self.text))

    def test_it_uses_no_bash_only_construct(self):
        for construct in BASHISMS:
            with self.subTest(construct=construct):
                self.assertNotIn(construct, self.code)

    def test_it_needs_no_external_command(self):
        for command in EXTERNAL:
            with self.subTest(command=command):
                self.assertNotIn(command, self.code)

    def test_it_tries_the_bare_name_before_any_windows_suffix(self):
        """Unix must never pay for the Windows suffixes, so the bare name is first."""
        self.assertIn("bops_suffixes='- .exe .com .bat .cmd'", self.code)
        self.assertIn('-) bops_candidate="$bops_dir/$bops_name" ;;', self.code)

    def test_it_accepts_a_windows_style_absolute_path(self):
        """A drive-letter path must count as absolute, for Git Bash and similar shells."""
        self.assertEqual(self.code.count('[A-Za-z]:[/\\\\]*'), 2)

    def test_it_reads_path_but_never_writes_it(self):
        self.assertIn("$PATH", self.code)
        self.assertIsNone(re.search(r"(^|\s)(export\s+)?PATH=", self.code))


class ItChangesNothingOutsideTheProcess(unittest.TestCase):

    def setUp(self):
        self.text = read(RESOLVER)
        self.code = "\n".join(code_lines(self.text))

    def test_it_reaches_no_network_and_installs_nothing(self):
        lowered = self.code.lower()
        for token in FORBIDDEN:
            with self.subTest(token=token):
                self.assertNotIn(token, lowered)

    def test_the_only_directory_change_is_the_subshell_that_finds_the_launcher(self):
        changes = [line for line in code_lines(self.text) if re.search(r"(^|\s|\()cd\s", line)]
        self.assertEqual(len(changes), 1)
        self.assertIn('bops_lib=$(CDPATH= cd -- "$bops_self_dir" && pwd)', changes[0])

    def test_it_writes_no_file(self):
        for redirect in (">", ">>"):
            for line in code_lines(self.text):
                if redirect in line:
                    with self.subTest(line=line):
                        # Only stderr and /dev/null are ever written to.
                        self.assertTrue(">&2" in line or "/dev/null" in line, line)


class TheSecurityContract(unittest.TestCase):

    def setUp(self):
        self.text = read(RESOLVER)
        self.code = "\n".join(code_lines(self.text))

    def test_the_launcher_comes_from_the_script_location_and_not_the_environment(self):
        self.assertIn('case $0 in', self.code)
        self.assertIn('bops_launcher="$bops_lib/python/bops_run.py"', self.code)
        # CLAUDE_PLUGIN_ROOT locates the resolver in the command body; the resolver never reads it.
        self.assertNotIn("CLAUDE_PLUGIN_ROOT", self.code)

    def test_only_absolute_path_elements_are_considered(self):
        """The guard that stops a `.` or empty PATH element becoming the interpreter."""
        self.assertIn("*) continue ;;", self.code)

    def test_every_candidate_is_probed_before_it_is_used(self):
        execs = [line for line in code_lines(self.text) if line.lstrip().startswith("exec ")]
        self.assertEqual(len(execs), 2)
        for line in execs:
            with self.subTest(line=line):
                self.assertIn(" -I ", line)
                self.assertIn('"$bops_launcher"', line)
                self.assertIn('"$@"', line)

    def test_the_probe_demands_a_token_and_not_merely_an_exit_status(self):
        self.assertIn("BOPS_PROBE_MARKER=BOPS_RUNTIME_OK", self.code)
        self.assertIn('[ "$bops_probe_out" = "$BOPS_PROBE_MARKER" ] || return 1', self.code)
        self.assertIn("-I -c", self.code)

    def test_the_probe_requires_a_regular_executable_file(self):
        self.assertIn('[ -f "$1" ] || return 1', self.code)
        self.assertIn('[ -x "$1" ] || return 1', self.code)

    def test_the_override_is_absolute_validated_and_never_falls_back(self):
        self.assertIn('if [ "${BOPS_PYTHON-}" != "" ]; then', self.code)
        self.assertIn("must be an absolute path", self.text)
        # Announced on stderr: an override that is used silently is a silent redirect.
        self.assertIn("using the interpreter named by BOPS_PYTHON", self.text)

    def test_no_interpreter_path_is_hard_coded_as_a_candidate(self):
        """`/usr/bin/python3` may appear as guidance, never as something the resolver runs."""
        for line in code_lines(self.text):
            if "/usr/bin/python3" in line:
                with self.subTest(line=line):
                    self.assertTrue(line.lstrip().startswith("printf "), line)
        self.assertIsNone(re.search(r"^\s*(exec|bops_probe)\s+[\"']?/", self.text, re.M))

    def test_the_failure_message_prints_no_environment_value(self):
        messages = [line for line in code_lines(self.text) if ">&2" in line]
        self.assertTrue(messages)
        for line in messages:
            with self.subTest(line=line):
                for leak in ("$PATH", "$HOME", "$bops_dir", "$bops_rest"):
                    self.assertNotIn(leak, line)


class TheVersionFloorIsOneNumber(unittest.TestCase):

    def test_the_resolver_floor_equals_the_one_claude_md_states(self):
        code = "\n".join(code_lines(read(RESOLVER)))
        major = re.search(r"^BOPS_MIN_MAJOR=(\d+)$", code, re.M)
        minor = re.search(r"^BOPS_MIN_MINOR=(\d+)$", code, re.M)
        self.assertTrue(major and minor)
        floor = "%s.%s" % (major.group(1), minor.group(1))
        self.assertEqual(floor, "3.9")
        self.assertIn("Python %s+" % floor, read(CLAUDE_MD))

    def test_the_failure_status_is_distinct_from_the_launcher_status(self):
        code = "\n".join(code_lines(read(RESOLVER)))
        statuses = set(re.findall(r"^\s*exit (\d+)$", code, re.M))
        self.assertEqual(statuses, {"78"})
        self.assertIn("raise SystemExit(2)", read(LAUNCHER))


class EveryShippedBlockUsesTheBoundary(unittest.TestCase):
    """O: one boundary, named by every command and skill that reaches the engine."""

    @classmethod
    def setUpClass(cls):
        cls.files = shipped_markdown()

    def test_the_block_count_and_the_file_count_are_what_the_repository_holds(self):
        commands = [p for p in self.files if p.startswith(("commands/", "dev/harness/"))
                    and BOUNDARY_LINE in self.files[p]]
        skills = [p for p in self.files if p.startswith("skills/")
                  and BOUNDARY_LINE in self.files[p]]
        self.assertEqual(len(commands), ENGINE_COMMANDS)
        self.assertEqual(len(skills), ENGINE_SKILLS)
        self.assertEqual(sum(t.count(BOUNDARY_LINE) for t in self.files.values()), ENGINE_BLOCKS)

    def test_no_shipped_file_keeps_the_retired_form(self):
        for path, text in self.files.items():
            with self.subTest(path=path):
                self.assertNotIn(RETIRED_LINE, text)
                self.assertNotIn("lib/python/bops_run.py", text)

    def test_no_shipped_file_names_an_interpreter_of_its_own(self):
        """The whole point: 26 files, and none of them decides what Python is called."""
        for path, text in self.files.items():
            for line in text.split("\n"):
                if re.match(r"\s*(python|python3|py)\b", line):
                    with self.subTest(path=path, line=line):
                        self.fail("a shipped line names an interpreter: %r" % line)

    def test_the_boundary_is_the_only_place_the_plugin_root_appears(self):
        for path, text in self.files.items():
            for line in text.split("\n"):
                if "${CLAUDE_PLUGIN_ROOT}" in without_reference_tokens(line):
                    with self.subTest(path=path, line=line):
                        self.assertIn(line, (BOUNDARY_LINE, HEREDOC_OPEN))


if __name__ == "__main__":
    unittest.main()
