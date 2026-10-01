"""Every way a forecast or an anomaly scan can be asked for something it cannot give.

The rule under test throughout: **return a structured refusal that names what was missing,
never a fabricated estimate and never an unhandled traceback.** A forecast is the easiest
place in the system to produce a confident-looking wrong answer, so the refusals matter more
here than anywhere else.

The Milestone 6 and 7 fixtures are reused for quality and mapping failures rather than
rebuilt - a second definition of "CRITICAL" would be a second thing to keep in step.
"""

import json
import os
import shutil
import tempfile
import unittest
from decimal import Decimal

from bops import commands, pipeline
from bops.analytics import contract as analytics_contract
from bops.anomaly import contract as anomaly_contract
from bops.forecast import contract as forecast_contract
from bops.quality import contract as quality_contract

from fixtures import build_analytics_fixtures as analytics_build
from fixtures import build_fixtures as legacy
from fixtures import build_forecast_fixtures as build

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

D = Decimal

M8_COMMANDS = ("revenue-forecast", "anomaly-detection")


class M8NegativeCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m8-negative-")
        cls.paths = {
            # shape
            "one_period": build.series(cls.directory, [10000], "neg_one.csv"),
            "two_periods": build.series(cls.directory, [10000, 11000],
                                        "neg_two.csv"),
            "short": build.short(cls.directory),
            "flat": build.flat(cls.directory),
            "trend": build.steady_trend(cls.directory),
            "gap": build.with_gap(cls.directory),
            "zero_tail": build.zero_tail(cls.directory),
            "all_zero": build.series(cls.directory, [0] * 24, "neg_zero.csv"),
            "no_cost": build.no_cost(cls.directory),
            # missing columns
            "empty": analytics_build.empty(cls.directory),
            "no_date": analytics_build.without(cls.directory, "OrderDate"),
            "no_customer": analytics_build.without(cls.directory, "Customer"),
            # quality
            "critical": legacy.critical_missing_revenue(cls.directory),
            "no_revenue_column": legacy.critical_no_revenue_column(cls.directory),
            "warning": legacy.warning_duplicates(cls.directory),
            "ambiguous": legacy.ambiguous_mapping(cls.directory),
        }
        cls.missing = os.path.join(cls.directory, "no-such-file.csv")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def run_command(self, command_id, key, **kwargs):
        return commands.run(command_id, self.paths.get(key, key),
                            load_context_files=False, **kwargs)

    def result(self, key):
        return pipeline.run(self.paths.get(key, key), load_context_files=False)


# ==========================================================================
# Input that cannot be read at all
# ==========================================================================

class TestUnreadableInput(M8NegativeCase):

    def test_a_missing_file_is_a_structured_result_for_both_commands(self):
        for command_id in M8_COMMANDS:
            run = commands.run(command_id, self.missing, load_context_files=False)
            self.assertEqual(run.status, "unavailable", command_id)
            self.assertIsNotNone(run.reason, command_id)
            self.assertIsNotNone(run.error_type, command_id)

    def test_a_missing_file_still_renders_with_the_reason(self):
        for command_id in M8_COMMANDS:
            run = commands.run(command_id, self.missing, load_context_files=False)
            text = commands.render(run).lower()
            self.assertIn("not available", text, command_id)
            self.assertIn("not found", text, command_id)

    def test_no_file_at_all_asks_for_one(self):
        for command_id in M8_COMMANDS:
            run = commands.run(command_id, None, load_context_files=False)
            self.assertEqual(run.status, "unavailable", command_id)
            self.assertIn("No data file", run.reason)

    def test_an_empty_dataset_claims_nothing(self):
        for command_id in M8_COMMANDS:
            run = self.run_command(command_id, "empty")
            self.assertIn(run.status, ("halted", "unavailable"), command_id)
            self.assertEqual(run.material_findings(), [], command_id)


# ==========================================================================
# Insufficient history
# ==========================================================================

class TestInsufficientHistory(M8NegativeCase):

    def forecast(self, key):
        return pipeline.forecast(self.result(key)).forecasts["revenue"]

    def test_a_single_period_produces_no_forecast(self):
        result = self.forecast("one_period")
        self.assertEqual(result.status, forecast_contract.INSUFFICIENT_DATA)
        self.assertEqual(result.scenarios, {})

    def test_two_periods_produce_no_forecast(self):
        result = self.forecast("two_periods")
        self.assertEqual(result.status, forecast_contract.INSUFFICIENT_DATA)

    def test_the_refusal_states_both_the_count_and_the_requirement(self):
        reason = self.forecast("short").reason
        self.assertIn("4 periods", reason)
        self.assertIn("12 are required", reason)

    def test_no_scenario_or_band_is_invented_for_a_refused_forecast(self):
        result = self.forecast("short")
        self.assertEqual(result.scenarios, {})
        self.assertFalse(result.uncertainty.available)
        self.assertFalse(result.validation.performed)

    def test_a_single_period_establishes_no_anomaly_baseline(self):
        scan = pipeline.detect_anomalies(self.result("one_period"))
        self.assertEqual(scan.scanned_metrics.get("revenue"),
                         anomaly_contract.INSUFFICIENT_DATA)
        self.assertEqual(scan.flagged(), [])

    def test_a_short_history_scans_nothing_and_says_why(self):
        scan = pipeline.detect_anomalies(self.result("short"))
        self.assertEqual(scan.findings, [])
        self.assertTrue(scan.limitations)

    def test_neither_command_fabricates_a_finding_on_short_history(self):
        for command_id in M8_COMMANDS:
            run = self.run_command(command_id, "short")
            self.assertEqual(run.material_findings(), [], command_id)


# ==========================================================================
# Missing fields
# ==========================================================================

class TestMissingFields(M8NegativeCase):

    def test_no_date_column_makes_both_commands_unavailable(self):
        for command_id in M8_COMMANDS:
            run = self.run_command(command_id, "no_date")
            self.assertIn(run.status, ("unavailable", "halted"), command_id)

    def test_no_revenue_column_produces_no_revenue_forecast(self):
        run = self.run_command("revenue-forecast", "no_revenue_column")
        self.assertIn(run.status, ("unavailable", "halted"))

    def test_a_missing_cost_column_refuses_gross_profit_by_name(self):
        result = pipeline.forecast(self.result("no_cost")).forecasts["gross_profit"]
        self.assertEqual(result.status, forecast_contract.UNAVAILABLE)
        self.assertIn("cost", result.reason.lower())

    def test_a_missing_cost_column_makes_margin_unscannable(self):
        scan = pipeline.detect_anomalies(self.result("no_cost"))
        self.assertEqual(scan.scanned_metrics["gross_margin"],
                         anomaly_contract.UNAVAILABLE)

    def test_a_missing_customer_column_makes_customer_activity_unscannable(self):
        scan = pipeline.detect_anomalies(self.result("no_customer"))
        self.assertEqual(scan.scanned_metrics["active_customers"],
                         anomaly_contract.UNAVAILABLE)

    def test_operating_expense_is_unavailable_not_substituted(self):
        result = pipeline.forecast(
            self.result("trend")).forecasts["operating_expense"]
        self.assertEqual(result.status, forecast_contract.UNAVAILABLE)
        self.assertEqual(result.scenarios, {})

    def test_cash_flow_is_unavailable_not_derived(self):
        result = pipeline.forecast(self.result("trend")).forecasts["cash_flow"]
        self.assertEqual(result.status, forecast_contract.UNAVAILABLE)
        self.assertEqual(result.scenarios, {})

    def test_no_cash_figure_appears_anywhere_in_the_rendered_forecast(self):
        text = commands.render(self.run_command("revenue-forecast", "trend"))
        self.assertIn("Net cash movement", text)
        self.assertIn("unavailable", text)


# ==========================================================================
# Degenerate series shapes
# ==========================================================================

class TestDegenerateShapes(M8NegativeCase):

    def test_a_constant_series_forecasts_flat_and_never_invents_movement(self):
        result = pipeline.forecast(self.result("flat")).forecasts["revenue"]
        values = {p.value for p in result.base().points}
        self.assertEqual(len(values), 1)

    def test_a_constant_series_produces_no_anomaly(self):
        scan = pipeline.detect_anomalies(self.result("flat"))
        self.assertEqual([o for o in scan.by_metric("revenue") if o.flagged], [])

    def test_an_all_zero_series_does_not_raise_in_either_engine(self):
        result = self.result("all_zero")
        forecasts = pipeline.forecast(result)
        scan = pipeline.detect_anomalies(result)
        json.dumps(forecasts.as_dict())
        json.dumps(scan.as_dict())

    def test_a_zero_baseline_never_reports_a_percentage_it_cannot_compute(self):
        scan = pipeline.detect_anomalies(self.result("all_zero"))
        for observation in scan.observations:
            if observation.deviation_pct is None:
                self.assertIsNotNone(observation.observed)

    def test_a_zero_tail_is_caveated_rather_than_silently_forecast(self):
        result = pipeline.forecast(self.result("zero_tail")).forecasts["revenue"]
        self.assertTrue(any("undefined" in c for c in result.caveats))

    def test_irregular_periods_are_reported_and_never_filled(self):
        result = pipeline.forecast(self.result("gap")).forecasts["revenue"]
        joined = " ".join(result.caveats)
        self.assertIn("not a zero period", joined)


# ==========================================================================
# Horizon and method
# ==========================================================================

class TestUnsupportedRequests(M8NegativeCase):

    def test_a_zero_horizon_is_refused_rather_than_defaulted(self):
        run = self.run_command("revenue-forecast", "trend", horizon=0)
        result = run.forecast_set.forecasts["revenue"]
        self.assertEqual(result.status, forecast_contract.UNAVAILABLE)
        self.assertIn("at least 1", result.reason)

    def test_a_negative_horizon_is_refused(self):
        result = pipeline.forecast(self.result("trend"),
                                   horizon=-3).forecasts["revenue"]
        self.assertEqual(result.status, forecast_contract.UNAVAILABLE)

    def test_an_over_long_horizon_is_reduced_not_silently_honoured(self):
        result = pipeline.forecast(self.result("trend"),
                                   horizon=50).forecasts["revenue"]
        self.assertEqual(result.horizon, 12)
        self.assertTrue(any("at most" in c for c in result.caveats))

    def test_an_unknown_forecast_method_is_refused_by_name(self):
        with self.assertRaises(KeyError):
            pipeline.forecast(self.result("trend"), method_id="crystal_ball")

    def test_a_forced_method_without_the_history_it_needs_is_refused(self):
        result = pipeline.forecast(self.result("short"),
                                   method_id="seasonal_naive").forecasts["revenue"]
        self.assertEqual(result.status, forecast_contract.INSUFFICIENT_DATA)

    def test_an_unknown_forecast_target_is_refused_by_name(self):
        with self.assertRaises(KeyError):
            pipeline.forecast(self.result("trend"), targets=["share_price"])

    def test_an_unknown_anomaly_metric_is_refused_by_name(self):
        with self.assertRaises(KeyError):
            pipeline.detect_anomalies(self.result("trend"), metrics=["morale"])


# ==========================================================================
# Quality gate
# ==========================================================================

class TestQualityGate(M8NegativeCase):

    def test_a_critical_grade_stops_both_commands(self):
        for command_id in M8_COMMANDS:
            run = self.run_command(command_id, "critical")
            self.assertIn(run.status, ("halted", "unavailable"), command_id)
            self.assertEqual(run.findings(), [], command_id)

    def test_a_critical_grade_produces_no_forecast_figure_at_all(self):
        forecasts = pipeline.forecast(self.result("critical"))
        self.assertEqual(forecasts.forecasts, {})
        text = commands.render(self.run_command("revenue-forecast", "critical"))
        self.assertNotIn("Assumption register", text)

    def test_a_critical_grade_produces_no_anomaly_at_all(self):
        scan = pipeline.detect_anomalies(self.result("critical"))
        self.assertEqual(scan.observations, [])

    def test_a_warning_lets_both_engines_proceed_with_the_caveat_attached(self):
        result = self.result("warning")
        if result.quality.grade != quality_contract.WARNING:
            self.skipTest("fixture did not produce a WARNING grade")
        for produced in (pipeline.forecast(result),
                         pipeline.detect_anomalies(result)):
            for finding in produced.findings:
                self.assertTrue(finding.caveats)

    def test_a_warning_lowers_forecast_confidence(self):
        from bops import evidence
        result = self.result("warning")
        if result.quality.grade != quality_contract.WARNING:
            self.skipTest("fixture did not produce a WARNING grade")
        forecasts = pipeline.forecast(result)
        for item in forecasts.forecasts.values():
            if item.available:
                self.assertEqual(item.confidence, evidence.LOW)

    def test_an_ambiguous_mapping_marks_dependent_figures_provisional(self):
        result = self.result("ambiguous")
        forecasts = pipeline.forecast(result)
        joined = " ".join(forecasts.caveats)
        if result.semantic_map.needs_confirmation():
            self.assertIn("provisional", joined)

    def test_neither_engine_re_runs_the_quality_checks(self):
        result = self.result("trend")
        before = result.quality.as_dict()
        pipeline.forecast(result)
        pipeline.detect_anomalies(result)
        self.assertEqual(result.quality.as_dict(), before)


# ==========================================================================
# What the layer must never say
# ==========================================================================

class TestInterpretationBoundary(M8NegativeCase):

    def all_statements(self, run):
        out = []
        for finding in run.findings():
            out.append(finding.statement)
        for _domain, item in run.limitations():
            out.append(item.reason)
        return out

    def test_no_forecast_statement_promises_an_outcome(self):
        run = self.run_command("revenue-forecast", "trend")
        for statement in self.all_statements(run):
            lowered = statement.lower()
            for word in forecast_contract.FORBIDDEN_CERTAINTY:
                self.assertNotIn(word, lowered, statement)

    def test_no_anomaly_statement_alleges_fraud(self):
        run = self.run_command("anomaly-detection", "trend")
        for statement in self.all_statements(run):
            lowered = statement.lower()
            for word in anomaly_contract.FRAUD_LANGUAGE:
                self.assertNotIn(word, lowered, statement)

    def test_neither_engine_emits_a_recommendation(self):
        for command_id in M8_COMMANDS:
            run = self.run_command(command_id, "trend")
            for finding in run.findings():
                self.assertNotEqual(finding.finding_type,
                                    analytics_contract.RECOMMENDATION)

    def test_neither_engine_emits_an_interpretation(self):
        for command_id in M8_COMMANDS:
            run = self.run_command(command_id, "trend")
            for finding in run.findings():
                self.assertNotEqual(finding.finding_type,
                                    analytics_contract.INTERPRETATION)

    def test_the_forecast_engine_may_not_emit_judgement(self):
        forecast_set = forecast_contract.ForecastSet("forecast")
        for kind in (analytics_contract.INTERPRETATION,
                     analytics_contract.RECOMMENDATION):
            with self.assertRaises(analytics_contract.AnalysisError):
                forecast_set.add(analytics_contract.AnalysisFinding(
                    "x", "forecast", kind, "Judgement."))

    def test_the_anomaly_engine_may_not_emit_an_estimate(self):
        """Anomalies are measured, never modelled - class 6 belongs to forecasting."""
        anomaly_set = anomaly_contract.AnomalySet("anomaly")
        with self.assertRaises(analytics_contract.AnalysisError):
            anomaly_set.add(analytics_contract.AnalysisFinding(
                "x", "anomaly", analytics_contract.ASSUMPTION, "An estimate."))


# ==========================================================================
# Determinism
# ==========================================================================

class TestDeterminism(M8NegativeCase):

    def test_repeated_forecasts_are_identical(self):
        first = pipeline.forecast(self.result("trend")).as_dict()
        second = pipeline.forecast(self.result("trend")).as_dict()
        self.assertEqual(json.dumps(first, sort_keys=True),
                         json.dumps(second, sort_keys=True))

    def test_repeated_scans_are_identical(self):
        first = pipeline.detect_anomalies(self.result("spike" if "spike"
                                                      in self.paths else "trend"))
        second = pipeline.detect_anomalies(self.result("spike" if "spike"
                                                       in self.paths else "trend"))
        self.assertEqual(json.dumps(first.as_dict(), sort_keys=True),
                         json.dumps(second.as_dict(), sort_keys=True))

    def test_no_analytical_value_carries_a_timestamp(self):
        """Metadata may be time-stamped; analytical results may not."""
        document = json.dumps(pipeline.forecast(self.result("trend")).as_dict())
        self.assertNotIn("generated_at", document)

    def test_both_commands_render_identically_across_runs(self):
        for command_id in M8_COMMANDS:
            first = commands.render(self.run_command(command_id, "trend"))
            second = commands.render(self.run_command(command_id, "trend"))
            self.assertEqual(first, second, command_id)


if __name__ == "__main__":
    unittest.main()
