# -*- coding: utf-8 -*-
"""M11 verification and finalisation (ADR-0034, amended by ADR-0035).

`bops.verification` is the engine. These tests run it over genuine inputs: the shipped synthetic demo
file through `commands.run()`, the Strategy and Decision Support fixtures, the SWOT engine and the
Executive Report engine. Recomputation runs the real fixed operation (`recompute_request`) in-process;
the MCP transport and the agent boundary have their own suites.

What gets the most attention:

* **Deterministic authority.** A result is `passed` only with no finding; every finding blocks.
* **Blind recomputation.** Figures are compared through digests bound to a sealed request; nothing a
  caller supplies can stand in for a recomputed value.
* **Finalisation changes lifecycle only.** Content and `report_id` are byte-identical to the draft.
* **Fail closed and no re-entry.**

**Every fixture is synthetic.** Working files go to a temporary directory, removed afterwards.
"""

import copy
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"), os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import commands as C                              # noqa: E402
from bops import config as config_mod                       # noqa: E402
from bops import decision_support as D                      # noqa: E402
from bops import executive_report as E                      # noqa: E402
from bops import jsonschema_mini                            # noqa: E402
from bops import pipeline as pipeline_mod                   # noqa: E402
from bops import strategy                                   # noqa: E402
from bops import swot as swot_mod                           # noqa: E402
from bops import synthesis as S                             # noqa: E402
from bops import verification as V                          # noqa: E402
from bops.commands import runner as runner_mod              # noqa: E402
from bops.kpi import catalog as kpi_catalog                 # noqa: E402
from bops.synthesis import contract as sc                   # noqa: E402
from unit import test_m10_3_2_strategy as F                # noqa: E402
from unit import test_m10_3_3_decision_support as T        # noqa: E402

SCHEMAS = os.path.join(REPO_ROOT, "lib", "schemas")
FRAMING = {"reporting_period": "FY2025", "audience": "Board of directors",
           "questions": ["Where is gross margin going?"]}
MARGIN_RATIONALE = "Average gross margin moved from 37.26% to 34.41% over the period."

_STATE = {}


def setUpModule():
    _STATE["previous"] = os.environ.get(V.ENV_DIRECTORY)
    _STATE["directory"] = tempfile.mkdtemp(prefix="bops-m11-verification-")
    os.environ[V.ENV_DIRECTORY] = _STATE["directory"]


def tearDownModule():
    if _STATE.get("previous") is None:
        os.environ.pop(V.ENV_DIRECTORY, None)
    else:
        os.environ[V.ENV_DIRECTORY] = _STATE["previous"]
    shutil.rmtree(_STATE["directory"], ignore_errors=True)


def anomaly_run():
    if "anomaly" not in _STATE:
        _STATE["anomaly"] = C.run("anomaly-detection", source=F.DEMO)
    return _STATE["anomaly"]


class Scene(object):
    """One strict set with command-path KPIs, findings and anomalies, and every component over it."""

    def __init__(self, kpi_run=None):
        self.f = T.Fixture()
        self.synthesis, self.parts = self.f.synthesis, self.f.parts
        # A test that mutates a KPI passes its own run: the shared run is never mutated.
        C.kpi_statements(self.synthesis, kpi_run or F.shared_run(), F.DATASET_ID)
        C.internal_statements(self.synthesis, anomaly_run(), S.ORIGIN_ANOMALY, F.DATASET_ID)
        self.strategy = strategy.build(self.synthesis, [F.proposal(
            [self.parts["margin"]], rationale=MARGIN_RATIONALE)])
        self.f.strategy = self.strategy
        self.f.record = self.strategy.recommendations[0]
        self.f.rec = self.f.record["action"]
        self.package = self.f.build()
        self.swot = swot_mod.build(self.synthesis, [
            {"quadrant": "strengths", "tag": "data-supported",
             "synthesis_id": self.parts["growth"].id},
            {"quadrant": "weaknesses", "tag": "data-supported",
             "synthesis_id": self.parts["margin"].id}])

    def report(self, packages=None, request=None, **overrides):
        components = dict(strategy_result=self.strategy, swot=self.swot,
                          decision_results=packages, config=config_mod.resolve())
        components.update(overrides)
        return E.build(self.synthesis, FRAMING if request is None else request, **components)


def relay_for(draft):
    """The full blind flow in-process: issue, run the fixed operation, relay its envelope."""
    request_id = V.issue_recomputation(draft)
    if request_id is None:
        return None
    return json.dumps(V.recompute_request({"request_id": request_id}))


def verified(draft):
    return V.verify(draft, relay_for(draft))


def sealed(draft):
    """Issue and recompute once; return the relay and the working files, for reuse after tampering."""
    relay = relay_for(draft)
    envelope = json.loads(relay)
    paths = [os.path.join(V.verification_directory(), "requests", envelope["request_id"] + ".json"),
             os.path.join(V.verification_directory(), "records", envelope["record_id"] + ".json")]
    files = dict((p, io.open(p, "rb").read()) for p in paths)
    return relay, files


def restore(files):
    for path, data in files.items():
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with io.open(path, "wb") as handle:
            handle.write(data)


def checks_failed(result):
    return sorted(set(f["check_id"] for f in result.as_dict()["findings"]))


def schema_errors(document, name):
    with io.open(os.path.join(SCHEMAS, name), encoding="utf-8") as handle:
        schema = json.load(handle)
    return jsonschema_mini.validate(json.loads(json.dumps(document, default=str)), schema)


def working_files():
    return [name for _dp, _dn, names in os.walk(V.verification_directory()) for name in names]


def shared():
    """One scene, one finalised package and a report over it, verified once for the whole module."""
    if "scene" not in _STATE:
        scene = Scene()
        package_result = verified(scene.package)
        final_package = V.finalise(scene.package, package_result)
        report = scene.report(packages=[final_package])
        report_result = verified(report)
        _STATE["scene"] = (scene, package_result, final_package, report, report_result)
    return _STATE["scene"]


# =======================================================================================
# A. Valid drafts, determinism, the result
# =======================================================================================

class ValidDrafts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        (cls.scene, cls.package_result, cls.final_package, cls.report,
         cls.report_result) = shared()

    def test_a_valid_package_passes(self):
        record = self.package_result.as_dict()
        self.assertEqual((record["status"], record["findings"]), ("passed", []))
        self.assertTrue(record["finalisation_permitted"])
        self.assertEqual(record["subject"]["kind"], "decision_package")
        self.assertEqual(record["recomputation"]["status"], "completed")
        self.assertGreater(record["recomputation"]["figures_checked"], 0)

    def test_a_valid_report_over_a_final_package_passes(self):
        record = self.report_result.as_dict()
        self.assertEqual((record["status"], record["findings"]), ("passed", []), record["findings"])
        self.assertEqual(record["subject"], {
            "kind": "executive_report", "report_id": self.report.report_id,
            "digest": "sha256:" + __import__("hashlib").sha256(
                self.report.to_json().encode("utf-8")).hexdigest()})
        self.assertEqual(record["components"]["decision_packages"][0]["lifecycle"], "final")
        self.assertEqual(record["components"]["decision_packages"][0]["verification_id"],
                         self.package_result.verification_id)

    def test_every_catalogue_check_is_reported_in_order(self):
        record = self.report_result.as_dict()
        self.assertEqual([c["check_id"] for c in record["checks"]], list(V.CHECK_IDS))
        self.assertEqual(len(record["checks"]), 46)
        self.assertEqual(set(c["outcome"] for c in record["checks"]), {"passed"})
        package = self.package_result.as_dict()
        not_applicable = [c["check_id"] for c in package["checks"]
                          if c["outcome"] == "not_applicable"]
        self.assertIn("section.set", not_applicable)
        self.assertIn("lifecycle.packages_final", not_applicable)

    def test_all_eleven_sections_are_verified(self):
        outcomes = dict((c["check_id"], c["outcome"]) for c in self.report_result.as_dict()["checks"])
        for check_id in ("section.set", "section.order", "section.status", "section.availability",
                         "content.statements", "content.summary", "content.kpi",
                         "content.anomalies", "content.strategy", "content.swot",
                         "content.decision_packages", "content.evidence_and_uncertainty",
                         "provenance.outlook", "provenance.framing", "boundary.fixed_text"):
            self.assertEqual(outcomes[check_id], "passed", check_id)
        self.assertEqual(list(json.loads(self.report.to_json())["sections"]),
                         list(E.SECTION_ORDER))

    def test_the_result_is_closed_and_schema_valid(self):
        for result in (self.report_result, self.package_result):
            self.assertEqual(schema_errors(result.as_dict(), "verification.schema.json"), [])
            self.assertRegex(result.verification_id, r"^ver-[0-9a-f]{12}$")
        record = self.report_result.as_dict()
        for forbidden in ("confidence", "trust", "severity", "likelihood", "score", "rank",
                          "priority", "timestamp", "created_at"):
            self.assertNotIn(forbidden, record)
        tampered = dict(record, severity="high")
        self.assertTrue(schema_errors(tampered, "verification.schema.json"))
        self.assertEqual(record["human_decision"], V.HUMAN_DECISION)

    def test_same_inputs_give_a_byte_identical_result_and_id(self):
        relay = relay_for(self.report)
        envelope = json.loads(relay)
        again = V.verify(self.report, relay)
        self.assertEqual(again.to_json(), self.report_result.to_json())
        self.assertEqual(again.verification_id, self.report_result.verification_id)
        for folder, name in (("requests", envelope["request_id"]),
                             ("records", envelope["record_id"])):
            self.assertFalse(os.path.exists(os.path.join(V.verification_directory(), folder,
                                                         name + ".json")), "consumed")

    def test_no_model_text_can_stand_for_a_result(self):
        with self.assertRaises(V.VerificationError):
            V.VerificationResult(self.report, self.report_result.as_dict())
        for bad in (self.report_result.as_dict(), json.loads(self.report_result.to_json()), None):
            with self.assertRaises(V.VerificationError):
                V.finalise(self.report, bad)
        for keyword in ("expected", "observed", "result", "lifecycle", "confidence", "trust",
                        "recomputed", "findings"):
            with self.assertRaises(TypeError):
                V.verify(self.report, **{keyword: "x"})


# =======================================================================================
# B. Input refusal
# =======================================================================================

class InputRefusal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        (cls.scene, _p, cls.final_package, cls.report, cls.report_result) = shared()

    def test_anything_but_a_genuine_draft_is_refused_with_no_result(self):
        final_report = V.finalise(self.report, self.report_result)
        for bad in (None, {}, "draft", self.report.as_dict(), json.loads(self.report.to_json()),
                    self.scene.strategy, self.scene.synthesis, self.scene.swot,
                    self.final_package, final_report):
            with self.assertRaises(V.VerificationError):
                V.verify(bad)
            with self.assertRaises(V.VerificationError):
                V.issue_recomputation(bad)

    def test_a_draft_whose_lifecycle_was_edited_fails_and_runs_nothing_else(self):
        report = self.scene.report(packages=[self.final_package])
        report._report["lifecycle"] = "final"
        result = V.verify(report, None)
        checks = result.as_dict()["checks"]
        self.assertEqual(checks[0], {"check_id": "input.genuine_draft",
                                     "category": "input_integrity", "method": "source_binding",
                                     "outcome": "failed"})
        self.assertLessEqual(set(c["outcome"] for c in checks[1:]), {"not_run", "not_applicable"})
        self.assertEqual(checks_failed(result), ["input.genuine_draft"])


# =======================================================================================
# C. The synthesis set and the binding graph
# =======================================================================================

class Binding(unittest.TestCase):

    def fresh(self):
        scene = Scene()
        package = V.finalise(scene.package, verified(scene.package))
        return scene, scene.report(packages=[package]), package

    def test_a_changed_set_fails_binding(self):
        scene, report, _pkg = self.fresh()
        S.assumption(scene.synthesis, S.ORIGIN_FINANCIAL, "Volumes are assumed stable.",
                     "No volume forecast exists.")
        self.assertIn("binding.synthesis", checks_failed(V.verify(report, None)))

    def test_a_critical_non_strict_or_empty_set_fails(self):
        for mutate, check_id in (
                (lambda s: setattr(s, "quality_grade", "CRITICAL"), "synthesis.quality_grade"),
                (lambda s: setattr(s, "require_dimension_provenance", False),
                 "synthesis.genuine_strict"),
                (lambda s: setattr(s, "_items", []), "synthesis.genuine_strict")):
            scene, report, _pkg = self.fresh()
            mutate(scene.synthesis)
            failed = checks_failed(V.verify(report, None))
            self.assertIn(check_id, failed)
            if check_id == "synthesis.quality_grade" or not scene.synthesis.items:
                self.assertIn("binding.synthesis", failed)

    def test_a_stale_report_id_fails_reproduction(self):
        scene, report, _pkg = self.fresh()
        relay, files = sealed(report)
        report._report["report_id"] = "rpt-000000000000"
        restore(files)
        result = V.verify(report, relay)
        finding = [f for f in result.as_dict()["findings"] if f["check_id"] == "reproduction.report"]
        self.assertEqual(finding[0]["location"], "/report_id")

    def test_a_changed_strategy_result_fails(self):
        scene, report, _pkg = self.fresh()
        scene.strategy._records[0]["confidence"] = "LOW" if scene.strategy._records[0][
            "confidence"] != "LOW" else "HIGH"
        failed = checks_failed(V.verify(report, None))
        self.assertIn("binding.strategy", failed)
        self.assertIn("reproduction.strategy", failed)

    def test_a_wrong_set_strategy_or_package_fails(self):
        scene, report, _pkg = self.fresh()
        other = Scene()
        report._strategy = other.strategy
        self.assertIn("binding.strategy", checks_failed(V.verify(report, None)))
        scene, report, _pkg = self.fresh()
        report._packages = [(other.package, report._packages[0][1])]
        failed = checks_failed(V.verify(report, None))
        self.assertIn("binding.decision_packages", failed)
        self.assertIn("lifecycle.packages_final", failed)

    def test_a_missing_or_duplicate_component_fails(self):
        scene, report, _pkg = self.fresh()
        report._swot = None
        self.assertIn("binding.sources_record", checks_failed(V.verify(report, None)))
        scene, report, _pkg = self.fresh()
        report._packages = report._packages * 2
        findings = V.verify(report, None).as_dict()["findings"]
        self.assertIn("duplicate", [f["observed"] for f in findings
                                    if f["check_id"] == "binding.decision_packages"])

    def test_an_edited_swot_fails(self):
        scene, report, _pkg = self.fresh()
        report._swot["quadrants"][0]["points"][0]["tag"] = "externally-sourced"
        failed = checks_failed(V.verify(report, None))
        self.assertIn("binding.swot", failed)
        self.assertIn("reproduction.swot", failed)

    def test_same_set_components_pass_and_draft_packages_block(self):
        scene = Scene()
        draft_report = scene.report(packages=[scene.package])
        result = verified(draft_report)
        self.assertEqual(checks_failed(result), ["lifecycle.packages_final"])
        self.assertEqual(result.as_dict()["findings"][0]["observed"], "not_final")
        with self.assertRaises(V.VerificationError):
            V.finalise(draft_report, result)

    def test_a_changed_registered_figure_fails_registry_and_recomputation(self):
        scene = Scene(kpi_run=C.run("business-health", source=F.DEMO))
        package = V.finalise(scene.package, verified(scene.package))
        report = scene.report(packages=[package])
        relay, files = sealed(report)
        registered = dict((r.kpi_id, r) for r in scene.synthesis.registered_kpis())
        kpi = [r for r in registered.values() if r.available][0]
        kpi.value = kpi.value + 1
        restore(files)
        failed = checks_failed(V.verify(report, relay))
        self.assertIn("synthesis.registry_agreement", failed)
        self.assertIn("recomputation.kpi", failed)


# =======================================================================================
# D. Blind recomputation
# =======================================================================================

class Recomputation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        (cls.scene, _p, cls.final_package, _r, _rr) = shared()

    def report(self):
        return self.scene.report(packages=[self.final_package])

    def test_the_request_carries_ids_paths_and_hashes_but_no_value(self):
        report = self.report()
        request_id = V.issue_recomputation(report)
        self.assertRegex(request_id, r"^rcq-[0-9a-f]{16}$")
        path = os.path.join(V.verification_directory(), "requests", request_id + ".json")
        text = io.open(path, encoding="utf-8").read()
        request = json.loads(text)
        self.assertEqual(set(request), {"protocol", "request_id", "runs"})
        for item in self.scene.synthesis.items:
            if item.kind in sc.INTERNALLY_FOOTED_KINDS:
                self.assertNotIn(item.statement, text)
        for result in self.scene.synthesis.registered_kpis():
            if result.available:
                self.assertNotIn('"%s"' % result.value, text)
        os.remove(path)

    def test_a_missing_recomputation_basis_fails(self):
        synthesis = F.strict_set()
        synthesis.register_dataset(F.DATASET_ID, label="demo")
        for result in F.shared_run().kpis.values():
            S.from_kpi_result(synthesis, result, dataset_id=F.DATASET_ID)
        report = E.build(synthesis, {})
        with self.assertRaises(V.VerificationError):
            V.issue_recomputation(report)
        result = V.verify(report, None)
        self.assertIn("recomputation.request", checks_failed(result))
        self.assertEqual(result.as_dict()["recomputation"]["status"], "failed")

    def test_an_absent_failed_or_malformed_relay_fails(self):
        report = self.report()
        relay, files = sealed(report)
        envelope = json.loads(relay)
        bad_relays = {
            None: "absent",
            "not json": "malformed",
            "Here it is: " + relay: "malformed",
            json.dumps(dict(envelope, extra="x")): "malformed",
            json.dumps(dict(envelope, protocol="bops.verifier.result/2")): "malformed",
            json.dumps(dict(envelope, request_id="rcq-" + "0" * 16)): "mismatched",
            json.dumps(dict(envelope, status="failed", record_id=None,
                            error_code="execution_error")): "execution_error",
            json.dumps(dict(envelope, observed_value="171450.93")): "malformed",
        }
        for bad, observed in bad_relays.items():
            restore(files)
            result = V.verify(report, bad)
            relay_findings = [f for f in result.as_dict()["findings"]
                              if f["check_id"] == "recomputation.relay"]
            self.assertEqual([f["observed"] for f in relay_findings], [observed], bad)
            self.assertFalse(result.passed)
        restore(files)
        fenced = "```json\n%s\n```" % relay
        self.assertTrue(V.verify(report, fenced).passed, "one code fence is only a wrapper")

    def test_a_missing_altered_or_foreign_record_fails(self):
        report = self.report()
        relay, files = sealed(report)
        record_path = [p for p in files if "records" in p][0]
        restore(files)
        os.remove(record_path)
        self.assertIn("recomputation.record", checks_failed(V.verify(report, relay)))
        restore(files)
        with io.open(record_path, "ab") as handle:
            handle.write(b" ")
        self.assertIn("recomputation.record", checks_failed(V.verify(report, relay)))
        # a genuine record for another request: the package's, which cites fewer figures
        other_relay = relay_for(self.scene.package)
        restore(files)
        forged = json.dumps(dict(json.loads(relay), record_id=json.loads(other_relay)["record_id"]))
        self.assertIn("recomputation.record", checks_failed(V.verify(report, forged)))

    def test_a_changed_recomputed_digest_fails_the_comparison(self):
        report = self.report()
        relay, files = sealed(report)
        record_path = [p for p in files if "records" in p][0]
        record = json.loads(files[record_path].decode("utf-8"))
        run = record["runs"][0]
        item = [i for i in run["items"] if i["kind"] == "kpi"][0]
        field = sorted(item["digests"])[0]
        item["digests"][field] = "sha256:" + "0" * 64
        record_id = V._content_address("rcr-", record, 16)
        record["record_id"] = record_id
        forged_path = os.path.join(V.verification_directory(), "records", record_id + ".json")
        restore(files)
        with io.open(forged_path, "wb") as handle:
            handle.write(runner_mod.canonical_json(record).encode("utf-8"))
        result = V.verify(report, json.dumps(dict(json.loads(relay), record_id=record_id)))
        self.assertEqual(checks_failed(result), ["recomputation.kpi"])
        finding = result.as_dict()["findings"][0]
        self.assertEqual(finding["observed"], "differs")
        self.assertTrue(finding["expected"].startswith("run:%s/kpi:" % run["run_id"]))

    def test_a_changed_source_fails_and_nothing_from_that_run_is_trusted(self):
        workdir = tempfile.mkdtemp(prefix="bops-m11-source-")
        try:
            source = os.path.join(workdir, "sales.csv")
            shutil.copy(F.DEMO, source)
            synthesis = F.strict_set()
            C.kpi_statements(synthesis, C.run("business-health", source=source), F.DATASET_ID)
            report = E.build(synthesis, {})
            request_id = V.issue_recomputation(report)
            with io.open(source, "ab") as handle:
                handle.write(b"\n")
            envelope = V.recompute_request({"request_id": request_id})
            self.assertEqual(envelope["status"], "completed")
            result = V.verify(report, json.dumps(envelope))
            self.assertEqual(checks_failed(result), ["recomputation.source"])
            outcomes = dict((c["check_id"], c["outcome"]) for c in result.as_dict()["checks"])
            self.assertEqual(result.as_dict()["recomputation"]["runs"][0]["source_status"],
                             "mismatched")
            self.assertEqual(result.as_dict()["recomputation"]["figures_checked"], 0)
            self.assertEqual(outcomes["recomputation.kpi"], "not_run", "nothing trusted, nothing passed")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def test_a_changed_configuration_fails(self):
        project = tempfile.mkdtemp(prefix="bops-m11-config-")
        try:
            context = os.path.join(project, ".businessops", "business_context.json")
            os.makedirs(os.path.dirname(context))
            shutil.copy(F.DEMO_CONTEXT, context)
            synthesis = F.strict_set()
            C.kpi_statements(synthesis, C.run("business-health", source=F.DEMO,
                                              project_dir=project), F.DATASET_ID)
            report = E.build(synthesis, {})
            request_id = V.issue_recomputation(report)
            os.remove(context)
            result = V.verify(report, json.dumps(V.recompute_request({"request_id": request_id})))
            self.assertEqual(checks_failed(result), ["recomputation.configuration"])
        finally:
            shutil.rmtree(project, ignore_errors=True)

    def test_a_source_that_changes_during_the_run_yields_no_basis(self):
        workdir = tempfile.mkdtemp(prefix="bops-m11-during-")
        try:
            source = os.path.join(workdir, "sales.csv")
            shutil.copy(F.DEMO, source)
            original = pipeline_mod.run

            def changing(*args, **kwargs):
                result = original(*args, **kwargs)
                with io.open(source, "ab") as handle:
                    handle.write(b"\n")
                return result
            with mock.patch.object(pipeline_mod, "run", changing):
                run = C.run("business-health", source=source)
            self.assertEqual((run.status, run.error_type, run.run_id),
                             (runner_mod.UNAVAILABLE, "SourceChanged", None))
            self.assertEqual(run.kpis, {})
            with self.assertRaises(sc.SynthesisError):
                F.strict_set().register_run(run, F.DATASET_ID)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def test_the_operation_never_returns_a_value_path_or_message(self):
        report = self.report()
        request_id = V.issue_recomputation(report)
        envelope = V.recompute_request({"request_id": request_id})
        self.assertEqual(set(envelope), {"protocol", "request_id", "status", "record_id",
                                         "error_code"})
        text = json.dumps(envelope)
        self.assertNotIn(F.DEMO.replace("\\", "\\\\"), text)
        self.assertNotIn("northwind", text.lower())
        record_path = os.path.join(V.verification_directory(), "records",
                                   envelope["record_id"] + ".json")
        record = io.open(record_path, encoding="utf-8").read()
        self.assertNotIn("northwind", record.lower())
        for result in self.scene.synthesis.registered_kpis():
            if result.available:
                self.assertNotIn('"%s"' % result.value, record)
        for path in (record_path, os.path.join(V.verification_directory(), "requests",
                                               request_id + ".json")):
            os.remove(path)


# =======================================================================================
# E. Text figures (the ADR-0031 figure rule, reused through reproduction)
# =======================================================================================

class TextFigures(unittest.TestCase):

    def scene_with(self, rationale):
        scene = Scene()
        scene.strategy._proposals[0]["rationale"] = rationale
        return scene

    def test_the_exact_figure_passes(self):
        scene = self.scene_with(MARGIN_RATIONALE)
        self.assertNotIn("reproduction.strategy", checks_failed(verified(scene.package)))

    def test_altered_rounded_signed_or_worded_figures_fail(self):
        for rationale in ("Average gross margin moved from 37.26% to 34.42% over the period.",
                          "Average gross margin moved from 37.26% to 34.4% over the period.",
                          "Average gross margin moved from 37.26% to -34.41% over the period.",
                          "Average gross margin moved from 37.26% to thirty-four percent."):
            scene = self.scene_with(rationale)
            findings = [f for f in V.verify(scene.package, relay_for(scene.package))
                        .as_dict()["findings"] if f["check_id"] == "reproduction.strategy"]
            self.assertEqual([f["observed"] for f in findings], ["refused"], rationale)

    def test_an_unexpected_failure_inside_the_figure_rule_fails_closed(self):
        scene = Scene()
        relay = relay_for(scene.package)
        with mock.patch.object(strategy, "require_grounded", side_effect=RuntimeError("boom")):
            result = V.verify(scene.package, relay)
        self.assertFalse(result.passed)
        self.assertIn("reproduction.strategy", checks_failed(result))
        self.assertNotIn("boom", result.to_json())


# =======================================================================================
# F. Sections, content and provenance (tampering one report at a time)
# =======================================================================================

class ContentTampering(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        (cls.scene, _p, cls.final_package, report, _rr) = shared()
        cls.relay, cls.files = sealed(report)

    def check(self, tamper, expected):
        report = self.scene.report(packages=[self.final_package])
        tamper(report._report["sections"], report._report)
        restore(self.files)
        failed = checks_failed(V.verify(report, self.relay))
        self.assertIn(expected, failed)
        return failed

    def test_each_tamper_is_located_by_its_check(self):
        s = E
        cases = [
            (lambda sec, r: sec.pop(s.OUTLOOK), "section.set"),
            (lambda sec, r: r.__setitem__("section_order", list(reversed(r["section_order"]))),
             "section.order"),
            (lambda sec, r: sec[s.SWOT].__setitem__("status", "empty"), "section.status"),
            (lambda sec, r: sec[s.EXECUTIVE_SUMMARY]["availability"].reverse(),
             "section.availability"),
            (lambda sec, r: sec[s.FINDINGS]["evidence"][0]["statement_detail"].__setitem__(
                "statement", "Revenue growth is 90%."), "content.statements"),
            (lambda sec, r: sec[s.EXECUTIVE_SUMMARY].__setitem__("materiality_not_assessed", 0),
             "content.summary"),
            (lambda sec, r: sec[s.KPI_SCORECARD]["rows"].reverse(), "content.kpi"),
            (lambda sec, r: sec[s.ANOMALIES]["statements"][0].__setitem__("caveats", []),
             "content.anomalies"),
            (lambda sec, r: sec[s.STRATEGY_RECOMMENDATIONS]["result"]["recommendations"][0]
             .__setitem__("action", "Close the business."), "content.strategy"),
            (lambda sec, r: sec[s.SWOT]["result"]["quadrants"][0]["points"][0].__setitem__(
                "tag", "externally-sourced"), "content.swot"),
            (lambda sec, r: sec[s.DECISION_SUPPORT]["packages"][0]["package"]["body"]["guidance"]
             .__setitem__("preferred_option", None), "content.decision_packages"),
            (lambda sec, r: sec[s.EVIDENCE_AND_UNCERTAINTY].__setitem__("limitations", []),
             "content.evidence_and_uncertainty"),
            (lambda sec, r: sec[s.OUTLOOK].__setitem__("status", "included"), "provenance.outlook"),
            (lambda sec, r: sec[s.REPORTING_FRAME]["framing"]["audience"].__setitem__(
                "origin", "evidence"), "provenance.framing"),
            (lambda sec, r: [e["statement_detail"].__setitem__("trust", "trusted")
                             for e in sec[s.FINDINGS]["evidence"]
                             if e["statement_detail"]["kind"] == "SOURCED"],
             "provenance.external_trust"),
            (lambda sec, r: sec[s.FINDINGS]["evidence"][0]["statement_detail"].__setitem__(
                "kind", "ASSUMPTION"), "provenance.evidence_kinds"),
            (lambda sec, r: sec[s.FINDINGS]["evidence"][0]["statement_detail"].__setitem__(
                "synthesis_id", r["sources"]["strategy"]["recommendation_ids"][0]),
             "provenance.owned_content"),
            (lambda sec, r: sec[s.DECISIONS_FOR_THE_READER].__setitem__(
                "human_decision", "Approved by the board."), "boundary.fixed_text"),
            (lambda sec, r: sec[s.KPI_SCORECARD]["rows"][0].__setitem__("target", "5"),
             "boundary.forbidden_fields"),
            (lambda sec, r: r.__setitem__("lifecycle_note", "Verified."), "lifecycle.draft_input"),
        ]
        for tamper, expected in cases:
            self.check(tamper, expected)

    def test_a_score_field_is_refused_by_boundary_and_schema(self):
        failed = self.check(lambda sec, r: r.__setitem__("health_score", 90),
                            "boundary.forbidden_fields")
        self.assertIn("schema.subject", failed)

    def test_findings_are_ordered_by_catalogue_section_and_position_only(self):
        report = self.scene.report(packages=[self.final_package])
        sections = report._report["sections"]
        sections[E.DECISIONS_FOR_THE_READER]["human_decision"] = "Changed."
        sections[E.KPI_SCORECARD]["rows"].reverse()
        report._report["section_order"] = list(reversed(report._report["section_order"]))
        restore(self.files)
        first = V.verify(report, self.relay)
        restore(self.files)
        second = V.verify(report, self.relay)
        self.assertEqual(first.to_json(), second.to_json())
        index = dict((check_id, i) for i, check_id in enumerate(V.CHECK_IDS))
        positions = [index[f["check_id"]] for f in first.as_dict()["findings"]]
        self.assertEqual(positions, sorted(positions))
        for finding in first.as_dict()["findings"]:
            self.assertNotIn("severity", finding)
            self.assertIn(finding["observed"], V.OBSERVED_CODES)


# =======================================================================================
# G. Finalisation
# =======================================================================================

class Finalisation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        (cls.scene, cls.package_result, cls.final_package, cls.report,
         cls.report_result) = shared()
        cls.final = V.finalise(cls.report, cls.report_result)

    def test_only_lifecycle_fields_change_and_report_id_stays(self):
        final = json.loads(self.final.to_json())
        draft = json.loads(self.report.to_json())
        self.assertEqual(self.final.report_id, self.report.report_id)
        self.assertEqual(final["report_id"], draft["report_id"])
        self.assertEqual(final["verification_record"]["verification_id"],
                         self.report_result.verification_id)
        for holder in (final, final["sections"][E.REPORTING_FRAME]):
            self.assertEqual((holder["lifecycle"], holder["verification"], holder["lifecycle_note"]),
                             ("final", "verified", V.FINAL_REPORT_NOTE))
            holder["lifecycle"], holder["verification"] = "draft", "unverified"
            holder["lifecycle_note"] = E.LIFECYCLE_NOTE
        del final["verification_record"]
        self.assertEqual(final, draft)
        self.assertEqual(schema_errors(json.loads(self.final.to_json()),
                                       "executive_report.schema.json"), [])

    def test_the_final_package_changes_lifecycle_only(self):
        final = self.final_package.as_dict()
        draft = self.scene.package.as_dict()
        self.assertEqual(final["body"], draft["body"])
        for key in ("lifecycle", "verification", "lifecycle_note", "verification_record"):
            final.pop(key)
            draft.pop(key, None)
        self.assertEqual(final, draft)
        self.assertEqual(schema_errors(self.final_package.as_dict(),
                                       "decision_support.schema.json"), [])

    def test_the_final_note_says_integrity_not_approval(self):
        for note in (V.FINAL_REPORT_NOTE, V.FINAL_PACKAGE_NOTE):
            self.assertIn("verified for integrity", note)
            self.assertIn("does not mean", note)
        self.assertIn("records no approval", V.HUMAN_DECISION)

    def test_repeated_finalisation_is_equal_and_finals_are_refused(self):
        again = V.finalise(self.report, self.report_result)
        self.assertEqual(again.to_json(), self.final.to_json())
        with self.assertRaises(V.VerificationError):
            V.finalise(self.final, self.report_result)
        with self.assertRaises(V.VerificationError):
            V.verify(self.final, None)
        self.assertTrue(verified(self.report).passed, "the draft stays independently verifiable")

    def test_a_failed_foreign_or_stale_verification_cannot_finalise(self):
        scene = Scene()
        package = V.finalise(scene.package, verified(scene.package))
        report = scene.report(packages=[package])
        with self.assertRaises(V.VerificationError):
            V.finalise(report, self.report_result)               # another draft's verification
        failed = V.verify(report, None)
        with self.assertRaises(V.VerificationError):
            V.finalise(report, failed)
        result = verified(report)
        self.assertTrue(result.passed)
        S.assumption(scene.synthesis, S.ORIGIN_FINANCIAL, "Volumes stay flat.", "No forecast.")
        with self.assertRaises(V.VerificationError):
            V.finalise(report, result)
        with self.assertRaises(V.VerificationError):
            package.as_dict()

    def test_a_component_changed_after_verification_cannot_finalise(self):
        scene = Scene()
        package = V.finalise(scene.package, verified(scene.package))
        report = scene.report(packages=[package])
        result = verified(report)
        final = V.finalise(report, result)
        scene.swot["quadrants"][0]["points"][0]["tag"] = "externally-sourced"
        report._swot["quadrants"][0]["points"][0]["tag"] = "externally-sourced"
        with self.assertRaises(V.VerificationError):
            V.finalise(report, result)
        with self.assertRaises(V.VerificationError):
            final.as_dict()


# =======================================================================================
# H. Run registry and re-entry
# =======================================================================================

class RunRegistry(unittest.TestCase):

    def test_runs_are_content_addressed_bound_and_digested(self):
        synthesis = F.strict_set()
        C.kpi_statements(synthesis, F.shared_run(), F.DATASET_ID)
        C.internal_statements(synthesis, anomaly_run(), S.ORIGIN_ANOMALY, F.DATASET_ID)
        runs = synthesis.registered_runs()
        self.assertEqual([r["command_id"] for r in runs], ["business-health", "anomaly-detection"])
        self.assertEqual(len(set(r["dataset_id"] for r in runs)), 1, "one dataset, two runs")
        for record in runs:
            self.assertRegex(record["run_id"], r"^run-[0-9a-f]{12}$")
            self.assertRegex(record["source_sha256"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(synthesis.run_for(sc.P_KPI, "revenue")["command_id"], "business-health")
        view = json.loads(synthesis.to_json())
        self.assertEqual(view["runs"], runs)
        self.assertIn("kpi:revenue", view["run_bindings"])

    def test_kpi_statements_follow_the_catalogue(self):
        synthesis = F.strict_set()
        produced = C.kpi_statements(synthesis, F.shared_run(), F.DATASET_ID)
        order = [d.kpi_id for d in kpi_catalog.CATALOGUE]
        metrics = [item.metric for item in produced]
        self.assertEqual(metrics, sorted(metrics, key=order.index))

    def test_cross_run_re_registration_is_refused_and_changes_nothing(self):
        synthesis = F.strict_set()
        C.kpi_statements(synthesis, F.shared_run(), F.DATASET_ID)
        before = synthesis.to_json()
        other = C.run("business-health", source=F.DEMO, presentation="shareable")
        for call in (lambda: C.kpi_statements(synthesis, other, F.DATASET_ID),
                     lambda: C.internal_statements(synthesis, other, S.ORIGIN_KPI, F.DATASET_ID,
                                                   kpi_id="revenue")):
            with self.assertRaises(sc.SynthesisError):
                call()
            self.assertEqual(synthesis.to_json(), before)
        C.kpi_statements(synthesis, F.shared_run(), F.DATASET_ID)      # the same run: idempotent


class ReEntry(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        (cls.scene, cls.package_result, cls.final_package, cls.report,
         cls.report_result) = shared()

    def test_verification_artifacts_never_become_candidate_claims(self):
        final = V.finalise(self.report, self.report_result)
        record = self.report_result.as_dict()
        variants = [record, record["checks"][0], record["recomputation"],
                    self.report_result.verification_record(), json.loads(final.to_json()),
                    self.final_package.as_dict(), {"statement": "x", "verification_id": "ver-1"},
                    {"statement": "x", "request_id": "rcq-1"}, {"statement": "x", "check_id": "c"},
                    {"statement": "x", "analysis": "verification"},
                    {"statement": "x", "verification": "verified"},
                    {"statement": "x", "finding_id": "vf-1", "observed": "differs"}]
        for variant in variants:
            with self.assertRaises(sc.SynthesisError, msg=str(variant)[:80]):
                F.strict_set().register_claims([variant])
        for obj in (self.report_result, final, self.final_package):
            with self.assertRaises(sc.SynthesisError):
                F.strict_set().register_claims([obj])
        genuine = F.strict_set().register_claims([{"statement": "A source said x.",
                                                   "evidence_id": "ev-1", "class": 3,
                                                   "label": "SOURCED"}])
        self.assertEqual(len(genuine), 1)


# =======================================================================================
# I. Schemas and the engine's own boundary
# =======================================================================================

class Contract(unittest.TestCase):

    def load(self, name):
        with io.open(os.path.join(SCHEMAS, name), encoding="utf-8") as handle:
            return json.load(handle)

    def test_the_schema_catalogue_matches_the_engine(self):
        schema = self.load("verification.schema.json")
        self.assertEqual(schema["definitions"]["check_id"]["enum"], list(V.CHECK_IDS))
        self.assertEqual(schema["definitions"]["category"]["enum"], list(V.CATEGORIES))
        self.assertEqual(schema["definitions"]["method"]["enum"], list(V.METHODS))
        self.assertEqual(schema["definitions"]["finding"]["properties"]["observed"]["enum"],
                         list(V.OBSERVED_CODES))
        self.assertEqual(jsonschema_mini.unsupported_keywords(schema), set())
        self.assertEqual(sorted(set(entry[1] for entry in V.CATALOGUE)), sorted(V.CATEGORIES))

    def test_request_record_and_envelope_are_closed_protocol_shapes(self):
        schema = self.load("verification.schema.json")

        def errors(instance, definition):
            wrapper = {"$ref": "#/definitions/%s" % definition, "definitions": schema["definitions"]}
            return jsonschema_mini.validate(json.loads(json.dumps(instance)), wrapper)
        _scene, _pr, _fp, report, _rr = shared()
        relay, files = sealed(report)
        envelope = json.loads(relay)
        request = [json.loads(v.decode("utf-8")) for p, v in files.items() if "requests" in p][0]
        record = [json.loads(v.decode("utf-8")) for p, v in files.items() if "records" in p][0]
        self.assertEqual(errors(envelope, "protocol_envelope"), [])
        self.assertEqual(errors(request, "protocol_request"), [])
        self.assertEqual(errors(record, "protocol_record"), [])
        self.assertEqual(errors(V.envelope(None, "failed", error_code="request_id_invalid"),
                                "protocol_envelope"), [])
        for bad, definition in ((dict(envelope, figure="1"), "protocol_envelope"),
                                (dict(envelope, error_code="Traceback"), "protocol_envelope"),
                                (dict(request, figures=[]), "protocol_request"),
                                (dict(record, values={}), "protocol_record")):
            self.assertTrue(errors(bad, definition), definition)
        for path in files:
            os.remove(path)

    def test_the_verification_record_is_one_shape_in_every_schema(self):
        own = self.load("verification.schema.json")
        record = self.load("decision_support.schema.json")["definitions"]["verification_record"]
        report = self.load("executive_report.schema.json")["definitions"]
        self.assertEqual(report["verification_record"], record)
        self.assertEqual(report["decision_verification_record"], record)
        _scene, _pr, _fp, _report, result = shared()
        self.assertEqual(sorted(result.verification_record()), sorted(record["required"]))
        self.assertEqual(sorted(record["properties"]), sorted(record["required"]))
        self.assertIn("recomputation", own["properties"])

    def test_the_engine_reads_no_network_and_dispatches_nothing(self):
        with io.open(os.path.join(REPO_ROOT, "lib", "python", "bops", "verification.py"),
                     encoding="utf-8") as handle:
            body = handle.read()
        for token in ("import socket", "urllib", "http.client", "import requests", "subprocess",
                      "smtplib", "Agent(", "WebFetch", "confidence.combine", "severity ="):
            self.assertNotIn(token, body, token)
        self.assertFalse(re.search(r"^\s*def\s+\w*(approve|execute|send)\w*\(", body, re.M))


if __name__ == "__main__":                                   # pragma: no cover
    unittest.main()
