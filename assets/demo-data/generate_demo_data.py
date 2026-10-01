#!/usr/bin/env python3
"""Generate the BusinessOps synthetic demo dataset.

    python assets/demo-data/generate_demo_data.py

Produces `northwind_sales.csv` and `northwind_sales.xlsx` describing the *same* underlying
business, so the two ingestion paths can be compared directly.

Entirely synthetic: the company, customers, products, salespeople and every figure are
invented. No real business, person or private data appears here.

Deterministic — a fixed seed, so tests can assert exact figures. Regenerating always
produces byte-identical output.

The workbook is written with the standard library only (`zipfile` + XML), which also means
the demo file exercises the same constructs the Tier 3 reader must handle: shared strings,
styled date cells, a currency number format, and an inline string.

Designed trends (deliberately planted so the analysis layer has something true to find):
  * Steady underlying growth, roughly 18% year over year.
  * Q4 seasonal peak, strongest in November and December.
  * "Legacy Crates" declines steadily and is nearly retired by month 24.
  * "Chilled Logistics" launches in month 7 and grows fast.
  * Northern region grows well above the others; Scotland slowly shrinks.
  * Unit costs rise from month 19 while selling prices hold, compressing gross margin
    through the final half-year — the most important finding in the dataset, and the one a
    business owner would actually want surfaced.
"""

import csv
import datetime
import os
import random
import zipfile

SEED = 20260908
START_YEAR, START_MONTH = 2024, 1
MONTHS = 24
HERE = os.path.abspath(os.path.dirname(__file__))

CURRENCY = "GBP"

REGIONS = ["North", "South", "Midlands", "Scotland"]
REGION_WEIGHT = {"North": 0.34, "South": 0.29, "Midlands": 0.22, "Scotland": 0.15}

SALESPEOPLE = {
    "North": ["A. Okafor", "R. Lindqvist"],
    "South": ["M. Delacroix"],
    "Midlands": ["S. Whitfield"],
    "Scotland": ["T. Buchanan"],
}

# name -> (category, base unit price, base unit cost, lifecycle)
PRODUCTS = {
    "Ambient Pallets":    ("Storage",   142.00,  92.30, "steady"),
    "Legacy Crates":      ("Storage",    88.50,  61.95, "declining"),
    "Insulated Totes":    ("Packaging", 214.75, 133.15, "steady"),
    "Recycled Wrap":      ("Packaging",  36.20,  24.62, "growing"),
    "Chilled Logistics":  ("Services",  480.00, 288.00, "launch"),
    "Pallet Recovery":    ("Services",  165.00,  99.00, "steady"),
}

CUSTOMERS = [
    "Braemar Foods", "Calder Grocers", "Dunlin Wholesale", "Eastgate Retail",
    "Fenwick Provisions", "Glenmore Stores", "Harrowby Markets", "Ilkley Fresh",
    "Jesmond Supply", "Kelvin Trading", "Langdale Foods", "Marchmont Retail",
    "Netherby Group", "Oakworth Stores", "Penrith Provisions", "Quarrywood Foods",
    "Ravensdale Markets", "Selkirk Supply", "Thirlmere Trading", "Ullswater Foods",
    "Vale Provisions", "Wetherby Wholesale", "Yarrow Stores", "Zetland Markets",
]

HEADERS = ["OrderDate", "OrderID", "Customer", "Region", "Salesperson",
           "Product", "Category", "Quantity", "UnitPrice", "NetRevenue",
           "UnitCost", "CostOfGoods"]


def month_sequence():
    for index in range(MONTHS):
        year = START_YEAR + (START_MONTH - 1 + index) // 12
        month = (START_MONTH - 1 + index) % 12 + 1
        yield index, year, month


def seasonal_factor(month):
    """Q4 peak, quiet February — a retail/wholesale shape."""
    return {1: 0.88, 2: 0.82, 3: 0.95, 4: 1.00, 5: 1.02, 6: 1.00,
            7: 0.94, 8: 0.90, 9: 1.05, 10: 1.12, 11: 1.28, 12: 1.22}[month]


def growth_factor(index):
    return 1.0 + 0.014 * index          # ~18% a year, compounding gently


def product_factor(product, index):
    lifecycle = PRODUCTS[product][3]
    if lifecycle == "declining":        # Legacy Crates fades out
        return max(0.05, 1.0 - 0.041 * index)
    if lifecycle == "growing":
        return 1.0 + 0.030 * index
    if lifecycle == "launch":           # Chilled Logistics starts in month 7
        return 0.0 if index < 6 else min(1.9, 0.28 + 0.115 * (index - 6))
    return 1.0


def cost_inflation(index):
    """Unit costs climb from month 19 — the planted margin-compression trend.

    Selling prices do NOT rise to match, which is the whole point: the business is
    absorbing supplier increases and its gross margin is quietly eroding.
    """
    return 1.0 if index < 18 else 1.0 + 0.042 * (index - 17)


def region_weight(region, index):
    """Region demand shifts over time. Applied to order mix, never to price."""
    base = REGION_WEIGHT[region]
    if region == "North":               # the standout performer
        return base * (1.0 + 0.030 * index)
    if region == "Scotland":
        return base * max(0.4, 1.0 - 0.012 * index)
    return base


def build_rows():
    rng = random.Random(SEED)
    rows = []
    order_number = 41000

    for index, year, month in month_sequence():
        month_orders = int(78 * seasonal_factor(month) * growth_factor(index))
        for _ in range(month_orders):
            region = rng.choices(
                REGIONS, weights=[region_weight(r, index) for r in REGIONS])[0]
            product = rng.choices(
                list(PRODUCTS),
                weights=[max(0.001, product_factor(p, index)) for p in PRODUCTS])[0]
            if product_factor(product, index) <= 0.0:
                continue

            category, base_price, base_cost, _ = PRODUCTS[product]
            salesperson = rng.choice(SALESPEOPLE[region])
            customer = rng.choice(CUSTOMERS)
            day = rng.randint(1, 28)

            quantity = max(1, int(rng.gauss(9, 3.4)))
            price = base_price * rng.uniform(0.94, 1.07)
            cost = base_cost * cost_inflation(index) * rng.uniform(0.97, 1.03)

            price = round(price, 2)
            cost = round(cost, 2)
            order_number += 1
            rows.append({
                "OrderDate": datetime.date(year, month, day),
                "OrderID": "SO-%05d" % order_number,
                "Customer": customer,
                "Region": region,
                "Salesperson": salesperson,
                "Product": product,
                "Category": category,
                "Quantity": quantity,
                "UnitPrice": price,
                "NetRevenue": round(price * quantity, 2),
                "UnitCost": cost,
                "CostOfGoods": round(cost * quantity, 2),
            })

    rows.sort(key=lambda r: (r["OrderDate"], r["OrderID"]))
    return rows


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------

def write_csv(rows, path):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADERS)
        for row in rows:
            writer.writerow([
                row["OrderDate"].isoformat(), row["OrderID"], row["Customer"],
                row["Region"], row["Salesperson"], row["Product"], row["Category"],
                row["Quantity"], "%.2f" % row["UnitPrice"], "%.2f" % row["NetRevenue"],
                "%.2f" % row["UnitCost"], "%.2f" % row["CostOfGoods"],
            ])
    return path


# --------------------------------------------------------------------------
# XLSX (standard library only)
# --------------------------------------------------------------------------

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

EXCEL_EPOCH = datetime.date(1899, 12, 30)   # 1900 system, incl. the Lotus leap-year bug


def _serial(day):
    return (day - EXCEL_EPOCH).days


def _esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def write_xlsx(rows, path):
    # Shared strings for repeated text; UnitPrice uses an inline string nowhere, but the
    # Category column is written inline so the Tier 3 reader exercises that path too.
    shared, order = {}, []

    def sid(text):
        if text not in shared:
            shared[text] = len(order)
            order.append(text)
        return shared[text]

    for header in HEADERS:
        sid(header)
    for row in rows:
        for key in ("OrderID", "Customer", "Region", "Salesperson", "Product"):
            sid(row[key])

    # style indexes: 0 general, 1 date (builtin 14), 2 GBP currency (custom 164)
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="%s">'
        '<numFmts count="1"><numFmt numFmtId="164" formatCode="&quot;£&quot;#,##0.00"/></numFmts>'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border/></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="3">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="14" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>' % NS
    )

    sst = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<sst xmlns="%s" count="%d" uniqueCount="%d">%s</sst>'
           % (NS, len(order), len(order),
              "".join("<si><t>%s</t></si>" % _esc(t) for t in order)))

    def col_letter(index):
        letters = ""
        while index >= 0:
            letters = chr(index % 26 + 65) + letters
            index = index // 26 - 1
        return letters

    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="%s"><sheetData>' % NS]

    header_cells = "".join(
        '<c r="%s1" t="s"><v>%d</v></c>' % (col_letter(i), sid(h))
        for i, h in enumerate(HEADERS))
    parts.append('<row r="1">%s</row>' % header_cells)

    for number, row in enumerate(rows, start=2):
        cells = [
            '<c r="A%d" s="1"><v>%d</v></c>' % (number, _serial(row["OrderDate"])),
            '<c r="B%d" t="s"><v>%d</v></c>' % (number, sid(row["OrderID"])),
            '<c r="C%d" t="s"><v>%d</v></c>' % (number, sid(row["Customer"])),
            '<c r="D%d" t="s"><v>%d</v></c>' % (number, sid(row["Region"])),
            '<c r="E%d" t="s"><v>%d</v></c>' % (number, sid(row["Salesperson"])),
            '<c r="F%d" t="s"><v>%d</v></c>' % (number, sid(row["Product"])),
            # inline string, so Tier 3 must handle t="inlineStr"
            '<c r="G%d" t="inlineStr"><is><t>%s</t></is></c>' % (number, _esc(row["Category"])),
            '<c r="H%d"><v>%d</v></c>' % (number, row["Quantity"]),
            '<c r="I%d" s="2"><v>%.2f</v></c>' % (number, row["UnitPrice"]),
            '<c r="J%d" s="2"><v>%.2f</v></c>' % (number, row["NetRevenue"]),
            '<c r="K%d" s="2"><v>%.2f</v></c>' % (number, row["UnitCost"]),
            '<c r="L%d" s="2"><v>%.2f</v></c>' % (number, row["CostOfGoods"]),
        ]
        parts.append('<row r="%d">%s</row>' % (number, "".join(cells)))

    parts.append("</sheetData></worksheet>")
    sheet = "".join(parts)

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        '</Types>')

    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="%s/officeDocument" Target="xl/workbook.xml"/>'
                 '</Relationships>' % REL)

    workbook = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="%s" xmlns:r="%s">'
                '<sheets><sheet name="Sales" sheetId="1" r:id="rId1"/></sheets>'
                '</workbook>' % (NS, REL))

    workbook_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                     '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Id="rId1" Type="%s/worksheet" Target="worksheets/sheet1.xml"/>'
                     '<Relationship Id="rId2" Type="%s/styles" Target="styles.xml"/>'
                     '<Relationship Id="rId3" Type="%s/sharedStrings" Target="sharedStrings.xml"/>'
                     '</Relationships>' % (REL, REL, REL))

    fixed = (1980, 1, 1, 0, 0, 0)      # constant timestamps -> byte-identical rebuilds
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in (
                ("[Content_Types].xml", content_types),
                ("_rels/.rels", root_rels),
                ("xl/workbook.xml", workbook),
                ("xl/_rels/workbook.xml.rels", workbook_rels),
                ("xl/styles.xml", styles),
                ("xl/sharedStrings.xml", sst),
                ("xl/worksheets/sheet1.xml", sheet)):
            info = zipfile.ZipInfo(name, date_time=fixed)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payload)
    return path


def main():
    rows = build_rows()
    csv_path = write_csv(rows, os.path.join(HERE, "northwind_sales.csv"))
    xlsx_path = write_xlsx(rows, os.path.join(HERE, "northwind_sales.xlsx"))

    revenue = sum(r["NetRevenue"] for r in rows)
    cogs = sum(r["CostOfGoods"] for r in rows)
    print("rows            : %d" % len(rows))
    print("months          : %d (%s .. %s)" % (
        MONTHS, rows[0]["OrderDate"].isoformat(), rows[-1]["OrderDate"].isoformat()))
    print("customers       : %d" % len({r["Customer"] for r in rows}))
    print("products        : %d" % len({r["Product"] for r in rows}))
    print("regions         : %d" % len({r["Region"] for r in rows}))
    print("salespeople     : %d" % len({r["Salesperson"] for r in rows}))
    print("total revenue   : %s %.2f" % (CURRENCY, revenue))
    print("total COGS      : %s %.2f" % (CURRENCY, cogs))
    print("gross margin    : %.2f%%" % ((revenue - cogs) / revenue * 100.0))
    print("csv             : %s" % csv_path)
    print("xlsx            : %s" % xlsx_path)


if __name__ == "__main__":
    main()
