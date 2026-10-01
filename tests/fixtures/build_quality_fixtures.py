"""Deliberately broken fixtures — one per quality family, plus combinations.

Each represents a realistic business-data problem rather than a synthetic edge case, and
each declares its expected outcome so a test cannot quietly disagree with the intent.

Built at test time in a temporary directory. **The demo dataset is never modified.**
"""

import csv
import datetime
import os

HEADERS = ["OrderDate", "OrderID", "Customer", "Region", "Salesperson",
           "Product", "Quantity", "UnitPrice", "NetRevenue", "CostOfGoods"]


def _write(path, rows, headers=None):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers or HEADERS)
        writer.writerows(rows)
    return path


def _row(month=1, day=15, order=1000, customer="Acme Ltd", region="North",
         person="A. Rep", product="Widget", quantity=10, price=100.0,
         revenue=1000.0, cost=600.0, year=2025):
    return ["%04d-%02d-%02d" % (year, month, day), "SO-%05d" % order, customer, region,
            person, product, quantity, "%.2f" % price,
            revenue if isinstance(revenue, str) else "%.2f" % revenue,
            cost if isinstance(cost, str) else "%.2f" % cost]


def _clean_rows(months=12, per_month=4):
    rows, order = [], 1000
    for month in range(1, months + 1):
        for index in range(per_month):
            order += 1
            rows.append(_row(month=month, day=5 + index * 5, order=order,
                             customer="Customer %d" % (index + 1),
                             product="Product %d" % (index + 1)))
    return rows


# ---------------------------------------------------------------------------
# Clean baseline
# ---------------------------------------------------------------------------

def clean(directory, name="clean.csv"):
    """12 months, no defects. Every family should pass."""
    return _write(os.path.join(directory, name), _clean_rows())


# ---------------------------------------------------------------------------
# One broken fixture per family
# ---------------------------------------------------------------------------

def missing_values(directory, name="broken_missing_values.csv"):
    """Revenue blank on most rows — the analysis cannot proceed on this."""
    rows = _clean_rows()
    for row in rows[: int(len(rows) * 0.7)]:
        row[8] = ""
    return _write(os.path.join(directory, name), rows)


def missing_values_minor(directory, name="broken_missing_minor.csv"):
    """A couple of blank customer names — noted, not fatal."""
    rows = _clean_rows()
    rows[0][2] = ""
    return _write(os.path.join(directory, name), rows)


def duplicate_records(directory, name="broken_duplicate_records.csv"):
    """A third of the file is exact duplicate rows — every total is inflated."""
    rows = _clean_rows()
    rows = rows + rows[: int(len(rows) * 0.5)]
    return _write(os.path.join(directory, name), rows)


def invalid_dates(directory, name="broken_invalid_dates.csv"):
    """Half the date column is free text, so no period can be trusted."""
    rows = _clean_rows()
    for index, row in enumerate(rows):
        if index % 2 == 0:
            row[0] = "last tuesday"
    return _write(os.path.join(directory, name), rows)


def invalid_numbers(directory, name="broken_invalid_numbers.csv"):
    """Revenue contains notes instead of amounts."""
    rows = _clean_rows()
    for index, row in enumerate(rows):
        if index % 3 == 0:
            row[8] = "see invoice"
    return _write(os.path.join(directory, name), rows)


def invalid_numbers_minor(directory, name="broken_invalid_numbers_minor.csv"):
    """A single unreadable revenue value - noted, but totals are still usable."""
    rows = _clean_rows()
    rows[0][8] = "see invoice"
    return _write(os.path.join(directory, name), rows)


def negative_values(directory, name="broken_negative_values.csv"):
    """A run of negative revenue — refunds, or a sign error. Never fatal."""
    rows = _clean_rows()
    for row in rows[:8]:
        row[8] = "-1000.00"
    return _write(os.path.join(directory, name), rows)


def missing_periods(directory, name="broken_missing_periods.csv"):
    """A year of data with eight months entirely absent."""
    rows, order = [], 2000
    for month in (1, 2, 11, 12):
        for index in range(3):
            order += 1
            rows.append(_row(month=month, order=order))
    return _write(os.path.join(directory, name), rows)


def duplicate_transactions(directory, name="broken_duplicate_transactions.csv"):
    """One order number reused across unrelated rows."""
    rows = _clean_rows()
    for row in rows[:10]:
        row[1] = "SO-00001"
    return _write(os.path.join(directory, name), rows)


def inconsistent_customers(directory, name="broken_inconsistent_customers.csv"):
    """The same customer entered four ways."""
    rows = _clean_rows()
    for index, variant in enumerate(["Acme Ltd", "ACME LTD", "acme ltd", "Acme  Ltd"]):
        rows[index][2] = variant
    return _write(os.path.join(directory, name), rows)


def inconsistent_products(directory, name="broken_inconsistent_products.csv"):
    """The same product entered three ways."""
    rows = _clean_rows()
    for index, variant in enumerate(["Widget Pro", "widget pro", "WIDGET PRO"]):
        rows[index][5] = variant
    return _write(os.path.join(directory, name), rows)


def mixed_currency(directory, name="broken_mixed_currency.csv"):
    """Two currencies in one revenue column — never summable."""
    rows = _clean_rows(months=6)
    for index, row in enumerate(rows):
        row[8] = ("$%.2f" if index % 2 else "£%.2f") % 1000.0
    return _write(os.path.join(directory, name), rows)


def currency_contradiction(directory, name="broken_currency_contradiction.csv"):
    """All USD, to be run against a GBP Business Context."""
    rows = _clean_rows(months=6)
    for row in rows:
        row[8] = "$1000.00"
    return _write(os.path.join(directory, name), rows)


def outliers(directory, name="broken_outliers.csv"):
    """One revenue value 10,000x the rest — a misplaced decimal, not a good month."""
    rows = _clean_rows(months=12, per_month=4)
    rows[5][8] = "10000000.00"
    return _write(os.path.join(directory, name), rows)


def incomplete_dataset(directory, name="broken_incomplete_dataset.csv"):
    """Header row only — nothing to analyse."""
    return _write(os.path.join(directory, name), [])


def no_revenue_column(directory, name="broken_no_revenue.csv"):
    """Structurally present, but nothing that could be revenue."""
    headers = ["OrderDate", "Notes", "Reference"]
    rows = [["2025-%02d-15" % month, "a note", "REF-%d" % month]
            for month in range(1, 7)]
    return _write(os.path.join(directory, name), rows, headers)


def single_column(directory, name="broken_single_column.csv"):
    """One column — usually the wrong delimiter."""
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("Everything\n")
        for month in range(1, 5):
            fh.write("2025-%02d-15;SO-1;Acme;1000.00\n" % month)
    return path


# ---------------------------------------------------------------------------
# Multiple simultaneous failures
# ---------------------------------------------------------------------------

def multiple_failures(directory, name="broken_multiple.csv"):
    """Several unrelated defects at once — secondary problems must not be hidden."""
    rows = _clean_rows()
    for row in rows[:6]:            # missing revenue
        row[8] = ""
    for index, variant in enumerate(["Acme Ltd", "ACME LTD"]):   # label variants
        rows[index + 6][2] = variant
    rows[10][0] = "not a date"                                    # invalid date
    rows[11][8] = "-500.00"                                       # negative revenue
    rows = rows + rows[:4]                                        # duplicate records
    return _write(os.path.join(directory, name), rows)


def warning_only(directory, name="broken_warnings_only.csv"):
    """Real problems, none fatal: analysis must continue with warnings preserved."""
    rows = _clean_rows()
    rows[0][2] = "acme ltd"
    rows[1][2] = "ACME LTD"
    rows[2][8] = "-500.00"
    rows[3][1] = rows[4][1]
    return _write(os.path.join(directory, name), rows)


def all_null_field(directory, name="broken_all_null_field.csv"):
    """A column present but entirely empty."""
    rows = _clean_rows()
    for row in rows:
        row[4] = ""
    return _write(os.path.join(directory, name), rows)


def ragged(directory, name="broken_ragged.csv"):
    """Rows with the wrong number of fields."""
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(HEADERS) + "\n")
        fh.write("2025-01-15,SO-1,Acme,North,Rep,Widget,10,100.00,1000.00,600.00\n")
        fh.write("2025-02-15,SO-2,Acme\n")
        fh.write("2025-03-15,SO-3,Acme,North,Rep,Widget,10,100.00,1000.00,600.00,extra\n")
    return path


def sensitive_columns(directory, name="broken_sensitive.csv"):
    """Defects in columns holding personal data — findings must not echo the values."""
    headers = ["OrderDate", "Email", "Customer", "NetRevenue"]
    rows = []
    for month in range(1, 7):
        rows.append(["2025-%02d-15" % month,
                     "person%d@example.com" % month,
                     "Acme Ltd" if month % 2 else "ACME LTD",
                     "1000.00"])
    rows.append(rows[0][:])          # a duplicate record, so a finding fires
    return _write(os.path.join(directory, name), rows, headers)


# ---------------------------------------------------------------------------
# Expected outcomes — the contract each fixture asserts
# ---------------------------------------------------------------------------

# fixture builder -> (check_id, expected severity, expected halt)
EXPECTATIONS = (
    (missing_values, "missing_values", "CRITICAL", True),
    (duplicate_records, "duplicate_records", "CRITICAL", True),
    (invalid_dates, "invalid_dates", "CRITICAL", True),
    (invalid_numbers, "invalid_numbers", "CRITICAL", True),
    (negative_values, "negative_values", "WARNING", False),
    (missing_periods, "missing_periods", "CRITICAL", True),
    (duplicate_transactions, "duplicate_transactions", "WARNING", False),
    (inconsistent_customers, "inconsistent_customers", "WARNING", False),
    (inconsistent_products, "inconsistent_products", "WARNING", False),
    (mixed_currency, "currency_consistency", "CRITICAL", True),
    (outliers, "outliers", "WARNING", False),
    (incomplete_dataset, "incomplete_dataset", "CRITICAL", True),
)
