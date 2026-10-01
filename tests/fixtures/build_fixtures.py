"""Deterministic fixtures for the Milestone 2 scenarios.

Built in a temporary directory at test time rather than committed, so a broken fixture can
never be mistaken for real data and the fixtures always match the code that reads them.
"""

import csv
import os

CLEAN_HEADERS = ["OrderDate", "OrderID", "Customer", "Region", "Salesperson",
                 "Product", "Category", "Quantity", "UnitPrice", "NetRevenue",
                 "UnitCost", "CostOfGoods"]


def _write(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def small_clean(directory, name="clean.csv"):
    """A minimal well-formed dataset: 4 months, 2 products, 2 regions."""
    rows = []
    order = 1000
    for month in range(1, 5):
        for product, price, cost in (("Widget", 100.0, 60.0), ("Gadget", 200.0, 150.0)):
            for region in ("North", "South"):
                order += 1
                quantity = 10
                rows.append([
                    "2025-%02d-15" % month, "SO-%04d" % order, "Customer %s" % region,
                    region, "Rep %s" % region, product,
                    "Cat", quantity, "%.2f" % price, "%.2f" % (price * quantity),
                    "%.2f" % cost, "%.2f" % (cost * quantity)])
    return _write(os.path.join(directory, name), CLEAN_HEADERS, rows)


def critical_missing_revenue(directory, name="critical_missing_revenue.csv"):
    """CRITICAL: most revenue values are blank, so totals would be silently understated."""
    rows = []
    order = 2000
    for index in range(20):
        order += 1
        blank = index % 5 != 0          # 80% missing, far above the 5% limit
        rows.append([
            "2025-%02d-10" % ((index % 6) + 1), "SO-%04d" % order, "Customer A",
            "North", "Rep A", "Widget", "Cat", 5, "100.00",
            "" if blank else "500.00", "60.00", "300.00"])
    return _write(os.path.join(directory, name), CLEAN_HEADERS, rows)


def critical_no_revenue_column(directory, name="critical_no_revenue.csv"):
    """CRITICAL: no revenue column exists at all."""
    header = ["OrderDate", "Notes", "Reference"]
    rows = [["2025-01-15", "some note", "REF-1"],
            ["2025-02-15", "another note", "REF-2"]]
    return _write(os.path.join(directory, name), header, rows)


def critical_invalid_dates(directory, name="critical_invalid_dates.csv"):
    """CRITICAL: the date column is mostly unparseable text."""
    rows = []
    order = 3000
    for index in range(20):
        order += 1
        date = "2025-01-10" if index % 10 == 0 else "not a date %d" % index
        rows.append([date, "SO-%04d" % order, "Customer A", "North", "Rep A",
                     "Widget", "Cat", 5, "100.00", "500.00", "60.00", "300.00"])
    return _write(os.path.join(directory, name), CLEAN_HEADERS, rows)


def ambiguous_mapping(directory, name="ambiguous.csv"):
    """Revenue is plausible but not certain: a generic 'Amount' column.

    'Amount' is a weak-pattern match for revenue, so it should land between the confirm and
    auto thresholds — mapped provisionally, requiring confirmation, never silently accepted.
    """
    header = ["Period", "Amount", "Client", "Item"]
    rows = []
    for month in range(1, 7):
        rows.append(["2025-%02d-15" % month, "%.2f" % (1000.0 * month),
                     "Client %d" % month, "Item A"])
    return _write(os.path.join(directory, name), header, rows)


def warning_duplicates(directory, name="warning_duplicates.csv"):
    """WARNING only: duplicate order ids and inconsistent customer casing."""
    rows = []
    for month in range(1, 5):
        rows.append(["2025-%02d-15" % month, "SO-9001", "acme ltd", "North",
                     "Rep A", "Widget", "Cat", 5, "100.00", "500.00", "60.00", "300.00"])
        rows.append(["2025-%02d-16" % month, "SO-9001", "ACME Ltd", "North",
                     "Rep A", "Widget", "Cat", 5, "100.00", "500.00", "60.00", "300.00"])
    return _write(os.path.join(directory, name), CLEAN_HEADERS, rows)
