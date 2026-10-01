"""Workbook fixtures for cross-tier equivalence and adversarial data-layer tests.

Built at test time with the standard library, so each fixture is exactly the construct it
claims to be and no binary blobs are committed.
"""

import os
import zipfile

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

_CONTENT_TYPES_HEAD = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
    'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.spreadsheetml.styles+xml"/>'
    '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.'
    'openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>')

_ROOT_RELS = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.'
              'org/package/2006/relationships"><Relationship Id="rId1" Type="%s/'
              'officeDocument" Target="xl/workbook.xml"/></Relationships>' % REL)

# cellXfs: 0 general | 1 date (builtin 14) | 2 GBP custom | 3 percent (builtin 10)
#          4 datetime (builtin 22) | 5 unknown custom id
STYLES = (
    '<?xml version="1.0"?><styleSheet xmlns="%s">'
    '<numFmts count="2">'
    '<numFmt numFmtId="164" formatCode="&quot;£&quot;#,##0.00"/>'
    '<numFmt numFmtId="200" formatCode="[Blue]General"/>'
    '</numFmts>'
    '<fonts count="1"><font><sz val="11"/></font></fonts>'
    '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf/></cellStyleXfs>'
    '<cellXfs count="6">'
    '<xf numFmtId="0" xfId="0"/>'
    '<xf numFmtId="14" xfId="0" applyNumberFormat="1"/>'
    '<xf numFmtId="164" xfId="0" applyNumberFormat="1"/>'
    '<xf numFmtId="10" xfId="0" applyNumberFormat="1"/>'
    '<xf numFmtId="22" xfId="0" applyNumberFormat="1"/>'
    '<xf numFmtId="300" xfId="0" applyNumberFormat="1"/>'
    '</cellXfs></styleSheet>' % NS)


def _package(path, sheets, shared_strings, extra_parts=None, sheet_states=None,
             date_1904=False):
    """Assemble a workbook. `sheets` is [(name, sheetData xml)]."""
    states = sheet_states or {}
    overrides = "".join(
        '<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.'
        'openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1)
        for i in range(len(sheets)))
    content_types = _CONTENT_TYPES_HEAD + overrides + "</Types>"

    sheet_tags = "".join(
        '<sheet name="%s" sheetId="%d" r:id="rId%d"%s/>'
        % (name, i + 1, i + 1,
           (' state="%s"' % states[name]) if name in states else "")
        for i, (name, _xml) in enumerate(sheets))
    pr = '<workbookPr date1904="1"/>' if date_1904 else ""
    workbook = ('<?xml version="1.0"?><workbook xmlns="%s" xmlns:r="%s">%s<sheets>%s'
                '</sheets></workbook>' % (NS, REL, pr, sheet_tags))

    rels = ["<Relationship Id=\"rId%d\" Type=\"%s/worksheet\" Target=\"worksheets/"
            "sheet%d.xml\"/>" % (i + 1, REL, i + 1) for i in range(len(sheets))]
    rels.append('<Relationship Id="rIdS" Type="%s/styles" Target="styles.xml"/>' % REL)
    rels.append('<Relationship Id="rIdT" Type="%s/sharedStrings" '
                'Target="sharedStrings.xml"/>' % REL)
    workbook_rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.'
                     'openxmlformats.org/package/2006/relationships">%s</Relationships>'
                     % "".join(rels))

    sst = ('<?xml version="1.0"?><sst xmlns="%s" count="%d" uniqueCount="%d">%s</sst>'
           % (NS, len(shared_strings), len(shared_strings),
              "".join("<si><t>%s</t></si>" % s for s in shared_strings)))

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", _ROOT_RELS)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/styles.xml", STYLES)
        z.writestr("xl/sharedStrings.xml", sst)
        for i, (_name, xml) in enumerate(sheets):
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1),
                       '<?xml version="1.0"?><worksheet xmlns="%s"><sheetData>%s'
                       '</sheetData></worksheet>' % (NS, xml))
        for name, payload in (extra_parts or {}).items():
            z.writestr(name, payload)
    return path


def _header(names, shared_index):
    return ('<row r="1">%s</row>'
            % "".join('<c r="%s1" t="s"><v>%d</v></c>' % (chr(65 + i), shared_index[n])
                      for i, n in enumerate(names)))


# ---------------------------------------------------------------------------
# The cross-tier corpus
# ---------------------------------------------------------------------------

def rich_types(directory, name="rich_types.xlsx"):
    """Dates, currency, percentages, formulas, shared + inline strings, mixed types."""
    strings = ["Date", "Label", "Amount", "Rate", "Computed", "Stamp", "Mixed",
               "alpha", "beta"]
    index = {s: i for i, s in enumerate(strings)}
    rows = [_header(["Date", "Label", "Amount", "Rate", "Computed", "Stamp", "Mixed"],
                    index)]
    rows.append(
        '<row r="2">'
        '<c r="A2" s="1"><v>45000</v></c>'                       # styled date
        '<c r="B2" t="s"><v>%d</v></c>'                          # shared string
        '<c r="C2" s="2"><v>1234.56</v></c>'                     # GBP currency
        '<c r="D2" s="3"><v>0.352</v></c>'                       # percent
        '<c r="E2" s="2"><f>C2*2</f><v>2469.12</v></c>'          # formula, cached
        '<c r="F2" s="4"><v>45000.5</v></c>'                     # datetime
        '<c r="G2" t="inlineStr"><is><t>inline</t></is></c>'     # inline string
        '</row>' % index["alpha"])
    rows.append(
        '<row r="3">'
        '<c r="A3" s="1"><v>45031</v></c>'
        '<c r="B3" t="s"><v>%d</v></c>'
        '<c r="C3" s="2"><v>987.65</v></c>'
        '<c r="D3" s="3"><v>0.410</v></c>'
        '<c r="E3" s="2"><f>C3*2</f><v>1975.30</v></c>'
        '<c r="F3" s="4"><v>45031.25</v></c>'
        '<c r="G3"><v>42</v></c>'                                # number in a text column
        '</row>' % index["beta"])
    return _package(os.path.join(directory, name), [("Data", "".join(rows))], strings)


def multi_sheet(directory, name="multi_sheet.xlsx"):
    """Two sheets; the second is hidden."""
    strings = ["Date", "Amount", "Secret"]
    index = {s: i for i, s in enumerate(strings)}
    first = (_header(["Date", "Amount"], index)
             + '<row r="2"><c r="A2" s="1"><v>45000</v></c>'
               '<c r="B2" s="2"><v>100.00</v></c></row>')
    second = ('<row r="1"><c r="A1" t="s"><v>%d</v></c></row>'
              '<row r="2"><c r="A2"><v>1</v></c></row>' % index["Secret"])
    return _package(os.path.join(directory, name),
                    [("Visible", first), ("Hidden", second)], strings,
                    sheet_states={"Hidden": "hidden"})


def empty_rows_and_missing(directory, name="gaps.xlsx"):
    """Blank rows and missing cells."""
    strings = ["Date", "Amount"]
    index = {s: i for i, s in enumerate(strings)}
    body = (_header(["Date", "Amount"], index)
            + '<row r="2"><c r="A2" s="1"><v>45000</v></c>'
              '<c r="B2" s="2"><v>10.00</v></c></row>'
            + '<row r="3"></row>'
            + '<row r="4"><c r="A4" s="1"><v>45031</v></c></row>')
    return _package(os.path.join(directory, name), [("Data", body)], strings)


def duplicate_headers(directory, name="dup_headers.xlsx"):
    strings = ["Amount"]
    index = {s: i for i, s in enumerate(strings)}
    body = ('<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>0</v></c></row>'
            '<row r="2"><c r="A2"><v>1</v></c><c r="B2"><v>2</v></c></row>')
    return _package(os.path.join(directory, name), [("Data", body)], strings)


def date_1904_system(directory, name="date1904.xlsx"):
    strings = ["Date"]
    index = {s: i for i, s in enumerate(strings)}
    body = (_header(["Date"], index)
            + '<row r="2"><c r="A2" s="1"><v>43000</v></c></row>')
    return _package(os.path.join(directory, name), [("Data", body)], strings,
                    date_1904=True)


def unknown_number_format(directory, name="unknown_format.xlsx"):
    """numFmt id 300 is declared nowhere, so the reader cannot resolve it: warn, never
    guess it into a date or percentage."""
    strings = ["Value"]
    index = {s: i for i, s in enumerate(strings)}
    body = (_header(["Value"], index)
            + '<row r="2"><c r="A2" s="5"><v>123</v></c></row>')
    return _package(os.path.join(directory, name), [("Data", body)], strings)


CORPUS = (
    ("rich_types", rich_types),
    ("multi_sheet", multi_sheet),
    ("gaps", empty_rows_and_missing),
    ("duplicate_headers", duplicate_headers),
    ("date_1904", date_1904_system),
    ("unknown_format", unknown_number_format),
)


# ---------------------------------------------------------------------------
# Adversarial fixtures
# ---------------------------------------------------------------------------

def formula_without_cached_value(directory, name="no_cache.xlsx"):
    strings = ["Label", "Value"]
    index = {s: i for i, s in enumerate(strings)}
    body = (_header(["Label", "Value"], index)
            + '<row r="2"><c r="A2" t="inlineStr"><is><t>row</t></is></c>'
              '<c r="B2"><f>1+1</f></c></row>')
    return _package(os.path.join(directory, name), [("Data", body)], strings)


def external_reference(directory, name="external.xlsx"):
    """A formula pointing at another workbook. Must never be followed."""
    strings = ["Label", "Value"]
    index = {s: i for i, s in enumerate(strings)}
    body = (_header(["Label", "Value"], index)
            + '<row r="2"><c r="A2" t="inlineStr"><is><t>row</t></is></c>'
              '<c r="B2"><f>[1]Sheet1!A1</f><v>99</v></c></row>')
    extra = {"xl/externalLinks/externalLink1.xml":
             '<?xml version="1.0"?><externalLink xmlns="%s"/>' % NS}
    return _package(os.path.join(directory, name), [("Data", body)], strings,
                    extra_parts=extra)


def macro_enabled(directory, name="macro.xlsm"):
    strings = ["Value"]
    index = {s: i for i, s in enumerate(strings)}
    body = (_header(["Value"], index) + '<row r="2"><c r="A2"><v>1</v></c></row>')
    return _package(os.path.join(directory, name), [("Data", body)], strings,
                    extra_parts={"xl/vbaProject.bin": b"\x00fake macro payload"})


def shared_formula(directory, name="shared_formula.xlsx"):
    strings = ["Label", "Value"]
    index = {s: i for i, s in enumerate(strings)}
    body = (_header(["Label", "Value"], index)
            + '<row r="2"><c r="A2" t="inlineStr"><is><t>a</t></is></c>'
              '<c r="B2"><f t="shared" ref="B2:B3" si="0">A2*2</f><v>2</v></c></row>'
            + '<row r="3"><c r="A3" t="inlineStr"><is><t>b</t></is></c>'
              '<c r="B3"><f t="shared" si="0"/><v>4</v></c></row>')
    return _package(os.path.join(directory, name), [("Data", body)], strings)


def encrypted(directory, name="encrypted.xlsx"):
    """An OLE container, which is what a password-protected .xlsx actually is."""
    path = os.path.join(directory, name)
    with open(path, "wb") as fh:
        fh.write(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 500)
    return path


def corrupt_zip(directory, name="corrupt.xlsx"):
    path = os.path.join(directory, name)
    with open(path, "wb") as fh:
        fh.write(b"PK\x03\x04 this is not a real archive")
    return path


def malformed_xml(directory, name="malformed.xlsx"):
    """Valid zip, truncated worksheet XML."""
    path = os.path.join(directory, name)
    _package(path, [("Data", '<row r="1"><c r="A1"><v>1</v></c></row>')], ["Value"])
    # Rewrite the package with a deliberately truncated sheet part.
    import shutil
    good = path + ".good"
    shutil.move(path, good)
    with zipfile.ZipFile(good) as src, zipfile.ZipFile(path, "w") as dst:
        for item in src.infolist():
            payload = src.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                payload = b'<?xml version="1.0"?><worksheet><sheetData><row><c>'
            dst.writestr(item.filename, payload)
    os.remove(good)
    return path


def mixed_currency_csv(directory, name="mixed_currency.csv"):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("OrderDate,NetRevenue\n")
        fh.write("2025-01-15,£1000.00\n")
        fh.write("2025-02-15,$1200.00\n")
        fh.write("2025-03-15,£900.00\n")
    return path


def ambiguous_numbers_csv(directory, name="ambiguous_numbers.csv"):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("OrderDate,NetRevenue\n")
        for month in range(1, 5):
            fh.write("2025-%02d-15,1.234\n" % month)
    return path
