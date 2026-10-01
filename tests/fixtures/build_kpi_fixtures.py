"""Fixtures for the full KPI engine.

`rich_business` carries every field the catalogue can consume, so each metric has a
happy path. The narrower fixtures each remove or distort exactly one thing, so a failure
localises to the metric under test.

Built at test time; the demo dataset is never modified.
"""

import csv
import os

RICH_HEADERS = [
    "OrderDate", "OrderID", "Customer", "Product", "Region", "Salesperson",
    "Quantity", "UnitPrice", "NetRevenue", "CostOfGoods",
    "OperatingExpenses", "Depreciation", "Inventory", "Cash",
    "Receivables", "Payables", "CurrentAssets", "CurrentLiabilities",
    "MarketingSpend", "Leads", "Stage", "PipelineValue",
    "OpenedDate", "ClosedDate", "RecurringRevenue", "Investment",
]


def _write(path, rows, headers):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def _rich_rows(months=12, per_month=3, customers=6):
    """Deterministic, arithmetically simple values so expected results are hand-checkable."""
    rows, order = [], 5000
    for month in range(1, months + 1):
        for index in range(per_month):
            order += 1
            customer = "Customer %d" % ((order % customers) + 1)
            rows.append([
                "2025-%02d-%02d" % (month, 5 + index * 5),
                "SO-%05d" % order,
                customer,
                "Product %d" % (index + 1),
                "Region %d" % (index % 2),
                "Rep %d" % (index % 2),
                10,                       # Quantity
                "100.00",                 # UnitPrice
                "1000.00",                # NetRevenue
                "600.00",                 # CostOfGoods
                "100.00",                 # OperatingExpenses
                "20.00",                  # Depreciation
                "5000.00",                # Inventory
                "50000.00",               # Cash
                "9000.00",                # Receivables
                "4000.00",                # Payables
                "70000.00",               # CurrentAssets
                "30000.00",               # CurrentLiabilities
                "50.00",                  # MarketingSpend
                20,                       # Leads
                "won" if index == 0 else ("lost" if index == 1 else "open"),
                "2000.00",                # PipelineValue
                "2025-%02d-01" % month,   # OpenedDate
                "2025-%02d-21" % month,   # ClosedDate
                "800.00",                 # RecurringRevenue
                "10000.00",               # Investment
            ])
    return rows


def rich_business(directory, name="rich_business.csv", **kwargs):
    """Every field the catalogue can use. Every metric should have a happy path."""
    return _write(os.path.join(directory, name), _rich_rows(**kwargs), RICH_HEADERS)


def single_period(directory, name="single_period.csv"):
    """One month only — period-over-period metrics must report insufficient_data."""
    rows = _rich_rows(months=1, per_month=3)
    return _write(os.path.join(directory, name), rows, RICH_HEADERS)


def sales_only(directory, name="sales_only.csv"):
    """A plain sales extract: no opex, inventory, cash, pipeline or recurring fields."""
    headers = ["OrderDate", "OrderID", "Customer", "Product", "Region", "Salesperson",
               "Quantity", "UnitPrice", "NetRevenue", "CostOfGoods"]
    rows = [row[:10] for row in _rich_rows()]
    return _write(os.path.join(directory, name), rows, headers)


def zero_revenue(directory, name="zero_revenue.csv"):
    """Revenue present but zero — margins and rates are undefined, not zero."""
    rows = _rich_rows(months=3)
    for row in rows:
        row[8] = "0.00"
    return _write(os.path.join(directory, name), rows, RICH_HEADERS)


def zero_investment(directory, name="zero_investment.csv"):
    """A zero denominator for ROI."""
    rows = _rich_rows(months=3)
    for row in rows:
        row[25] = "0.00"
    return _write(os.path.join(directory, name), rows, RICH_HEADERS)


def cash_generative(directory, name="cash_generative.csv"):
    """Profitable every month — burn is zero and runway is not limited by burn."""
    rows = _rich_rows(months=6)
    for row in rows:
        row[9] = "100.00"       # low cost
        row[10] = "50.00"       # low opex
    return _write(os.path.join(directory, name), rows, RICH_HEADERS)


def loss_making(directory, name="loss_making.csv"):
    """Costs exceed revenue every month — a real burn rate and a finite runway."""
    rows = _rich_rows(months=6)
    for row in rows:
        row[9] = "900.00"
        row[10] = "400.00"
    return _write(os.path.join(directory, name), rows, RICH_HEADERS)


def no_repeat_customers(directory, name="no_repeat_customers.csv"):
    """Every customer appears once — retention 0%, churn 100%."""
    rows = _rich_rows(months=6, per_month=2)
    for index, row in enumerate(rows):
        row[2] = "Customer %d" % index
    return _write(os.path.join(directory, name), rows, RICH_HEADERS)


def all_open_deals(directory, name="all_open_deals.csv"):
    """No decided opportunities — win rate is undefined, not zero."""
    rows = _rich_rows(months=3)
    for row in rows:
        row[20] = "open"
    return _write(os.path.join(directory, name), rows, RICH_HEADERS)


def mixed_currency(directory, name="kpi_mixed_currency.csv"):
    """Two currencies — monetary metrics must be refused, never converted."""
    rows = _rich_rows(months=6)
    for index, row in enumerate(rows):
        row[8] = ("$%s" if index % 2 else "£%s") % "1000.00"
    return _write(os.path.join(directory, name), rows, RICH_HEADERS)


def large_values(directory, name="large_values.csv"):
    """Very large monetary values — Decimal must not lose precision."""
    rows = _rich_rows(months=3)
    for row in rows:
        row[8] = "99999999999.99"
        row[9] = "11111111111.11"
    return _write(os.path.join(directory, name), rows, RICH_HEADERS)


def rounding_boundary(directory, name="rounding_boundary.csv"):
    """Values that expose binary-float error if Decimal is not used throughout."""
    rows = _rich_rows(months=2, per_month=1)
    for row in rows:
        row[8] = "0.10"
        row[9] = "0.20"
    return _write(os.path.join(directory, name), rows, RICH_HEADERS)
