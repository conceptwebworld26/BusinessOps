"""Cohorts: group entities by when they first appear, then follow them.

One cohort definition, stated plainly and not negotiable: **an entity's cohort is the first
period in which it appears in this dataset.** Everything downstream — retention by offset,
revenue by offset — follows from that single rule, so there is no second definition to
disagree with.

The definition carries a limitation that must travel with every cohort figure: a customer
who was trading before the file begins is indistinguishable from a genuinely new one, so
the earliest cohort is inflated and its retention is understated relative to later ones.
That is a property of the data window, not a defect, and the honest response is to say so
rather than to quietly drop the first cohort.

Cohort analysis needs history. Below the configured minimum the result is
`insufficient_data` with the counts, never a one-period table that looks like an answer.
"""

from decimal import Decimal

from .. import mapping as mapping_mod
from ..kpi import primitives as p
from . import contract

ZERO = Decimal("0")

DEFAULT_MINIMUM_PERIODS = 3

WINDOW_ASSUMPTION = (
    "A customer's cohort is the first period they appear in this dataset. Anyone trading "
    "before the file begins is counted as new in the first period, so the earliest cohort "
    "is overstated and its retention understated."
)


def _revenue_by_entity_period(dataset, semantic_map):
    date_column = semantic_map.column_for(mapping_mod.DATE)
    entity_column = semantic_map.column_for(mapping_mod.CUSTOMER)
    revenue_column = semantic_map.column_for(mapping_mod.REVENUE)
    if not (date_column and entity_column and revenue_column):
        return None
    totals = {}
    for row in dataset.rows:
        period = p.period_key(row.get(date_column))
        entity = row.get(entity_column)
        value = row.get(revenue_column)
        if period is None or entity in (None, "") or not p.is_number(value):
            continue
        totals[(entity, period)] = totals.get((entity, period), ZERO) + p.dec(value)
    return totals


def build(dataset, semantic_map, entity_role=mapping_mod.CUSTOMER,
          minimum_periods=DEFAULT_MINIMUM_PERIODS, policy=None):
    """Acquisition cohorts with retention and revenue by period offset.

    Returns a dict with `status`, and — when available — `cohorts`, `periods` and
    `assumptions`. Entity identities never leave this function: a cohort row carries
    counts, shares and totals, never the members.
    """
    per_period = p.distinct_entities_per_period(dataset, semantic_map, entity_role)
    if per_period is None:
        return {"status": contract.UNAVAILABLE,
                "reason": "Cohort analysis needs a date column and a customer column; "
                          "at least one is not mapped.",
                "cohorts": [], "periods": []}

    periods = sorted(per_period)
    if len(periods) < minimum_periods:
        return {"status": contract.INSUFFICIENT_DATA,
                "reason": ("Cohort analysis needs at least %d periods to show retention "
                           "beyond acquisition; %d %s present."
                           % (minimum_periods, len(periods),
                              "is" if len(periods) == 1 else "are")),
                "cohorts": [], "periods": periods}

    # First appearance defines the cohort. One rule, applied once.
    first_seen = {}
    for period in periods:
        for entity in per_period[period]:
            if entity not in first_seen:
                first_seen[entity] = period

    members = {}
    for entity, period in first_seen.items():
        members.setdefault(period, set()).add(entity)

    revenue = _revenue_by_entity_period(dataset, semantic_map)

    cohorts = []
    for cohort_period in periods:
        cohort_members = members.get(cohort_period)
        if not cohort_members:
            continue
        size = len(cohort_members)
        entries = []
        for offset, period in enumerate(periods[periods.index(cohort_period):]):
            active = len(cohort_members & per_period.get(period, set()))
            entry = {"period": period, "offset": offset, "active": active,
                     "retention_pct": p.as_percent(active, size)}
            if revenue is not None:
                entry["revenue"] = sum(
                    (revenue.get((entity, period), ZERO) for entity in cohort_members),
                    ZERO)
            entries.append(entry)
        cohorts.append({"cohort": cohort_period, "size": size, "entries": entries})

    return {"status": contract.AVAILABLE, "reason": None, "periods": periods,
            "cohorts": cohorts, "assumptions": [WINDOW_ASSUMPTION]}


def retention_curve(result):
    """Mean retention by offset across cohorts, ignoring offsets no cohort has reached.

    Averaging across cohorts of different ages would compare an offset only the oldest
    cohort can reach against one every cohort has; each offset is therefore averaged only
    over the cohorts that actually observed it, and the count is reported alongside.
    """
    if result.get("status") != contract.AVAILABLE:
        return []
    by_offset = {}
    for cohort in result["cohorts"]:
        for entry in cohort["entries"]:
            if entry["retention_pct"] is None:
                continue
            by_offset.setdefault(entry["offset"], []).append(entry["retention_pct"])
    return [{"offset": offset,
             "cohorts": len(values),
             "mean_retention_pct": p.mean(values)}
            for offset, values in sorted(by_offset.items())]


def cohort_sizes(result):
    """`[(cohort period, size)]` — how many entities each cohort brought in."""
    if result.get("status") != contract.AVAILABLE:
        return []
    return [(c["cohort"], c["size"]) for c in result["cohorts"]]
