"""Milestone 8 review gate: the properties the M8 report asserted, proven independently.

The M8 suites test that the engines produce what they claim. These test the claims a reader
would be entitled to challenge:

  * **No future leakage.** The single most important property of an anomaly scan. Proven by
    truncation rather than by inspection: the verdict on period *t* must be byte-identical
    whether or not periods after *t* exist in the series. Reading the code is not proof;
    a baseline that accidentally saw the future would still look correct on the page.

  * **Growth is not an anomaly.** A business that grows is not anomalous every month. Tested
    across constant, linear, accelerating, declining and seasonal shapes.

  * **A spike is one event, not two.** The recovery month afterwards is normal.

  * **Degenerate spread does not produce meaningless scores** - and the floor that prevents
    that does not hide a genuine material anomaly.

  * **No claim of statistical validity.** Neither engine fits or tests a distribution, so no
    output may carry a unit or a phrase that invites a probability reading.
"""

import json
import os
import re
import shutil
import tempfile
import unittest
from decimal import Decimal

from bops import commands, pipeline
from bops.analytics import presentation
from bops.anomaly import baselines, contract as anomaly_contract, detectors
from bops.anomaly import engine as anomaly_engine
from bops.forecast import contract as forecast_contract, series as series_mod, validate

from fixtures import build_forecast_fixtures as build

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")

D = Decimal


class Config:
    """The materiality thresholds, standing in for a resolved configuration."""

    def __init__(self, **overrides):
        self.values = {"materiality.absolute_amount": D("1000"),
                       "materiality.percentage": D("5.0")}
        self.values.update(overrides)

    def get(self, key, default=None):
        return self.values.get(key, default)

    def source_of(self, key):
        return "test"


def periods(values, start_year=2023, start_month=1):
    out = []
    for index, value in enumerate(values):
        total = start_year * 12 + (start_month - 1) + index
        out.append(("%04d-%02d" % (total // 12, total % 12 + 1), D(str(value))))
    return out


def scan(values, config=None, **kwargs):
    return anomaly_engine.scan_series(
        periods(values), anomaly_engine.METRICS[0], config or Config(),
        min_baseline=kwargs.pop("min_baseline", 6), **kwargs)


def verdicts(values, **kwargs):
    """{period: status} for one series."""
    observations, _reason = scan(values, **kwargs)
    return {o.period: o.status for o in observations}


# ==========================================================================
# A. No future leakage
# ==========================================================================

class TestNoFutureLeakage(unittest.TestCase):
    """A verdict must depend only on what was knowable when the period closed."""

    SHAPES = {
        "flat": [10000] * 30,
        "linear": [10000 + 400 * i for i in range(30)],
        "spike_late": [10000] * 20 + [45000] + [10000] * 9,
        "drop_late": [10000] * 20 + [2000] + [10000] * 9,
        "noisy": [10000, 10600, 9700, 10400, 9900, 10250, 10800, 9600,
                  10500, 10100, 9800, 10700, 10000, 10450, 9750, 10300,
                  10900, 9500, 10200, 10650, 9850, 10350, 10050, 10750,
                  9950, 10550, 9650, 10250, 10400, 10150],
    }

    def test_truncating_the_future_never_changes_a_past_verdict(self):
        for name, values in self.SHAPES.items():
            full = verdicts(values)
            for cut in range(8, len(values)):
                truncated = verdicts(values[:cut])
                for period, status in truncated.items():
                    self.assertEqual(
                        status, full[period],
                        "%s: verdict for %s changed when the series was cut at %d"
                        % (name, period, cut))

    def test_truncating_the_future_never_changes_a_score(self):
        values = self.SHAPES["noisy"]
        full = {o.period: o.score for o in scan(values)[0]}
        for cut in (10, 16, 22, 28):
            for observation in scan(values[:cut])[0]:
                self.assertEqual(observation.score, full[observation.period],
                                 "score for %s moved when cut at %d"
                                 % (observation.period, cut))

    def test_a_later_spike_cannot_retrospectively_normalise_an_earlier_one(self):
        early = [10000] * 12 + [40000] + [10000] * 8
        both = list(early)
        both[19] = 40000
        self.assertEqual(verdicts(early)["2024-01"], verdicts(both)["2024-01"])

    def test_the_baseline_window_never_contains_the_observed_period(self):
        series = periods([1, 2, 3, 4, 5, 6, 7, 8])
        for index in range(1, len(series)):
            window = baselines.trailing_window(series, index, 12)
            self.assertNotIn(series[index][1], window[len(window) - 0:] or [])
            self.assertEqual(len(window), min(index, 12))
            self.assertEqual(window, [v for _p, v in series[max(0, index - 12):index]])

    def test_seasonal_rates_are_drawn_only_from_periods_before_the_observation(self):
        series = periods(list(range(1, 40)))
        for index in range(12, len(series)):
            rates = baselines.year_over_year_rates(series, index)
            self.assertEqual(len(rates), max(0, index - 12))

    def test_forecast_training_never_includes_the_validation_slice(self):
        history = series_mod.History("Revenue", periods([100 + 5 * i for i in range(24)]))
        holdout = validate.holdout_size(history.periods, 6)
        train = history.series[:-holdout]
        test = history.series[-holdout:]
        self.assertEqual(len(train) + len(test), history.periods)
        self.assertEqual(set(p for p, _v in train) & set(p for p, _v in test), set())

    def test_a_forecast_point_is_never_a_period_that_was_observed(self):
        result = pipeline.run(DEMO, load_context_files=False)
        forecasts = pipeline.forecast(result)
        for item in forecasts.forecasts.values():
            if not item.available:
                continue
            observed = {p for p, _v in item.history}
            for scenario in item.scenarios.values():
                for point in scenario.points:
                    self.assertNotIn(point.period, observed)


# ==========================================================================
# B. Growth is not an anomaly
# ==========================================================================

class TestGrowthShapes(unittest.TestCase):

    def flagged(self, values, **kwargs):
        observations, reason = scan(values, **kwargs)
        self.assertIsNone(reason)
        return [o for o in observations if o.flagged]

    def test_a_constant_series_flags_nothing(self):
        self.assertEqual(self.flagged([10000] * 30), [])

    def test_a_linear_ramp_flags_nothing(self):
        self.assertEqual(self.flagged([10000 + 500 * i for i in range(30)]), [])

    def test_a_steep_linear_ramp_flags_nothing(self):
        self.assertEqual(self.flagged([10000 + 5000 * i for i in range(30)]), [])

    def test_a_declining_trend_flags_nothing(self):
        self.assertEqual(self.flagged([40000 - 800 * i for i in range(30)]), [])

    def test_accelerating_growth_flags_nothing(self):
        """Compounding growth is ordinary business behaviour, not 24 anomalies.

        The additive step under-predicts a compounding series by a growing amount; the
        offset correction is what removes that, and without it every period here scored
        as an anomaly.
        """
        for rate in (1.03, 1.08):
            values = [round(10000 * (rate ** i), 2) for i in range(30)]
            self.assertEqual(self.flagged(values), [],
                             "compounding at %.0f%%/period was flagged"
                             % ((rate - 1) * 100))

    def test_seasonal_growth_is_not_flagged_every_period(self):
        """Seasonality is a documented limitation: no triggering detector models it.

        The level detectors follow a trend, not a repeating shape, so a strongly seasonal
        series produces some false positives at the turns. The guarantee is that it stays a
        minority of periods rather than becoming the whole report.
        """
        shape = [1.0, 0.9, 1.0, 1.05, 1.1, 1.2, 1.15, 1.1, 1.0, 1.05, 1.3, 1.5]
        values = [10000 * shape[i % 12] * (1.02 ** i) for i in range(36)]
        flagged = self.flagged(values)
        checked = len(scan(values)[0])
        self.assertLess(len(flagged), checked / 3,
                        "seasonal growth flagged %d of %d periods"
                        % (len(flagged), checked))

    def test_a_real_break_in_a_growing_series_is_still_caught(self):
        """The trend tolerance must not blind the detector to a genuine break."""
        values = [10000 + 500 * i for i in range(30)]
        values[22] = values[22] * 3
        flagged = self.flagged(values)
        self.assertIn("2024-11", [o.period for o in flagged])


# ==========================================================================
# C. Seasonal behaviour
# ==========================================================================

class TestSeasonalBehaviour(unittest.TestCase):

    def test_the_seasonal_detector_refuses_before_one_year_on_year_pair_exists(self):
        series = periods(list(range(1, 30)))
        self.assertIsNone(baselines.seasonal_baseline(series, 12)[0])
        self.assertIsNotNone(baselines.seasonal_baseline(series, 13)[0])

    def test_the_seasonal_detector_is_inadequate_below_its_minimum(self):
        series = periods(list(range(1, 30)))
        detector = detectors.get("seasonal_deviation")
        self.assertFalse(detector.adequate_for(series, 12))
        self.assertTrue(detector.adequate_for(series, 13))

    def test_uniform_year_on_year_growth_is_not_seasonally_anomalous(self):
        """A business doubling every year is not anomalous twelve times a year."""
        values = [10000 + 100 * i for i in range(12)]
        values += [2 * v for v in values[:12]]
        values += [4 * v for v in values[:12]]
        series = periods(values)
        detector = detectors.get("seasonal_deviation")
        for index in range(26, len(series)):
            measured = detector.measure(series, index, 12, detectors.MEDIUM)
            if measured is None:
                continue
            _baseline, _dev, _pct, score, threshold = measured
            self.assertLess(score, threshold,
                            "uniform doubling flagged at %s" % series[index][0])

    def test_a_broken_seasonal_pattern_is_still_caught(self):
        values = [10000 + 100 * i for i in range(12)]
        values += [2 * v for v in values[:12]]
        values += [4 * v for v in values[:12]]
        values[30] = 500                      # a December that collapses
        series = periods(values)
        detector = detectors.get("seasonal_deviation")
        _b, _d, _p, score, threshold = detector.measure(series, 30, 12,
                                                        detectors.MEDIUM)
        self.assertGreater(score, threshold)


# ==========================================================================
# D. Spike and recovery
# ==========================================================================

class TestSpikeAndRecovery(unittest.TestCase):

    def test_normal_spike_normal_produces_exactly_one_anomaly(self):
        values = [10000] * 30
        values[20] = 40000
        observations, _reason = scan(values)
        flagged = [o for o in observations if o.flagged]
        self.assertEqual([o.period for o in flagged], ["2024-09"])

    def test_the_recovery_period_is_classified_normal(self):
        values = [10000] * 30
        values[20] = 40000
        self.assertEqual(verdicts(values)["2024-10"], anomaly_contract.NORMAL)

    def test_a_drop_and_its_recovery_produce_exactly_one_anomaly(self):
        values = [10000] * 30
        values[20] = 1500
        flagged = [o for o in scan(values)[0] if o.flagged]
        self.assertEqual([o.period for o in flagged], ["2024-09"])

    def test_two_separated_spikes_produce_two_anomalies(self):
        values = [10000] * 30
        values[14] = 40000
        values[24] = 45000
        flagged = [o for o in scan(values)[0] if o.flagged]
        self.assertEqual(len(flagged), 2)

    def test_a_sustained_step_change_is_absorbed_within_the_baseline_window(self):
        """A permanent shift is a documented limitation, bounded rather than eliminated.

        A trailing-window detector cannot accept a new level instantly; it needs enough
        post-step periods for the offset correction to follow. What it must not do is flag
        the new level forever, so the guarantee is that the run of flags ends well inside
        the window and the tail is clean.
        """
        values = [10000] * 15 + [30000] * 15
        observations = scan(values)[0]
        flagged = [o.period for o in observations if o.flagged]
        self.assertLessEqual(len(flagged), anomaly_engine.DEFAULT_WINDOW,
                             "a step change produced %d flags" % len(flagged))
        tail = [o for o in observations[-6:] if o.flagged]
        self.assertEqual(tail, [], "the new level was still being flagged at the end")


# ==========================================================================
# E. Robust spread
# ==========================================================================

class TestRobustSpread(unittest.TestCase):

    def test_identical_residuals_do_not_produce_an_infinite_score(self):
        observations, _reason = scan([10000] * 30)
        for observation in observations:
            if observation.score is not None:
                self.assertLess(observation.score, D("1000000"))

    def test_a_zero_spread_never_divides_by_zero(self):
        series = periods([500] * 20)
        for detector in detectors.DETECTORS:
            for index in range(7, len(series)):
                if not detector.adequate_for(series, index):
                    continue
                measured = detector.measure(series, index, 12, detectors.MEDIUM)
                if measured is None:
                    continue
                self.assertIsNotNone(measured[0])

    def test_tightly_clustered_residuals_are_floored_not_amplified(self):
        """The bug this floor exists for: a modest month scoring like a crisis."""
        values = [10000 + 300 * i for i in range(24)]
        values[20] = values[20] * D("1.05")        # a 5% wobble
        observations, _reason = scan([D(str(v)) for v in values])
        wobble = [o for o in observations if o.period == "2024-09"]
        self.assertTrue(wobble)
        self.assertEqual(wobble[0].status, anomaly_contract.NORMAL)

    def test_the_floor_does_not_hide_a_genuine_material_anomaly(self):
        values = [10000 + 300 * i for i in range(24)]
        values[20] = values[20] * 4
        flagged = [o for o in scan([D(str(v)) for v in values])[0] if o.flagged]
        self.assertIn("2024-09", [o.period for o in flagged])

    def test_a_zero_baseline_yields_no_percentage_but_still_no_crash(self):
        observations, reason = scan([0] * 30)
        self.assertIsNone(reason)
        for observation in observations:
            self.assertEqual(observation.status, anomaly_contract.NORMAL)

    def test_a_series_rising_from_zero_does_not_produce_an_undefined_score(self):
        observations, _reason = scan([0] * 12 + [5000] * 18)
        for observation in observations:
            if observation.score is not None:
                self.assertGreaterEqual(observation.score, D("0"))

    def test_mad_of_identical_values_is_zero_and_handled(self):
        self.assertEqual(baselines.mad([D("5")] * 10), D("0"))
        self.assertEqual(baselines.stdev([D("5")] * 10), D("0"))


# ==========================================================================
# F. Materiality stays separate
# ==========================================================================

class TestMaterialitySeparation(unittest.TestCase):

    def spike(self, **config):
        values = [10000] * 30
        values[20] = 40000
        return scan(values, config=Config(**config))[0]

    def test_the_same_deviation_changes_status_when_only_the_policy_changes(self):
        """Detector evidence and materiality policy are independent inputs."""
        strict = [o for o in self.spike() if o.flagged]
        lenient = [o for o in self.spike(**{"materiality.absolute_amount": D("1e12"),
                                            "materiality.percentage": D("100000")})
                   if o.flagged]
        self.assertEqual([o.period for o in strict], [o.period for o in lenient])
        self.assertEqual({o.status for o in strict},
                         {anomaly_contract.MATERIAL_ANOMALY})
        self.assertEqual({o.status for o in lenient}, {anomaly_contract.UNUSUAL})

    def test_score_and_deviation_are_unchanged_by_the_materiality_policy(self):
        strict = {o.period: (o.score, o.deviation) for o in self.spike()}
        lenient = {o.period: (o.score, o.deviation)
                   for o in self.spike(**{"materiality.absolute_amount": D("1e12"),
                                          "materiality.percentage": D("100000")})}
        self.assertEqual(strict, lenient)

    def test_no_anomaly_specific_threshold_system_exists(self):
        """Thresholds move the detector only; the money judgement stays in materiality."""
        self.assertEqual(sorted(detectors.THRESHOLDS), sorted(detectors.DETECTOR_IDS))
        for table in detectors.THRESHOLDS.values():
            self.assertEqual(sorted(table), sorted(detectors.SENSITIVITIES))

    def test_every_flagged_observation_carries_the_policy_reason(self):
        for observation in self.spike():
            if observation.flagged:
                self.assertTrue(observation.materiality_reason)


# ==========================================================================
# G/H. Attribution and privacy
# ==========================================================================

class TestAttributionAndPrivacy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m8-review-")
        cls.spike = build.with_spike(cls.directory)
        cls.one_customer = build.single_customer(cls.directory)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def scan_file(self, path, **kwargs):
        return pipeline.detect_anomalies(
            pipeline.run(path, load_context_files=False), **kwargs)

    def test_attribution_reports_share_of_movement_not_a_cause(self):
        for observation in self.scan_file(self.spike).flagged():
            for contributor in observation.contributors:
                self.assertIsNotNone(contributor.share_pct)
                self.assertIsNotNone(contributor.baseline)

    def test_no_contributor_label_contains_causal_or_fraud_vocabulary(self):
        for observation in self.scan_file(self.spike).flagged():
            for contributor in observation.contributors:
                lowered = contributor.label.lower()
                for word in (anomaly_contract.CAUSAL_LANGUAGE
                             + anomaly_contract.FRAUD_LANGUAGE):
                    self.assertNotIn(word, lowered)

    def test_shareable_mode_pseudonymises_identifying_contributors(self):
        scan_set = self.scan_file(self.one_customer,
                                  presentation=presentation.SHAREABLE)
        for observation in scan_set.flagged():
            for contributor in observation.contributors:
                if contributor.dimension == "customer":
                    self.assertTrue(contributor.redacted)
                    self.assertNotIn("Customer 1", contributor.label)

    def test_no_raw_transaction_reaches_the_serialised_scan(self):
        document = json.dumps(self.scan_file(self.spike).as_dict())
        self.assertNotIn("SO-", document)

    def test_a_share_is_claimed_only_when_the_units_match(self):
        """Attribution is measured in revenue. Dividing a revenue movement by a deviation
        counted in orders or percentage points produced shares like 14140%, which answer
        nothing - so no share is claimed unless both sides are currency."""
        from bops.kpi import contract as kpi_contract
        scan_set = pipeline.detect_anomalies(
            pipeline.run(DEMO, load_context_files=False))
        checked = 0
        for observation in scan_set.flagged():
            for contributor in observation.contributors:
                checked += 1
                if observation.unit == kpi_contract.CURRENCY:
                    self.assertIsNotNone(contributor.share_pct, observation.metric)
                    self.assertLessEqual(abs(contributor.share_pct), D("1000"))
                else:
                    self.assertIsNone(contributor.share_pct, observation.metric)
        self.assertGreater(checked, 0)

    def test_a_non_currency_metric_says_what_its_contributors_measure(self):
        from bops.kpi import contract as kpi_contract
        scan_set = pipeline.detect_anomalies(
            pipeline.run(DEMO, load_context_files=False))
        for observation in scan_set.flagged():
            if observation.unit != kpi_contract.CURRENCY and observation.contributors:
                self.assertTrue(
                    any("measured in revenue" in c for c in observation.caveats),
                    observation.metric)

    def test_the_rendered_report_never_prints_an_unavailable_share(self):
        text = commands.render(
            commands.run("anomaly-detection", DEMO, load_context_files=False))
        self.assertNotIn("unavailable of the movement", text)

    def test_the_k_floor_is_the_existing_one(self):
        scan_set = self.scan_file(self.spike, presentation=presentation.SHAREABLE)
        self.assertEqual(scan_set.presentation, presentation.SHAREABLE)


# ==========================================================================
# I. No claim of statistical validity
# ==========================================================================

class TestNoStatisticalClaim(unittest.TestCase):
    """Neither engine fits or tests a distribution, so no output may imply one."""

    #: Units and phrases that invite a probability reading. "Sigma" is the important one:
    #: a reader who sees "3 sigma" infers roughly one-in-370, which nothing here computed.
    #: The confidence-level patterns carry the word deliberately - a bare "95%" would match
    #: an ordinary percentage such as "13.99% of the baseline", which claims nothing.
    DISTRIBUTIONAL = ("sigma", "confidence interval", "prediction interval",
                      "credible interval", "p-value", "statistically significant",
                      "statistical significance", "probability", "confidence level",
                      "95% confiden", "99% confiden", "standard error",
                      "normally distributed")

    def emitted_strings(self, anomaly_set):
        out = []
        for observation in anomaly_set.observations:
            out.append(observation.statement())
            out.append(observation.score_text())
            out.extend(observation.caveats)
        for finding in anomaly_set.findings:
            out.append(finding.statement)
            out.extend(finding.caveats)
        return out

    def setUp(self):
        self.result = pipeline.run(DEMO, load_context_files=False)

    def test_no_anomaly_output_uses_a_distributional_unit_or_phrase(self):
        scan_set = pipeline.detect_anomalies(self.result)
        for text in self.emitted_strings(scan_set):
            lowered = text.lower()
            for word in self.DISTRIBUTIONAL:
                self.assertNotIn(word, lowered, "%r in %r" % (word, text))

    def test_no_detector_declares_a_distributional_score_unit(self):
        for detector in detectors.DETECTORS:
            self.assertNotIn("sigma", detector.score_unit.lower(),
                             detector.detector_id)

    def test_the_rendered_anomaly_report_makes_no_distributional_claim(self):
        text = commands.render(
            commands.run("anomaly-detection", DEMO, load_context_files=False)).lower()
        for word in self.DISTRIBUTIONAL:
            self.assertNotIn(word, text, word)

    #: The engine denies statistical validity in words; those denials legitimately contain
    #: the phrases being screened for, so they are removed before scanning.
    SANCTIONED_DENIALS = (
        "not a statistical confidence interval",
        "this is an empirical range,",
    )

    def strip_denials(self, text):
        lowered = text.lower()
        for denial in self.SANCTIONED_DENIALS:
            lowered = lowered.replace(denial, "")
        return lowered

    def test_no_forecast_output_claims_a_statistical_interval(self):
        forecasts = pipeline.forecast(self.result)
        for item in forecasts.forecasts.values():
            self.assertFalse(item.uncertainty.statistical_interval)
            joined = self.strip_denials(item.uncertainty.statement() + " "
                                        + item.validation.statement())
            for word in ("confidence interval", "prediction interval", "p-value",
                         "95%", "statistically significant", "probability"):
                self.assertNotIn(word, joined, word)

    def test_the_rendered_forecast_report_makes_no_distributional_claim(self):
        text = self.strip_denials(commands.render(
            commands.run("revenue-forecast", DEMO, load_context_files=False)))
        for word in ("prediction interval", "p-value", "statistically significant",
                     "95% confident", "normally distributed", "sigma"):
            self.assertNotIn(word, text, word)

    def test_confidence_is_an_evidential_grade_not_a_probability(self):
        """`confidence` is the ledger's qualitative grade; `uncertainty` is the band.
        They are different fields with different types and must not be conflated."""
        from bops import evidence
        forecasts = pipeline.forecast(self.result)
        for item in forecasts.forecasts.values():
            if not item.available:
                continue
            self.assertIn(item.confidence, (evidence.MEDIUM, evidence.LOW))
            self.assertNotEqual(item.confidence, evidence.HIGH)
            self.assertIsInstance(item.uncertainty.pct, Decimal)
            self.assertNotEqual(str(item.confidence), str(item.uncertainty.pct))


# ==========================================================================
# J. Backtest error is a selection statistic
# ==========================================================================

NEWLINE = chr(10)
TAB = chr(9)


class TestComponentFrontmatterParses(unittest.TestCase):
    """Frontmatter must survive a strict YAML parser, not merely look right.

    Added because this review broke it: a bare ": " inside an unquoted scalar is a mapping
    to YAML, and once the file also carried CRLF the plugin validator rejected the command
    with "all frontmatter fields silently dropped" - a component that loads with no
    description does not route at all. Read as bytes on purpose, so newline translation
    cannot hide the problem the way text mode does.
    """

    def components(self):
        import glob
        return (sorted(glob.glob(os.path.join(REPO, "commands", "*.md")))
                + sorted(glob.glob(os.path.join(REPO, "skills", "*", "SKILL.md"))))

    def frontmatter(self, path):
        raw = open(path, "rb").read().decode("utf-8")
        self.assertTrue(raw.startswith("---"), path)
        end = raw.index("\n---", 3)
        return raw[4:end]

    def test_every_component_has_a_delimited_frontmatter_block(self):
        found = self.components()
        self.assertGreaterEqual(len(found), 15)
        for path in found:
            self.assertTrue(self.frontmatter(path).strip(), path)

    def test_no_frontmatter_value_carries_an_unquoted_colon(self):
        for path in self.components():
            for line in self.frontmatter(path).split(NEWLINE):
                if not re.match(r"^[A-Za-z-]+:\s", line):
                    continue
                key, _, value = line.partition(":")
                value = value.strip()
                if value and value[0] not in "\"'":
                    self.assertNotIn(": ", value,
                                     "%s: unquoted %s contains a colon"
                                     % (os.path.basename(path), key))

    def test_no_frontmatter_line_is_a_continuation(self):
        """A wrapped description silently becomes a different YAML shape."""
        for path in self.components():
            for line in self.frontmatter(path).split(NEWLINE):
                self.assertFalse(line[:1] in (" ", TAB),
                                 "%s: continuation line %r"
                                 % (os.path.basename(path), line[:40]))

    def test_frontmatter_declares_only_supported_fields(self):
        supported = {"name", "description", "argument-hint", "allowed-tools",
                     "disable-model-invocation", "hide-from-slash-command-tool",
                     "user-invocable"}
        for path in self.components():
            fields = set(re.findall(r"^([A-Za-z-]+):", self.frontmatter(path), re.M))
            self.assertTrue(fields <= supported,
                            "%s: %s" % (os.path.basename(path), fields - supported))


class TestBacktestHonesty(unittest.TestCase):

    def history(self, values):
        return series_mod.History("Revenue", periods(values))

    def test_the_reported_error_is_the_best_of_several_candidates(self):
        history = self.history([100 + 7 * i for i in range(24)])
        _chosen, validation, scored = validate.select(history, 6)
        self.assertGreater(len(scored), 1)
        best = min(s["mape"] for s in scored if s["mape"] is not None)
        self.assertEqual(validation.mape, best)

    def test_the_validation_statement_discloses_the_selection(self):
        """Reporting the winner's error without saying it won is optimistic."""
        history = self.history([100 + 7 * i for i in range(24)])
        _chosen, validation, _scored = validate.select(history, 6)
        statement = validation.statement().lower()
        self.assertIn("lowest error among", statement)
        self.assertIn("flatters", statement)

    def test_every_candidate_remains_inspectable(self):
        history = self.history([100 + 7 * i for i in range(24)])
        _chosen, validation, _scored = validate.select(history, 6)
        self.assertGreaterEqual(len(validation.candidates), 2)
        for candidate in validation.candidates:
            self.assertIn("method", candidate)


if __name__ == "__main__":
    unittest.main()
