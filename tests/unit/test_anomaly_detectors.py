"""The anomaly primitives: baselines, detectors, statuses and the fraud boundary.

All pure. A detector is arithmetic over a list of numbers, so the tests build the shape
they want - flat, trending, spiked - rather than reaching for a dataset.

The most important tests here are the ones that assert what the layer refuses to say: no
fraud vocabulary, no causal vocabulary, and no flag on a series where nothing happened.
"""

import unittest
from decimal import Decimal

from bops.anomaly import baselines, contract, detectors

D = Decimal


def pairs(values, start_year=2024, start_month=1):
    out = []
    for index, value in enumerate(values):
        total = start_year * 12 + (start_month - 1) + index
        out.append(("%04d-%02d" % (total // 12, total % 12 + 1), D(str(value))))
    return out


class Config:
    """Minimal stand-in for the resolved configuration."""

    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def source_of(self, key):
        return "test"


class TestStatistics(unittest.TestCase):

    def test_median_of_an_odd_list(self):
        self.assertEqual(baselines.median([D("3"), D("1"), D("2")]), D("2"))

    def test_median_of_an_even_list_averages_the_middle(self):
        self.assertEqual(baselines.median([D("1"), D("2"), D("3"), D("4")]),
                         D("2.5"))

    def test_mad_is_unmoved_by_a_single_extreme_value(self):
        ordinary = [D("10")] * 8 + [D("11")]
        with_outlier = ordinary + [D("1000")]
        self.assertEqual(baselines.mad(ordinary), baselines.mad(with_outlier))

    def test_stdev_needs_two_points(self):
        self.assertIsNone(baselines.stdev([D("5")]))

    def test_everything_stays_decimal(self):
        values = [D("1.1"), D("2.2"), D("3.3")]
        for computed in (baselines.mean(values), baselines.median(values),
                         baselines.mad(values), baselines.stdev(values)):
            self.assertIsInstance(computed, Decimal)

    def test_the_trailing_window_never_includes_the_period_being_judged(self):
        series = pairs([1, 2, 3, 4, 5])
        window = baselines.trailing_window(series, 4, 12)
        self.assertEqual(window, [D("1"), D("2"), D("3"), D("4")])


class TestBaselines(unittest.TestCase):

    def test_a_linear_ramp_is_predicted_exactly_and_leaves_no_spread(self):
        """The property that matters: on a straight ramp nothing is anomalous."""
        series = pairs([100 + 10 * i for i in range(8)])
        centre, spread, periods = baselines.rolling_median_baseline(series, 7, 12)
        self.assertEqual(periods, 7)
        self.assertEqual(centre, D("170"))            # the value actually observed at 7
        self.assertEqual(spread, D("0"))

    def test_a_growth_baseline_carries_the_typical_step_forward(self):
        series = pairs([100, 110, 121, 133.1])
        centre, _spread, periods = baselines.rolling_median_baseline(series, 3, 12)
        self.assertEqual(periods, 3)
        # Steps of 10 and 11 over the window; the median step of 10.5 is carried forward.
        self.assertEqual(centre, D("131.5"))

    def test_a_compounding_series_leaves_a_little_spread(self):
        """An additive baseline does not model compounding exactly, and says so through
        a non-zero spread rather than by pretending to a perfect fit."""
        series = pairs([100, 110, 121, 133.1, 146.41])
        _centre, spread, _p = baselines.rolling_median_baseline(series, 4, 12)
        self.assertGreater(spread, D("0"))

    def test_a_flat_series_expects_the_same_level_again(self):
        series = pairs([50] * 6)
        centre, spread, _p = baselines.rolling_median_baseline(series, 5, 12)
        self.assertEqual(centre, D("50"))
        self.assertEqual(spread, D("0"))

    def test_an_all_zero_window_falls_back_to_the_level(self):
        series = pairs([0, 0, 0, 5])
        centre, _spread, _p = baselines.rolling_median_baseline(series, 3, 12)
        self.assertEqual(centre, D("0"))

    def test_the_seasonal_baseline_carries_last_year_forward_by_the_growth_rate(self):
        # Two full years, every month exactly double the year before.
        values = [100 + i for i in range(12)] + [2 * (100 + i) for i in range(12)]
        series = pairs(values)
        centre, _spread, periods = baselines.seasonal_baseline(series, 20)
        self.assertGreater(periods, 0)
        # Month 20 is 2024-09 doubled; expecting last year's 108 grown by ~100%.
        self.assertAlmostEqual(float(centre), 216.0, places=4)

    def test_the_seasonal_baseline_refuses_before_one_full_year_on_year_pair(self):
        series = pairs(list(range(1, 26)))
        centre, _spread, _p = baselines.seasonal_baseline(series, 12)
        self.assertIsNone(centre)

    def test_year_over_year_rates_skip_a_zero_prior(self):
        values = [0] * 12 + [100] * 12
        rates = baselines.year_over_year_rates(pairs(values), 20)
        self.assertTrue(all(isinstance(r, Decimal) for r in rates))
        self.assertEqual(len(rates), 0)


class TestDetectors(unittest.TestCase):

    def test_every_detector_declares_an_adequacy_predicate_and_thresholds(self):
        for detector in detectors.DETECTORS:
            self.assertGreaterEqual(detector.min_periods, 4, detector.detector_id)
            for sensitivity in detectors.SENSITIVITIES:
                self.assertIsInstance(detector.threshold(sensitivity), Decimal)

    def test_sensitivity_lowers_the_bar_without_changing_the_arithmetic(self):
        for detector in detectors.DETECTORS:
            self.assertLess(detector.threshold(detectors.HIGH),
                            detector.threshold(detectors.LOW), detector.detector_id)

    def test_an_unknown_sensitivity_falls_back_to_medium(self):
        self.assertEqual(detectors.resolve_sensitivity(
            Config({"anomaly.sensitivity": "paranoid"})), detectors.MEDIUM)
        self.assertEqual(detectors.resolve_sensitivity(None), detectors.MEDIUM)

    def test_a_detector_below_its_minimum_is_not_adequate(self):
        series = pairs([1, 2, 3, 4, 5])
        adequate = [d.detector_id for d in detectors.adequate(series, 4)]
        self.assertIn("robust_deviation", adequate)
        self.assertNotIn("seasonal_deviation", adequate)

    def test_a_spike_scores_far_above_the_threshold(self):
        series = pairs([100, 102, 98, 101, 99, 100, 103, 500])
        measured = detectors.get("mean_deviation").measure(series, 7, 12,
                                                           detectors.MEDIUM)
        _baseline, _dev, _pct, score, threshold = measured
        self.assertGreater(score, threshold)

    def test_an_ordinary_period_scores_below_the_threshold(self):
        series = pairs([100, 102, 98, 101, 99, 100, 103, 101])
        measured = detectors.get("mean_deviation").measure(series, 7, 12,
                                                           detectors.MEDIUM)
        _baseline, _dev, _pct, score, threshold = measured
        self.assertLess(score, threshold)

    def test_a_flat_baseline_is_scored_on_percentage_and_says_so(self):
        series = pairs([100, 100, 100, 100, 100, 150])
        measured = detectors.get("robust_deviation").measure(series, 5, 12,
                                                             detectors.MEDIUM)
        baseline, _dev, _pct, score, _threshold = measured
        self.assertIn("percentage change", baseline.description)
        self.assertEqual(score, D("50"))

    def test_a_catalogue_is_machine_readable(self):
        import json
        json.dumps(detectors.catalogue())

    def test_an_unknown_detector_is_refused_by_name(self):
        with self.assertRaises(KeyError):
            detectors.get("vibes")


class TestObservationContract(unittest.TestCase):

    def observation(self, status=contract.UNUSUAL):
        baseline = contract.Baseline("mean_deviation", D("100"), spread=D("5"),
                                     periods=6, description="trailing mean")
        return contract.Observation(
            "revenue", "2025-03", D("160"), baseline, deviation=D("60"),
            deviation_pct=D("60"), score=D("12"), score_unit="sigma",
            threshold=D("2.5"), status=status, direction=contract.ABOVE,
            method="mean_deviation", metric_name="Revenue", currency="USD")

    def test_an_unknown_status_is_a_defect(self):
        with self.assertRaises(contract.AnomalyError):
            contract.Observation("revenue", "2025-01", D("1"), None, status="scary")

    def test_a_statement_names_the_baseline_it_was_measured_against(self):
        statement = self.observation().statement()
        self.assertIn("baseline", statement)
        self.assertIn("trailing mean", statement)
        self.assertIn("2025-03", statement)

    def test_no_statement_uses_fraud_vocabulary(self):
        statement = self.observation().statement().lower()
        for word in contract.FRAUD_LANGUAGE:
            self.assertNotIn(word, statement)

    def test_no_statement_asserts_a_cause(self):
        statement = self.observation().statement().lower()
        for word in contract.CAUSAL_LANGUAGE:
            self.assertNotIn(word, statement)

    def test_a_flagged_finding_carries_the_investigation_note(self):
        finding = self.observation().finding()
        self.assertIn(contract.INVESTIGATION_NOTE, finding.caveats)

    def test_a_normal_observation_carries_no_investigation_note(self):
        finding = self.observation(status=contract.NORMAL).finding()
        self.assertNotIn(contract.INVESTIGATION_NOTE, finding.caveats)

    def test_an_anomaly_is_a_calculation_not_an_assumption(self):
        from bops.analytics import contract as analytics_contract
        finding = self.observation().finding()
        self.assertEqual(finding.finding_type, analytics_contract.CALCULATION)
        self.assertEqual(finding.evidence_class, 4)

    def test_the_finding_carries_the_baseline_and_score_as_structured_inputs(self):
        inputs = self.observation().finding().inputs
        self.assertEqual(inputs["baseline_centre"], D("100"))
        self.assertEqual(inputs["baseline_method"], "mean_deviation")
        self.assertEqual(inputs["threshold"], D("2.5"))

    def test_only_flagged_observations_become_findings(self):
        anomaly_set = contract.AnomalySet("anomaly")
        anomaly_set.observe(self.observation(status=contract.NORMAL))
        self.assertEqual(len(anomaly_set.findings), 0)
        anomaly_set.observe(self.observation(status=contract.MATERIAL_ANOMALY))
        self.assertEqual(len(anomaly_set.findings), 1)
        self.assertEqual(len(anomaly_set.observations), 2)

    def test_the_set_reports_its_own_coverage(self):
        anomaly_set = contract.AnomalySet("anomaly")
        anomaly_set.observe(self.observation(status=contract.NORMAL))
        summary = anomaly_set.summary()
        self.assertEqual(summary["observations"], 1)
        self.assertEqual(summary["flagged"], 0)


class TestScanSeries(unittest.TestCase):
    """`scan_series` without a dataset - the pure core of the engine."""

    def scan(self, values, **kwargs):
        from bops.anomaly import engine
        metric = engine.METRICS[0]                       # revenue, currency
        config = Config({"materiality.absolute_amount": 1000,
                         "materiality.percentage": 5.0})
        return engine.scan_series(pairs(values), metric, config,
                                  min_baseline=kwargs.pop("min_baseline", 6), **kwargs)

    def test_a_constant_series_flags_nothing(self):
        observations, reason = self.scan([100] * 24)
        self.assertIsNone(reason)
        self.assertEqual([o for o in observations if o.flagged], [])

    def test_a_steady_trend_flags_nothing(self):
        observations, reason = self.scan([100 + 10 * i for i in range(24)])
        self.assertIsNone(reason)
        self.assertEqual([o for o in observations if o.flagged], [])

    def test_an_isolated_spike_is_flagged(self):
        values = [10000] * 24
        values[18] = 40000
        observations, _reason = self.scan(values)
        flagged = [o for o in observations if o.flagged]
        self.assertEqual([o.period for o in flagged], ["2025-07"])
        self.assertEqual(flagged[0].direction, contract.ABOVE)

    def test_an_isolated_drop_is_flagged(self):
        values = [10000] * 24
        values[18] = 2000
        observations, _reason = self.scan(values)
        flagged = [o for o in observations if o.flagged]
        self.assertEqual([o.period for o in flagged], ["2025-07"])
        self.assertEqual(flagged[0].direction, contract.BELOW)

    def test_multiple_anomalies_are_all_reported(self):
        values = [10000] * 24
        values[14] = 30000
        values[20] = 2000
        observations, _reason = self.scan(values)
        self.assertEqual(len([o for o in observations if o.flagged]), 2)

    def test_a_short_series_establishes_no_baseline(self):
        observations, reason = self.scan([100] * 5)
        self.assertEqual(observations, [])
        self.assertIn("not enough", reason)

    def test_the_scan_is_deterministic(self):
        values = [10000] * 24
        values[18] = 40000
        first = [(o.period, o.status, o.score) for o in self.scan(values)[0]]
        second = [(o.period, o.status, o.score) for o in self.scan(values)[0]]
        self.assertEqual(first, second)

    def test_higher_sensitivity_never_flags_fewer_periods(self):
        values = [10000, 10500, 9800, 10200, 9900, 10100, 10400, 9700,
                  10300, 10000, 12500, 10100, 9900, 10200, 10050, 9950,
                  10150, 10250, 9850, 10000, 10100, 9900, 10200, 10000]
        counts = {}
        for sensitivity in (detectors.LOW, detectors.MEDIUM, detectors.HIGH):
            observations, _reason = self.scan(values, sensitivity=sensitivity)
            counts[sensitivity] = len([o for o in observations if o.flagged])
        self.assertLessEqual(counts[detectors.LOW], counts[detectors.HIGH])

    def test_a_zero_baseline_does_not_raise(self):
        observations, reason = self.scan([0] * 12 + [0] * 12)
        self.assertIsNone(reason)
        self.assertEqual([o for o in observations if o.flagged], [])

    def test_negative_values_are_scored_rather_than_skipped(self):
        values = [-5000] * 24
        values[18] = -20000
        observations, _reason = self.scan(values)
        self.assertTrue(any(o.flagged for o in observations))


if __name__ == "__main__":
    unittest.main()
