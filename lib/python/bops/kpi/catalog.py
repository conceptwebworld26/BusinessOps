"""The approved KPI catalogue — 27 metrics.

The list is the product specification's "KPI Analysis / Potential KPIs", which enumerates
exactly twenty-seven metrics. `architecture.md` states the count ("~27 KPIs") but does not
enumerate them; see the M5 development record for the taxonomy gap this mirrors from M4.

Every formula in BusinessOps lives here or in `primitives.py` and nowhere else. Skills and
commands describe when and why a metric applies; they never restate the arithmetic.

Each definition declares what it needs, so a metric whose inputs are absent reports
`unavailable` naming the field, and one that does not suit the business model reports
`not_applicable` — which are different statements a user must be able to tell apart.
"""

from decimal import Decimal

from .. import mapping as m
from . import primitives as p
from .contract import (
    ALL_MODELS, COUNT, CURRENCY, DAYS, DERIVED, KPIDefinition, PERCENT,
    PERIOD_OVER_PERIOD, POINT_IN_TIME, RATIO, SUM, available, insufficient_data,
    not_applicable, unavailable,
)

CATALOGUE = []


def define(**kwargs):
    definition = KPIDefinition(**kwargs)
    CATALOGUE.append(definition)
    return definition


# Business models that do not sell discrete orders, so order-based metrics are moot.
_NON_TRANSACTIONAL = ("saas",)
_RECURRING_MODELS = ("saas", "marketplace")
_INVENTORY_MODELS = ("retail", "wholesale_distribution", "manufacturing", "hospitality")
_SERVICE_MODELS = ("professional_services", "agency")


def _require(context, *roles):
    """Check an input contract.

    Returns (absent, unconfirmed). Both block calculation, but for different reasons the
    user must be able to tell apart: an absent field needs supplying, an unconfirmed one
    needs a decision.
    """
    absent, unconfirmed = [], []
    for role in roles:
        mapping = context.semantic_map.mappings.get(role)
        if mapping is None:
            absent.append(role)
        elif mapping.status != m.AUTO:
            unconfirmed.append(role)
    return absent, unconfirmed


def _blocked(definition, context, *roles):
    """A ready-made `unavailable` result when an input contract is not satisfied."""
    absent, unconfirmed = _require(context, *roles)
    if absent or unconfirmed:
        return unavailable(definition, missing_inputs=absent,
                           unconfirmed_inputs=unconfirmed)
    return None


# ===========================================================================
# 1-2. Revenue and revenue growth
# ===========================================================================

def _calc_revenue(definition, context):
    blocked = _blocked(definition, context, m.DATE, m.REVENUE)
    if blocked:
        return blocked
    value = p.total(context.dataset, context.semantic_map, m.REVENUE)
    series = p.series_by_period(context.dataset, context.semantic_map, m.REVENUE) or []
    return available(definition, value, currency=context.currency,
                     inputs_used={"revenue_column": context.column(m.REVENUE),
                                  "rows": context.dataset.row_count},
                     periods=len(series), rows_used=context.dataset.row_count,
                     series=series)


REVENUE = define(
    kpi_id="revenue", name="Revenue", category="revenue",
    description="Total revenue recognised across the reporting period.",
    formula="sum(revenue)", inputs=(m.DATE, m.REVENUE), unit=CURRENCY,
    aggregation=SUM, calculator=_calc_revenue,
    result_semantics="A single monetary total for the whole period.")


def _calc_revenue_growth(definition, context):
    blocked = _blocked(definition, context, m.DATE, m.REVENUE)
    if blocked:
        return blocked
    series = p.series_by_period(context.dataset, context.semantic_map, m.REVENUE) or []
    if len(series) < definition.minimum_periods:
        return insufficient_data(definition, len(series), definition.minimum_periods)
    earlier, later = p.split_halves(series)
    prior, current = p.sum_series(earlier), p.sum_series(later)
    growth = p.as_percent(current - prior, prior)
    if growth is None:
        return unavailable(
            definition,
            reason="The earlier comparison period has zero revenue, so a growth rate is "
                   "undefined rather than infinite.")
    return available(definition, growth, currency=None,
                     inputs_used={"prior_total": prior, "current_total": current,
                                  "prior_periods": "%s..%s" % (earlier[0][0], earlier[-1][0]),
                                  "current_periods": "%s..%s" % (later[0][0], later[-1][0])},
                     periods=len(series), series=series)


REVENUE_GROWTH = define(
    kpi_id="revenue_growth", name="Revenue growth", category="revenue",
    description="Change in revenue between the earlier and later halves of the period range.",
    formula="(sum(revenue, later half) - sum(revenue, earlier half)) / sum(revenue, earlier half) * 100",
    inputs=(m.DATE, m.REVENUE), unit=PERCENT, aggregation=PERIOD_OVER_PERIOD,
    calculator=_calc_revenue_growth, minimum_periods=2,
    calculation_notes="Half over half rather than last versus first, so one unusual month "
                      "does not define a trend.",
    result_semantics="A percentage change. Undefined when the earlier period is zero.")


# ===========================================================================
# 3-4. Gross profit and gross margin
# ===========================================================================

def _gross_parts(context):
    revenue = p.total(context.dataset, context.semantic_map, m.REVENUE)
    cost = p.total(context.dataset, context.semantic_map, m.COST)
    return revenue, cost


def _calc_gross_profit(definition, context):
    blocked = _blocked(definition, context, m.DATE, m.REVENUE, m.COST)
    if blocked:
        return blocked
    revenue, cost = _gross_parts(context)
    return available(definition, revenue - cost, currency=context.currency,
                     inputs_used={"revenue": revenue, "cost_of_goods": cost})


GROSS_PROFIT = define(
    kpi_id="gross_profit", name="Gross profit", category="profitability",
    description="Revenue remaining after the direct cost of goods sold.",
    formula="sum(revenue) - sum(cost_of_goods)",
    inputs=(m.DATE, m.REVENUE, m.COST), unit=CURRENCY, aggregation=DERIVED,
    calculator=_calc_gross_profit)


def _calc_gross_margin(definition, context):
    blocked = _blocked(definition, context, m.DATE, m.REVENUE, m.COST)
    if blocked:
        return blocked
    revenue, cost = _gross_parts(context)
    margin = p.as_percent(revenue - cost, revenue)
    if margin is None:
        return unavailable(definition,
                           reason="Revenue is zero, so a margin percentage is undefined.")
    series = []
    revenue_series = dict(p.series_by_period(context.dataset, context.semantic_map,
                                             m.REVENUE) or [])
    cost_series = dict(p.series_by_period(context.dataset, context.semantic_map,
                                          m.COST) or [])
    for period in sorted(revenue_series):
        value = p.as_percent(revenue_series[period] - cost_series.get(period, p.ZERO),
                             revenue_series[period])
        if value is not None:
            series.append((period, value))
    return available(definition, margin,
                     inputs_used={"revenue": revenue, "cost_of_goods": cost},
                     periods=len(series), series=series)


GROSS_MARGIN = define(
    kpi_id="gross_margin", name="Gross margin", category="profitability",
    description="Gross profit as a percentage of revenue.",
    formula="(sum(revenue) - sum(cost_of_goods)) / sum(revenue) * 100",
    inputs=(m.DATE, m.REVENUE, m.COST), unit=PERCENT, aggregation=DERIVED,
    calculator=_calc_gross_margin)


# ===========================================================================
# 5-6. Operating profit and operating margin
# ===========================================================================

def _operating_profit_value(context):
    revenue = p.total(context.dataset, context.semantic_map, m.REVENUE)
    cost = p.total(context.dataset, context.semantic_map, m.COST)
    opex = p.total(context.dataset, context.semantic_map, m.OPERATING_EXPENSE)
    return revenue, cost, opex, (revenue - cost - opex)


def _calc_operating_profit(definition, context):
    blocked = _blocked(definition, context, m.REVENUE, m.COST, m.OPERATING_EXPENSE)
    if blocked:
        return blocked
    revenue, cost, opex, profit = _operating_profit_value(context)
    return available(definition, profit, currency=context.currency,
                     inputs_used={"revenue": revenue, "cost_of_goods": cost,
                                  "operating_expenses": opex})


OPERATING_PROFIT = define(
    kpi_id="operating_profit", name="Operating profit", category="profitability",
    description="Profit after direct costs and operating expenses, before interest and tax.",
    formula="sum(revenue) - sum(cost_of_goods) - sum(operating_expenses)",
    inputs=(m.REVENUE, m.COST, m.OPERATING_EXPENSE), unit=CURRENCY,
    aggregation=DERIVED, calculator=_calc_operating_profit)


def _calc_operating_margin(definition, context):
    blocked = _blocked(definition, context, m.REVENUE, m.COST, m.OPERATING_EXPENSE)
    if blocked:
        return blocked
    revenue, cost, opex, profit = _operating_profit_value(context)
    margin = p.as_percent(profit, revenue)
    if margin is None:
        return unavailable(definition,
                           reason="Revenue is zero, so a margin percentage is undefined.")
    return available(definition, margin,
                     inputs_used={"operating_profit": profit, "revenue": revenue})


OPERATING_MARGIN = define(
    kpi_id="operating_margin", name="Operating margin", category="profitability",
    description="Operating profit as a percentage of revenue.",
    formula="operating_profit / sum(revenue) * 100",
    inputs=(m.REVENUE, m.COST, m.OPERATING_EXPENSE), unit=PERCENT,
    aggregation=DERIVED, calculator=_calc_operating_margin)


# ===========================================================================
# 7-8. EBITDA and EBITDA margin
# ===========================================================================

def _calc_ebitda(definition, context):
    blocked = _blocked(definition, context, m.REVENUE, m.COST, m.OPERATING_EXPENSE, m.DEPRECIATION)
    if blocked:
        return blocked
    _r, _c, _o, operating = _operating_profit_value(context)
    depreciation = p.total(context.dataset, context.semantic_map, m.DEPRECIATION)
    return available(definition, operating + depreciation, currency=context.currency,
                     inputs_used={"operating_profit": operating,
                                  "depreciation_amortisation": depreciation})


EBITDA = define(
    kpi_id="ebitda", name="EBITDA", category="profitability",
    description="Earnings before interest, tax, depreciation and amortisation.",
    formula="operating_profit + sum(depreciation_amortisation)",
    inputs=(m.REVENUE, m.COST, m.OPERATING_EXPENSE, m.DEPRECIATION), unit=CURRENCY,
    aggregation=DERIVED, calculator=_calc_ebitda,
    assumptions=("Interest and tax are assumed to be excluded from operating expenses; "
                 "if they are included, EBITDA will be understated.",))


def _calc_ebitda_margin(definition, context):
    blocked = _blocked(definition, context, m.REVENUE, m.COST, m.OPERATING_EXPENSE, m.DEPRECIATION)
    if blocked:
        return blocked
    _r, _c, _o, operating = _operating_profit_value(context)
    depreciation = p.total(context.dataset, context.semantic_map, m.DEPRECIATION)
    revenue = p.total(context.dataset, context.semantic_map, m.REVENUE)
    margin = p.as_percent(operating + depreciation, revenue)
    if margin is None:
        return unavailable(definition,
                           reason="Revenue is zero, so a margin percentage is undefined.")
    return available(definition, margin,
                     inputs_used={"ebitda": operating + depreciation, "revenue": revenue})


EBITDA_MARGIN = define(
    kpi_id="ebitda_margin", name="EBITDA margin", category="profitability",
    description="EBITDA as a percentage of revenue.",
    formula="ebitda / sum(revenue) * 100",
    inputs=(m.REVENUE, m.COST, m.OPERATING_EXPENSE, m.DEPRECIATION), unit=PERCENT,
    aggregation=DERIVED, calculator=_calc_ebitda_margin)


# ===========================================================================
# 9. Average order value
# ===========================================================================

def _order_count(context):
    """Distinct orders, or row count when no identifier exists. The basis is recorded."""
    identifier = context.semantic_map.column_for(m.ORDER_ID)
    if identifier and context.semantic_map.confirmed(m.ORDER_ID):
        return (len({v for v in context.dataset.column(identifier) if v not in (None, "")}),
                "distinct %s" % identifier)
    return context.dataset.row_count, "row count (no order identifier column)"


def _calc_aov(definition, context):
    blocked = _blocked(definition, context, m.REVENUE)
    if blocked:
        return blocked
    revenue = p.total(context.dataset, context.semantic_map, m.REVENUE)
    orders, basis = _order_count(context)
    value = p.safe_divide(revenue, orders)
    if value is None:
        return unavailable(definition,
                           reason="No orders were found, so an average order value is "
                                  "undefined rather than zero.")
    return available(definition, value, currency=context.currency,
                     inputs_used={"revenue": revenue, "orders": orders,
                                  "order_basis": basis})


AVERAGE_ORDER_VALUE = define(
    kpi_id="average_order_value", name="Average order value", category="revenue",
    description="Average revenue per order.",
    formula="sum(revenue) / count(distinct order_id)",
    inputs=(m.REVENUE,), optional_inputs=(m.ORDER_ID,), unit=CURRENCY,
    aggregation=DERIVED, calculator=_calc_aov,
    applicable_models=tuple(x for x in (
        "retail", "wholesale_distribution", "marketplace", "manufacturing",
        "hospitality", "agency", "professional_services", "nonprofit", "other")),
    not_applicable_reason="Average order value describes discrete orders. A subscription "
                          "business measures recurring revenue per customer instead.",
    calculation_notes="Falls back to row count when no order identifier is mapped; the "
                      "basis used is always recorded.")


# ===========================================================================
# 10. Customer acquisition cost
# ===========================================================================

def _calc_cac(definition, context):
    blocked = _blocked(definition, context, m.MARKETING_SPEND, m.CUSTOMER, m.DATE)
    if blocked:
        return blocked
    spend = p.total(context.dataset, context.semantic_map, m.MARKETING_SPEND)
    per_period = p.distinct_entities_per_period(context.dataset, context.semantic_map,
                                                m.CUSTOMER) or {}
    if len(per_period) < 2:
        return insufficient_data(definition, len(per_period), 2)
    seen, new_customers = set(), 0
    for index, (_period, customers) in enumerate(sorted(per_period.items())):
        if index:
            new_customers += len(customers - seen)
        seen |= customers
    value = p.safe_divide(spend, new_customers)
    if value is None:
        return unavailable(definition,
                           reason="No new customers were acquired in the period, so an "
                                  "acquisition cost is undefined rather than zero.")
    return available(definition, value, currency=context.currency,
                     inputs_used={"marketing_spend": spend,
                                  "new_customers": new_customers})


CUSTOMER_ACQUISITION_COST = define(
    kpi_id="customer_acquisition_cost", name="Customer acquisition cost",
    category="customer",
    description="Average marketing and sales spend to acquire one new customer.",
    formula="sum(marketing_spend) / count(new customers)",
    inputs=(m.MARKETING_SPEND, m.CUSTOMER, m.DATE), unit=CURRENCY,
    aggregation=DERIVED, calculator=_calc_cac, minimum_periods=2,
    assumptions=("A customer is counted as new the first period they appear in the data; "
                 "customers present before the data begins cannot be identified.",))


# ===========================================================================
# 11. Customer lifetime value
# ===========================================================================

def _calc_clv(definition, context):
    blocked = _blocked(definition, context, m.CUSTOMER, m.REVENUE, m.DATE)
    if blocked:
        return blocked
    per_customer = p.revenue_per_entity(context.dataset, context.semantic_map,
                                        m.CUSTOMER) or {}
    if not per_customer:
        return unavailable(definition,
                           reason="No customer revenue could be attributed.")
    period_list = p.periods(context.dataset, context.semantic_map)
    if len(period_list) < 2:
        return insufficient_data(definition, len(period_list), 2)
    average = p.mean(per_customer.values())
    return available(definition, average, currency=context.currency,
                     inputs_used={"customers": len(per_customer),
                                  "periods_observed": len(period_list)},
                     periods=len(period_list),
                     caveats=["Observed revenue per customer over the periods present, "
                              "not a projected lifetime value. BusinessOps does not "
                              "project lifetime value; /revenue-forecast forecasts "
                              "revenue and gross profit only."])


CUSTOMER_LIFETIME_VALUE = define(
    kpi_id="customer_lifetime_value", name="Customer lifetime value",
    category="customer",
    description="Average revenue observed per customer across the period range.",
    formula="sum(revenue) / count(distinct customers)",
    inputs=(m.CUSTOMER, m.REVENUE, m.DATE), unit=CURRENCY, aggregation=DERIVED,
    calculator=_calc_clv, minimum_periods=2,
    calculation_notes="Observed, not projected. A projected CLV needs a retention curve "
                      "and a discount rate, which M5 deliberately does not model.")


# ===========================================================================
# 12-13. Customer retention and churn
# ===========================================================================

def _retention_parts(context):
    per_period = p.distinct_entities_per_period(context.dataset, context.semantic_map,
                                                m.CUSTOMER) or {}
    ordered = sorted(per_period.items())
    if len(ordered) < 2:
        return None, None, len(ordered)
    midpoint = len(ordered) // 2
    earlier = set().union(*[c for _p, c in ordered[:midpoint]])
    later = set().union(*[c for _p, c in ordered[midpoint:]])
    return earlier, later, len(ordered)


def _calc_retention(definition, context):
    blocked = _blocked(definition, context, m.CUSTOMER, m.DATE)
    if blocked:
        return blocked
    earlier, later, count = _retention_parts(context)
    if earlier is None:
        return insufficient_data(definition, count, 2)
    retained = len(earlier & later)
    value = p.as_percent(retained, len(earlier))
    if value is None:
        return unavailable(definition,
                           reason="No customers were active in the earlier period, so a "
                                  "retention rate is undefined.")
    return available(definition, value,
                     inputs_used={"customers_earlier": len(earlier),
                                  "retained": retained},
                     periods=count)


CUSTOMER_RETENTION = define(
    kpi_id="customer_retention", name="Customer retention", category="customer",
    description="Share of earlier-period customers who transacted again later.",
    formula="count(customers in both halves) / count(customers in earlier half) * 100",
    inputs=(m.CUSTOMER, m.DATE), unit=PERCENT, aggregation=PERIOD_OVER_PERIOD,
    calculator=_calc_retention, minimum_periods=2)


def _calc_churn(definition, context):
    blocked = _blocked(definition, context, m.CUSTOMER, m.DATE)
    if blocked:
        return blocked
    earlier, later, count = _retention_parts(context)
    if earlier is None:
        return insufficient_data(definition, count, 2)
    lost = len(earlier - later)
    value = p.as_percent(lost, len(earlier))
    if value is None:
        return unavailable(definition,
                           reason="No customers were active in the earlier period, so a "
                                  "churn rate is undefined.")
    return available(definition, value,
                     inputs_used={"customers_earlier": len(earlier), "lost": lost},
                     periods=count,
                     caveats=["Churn here means a customer stopped transacting in the "
                              "later period. For a transactional business that may be "
                              "ordinary buying rhythm rather than a lost customer."])


CUSTOMER_CHURN = define(
    kpi_id="customer_churn", name="Customer churn", category="customer",
    description="Share of earlier-period customers who did not transact again.",
    formula="count(customers only in earlier half) / count(customers in earlier half) * 100",
    inputs=(m.CUSTOMER, m.DATE), unit=PERCENT, aggregation=PERIOD_OVER_PERIOD,
    calculator=_calc_churn, minimum_periods=2)


# ===========================================================================
# 14. Conversion rate
# ===========================================================================

def _calc_conversion(definition, context):
    blocked = _blocked(definition, context, m.LEAD_COUNT)
    if blocked:
        return blocked
    leads = p.total(context.dataset, context.semantic_map, m.LEAD_COUNT)
    orders, basis = _order_count(context)
    value = p.as_percent(orders, leads)
    if value is None:
        return unavailable(definition,
                           reason="No leads were recorded, so a conversion rate is "
                                  "undefined rather than zero.")
    return available(definition, value,
                     inputs_used={"leads": leads, "orders": orders,
                                  "order_basis": basis})


CONVERSION_RATE = define(
    kpi_id="conversion_rate", name="Conversion rate", category="sales",
    description="Share of leads or visits that became orders.",
    formula="count(orders) / sum(leads) * 100",
    inputs=(m.LEAD_COUNT,), optional_inputs=(m.ORDER_ID,), unit=PERCENT,
    aggregation=DERIVED, calculator=_calc_conversion)


# ===========================================================================
# 15-17. Pipeline value, win rate, average sales cycle
# ===========================================================================

def _calc_pipeline_value(definition, context):
    blocked = _blocked(definition, context, m.PIPELINE_VALUE)
    if blocked:
        return blocked
    value = p.total(context.dataset, context.semantic_map, m.PIPELINE_VALUE)
    return available(definition, value, currency=context.currency,
                     inputs_used={"pipeline_column": context.column(m.PIPELINE_VALUE)})


SALES_PIPELINE_VALUE = define(
    kpi_id="sales_pipeline_value", name="Sales pipeline value", category="sales",
    description="Total value of open opportunities.",
    formula="sum(pipeline_value)", inputs=(m.PIPELINE_VALUE,), unit=CURRENCY,
    aggregation=SUM, calculator=_calc_pipeline_value)


_WON = ("won", "closed won", "closed-won", "win", "successful")
_LOST = ("lost", "closed lost", "closed-lost", "loss", "unsuccessful")


def _calc_win_rate(definition, context):
    blocked = _blocked(definition, context, m.DEAL_STAGE)
    if blocked:
        return blocked
    column = context.semantic_map.column_for(m.DEAL_STAGE)
    stages = [str(v).strip().lower() for v in context.dataset.column(column)
              if v not in (None, "")]
    won = sum(1 for s in stages if s in _WON)
    lost = sum(1 for s in stages if s in _LOST)
    decided = won + lost
    value = p.as_percent(won, decided)
    if value is None:
        return unavailable(
            definition,
            reason="No closed opportunities were found, so a win rate is undefined. "
                   "Recognised outcomes are %s." % ", ".join(sorted(set(_WON) | set(_LOST))))
    return available(definition, value,
                     inputs_used={"won": won, "lost": lost, "decided": decided})


WIN_RATE = define(
    kpi_id="win_rate", name="Win rate", category="sales",
    description="Share of decided opportunities that were won.",
    formula="count(won) / (count(won) + count(lost)) * 100",
    inputs=(m.DEAL_STAGE,), unit=PERCENT, aggregation=DERIVED,
    calculator=_calc_win_rate,
    calculation_notes="Open opportunities are excluded from the denominator; only decided "
                      "outcomes count.")


def _calc_sales_cycle(definition, context):
    blocked = _blocked(definition, context, m.DEAL_OPENED, m.DEAL_CLOSED)
    if blocked:
        return blocked
    opened_column = context.semantic_map.column_for(m.DEAL_OPENED)
    closed_column = context.semantic_map.column_for(m.DEAL_CLOSED)
    import datetime as _dt
    durations = []
    for row in context.dataset.rows:
        opened, closed = row.get(opened_column), row.get(closed_column)
        if isinstance(opened, _dt.datetime):
            opened = opened.date()
        if isinstance(closed, _dt.datetime):
            closed = closed.date()
        if isinstance(opened, _dt.date) and isinstance(closed, _dt.date):
            days = (closed - opened).days
            if days >= 0:
                durations.append(Decimal(days))
    if not durations:
        return unavailable(
            definition,
            reason="No opportunity had both a valid opened and closed date, so an average "
                   "cycle length cannot be measured.")
    return available(definition, p.mean(durations),
                     inputs_used={"opportunities": len(durations)})


AVERAGE_SALES_CYCLE = define(
    kpi_id="average_sales_cycle", name="Average sales cycle", category="sales",
    description="Average days from opportunity opened to closed.",
    formula="mean(closed_date - opened_date) in days",
    inputs=(m.DEAL_OPENED, m.DEAL_CLOSED), unit=DAYS, aggregation=DERIVED,
    calculator=_calc_sales_cycle,
    calculation_notes="Negative durations are excluded as data errors rather than "
                      "averaged in.")


# ===========================================================================
# 18-20. Recurring revenue, MRR, ARR
# ===========================================================================

def _recurring_total(context):
    return p.total(context.dataset, context.semantic_map, m.RECURRING_REVENUE)


def _calc_recurring_revenue(definition, context):
    blocked = _blocked(definition, context, m.RECURRING_REVENUE)
    if blocked:
        return blocked
    return available(definition, _recurring_total(context), currency=context.currency,
                     inputs_used={"recurring_column": context.column(m.RECURRING_REVENUE)})


RECURRING_REVENUE = define(
    kpi_id="recurring_revenue", name="Recurring revenue", category="revenue",
    description="Total contracted recurring revenue in the period.",
    formula="sum(recurring_revenue)", inputs=(m.RECURRING_REVENUE,), unit=CURRENCY,
    aggregation=SUM, calculator=_calc_recurring_revenue,
    applicable_models=_RECURRING_MODELS,
    not_applicable_reason="Recurring revenue measures subscription or contracted income. "
                          "A transactional business has none by definition.")


def _calc_mrr(definition, context):
    blocked = _blocked(definition, context, m.RECURRING_REVENUE, m.DATE)
    if blocked:
        return blocked
    series = p.series_by_period(context.dataset, context.semantic_map,
                                m.RECURRING_REVENUE) or []
    if not series:
        return unavailable(definition,
                           reason="No recurring revenue could be attributed to a period.")
    latest_period, latest_value = series[-1]
    return available(definition, latest_value, currency=context.currency,
                     inputs_used={"period": latest_period}, periods=len(series),
                     series=series)


MONTHLY_RECURRING_REVENUE = define(
    kpi_id="mrr", name="Monthly recurring revenue (MRR)", category="revenue",
    description="Recurring revenue in the most recent month.",
    formula="sum(recurring_revenue) for the latest month",
    inputs=(m.RECURRING_REVENUE, m.DATE), unit=CURRENCY, aggregation=POINT_IN_TIME,
    calculator=_calc_mrr, applicable_models=_RECURRING_MODELS,
    not_applicable_reason="MRR measures subscription revenue. A transactional business "
                          "has none by definition.")


def _calc_arr(definition, context):
    result = _calc_mrr(definition, context)
    if not result.available:
        return result
    return available(definition, result.value * Decimal("12"), currency=context.currency,
                     inputs_used=dict(result.inputs_used, mrr=result.value),
                     periods=result.periods,
                     assumptions=("Annualised as the latest month multiplied by twelve; "
                                  "it assumes the current run rate persists.",))


ANNUAL_RECURRING_REVENUE = define(
    kpi_id="arr", name="Annual recurring revenue (ARR)", category="revenue",
    description="Annualised run rate from the latest month's recurring revenue.",
    formula="mrr * 12", inputs=(m.RECURRING_REVENUE, m.DATE), unit=CURRENCY,
    aggregation=POINT_IN_TIME, calculator=_calc_arr,
    applicable_models=_RECURRING_MODELS,
    not_applicable_reason="ARR measures subscription revenue. A transactional business "
                          "has none by definition.")


# ===========================================================================
# 21-22. Burn rate and runway
# ===========================================================================

def _monthly_net_cash(context):
    """Net cash movement per month, from revenue less all recorded costs."""
    revenue = dict(p.series_by_period(context.dataset, context.semantic_map,
                                      m.REVENUE) or [])
    cost = dict(p.series_by_period(context.dataset, context.semantic_map, m.COST) or [])
    opex = dict(p.series_by_period(context.dataset, context.semantic_map,
                                   m.OPERATING_EXPENSE) or [])
    return [(period, revenue[period] - cost.get(period, p.ZERO) - opex.get(period, p.ZERO))
            for period in sorted(revenue)]


def _calc_burn_rate(definition, context):
    blocked = _blocked(definition, context, m.DATE, m.REVENUE, m.COST, m.OPERATING_EXPENSE)
    if blocked:
        return blocked
    net = _monthly_net_cash(context)
    if len(net) < definition.minimum_periods:
        return insufficient_data(definition, len(net), definition.minimum_periods)
    average = p.mean([value for _period, value in net])
    burn = -average
    if burn <= 0:
        return available(definition, Decimal("0"), currency=context.currency,
                         inputs_used={"average_monthly_net": average},
                         periods=len(net),
                         caveats=["The business was cash-generative on average over these "
                                  "periods, so there is no burn."])
    return available(definition, burn, currency=context.currency,
                     inputs_used={"average_monthly_net": average}, periods=len(net))


BURN_RATE = define(
    kpi_id="burn_rate", name="Burn rate", category="cash",
    description="Average monthly net cash consumed.",
    formula="-mean(monthly revenue - monthly cost - monthly operating expenses)",
    inputs=(m.DATE, m.REVENUE, m.COST, m.OPERATING_EXPENSE), unit=CURRENCY,
    aggregation=DERIVED, calculator=_calc_burn_rate, minimum_periods=2,
    calculation_notes="Zero when the business is cash-generative; never negative.")


def _calc_runway(definition, context):
    blocked = _blocked(definition, context, m.CASH_BALANCE, m.DATE, m.REVENUE, m.COST,
                       m.OPERATING_EXPENSE)
    if blocked:
        return blocked
    burn = _calc_burn_rate(BURN_RATE, context)
    if not burn.available:
        return unavailable(definition,
                           reason="Runway needs a burn rate, which is unavailable: %s"
                                  % burn.reason)
    cash = p.latest(context.dataset, context.semantic_map, m.CASH_BALANCE)
    if burn.value == 0:
        # There is no finite number to report, and a blank cell in a scorecard would read
        # as a defect. `unavailable` with a reason that says why is the honest fit: the
        # data is fine, the quantity simply is not bounded.
        return unavailable(
            definition,
            reason="The business was cash-generative over these periods, so runway is not "
                   "limited by burn. There is no finite number of months to report.",
            inputs_used={"cash": cash, "burn_rate": burn.value})
    months = p.safe_divide(cash, burn.value)
    if months is None:
        return unavailable(definition, reason="Burn rate is zero, so runway is unbounded.")
    return available(definition, months,
                     inputs_used={"cash": cash, "burn_rate": burn.value})


RUNWAY = define(
    kpi_id="runway", name="Runway", category="cash",
    description="Months of operation the current cash balance supports at the current burn.",
    formula="latest(cash_balance) / burn_rate",
    inputs=(m.CASH_BALANCE, m.DATE, m.REVENUE, m.COST, m.OPERATING_EXPENSE),
    unit=COUNT, aggregation=DERIVED, calculator=_calc_runway, minimum_periods=2,
    result_semantics="A number of months. Not limited by burn when the business is "
                     "cash-generative.")


# ===========================================================================
# 23. Working capital
# ===========================================================================

def _calc_working_capital(definition, context):
    blocked = _blocked(definition, context, m.CURRENT_ASSETS, m.CURRENT_LIABILITIES)
    if blocked:
        return blocked
    assets = p.latest(context.dataset, context.semantic_map, m.CURRENT_ASSETS)
    liabilities = p.latest(context.dataset, context.semantic_map, m.CURRENT_LIABILITIES)
    return available(definition, assets - liabilities, currency=context.currency,
                     inputs_used={"current_assets": assets,
                                  "current_liabilities": liabilities})


WORKING_CAPITAL = define(
    kpi_id="working_capital", name="Working capital", category="finance",
    description="Current assets less current liabilities.",
    formula="latest(current_assets) - latest(current_liabilities)",
    inputs=(m.CURRENT_ASSETS, m.CURRENT_LIABILITIES), unit=CURRENCY,
    aggregation=POINT_IN_TIME, calculator=_calc_working_capital)


# ===========================================================================
# 24-25. DSO and DPO
# ===========================================================================

def _days_outstanding(definition, context, balance_role, flow_role, flow_label):
    blocked = _blocked(definition, context, balance_role, flow_role, m.DATE)
    if blocked:
        return blocked
    balance = p.latest(context.dataset, context.semantic_map, balance_role)
    flow = p.total(context.dataset, context.semantic_map, flow_role)
    period_list = p.periods(context.dataset, context.semantic_map)
    if not period_list:
        return unavailable(definition,
                           reason="No periods could be identified from the date column.")
    days = Decimal(30 * len(period_list))
    value = p.safe_divide(balance * days, flow)
    if value is None:
        return unavailable(definition,
                           reason="%s is zero, so a days-outstanding figure is undefined."
                                  % flow_label)
    return available(definition, value,
                     inputs_used={"balance": balance, flow_label.lower(): flow,
                                  "days_in_range": int(days)},
                     periods=len(period_list),
                     assumptions=("Each period is treated as 30 days; a precise figure "
                                  "needs exact period boundaries.",))


def _calc_dso(definition, context):
    return _days_outstanding(definition, context, m.RECEIVABLES, m.REVENUE, "Revenue")


DAYS_SALES_OUTSTANDING = define(
    kpi_id="days_sales_outstanding", name="Days sales outstanding (DSO)",
    category="finance",
    description="Average days to collect payment after a sale.",
    formula="latest(receivables) / sum(revenue) * days_in_range",
    inputs=(m.RECEIVABLES, m.REVENUE, m.DATE), unit=DAYS, aggregation=DERIVED,
    calculator=_calc_dso)


def _calc_dpo(definition, context):
    return _days_outstanding(definition, context, m.PAYABLES, m.COST, "Cost of goods")


DAYS_PAYABLE_OUTSTANDING = define(
    kpi_id="days_payable_outstanding", name="Days payable outstanding (DPO)",
    category="finance",
    description="Average days taken to pay suppliers.",
    formula="latest(payables) / sum(cost_of_goods) * days_in_range",
    inputs=(m.PAYABLES, m.COST, m.DATE), unit=DAYS, aggregation=DERIVED,
    calculator=_calc_dpo)


# ===========================================================================
# 26. Inventory turnover
# ===========================================================================

def _calc_inventory_turnover(definition, context):
    blocked = _blocked(definition, context, m.COST, m.INVENTORY_VALUE)
    if blocked:
        return blocked
    cost = p.total(context.dataset, context.semantic_map, m.COST)
    inventory_values = p.numeric_values(context.dataset, context.semantic_map,
                                        m.INVENTORY_VALUE) or []
    average_inventory = p.mean(inventory_values)
    value = p.safe_divide(cost, average_inventory)
    if value is None:
        return unavailable(definition,
                           reason="Average inventory value is zero, so turnover is "
                                  "undefined rather than infinite.")
    return available(definition, value,
                     inputs_used={"cost_of_goods": cost,
                                  "average_inventory": average_inventory})


INVENTORY_TURNOVER = define(
    kpi_id="inventory_turnover", name="Inventory turnover", category="operations",
    description="How many times inventory was sold and replaced in the period.",
    formula="sum(cost_of_goods) / mean(inventory_value)",
    inputs=(m.COST, m.INVENTORY_VALUE), unit=RATIO, aggregation=DERIVED,
    calculator=_calc_inventory_turnover, applicable_models=_INVENTORY_MODELS,
    not_applicable_reason="Inventory turnover measures physical stock. A business that "
                          "holds no inventory has nothing to turn over.")


# ===========================================================================
# 27. Return on investment
# ===========================================================================

def _calc_roi(definition, context):
    blocked = _blocked(definition, context, m.INVESTMENT, m.REVENUE, m.COST)
    if blocked:
        return blocked
    investment = p.total(context.dataset, context.semantic_map, m.INVESTMENT)
    revenue = p.total(context.dataset, context.semantic_map, m.REVENUE)
    cost = p.total(context.dataset, context.semantic_map, m.COST)
    gain = revenue - cost - investment
    value = p.as_percent(gain, investment)
    if value is None:
        return unavailable(definition,
                           reason="Investment is zero, so a return on it is undefined.")
    return available(definition, value,
                     inputs_used={"gain": gain, "investment": investment})


RETURN_ON_INVESTMENT = define(
    kpi_id="return_on_investment", name="Return on investment (ROI)",
    category="finance",
    description="Net gain as a percentage of the investment that produced it.",
    formula="(sum(revenue) - sum(cost_of_goods) - sum(investment)) / sum(investment) * 100",
    inputs=(m.INVESTMENT, m.REVENUE, m.COST), unit=PERCENT, aggregation=DERIVED,
    calculator=_calc_roi)


# ===========================================================================
# Beyond the approved 27: retained from Milestone 2
# ===========================================================================

def _calc_nrr(definition, context):
    blocked = _blocked(definition, context, m.DATE, m.REVENUE, m.CUSTOMER)
    if blocked:
        return blocked
    per_period = p.distinct_entities_per_period(context.dataset, context.semantic_map,
                                                m.CUSTOMER) or {}
    ordered = sorted(per_period.items())
    if len(ordered) < 2:
        return insufficient_data(definition, len(ordered), 2)
    midpoint = len(ordered) // 2
    earlier_customers = set().union(*[c for _p, c in ordered[:midpoint]])
    revenue_column = context.semantic_map.column_for(m.REVENUE)
    date_column = context.semantic_map.column_for(m.DATE)
    earlier_periods = {period for period, _c in ordered[:midpoint]}

    base, retained = p.ZERO, p.ZERO
    for row in context.dataset.rows:
        customer = row.get(context.semantic_map.column_for(m.CUSTOMER))
        value = row.get(revenue_column)
        period = p.period_key(row.get(date_column))
        if customer not in earlier_customers or not p.is_number(value):
            continue
        if period in earlier_periods:
            base += p.dec(value)
        else:
            retained += p.dec(value)
    value = p.as_percent(retained, base)
    if value is None:
        return unavailable(definition,
                           reason="The earlier cohort produced no revenue, so retention "
                                  "cannot be expressed as a rate.")
    return available(definition, value,
                     inputs_used={"cohort_base_revenue": base,
                                  "cohort_later_revenue": retained},
                     periods=len(ordered))


NET_REVENUE_RETENTION = define(
    kpi_id="net_revenue_retention", name="Net revenue retention (NRR)",
    category="customer",
    description="Revenue from an earlier customer cohort in the later period, relative to "
                "what that cohort produced originally.",
    formula="revenue(earlier cohort, later half) / revenue(earlier cohort, earlier half) * 100",
    inputs=(m.DATE, m.REVENUE, m.CUSTOMER), unit=PERCENT,
    aggregation=PERIOD_OVER_PERIOD, calculator=_calc_nrr,
    applicable_models=_RECURRING_MODELS, minimum_periods=2,
    not_applicable_reason="Net revenue retention measures recurring subscription revenue. "
                          "It is not meaningful for a transactional business model.",
    calculation_notes="Not part of the approved 27; introduced in Milestone 2 to "
                      "demonstrate the not_applicable bucket and retained for continuity.")


# ===========================================================================

BY_ID = {definition.kpi_id: definition for definition in CATALOGUE}

# The approved 27, in specification order.
APPROVED_27 = (
    "revenue", "revenue_growth", "gross_profit", "gross_margin",
    "operating_profit", "operating_margin", "ebitda", "ebitda_margin",
    "average_order_value", "customer_acquisition_cost", "customer_lifetime_value",
    "customer_retention", "customer_churn", "conversion_rate",
    "sales_pipeline_value", "win_rate", "average_sales_cycle",
    "recurring_revenue", "mrr", "arr", "burn_rate", "runway",
    "working_capital", "days_sales_outstanding", "days_payable_outstanding",
    "inventory_turnover", "return_on_investment",
)

# Retained beyond the approved list, with the reason recorded on the definition.
BEYOND_APPROVED = ("net_revenue_retention",)

ALL_IDS = APPROVED_27 + BEYOND_APPROVED
