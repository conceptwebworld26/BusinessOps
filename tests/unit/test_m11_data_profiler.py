# -*- coding: utf-8 -*-
"""M11 data profiler (ADR-0036).

`bops.data_profile` is the engine. These tests run it over genuine files - synthetic CSVs and
workbooks written to a temporary directory, and the shipped synthetic demo data - through the real
Data Layer, Data Quality, KPI engine and command registry. Nothing is mocked except where a test
needs a source to change mid-read.

What gets the most attention:

* **Closed request.** Anything outside `sources`, `sheets`, `objective`, `presentation` is refused
  whole; nothing is truncated.
* **Privacy.** Canary values planted in customer, transaction, restricted, identifier and hidden
  fields never appear in the JSON, the rendered text, an exception or captured output.
* **Exact counts, labelled facts.** Counts are exact over every row; inferred facts state their
  sample; the distinct cap yields `null`, never an estimate.
* **Reference, never re-decide.** Quality, KPI and command entries equal what M4, M5 and the
  registry decide, with every value, message and outcome dropped.
* **Bound and inert.** Same inputs, same bytes and id; a changed source refuses to serialise; no
  part of a profile enters synthesis.

**Every fixture is synthetic.**
"""

import contextlib
import copy
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"), os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import data_profile as P                          # noqa: E402
from bops import jsonschema_mini                            # noqa: E402
from bops import mapping as mapping_mod                     # noqa: E402
from bops import synthesis as S                             # noqa: E402
from bops.commands import registry as command_registry      # noqa: E402
from bops.errors import ConfigError                         # noqa: E402
from bops.ingest import canonical as canonical_mod          # noqa: E402
from bops.ingest import readers                             # noqa: E402
from bops.kpi import registry as kpi_registry               # noqa: E402
from bops.privacy import sensitivity as sensitivity_mod     # noqa: E402
from bops.quality import checks as quality_checks           # noqa: E402
from fixtures import build_workbooks as W                  # noqa: E402

DEMO_CSV = os.path.join(REPO_ROOT, "assets", "demo-data", "northwind_sales.csv")
DEMO_XLSX = os.path.join(REPO_ROOT, "assets", "demo-data", "northwind_sales.xlsx")
DEMO_CONTEXT = os.path.join(REPO_ROOT, "assets", "demo-data", "business_context.json")

#: Planted in every kind of field a profile must never reveal. Each is distinctive enough that its
#: appearance anywhere is a leak, never a coincidence.
CANARIES = ("Zyxcanary Holdings", "wren.canary@example-canary.test", "ORD-CANARY-7731",
            "Quokkafizz Deluxe", "98765.43", "Wombatshire", "Pangolinmemo", "HIDDENPAYROLL-4412",
            "+44 7700 900123", "SKU-CANARY-5519")

_TMP = {}


def setUpModule():
    _TMP["root"] = tempfile.mkdtemp(prefix="bops-profile-")


def tearDownModule():
    shutil.rmtree(_TMP["root"], ignore_errors=True)


def tmpdir():
    return tempfile.mkdtemp(dir=_TMP["root"])


def write_csv(directory, name, header, rows):
    path = os.path.join(directory, name)
    with io.open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(header) + "\n")
        for row in rows:
            handle.write(",".join(str(cell) for cell in row) + "\n")
    return path


def _cell(ref, value):
    if isinstance(value, tuple) and value[0] == "date":
        return '<c r="%s" s="1"><v>%d</v></c>' % (ref, value[1])
    if isinstance(value, (int, float)):
        return '<c r="%s"><v>%s</v></c>' % (ref, value)
    return '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, value)


def sheet_xml(header, rows):
    lines = []
    for number, values in enumerate([header] + list(rows), start=1):
        lines.append('<row r="%d">%s</row>' % (number, "".join(
            _cell("%s%d" % (chr(65 + i), number), v) for i, v in enumerate(values))))
    return "".join(lines)


def workbook(directory, name, sheets, states=None, extra_parts=None):
    """`sheets` is [(name, header, rows)] or [(name, raw xml)]."""
    parts = []
    for sheet in sheets:
        parts.append((sheet[0], sheet[1] if len(sheet) == 2 else sheet_xml(sheet[1], sheet[2])))
    return W._package(os.path.join(directory, name), parts, [], extra_parts=extra_parts,
                      sheet_states=states)


def canary_csv(directory, name="canary.csv"):
    header = ["OrderDate", "OrderID", "Customer", "ContactEmail", "Region", "Product",
              "NetRevenue", "Notes", "ProductCode"]
    rows = []
    for i in range(12):
        rows.append(["2025-%02d-15" % (i + 1), "ORD-CANARY-7731" if i == 0 else "ORD-%04d" % i,
                     "Zyxcanary Holdings" if i % 2 else "Other Buyer %d" % i,
                     "wren.canary@example-canary.test" if i == 3 else "person%d@example.test" % i,
                     "Wombatshire" if i % 3 == 0 else "Northfield",
                     "Quokkafizz Deluxe" if i % 2 else "quokkafizz deluxe",
                     "98765.43" if i == 5 else "%d.50" % (100 + i),
                     "Pangolinmemo %d" % i if i else "+44 7700 900123",
                     "SKU-CANARY-5519" if i == 7 else "SKU-%04d" % i])
    return write_csv(directory, name, header, rows)


def build(request, **kwargs):
    kwargs.setdefault("load_context_files", False)
    return P.build(request, **kwargs)


def refused(test, request, **kwargs):
    with test.assertRaises(P.DataProfileError) as caught:
        build(request, **kwargs)
    return str(caught.exception)


def demo_context():
    with io.open(DEMO_CONTEXT, encoding="utf-8") as handle:
        return json.load(handle)


def dataset(doc, index=0):
    return doc["datasets"][index]


def column(doc, name, index=0):
    for entry in dataset(doc, index)["columns"]:
        if entry["original_name"] == name:
            return entry
    raise AssertionError("no column %s" % name)


def limitation_codes(doc):
    return [entry["code"] for entry in doc["limitations"]]


# =================================================================================================
# Request
# =================================================================================================

class RequestValidation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = tmpdir()
        cls.csv = write_csv(cls.dir, "a.csv", ["Region", "Amount"], [["North", 1], ["South", 2]])
        cls.book = workbook(cls.dir, "b.xlsx", [("Data", ["Region", "Amount"], [["North", 1]])])

    def test_a_valid_request_is_accepted_with_the_default_presentation(self):
        accepted = P.validate_request({"sources": [self.csv]})
        self.assertEqual(accepted, {"sources": [self.csv], "presentation": "local"})
        self.assertEqual(build({"sources": [self.csv]}).status, P.COMPLETE_WITH_LIMITATIONS)

    def test_missing_and_empty_sources_are_refused(self):
        refused(self, {})
        refused(self, {"sources": []})
        refused(self, {"sources": self.csv})

    def test_more_than_twenty_sources_are_refused_not_truncated(self):
        directory = tmpdir()
        paths = [write_csv(directory, "s%02d.csv" % i, ["A"], [[i]]) for i in range(21)]
        message = refused(self, {"sources": paths})
        self.assertIn("none is dropped", message)
        self.assertEqual(len(build({"sources": paths[:20]}).as_dict()["sources"]), 20)

    def test_duplicate_sources_are_refused_however_spelled(self):
        refused(self, {"sources": [self.csv, self.csv]})
        refused(self, {"sources": [self.csv, os.path.join(self.dir, ".", "a.csv")]})

    def test_the_same_name_and_bytes_in_two_folders_is_a_duplicate(self):
        other = tmpdir()
        copy_path = os.path.join(other, "a.csv")
        shutil.copyfile(self.csv, copy_path)
        refused(self, {"sources": [self.csv, copy_path]})

    def test_duplicate_sheet_requests_are_refused(self):
        refused(self, {"sources": [self.book], "sheets": {self.book: ["Data", "Data"]}})

    def test_urls_schemes_and_stdin_are_refused(self):
        for source in ("https://example.com/data.csv", "file:///tmp/data.csv",
                       "s3://bucket/data.csv", "-"):
            refused(self, {"sources": [source]})

    def test_folders_globs_missing_files_and_other_extensions_are_refused(self):
        refused(self, {"sources": [self.dir]})
        refused(self, {"sources": [os.path.join(self.dir, "*.csv")]})
        refused(self, {"sources": [os.path.join(self.dir, "missing.csv")]})
        json_path = os.path.join(self.dir, "data.json")
        with open(json_path, "w") as handle:
            handle.write("{}")
        refused(self, {"sources": [json_path]})

    def test_unknown_fields_and_caller_supplied_facts_are_refused(self):
        for field in ("statistics", "row_count", "distinct_count", "kind", "sensitivity",
                      "classification", "role", "quality_grade", "applicability", "confidence",
                      "score", "rank", "priority", "profile_id", "metadata", "trust"):
            message = refused(self, {"sources": [self.csv], field: 1})
            self.assertIn(field, message)

    def test_a_supplied_profile_object_or_its_dict_is_refused(self):
        genuine = build({"sources": [self.csv]})
        refused(self, genuine)
        refused(self, genuine.as_dict())
        refused(self, {"sources": [self.csv], "profile": genuine.as_dict()})

    def test_objective_accepts_only_closed_ids(self):
        refused(self, {"sources": [self.csv], "objective": {"command_id": "not-a-command"}})
        refused(self, {"sources": [self.csv], "objective": {"kpi_ids": ["not_a_kpi"]}})
        refused(self, {"sources": [self.csv], "objective": {"kpi_ids": ["revenue", "revenue"]}})
        refused(self, {"sources": [self.csv], "objective": {"question": "how are sales?"}})
        refused(self, {"sources": [self.csv], "objective": {}})
        refused(self, {"sources": [self.csv], "objective": "sales-analysis"})

    def test_presentation_is_closed(self):
        refused(self, {"sources": [self.csv], "presentation": "public"})

    def test_sheets_must_name_a_workbook_in_sources_and_an_existing_sheet(self):
        refused(self, {"sources": [self.csv], "sheets": {self.csv: ["Data"]}})
        refused(self, {"sources": [self.csv], "sheets": {self.book: ["Data"]}})
        refused(self, {"sources": [self.book], "sheets": {self.book: ["Absent"]}})
        refused(self, {"sources": [self.book], "sheets": {self.book: []}})

    def test_refusal_messages_never_echo_supplied_values(self):
        message = refused(self, {"sources": ["https://ORD-CANARY-7731.example/x.csv"]})
        self.assertNotIn("ORD-CANARY-7731", message)
        message = refused(self, {"sources": [self.csv], "objective": {"kpi_ids": ["Zyxcanary"]}})
        self.assertNotIn("Zyxcanary", message)


# =================================================================================================
# Workbooks, sheets and sources
# =================================================================================================

class WorkbookCoverage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = tmpdir()
        cls.book = workbook(cls.dir, "book.xlsx", [
            ("Sales", ["Region", "Amount"], [["North", 10], ["South", 20]]),
            ("Payroll", ["Employee", "Salary"], [["HIDDENPAYROLL-4412", 55555]]),
            ("Costs", ["Region", "Cost"], [["North", 4]]),
        ], states={"Payroll": "hidden"})

    def test_every_visible_sheet_is_profiled_in_workbook_order(self):
        doc = build({"sources": [self.book]}).as_dict()
        self.assertEqual([d["sheet"] for d in doc["datasets"]], ["Sales", "Costs"])
        self.assertIn(P.HIDDEN_SHEET_NOT_PROFILED, limitation_codes(doc))
        sheets = doc["sources"][0]["workbook"]["sheets"]
        self.assertEqual(sheets, [{"name": "Sales", "visibility": "visible"},
                                  {"name": "Payroll", "visibility": "hidden"},
                                  {"name": "Costs", "visibility": "visible"}])

    def test_an_unnamed_hidden_sheet_is_never_read(self):
        with mock.patch.object(P.readers, "read", wraps=readers.read) as spy:
            result = build({"sources": [self.book]})
        self.assertEqual([c.kwargs["sheet_name"] for c in spy.call_args_list], ["Sales", "Costs"])
        text = result.to_json() + P.render(result)
        self.assertNotIn("HIDDENPAYROLL-4412", text)
        self.assertNotIn("Employee", text)

    def test_a_named_hidden_sheet_is_profiled_without_its_values(self):
        result = build({"sources": [self.book], "sheets": {self.book: ["Payroll"]}})
        doc = result.as_dict()
        self.assertEqual([d["sheet"] for d in doc["datasets"]], ["Payroll"])
        self.assertIn("hidden_sheet_read", dataset(doc)["warning_codes"]["value"])
        self.assertNotIn(P.HIDDEN_SHEET_NOT_PROFILED, limitation_codes(doc))
        text = result.to_json() + P.render(result)
        self.assertNotIn("HIDDENPAYROLL-4412", text)
        self.assertNotIn("55555", text)

    def test_differing_headers_across_profiled_sheets_are_a_limitation(self):
        doc = build({"sources": [self.book]}).as_dict()
        self.assertIn(P.INCONSISTENT_HEADERS_ACROSS_SHEETS, limitation_codes(doc))

    def test_multiple_files_are_profiled_in_request_order(self):
        csv = write_csv(tmpdir(), "z.csv", ["Region"], [["North"]])
        doc = build({"sources": [csv, self.book]}).as_dict()
        self.assertEqual([s["source_name"] for s in doc["sources"]], ["z.csv", "book.xlsx"])
        self.assertEqual([d["source_ref"] for d in doc["datasets"]],
                         [doc["sources"][0]["source_ref"]] + [doc["sources"][1]["source_ref"]] * 2)

    def test_macros_are_observed_never_executed(self):
        path = W.macro_enabled(tmpdir())
        doc = build({"sources": [path]}).as_dict()
        self.assertTrue(doc["sources"][0]["workbook"]["macro_enabled"])
        self.assertIn(P.MACRO_ENABLED_NOT_EXECUTED, limitation_codes(doc))

    def test_external_links_are_counted_never_followed(self):
        path = W.external_reference(tmpdir())
        doc = build({"sources": [path]}).as_dict()
        self.assertEqual(doc["sources"][0]["workbook"]["external_link_count"], 1)
        self.assertIn(P.EXTERNAL_LINKS_NOT_FOLLOWED, limitation_codes(doc))

    def test_an_encrypted_workbook_is_unavailable_with_csv_guidance(self):
        path = W.encrypted(tmpdir())
        result = build({"sources": [path]})
        doc = result.as_dict()
        self.assertEqual(doc["status"], P.UNAVAILABLE)
        self.assertEqual((doc["sources"][0]["status"], doc["sources"][0]["reason_code"],
                          doc["sources"][0]["guidance"]),
                         (P.UNAVAILABLE, P.ENCRYPTED, P.CSV_EXPORT_GUIDANCE))
        self.assertEqual(doc["datasets"], [])
        self.assertIn("export", P.render(result).lower())

    def test_one_unreadable_source_makes_the_profile_partial(self):
        good = write_csv(tmpdir(), "good.csv", ["Region"], [["North"]])
        doc = build({"sources": [good, W.corrupt_zip(tmpdir())]}).as_dict()
        self.assertEqual(doc["status"], P.PARTIAL)
        self.assertEqual(doc["sources"][1]["reason_code"], P.MALFORMED)

    def test_a_malformed_sheet_is_an_unavailable_dataset(self):
        doc = build({"sources": [W.malformed_xml(tmpdir())]}).as_dict()
        self.assertEqual(doc["status"], P.UNAVAILABLE)
        self.assertEqual((dataset(doc)["status"], dataset(doc)["reason_code"]),
                         (P.UNAVAILABLE, P.MALFORMED))

    def test_a_reader_refusal_is_reader_refused_never_a_fabricated_profile(self):
        path = workbook(tmpdir(), "t4.xlsx", [("Data", ["A"], [[1]])])
        doc = build({"sources": [path]}, prefer_tier=4).as_dict()
        self.assertEqual(doc["status"], P.UNAVAILABLE)
        self.assertEqual(doc["sources"][0]["reason_code"], P.READER_REFUSED)
        self.assertEqual(doc["sources"][0]["guidance"], P.CSV_EXPORT_GUIDANCE)
        self.assertEqual(dataset(doc)["columns"], [])

    def test_an_empty_sheet_has_no_columns(self):
        path = workbook(tmpdir(), "empty.xlsx", [("Data", ["A"], [[1]]), ("Blank", "")])
        doc = build({"sources": [path]}).as_dict()
        self.assertEqual(doc["status"], P.PARTIAL)
        self.assertEqual(dataset(doc, 1)["reason_code"], P.NO_COLUMNS)

    def test_an_empty_csv_is_empty_file(self):
        path = os.path.join(tmpdir(), "empty.csv")
        open(path, "w").close()
        doc = build({"sources": [path]}).as_dict()
        self.assertEqual(doc["sources"][0]["reason_code"], P.EMPTY_FILE)

    def test_a_source_changed_during_the_read_is_unavailable_and_unprofiled(self):
        path = write_csv(tmpdir(), "moving.csv", ["Region", "Amount"], [["North", 1]])
        real_read = readers.read

        def read_then_change(*args, **kwargs):
            outcome = real_read(*args, **kwargs)
            with open(path, "a") as handle:
                handle.write("South,2\n")
            return outcome

        with mock.patch.object(P.readers, "read", side_effect=read_then_change):
            result = build({"sources": [path]})
        doc = result.as_dict()
        self.assertEqual(doc["status"], P.UNAVAILABLE)
        self.assertEqual(doc["sources"][0]["reason_code"], P.CHANGED_DURING_PROFILE)
        self.assertEqual(doc["datasets"], [])

    def test_every_reader_refusal_message_maps_to_its_closed_code(self):
        """Pins `_READER_REASONS` against the Data Layer's real messages."""
        directory = tmpdir()
        existing = write_csv(directory, "x.csv", ["A"], [[1]])
        empty_csv = os.path.join(directory, "empty.csv")
        open(empty_csv, "w").close()
        blank_sheet = workbook(directory, "blank.xlsx", [("Blank", "")])
        tier4 = workbook(directory, "tier4.xlsx", [("Data", ["A"], [[1]])])
        cases = (
            (lambda: readers.read(empty_csv), P.EMPTY_FILE),
            (lambda: readers.read(W.encrypted(directory)), P.ENCRYPTED),
            (lambda: readers.read(W.corrupt_zip(directory)), P.MALFORMED),
            (lambda: readers.read(W.malformed_xml(directory)), P.MALFORMED),
            (lambda: readers.read(blank_sheet, sheet_name="Blank"), P.NO_COLUMNS),
            (lambda: readers.read(tier4, prefer_tier=4), P.READER_REFUSED),
            (lambda: readers.read(tier4, prefer_tier=1), P.READER_REFUSED),
        )
        for action, code in cases:
            try:
                action()
            except Exception as exc:                       # the real reader's refusal
                self.assertEqual(P._reason_for(exc, existing), code, str(type(exc)))
            else:
                if code == P.READER_REFUSED:               # Tier 1 present on this machine
                    continue
                self.fail("the reader did not refuse (%s)" % code)
        self.assertEqual(P._reason_for(
            ConfigError("could not decode file with any supported encoding"), existing),
            P.UNSUPPORTED_ENCODING)
        self.assertEqual(P._reason_for(ConfigError("sheet 'file is empty' contains malformed XML"),
                                       existing), P.MALFORMED)
        self.assertEqual(P._reason_for(ConfigError("something unforeseen"), existing),
                         P.UNREADABLE)
        self.assertEqual(P._reason_for(ConfigError("file is empty"),
                                       os.path.join(directory, "gone.csv")), P.UNREADABLE)


# =================================================================================================
# Counts, dates and the distinct cap
# =================================================================================================

class Counts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = tmpdir()
        cls.path = write_csv(cls.dir, "counts.csv",
                             ["OrderDate", "Region", "Code", "Units"],
                             [["2025-01-15", "North", "A1", 1],
                              ["2025-01-20", "", "A2", 2],
                              ["2025-03-02", "n/a", "A3", 2],
                              ["2025-03-09", "North", "A4", ""],
                              ["2025-04-30", "South", "A5", 5]])
        cls.doc = build({"sources": [cls.path]}).as_dict()

    def test_non_null_and_empty_counts_are_exact(self):
        region = column(self.doc, "Region")["facts"]
        self.assertEqual((region["non_null_count"]["value"], region["empty_count"]["value"]),
                         (3, 2))
        self.assertEqual(region["non_null_count"]["examined"], 5)
        units = column(self.doc, "Units")["facts"]
        self.assertEqual((units["non_null_count"]["value"], units["empty_count"]["value"]), (4, 1))

    def test_distinct_and_uniqueness_are_exact(self):
        region = column(self.doc, "Region")["facts"]
        self.assertEqual(region["distinct_count"]["value"], 2)
        self.assertEqual(region["uniqueness_rate"]["value"], "0.6667")
        self.assertIsNone(region["distinct_at_least"]["value"])
        code = column(self.doc, "Code")["facts"]
        self.assertEqual((code["distinct_count"]["value"], code["uniqueness_rate"]["value"]),
                         (5, "1.0000"))

    def test_date_coverage_states_bounds_and_months(self):
        coverage = column(self.doc, "OrderDate")["facts"]["date_coverage"]
        self.assertEqual(coverage["value"], {"first": "2025-01-15", "last": "2025-04-30",
                                             "period_count": 3})
        self.assertEqual((coverage["basis"], coverage["examined"]), (P.CALCULATED, 5))
        self.assertIsNone(column(self.doc, "Region")["facts"]["date_coverage"])

    def test_the_distinct_cap_yields_null_never_an_estimate(self):
        with mock.patch.object(P, "DISTINCT_CAP", 3):
            doc = build({"sources": [self.path, write_csv(
                tmpdir(), "other.csv", ["Code"], [["A1"], ["A2"]])]}).as_dict()
        code = column(doc, "Code")["facts"]
        self.assertIsNone(code["distinct_count"]["value"])
        self.assertEqual(code["distinct_at_least"]["value"], 4)
        self.assertIsNone(code["uniqueness_rate"]["value"])
        self.assertEqual(doc["limits"]["distinct_cap"], 3)
        self.assertIn({"code": P.DISTINCT_COUNT_CAPPED, "subject_ref": column(doc, "Code")["column_ref"],
                       "reason": P.LIMITATION_TEXT[P.DISTINCT_COUNT_CAPPED]}, doc["limitations"])
        refs = {r["left"] for r in doc["relationships"]} | {r["right"] for r in doc["relationships"]}
        self.assertNotIn(column(doc, "Code")["column_ref"], refs)

    def test_large_files_are_counted_exactly_while_inference_states_its_sample(self):
        rows = [["2024-%02d-01" % (i % 12 + 1), "R%d" % (i % 7), i] for i in range(1500)]
        rows[1499][1] = ""
        doc = build({"sources": [write_csv(tmpdir(), "large.csv", ["OrderDate", "Region", "Seq"],
                                           rows)]}).as_dict()
        region = column(doc, "Region")["facts"]
        self.assertEqual(region["non_null_count"]["value"], 1499)
        self.assertEqual(region["distinct_count"]["value"], 7)
        self.assertEqual(region["kind"]["examined"], P.KIND_SAMPLE)
        self.assertEqual(region["sensitivity"]["examined"], P.SENSITIVITY_SAMPLE)
        self.assertEqual(column(doc, "Seq")["facts"]["distinct_count"]["value"], 1500)
        self.assertEqual(dataset(doc)["row_count"]["value"], 1500)
        self.assertIn(P.SAMPLED_INFERENCE, limitation_codes(doc))

    def test_header_only_and_dateless_data_are_limitations(self):
        doc = build({"sources": [write_csv(tmpdir(), "header.csv", ["Region", "Amount"], [])]}
                    ).as_dict()
        self.assertEqual(dataset(doc)["row_count"]["value"], 0)
        self.assertIn(P.NO_ROWS, limitation_codes(doc))
        self.assertIn(P.NO_DATE_COLUMN, limitation_codes(doc))
        self.assertEqual(doc["status"], P.COMPLETE_WITH_LIMITATIONS)

    def test_mixed_types_are_a_limitation(self):
        doc = build({"sources": [write_csv(tmpdir(), "mixed.csv", ["Value"],
                                           [[1], ["text"], [3], ["more"]])]}).as_dict()
        self.assertTrue(column(doc, "Value")["facts"]["mixed_types"]["value"])
        self.assertIn(P.MIXED_TYPES, limitation_codes(doc))

    def test_no_total_average_minimum_or_maximum_of_a_figure_exists(self):
        text = json.dumps(self.doc)
        for forbidden in ('"sum"', '"total"', '"mean"', '"average"', '"median"', '"min"',
                          '"max"', '"top_values"', '"sample"', '"rank"', '"score"'):
            self.assertNotIn(forbidden, text)


# =================================================================================================
# Keys
# =================================================================================================

class Keys(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        directory = tmpdir()
        cls.left = write_csv(directory, "left.csv", ["LineRef", "Product", "OrderID"],
                             [["L1", "Quokkafizz Deluxe", "O1"], ["L2", "Beta", "O2"],
                              ["L3", "Gamma", "O3"], ["L4", "Beta", "O4"]])
        cls.right = write_csv(directory, "right.csv", ["Product", "OrderID"],
                              [["Beta", "O2"], ["Gamma", "O3"], ["Delta", "O9"]])
        cls.result = build({"sources": [cls.left, cls.right]})
        cls.doc = cls.result.as_dict()

    def test_unique_non_null_and_mapped_role_candidates(self):
        rules = {c["column_ref"]: c["rule"] for c in dataset(self.doc)["key_candidates"]}
        self.assertEqual(rules[column(self.doc, "LineRef")["column_ref"]], P.UNIQUE_NON_NULL)
        self.assertEqual(rules[column(self.doc, "Product")["column_ref"]], P.MAPPED_ROLE)
        for candidate in dataset(self.doc)["key_candidates"]:
            self.assertEqual((candidate["basis"], candidate["status"]), (P.CALCULATED, P.CANDIDATE))

    def test_overlap_is_a_jaccard_rate_between_eligible_candidates(self):
        left_product = column(self.doc, "Product")["column_ref"]
        right_product = column(self.doc, "Product", 1)["column_ref"]
        pairs = {(r["left"], r["right"]): r for r in self.doc["relationships"]}
        overlap = pairs[(left_product, right_product)]
        self.assertEqual(overlap["overlap_rate"], "0.5000")      # {Beta, Gamma} / 4 distinct
        self.assertEqual((overlap["basis"], overlap["status"]), (P.CALCULATED, P.CANDIDATE))

    def test_restricted_key_columns_take_part_in_no_overlap(self):
        order_refs = {column(self.doc, "OrderID")["column_ref"],
                      column(self.doc, "OrderID", 1)["column_ref"]}
        self.assertEqual(column(self.doc, "OrderID")["facts"]["sensitivity"]["value"]["class"],
                         "restricted")
        for relationship in self.doc["relationships"]:
            self.assertFalse({relationship["left"], relationship["right"]} & order_refs)

    def test_no_key_value_appears_and_the_order_is_deterministic(self):
        text = self.result.to_json() + P.render(self.result)
        for value in ("Quokkafizz Deluxe", "Gamma", "Delta", "L3", "O9"):
            self.assertNotIn(value, text)
        again = build({"sources": [self.left, self.right]}).as_dict()
        self.assertEqual(again["relationships"], self.doc["relationships"])


# =================================================================================================
# Fact bases
# =================================================================================================

CALCULATED_FACTS = ("non_null_count", "empty_count", "distinct_count", "distinct_at_least",
                    "uniqueness_rate", "date_coverage")
INFERRED_FACTS = ("kind", "kind_counts", "mixed_types", "ambiguous_count", "currencies",
                  "day_first", "sensitivity", "role")
OBSERVED_DATASET_FACTS = ("reader_tier", "row_count", "column_count", "processing_mode",
                          "rows_examined", "complete", "warning_codes")


class FactBases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.doc = build({"sources": [DEMO_CSV, DEMO_XLSX]}).as_dict()

    def test_every_fact_carries_the_basis_the_contract_assigns(self):
        for entry in self.doc["datasets"]:
            for name in OBSERVED_DATASET_FACTS:
                self.assertEqual(entry[name]["basis"], P.OBSERVED, name)
            self.assertEqual(entry["duplicate_headers"]["basis"], P.CALCULATED)
            for col in entry["columns"]:
                self.assertEqual(set(col["facts"]), set(CALCULATED_FACTS + INFERRED_FACTS))
                for name in CALCULATED_FACTS:
                    if col["facts"][name] is not None:
                        self.assertEqual(col["facts"][name]["basis"], P.CALCULATED, name)
                for name in INFERRED_FACTS:
                    if col["facts"][name] is not None:
                        self.assertEqual(col["facts"][name]["basis"], P.INFERRED, name)
        self.assertEqual(self.doc["sources"][1]["workbook"]["basis"], P.OBSERVED)

    def test_inferred_facts_are_the_data_layer_results_verbatim(self):
        data = readers.read(DEMO_CSV)
        canonical = canonical_mod.build(data)
        semantic_map = mapping_mod.infer(data)
        for name in data.columns:
            field = canonical.field(name)
            facts = column(self.doc, name)["facts"]
            self.assertEqual(facts["kind"]["value"], field.kind)
            self.assertEqual(facts["sensitivity"]["value"]["class"], field.sensitivity.sensitivity)
            self.assertEqual(facts["kind_counts"]["value"], field.profile.kind_counts)
            if facts["role"] is not None and facts["role"]["value"] is not None:
                mapping = semantic_map.mappings[facts["role"]["value"]["role"]]
                self.assertEqual((mapping.column, mapping.status),
                                 (name, facts["role"]["value"]["status"]))
        self.assertEqual(P.SENSITIVITY_SAMPLE, sensitivity_mod.SAMPLE_SIZE)
        import inspect
        self.assertEqual(inspect.signature(canonical_mod.build).parameters["sample"].default,
                         P.KIND_SAMPLE)

    def test_inferred_samples_are_stated_and_observed_facts_examine_nothing(self):
        date = column(self.doc, "OrderDate")["facts"]
        self.assertEqual(date["kind"]["examined"], 1000)
        self.assertEqual(date["sensitivity"]["examined"], 200)
        self.assertEqual(date["role"]["examined"], 200)
        self.assertEqual(date["non_null_count"]["examined"], 2204)
        self.assertIsNone(dataset(self.doc)["row_count"]["examined"])

    def test_ambiguous_values_stay_inferred_and_are_counted_not_resolved(self):
        doc = build({"sources": [W.ambiguous_numbers_csv(tmpdir())]}).as_dict()
        revenue = column(doc, "NetRevenue")["facts"]
        self.assertEqual(revenue["ambiguous_count"]["basis"], P.INFERRED)
        self.assertEqual(revenue["ambiguous_count"]["value"], 4)

    def test_a_confirm_required_role_is_shown_as_exactly_that(self):
        doc = build({"sources": [write_csv(tmpdir(), "weak.csv", ["When", "Sales Total"],
                                           [["2025-01-01", "1.5"], ["2025-02-01", "text"]])]}
                    ).as_dict()
        statuses = {c["facts"]["role"]["value"]["status"] for c in dataset(doc)["columns"]
                    if c["facts"]["role"] is not None and c["facts"]["role"]["value"]}
        self.assertTrue(statuses <= {mapping_mod.AUTO, mapping_mod.CONFIRM_REQUIRED})

    def test_restricted_and_never_columns_report_name_kind_class_and_counts_only(self):
        doc = build({"sources": [write_csv(tmpdir(), "people.csv",
                                           ["DateOfBirth", "Customer", "Amount"],
                                           [["1980-01-02", "Alpha", 1], ["1990-03-04", "Beta", 2]])]}
                    ).as_dict()
        for name in ("DateOfBirth", "Customer"):
            facts = column(doc, name)["facts"]
            self.assertIn(facts["sensitivity"]["value"]["class"], ("restricted", "never"))
            for withheld in ("date_coverage", "currencies", "day_first", "role"):
                self.assertIsNone(facts[withheld], (name, withheld))
            self.assertEqual(facts["non_null_count"]["value"], 2)
        self.assertNotIn("1980", json.dumps(doc))


# =================================================================================================
# Privacy
# =================================================================================================

class Privacy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = tmpdir()
        cls.csv = canary_csv(cls.dir)
        cls.book = workbook(cls.dir, "canary.xlsx", [
            ("Orders", ["OrderID", "Customer", "Amount"],
             [["ORD-CANARY-7731", "Zyxcanary Holdings", 98765.43], ["ORD-2", "Other", 3]]),
            ("Secret", ["Code"], [["HIDDENPAYROLL-4412"]]),
        ], states={"Secret": "hidden"})
        cls.outputs = []
        cls.captured = []
        for presentation in ("local", "shareable"):
            request = {"sources": [cls.csv, cls.book], "presentation": presentation,
                       "objective": {"command_id": "customer-analysis",
                                     "kpi_ids": ["revenue", "average_order_value"]}}
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                result = build(request)
                cls.outputs += [result.to_json(), P.render(result)]
            cls.captured += [out.getvalue(), err.getvalue()]
        cls.local = build({"sources": [cls.csv]}).as_dict()
        cls.shareable = build({"sources": [cls.csv], "presentation": "shareable"}).as_dict()

    def test_no_canary_appears_in_json_render_or_captured_output(self):
        for text in self.outputs + self.captured:
            for canary in CANARIES:
                self.assertNotIn(canary, text)
                self.assertNotIn(canary.lower(), text.lower())

    def test_nothing_is_printed_while_profiling(self):
        self.assertEqual([t for t in self.captured if t.strip()], [])

    def test_the_quality_finding_that_quotes_values_is_referenced_without_them(self):
        findings = dataset(self.local)["quality"]["findings"]
        codes = [f["code"] for f in findings]
        self.assertIn("inconsistent_product_labels", codes)
        for finding in findings:
            self.assertEqual(set(finding), {"check_id", "family", "code", "severity", "affected",
                                            "fields", "completeness"})

    def test_exceptions_carry_no_values(self):
        path = os.path.join(tmpdir(), "stale.csv")
        shutil.copyfile(self.csv, path)
        result = build({"sources": [path]})
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("2026-01-01,ORD-X,Zyxcanary Holdings,a@b.test,Wombatshire,Q,1,n,S\n")
        with self.assertRaises(P.DataProfileError) as caught:
            result.to_json()
        for canary in CANARIES + (path, os.path.basename(path)):
            self.assertNotIn(canary, str(caught.exception))

    def test_shareable_bands_small_counts_hides_paths_and_never_column_names(self):
        self.assertIsNone(self.shareable["sources"][0]["source_path"])
        self.assertEqual(self.local["sources"][0]["source_path"], os.path.abspath(self.csv))
        names = [c["original_name"] for c in dataset(self.shareable)["columns"]]
        self.assertIn("column_3", names)          # Customer, classed never
        self.assertNotIn("Customer", names)
        self.assertIn("column_4", names)          # ContactEmail, classed never
        region = [c for c in dataset(self.shareable)["columns"] if c["original_name"] == "Region"][0]
        self.assertEqual(region["facts"]["distinct_count"]["value"], "1-9")
        self.assertEqual(column(self.local, "Region")["facts"]["distinct_count"]["value"], 2)
        self.assertEqual(dataset(self.shareable)["row_count"]["value"], 12)

    def test_only_iso_currency_codes_and_permitted_date_bounds_are_values(self):
        doc = build({"sources": [W.mixed_currency_csv(tmpdir())]}).as_dict()
        self.assertEqual(column(doc, "NetRevenue")["facts"]["currencies"]["value"], ["GBP", "USD"])
        self.assertNotIn("1000.00", json.dumps(doc))
        self.assertNotIn("£", json.dumps(doc, ensure_ascii=False))


# =================================================================================================
# M4, M5, commands and Business Context
# =================================================================================================

class References(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.context = demo_context()
        cls.result = build({"sources": [DEMO_CSV],
                            "objective": {"command_id": "customer-analysis",
                                          "kpi_ids": ["revenue", "inventory_turnover"]}},
                           context_overrides=cls.context)
        cls.doc = cls.result.as_dict()
        context, config = P._resolve_context(None, None, cls.context, False)
        cls.data = readers.read(DEMO_CSV)
        cls.canonical = canonical_mod.build(cls.data)
        cls.map = mapping_mod.infer(cls.data)
        cls.quality = quality_checks.run(cls.data, cls.map, config, canonical=cls.canonical,
                                         context=context)
        cls.kpis = kpi_registry.calculate(cls.data, cls.map, context, config,
                                          ["revenue", "inventory_turnover", "customer_count"],
                                          canonical=cls.canonical, quality=cls.quality)

    def test_quality_is_m4s_verdict_by_reference(self):
        quality = dataset(self.doc)["quality"]
        self.assertEqual((quality["grade"], quality["halted"], quality["completeness"]),
                         (self.quality.grade, self.quality.halted, self.quality.completeness))
        self.assertEqual([(f["check_id"], f["code"], f["severity"]) for f in quality["findings"]],
                         [(f.check_id, f.code, f.severity) for f in self.quality.findings])

    def test_kpi_status_is_retained_and_every_value_discarded(self):
        kpis = dataset(self.doc)["applicability"]["kpis"]
        by_id = {k["kpi_id"]: k for k in kpis}
        for kpi_id in ("revenue", "inventory_turnover"):
            self.assertEqual(by_id[kpi_id]["status"], self.kpis[kpi_id].status)
            self.assertEqual(set(by_id[kpi_id]), {"kpi_id", "status", "inputs", "minimum_periods"})
        self.assertEqual(by_id["revenue"]["status"], kpi_registry.AVAILABLE)
        revenue = str(self.kpis["revenue"].value)
        self.assertGreaterEqual(len(revenue), 5)
        self.assertNotIn(revenue, self.result.to_json())
        self.assertNotIn(revenue, P.render(self.result))

    def test_the_business_model_decides_applicability_through_m5_only(self):
        services = copy.deepcopy(self.context)
        services["identity"]["business_model"] = "professional_services"
        doc = build({"sources": [DEMO_CSV], "objective": {"kpi_ids": ["inventory_turnover"]}},
                    context_overrides=services).as_dict()
        self.assertEqual(dataset(doc)["applicability"]["kpis"][0]["status"],
                         kpi_registry.NOT_APPLICABLE)

    def test_command_kpi_focus_follows_the_requested_kpis(self):
        spec = command_registry.BY_ID["customer-analysis"]
        ids = [k["kpi_id"] for k in dataset(self.doc)["applicability"]["kpis"]]
        self.assertEqual(ids, ["revenue", "inventory_turnover"]
                         + [k for k in spec.kpi_focus if k not in ("revenue", "inventory_turnover")])

    def test_command_entry_reports_declared_roles_and_mapping_status_never_an_outcome(self):
        command = dataset(self.doc)["applicability"]["command"]
        spec = command_registry.BY_ID["customer-analysis"]
        self.assertEqual(set(command), {"command_id", "required_roles"})
        self.assertEqual([r["role"] for r in command["required_roles"]], list(spec.required_roles))
        for entry in command["required_roles"]:
            mapping = self.map.mappings.get(entry["role"])
            self.assertEqual(entry["status"], mapping.status if mapping else P.ABSENT)

    def test_an_absent_required_role_is_absent(self):
        doc = build({"sources": [write_csv(tmpdir(), "nocust.csv", ["OrderDate", "Amount"],
                                           [["2025-01-01", 1]])],
                     "objective": {"command_id": "customer-analysis"}}).as_dict()
        roles = {r["role"]: r["status"] for r in dataset(doc)["applicability"]["command"]["required_roles"]}
        self.assertEqual(roles[mapping_mod.CUSTOMER], P.ABSENT)

    def test_no_objective_means_no_applicability(self):
        self.assertIsNone(dataset(build({"sources": [DEMO_CSV]}).as_dict())["applicability"])

    def test_business_context_is_labelled_context_and_never_a_fact(self):
        self.assertEqual(self.doc["context_used"],
                         {"basis": "context", "business_model": "retail", "currency": "GBP"})
        self.assertIsNone(build({"sources": [DEMO_CSV]}).as_dict()["context_used"])
        for entry in dataset(self.doc)["columns"]:
            self.assertNotEqual(entry["facts"]["kind"]["basis"], "context")


# =================================================================================================
# Determinism, identity and integrity
# =================================================================================================

class Determinism(unittest.TestCase):

    def test_identical_inputs_give_byte_identical_output_and_id(self):
        request = {"sources": [DEMO_CSV, DEMO_XLSX], "objective": {"command_id": "sales-analysis"}}
        first, second = build(request), build(request)
        self.assertEqual(first.to_json(), second.to_json())
        self.assertRegex(first.profile_id, r"^dpr-[0-9a-f]{12}$")
        self.assertEqual(first.profile_id, second.profile_id)
        self.assertNotIn("calculated_at", first.to_json())

    def test_the_id_follows_bytes_request_presentation_and_context_not_location(self):
        directory = tmpdir()
        path = write_csv(directory, "d.csv", ["Region"], [["North"], ["South"]])
        base = build({"sources": [path]}).profile_id
        moved_dir = tmpdir()
        moved = os.path.join(moved_dir, "d.csv")
        shutil.copyfile(path, moved)
        self.assertEqual(build({"sources": [moved]}).profile_id, base)
        self.assertEqual(build({"sources": [moved], "presentation": "shareable"}).to_json(),
                         build({"sources": [path], "presentation": "shareable"}).to_json())
        self.assertNotEqual(build({"sources": [path], "presentation": "shareable"}).profile_id, base)
        self.assertNotEqual(build({"sources": [path]}, context_overrides=demo_context()).profile_id,
                            base)
        self.assertNotEqual(build({"sources": [path],
                                   "objective": {"kpi_ids": ["revenue"]}}).profile_id, base)
        with open(moved, "a") as handle:
            handle.write("East\n")
        self.assertNotEqual(build({"sources": [moved]}).profile_id, base)

    def test_refs_are_content_addressed(self):
        doc = build({"sources": [DEMO_CSV]}).as_dict()
        self.assertRegex(doc["sources"][0]["source_ref"], r"^src-[0-9a-f]{12}$")
        self.assertRegex(dataset(doc)["dataset_ref"], r"^dst-[0-9a-f]{12}$")
        self.assertRegex(dataset(doc)["columns"][0]["column_ref"], r"^col-[0-9a-f]{12}$")
        self.assertTrue(doc["config_digest"].startswith("sha256:"))
        self.assertEqual(doc["request"]["sources"], [doc["sources"][0]["source_ref"]])


class Integrity(unittest.TestCase):

    def test_a_changed_source_refuses_serialisation_and_rendering(self):
        path = write_csv(tmpdir(), "s.csv", ["Region"], [["North"]])
        result = build({"sources": [path]})
        self.assertEqual(result.stale_sources(), [])
        with open(path, "a") as handle:
            handle.write("South\n")
        for action in (result.as_dict, result.to_json, lambda: P.render(result)):
            with self.assertRaises(P.DataProfileError) as caught:
                action()
            self.assertEqual(str(caught.exception), P.STALE)

    def test_a_deleted_source_is_stale_too(self):
        path = write_csv(tmpdir(), "gone.csv", ["Region"], [["North"]])
        result = build({"sources": [path]})
        os.remove(path)
        with self.assertRaises(P.DataProfileError):
            result.as_dict()

    def test_a_result_cannot_be_constructed_or_modified_by_a_caller(self):
        with self.assertRaises(P.DataProfileError):
            P.DataProfileResult({"analysis": "data_profile"}, [])
        result = build({"sources": [DEMO_CSV]})
        with self.assertRaises(P.DataProfileError):
            result._document = {}
        with self.assertRaises(P.DataProfileError):
            result.status = "complete"
        mutated = result.as_dict()
        mutated["status"] = "complete"
        self.assertEqual(result.as_dict()["status"], P.COMPLETE_WITH_LIMITATIONS)

    def test_render_accepts_only_a_genuine_result(self):
        with self.assertRaises(P.DataProfileError):
            P.render(build({"sources": [DEMO_CSV]}).as_dict())


# =================================================================================================
# Synthesis re-entry
# =================================================================================================

class ReEntry(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result = build({"sources": [DEMO_CSV, DEMO_XLSX],
                            "objective": {"command_id": "sales-analysis"}})
        cls.doc = cls.result.as_dict()

    def refused(self, record):
        synthesis = S.SynthesisSet(subject="profile re-entry")
        with self.assertRaises(S.SynthesisError):
            synthesis.register_claims([record])
        self.assertEqual(synthesis.as_dict()["claims"] if "claims" in synthesis.as_dict() else [],
                         [])

    def test_a_genuine_profile_and_its_dict_are_refused(self):
        self.refused(self.result)
        self.refused(self.doc)

    def test_every_part_of_a_profile_is_refused(self):
        entry = dataset(self.doc)
        parts = ([self.doc["sources"][0], entry, entry["columns"][0], entry["key_candidates"][0],
                  entry["columns"][0]["facts"]["non_null_count"],
                  entry["columns"][0]["facts"]["kind"],
                  entry["applicability"], entry["applicability"]["kpis"][0],
                  entry["applicability"]["command"], self.doc["relationships"][0],
                  self.doc["limitations"][0]]
                 + entry["quality"]["findings"][:1])
        for part in parts:
            self.refused(copy.deepcopy(part))

    def test_profile_only_fields_cannot_bypass_the_boundary(self):
        for field in ("profile_id", "source_ref", "dataset_ref", "column_ref", "key_candidates",
                      "relationships", "applicability", "required_roles", "overlap_rate"):
            self.refused({"statement": "Revenue grew.", field: "x"})

    def test_forged_and_malformed_profiles_are_refused(self):
        self.refused({"statement": "The data is clean.", "analysis": " Data_Profile "})
        self.refused({"statement": "Overlap is complete.", "left": "col-0123456789ab"})
        self.refused({"statement": "Three columns.", "basis": "Calculated", "examined": 3,
                      "value": 3})
        self.refused({"analysis": "data_profile"})

    def test_an_ordinary_candidate_claim_is_still_accepted(self):
        synthesis = S.SynthesisSet(subject="control")
        registered = synthesis.register_claims([{"statement": "Revenue grew 5% in 2025.",
                                                 "class": 3}])
        self.assertEqual(len(registered), 1)


# =================================================================================================
# Schema
# =================================================================================================

class Schema(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.schema = P.load_schema()
        directory = tmpdir()
        cls.local = build({"sources": [DEMO_CSV, W.encrypted(directory), W.multi_sheet(directory)],
                           "objective": {"command_id": "sales-analysis", "kpi_ids": ["revenue"]}},
                          context_overrides=demo_context()).as_dict()
        cls.shareable = build({"sources": [canary_csv(directory)], "presentation": "shareable"}
                              ).as_dict()

    def errors(self, document):
        return jsonschema_mini.validate(document, self.schema)

    def test_genuine_profiles_conform(self):
        self.assertEqual(self.errors(self.local), [])
        self.assertEqual(self.errors(self.shareable), [])
        self.assertEqual(jsonschema_mini.unsupported_keywords(self.schema), set())
        self.assertEqual(P.validate_document(self.local), [])

    def test_the_schema_is_closed_against_forbidden_fields(self):
        for field in ("confidence", "score", "rank", "priority", "recommendation", "evidence",
                      "decision", "approval", "lifecycle", "timestamp", "generated_at"):
            document = copy.deepcopy(self.local)
            document[field] = "x"
            self.assertTrue(self.errors(document), field)

    def test_nested_shapes_are_closed(self):
        mutations = (
            lambda d: d.__setitem__("profile_id", "dpr-XYZ"),
            lambda d: d.__setitem__("status", "good"),
            lambda d: dataset(d)["columns"][0]["facts"]["kind"].__setitem__("basis",
                                                                           "model_generated"),
            lambda d: dataset(d)["columns"][0]["facts"].__setitem__("sample_values", ["a"]),
            lambda d: dataset(d)["columns"][0]["facts"]["non_null_count"].__setitem__("value", -1),
            lambda d: dataset(d)["quality"]["findings"].append(
                {"check_id": "x", "family": "x", "code": "x", "severity": "INFO", "affected": 1,
                 "fields": [], "completeness": "exhaustive", "message": "value"}),
            lambda d: dataset(d)["applicability"]["kpis"][0].__setitem__("value", "1"),
            lambda d: dataset(d)["applicability"]["command"].__setitem__("outcome", "ok"),
            lambda d: d["relationships"].append({"left": "col-0123456789ab",
                                                 "right": "col-0123456789ac",
                                                 "overlap_rate": "0.5000", "basis": "calculated",
                                                 "status": "confirmed"}),
            lambda d: d["limitations"].append({"code": "data_is_bad",
                                               "subject_ref": "src-0123456789ab", "reason": "x"}),
            lambda d: d["sources"][1].__setitem__("reason_code", "password_guessed"),
            lambda d: d["sources"][0].__setitem__("rows", [["a"]]),
        )
        for mutate in mutations:
            document = copy.deepcopy(self.local)
            mutate(document)
            self.assertTrue(self.errors(document))


# =================================================================================================
# Scope, layering and the skill
# =================================================================================================

class Scope(unittest.TestCase):

    def test_no_lower_layer_imports_the_profile(self):
        pattern = re.compile(r"(import\s+data_profile|from\s+\.+\s+import\s+data_profile"
                             r"|from\s+\.*data_profile\s+import|bops\.data_profile)")
        library = os.path.join(REPO_ROOT, "lib", "python", "bops")
        for directory, _dirs, files in os.walk(library):
            for name in files:
                if name.endswith(".py") and name != "data_profile.py":
                    with io.open(os.path.join(directory, name), encoding="utf-8") as handle:
                        self.assertIsNone(pattern.search(handle.read()), name)

    def test_no_agent_mcp_server_or_command_was_added_for_profiling(self):
        self.assertFalse(os.path.exists(os.path.join(REPO_ROOT, "agents", "bops-data-profiler.md")))
        with io.open(os.path.join(REPO_ROOT, ".mcp.json"), encoding="utf-8") as handle:
            self.assertEqual(list(json.load(handle)["mcpServers"]), ["bops-verifier"])
        self.assertEqual([n for n in os.listdir(os.path.join(REPO_ROOT, "commands"))
                          if "profil" in n or "ingest" in n], [])

    def test_the_engine_makes_no_network_call(self):
        with io.open(os.path.join(REPO_ROOT, "lib", "python", "bops", "data_profile.py"),
                     encoding="utf-8") as handle:
            source = handle.read()
        for module in ("urllib", "http.client", "socket", "requests", "subprocess"):
            self.assertNotIn("import %s" % module, source)

    def test_the_skill_is_the_existing_ingestion_location_and_states_the_boundaries(self):
        path = os.path.join(REPO_ROOT, "skills", "bops-data-ingestion", "SKILL.md")
        with io.open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("name: bops-data-ingestion", text)
        self.assertIn("data_profile.build(", text)
        self.assertIn("data_profile.render(", text)
        for phrase in ("Never open a source file", "No values.", "not evidence",
                       "exact count over every row read", "never an\nanswer about the business",
                       "Never describe it as a join", "rank", "recommend"):
            self.assertIn(phrase, text)


if __name__ == "__main__":                                   # pragma: no cover
    unittest.main()
