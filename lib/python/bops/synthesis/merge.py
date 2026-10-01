"""Bringing each domain into the synthesis set, without implying they are the same thing.

Every function here is a translator. It takes an object one of the earlier milestones
already produced - an `AnalysisSet`, a `KPIResult`, an `EvidenceSet` - and expresses it as
synthesis statements with provenance pointing back at the original. None of them computes
anything, because the computation already happened in the layer that owns it.

The asymmetry between the internal and external paths is the important part and it is
deliberate:

* **Internal findings become statements automatically.** They were produced by the engine
  from the user's own data, they already carry their basis and their materiality verdict,
  and the classification they arrive with is the classification they keep.
* **External evidence does not.** Registering an `EvidenceSet` makes its items citable and
  its conflicts visible; it creates no statements at all. Turning "this source says X" into
  a statement is a reading of a source, and a reading is judgement - it comes from a skill,
  through `sourced_statement()`, naming the evidence it rests on. There is no path by which
  retrieved wording becomes an assertion on its own.

`compare_values()` is the other half of that discipline: the only way to relate an internal
figure to an external one, and it refuses far more often than it agrees.
"""

from .. import quantity as quantity_mod
from . import compatibility as compatibility_mod
from . import confidence as confidence_mod
from . import limitations as limitations_mod
from .conflicts import CrossDomainConflict
from .contract import (
    ASSUMPTION, CALCULATION, EXTERNAL_ORIGINS, FACT, INTERPRETATION, ORIGIN_ANOMALY,
    ORIGIN_FORECAST, ORIGIN_KPI, P_ANOMALY, P_CLAIM, P_DATASET, P_EVIDENCE, P_FINDING,
    P_FORECAST, P_KPI, ProvenanceRef, SOURCED, SynthesisError, SynthesisItem,
)

#: Finding types the analytics engine emits, mapped onto synthesis kinds. The engine emits
#: only FACT and CALCULATION (`analytics.contract.ENGINE_EMITS`), so the map is short and
#: complete; anything else arriving is a defect in the layer below, not a case to handle.
FINDING_KIND = {FACT: FACT, CALCULATION: CALCULATION}

#: The note `interpretation()` writes naming the statements a reading rests on. Spelled once
#: so the writer below and `interpretation_supports()` cannot drift apart (M10.3.1).
RESTS_ON = "Rests on: "


def _provenance_kind_for_origin(origin):
    if origin == ORIGIN_FORECAST:
        return P_FORECAST
    if origin == ORIGIN_ANOMALY:
        return P_ANOMALY
    if origin == ORIGIN_KPI:
        return P_KPI
    return P_FINDING


def from_analysis_set(synthesis, analysis_set, origin, dataset_id=None,
                      period=None, geography=None, metric_definition=None, scope=None,
                      methodology=None):
    """Translate one internal analysis into synthesis statements.

    The finding's own `finding_type`, `basis`, `materiality` and `caveats` are carried
    across unchanged. Nothing is re-judged here: re-deciding materiality at synthesis time
    would be a second materiality policy, which ADR-0012 forbids and section 6 of the
    milestone brief forbids again.
    """
    synthesis.register_analysis(analysis_set)
    kind_of_ref = _provenance_kind_for_origin(origin)
    produced = []

    for finding in analysis_set.findings:
        kind = FINDING_KIND.get(finding.finding_type)
        if kind is None:
            raise SynthesisError(
                "the analytics engine emitted %r, which the synthesis layer does not "
                "accept as an internal statement" % (finding.finding_type,))

        provenance = [ProvenanceRef(kind_of_ref, finding.analysis_id,
                                    label=analysis_set.analysis_type,
                                    detail=finding.basis)]
        if dataset_id:
            provenance.append(ProvenanceRef(P_DATASET, dataset_id,
                                            label="analysed dataset"))

        item = SynthesisItem(
            kind, origin, finding.statement,
            provenance=provenance,
            metric=finding.metric,
            metric_definition=metric_definition,
            period=finding.period or period,
            geography=geography,
            currency=finding.currency or analysis_set.currency,
            unit=finding.unit,
            scope=scope,
            methodology=methodology,
            observed=finding.observed,
            comparison=finding.comparison,
            change=finding.change,
            change_pct=finding.change_pct,
            basis=finding.basis,
            materiality=_materiality_of(finding),
            caveats=list(finding.caveats),
            limitations=list(analysis_set.limitations))
        produced.append(synthesis.add(item))

    return produced


def _materiality_of(finding):
    """Carry the upstream materiality verdict across without re-deciding it."""
    if not finding.materiality:
        return None
    return {"outcome": finding.materiality,
            "reason": finding.materiality_reason,
            "basis": finding.basis,
            "observed": finding.observed,
            "comparison": finding.comparison}


def from_kpi_result(synthesis, result, dataset_id=None, period=None, statement=None,
                    materiality=None, geography=None, metric_definition=None,
                    scope=None, methodology=None):
    """Translate one computed KPI into a calculation, or record why it is unavailable.

    An unavailable KPI produces a limitation rather than a statement. That is the whole
    behaviour: a metric that could not be computed must not become a sentence, and it
    must not vanish either.

    **The four dimension parameters mirror `from_analysis_set` exactly** (M10.2-R.14). A
    KPI carries its own metric, period, currency and unit, but the analytics engine has no
    opinion on which territory, boundary, slice or method the figure describes — those are
    the caller's to state about its own data, exactly as they already were for an analysis
    set. Added additively: every default is `None`, so an existing caller's output is
    byte-identical, and the asymmetry that made a KPI unusable for comparison is gone.

    They describe an **internal** figure and never leave the machine. An internal statement
    is engine-footed on the registered dataset (ADR-0023) and carries no dimension
    provenance; these values populate the dimensions `compatibility.compare()` reads on our
    side, which is what lets a comparison be refused rather than assumed.
    """
    synthesis.register_kpi(result)
    from ..kpi import contract as kpi_contract

    if result.status not in kpi_contract.VALUE_BEARING:
        synthesis.limit("kpi.%s" % result.status, result.kpi_id,
                        result.reason or "The KPI could not be computed.",
                        status=result.status)
        return None

    provenance = [ProvenanceRef(P_KPI, result.kpi_id, label=result.definition.name,
                                detail=result.definition.formula
                                if hasattr(result.definition, "formula") else None)]
    if dataset_id:
        provenance.append(ProvenanceRef(P_DATASET, dataset_id, label="analysed dataset"))

    item = SynthesisItem(
        CALCULATION, ORIGIN_KPI,
        statement or ("%s: %s" % (result.definition.name, result.value)),
        provenance=provenance,
        metric=result.kpi_id,
        metric_definition=metric_definition,
        period=period,
        geography=geography,
        currency=getattr(result, "currency", None),
        unit=result.definition.unit,
        scope=scope,
        methodology=methodology,
        observed=result.value,
        basis=getattr(result.definition, "formula", None) or result.kpi_id,
        materiality=materiality,
        caveats=list(getattr(result, "caveats", []) or []))
    return synthesis.add(item)


def register_external(synthesis, evidence_set, origin=None):
    """Make an evidence set citable. Creates no statements, by design.

    Registration is the whole operation. The set's items become resolvable provenance
    targets and its declared conflicts become visible to every statement that cites them;
    what any of it *means* is not decided here and is not decided by Python.
    """
    if origin is not None and origin not in EXTERNAL_ORIGINS:
        raise SynthesisError(
            "%r is not an external research origin; external evidence belongs to one of "
            "%s" % (origin, ", ".join(EXTERNAL_ORIGINS)))
    synthesis.register_evidence_set(evidence_set)
    return [item.id for item in evidence_set.items]


def sourced_statement(synthesis, origin, statement, evidence_ids=(), claim_ids=(),
                      metric=None, metric_definition=None, period=None, geography=None,
                      currency=None, unit=None, scope=None, methodology=None,
                      observed=None, materiality=None, caveats=(), limitations=(),
                      confidence_reasons=(), source_unit=None, source_scale=None,
                      dimension_provenance=()):
    """Record that a named source said something, citing the evidence it came from.

    This is `SOURCED` and never `FACT`. The distinction survives all the way into the
    ledger, where class 3 and class 1 are different provenance classes and are required to
    look different in output.

    **`source_unit` is the canonicalisation seam** (ADR-0025). A published figure arrives as
    notation - "USD 282.80 billion" - and passing that notation as `source_unit` alongside
    the source's own `observed` figure decomposes it into a value in base units, the
    quantity type `currency`, and the currency code, before the statement exists. Passing it
    as `unit` instead is refused, because a magnitude is not a quantity type.

    Canonicalisation happens **here**, at construction, and never inside
    `compatibility.compare()`. It converts no currency and cannot: `source_scale` rescales a
    magnitude the source already stated, and there is no rate, no lookup and no path to one.
    A currency is read only from an explicit three-letter code - a bare "$" leaves the
    currency unstated, which rejects, because four currencies use that symbol.

    **`dimension_provenance` is the admissibility seam** (ADR-0026). Each entry names the
    evidence item a dimension rests on, the basis it rests on it by, and the source text
    that carries it. The set resolves them at `add()` time: a dimension with an admissible,
    fully bound footing reaches `compatibility.compare()`; an asserted or unbound one reads
    as unstated. A dimension with no footing is passed through unchanged, so this parameter
    is additive - unless the set was built with `require_dimension_provenance=True`, which
    refuses the pass-through for external statements.
    """
    if source_unit is not None or source_scale is not None:
        if unit is not None:
            raise SynthesisError(
                "pass either the source's notation (source_unit/source_scale) or a "
                "canonical unit, not both; two descriptions of one magnitude can disagree")
        if observed is None:
            raise SynthesisError(
                "source notation was supplied with no figure to canonicalise")
        amount, unit, parsed_currency = quantity_mod.canonical_amount(
            observed, unit_text=source_unit,
            scale=source_scale if source_unit is None else None,
            currency=currency if source_unit is None else None)
        if source_unit is not None and parsed_currency is not None:
            if currency is not None and currency != parsed_currency:
                raise SynthesisError(
                    "the source notation states currency %r and the caller states %r; a "
                    "figure with two currencies is not canonicalised, it is refused"
                    % (parsed_currency, currency))
            currency = parsed_currency
        observed = amount
    if origin not in EXTERNAL_ORIGINS:
        raise SynthesisError(
            "a sourced statement must have an external origin; %r is internal" % (origin,))
    refs = [ProvenanceRef(P_EVIDENCE, eid) for eid in evidence_ids]
    refs += [ProvenanceRef(P_CLAIM, cid) for cid in claim_ids]
    if not refs:
        raise SynthesisError(
            "a sourced statement must cite at least one evidence item or candidate "
            "claim; an uncited external statement is not sourced, it is invented")

    item = SynthesisItem(
        SOURCED, origin, statement, provenance=refs,
        metric=metric, metric_definition=metric_definition, period=period,
        geography=geography, currency=currency, unit=unit, scope=scope,
        methodology=methodology, observed=observed, materiality=materiality,
        caveats=list(caveats), limitations=list(limitations),
        confidence_reasons=list(confidence_reasons),
        dimension_provenance=list(dimension_provenance))
    return synthesis.add(item)


def interpretation(synthesis, origin, statement, supports=(), caveats=(),
                   limitations=(), confidence_reasons=(), period=None, geography=None,
                   metric=None, materiality=None):
    """Record a reading of statements already in the set.

    `supports` names the statements the reading rests on, and they must already be in the
    set. An interpretation of nothing is an opinion; the ledger has always said so, and
    here it is unconstructible rather than merely discouraged.
    """
    supports = list(supports)
    if not supports:
        raise SynthesisError(
            "an interpretation must name the statements it rests on. An interpretation "
            "that traces to nothing is an opinion and is not synthesised.")

    known = dict((item.id, item) for item in synthesis.items)
    refs = []
    for support_id in supports:
        source = known.get(support_id)
        if source is None:
            raise SynthesisError(
                "interpretation cites %r, which is not a statement in this set"
                % (support_id,))
        refs.extend(source.provenance)

    seen, provenance = set(), []
    for ref in refs:
        if ref.key() in seen:
            continue
        seen.add(ref.key())
        provenance.append(ref)

    item = SynthesisItem(
        INTERPRETATION, origin, statement, provenance=provenance,
        metric=metric, period=period, geography=geography, materiality=materiality,
        caveats=list(caveats), limitations=list(limitations),
        confidence_reasons=list(confidence_reasons),
        notes=["%s%s" % (RESTS_ON, ", ".join(sorted(supports)))])
    return synthesis.add(item)


def interpretation_supports(item):
    """The statement ids an interpretation says it rests on, read back from its note.

    Read-only, and it establishes nothing on its own: a note is text on the item, and text
    can be written by anyone who constructs one. Whether the named statements exist in a set
    and account for the provenance the interpretation actually carries is a question for the
    reader holding that set. Returns `None` where the note appears more than once, because
    two accounts of what a reading rests on are not one account (M10.3.1).
    """
    found = [note[len(RESTS_ON):] for note in item.notes
             if isinstance(note, str) and note.startswith(RESTS_ON)]
    if len(found) > 1:
        return None
    if not found:
        return []
    return [part.strip() for part in found[0].split(",") if part.strip()]


def assumption(synthesis, origin, statement, detail, caveats=()):
    """Record something modelled or assumed, with provenance explicitly unavailable."""
    item = SynthesisItem(
        ASSUMPTION, origin, statement,
        provenance=[ProvenanceRef.unavailable(detail, label="assumption")],
        caveats=list(caveats))
    return synthesis.add(item)


def compare_values(synthesis, left, right, subject=None, record_conflict=True):
    """The only sanctioned way to relate two figures, and it usually says no.

    Returns the compatibility record. Where the values are not comparable, a limitation is
    recorded and - for an internal/external pair - so is a conflict, because "our number
    and their number disagree" is a finding worth keeping even when the disagreement turns
    out to be definitional rather than substantive.

    No combined figure is ever produced here. Not a ratio, not a difference, not a share.
    Establishing comparability is a precondition for a downstream capability to do that
    arithmetic deliberately; it is not permission granted in passing.
    """
    subject = subject or (left.metric or left.statement)
    result = compatibility_mod.compare(left, right)

    if compatibility_mod.may_combine(result):
        return result

    summary = compatibility_mod.mismatch_summary(result)
    synthesis.limit(
        limitations_mod.INCOMPARABLE, subject,
        "%s %s" % (result["reason"], summary or ""))

    for item in (left, right):
        if confidence_mod.INCOMPARABLE_VALUES not in item.confidence_reasons:
            item.confidence_reasons.append(confidence_mod.INCOMPARABLE_VALUES)
        synthesis._regrade(item)

    if record_conflict and left.domain != right.domain:
        internal, external = ((left, right) if left.domain == "internal"
                              else (right, left))
        synthesis.add_conflict(CrossDomainConflict.between_domains(
            subject,
            {"synthesis_id": internal.id, "value": internal.observed,
             "unit": internal.unit, "definition": internal.metric_definition,
             "scope": internal.scope, "period": internal.period,
             "methodology": internal.methodology},
            {"synthesis_id": external.id, "value": external.observed,
             "unit": external.unit, "definition": external.metric_definition,
             "scope": external.scope, "period": external.period,
             "methodology": external.methodology,
             "evidence_id": next((r.ref_id for r in external.external_refs()), None)},
            reason=("An internal figure and an external estimate were compared and are "
                    "not comparable: %s" % (summary or result["reason"]))))

    return result
