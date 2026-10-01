"""The synthesis contract: one typed statement that knows where it came from.

Milestone 10.1 builds the intermediate representation that SWOT, strategy, decision
support and executive reporting will all read. Its job is not to say anything new. Its job
is to let four downstream capabilities share one set of statements **without any of them
having to re-derive what kind of statement each one is, what it rests on, or how far it
may be trusted**.

Three properties make that safe, and each is enforced here rather than described:

1.  **Nothing is promoted.** A candidate claim stays candidate; external evidence stays
    untrusted external evidence; an interpretation stays an interpretation. There is no
    code path in this package that raises the standing of anything, which is why no
    constant here names a "verified" state.
2.  **Nothing is asserted without provenance.** A statement either names source objects
    that actually exist in the set, or it carries provenance explicitly marked
    `unavailable` and is graded accordingly. Fabricated provenance is refused, not noted.
3.  **Recommendations are not produced.** Class 7 needs six fields and a decision owner;
    M10.1 has neither. `RECOMMENDATION` is a reserved, refused kind, so an advisory
    sentence cannot enter as an interpretation and be read back as advice.

Vocabulary is **reused**, not restated. Statement kinds come from `analytics.contract`,
the provenance classes from `evidence`, the tier and support rules from
`research.sources`, and confidence from `evidence`. A second spelling of any of those
would be a second policy (ADR-0012).
"""

import hashlib
from decimal import Decimal

from .. import evidence as evidence_mod
from ..analytics import contract as analytics_contract
from ..kpi import contract as kpi_contract
from ..research import contract as research_contract
from ..research import evidence_set as evidence_set_mod
from ..research import handoff as handoff_mod
from ..research import sources as sources_mod


class SynthesisError(Exception):
    """A synthesis input violates its contract - a defect, not a user error."""


# ---------------------------------------------------------------------------
# Statement kinds - reused wholesale from the analytics contract
# ---------------------------------------------------------------------------

FACT = analytics_contract.FACT
CALCULATION = analytics_contract.CALCULATION
INTERPRETATION = analytics_contract.INTERPRETATION
RECOMMENDATION = analytics_contract.RECOMMENDATION
ASSUMPTION = analytics_contract.ASSUMPTION

#: What a source said. The internal analytics contract has no such kind because nothing
#: internal is externally sourced, but the ledger has had the class since ADR-0005 and
#: `evidence.Claim.label` already spells it `SOURCED`. Reusing that spelling keeps one
#: name for one concept; inventing `EXTERNAL_FACT` would create a second.
SOURCED = "SOURCED"

STATEMENT_KINDS = analytics_contract.FINDING_TYPES + (SOURCED,)

#: The evidence-ledger class each kind maps to. The ledger owns the class list; this map
#: extends the analytics one by the single class the analytics layer never needed.
EVIDENCE_CLASS = dict(analytics_contract.EVIDENCE_CLASS)
EVIDENCE_CLASS[SOURCED] = evidence_mod.EXTERNAL_SOURCED

#: What the synthesis foundation may emit. `RECOMMENDATION` is deliberately absent:
#: M10.1 establishes the representation a recommendation will later occupy, and produces
#: none. A downstream milestone that issues one does so through `evidence.Claim`, which
#: already demands all six class-7 fields.
SYNTHESIS_EMITS = (FACT, CALCULATION, SOURCED, INTERPRETATION, ASSUMPTION)

#: Kinds an internal statement may take. `SOURCED` is absent: internal data is not
#: externally sourced, and letting it borrow the label would hide where a number came from.
INTERNAL_KINDS = (FACT, CALCULATION, INTERPRETATION, ASSUMPTION)

#: Kinds an external statement may take. `FACT` and `CALCULATION` are absent, and that
#: absence is the mechanism behind "external source wording never becomes an internal
#: fact": there is no kind for it to become. What a source said is `SOURCED`; what we make
#: of it is `INTERPRETATION`.
EXTERNAL_KINDS = (SOURCED, INTERPRETATION, ASSUMPTION)

#: Kinds reserved for downstream milestones. Refused on construction.
DEFERRED_KINDS = (RECOMMENDATION,)

DEFERRED_NOTE = (
    "Recommendations are produced downstream (strategy, decision support), not by the "
    "synthesis foundation. This collection is reserved and is always empty in M10.1.")

#: The one spelling of untrusted, read from the module that defines it.
UNTRUSTED = evidence_set_mod.UNTRUSTED
INTERNAL_TRUST = "internal"


# ---------------------------------------------------------------------------
# Domains and origins
# ---------------------------------------------------------------------------

INTERNAL = "internal"
EXTERNAL = "external"
DOMAINS = (INTERNAL, EXTERNAL)

ORIGIN_KPI = "kpi"
ORIGIN_SALES = "sales"
ORIGIN_CUSTOMER = "customer"
ORIGIN_PRODUCT = "product"
ORIGIN_FINANCIAL = "financial"
ORIGIN_FORECAST = "forecast"
ORIGIN_ANOMALY = "anomaly"
ORIGIN_QUALITY = "quality"

#: External origins are the research categories, reused rather than re-spelled.
ORIGIN_COMPANY = research_contract.COMPANY
ORIGIN_MARKET = research_contract.MARKET
ORIGIN_COMPETITOR = research_contract.COMPETITOR
ORIGIN_INDUSTRY = research_contract.INDUSTRY

INTERNAL_ORIGINS = (ORIGIN_KPI, ORIGIN_SALES, ORIGIN_CUSTOMER, ORIGIN_PRODUCT,
                    ORIGIN_FINANCIAL, ORIGIN_FORECAST, ORIGIN_ANOMALY, ORIGIN_QUALITY)
EXTERNAL_ORIGINS = (ORIGIN_COMPANY, ORIGIN_MARKET, ORIGIN_COMPETITOR, ORIGIN_INDUSTRY)
ORIGINS = INTERNAL_ORIGINS + EXTERNAL_ORIGINS

DOMAIN_OF_ORIGIN = dict(
    [(o, INTERNAL) for o in INTERNAL_ORIGINS] + [(o, EXTERNAL) for o in EXTERNAL_ORIGINS])


# ---------------------------------------------------------------------------
# Support - a four-value view of the one support policy, never a second one
# ---------------------------------------------------------------------------

SUPPORTED = "supported"
PARTIALLY_SUPPORTED = "partially_supported"
UNSUPPORTED = "unsupported"
INSUFFICIENT_EVIDENCE = "insufficient_evidence"

SUPPORT_STATES = (SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, INSUFFICIENT_EVIDENCE)

#: How `research.sources.assess_support()`'s three verdicts map onto the four states a
#: synthesised statement needs. The fourth state exists because "we checked and the
#: sources are too weak" and "nothing was linked, so we cannot check" are different
#: answers, and collapsing them would let an unevidenced statement read as a refuted one.
SUPPORT_FROM_TIER_ASSESSMENT = {
    sources_mod.SUPPORTED: SUPPORTED,
    sources_mod.CORROBORATION_ONLY: PARTIALLY_SUPPORTED,
    sources_mod.UNSUPPORTED: UNSUPPORTED,
}

#: Weakest first. A statement resting on two legs is only as strong as the weaker leg,
#: so a cross-domain item takes the minimum rather than the better half.
SUPPORT_ORDER = (INSUFFICIENT_EVIDENCE, UNSUPPORTED, PARTIALLY_SUPPORTED, SUPPORTED)


def weakest_support(states):
    """The weakest of several support verdicts. Empty input is `insufficient_evidence`."""
    present = [s for s in states if s in SUPPORT_STATES]
    if not present:
        return INSUFFICIENT_EVIDENCE
    return min(present, key=SUPPORT_ORDER.index)


# ---------------------------------------------------------------------------
# Provenance references
# ---------------------------------------------------------------------------

P_DATASET = "dataset"
P_CALCULATION = "calculation"
P_KPI = "kpi"
P_FINDING = "finding"
P_FORECAST = "forecast"
P_ANOMALY = "anomaly"
P_EVIDENCE = "evidence"
P_CLAIM = "claim"
P_UNAVAILABLE = "unavailable"

PROVENANCE_KINDS = (P_DATASET, P_CALCULATION, P_KPI, P_FINDING, P_FORECAST, P_ANOMALY,
                    P_EVIDENCE, P_CLAIM, P_UNAVAILABLE)

#: Kinds that must resolve against a registered source object. `P_UNAVAILABLE` is the
#: single exception, and it is the honest one: it asserts nothing.
RESOLVABLE_KINDS = (P_DATASET, P_CALCULATION, P_KPI, P_FINDING, P_FORECAST, P_ANOMALY,
                    P_EVIDENCE, P_CLAIM)

#: Provenance kinds sourced from outside the business. Everything else is internal.
EXTERNAL_PROVENANCE = (P_EVIDENCE, P_CLAIM)

#: Provenance kinds produced from the user's own data. The complement of
#: `EXTERNAL_PROVENANCE` within `RESOLVABLE_KINDS`: `P_UNAVAILABLE` belongs to neither,
#: because provenance that asserts nothing cannot be a statement's footing.
INTERNAL_PROVENANCE = tuple(k for k in RESOLVABLE_KINDS if k not in EXTERNAL_PROVENANCE)

#: Kinds that assert something about the business itself and therefore require internal
#: footing. `FACT` is class 1 (measured from the user's data) and `CALCULATION` is class 4
#: (computed from it); both read downstream as "this is true of us", so both must rest on
#: at least one resolvable internal source.
#:
#: The domain constraint above is necessary but not sufficient, and M10.2 proved it: it
#: keys off the caller's declared `origin`, so a caller naming an internal origin while
#: citing only external evidence produced an item labelled `domain: internal`,
#: `trust: internal`, `evidence_class: 1` whose sole provenance was a tier-C research
#: house. The remedy is to read the provenance that is actually attached rather than the
#: label the caller chose, which `SynthesisSet` does at `add()` time because resolution
#: needs the registries. See ADR-0023.
INTERNALLY_FOOTED_KINDS = (FACT, CALCULATION)


class ProvenanceRef:
    """A pointer from a synthesised statement to the object it came from.

    Deliberately a pointer and not a copy: an executive report that embedded its evidence
    would drift from that evidence the moment either changed, and a reader chasing
    "where did this come from" would be reading a transcription rather than a source.
    """

    __slots__ = ("kind", "ref_id", "label", "detail")

    def __init__(self, kind, ref_id=None, label=None, detail=None):
        if kind not in PROVENANCE_KINDS:
            raise SynthesisError("unknown provenance kind %r" % (kind,))
        if kind in RESOLVABLE_KINDS and not (ref_id and str(ref_id).strip()):
            raise SynthesisError(
                "a %r provenance reference must name the object it points at; provenance "
                "that names nothing is not provenance." % (kind,))
        if kind == P_UNAVAILABLE and not (detail and str(detail).strip()):
            raise SynthesisError(
                "unavailable provenance must say why it is unavailable, so that an "
                "absent chain is auditable rather than merely empty.")
        self.kind = kind
        self.ref_id = str(ref_id) if ref_id is not None else None
        self.label = label
        self.detail = detail

    @property
    def is_resolvable(self):
        return self.kind in RESOLVABLE_KINDS

    @property
    def is_external(self):
        return self.kind in EXTERNAL_PROVENANCE

    @classmethod
    def unavailable(cls, detail, label=None):
        """Provenance that does not exist, said out loud rather than invented."""
        return cls(P_UNAVAILABLE, None, label=label, detail=detail)

    def key(self):
        return (self.kind, self.ref_id)

    def as_dict(self):
        record = {"kind": self.kind, "ref_id": self.ref_id, "label": self.label,
                  "detail": self.detail}
        return dict((k, v) for k, v in record.items() if v is not None)

    @classmethod
    def from_dict(cls, record):
        if not isinstance(record, dict):
            raise SynthesisError("a provenance reference must be a record")
        return cls(record.get("kind"), record.get("ref_id"),
                   label=record.get("label"), detail=record.get("detail"))

    def __eq__(self, other):
        return isinstance(other, ProvenanceRef) and self.as_dict() == other.as_dict()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.kind, self.ref_id, self.label, self.detail))

    def __repr__(self):
        return "ProvenanceRef(%s:%s)" % (self.kind, self.ref_id)


# ---------------------------------------------------------------------------
# Comparability dimensions carried on every statement that holds a value
# ---------------------------------------------------------------------------

#: The dimensions two values must share before they may be related. Named here because
#: both `compatibility` and every item that carries a figure need the same list.
DIMENSIONS = ("metric_definition", "period", "geography", "currency", "unit", "scope",
              "methodology")


def _quantity_type_or_refuse(unit):
    """Accept a canonical quantity type or nothing at all; refuse anything else (ADR-0025).

    `None` is legitimate and means the dimension is not stated, which fails comparability on
    `unknown`. What is refused is a **token outside the vocabulary** - `"USD billion"`,
    `"$m"`, `"units sold"` - because `compatibility.compare()` tests this dimension by exact
    equality, and two unrecognised labels agreeing with each other would certify a
    comparison nobody checked. A magnitude-qualified label is the dangerous case: two
    statements both labelled `"USD billion"` match on the token while one holds 3400000000
    and the other 282.8, which is a comparison wrong by a factor of a billion.

    Refusing here rather than coercing to `None` keeps the failure where the defect is - in
    the caller that built the statement - instead of surfacing three layers away as an
    unexplained `unknown`. `bops.quantity.canonical_amount()` is how source notation becomes
    a value and a quantity type in the first place.
    """
    if unit is None:
        return None
    if kpi_contract.is_quantity_type(unit):
        return unit
    raise SynthesisError(
        "%r is not a canonical quantity type. A unit names what kind of quantity this is "
        "and nothing else - one of %s - never a magnitude, a currency code or a display "
        "label. Canonicalise the figure with bops.quantity.canonical_amount() first: a "
        "source's \"USD billion\" is a value in base units, unit %r and currency \"USD\"."
        % (unit, ", ".join(kpi_contract.QUANTITY_TYPES), kpi_contract.CURRENCY))


def _plain(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return dict((k, _plain(v)) for k, v in value.items())
    return value


def synthesis_id(kind, origin, statement):
    """A deterministic id for one synthesised statement.

    Content-addressed for the same reason evidence ids are: the same statement built
    twice from the same inputs must carry the same id, so a fixture can assert an exact
    value and a downstream consumer can deduplicate without a sequence counter.
    """
    seed = "|".join(str(p) for p in (kind, origin, statement))
    return "sy-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


#: Fields a caller must never supply, because the set derives them. Mirrors the guard
#: `EvidenceSet.add()` already applies to instruction fields: the defence against a
#: forged `verified` or `source_tier` is that there is no parameter to forge.
DERIVED_FIELDS = frozenset({
    "verified", "status", "trust", "source_tier", "usable", "may_stand_alone",
    "support", "confidence", "tier", "verified_by", "trusted",
})


def _limitation_dict(limitation):
    if isinstance(limitation, dict):
        return limitation
    if hasattr(limitation, "as_dict"):
        return limitation.as_dict()
    return {"code": "unspecified", "subject": None, "reason": str(limitation),
            "status": analytics_contract.UNAVAILABLE}


class SynthesisItem:
    """One statement in the synthesis layer, with its kind and its chain attached.

    The value-bearing dimensions (`period`, `geography`, `currency`, `unit`, ...) are
    first-class fields rather than free text because the compatibility test reads them.
    A figure whose period is prose inside the statement cannot be checked against another.
    """

    __slots__ = ("id", "kind", "origin", "domain", "statement", "metric",
                 "metric_definition", "period", "geography", "currency", "unit", "scope",
                 "methodology", "observed", "comparison", "change", "change_pct",
                 "basis", "provenance", "materiality", "limitations", "caveats",
                 "confidence_reasons", "support", "support_detail", "conflict_refs",
                 "confidence", "confidence_detail", "notes", "dimension_provenance",
                 "_resolved_dimensions", "dimension_resolution")

    def __init__(self, kind, origin, statement, provenance=None, metric=None,
                 metric_definition=None, period=None, geography=None, currency=None,
                 unit=None, scope=None, methodology=None, observed=None, comparison=None,
                 change=None, change_pct=None, basis=None, materiality=None,
                 limitations=None, caveats=None, confidence_reasons=None, notes=None,
                 item_id=None, dimension_provenance=None, **forbidden):
        offending = sorted(set(forbidden) & DERIVED_FIELDS)
        if offending:
            raise SynthesisError(
                "these fields are derived by the synthesis set and may not be supplied: "
                "%s. Support, confidence, trust and verification are conclusions, not "
                "inputs." % ", ".join(offending))
        if forbidden:
            raise SynthesisError(
                "unknown synthesis item fields: %s" % ", ".join(sorted(forbidden)))

        if kind in DEFERRED_KINDS:
            raise SynthesisError(
                "%s is reserved for a downstream milestone and is not produced by the "
                "synthesis foundation. %s" % (kind, DEFERRED_NOTE))
        if kind not in SYNTHESIS_EMITS:
            raise SynthesisError("unknown synthesis statement kind %r" % (kind,))
        if origin not in ORIGINS:
            raise SynthesisError("unknown synthesis origin %r" % (origin,))

        domain = DOMAIN_OF_ORIGIN[origin]
        if domain == EXTERNAL and kind not in EXTERNAL_KINDS:
            raise SynthesisError(
                "an external statement may not be a %s. What a source said is %s; a "
                "reading of it is %s. External wording never becomes an internal fact or "
                "an engine calculation." % (kind, SOURCED, INTERPRETATION))
        if domain == INTERNAL and kind not in INTERNAL_KINDS:
            raise SynthesisError(
                "an internal statement may not be a %s; %s means a public source said it, "
                "and internal data has no such source." % (kind, SOURCED))

        statement = str(statement or "").strip()
        if not statement:
            raise SynthesisError("a synthesised statement with no text is not a statement")

        # Recommendation injection: an advisory sentence must not enter as an
        # interpretation and be read back downstream as advice. The marker list is M9's,
        # imported rather than copied, so the two guards cannot drift apart.
        lowered = statement.lower()
        marker = next((m for m in handoff_mod.ADVISORY_MARKERS if m in lowered), None)
        if marker is not None:
            raise SynthesisError(
                "this statement reads as advice (%r), not as a fact, calculation or "
                "interpretation. A recommendation is never introduced by rewording; it "
                "is class 7 and requires evidence, rationale, expected benefit, risks, "
                "dependencies and confidence." % marker.strip())

        if kind == CALCULATION and not basis:
            raise SynthesisError(
                "a calculation must name the primitive, metric or formula that produced "
                "it; a number without its basis cannot be audited")

        self.provenance = list(provenance or [])
        for ref in self.provenance:
            if not isinstance(ref, ProvenanceRef):
                raise SynthesisError(
                    "provenance must be ProvenanceRef objects, so that a reference "
                    "cannot be a bare string nobody resolves")
        if not self.provenance:
            raise SynthesisError(
                "every synthesised statement must carry provenance. Where none exists, "
                "say so with ProvenanceRef.unavailable(reason) rather than omitting it.")

        self.kind = kind
        self.origin = origin
        self.domain = DOMAIN_OF_ORIGIN[origin]
        self.statement = statement
        self.id = item_id or synthesis_id(kind, origin, statement)
        self.metric = metric
        self.metric_definition = metric_definition
        self.period = period
        self.geography = geography
        self.currency = currency
        self.unit = _quantity_type_or_refuse(unit)
        self.scope = scope
        self.methodology = methodology
        self.observed = observed
        self.comparison = comparison
        self.change = change
        self.change_pct = change_pct
        self.basis = basis
        self.materiality = dict(materiality) if materiality else None
        self.limitations = list(limitations or [])
        self.caveats = list(caveats or [])
        self.confidence_reasons = list(confidence_reasons or [])
        self.notes = list(notes or [])

        # ADR-0026. Footings for the seven dimensions, each naming the evidence it rests
        # on. Validated here for shape; whether one actually *holds* needs the registry,
        # so that judgement is made by the set at `add()` time, exactly as support and
        # confidence are.
        self.dimension_provenance = list(dimension_provenance or [])
        for entry in self.dimension_provenance:
            if type(entry).__name__ != "DimensionProvenance":
                raise SynthesisError(
                    "dimension provenance must be DimensionProvenance objects, so that a "
                    "footing cannot be a bare mapping nobody resolves")
        #: Set by `SynthesisSet.add()`. Until then the item reports what it was told,
        #: which is the pre-M10.2-R.6 behaviour and keeps an unregistered item usable.
        self._resolved_dimensions = None
        self.dimension_resolution = []

        # Derived by the set on `add()`. Until then the item is explicitly unassessed.
        self.support = None
        self.support_detail = None
        self.conflict_refs = []
        self.confidence = None
        self.confidence_detail = None

    # -- state --------------------------------------------------------------

    @property
    def evidence_class(self):
        return EVIDENCE_CLASS[self.kind]

    @property
    def is_evidential(self):
        return self.evidence_class in evidence_mod.EVIDENTIAL

    @property
    def is_external(self):
        return self.domain == EXTERNAL

    @property
    def trust(self):
        """External statements stay untrusted for ever. There is no promotion path."""
        return UNTRUSTED if self.is_external else INTERNAL_TRUST

    @property
    def is_material(self):
        from .. import materiality as materiality_mod
        return bool(self.materiality
                    and self.materiality.get("outcome") == materiality_mod.MATERIAL)

    @property
    def declared_dimensions(self):
        """What the caller said, before any footing was checked. Audit view only."""
        return {"metric_definition": self.metric_definition, "period": self.period,
                "geography": self.geography, "currency": self.currency,
                "unit": self.unit, "scope": self.scope, "methodology": self.methodology}

    @property
    def dimensions(self):
        """The dimensions `compatibility.compare()` may read (ADR-0026).

        Once the item is in a set this is the **resolved** view: a dimension appears with
        its value only where an admissible, fully bound footing established it, and an
        asserted or unbound one reads as `None` - which fails the comparison on `unknown`,
        exactly as an absent dimension always has. Before the item is added, and for any
        dimension carrying no footing, it is the declared view unchanged.
        """
        if self._resolved_dimensions is None:
            return self.declared_dimensions
        return dict(self._resolved_dimensions)

    def provenance_keys(self):
        return [ref.key() for ref in self.provenance]

    def external_refs(self):
        return [ref for ref in self.provenance if ref.is_external]

    def internal_refs(self):
        return [ref for ref in self.provenance
                if ref.is_resolvable and not ref.is_external]

    def has_provenance(self):
        """True when at least one reference actually points at something."""
        return any(ref.is_resolvable for ref in self.provenance)

    # -- serialisation ------------------------------------------------------

    def as_dict(self):
        record = {
            "synthesis_id": self.id,
            "kind": self.kind,
            "evidence_class": self.evidence_class,
            "origin": self.origin,
            "domain": self.domain,
            "trust": self.trust,
            "statement": self.statement,
            "metric": self.metric,
            "metric_definition": self.metric_definition,
            "period": self.period,
            "geography": self.geography,
            "currency": self.currency,
            "unit": self.unit,
            "scope": self.scope,
            "methodology": self.methodology,
            "observed": _plain(self.observed),
            "comparison": _plain(self.comparison),
            "change": _plain(self.change),
            "change_pct": _plain(self.change_pct),
            "basis": self.basis,
            "provenance": [ref.as_dict() for ref in self.provenance],
            "materiality": _plain(self.materiality) if self.materiality else None,
            "support": self.support,
            "support_detail": _plain(self.support_detail),
            "conflict_refs": sorted(self.conflict_refs),
            "confidence": self.confidence,
            "confidence_detail": self.confidence_detail,
            "limitations": [_limitation_dict(x) for x in self.limitations],
            "caveats": list(self.caveats),
            "notes": list(self.notes),
            # ADR-0026. Fixed dimension order, never insertion or dictionary order, so the
            # same set serialises byte-identically however the footings were added.
            "dimension_provenance": self._dimension_provenance_records(),
            "dimension_resolution": list(self.dimension_resolution),
            "resolved_dimensions": (dict(self._resolved_dimensions)
                                    if self._resolved_dimensions is not None else None),
        }
        return dict((k, v) for k, v in record.items() if v not in (None, [], {}))

    def _dimension_provenance_records(self):
        """Footings in fixed dimension order. Source metadata is not written here.

        `as_dict(evidence=None)` is deliberate: the resolved source identity, tier and
        freshness belong to the resolution trail, which is re-derived from the registry on
        every load. Writing them beside the footing would create a second, caller-adjacent
        copy of metadata this architecture derives locally - and a reloaded set would then
        have a tier to read without resolving anything.
        """
        order = dict((name, index) for index, name in enumerate(DIMENSIONS))
        entries = sorted(self.dimension_provenance,
                         key=lambda e: (order.get(e.dimension, len(DIMENSIONS)),
                                        str(e.basis), str(e.evidence_id),
                                        str(e.value)))
        return [entry.as_dict() for entry in entries]

    @classmethod
    def from_dict(cls, record):
        """Rebuild an item from its serialised form, provenance included.

        Derived conclusions (`support`, `confidence`, `conflict_refs`) are restored as
        read, because a round-trip must not silently re-grade a statement; re-adding the
        item to a live set is what re-derives them.
        """
        if not isinstance(record, dict):
            raise SynthesisError("a synthesis item must be a record")
        for required in ("kind", "origin", "statement"):
            if required not in record:
                raise SynthesisError("a synthesis item is missing %r" % required)
        item = cls(
            record["kind"], record["origin"], record["statement"],
            provenance=[ProvenanceRef.from_dict(p)
                        for p in record.get("provenance") or []],
            metric=record.get("metric"),
            metric_definition=record.get("metric_definition"),
            period=record.get("period"), geography=record.get("geography"),
            currency=record.get("currency"), unit=record.get("unit"),
            scope=record.get("scope"), methodology=record.get("methodology"),
            observed=record.get("observed"), comparison=record.get("comparison"),
            change=record.get("change"), change_pct=record.get("change_pct"),
            basis=record.get("basis"), materiality=record.get("materiality"),
            limitations=record.get("limitations"), caveats=record.get("caveats"),
            notes=record.get("notes"),
            item_id=record.get("synthesis_id"),
            dimension_provenance=[
                _dimension_provenance_from_dict(entry)
                for entry in record.get("dimension_provenance") or []])
        item.support = record.get("support")
        item.support_detail = record.get("support_detail")
        item.conflict_refs = list(record.get("conflict_refs") or [])
        item.confidence = record.get("confidence")
        item.confidence_detail = record.get("confidence_detail")
        # `resolved_dimensions` and `dimension_resolution` are deliberately **not**
        # restored (ADR-0026). A serialised admissibility verdict is a verdict nobody
        # re-checked; re-adding the item to a live set with its evidence registered is the
        # only thing that re-establishes one. Until then the item reports what it declared,
        # and any footing it carries resolves against nothing.
        return item

    def __repr__(self):
        return "SynthesisItem(%s %s %s)" % (self.kind, self.origin, self.id)


def _dimension_provenance_from_dict(record):
    """Late import: `dimension_provenance` imports this module, so the edge is one-way."""
    from .dimension_provenance import DimensionProvenance
    return DimensionProvenance.from_dict(record)
