"""Deterministic forecast methods, each declared with its adequacy predicate.

`architecture.md` lists "a forecast method / anomaly detector - register with its adequacy
predicate" as a registration-only extension point requiring no ADR. This module is that
registry.

An **adequacy predicate** is the method's own statement of what history it needs to mean
anything. Seasonal naive with eleven months of history is not a weak forecast, it is a
meaningless one - there is no prior same-month to copy. Making that a property of the
method, rather than a check in the caller, is what lets a new method be added without
touching the engine.

Every method here is arithmetic a reader can reproduce by hand:

    naive             tomorrow looks like today
    moving_average    tomorrow looks like the recent average
    drift             today, continued along the average step so far
    linear_trend      least-squares line through the whole history
    seasonal_naive    this month next year looks like this month last year

No method fits a distribution, so none of them can produce a statistical confidence
interval, which is why `contract.UncertaintyBand` refuses to call itself one.

All arithmetic is `decimal.Decimal`. There is no randomness anywhere in this module: the
same series and parameters always produce the same numbers.
"""

from decimal import Decimal

ZERO = Decimal("0")

#: Monthly periods in one seasonal cycle. The engine is monthly-only (see `series.py`).
SEASON = 12


def _dec(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _values(series):
    return [_dec(v) for _period, v in series]


class Method:
    """One forecast method: how much history it needs, and what it projects.

    `adequate_for` is the predicate. `project` is only ever called after it passes, so a
    method body never has to defend itself against a series that is too short.
    """

    __slots__ = ("method_id", "name", "min_periods", "rationale", "_project", "priority")

    def __init__(self, method_id, name, min_periods, rationale, project, priority):
        self.method_id = method_id
        self.name = name
        self.min_periods = min_periods
        self.rationale = rationale
        self._project = project
        self.priority = priority

    def adequate_for(self, series):
        """Whether this method has enough history to be meaningful, not merely computable."""
        return len(series) >= self.min_periods

    def shortfall(self, series):
        return max(0, self.min_periods - len(series))

    def project(self, series, horizon):
        """`horizon` values continuing `series`. Never called when inadequate."""
        if not self.adequate_for(series):
            raise ValueError("%s needs %d periods, got %d"
                             % (self.method_id, self.min_periods, len(series)))
        if horizon < 1:
            return []
        return self._project(series, horizon)

    def as_dict(self):
        return {"method": self.method_id, "name": self.name,
                "min_periods": self.min_periods, "rationale": self.rationale}

    def __repr__(self):
        return "Method(%s, min=%d)" % (self.method_id, self.min_periods)


# -- the projections --------------------------------------------------------

def _naive(series, horizon):
    """The last observed value, repeated. The floor of the hierarchy."""
    last = _values(series)[-1]
    return [last] * horizon


def _moving_average(series, horizon, window=3):
    """The mean of the trailing window, repeated.

    Flat by construction: it smooths noise and deliberately claims no direction. That is
    the right answer for a series with no trend, and a poor one for a series with a strong
    trend - which is what the backtest is for.
    """
    values = _values(series)
    tail = values[-window:] if len(values) >= window else values
    average = sum(tail, ZERO) / Decimal(len(tail))
    return [average] * horizon


def _drift(series, horizon):
    """The last value continued along the average step observed across the whole history.

    The classic drift method: a straight line pinned to the final observation rather than
    fitted through the middle of the data.
    """
    values = _values(series)
    span = Decimal(len(values) - 1)
    step = (values[-1] - values[0]) / span if span > ZERO else ZERO
    last = values[-1]
    return [last + step * Decimal(h) for h in range(1, horizon + 1)]


def _linear_trend(series, horizon):
    """Ordinary least squares against the period index, in Decimal.

    Written out rather than pulled from a library because the whole engine is stdlib-only
    (CLAUDE.md 4) and because a reader auditing a forecast should be able to see the two
    sums that produced it.
    """
    values = _values(series)
    n = Decimal(len(values))
    xs = [Decimal(i) for i in range(len(values))]
    mean_x = sum(xs, ZERO) / n
    mean_y = sum(values, ZERO) / n
    numerator = sum(((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)), ZERO)
    denominator = sum(((x - mean_x) ** 2 for x in xs), ZERO)
    slope = numerator / denominator if denominator != ZERO else ZERO
    intercept = mean_y - slope * mean_x
    start = len(values)
    return [intercept + slope * Decimal(start + h) for h in range(horizon)]


def _seasonal_naive(series, horizon):
    """The value from the same month one seasonal cycle earlier.

    The only method here that can reproduce a repeating shape. It needs a full cycle of
    history to have a same-month to copy at all, which is its adequacy predicate.
    """
    values = _values(series)
    out = []
    for h in range(horizon):
        source = len(values) - SEASON + (h % SEASON)
        out.append(values[source] if 0 <= source < len(values) else values[-1])
    return out


#: The hierarchy, most conservative first. `priority` breaks ties when two methods score
#: identically in the backtest, so selection stays deterministic.
METHODS = (
    Method("naive", "Naive (last value carried forward)", 2,
           "Repeats the most recent observed period. The most conservative option, and "
           "the fallback when nothing richer is adequate.",
           _naive, priority=1),
    Method("moving_average", "3-period moving average", 3,
           "Averages the last three periods and holds that level flat. Smooths noise; "
           "claims no direction.",
           _moving_average, priority=2),
    Method("drift", "Drift (last value plus average step)", 4,
           "Continues from the latest period along the average period-to-period step "
           "observed across the history.",
           _drift, priority=3),
    Method("linear_trend", "Linear trend (least squares)", 6,
           "Fits a least-squares line through every observed period and extends it. "
           "Assumes the observed direction continues.",
           _linear_trend, priority=4),
    Method("seasonal_naive", "Seasonal naive (same period last year)", SEASON + 1,
           "Repeats the value from the same month one year earlier. The only method here "
           "that reproduces a repeating annual shape.",
           _seasonal_naive, priority=5),
)

BY_ID = {m.method_id: m for m in METHODS}
METHOD_IDS = tuple(m.method_id for m in METHODS)


def get(method_id):
    method = BY_ID.get(method_id)
    if method is None:
        raise KeyError("unknown forecast method %r; known: %s"
                       % (method_id, ", ".join(METHOD_IDS)))
    return method


def adequate(series):
    """Every method whose adequacy predicate this history satisfies, priority order."""
    return [m for m in METHODS if m.adequate_for(series)]


def inadequate(series):
    """(method, periods_short) for every method this history cannot support."""
    return [(m, m.shortfall(series)) for m in METHODS if not m.adequate_for(series)]


def catalogue():
    return {"count": len(METHODS), "methods": [m.as_dict() for m in METHODS]}
