"""Readers and the canonical Dataset (M2)."""

import datetime
import os
import shutil
import tempfile
import unittest
import zipfile

from bops import ingest
from bops.errors import ConfigError
from bops.ingest import readers
from bops.runtime import tiers

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO_CSV = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
DEMO_XLSX = os.path.join(REPO, "assets", "demo-data", "northwind_sales.xlsx")


class TestSerialDates(unittest.TestCase):
    def test_1900_system_with_leap_year_bug(self):
        self.assertEqual(readers.serial_to_date(45000), datetime.date(2023, 3, 15))

    def test_1904_system_differs(self):
        self.assertNotEqual(readers.serial_to_date(45000, use_1904=True),
                            readers.serial_to_date(45000))

    def test_fractional_serial_becomes_datetime(self):
        self.assertIsInstance(readers.serial_to_date(45000.5), datetime.datetime)


class TestNumberFormatResolution(unittest.TestCase):
    """The Tier 3 gap found during architecture review: built-in format ids."""

    def test_builtin_date_ids_recognised(self):
        for fmt_id in (14, 15, 16, 17, 22):
            self.assertTrue(readers._is_date_format(fmt_id, None), fmt_id)

    def test_builtin_percent_ids_recognised(self):
        for fmt_id in (9, 10):
            self.assertTrue(readers._is_percent_format(fmt_id, None), fmt_id)

    def test_plain_number_is_not_a_date(self):
        self.assertFalse(readers._is_date_format(0, None))
        self.assertFalse(readers._is_date_format(4, "#,##0.00"))

    def test_currency_symbol_extracted_from_format_code(self):
        self.assertEqual(readers._currency_of('"£"#,##0.00'), "£")
        self.assertEqual(readers._currency_of('"$"#,##0'), "$")
        self.assertIsNone(readers._currency_of("#,##0.00"))

    def test_quoted_literals_do_not_create_false_dates(self):
        self.assertFalse(readers._is_date_format(0, '"days"#,##0'))


class TestCsvReader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, text, name="t.csv", encoding="utf-8"):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding=encoding, newline="") as fh:
            fh.write(text)
        return path

    def test_types_are_coerced(self):
        path = self._write("D,N,F,T\n2025-01-15,42,3.5,hello\n")
        row = ingest.read_csv(path).rows[0]
        self.assertEqual(row["D"], datetime.date(2025, 1, 15))
        self.assertEqual(row["N"], 42)
        self.assertEqual(row["F"], 3.5)
        self.assertEqual(row["T"], "hello")

    def test_blank_becomes_none_not_zero(self):
        path = self._write("A,B\n,5\n")
        self.assertIsNone(ingest.read_csv(path).rows[0]["A"])

    def test_semicolon_delimiter_detected(self):
        path = self._write("A;B\n1;2\n")
        dataset = ingest.read_csv(path)
        self.assertEqual(dataset.columns, ["A", "B"])

    def test_blank_lines_skipped(self):
        path = self._write("A\n1\n\n2\n")
        self.assertEqual(ingest.read_csv(path).row_count, 2)

    def test_ragged_row_warns_rather_than_failing(self):
        path = self._write("A,B,C\n1,2\n")
        dataset = ingest.read_csv(path)
        self.assertIn("ragged_row", {w.code for w in dataset.warnings})

    def test_duplicate_headers_warn(self):
        path = self._write("A,A\n1,2\n")
        self.assertIn("duplicate_headers",
                      {w.code for w in ingest.read_csv(path).warnings})

    def test_non_utf8_falls_back_and_warns(self):
        path = os.path.join(self.tmp, "cp.csv")
        with open(path, "wb") as fh:
            fh.write("A\ncaf\xe9\n".encode("cp1252"))
        dataset = ingest.read_csv(path)
        self.assertIn("encoding_fallback", {w.code for w in dataset.warnings})

    def test_empty_file_raises(self):
        with self.assertRaises(ConfigError):
            ingest.read_csv(self._write(""))

    def test_missing_file_raises(self):
        with self.assertRaises(ConfigError):
            ingest.read_csv(os.path.join(self.tmp, "nope.csv"))

    def test_source_file_is_not_modified(self):
        path = self._write("A,B\n1,2\n")
        before = open(path, "rb").read()
        ingest.read_csv(path)
        self.assertEqual(open(path, "rb").read(), before)


class TestXlsxTier3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = ingest.read_xlsx(DEMO_XLSX, prefer_tier=tiers.TIER_STDLIB)

    def test_sheets_detected(self):
        self.assertEqual(self.dataset.sheets, ["Sales"])

    def test_headers_detected(self):
        self.assertEqual(self.dataset.columns[0], "OrderDate")
        self.assertEqual(len(self.dataset.columns), 12)

    def test_styled_date_cells_become_dates(self):
        self.assertIsInstance(self.dataset.rows[0]["OrderDate"], datetime.date)

    def test_inline_strings_read(self):
        self.assertIsInstance(self.dataset.rows[0]["Category"], str)

    def test_tier_recorded_on_dataset(self):
        self.assertEqual(self.dataset.reader_tier.tier, tiers.TIER_STDLIB)

    def test_bad_zip_raises_clearly(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "fake.xlsx")
            with open(path, "wb") as fh:
                fh.write(b"not a zip")
            with self.assertRaises(ConfigError) as caught:
                ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
            self.assertIn("readable .xlsx", str(caught.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_unknown_sheet_name_raises_and_lists_available(self):
        with self.assertRaises(ConfigError) as caught:
            ingest.read_xlsx(DEMO_XLSX, sheet_name="Nope",
                             prefer_tier=tiers.TIER_STDLIB)
        self.assertIn("Sales", str(caught.exception))


class TestFormulaHandling(unittest.TestCase):
    """Formulas are never evaluated, and a missing cached value is never invented."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _workbook(self, cell_xml):
        NS = readers.NS
        REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
        path = os.path.join(self.tmp, "f.xlsx")
        # Two columns: a populated Label plus the cell under test. Without the second
        # column an all-empty row is (correctly) skipped, so there would be nothing to
        # assert against.
        sheet = ('<?xml version="1.0"?><worksheet xmlns="%s"><sheetData>'
                 '<row r="1"><c r="A1" t="inlineStr"><is><t>Label</t></is></c>'
                 '<c r="B1" t="inlineStr"><is><t>Val</t></is></c></row>'
                 '<row r="2"><c r="A2" t="inlineStr"><is><t>row1</t></is></c>'
                 '%s</row></sheetData></worksheet>' % (NS, cell_xml))
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("[Content_Types].xml",
                       '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                       '<Default Extension="xml" ContentType="application/xml"/>'
                       '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                       '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                       '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
            z.writestr("_rels/.rels",
                       '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="rId1" Type="%s/officeDocument" Target="xl/workbook.xml"/></Relationships>' % REL)
            z.writestr("xl/workbook.xml",
                       '<?xml version="1.0"?><workbook xmlns="%s" xmlns:r="%s"><sheets>'
                       '<sheet name="S" sheetId="1" r:id="rId1"/></sheets></workbook>' % (NS, REL))
            z.writestr("xl/_rels/workbook.xml.rels",
                       '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="rId1" Type="%s/worksheet" Target="worksheets/sheet1.xml"/></Relationships>' % REL)
            z.writestr("xl/worksheets/sheet1.xml", sheet)
        return path

    def test_cached_formula_value_is_used(self):
        path = self._workbook('<c r="B2"><f>1+1</f><v>2</v></c>')
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        self.assertEqual(dataset.rows[0]["Val"], 2)

    def test_formula_without_cached_value_is_none_and_warns(self):
        path = self._workbook('<c r="B2"><f>1+1</f></c>')
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        self.assertIsNone(dataset.rows[0]["Val"])
        self.assertIn("formula_without_cached_value",
                      {w.code for w in dataset.warnings})

    def test_error_cell_becomes_none_and_warns(self):
        path = self._workbook('<c r="B2" t="e"><v>#DIV/0!</v></c>')
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        self.assertIsNone(dataset.rows[0]["Val"])
        self.assertIn("cell_error", {w.code for w in dataset.warnings})


class TestDispatchAndProvenance(unittest.TestCase):
    def test_unsupported_extension_raises(self):
        with self.assertRaises(ConfigError) as caught:
            ingest.read("something.pdf")
        message = str(caught.exception).lower()
        self.assertIn("unsupported file type", message)
        self.assertIn(".csv", message)      # names what IS supported

    def test_provenance_record_is_complete(self):
        provenance = ingest.read_csv(DEMO_CSV).provenance()
        for key in ("source_type", "source_path", "source_name", "rows",
                    "columns", "column_names", "warnings"):
            self.assertIn(key, provenance)
        self.assertEqual(provenance["source_type"], "csv")
        self.assertEqual(provenance["rows"], 2204)

    def test_xlsx_provenance_includes_reader_tier(self):
        dataset = ingest.read_xlsx(DEMO_XLSX, prefer_tier=tiers.TIER_STDLIB)
        self.assertIn("reader_tier", dataset.provenance())


if __name__ == "__main__":
    unittest.main()
