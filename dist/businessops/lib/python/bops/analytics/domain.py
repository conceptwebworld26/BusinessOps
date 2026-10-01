"""Shared scaffolding for the four analytical domains.

Sales, customer, product and financial analysis differ in what they look at, not in how
they behave. They all consume the same pipeline result, honour the same quality gate,
inherit the same caveats, consume KPI results rather than recomputing them, and return the
same `AnalysisSet`. That common behaviour lives here so it exists once.

The one rule this module enforces above all others: **a KPI is consumed, never recomputed.**
`emit_kpi` reads a `KPIResult` and turns it into a finding, or turns its absence into a
limitation carrying the engine's own reason. No analytical module re-derives revenue
growth, gross margin or churn.
"""

from decimal import Decimal, ROUND_HALF_UP

from .. import mapping as mapping_mod
from ..kpi import contract as kpi_contract
from ..quality import contract as quality_contract
from . import contract, presentation as presentation_mod

ZERO = Decimal("0")

#: Default concentration ratios reported when configuration names none.
DEFAULT_RATIOS = (1, 3, 5, 10)

#: How a KPI bucket becomes an analysis limitation. The vocabularies are deliberately equal.
KPI_STATUS_TO_ANALYSIS = {
    kpi_contract.UNAVAILABLE: contract.UNAVAILABLE,
    kpi_contract.NOT_APPLICABLE: contract.NOT_APPLICABLE,
    kpi_contract.INSUFFICIENT_DATA: contract.INSUFFICIENT_DATA,
}

#: Dimension roles the analytics layer can segment by, and the human name for each.
DIMENSIONS = (
    (mapping_mod.PRODUCT, "product"),
    (mapping_mod.CATEGORY, "category"),
    (mapping_mod.REGION, "region"),
    (mapping_mod.SALESPERSON, "salesperson"),
    (mapping_mod.CUSTOMER, "customer"),
)


def text_amount(value, currency=None):
    """A figure for a human-readable sentence.

    Quantisation here is presentation, applied once, to the sentence only — the structured
    `observed` / `change` fields keep the engine's full precision (CLAUDE.md section 4).
    """
    if value is None:
        return "unavailable"
    quantised = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return "%s %s" % (currency, quantised) if currency else str(quantised)


def text_percent(value, places=2):
    if value is None:
        return "unavailable"
    quant = Decimal("1") if places == 0 else Decimal("0." + "0" * places)
    return "%s%%" % Decimal(value).quantize(quant, rounding=ROUND_HALF_UP)


def text_points(value):
    if value is None:
        return "unavailable"
    return "%spp" % Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class AnalysisContext:
    """Everything the four domains read. Assembled once per analysis."""

    __slots__ = ("dataset", "semantic_map", "canonical", "kpis", "quality", "context",
                 "config", "policy", "currency", "business_model", "periods", "ledger")

    def __init__(self, result, policy):
        self.dataset = result.dataset
        self.semantic_map = result.semantic_map
        self.canonical = result.canonical
        self.kpis = result.kpis or {}
        self.quality = result.quality
        self.context = result.context
        self.config = result.config
        self.ledger = result.ledger
        self.policy = policy
        self.currency = self._currency()
        self.business_model = (result.context.get("identity.business_model")
                               if result.context is not None else None)
        from ..kpi import primitives as p
        self.periods = p.periods(result.dataset, result.semantic_map)

    def _currency(self):
        if self.context is not None:
            stated = self.context.get("reporting.currency")
            if stated:
                return stated
        if self.config is not None:
            return self.config.get("locale.currency")
        return None

    def column(self, role):
        return self.semantic_map.column_for(role) if self.semantic_map else None

    def has(self, role):
        return bool(self.column(role))

    def confirmed(self, role):
        return bool(self.semantic_map and self.semantic_map.confirmed(role))

    def kpi(self, kpi_id):
        return self.kpis.get(kpi_id)

    def available_dimensions(self):
        """Mapped dimension roles, in a fixed order. Unconfirmed ones are still reported."""
        return [(role, name) for role, name in DIMENSIONS if self.has(role)]


def prepare(result, analysis_type, presentation=presentation_mod.LOCAL, dimensions=()):
    """Build the `AnalysisSet` and context for one domain.

    Returns `(analysis_set, context)`. When the run halted at the quality gate the context
    is `None` and the set is already `unavailable` — no analytical claim may be generated
    from a dataset the quality gate rejected, so there is nothing further to do.
    """
    quality_grade = result.quality.grade if result.quality is not None else None
    provenance = _provenance(result)

    if result.halted:
        analysis = contract.AnalysisSet(
            analysis_type, status=contract.UNAVAILABLE,
            reason=("No analysis was produced: the data quality gate halted this run. "
                    "%s" % (result.halt_reason or "")).strip(),
            quality_grade=quality_grade, provenance=provenance,
            presentation=presentation)
        analysis.limit("quality_gate", analysis_type,
                       "The dataset failed the quality gate; analytical claims built on it "
                       "would carry a validity the data does not have.")
        return analysis, None

    policy = presentation_mod.policy_for(result.canonical, presentation, result.config)
    context = AnalysisContext(result, policy)

    analysis = contract.AnalysisSet(
        analysis_type, status=contract.AVAILABLE,
        quality_grade=quality_grade, provenance=provenance,
        presentation=presentation, business_model=context.business_model,
        currency=context.currency, periods=list(context.periods))

    # Quality warnings are not footnotes: they attach to every finding this set produces.
    if result.quality is not None:
        for caveat in result.quality.caveats():
            analysis.add_caveat(caveat)

    # An unconfirmed mapping makes every dependent figure provisional, at the point of use.
    unconfirmed = (result.semantic_map.needs_confirmation()
                   if result.semantic_map is not None else [])
    for mapping in sorted(unconfirmed, key=lambda m: m.role):
        analysis.add_caveat(
            "Column %r is only provisionally identified as %s; figures depending on it are "
            "provisional until confirmed." % (mapping.column, mapping.role))

    # Dimensions this domain wanted but the data does not carry. Recorded twice on
    # purpose: `dimensions_skipped` for a consumer that wants the map, and a limitation
    # for one that reads only the limitations — a skipped dimension must not be invisible
    # to either.
    for role, name in dimensions:
        if not context.has(role):
            reason = ("No column is mapped to %s, so %s analysis was not attempted."
                      % (role, name))
            analysis.dimensions_skipped[name] = reason
            analysis.limit("unmapped_dimension", name, reason)
        else:
            analysis.dimensions_covered.append(name)

    restricted = presentation_mod.restricted_columns(
        policy, [context.column(role) for role, _n in dimensions if context.has(role)])
    if restricted:
        analysis.restricted_dimensions = sorted(set(restricted))
        caveat = presentation_mod.export_caveat(analysis.restricted_dimensions)
        if caveat and presentation == presentation_mod.LOCAL:
            analysis.add_caveat(caveat)

    return analysis, context


def _provenance(result):
    record = {}
    if result.canonical is not None:
        source = result.canonical.provenance()
        record["source"] = source.get("source_name")
        record["rows"] = result.canonical.row_count
        record["processing_mode"] = result.canonical.processing_mode
        record["complete"] = result.canonical.complete
        tier = source.get("reader_tier")
        if tier:
            record["reader_tier"] = tier.get("tier")
    elif result.dataset is not None:
        record["source"] = result.dataset.provenance().get("source_name")
        record["rows"] = result.dataset.row_count
    if result.quality is not None:
        record["quality_grade"] = result.quality.grade
    return record


def emit_kpi(analysis, context, kpi_id, dimension=None, unit_text=None):
    """Turn a KPI result into a finding, or its absence into a limitation.

    Never recomputes. If the metric is not in the result set at all, that is recorded as a
    limitation too — silence would read as "nothing to report".
    """
    result = context.kpi(kpi_id)
    analysis.note_metric(kpi_id)
    if result is None:
        analysis.limit("kpi_not_requested", kpi_id,
                       "The KPI engine was not asked for this metric in this run.")
        return None

    if not result.available:
        analysis.limit(
            "kpi_%s" % result.status, result.definition.name,
            result.reason or "The KPI engine could not produce this metric.",
            status=KPI_STATUS_TO_ANALYSIS.get(result.status, contract.UNAVAILABLE))
        return None

    unit = result.unit
    if unit == kpi_contract.CURRENCY:
        rendered = text_amount(result.value, result.currency or context.currency)
    elif unit == kpi_contract.PERCENT:
        rendered = text_percent(result.value)
    elif unit == kpi_contract.DAYS:
        rendered = "%s days" % text_amount(result.value)
    else:
        rendered = text_amount(result.value)

    finding = contract.AnalysisFinding(
        analysis_id="%s.kpi.%s" % (analysis.analysis_type, kpi_id),
        analysis_type=analysis.analysis_type,
        finding_type=contract.CALCULATION,
        statement="%s is %s%s." % (result.definition.name, rendered,
                                   " (%s)" % unit_text if unit_text else ""),
        metric=kpi_id,
        dimension=dimension,
        observed=result.value,
        unit=unit,
        currency=result.currency or (context.currency if unit == kpi_contract.CURRENCY
                                     else None),
        basis=result.formula,
        inputs=dict(result.inputs_used),
        fields_used=tuple(sorted(result.definition.inputs)),
        caveats=list(result.caveats),
        assumptions=list(result.assumptions),
        provenance=dict(result.provenance),
    )
    if result.status == kpi_contract.PARTIAL:
        finding.caveats.append(
            "Computed from an incomplete pass over the data; treat as provisional.")
    return analysis.add(finding)


def fact(analysis, analysis_id, statement, **kwargs):
    """A statement read directly from the data (evidence class 1)."""
    return analysis.add(contract.AnalysisFinding(
        analysis_id="%s.%s" % (analysis.analysis_type, analysis_id),
        analysis_type=analysis.analysis_type, finding_type=contract.FACT,
        statement=statement, **kwargs))


def calculation(analysis, analysis_id, statement, basis, **kwargs):
    """A statement produced by a deterministic primitive (evidence class 4)."""
    return analysis.add(contract.AnalysisFinding(
        analysis_id="%s.%s" % (analysis.analysis_type, analysis_id),
        analysis_type=analysis.analysis_type, finding_type=contract.CALCULATION,
        statement=statement, basis=basis, **kwargs))


def require(analysis, context, *roles):
    """Record a limitation for each role that is not mapped. Returns True when all present."""
    missing = [role for role in roles if not context.has(role)]
    for role in missing:
        analysis.limit("unmapped_role", role,
                       "No column is mapped to %s in this dataset." % role)
    return not missing


def quality_is_clean(context):
    return (context.quality is not None
            and context.quality.grade == quality_contract.PASS)


def top_n_setting(context, fallback=5):
    if context.config is None:
        return fallback
    return int(context.config.get("analytics.top_n", fallback))


# ---------------------------------------------------------------------------
# The dimension block — one shape, used by every domain that segments
# ---------------------------------------------------------------------------

def plural(name, count=2):
    """English plural for a dimension name. "category" must not become "categorys"."""
    if count == 1:
        return name
    if name.endswith("y") and not name.endswith(("ay", "ey", "iy", "oy", "uy")):
        return name[:-1] + "ies"
    if name.endswith(("s", "x", "z", "ch", "sh")):
        return name + "es"
    return name + "s"


def emit_dimension(analysis, context, role, name, value_role=mapping_mod.REVENUE,
                   include_movements=True, include_mix=True, include_contribution=True):
    """Rank, compare and decompose one dimension, emitting findings as it goes.

    Sales, product and customer analysis all want the same four things from a dimension —
    who is largest, who moved, how the composition shifted, and who drove the net change —
    so the shape exists once. Returns the structures it built, so a caller can compute
    concentration from the same ranking rather than a second one.
    """
    from .. import materiality as materiality_mod
    from . import mix as mix_mod
    from . import segmentation as segmentation_mod

    column = context.column(role)
    segments = segmentation_mod.segment(context.dataset, context.semantic_map, role,
                                        value_role=value_role, policy=context.policy)
    analysis.note_primitive("segmentation.segment")
    if not segments:
        analysis.limit("no_segments", name,
                       "No usable values were found in the %s column, so %s analysis "
                       "produced nothing." % (column or role, name))
        return None

    grand_total = segmentation_mod.total_of(segments)
    largest = segments[0]
    calculation(
        analysis, "%s.largest" % name,
        "%s is the largest %s by revenue at %s (%s of the total)."
        % (largest.label, name, text_amount(largest.total, context.currency),
           text_percent(largest.share_pct)),
        basis="revenue summed by %s column, ranked descending" % role,
        metric=None, dimension=name,
        dimension_value=(None if largest.redacted else largest.key),
        dimension_redacted=largest.redacted,
        observed=largest.total, share_pct=largest.share_pct,
        unit="currency", currency=context.currency,
        fields_used=(column,), inputs={"members": len(segments)})

    built = {"segments": segments, "grand_total": grand_total,
             "movements": None, "mix": None, "contribution": None}

    by_period = segmentation_mod.segment_by_period(
        context.dataset, context.semantic_map, role, value_role=value_role)
    earlier_periods, later_periods = segmentation_mod.halves(by_period)
    if not earlier_periods or not later_periods:
        analysis.limit(
            "no_comparison_period", name,
            "Only %d period(s) of history are present, so %s movement cannot be compared "
            "period over period." % (len(by_period), name),
            status=contract.INSUFFICIENT_DATA)
        return built

    earlier = segmentation_mod.collapse(by_period, earlier_periods)
    later = segmentation_mod.collapse(by_period, later_periods)
    analysis.comparison_periods = {"earlier": list(earlier_periods),
                                   "later": list(later_periods)}

    if not include_movements:
        return built

    moves = segmentation_mod.movements(earlier, later, policy=context.policy,
                                       column=column, dimension_role=role)
    segmentation_mod.judge_movements(moves, context.config, name.title(), materiality_mod)
    analysis.note_primitive("segmentation.movements")
    built["movements"] = moves

    limit = top_n_setting(context)
    reported = []
    for item in reversed(moves):                       # largest increase first
        if item.materiality == materiality_mod.MATERIAL and len(reported) < limit:
            reported.append(item)
    for item in moves:                                 # then largest decreases
        if (item.materiality == materiality_mod.MATERIAL and item not in reported
                and len(reported) < limit * 2):
            reported.append(item)

    if not reported:
        analysis.limit(
            "no_material_movement", name,
            "No %s moved by more than the materiality thresholds between the two halves "
            "of the period." % name, status=contract.AVAILABLE)

    for item in reported:
        calculation(
            analysis, "%s.movement.%s" % (name, _slug(item.label)),
            "%s moved from %s to %s (%s, %s)."
            % (item.label, text_amount(item.earlier, context.currency),
               text_amount(item.later, context.currency),
               text_amount(item.change, context.currency),
               text_percent(item.change_pct) if item.change_pct is not None
               else "no comparable base"),
            basis="revenue by %s, earlier half versus later half of the period range" % role,
            dimension=name,
            dimension_value=(None if item.redacted else item.key),
            dimension_redacted=item.redacted,
            period="%s..%s" % (later_periods[0], later_periods[-1]),
            comparison_period="%s..%s" % (earlier_periods[0], earlier_periods[-1]),
            observed=item.later, comparison=item.earlier,
            change=item.change, change_pct=item.change_pct,
            direction=item.direction, materiality=item.materiality,
            materiality_reason=item.materiality_reason,
            unit="currency", currency=context.currency, fields_used=(column,))

    if include_mix:
        shifts = mix_mod.mix_shift(earlier, later, policy=context.policy, column=column,
                                  dimension_role=role)
        analysis.note_primitive("mix.mix_shift")
        built["mix"] = shifts
        for item in shifts[:2]:
            if item.points_change is None or item.points_change == ZERO:
                continue
            calculation(
                analysis, "%s.mix.%s" % (name, _slug(item.label)),
                "%s moved from %s to %s of revenue, a shift of %s."
                % (item.label, text_percent(item.earlier_share),
                   text_percent(item.later_share), text_points(item.points_change)),
                basis="share of total revenue by %s, earlier half versus later half" % role,
                dimension=name,
                dimension_value=(None if item.redacted else item.key),
                dimension_redacted=item.redacted,
                observed=item.later_share, comparison=item.earlier_share,
                change=item.points_change, direction=item.direction,
                unit=kpi_contract.PERCENTAGE_POINTS, fields_used=(column,))

    if include_contribution:
        rows, net_change = mix_mod.contribution_to_change(
            earlier, later, policy=context.policy, column=column, dimension_role=role)
        analysis.note_primitive("mix.contribution_to_change")
        built["contribution"] = (rows, net_change)
        if net_change == ZERO:
            analysis.limit(
                "net_change_zero", name,
                "Total revenue was unchanged between the two halves, so the movement "
                "cannot be apportioned across %s." % name, status=contract.AVAILABLE)
        elif rows:
            leader = rows[0]
            calculation(
                analysis, "%s.contribution" % name,
                "%s accounts for %s of the %s net revenue movement."
                % (leader["label"], text_percent(leader["share_of_change_pct"]),
                   text_amount(net_change, context.currency)),
                basis="each member's change divided by the net change in total revenue",
                dimension=name,
                dimension_value=(None if leader["redacted"] else leader.get("key")),
                dimension_redacted=leader["redacted"],
                observed=leader["change"], change=leader["change"],
                share_pct=leader["share_of_change_pct"],
                unit="currency", currency=context.currency, fields_used=(column,))

    return built


def emit_concentration(analysis, context, segments, role, name, subject=None):
    """Concentration measures for an already-ranked dimension."""
    from .. import materiality as materiality_mod
    from . import concentration as concentration_mod

    if not segments:
        return None
    ratios = DEFAULT_RATIOS
    if context.config is not None:
        ratios = context.config.get("analytics.concentration_ratios", DEFAULT_RATIOS)
    record = concentration_mod.profile(segments, tuple(int(r) for r in ratios))
    analysis.note_primitive("concentration.profile")

    column = context.column(role)
    reportable = [n for n in sorted(record["cr"]) if record["cr"][n] is not None]
    if not reportable:
        analysis.limit("concentration_members", name,
                       "Only %d %s present, too few for a concentration ratio."
                       % (record["members"],
                          "%s is" % name if record["members"] == 1
                          else "%s are" % plural(name)),
                       status=contract.INSUFFICIENT_DATA)
        return record

    largest_reported = max(reportable)
    verdict = concentration_mod.judge_share(
        "%s concentration" % (subject or name),
        segments[0].total, record["grand_total"], context.config, materiality_mod)

    calculation(
        analysis, "%s.concentration" % name,
        "The top %d of %d %s account for %s of revenue; the largest single %s holds %s. "
        "Half of revenue comes from %s %s."
        % (largest_reported, record["members"], plural(name, record["members"]),
           text_percent(record["cr"][largest_reported]), name,
           text_percent(record["largest_share_pct"]),
           record["members_for_half"] if record["members_for_half"] is not None
           else "an undetermined number of",
           plural(name, record["members_for_half"] or 2)),
        basis="cumulative share of total revenue held by the highest-ranked members",
        dimension=name,
        observed=record["cr"][largest_reported],
        share_pct=record["largest_share_pct"],
        materiality=verdict.outcome, materiality_reason=verdict.reason,
        unit="percent", fields_used=(column,),
        inputs={"members": record["members"],
                "hhi": record["hhi"],
                "members_for_half": record["members_for_half"],
                "cr": {str(k): v for k, v in record["cr"].items()}})
    return record


def _slug(text):
    """A stable, printable identifier fragment. Never leaks a value a policy redacted."""
    out = []
    for char in str(text).lower():
        out.append(char if char.isalnum() else "_")
    return "".join(out).strip("_")[:40] or "member"
