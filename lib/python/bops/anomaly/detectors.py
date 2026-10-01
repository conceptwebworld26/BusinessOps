"""Anomaly detectors, each declared with its adequacy predicate and its threshold.

Same registration pattern as `forecast.methods`: `architecture.md` names "a forecast method
/ anomaly detector - register with its adequacy predicate" as an extension point requiring
no ADR, so a detector is a table entry rather than a branch in the engine.

Three detectors, deliberately overlapping, because they are blind in different places. Each
adequate detector scores the period; the detector that produced the verdict is always named
in the finding.

**Only one of them may raise a flag.** `triggers` marks a detector as authoritative or
corroborating, and the split is about evidence rather than arithmetic. A detector whose
window is contaminated by the very event being examined, or whose entire baseline is a
single observation, will disagree with a robust one - and when they disagree it is the
fragile one that is wrong. Letting any detector trigger meant a single spike was reported
twice (once as the spike, once as the return to normal) and a spike in one year made the
same month a year later look like a collapse.

Scores are expressed in multiples of the detector's own typical prediction error. That is a
ratio of two measured quantities, not a distributional statistic: the engine fits no
distribution and tests none, so no score is a sigma, carries a probability, or implies a
significance level.

**Sensitivity** is the one tuning knob, and it is configuration rather than a hidden
constant: `anomaly.sensitivity` in `config/businessops.defaults.json`, defaulting to
`medium`. It moves the thresholds, never the arithmetic - so raising sensitivity can flag
more periods but can never change what a deviation *is*.
"""

from decimal import Decimal, InvalidOperation

from . import baselines, contract

ZERO = Decimal("0")

LOW = "low"
MEDIUM = "medium"
HIGH = "high"

SENSITIVITIES = (LOW, MEDIUM, HIGH)

#: Threshold per sensitivity, per detector. Higher sensitivity means a lower bar to flag.
#: The level detectors score in multiples of their own typical prediction error; the
#: seasonal detector scores in percent. Neither is a distributional quantity.
THRESHOLDS = {
    "robust_deviation":     {LOW: Decimal("4.0"), MEDIUM: Decimal("3.0"),
                             HIGH: Decimal("2.5")},
    "mean_deviation":       {LOW: Decimal("3.5"), MEDIUM: Decimal("2.5"),
                             HIGH: Decimal("2.0")},
    "seasonal_deviation":   {LOW: Decimal("60"), MEDIUM: Decimal("40"),
                             HIGH: Decimal("25")},
}


#: The tightest spread any baseline may claim, as a share of its own level. Prevents a
#: run of similar residuals from collapsing the spread and inflating every later score.
MIN_SPREAD_SHARE = Decimal("0.01")


def resolve_sensitivity(config):
    if config is None:
        return MEDIUM
    value = str(config.get("anomaly.sensitivity", MEDIUM) or MEDIUM).lower()
    return value if value in SENSITIVITIES else MEDIUM


def _safe_pct(numerator, denominator):
    """Percentage, or None when the denominator makes one meaningless."""
    if denominator is None or denominator == ZERO:
        return None
    try:
        magnitude = denominator if denominator > ZERO else -denominator
        return numerator / magnitude * Decimal("100")
    except (InvalidOperation, ZeroDivisionError):
        return None


class Detector:
    """One way of deciding whether a period is unusual.

    `triggers` says whether this detector may raise a flag on its own, or only corroborate
    one. The distinction exists because the detectors fail differently, and a detector that
    is known to fail on a particular window must not be able to overrule one that is built
    to survive it - see the note on `mean_deviation` in the registry below.
    """

    __slots__ = ("detector_id", "name", "min_periods", "spread_kind", "score_unit",
                 "description", "_measure", "triggers")

    def __init__(self, detector_id, name, min_periods, spread_kind, score_unit,
                 description, measure, triggers=True):
        self.detector_id = detector_id
        self.name = name
        self.min_periods = min_periods
        self.spread_kind = spread_kind
        self.score_unit = score_unit
        self.description = description
        self._measure = measure
        self.triggers = triggers

    def adequate_for(self, series, index):
        """Whether enough prior history exists at `index` for this detector to mean anything."""
        return index >= self.min_periods

    def threshold(self, sensitivity):
        return THRESHOLDS[self.detector_id][sensitivity]

    def measure(self, series, index, window, sensitivity):
        """Returns `(Baseline, deviation, deviation_pct, score, threshold)` or None."""
        return self._measure(self, series, index, window, sensitivity)

    def as_dict(self):
        return {"detector": self.detector_id, "name": self.name,
                "min_periods": self.min_periods, "score_unit": self.score_unit,
                "description": self.description,
                "thresholds": {k: str(v)
                               for k, v in THRESHOLDS[self.detector_id].items()}}

    def __repr__(self):
        return "Detector(%s, min=%d)" % (self.detector_id, self.min_periods)


def _spread_measure(detector, series, index, window, sensitivity, compute):
    """Shared body for the two spread-based detectors."""
    centre, spread, periods = compute(series, index, window)
    if centre is None or periods < detector.min_periods:
        return None
    observed = series[index][1]
    deviation = observed - centre
    threshold = detector.threshold(sensitivity)

    if spread is None or spread == ZERO:
        # A flat baseline has no spread to score against. Any movement away from it is a
        # departure from a perfectly steady series, so fall back to percentage change
        # rather than dividing by zero or silently declaring the period normal.
        pct = _safe_pct(deviation, centre)
        score = None if pct is None else (pct if pct >= ZERO else -pct)
        threshold = THRESHOLDS["seasonal_deviation"][sensitivity]
        baseline = baselines_record(detector, centre, spread, periods, window,
                                    "flat baseline; scored on percentage change")
        return baseline, deviation, pct, score, threshold

    # A spread floor. When past residuals happen to cluster, the measured spread collapses
    # toward zero and every subsequent ordinary month divides by it into a huge score - a
    # baseline that fits well starts claiming a precision the data cannot support. No
    # baseline is treated as tighter than one percent of its own level.
    centre_magnitude = centre if centre >= ZERO else -centre
    floor = centre_magnitude * MIN_SPREAD_SHARE
    if spread < floor:
        spread = floor
        if spread == ZERO:
            pct = _safe_pct(deviation, centre)
            score = None if pct is None else (pct if pct >= ZERO else -pct)
            baseline = baselines_record(detector, centre, spread, periods, window,
                                        "flat baseline; scored on percentage change")
            return baseline, deviation, pct, score, \
                THRESHOLDS["seasonal_deviation"][sensitivity]

    scaled = spread / baselines.MAD_SCALE if detector.spread_kind == "mad" else spread
    magnitude = deviation if deviation >= ZERO else -deviation
    score = magnitude / scaled if scaled != ZERO else None
    baseline = baselines_record(detector, centre, spread, periods, window)
    return baseline, deviation, _safe_pct(deviation, centre), score, threshold


def baselines_record(detector, centre, spread, periods, window, note=None):
    return contract.Baseline(
        detector.detector_id, centre, spread=spread, spread_kind=detector.spread_kind,
        periods=periods, window=window,
        description=note or detector.description)


def _robust(detector, series, index, window, sensitivity):
    return _spread_measure(detector, series, index, window, sensitivity,
                           baselines.rolling_median_baseline)


def _mean(detector, series, index, window, sensitivity):
    return _spread_measure(detector, series, index, window, sensitivity,
                           baselines.trailing_mean_baseline)


def _seasonal(detector, series, index, window, sensitivity):
    """Same month last year. Scored in percent, because one prior year gives no spread."""
    centre, spread, periods = baselines.seasonal_baseline(series, index)
    if centre is None:
        return None
    observed = series[index][1]
    deviation = observed - centre
    pct = _safe_pct(deviation, centre)
    if pct is None:
        return None
    score = pct if pct >= ZERO else -pct
    baseline = baselines_record(detector, centre, spread, periods, baselines.SEASON)
    return baseline, deviation, pct, score, detector.threshold(sensitivity)


DETECTORS = (
    Detector("robust_deviation", "Robust deviation (median step, MAD of residuals)", 4,
             "mad", "x typical error",
             "expected level from the median trailing step, corrected for recent bias; "
             "median absolute deviation of past prediction errors", _robust),

    # Corroborating only. The mean is dragged by any outlier inside its own window, so in
    # the one situation that matters most - the period *after* a spike - it reports the
    # return to normal as a crash. The robust detector is built to survive exactly that
    # window, and a detector that fails there must not be able to overrule one that does
    # not. Its score is still measured and reported; it simply cannot raise a flag alone.
    Detector("mean_deviation", "Deviation from mean step (corroborating)", 4, "stdev",
             "x typical error",
             "expected level from the mean trailing step, corrected for recent bias; "
             "standard deviation of past prediction errors", _mean, triggers=False),
    # Corroborating only, for a reason that is about evidence rather than arithmetic. Its
    # whole baseline is one observation - the same month a year earlier - so it cannot
    # distinguish "this year is unusual" from "last year was unusual". Outvoting a bad
    # prior year needs three or more same-month observations, and a business with two or
    # three years of history never has them. It is measured and reported, so a reader still
    # sees the year-on-year comparison; it simply cannot raise a flag by itself.
    Detector("seasonal_deviation", "Same period last year, growth-adjusted "
             "(corroborating)", baselines.SEASON + 1, "mad", "%",
             "same calendar month one year earlier, carried forward by the typical "
             "year-on-year growth rate", _seasonal, triggers=False),
)

BY_ID = {d.detector_id: d for d in DETECTORS}
DETECTOR_IDS = tuple(d.detector_id for d in DETECTORS)


def get(detector_id):
    detector = BY_ID.get(detector_id)
    if detector is None:
        raise KeyError("unknown anomaly detector %r; known: %s"
                       % (detector_id, ", ".join(DETECTOR_IDS)))
    return detector


def adequate(series, index):
    return [d for d in DETECTORS if d.adequate_for(series, index)]


def catalogue():
    return {"count": len(DETECTORS), "detectors": [d.as_dict() for d in DETECTORS],
            "sensitivities": list(SENSITIVITIES)}
