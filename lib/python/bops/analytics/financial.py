"""Financial analysis — the profit and cash picture, and an honest account of its gaps.

This module reports the financial KPIs the engine could produce, the movement in the ones
that have a time series, and — just as prominently — the ones it could not produce and why.
A sales extract has no operating expenses, no balance sheet and no cash position; the
correct output for a business that supplies one is a short set of margin facts and a clear
statement that profitability below gross level, working capital and runway are unavailable
for a named reason. Filling those gaps with an estimate would be the single most damaging
thing this layer could do.

Nothing here computes a KPI. Revenue, gross profit, margin, EBITDA, working capital, burn
and runway all come from the Milestone 5 engine. What is computed here is movement: the
per-period margin series, the cost-to-revenue ratio and the half-over-half comparison,
which the KPI engine has no equivalent of.

This module performs no transactions, proposes no accounting entries and executes nothing.
It reads numbers and reports them.
"""

from decimal import Decimal

from .. import materiality as materiality_mod
from .. import mapping as mapping_mod
from ..kpi import contract as kpi_contract
from ..kpi import primitives as p
from . import (concentration as concentration_mod, contract, domain,
               presentation as presentation_mod, segmentation as segmentation_mod)

ZERO = Decimal("0")

ANALYSIS_TYPE = "financial"

#: Reported in this order — the profit-and-loss walk, then the balance sheet, then cash.
FINANCIAL_KPIS = (
    "revenue", "gross_profit", "gross_margin",
    "operating_profit", "operating_margin", "ebitda", "ebitda_margin",
    "working_capital", "days_sales_outstanding", "days_payable_outstanding",
    "burn_rate", "runway", "return_on_investment",
)

FINANCIAL_DIMENSIONS = ((mapping_mod.CUSTOMER, "customer"),
                        (mapping_mod.PRODUCT, "product"))


def analyse(result, presentation=presentation_mod.LOCAL):
    """The full financial analysis for one pipeline run."""
    analysis, context = domain.prepare(result, ANALYSIS_TYPE, presentation,
                                       FINANCIAL_DIMENSIONS)
    if context is None:
        return analysis

    if not context.has(mapping_mod.REVENUE):
        analysis.status = contract.UNAVAILABLE
        analysis.reason = ("Financial analysis needs a revenue column; none is mapped in "
                           "this dataset.")
        analysis.limit("unmapped_role", mapping_mod.REVENUE,
                       "No column is mapped to revenue in this dataset.")
        return analysis

    for kpi_id in FINANCIAL_KPIS:
        domain.emit_kpi(analysis, context, kpi_id)

    _margin_movement(analysis, context)
    _cost_ratio(analysis, context)
    _profit_trend(analysis, context)
    _revenue_concentration(analysis, context)
    return analysis


def _margin_movement(analysis, context):
    """Gross margin per period, and whether it moved materially — in points, not percent."""
    if not context.has(mapping_mod.COST):
        analysis.limit(
            "unmapped_role", "margin movement",
            "No cost column is mapped, so gross margin cannot be tracked over time.")
        return

    series = segmentation_mod.margin_by_period(context.dataset, context.semantic_map)
    analysis.note_primitive("segmentation.margin_by_period")
    if len(series) < 4:
        analysis.limit(
            "short_margin_series", "margin movement",
            "Only %d period(s) have both revenue and cost, too few to compare margin "
            "half over half." % len(series), status=contract.INSUFFICIENT_DATA)
        return

    earlier, later = segmentation_mod.series_halves(series)
    verdict = materiality_mod.assess_margin("Gross margin", later, earlier, context.config)
    midpoint = len(series) // 2
    domain.calculation(
        analysis, "margin.movement",
        "Average gross margin moved from %s to %s, a change of %s (%s)."
        % (domain.text_percent(earlier), domain.text_percent(later),
           domain.text_points(later - earlier), verdict.outcome),
        basis="mean of the per-period gross margin series, earlier half versus later half",
        metric="gross_margin",
        period="%s..%s" % (series[midpoint][0], series[-1][0]),
        comparison_period="%s..%s" % (series[0][0], series[midpoint - 1][0]),
        observed=later, comparison=earlier, change=later - earlier,
        unit=kpi_contract.PERCENTAGE_POINTS,
        direction=("increase" if later > earlier
                   else "decrease" if later < earlier else "flat"),
        materiality=verdict.outcome, materiality_reason=verdict.reason,
        fields_used=(context.column(mapping_mod.REVENUE),
                     context.column(mapping_mod.COST),
                     context.column(mapping_mod.DATE)),
        inputs={"periods": len(series)})


def _cost_ratio(analysis, context):
    """Cost of goods as a share of revenue — the same movement seen from the cost side."""
    if not context.has(mapping_mod.COST):
        return
    revenue = p.total(context.dataset, context.semantic_map, mapping_mod.REVENUE)
    cost = p.total(context.dataset, context.semantic_map, mapping_mod.COST)
    ratio = p.as_percent(cost, revenue)
    if ratio is None:
        analysis.limit("zero_revenue", "cost ratio",
                       "Total revenue is zero, so cost as a share of revenue is undefined "
                       "rather than zero.")
        return
    domain.calculation(
        analysis, "cost.ratio",
        "Cost of goods is %s of revenue over the whole period." % domain.text_percent(ratio),
        basis="total cost divided by total revenue",
        observed=ratio, unit="percent",
        fields_used=(context.column(mapping_mod.REVENUE),
                     context.column(mapping_mod.COST)),
        inputs={"revenue": revenue, "cost": cost})


def _profit_trend(analysis, context):
    """Gross profit by period, compared half over half against the materiality thresholds."""
    if not context.has(mapping_mod.COST):
        return
    revenue = dict(p.series_by_period(context.dataset, context.semantic_map,
                                      mapping_mod.REVENUE) or [])
    cost = dict(p.series_by_period(context.dataset, context.semantic_map,
                                   mapping_mod.COST) or [])
    periods = sorted(set(revenue) & set(cost))
    if len(periods) < 2:
        analysis.limit(
            "short_profit_series", "gross profit trend",
            "Fewer than two periods have both revenue and cost, so gross profit cannot be "
            "compared.", status=contract.INSUFFICIENT_DATA)
        return

    midpoint = len(periods) // 2
    earlier = sum((revenue[k] - cost[k] for k in periods[:midpoint]), ZERO)
    later = sum((revenue[k] - cost[k] for k in periods[midpoint:]), ZERO)
    verdict = materiality_mod.assess_amount("Gross profit", later, earlier, context.config)
    domain.calculation(
        analysis, "gross_profit.trend",
        "Gross profit moved from %s in the earlier half of the period to %s in the later "
        "half, a change of %s (%s)."
        % (domain.text_amount(earlier, context.currency),
           domain.text_amount(later, context.currency),
           domain.text_amount(later - earlier, context.currency), verdict.outcome),
        basis="gross profit summed by period, earlier half versus later half",
        metric="gross_profit",
        period="%s..%s" % (periods[midpoint], periods[-1]),
        comparison_period="%s..%s" % (periods[0], periods[midpoint - 1]),
        observed=later, comparison=earlier, change=later - earlier,
        change_pct=p.as_percent(later - earlier, earlier) if earlier else None,
        unit="currency", currency=context.currency,
        direction=("increase" if later > earlier
                   else "decrease" if later < earlier else "flat"),
        materiality=verdict.outcome, materiality_reason=verdict.reason,
        fields_used=(context.column(mapping_mod.REVENUE),
                     context.column(mapping_mod.COST),
                     context.column(mapping_mod.DATE)))


def _revenue_concentration(analysis, context):
    """How exposed the revenue line is to a small number of counterparties."""
    for role, name in FINANCIAL_DIMENSIONS:
        if not context.has(role):
            continue
        segments = segmentation_mod.segment(context.dataset, context.semantic_map, role,
                                            policy=context.policy)
        analysis.note_primitive("segmentation.segment")
        if not segments:
            continue
        domain.emit_concentration(analysis, context, segments, role, name,
                                  subject="Revenue by %s" % name)
        return
    analysis.limit(
        "no_concentration_dimension", "revenue concentration",
        "Neither a customer nor a product column is mapped, so revenue concentration "
        "cannot be assessed.")


def unavailable_summary(analysis):
    """The financial picture that could not be produced, grouped by why.

    Reported at the same prominence as the findings: a reader who is not told that
    operating profit is missing will assume gross profit is the whole story.
    """
    grouped = {}
    for item in analysis.limitations:
        if item.code.startswith("kpi_"):
            grouped.setdefault(item.status, []).append((item.subject, item.reason))
    return {status: sorted(rows) for status, rows in sorted(grouped.items())}
