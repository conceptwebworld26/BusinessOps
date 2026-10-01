"""Shared deterministic primitives for KPI calculation.

Every arithmetic operation a KPI performs goes through this module. That is what keeps
dependent metrics consistent: gross margin cannot disagree with gross profit, because both
call the same `total()` and the same `safe_divide()`.

Money is `Decimal` end to end. Binary floating point never touches a monetary path, and
rounding happens once — at presentation, in the renderer — never here.
"""

import datetime
from decimal import Decimal, DivisionByZero, InvalidOperation

from .. import mapping as mapping_mod

ZERO = Decimal("0")


def dec(value):
    """Coerce to Decimal without going through binary float."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise TypeError("boolean is not a monetary value")
    return Decimal(str(value))


def is_number(value):
    return (isinstance(value, (int, float, Decimal))
            and not isinstance(value, bool))


def safe_divide(numerator, denominator):
    """Division that returns None rather than raising or inventing zero.

    A zero denominator is a real business situation — no orders, no customers, no revenue —
    and the honest answer is "undefined", not 0.
    """
    try:
        denominator = dec(denominator)
        if denominator == ZERO:
            return None
        return dec(numerator) / denominator
    except (InvalidOperation, DivisionByZero, TypeError, ValueError):
        return None


def as_percent(numerator, denominator):
    """A ratio expressed as a percentage, or None if undefined."""
    quotient = safe_divide(numerator, denominator)
    return None if quotient is None else quotient * Decimal("100")


# ---------------------------------------------------------------------------
# Column access
# ---------------------------------------------------------------------------

def column_values(dataset, semantic_map, role):
    """Every value in the column mapped to `role`, or None if the role is unmapped."""
    column = semantic_map.column_for(role)
    if not column:
        return None
    return dataset.column(column)


def numeric_values(dataset, semantic_map, role):
    values = column_values(dataset, semantic_map, role)
    if values is None:
        return None
    return [dec(v) for v in values if is_number(v)]


def total(dataset, semantic_map, role):
    """Sum a numeric role. Returns None when the role is unmapped."""
    values = numeric_values(dataset, semantic_map, role)
    if values is None:
        return None
    return sum(values, ZERO)


def latest(dataset, semantic_map, role):
    """The last non-empty value of a point-in-time role (a balance, not a flow)."""
    values = numeric_values(dataset, semantic_map, role)
    if not values:
        return None
    return values[-1]


def mean(values):
    values = list(values)
    if not values:
        return None
    return sum(values, ZERO) / Decimal(len(values))


def distinct_count(dataset, semantic_map, role):
    """Distinct non-empty entities in a categorical role."""
    values = column_values(dataset, semantic_map, role)
    if values is None:
        return None
    return len({v for v in values if v not in (None, "")})


# ---------------------------------------------------------------------------
# Periods
# ---------------------------------------------------------------------------

def period_key(value):
    """Calendar month key. The only granularity M5 supports; see the M5 limitations."""
    if isinstance(value, datetime.datetime):
        value = value.date()
    if isinstance(value, datetime.date):
        return "%04d-%02d" % (value.year, value.month)
    return None


def periods(dataset, semantic_map):
    """Ordered distinct periods present in the data."""
    values = column_values(dataset, semantic_map, mapping_mod.DATE)
    if values is None:
        return []
    return sorted({period_key(v) for v in values} - {None})


def series_by_period(dataset, semantic_map, role):
    """Ordered (period, Decimal total) pairs for a numeric role."""
    date_column = semantic_map.column_for(mapping_mod.DATE)
    value_column = semantic_map.column_for(role)
    if not date_column or not value_column:
        return None
    buckets = {}
    for row in dataset.rows:
        key = period_key(row.get(date_column))
        value = row.get(value_column)
        if key is None or not is_number(value):
            continue
        buckets[key] = buckets.get(key, ZERO) + dec(value)
    return sorted(buckets.items())


def split_halves(series):
    """Split an ordered series into earlier and later halves for comparison.

    Half-over-half rather than last-vs-first: a single unusual month should not define a
    trend. Returns (earlier, later) or (None, None) when there is too little history.
    """
    if not series or len(series) < 2:
        return None, None
    midpoint = len(series) // 2
    return series[:midpoint], series[midpoint:]


def sum_series(pairs):
    return sum((value for _period, value in pairs), ZERO)


def distinct_entities_per_period(dataset, semantic_map, entity_role):
    """{period: {entities}} — the basis for retention, churn and new-customer metrics."""
    date_column = semantic_map.column_for(mapping_mod.DATE)
    entity_column = semantic_map.column_for(entity_role)
    if not date_column or not entity_column:
        return None
    buckets = {}
    for row in dataset.rows:
        key = period_key(row.get(date_column))
        entity = row.get(entity_column)
        if key is None or entity in (None, ""):
            continue
        buckets.setdefault(key, set()).add(entity)
    return dict(sorted(buckets.items()))


def revenue_per_entity(dataset, semantic_map, entity_role):
    """{entity: total revenue} — the basis for lifetime-value style metrics."""
    entity_column = semantic_map.column_for(entity_role)
    revenue_column = semantic_map.column_for(mapping_mod.REVENUE)
    if not entity_column or not revenue_column:
        return None
    totals = {}
    for row in dataset.rows:
        entity = row.get(entity_column)
        value = row.get(revenue_column)
        if entity in (None, "") or not is_number(value):
            continue
        totals[entity] = totals.get(entity, ZERO) + dec(value)
    return totals


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------

def resolve_currency(canonical, business_context, config):
    """The single currency every monetary KPI is denominated in.

    Returns (currency, error). An error means monetary metrics must not be produced:
    BusinessOps never converts, so summing across currencies would be meaningless.
    """
    currencies = canonical.currencies() if canonical is not None else []
    if len(currencies) > 1:
        return None, ("The data contains %d currencies (%s). Monetary metrics cannot be "
                      "aggregated across currencies, and BusinessOps does not convert."
                      % (len(currencies), ", ".join(currencies)))

    stated = None
    if business_context is not None:
        stated = business_context.get("reporting.currency")
    if stated and currencies and stated not in currencies:
        return None, ("Business Context states the reporting currency is %s but the data "
                      "is denominated in %s. No exchange rate is applied automatically."
                      % (stated, ", ".join(currencies)))

    if currencies:
        return currencies[0], None
    if stated:
        return stated, None
    if config is not None:
        return config.get("locale.currency", "USD"), None
    return "USD", None
