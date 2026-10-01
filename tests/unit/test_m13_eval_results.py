"""M13-DEF-06 guard: a harness result is admissible only if its run actually executed.

ADR-0039 E.6 already says what the evidence classes mean — `automated_pass` is a case
**executed** under section F whose every run passed, and a run the platform refused or failed
is `execution_unavailable`. Nothing enforced it, and on 2026-09-22 the Stage 2 pilot showed why
that mattered: the platform refused the run before its first turn, no tool event reached the
trace, and the harness still reported `passed: true`, `score: 1`, `casesPassed: 1`. The single
LLM grader was evaluated against an empty transcript, and a negatively-worded criterion ("did it
avoid asking for approval?") passes vacuously against nothing at all.

This module is the rule, written once and deterministically:

- `run_admissibility()` accepts a run only when it took at least one turn, reported no error,
  and carries a real verdict. Anything it cannot establish is inadmissible, never admissible.
- `classify_case()` maps a case's runs to exactly one ADR-0039 E.6 class. An observed failure
  takes precedence over an unavailability (E.6); a pass requires every expected run to be
  admissible and passing.
- `classify_result()` applies it to a whole `--json` document.
- **ADR-0049 (M13-DEF-23):** a run whose only unfavourable evidence is a *split* -- a scored
  semantic LLM grader whose recorded judge votes include both a pass and a fail -- is
  `execution_unavailable` for that run: inconclusive, never a pass and never a fail. A run with an
  established failure (a deterministic grader, or a semantic grader whose votes agree) is still a
  failure, and every inadmissible run is classified exactly as before. There is no majority rule.
  Results recorded before ADR-0049 keep their classes: `SPLIT_AS_RECORDED` names the prior rule,
  used only to confirm those stored classes, and never to classify a new result.

It reads no network, starts no process and executes no eval. The committed fixture is the shape
the pilot produced, kept so the regression cannot come back quietly. **It is not evidence that
BusinessOps behaves any particular way**, and no test here asserts one.
"""

import copy
import json
import os
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCEDURE = os.path.join(REPO, "docs", "testing", "eval-suite.md")
PILOT = os.path.join(REPO, "tests", "fixtures", "eval_results",
                     "2026-09-22-stage2-pilot.json")
#: The second 2026-09-22 pilot: the run that genuinely executed, and failed. It is the other
#: half of the rule's job -- the refused run above must not be admitted, and this one must be.
EXECUTED = os.path.join(REPO, "tests", "fixtures", "eval_results",
                        "2026-09-22-pilot-executed.json")

#: ADR-0039 F: the policy runs every case three times at threshold 1.0.
EXPECTED_RUNS = 3
PASS = "automated_pass"
FAIL = "automated_fail"
UNAVAILABLE = "execution_unavailable"
#: The sentence docs/testing/eval-suite.md must carry, so the rule cannot vanish from the
#: procedure while this module still enforces it.
RULE_SENTENCE = ("A result is admissible only if its run executed: at least one turn, no error, "
                 "and a recorded verdict.")
#: ADR-0049: a split semantic verdict is inconclusive. The rule for every result from now on.
SPLIT_INCONCLUSIVE = "ADR-0049"
#: The rule in force when the 2026-09-22 pilots and the 2026-09-25 closing evaluation were
#: recorded: the platform's majority verdict stood. Used only to confirm those stored classes.
SPLIT_AS_RECORDED = "pre-ADR-0049"
#: The sentence docs/testing/eval-suite.md must carry for ADR-0049.
SPLIT_SENTENCE = "Semantic LLM judge disagreement is classified as execution_unavailable."


def run_admissibility(run):
    """None if this run's result may be counted, else why it may not be."""
    if not isinstance(run, dict):
        return "the run record is not a mapping"
    error = run.get("error")
    if isinstance(error, str) and error.strip():
        return "the run reported an error: %s" % error.strip().split(" · ")[0][:120]
    if error not in (None, "", False):
        return "the run reported an error"
    turns = run.get("turns")
    if not isinstance(turns, int) or isinstance(turns, bool):
        return "the run does not record how many turns it took"
    if turns < 1:
        return "the run took no turn"
    if not isinstance(run.get("passed"), bool):
        return "the run carries no verdict"
    graders = run.get("graders")
    if graders is not None:
        if not isinstance(graders, list) or not graders:
            return "the run scored no grader"
        if not any(isinstance(g, dict) and g.get("scored", True) for g in graders):
            return "no grader in the run was scored"
    return None


def judge_votes(grader):
    """[bool, ...] for a semantic grader's recorded judge votes, or None if it records none.

    Reads the platform's `judgeVotes` list when present, else the `judge votes: PASS FAIL ...`
    explanation (the only form the trimmed fixtures keep). Anything else is not a vote record.
    """
    if not isinstance(grader, dict):
        return None
    votes = grader.get("judgeVotes")
    if isinstance(votes, list) and votes and all(isinstance(v, bool) for v in votes):
        return list(votes)
    text = grader.get("explanation")
    if isinstance(text, str) and text.startswith("judge votes:"):
        words = text[len("judge votes:"):].split()
        if words and all(w in ("PASS", "FAIL") for w in words):
            return [w == "PASS" for w in words]
    return None


def split_graders(run):
    """[(grader name, votes text)] for every scored semantic grader whose votes conflict."""
    found = []
    for grader in run.get("graders") or []:
        votes = judge_votes(grader)
        if grader.get("scored", True) and votes and len(set(votes)) > 1:
            found.append((grader.get("name"), " ".join("PASS" if v else "FAIL" for v in votes)))
    return found


def established_failure(run):
    """True when a scored grader failed on evidence ADR-0049 accepts: a deterministic grader, or a
    semantic grader whose votes agree. A grader recording no votes is taken as recorded."""
    for grader in run.get("graders") or []:
        if not isinstance(grader, dict) or not grader.get("scored", True) or grader.get("passed") is not False:
            continue
        votes = judge_votes(grader)
        if votes is None or len(set(votes)) == 1:
            return True
    return False


def classify_case(case, expected_runs=EXPECTED_RUNS, split_rule=SPLIT_INCONCLUSIVE):
    """(class, reason) for one case of a harness result, under ADR-0039 E.6 as amended by ADR-0049."""
    if not isinstance(case, dict):
        return UNAVAILABLE, "the case record is not a mapping"
    arms = case.get("arms")
    runs = arms.get("with") if isinstance(arms, dict) else None
    if not isinstance(runs, list) or not runs:
        return UNAVAILABLE, "the case has no recorded run"
    admissible, refused = [], []
    for index, run in enumerate(runs):
        reason = run_admissibility(run)
        if reason is not None:
            refused.append("run %d: %s" % (index + 1, reason))
        elif (split_rule == SPLIT_INCONCLUSIVE and split_graders(run)
              and not established_failure(run)):
            # ADR-0049: inconclusive automated evidence, not a product failure.
            refused.append("run %d: semantic judge votes split (%s); inconclusive under ADR-0049"
                           % (index + 1, "; ".join("%s %s" % s for s in split_graders(run))))
        else:
            admissible.append(run)
    # E.6: an observed failure takes precedence over an unavailability.
    failed = [r for r in admissible if r.get("passed") is False]
    if failed:
        return FAIL, "%d of %d executed runs failed" % (len(failed), len(admissible))
    if refused:
        return UNAVAILABLE, "; ".join(refused)
    if len(admissible) < expected_runs:
        return UNAVAILABLE, ("only %d of %d runs were scored, and none failed"
                             % (len(admissible), expected_runs))
    return PASS, "all %d runs executed and passed" % len(admissible)


def classify_result(document, expected_runs=EXPECTED_RUNS, split_rule=SPLIT_INCONCLUSIVE):
    """{case name: (class, reason)} for a whole `claude plugin eval --json` document."""
    cases = document.get("cases") if isinstance(document, dict) else None
    if not isinstance(cases, list):
        return {}
    out = {}
    for index, case in enumerate(cases):
        name = case.get("name") if isinstance(case, dict) else None
        out[name or "case %d" % (index + 1)] = classify_case(case, expected_runs, split_rule)
    return out


def passing_run(**overrides):
    run = {"score": 1, "passed": True, "turns": 4, "costUsd": 0.01,
           "graders": [{"name": "g-one", "passed": True, "scored": True}]}
    run.update(overrides)
    return run


def case_of(*runs):
    return {"name": "a01-read-only-anomaly-detection", "arms": {"with": list(runs)}}


class TheStageTwoPilotIsNeverAPass(unittest.TestCase):
    """The regression M13-DEF-06 is named for, pinned to the shape the pilot produced."""

    @classmethod
    def setUpClass(cls):
        with open(PILOT, encoding="utf-8") as handle:
            cls.document = json.load(handle)

    def test_the_fixture_still_has_the_shape_that_caused_the_defect(self):
        run = self.document["cases"][0]["arms"]["with"][0]
        self.assertEqual(run["turns"], 0)
        self.assertTrue(run["error"].strip())
        self.assertIs(run["passed"], True)
        self.assertEqual(self.document["aggregates"], {"casesTotal": 1, "casesPassed": 1,
                                                       "overallScore": 1, "overallPassRate": 1})
        self.assertEqual(run["graders"][0]["explanation"], "judge votes: PASS PASS PASS")

    def test_the_harness_verdict_is_refused(self):
        classified = classify_result(self.document)
        verdict, reason = classified["a01-read-only-anomaly-detection"]
        self.assertEqual(verdict, UNAVAILABLE)
        # The run carries both an error and zero turns; the rule reports the error it hit first,
        # and either one alone is enough to refuse the result.
        self.assertIn("reported an error", reason)
        run = copy.deepcopy(self.document["cases"][0]["arms"]["with"][0])
        del run["error"]
        self.assertIn("took no turn", run_admissibility(run))

    def test_it_is_not_a_pass_by_any_route(self):
        classified = classify_result(self.document)
        for verdict, _reason in classified.values():
            self.assertNotEqual(verdict, PASS)
            self.assertNotEqual(verdict, FAIL)

    def test_the_headline_aggregate_does_not_override_the_run(self):
        """`casesPassed: 1` and `overallScore: 1` are the harness's; they are not admissible."""
        document = copy.deepcopy(self.document)
        document["aggregates"]["overallPassRate"] = 1
        document["cases"][0]["aggregates"]["score"] = 1
        self.assertEqual(classify_result(document)["a01-read-only-anomaly-detection"][0],
                         UNAVAILABLE)


class ARunIsAdmissibleOnlyIfItExecuted(unittest.TestCase):

    def test_a_clean_run_is_admissible(self):
        self.assertIsNone(run_admissibility(passing_run()))

    def test_zero_turns_is_refused(self):
        self.assertIn("no turn", run_admissibility(passing_run(turns=0)))

    def test_an_error_is_refused_even_with_turns(self):
        self.assertIn("error", run_admissibility(passing_run(error="exit 1: sandbox unavailable")))

    def test_an_error_is_refused_even_when_the_run_says_passed(self):
        self.assertIsNotNone(run_admissibility(passing_run(turns=0, error="refused", passed=True)))

    def test_missing_turns_is_refused(self):
        run = passing_run()
        del run["turns"]
        self.assertIn("how many turns", run_admissibility(run))

    def test_a_non_integer_turn_count_is_refused(self):
        self.assertIsNotNone(run_admissibility(passing_run(turns="4")))
        self.assertIsNotNone(run_admissibility(passing_run(turns=True)))

    def test_a_missing_verdict_is_refused(self):
        run = passing_run()
        del run["passed"]
        self.assertIn("no verdict", run_admissibility(run))

    def test_an_unscored_grader_set_is_refused(self):
        self.assertIn("no grader", run_admissibility(
            passing_run(graders=[{"name": "g", "passed": True, "scored": False}])))
        self.assertIn("scored no grader", run_admissibility(passing_run(graders=[])))

    def test_a_malformed_run_is_refused(self):
        for value in (None, [], "passed", 1):
            with self.subTest(run=value):
                self.assertIsNotNone(run_admissibility(value))


class ACaseTakesExactlyOneClass(unittest.TestCase):

    def test_three_executed_passing_runs_are_a_pass(self):
        verdict, _ = classify_case(case_of(passing_run(), passing_run(), passing_run()))
        self.assertEqual(verdict, PASS)

    def test_one_executed_failing_run_is_a_fail(self):
        verdict, reason = classify_case(case_of(passing_run(), passing_run(),
                                                passing_run(passed=False)))
        self.assertEqual(verdict, FAIL)
        self.assertIn("1 of 3", reason)

    def test_an_observed_failure_outranks_a_refusal(self):
        verdict, _ = classify_case(case_of(passing_run(passed=False), passing_run(turns=0)))
        self.assertEqual(verdict, FAIL)

    def test_passes_with_one_refused_run_are_unavailable(self):
        verdict, reason = classify_case(case_of(passing_run(), passing_run(),
                                                passing_run(turns=0, error="refused")))
        self.assertEqual(verdict, UNAVAILABLE)
        self.assertIn("run 3", reason)

    def test_too_few_runs_are_unavailable_even_when_all_passed(self):
        verdict, reason = classify_case(case_of(passing_run(), passing_run()))
        self.assertEqual(verdict, UNAVAILABLE)
        self.assertIn("only 2 of 3", reason)

    def test_no_runs_at_all_are_unavailable(self):
        for arms in ({"with": []}, {}, None, {"with": "three"}):
            with self.subTest(arms=arms):
                verdict, _ = classify_case({"name": "a01", "arms": arms})
                self.assertEqual(verdict, UNAVAILABLE)

    def test_a_pass_needs_every_run_admissible(self):
        """No combination containing an inadmissible run may classify as a pass."""
        bad = (passing_run(turns=0), passing_run(error="refused"),
               passing_run(graders=[{"name": "g", "scored": False}]))
        for index, broken in enumerate(bad):
            for position in range(EXPECTED_RUNS):
                runs = [passing_run() for _ in range(EXPECTED_RUNS)]
                runs[position] = broken
                with self.subTest(kind=index, position=position):
                    self.assertNotEqual(classify_case(case_of(*runs))[0], PASS)


class TheExecutedPilotIsAdmittedAndFails(unittest.TestCase):
    """The counterpart regression: the rule must not refuse a run that really executed.

    A default-refuse rule fails in two directions. M13-DEF-06 was the first: a refused run
    admitted as a pass. The second would be as damaging -- an executed failure written off as
    `execution_unavailable` because its cause was environmental, which would let an infrastructure
    problem quietly erase a real observed failure. ADR-0039 E.6 settles it: "an observed failure
    takes precedence". This class pins that direction to the run that produced it.
    """

    @classmethod
    def setUpClass(cls):
        with open(EXECUTED, encoding="utf-8") as handle:
            cls.document = json.load(handle)

    def run_record(self):
        return self.document["cases"][0]["arms"]["with"][0]

    def test_the_fixture_still_has_the_shape_that_makes_it_admissible(self):
        run = self.run_record()
        self.assertEqual(run["turns"], 5)
        self.assertIsNone(run["error"])
        self.assertIs(run["passed"], False)
        self.assertIs(run["graders"][0]["scored"], True)
        self.assertEqual(self.document["aggregates"], {"casesTotal": 1, "casesPassed": 0,
                                                      "overallScore": 0, "overallPassRate": 0})

    def test_the_run_is_admissible(self):
        self.assertIsNone(run_admissibility(self.run_record()))

    def test_the_case_is_automated_fail_not_execution_unavailable(self):
        verdict, reason = classify_result(self.document, split_rule=SPLIT_AS_RECORDED)["a01-read-only-anomaly-detection"]
        self.assertEqual(verdict, FAIL)
        self.assertIn("failed", reason)

    def test_one_run_of_three_is_still_a_fail_because_the_run_that_ran_failed(self):
        """E.6: `automated_pass` needs all three runs; a single failing run is enough for FAIL."""
        self.assertEqual(classify_result(self.document, expected_runs=3, split_rule=SPLIT_AS_RECORDED)
                         ["a01-read-only-anomaly-detection"][0], FAIL)
        self.assertEqual(classify_result(self.document, expected_runs=1, split_rule=SPLIT_AS_RECORDED)
                         ["a01-read-only-anomaly-detection"][0], FAIL)

    def test_an_environmental_cause_does_not_downgrade_it(self):
        """The grader's evidence names blocked tools. The class is unchanged by that."""
        self.assertIn("denied", self.run_record()["graders"][0]["evidence"])
        self.assertEqual(classify_result(self.document, split_rule=SPLIT_AS_RECORDED)["a01-read-only-anomaly-detection"][0],
                         FAIL)

    def test_it_is_never_a_pass(self):
        for rule in (SPLIT_AS_RECORDED, SPLIT_INCONCLUSIVE):
            for verdict, _reason in classify_result(self.document, split_rule=rule).values():
                self.assertNotEqual(verdict, PASS)


class TheRuleIsWrittenDown(unittest.TestCase):

    def test_the_procedure_states_the_admissibility_rule(self):
        with open(PROCEDURE, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(RULE_SENTENCE, text)
        self.assertIn("M13-DEF-06", text)

    def test_no_recorded_result_is_admitted_that_this_module_would_refuse(self):
        """Every committed harness result is classified, and a pass is admitted only on the rule.

        The two 2026-09-22 pilot results claim no pass. The M13.2 closing evaluation
        (`2026-09-25-closing-evaluation.json`, five invocations) holds real passes, and each one
        must rest on runs that all executed and all passed; a case with any run the rule refuses
        -- a session-limit or turn-limit stop -- is never a pass.
        """
        directory = os.path.dirname(PILOT)
        found = 0
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".json"):
                continue
            found += 1
            with open(os.path.join(directory, name), encoding="utf-8") as handle:
                document = json.load(handle)
            documents = document.get("invocations", [document])
            for part in documents:
                cases = {c["name"]: c for c in part.get("cases", [])}
                for case, (verdict, _reason) in classify_result(part).items():
                    with self.subTest(result=name, case=case):
                        if name.startswith("2026-09-22"):
                            self.assertNotEqual(verdict, PASS)
                        runs = cases[case]["arms"]["with"]
                        if verdict == PASS:
                            self.assertEqual(len(runs), EXPECTED_RUNS)
                            for run in runs:
                                self.assertIsNone(run_admissibility(run))
                                self.assertIs(run["passed"], True)
                        if any(run_admissibility(run) is not None for run in runs):
                            self.assertNotEqual(verdict, PASS)
        self.assertEqual(found, 5)


# ---------------------------------------------------------------------------------------------
# ADR-0049 (M13-DEF-23): a genuine semantic judge split is inconclusive, never pass or fail
# ---------------------------------------------------------------------------------------------

CLOSING = os.path.join(REPO, "tests", "fixtures", "eval_results", "2026-09-25-closing-evaluation.json")
#: The historical results' bytes, recorded when ADR-0049 was adopted. They must never change.
HISTORICAL_SHA256 = {
    "2026-09-22-pilot-executed.json": "77a088d5cb91c3bbbe7b447db9d0d87986ee45287088a079d2ecc8caaad2edc8",
    "2026-09-22-stage2-pilot.json": "ee59fea79de6d0f2f3c078dd7a5af93ab34b2186bcebbbfdf6882352ab161b4f",
    "2026-09-25-closing-evaluation.json": "ff828b709753e599a6712a432f73aefce4a6c0c467b8bac73e2531aab0e64b2e",
}


def judged(votes, name="g-judge"):
    """A scored semantic grader as the platform records it: the majority is `passed`."""
    marks = votes.split()
    return {"name": name, "scored": True, "passed": marks.count("PASS") > marks.count("FAIL"),
            "explanation": "judge votes: " + votes}


def deterministic(passed=True, name="g-det"):
    return {"name": name, "scored": True, "passed": passed,
            "explanation": "Skill called 1x (expected 1..\u221e)" if passed else "pattern not found"}


def judged_run(*graders, **overrides):
    return passing_run(graders=list(graders), passed=all(g["passed"] for g in graders), **overrides)


def three(*graders):
    return case_of(*[judged_run(*graders) for _ in range(3)])


class SemanticJudgeSplitsAreInconclusive(unittest.TestCase):

    def verdict(self, case, rule=SPLIT_INCONCLUSIVE):
        return classify_case(case, split_rule=rule)

    def test_1_unanimous_pass_is_a_pass(self):
        self.assertEqual(self.verdict(three(judged("PASS PASS PASS")))[0], PASS)

    def test_2_unanimous_fail_is_a_fail(self):
        self.assertEqual(self.verdict(three(judged("FAIL FAIL FAIL")))[0], FAIL)

    def test_3_to_5_every_split_is_unavailable_whichever_way_the_majority_fell(self):
        for votes in ("PASS FAIL PASS", "FAIL PASS FAIL", "PASS FAIL FAIL", "FAIL FAIL PASS"):
            with self.subTest(votes=votes):
                verdict, reason = self.verdict(three(deterministic(), judged(votes)))
                self.assertEqual(verdict, UNAVAILABLE)
                self.assertIn("semantic judge votes split", reason)

    def test_6_an_execution_error_stays_an_error_and_is_not_read_as_a_split(self):
        for error in ("exit 1: Reached maximum number of turns (10)",
                      "exit 1: You've hit your session limit \u00b7 resets 8:50am (UTC)",
                      "exit 1: Sandbox is required but failed to initialize"):
            with self.subTest(error=error):
                run = judged_run(judged("PASS FAIL PASS"), error=error)
                verdict, reason = self.verdict(case_of(run, run, run))
                self.assertEqual(verdict, UNAVAILABLE)
                self.assertIn("reported an error", reason)
                self.assertNotIn("split", reason)

    def test_7_zero_turns_stays_inadmissible(self):
        run = judged_run(judged("PASS PASS PASS"), turns=0)
        verdict, reason = self.verdict(case_of(run, run, run))
        self.assertEqual(verdict, UNAVAILABLE)
        self.assertIn("no turn", reason)

    def test_8_a_missing_verdict_stays_inadmissible(self):
        run = judged_run(judged("PASS FAIL PASS"))
        del run["passed"]
        verdict, reason = self.verdict(case_of(run, run, run))
        self.assertEqual(verdict, UNAVAILABLE)
        self.assertIn("no verdict", reason)

    def test_9_deterministic_graders_classify_as_before(self):
        self.assertEqual(self.verdict(three(deterministic(True)))[0], PASS)
        self.assertEqual(self.verdict(three(deterministic(False)))[0], FAIL)

    def test_10_and_11_unanimous_semantic_verdicts_beside_deterministic_ones(self):
        self.assertEqual(self.verdict(three(deterministic(), judged("PASS PASS PASS")))[0], PASS)
        self.assertEqual(self.verdict(three(deterministic(), judged("FAIL FAIL FAIL")))[0], FAIL)

    def test_12_the_split_is_named_in_the_evidence_in_either_record_form(self):
        platform_form = {"name": "g-raw", "scored": True, "passed": True, "judgeVotes": [True, False, True],
                         "explanation": "judge votes: PASS FAIL PASS"}
        for grader in (judged("PASS FAIL PASS", name="g-raw"), dict(platform_form, explanation="x")):
            with self.subTest(grader=grader):
                run = judged_run(grader)
                self.assertEqual(split_graders(run), [("g-raw", "PASS FAIL PASS")])
                verdict, reason = self.verdict(case_of(run, run, run))
                self.assertEqual(verdict, UNAVAILABLE)
                self.assertIn("g-raw PASS FAIL PASS", reason)
                self.assertIn("ADR-0049", reason)

    def test_an_established_failure_outranks_a_split_in_the_same_run(self):
        for other in (deterministic(False), judged("FAIL FAIL FAIL", name="g-other")):
            with self.subTest(other=other["name"]):
                self.assertEqual(self.verdict(three(other, judged("PASS FAIL PASS")))[0], FAIL)

    def test_a_failing_run_outranks_a_split_run_across_the_case(self):
        case = case_of(judged_run(deterministic(False)), judged_run(judged("PASS FAIL PASS")),
                       judged_run(judged("PASS PASS PASS")))
        self.assertEqual(self.verdict(case)[0], FAIL)

    def test_a_skipped_or_unscored_grader_is_not_a_split(self):
        skipped = {"name": "g-skip", "scored": True, "passed": False, "explanation": "skipped: cost ceiling"}
        self.assertEqual(self.verdict(three(skipped))[0], FAIL)
        unscored = dict(judged("PASS FAIL PASS"), scored=False, passed=True)
        self.assertEqual(split_graders(judged_run(unscored)), [])
        self.assertEqual(self.verdict(three(deterministic(), unscored))[0], PASS)

    def test_the_admissibility_rule_is_untouched(self):
        """M13-DEF-06: a split does not make a run inadmissible; the case rule treats it."""
        self.assertIsNone(run_admissibility(judged_run(judged("PASS FAIL PASS"))))

    def test_13_the_historical_results_are_byte_identical(self):
        import hashlib
        for name, digest in HISTORICAL_SHA256.items():
            with self.subTest(result=name):
                with open(os.path.join(REPO, "tests", "fixtures", "eval_results", name), "rb") as handle:
                    self.assertEqual(hashlib.sha256(handle.read()).hexdigest(), digest)

    def test_14_the_recorded_splits_under_each_rule_without_rewriting_them(self):
        """ADR-0049 applies to future results; the stored classes stay as recorded."""
        with open(CLOSING, encoding="utf-8") as handle:
            document = json.load(handle)
        amended, recorded = {}, {}
        for invocation in document["invocations"]:
            amended.update(classify_result(invocation))
            recorded.update(classify_result(invocation, split_rule=SPLIT_AS_RECORDED))
        expected = {"a10-read-only-industry-research": UNAVAILABLE,
                    "a13-read-only-profitability-analysis": UNAVAILABLE,
                    "c02-accounting-pull-named-absence": UNAVAILABLE,
                    "c03-connect-hubspot-no-auth": UNAVAILABLE,
                    "d05-tier3-customer-refused": FAIL,
                    "d07-reidentifying-combination-blocked": UNAVAILABLE}
        for case, klass in expected.items():
            with self.subTest(case=case):
                self.assertEqual(amended[case][0], klass)
                self.assertEqual(recorded[case][0], FAIL)
        counts = {}
        for klass, _reason in recorded.values():
            counts[klass] = counts.get(klass, 0) + 1
        self.assertEqual(counts, {PASS: 16, FAIL: 34, UNAVAILABLE: 14})
        self.assertAlmostEqual(sum(i["costUsd"] for i in document["invocations"]), 47.0, places=2)

    def test_the_executed_pilots_split_is_inconclusive_under_the_amended_rule_only(self):
        with open(EXECUTED, encoding="utf-8") as handle:
            document = json.load(handle)
        self.assertEqual(classify_result(document)["a01-read-only-anomaly-detection"][0], UNAVAILABLE)
        self.assertEqual(classify_result(document, split_rule=SPLIT_AS_RECORDED)
                         ["a01-read-only-anomaly-detection"][0], FAIL)

    def test_the_amended_rule_is_the_default_for_every_new_result(self):
        """Nothing has to opt in to ADR-0049: only the historical confirmation opts out."""
        case = three(judged("PASS FAIL PASS"))
        self.assertEqual(classify_case(case)[0], UNAVAILABLE)
        self.assertEqual(classify_result({"cases": [case]})["a01-read-only-anomaly-detection"][0],
                         UNAVAILABLE)
        self.assertEqual(classify_case(case, split_rule=SPLIT_AS_RECORDED)[0], PASS)

    def test_the_procedure_states_the_rule(self):
        with open(PROCEDURE, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn(SPLIT_SENTENCE, text)
        self.assertNotIn("majority-vote rule applies", text)


# ---------------------------------------------------------------------------------------------
# The 2026-09-25 controlled re-evaluation: 34 cases, recorded separately (ADR-0049 in force)
# ---------------------------------------------------------------------------------------------

REEVALUATION = os.path.join(REPO, "tests", "fixtures", "eval_results",
                            "2026-09-25-reevaluation-34-cases.json")
#: The 34 cases whose graders, routing or staging changed after the closing evaluation.
REEVALUATION_SCOPE = (["a20", "a21", "a23", "a24", "b01", "b02", "b04"]
                      + ["d%02d" % n for n in range(1, 9)]
                      + ["r%02d" % n for n in list(range(1, 17)) + [20, 21, 22]])


class TheReEvaluationIsRecordedSeparately(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(REEVALUATION, encoding="utf-8") as handle:
            cls.document = json.load(handle)
        cls.classes = {}
        for invocation in cls.document["invocations"]:
            cls.classes.update(classify_result(invocation))

    def test_it_covers_exactly_the_thirty_four_cases_once(self):
        names = [c["name"] for i in self.document["invocations"] for c in i["cases"]]
        self.assertEqual(sorted(n[:3] for n in names), sorted(REEVALUATION_SCOPE))
        self.assertEqual(len(names), len(set(names)))

    def test_its_classes_are_the_ones_adr_0049_computes(self):
        counts = {}
        for klass, _reason in self.classes.values():
            counts[klass] = counts.get(klass, 0) + 1
        self.assertEqual(counts, {PASS: 13, FAIL: 11, UNAVAILABLE: 10})
        for case in ("r02", "r03", "r04", "r05", "r06", "r07", "r08", "r09", "r15", "r16"):
            name = next(n for n in self.classes if n.startswith(case))
            with self.subTest(case=case):
                self.assertEqual(self.classes[name][0], UNAVAILABLE)
                self.assertIn("reported an error", self.classes[name][1])

    def test_its_runs_cost_and_ceiling(self):
        runs = [r for i in self.document["invocations"] for c in i["cases"]
                for arm in c["arms"].values() for r in arm]
        self.assertEqual(len(runs), 159)
        self.assertEqual(sum(1 for r in runs if run_admissibility(r) is None), 105)
        cost = sum(i["costUsd"] for i in self.document["invocations"])
        self.assertAlmostEqual(cost, 27.2552, places=3)
        self.assertLessEqual(cost, self.document["cost_ceiling_usd"])
        for invocation in self.document["invocations"]:
            self.assertLessEqual(invocation["max_cost_usd"], self.document["cost_ceiling_usd"])

    def test_no_semantic_split_occurred_so_adr_0049_did_not_change_any_class(self):
        runs = [r for i in self.document["invocations"] for c in i["cases"]
                for arm in c["arms"].values() for r in arm]
        self.assertEqual([s for r in runs for s in split_graders(r)], [])
        recorded = {}
        for invocation in self.document["invocations"]:
            recorded.update(classify_result(invocation, split_rule=SPLIT_AS_RECORDED))
        self.assertEqual(recorded, self.classes)

    def test_it_is_not_the_closing_evaluation_and_leaves_it_unchanged(self):
        self.assertNotEqual(REEVALUATION, CLOSING)
        dirs = {i["results_dir"] for i in self.document["invocations"]}
        with open(CLOSING, encoding="utf-8") as handle:
            closing = {i["results_dir"] for i in json.load(handle)["invocations"]}
        self.assertEqual(dirs & closing, set())


# ---------------------------------------------------------------------------------------------
# The 2026-09-26 availability-completion evaluation: the ten cases the re-evaluation lost
# ---------------------------------------------------------------------------------------------

AVAILABILITY = os.path.join(REPO, "tests", "fixtures", "eval_results",
                            "2026-09-26-availability-10-cases.json")
AVAILABILITY_SCOPE = ["r02", "r03", "r04", "r05", "r06", "r07", "r08", "r09", "r15", "r16"]


class TheAvailabilityCompletionIsRecordedSeparately(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(AVAILABILITY, encoding="utf-8") as handle:
            cls.document = json.load(handle)
        cls.runs = [r for i in cls.document["invocations"] for c in i["cases"]
                    for arm in c["arms"].values() for r in arm]

    def test_it_covers_exactly_the_ten_unavailable_cases_with_the_raised_turn_budget(self):
        cases = [c for i in self.document["invocations"] for c in i["cases"]]
        self.assertEqual(sorted(c["name"][:3] for c in cases), AVAILABILITY_SCOPE)
        self.assertEqual({c["maxTurns"] for c in cases}, {self.document["max_turns"]})
        self.assertEqual(self.document["max_turns"], 20)

    def test_every_case_is_an_admissible_automated_pass(self):
        classes = {}
        for invocation in self.document["invocations"]:
            classes.update(classify_result(invocation))
        self.assertEqual({k for k, _r in classes.values()}, {PASS})
        self.assertEqual(len(classes), 10)
        self.assertEqual(len(self.runs), 60)
        self.assertTrue(all(run_admissibility(r) is None for r in self.runs))

    def test_it_stays_inside_the_remaining_authorisation(self):
        cost = sum(i["costUsd"] for i in self.document["invocations"])
        self.assertAlmostEqual(cost, 17.6052, places=3)
        self.assertLessEqual(cost, self.document["cost_ceiling_usd"])
        self.assertLessEqual(self.document["prior_spend_usd"] + cost, self.document["authorization_usd"])
        for invocation in self.document["invocations"]:
            self.assertLessEqual(invocation["max_cost_usd"], self.document["cost_ceiling_usd"])

    def test_no_split_and_no_platform_limit_occurred(self):
        self.assertEqual([s for r in self.runs for s in split_graders(r)], [])
        self.assertEqual([r["error"] for r in self.runs if r["error"]], [])

    def test_it_is_separate_from_both_earlier_records(self):
        mine = {i["results_dir"] for i in self.document["invocations"]}
        for path in (CLOSING, REEVALUATION):
            with open(path, encoding="utf-8") as handle:
                other = {i["results_dir"] for i in json.load(handle)["invocations"]}
            with self.subTest(record=os.path.basename(path)):
                self.assertEqual(mine & other, set())


if __name__ == "__main__":
    unittest.main()
