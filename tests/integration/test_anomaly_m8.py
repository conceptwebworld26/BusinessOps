"""Anomaly detection end to end: pipeline, engine, privacy, command and rendered report.

The unit tests prove the scoring. These prove what only a whole run can show: that the scan
reads the mapped dataset rather than the file, that the materiality policy decides what
leads, that contributor attribution passes through the Milestone 3 privacy policy, and -
most importantly - that nothing the layer emits calls a deviation a cause or a crime.
"""

import json
import os
import shutil
import tempfile
import unittest
from decimal import Decimal

from bops import anomaly, commands, evidence, pipeline
from bops.analytics import contract as analytics_contract
from bops.analytics import presentation
from bops.anomaly import contract as anomaly_contract, detectors
from bops.quality import contract as quality_contract

from fixtures import build_forecast_fixtures as build

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")

D = Decimal


class AnomalyCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m8-anomaly-")
        cls.paths = {
            "flat": build.flat(cls.directory),
            "trend": build.steady_trend(cls.directory),
            "spike": build.with_spike(cls.directory),
            "drop": build.with_drop(cls.directory),
            "two": build.with_two_anomalies(cls.directory),
            "short": build.short(cls.directory),
            "no_cost": build.no_cost(cls.directory),
            "one_customer": build.single_customer(cls.directory),
            "gap": build.with_gap(cls.directory),
        }

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def result(self, key):
        return pipeline.run(self.paths.get(key, key), load_context_files=False)

    def scan(self, key, **kwargs):
        return pipeline.detect_anomalies(self.result(key), **kwargs)

    def revenue_flags(self, key, **kwargs):
        scan = self.scan(key, **kwargs)
        return [o for o in scan.by_metric("revenue") if o.flagged]


class TestAnomalyDetection(AnomalyCase):

    def test_a_flat_series_flags_nothing(self):
        self.assertEqual(self.revenue_flags("flat"), [])

    def test_a_steady_trend_flags_nothing(self):
        self.assertEqual(self.revenue_flags("trend"), [])

    def test_a_scan_that_finds_nothing_still_reports_that_it_ran(self):
        scan = self.scan("flat")
        self.assertEqual(scan.status, anomaly_contract.AVAILABLE)
        self.assertGreater(len(scan.observations), 0)
        self.assertEqual(scan.scanned_metrics["revenue"], anomaly_contract.AVAILABLE)

    def test_an_isolated_spike_is_flagged_once(self):
        flags = self.revenue_flags("spike")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].direction, anomaly_contract.ABOVE)

    def test_an_isolated_drop_is_flagged_once(self):
        flags = self.revenue_flags("drop")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].direction, anomaly_contract.BELOW)

    def test_the_month_after_a_spike_is_not_reported_as_a_second_event(self):
        flags = self.revenue_flags("spike")
        self.assertEqual(len(flags), 1)

    def test_two_separate_anomalies_are_both_reported(self):
        self.assertEqual(len(self.revenue_flags("two")), 2)

    def test_every_flagged_observation_names_its_baseline(self):
        for observation in self.revenue_flags("spike"):
            self.assertIsNotNone(observation.baseline)
            self.assertIsNotNone(observation.baseline.centre)
            self.assertTrue(observation.baseline.description)

    def test_every_flagged_observation_names_its_detector_and_threshold(self):
        for observation in self.revenue_flags("spike"):
            self.assertIn(observation.method, detectors.DETECTOR_IDS)
            self.assertIsNotNone(observation.threshold)
            self.assertGreaterEqual(observation.score, observation.threshold)

    def test_the_scan_records_which_periods_it_checked_and_found_normal(self):
        scan = self.scan("spike")
        normal = [o for o in scan.by_metric("revenue")
                  if o.status == anomaly_contract.NORMAL]
        self.assertGreater(len(normal), 5)

    def test_the_scan_is_deterministic(self):
        first = json.dumps(self.scan("spike").as_dict(), sort_keys=True)
        second = json.dumps(self.scan("spike").as_dict(), sort_keys=True)
        self.assertEqual(first, second)

    def test_the_scan_is_json_serialisable(self):
        json.dumps(self.scan("spike").as_dict())

    def test_sensitivity_is_recorded_on_the_set(self):
        self.assertEqual(self.scan("spike", sensitivity=detectors.HIGH).sensitivity,
                         detectors.HIGH)


class TestAnomalyMetrics(AnomalyCase):

    def test_the_supported_metrics_are_scanned_on_a_sales_extract(self):
        scanned = self.scan("spike").scanned_metrics
        for metric in ("revenue", "cost", "gross_profit", "gross_margin",
                       "order_count", "active_customers"):
            self.assertEqual(scanned[metric], anomaly_contract.AVAILABLE, metric)

    def test_operating_expense_and_cash_are_unavailable_and_named(self):
        scan = self.scan("spike")
        for metric in ("operating_expense", "cash_balance"):
            self.assertEqual(scan.scanned_metrics[metric],
                             anomaly_contract.UNAVAILABLE, metric)
        reasons = " ".join(item.reason for item in scan.limitations)
        self.assertIn("operating_expense", reasons)
        self.assertIn("cash_balance", reasons)

    def test_margin_is_unavailable_without_a_cost_column(self):
        scan = self.scan("no_cost")
        self.assertEqual(scan.scanned_metrics["gross_margin"],
                         anomaly_contract.UNAVAILABLE)

    def test_a_named_subset_of_metrics_can_be_requested(self):
        scan = self.scan("spike", metrics=["revenue"])
        self.assertEqual(sorted(scan.scanned_metrics), ["revenue"])

    def test_a_margin_anomaly_is_measured_in_percent_not_currency(self):
        scan = self.scan("spike")
        for observation in scan.by_metric("gross_margin"):
            self.assertIsNone(observation.currency)
            self.assertTrue(any("percentage point" in c for c in observation.caveats))


class TestAnomalyMateriality(AnomalyCase):

    def test_material_anomaly_requires_both_the_threshold_and_the_policy(self):
        scan = self.scan("spike")
        for observation in scan.flagged():
            if observation.status == anomaly_contract.MATERIAL_ANOMALY:
                self.assertEqual(observation.materiality, "material")

    def test_an_unusual_but_immaterial_deviation_is_not_a_material_anomaly(self):
        """The two vocabularies are independent; only agreement produces the top status."""
        from bops.anomaly import engine as anomaly_engine

        class Config:
            def get(self, key, default=None):
                # An absurdly high bar: nothing here can clear the materiality policy.
                return {"materiality.absolute_amount": D("10000000"),
                        "materiality.percentage": D("500")}.get(key, default)

            def source_of(self, key):
                return "test"

        values = [D("10000")] * 24
        values[18] = D("40000")
        series = [("2024-%02d" % (i + 1) if i < 12 else "2025-%02d" % (i - 11), v)
                  for i, v in enumerate(values)]
        observations, _reason = anomaly_engine.scan_series(
            series, anomaly_engine.METRICS[0], Config(), min_baseline=6)
        flagged = [o for o in observations if o.flagged]
        self.assertTrue(flagged)
        self.assertEqual({o.status for o in flagged}, {anomaly_contract.UNUSUAL})

    def test_no_second_threshold_system_is_introduced(self):
        """Materiality verdicts come from the existing policy, with its own reason text."""
        for observation in self.scan("spike").flagged():
            self.assertTrue(observation.materiality_reason)


class TestContributorAttribution(AnomalyCase):

    def test_a_flagged_period_names_where_the_deviation_sits(self):
        flags = self.revenue_flags("spike")
        self.assertTrue(flags[0].contributors)

    def test_contributors_carry_their_share_of_the_movement(self):
        for contributor in self.revenue_flags("spike")[0].contributors:
            self.assertIsNotNone(contributor.share_pct)
            self.assertIsNotNone(contributor.value)

    def test_attribution_can_be_switched_off(self):
        scan = pipeline.detect_anomalies(self.result("spike"))
        self.assertTrue(any(o.contributors for o in scan.flagged()))
        from bops.anomaly import engine as anomaly_engine
        without = anomaly_engine.run(self.result("spike"), attribute=False)
        self.assertFalse(any(o.contributors for o in without.flagged()))

    def test_attribution_never_asserts_a_cause(self):
        for observation in self.revenue_flags("spike"):
            for contributor in observation.contributors:
                lowered = contributor.label.lower()
                for word in anomaly_contract.CAUSAL_LANGUAGE:
                    self.assertNotIn(word, lowered)


class TestAnomalyPrivacy(AnomalyCase):

    def test_shareable_presentation_pseudonymises_identifying_contributors(self):
        scan = pipeline.detect_anomalies(
            self.result("one_customer"), presentation=presentation.SHAREABLE)
        for observation in scan.flagged():
            for contributor in observation.contributors:
                if contributor.dimension == "customer":
                    self.assertTrue(contributor.redacted)

    def test_no_observation_exposes_an_individual_transaction(self):
        scan = self.scan("spike")
        document = json.dumps(scan.as_dict())
        self.assertNotIn("SO-", document)

    def test_the_privacy_policy_is_the_existing_one(self):
        scan = pipeline.detect_anomalies(
            self.result("spike"), presentation=presentation.SHAREABLE)
        self.assertEqual(scan.presentation, presentation.SHAREABLE)

    def test_local_presentation_still_records_the_export_restriction(self):
        scan = self.scan("spike")
        self.assertEqual(scan.presentation, presentation.LOCAL)


class TestFraudBoundary(AnomalyCase):
    """The boundary M8 must never cross, asserted against every emitted string."""

    def strings(self, scan):
        """Every string the scan emits, except the boundary note itself.

        The note is the one sanctioned mention of the word: it exists to *deny* that an
        anomaly is evidence of fraud. Excluding it keeps the assertion pointed at the
        statements that describe the data.
        """
        out = []
        for observation in scan.observations:
            out.append(observation.statement())
            out.extend(observation.caveats)
        for finding in scan.findings:
            out.append(finding.statement)
            out.extend(finding.caveats)
        for item in scan.limitations:
            out.append(item.reason)
        return [text for text in out
                if text != anomaly_contract.INVESTIGATION_NOTE]

    def test_no_emitted_string_uses_fraud_vocabulary(self):
        for key in ("spike", "drop", "two"):
            for text in self.strings(self.scan(key)):
                lowered = text.lower()
                for word in anomaly_contract.FRAUD_LANGUAGE:
                    self.assertNotIn(word, lowered, "%s: %s" % (word, text))

    def test_no_emitted_string_asserts_a_cause(self):
        for text in self.strings(self.scan("spike")):
            lowered = text.lower()
            for word in anomaly_contract.CAUSAL_LANGUAGE:
                self.assertNotIn(word, lowered, "%s: %s" % (word, text))

    def test_every_flagged_finding_carries_the_investigation_note(self):
        scan = self.scan("spike")
        for finding in scan.findings:
            self.assertIn(anomaly_contract.INVESTIGATION_NOTE, finding.caveats)

    def test_the_rendered_report_carries_the_boundary_statement(self):
        run = commands.run("anomaly-detection", self.paths["spike"],
                           load_context_files=False)
        text = commands.render(run)
        self.assertIn("not evidence of fraud", text)

    def test_the_set_publishes_the_boundary_in_its_structured_output(self):
        self.assertEqual(self.scan("spike").as_dict()["fraud_boundary"],
                         anomaly_contract.INVESTIGATION_NOTE)


class TestAnomalyEvidence(AnomalyCase):

    def test_anomaly_findings_are_calculations(self):
        for finding in self.scan("spike").findings:
            self.assertEqual(finding.finding_type, analytics_contract.CALCULATION)
            self.assertEqual(finding.evidence_class, evidence.CALCULATED)

    def test_anomaly_claims_are_evidential_in_the_ledger(self):
        result = self.result("spike")
        pipeline.detect_anomalies(result)
        classes = {claim.provenance_class for claim in result.ledger.claims}
        self.assertIn(evidence.CALCULATED, classes)

    def test_every_finding_carries_the_baseline_as_structured_input(self):
        for finding in self.scan("spike").findings:
            self.assertIn("baseline_centre", finding.inputs)
            self.assertIn("baseline_method", finding.inputs)
            self.assertIn("threshold", finding.inputs)

    def test_every_finding_names_the_detector_as_its_basis(self):
        for finding in self.scan("spike").findings:
            self.assertTrue(finding.basis.startswith("anomaly."))

    def test_provenance_survives_onto_every_finding(self):
        for finding in self.scan("spike").findings:
            self.assertIn("source", finding.provenance)


class TestAnomalyQuality(AnomalyCase):

    def test_a_critical_halt_scans_nothing(self):
        from fixtures import build_fixtures as legacy
        path = legacy.critical_missing_revenue(self.directory)
        scan = pipeline.detect_anomalies(pipeline.run(path, load_context_files=False))
        self.assertEqual(scan.status, analytics_contract.UNAVAILABLE)
        self.assertEqual(scan.observations, [])
        self.assertEqual(scan.findings, [])

    def test_a_warning_travels_into_every_finding(self):
        from fixtures import build_fixtures as legacy
        path = legacy.warning_duplicates(self.directory)
        result = pipeline.run(path, load_context_files=False)
        if result.quality.grade != quality_contract.WARNING:
            self.skipTest("fixture did not produce a WARNING grade")
        scan = pipeline.detect_anomalies(result)
        for finding in scan.findings:
            self.assertTrue(finding.caveats)

    def test_quality_is_never_re_run_by_the_anomaly_layer(self):
        result = self.result("spike")
        before = result.quality.as_dict()
        pipeline.detect_anomalies(result)
        self.assertEqual(result.quality.as_dict(), before)

    def test_a_short_history_establishes_no_baseline(self):
        scan = self.scan("short")
        self.assertEqual(scan.scanned_metrics["revenue"],
                         anomaly_contract.INSUFFICIENT_DATA)
        reasons = " ".join(item.reason for item in scan.limitations)
        self.assertIn("baseline", reasons)


class TestAnomalyCommand(AnomalyCase):

    def run_command(self, key="spike", **kwargs):
        return commands.run("anomaly-detection", self.paths.get(key, key),
                            load_context_files=False, **kwargs)

    def test_the_command_drives_the_anomaly_engine(self):
        from bops.commands import registry
        self.assertEqual(registry.require("anomaly-detection").engine, "anomaly")

    def test_the_command_produces_an_anomaly_set(self):
        run = self.run_command()
        self.assertEqual(run.status, "ok")
        self.assertIsNotNone(run.anomaly_set)
        self.assertTrue(run.findings())

    def test_the_command_runs_no_historical_analytics_domain(self):
        self.assertEqual(sorted(self.run_command().analyses), ["anomaly"])

    def test_the_sensitivity_argument_reaches_the_engine(self):
        run = self.run_command(sensitivity=detectors.HIGH)
        self.assertEqual(run.anomaly_set.sensitivity, detectors.HIGH)

    def test_the_rendered_report_shows_coverage_and_flags(self):
        text = commands.render(self.run_command())
        self.assertIn("## Anomalies", text)
        self.assertIn("Periods checked", text)
        self.assertIn("Sensitivity", text)

    def test_the_rendered_report_names_the_baseline_for_each_flag(self):
        text = commands.render(self.run_command())
        self.assertIn("Baseline", text)

    def test_a_clean_dataset_renders_the_nothing_found_statement(self):
        text = commands.render(self.run_command("flat"))
        self.assertIn("found nothing unusual", text)

    def test_a_missing_file_is_a_structured_result(self):
        run = commands.run("anomaly-detection",
                           os.path.join(self.directory, "nope.csv"),
                           load_context_files=False)
        self.assertEqual(run.status, "unavailable")

    def test_the_command_result_is_json_serialisable(self):
        json.dumps(self.run_command().as_dict())

    def test_repeated_execution_renders_identically(self):
        self.assertEqual(commands.render(self.run_command()),
                         commands.render(self.run_command()))

    def test_the_demo_dataset_scans(self):
        run = commands.run("anomaly-detection", DEMO, load_context_files=False)
        self.assertEqual(run.status, "ok")
        self.assertTrue(run.anomaly_set.flagged())


if __name__ == "__main__":
    unittest.main()
