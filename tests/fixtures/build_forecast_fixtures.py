"""Fixtures for the Milestone 8 forecasting and anomaly layers.

Milestone 6 fixtures top out at a handful of months, which is below every forecast minimum
and every anomaly baseline. These builders produce series long enough to forecast, each
shaped to isolate exactly one behaviour: a trend, a flat line, a spike, a gap, a zero.

Every series is written as an ordinary sales CSV with the same headers the rest of the
suite uses, so the whole pipeline - ingestion, mapping, quality, KPIs - runs unchanged.
Values are round numbers, so an expected forecast can be checked by hand.

Built at test time; the demo dataset is never modified.
"""

import csv
import os

HEADERS = ["OrderDate", "OrderID", "Customer", "Product", "Category", "Region",
           "Salesperson", "Quantity", "UnitPrice", "NetRevenue", "CostOfGoods"]

PRODUCTS = ("Widget", "Gadget")
CATEGORIES = {"Widget": "Hardware", "Gadget": "Parts"}
REGIONS = ("North", "South")
REPS = ("Ada", "Grace")

#: Cost is a fixed share of revenue, so gross profit and margin are exactly predictable.
COST_SHARE = 0.6


def _write(path, rows, headers=HEADERS):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def month_label(index, start_year=2024, start_month=1):
    """The 'YYYY-MM' for month `index` counted from the start, zero-based."""
    total = (start_year * 12 + (start_month - 1)) + index
    return "%04d-%02d" % (total // 12, total % 12 + 1)


def rows_from(values, start_year=2024, start_month=1, rows_per_month=2, customers=6,
              skip=(), cost_share=COST_SHARE):
    """Build sales rows whose monthly revenue totals are exactly `values`.

    Each month's total is split evenly across `rows_per_month` rows, so the period series
    the KPI engine rebuilds equals the value asked for here.
    """
    rows, order = [], 9000
    for index, total in enumerate(values):
        period = month_label(index, start_year, start_month)
        if period in skip:
            continue
        share = float(total) / rows_per_month
        for slot in range(rows_per_month):
            order += 1
            product = PRODUCTS[slot % len(PRODUCTS)]
            rows.append([
                "%s-%02d" % (period, 4 + slot * 5),
                "SO-%05d" % order,
                "Customer %d" % ((order % customers) + 1),
                product,
                CATEGORIES[product],
                REGIONS[slot % len(REGIONS)],
                REPS[slot % len(REPS)],
                10,
                "%.2f" % (share / 10.0),
                "%.2f" % share,
                "%.2f" % (share * cost_share),
            ])
    return rows


def series(directory, values, name, **kwargs):
    return _write(os.path.join(directory, name), rows_from(values, **kwargs))


# -- shaped series -----------------------------------------------------------

def steady_trend(directory, months=24, base=10000, step=500,
                 name="fc_trend.csv"):
    """A clean linear ramp. Linear trend should win the backtest comfortably."""
    return series(directory, [base + step * i for i in range(months)], name)


def flat(directory, months=24, value=10000, name="fc_flat.csv"):
    """A perfectly constant series: no trend, no volatility, no spread."""
    return series(directory, [value] * months, name)


def seasonal(directory, years=3, base=10000, name="fc_seasonal.csv"):
    """A repeating annual shape with no underlying growth."""
    shape = [1.0, 0.9, 1.0, 1.05, 1.1, 1.2, 1.15, 1.1, 1.0, 1.05, 1.3, 1.5]
    values = [base * shape[i % 12] for i in range(12 * years)]
    return series(directory, values, name)


def with_spike(directory, months=24, base=10000, spike_at=18, factor=3.0,
               name="fc_spike.csv"):
    """A flat-ish series with one isolated month far above the rest."""
    values = [base] * months
    values[spike_at] = base * factor
    return series(directory, values, name)


def with_drop(directory, months=24, base=10000, drop_at=18, factor=0.2,
              name="fc_drop.csv"):
    """A flat-ish series with one isolated month far below the rest."""
    values = [base] * months
    values[drop_at] = base * factor
    return series(directory, values, name)


def with_two_anomalies(directory, months=24, base=10000,
                       name="fc_two_anomalies.csv"):
    values = [base] * months
    values[14] = base * 2.5
    values[20] = base * 0.3
    return series(directory, values, name)


def with_gap(directory, months=24, base=10000, step=400, missing=("2025-03",),
             name="fc_gap.csv"):
    """A trend with whole months absent - a gap, not a zero."""
    values = [base + step * i for i in range(months)]
    return series(directory, values, name, skip=set(missing))


def zero_tail(directory, months=24, base=10000, name="fc_zero_tail.csv"):
    """A series whose most recent months are zero: percentage change is undefined."""
    values = [base] * (months - 3) + [0, 0, 0]
    return series(directory, values, name)


def short(directory, months=4, base=10000, step=200, name="fc_short.csv"):
    """Below every forecast minimum and every anomaly baseline."""
    return series(directory, [base + step * i for i in range(months)], name)


def exactly_minimum(directory, months=12, base=10000, step=300,
                    name="fc_minimum.csv"):
    """Exactly the configured minimum history - the boundary case."""
    return series(directory, [base + step * i for i in range(months)], name)


def long_history(directory, months=60, base=10000, step=200,
                 name="fc_long.csv"):
    """Long enough to exercise the horizon ceiling and a wide backtest."""
    return series(directory, [base + step * i for i in range(months)], name)


def no_cost(directory, months=24, base=10000, step=500, name="fc_no_cost.csv"):
    """Revenue only: gross profit must be refused, not derived."""
    headers = [h for h in HEADERS if h != "CostOfGoods"]
    rows = rows_from([base + step * i for i in range(months)])
    trimmed = [row[:-1] for row in rows]
    return _write(os.path.join(directory, name), trimmed, headers)


def single_customer(directory, months=24, base=10000, name="fc_one_customer.csv"):
    """One customer across the whole series - below the k-anonymity floor."""
    return series(directory, [base] * months, name, customers=1)
