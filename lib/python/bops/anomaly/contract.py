"""The anomaly output contract: what "unusual" means, and what it deliberately does not.

An anomaly detector answers exactly one question - *is this observation far from what this
series normally does?* - and it answers it with arithmetic a reader can check. It does not
answer, and must never appear to answer:

    why the value moved            that is causal analysis, which the engine cannot do
    whether it is bad              that is judgement, and belongs to a skill
    whether someone did something  that is an allegation, and belongs nowhere in M8

The last one is the reason this module states the fraud boundary as data rather than as
documentation. `FRAUD_LANGUAGE` is asserted against in the tests, and `INVESTIGATION_NOTE`
is the strongest thing an anomaly finding is permitted to say about what a reader should do
with it. An unusual number is a place to look, not a conclusion about a person.

Two vocabularies meet here and stay distinct:

    status       how unusual it is, measured against a baseline  (this module)
    materiality  whether it is big enough to matter, per user policy  (`materiality.py`)

They are independent. A tiny deviation can be statistically striking, and a huge one can be
ordinary for a volatile series. Only when both agree is a finding a `material_anomaly`.
"""

from decimal import Decimal, ROUND_HALF_UP

from ..analytics import contract as analytics_contract

ZERO = Decimal("0")

# -- observation status ------------------------------------------------------

NORMAL = "normal"
UNUSUAL = "unusual"
MATERIAL_ANOMALY = "material_anomaly"
INSUFFICIENT_DATA = "insufficient_data"

STATUSES = (NORMAL, UNUSUAL, MATERIAL_ANOMALY, INSUFFICIENT_DATA)

#: Statuses that represent something worth showing a reader.
FLAGGED = (UNUSUAL, MATERIAL_ANOMALY)

# -- analysis-level status (the analytics vocabulary, unchanged) -------------

AVAILABLE = analytics_contract.AVAILABLE
UNAVAILABLE = analytics_contract.UNAVAILABLE
NOT_APPLICABLE = analytics_contract.NOT_APPLICABLE

# -- direction ---------------------------------------------------------------

ABOVE = "above_baseline"
BELOW = "below_baseline"

# -- the fraud boundary, expressed as data -----------------------------------

#: Words no anomaly output may contain. Asserted in the tests against every emitted
#: statement. Anomaly detection observes deviation; it establishes nothing about intent.
FRAUD_LANGUAGE = ("fraud", "fraudulent", "fraudster", "embezzl", "theft", "stolen",
                  "steal", "scam", "launder", "criminal", "suspicious activity",
                  "wrongdoing", "misconduct", "manipulat", "falsif", "forged")

#: The strongest permitted statement about what to do with an anomaly.
INVESTIGATION_NOTE = ("This is a deviation from the historical baseline and may warrant "
                      "investigation. It does not establish a cause, and it is not "
                      "evidence of fraud or of any wrongdoing.")

#: Causal words that would turn an observation into an explanation.
CAUSAL_LANGUAGE = ("because", "caused by", "due to the fact", "as a result of customers",
                   "customers preferred", "driven by demand")


def _plain(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def money(value, currency=None):
    if value is None:
        return "unavailable"
    quantised = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return "%s %s" % (currency, quantised) if currency else str(quantised)


def percent(value, places=2):
    if value is None:
        return "unavailable"
    quant = Decimal("1") if places == 0 else Decimal("0." + "0" * places)
    return "%s%%" % Decimal(value).quantize(quant, rounding=ROUND_HALF_UP)


class AnomalyError(Exception):
    """An anomaly finding violates the contract - a defect, not a user error."""


class Baseline:
    """What "normal" was taken to be, and how it was computed.

    Carried with every observation rather than recomputed for display. An anomaly whose
    baseline is not stated is an assertion, not a finding - a reader cannot tell whether
    the value is odd or the baseline is.
    """

    __slots__ = ("method", "centre", "spread", "spread_kind", "periods", "window",
                 "description")

    def __init__(self, method, centre, spread=None, spread_kind=None, periods=None,
                 window=None, description=None):
        self.method = method
        self.centre = centre
        self.spread = spread
        self.spread_kind = spread_kind
        self.periods = periods
        self.window = window
        self.description = description

    def statement(self, currency=None):
        return ("baseline %s (%s over %s periods)"
                % (money(self.centre, currency), self.description or self.method,
                   self.periods if self.periods is not None else "?"))

    def as_dict(self):
        record = {"method": self.method, "centre": _plain(self.centre),
                  "spread": _plain(self.spread), "spread_kind": self.spread_kind,
                  "periods": self.periods, "window": self.window,
                  "description": self.description}
        return {k: v for k, v in record.items() if v is not None}

    def __repr__(self):
        return "Baseline(%s centre=%s)" % (self.method, self.centre)


class Contributor:
    """One dimension member's share of an anomalous period's deviation.

    Attribution is arithmetic, not explanation: it says *where* in the data the deviation
    sits, never why. The label passes through the Milestone 3 privacy policy, so a customer
    contributor is pseudonymised whenever the presentation mode requires it.
    """

    __slots__ = ("dimension", "label", "redacted", "value", "baseline", "deviation",
                 "share_pct")

    def __init__(self, dimension, label, value, baseline=None, deviation=None,
                 share_pct=None, redacted=False):
        self.dimension = dimension
        self.label = label
        self.value = value
        self.baseline = baseline
        self.deviation = deviation
        self.share_pct = share_pct
        self.redacted = redacted

    def as_dict(self):
        record = {"dimension": self.dimension, "label": self.label,
                  "redacted": self.redacted or None,
                  "value": _plain(self.value), "baseline": _plain(self.baseline),
                  "deviation": _plain(self.deviation),
                  "share_pct": _plain(self.share_pct)}
        return {k: v for k, v in record.items() if v is not None}

    def __repr__(self):
        return "Contributor(%s %s)" % (self.label, self.deviation)


class Observation:
    """One period of one metric, measured against its baseline.

    `status` is set by the detector from the deviation; `materiality` is set from the user's
    configured policy. `MATERIAL_ANOMALY` requires both, which is what stops a volatile
    series from producing a page of alarming, meaningless flags.
    """

    __slots__ = ("metric", "metric_name", "period", "observed", "baseline", "deviation",
                 "deviation_pct", "score", "score_unit", "threshold", "status",
                 "direction", "materiality", "materiality_reason", "method",
                 "contributors", "caveats", "dimension", "dimension_value",
                 "dimension_redacted", "currency", "unit")

    def __init__(self, metric, period, observed, baseline, deviation=None,
                 deviation_pct=None, score=None, score_unit=None, threshold=None,
                 status=NORMAL, direction=None, materiality=None,
                 materiality_reason=None, method=None, contributors=None, caveats=(),
                 metric_name=None, dimension=None, dimension_value=None,
                 dimension_redacted=False, currency=None, unit=None):
        if status not in STATUSES:
            raise AnomalyError("unknown anomaly status %r" % (status,))
        self.metric = metric
        self.metric_name = metric_name or metric
        self.period = period
        self.observed = observed
        self.baseline = baseline
        self.deviation = deviation
        self.deviation_pct = deviation_pct
        self.score = score
        self.score_unit = score_unit
        self.threshold = threshold
        self.status = status
        self.direction = direction
        self.materiality = materiality
        self.materiality_reason = materiality_reason
        self.method = method
        self.contributors = list(contributors or [])
        self.caveats = list(caveats)
        self.dimension = dimension
        self.dimension_value = dimension_value
        self.dimension_redacted = dimension_redacted
        self.currency = currency
        self.unit = unit

    @property
    def flagged(self):
        return self.status in FLAGGED

    def score_text(self):
        """The deviation expressed in the detector's own units."""
        if self.score is None:
            return "deviation unscored"
        if self.score_unit == "%":
            return percent(self.score)
        rounded = Decimal(self.score).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return "%s %s" % (rounded, self.score_unit or "units")

    def statement(self):
        """The sentence a reader sees. Descriptive only - no cause, no allegation."""
        where = " for %s" % self.dimension_value if self.dimension_value else ""
        magnitude = None if self.deviation is None else abs(self.deviation)
        share = (percent(self.deviation_pct) if self.deviation_pct is not None
                 else "an undefined percentage")
        return ("%s%s in %s was %s, %s the %s by %s (%s of the baseline; %s)."
                % (self.metric_name, where, self.period,
                   money(self.observed, self.currency),
                   "above" if self.direction == ABOVE else "below",
                   self.baseline.statement(self.currency) if self.baseline else "baseline",
                   money(magnitude, self.currency), share, self.score_text()))

    def as_dict(self):
        record = {
            "anomaly_id": "anomaly.%s.%s%s" % (
                self.metric, self.period,
                ".%s" % self.dimension_value if self.dimension_value else ""),
            "metric": self.metric, "metric_name": self.metric_name,
            "period": self.period,
            "observed_value": _plain(self.observed),
            "baseline": self.baseline.as_dict() if self.baseline else None,
            "deviation": _plain(self.deviation),
            "deviation_pct": _plain(self.deviation_pct),
            "score": _plain(self.score), "score_unit": self.score_unit,
            "threshold": _plain(self.threshold),
            "status": self.status, "direction": self.direction,
            "materiality": self.materiality,
            "materiality_reason": self.materiality_reason,
            "method": self.method,
            "dimension": self.dimension, "dimension_value": self.dimension_value,
            "dimension_redacted": self.dimension_redacted or None,
            "currency": self.currency, "unit": self.unit,
            "contributors": [c.as_dict() for c in self.contributors] or None,
            "caveats": list(self.caveats) or None,
        }
        return {k: v for k, v in record.items() if v is not None}

    def finding(self, analysis_type="anomaly"):
        """A `CALCULATION` finding: the deviation is measured, not assumed.

        Unlike a forecast, an anomaly is entirely about periods that already happened, so
        it is evidential. What it is *not* is an explanation, which is why the investigation
        note travels with every flagged observation.
        """
        caveats = list(self.caveats)
        if self.flagged and INVESTIGATION_NOTE not in caveats:
            caveats.append(INVESTIGATION_NOTE)
        return analytics_contract.AnalysisFinding(
            analysis_id="%s.%s.%s%s" % (
                analysis_type, self.metric, self.period,
                ".%s" % self.dimension_value if self.dimension_value else ""),
            analysis_type=analysis_type,
            finding_type=analytics_contract.CALCULATION,
            statement=self.statement(),
            metric=self.metric,
            dimension=self.dimension,
            dimension_value=self.dimension_value,
            dimension_redacted=self.dimension_redacted,
            period=self.period,
            observed=self.observed,
            comparison=self.baseline.centre if self.baseline else None,
            change=self.deviation,
            change_pct=self.deviation_pct,
            unit=self.unit,
            currency=self.currency,
            materiality=self.materiality,
            materiality_reason=self.materiality_reason,
            basis="anomaly.%s" % (self.method or "detector"),
            inputs={"baseline_method": self.baseline.method if self.baseline else None,
                    "baseline_centre": self.baseline.centre if self.baseline else None,
                    "baseline_spread": self.baseline.spread if self.baseline else None,
                    "baseline_periods": self.baseline.periods if self.baseline else None,
                    "score": self.score, "score_unit": self.score_unit,
                    "threshold": self.threshold, "anomaly_status": self.status,
                    "contributors": [c.as_dict() for c in self.contributors]},
            caveats=caveats,
            direction=self.direction)

    def __repr__(self):
        return "Observation(%s %s %s)" % (self.metric, self.period, self.status)


class AnomalySet(analytics_contract.AnalysisSet):
    """Every anomaly scan run over one dataset.

    A plain `AnalysisSet` subclass with no widened emission rule: anomalies are
    `CALCULATION` findings, so the Milestone 6 contract already covers them exactly. The
    subclass exists only to carry the scanned observations alongside the findings, so a
    consumer can read the full scan - including the periods that were checked and found
    normal - rather than only the flags.
    """

    __slots__ = ("observations", "scanned_metrics", "sensitivity", "min_baseline_periods")

    def __init__(self, analysis_type="anomaly", **kwargs):
        self.observations = []
        self.scanned_metrics = {}
        self.sensitivity = kwargs.pop("sensitivity", None)
        self.min_baseline_periods = kwargs.pop("min_baseline_periods", None)
        super(AnomalySet, self).__init__(analysis_type, **kwargs)

    @classmethod
    def adopt(cls, analysis, **extra):
        """Re-wrap a prepared `AnalysisSet`. See `forecast.contract.ForecastSet.adopt`."""
        adopted = cls(analysis.analysis_type, status=analysis.status,
                      reason=analysis.reason, **extra)
        for slot in analytics_contract.AnalysisSet.__slots__:
            if slot in ("analysis_type", "status", "reason"):
                continue
            setattr(adopted, slot, getattr(analysis, slot))
        return adopted

    def observe(self, observation, emit=True):
        """Record one checked period; emit a finding only when it is actually unusual."""
        self.observations.append(observation)
        if emit and observation.flagged:
            self.add(observation.finding(self.analysis_type))
        return observation

    def flagged(self):
        return [o for o in self.observations if o.flagged]

    def material(self):
        return [o for o in self.observations if o.status == MATERIAL_ANOMALY]

    def by_metric(self, metric):
        return [o for o in self.observations if o.metric == metric]

    def summary(self):
        record = super(AnomalySet, self).summary()
        record.update({
            "observations": len(self.observations),
            "flagged": len(self.flagged()),
            "material_anomalies": len(self.material()),
            "metrics_scanned": dict(self.scanned_metrics),
            "sensitivity": self.sensitivity,
        })
        return record

    def as_dict(self):
        record = super(AnomalySet, self).as_dict()
        record["sensitivity"] = self.sensitivity
        record["min_baseline_periods"] = self.min_baseline_periods
        record["scanned_metrics"] = dict(self.scanned_metrics)
        record["observations"] = [o.as_dict() for o in self.observations]
        record["fraud_boundary"] = INVESTIGATION_NOTE
        return record

    def __repr__(self):
        return "AnomalySet(%s: %d observations, %d flagged)" % (
            self.status, len(self.observations), len(self.flagged()))
