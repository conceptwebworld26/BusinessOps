"""The analytics output contract: what a deterministic finding looks like.

Milestone 6 sits above the KPI engine, so its output has to answer a harder question than
"what is the number". It has to say **what kind of statement this is** — something the data
shows, something the engine computed, something a reader inferred, or something someone is
being advised to do — and it has to keep that distinction attached to the statement rather
than to the prose around it.

Four classifications, and they are not interchangeable:

    FACT            read directly from the data (evidence class 1)
    CALCULATION     produced by the engine from class 1 (evidence class 4)
    INTERPRETATION  a reading of facts and calculations (evidence class 5)
    RECOMMENDATION  a proposed action (evidence class 7)

The engine emits only `FACT` and `CALCULATION`. Interpretation is judgement and belongs to
a skill; a recommendation additionally requires all six fields the evidence ledger demands,
which is why `as_claim()` delegates that rule to `evidence.Claim` rather than restating it.

The status vocabulary deliberately mirrors the KPI engine's, because a reader should not
have to learn a second set of words for the same four situations.
"""

from decimal import Decimal

from .. import evidence as evidence_mod

# -- analysis status --------------------------------------------------------

AVAILABLE = "available"                   # the analysis ran and produced findings
UNAVAILABLE = "unavailable"               # a required input is absent
NOT_APPLICABLE = "not_applicable"         # meaningless for this business model
INSUFFICIENT_DATA = "insufficient_data"   # inputs present, history too short

STATUSES = (AVAILABLE, UNAVAILABLE, NOT_APPLICABLE, INSUFFICIENT_DATA)

# -- finding classification -------------------------------------------------

FACT = "FACT"
CALCULATION = "CALCULATION"
INTERPRETATION = "INTERPRETATION"
RECOMMENDATION = "RECOMMENDATION"
ASSUMPTION = "ASSUMPTION"

FINDING_TYPES = (FACT, CALCULATION, INTERPRETATION, RECOMMENDATION, ASSUMPTION)

#: The evidence class each classification maps to. The ledger owns the class list.
EVIDENCE_CLASS = {
    FACT: evidence_mod.USER_DATA,
    CALCULATION: evidence_mod.CALCULATED,
    INTERPRETATION: evidence_mod.INTERPRETATION,
    ASSUMPTION: evidence_mod.ASSUMPTION,
    RECOMMENDATION: evidence_mod.RECOMMENDATION,
}

#: Classifications the deterministic engine is permitted to emit. Judgement is not one.
ENGINE_EMITS = (FACT, CALCULATION)


class AnalysisError(Exception):
    """A finding violates the contract — a defect, not a user error."""


def _plain(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


class Limitation:
    """Something this analysis could not do, and why.

    A limitation is not a failure. It is the part of the answer that says where the answer
    stops, and it is reported at the same prominence as the findings.
    """

    __slots__ = ("code", "subject", "reason", "status")

    def __init__(self, code, subject, reason, status=UNAVAILABLE):
        self.code = code
        self.subject = subject
        self.reason = reason
        self.status = status

    def as_dict(self):
        return {"code": self.code, "subject": self.subject,
                "reason": self.reason, "status": self.status}

    def __repr__(self):
        return "Limitation(%s: %s)" % (self.code, self.subject)


class AnalysisFinding:
    """One deterministic analytical statement, carrying everything needed to audit it."""

    __slots__ = ("analysis_id", "analysis_type", "finding_type", "statement", "metric",
                 "dimension", "dimension_value", "dimension_redacted", "period",
                 "comparison_period", "observed", "comparison", "change", "change_pct",
                 "share_pct", "unit", "currency", "materiality", "materiality_reason",
                 "basis", "inputs", "fields_used", "caveats", "assumptions", "confidence",
                 "direction", "provenance")

    def __init__(self, analysis_id, analysis_type, finding_type, statement,
                 metric=None, dimension=None, dimension_value=None,
                 dimension_redacted=False, period=None, comparison_period=None,
                 observed=None, comparison=None, change=None, change_pct=None,
                 share_pct=None, unit=None, currency=None, materiality=None,
                 materiality_reason=None, basis=None, inputs=None, fields_used=(),
                 caveats=(), assumptions=(), confidence=None, direction=None,
                 provenance=None):
        if finding_type not in FINDING_TYPES:
            raise AnalysisError("unknown finding type %r" % (finding_type,))
        if finding_type == CALCULATION and not basis:
            raise AnalysisError(
                "a calculation must name the primitive or metric that produced it")
        self.analysis_id = analysis_id
        self.analysis_type = analysis_type
        self.finding_type = finding_type
        self.statement = statement
        self.metric = metric
        self.dimension = dimension
        self.dimension_value = dimension_value
        self.dimension_redacted = dimension_redacted
        self.period = period
        self.comparison_period = comparison_period
        self.observed = observed
        self.comparison = comparison
        self.change = change
        self.change_pct = change_pct
        self.share_pct = share_pct
        self.unit = unit
        self.currency = currency
        self.materiality = materiality
        self.materiality_reason = materiality_reason
        self.basis = basis
        self.inputs = dict(inputs or {})
        self.fields_used = tuple(fields_used)
        self.caveats = list(caveats)
        self.assumptions = list(assumptions)
        self.confidence = confidence
        self.direction = direction
        self.provenance = dict(provenance or {})

    @property
    def evidence_class(self):
        return EVIDENCE_CLASS[self.finding_type]

    @property
    def is_evidential(self):
        return self.evidence_class in evidence_mod.EVIDENTIAL

    def as_claim(self, **extra):
        """Convert to a ledger claim. The ledger, not this module, enforces its own rules."""
        kwargs = {"confidence": self.confidence,
                  "caveats": list(self.caveats),
                  "inputs": _plain(self.inputs)}
        if self.finding_type == CALCULATION:
            kwargs["formula"] = self.basis
        if self.finding_type == FACT:
            kwargs["source"] = self.provenance or {"source_name": "analysed dataset"}
        kwargs.update(extra)
        return evidence_mod.Claim(self.statement, self.evidence_class, **kwargs)

    def as_dict(self):
        record = {
            "analysis_id": self.analysis_id,
            "analysis_type": self.analysis_type,
            "finding_type": self.finding_type,
            "evidence_class": self.evidence_class,
            "statement": self.statement,
            "metric": self.metric,
            "dimension": self.dimension,
            "dimension_value": self.dimension_value,
            "dimension_redacted": self.dimension_redacted or None,
            "period": self.period,
            "comparison_period": self.comparison_period,
            "observed": _plain(self.observed),
            "comparison": _plain(self.comparison),
            "change": _plain(self.change),
            "change_pct": _plain(self.change_pct),
            "share_pct": _plain(self.share_pct),
            "unit": self.unit,
            "currency": self.currency,
            "materiality": self.materiality,
            "materiality_reason": self.materiality_reason,
            "basis": self.basis,
            "inputs": _plain(self.inputs),
            "fields_used": list(self.fields_used),
            "caveats": self.caveats,
            "assumptions": self.assumptions,
            "confidence": self.confidence,
            "direction": self.direction,
            "provenance": self.provenance,
        }
        return {k: v for k, v in record.items() if v not in (None, [], {}, ())}

    def __repr__(self):
        return "AnalysisFinding(%s %s)" % (self.finding_type, self.analysis_id)


class AnalysisSet:
    """Everything one analytical domain produced for one dataset.

    An `AnalysisSet` is always returned — including when nothing could be analysed. A
    caller never has to distinguish "no findings because nothing happened" from "no findings
    because the analysis never ran": `status` and `limitations` say which.
    """

    __slots__ = ("analysis_type", "status", "reason", "findings", "limitations",
                 "dimensions_covered", "dimensions_skipped", "restricted_dimensions",
                 "presentation", "caveats", "provenance", "metrics_used", "primitives_used",
                 "business_model", "currency", "quality_grade", "periods",
                 "comparison_periods")

    def __init__(self, analysis_type, status=AVAILABLE, reason=None, findings=None,
                 limitations=None, dimensions_covered=(), dimensions_skipped=None,
                 restricted_dimensions=(), presentation=None, caveats=(), provenance=None,
                 metrics_used=(), primitives_used=(), business_model=None, currency=None,
                 quality_grade=None, periods=None, comparison_periods=None):
        if status not in STATUSES:
            raise AnalysisError("unknown analysis status %r" % (status,))
        self.analysis_type = analysis_type
        self.status = status
        self.reason = reason
        self.findings = list(findings or [])
        self.limitations = list(limitations or [])
        self.dimensions_covered = list(dimensions_covered)
        self.dimensions_skipped = dict(dimensions_skipped or {})
        self.restricted_dimensions = list(restricted_dimensions)
        self.presentation = presentation
        self.caveats = list(caveats)
        self.provenance = dict(provenance or {})
        self.metrics_used = list(metrics_used)
        self.primitives_used = list(primitives_used)
        self.business_model = business_model
        self.currency = currency
        self.quality_grade = quality_grade
        self.periods = periods
        self.comparison_periods = comparison_periods

    # -- assembly -----------------------------------------------------------

    def add(self, finding):
        if finding.finding_type not in ENGINE_EMITS:
            raise AnalysisError(
                "the deterministic engine may emit only %s; %r is judgement and belongs "
                "to a skill" % (" or ".join(ENGINE_EMITS), finding.finding_type))
        for caveat in self.caveats:
            if caveat not in finding.caveats:
                finding.caveats.append(caveat)
        if finding.confidence is None:
            finding.confidence = self.default_confidence
        if not finding.provenance:
            finding.provenance = dict(self.provenance)
        self.findings.append(finding)
        return finding

    def limit(self, code, subject, reason, status=UNAVAILABLE):
        limitation = Limitation(code, subject, reason, status)
        self.limitations.append(limitation)
        return limitation

    def note_primitive(self, name):
        if name not in self.primitives_used:
            self.primitives_used.append(name)

    def note_metric(self, kpi_id):
        if kpi_id not in self.metrics_used:
            self.metrics_used.append(kpi_id)

    def add_caveat(self, caveat):
        """A caveat that travels with every finding, past and future."""
        if caveat in self.caveats:
            return
        self.caveats.append(caveat)
        for finding in self.findings:
            if caveat not in finding.caveats:
                finding.caveats.append(caveat)

    # -- state --------------------------------------------------------------

    @property
    def default_confidence(self):
        """Quality drives confidence. A warning is not a footnote, it is a downgrade."""
        from ..quality import contract as quality_contract
        if self.quality_grade == quality_contract.PASS:
            return evidence_mod.HIGH
        return evidence_mod.MEDIUM

    @property
    def available(self):
        return self.status == AVAILABLE

    def of_type(self, finding_type):
        return [f for f in self.findings if f.finding_type == finding_type]

    def material(self):
        from .. import materiality as materiality_mod
        return [f for f in self.findings if f.materiality == materiality_mod.MATERIAL]

    def by_dimension(self, dimension):
        return [f for f in self.findings if f.dimension == dimension]

    def record_in(self, ledger):
        """Append every finding to an evidence ledger, preserving its class."""
        return [ledger.add(f.as_claim()) for f in self.findings]

    def summary(self):
        counts = {}
        for finding in self.findings:
            counts[finding.finding_type] = counts.get(finding.finding_type, 0) + 1
        return {"analysis_type": self.analysis_type, "status": self.status,
                "findings": len(self.findings), "by_type": counts,
                "limitations": len(self.limitations),
                "dimensions_covered": list(self.dimensions_covered),
                "dimensions_skipped": dict(self.dimensions_skipped)}

    def as_dict(self):
        return {
            "analysis_type": self.analysis_type,
            "status": self.status,
            "reason": self.reason,
            "business_model": self.business_model,
            "currency": self.currency,
            "quality_grade": self.quality_grade,
            "presentation": self.presentation,
            "periods": self.periods,
            "comparison_periods": self.comparison_periods,
            "metrics_used": list(self.metrics_used),
            "primitives_used": list(self.primitives_used),
            "dimensions_covered": list(self.dimensions_covered),
            "dimensions_skipped": dict(self.dimensions_skipped),
            "restricted_dimensions": list(self.restricted_dimensions),
            "caveats": list(self.caveats),
            "provenance": dict(self.provenance),
            "findings": [f.as_dict() for f in self.findings],
            "limitations": [item.as_dict() for item in self.limitations],
            "summary": self.summary(),
        }

    def __len__(self):
        return len(self.findings)

    def __repr__(self):
        return "AnalysisSet(%s: %s, %d findings, %d limitations)" % (
            self.analysis_type, self.status, len(self.findings), len(self.limitations))
