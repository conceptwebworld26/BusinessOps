# -*- coding: utf-8 -*-
"""Executive Report: an assembly of existing artifacts over one synthesis set (ADR-0033).

`bops.executive_report` is the engine, `bops-executive-report` the skill and `/executive-report` the
command. These tests pin the contract ADR-0033 decided, over genuine inputs: `commands.run()` over the
shipped synthetic demo file (analytics, KPIs and the anomaly engine), genuine `BOPS-REC/1` replies closed
through `research.close_retrieval_object()`, and the existing synthesis translators, SWOT, Strategy and
Decision Support engines. Fixtures are imported from the Strategy and Decision Support suites rather than
copied, so all four consumers are tested over one definition of the evidence.

What gets the most attention:

* **Assembly, never authorship.** Every statement, record and package part equals its source.
* **Binding.** Components must be bound to the same set object; mutation refuses serialisation.
* **Fail closed.** Every refusal raises `ExecutiveReportError`; an invalid optional input is never dropped.
* **Draft only, no score, no target, no recommendation, no re-entry, no forecast bypass.**

**Every fixture is synthetic.** Nothing reaches a network or dispatches a scout.
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
from bops import decision_support as D                      # noqa: E402
from bops import executive_report as E                      # noqa: E402
from bops import jsonschema_mini                            # noqa: E402
from bops import research as R                              # noqa: E402
from bops import strategy                                   # noqa: E402
from bops import swot as swot_mod                           # noqa: E402
from bops import synthesis as S                             # noqa: E402
from bops.forecast import contract as forecast_contract     # noqa: E402
from bops.kpi import catalog as kpi_catalog                 # noqa: E402
from bops.synthesis import contract as sc                   # noqa: E402
from bops.synthesis import grounding                        # noqa: E402
from bops.synthesis import limitations as lim_mod           # noqa: E402
from unit import test_m10_3_2_strategy as F                # noqa: E402
from unit import test_m10_3_3_decision_support as T        # noqa: E402

LIB = os.path.join(REPO_ROOT, "lib", "python", "bops")
ER_PY = os.path.join(LIB, "executive_report.py")
SCHEMAS = os.path.join(REPO_ROOT, "lib", "schemas")
ER_SCHEMA = os.path.join(SCHEMAS, "executive_report.schema.json")
SKILL_MD = os.path.join(REPO_ROOT, "skills", "bops-executive-report", "SKILL.md")
COMMAND_MD = os.path.join(REPO_ROOT, "commands", "executive-report.md")

FRAMING = {"reporting_period": "FY2025 against FY2024", "audience": "Board of directors",
           "objective": "Decide where to act on the margin decline.",
           "questions": ["Where is gross margin going?", "Is demand still rising?"],
           "constraints": ["No price change before the next catalogue."]}

read = F.read
code = F.code
all_keys = F.all_keys

_ANOMALY_RUN = {}


def anomaly_run():
    if "run" not in _ANOMALY_RUN:
        _ANOMALY_RUN["run"] = C.run("anomaly-detection", source=F.DEMO)
    return _ANOMALY_RUN["run"]


def load_schema(path=ER_SCHEMA):
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def schema_errors(document):
    return jsonschema_mini.validate(json.loads(json.dumps(document, default=str)), load_schema())


def refused(test, call, contains=None):
    with test.assertRaises(E.ExecutiveReportError) as caught:
        call()
    if contains:
        test.assertIn(contains, str(caught.exception))
    return caught.exception


class World(object):
    """One mixed strict set with KPIs and anomalies, and a Strategy result, SWOT and package over it."""

    def __init__(self, kpis=True, anomalies=True, **fields):
        self.f = T.Fixture(**fields)
        self.synthesis, self.parts = self.f.synthesis, self.f.parts
        if kpis:
            for _kpi_id, result in sorted(F.shared_run().kpis.items()):
                S.from_kpi_result(self.synthesis, result, dataset_id=F.DATASET_ID)
        if anomalies:
            C.internal_statements(self.synthesis, anomaly_run(), S.ORIGIN_ANOMALY, F.DATASET_ID)
        self.strategy = strategy.build(self.synthesis, [
            F.proposal([self.parts["margin"]]),
            F.proposal([self.parts["demand"]], action="Assess reported demand before repricing.",
                       rationale="Demand for capacity increased during 2025.",
                       expected_benefit="A pricing decision that reflects demand.")])
        self.f.strategy = self.strategy
        self.f.record = self.strategy.recommendations[0]
        self.f.rec = self.f.record["action"]
        self.package = self.make_package()
        self.swot = swot_mod.build(self.synthesis, [
            {"quadrant": "strengths", "tag": "data-supported",
             "synthesis_id": self.parts["growth"].id},
            {"quadrant": "weaknesses", "tag": "data-supported",
             "synthesis_id": self.parts["margin"].id},
            {"quadrant": "opportunities", "tag": "externally-sourced",
             "synthesis_id": self.parts["demand"].id},
            {"quadrant": "threats", "tag": "analytical-inference",
             "synthesis_id": self.parts["pressure"].id}])

    def make_package(self):
        """The decision package over this set; the same inputs give an identical package."""
        return self.f.build(not_assessable=[{
            "option": self.strategy.recommendations[1]["action"],
            "reason": "No evidence relates demand-first sequencing to gross margin."}])

    def build(self, request=None, **components):
        return E.build(self.synthesis, FRAMING if request is None else request, **components)

    def full(self, **overrides):
        components = dict(strategy_result=self.strategy, swot=self.swot,
                          decision_results=[self.package], config=config_mod.resolve())
        components.update(overrides)
        return self.build(**components)


def minimal_set():
    return F.add_internal(F.strict_set())


# =======================================================================================
# A. Happy paths
# =======================================================================================

class MinimalReport(unittest.TestCase):
    """A genuine strict set and an empty request is a valid report."""

    @classmethod
    def setUpClass(cls):
        cls.synthesis = minimal_set()
        cls.before = cls.synthesis.to_json()
        cls.result = E.build(cls.synthesis, {})
        cls.output = cls.result.as_dict()

    def test_all_eleven_sections_are_present_in_order(self):
        self.assertEqual(E.SECTION_ORDER, (
            "reporting_frame", "executive_summary", "kpi_scorecard", "findings", "anomalies",
            "outlook", "swot", "strategy_recommendations", "decision_support",
            "evidence_and_uncertainty", "decisions_for_the_reader"))
        self.assertEqual(self.output["section_order"], list(E.SECTION_ORDER))
        self.assertEqual(list(self.output["sections"]), list(E.SECTION_ORDER))
        serialised = self.result.to_json()
        positions = [serialised.index('"%s": {"status"' % n) for n in E.SECTION_ORDER]
        self.assertEqual(positions, sorted(positions))

    def test_empty_states_are_explicit(self):
        sections = self.output["sections"]
        self.assertEqual({n: sections[n]["status"] for n in E.SECTION_ORDER}, {
            "reporting_frame": "included", "executive_summary": "included",
            "kpi_scorecard": "not_available", "findings": "included",
            "anomalies": "not_available", "outlook": "not_available", "swot": "not_supplied",
            "strategy_recommendations": "not_supplied", "decision_support": "not_supplied",
            "evidence_and_uncertainty": "included", "decisions_for_the_reader": "included"})
        for name in E.SECTION_ORDER:
            if sections[name]["status"] != E.INCLUDED:
                self.assertTrue(sections[name]["reason"], name)

    def test_draft_schema_valid_and_identified(self):
        self.assertEqual(schema_errors(self.output), [])
        self.assertEqual(self.output["lifecycle"], "draft")
        self.assertEqual(self.output["verification"], "unverified")
        self.assertRegex(self.output["report_id"], r"^rpt-[0-9a-f]{12}$")
        self.assertEqual(self.output["human_decision"], E.HUMAN_DECISION)
        self.assertEqual(self.output["synthesis_digest"],
                         strategy.synthesis_digest(self.synthesis))

    def test_nothing_is_written_to_the_set(self):
        self.assertEqual(self.synthesis.to_json(), self.before)
        self.assertEqual(self.synthesis.recommendations, [])
        self.assertEqual(self.synthesis.candidate_claims, [])

    def test_render_states_draft_and_every_section(self):
        rendered = E.render(self.result)
        self.assertIn("**Lifecycle:** draft — unverified", rendered)
        self.assertIn(E.HUMAN_DECISION, rendered)
        for number, name in enumerate(E.SECTION_ORDER, start=1):
            self.assertIn("## %d. " % number, rendered, name)


class FullReport(unittest.TestCase):
    """All optional artifacts together, and each alone."""

    @classmethod
    def setUpClass(cls):
        cls.w = World()
        cls.before = cls.w.synthesis.to_json()
        cls.result = cls.w.full()
        cls.output = cls.result.as_dict()
        cls.sections = cls.output["sections"]

    def test_every_section_is_included_except_outlook(self):
        for name in E.SECTION_ORDER:
            expected = E.NOT_AVAILABLE if name == E.OUTLOOK else E.INCLUDED
            self.assertEqual(self.sections[name]["status"], expected, name)
        self.assertEqual(schema_errors(self.output), [])

    def test_each_optional_artifact_alone_is_valid(self):
        for components in ({"strategy_result": self.w.strategy}, {"swot": self.w.swot},
                           {"decision_results": [self.w.package]}):
            output = self.w.build(**components).as_dict()
            self.assertEqual(schema_errors(output), [], components)

    def test_sources_bind_every_component(self):
        sources = self.output["sources"]
        self.assertTrue(sources["strategy"]["included"])
        self.assertEqual(sources["strategy"]["recommendation_ids"],
                         [r["recommendation_id"] for r in self.w.strategy.recommendations])
        self.assertEqual(sources["strategy"]["synthesis_digest"], self.output["synthesis_digest"])
        self.assertTrue(sources["swot"]["included"])
        self.assertEqual(sources["swot"]["digest"],
                         "sha256:" + __import__("hashlib").sha256(
                             swot_mod.to_json(self.w.swot).encode("utf-8")).hexdigest())
        self.assertEqual(len(sources["decision_packages"]), 1)
        self.assertEqual(sources["decision_packages"][0]["decision_question"], T.QUESTION)

    def test_deterministic_and_repeatable(self):
        again = self.w.full()
        self.assertEqual(again.to_json(), self.result.to_json())
        self.assertEqual(again.report_id, self.result.report_id)
        self.assertEqual(E.render(again), E.render(self.result))
        self.assertEqual(self.result.to_json(), self.result.to_json())

    def test_report_id_is_content_addressed(self):
        other = self.w.full(swot=None)
        self.assertNotEqual(other.report_id, self.result.report_id)
        reframed = self.w.build(dict(FRAMING, audience="Operating committee"),
                                strategy_result=self.w.strategy, swot=self.w.swot,
                                decision_results=[self.w.package], config=config_mod.resolve())
        self.assertNotEqual(reframed.report_id, self.result.report_id)

    def test_the_set_is_untouched(self):
        self.assertEqual(self.w.synthesis.to_json(), self.before)
        self.assertEqual(self.w.synthesis.recommendations, [])


# =======================================================================================
# B. Sections
# =======================================================================================

class Sections(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.w = World()
        cls.result = cls.w.full()
        cls.output = cls.result.as_dict()
        cls.sections = cls.output["sections"]
        index = grounding.index(cls.w.synthesis)
        cls.readable = []
        for position, item in enumerate(cls.w.synthesis.items):
            try:
                grounding.evidence_domains(index, position, item)
            except grounding.GroundingError:
                continue
            cls.readable.append(item)

    # -- reporting frame -----------------------------------------------------------------

    def test_reporting_frame_preserves_framing_verbatim(self):
        frame = self.sections["reporting_frame"]
        for name in E.TEXT_FIELDS:
            self.assertEqual(frame["framing"][name],
                             {"text": FRAMING[name], "origin": "user", "stated": True})
        for name in E.LIST_FIELDS:
            self.assertEqual(frame["framing"][name],
                             [{"text": t, "origin": "user"} for t in FRAMING[name]])
        self.assertEqual(frame["datasets"][0]["id"], F.DATASET_ID)
        self.assertEqual(frame["external_evidence"][0]["subject"], F.MARKET_SUBJECT)
        self.assertEqual(frame["materiality_thresholds"][1],
                         {"key": "materiality.percentage", "value": "5.0",
                          "source": "default layer"})

    def test_absent_framing_is_not_stated_never_inferred(self):
        frame = self.w.build({}).as_dict()["sections"]["reporting_frame"]
        for name in E.TEXT_FIELDS:
            self.assertEqual(frame["framing"][name], {"text": None, "origin": None,
                                                      "stated": False})
        self.assertEqual(frame["framing"]["questions"], [])
        self.assertEqual(frame["materiality_thresholds"], [])

    def test_a_quality_warning_precedes_the_figures(self):
        w = World(kpis=False, anomalies=False, quality_grade="WARNING")
        result = w.build({})
        frame = result.as_dict()["sections"]["reporting_frame"]
        self.assertEqual(frame["quality_warning"], E.QUALITY_WARNING)
        rendered = E.render(result)
        self.assertLess(rendered.index("Data quality"), rendered.index("## 2. Executive summary"))

    # -- executive summary ------------------------------------------------------------------

    def test_summary_lists_every_readable_material_statement_in_set_order(self):
        summary = self.sections["executive_summary"]
        expected = [item.id for item in self.readable if item.is_material]
        self.assertTrue(expected)
        self.assertEqual([e["statement_detail"]["synthesis_id"] for e in summary["material_statements"]],
                         expected)
        by_id = dict((item.id, item) for item in self.w.synthesis.items)
        for entry in summary["material_statements"]:
            item = by_id[entry["statement_detail"]["synthesis_id"]]
            self.assertEqual(entry["statement_detail"]["statement"], item.statement)
            self.assertEqual(entry["statement_detail"]["confidence"], item.confidence)
            self.assertEqual(entry["statement_detail"]["materiality"], item.as_dict()["materiality"])
            self.assertNotEqual(item.kind, sc.ASSUMPTION)

    def test_summary_counts_and_standing(self):
        summary = self.sections["executive_summary"]
        self.assertEqual(summary["materiality_not_assessed"],
                         len([i for i in self.w.synthesis.items if not i.materiality]))
        self.assertEqual(summary["synthesis_confidence"],
                         self.w.synthesis.confidence().as_dict())
        self.assertEqual(summary["conflict_count"], len(self.w.synthesis.conflicts))
        self.assertEqual(summary["limitation_count"], len(self.w.synthesis.limitations))

    def test_summary_states_the_availability_of_sections_3_and_5_to_9(self):
        """ADR-0033 section 4, item 7: copied from each section's own status, in section order."""
        expected_names = ["kpi_scorecard", "anomalies", "outlook", "swot",
                          "strategy_recommendations", "decision_support"]
        self.assertEqual(list(E.AVAILABILITY_SECTIONS), expected_names)
        minimal_output = E.build(minimal_set(), {}).as_dict()
        for output in (self.output, minimal_output):
            availability = output["sections"]["executive_summary"]["availability"]
            self.assertEqual(availability, [
                {"section": name, "status": output["sections"][name]["status"]}
                for name in expected_names])
            self.assertEqual(schema_errors(output), [])
        minimal = minimal_output["sections"]["executive_summary"]
        self.assertEqual([a["status"] for a in minimal["availability"]],
                         ["not_available", "not_available", "not_available", "not_supplied",
                          "not_supplied", "not_supplied"])
        self.assertIn("- Availability: KPI scorecard included · Anomalies included · Outlook "
                      "not available", E.render(self.result))

    def test_summary_references_records_and_packages_without_changing_them(self):
        summary = self.sections["executive_summary"]
        self.assertEqual(summary["recommendations"], [
            {"recommendation_id": r["recommendation_id"], "issued_by": r["issued_by"],
             "action": r["action"], "confidence": r["confidence"]}
            for r in self.w.strategy.recommendations])
        decision = summary["decisions"][0]
        guidance = self.w.package.as_dict()["body"]["guidance"]
        self.assertEqual(decision["decision_question"], T.QUESTION)
        self.assertEqual(decision["preferred_option"]["option_id"], guidance["preferred_option"])
        self.assertEqual(decision["preference_basis"], guidance["preference_basis"])
        self.assertEqual(decision["lifecycle_label"], "draft — unverified")

    def test_material_statements_the_evidence_does_not_support_are_listed_not_hidden(self):
        synthesis = F.strict_set()
        F.add_internal(synthesis, domains=("financial",))
        evidence = S.evidence_from_retrieval(F.close_market(records=[F.CAPACITY]))
        S.register_external(synthesis, evidence, S.ORIGIN_MARKET)
        weak = S.sourced_statement(synthesis, S.ORIGIN_MARKET, F.CAPACITY_TEXT,
                                   evidence_ids=[evidence.items[0].id],
                                   materiality={"outcome": "material", "reason": "test",
                                                "basis": "fixture"})
        self.assertEqual(weak.support, sc.UNSUPPORTED)
        output = E.build(synthesis, {}).as_dict()
        summary = output["sections"]["executive_summary"]
        self.assertEqual(summary["material_not_supported"], [weak.id])
        self.assertNotIn(weak.id, [e["statement_detail"]["synthesis_id"]
                                   for e in summary["material_statements"]])
        not_supported = output["sections"]["evidence_and_uncertainty"]["not_supported"]
        self.assertEqual([d["synthesis_id"] for d in not_supported], [weak.id])
        self.assertTrue(not_supported[0]["reason"])

    # -- KPI scorecard ---------------------------------------------------------------------

    def test_kpi_rows_follow_the_catalogue_and_carry_status(self):
        rows = self.sections["kpi_scorecard"]["rows"]
        catalogue = [d.kpi_id for d in kpi_catalog.CATALOGUE]
        ids = [row["kpi_id"] for row in rows]
        self.assertEqual(ids, [k for k in catalogue if k in set(ids)])
        self.assertEqual(set(ids), set(F.shared_run().kpis))
        for row in rows:
            result = F.shared_run().kpis[row["kpi_id"]]
            self.assertEqual(row["status"], result.status)
            if result.available:
                self.assertEqual(row["value"], str(result.value))
                self.assertIsNone(row["reason"])
                self.assertEqual(len(row["statements"]), 1)
                detail = row["statements"][0]["statement_detail"]
                statement = [i for i in self.w.synthesis.items if i.id == detail["synthesis_id"]][0]
                self.assertEqual(detail["confidence"], statement.confidence)
                self.assertEqual(row["statements"][0]["prior"],
                                 None if statement.comparison is None else str(statement.comparison))
            else:
                self.assertIsNone(row["value"])
                self.assertEqual(row["reason"], result.reason)
                self.assertEqual(row["statements"], [])

    def test_no_target_rating_or_score_exists(self):
        forbidden = re.compile(r"target|rating|score|rank|weight|priorit|severity|likelihood|"
                               r"health|colou?r|traffic|best|top_|winner", re.I)
        self.assertEqual(sorted(k for k in all_keys(self.sections) if forbidden.search(k)
                                and k != "kpi_scorecard"), [])

    # -- findings ---------------------------------------------------------------------------

    def test_findings_follow_set_order_evidence_then_interpretations(self):
        findings = self.sections["findings"]
        held = (S.ORIGIN_KPI, S.ORIGIN_ANOMALY, S.ORIGIN_FORECAST)
        expected_evidence = [i.id for i in self.readable
                             if i.origin not in held and i.kind != sc.INTERPRETATION]
        expected_readings = [i.id for i in self.readable
                             if i.origin not in held and i.kind == sc.INTERPRETATION]
        self.assertEqual([e["statement_detail"]["synthesis_id"] for e in findings["evidence"]],
                         expected_evidence)
        self.assertEqual([e["statement_detail"]["synthesis_id"] for e in findings["interpretations"]],
                         expected_readings)
        for entry in findings["interpretations"]:
            self.assertEqual(entry["label"], "interpretation")
            self.assertTrue(entry["statement_detail"]["supports"])

    # -- anomalies -----------------------------------------------------------------------------

    def test_anomalies_carry_the_investigation_note_and_their_finding(self):
        anomalies = self.sections["anomalies"]
        expected = [i.id for i in self.readable if i.origin == S.ORIGIN_ANOMALY]
        self.assertTrue(expected)
        self.assertEqual([e["statement_detail"]["synthesis_id"] for e in anomalies["statements"]], expected)
        from bops.anomaly import contract as anomaly_contract
        for entry in anomalies["statements"]:
            self.assertIn(anomaly_contract.INVESTIGATION_NOTE, entry["caveats"])
            self.assertTrue(entry["anomaly"]["analysis_id"].startswith("anomaly."))
        text = json.dumps(anomalies).lower().replace(
            json.dumps(anomaly_contract.INVESTIGATION_NOTE).lower()[1:-1], "")
        for word in ("fraud", "theft", "misstatement", "wrongdoing"):
            self.assertNotIn(word, text)

    def test_anomalies_show_observed_baseline_and_deviation_from_the_finding(self):
        """ADR-0033 section 6: resolved from the registered finding, never computed here."""
        findings = dict((f.analysis_id, f) for f in anomaly_run().anomaly_set.findings)

        def plain(value):
            return None if value is None else str(value)
        for entry in self.sections["anomalies"]["statements"]:
            anomaly = entry["anomaly"]
            finding = findings[anomaly["analysis_id"]]
            self.assertEqual(
                (anomaly["metric"], anomaly["period"], anomaly["observed"], anomaly["baseline"],
                 anomaly["deviation"], anomaly["deviation_pct"], anomaly["unit"],
                 anomaly["currency"], anomaly["basis"]),
                (finding.metric, plain(finding.period), plain(finding.observed),
                 plain(finding.comparison), plain(finding.change), plain(finding.change_pct),
                 finding.unit, finding.currency, finding.basis))
            self.assertIsNotNone(anomaly["observed"])
            self.assertIsNotNone(anomaly["baseline"])
            # The statement the engine wrote already prints those figures; nothing is added.
            self.assertIn(entry["statement_detail"]["statement"],
                          [f.statement for f in findings.values()])

    # -- outlook ---------------------------------------------------------------------------------

    def test_outlook_is_not_available(self):
        outlook = self.sections["outlook"]
        self.assertEqual(outlook, {"status": "not_available", "reason": E.REASON_NO_FORECAST,
                                   "statements": []})

    # -- SWOT, strategy, decision support --------------------------------------------------------

    def test_swot_is_preserved_whole(self):
        self.assertEqual(self.sections["swot"]["result"], self.w.swot)
        self.assertEqual(self.w.build(swot=None).as_dict()["sections"]["swot"]["status"],
                         "not_supplied")

    def test_an_empty_swot_is_empty_not_missing(self):
        empty = swot_mod.build(self.w.synthesis, [])
        section = self.w.build(swot=empty).as_dict()["sections"]["swot"]
        self.assertEqual(section["status"], "empty")
        self.assertEqual(section["result"], empty)

    def test_strategy_is_preserved_whole_in_its_own_order(self):
        section = self.sections["strategy_recommendations"]
        self.assertEqual(section["result"], self.w.strategy.as_dict())
        self.assertEqual([r["recommendation_id"] for r in section["result"]["recommendations"]],
                         [r["recommendation_id"] for r in self.w.strategy.recommendations])

    def test_a_strategy_result_with_no_records_is_empty(self):
        none = strategy.build(self.w.synthesis, [])
        section = self.w.build(strategy_result=none).as_dict()["sections"][
            "strategy_recommendations"]
        self.assertEqual(section["status"], "empty")
        self.assertEqual(section["result"]["empty_state"], strategy.EMPTY_STATE)

    def test_decision_packages_are_preserved_whole_and_labelled(self):
        section = self.sections["decision_support"]
        entry = section["packages"][0]
        self.assertEqual(entry["package"], self.w.package.as_dict())
        self.assertEqual(entry["lifecycle_label"], "draft — unverified")
        self.assertEqual(list(entry["package"]["body"]), list(D.PART_ORDER))

    # -- evidence and uncertainty ---------------------------------------------------------------

    def test_evidence_and_uncertainty_is_carried_whole_and_labelled(self):
        section = self.sections["evidence_and_uncertainty"]
        self.assertEqual(section["synthesis_confidence"], self.w.synthesis.confidence().as_dict())
        self.assertEqual(section["conflicts"], [c.as_dict() for c in self.w.synthesis.conflicts])
        self.assertEqual(section["limitations"], lim_mod.as_dicts(self.w.synthesis.limitations))
        self.assertEqual([a["synthesis_id"] for a in section["assumptions"]],
                         [i.id for i in self.w.synthesis.items if i.kind == sc.ASSUMPTION])
        components = [c["component"] for c in section["component_confidence"]]
        self.assertEqual(components, ["strategy_recommendations", "decision_package"])
        package = self.w.package.as_dict()["body"]["uncertainty"]
        self.assertEqual(section["component_confidence"][1]["confidence"],
                         {"confidence": package["confidence"],
                          "reasons": package["confidence_reasons"]})
        self.assertIn("kpi.unavailable", [l["code"] for l in section["limitations"]])

    # -- decisions for the reader ----------------------------------------------------------------

    def test_decisions_for_the_reader_decide_nothing_and_execute_nothing(self):
        section = self.sections["decisions_for_the_reader"]
        self.assertEqual(section["human_decision"], E.HUMAN_DECISION)
        self.assertEqual(section["no_decision_recorded"], E.NO_DECISION_RECORDED)
        self.assertEqual(section["recommendations_awaiting_decision"],
                         [r["recommendation_id"] for r in self.w.strategy.recommendations])
        forbidden = re.compile(r"owner|due|deadline|assign|execut|approv|action_plan|sent|"
                               r"transaction|decided|decision_made", re.I)
        self.assertEqual(sorted(k for k in all_keys(section) if forbidden.search(k)), [])
        for word in ("approved", "has been decided", "was sent", "executed"):
            self.assertNotIn(word, json.dumps(section).lower().replace("recorded no approval", ""))

    def test_next_steps_are_references_to_package_content(self):
        w = World(kpis=False, anomalies=False)
        step = {"text": "Gather evidence on demand-first sequencing.",
                "addresses": {"kind": "limitation", "ref": D.NOT_ASSESSABLE}}
        package = w.f.build(next_steps=[step], not_assessable=[{
            "option": w.strategy.recommendations[1]["action"],
            "reason": "No evidence relates demand-first sequencing to gross margin."}])
        result = w.build({}, strategy_result=w.strategy, decision_results=[package])
        section = result.as_dict()["sections"]["decisions_for_the_reader"]
        digest = result.as_dict()["sources"]["decision_packages"][0]["digest"]
        self.assertEqual(section["next_steps"], [{"package_digest": digest, "index": 0,
                                                  "text": step["text"],
                                                  "addresses": step["addresses"]}])
        self.assertEqual(package.as_dict()["body"]["uncertainty"]["next_steps"], [step])


# =======================================================================================
# C. Fail closed and security
# =======================================================================================

class FailClosed(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.w = World(kpis=False, anomalies=False)
        cls.before = cls.w.synthesis.to_json()

    def tearDown(self):
        self.assertEqual(self.w.synthesis.to_json(), self.before)

    # -- the set ----------------------------------------------------------------------------------

    def test_missing_non_strict_serialised_or_empty_sets_are_refused(self):
        loose = S.SynthesisSet(subject="loose")
        F.add_internal(loose)
        for synthesis in (None, self.w.synthesis.as_dict(), loose, F.strict_set(),
                          json.loads(self.w.synthesis.to_json())):
            refused(self, lambda s=synthesis: E.build(s, {}))

    def test_a_critical_set_is_refused(self):
        synthesis = F.add_internal(F.strict_set(quality_grade="CRITICAL"))
        refused(self, lambda: E.build(synthesis, {}), contains="CRITICAL")

    def test_an_ambiguous_statement_id_is_refused(self):
        synthesis = F.strict_set()
        for _ in range(2):
            C.internal_statements(synthesis, F.shared_run(), S.ORIGIN_FINANCIAL, F.DATASET_ID,
                                  domains=["financial"])
        refused(self, lambda: E.build(synthesis, {}), contains="identifies 2 statements")

    # -- the request ---------------------------------------------------------------------------------

    def test_caller_conclusions_and_unknown_keys_are_refused(self):
        for field in ("confidence", "confidence_reasons", "trust", "verification", "verified",
                      "lifecycle", "support", "score", "rank", "weight", "priority", "severity",
                      "likelihood", "target", "report_id", "sections", "summary", "forecast",
                      "kpis", "anomalies", "evidence", "materiality"):
            refused(self, lambda f=field: self.w.build(dict(FRAMING, **{f: "HIGH"})),
                    contains="is not accepted")

    def test_malformed_framing_is_refused(self):
        for request in (None, [], "FY2025", {"audience": ""}, {"audience": "  "},
                        {"objective": 42}, {"questions": "one"}, {"questions": [""]},
                        {"constraints": ["a", "a"]}, {"reporting_period": ["FY2025"]}):
            refused(self, lambda r=request: E.build(self.w.synthesis, r))

    # -- components ------------------------------------------------------------------------------

    def test_strategy_inputs_must_be_the_one_bound_result(self):
        other = World(kpis=False, anomalies=False)
        for bad in (self.w.strategy.as_dict(), [self.w.strategy, self.w.strategy],
                    other.strategy):
            refused(self, lambda b=bad: self.w.build(strategy_result=b))

    def test_decision_inputs_must_be_bound_distinct_objects(self):
        other = World(kpis=False, anomalies=False)
        rebuilt = self.w.make_package()
        self.assertIsNot(rebuilt, self.w.package)
        self.assertEqual(rebuilt.to_json(), self.w.package.to_json())
        for bad in (self.w.package, [self.w.package.as_dict()], [other.package],
                    [self.w.package, self.w.package], [self.w.package, rebuilt]):
            refused(self, lambda b=bad: self.w.build(decision_results=b))

    def test_a_package_built_with_a_different_strategy_result_is_refused(self):
        second = strategy.build(self.w.synthesis, [F.proposal([self.w.parts["margin"]])])
        refused(self, lambda: self.w.build(strategy_result=second,
                                           decision_results=[self.w.package]),
                contains="different StrategyResult")

    def test_swot_inputs_must_rebuild_exactly(self):
        edited_text = copy.deepcopy(self.w.swot)
        edited_text["quadrants"][0]["points"][0]["statement"] = "Revenue growth is 90%."
        edited_tag = copy.deepcopy(self.w.swot)
        edited_tag["quadrants"][0]["points"][0]["tag"] = "externally-sourced"
        moved = copy.deepcopy(self.w.swot)
        moved["quadrants"][1]["points"].append(moved["quadrants"][0]["points"].pop())
        dropped_conflicts = dict(self.w.swot, conflicts=[{"conflict_id": "x"}])
        fake = copy.deepcopy(self.w.swot)
        fake["quadrants"][0]["points"][0]["synthesis_id"] = "sy-000000000000"
        other = World(kpis=False, anomalies=False, subject="Another business")
        foreign = swot_mod.build(other.synthesis, [
            {"quadrant": "strengths", "tag": "data-supported",
             "synthesis_id": other.parts["growth"].id}])
        foreign_statement = copy.deepcopy(foreign)
        for bad in (edited_text, edited_tag, moved, dropped_conflicts, fake,
                    [self.w.swot], "swot", {"quadrants": "none"}, foreign_statement):
            refused(self, lambda b=bad: self.w.build(swot=b))
        external_elsewhere = F.strict_set()
        demand, _p, _c = F.add_external(external_elsewhere)
        out_of_set = copy.deepcopy(self.w.swot)
        out_of_set["quadrants"][2]["points"][0]["synthesis_id"] = "sy-%s" % ("f" * 12)
        refused(self, lambda: self.w.build(swot=out_of_set))

    def test_configuration_must_be_resolved(self):
        refused(self, lambda: self.w.build(config={"materiality": {"percentage": 1}}))

    def test_forecast_kpi_anomaly_and_command_objects_have_no_entry_point(self):
        forecast_run = C.run("revenue-forecast", source=F.DEMO)
        for keyword, value in (("forecast", forecast_run.forecast_set),
                               ("kpis", F.shared_run().kpis),
                               ("anomalies", anomaly_run().anomaly_set),
                               ("command_result", F.shared_run())):
            with self.assertRaises(TypeError):
                self.w.build(**{keyword: value})
        for bad in (forecast_run.forecast_set, F.shared_run()):
            refused(self, lambda b=bad: self.w.build(strategy_result=b))
            refused(self, lambda b=bad: self.w.build(decision_results=[b]))
            refused(self, lambda b=bad: E.build(b, {}))

    # -- binding ----------------------------------------------------------------------------------

    def test_a_result_cannot_be_constructed_outside_build(self):
        refused(self, lambda: E.ExecutiveReportResult(self.w.synthesis, "sha256:" + "0" * 64,
                                                      None, None, None, None, [], {}, [], {}))

    def test_mutating_the_set_refuses_serialisation(self):
        w = World(kpis=False, anomalies=False)
        result = w.full()
        S.assumption(w.synthesis, S.ORIGIN_FINANCIAL, "Volumes are assumed stable.",
                     "No volume forecast exists.")
        for call in (result.as_dict, result.to_json):
            refused(self, call, contains="changed after this report was built")
        self.assertFalse(result.is_bound_to(w.synthesis))

    def test_mutating_the_swot_record_refuses_serialisation(self):
        w = World(kpis=False, anomalies=False)
        record = copy.deepcopy(w.swot)
        result = w.build(swot=record)
        result.as_dict()
        record["quadrants"][0]["points"][0]["tag"] = "externally-sourced"
        refused(self, result.as_dict)

    def test_a_strategy_or_package_no_longer_bound_refuses_serialisation(self):
        for components in ({"strategy_result": "strategy"}, {"decision_results": "package"}):
            w = World(kpis=False, anomalies=False)
            name, attr = list(components.items())[0]
            value = getattr(w, attr)
            result = w.build(**{name: [value] if name == "decision_results" else value})
            w.synthesis.add_conflict(S.CrossDomainConflict(
                "numeric", "fixture conflict",
                [{"synthesis_id": w.parts["margin"].id, "value": 1},
                 {"synthesis_id": w.parts["growth"].id, "value": 2}]))
            refused(self, result.as_dict)

    def test_tampering_with_a_bound_strategy_result_refuses_serialisation(self):
        w = World(kpis=False, anomalies=False)
        result = w.build({}, strategy_result=w.strategy)
        result.as_dict()
        w.strategy._records[0]["confidence"] = "HIGH" if w.strategy._records[0][
            "confidence"] != "HIGH" else "LOW"
        refused(self, result.as_dict, contains="changed after this report was built")

    def test_tampering_with_a_bound_decision_package_refuses_serialisation(self):
        w = World(kpis=False, anomalies=False)
        result = w.build({}, decision_results=[w.package])
        result.as_dict()
        w.package._body["guidance"]["no_preference_reason"] = "Preferred by the report."
        refused(self, result.as_dict, contains="changed after this report was built")

    def test_the_report_cannot_be_set_to_final(self):
        """Amended by the M11 verification implementation (ADR-0034 section 8): the schema now
        admits `final`, but only with `verified` and a `verification_record`, which only
        `verification.finalise()` produces. `build()` still has no path to `final`."""
        result = self.w.build({})
        with self.assertRaises(AttributeError):
            result.lifecycle = E.FINAL
        self.assertFalse(E.PRODUCES_FINAL)
        self.assertEqual(result.as_dict()["lifecycle"], "draft")
        body = code(ER_PY)
        self.assertEqual(len(re.findall(r"\bFINAL\b", body)), 3, "defined, listed, exported only")
        self.assertEqual(load_schema()["properties"]["lifecycle"]["enum"], ["draft", "final"])
        document = result.as_dict()
        document["lifecycle"] = "final"
        self.assertTrue(schema_errors(document))
        document["verification"] = "verified"
        self.assertTrue(schema_errors(document), "final without a verification record")

    # -- re-entry and trust ---------------------------------------------------------------------

    def test_the_report_and_every_part_are_refused_as_candidate_claims(self):
        w = World()
        result = w.full()
        output = result.as_dict()
        sections = output["sections"]
        variants = [output, sections, dict(output, analysis="Executive_Report")]
        variants += [sections[name] for name in E.SECTION_ORDER]
        variants += [sections["executive_summary"]["material_statements"][0],
                     sections["executive_summary"]["material_statements"][0]["statement_detail"],
                     sections["executive_summary"]["decisions"][0],
                     sections["kpi_scorecard"]["rows"][0],
                     sections["findings"]["evidence"][0],
                     sections["anomalies"]["statements"][0],
                     sections["swot"]["result"],
                     sections["swot"]["result"]["quadrants"][0]["points"][0],
                     sections["decision_support"]["packages"][0],
                     sections["evidence_and_uncertainty"]["assumptions"][0],
                     sections["decisions_for_the_reader"]["decision_questions"][0],
                     {"statement": "x", "report_id": "rpt-000000000000"},
                     {"statement": "x", "synthesis_id": "sy-000000000000"},
                     {"statement": "x", "kpi_id": "revenue"},
                     {"statement": "x", "lifecycle_label": "draft — unverified"}]
        for variant in variants:
            synthesis = F.strict_set()
            with self.assertRaises(sc.SynthesisError, msg=str(variant)[:100]):
                synthesis.register_claims([variant])
            self.assertEqual(synthesis.candidate_claims, [])
        with self.assertRaises(sc.SynthesisError):
            F.strict_set().register_claims([result])
        genuine = F.strict_set().register_claims([{"statement": "A source said x.",
                                                   "evidence_id": "ev-1", "class": 3,
                                                   "label": "SOURCED"}])
        self.assertEqual(len(genuine), 1)

    def test_recommendations_assumptions_and_framing_are_never_evidence(self):
        w = World()
        output = w.full().as_dict()
        sections = output["sections"]
        evidence_ids = set()
        for entry in (sections["executive_summary"]["material_statements"]
                      + sections["findings"]["evidence"] + sections["findings"]["interpretations"]
                      + sections["anomalies"]["statements"]):
            evidence_ids.add(entry["statement_detail"]["synthesis_id"])
        for row in sections["kpi_scorecard"]["rows"]:
            evidence_ids.update(s["statement_detail"]["synthesis_id"] for s in row["statements"])
        self.assertNotIn(w.parts["assumed"].id, evidence_ids)
        for record in w.strategy.recommendations:
            self.assertNotIn(record["recommendation_id"], evidence_ids)
        evidential = json.dumps([sections[n] for n in ("executive_summary", "kpi_scorecard",
                                                        "findings", "anomalies")])
        for name in E.TEXT_FIELDS:
            self.assertNotIn(FRAMING[name], evidential)
        for text in FRAMING["questions"] + FRAMING["constraints"]:
            self.assertNotIn(text, evidential)

    def test_external_evidence_stays_untrusted(self):
        w = World(kpis=False, anomalies=False)
        output = w.build({}).as_dict()
        demand = [e for e in output["sections"]["findings"]["evidence"]
                  if e["statement_detail"]["synthesis_id"] == w.parts["demand"].id][0]
        self.assertEqual(demand["statement_detail"]["trust"], "untrusted")
        self.assertEqual(demand["statement_detail"]["kind"], "SOURCED")
        self.assertIn("untrusted data", output["trust_statement"])

    def test_the_engine_has_no_side_effects_or_upstream_bypass(self):
        body = code(ER_PY)
        for token in ("open(", "urllib", "socket", "http", "subprocess", "requests", "smtp",
                      "open_retrieval", "close_retrieval", "scout", "gate", "commands",
                      "pipeline", "ingest", "from .forecast", "from .anomaly",
                      "from .kpi import engine", "ForecastSet", "AnomalySet",
                      "register_claims(", "register_analysis(", "register_kpi(",
                      "register_external(", "register_dataset(", "synthesis.add(",
                      "interpretation(", "sourced_statement(", "assumption(", "from_kpi_result(",
                      "from_analysis_set(", "internal_statements(", "ground_recommendation(",
                      "._registry", "._items", "write("):
            self.assertNotIn(token, body, token)
        for line in body.splitlines():
            if ".add(" in line:
                self.assertIn("digests.add(", line)
        self.assertFalse(E.EXECUTES_ACTIONS)


# =======================================================================================
# D. Contract-specific
# =======================================================================================

class Contract(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.w = World(kpis=False, anomalies=False)

    def test_executive_report_issues_no_recommendations(self):
        self.assertFalse(E.ISSUES_RECOMMENDATIONS)
        self.assertNotIn(E.ISSUED_BY, strategy.RECOMMENDATION_ISSUERS)
        with self.assertRaises(strategy.StrategyError):
            strategy.ground_recommendation(self.w.synthesis, grounding.index(self.w.synthesis),
                                           F.proposal([self.w.parts["margin"]]),
                                           issued_by=E.ISSUED_BY)
        output = self.w.full().as_dict()
        issuers = set()

        def walk(node):
            if isinstance(node, dict):
                if "recommendation_id" in node and "issued_by" in node:
                    issuers.add(node["issued_by"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
        walk(output)
        self.assertTrue(issuers)
        self.assertNotIn(E.ISSUED_BY, issuers)

    def test_strategy_confidence_and_order_are_never_changed(self):
        reversed_order = strategy.build(self.w.synthesis, [
            F.proposal([self.w.parts["demand"]], action="Assess reported demand before repricing.",
                       rationale="Demand for capacity increased during 2025.",
                       expected_benefit="A pricing decision that reflects demand."),
            F.proposal([self.w.parts["margin"]])])
        shown = self.w.build({}, strategy_result=reversed_order).as_dict()
        self.assertEqual(shown["sections"]["strategy_recommendations"]["result"],
                         reversed_order.as_dict())
        self.assertEqual([r["confidence"] for r in shown["sections"]["executive_summary"][
            "recommendations"]], [r["confidence"] for r in reversed_order.recommendations])

    def test_decision_confidence_preference_and_package_order_are_never_changed(self):
        second = self.w.f.build(decision_question="Should we hold prices this year?",
                                preferred_option=None, preference_criteria=None)
        for order in ([self.w.package, second], [second, self.w.package]):
            output = self.w.build({}, strategy_result=self.w.strategy,
                                  decision_results=order).as_dict()
            packages = output["sections"]["decision_support"]["packages"]
            self.assertEqual([p["package"] for p in packages], [p.as_dict() for p in order])
            views = output["sections"]["decisions_for_the_reader"]["decision_questions"]
            self.assertEqual([v["decision_question"] for v in views],
                             [p.as_dict()["body"]["decision_question"]["text"] for p in order])
            self.assertEqual([v["no_preference_reason"] for v in views],
                             [p.as_dict()["body"]["guidance"]["no_preference_reason"]
                              for p in order])

    def test_a_future_final_package_is_shown_exactly_as_carried(self):
        record = self.w.package.as_dict()
        record["lifecycle"] = "final"
        record["verification"] = "verified"
        before = copy.deepcopy(record)
        entry = E.package_entry(record, "sha256:" + "a" * 64)
        self.assertEqual(entry["package"], before)
        self.assertEqual(record, before)
        self.assertEqual(entry["lifecycle_label"], "final — verified")
        draft = E.package_entry(self.w.package.as_dict(), "sha256:" + "a" * 64)
        self.assertEqual(draft["lifecycle_label"], "draft — unverified")

    def test_no_overall_score_or_report_confidence_exists(self):
        output = self.w.full().as_dict()
        self.assertNotIn("confidence", output)
        self.assertEqual(sorted(k for k in all_keys(output) if re.search(
            r"overall|score|health|report_confidence|rating", k, re.I)
            and k != "kpi_scorecard"), [])

    def test_mirrored_schema_definitions_are_pinned(self):
        mine = load_schema()["definitions"]
        for prefix, filename in (("strategy_", "strategy.schema.json"),
                                 ("swot_", "swot.schema.json"),
                                 ("decision_", "decision_support.schema.json")):
            theirs = load_schema(os.path.join(SCHEMAS, filename))

            def unprefix(node):
                if isinstance(node, dict):
                    return dict((k, "#/definitions/" + v[len("#/definitions/" + prefix):]
                                 if k == "$ref" else unprefix(v)) for k, v in node.items())
                if isinstance(node, list):
                    return [unprefix(v) for v in node]
                return node
            top = dict((k, v) for k, v in theirs.items()
                       if k not in ("$schema", "$id", "title", "description", "definitions"))
            self.assertEqual(unprefix(mine[prefix + "result"]), top, filename)
            for name, definition in theirs.get("definitions", {}).items():
                self.assertEqual(unprefix(mine[prefix + name]), definition, prefix + name)

    def test_the_schema_is_closed(self):
        document = self.w.full().as_dict()
        schema = load_schema()
        self.assertEqual(jsonschema_mini.validate(json.loads(json.dumps(document)), schema), [])
        mutations = [
            lambda d: d.__setitem__("score", 1),
            lambda d: d.__setitem__("confidence", "HIGH"),
            lambda d: d.__setitem__("verification", "verified"),
            lambda d: d["sections"].__setitem__("key_risks", {"status": "included"}),
            lambda d: d["sections"].pop("outlook"),
            lambda d: d.__setitem__("section_order", list(reversed(d["section_order"]))),
            lambda d: d["sections"]["kpi_scorecard"].__setitem__("status", "empty"),
            lambda d: d["sections"]["outlook"].__setitem__("status", "included"),
            lambda d: d["sections"]["findings"]["evidence"][0].__setitem__("rank", 1),
            lambda d: d["sections"]["executive_summary"].__setitem__("health_score", 90),
            lambda d: d["sections"]["reporting_frame"]["framing"].__setitem__("target", 5),
            lambda d: d["sections"]["decisions_for_the_reader"].__setitem__("owner", "CFO"),
            lambda d: d["sections"]["swot"].__setitem__("status", "ranked"),
            lambda d: d["sources"]["strategy"].__setitem__("weight", 2),
        ]
        for mutate in mutations:
            changed = json.loads(json.dumps(document))
            mutate(changed)
            self.assertTrue(jsonschema_mini.validate(changed, schema))


# =======================================================================================
# E. Forecast boundary
# =======================================================================================

class ForecastBoundary(unittest.TestCase):

    def test_forecasts_cannot_enter_the_set_through_existing_translators(self):
        forecast_run = C.run("revenue-forecast", source=F.DEMO)
        synthesis = F.strict_set()
        with self.assertRaises(sc.SynthesisError):
            C.internal_statements(synthesis, forecast_run, S.ORIGIN_FORECAST, F.DATASET_ID)

    def test_a_forecast_footed_assumption_is_never_an_outlook_or_evidence(self):
        forecast_run = C.run("revenue-forecast", source=F.DEMO)
        synthesis = F.add_internal(F.strict_set())
        synthesis.register_analysis(forecast_run.forecast_set)
        finding = forecast_run.forecast_set.findings[0]
        estimate = synthesis.add(sc.SynthesisItem(
            sc.ASSUMPTION, S.ORIGIN_FORECAST, finding.statement,
            provenance=[sc.ProvenanceRef(sc.P_FORECAST, finding.analysis_id)]))
        output = E.build(synthesis, {}).as_dict()
        sections = output["sections"]
        self.assertEqual(sections["outlook"]["status"], "not_available")
        self.assertEqual(sections["outlook"]["statements"], [])
        self.assertIn(estimate.id, [a["synthesis_id"] for a in
                                    sections["evidence_and_uncertainty"]["assumptions"]])
        shown = json.dumps([sections[n] for n in ("executive_summary", "kpi_scorecard",
                                                   "findings", "anomalies")])
        self.assertNotIn(estimate.id, shown)
        for phrase in forecast_contract.FORBIDDEN_CERTAINTY:
            self.assertNotIn(phrase, json.dumps(sections["outlook"]).lower())


# =======================================================================================
# F. Command-level flow
# =======================================================================================

class CommandLevelFlow(unittest.TestCase):
    """`/executive-report` end to end: real runner, anomaly engine, reply, local join, all skills."""

    @classmethod
    def setUpClass(cls):
        cls.brief = F.open_market_brief()
        cls.command_run = C.run("business-health", source=F.DEMO)
        cls.joined = F.join()
        cls.synthesis = cls.joined.synthesis
        F.add_internal(cls.synthesis, run=cls.command_run, domains=("sales", "product"))
        for _kpi_id, result in sorted(cls.command_run.kpis.items()):
            S.from_kpi_result(cls.synthesis, result, dataset_id=F.DATASET_ID)
        C.internal_statements(cls.synthesis, anomaly_run(), S.ORIGIN_ANOMALY, F.DATASET_ID)
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
        rec = cls.strategy.recommendations[0]["action"]
        cls.package = D.build(cls.synthesis, {
            "decision_question": "Should we keep the Legacy Crates line?",
            "options": ["Keep the line unchanged"], "include_status_quo": False,
            "criteria": ["Fit with the range"],
            "tradeoffs": [{"options": [rec, "Keep the line unchanged"],
                           "criteria": ["Fit with the range"],
                           "text": "Reviewing responds to the decline; keeping the line does not.",
                           "evidence": [cls.reading.id]}],
            "preferred_option": rec, "preference_criteria": ["Fit with the range"]},
            strategy_result=cls.strategy)
        cls.swot = swot_mod.build(cls.synthesis, [
            {"quadrant": "weaknesses", "tag": "data-supported", "synthesis_id": legacy.id},
            {"quadrant": "threats", "tag": "externally-sourced", "synthesis_id": cls.price.id}])
        cls.before = cls.synthesis.to_json()
        cls.framing = {"reporting_period": "FY2025", "audience": "Owner",
                       "questions": ["What happened to Legacy Crates?"]}
        cls.result = E.build(cls.synthesis, cls.framing, strategy_result=cls.strategy,
                             swot=cls.swot, decision_results=[cls.package],
                             config=config_mod.resolve())
        cls.output = cls.result.as_dict()

    def test_the_real_seams_reached_the_real_builder(self):
        self.assertEqual(self.brief["status"], R.AUTHORISED)
        self.assertIs(type(self.command_run), C.CommandResult)
        self.assertIs(type(self.joined), C.LocalJoin)
        self.assertIs(type(self.result), E.ExecutiveReportResult)
        self.assertEqual(schema_errors(self.output), [])

    def test_a_draft_report_with_every_section(self):
        self.assertEqual(self.output["lifecycle"], "draft")
        statuses = dict((n, self.output["sections"][n]["status"]) for n in E.SECTION_ORDER)
        self.assertEqual(statuses["outlook"], "not_available")
        for name in ("kpi_scorecard", "findings", "anomalies", "swot",
                     "strategy_recommendations", "decision_support"):
            self.assertEqual(statuses[name], "included", name)
        rendered = E.render(self.result)
        self.assertIn("# Executive report", rendered)
        self.assertIn("draft — unverified", rendered)

    def test_framing_stays_framing_and_never_reaches_a_query(self):
        query = json.dumps(self.brief)
        for text in ("FY2025", "Owner", "What happened to Legacy Crates?"):
            self.assertNotIn(text, query)
        self.assertNotIn(str(self.joined.internal.observed), query)
        frame = self.output["sections"]["reporting_frame"]["framing"]
        self.assertEqual(frame["audience"], {"text": "Owner", "origin": "user", "stated": True})

    def test_optional_binding_is_enforced_on_the_command_path(self):
        other = World(kpis=False, anomalies=False)
        refused(self, lambda: E.build(self.synthesis, self.framing,
                                      strategy_result=other.strategy))
        refused(self, lambda: E.build(self.synthesis, self.framing,
                                      decision_results=[other.package]))
        refused(self, lambda: E.build(self.synthesis, self.framing, swot=other.swot))

    def test_no_side_effects(self):
        self.assertEqual(self.synthesis.to_json(), self.before)
        self.assertEqual(self.synthesis.recommendations, [])
        self.assertEqual(self.synthesis.candidate_claims, [])


# =======================================================================================
# G. Skill, command, registry
# =======================================================================================

class SkillAndCommand(unittest.TestCase):

    def test_the_skill_is_discoverable_with_supported_frontmatter(self):
        block = F.frontmatter(read(SKILL_MD))
        self.assertTrue(re.search(r"^name:\s*bops-executive-report\s*$", block, re.M))
        declared = set(re.findall(r"^([a-zA-Z-]+):", block, re.M))
        self.assertTrue(declared <= {"name", "description", "argument-hint",
                                     "user-invocable"}, declared)

    def test_the_command_is_thin_and_names_the_skill(self):
        text = read(COMMAND_MD)
        declared = set(re.findall(r"^([a-zA-Z-]+):", F.frontmatter(text), re.M))
        self.assertTrue(declared <= {"description", "argument-hint", "allowed-tools",
                                     "disable-model-invocation",
                                     "hide-from-slash-command-tool"}, declared)
        self.assertIn("`bops-executive-report`", text)
        self.assertIn("This command sequences", text)
        self.assertIn("**None required to run.**", text)
        body = text.split("---", 2)[2]
        for engine_rule in ("confidence.combine", "grounding.", "from_analysis_set",
                            "ForecastSet", "is_material"):
            self.assertNotIn(engine_rule, body)

    def test_both_state_the_contract_and_the_boundary(self):
        skill = " ".join(read(SKILL_MD).split())
        for token in ("executive_report.build(", "never authors", "draft",
                      "Forecasts have no path into the set", "financial transactions are prohibited",
                      "never evidence", "issues no recommendation"):
            self.assertIn(token, skill, token)
        for name in E.SECTION_ORDER + E.REQUEST_FIELDS:
            self.assertIn("`%s`" % name, skill, name)
        command = " ".join(read(COMMAND_MD).split()).lower()
        self.assertIn("nothing internal is sent as a fallback", command)
        self.assertIn("financial transactions are prohibited", command)
        self.assertIn("never part of any query", command)

    def test_the_command_skill_module_and_schema_ship_together(self):
        for path in (SKILL_MD, COMMAND_MD, ER_PY, ER_SCHEMA):
            self.assertTrue(os.path.exists(path), path)
        index = read(os.path.join(REPO_ROOT, "docs", "commands", "README.md"))
        self.assertIn("/executive-report", index)
        skills_index = read(os.path.join(REPO_ROOT, "docs", "skills", "README.md"))
        self.assertIn("bops-executive-report", skills_index)


if __name__ == "__main__":                                   # pragma: no cover
    unittest.main()
