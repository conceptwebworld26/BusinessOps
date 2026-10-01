"""Synthetic large CSV datasets for the M13.1 large-dataset measurement (ADR-0039 section D.1).

Every value is synthetic and produced by fixed integer arithmetic on the row index: there is
no random number generator, no clock and no external input, so the same `rows` argument
always writes byte-identical files. Labels are obviously synthetic ("Synthetic Customer 0001",
"Synthetic Product 07"); nothing is copied from, shaped after or named after real data.

Money is built in integer pence and written with two decimals, so a revenue or cost figure is
exact in the file and needs no binary floating point to generate.

The files are written into a caller-supplied temporary directory and are never committed.
"""

import os

#: The demo dataset's header, so the semantic mapper resolves the same roles it does there.
HEADERS = ("OrderDate", "OrderID", "Customer", "Region", "Salesperson", "Product",
           "Category", "Quantity", "UnitPrice", "NetRevenue", "UnitCost", "CostOfGoods")

#: Twenty-four monthly periods, 2024-01 to 2025-12: enough history for every analytics
#: domain, and the same span as the demo dataset.
MONTHS = 24

REGIONS = ("North", "South", "East", "West")
CATEGORIES = ("Storage", "Packaging", "Logistics")
CUSTOMERS = 400
PRODUCTS = 12
SALESPEOPLE = 8


def _pence(value):
    return "%d.%02d" % divmod(value, 100)


def row(index):
    """One synthetic row, as a tuple of strings, derived only from `index`."""
    month = index % MONTHS                       # 0..23, every month equally represented
    year = 2024 + month // 12
    day = (index % 28) + 1
    product = index % PRODUCTS
    quantity = (index % 9) + 1
    unit_price = 5000 + (product * 750) + (index % 97)        # pence
    unit_cost = (unit_price * 3) // 5 + (index % 13)          # pence, below price
    return (
        "%04d-%02d-%02d" % (year, month % 12 + 1, day),
        "SYN-%07d" % index,
        "Synthetic Customer %04d" % (index % CUSTOMERS),
        REGIONS[index % len(REGIONS)],
        "Synthetic Rep %02d" % (index % SALESPEOPLE),
        "Synthetic Product %02d" % product,
        CATEGORIES[product % len(CATEGORIES)],
        str(quantity),
        _pence(unit_price),
        _pence(unit_price * quantity),
        _pence(unit_cost),
        _pence(unit_cost * quantity),
    )


def expected_revenue_pence(rows):
    """The exact revenue total the file holds, in pence, computed independently of any reader."""
    total = 0
    for index in range(rows):
        product = index % PRODUCTS
        unit_price = 5000 + (product * 750) + (index % 97)
        total += unit_price * ((index % 9) + 1)
    return total


def large_csv(directory, rows, name=None):
    """Write `rows` synthetic rows to `directory` and return the path."""
    path = os.path.join(directory, name or ("m13_large_%d.csv" % rows))
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(HEADERS) + "\n")
        for index in range(rows):
            handle.write(",".join(row(index)) + "\n")
    return path
