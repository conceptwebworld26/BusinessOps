"""The forecasting output contract: what an estimate looks like, and how it stays honest.

A forecast is **not** a fact and not an ordinary calculation. `reference/evidence-ledger.md`
class 6 is "estimate / assumption - modelled or assumed - flagged, and entered in the
assumption register", and that is exactly what every value in this module is. The
consequence is structural rather than cosmetic: forecast findings carry provenance class 6,
which the ledger already treats as *generative* rather than *evidential*, so a forecast can
never be summarised into the same register as a measured figure.

That single decision is what keeps the architecture rule - "actuals never merged with
forecast" - true by construction rather than by discipline.

Four things are kept apart on purpose, because collapsing any two of them is how a forecast
starts lying:

    model output          what the method produced from history
    scenario assumption   a stated, quantified adjustment to that output
    uncertainty           how wrong the method was on history it did not see
    user assumption       something the caller asserted, not something observed

The status vocabulary is the analytics layer's, unchanged, so a reader does not learn a
second set of words for the same four situations.
"""

from decimal import Decimal, ROUND_HALF_UP

from .. import evidence as evidence_mod
from ..analytics import contract as analytics_contract

ZERO = Decimal("0")

# -- status (deliberately identical to the analytics vocabulary) -------------

AVAILABLE = analytics_contract.AVAILABLE
UNAVAILABLE = analytics_contract.UNAVAILABLE
NOT_APPLICABLE = analytics_contract.NOT_APPLICABLE
INSUFFICIENT_DATA = analytics_contract.INSUFFICIENT_DATA

STATUSES = (AVAILABLE, UNAVAILABLE, NOT_APPLICABLE, INSUFFICIENT_DATA)

# -- scenarios ---------------------------------------------------------------

BASE = "base"
UPSIDE = "upside"
DOWNSIDE = "downside"

SCENARIOS = (BASE, UPSIDE, DOWNSIDE)

#: Wording that would turn an estimate into a promise. Listed here rather than only in the
#: tests so the engine and its tests read one definition.
FORBIDDEN_CERTAINTY = ("will happen", "guaranteed", "guarantee", "certainly",
                       "definitely", "will be exactly", "assured", "no risk",
                       "risk-free", "is certain")

# -- uncertainty kinds -------------------------------------------------------

#: Derived from how wrong the method actually was on a held-out slice of real history.
EMPIRICAL_ERROR = "empirical_error_band"
#: Derived from how much the series itself moves period to period.
HISTORICAL_VOLATILITY = "historical_volatility_band"
#: No defensible band could be derived.
NO_BAND = "none"

BAND_KINDS = (EMPIRICAL_ERROR, HISTORICAL_VOLATILITY, NO_BAND)


class ForecastError(Exception):
    """A forecast violates the contract - a defect, not a user error."""


def _plain(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def money(value, currency=None):
    """A figure for a sentence. Rounding is presentation, applied once (CLAUDE.md 4)."""
    if value is None:
        return "unavailable"
    quantised = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return "%s %s" % (currency, quantised) if currency else str(quantised)


def percent(value, places=2):
    if value is None:
        return "unavailable"
    quant = Decimal("1") if places == 0 else Decimal("0." + "0" * places)
    return "%s%%" % Decimal(value).quantize(quant, rounding=ROUND_HALF_UP)


class Assumption:
    """One stated, auditable assumption behind a forecast or a scenario.

    Every assumption is provenance class 6 and is registered. An assumption that is not in
    the register does not exist, which is the point of the register: it makes the set of
    things being taken on trust enumerable rather than scattered through prose.
    """

    __slots__ = ("assumption_id", "subject", "statement", "basis", "scenario",
                 "direction", "quantified_pct", "origin")

    #: Where the assumption came from - observed in the data, or asserted by the caller.
    DERIVED = "derived_from_history"
    STATED = "stated_by_user"
    METHOD = "method_property"

    def __init__(self, assumption_id, subject, statement, basis=None, scenario=None,
                 direction=None, quantified_pct=None, origin=DERIVED):
        self.assumption_id = assumption_id
        self.subject = subject
        self.statement = statement
        self.basis = basis
        self.scenario = scenario
        self.direction = direction
        self.quantified_pct = quantified_pct
        self.origin = origin

    def as_claim(self):
        """Class 6. The ledger enforces its own rules; this only supplies the class."""
        return evidence_mod.Claim(
            self.statement, evidence_mod.ASSUMPTION,
            based_on=self.basis,
            caveats=["An assumption, not an observation."])

    def as_dict(self):
        record = {"assumption_id": self.assumption_id, "subject": self.subject,
                  "statement": self.statement, "basis": self.basis,
                  "scenario": self.scenario, "direction": self.direction,
                  "quantified_pct": _plain(self.quantified_pct),
                  "origin": self.origin,
                  "evidence_class": evidence_mod.ASSUMPTION}
        return {k: v for k, v in record.items() if v is not None}

    def __repr__(self):
        return "Assumption(%s)" % self.assumption_id


class AssumptionRegister:
    """The enumerable set of things a forecast takes on trust.

    `reference/evidence-ledger.md` requires class-6 statements to be "flagged, and entered
    in the assumption register". This is that register.
    """

    __slots__ = ("entries",)

    def __init__(self, entries=None):
        self.entries = list(entries or [])

    def add(self, assumption_id, subject, statement, **kwargs):
        assumption = Assumption(assumption_id, subject, statement, **kwargs)
        self.entries.append(assumption)
        return assumption

    def for_scenario(self, scenario):
        """Assumptions that apply to one scenario: the shared ones plus its own."""
        return [a for a in self.entries
                if a.scenario is None or a.scenario == scenario]

    def statements(self):
        return [a.statement for a in self.entries]

    def record_in(self, ledger):
        return [ledger.add(a.as_claim()) for a in self.entries]

    def as_dict(self):
        return [a.as_dict() for a in self.entries]

    def __len__(self):
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    def __repr__(self):
        return "AssumptionRegister(%d)" % len(self.entries)


class UncertaintyBand:
    """How wide the forecast could reasonably be, and *why* that width was chosen.

    This is deliberately **not** a confidence interval. Nothing in the deterministic engine
    fits a distribution to the residuals, so calling the band "95% confident" would attach
    a statistical guarantee the arithmetic does not support. `statistical_interval` is
    always False and is written into the output, so a downstream reader cannot mistake one
    for the other.
    """

    __slots__ = ("kind", "pct", "basis", "sample_periods")

    def __init__(self, kind, pct=None, basis=None, sample_periods=None):
        if kind not in BAND_KINDS:
            raise ForecastError("unknown uncertainty band kind %r" % (kind,))
        self.kind = kind
        self.pct = pct
        self.basis = basis
        self.sample_periods = sample_periods

    @property
    def statistical_interval(self):
        """Always False. See the class docstring - this is a documented invariant."""
        return False

    @property
    def available(self):
        return self.kind != NO_BAND and self.pct is not None

    def bounds(self, value):
        """(low, high) around one central value, or (None, None) with no band."""
        if not self.available or value is None:
            return None, None
        delta = (Decimal(value) * Decimal(self.pct)) / Decimal("100")
        if delta < ZERO:
            delta = -delta
        return Decimal(value) - delta, Decimal(value) + delta

    def statement(self):
        if not self.available:
            return ("No uncertainty band could be derived; the forecast is a single "
                    "estimate with no stated width.")
        return ("Uncertainty band of +/-%s, derived from %s. This is an empirical range, "
                "not a statistical confidence interval."
                % (percent(self.pct), self.basis or self.kind))

    def as_dict(self):
        return {"kind": self.kind, "pct": _plain(self.pct), "basis": self.basis,
                "sample_periods": self.sample_periods,
                "statistical_interval": self.statistical_interval,
                "statement": self.statement()}

    def __repr__(self):
        return "UncertaintyBand(%s %s)" % (self.kind, self.pct)


class ForecastPoint:
    """One forecast period under one scenario."""

    __slots__ = ("period", "scenario", "value", "low", "high")

    def __init__(self, period, scenario, value, low=None, high=None):
        self.period = period
        self.scenario = scenario
        self.value = value
        self.low = low
        self.high = high

    def as_dict(self):
        record = {"period": self.period, "scenario": self.scenario,
                  "value": _plain(self.value), "low": _plain(self.low),
                  "high": _plain(self.high)}
        return {k: v for k, v in record.items() if v is not None}

    def __repr__(self):
        return "ForecastPoint(%s %s=%s)" % (self.period, self.scenario, self.value)


class Scenario:
    """One named view of the future, with the assumption that produces it stated.

    A scenario is an assumption plus its arithmetic consequence. Neither half is useful
    alone: the number without the assumption is a guess, and the assumption without the
    number is a sentence.
    """

    __slots__ = ("name", "adjustment_pct", "method", "assumption", "points", "caveat")

    def __init__(self, name, adjustment_pct, method, assumption=None, points=None,
                 caveat=None):
        if name not in SCENARIOS:
            raise ForecastError("unknown scenario %r" % (name,))
        self.name = name
        self.adjustment_pct = adjustment_pct
        self.method = method
        self.assumption = assumption
        self.points = list(points or [])
        self.caveat = caveat

    def total(self):
        return sum((p.value for p in self.points if p.value is not None), ZERO)

    def as_dict(self):
        record = {"scenario": self.name,
                  "adjustment_pct": _plain(self.adjustment_pct),
                  "method": self.method,
                  "assumption": self.assumption.as_dict() if self.assumption else None,
                  "total": _plain(self.total()),
                  "points": [p.as_dict() for p in self.points],
                  "caveat": self.caveat}
        return {k: v for k, v in record.items() if v is not None}

    def __repr__(self):
        return "Scenario(%s %s)" % (self.name, self.adjustment_pct)


class Validation:
    """What happened when the method was tested on history it had not seen.

    A forecast that has never been validated is not thereby wrong, but it is differently
    trustworthy, and the difference has to be visible. `status` distinguishes "tested and
    this is the error" from "not testable, and here is why".
    """

    __slots__ = ("status", "method", "training_period", "validation_period",
                 "training_periods", "validation_periods", "mape", "mae", "reason",
                 "candidates")

    def __init__(self, status, method=None, training_period=None, validation_period=None,
                 training_periods=None, validation_periods=None, mape=None, mae=None,
                 reason=None, candidates=None):
        self.status = status
        self.method = method
        self.training_period = training_period
        self.validation_period = validation_period
        self.training_periods = training_periods
        self.validation_periods = validation_periods
        self.mape = mape
        self.mae = mae
        self.reason = reason
        self.candidates = list(candidates or [])

    @property
    def performed(self):
        return self.status == AVAILABLE

    @property
    def selected_from(self):
        """How many methods were compared on this same holdout, or None."""
        return len(self.candidates) or None

    def statement(self):
        """What the backtest showed, including why the figure flatters the method.

        The error is the *lowest* of every candidate scored on one holdout, and the method
        was selected for that. A statistic used to choose is optimistic as an estimate of
        the chosen thing: the winner's advantage is partly real skill and partly having
        suited those particular periods. Reporting it without that sentence would let a
        reader treat it as a clean out-of-sample error, and the uncertainty band derived
        from it is narrower for the same reason.
        """
        if not self.performed:
            return ("No holdout validation was performed: %s"
                    % (self.reason or "history was too short to hold any of it back."))
        selection = ""
        if self.selected_from and self.selected_from > 1:
            selection = (" This is the lowest error among %d methods scored on the same "
                         "holdout, and the method was selected on it, so it flatters the "
                         "method and the band derived from it is correspondingly narrow."
                         % self.selected_from)
        return ("Backtest on %s (%d periods held out, %d used for training): mean absolute "
                "percentage error %s. Past error is not a guarantee of future error.%s"
                % (self.validation_period, self.validation_periods or 0,
                   self.training_periods or 0, percent(self.mape), selection))

    def as_dict(self):
        record = {"status": self.status, "method": self.method,
                  "training_period": self.training_period,
                  "validation_period": self.validation_period,
                  "training_periods": self.training_periods,
                  "validation_periods": self.validation_periods,
                  "mape": _plain(self.mape), "mae": _plain(self.mae),
                  "reason": self.reason, "statement": self.statement(),
                  "candidates": _plain(self.candidates)}
        return {k: v for k, v in record.items() if v not in (None, [])}

    def __repr__(self):
        return "Validation(%s %s)" % (self.status, self.mape)


class ForecastResult:
    """One metric, forecast over one horizon - or a precise account of why it was not.

    A `ForecastResult` is always returned. A caller never has to distinguish "no forecast
    because nothing happened" from "no forecast because it was refused": `status` and
    `reason` say which, and the unavailable case still carries the history and provenance
    that were established before the refusal.
    """

    __slots__ = ("forecast_id", "metric", "metric_name", "status", "reason", "unit",
                 "currency", "frequency", "history", "historical_period",
                 "forecast_period", "horizon", "method", "method_name",
                 "method_rationale", "parameters", "scenarios", "assumptions",
                 "uncertainty", "validation", "quality_grade", "provenance", "caveats",
                 "confidence", "depends_on", "min_history")

    def __init__(self, forecast_id, metric, metric_name=None, status=AVAILABLE,
                 reason=None, unit=None, currency=None, frequency=None, history=None,
                 historical_period=None, forecast_period=None, horizon=None, method=None,
                 method_name=None, method_rationale=None, parameters=None, scenarios=None,
                 assumptions=None, uncertainty=None, validation=None, quality_grade=None,
                 provenance=None, caveats=(), confidence=None, depends_on=(),
                 min_history=None):
        if status not in STATUSES:
            raise ForecastError("unknown forecast status %r" % (status,))
        self.forecast_id = forecast_id
        self.metric = metric
        self.metric_name = metric_name or metric
        self.status = status
        self.reason = reason
        self.unit = unit
        self.currency = currency
        self.frequency = frequency
        self.history = list(history or [])
        self.historical_period = historical_period
        self.forecast_period = forecast_period
        self.horizon = horizon
        self.method = method
        self.method_name = method_name
        self.method_rationale = method_rationale
        self.parameters = dict(parameters or {})
        self.scenarios = dict(scenarios or {})
        self.assumptions = assumptions if assumptions is not None else AssumptionRegister()
        self.uncertainty = uncertainty or UncertaintyBand(NO_BAND)
        self.validation = validation or Validation(INSUFFICIENT_DATA)
        self.quality_grade = quality_grade
        self.provenance = dict(provenance or {})
        self.caveats = list(caveats)
        self.confidence = confidence
        self.depends_on = tuple(depends_on)
        self.min_history = min_history

    @property
    def available(self):
        return self.status == AVAILABLE

    @property
    def history_periods(self):
        return len(self.history)

    def scenario(self, name):
        return self.scenarios.get(name)

    def base(self):
        return self.scenarios.get(BASE)

    def base_total(self):
        scenario = self.base()
        return scenario.total() if scenario is not None else None

    def add_caveat(self, caveat):
        if caveat and caveat not in self.caveats:
            self.caveats.append(caveat)

    def findings(self, analysis_type="forecast"):
        """Class-6 findings, one per scenario, for the analytics contract.

        Emitted as `ASSUMPTION` rather than `CALCULATION` on purpose: the arithmetic is
        deterministic, but the *statement* is about a period that has not happened.
        """
        out = []
        if not self.available:
            return out
        for name in SCENARIOS:
            scenario = self.scenarios.get(name)
            if scenario is None:
                continue
            total = scenario.total()
            low, high = self.uncertainty.bounds(total)
            statement = (
                "Under the %s scenario, forecast %s for %s is %s (%d periods, %s method)."
                % (name, self.metric_name, self.forecast_period,
                   money(total, self.currency), self.horizon or 0, self.method))
            finding = analytics_contract.AnalysisFinding(
                analysis_id="%s.%s.%s" % (analysis_type, self.metric, name),
                analysis_type=analysis_type,
                finding_type=analytics_contract.ASSUMPTION,
                statement=statement,
                metric=self.metric,
                period=self.forecast_period,
                comparison_period=self.historical_period,
                observed=total,
                unit=self.unit,
                currency=self.currency,
                basis=self.method,
                inputs={"method": self.method, "horizon": self.horizon,
                        "history_periods": self.history_periods,
                        "scenario": name,
                        "adjustment_pct": scenario.adjustment_pct,
                        "band_low": low, "band_high": high},
                caveats=list(self.caveats) + [self.uncertainty.statement(),
                                              self.validation.statement()],
                assumptions=[a.statement
                             for a in self.assumptions.for_scenario(name)],
                confidence=self.confidence,
                provenance=dict(self.provenance))
            out.append(finding)
        return out

    def summary(self):
        return {"forecast_id": self.forecast_id, "metric": self.metric,
                "status": self.status, "method": self.method,
                "history_periods": self.history_periods, "horizon": self.horizon,
                "scenarios": sorted(self.scenarios),
                "validated": self.validation.performed,
                "assumptions": len(self.assumptions)}

    def as_dict(self):
        record = {
            "forecast_id": self.forecast_id,
            "metric": self.metric,
            "metric_name": self.metric_name,
            "status": self.status,
            "reason": self.reason,
            "unit": self.unit,
            "currency": self.currency,
            "frequency": self.frequency,
            "depends_on": list(self.depends_on),
            "min_history": self.min_history,
            "history_periods": self.history_periods,
            "historical_period": self.historical_period,
            "forecast_period": self.forecast_period,
            "horizon": self.horizon,
            "method": self.method,
            "method_name": self.method_name,
            "method_rationale": self.method_rationale,
            "parameters": _plain(self.parameters),
            "history": [{"period": p, "value": _plain(v)} for p, v in self.history],
            "scenarios": {name: s.as_dict() for name, s in sorted(self.scenarios.items())},
            "assumptions": self.assumptions.as_dict(),
            "uncertainty": self.uncertainty.as_dict(),
            "validation": self.validation.as_dict(),
            "quality_grade": self.quality_grade,
            "provenance": dict(self.provenance),
            "caveats": list(self.caveats),
            "confidence": self.confidence,
            "evidence_class": evidence_mod.ASSUMPTION,
            "summary": self.summary(),
        }
        return {k: v for k, v in record.items() if v not in (None, [], {}, ())}

    def __repr__(self):
        return "ForecastResult(%s: %s, %s)" % (self.metric, self.status, self.method)


class ForecastSet(analytics_contract.AnalysisSet):
    """Every forecast produced for one dataset.

    A subclass rather than a sibling because everything an `AnalysisSet` does - caveat
    propagation, quality-driven confidence, ledger recording, limitations, serialisation -
    is wanted here unchanged. Exactly one rule differs, and it is the reason the subclass
    exists: this engine is permitted to emit provenance class 6, because an estimate about a
    future period is the one thing the historical analytics layer must never produce.
    Interpretation and recommendation stay forbidden.
    """

    __slots__ = ("forecasts", "horizon", "requested_horizon", "frequency")

    #: `AnalysisSet.ENGINE_EMITS` plus the one class this engine exists to produce.
    EMITS = (analytics_contract.FACT, analytics_contract.CALCULATION,
             analytics_contract.ASSUMPTION)

    def __init__(self, analysis_type="forecast", **kwargs):
        self.forecasts = {}
        self.horizon = kwargs.pop("horizon", None)
        self.requested_horizon = kwargs.pop("requested_horizon", None)
        self.frequency = kwargs.pop("frequency", None)
        super(ForecastSet, self).__init__(analysis_type, **kwargs)

    @classmethod
    def adopt(cls, analysis, **extra):
        """Re-wrap a prepared `AnalysisSet` as a `ForecastSet`.

        The Milestone 6 `domain.prepare()` already does everything a forecast needs before
        any arithmetic happens - honours the quality halt, attaches quality caveats, marks
        provisional mappings, and builds the privacy policy. Adopting its output reuses all
        of that rather than restating it here, which is why this module contains no copy of
        the quality gate.
        """
        adopted = cls(analysis.analysis_type, status=analysis.status,
                      reason=analysis.reason, **extra)
        for slot in analytics_contract.AnalysisSet.__slots__:
            if slot in ("analysis_type", "status", "reason"):
                continue
            setattr(adopted, slot, getattr(analysis, slot))
        return adopted

    def add(self, finding):
        """As `AnalysisSet.add`, widened by exactly one provenance class."""
        if finding.finding_type not in self.EMITS:
            raise analytics_contract.AnalysisError(
                "the forecasting engine may emit only %s; %r is judgement and belongs to "
                "a skill" % (" or ".join(self.EMITS), finding.finding_type))
        for caveat in self.caveats:
            if caveat not in finding.caveats:
                finding.caveats.append(caveat)
        if finding.confidence is None:
            finding.confidence = self.default_confidence
        if not finding.provenance:
            finding.provenance = dict(self.provenance)
        self.findings.append(finding)
        return finding

    def register(self, forecast):
        """Attach one metric's forecast and emit its scenario findings."""
        self.forecasts[forecast.metric] = forecast
        if forecast.available:
            for finding in forecast.findings(self.analysis_type):
                self.add(finding)
        else:
            self.limit("forecast_%s" % forecast.status, forecast.metric_name,
                       forecast.reason or "No forecast could be produced.",
                       status=forecast.status)
        return forecast

    def available_forecasts(self):
        return {k: v for k, v in self.forecasts.items() if v.available}

    def assumption_register(self):
        """Every assumption across every forecast, in metric order."""
        register = AssumptionRegister()
        for metric in sorted(self.forecasts):
            register.entries.extend(self.forecasts[metric].assumptions.entries)
        return register

    def as_dict(self):
        record = super(ForecastSet, self).as_dict()
        record["horizon"] = self.horizon
        record["requested_horizon"] = self.requested_horizon
        record["frequency"] = self.frequency
        record["forecasts"] = {k: v.as_dict() for k, v in sorted(self.forecasts.items())}
        record["assumption_register"] = self.assumption_register().as_dict()
        return record

    def __repr__(self):
        return "ForecastSet(%s: %d forecasts, %d findings, %d limitations)" % (
            self.status, len(self.forecasts), len(self.findings), len(self.limitations))
