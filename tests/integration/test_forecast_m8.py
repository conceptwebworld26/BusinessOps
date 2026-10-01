"""Forecasting end to end: pipeline, engine, contract, command and rendered report.

The unit tests prove the arithmetic. These prove the things only a whole run can show: that
a forecast consumes the KPI and quality layers rather than re-deriving them, that its
findings enter the ledger as class 6, that scenarios and assumptions survive to the
rendered page, and that a target with no data is refused by name rather than estimated.
"""

import json
import os
import shutil
import tempfile
import unittest
from decimal import Decimal

from bops import commands, evidence, forecast, pipeline
from bops.analytics import contract as analytics_contract
from bops.forecast import contract as forecast_contract, engine, variance
from bops.quality import contract as quality_contract

from fixtures import build_forecast_fixtures as build

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")

D = Decimal


class ForecastCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m8-forecast-")
        cls.paths = {
            "trend": build.steady_trend(cls.directory),
            "flat": build.flat(cls.directory),
            "seasonal": build.seasonal(cls.directory),
            "gap": build.with_gap(cls.directory),
            "zero_tail": build.zero_tail(cls.directory),
            "short": build.short(cls.directory),
            "minimum": build.exactly_minimum(cls.directory),
            "long": build.long_history(cls.directory),
            "no_cost": build.no_cost(cls.directory),
        }

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def result(self, key):
        return pipeline.run(self.paths.get(key, key), load_context_files=False)

    def forecast(self, key, **kwargs):
        return pipeline.forecast(self.result(key), **kwargs)

    def revenue(self, key, **kwargs):
        return self.forecast(key, **kwargs).forecasts["revenue"]


class TestForecastProduction(ForecastCase):

    def test_a_clean_trend_produces_a_forecast(self):
        result = self.revenue("trend")
        self.assertEqual(result.status, forecast_contract.AVAILABLE)
        self.assertEqual(result.history_periods, 24)
        self.assertEqual(result.horizon, 6)

    def test_a_linear_ramp_selects_the_linear_trend_method(self):
        self.assertEqual(self.revenue("trend").method, "linear_trend")

    def test_the_forecast_periods_follow_the_last_observed_period(self):
        result = self.revenue("trend")
        self.assertEqual(result.forecast_period, "2026-01..2026-06")
        self.assertEqual([p.period for p in result.base().points],
                         ["2026-01", "2026-02", "2026-03",
                          "2026-04", "2026-05", "2026-06"])

    def test_a_ramp_is_extended_at_the_observed_step(self):
        """10000 rising by 500 a month for 24 months continues at 22000, 22500, ..."""
        points = self.revenue("trend").base().points
        self.assertEqual(points[0].value.quantize(D("1")), D("22000"))
        self.assertEqual(points[1].value.quantize(D("1")), D("22500"))

    def test_all_three_scenarios_are_produced(self):
        scenarios = self.revenue("trend").scenarios
        self.assertEqual(sorted(scenarios), ["base", "downside", "upside"])

    def test_upside_exceeds_base_which_exceeds_downside(self):
        result = self.revenue("flat")
        self.assertGreater(result.scenario("upside").total(),
                           result.scenario("base").total())
        self.assertGreater(result.scenario("base").total(),
                           result.scenario("downside").total())

    def test_every_scenario_states_its_assumption(self):
        for name, scenario in self.revenue("trend").scenarios.items():
            self.assertIsNotNone(scenario.assumption, name)
            self.assertTrue(scenario.assumption.statement, name)

    def test_the_assumption_register_is_populated_and_class_six(self):
        result = self.revenue("trend")
        self.assertGreaterEqual(len(result.assumptions), 4)
        for assumption in result.assumptions:
            self.assertEqual(assumption.as_dict()["evidence_class"],
                             evidence.ASSUMPTION)

    def test_continuity_is_always_an_explicit_assumption(self):
        statements = " ".join(self.revenue("trend").assumptions.statements()).lower()
        self.assertIn("continue", statements)

    def test_a_backtest_is_performed_and_reported(self):
        validation = self.revenue("trend").validation
        self.assertTrue(validation.performed)
        self.assertIsNotNone(validation.mape)
        self.assertIn("..", validation.training_period)
        self.assertIn("..", validation.validation_period)

    def test_the_uncertainty_band_comes_from_measured_error(self):
        result = self.revenue("trend")
        self.assertEqual(result.uncertainty.kind, forecast_contract.EMPIRICAL_ERROR)
        self.assertFalse(result.uncertainty.statistical_interval)

    def test_every_point_carries_its_band(self):
        for point in self.revenue("trend").base().points:
            self.assertIsNotNone(point.low)
            self.assertIsNotNone(point.high)
            self.assertLessEqual(point.low, point.value)
            self.assertGreaterEqual(point.high, point.value)

    def test_a_seasonal_series_can_select_the_seasonal_method(self):
        result = self.revenue("seasonal")
        self.assertEqual(result.status, forecast_contract.AVAILABLE)
        self.assertIn(result.method, ("seasonal_naive", "moving_average", "naive",
                                      "linear_trend", "drift"))
        self.assertIn("seasonal_naive",
                      [c["method"] for c in result.validation.candidates])

    def test_confidence_is_never_high_for_an_estimate(self):
        for key in ("trend", "flat", "seasonal", "long"):
            self.assertNotEqual(self.revenue(key).confidence, evidence.HIGH, key)

    def test_a_forecast_is_deterministic(self):
        first = self.revenue("trend").as_dict()
        second = self.revenue("trend").as_dict()
        self.assertEqual(json.dumps(first, sort_keys=True),
                         json.dumps(second, sort_keys=True))

    def test_the_forecast_set_is_json_serialisable(self):
        json.dumps(self.forecast("trend").as_dict())


class TestForecastTargets(ForecastCase):

    def test_gross_profit_is_forecast_when_revenue_and_cost_are_present(self):
        result = self.forecast("trend").forecasts["gross_profit"]
        self.assertEqual(result.status, forecast_contract.AVAILABLE)
        joined = " ".join(result.assumptions.statements()).lower()
        self.assertIn("revenue - cost", joined)

    def test_gross_profit_is_refused_without_a_cost_column(self):
        result = self.forecast("no_cost").forecasts["gross_profit"]
        self.assertEqual(result.status, forecast_contract.UNAVAILABLE)
        self.assertIn("cost", result.reason.lower())

    def test_operating_expense_is_never_inferred_from_cost_of_goods(self):
        result = self.forecast("trend").forecasts["operating_expense"]
        self.assertEqual(result.status, forecast_contract.UNAVAILABLE)
        self.assertIn("operating_expense", result.reason)
        self.assertIn("never inferred", result.reason)

    def test_cash_flow_is_never_derived_from_sales(self):
        result = self.forecast("trend").forecasts["cash_flow"]
        self.assertEqual(result.status, forecast_contract.UNAVAILABLE)
        self.assertIn("cash_balance", result.reason)
        self.assertIn("never derived", result.reason)

    def test_sales_is_not_a_second_forecast_path_for_revenue(self):
        """Sales is the revenue series; a separate target would give one question two
        answers."""
        self.assertNotIn("sales", engine.TARGET_IDS)

    def test_a_named_subset_of_targets_can_be_requested(self):
        forecasts = self.forecast("trend", targets=["revenue"]).forecasts
        self.assertEqual(sorted(forecasts), ["revenue"])


class TestForecastRefusal(ForecastCase):

    def test_a_short_history_is_refused_with_the_count_and_the_requirement(self):
        result = self.revenue("short")
        self.assertEqual(result.status, forecast_contract.INSUFFICIENT_DATA)
        self.assertIn("4 periods", result.reason)
        self.assertIn("12 are required", result.reason)

    def test_exactly_the_minimum_history_is_accepted(self):
        result = self.revenue("minimum")
        self.assertEqual(result.status, forecast_contract.AVAILABLE)
        self.assertEqual(result.history_periods, 12)

    def test_a_refused_forecast_still_carries_its_history_and_provenance(self):
        result = self.revenue("short")
        self.assertEqual(result.history_periods, 4)
        self.assertIn("source", result.provenance)

    def test_a_refusal_becomes_a_limitation_not_a_silent_gap(self):
        forecast_set = self.forecast("short")
        codes = [item.code for item in forecast_set.limitations]
        self.assertIn("forecast_insufficient_data", codes)

    def test_a_set_with_nothing_forecastable_reports_insufficient_data(self):
        forecast_set = self.forecast("short")
        self.assertEqual(forecast_set.status, forecast_contract.INSUFFICIENT_DATA)
        self.assertEqual(forecast_set.available_forecasts(), {})

    def test_an_over_long_horizon_is_reduced_and_the_reduction_is_stated(self):
        result = self.revenue("trend", horizon=20)
        self.assertEqual(result.horizon, 12)
        self.assertTrue(any("at most" in c for c in result.caveats))

    def test_the_horizon_ceiling_holds_on_a_long_history(self):
        result = self.revenue("long", horizon=40)
        self.assertEqual(result.horizon, engine.MAX_HORIZON)


class TestForecastEdgeShapes(ForecastCase):

    def test_a_constant_series_is_forecast_flat_with_a_default_band(self):
        result = self.revenue("flat")
        self.assertEqual(result.status, forecast_contract.AVAILABLE)
        values = {p.value for p in result.base().points}
        self.assertEqual(len(values), 1)
        self.assertTrue(any("same value" in c for c in result.caveats))

    def test_a_zero_tail_is_flagged_as_making_percentages_undefined(self):
        result = self.revenue("zero_tail")
        self.assertTrue(any("undefined" in c for c in result.caveats), result.caveats)

    def test_a_gap_is_reported_and_never_filled_with_zero(self):
        result = self.revenue("gap")
        joined = " ".join(result.caveats)
        self.assertIn("missing period", joined)
        self.assertIn("not a zero period", joined)

    def test_a_gap_forecasts_only_from_the_unbroken_recent_run(self):
        result = self.revenue("gap")
        self.assertTrue(any("unbroken" in c for c in result.caveats), result.caveats)


class TestForecastQualityAndContext(ForecastCase):

    def test_a_critical_halt_produces_no_forecast_at_all(self):
        from fixtures import build_fixtures as legacy
        path = legacy.critical_missing_revenue(self.directory)
        forecast_set = pipeline.forecast(
            pipeline.run(path, load_context_files=False))
        self.assertEqual(forecast_set.status, analytics_contract.UNAVAILABLE)
        self.assertEqual(forecast_set.forecasts, {})
        self.assertEqual(forecast_set.findings, [])

    def test_a_warning_survives_into_every_scenario_finding(self):
        from fixtures import build_fixtures as legacy
        path = legacy.warning_duplicates(self.directory)
        result = pipeline.run(path, load_context_files=False)
        if result.quality.grade != quality_contract.WARNING:
            self.skipTest("fixture did not produce a WARNING grade")
        forecast_set = pipeline.forecast(result)
        for finding in forecast_set.findings:
            self.assertTrue(finding.caveats)

    def test_quality_is_never_re_run_by_the_forecast_layer(self):
        result = self.result("trend")
        before = result.quality.as_dict()
        pipeline.forecast(result)
        self.assertEqual(result.quality.as_dict(), before)

    def test_the_currency_comes_from_the_existing_context_resolution(self):
        self.assertEqual(self.revenue("trend").currency, "USD")

    def test_the_quality_grade_travels_with_the_forecast(self):
        self.assertEqual(self.revenue("trend").quality_grade,
                         self.result("trend").quality.grade)


class TestForecastEvidence(ForecastCase):

    def test_forecast_findings_are_class_six_not_calculations(self):
        for finding in self.forecast("trend").findings:
            self.assertEqual(finding.finding_type, analytics_contract.ASSUMPTION)
            self.assertEqual(finding.evidence_class, evidence.ASSUMPTION)

    def test_forecast_claims_are_generative_in_the_ledger(self):
        result = self.result("trend")
        pipeline.forecast(result)
        classes = {claim.provenance_class for claim in result.ledger.claims}
        self.assertIn(evidence.ASSUMPTION, classes)
        self.assertTrue(evidence.ASSUMPTION in evidence.GENERATIVE)

    def test_every_finding_names_its_method_and_horizon(self):
        for finding in self.forecast("trend").findings:
            self.assertIn("method", finding.inputs)
            self.assertIn("horizon", finding.inputs)
            self.assertTrue(finding.basis)

    def test_every_finding_carries_the_uncertainty_and_validation_statements(self):
        for finding in self.forecast("trend").findings:
            joined = " ".join(finding.caveats)
            self.assertIn("not a statistical confidence interval", joined)

    def test_no_forecast_statement_promises_an_outcome(self):
        for finding in self.forecast("trend").findings:
            lowered = finding.statement.lower()
            for word in forecast_contract.FORBIDDEN_CERTAINTY:
                self.assertNotIn(word, lowered)

    def test_every_statement_names_itself_a_forecast(self):
        for finding in self.forecast("trend").findings:
            self.assertIn("forecast", finding.statement.lower())

    def test_actuals_are_never_merged_into_the_forecast_points(self):
        result = self.revenue("trend")
        history = {period for period, _v in result.history}
        for scenario in result.scenarios.values():
            for point in scenario.points:
                self.assertNotIn(point.period, history)


class TestForecastVersusActual(ForecastCase):

    def setUp(self):
        self.result_obj = self.result("trend")
        self.forecast_obj = pipeline.forecast(
            self.result_obj).forecasts["revenue"]
        self.config = self.result_obj.config

    def actuals(self, **overrides):
        base = {p.period: p.value for p in self.forecast_obj.base().points}
        base.update(overrides)
        return base

    def test_a_perfect_match_has_zero_variance(self):
        comparison = variance.compare(self.forecast_obj, self.actuals(), self.config)
        self.assertEqual(comparison["status"], forecast_contract.AVAILABLE)
        for row in comparison["comparisons"]:
            self.assertEqual(D(row["variance"]), D("0"))

    def test_an_actual_above_forecast_is_reported_as_such(self):
        period = self.forecast_obj.base().points[0].period
        actual = self.forecast_obj.base().points[0].value * D("2")
        comparison = variance.compare(self.forecast_obj,
                                      self.actuals(**{period: actual}), self.config)
        row = comparison["comparisons"][0]
        self.assertEqual(row["direction"], variance.OVER)
        self.assertGreater(D(row["variance"]), D("0"))
        self.assertAlmostEqual(float(D(row["variance_pct"])), 100.0, places=4)

    def test_materiality_comes_from_the_existing_policy(self):
        period = self.forecast_obj.base().points[0].period
        comparison = variance.compare(
            self.forecast_obj, self.actuals(**{period: D("1")}), self.config)
        self.assertIn(comparison["comparisons"][0]["materiality"],
                      ("material", "not_material", "undetermined"))

    def test_a_zero_forecast_withholds_the_percentage_and_says_why(self):
        row = variance.compare_period("2026-01", D("0"), D("500"), self.config)
        self.assertIsNone(row.variance_pct)
        self.assertIn("undefined", row.pct_withheld_reason)

    def test_an_unforecast_period_is_reported_as_uncovered(self):
        comparison = variance.compare(
            self.forecast_obj, self.actuals(**{"2030-01": D("5")}), self.config)
        self.assertIn("2030-01", comparison["uncovered"])

    def test_comparing_a_refused_forecast_returns_its_reason(self):
        refused = self.forecast("short").forecasts["revenue"]
        comparison = variance.compare(refused, {"2024-06": D("1")}, self.config)
        self.assertEqual(comparison["status"], forecast_contract.INSUFFICIENT_DATA)
        self.assertEqual(comparison["comparisons"], [])

    def test_variance_findings_are_calculations_not_assumptions(self):
        comparison = variance.compare(self.forecast_obj, self.actuals(), self.config)
        for finding in variance.findings(comparison, currency="USD"):
            self.assertEqual(finding.finding_type, analytics_contract.CALCULATION)

    def test_no_actuals_at_all_is_insufficient_data(self):
        comparison = variance.compare(self.forecast_obj, {}, self.config)
        self.assertEqual(comparison["status"], forecast_contract.INSUFFICIENT_DATA)


class TestForecastCommand(ForecastCase):

    def run_command(self, key="trend", **kwargs):
        return commands.run("revenue-forecast", self.paths.get(key, key),
                            load_context_files=False, **kwargs)

    def test_the_command_drives_the_forecast_engine(self):
        from bops.commands import registry
        self.assertEqual(registry.require("revenue-forecast").engine, "forecast")

    def test_the_command_produces_a_forecast_set(self):
        run = self.run_command()
        self.assertEqual(run.status, "ok")
        self.assertIsNotNone(run.forecast_set)
        self.assertEqual(len(run.findings()), 6)          # two targets x three scenarios

    def test_the_horizon_argument_reaches_the_engine(self):
        run = self.run_command(horizon=3)
        self.assertEqual(run.forecast_set.forecasts["revenue"].horizon, 3)

    def test_the_command_runs_no_historical_analytics_domain(self):
        run = self.run_command()
        self.assertEqual(sorted(run.analyses), ["forecast"])

    def test_a_missing_file_is_a_structured_result(self):
        run = commands.run("revenue-forecast",
                           os.path.join(self.directory, "nope.csv"),
                           load_context_files=False)
        self.assertEqual(run.status, "unavailable")
        self.assertIsNotNone(run.reason)

    def test_the_rendered_report_marks_every_figure_an_estimate(self):
        text = commands.render(self.run_command())
        self.assertIn("## Forecast", text)
        self.assertIn("estimate", text.lower())
        self.assertIn("never merged with actuals", text)

    def test_the_rendered_report_shows_scenarios_and_assumptions(self):
        text = commands.render(self.run_command())
        for name in ("base", "upside", "downside"):
            self.assertIn(name, text)
        self.assertIn("Assumption register", text)

    def test_the_rendered_report_states_the_backtest_and_the_band(self):
        text = commands.render(self.run_command())
        self.assertIn("Validation.", text)
        self.assertIn("not a statistical confidence interval", text)

    def test_the_rendered_report_names_what_could_not_be_forecast(self):
        text = commands.render(self.run_command())
        self.assertIn("Operating expense", text)
        self.assertIn("unavailable", text)

    def test_the_command_result_is_json_serialisable(self):
        json.dumps(self.run_command().as_dict())

    def test_repeated_execution_renders_identically(self):
        self.assertEqual(commands.render(self.run_command()),
                         commands.render(self.run_command()))

    def test_the_demo_dataset_forecasts(self):
        run = commands.run("revenue-forecast", DEMO, load_context_files=False)
        self.assertEqual(run.status, "ok")
        self.assertEqual(run.forecast_set.forecasts["revenue"].status,
                         forecast_contract.AVAILABLE)


if __name__ == "__main__":
    unittest.main()
