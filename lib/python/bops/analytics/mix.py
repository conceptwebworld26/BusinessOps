"""Mix: the composition of a total, and how that composition moved.

A total can be flat while everything underneath it changes. Mix analysis is what makes that
visible — and it is the honest way to talk about a margin movement without asserting a
cause: "the low-margin line grew from 18% to 31% of revenue" is a fact, whereas "margin
fell because of the mix shift" is a claim the arithmetic does not support.

Mix shift is measured in **percentage points**, never as a percentage change of a
percentage. A share moving from 10% to 12% moved two points; calling that "20% growth"
invites exactly the confusion the output standards forbid.

Contribution to change apportions a *net* movement across its members. When the net
movement is zero the apportionment is undefined and reported as such, rather than dividing
by zero or silently returning shares that sum to nothing.
"""

from decimal import Decimal

from ..kpi import primitives as p
from . import presentation as presentation_mod

ZERO = Decimal("0")


def _policy(policy):
    return policy if policy is not None else presentation_mod.LabelPolicy()


def shares(totals):
    """`{key: share %}` for one window. None where the total is zero."""
    grand_total = sum(totals.values(), ZERO)
    return {key: p.as_percent(value, grand_total) for key, value in totals.items()}


class MixShift:
    """One member's change of share between two windows, in percentage points."""

    __slots__ = ("key", "label", "redacted", "earlier", "later", "earlier_share",
                 "later_share", "points_change", "direction", "dimension")

    def __init__(self, key, earlier, later, earlier_share, later_share, dimension=None):
        self.key = key
        self.label = str(key)
        self.redacted = False
        self.earlier = earlier
        self.later = later
        self.earlier_share = earlier_share
        self.later_share = later_share
        if earlier_share is None or later_share is None:
            self.points_change = None
            self.direction = None
        else:
            self.points_change = later_share - earlier_share
            self.direction = ("gaining" if self.points_change > ZERO
                              else "losing" if self.points_change < ZERO else "flat")
        self.dimension = dimension

    def as_dict(self):
        record = {"label": self.label,
                  "earlier": str(self.earlier), "later": str(self.later),
                  "earlier_share_pct": (str(self.earlier_share)
                                        if self.earlier_share is not None else None),
                  "later_share_pct": (str(self.later_share)
                                      if self.later_share is not None else None),
                  "points_change": (str(self.points_change)
                                    if self.points_change is not None else None),
                  "direction": self.direction}
        if self.redacted:
            record["redacted"] = True
        else:
            record["key"] = self.key
        if self.dimension:
            record["dimension"] = self.dimension
        return {k: v for k, v in record.items() if v is not None}

    def __repr__(self):
        return "MixShift(%s %s)" % (self.label, self.points_change)


def mix_shift(earlier_totals, later_totals, policy=None, column=None, dimension_role=None):
    """Every member's share in both windows and the points it moved.

    Ordered by the size of the shift regardless of direction, so the largest structural
    change appears first whether it is a gain or a loss; ties break on the key.
    """
    policy = _policy(policy)
    earlier_shares = shares(earlier_totals)
    later_shares = shares(later_totals)

    rows = []
    for key in set(earlier_totals) | set(later_totals):
        rows.append(MixShift(key,
                             earlier_totals.get(key, ZERO), later_totals.get(key, ZERO),
                             earlier_shares.get(key), later_shares.get(key),
                             dimension=dimension_role))
    rows.sort(key=lambda r: (-(r.points_change.copy_abs()
                               if r.points_change is not None else ZERO), str(r.key)))
    for index, item in enumerate(rows, start=1):
        item.label, item.redacted = policy.label(
            column, item.key, role=dimension_role, rank=index)
    return rows


def contribution_to_change(earlier_totals, later_totals, policy=None, column=None,
                           dimension_role=None):
    """Apportion the net movement of a total across its members.

    Returns `(rows, net_change)`. Each row's `share_of_change_pct` is `None` when the net
    change is zero: members can move a great deal while netting out, and reporting a share
    of nothing would be arithmetic theatre.
    """
    policy = _policy(policy)
    keys = set(earlier_totals) | set(later_totals)
    net_change = (sum(later_totals.values(), ZERO) - sum(earlier_totals.values(), ZERO))

    rows = []
    for key in keys:
        earlier = earlier_totals.get(key, ZERO)
        later = later_totals.get(key, ZERO)
        change = later - earlier
        rows.append({"key": key, "label": str(key), "redacted": False,
                     "earlier": earlier, "later": later, "change": change,
                     "share_of_change_pct": (p.as_percent(change, net_change)
                                             if net_change != ZERO else None),
                     "dimension": dimension_role})
    rows.sort(key=lambda r: (-r["change"], str(r["key"])))
    for index, item in enumerate(rows, start=1):
        item["label"], item["redacted"] = policy.label(
            column, item["key"], role=dimension_role, rank=index)
        if item["redacted"]:
            item.pop("key")
    return rows, net_change


def mix_series(by_period):
    """`{period: {key: share %}}` — composition over time, for a chart-ready consumer."""
    return {period: shares(totals) for period, totals in sorted(by_period.items())}
