"""The forecasting primitives: methods, adequacy, history preparation, backtest, horizon.

All pure. A forecast method is arithmetic over a list of numbers, so it is tested against
hand-computed expectations rather than against a dataset - if `linear_trend` cannot extend
1, 2, 3 to 4, no amount of pipeline integration will save it.
"""

import unittest
from decimal import Decimal

from bops.forecast import contract, engine, methods, series, validate

D = Decimal


def pairs(values):
    """('2024-01', v), ('2024-02', v), ... for a list of numbers.

    Built with `series.step` rather than a local date helper, so a change to the engine's
    period arithmetic shows up here rather than being masked by a second implementation.
    """
    return [(series.step("2024-01", index), D(str(value)))
            for index, value in enumerate(values)]


class TestMethods(unittest.TestCase):

    def test_every_method_declares_an_adequacy_predicate(self):
        for method in methods.METHODS:
            self.assertGreaterEqual(method.min_periods, 2, method.method_id)
            self.assertTrue(method.rationale, method.method_id)

    def test_naive_repeats_the_last_value(self):
        got = methods.get("naive").project(pairs([5, 7, 9]), 3)
        self.assertEqual(got, [D("9")] * 3)

    def test_moving_average_holds_the_recent_mean_flat(self):
        got = methods.get("moving_average").project(pairs([10, 20, 30, 40]), 2)
        self.assertEqual(got, [D("30")] * 2)          # mean of 20, 30, 40

    def test_drift_continues_the_average_step_from_the_last_value(self):
        got = methods.get("drift").project(pairs([10, 12, 14, 16]), 2)
        self.assertEqual(got, [D("18"), D("20")])

    def test_linear_trend_extends_a_straight_line_exactly(self):
        got = methods.get("linear_trend").project(pairs([1, 2, 3, 4, 5, 6]), 3)
        self.assertEqual([g.quantize(D("0.0001")) for g in got],
                         [D("7.0000"), D("8.0000"), D("9.0000")])

    def test_seasonal_naive_copies_the_same_month_a_year_earlier(self):
        values = list(range(1, 25))                    # 24 periods
        got = methods.get("seasonal_naive").project(pairs(values), 3)
        self.assertEqual(got, [D("13"), D("14"), D("15")])

    def test_adequacy_gates_a_method_from_running_at_all(self):
        short = pairs([1, 2, 3])
        self.assertFalse(methods.get("seasonal_naive").adequate_for(short))
        with self.assertRaises(ValueError):
            methods.get("seasonal_naive").project(short, 1)

    def test_adequate_returns_only_supportable_methods(self):
        adequate = [m.method_id for m in methods.adequate(pairs([1, 2, 3, 4]))]
        self.assertIn("naive", adequate)
        self.assertIn("drift", adequate)
        self.assertNotIn("seasonal_naive", adequate)

    def test_inadequate_reports_how_many_periods_short(self):
        shortfalls = dict((m.method_id, n)
                          for m, n in methods.inadequate(pairs([1, 2, 3])))
        self.assertEqual(shortfalls["seasonal_naive"], 10)

    def test_a_horizon_of_zero_produces_no_points(self):
        self.assertEqual(methods.get("naive").project(pairs([1, 2]), 0), [])

    def test_methods_are_deterministic(self):
        history = pairs([3, 1, 4, 1, 5, 9, 2, 6])
        for method in methods.METHODS:
            if not method.adequate_for(history):
                continue
            self.assertEqual(method.project(history, 4), method.project(history, 4),
                             method.method_id)


class TestSeriesPreparation(unittest.TestCase):

    def test_period_arithmetic_crosses_a_year_boundary(self):
        self.assertEqual(series.step("2024-11", 3), "2025-02")
        self.assertEqual(series.step("2024-01", -1), "2023-12")

    def test_horizon_periods_follow_the_last_observed_period(self):
        self.assertEqual(series.horizon_periods("2025-12", 3),
                         ["2026-01", "2026-02", "2026-03"])

    def test_find_gaps_names_every_missing_month(self):
        observed = [("2024-01", D("1")), ("2024-04", D("2"))]
        self.assertEqual(series.find_gaps(observed), ["2024-02", "2024-03"])

    def test_longest_contiguous_takes_the_run_ending_at_the_present(self):
        observed = [("2024-01", D("1")), ("2024-02", D("2")),
                    ("2024-09", D("3")), ("2024-10", D("4")), ("2024-11", D("5"))]
        self.assertEqual([p for p, _v in series.longest_contiguous(observed)],
                         ["2024-09", "2024-10", "2024-11"])

    def test_a_constant_history_is_recognised_and_has_zero_volatility(self):
        history = series.History("Revenue", pairs([7, 7, 7, 7]))
        self.assertTrue(history.constant())
        self.assertEqual(history.volatility_pct(), D("0"))

    def test_volatility_is_none_only_when_no_move_could_be_measured(self):
        self.assertIsNone(series.History("Revenue", pairs([7])).volatility_pct())
        self.assertIsNone(series.History("Revenue", pairs([0, 0])).volatility_pct())

    def test_zero_baseline_is_recognised_from_the_recent_periods(self):
        history = series.History("Revenue", pairs([5, 5, 0, 0, 0]))
        self.assertTrue(history.zero_baseline())

    def test_volatility_skips_a_zero_predecessor_rather_than_dividing_by_it(self):
        history = series.History("Revenue", pairs([0, 100, 110]))
        self.assertEqual(history.volatility_pct(), D("10"))

    def test_derived_uses_only_periods_present_in_both_series(self):
        revenue = [("2024-01", D("100")), ("2024-02", D("200"))]
        cost = [("2024-02", D("50"))]
        self.assertEqual(series.derived(revenue, cost, "Gross profit"),
                         [("2024-02", D("150"))])

    def test_derived_returns_nothing_when_no_period_overlaps(self):
        self.assertIsNone(series.derived([("2024-01", D("1"))],
                                         [("2024-02", D("1"))], "Gross profit"))


class TestValidation(unittest.TestCase):

    def history(self, values):
        return series.History("Revenue", pairs(values))

    def test_a_short_history_holds_nothing_back(self):
        self.assertEqual(validate.holdout_size(4, 6), 0)

    def test_holdout_never_exceeds_a_third_of_the_history(self):
        self.assertLessEqual(validate.holdout_size(24, 12), 8)

    def test_a_perfect_line_backtests_to_almost_no_error(self):
        history = self.history([100 + 10 * i for i in range(24)])
        chosen, validation, _scored = validate.select(history, 6)
        self.assertEqual(validation.status, contract.AVAILABLE)
        self.assertEqual(chosen.method_id, "linear_trend")
        self.assertLess(validation.mape, D("0.001"))

    def test_selection_reports_every_candidate_it_compared(self):
        history = self.history([100 + 10 * i for i in range(24)])
        _chosen, validation, _scored = validate.select(history, 6)
        compared = {c["method"] for c in validation.candidates}
        self.assertIn("naive", compared)
        self.assertIn("linear_trend", compared)

    def test_without_a_backtest_the_validation_says_so_rather_than_claiming_error(self):
        _chosen, validation, _scored = validate.select(self.history([1, 2, 3, 4]), 3)
        self.assertEqual(validation.status, contract.INSUFFICIENT_DATA)
        self.assertIsNone(validation.mape)
        self.assertIn("too short", validation.reason)

    def test_a_forced_method_below_its_minimum_is_refused(self):
        chosen, validation, _s = validate.select(self.history([1, 2, 3, 4]), 2,
                                                 preferred="seasonal_naive")
        self.assertIsNone(chosen)
        self.assertEqual(validation.status, contract.INSUFFICIENT_DATA)

    def test_selection_is_deterministic(self):
        history = self.history([100, 120, 90, 130, 110, 140, 105, 150,
                                115, 160, 125, 170, 130, 180, 140, 190,
                                150, 200, 160, 210, 170, 220, 180, 230])
        first = validate.select(history, 6)[0].method_id
        second = validate.select(history, 6)[0].method_id
        self.assertEqual(first, second)

    def test_mape_ignores_a_zero_actual_and_counts_it(self):
        mae, mape, skipped = validate._errors([D("0"), D("100")], [D("10"), D("110")])
        self.assertEqual(skipped, 1)
        self.assertEqual(mape, D("10"))
        self.assertEqual(mae, D("10"))


class TestHorizon(unittest.TestCase):

    class Config:
        def __init__(self, values=None):
            self.values = values or {}

        def get(self, key, default=None):
            return self.values.get(key, default)

    def test_the_default_horizon_comes_from_configuration(self):
        horizon, note = engine.resolve_horizon(
            None, 24, self.Config({"forecast.default_horizon_periods": 4}))
        self.assertEqual(horizon, 4)
        self.assertIsNone(note)

    def test_a_horizon_beyond_half_the_history_is_reduced_and_explained(self):
        horizon, note = engine.resolve_horizon(12, 12, self.Config())
        self.assertEqual(horizon, 6)
        self.assertIn("at most", note)

    def test_the_absolute_ceiling_applies_however_long_the_history(self):
        horizon, _note = engine.resolve_horizon(100, 600, self.Config())
        self.assertEqual(horizon, engine.MAX_HORIZON)

    def test_a_horizon_below_one_is_refused(self):
        horizon, note = engine.resolve_horizon(0, 24, self.Config())
        self.assertIsNone(horizon)
        self.assertIn("at least 1", note)


class TestContract(unittest.TestCase):

    def test_an_uncertainty_band_is_never_a_statistical_interval(self):
        band = contract.UncertaintyBand(contract.EMPIRICAL_ERROR, pct=D("10"),
                                        basis="backtest")
        self.assertFalse(band.statistical_interval)
        self.assertIn("not a statistical confidence interval", band.statement())

    def test_band_bounds_are_symmetric_around_the_value(self):
        band = contract.UncertaintyBand(contract.EMPIRICAL_ERROR, pct=D("10"))
        low, high = band.bounds(D("100"))
        self.assertEqual((low, high), (D("90"), D("110")))

    def test_an_absent_band_produces_no_bounds_and_says_so(self):
        band = contract.UncertaintyBand(contract.NO_BAND)
        self.assertEqual(band.bounds(D("100")), (None, None))
        self.assertIn("No uncertainty band", band.statement())

    def test_an_unknown_band_kind_is_a_defect(self):
        with self.assertRaises(contract.ForecastError):
            contract.UncertaintyBand("wishful_thinking")

    def test_an_unknown_scenario_is_a_defect(self):
        with self.assertRaises(contract.ForecastError):
            contract.Scenario("miracle", D("0"), "naive")

    def test_the_assumption_register_is_enumerable_and_class_six(self):
        register = contract.AssumptionRegister()
        register.add("a1", "Revenue", "Conditions continue.")
        self.assertEqual(len(register), 1)
        self.assertEqual(register.as_dict()[0]["evidence_class"], 6)

    def test_scenario_specific_assumptions_are_scoped_to_their_scenario(self):
        register = contract.AssumptionRegister()
        register.add("shared", "Revenue", "Shared.")
        register.add("up", "Revenue", "Upside only.", scenario=contract.UPSIDE)
        self.assertEqual(len(register.for_scenario(contract.BASE)), 1)
        self.assertEqual(len(register.for_scenario(contract.UPSIDE)), 2)

    def test_a_forecast_set_may_emit_class_six_but_never_judgement(self):
        from bops.analytics import contract as analytics_contract
        forecast_set = contract.ForecastSet("forecast")
        assumption = analytics_contract.AnalysisFinding(
            "f1", "forecast", analytics_contract.ASSUMPTION, "An estimate.")
        forecast_set.add(assumption)
        self.assertEqual(len(forecast_set.findings), 1)
        with self.assertRaises(analytics_contract.AnalysisError):
            forecast_set.add(analytics_contract.AnalysisFinding(
                "f2", "forecast", analytics_contract.RECOMMENDATION, "Do this."))

    def test_the_historical_analytics_contract_still_refuses_class_six(self):
        """M6 must not have been widened by M8."""
        from bops.analytics import contract as analytics_contract
        analysis = analytics_contract.AnalysisSet("sales")
        with self.assertRaises(analytics_contract.AnalysisError):
            analysis.add(analytics_contract.AnalysisFinding(
                "s1", "sales", analytics_contract.ASSUMPTION, "An estimate."))


if __name__ == "__main__":
    unittest.main()
