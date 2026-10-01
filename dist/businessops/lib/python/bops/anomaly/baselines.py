"""Baselines: what a series normally does, computed several defensible ways.

Every anomaly is a comparison, and the comparison is only as good as what it compares
against. A baseline here answers one question - *what should this period have been?* - and
is built in three steps:

    1. project    carry every value in the trailing window forward to the period being
                  judged, at the window's typical period-over-period step, and combine the
                  projections. Combining them, rather than anchoring on the last value
                  alone, is what stops the month after a spike reading as a crash.
    2. correct    add the predictor's own recent offset. A model that is consistently low
                  is mis-fitting the series, not discovering an anomaly every month.
    3. spread     measure dispersion of the past prediction errors around that same offset,
                  so centre and spread are on one footing.

Three baselines, chosen because they fail differently:

    rolling_median   steps and errors combined with the median. Robust - one enormous month
                     contributes one projection out of twelve.
    trailing_mean    the same, combined with the mean. More sensitive on clean data, and
                     dragged by any outlier in its own window, which is why the detector
                     built on it corroborates rather than triggers.
    seasonal         the same calendar month one year earlier, carried forward by the
                     typical year-on-year rate.

All are trailing: a period is compared only against periods *before* it, and every quantity
- projection, offset and spread - is computed from data that closed before the period being
judged. Using the whole series to judge a point would let a large month raise its own
baseline and hide itself.

Median and MAD are computed here rather than taken from `statistics` because the engine
works in `Decimal` (CLAUDE.md 4) and `statistics` would coerce to float, which is the one
thing a money path may not do.
"""

from decimal import Decimal

ZERO = Decimal("0")

ROLLING_MEDIAN = "rolling_median"
TRAILING_MEAN = "trailing_mean"
SEASONAL = "seasonal"

#: Rescales a median absolute deviation onto the same footing as a standard deviation, so
#: the robust and non-robust detectors produce scores on one comparable scale and a single
#: threshold family serves both. It is a unit conversion between two spread measures and
#: nothing more: the engine fits no distribution and tests none, so a score carries no
#: probability and is never labelled "sigma".
MAD_SCALE = Decimal("0.6745")

SEASON = 12


def median(values):
    """The middle value, in Decimal. Even-length lists average the two middle values."""
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def mean(values):
    if not values:
        return None
    return sum(values, ZERO) / Decimal(len(values))


def mad(values, centre=None):
    """Median absolute deviation - the robust analogue of a standard deviation."""
    if not values:
        return None
    centre = median(values) if centre is None else centre
    return median([abs(v - centre) for v in values])


def stdev(values, centre=None):
    """Population standard deviation in Decimal (the series is the whole population)."""
    if len(values) < 2:
        return None
    centre = mean(values) if centre is None else centre
    variance = sum(((v - centre) ** 2 for v in values), ZERO) / Decimal(len(values))
    return variance.sqrt()


def trailing_window(series, index, window):
    """The `window` values immediately before `index`. Never includes `index` itself."""
    start = max(0, index - window)
    return [value for _period, value in series[start:index]]


def growth_rates(values):
    """Period-over-period relative changes. Zero denominators are skipped, not treated
    as infinite moves."""
    rates = []
    for earlier, later in zip(values, values[1:]):
        if earlier == ZERO:
            continue
        rates.append((later - earlier) / earlier)
    return rates


def period_steps(values):
    """Period-over-period absolute changes.

    Additive rather than relative, because the two series where the answer must be exactly
    "nothing is happening" - a flat line and a straight ramp - both have a constant step
    and neither has a constant growth rate. Compounding a rate through a linear series
    overshoots, and the resulting model error is indistinguishable from a real anomaly.
    """
    return [later - earlier for earlier, later in zip(values, values[1:])]


def _growth_baseline(series, index, window, robust):
    """(centre, spread, periods) - the level the trend leads you to expect.

    Three biases have to be removed, and removing only some of them produces a detector
    that is useless in a different way each time:

    **Trend.** A growing business sits above the average of its own past every month, so a
    plain trailing average calls every period a spike. The window's typical
    period-over-period step is measured and applied.

    **A single outlier.** Anchoring on the immediately preceding value makes the month
    *after* a spike look like a crash. Combining a projection from every window value
    instead means a lone outlier contributes one of twelve.

    **Model error.** An additive step cannot fit a compounding series exactly, and the
    resulting offset grows with the level. Left uncorrected it lands wholly in the
    deviation while the spread is measured around it, so every ordinary period in a
    compounding series scores as an anomaly.

    On a flat or straight-line series the step fits exactly, every residual is zero, and
    the baseline reduces to the projection itself.
    """
    values = trailing_window(series, index, window)
    if len(values) < 2:
        return None, None, len(values)

    projection = project(values, robust)
    if projection is None:
        centre = median(values) if robust else mean(values)
        spread = mad(values, centre) if robust else stdev(values, centre)
        return centre, spread, len(values)

    # How wrong this same predictor was on each earlier period. Two things come out of
    # these residuals, and using them for only one of the two is what makes a detector
    # misbehave.
    residuals = []
    for position in range(max(2, index - window), index):
        prior = trailing_window(series, position, window)
        predicted = project(prior, robust)
        if predicted is not None:
            residuals.append(series[position][1] - predicted)

    if len(residuals) < 2:
        return projection, None, len(values)

    # 1. **Bias.** A predictor that is consistently low is not discovering an anomaly every
    #    period; it is mis-modelling the series. An additive step under-predicts a
    #    compounding series by a growing amount, and that offset would otherwise land
    #    entirely in the deviation while the spread was measured around it - guaranteeing a
    #    large score for every ordinary period. Correcting the centre by the predictor's own
    #    recent offset puts centre and spread on the same footing, and it is also what lets
    #    the baseline follow a permanent step change instead of arguing with it for as long
    #    as the window is wide.
    #
    # 2. **Spread.** Dispersion around that corrected prediction: how far off a period
    #    normally lands once the systematic part is accounted for.
    #
    # On a flat or straight-line series every residual is zero, so both terms vanish and
    # the baseline is exactly the projection.
    bias = median(residuals) if robust else mean(residuals)
    centre = projection + bias
    spread = mad(residuals, bias) if robust else stdev(residuals, bias)
    return centre, spread, len(values)


def project(values, robust=True):
    """The next value a window implies, carried forward at its typical step.

    Each observation is carried forward to the period after the window at the window's
    typical period-over-period step, and the projections are then combined. Using the
    median of every projection rather than the last value alone means one outlier inside
    the window contributes one projection out of twelve, so the month *after* a spike is
    not reported as a crash.
    """
    if len(values) < 2:
        return None
    steps = period_steps(values)
    centre_step = median(steps) if robust else mean(steps)
    if centre_step is None:
        return None
    count = len(values)
    projected = [value + centre_step * Decimal(count - position)
                 for position, value in enumerate(values)]
    return median(projected) if robust else mean(projected)


def rolling_median_baseline(series, index, window):
    """(centre, spread, periods) from the median trailing growth rate and its MAD."""
    return _growth_baseline(series, index, window, robust=True)


def trailing_mean_baseline(series, index, window):
    """(centre, spread, periods) from the mean trailing growth rate and its deviation."""
    return _growth_baseline(series, index, window, robust=False)


def level_median_baseline(series, index, window):
    """The plain trailing median of the levels, with MAD.

    Kept for a series with no trend, and used by the tests to show the difference between
    a level baseline and a growth baseline on the same data.
    """
    values = trailing_window(series, index, window)
    if not values:
        return None, None, 0
    centre = median(values)
    return centre, mad(values, centre), len(values)


def year_over_year_rates(series, index, season=SEASON):
    """Every year-on-year growth rate observable strictly before `index`."""
    rates = []
    for i in range(season, index):
        prior = series[i - season][1]
        if prior == ZERO:
            continue
        rates.append((series[i][1] - prior) / prior)
    return rates


def seasonal_baseline(series, index, season=SEASON):
    """(centre, spread, periods) - the same month last year, carried forward by the
    business's own year-on-year growth.

    Comparing this March against last March directly answers the wrong question for any
    growing or shrinking business: a company up 90% on the year is 90% above last March
    every March, and a detector reading that as anomalous simply rediscovers the growth
    rate twelve times. The centre is therefore last year's same month *grown by the typical
    year-on-year rate observed so far*, which leaves only the part of the move the annual
    pattern does not already account for.

    Returns no baseline at all when there is not yet one full year-on-year pair to learn
    the rate from - an unadjusted comparison would be worse than none.
    """
    if index < season:
        return None, None, 0
    rates = year_over_year_rates(series, index, season)
    if not rates:
        return None, None, 0
    last_year = series[index - season][1]
    centre_rate = median(rates)
    centre = last_year * (Decimal("1") + centre_rate)
    spread_rate = mad(rates, centre_rate)
    magnitude = last_year if last_year > ZERO else -last_year
    spread = magnitude * spread_rate if spread_rate is not None else None
    return centre, spread, len(rates)
