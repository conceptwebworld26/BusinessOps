"""Forecast orchestration: history in, scenarios out, every step recorded.

Nine stages, in order, each one belonging to a module that does only that:

    1 history       series.prepare        the mapped dataset becomes a monthly series
    2 preprocessing series.prepare        gaps found, contiguity resolved, nothing filled
    3 adequacy      methods.adequate      which methods this history can support at all
    4 selection     validate.select       backtest every candidate; lowest error wins
    5 assumptions   this module           what the chosen method is taking on trust
    6 forecast      Method.project        the base numbers
    7 scenarios     this module           base adjusted by a stated, quantified band
    8 uncertainty   this module           width, from measured error or observed volatility
    9 presentation  contract              rendering and rounding, applied once

The four targets differ only in where their history comes from. Revenue and operating
expense are direct roles; gross profit is derived from two roles and says so; cash flow
requires a cash role that a sales extract does not have. None of them invents an input:
where the field is absent, the target is `unavailable` and names the field it needs.
"""

from decimal import Decimal

from .. import mapping as mapping_mod
from ..analytics import domain as domain_mod, presentation as presentation_mod
from ..kpi import contract as kpi_contract, primitives as p
from . import contract, methods as methods_mod, series as series_mod, validate

ZERO = Decimal("0")

#: Never project further than half the observed history: a 6-period forecast from 12
#: periods is an extrapolation, and from 4 periods it is a guess wearing a chart.
HORIZON_HISTORY_DIVISOR = 2

#: An absolute ceiling regardless of history, so a 20-year series cannot request 120 months.
MAX_HORIZON = 24

#: Scenario bands when no error and no volatility could be measured - a constant series.
#: Deliberately narrow: a flat history gives no evidence of movement in either direction.
FALLBACK_BAND_PCT = Decimal("5")

#: The most a scenario band may widen to. An unbounded band is not a forecast.
MAX_BAND_PCT = Decimal("60")

#: The narrowest a band may close to. A zero-width band would present three identical
#: scenarios as one certain outcome; see `_clamp`.
MIN_BAND_PCT = Decimal("1")


class Target:
    """One forecastable metric: where its history comes from, and what it needs."""

    __slots__ = ("target_id", "name", "kpi_id", "roles", "derived_from", "unit",
                 "needs_note")

    def __init__(self, target_id, name, kpi_id=None, roles=(), derived_from=None,
                 unit=kpi_contract.CURRENCY, needs_note=None):
        self.target_id = target_id
        self.name = name
        self.kpi_id = kpi_id
        self.roles = tuple(roles)
        self.derived_from = derived_from
        self.unit = unit
        self.needs_note = needs_note

    def as_dict(self):
        return {"target": self.target_id, "name": self.name, "kpi": self.kpi_id,
                "roles": list(self.roles), "derived_from": self.derived_from,
                "unit": self.unit}

    def __repr__(self):
        return "Target(%s)" % self.target_id


#: `sales` is deliberately absent as a separate target. Sales *is* the revenue series in
#: this data model, and giving it a second forecast path would produce two numbers for one
#: question - exactly the duplication ADR-0012 forbids.
TARGETS = (
    Target("revenue", "Revenue", kpi_id="revenue", roles=(mapping_mod.REVENUE,)),
    Target("gross_profit", "Gross profit", kpi_id="gross_profit",
           roles=(mapping_mod.REVENUE, mapping_mod.COST),
           derived_from="revenue - cost of goods, per period",
           needs_note="a cost column as well as a revenue column"),
    Target("operating_expense", "Operating expense",
           roles=(mapping_mod.OPERATING_EXPENSE,),
           needs_note=("a column mapped to operating_expense. Operating expense is never "
                       "inferred from cost of goods: they are different things, and "
                       "substituting one for the other would misstate both")),
    Target("cash_flow", "Net cash movement",
           roles=(mapping_mod.CASH_BALANCE,),
           needs_note=("a column mapped to cash_balance. Cash movement is never derived "
                       "from sales: revenue is not cash, and a sales extract carries no "
                       "information about what was actually collected or paid")),
)

BY_ID = {t.target_id: t for t in TARGETS}
TARGET_IDS = tuple(t.target_id for t in TARGETS)


def resolve_horizon(requested, history_periods, config):
    """Validate the horizon against history. Returns `(horizon, limitation_or_None)`."""
    default = int(config.get("forecast.default_horizon_periods", 6)) if config else 6
    # `is None` rather than a truth test: an explicit horizon of 0 is a request to be
    # refused, not an absent argument to be defaulted.
    horizon = default if requested is None else int(requested)

    if horizon < 1:
        return None, ("A forecast horizon must be at least 1 period; %r was requested."
                      % requested)
    supported = min(MAX_HORIZON, max(1, history_periods // HORIZON_HISTORY_DIVISOR))
    if horizon > supported:
        return supported, (
            "A %d-period horizon was requested but %d periods of history support at most "
            "%d (no more than half the observed history, capped at %d). The forecast was "
            "produced for %d periods instead."
            % (horizon, history_periods, supported, MAX_HORIZON, supported))
    return horizon, None


def _clamp(pct):
    """Keep a band inside its bounds.

    The lower bound matters as much as the upper one. A method that reproduced held-out
    history exactly backtests at zero error, and carrying that through would make the
    upside, base and downside scenarios identical - presenting a forecast as certain. No
    estimate about a period that has not happened is certain, so the band never closes
    completely.
    """
    if pct < MIN_BAND_PCT:
        return MIN_BAND_PCT
    return MAX_BAND_PCT if pct > MAX_BAND_PCT else pct


def _band_pct(history, validation):
    """The scenario band width, and the basis it was measured from.

    Preference order is evidential: measured error beats observed volatility, and both beat
    a convention. Whichever is used is named in the output.
    """
    if validation.performed and validation.mape is not None:
        return _clamp(validation.mape), contract.EMPIRICAL_ERROR, (
            "the mean absolute percentage error of this method on %d periods of held-out "
            "history" % (validation.validation_periods or 0)), validation.validation_periods

    volatility = history.volatility_pct()
    if volatility is not None and volatility > ZERO:
        return _clamp(volatility), contract.HISTORICAL_VOLATILITY, (
            "the average period-to-period movement observed across %d periods of history"
            % history.periods), history.periods

    return FALLBACK_BAND_PCT, contract.HISTORICAL_VOLATILITY, (
        "a default band: the history is flat, so it offers no evidence of movement in "
        "either direction"), history.periods


def _register_assumptions(target, history, method, band_pct, validation):
    """Everything this forecast takes on trust, enumerated before any scenario is built."""
    register = contract.AssumptionRegister()
    register.add(
        "method.%s" % method.method_id, target.name,
        "The %s method is appropriate for %s: %s"
        % (method.name, target.name.lower(), method.rationale),
        basis="methods.%s" % method.method_id, origin=contract.Assumption.METHOD)
    register.add(
        "continuity", target.name,
        "Conditions that produced the observed %d periods (%s) continue through the "
        "forecast period. No external event, price change or business change is modelled."
        % (history.periods, history.span),
        basis="history %s" % history.span)
    if history.gaps:
        register.add(
            "gaps", target.name,
            "The %d missing period(s) in the history are genuinely absent observations, "
            "not periods of zero activity." % len(history.gaps),
            basis="series.find_gaps")
    if not validation.performed:
        register.add(
            "unvalidated", target.name,
            "The method has not been tested against held-out history, so its typical "
            "error on this series is unknown.",
            basis=validation.reason)
    elif validation.selected_from and validation.selected_from > 1:
        register.add(
            "selection", target.name,
            "The backtest error is the lowest of %d methods scored on the same held-out "
            "periods, and the method was chosen on it. It is therefore an optimistic "
            "estimate of future error, and the uncertainty band derived from it is "
            "narrower than a clean out-of-sample test would give."
            % validation.selected_from,
            basis="validate.select", origin=contract.Assumption.METHOD)
    if target.derived_from:
        register.add(
            "derivation", target.name,
            "%s is derived as %s, and only periods carrying both inputs are used."
            % (target.name, target.derived_from),
            basis=target.derived_from)
    return register


def _scenarios(base_values, periods, band_pct, register, target, method):
    """Base, upside and downside - each an assumption plus its arithmetic consequence."""
    out = {}

    base_points = [contract.ForecastPoint(period, contract.BASE, value)
                   for period, value in zip(periods, base_values)]
    out[contract.BASE] = contract.Scenario(
        contract.BASE, ZERO, method.method_id,
        assumption=register.add(
            "scenario.base", target.name,
            "Base scenario: the %s projection is taken unadjusted." % method.name,
            scenario=contract.BASE, direction="none", quantified_pct=ZERO,
            basis="methods.%s" % method.method_id),
        points=base_points,
        caveat="A central estimate, not a prediction of what will occur.")

    for name, sign, wording in ((contract.UPSIDE, Decimal("1"), "above"),
                                (contract.DOWNSIDE, Decimal("-1"), "below")):
        adjustment = band_pct * sign
        points = [contract.ForecastPoint(
            period, name, value + (value * adjustment / Decimal("100")))
            for period, value in zip(periods, base_values)]
        assumption = register.add(
            "scenario.%s" % name, target.name,
            "%s scenario: %s performs %s the base projection by %s, the width measured "
            "from this series."
            % (name.title(), target.name.lower(), wording, contract.percent(band_pct)),
            scenario=name, direction=wording, quantified_pct=adjustment,
            basis="scenario band")
        out[name] = contract.Scenario(
            name, adjustment, method.method_id, assumption=assumption, points=points,
            caveat=("An illustrative %s case under a stated assumption, not a bound on "
                    "what can occur." % name))
    return out


def forecast_series(history, target, config, horizon=None, quality_grade=None,
                    provenance=None, currency=None, method_id=None, caveats=()):
    """Forecast one prepared history. The pure core: no dataset, no pipeline, no I/O."""
    min_history = int(config.get("forecast.min_history_periods", 12)) if config else 12

    common = {"metric": target.target_id, "metric_name": target.name,
              "unit": target.unit, "currency": currency,
              "frequency": history.frequency,
              "history": history.series,
              "historical_period": history.span,
              "quality_grade": quality_grade, "provenance": dict(provenance or {}),
              "depends_on": target.roles, "min_history": min_history,
              "caveats": list(caveats) + list(history.notes)}

    if history.periods < min_history:
        return contract.ForecastResult(
            "forecast.%s" % target.target_id, status=contract.INSUFFICIENT_DATA,
            reason=("%s has %d periods of history; %d are required before a forecast is "
                    "produced. A shorter series cannot distinguish a trend from noise, so "
                    "no forecast is offered rather than an unreliable one."
                    % (target.name, history.periods, min_history)),
            **common)

    horizon, horizon_note = resolve_horizon(horizon, history.periods, config)
    if horizon is None:
        return contract.ForecastResult(
            "forecast.%s" % target.target_id, status=contract.UNAVAILABLE,
            reason=horizon_note, **common)

    chosen, validation, _scored = validate.select(history, horizon, preferred=method_id)
    if chosen is None:
        return contract.ForecastResult(
            "forecast.%s" % target.target_id, status=contract.INSUFFICIENT_DATA,
            reason=validation.reason, validation=validation, **common)

    base_values = chosen.project(history.series, horizon)
    periods = series_mod.horizon_periods(history.last_period, horizon)

    band_pct, band_kind, band_basis, sample = _band_pct(history, validation)
    uncertainty = contract.UncertaintyBand(band_kind, pct=band_pct, basis=band_basis,
                                           sample_periods=sample)

    register = _register_assumptions(target, history, chosen, band_pct, validation)
    scenarios = _scenarios(base_values, periods, band_pct, register, target, chosen)

    for name, scenario in scenarios.items():
        for point in scenario.points:
            point.low, point.high = uncertainty.bounds(point.value)

    result_caveats = list(common.pop("caveats"))
    if horizon_note:
        result_caveats.append(horizon_note)
    if history.constant():
        result_caveats.append(
            "Every observed period holds the same value, so the forecast repeats it and "
            "the scenario band is a default rather than a measured spread.")
    if history.zero_baseline():
        result_caveats.append(
            "The most recent periods are zero, so percentage comparisons against this "
            "forecast will be undefined.")

    confidence = _confidence(history, validation, quality_grade)

    return contract.ForecastResult(
        "forecast.%s" % target.target_id, status=contract.AVAILABLE,
        forecast_period="%s..%s" % (periods[0], periods[-1]),
        horizon=horizon, method=chosen.method_id, method_name=chosen.name,
        method_rationale=_rationale(chosen, validation),
        parameters={"min_history_periods": min_history, "horizon": horizon,
                    "band_pct": band_pct, "season": methods_mod.SEASON},
        scenarios=scenarios, assumptions=register, uncertainty=uncertainty,
        validation=validation, confidence=confidence, caveats=result_caveats, **common)


def _rationale(method, validation):
    if validation.performed and validation.candidates:
        others = [c for c in validation.candidates if c["method"] != method.method_id]
        beaten = ", ".join(
            "%s (%s)" % (c["method"], contract.percent(c["mape"]) if c["mape"] is not None
                         else "no MAPE")
            for c in others[:4])
        return ("Selected by backtest: %s had the lowest error (%s) on held-out history%s."
                % (method.name, contract.percent(validation.mape),
                   "; it was compared against %s" % beaten if beaten else ""))
    return ("Selected as the most capable method whose minimum history requirement (%d "
            "periods) is met; no backtest was possible."
            % method.min_periods)


def _confidence(history, validation, quality_grade):
    """Confidence follows evidence: history length, measured error and data quality.

    Never HIGH. A forecast is a class-6 estimate about a period that has not happened, and
    the highest confidence class is reserved for measured fact.
    """
    from .. import evidence as evidence_mod
    from ..quality import contract as quality_contract

    if quality_grade is not None and quality_grade != quality_contract.PASS:
        return evidence_mod.LOW
    if not validation.performed:
        return evidence_mod.LOW
    if validation.mape is not None and validation.mape > Decimal("25"):
        return evidence_mod.LOW
    if history.periods < methods_mod.SEASON * 2:
        return evidence_mod.MEDIUM
    return evidence_mod.MEDIUM


# -- pipeline-facing entry point --------------------------------------------

def _history_for(target, result, config):
    """Build one target's history from the canonical dataset. Returns (history, reason)."""
    dataset, semantic_map = result.dataset, result.semantic_map

    if target.target_id == "gross_profit":
        revenue, reason = series_mod.prepare(
            dataset, semantic_map, mapping_mod.REVENUE, "Revenue")
        if revenue is None:
            return None, reason
        if not semantic_map.column_for(mapping_mod.COST):
            return None, ("No column is mapped to cost, so gross profit cannot be "
                          "forecast. Gross profit needs %s." % target.needs_note)
        cost, cost_reason = series_mod.prepare(
            dataset, semantic_map, mapping_mod.COST, "Cost")
        if cost is None:
            return None, cost_reason
        combined = series_mod.derived(revenue.series, cost.series, "Gross profit")
        if not combined:
            return None, ("No period carries both revenue and cost, so gross profit has "
                          "no history to forecast.")
        return series_mod.History(
            "Gross profit", combined, regular=revenue.regular, gaps=revenue.gaps,
            trimmed=revenue.trimmed, original_periods=len(combined),
            notes=list(revenue.notes)), None

    role = target.roles[0]
    history, reason = series_mod.prepare(dataset, semantic_map, role, target.name)
    if history is None and target.needs_note:
        reason = "%s cannot be forecast: it needs %s." % (target.name, target.needs_note)
    return history, reason


def run(result, targets=None, horizon=None, presentation=presentation_mod.LOCAL,
        method_id=None):
    """Forecast every requested target over one completed pipeline result.

    Returns a `ForecastSet`. When the quality gate halted the run, the set comes back
    unavailable with no forecast attempted - `domain.prepare` enforces that, and this
    module does not second-guess it.
    """
    analysis, context = domain_mod.prepare(result, "forecast", presentation=presentation)
    wanted = [BY_ID[t] for t in (targets or TARGET_IDS)] if targets else list(TARGETS)

    fset = contract.ForecastSet.adopt(
        analysis, requested_horizon=horizon, frequency=series_mod.MONTHLY)

    if context is None:                       # halted at the quality gate
        return fset

    config = result.config
    currency = context.currency
    fset.horizon = None

    for target in wanted:
        if target.kpi_id:
            fset.note_metric(target.kpi_id)
        history, reason = _history_for(target, result, config)
        if history is None:
            fset.register(contract.ForecastResult(
                "forecast.%s" % target.target_id, metric=target.target_id,
                metric_name=target.name, status=contract.UNAVAILABLE, reason=reason,
                unit=target.unit, currency=currency, depends_on=target.roles,
                quality_grade=analysis.quality_grade,
                provenance=dict(analysis.provenance)))
            continue

        forecast = forecast_series(
            history, target, config, horizon=horizon,
            quality_grade=analysis.quality_grade, provenance=dict(analysis.provenance),
            currency=currency, method_id=method_id, caveats=list(analysis.caveats))
        fset.register(forecast)
        if forecast.available and fset.horizon is None:
            fset.horizon = forecast.horizon

    fset.note_primitive("kpi.primitives.series_by_period")
    if not fset.available_forecasts():
        fset.status = contract.INSUFFICIENT_DATA
        fset.reason = ("No target could be forecast from this dataset. Each limitation "
                       "below names the field or the history it needed.")
    return fset


def compare_actuals(forecast_result, actuals, config, scenario=contract.BASE):
    """Re-exported so a caller needs only this module. See `variance.compare`."""
    from . import variance
    return variance.compare(forecast_result, actuals, config, scenario=scenario)
