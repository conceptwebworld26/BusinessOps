"""Deterministic sales aggregations.

Only arithmetic lives here — totals, shares, trends. Deciding which of these facts is worth
telling a business owner is judgement, and that belongs to the `bops-sales-intelligence`
skill, which reads these outputs rather than recomputing them.
"""

from decimal import Decimal, ROUND_HALF_UP

from .. import mapping as mapping_mod
from ..kpi import primitives as kpi_primitives
from ..kpi.primitives import period_key as _period_key
from ..kpi.registry import monthly_totals
from . import contract, domain, presentation as presentation_mod, segmentation


def _dec(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money(value):
    return _dec(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _rate(value):
    return _dec(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def by_dimension(dataset, semantic_map, role, value_role=mapping_mod.REVENUE):
    """Total a numeric role grouped by a categorical role, with each group's share."""
    key_column = semantic_map.column_for(role)
    value_column = semantic_map.column_for(value_role)
    if not key_column or not value_column:
        return []

    totals = {}
    for row in dataset.rows:
        key = row.get(key_column)
        value = row.get(value_column)
        if key in (None, "") or not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        totals[key] = totals.get(key, Decimal("0")) + _dec(value)

    grand_total = sum(totals.values(), Decimal("0"))
    rows = [{"key": key,
             "total": _money(total),
             "share_pct": _rate(total / grand_total * Decimal("100")) if grand_total else None}
            for key, total in totals.items()]
    rows.sort(key=lambda r: -r["total"])
    return rows


def period_split(dataset, semantic_map, role, value_role=mapping_mod.REVENUE):
    """Totals per dimension for the earlier and later halves of the period range."""
    date_column = semantic_map.column_for(mapping_mod.DATE)
    key_column = semantic_map.column_for(role)
    value_column = semantic_map.column_for(value_role)
    if not (date_column and key_column and value_column):
        return {}, [], []

    periods = sorted({_period_key(r.get(date_column)) for r in dataset.rows} - {None})
    if len(periods) < 2:
        return {}, periods, []
    midpoint = len(periods) // 2
    earlier, later = set(periods[:midpoint]), set(periods[midpoint:])

    split = {}
    for row in dataset.rows:
        period = _period_key(row.get(date_column))
        key = row.get(key_column)
        value = row.get(value_column)
        if (period is None or key in (None, "")
                or not isinstance(value, (int, float)) or isinstance(value, bool)):
            continue
        entry = split.setdefault(key, {"earlier": Decimal("0"), "later": Decimal("0")})
        entry["earlier" if period in earlier else "later"] += _dec(value)

    return split, sorted(earlier), sorted(later)


def trend(dataset, semantic_map, value_role=mapping_mod.REVENUE):
    """The monthly series plus its direction and magnitude, half over half."""
    series = monthly_totals(dataset, semantic_map, value_role)
    if len(series) < 2:
        return {"series": series, "direction": None, "change_pct": None}

    midpoint = len(series) // 2
    earlier = sum((v for _, v in series[:midpoint]), Decimal("0"))
    later = sum((v for _, v in series[midpoint:]), Decimal("0"))
    change = ((later - earlier) / earlier * Decimal("100")) if earlier else None

    direction = None
    if change is not None:
        direction = "rising" if change > 1 else "falling" if change < -1 else "flat"

    return {"series": series,
            "first_period": series[0][0], "last_period": series[-1][0],
            "earlier_total": _money(earlier), "later_total": _money(later),
            "change_pct": _rate(change) if change is not None else None,
            "direction": direction,
            "peak": max(series, key=lambda p: p[1]),
            "trough": min(series, key=lambda p: p[1])}


def margin_series(dataset, semantic_map):
    """Gross margin percent per month, rounded — the series that reveals compression.

    The arithmetic lives in `segmentation.margin_by_period`; this wrapper keeps the
    Milestone 2 rounded shape the vertical-slice renderer expects.
    """
    return [(period, _rate(margin))
            for period, margin in segmentation.margin_by_period(dataset, semantic_map)]


def movers(split, minimum_base=Decimal("0")):
    """Rank dimension members by their half-over-half movement."""
    rows = []
    for key, halves in split.items():
        earlier, later = halves["earlier"], halves["later"]
        if earlier <= minimum_base and later <= minimum_base:
            continue
        change = later - earlier
        change_pct = (change / earlier * Decimal("100")) if earlier else None
        rows.append({"key": key, "earlier": _money(earlier), "later": _money(later),
                     "change": _money(change),
                     "change_pct": _rate(change_pct) if change_pct is not None else None})
    rows.sort(key=lambda r: r["change"])
    return rows


# ===========================================================================
# Milestone 6 — the full sales analysis
# ===========================================================================
#
# Everything above this line is the Milestone 2 aggregation set, still used by the
# vertical-slice renderer. Everything below assembles a complete `AnalysisSet`.
#
# Note what `analyse` does *not* do: it never recomputes revenue growth. The KPI engine
# owns that formula, so the magnitude and direction of the trend are read from the
# `revenue_growth` result and only the shape of the series — how many periods, which month
# was strongest, which weakest — is derived here.

ANALYSIS_TYPE = "sales"

SALES_DIMENSIONS = (
    (mapping_mod.PRODUCT, "product"),
    (mapping_mod.CATEGORY, "category"),
    (mapping_mod.REGION, "region"),
    (mapping_mod.SALESPERSON, "salesperson"),
    (mapping_mod.CUSTOMER, "customer"),
)

#: Dimensions where concentration is decision-relevant rather than merely descriptive.
CONCENTRATED_DIMENSIONS = (mapping_mod.CUSTOMER, mapping_mod.PRODUCT)

SALES_KPIS = ("revenue", "revenue_growth", "gross_profit", "gross_margin",
              "average_order_value")


def analyse(result, presentation=presentation_mod.LOCAL):
    """The full sales analysis for one pipeline run."""
    analysis, context = domain.prepare(result, ANALYSIS_TYPE, presentation,
                                       SALES_DIMENSIONS)
    if context is None:
        return analysis

    if not (context.has(mapping_mod.REVENUE) and context.has(mapping_mod.DATE)):
        analysis.status = contract.UNAVAILABLE
        analysis.reason = ("Sales analysis needs a date column and a revenue column. "
                           "Missing: %s."
                           % ", ".join(r for r in (mapping_mod.DATE, mapping_mod.REVENUE)
                                       if not context.has(r)))
        domain.require(analysis, context, mapping_mod.DATE, mapping_mod.REVENUE)
        return analysis

    for kpi_id in SALES_KPIS:
        domain.emit_kpi(analysis, context, kpi_id)

    _revenue_shape(analysis, context)
    _order_trend(analysis, context)

    for role, name in SALES_DIMENSIONS:
        if not context.has(role):
            continue
        # Customer movement belongs to customer intelligence; sales takes the
        # concentration figure only, so the two skills do not report the same list twice.
        full = role != mapping_mod.CUSTOMER
        built = domain.emit_dimension(analysis, context, role, name,
                                      include_movements=full, include_mix=full,
                                      include_contribution=full)
        if built and role in CONCENTRATED_DIMENSIONS:
            domain.emit_concentration(analysis, context, built["segments"], role, name)

    return analysis


def _revenue_shape(analysis, context):
    """The shape of the revenue series. Magnitude comes from the KPI, never from here."""
    series = kpi_primitives.series_by_period(
        context.dataset, context.semantic_map, mapping_mod.REVENUE) or []
    analysis.note_primitive("kpi.primitives.series_by_period")
    if len(series) < 2:
        analysis.limit("single_period", "revenue trend",
                       "Only %d period is present, so no revenue trend can be assessed."
                       % len(series), status=contract.INSUFFICIENT_DATA)
        return

    peak = max(series, key=lambda pair: (pair[1], pair[0]))
    trough = min(series, key=lambda pair: (pair[1], pair[0]))
    domain.calculation(
        analysis, "revenue.series",
        "Revenue is recorded across %d months, from %s to %s. The strongest month was %s "
        "at %s; the weakest was %s at %s."
        % (len(series), series[0][0], series[-1][0],
           peak[0], domain.text_amount(peak[1], context.currency),
           trough[0], domain.text_amount(trough[1], context.currency)),
        basis="revenue summed by calendar month",
        metric="revenue", period="%s..%s" % (series[0][0], series[-1][0]),
        observed=peak[1], comparison=trough[1], unit="currency",
        currency=context.currency,
        fields_used=(context.column(mapping_mod.DATE),
                     context.column(mapping_mod.REVENUE)),
        inputs={"periods": len(series), "peak_period": peak[0],
                "trough_period": trough[0]})

    growth = context.kpi("revenue_growth")
    if growth is not None and growth.available and growth.value is not None:
        direction = ("rising" if growth.value > 0
                     else "falling" if growth.value < 0 else "flat")
        domain.calculation(
            analysis, "revenue.direction",
            "Revenue is %s across the period: the KPI engine reports revenue growth of %s."
            % (direction, domain.text_percent(growth.value)),
            basis="revenue_growth KPI result (not recomputed here)",
            metric="revenue_growth", observed=growth.value, direction=direction,
            unit="percent", change_pct=growth.value,
            fields_used=tuple(sorted(growth.definition.inputs)))


def _order_trend(analysis, context):
    """Order counts per month, and how the count moved. Extends nothing the KPIs own."""
    if not context.has(mapping_mod.ORDER_ID):
        analysis.limit("unmapped_role", "order trend",
                       "No column is mapped to order_id, so order volume was not analysed.")
        return

    counts = segmentation.entity_count_per_period(
        context.dataset, context.semantic_map, mapping_mod.ORDER_ID)
    analysis.note_primitive("segmentation.entity_count_per_period")
    if not counts:
        analysis.limit("no_orders", "order trend",
                       "No dated orders were found, so order volume was not analysed.")
        return

    periods = sorted(counts)
    if len(periods) < 2:
        analysis.limit("single_period", "order trend",
                       "Only one period of orders is present, so order volume cannot be "
                       "compared.", status=contract.INSUFFICIENT_DATA)
        return

    midpoint = len(periods) // 2
    earlier = sum(counts[p] for p in periods[:midpoint])
    later = sum(counts[p] for p in periods[midpoint:])
    change_pct = kpi_primitives.as_percent(later - earlier, earlier)
    domain.calculation(
        analysis, "orders.trend",
        "Distinct orders moved from %d in the earlier half of the period to %d in the "
        "later half (%s)."
        % (earlier, later,
           domain.text_percent(change_pct) if change_pct is not None
           else "no comparable base"),
        basis="distinct order identifiers per month, earlier half versus later half",
        period="%s..%s" % (periods[midpoint], periods[-1]),
        comparison_period="%s..%s" % (periods[0], periods[midpoint - 1]),
        observed=later, comparison=earlier, change=later - earlier,
        change_pct=change_pct, unit="count",
        direction=("increase" if later > earlier
                   else "decrease" if later < earlier else "flat"),
        fields_used=(context.column(mapping_mod.ORDER_ID),
                     context.column(mapping_mod.DATE)))
