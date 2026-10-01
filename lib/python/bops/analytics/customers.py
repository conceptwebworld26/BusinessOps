"""Customer analytics — behaviour only, never inferred intent.

The architecture is explicit that customer intelligence describes what customers *did*, not
what they wanted, felt or intended. Everything in this module is a count, a share, a total
or a ratio of observed transactions. There is no propensity, no segment persona and no
inferred motivation, because none of that is in a sales file.

Retention, churn, lifetime value and acquisition cost are **not** computed here — the KPI
engine owns those formulas and this module reads its results. What is computed here is what
the KPI engine has no equivalent for: how many distinct customers there are, how many are
new in each period, how many return, how concentrated revenue is, and how cohorts behave
over time.

Customer identifiers are handled conservatively throughout: no individual transaction is
ever emitted, groups below the k-anonymity floor report banded counts, and in shareable
presentation every customer label becomes a stable pseudonym.
"""

from decimal import Decimal

from .. import mapping as mapping_mod
from ..kpi import primitives as p
from . import (cohorts as cohorts_mod, contract, domain,
               presentation as presentation_mod)

ZERO = Decimal("0")

ANALYSIS_TYPE = "customer"

CUSTOMER_DIMENSIONS = ((mapping_mod.CUSTOMER, "customer"),)

CUSTOMER_KPIS = ("customer_lifetime_value", "customer_acquisition_cost",
                 "customer_retention", "customer_churn", "net_revenue_retention")


def analyse(result, presentation=presentation_mod.LOCAL):
    """The full customer analysis for one pipeline run."""
    analysis, context = domain.prepare(result, ANALYSIS_TYPE, presentation,
                                       CUSTOMER_DIMENSIONS)
    if context is None:
        return analysis

    if not context.has(mapping_mod.CUSTOMER):
        analysis.status = contract.UNAVAILABLE
        analysis.reason = (
            "Customer analysis is not possible: no column in this dataset was identified "
            "as a customer. Add or confirm a customer column and the analysis will run.")
        analysis.limit("unmapped_role", mapping_mod.CUSTOMER,
                       "No column is mapped to customer in this dataset.")
        return analysis

    for kpi_id in CUSTOMER_KPIS:
        domain.emit_kpi(analysis, context, kpi_id)

    _population(analysis, context)
    _new_and_returning(analysis, context)

    built = domain.emit_dimension(analysis, context, mapping_mod.CUSTOMER, "customer")
    if built:
        domain.emit_concentration(analysis, context, built["segments"],
                                  mapping_mod.CUSTOMER, "customer", subject="Customer")

    _cohorts(analysis, context)
    return analysis


def _population(analysis, context):
    """How many customers there are, and how much the typical one is worth."""
    column = context.column(mapping_mod.CUSTOMER)
    count = p.distinct_count(context.dataset, context.semantic_map, mapping_mod.CUSTOMER)
    analysis.note_primitive("kpi.primitives.distinct_count")
    if not count:
        analysis.limit("no_customers", "customer count",
                       "The customer column contains no usable values.")
        return

    shown, banded = context.policy.entity_count(count)
    domain.fact(
        analysis, "customers.count",
        "The dataset covers %s distinct customers across %d transaction rows."
        % (shown, context.dataset.row_count),
        dimension="customer", observed=count, unit="count",
        fields_used=(column,),
        caveats=(["Fewer customers than the k-anonymity floor, so the count is banded."]
                 if banded else []),
        provenance=dict(analysis.provenance))

    if not context.has(mapping_mod.REVENUE):
        return
    totals = p.revenue_per_entity(context.dataset, context.semantic_map,
                                  mapping_mod.CUSTOMER) or {}
    if not totals:
        return
    values = sorted(totals.values())
    median = values[len(values) // 2]
    domain.calculation(
        analysis, "customers.median_revenue",
        "Median revenue per customer is %s, against a mean of %s — the gap between them is "
        "the measure of how uneven the customer base is."
        % (domain.text_amount(median, context.currency),
           domain.text_amount(p.mean(values), context.currency)),
        basis="total revenue per customer; median and mean of that distribution",
        dimension="customer", observed=median, comparison=p.mean(values),
        unit="currency", currency=context.currency,
        fields_used=(column, context.column(mapping_mod.REVENUE)),
        inputs={"customers": count})


def _new_and_returning(analysis, context):
    """New versus returning customers per period, and how many ever come back."""
    per_period = p.distinct_entities_per_period(
        context.dataset, context.semantic_map, mapping_mod.CUSTOMER)
    analysis.note_primitive("kpi.primitives.distinct_entities_per_period")
    if not per_period:
        analysis.limit("no_dated_customers", "new versus returning",
                       "Customers could not be placed in periods; a date column is needed.")
        return

    periods = sorted(per_period)
    if len(periods) < 2:
        analysis.limit(
            "single_period", "new versus returning",
            "Only one period is present, so a customer cannot yet be new or returning.",
            status=contract.INSUFFICIENT_DATA)
        return

    seen, rows = set(), []
    for period in periods:
        active = per_period[period]
        new = active - seen
        rows.append({"period": period, "active": len(active), "new": len(new),
                     "returning": len(active) - len(new)})
        seen |= active

    # The first period cannot distinguish new from returning: everyone is new by definition.
    comparable = rows[1:]
    total_new = sum(r["new"] for r in comparable)
    total_active = sum(r["active"] for r in comparable)
    domain.calculation(
        analysis, "customers.new_versus_returning",
        "After the opening period, %d of %d customer-periods were first appearances "
        "(%s); the rest were returning customers."
        % (total_new, total_active, domain.text_percent(
            p.as_percent(total_new, total_active))),
        basis="distinct customers per period, compared with every customer seen before",
        dimension="customer", observed=total_new, comparison=total_active,
        share_pct=p.as_percent(total_new, total_active), unit="count",
        fields_used=(context.column(mapping_mod.CUSTOMER),
                     context.column(mapping_mod.DATE)),
        inputs={"periods": len(periods)},
        assumptions=[cohorts_mod.WINDOW_ASSUMPTION])

    appearances = {}
    for period in periods:
        for entity in per_period[period]:
            appearances[entity] = appearances.get(entity, 0) + 1
    repeat = sum(1 for count in appearances.values() if count > 1)
    domain.calculation(
        analysis, "customers.repeat",
        "%d of %d customers appear in more than one period (%s)."
        % (repeat, len(appearances),
           domain.text_percent(p.as_percent(repeat, len(appearances)))),
        basis="count of customers appearing in two or more distinct periods",
        dimension="customer", observed=repeat, comparison=len(appearances),
        share_pct=p.as_percent(repeat, len(appearances)), unit="count",
        fields_used=(context.column(mapping_mod.CUSTOMER),
                     context.column(mapping_mod.DATE)))


def _cohorts(analysis, context):
    """Acquisition cohorts and the retention curve across them."""
    minimum = cohorts_mod.DEFAULT_MINIMUM_PERIODS
    if context.config is not None:
        minimum = int(context.config.get("analytics.min_cohort_periods", minimum))

    built = cohorts_mod.build(context.dataset, context.semantic_map,
                              minimum_periods=minimum, policy=context.policy)
    analysis.note_primitive("cohorts.build")
    if built["status"] != contract.AVAILABLE:
        analysis.limit("cohorts_%s" % built["status"], "cohort analysis",
                       built["reason"], status=built["status"])
        return

    sizes = cohorts_mod.cohort_sizes(built)
    domain.calculation(
        analysis, "customers.cohorts",
        "%d acquisition cohorts were identified, from %s (%d customers) to %s "
        "(%d customers)."
        % (len(sizes), sizes[0][0], sizes[0][1], sizes[-1][0], sizes[-1][1]),
        basis="customers grouped by the first period in which they appear",
        dimension="customer", observed=len(sizes), unit="count",
        fields_used=(context.column(mapping_mod.CUSTOMER),
                     context.column(mapping_mod.DATE)),
        assumptions=list(built["assumptions"]),
        inputs={"cohorts": len(sizes), "periods": len(built["periods"])})

    curve = cohorts_mod.retention_curve(built)
    analysis.note_primitive("cohorts.retention_curve")
    later = [row for row in curve if row["offset"] > 0]
    if not later:
        analysis.limit("cohort_offsets", "cohort retention",
                       "No cohort has been observed beyond its acquisition period.",
                       status=contract.INSUFFICIENT_DATA)
        return

    first = later[0]
    domain.calculation(
        analysis, "customers.cohort_retention",
        "One period after acquisition, cohorts retain %s of their customers on average "
        "(mean across the %d cohorts old enough to be observed)."
        % (domain.text_percent(first["mean_retention_pct"]), first["cohorts"]),
        basis="mean retention at each offset, averaged only over cohorts that reached it",
        dimension="customer", observed=first["mean_retention_pct"], unit="percent",
        fields_used=(context.column(mapping_mod.CUSTOMER),
                     context.column(mapping_mod.DATE)),
        assumptions=list(built["assumptions"]),
        inputs={"offset": 1, "cohorts_observed": first["cohorts"]})
