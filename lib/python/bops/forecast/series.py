"""History preparation: turning a mapped dataset into a series a method may forecast.

Three questions have to be answered before any arithmetic, and none of them may be answered
by assumption:

  1. **What is the series?** Built from `kpi.primitives.series_by_period`, so the forecast
     sums revenue exactly the way every other part of BusinessOps sums revenue.
  2. **What is its frequency?** Calendar-monthly is the only granularity the engine has
     (`kpi.primitives.period_key`), so the answer is either "monthly" or "unsupported" -
     never a guess.
  3. **Is it regular?** A gap month is not a zero month. Silently treating an absent period
     as zero would invent a collapse that never happened, so gaps are detected, reported,
     and - because a method needs evenly spaced points - the series is either refused or
     forecast from the contiguous run that follows the last gap.

The source file is never read here. Everything comes from the canonical dataset and the
semantic map, exactly as the M6 analytics do.
"""

import calendar
from decimal import Decimal

from .. import mapping as mapping_mod
from ..kpi import primitives as p

ZERO = Decimal("0")

MONTHLY = "monthly"
UNSUPPORTED = "unsupported"

#: A forecast needs enough contiguous points to be a shape rather than two dots.
MIN_CONTIGUOUS = 2


def _parse(period):
    """'YYYY-MM' -> (year, month). The only period format the engine produces."""
    try:
        year, month = period.split("-")
        return int(year), int(month)
    except (ValueError, AttributeError):
        return None


def _index(period):
    parsed = _parse(period)
    if parsed is None:
        return None
    year, month = parsed
    return year * 12 + (month - 1)


def step(period, offset):
    """The period `offset` months after `period`, as 'YYYY-MM'."""
    parsed = _parse(period)
    if parsed is None:
        return None
    year, month = parsed
    total = year * 12 + (month - 1) + offset
    return "%04d-%02d" % (total // 12, total % 12 + 1)


def horizon_periods(last_period, horizon):
    """The labels of the periods being forecast."""
    return [step(last_period, h) for h in range(1, horizon + 1)]


def span(series):
    """'2024-01..2025-12' for a series, or None."""
    if not series:
        return None
    return "%s..%s" % (series[0][0], series[-1][0])


def month_days(period):
    parsed = _parse(period)
    if parsed is None:
        return None
    return calendar.monthrange(parsed[0], parsed[1])[1]


class History:
    """One prepared series, with everything that was discovered about it."""

    __slots__ = ("metric", "series", "frequency", "regular", "gaps", "trimmed",
                 "original_periods", "notes", "partial_final")

    def __init__(self, metric, series, frequency=MONTHLY, regular=True, gaps=(),
                 trimmed=False, original_periods=0, notes=(), partial_final=False):
        self.metric = metric
        self.series = list(series)
        self.frequency = frequency
        self.regular = regular
        self.gaps = list(gaps)
        self.trimmed = trimmed
        self.original_periods = original_periods
        self.notes = list(notes)
        self.partial_final = partial_final

    @property
    def periods(self):
        return len(self.series)

    @property
    def values(self):
        return [v for _period, v in self.series]

    @property
    def labels(self):
        return [period for period, _v in self.series]

    @property
    def span(self):
        return span(self.series)

    @property
    def last_period(self):
        return self.series[-1][0] if self.series else None

    def constant(self):
        """A series that never moves. Forecastable, but nothing can be said about error."""
        values = self.values
        return bool(values) and len(set(values)) == 1

    def zero_baseline(self):
        """A series whose recent level is zero - percentage change is undefined against it."""
        values = self.values
        return bool(values) and all(v == ZERO for v in values[-3:])

    def volatility_pct(self):
        """Mean absolute period-over-period percentage change.

        The fallback basis for an uncertainty band when history is too short to hold any
        of it back for a backtest. Periods with a zero predecessor are skipped rather than
        counted as an infinite move.
        """
        values = self.values
        moves = []
        for earlier, later in zip(values, values[1:]):
            if earlier == ZERO:
                continue
            change = (later - earlier) / earlier * Decimal("100")
            moves.append(change if change >= ZERO else -change)
        if not moves:
            return None
        return sum(moves, ZERO) / Decimal(len(moves))

    def as_dict(self):
        return {"metric": self.metric, "frequency": self.frequency,
                "periods": self.periods, "span": self.span,
                "regular": self.regular, "gaps": list(self.gaps),
                "trimmed": self.trimmed, "original_periods": self.original_periods,
                "notes": list(self.notes)}

    def __len__(self):
        return len(self.series)

    def __repr__(self):
        return "History(%s: %d periods, %s)" % (self.metric, self.periods, self.span)


def find_gaps(series):
    """Missing calendar months inside the observed range."""
    gaps = []
    for (earlier, _a), (later, _b) in zip(series, series[1:]):
        first, second = _index(earlier), _index(later)
        if first is None or second is None:
            continue
        for offset in range(1, second - first):
            gaps.append(step(earlier, offset))
    return gaps


def longest_contiguous(series):
    """The last unbroken run of consecutive months.

    The *last* run rather than the longest: a forecast continues from the present, so the
    run ending at the most recent observation is the only one that can be extended.
    """
    if not series:
        return []
    start = 0
    for i in range(1, len(series)):
        first, second = _index(series[i - 1][0]), _index(series[i][0])
        if first is None or second is None or second - first != 1:
            start = i
    return series[start:]


def prepare(dataset, semantic_map, role, metric, allow_trim=True):
    """Build a `History` for one numeric role, or return None when the role is unmapped.

    Returns `(history, reason)`. A `None` history always carries a reason naming the field
    that was missing - a forecast that cannot start must say what it needed.
    """
    if not semantic_map or not semantic_map.column_for(mapping_mod.DATE):
        return None, ("No column is mapped to a date, so no time series can be built and "
                      "nothing can be forecast.")
    if not semantic_map.column_for(role):
        return None, ("No column is mapped to %s, so %s cannot be forecast. Supply a "
                      "column holding %s and the forecast becomes available."
                      % (role, metric, role.replace("_", " ")))

    raw = p.series_by_period(dataset, semantic_map, role)
    if not raw:
        return None, ("The %s column is mapped but holds no numeric values in any dated "
                      "period, so there is no history to forecast." % role)

    notes = []
    gaps = find_gaps(raw)
    regular = not gaps
    working, trimmed = raw, False

    if gaps:
        notes.append(
            "History has %d missing period(s) (%s). A missing period is not a zero "
            "period, so it was not filled in."
            % (len(gaps), ", ".join(gaps[:6]) + ("..." if len(gaps) > 6 else "")))
        if allow_trim:
            contiguous = longest_contiguous(raw)
            if len(contiguous) >= MIN_CONTIGUOUS and len(contiguous) < len(raw):
                working, trimmed = contiguous, True
                notes.append(
                    "The forecast uses only the %d unbroken periods since the last gap "
                    "(%s); the earlier periods are reported but not projected from."
                    % (len(contiguous), span(contiguous)))

    return History(metric, working, frequency=MONTHLY, regular=regular, gaps=gaps,
                   trimmed=trimmed, original_periods=len(raw), notes=notes), None


def derived(numerator_series, subtrahend_series, metric):
    """A series built by subtracting one aligned series from another (revenue - cost).

    Only periods present in both contribute. A period with revenue but no cost is dropped
    rather than treated as zero-cost, because assuming zero cost would inflate gross profit
    in exactly the period where the data is weakest.
    """
    if numerator_series is None or subtrahend_series is None:
        return None
    right = dict(subtrahend_series)
    out = [(period, value - right[period])
           for period, value in numerator_series if period in right]
    return out or None
