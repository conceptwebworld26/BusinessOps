"""Forecast versus actual: what was estimated, what happened, and whether the gap matters.

Two rules govern this module.

**Materiality is not redecided here.** Whether a variance matters is a question
`materiality.assess_amount` already answers, using the user's configured thresholds. A
second threshold system would let the same gap be material in one report and immaterial in
another, so this module computes the gap and asks the existing policy about it.

**A percentage is only reported when it means something.** Percentage variance against a
zero actual is undefined, and against a near-zero actual it is arithmetically valid but
rhetorically useless - "revenue missed forecast by 40,000%" describes a small denominator,
not a large miss. Both cases are reported as an absolute variance with the percentage
explicitly withheld and a reason given.
"""

from decimal import Decimal

from .. import materiality as materiality_mod
from ..analytics import contract as analytics_contract
from . import contract

ZERO = Decimal("0")

OVER = "above_forecast"
UNDER = "below_forecast"
ON = "on_forecast"


def _dec(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


class Variance:
    """One period compared: forecast, actual, and the size and direction of the gap."""

    __slots__ = ("period", "scenario", "forecast", "actual", "variance",
                 "variance_pct", "pct_withheld_reason", "direction", "materiality",
                 "materiality_reason")

    def __init__(self, period, scenario, forecast, actual, variance, variance_pct=None,
                 pct_withheld_reason=None, direction=ON, materiality=None,
                 materiality_reason=None):
        self.period = period
        self.scenario = scenario
        self.forecast = forecast
        self.actual = actual
        self.variance = variance
        self.variance_pct = variance_pct
        self.pct_withheld_reason = pct_withheld_reason
        self.direction = direction
        self.materiality = materiality
        self.materiality_reason = materiality_reason

    def as_dict(self):
        record = {"period": self.period, "scenario": self.scenario,
                  "forecast": contract._plain(self.forecast),
                  "actual": contract._plain(self.actual),
                  "variance": contract._plain(self.variance),
                  "variance_pct": contract._plain(self.variance_pct),
                  "pct_withheld_reason": self.pct_withheld_reason,
                  "direction": self.direction,
                  "materiality": self.materiality,
                  "materiality_reason": self.materiality_reason}
        return {k: v for k, v in record.items() if v is not None}

    def __repr__(self):
        return "Variance(%s %s)" % (self.period, self.variance)


def compare_period(period, forecast_value, actual_value, config, scenario=contract.BASE,
                   subject="Forecast"):
    """One period. `variance` is actual minus forecast: positive means the actual came in
    above the estimate."""
    forecast_value = _dec(forecast_value)
    actual_value = _dec(actual_value)
    difference = actual_value - forecast_value

    variance_pct, withheld = None, None
    if forecast_value == ZERO:
        withheld = ("Percentage variance is undefined: the forecast for this period was "
                    "zero.")
    else:
        magnitude = forecast_value if forecast_value > ZERO else -forecast_value
        variance_pct = difference / magnitude * Decimal("100")

    if difference > ZERO:
        direction = OVER
    elif difference < ZERO:
        direction = UNDER
    else:
        direction = ON

    # The existing policy decides materiality; this module only supplies the two figures.
    verdict = materiality_mod.assess_amount(
        "%s %s" % (subject, period), actual_value, forecast_value, config)

    return Variance(period, scenario, forecast_value, actual_value, difference,
                    variance_pct=variance_pct, pct_withheld_reason=withheld,
                    direction=direction, materiality=verdict.outcome,
                    materiality_reason=verdict.reason)


def compare(forecast_result, actuals, config, scenario=contract.BASE):
    """Compare a forecast against actuals that arrived later.

    `actuals` is `{period: value}` or an ordered `(period, value)` sequence. Only periods
    the forecast actually covers are compared; an actual for an unforecast period is
    reported as uncovered rather than silently dropped.
    """
    if hasattr(actuals, "items"):
        actual_map = dict(actuals)
    else:
        actual_map = dict(actuals or [])

    if not forecast_result.available:
        return {"status": forecast_result.status,
                "reason": forecast_result.reason or "No forecast was produced to compare.",
                "comparisons": [], "uncovered": sorted(actual_map)}

    band = forecast_result.scenario(scenario)
    if band is None:
        return {"status": contract.UNAVAILABLE,
                "reason": "The forecast carries no %r scenario." % scenario,
                "comparisons": [], "uncovered": sorted(actual_map)}

    comparisons, covered = [], set()
    for point in band.points:
        if point.period not in actual_map:
            continue
        covered.add(point.period)
        comparisons.append(compare_period(
            point.period, point.value, actual_map[point.period], config,
            scenario=scenario, subject=forecast_result.metric_name))

    total_forecast = sum((c.forecast for c in comparisons), ZERO)
    total_actual = sum((c.actual for c in comparisons), ZERO)
    total = None
    if comparisons:
        total = compare_period(
            "%s..%s" % (comparisons[0].period, comparisons[-1].period),
            total_forecast, total_actual, config, scenario=scenario,
            subject="%s total" % forecast_result.metric_name)

    return {
        "status": contract.AVAILABLE if comparisons else contract.INSUFFICIENT_DATA,
        "reason": (None if comparisons else
                   "No actual values were supplied for any forecast period."),
        "metric": forecast_result.metric,
        "scenario": scenario,
        "method": forecast_result.method,
        "comparisons": [c.as_dict() for c in comparisons],
        "total": total.as_dict() if total else None,
        "periods_compared": len(comparisons),
        "uncovered": sorted(set(actual_map) - covered),
    }


def findings(comparison, currency=None, analysis_type="forecast_variance"):
    """Variance findings for the analytics contract.

    A variance is a `CALCULATION`, not an assumption: both halves are now observed, and the
    subtraction between them is ordinary arithmetic. The forecast being compared *was* an
    estimate, which is why the statement names it as one.
    """
    out = []
    for record in comparison.get("comparisons", []):
        pct = record.get("variance_pct")
        pct_text = (" (%s)" % contract.percent(Decimal(pct))) if pct is not None else ""
        statement = (
            "In %s, actual %s was %s against a forecast of %s: a variance of %s%s."
            % (record["period"], comparison.get("metric", "the metric"),
               contract.money(Decimal(record["actual"]), currency),
               contract.money(Decimal(record["forecast"]), currency),
               contract.money(Decimal(record["variance"]), currency), pct_text))
        caveats = []
        if record.get("pct_withheld_reason"):
            caveats.append(record["pct_withheld_reason"])
        out.append(analytics_contract.AnalysisFinding(
            analysis_id="%s.%s.%s" % (analysis_type, comparison.get("metric"),
                                      record["period"]),
            analysis_type=analysis_type,
            finding_type=analytics_contract.CALCULATION,
            statement=statement,
            metric=comparison.get("metric"),
            period=record["period"],
            observed=Decimal(record["actual"]),
            comparison=Decimal(record["forecast"]),
            change=Decimal(record["variance"]),
            change_pct=Decimal(pct) if pct is not None else None,
            currency=currency,
            materiality=record.get("materiality"),
            materiality_reason=record.get("materiality_reason"),
            direction=record.get("direction"),
            basis="variance.compare_period (actual - forecast)",
            caveats=caveats))
    return out
