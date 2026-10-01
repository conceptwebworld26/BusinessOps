# -*- coding: utf-8 -*-
"""M10.3.3 — Decision Support: a twelve-part draft decision package beside the set (ADR-0032).

`bops.decision_support` is the engine, `bops-decision-support` the skill and `/decision-support` the
command. These tests pin the contract ADR-0032 decided, over the same genuine inputs the Strategy
tests use: `commands.run()` over the shipped synthetic demo file, genuine `BOPS-REC/1` replies
closed through `research.close_retrieval_object()`, and the existing synthesis translators. The
fixtures are imported from `test_m10_3_2_strategy` rather than copied, so both consumers are
tested over one definition of the evidence.

What gets the most attention:

* **Fail closed.** Every refusal raises `DecisionSupportError`; no partial package exists.
* **Framing is never evidence.** Question, objective, options, constraints, criteria and Business
  Context are stored with their origin and cannot be cited.
* **Nothing authored that should be derived.** Confidence, lifecycle, trust, scores, weights,
  ranks and priorities have nowhere to go.
* **Figures are quoted.** Unsupported, re-signed, rounded, worded and non-ASCII figures refused.
* **At most one preferred option**, only under ADR-0032 section 10, with a fixed reason otherwise.
* **Draft only.** No path to `final`.
* **Nothing re-enters synthesis**, and nothing is executed or transmitted.

**Every fixture is synthetic.**
"""

import copy
import io
import json
import os
import re
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"),
             os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import commands as C                              # noqa: E402
from bops import config as config_mod                       # noqa: E402
from bops import context as context_mod                     # noqa: E402
from bops import decision_support as D                      # noqa: E402
from bops import evidence as evidence_mod                   # noqa: E402
from bops import jsonschema_mini                            # noqa: E402
from bops import research as R                              # noqa: E402
from bops import strategy                                   # noqa: E402
from bops import synthesis as S                             # noqa: E402
from bops.synthesis import confidence as conf_mod           # noqa: E402
from bops.synthesis import contract as sc                   # noqa: E402
from bops.synthesis import limitations as lim_mod           # noqa: E402
from unit import test_m10_3_2_strategy as F                # noqa: E402

LIB = os.path.join(REPO_ROOT, "lib", "python", "bops")
DS_PY = os.path.join(LIB, "decision_support.py")
DS_SCHEMA = os.path.join(REPO_ROOT, "lib", "schemas", "decision_support.schema.json")
STRATEGY_SCHEMA = F.STRATEGY_SCHEMA
LEDGER_SCHEMA = F.LEDGER_SCHEMA
SKILL_MD = os.path.join(REPO_ROOT, "skills", "bops-decision-support", "SKILL.md")
COMMAND_MD = os.path.join(REPO_ROOT, "commands", "decision-support.md")

QUESTION = "Should we reprice the product lines behind the gross margin decline?"
OBJECTIVE = "Protect gross margin without losing core customers."
CONSTRAINT = "No price change before the next catalogue."
HOLD = "Hold prices and cut costs"
CRITERION = "Effect on gross margin"
SECOND = "Effect on customer retention"
QUO = D.STATUS_QUO_LABEL

read = F.read
code = F.code
all_keys = F.all_keys


def load_schema(path=DS_SCHEMA):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def errors(document, definition=None):
    schema = load_schema()
    if definition:
        schema = {"$ref": "#/definitions/%s" % definition, "definitions": schema["definitions"]}
    return jsonschema_mini.validate(json.loads(json.dumps(document, default=str)), schema)


def ids(items):
    return [item if isinstance(item, str) else item.id for item in items]


class Fixture(object):
    """One mixed strict set, a Strategy result bound to it, and a valid request over both."""

    def __init__(self, **fields):
        self.synthesis, self.parts = F.mixed_set(**fields)
        self.strategy = strategy.build(self.synthesis, [F.proposal([self.parts["margin"]])])
        self.record = self.strategy.recommendations[0]
        self.rec = self.record["action"]

    def request(self, **overrides):
        p = self.parts
        request = {
            "decision_question": QUESTION,
            "objective": OBJECTIVE,
            "constraints": [CONSTRAINT],
            "options": [HOLD],
            "criteria": [CRITERION],
            "tradeoffs": [
                {"options": [self.rec, HOLD], "criteria": [CRITERION],
                 "text": "Repricing acts on the gross margin decline directly; holding prices "
                         "leaves the decline to cost cutting.",
                 "evidence": ids([p["margin"]])},
                {"options": [QUO], "criteria": [CRITERION],
                 "text": "Making no change leaves the gross margin decline in place.",
                 "evidence": ids([p["margin"]])},
            ],
            "risks": [{"option": self.rec, "text": "Price changes may reduce order volume.",
                       "evidence": ids([p["price"]])}],
            "expected_outcomes": [{"option": self.rec,
                                   "text": "Repricing addresses the move from 37.26% to 34.41%.",
                                   "evidence": ids([p["margin"]])}],
            "preferred_option": self.rec,
            "preference_criteria": [CRITERION],
        }
        request.update(copy.deepcopy(overrides))
        return request

    def build(self, strategy_result="bound", config=None, **overrides):
        bound = self.strategy if strategy_result == "bound" else strategy_result
        return D.build(self.synthesis, self.request(**overrides), strategy_result=bound,
                       config=config)


# =======================================================================================
# A. Positive paths
# =======================================================================================

class FullPackage(unittest.TestCase):
    """A complete package with a bound Strategy result and a preferred option."""

    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()
        cls.before = cls.f.synthesis.to_json()
        cls.result = cls.f.build()
        cls.output = cls.result.as_dict()
        cls.body = cls.output["body"]
        cls.options = dict((o["label"], o) for o in cls.body["options"])

    def test_the_twelve_parts_appear_in_the_contract_order(self):
        self.assertEqual(D.PART_ORDER, (
            "decision_question", "business_context", "objective", "options", "criteria",
            "evidence", "assumptions", "tradeoffs", "risks", "expected_outcomes", "guidance",
            "uncertainty"))
        self.assertEqual(tuple(self.body), D.PART_ORDER)
        serialised = self.result.to_json()
        positions = [serialised.index('"%s":' % part) for part in D.PART_ORDER]
        self.assertEqual(positions, sorted(positions))

    def test_the_package_is_schema_valid(self):
        self.assertEqual(errors(self.output), [])

    def test_the_package_is_a_draft_and_unverified(self):
        self.assertEqual(self.output["lifecycle"], D.DRAFT)
        self.assertEqual(self.result.lifecycle, D.DRAFT)
        self.assertEqual(self.output["verification"], D.UNVERIFIED)
        self.assertIn("draft", D.render(self.result).lower())
        self.assertIn("unverified", D.render(self.result))

    def test_framing_is_stored_verbatim_with_its_origin(self):
        self.assertEqual(self.body["decision_question"], {"text": QUESTION, "origin": "user"})
        self.assertEqual(self.body["objective"],
                         {"text": OBJECTIVE, "origin": "user", "stated": True})
        self.assertEqual(self.body["business_context"]["constraints"],
                         [{"text": CONSTRAINT, "origin": "user"}])
        self.assertEqual(self.body["criteria"][0]["origin"], "user")

    def test_options_are_user_then_record_then_status_quo(self):
        self.assertEqual([(o["label"], o["origin"]) for o in self.body["options"]],
                         [(HOLD, "user"), (self.f.rec, "recommendation"), (QUO, "status_quo")])
        self.assertEqual(self.options[self.f.rec]["recommendation_id"],
                         self.f.record["recommendation_id"])
        self.assertIsNone(self.options[HOLD]["recommendation_id"])

    def test_the_preferred_option_and_its_basis(self):
        guidance = self.body["guidance"]
        self.assertEqual(guidance["preferred_option"], self.options[self.f.rec]["option_id"])
        self.assertEqual(guidance["preference_basis"], {
            "recommendation_id": self.f.record["recommendation_id"],
            "criterion_ids": [self.body["criteria"][0]["criterion_id"]]})
        self.assertIsNone(guidance["no_preference_reason"])

    def test_strategy_records_are_packaged_unchanged(self):
        self.assertEqual(self.body["guidance"]["recommendations"], self.f.strategy.recommendations)
        self.assertEqual(self.body["guidance"]["recommendations"][0]["issued_by"],
                         strategy.ISSUED_BY)
        self.assertEqual(self.result.claims(), [])
        self.assertTrue(self.output["strategy_result_bound"])

    def test_the_evidence_part_indexes_exactly_what_is_cited_in_set_order(self):
        p = self.f.parts
        cited = {p["margin"].id, p["price"].id}
        listed = [d["synthesis_id"] for d in self.body["evidence"]]
        self.assertEqual(set(listed), cited)
        order = [item.id for item in self.f.synthesis.items if item.id in cited]
        self.assertEqual(listed, order)
        self.assertEqual(self.body["evidence"][0]["statement"], p["margin"].statement)

    def test_metadata_is_complete(self):
        for field in ("schema_version", "analysis", "issued_by", "lifecycle", "subject",
                      "synthesis_digest", "trust_statement", "human_decision", "order_note",
                      "material_not_cited", "conflicts", "limitations", "confidence"):
            self.assertIn(field, self.output)
        self.assertEqual(self.output["issued_by"], "bops-decision-support")
        self.assertEqual(self.output["synthesis_digest"],
                         strategy.synthesis_digest(self.f.synthesis))
        self.assertEqual(self.output["trust_statement"], S.TRUST_STATEMENT)
        self.assertIn("financial transactions are prohibited", self.output["human_decision"])
        self.assertIn("No order here is a ranking", self.output["order_note"])

    def test_the_synthesis_set_is_untouched(self):
        self.assertEqual(self.f.synthesis.to_json(), self.before)
        self.assertEqual(self.f.synthesis.recommendations, [])
        self.assertEqual(self.f.synthesis.candidate_claims, [])

    def test_the_package_is_deterministic(self):
        self.assertEqual(self.f.build().to_json(), self.result.to_json())
        self.assertEqual(D.render(self.f.build()), D.render(self.result))

    def test_tradeoffs_risks_and_outcomes_reference_real_options(self):
        option_ids = set(o["option_id"] for o in self.body["options"])
        for tradeoff in self.body["tradeoffs"]:
            self.assertTrue(set(tradeoff["option_ids"]) <= option_ids)
        for part in ("risks", "expected_outcomes"):
            for entry in self.body[part]:
                self.assertIn(entry["option_id"], option_ids)

    def test_render_carries_every_part_and_the_boundary(self):
        rendered = D.render(self.result)
        for title in ("1. Decision question", "4. Options", "8. Tradeoffs",
                      "11. Recommendation and decision guidance",
                      "12. Uncertainty, limitations and next steps", D.HUMAN_DECISION,
                      D.ORDER_NOTE, "**Preferred option:**", "The other options are not ordered"):
            self.assertIn(title, rendered)


class WithoutStrategy(unittest.TestCase):
    """Strategy is optional; Decision Support issues its own records under ADR-0031."""

    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()
        p = cls.f.parts
        cls.action = "Assess chilled storage capacity against reported UK demand."
        cls.result = D.build(cls.f.synthesis, {
            "decision_question": "Should we expand chilled storage capacity?",
            "options": [HOLD],
            "recommendations": [F.proposal([p["demand"], p["growth"]], action=cls.action,
                                           rationale="Demand rose while revenue grew.",
                                           expected_benefit="A capacity view grounded in "
                                                            "reported demand.")],
            "expected_outcomes": [{"option": cls.action,
                                   "text": "Revenue growth is 69.72%, alongside rising demand.",
                                   "evidence": ids([p["growth"], p["demand"]])}],
        })
        cls.output = cls.result.as_dict()

    def test_records_are_issued_as_decision_support(self):
        record = self.output["body"]["guidance"]["recommendations"][0]
        self.assertEqual(record["issued_by"], strategy.DECISION_SUPPORT_ISSUER)
        self.assertFalse(self.output["strategy_result_bound"])
        self.assertEqual(errors(self.output), [])

    def test_issued_records_become_ledger_claims(self):
        ledger = evidence_mod.Ledger()
        self.result.record_in(ledger)
        self.assertEqual(len(ledger.claims), 1)
        self.assertEqual(ledger.claims[0].provenance_class, evidence_mod.RECOMMENDATION)
        document = {"schema_version": "1.0.0", "claims": [c.as_dict() for c in ledger.claims]}
        self.assertEqual(F.schema_errors(document, LEDGER_SCHEMA), [])

    def test_the_record_option_and_the_unrequested_preference(self):
        labels = [o["label"] for o in self.output["body"]["options"]]
        self.assertEqual(labels, [HOLD, self.action, QUO])
        guidance = self.output["body"]["guidance"]
        self.assertIsNone(guidance["preferred_option"])
        self.assertEqual(guidance["no_preference_reason"], D.NO_PREFERENCE_REQUESTED)

    def test_strategy_behaviour_is_unchanged(self):
        record = strategy.build(self.f.synthesis, [F.proposal([self.f.parts["margin"]])])
        self.assertEqual(record.recommendations[0]["issued_by"], strategy.ISSUED_BY)
        self.assertEqual(load_schema(STRATEGY_SCHEMA)["properties"]["issued_by"],
                         {"const": "bops-strategy-recommendations"})
        with self.assertRaises(strategy.StrategyError):
            strategy.ground_recommendation(self.f.synthesis, S.grounding.index(self.f.synthesis),
                                           F.proposal([self.f.parts["margin"]]),
                                           issued_by="someone-else")


class StatusQuoAndObjective(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()

    def test_the_status_quo_can_be_excluded(self):
        result = self.f.build(include_status_quo=False, tradeoffs=[
            self.f.request()["tradeoffs"][0]])
        labels = [o["label"] for o in result.as_dict()["body"]["options"]]
        self.assertNotIn(QUO, labels)

    def test_an_absent_objective_is_recorded_as_not_stated(self):
        request = self.f.request()
        del request["objective"]
        body = D.build(self.f.synthesis, request, self.f.strategy).as_dict()["body"]
        self.assertEqual(body["objective"], {"text": None, "origin": None, "stated": False})
        self.assertEqual(errors(body["objective"], "objective"), [])


# =======================================================================================
# B. Preferred option (ADR-0032 section 10)
# =======================================================================================

class PreferredOption(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()

    def guidance(self, **overrides):
        output = self.f.build(**overrides).as_dict()
        self.assertEqual(errors(output), [])
        return output["body"]["guidance"]

    def assertNoPreference(self, reason, **overrides):
        guidance = self.guidance(**overrides)
        self.assertIsNone(guidance["preferred_option"])
        self.assertIsNone(guidance["preference_basis"])
        self.assertEqual(guidance["no_preference_reason"], reason)

    def test_all_conditions_hold(self):
        self.assertIsNotNone(self.guidance()["preferred_option"])

    def test_not_requested(self):
        self.assertNoPreference(D.NO_PREFERENCE_REQUESTED, preferred_option=None,
                                preference_criteria=None)

    def test_no_criteria(self):
        tradeoffs = [dict(t, criteria=[]) for t in self.f.request()["tradeoffs"]]
        self.assertNoPreference(D.NO_PREFERENCE_CRITERIA, criteria=[], tradeoffs=tradeoffs,
                                preference_criteria=None)

    def test_basis_not_named(self):
        self.assertNoPreference(D.NO_PREFERENCE_BASIS, preference_criteria=[])

    def test_a_user_option_or_the_status_quo_has_no_record(self):
        self.assertNoPreference(D.NO_PREFERENCE_RECORD, preferred_option=HOLD)
        self.assertNoPreference(D.NO_PREFERENCE_RECORD, preferred_option=QUO)

    def test_the_record_evidence_is_not_related_to_the_criterion(self):
        request = self.f.request()
        request["tradeoffs"][0]["evidence"] = ids([self.f.parts["growth"]])
        self.assertNoPreference(D.NO_PREFERENCE_UNRELATED, tradeoffs=request["tradeoffs"])
        request = self.f.request()
        request["tradeoffs"][0]["criteria"] = []
        self.assertNoPreference(D.NO_PREFERENCE_UNRELATED, tradeoffs=request["tradeoffs"])

    def test_another_option_is_unassessed(self):
        tradeoffs = self.f.request()["tradeoffs"][:1]
        self.assertNoPreference(D.NO_PREFERENCE_UNASSESSED, tradeoffs=tradeoffs)

    def test_another_option_labelled_not_assessable_satisfies_the_condition(self):
        tradeoffs = self.f.request()["tradeoffs"][:1]
        guidance = self.guidance(tradeoffs=tradeoffs, not_assessable=[
            {"option": QUO, "reason": "The data holds no view of an unchanged price list."}])
        self.assertIsNotNone(guidance["preferred_option"])

    # -- the contract's four conditions, checked over the basis as a whole (remediation) --------

    def two_criteria(self, **overrides):
        """Two criteria named as the basis; every tradeoff names only the first."""
        fields = dict(criteria=[CRITERION, SECOND], preference_criteria=[CRITERION, SECOND])
        fields.update(overrides)
        return fields

    def test_a_preference_needs_no_tradeoff_per_criterion(self):
        request = self.f.request(**self.two_criteria())
        for tradeoff in request["tradeoffs"]:
            self.assertEqual(tradeoff["criteria"], [CRITERION])
        output = self.f.build(**self.two_criteria()).as_dict()
        self.assertEqual(errors(output), [])
        body = output["body"]
        guidance = body["guidance"]
        options = dict((o["label"], o["option_id"]) for o in body["options"])
        criteria = dict((c["text"], c["criterion_id"]) for c in body["criteria"])
        self.assertEqual(guidance["preferred_option"], options[self.f.rec])
        self.assertEqual(guidance["preference_basis"], {
            "recommendation_id": self.f.record["recommendation_id"],
            "criterion_ids": [criteria[CRITERION], criteria[SECOND]]})
        self.assertIsNone(guidance["no_preference_reason"])
        named = set()
        for tradeoff in body["tradeoffs"]:
            named.update(tradeoff["criterion_ids"])
        self.assertNotIn(criteria[SECOND], named)
        for key in all_keys(output):
            self.assertIsNone(re.search(r"score|weight|rank|priorit|matrix", key, re.I), key)

    def test_one_comparative_tradeoff_can_assess_every_option(self):
        p = self.f.parts
        tradeoffs = [{"options": [HOLD, self.f.rec, QUO], "criteria": [CRITERION],
                      "text": "Only repricing acts on the gross margin decline directly.",
                      "evidence": ids([p["margin"]])}]
        guidance = self.guidance(tradeoffs=tradeoffs, **self.two_criteria())
        self.assertIsNotNone(guidance["preferred_option"])

    def test_two_criteria_but_no_criteria_stated_is_still_null(self):
        tradeoffs = [dict(t, criteria=[]) for t in self.f.request()["tradeoffs"]]
        self.assertNoPreference(D.NO_PREFERENCE_CRITERIA, criteria=[], tradeoffs=tradeoffs,
                                preference_criteria=None)

    def test_two_criteria_without_a_qualifying_recommendation_is_null(self):
        self.assertNoPreference(D.NO_PREFERENCE_RECORD, **self.two_criteria(
            preferred_option=HOLD))
        request = self.f.request()
        request["tradeoffs"][0]["evidence"] = ids([self.f.parts["growth"]])
        self.assertNoPreference(D.NO_PREFERENCE_UNRELATED, **self.two_criteria(
            tradeoffs=request["tradeoffs"]))

    def test_another_option_assessed_on_different_criteria_only_is_null(self):
        request = self.f.request()
        request["tradeoffs"][1]["criteria"] = [SECOND]
        self.assertNoPreference(D.NO_PREFERENCE_UNASSESSED, **self.two_criteria(
            tradeoffs=request["tradeoffs"]))
        request["tradeoffs"][1]["criteria"] = []
        self.assertNoPreference(D.NO_PREFERENCE_UNASSESSED, **self.two_criteria(
            tradeoffs=request["tradeoffs"]))
        guidance = self.guidance(**self.two_criteria(
            tradeoffs=request["tradeoffs"][:1],
            not_assessable=[{"option": QUO, "reason": "No view of an unchanged price list."}]))
        self.assertIsNotNone(guidance["preferred_option"])

    def test_two_criteria_with_a_missing_basis_is_null(self):
        self.assertNoPreference(D.NO_PREFERENCE_BASIS, **self.two_criteria(
            preference_criteria=[]))
        self.assertNoPreference(D.NO_PREFERENCE_BASIS, **self.two_criteria(
            preference_criteria=None))

    def test_the_preference_uses_a_basis_criterion_not_any_criterion(self):
        tradeoffs = [dict(t, criteria=[SECOND]) for t in self.f.request()["tradeoffs"]]
        self.assertNoPreference(D.NO_PREFERENCE_UNRELATED, criteria=[CRITERION, SECOND],
                                preference_criteria=[CRITERION], tradeoffs=tradeoffs)

    def test_malformed_preference_requests_are_refused(self):
        for overrides in ({"preferred_option": "An option nobody offered"},
                          {"preferred_option": [self.f.rec, HOLD]},
                          {"preference_criteria": ["A criterion nobody stated"]},
                          {"preferred_option": None, "preference_criteria": [CRITERION]}):
            with self.assertRaises(D.DecisionSupportError, msg=overrides):
                self.f.build(**overrides)

    def test_the_preference_carries_its_record_confidence_and_nothing_is_ordered(self):
        result = self.f.build()
        body = result.as_dict()["body"]
        self.assertIn("carrying that record's confidence %s" % self.f.record["confidence"],
                      D.render(result))
        self.assertEqual([o["origin"] for o in body["options"]],
                         ["user", "recommendation", "status_quo"])


# =======================================================================================
# C. Confidence and uncertainty
# =======================================================================================

class Confidence(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()
        p = cls.f.parts
        request = cls.f.request(options=[HOLD, "Exit the Legacy Crates line"])
        request["tradeoffs"][0]["assumptions"] = ids([p["assumed"]])
        request["risks"].append({"option": QUO, "text": "Competitors may keep cutting prices."})
        cls.result = D.build(cls.f.synthesis, request, cls.f.strategy)
        cls.body = cls.result.as_dict()["body"]
        cls.labels = dict((o["option_id"], o["label"]) for o in cls.body["options"])

    def by_label(self, label):
        return [o for o in self.body["uncertainty"]["options"]
                if self.labels[o["option_id"]] == label][0]

    def test_an_unevidenced_risk_is_low_for_insufficient_evidence(self):
        risk = [r for r in self.body["risks"] if not r["evidence"]][0]
        self.assertEqual(risk["confidence"], S.LOW)
        self.assertEqual(risk["confidence_reasons"], [conf_mod.INSUFFICIENT_EVIDENCE])

    def test_an_assumption_dependent_tradeoff_is_low(self):
        tradeoff = [t for t in self.body["tradeoffs"] if t["assumption_ids"]][0]
        self.assertEqual(tradeoff["confidence"], S.LOW)
        assumption = self.body["assumptions"][0]
        self.assertEqual(assumption["synthesis_id"], self.f.parts["assumed"].id)
        self.assertEqual(assumption["referenced_by"], [tradeoff["tradeoff_id"]])
        self.assertNotIn(self.f.parts["assumed"].id,
                         [d["synthesis_id"] for d in self.body["evidence"]])

    def test_an_option_nothing_assesses_is_low(self):
        entry = self.by_label("Exit the Legacy Crates line")
        self.assertEqual(entry["confidence"], S.LOW)
        self.assertEqual(entry["confidence_reasons"], [conf_mod.INSUFFICIENT_EVIDENCE])

    def test_confidence_is_combine_over_what_is_cited(self):
        p = self.f.parts
        outcome = self.body["expected_outcomes"][0]
        expected = conf_mod.combine([conf_mod.assess(p["margin"].confidence_detail["reasons"])])
        self.assertEqual(outcome["confidence"], expected.level)
        self.assertEqual(outcome["confidence_reasons"], list(expected.reasons))

    def test_option_and_package_confidence_are_derived(self):
        levels = [conf_mod.assess(o["confidence_reasons"])
                  for o in self.body["uncertainty"]["options"]]
        records = [conf_mod.assess(r["confidence_reasons"])
                   for r in self.body["guidance"]["recommendations"]]
        expected = conf_mod.combine(levels + records)
        self.assertEqual(self.body["uncertainty"]["confidence"], expected.level)
        self.assertEqual(self.body["uncertainty"]["confidence_reasons"], list(expected.reasons))


class ConflictsAndNextSteps(unittest.TestCase):
    """Conflicts are carried whole; next steps address only what the package carries."""

    @classmethod
    def setUpClass(cls):
        retrieval = F.close_market()
        item_ids = [item.id for item in retrieval["evidence_set"].items]
        declared = [{"subject": "UK chilled storage demand direction",
                     "positions": [{"evidence_id": item_ids[0], "value": 4, "unit": "%",
                                    "definition": "capacity demand growth"},
                                   {"evidence_id": item_ids[1], "value": -2, "unit": "%",
                                    "definition": "capacity demand growth"}]}]
        cls.synthesis = F.add_internal(F.strict_set())
        cls.demand, cls.price, _capacity = F.add_external(
            cls.synthesis, retrieval=F.close_market(conflicts=declared))
        cls.conflict = cls.synthesis.conflicts[0]

    def request(self, **overrides):
        request = {"decision_question": "Should we add chilled storage capacity?",
                   "options": ["Add capacity"],
                   "tradeoffs": [{"options": ["Add capacity", QUO],
                                  "text": "Reported demand rose, but the sources disagree.",
                                  "evidence": [self.demand.id]}]}
        request.update(overrides)
        return request

    def test_a_contested_tradeoff_is_low_and_the_conflict_is_carried(self):
        body = D.build(self.synthesis, self.request()).as_dict()["body"]
        self.assertEqual(body["tradeoffs"][0]["confidence"], S.LOW)
        self.assertIn(conf_mod.UNRESOLVED_CONFLICT, body["tradeoffs"][0]["confidence_reasons"])
        carried = body["uncertainty"]["conflicts"]
        self.assertEqual([c["conflict_id"] for c in carried], [self.conflict.id])
        self.assertTrue(carried[0]["unresolved"])
        self.assertNotIn("resolution", carried[0])

    def test_a_next_step_addressing_the_conflict_is_accepted(self):
        step = {"text": "Obtain a second demand source to test the disagreement.",
                "addresses": {"kind": "conflict", "ref": self.conflict.id}}
        body = D.build(self.synthesis, self.request(next_steps=[step])).as_dict()["body"]
        self.assertEqual(body["uncertainty"]["next_steps"], [step])
        codes = [l["code"] for l in body["uncertainty"]["limitations"]]
        self.assertIn(lim_mod.UNRESOLVED_CONFLICT, codes)
        limitation = codes[0]
        step = {"text": "Close this gap.", "addresses": {"kind": "limitation", "ref": limitation}}
        D.build(self.synthesis, self.request(next_steps=[step]))

    def test_a_next_step_addressing_nothing_the_package_carries_is_refused(self):
        for addresses in ({"kind": "conflict", "ref": "cf-000000000000"},
                          {"kind": "limitation", "ref": "not.a.code"},
                          {"kind": "unresolved_dimension", "ref": "sy-000000000000:period"},
                          {"kind": "action", "ref": self.conflict.id},
                          {"kind": "conflict", "ref": self.conflict.id, "owner": "CFO"}):
            with self.assertRaises(D.DecisionSupportError, msg=addresses):
                D.build(self.synthesis, self.request(next_steps=[
                    {"text": "Look again.", "addresses": addresses}]))
        with self.assertRaises(D.DecisionSupportError):
            D.build(self.synthesis, self.request(next_steps=[
                {"text": "Look again.", "addresses": {"kind": "conflict",
                                                      "ref": self.conflict.id},
                 "due": "2026-10-01"}]))


class InterpretationAndMateriality(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()

    def test_an_interpretation_is_cited_with_its_verified_supports(self):
        p = self.f.parts
        body = self.f.build(expected_outcomes=[{
            "option": self.f.rec, "text": "Repricing responds to the competing price pressure.",
            "evidence": ids([p["pressure"]])}]).as_dict()["body"]
        detail = [d for d in body["evidence"] if d["synthesis_id"] == p["pressure"].id][0]
        self.assertEqual(detail["kind"], S.INTERPRETATION)
        self.assertEqual(sorted(s["synthesis_id"] for s in detail["supports"]),
                         sorted([p["margin"].id, p["price"].id]))

    def test_materiality_is_inherited_and_uncited_material_statements_listed(self):
        output = self.f.build().as_dict()
        margin = [d for d in output["body"]["evidence"]
                  if d["synthesis_id"] == self.f.parts["margin"].id][0]
        self.assertTrue(margin["material"])
        material = [item.id for item in self.f.synthesis.material()]
        self.assertEqual(output["material_not_cited"],
                         [i for i in material if i not in
                          [d["synthesis_id"] for d in output["body"]["evidence"]]])

    def test_a_configured_threshold_becomes_a_criterion_with_its_layer(self):
        body = self.f.build(config=config_mod.resolve(),
                            materiality_criteria=["percentage"]).as_dict()["body"]
        criterion = body["criteria"][-1]
        self.assertEqual(criterion["origin"], "configuration")
        self.assertEqual(criterion["source"], "materiality.percentage (default layer)")
        resolved = config_mod.resolve(command_args={"materiality": {"percentage": 7}})
        body = self.f.build(config=resolved, materiality_criteria=["percentage"]).as_dict()["body"]
        self.assertEqual(body["criteria"][-1]["source"], "materiality.percentage (command layer)")
        self.assertIn("7", body["criteria"][-1]["text"])

    def test_a_tradeoff_may_quote_the_threshold_it_references(self):
        resolved = config_mod.resolve()
        criterion = "Materiality threshold percentage: %s" % resolved.get("materiality.percentage")
        request = self.f.request(materiality_criteria=["percentage"])
        request["tradeoffs"][0]["criteria"] = [criterion]
        request["tradeoffs"][0]["text"] = ("The gross margin decline exceeds the %s threshold "
                                           "the user asked to apply."
                                           % resolved.get("materiality.percentage"))
        D.build(self.f.synthesis, request, self.f.strategy, config=resolved)
        request["tradeoffs"][0]["criteria"] = []
        with self.assertRaises(D.DecisionSupportError):
            D.build(self.f.synthesis, request, self.f.strategy, config=resolved)

    def test_a_threshold_is_never_typed_in_by_the_caller(self):
        with self.assertRaises(D.DecisionSupportError):
            self.f.build(materiality_criteria=["percentage"])
        with self.assertRaises(D.DecisionSupportError):
            self.f.build(config=config_mod.resolve(), materiality_criteria=["weight"])
        with self.assertRaises(D.DecisionSupportError):
            self.f.build(config={"materiality": {"percentage": 1}},
                         materiality_criteria=["percentage"])


class Divergences(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()
        p = cls.f.parts
        cls.proposal = F.proposal([p["demand"]], action="Assess reported demand before repricing.",
                                  rationale="Demand for capacity increased during 2025.",
                                  expected_benefit="A pricing decision that reflects demand.")
        cls.own = strategy.recommendation_id(cls.proposal["action"], cls.proposal["evidence"])

    def build(self, note, rec_ids=None):
        rec_ids = rec_ids or [self.f.record["recommendation_id"], self.own]
        return self.f.build(recommendations=[self.proposal], preferred_option=None,
                            preference_criteria=None,
                            divergences=[{"recommendations": rec_ids, "note": note}])

    def test_a_divergence_names_both_records_and_neither_wins(self):
        output = self.build("One record reviews pricing; the other assesses demand first.").as_dict()
        guidance = output["body"]["guidance"]
        self.assertEqual([r["issued_by"] for r in guidance["recommendations"]],
                         [strategy.ISSUED_BY, strategy.DECISION_SUPPORT_ISSUER])
        self.assertEqual(guidance["divergences"][0]["recommendation_ids"],
                         [self.f.record["recommendation_id"], self.own])
        self.assertEqual(errors(output), [])

    def test_a_note_quoting_a_figure_the_records_state_is_accepted(self):
        self.build("One record rests on the move from 37.26% to 34.41%; the other on demand.")

    def test_malformed_divergences_are_refused(self):
        for note, rec_ids in (("Margin fell by 3%.", None),
                              ("One record only.", [self.own]),
                              ("Unknown record.", [self.own, "rec-000000000000"])):
            with self.assertRaises(D.DecisionSupportError, msg=note):
                self.build(note, rec_ids)

    def test_the_same_record_twice_in_guidance_is_refused(self):
        with self.assertRaises(D.DecisionSupportError):
            self.f.build(recommendations=[F.proposal([self.f.parts["margin"]])])


# =======================================================================================
# D. Fail closed and security
# =======================================================================================

class FailClosed(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()
        cls.before = cls.f.synthesis.to_json()

    def refused(self, contains=None, strategy_result="bound", **overrides):
        with self.assertRaises(D.DecisionSupportError) as caught:
            self.f.build(strategy_result=strategy_result, **overrides)
        if contains:
            self.assertIn(contains, str(caught.exception))
        self.assertEqual(self.f.synthesis.to_json(), self.before)

    def tradeoff(self, **fields):
        request = self.f.request()
        request["tradeoffs"][0].update(fields)
        return request["tradeoffs"]

    def without_status_quo_tradeoff(self):
        """The tradeoffs minus the status quo's, so the status quo may be labelled unassessable."""
        return self.f.request()["tradeoffs"][:1]

    # -- question and options ------------------------------------------------------

    def test_a_missing_blank_or_non_string_question_is_refused(self):
        request = self.f.request()
        del request["decision_question"]
        with self.assertRaises(D.DecisionSupportError):
            D.build(self.f.synthesis, request, self.f.strategy)
        for question in (None, "", "   ", "\n\t", 42, ["Should we reprice?"],
                         {"text": "Should we reprice?"}):
            self.refused(decision_question=question)

    def test_a_multi_sentence_question_is_kept_exactly(self):
        question = ("Should we reprice the lines behind the margin decline? Or should we hold "
                    "prices this year? We need to decide before the next catalogue.")
        self.assertGreater(question.count("?"), 1)
        output = self.f.build(decision_question=question).as_dict()
        self.assertEqual(output["body"]["decision_question"], {"text": question, "origin": "user"})
        self.assertEqual(errors(output), [])
        self.assertIn(question, D.render(self.f.build(decision_question=question)))

    def test_the_engine_does_not_judge_question_meaning(self):
        body = code(DS_PY)
        self.assertNotIn('count("?")', body)
        self.assertNotIn("isalpha", body)

    def test_fewer_than_two_options_is_refused(self):
        self.refused(contains="at least two options", strategy_result=None, options=[],
                     include_status_quo=False, tradeoffs=[], risks=[], expected_outcomes=[],
                     preferred_option=None, preference_criteria=None)
        self.refused(strategy_result=None, options=[HOLD], include_status_quo=False,
                     tradeoffs=[], risks=[], expected_outcomes=[], preferred_option=None,
                     preference_criteria=None)

    def test_duplicate_or_malformed_options_are_refused(self):
        self.refused(options=[HOLD, HOLD])
        self.refused(options=[QUO])
        self.refused(options=[""])
        self.refused(options=HOLD)
        self.refused(include_status_quo="yes")

    def test_a_package_citing_no_evidence_is_refused(self):
        self.refused(contains="cites no evidence", strategy_result=None, tradeoffs=[],
                     risks=[], expected_outcomes=[], preferred_option=None,
                     preference_criteria=None)

    # -- evidence ----------------------------------------------------------------------

    def test_fake_malformed_and_out_of_set_ids_are_refused(self):
        other = F.strict_set()
        demand, _price, _capacity = F.add_external(other)
        foreign = F.add_internal(F.strict_set(), domains=("financial",))
        for evidence in (["sy-000000000000"], ["not-an-id"], [42], "sy-000000000000", []):
            self.refused(tradeoffs=self.tradeoff(evidence=evidence))
        with self.assertRaises(D.DecisionSupportError):
            D.build(foreign, {"decision_question": QUESTION, "options": [HOLD],
                              "expected_outcomes": [{"option": HOLD, "text": "Demand rose.",
                                                     "evidence": [demand.id]}]})

    def test_an_ambiguous_id_is_refused(self):
        synthesis = F.strict_set()
        for _ in range(2):
            C.internal_statements(synthesis, F.shared_run(), S.ORIGIN_FINANCIAL, F.DATASET_ID,
                                  domains=["financial"])
        margin = [i for i in synthesis.items if i.statement.startswith(F.MARGIN_DECLINE)][0]
        with self.assertRaises(D.DecisionSupportError) as caught:
            D.build(synthesis, {"decision_question": QUESTION, "options": [HOLD],
                                "expected_outcomes": [{"option": HOLD, "text": "Margin fell.",
                                                       "evidence": [margin.id]}]})
        self.assertIn("identifies 2 statements", str(caught.exception))

    def test_duplicate_evidence_is_refused(self):
        margin = self.f.parts["margin"].id
        self.refused(contains="twice", tradeoffs=self.tradeoff(evidence=[margin, margin]))
        self.refused(risks=[{"option": HOLD, "text": "Costs may rise.",
                             "evidence": [margin, margin]}])

    def test_a_recommendation_or_assumption_is_never_evidence(self):
        self.refused(tradeoffs=self.tradeoff(evidence=[self.f.record["recommendation_id"]]))
        self.refused(contains="assumption",
                     tradeoffs=self.tradeoff(evidence=ids([self.f.parts["assumed"]])))
        self.refused(tradeoffs=self.tradeoff(assumptions=ids([self.f.parts["margin"]])))

    def test_metadata_and_business_context_are_never_evidence(self):
        margin = self.f.synthesis.items[0]
        for reference in (F.DEMAND_DOC, "business_context", "identity.business_name",
                          "Northwind demo", margin.provenance[0].ref_id,
                          self.f.parts["demand"].provenance[0].ref_id):
            self.refused(tradeoffs=self.tradeoff(evidence=[reference]))

    def test_tradeoffs_and_outcomes_need_evidence(self):
        self.refused(tradeoffs=self.tradeoff(evidence=[]))
        request = self.f.request()
        del request["tradeoffs"][0]["evidence"]
        self.refused(tradeoffs=request["tradeoffs"])
        self.refused(expected_outcomes=[{"option": HOLD, "text": "Costs fall.", "evidence": []}])

    def test_unknown_options_and_criteria_are_refused(self):
        self.refused(tradeoffs=self.tradeoff(options=["Somebody else's option"]))
        self.refused(tradeoffs=self.tradeoff(options=[]))
        self.refused(tradeoffs=self.tradeoff(criteria=["An unstated criterion"]))
        self.refused(risks=[{"option": "Nobody's", "text": "Risky."}])

    def test_an_option_cannot_be_both_assessed_and_not_assessable(self):
        self.refused(not_assessable=[{"option": HOLD, "reason": "No cost data."}])
        self.f.build(not_assessable=[{"option": QUO, "reason": "No data."}],
                     tradeoffs=self.without_status_quo_tradeoff())
        self.refused(not_assessable=[{"option": QUO, "reason": ""}],
                     tradeoffs=self.without_status_quo_tradeoff())
        self.refused(not_assessable=[{"option": QUO, "reason": "No data."}] * 2,
                     tradeoffs=self.without_status_quo_tradeoff())

    # -- strategy result -----------------------------------------------------------------

    def test_an_invalid_or_mismatched_strategy_result_is_refused(self):
        self.refused(contains="StrategyResult", strategy_result=self.f.strategy.as_dict())
        other = Fixture()
        self.refused(contains="not bound", strategy_result=other.strategy)

    def test_a_strategy_result_over_a_since_changed_set_is_refused(self):
        f = Fixture()
        S.assumption(f.synthesis, S.ORIGIN_FINANCIAL, "Volumes are assumed stable.",
                     "No volume forecast exists.")
        with self.assertRaises(D.DecisionSupportError):
            f.build()

    def test_a_non_genuine_set_is_refused(self):
        for synthesis in (self.f.synthesis.as_dict(), S.SynthesisSet(subject="loose"), None):
            with self.assertRaises(D.DecisionSupportError):
                D.build(synthesis, self.f.request())

    # -- authored conclusions ------------------------------------------------------------

    def test_caller_conclusions_are_refused_at_every_level(self):
        forbidden = ("confidence", "confidence_reasons", "lifecycle", "trust", "verification",
                     "support", "score", "rank", "weight", "priority", "severity",
                     "likelihood")
        for field in forbidden:
            self.refused(**{field: "HIGH"})
            self.refused(tradeoffs=self.tradeoff(**{field: "HIGH"}))
            self.refused(risks=[{"option": HOLD, "text": "Costs may rise.", field: 1}])
            self.refused(expected_outcomes=[{"option": self.f.rec, "text": "Margin holds.",
                                             "evidence": ids([self.f.parts["margin"]]),
                                             field: 1}])
            self.refused(strategy_result=None, preferred_option=None, preference_criteria=None,
                         recommendations=[dict(F.proposal([self.f.parts["demand"]],
                                                          action="Assess demand."),
                                               **{field: 1})])
            self.refused(not_assessable=[{"option": QUO, "reason": "No data.", field: 1}],
                         tradeoffs=self.without_status_quo_tradeoff())
            self.refused(options=[{"label": HOLD, field: 1}])

    def test_a_lifecycle_cannot_be_set_to_final(self):
        self.refused(lifecycle=D.FINAL)
        result = self.f.build()
        with self.assertRaises(AttributeError):
            result.lifecycle = D.FINAL
        self.assertFalse(D.PRODUCES_FINAL)
        body = code(DS_PY)
        self.assertEqual(len(re.findall(r"\bFINAL\b", body)), 3, "FINAL defined, listed, exported")
        schema = load_schema()
        self.assertEqual(schema["properties"]["lifecycle"]["enum"], ["draft", "final"])

    def test_a_package_cannot_be_constructed_outside_build(self):
        with self.assertRaises(D.DecisionSupportError):
            D.DecisionResult(self.f.synthesis, None, "sha256:" + "0" * 64, {}, [])

    def test_a_package_refuses_to_serialise_once_its_set_changes(self):
        f = Fixture()
        result = f.build()
        S.assumption(f.synthesis, S.ORIGIN_FINANCIAL, "Volumes are assumed stable.",
                     "No volume forecast exists.")
        for call in (result.as_dict, result.claims, result.to_json):
            with self.assertRaises(D.DecisionSupportError):
                call()

    # -- figures -------------------------------------------------------------------------

    def test_figures_must_be_printed_by_cited_evidence(self):
        margin = ids([self.f.parts["margin"]])
        for text in ("Repricing restores margin to 38%.",          # unsupported
                     "The margin fell by 2.85pp.",                  # sign altered
                     "The margin fell to 34.4%.",                   # rounded
                     "The margin fell to 34%.",                     # rounded
                     "The margin fell by five percent.",            # number word
                     "The margin fell by twenty-five basis points.",
                     u"The margin fell to ٣٤.٤١%.",   # non-ASCII numeral
                     u"The margin fell to ３４.４１%."):
            self.refused(tradeoffs=self.tradeoff(text=text, evidence=margin))
            self.refused(expected_outcomes=[{"option": self.f.rec, "text": text,
                                             "evidence": margin}])
            self.refused(risks=[{"option": self.f.rec, "text": text, "evidence": margin}])

    def test_the_exact_printed_figure_and_sign_are_accepted(self):
        margin = ids([self.f.parts["margin"]])
        self.f.build(tradeoffs=self.tradeoff(
            text="The margin moved from 37.26% to 34.41%, a change of -2.85pp.",
            evidence=margin))

    def test_an_unevidenced_risk_may_state_no_figure(self):
        self.refused(risks=[{"option": QUO, "text": "Competitors may cut prices by 5%."}])
        self.refused(risks=[{"option": QUO, "text": "Competitors may cut prices in 2027."}])
        self.refused(not_assessable=[{"option": QUO, "reason": "No data for 3 lines."}],
                     tradeoffs=self.without_status_quo_tradeoff())

    def test_a_next_step_may_not_introduce_a_figure(self):
        labelled = dict(not_assessable=[{"option": QUO, "reason": "No data."}],
                        tradeoffs=self.without_status_quo_tradeoff())
        addresses = {"kind": "limitation", "ref": D.NOT_ASSESSABLE}
        self.f.build(next_steps=[{"text": "Collect cost data.", "addresses": addresses}],
                     **labelled)
        for text in ("Collect cost data for 12 months.", "Collect cost data for twelve months."):
            self.refused(next_steps=[{"text": text, "addresses": addresses}], **labelled)


class NumberWords(unittest.TestCase):
    """The figure rule M10.3.3 extended: a cardinal written in words is a figure."""

    def test_number_words_are_tokens(self):
        self.assertEqual(strategy.figure_tokens("five percent"), [("number_word", "five")])
        self.assertEqual(strategy.figure_tokens("Twenty-five sites"),
                         [("number_word", "twenty five")])
        self.assertEqual(strategy.figure_tokens("one hundred and five crates"),
                         [("number_word", "one hundred five")])
        self.assertEqual(strategy.figure_tokens("two and three"),
                         [("number_word", "two"), ("number_word", "three")])
        self.assertEqual(strategy.figure_tokens("millions of customers"),
                         [("number_word", "millions")])

    def test_ordinary_words_are_not_figures(self):
        for text in ("one of the options", "no one knows", "about half", "roughly double",
                     "a few lines", "USD 3.47 million", "often attends tent sites"):
            self.assertFalse([t for t in strategy.figure_tokens(text) if t[0] == "number_word"],
                             text)

    def test_a_number_word_the_evidence_prints_is_accepted(self):
        strategy.require_grounded("rationale", "Three operators launched.",
                                  ["Three operators launched services in 2025."], [])
        with self.assertRaises(strategy.StrategyError):
            strategy.require_grounded("rationale", "Four operators launched.",
                                      ["Three operators launched services in 2025."], [])
        with self.assertRaises(strategy.StrategyError):
            strategy.require_grounded("rationale", "Three operators launched.",
                                      ["3 operators launched services in 2025."], [])

    def test_a_number_phrase_matches_only_the_same_phrase(self):
        strategy.require_grounded("rationale", "Twenty-five sites opened.",
                                  ["Twenty five sites opened in 2025."], [])
        for text, printed in (("Twenty-one sites opened.", "Twenty-three sites opened."),
                              ("Twenty sites opened.", "Twenty-three sites opened."),
                              ("Five sites opened.", "Twenty-five sites opened."),
                              ("One hundred sites opened.", "Two hundred sites opened."),
                              ("Two thousand pallets were added.",
                               "Two stores and a thousand pallets were added.")):
            with self.assertRaises(strategy.StrategyError, msg=text):
                strategy.require_grounded("rationale", text, [printed], [])


class AntiReentry(unittest.TestCase):
    """A decision package and its parts never re-enter synthesis (ADR-0032 constraint 7)."""

    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()
        p = cls.f.parts
        cls.result = cls.f.build(
            recommendations=[F.proposal([p["demand"]], action="Assess reported demand.")],
            next_steps=[])
        cls.output = cls.result.as_dict()

    def test_register_claims_refuses_the_package_and_every_part(self):
        body = self.output["body"]
        variants = [self.output, body, body["decision_question"], body["objective"],
                    body["business_context"]["constraints"][0], body["options"][0],
                    body["options"][-1], body["criteria"][0], body["tradeoffs"][0],
                    body["risks"][0], body["expected_outcomes"][0], body["guidance"],
                    body["guidance"]["recommendations"][-1], body["uncertainty"],
                    {"recommendation_ids": ["rec-000000000000", "rec-111111111111"],
                     "note": "x"},
                    {"text": "x", "addresses": {"kind": "limitation", "ref": "y"}},
                    dict(body["uncertainty"]["options"][0], statement="x"),
                    {"statement": "x", "analysis": "Decision_Support"},
                    {"statement": "x", "lifecycle": "draft"},
                    {"statement": "x", "referenced_by": ["trd-000000000000"]}]
        variants += [claim.as_dict() for claim in self.result.claims()]
        for variant in variants:
            synthesis = F.strict_set()
            with self.assertRaises(sc.SynthesisError, msg=str(variant)[:120]):
                synthesis.register_claims([variant])
            self.assertEqual(synthesis.candidate_claims, [])

    def test_a_genuine_candidate_claim_is_still_accepted(self):
        registered = F.strict_set().register_claims([{"statement": "A source said x.",
                                                      "evidence_id": "ev-1", "class": 3,
                                                      "label": "SOURCED"}])
        self.assertEqual(len(registered), 1)

    def test_the_set_holds_no_package_or_record(self):
        self.assertEqual(self.f.synthesis.recommendations, [])
        self.assertNotIn("decision_support", self.f.synthesis.to_json())

    def test_the_engine_has_no_path_into_synthesis_authoring(self):
        body = code(DS_PY)
        for call in ("interpretation(", "sourced_statement(", "register_claims(",
                     "register_external(", "synthesis.add(", "assumption(",
                     "footed_statement(", "from_analysis_set(", "local_join(",
                     "add_conflict(", ".limit(", "._items"):
            self.assertNotIn(call, body, call)

    def test_the_engine_reads_no_file_and_reaches_no_network_or_analysis(self):
        body = code(DS_PY)
        for token in ("open(", "urllib", "socket", "http", "subprocess", "open_retrieval",
                      "close_retrieval", "scout", "gate", "commands", "pipeline", "ingest",
                      "requests", "smtp", "webhook"):
            self.assertNotIn(token, body, token)
        self.assertFalse(D.EXECUTES_ACTIONS)


class Output(unittest.TestCase):
    """Nothing scored, ranked, weighted or executed; the schema is closed."""

    @classmethod
    def setUpClass(cls):
        cls.f = Fixture()
        cls.output = cls.f.build().as_dict()
        cls.schema = load_schema()

    def test_no_score_rank_weight_priority_or_execution_key_at_any_depth(self):
        forbidden = re.compile(r"rank|score|priorit|weight|winner|best|top_|severity|"
                               r"likelihood|execut|owner|due", re.I)
        self.assertEqual(sorted(k for k in all_keys(self.output) if forbidden.search(k)), [])

    def test_the_schema_refuses_added_conclusions(self):
        cases = [((), "score"), ((), "priority"), (("body",), "ranking"),
                 (("body", "options", 0), "weight"), (("body", "options", 0), "confidence"),
                 (("body", "criteria", 0), "weight"), (("body", "tradeoffs", 0), "score"),
                 (("body", "risks", 0), "severity"), (("body", "risks", 0), "likelihood"),
                 (("body", "expected_outcomes", 0), "estimated_value"),
                 (("body", "guidance"), "ranking"),
                 (("body", "uncertainty", "options", 0), "rank")]
        for path, key in cases:
            document = copy.deepcopy(self.output)
            node = document
            for step in path:
                node = node[step]
            node[key] = 1
            self.assertTrue(jsonschema_mini.validate(document, self.schema), (path, key))

    def test_the_schema_refuses_invalid_lifecycle_refs_and_shapes(self):
        for mutate in (lambda d: d.__setitem__("lifecycle", "approved"),
                       lambda d: d.__setitem__("verification", "verified"),
                       lambda d: d["body"]["options"][0].__setitem__("option_id", "option-1"),
                       lambda d: d["body"]["options"][0].__setitem__("origin", "model"),
                       lambda d: d["body"]["tradeoffs"][0].__setitem__("evidence", []),
                       lambda d: d["body"]["tradeoffs"][0].__setitem__("evidence", ["x"]),
                       lambda d: d["body"]["options"].__delitem__(slice(1, None)),
                       lambda d: d["body"]["guidance"].__setitem__("no_preference_reason", "x"),
                       lambda d: d["body"]["decision_question"].__setitem__("origin", "data"),
                       lambda d: d["body"].__delitem__("uncertainty")):
            document = copy.deepcopy(self.output)
            mutate(document)
            self.assertTrue(jsonschema_mini.validate(document, self.schema))

    def test_the_request_definition_is_closed(self):
        request = self.f.request()
        self.assertEqual(errors(request, "request"), [])
        for field in ("confidence", "lifecycle", "trust", "score", "rank", "weight", "priority"):
            self.assertTrue(errors(dict(request, **{field: 1}), "request"), field)
        tradeoff = dict(request["tradeoffs"][0], weight=2)
        self.assertTrue(errors(dict(request, tradeoffs=[tradeoff]), "request"))
        self.assertEqual(sorted(self.schema["definitions"]["request"]["properties"]),
                         sorted(D.REQUEST_FIELDS))

    def test_mirrored_definitions_are_pinned_to_strategy(self):
        mine = self.schema["definitions"]
        theirs = load_schema(STRATEGY_SCHEMA)["definitions"]
        for name in ("synthesis_id", "text", "level", "confidence_assessment",
                     "evidence_detail", "limitation"):
            self.assertEqual(mine[name], theirs[name], name)
        record = copy.deepcopy(mine["recommendation"])
        self.assertEqual(record["properties"].pop("issued_by"),
                         {"enum": [strategy.ISSUED_BY, strategy.DECISION_SUPPORT_ISSUER]})
        strategy_record = copy.deepcopy(theirs["recommendation"])
        strategy_record["properties"].pop("issued_by")
        self.assertEqual(record, strategy_record)
        self.assertEqual(list(strategy.RECOMMENDATION_ISSUERS),
                         [strategy.ISSUED_BY, strategy.DECISION_SUPPORT_ISSUER])


# =======================================================================================
# E. Command-level flow, context and trust
# =======================================================================================

class CommandLevelFlow(unittest.TestCase):
    """`/decision-support` end to end: real runner, real reply, local join, Strategy optional."""

    @classmethod
    def setUpClass(cls):
        cls.brief = F.open_market_brief()
        cls.command_run = C.run("business-health", source=F.DEMO)
        cls.joined = F.join()
        cls.synthesis = cls.joined.synthesis
        F.add_internal(cls.synthesis, run=cls.command_run, domains=("sales", "product"))
        cls.demand, cls.price, cls.capacity = F.add_external(cls.synthesis)
        legacy = F.find(cls.synthesis, F.LEGACY_DECLINE, S.ORIGIN_PRODUCT)
        cls.reading = S.interpretation(
            cls.synthesis, S.ORIGIN_PRODUCT,
            "The Legacy Crates line declined while a competing operator introduced a "
            "lower-priced chilled storage service.", supports=[legacy.id, cls.price.id])
        cls.strategy = strategy.build(cls.synthesis, [F.proposal(
            [cls.reading], action="Review whether the Legacy Crates line still fits the range.",
            rationale="The line declined while a lower-priced competing service arrived.",
            expected_benefit="A range decision grounded in the line's own trend.")])
        cls.rec = cls.strategy.recommendations[0]["action"]
        cls.before = cls.synthesis.to_json()
        cls.result = D.build(cls.synthesis, {
            "decision_question": "Should we keep the Legacy Crates line?",
            "options": ["Keep the line unchanged in the range"],
            "include_status_quo": False,
            "criteria": ["Fit with the range"],
            "tradeoffs": [{"options": [cls.rec, "Keep the line unchanged in the range"],
                           "criteria": ["Fit with the range"],
                           "text": "Reviewing responds to the decline and the lower-priced "
                                   "competing service; keeping the line leaves both unaddressed.",
                           "evidence": [cls.reading.id]}],
            "expected_outcomes": [{"option": cls.rec,
                                   "text": "A range view that reflects 3,500 new chilled pallet "
                                           "positions reported in 2025.",
                                   "evidence": [cls.capacity.id, cls.reading.id]}],
            "preferred_option": cls.rec,
            "preference_criteria": ["Fit with the range"],
        }, strategy_result=cls.strategy, config=config_mod.resolve())
        cls.output = cls.result.as_dict()

    def test_the_path_used_the_real_seams(self):
        self.assertEqual(self.brief["status"], R.AUTHORISED)
        self.assertIs(type(self.command_run), C.CommandResult)
        self.assertIs(type(self.joined), C.LocalJoin)
        self.assertTrue(self.synthesis.require_dimension_provenance)

    def test_the_package_is_valid_preferred_and_untouched(self):
        self.assertEqual(errors(self.output), [])
        self.assertIsNotNone(self.output["body"]["guidance"]["preferred_option"])
        self.assertEqual(self.synthesis.to_json(), self.before)

    def test_external_evidence_stays_untrusted_and_keeps_its_provenance(self):
        details = dict((d["synthesis_id"], d) for d in self.output["body"]["evidence"])
        capacity = details[self.capacity.id]
        self.assertEqual(capacity["trust"], "untrusted")
        self.assertEqual(capacity["domain"], "external")
        self.assertEqual(capacity["kind"], S.SOURCED)
        self.assertEqual(capacity["evidence_class"], self.capacity.evidence_class)
        self.assertIn("untrusted data", self.output["trust_statement"])

    def test_nothing_internal_or_framing_reached_the_query(self):
        query = json.dumps(self.brief)
        self.assertNotIn(str(self.joined.internal.observed), query)
        for framing in ("Legacy Crates", "Should we keep", "Fit with the range"):
            self.assertNotIn(framing, query)

    def test_render_uses_the_package_only(self):
        rendered = D.render(self.result)
        self.assertIn("# Decision support", rendered)
        self.assertIn(self.rec, rendered)


class BusinessContextFraming(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(F.DEMO_CONTEXT, encoding="utf-8") as handle:
            cls.context = context_mod.resolve(overrides=json.load(handle), load_files=False)
        cls.name = cls.context.get("identity.business_name")
        cls.f = Fixture(subject=cls.name,
                        business_model=cls.context.get("identity.business_model"),
                        currency=cls.context.get("reporting.currency"))

    def test_context_frames_the_package_and_is_never_evidence(self):
        output = self.f.build().as_dict()
        context = output["body"]["business_context"]
        self.assertEqual(context["subject"], self.name)
        self.assertEqual(context["business_model"], "retail")
        self.assertTrue(D.render(self.f.build()).startswith("# Decision support — %s" % self.name))
        self.assertNotIn(self.name, json.dumps(output["body"]["evidence"]))

    def test_context_cannot_be_cited_or_introduce_a_figure(self):
        request = self.f.request()
        for reference in ("identity.business_name", self.name):
            request["tradeoffs"][0]["evidence"] = [reference]
            with self.assertRaises(D.DecisionSupportError):
                D.build(self.f.synthesis, request, self.f.strategy)
        threshold = str(self.context.get("analysis.materiality.absolute_amount"))
        request = self.f.request()
        request["tradeoffs"][0]["text"] = "Movements above %s are material here." % threshold
        with self.assertRaises(D.DecisionSupportError):
            D.build(self.f.synthesis, request, self.f.strategy)


# =======================================================================================
# F. Skill, command, registry
# =======================================================================================

class SkillAndCommand(unittest.TestCase):

    def test_the_skill_is_discoverable_with_supported_frontmatter(self):
        block = F.frontmatter(read(SKILL_MD))
        self.assertTrue(re.search(r"^name:\s*bops-decision-support\s*$", block, re.M))
        declared = set(re.findall(r"^([a-zA-Z-]+):", block, re.M))
        self.assertTrue(declared <= {"name", "description", "argument-hint",
                                     "user-invocable"}, declared)

    def test_the_command_is_thin_and_names_the_skill(self):
        text = read(COMMAND_MD)
        declared = set(re.findall(r"^([a-zA-Z-]+):", F.frontmatter(text), re.M))
        self.assertTrue(declared <= {"description", "argument-hint", "allowed-tools",
                                     "disable-model-invocation",
                                     "hide-from-slash-command-tool"}, declared)
        self.assertIn("`bops-decision-support`", text)
        self.assertIn("This command sequences", text)
        self.assertIn("**None required to run.**", text)
        body = text.split("---", 2)[2]
        for engine_rule in ("confidence.combine", "require_grounded", "grounding.one"):
            self.assertNotIn(engine_rule, body)

    def test_both_state_the_contract_and_the_boundary(self):
        skill = " ".join(read(SKILL_MD).split())
        for token in ("decision_support.build(", "draft", "never evidence",
                      "Figures are quoted, never produced", "financial transactions are prohibited",
                      "Only the verifier finalises", "not** ordered"):
            self.assertIn(token, skill, token)
        for field in D.REQUEST_FIELDS:
            self.assertIn('"%s"' % field, skill, field)
        command = " ".join(read(COMMAND_MD).split()).lower()
        self.assertIn("nothing internal is sent as a fallback", command)
        self.assertIn("financial transactions are prohibited", command)
        self.assertIn("never part of any query", command)

    def test_decision_support_does_not_depend_on_executive_report(self):
        """Amended by the Executive Report implementation: the report assembles packages; the
        package engine knows nothing about the report."""
        skills = set(os.listdir(os.path.join(REPO_ROOT, "skills")))
        commands = {n[:-3] for n in os.listdir(os.path.join(REPO_ROOT, "commands"))}
        self.assertIn("bops-decision-support", skills)
        self.assertIn("decision-support", commands)
        self.assertIn("bops-executive-report", skills)
        self.assertIn("executive-report", commands)
        self.assertNotIn("executive", code(DS_PY).lower())


if __name__ == "__main__":                                   # pragma: no cover
    unittest.main()
