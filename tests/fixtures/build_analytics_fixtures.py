"""Fixtures for the Milestone 6 analytics layer.

`full` carries every dimension the analytics layer can segment by, so each domain has a
happy path. The other builders each remove or distort exactly one thing, so a failure
localises to the behaviour under test rather than to the fixture.

Quality WARNING, CRITICAL and ambiguous-mapping cases are not rebuilt here — `build_fixtures`
already produces them, and a second set would be a second definition of the same condition.

Built at test time; the demo dataset is never modified.
"""

import csv
import os

HEADERS = ["OrderDate", "OrderID", "Customer", "Product", "Category", "Region",
           "Salesperson", "Quantity", "UnitPrice", "NetRevenue", "CostOfGoods"]

PRODUCTS = ("Widget", "Gadget", "Sprocket", "Flange")
CATEGORIES = {"Widget": "Hardware", "Gadget": "Hardware",
              "Sprocket": "Parts", "Flange": "Parts"}
REGIONS = ("North", "South")
REPS = ("Ada", "Grace")


def _write(path, rows, headers=HEADERS):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def _rows(months=6, per_month=4, customers=8, growth=True):
    """Deterministic and arithmetically simple, so expected values are hand-checkable."""
    rows, order = [], 7000
    for month in range(1, months + 1):
        for index in range(per_month):
            order += 1
            product = PRODUCTS[index % len(PRODUCTS)]
            # A steady ramp on one line only, so mix shift is unambiguous.
            revenue = 1000 + (month * 100 if growth and product == "Widget" else 0)
            rows.append([
                # Day spacing keeps every row inside its month for up to seven per month.
                "2025-%02d-%02d" % (month, 3 + index * 4),
                "SO-%05d" % order,
                "Customer %d" % ((order % customers) + 1),
                product,
                CATEGORIES[product],
                REGIONS[index % len(REGIONS)],
                REPS[index % len(REPS)],
                10,
                "%.2f" % (revenue / 10.0),
                "%.2f" % revenue,
                "%.2f" % (revenue * 0.6),
            ])
    return rows


def full(directory, name="analytics_full.csv", **kwargs):
    """Every dimension mapped. Every analytical domain should have a happy path."""
    return _write(os.path.join(directory, name), _rows(**kwargs))


def without(directory, *columns, **kwargs):
    """The same data with named columns removed — one missing dimension per fixture."""
    name = kwargs.pop("name", "analytics_without_%s.csv"
                      % "_".join(c.lower() for c in columns))
    keep = [i for i, header in enumerate(HEADERS) if header not in columns]
    headers = [HEADERS[i] for i in keep]
    rows = [[row[i] for i in keep] for row in _rows(**kwargs)]
    return _write(os.path.join(directory, name), rows, headers)


def single_period(directory, name="analytics_single_period.csv"):
    """One month — no comparison period, so every movement is insufficient_data."""
    return _write(os.path.join(directory, name), _rows(months=1, per_month=6))


def two_periods(directory, name="analytics_two_periods.csv"):
    """Enough for a half-over-half comparison, too few for the cohort minimum of three."""
    return _write(os.path.join(directory, name), _rows(months=2, per_month=4))


def tied_segments(directory, name="analytics_ties.csv"):
    """Two products with identical totals — ranking must be stable and share a rank."""
    rows = []
    order = 8000
    for month in (1, 2, 3, 4):
        for product in ("Alpha", "Bravo", "Charlie"):
            order += 1
            rows.append([
                "2025-%02d-10" % month, "SO-%05d" % order,
                "Customer 1", product, "Hardware", "North", "Ada",
                10, "100.00", "1000.00", "600.00",
            ])
    return _write(os.path.join(directory, name), rows)


def empty(directory, name="analytics_empty.csv"):
    """Headers with no rows at all."""
    return _write(os.path.join(directory, name), [])


def single_customer(directory, name="analytics_single_customer.csv"):
    """One customer — below the k-anonymity floor, so counts must be banded."""
    rows = _rows(months=4, per_month=3)
    for row in rows:
        row[2] = "Only Customer"
    return _write(os.path.join(directory, name), rows)


def flat_revenue(directory, name="analytics_flat.csv"):
    """Identical revenue in both halves — the net movement is exactly zero."""
    return _write(os.path.join(directory, name), _rows(months=6, per_month=4, growth=False))


def zero_revenue(directory, name="analytics_zero_revenue.csv"):
    """Revenue present but zero — shares and ratios are undefined, never zero."""
    rows = _rows(months=4, per_month=3)
    for row in rows:
        row[9] = "0.00"
        row[10] = "0.00"
    return _write(os.path.join(directory, name), rows)
