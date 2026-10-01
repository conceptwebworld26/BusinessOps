"""Concentration: how much of the whole sits in how few members.

Concentration is the single most decision-relevant shape in small-business data. A firm
with £3m of revenue spread over 200 customers and a firm with £3m over four are not the
same business, and no total, growth rate or margin will tell you which one you are looking
at.

Three measures, all deterministic, none of them a judgement:

  * **Top-N contribution** — what share the largest N members hold.
  * **Concentration ratio (CR-N)** — the same quantity reported across several N, so the
    shape of the curve is visible rather than a single point on it.
  * **Members for half** — how few members it takes to reach 50% of the total.

The Herfindahl-Hirschman index is included because it is the one summary statistic that
does not depend on choosing an N: the sum of squared percentage shares, ranging from near
zero (perfectly dispersed) to 10,000 (a single member). It is reported as a number, never
as a verdict — whether a given level is dangerous is judgement, and belongs to a skill.

Whether a concentration figure is *material* is decided by `bops.materiality`, not here.
There is one materiality system.
"""

from decimal import Decimal

from ..kpi import primitives as p

ZERO = Decimal("0")

DEFAULT_RATIOS = (1, 3, 5, 10)
HALF = Decimal("50")


def top_n(segments, n):
    """The largest `n` members and the share they hold.

    `segments` must already be ordered — `segmentation.order` is the only ordering used —
    so this function never re-sorts and never disagrees with the ranking shown elsewhere.
    """
    members = list(segments)[:max(0, int(n))]
    grand_total = sum((s.total for s in segments), ZERO)
    subtotal = sum((s.total for s in members), ZERO)
    return {
        "n": int(n),
        "members": members,
        "count": len(members),
        "total": subtotal,
        "grand_total": grand_total,
        "share_pct": p.as_percent(subtotal, grand_total),
    }


def cumulative_shares(segments):
    """`[(member, cumulative share %)]` in ranked order — the concentration curve."""
    grand_total = sum((s.total for s in segments), ZERO)
    running, out = ZERO, []
    for item in segments:
        running += item.total
        out.append((item, p.as_percent(running, grand_total)))
    return out


def members_for_share(segments, target_pct=HALF):
    """How few members it takes to reach `target_pct` of the total.

    Returns None when the total is zero or empty: "no members are needed" would be a
    nonsense answer, and zero would read as concentration rather than absence.
    """
    for index, (_item, share) in enumerate(cumulative_shares(segments), start=1):
        if share is None:
            return None
        if share >= target_pct:
            return index
    return None


def hhi(segments):
    """Herfindahl-Hirschman index over percentage shares: 0 (dispersed) to 10,000 (one)."""
    grand_total = sum((s.total for s in segments), ZERO)
    if grand_total == ZERO:
        return None
    total = ZERO
    for item in segments:
        share = p.as_percent(item.total, grand_total)
        if share is None:
            return None
        total += share * share
    return total


def profile(segments, ratios=DEFAULT_RATIOS):
    """Every concentration measure for one ranked dimension, as data not verdicts."""
    segments = list(segments)
    grand_total = sum((s.total for s in segments), ZERO)
    record = {
        "members": len(segments),
        "grand_total": grand_total,
        "cr": {},
        "hhi": hhi(segments),
        "members_for_half": members_for_share(segments, HALF),
        "largest_share_pct": segments[0].share_pct if segments else None,
        "largest_label": segments[0].label if segments else None,
        "largest_redacted": segments[0].redacted if segments else False,
    }
    for n in ratios:
        if n <= 0:
            continue
        summary = top_n(segments, n)
        # CR-N is only meaningful when there are at least N members to concentrate.
        record["cr"][n] = summary["share_pct"] if len(segments) >= n else None
    return record


def judge_share(subject, amount, total, config, materiality_mod):
    """Whether a member's share of the whole is material. Reuses the one materiality system."""
    return materiality_mod.assess_share_of_revenue(subject, amount, total, config)
