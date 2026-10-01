"""M13-DEF-10: the evaluation grant set is represented correctly, and stays least-privilege.

The 2026-09-22 three-run pilot showed that the authorised grant permits the ADR-0045 engine call
but not the read-only step the agent takes first, and that in `dontAsk` mode the denial ends the
attempt. Choosing the remediation is an owner decision that needs a paid run to verify, so what
this module holds is the *representation*: which grant is authorised, which are excluded, that any
candidate is read-only, and that grants stay operator-side rather than migrating into a case file.

It reads documents and case files as text. It starts no process, runs no evaluation, and asserts
nothing about which candidate the owner will choose.
"""

import glob
import importlib.util
import os
import re
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
#: BusinessOps M3 moved the M9-B harness from commands/ to dev/harness/ (ADR-0055); it is still
#: enumerated with the commands so every check keeps covering it at its new location.
PROCEDURE = os.path.join(REPO, "docs", "testing", "eval-suite.md")
DEFECTS = os.path.join(REPO, "docs", "testing", "defects.md")
RESOLVER = os.path.join("lib", "bops_run.sh")

#: The runtime grant, written with a placeholder because the real value is an absolute path and
#: §E.5 forbids one in a case file. It permits exactly the ADR-0045 invocation. Unchanged since
#: 2026-09-22 and this module exists partly to keep it that way.
RESOLVER_GRANT = "Bash(sh <plugin path>/lib/bops_run.sh:*)"
#: The read grant added 2026-09-23 for M13-DEF-10. A **bare** tool name, with no pattern: that is
#: what makes the harness compute read scopes at all, and it is why the spelling matters. It grants
#: no shell, no write, no network and no connector access.
READ_GRANT = "Read"
#: The whole authorised set. Exactly two entries.
AUTHORISED = (READ_GRANT, RESOLVER_GRANT)
#: Shell grants the procedure may mention only as things ruled out. `Bash(ls:*)` is here because it
#: was the considered alternative to `Read` and was rejected: read-only in effect, but still shell.
EXCLUDED = ("Bash(ls:*)", "Bash(sh:*)", "Bash(python:*)", "Bash(python *)")
#: Every `Bash(...)` grant the procedure is allowed to mention at all. There is no read-only shell
#: allowlist any more: the discovery path uses `Read`, so no command name is permitted a grant.
PERMITTED_MENTIONS = (RESOLVER_GRANT,) + EXCLUDED
GRANT = re.compile(r"Bash\([^)]*\)")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def case_paths():
    return sorted(glob.glob(os.path.join(REPO, "evals", "*", "*", "case.yaml")))


def load_cases():
    spec = importlib.util.spec_from_file_location(
        "m13_eval_cases", os.path.join(os.path.dirname(__file__), "test_m13_eval_cases.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_cases()


class TheAuthorisedGrant(unittest.TestCase):

    def setUp(self):
        self.text = read(PROCEDURE)

    def test_the_procedure_names_both_authorised_grants(self):
        for grant in AUTHORISED:
            with self.subTest(grant=grant):
                self.assertIn(grant, self.text)

    def test_the_resolver_grant_is_unchanged(self):
        """M13-DEF-10's remediation must not have touched the runtime boundary's grant."""
        self.assertIn(RESOLVER_GRANT, self.text)
        self.assertIn("Unchanged since 2026-09-22", self.text)

    def test_the_read_grant_is_bare_because_a_pattern_would_not_compute_read_scopes(self):
        """The spelling is load-bearing: `Read(<pattern>)` would not grant read scopes at all."""
        self.assertEqual(READ_GRANT, "Read")
        self.assertNotIn("Read(", self.text)
        self.assertIn("bare read tool", self.text)

    def test_it_matches_the_invocation_form_the_commands_actually_use(self):
        """The grant must track ADR-0045's boundary, not drift from it."""
        self.assertTrue(os.path.isfile(os.path.join(REPO, RESOLVER)))
        boundary = 'sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "'
        shipped = [p for p in
                   (glob.glob(os.path.join(REPO, "commands", "*.md"))
                        + glob.glob(os.path.join(REPO, "dev", "harness", "*.md"))) +
                   glob.glob(os.path.join(REPO, "skills", "*", "SKILL.md"))
                   if boundary in read(p)]
        self.assertEqual(len(shipped), 26)
        # The grant's command prefix is the boundary's, with the placeholder substituted.
        self.assertTrue(RESOLVER_GRANT.startswith("Bash(sh "))
        self.assertIn("/lib/bops_run.sh:*)", RESOLVER_GRANT)

    def test_the_grant_is_written_with_a_placeholder_not_a_real_path(self):
        self.assertIn("<plugin path>", RESOLVER_GRANT)
        self.assertIsNone(re.search(r"Bash\(sh /(home|mnt|Users)/", self.text))


class ExcludedGrantsAreOnlyEverExcluded(unittest.TestCase):

    def setUp(self):
        self.text = read(PROCEDURE)

    def test_every_grant_the_procedure_mentions_is_one_of_the_known_ones(self):
        for mention in sorted(set(GRANT.findall(self.text))):
            with self.subTest(grant=mention):
                self.assertIn(mention, PERMITTED_MENTIONS)

    def test_each_excluded_grant_is_named_together_with_a_reason(self):
        """Naming a broad grant without saying why it is refused invites its later use."""
        reason = re.compile(r"broader|retired|defeats|never|not to be used|excluded|rejected|"
                            r"why not|still shell")
        for grant in EXCLUDED:
            with self.subTest(grant=grant):
                self.assertIn(grant, self.text)
                mentions = [l for l in self.text.split("\n") if grant in l]
                self.assertTrue(any(reason.search(l.lower()) for l in mentions),
                                "no mention of %s states a reason: %r" % (grant, mentions))

    def test_the_broad_shell_grant_is_never_presented_as_available(self):
        for line in self.text.split("\n"):
            if "Bash(sh:*)" in line:
                with self.subTest(line=line):
                    self.assertNotRegex(line.lower(), r"\bauthorised\b|\brecommended\b|\buse\b")


class TheDiscoveryPathIsReadNotShell(unittest.TestCase):

    def setUp(self):
        self.text = read(PROCEDURE)

    def section(self):
        """Just the grant-set section, so a match elsewhere cannot satisfy these tests."""
        body = self.text[self.text.index("### The grant set"):]
        marker = "\n**Recording"
        return body[:body.index(marker)] if marker in body else body

    def test_the_only_shell_grant_is_the_resolver_grant(self):
        """No second shell grant was introduced. The discovery path is not a shell at all."""
        shell_grants = [g for g in set(GRANT.findall(self.text)) if g not in EXCLUDED]
        self.assertEqual(shell_grants, [RESOLVER_GRANT])

    def test_the_rejected_shell_alternative_is_recorded_as_rejected(self):
        """`Bash(ls:*)` must remain visibly considered-and-refused, not quietly available."""
        self.assertIn("Bash(ls:*)", self.text)
        self.assertIn("considered and rejected", self.text)
        section = self.section()
        self.assertIn("still shell execution", section)

    def test_no_grant_can_expand_into_arbitrary_shell_execution(self):
        forbidden = ("rm", "mv", "tee", "curl", "wget", "python", "sh -c", "bash -c", "chmod",
                     "chown", "pip", "git", "eval", "xargs")
        for grant in AUTHORISED:
            for word in forbidden:
                with self.subTest(grant=grant, word=word):
                    self.assertNotIn(word, grant)
        # The resolver grant names one exact script and one flag pattern, nothing composable.
        self.assertEqual(RESOLVER_GRANT.count("("), 1)
        self.assertNotIn(";", RESOLVER_GRANT)
        self.assertNotIn("&&", RESOLVER_GRANT)
        self.assertNotIn("|", RESOLVER_GRANT)


class GrantsStayOperatorSide(unittest.TestCase):
    """§F.5 keeps grants on the command line. A case file may not carry one."""

    @classmethod
    def setUpClass(cls):
        cls.cases = load_cases()

    def test_no_case_declares_allowed_tools(self):
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertNotIn("allowed_tools", case.get("execution", {}))

    def test_no_case_file_contains_a_bash_grant_or_an_absolute_path(self):
        for path in case_paths():
            text = read(path)
            relative = os.path.relpath(path, REPO).replace(os.sep, "/")
            with self.subTest(case=relative):
                self.assertIsNone(GRANT.search(text))
                self.assertIsNone(re.search(r"(^|\s)/(home|mnt|Users|etc)/", text))

    def test_every_case_still_declares_the_symbolic_grant(self):
        """The symbol `engine-python` is unchanged by ADR-0045; only its mapping changed."""
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertEqual(case["tool_grants"], ["engine-python"])


class NoOtherCapabilityWasIntroduced(unittest.TestCase):
    """The remediation added read access and nothing else."""

    def setUp(self):
        self.text = read(PROCEDURE)

    def test_no_web_connector_or_authentication_grant_appears(self):
        """Written here rather than in the procedure, which a Safety test keeps free of them."""
        for token in ("WebSearch", "WebFetch", "mcp__", "--allow-real-servers", "--mocks off",
                      "authenticate", "oauth", "token="):
            with self.subTest(token=token):
                self.assertNotIn(token, self.text)

    def test_no_write_or_edit_grant_appears(self):
        for token in ("Write(", "Edit(", "NotebookEdit(", "MultiEdit("):
            with self.subTest(token=token):
                self.assertNotIn(token, self.text)

    def test_the_authorised_set_is_exactly_two_entries(self):
        self.assertEqual(len(AUTHORISED), 2)
        self.assertEqual(set(AUTHORISED), {READ_GRANT, RESOLVER_GRANT})


class ThePilotCaseRemainsValid(unittest.TestCase):
    """ADR-0039 and ADR-0044 invariants: the remediation touched no case contract."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "m13_eval_cases_v", os.path.join(os.path.dirname(__file__), "test_m13_eval_cases.py"))
        cls.validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.validator)
        cls.cases = cls.validator.load_cases()

    def test_a01_has_no_platform_contract_problem(self):
        case = self.cases["evals/approval/a01-read-only-anomaly-detection"]
        self.assertEqual(self.validator.platform_problems(case), [])
        self.assertEqual(case["platform_status"], "loadable")

    def test_every_case_still_loads_and_nothing_became_pending(self):
        for directory, case in self.cases.items():
            with self.subTest(case=directory):
                self.assertEqual(self.validator.platform_problems(case), [])
                self.assertEqual(case["platform_status"], "loadable")

    def test_the_stage_3_mapping_is_untouched(self):
        mapped = sum(1 for c in self.cases.values() for g in c["bops_graders"]
                     if g.get("platform_mapping") == "mapped")
        self.assertEqual(mapped, 133)

    def test_the_pilot_case_keeps_its_recorded_result(self):
        """The previous run's verdict is a fact and the remediation does not revise it.

        Since the M13.2 closing evaluation (2026-09-24/25) the case's class is that run's; the
        pilot's `automated_fail` is kept as history in the case's reason, not overwritten.
        """
        case = self.cases["evals/approval/a01-read-only-anomaly-detection"]
        self.assertIn("historical, superseded as the M13.2 result: executed 2026-09-22 under the "
                      "owner-authorised one-run pilot and classified automated_fail",
                      case["evidence_reason"])


class TheDistinctionIsWrittenDown(unittest.TestCase):
    """Deterministically corrected is not live-verified, and the documents must say so."""

    def test_the_procedure_states_both_halves(self):
        text = read(PROCEDURE)
        self.assertIn("deterministically corrected", text.lower())
        self.assertIn("not live-verified", text.lower())

    def test_the_defect_record_states_both_halves(self):
        text = read(DEFECTS)
        block = text[text.index("### M13-DEF-10"):]
        self.assertIn("deterministically corrected", block.lower())
        self.assertIn("not live-verified", block.lower())

    def test_no_result_file_pretends_the_agent_succeeded(self):
        """No fabricated pass may enter the recorded results."""
        import glob as _glob
        for path in _glob.glob(os.path.join(REPO, "tests", "fixtures", "eval_results", "*.json")):
            with self.subTest(fixture=os.path.basename(path)):
                self.assertNotIn("automated_pass", read(path))


class TheDefectIsRecorded(unittest.TestCase):

    def setUp(self):
        self.text = read(DEFECTS)

    def test_m13_def_10_is_a_fixed_infrastructure_defect(self):
        """`fixed_infrastructure` because the configuration is corrected; `no` follows by rule."""
        block = self.text[self.text.index("### M13-DEF-10"):]
        self.assertIn("| `defect_class` | infrastructure |", block)
        self.assertIn("| `status` | fixed_infrastructure |", block)
        self.assertIn("| `blocks_m13_completion` | no |", block)

    def test_it_records_that_read_was_never_actually_permitted(self):
        """The correction to the earlier analysis must stay on the record, not be quietly dropped."""
        block = self.text[self.text.index("### M13-DEF-10"):]
        self.assertIn("never available", block)
        self.assertIn("bare read tool", block)
        self.assertIn("wrong on the\nfacts", block)

    def test_it_records_that_the_resolver_grant_is_unchanged(self):
        block = self.text[self.text.index("### M13-DEF-10"):]
        self.assertIn("resolver grant is unchanged", block)

    def test_it_preserves_the_pilot_facts(self):
        block = self.text[self.text.index("### M13-DEF-10"):]
        for fact in ("admissible", "3 of 3 runs", "automated_fail",
                     "no new evaluation has been run"):
            with self.subTest(fact=fact):
                self.assertIn(fact, block)

    def test_it_states_the_reproducibility_and_does_not_blame_the_product(self):
        block = self.text[self.text.index("### M13-DEF-10"):]
        self.assertIn("3 of 3 runs", block)
        self.assertIn("No product file is implicated", block)
        self.assertIn("permission_denied", block)
        self.assertIn("dontAsk", block)

    def test_it_refuses_the_broad_shell_grant_in_writing(self):
        block = self.text[self.text.index("### M13-DEF-10"):]
        self.assertIn("Bash(sh:*)", block)
        self.assertIn("broader", block)


if __name__ == "__main__":
    unittest.main()
