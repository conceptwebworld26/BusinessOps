"""Segmentation: deterministic grouping, ranking and per-segment movement.

The whole analytics layer rests on this module. A region comparison, a product ranking, a
customer concentration figure and a salesperson league table are the same operation applied
to a different column, so they are the same code — which is why they can never disagree.

Two properties matter more than anything else here:

  * **Determinism.** Ordering is always `(-total, key)`, never dictionary order. Two runs
    over the same data produce the same list, in the same order, with the same ranks.
  * **Tie handling is explicit.** Equal totals share a rank (1, 2, 2, 4), and the tie is
    broken for *display* by the key, so the output is stable without pretending the two
    values differ.

Money stays `Decimal` and unrounded. Rounding happens once, at presentation.
"""

from decimal import Decimal

from .. import mapping as mapping_mod
from ..kpi import primitives as p
from . import presentation as presentation_mod

ZERO = Decimal("0")

ASCENDING = "ascending"
DESCENDING = "descending"


class Segment:
    """One member of a dimension, with its total and its share of the whole."""

    __slots__ = ("key", "label", "redacted", "total", "share_pct", "rows",
                 "entities", "rank", "dimension")

    def __init__(self, key, label, total, share_pct=None, rows=0, entities=None,
                 redacted=False, dimension=None):
        self.key = key
        self.label = label
        self.redacted = redacted
        self.total = total
        self.share_pct = share_pct
        self.rows = rows
        self.entities = entities
        self.rank = None
        self.dimension = dimension

    def as_dict(self):
        record = {"label": self.label, "total": str(self.total),
                  "rows": self.rows, "rank": self.rank}
        if self.share_pct is not None:
            record["share_pct"] = str(self.share_pct)
        if self.redacted:
            record["redacted"] = True
        else:
            record["key"] = self.key
        if self.entities is not None:
            record["entities"] = self.entities
        if self.dimension:
            record["dimension"] = self.dimension
        return record

    def __repr__(self):
        return "Segment(%s=%s)" % (self.label, self.total)


def _policy(policy):
    return policy if policy is not None else presentation_mod.LabelPolicy()


def order(segments, direction=DESCENDING):
    """The one ordering rule: by total, ties broken by key. Never dictionary order."""
    sign = -1 if direction == DESCENDING else 1
    return sorted(segments, key=lambda s: (sign * s.total, str(s.key)))


def assign_ranks(segments):
    """Competition ranking — equal totals share a rank, and the next rank skips."""
    previous_total, previous_rank = None, 0
    for index, segment in enumerate(segments, start=1):
        if previous_total is not None and segment.total == previous_total:
            segment.rank = previous_rank
        else:
            segment.rank = index
            previous_rank = index
            previous_total = segment.total
    return segments


def segment(dataset, semantic_map, dimension_role, value_role=mapping_mod.REVENUE,
            policy=None, entity_role=None, direction=DESCENDING):
    """Total `value_role` grouped by `dimension_role`, ranked, with each member's share.

    Returns `[]` when either column is unmapped — an unmapped dimension is a limitation for
    the caller to report, not an empty analysis pretending to be a complete one.
    """
    policy = _policy(policy)
    key_column = semantic_map.column_for(dimension_role)
    value_column = semantic_map.column_for(value_role)
    if not key_column or not value_column:
        return []
    entity_column = (semantic_map.column_for(entity_role) if entity_role else None)

    totals, rows, entities = {}, {}, {}
    for row in dataset.rows:
        key = row.get(key_column)
        value = row.get(value_column)
        if key in (None, "") or not p.is_number(value):
            continue
        totals[key] = totals.get(key, ZERO) + p.dec(value)
        rows[key] = rows.get(key, 0) + 1
        if entity_column:
            entity = row.get(entity_column)
            if entity not in (None, ""):
                entities.setdefault(key, set()).add(entity)

    grand_total = sum(totals.values(), ZERO)
    segments = [Segment(key, str(key), total,
                        share_pct=p.as_percent(total, grand_total),
                        rows=rows[key], dimension=dimension_role,
                        entities=(len(entities[key]) if key in entities else None))
                for key, total in totals.items()]
    segments = assign_ranks(order(segments, direction))

    for item in segments:
        item.label, item.redacted = policy.label(
            key_column, item.key, role=dimension_role, rank=item.rank)
    return segments


def total_of(segments):
    return sum((s.total for s in segments), ZERO)


def segment_by_period(dataset, semantic_map, dimension_role,
                      value_role=mapping_mod.REVENUE):
    """`{period: {key: total}}` — the basis for mix shift and per-segment trends."""
    date_column = semantic_map.column_for(mapping_mod.DATE)
    key_column = semantic_map.column_for(dimension_role)
    value_column = semantic_map.column_for(value_role)
    if not (date_column and key_column and value_column):
        return {}

    buckets = {}
    for row in dataset.rows:
        period = p.period_key(row.get(date_column))
        key = row.get(key_column)
        value = row.get(value_column)
        if period is None or key in (None, "") or not p.is_number(value):
            continue
        buckets.setdefault(period, {})
        buckets[period][key] = buckets[period].get(key, ZERO) + p.dec(value)
    return dict(sorted(buckets.items()))


def halves(by_period):
    """Split `{period: {...}}` into earlier and later period lists, half over half.

    Half-over-half rather than last-versus-first, matching the KPI engine: one unusual
    month should not define a trend. Returns `(earlier_periods, later_periods)`.
    """
    periods = sorted(by_period)
    if len(periods) < 2:
        return [], []
    midpoint = len(periods) // 2
    return periods[:midpoint], periods[midpoint:]


def collapse(by_period, period_list):
    """Sum `{period: {key: total}}` over the named periods."""
    totals = {}
    for period in period_list:
        for key, value in (by_period.get(period) or {}).items():
            totals[key] = totals.get(key, ZERO) + value
    return totals


class Movement:
    """One dimension member's change between two comparable windows."""

    __slots__ = ("key", "label", "redacted", "earlier", "later", "change", "change_pct",
                 "direction", "materiality", "materiality_reason", "dimension")

    def __init__(self, key, label, earlier, later, redacted=False, dimension=None):
        self.key = key
        self.label = label
        self.redacted = redacted
        self.earlier = earlier
        self.later = later
        self.change = later - earlier
        self.change_pct = p.as_percent(self.change, earlier) if earlier else None
        self.direction = ("increase" if self.change > ZERO
                          else "decrease" if self.change < ZERO else "flat")
        self.materiality = None
        self.materiality_reason = None
        self.dimension = dimension

    def as_dict(self):
        record = {"label": self.label, "earlier": str(self.earlier),
                  "later": str(self.later), "change": str(self.change),
                  "direction": self.direction}
        if self.change_pct is not None:
            record["change_pct"] = str(self.change_pct)
        if self.redacted:
            record["redacted"] = True
        else:
            record["key"] = self.key
        if self.materiality:
            record["materiality"] = self.materiality
            record["materiality_reason"] = self.materiality_reason
        if self.dimension:
            record["dimension"] = self.dimension
        return record

    def __repr__(self):
        return "Movement(%s %s %s)" % (self.label, self.direction, self.change)


def movements(earlier_totals, later_totals, policy=None, column=None, dimension_role=None):
    """Rank every dimension member by its change between two windows.

    A member present in only one window is included with zero on the other side: a product
    that stopped selling is one of the most important things a ranking can show, and
    dropping it because a key is missing would hide it.
    """
    policy = _policy(policy)
    keys = set(earlier_totals) | set(later_totals)
    rows = []
    for key in keys:
        earlier = earlier_totals.get(key, ZERO)
        later = later_totals.get(key, ZERO)
        rows.append(Movement(key, str(key), earlier, later, dimension=dimension_role))
    rows.sort(key=lambda m: (m.change, str(m.key)))
    for index, item in enumerate(rows, start=1):
        item.label, item.redacted = policy.label(
            column, item.key, role=dimension_role, rank=index)
    return rows


def judge_movements(rows, config, subject_prefix, materiality_mod):
    """Attach a materiality verdict to each movement. The verdict comes from M2/M4."""
    for item in rows:
        verdict = materiality_mod.assess_amount(
            "%s %s" % (subject_prefix, item.label), item.later, item.earlier, config)
        item.materiality = verdict.outcome
        item.materiality_reason = verdict.reason
    return rows


def margin_by_dimension(dataset, semantic_map, dimension_role, policy=None):
    """Revenue, cost, gross profit and gross margin per dimension member.

    This **extends** the `gross_margin` KPI rather than restating it: the KPI is the
    whole-business figure, this is the same quantity evaluated per segment. The arithmetic
    is not duplicated — both go through `kpi.primitives.as_percent`.
    """
    policy = _policy(policy)
    key_column = semantic_map.column_for(dimension_role)
    revenue_column = semantic_map.column_for(mapping_mod.REVENUE)
    cost_column = semantic_map.column_for(mapping_mod.COST)
    if not (key_column and revenue_column and cost_column):
        return []

    revenue, cost, rows = {}, {}, {}
    for row in dataset.rows:
        key = row.get(key_column)
        if key in (None, ""):
            continue
        revenue_value = row.get(revenue_column)
        cost_value = row.get(cost_column)
        if not p.is_number(revenue_value) or not p.is_number(cost_value):
            continue
        revenue[key] = revenue.get(key, ZERO) + p.dec(revenue_value)
        cost[key] = cost.get(key, ZERO) + p.dec(cost_value)
        rows[key] = rows.get(key, 0) + 1

    out = []
    for key in revenue:
        gross_profit = revenue[key] - cost[key]
        out.append({"key": key, "label": str(key),
                    "revenue": revenue[key], "cost": cost[key],
                    "gross_profit": gross_profit,
                    "margin_pct": p.as_percent(gross_profit, revenue[key]),
                    "rows": rows[key], "redacted": False})
    out.sort(key=lambda r: (-r["revenue"], str(r["key"])))
    for index, item in enumerate(out, start=1):
        item["label"], item["redacted"] = policy.label(
            key_column, item["key"], role=dimension_role, rank=index)
        if item["redacted"]:
            item.pop("key")
    return out


def first_period_seen(dataset, semantic_map, dimension_role):
    """`{key: first period the member appears in}` — the basis for ramp observations."""
    date_column = semantic_map.column_for(mapping_mod.DATE)
    key_column = semantic_map.column_for(dimension_role)
    if not (date_column and key_column):
        return {}
    first = {}
    for row in dataset.rows:
        period = p.period_key(row.get(date_column))
        key = row.get(key_column)
        if period is None or key in (None, ""):
            continue
        if key not in first or period < first[key]:
            first[key] = period
    return dict(sorted(first.items(), key=lambda kv: (kv[1], str(kv[0]))))


def entity_count_per_period(dataset, semantic_map, entity_role):
    """`{period: count of distinct entities}` — counts only, never the entities."""
    per_period = p.distinct_entities_per_period(dataset, semantic_map, entity_role)
    if per_period is None:
        return None
    return {period: len(entities) for period, entities in per_period.items()}


def margin_by_period(dataset, semantic_map):
    """`[(period, gross margin %)]` at full precision.

    This is the `gross_margin` KPI evaluated per period rather than once over the whole
    range — an extension of the metric, not a second definition of it, which is why the
    division goes through `kpi.primitives.as_percent` like every other margin in the system.
    Periods with zero revenue are omitted: an undefined margin is not a zero one.
    """
    revenue = dict(p.series_by_period(dataset, semantic_map, mapping_mod.REVENUE) or [])
    cost = dict(p.series_by_period(dataset, semantic_map, mapping_mod.COST) or [])
    if not revenue or not cost:
        return []
    out = []
    for period in sorted(revenue):
        margin = p.as_percent(revenue[period] - cost.get(period, ZERO), revenue[period])
        if margin is not None:
            out.append((period, margin))
    return out


def series_halves(series):
    """Split an ordered `[(period, value)]` series and return the mean of each half."""
    if len(series) < 4:
        return None, None
    midpoint = len(series) // 2
    earlier = p.mean([v for _period, v in series[:midpoint]])
    later = p.mean([v for _period, v in series[midpoint:]])
    return earlier, later
