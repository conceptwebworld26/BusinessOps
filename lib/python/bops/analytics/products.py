"""Product analytics — contribution, growth, margin and mix, weighed together.

A product is not weak because it is small. It might be small and growing, small and highly
profitable, or small and the only reason a large customer stays. The single most useful
thing this module does is refuse to rank products on one axis: `profile()` returns revenue,
share, growth, margin and first appearance as one row per product, so the skill that reads
it has to look at all of them.

Per-product margin **extends** the `gross_margin` KPI rather than restating it — the KPI is
the whole-business figure, this is the same quantity evaluated per segment, and both go
through `segmentation.margin_by_dimension`, which in turn uses the KPI primitives. Nothing
is computed twice.
"""

from decimal import Decimal

from .. import mapping as mapping_mod
from ..kpi import primitives as p
from . import (contract, domain, presentation as presentation_mod,
               segmentation as segmentation_mod)

ZERO = Decimal("0")

ANALYSIS_TYPE = "product"

PRODUCT_DIMENSIONS = ((mapping_mod.PRODUCT, "product"),
                      (mapping_mod.CATEGORY, "category"))

PRODUCT_KPIS = ("gross_margin", "inventory_turnover")


def profile(dataset, semantic_map, dimension_role=mapping_mod.PRODUCT, policy=None,
            config=None):
    """One row per product carrying every axis worth judging it on.

    Returns `[]` when the dimension is unmapped. Margin fields are `None` when no cost
    column exists — absent, not zero, because a zero margin is a very different statement.
    """
    segments = segmentation_mod.segment(dataset, semantic_map, dimension_role,
                                        policy=policy)
    if not segments:
        return []

    by_period = segmentation_mod.segment_by_period(dataset, semantic_map, dimension_role)
    earlier_periods, later_periods = segmentation_mod.halves(by_period)
    earlier = segmentation_mod.collapse(by_period, earlier_periods)
    later = segmentation_mod.collapse(by_period, later_periods)

    margins = {row.get("key", row["label"]): row
               for row in segmentation_mod.margin_by_dimension(
                   dataset, semantic_map, dimension_role, policy=policy)}
    first_seen = segmentation_mod.first_period_seen(dataset, semantic_map, dimension_role)

    rows = []
    for item in segments:
        margin_row = margins.get(item.key)
        earlier_total = earlier.get(item.key, ZERO)
        later_total = later.get(item.key, ZERO)
        rows.append({
            "key": item.key if not item.redacted else None,
            "label": item.label,
            "redacted": item.redacted,
            "rank": item.rank,
            "revenue": item.total,
            "share_pct": item.share_pct,
            "rows": item.rows,
            "earlier": earlier_total if earlier_periods else None,
            "later": later_total if later_periods else None,
            "change": ((later_total - earlier_total)
                       if (earlier_periods and later_periods) else None),
            "change_pct": (p.as_percent(later_total - earlier_total, earlier_total)
                           if (earlier_periods and later_periods and earlier_total)
                           else None),
            "gross_profit": margin_row["gross_profit"] if margin_row else None,
            "margin_pct": margin_row["margin_pct"] if margin_row else None,
            "first_period": first_seen.get(item.key),
        })
    return rows


def analyse(result, presentation=presentation_mod.LOCAL):
    """The full product analysis for one pipeline run."""
    analysis, context = domain.prepare(result, ANALYSIS_TYPE, presentation,
                                       PRODUCT_DIMENSIONS)
    if context is None:
        return analysis

    if not context.has(mapping_mod.PRODUCT) and not context.has(mapping_mod.CATEGORY):
        analysis.status = contract.UNAVAILABLE
        analysis.reason = ("Product analysis is not possible: no column in this dataset "
                           "was identified as a product or a product category.")
        analysis.limit("unmapped_role", mapping_mod.PRODUCT,
                       "No column is mapped to product or category in this dataset.")
        return analysis

    for kpi_id in PRODUCT_KPIS:
        domain.emit_kpi(analysis, context, kpi_id)

    for role, name in PRODUCT_DIMENSIONS:
        if not context.has(role):
            continue
        built = domain.emit_dimension(analysis, context, role, name)
        if built:
            domain.emit_concentration(analysis, context, built["segments"], role, name)

    if context.has(mapping_mod.PRODUCT):
        _profitability(analysis, context)
        _ramp(analysis, context)
    return analysis


def _profitability(analysis, context):
    """Margin per product, where a cost column supports it."""
    if not context.has(mapping_mod.COST):
        analysis.limit(
            "unmapped_role", "product profitability",
            "No cost column is mapped, so per-product margin cannot be calculated. "
            "Revenue ranking alone does not show which products are worth selling.")
        return

    rows = segmentation_mod.margin_by_dimension(
        context.dataset, context.semantic_map, mapping_mod.PRODUCT,
        policy=context.policy)
    analysis.note_primitive("segmentation.margin_by_dimension")
    priced = [row for row in rows if row["margin_pct"] is not None]
    if not priced:
        analysis.limit("no_margin", "product profitability",
                       "No product had both revenue and cost recorded, so margin could "
                       "not be calculated for any of them.")
        return

    best = max(priced, key=lambda r: (r["margin_pct"], r["label"]))
    worst = min(priced, key=lambda r: (r["margin_pct"], r["label"]))
    column = context.column(mapping_mod.PRODUCT)

    domain.calculation(
        analysis, "product.margin_spread",
        "Gross margin ranges from %s on %s to %s on %s, a spread of %s across %d products."
        % (domain.text_percent(worst["margin_pct"]), worst["label"],
           domain.text_percent(best["margin_pct"]), best["label"],
           domain.text_points(best["margin_pct"] - worst["margin_pct"]), len(priced)),
        basis="revenue less cost per product, divided by that product's revenue",
        metric="gross_margin", dimension="product",
        observed=best["margin_pct"], comparison=worst["margin_pct"],
        change=best["margin_pct"] - worst["margin_pct"],
        unit="percent",
        fields_used=(column, context.column(mapping_mod.REVENUE),
                     context.column(mapping_mod.COST)),
        inputs={"products_priced": len(priced),
                "highest_margin": best["label"], "lowest_margin": worst["label"]})

    # The product with the largest gross profit is not always the largest by revenue, and
    # that difference is usually the point of the analysis.
    largest_profit = max(priced, key=lambda r: (r["gross_profit"], r["label"]))
    largest_revenue = max(priced, key=lambda r: (r["revenue"], r["label"]))
    if largest_profit["label"] != largest_revenue["label"]:
        domain.calculation(
            analysis, "product.profit_versus_revenue",
            "%s is the largest product by revenue, but %s contributes the most gross "
            "profit (%s against %s)."
            % (largest_revenue["label"], largest_profit["label"],
               domain.text_amount(largest_profit["gross_profit"], context.currency),
               domain.text_amount(largest_revenue["gross_profit"], context.currency)),
            basis="gross profit per product, ranked, compared with the revenue ranking",
            dimension="product", observed=largest_profit["gross_profit"],
            comparison=largest_revenue["gross_profit"],
            unit="currency", currency=context.currency,
            fields_used=(column, context.column(mapping_mod.REVENUE),
                         context.column(mapping_mod.COST)))


def _ramp(analysis, context):
    """Products that appear part-way through the window.

    This is an observation about the data window, not an anomaly detector: a product whose
    first record is later than the file's first period either launched then or was simply
    not recorded before. Both readings are stated; neither is chosen.
    """
    first_seen = segmentation_mod.first_period_seen(
        context.dataset, context.semantic_map, mapping_mod.PRODUCT)
    analysis.note_primitive("segmentation.first_period_seen")
    if not first_seen:
        return
    periods = sorted(set(first_seen.values()))
    opening = periods[0]
    later_entrants = [key for key, period in first_seen.items() if period != opening]
    if not later_entrants:
        return

    policy = context.policy
    column = context.column(mapping_mod.PRODUCT)
    labels = []
    for index, key in enumerate(sorted(later_entrants,
                                       key=lambda k: (first_seen[k], str(k))), start=1):
        label, _redacted = policy.label(column, key, role=mapping_mod.PRODUCT, rank=index)
        labels.append("%s (first seen %s)" % (label, first_seen[key]))

    domain.fact(
        analysis, "product.later_entrants",
        "%d product(s) have no records in the opening period %s: %s. They either began "
        "selling later or were not recorded earlier; this dataset cannot distinguish the "
        "two." % (len(later_entrants), opening, "; ".join(labels[:5])),
        dimension="product", observed=len(later_entrants), unit="count",
        fields_used=(column, context.column(mapping_mod.DATE)),
        provenance=dict(analysis.provenance))
