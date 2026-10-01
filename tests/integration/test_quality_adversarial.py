"""Milestone 4 — adversarial input to the quality layer.

Every case asserts one of three honest outcomes: **fail safely, warn honestly, or say it
cannot tell.** Nothing here may be silently accepted, and not every bad condition is
CRITICAL — over-escalating is its own failure, because a gate that always halts is a gate
nobody trusts.
"""

import json
import os
import shutil
import tempfile
import unittest

from bops import ingest, pipeline, quality
from bops import config as config_mod
from bops import mapping as mapping_mod
from bops.errors import ConfigError
from bops.ingest import canonical as canonical_mod
from bops.quality import checks as quality_checks
from bops.quality import report as report_mod
from bops.runtime import tiers

from fixtures import build_quality_fixtures as fixtures
from fixtures import build_workbooks

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class AdversarialCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.schema = report_mod.load_schema()

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bops-m4-adv-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def assess(self, path, context_overrides=None):
        dataset = ingest.read(path)
        canonical = canonical_mod.build(dataset)
        business_context = None
        if context_overrides is not None:
            from bops.context import loader
            business_context = loader.resolve(overrides=context_overrides,
                                              load_files=False)
        return quality_checks.run(
            dataset, mapping_mod.infer(dataset),
            config_mod.resolve(defaults=config_mod.load_defaults()),
            canonical, business_context)

    def assert_report_valid(self, report):
        self.assertEqual(report.validate(self.schema), [])


# ==========================================================================
# Structurally impossible input
# ==========================================================================

class TestStructurallyImpossible(AdversarialCase):

    def test_header_only_dataset_halts(self):
        report = self.assess(fixtures.incomplete_dataset(self.tmp))
        self.assertTrue(report.halted)
        self.assertIn("no_rows", {f.code for f in report.findings})
        self.assert_report_valid(report)

    def test_completely_empty_file_is_refused_at_ingestion(self):
        path = os.path.join(self.tmp, "empty.csv")
        open(path, "w").close()
        with self.assertRaises(ConfigError):
            ingest.read(path)

    def test_single_column_halts_with_a_delimiter_hint(self):
        report = self.assess(fixtures.single_column(self.tmp))
        self.assertTrue(report.halted)
        findings = [f for f in report.findings if f.code == "too_few_columns"]
        self.assertTrue(findings)
        self.assertIn("delimiter", findings[0].remediation)

    def test_no_revenue_column_halts_and_explains_why(self):
        report = self.assess(fixtures.no_revenue_column(self.tmp))
        self.assertTrue(report.halted)
        finding = next(f for f in report.findings if f.code == "missing_role_revenue")
        self.assertIn("explanation", finding.evidence)
        self.assertTrue(finding.remediation)

    def test_all_null_field_is_reported_but_not_fatal(self):
        report = self.assess(fixtures.all_null_field(self.tmp))
        self.assertIn("empty_column", {f.code for f in report.findings})
        self.assertFalse(report.halted)

    def test_ragged_rows_are_reported(self):
        report = self.assess(fixtures.ragged(self.tmp))
        codes = {f.code for f in report.findings}
        self.assertTrue(any("ragged" in c for c in codes), codes)
        self.assert_report_valid(report)


# ==========================================================================
# Value-level problems
# ==========================================================================

class TestValueProblems(AdversarialCase):

    def test_ambiguous_numbers_warn_and_are_never_guessed(self):
        path = os.path.join(self.tmp, "ambiguous.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("OrderDate,NetRevenue,Quantity\n")
            for month in range(1, 7):
                fh.write("2025-%02d-15,1000.00,1.234\n" % month)
        report = self.assess(path)
        self.assertIn("ambiguous_numbers", {f.code for f in report.findings})

    def test_ambiguous_dates_warn_and_are_never_guessed(self):
        path = os.path.join(self.tmp, "ambiguous_dates.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("OrderDate,NetRevenue\n")
            for day in (3, 5, 7, 9):
                fh.write("0%d/04/2025,1000.00\n" % day)
        report = self.assess(path)
        codes = {f.code for f in report.findings}
        self.assertTrue("ambiguous_dates" in codes or "invalid_dates" in codes, codes)

    def test_mixed_types_in_one_column_warn(self):
        path = os.path.join(self.tmp, "mixed.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("OrderDate,NetRevenue,Notes\n")
            fh.write("2025-01-15,1000.00,42\n")
            fh.write("2025-02-15,1000.00,text\n")
            fh.write("2025-03-15,1000.00,2025-01-01\n")
            fh.write("2025-04-15,1000.00,more text\n")
        report = self.assess(path)
        self.assertIn("mixed_types", {f.code for f in report.findings})

    def test_mixed_currencies_halt(self):
        report = self.assess(fixtures.mixed_currency(self.tmp))
        self.assertTrue(report.halted)
        self.assertIn("mixed_currencies", {f.code for f in report.findings})

    def test_currency_mismatch_with_context_halts(self):
        report = self.assess(fixtures.currency_contradiction(self.tmp),
                             context_overrides={"reporting": {"currency": "GBP"}})
        self.assertTrue(report.halted)
        finding = next(f for f in report.findings if f.code == "currency_contradiction")
        self.assertIn("no exchange rate is applied", finding.message)

    def test_negative_values_warn_without_halting(self):
        report = self.assess(fixtures.negative_values(self.tmp))
        self.assertFalse(report.halted)
        self.assertTrue([f for f in report.findings if "negative" in f.code])

    def test_outlier_warns_without_halting_and_is_not_called_fraud(self):
        report = self.assess(fixtures.outliers(self.tmp))
        self.assertFalse(report.halted)
        findings = report.by_check("outliers")
        self.assertTrue(findings)
        self.assertNotIn("fraud", json.dumps([f.as_dict() for f in findings]).lower())


# ==========================================================================
# Workbook-level problems reaching the quality layer
# ==========================================================================

class TestWorkbookProblems(AdversarialCase):

    def _xlsx_report(self, path):
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        canonical = canonical_mod.build(dataset)
        return quality_checks.run(
            dataset, mapping_mod.infer(dataset),
            config_mod.resolve(defaults=config_mod.load_defaults()), canonical)

    def test_missing_cached_formula_reaches_the_quality_report(self):
        report = self._xlsx_report(
            build_workbooks.formula_without_cached_value(self.tmp))
        finding = next(f for f in report.findings
                       if f.code == "formula_without_cached_value")
        self.assertEqual(finding.check_id, "broken_formulas")
        self.assertIn("never evaluates", finding.message)

    def test_external_reference_is_reported_as_possibly_stale(self):
        report = self._xlsx_report(build_workbooks.external_reference(self.tmp))
        finding = next(f for f in report.findings
                       if f.code == "external_reference_cached")
        self.assertIn("stale", finding.message)

    def test_degraded_tier3_read_is_reported(self):
        report = self._xlsx_report(build_workbooks.rich_types(self.tmp))
        messages = " ".join(f.message for f in report.findings)
        self.assertIn("stdlib parser", messages)
        self.assertFalse(report.halted)

    def test_unsupported_number_format_reaches_the_report(self):
        report = self._xlsx_report(build_workbooks.unknown_number_format(self.tmp))
        messages = " ".join(f.message for f in report.findings)
        self.assertIn("Number format", messages)

    def test_corrupt_workbook_is_refused_before_quality_runs(self):
        with self.assertRaises(ConfigError):
            ingest.read_xlsx(build_workbooks.corrupt_zip(self.tmp),
                             prefer_tier=tiers.TIER_STDLIB)

    def test_encrypted_workbook_is_refused_before_quality_runs(self):
        with self.assertRaises(ConfigError):
            ingest.read_xlsx(build_workbooks.encrypted(self.tmp),
                             prefer_tier=tiers.TIER_STDLIB)


# ==========================================================================
# Scale and combinations
# ==========================================================================

class TestScaleAndCombinations(AdversarialCase):

    def test_multiple_simultaneous_failures_are_all_reported(self):
        report = self.assess(fixtures.multiple_failures(self.tmp))
        families = {f.check_id for f in report.findings}
        self.assertGreaterEqual(len(families), 3, families)
        self.assertTrue(report.critical)
        self.assertTrue(report.warnings)
        self.assert_report_valid(report)

    def test_a_critical_finding_does_not_suppress_the_rest_of_the_report(self):
        report = self.assess(fixtures.multiple_failures(self.tmp))
        # Every family still reports a result, even though the run halts.
        self.assertEqual(len(report.check_results), 13)

    def test_oversized_input_is_handled_without_error(self):
        path = os.path.join(self.tmp, "big.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("OrderDate,OrderID,NetRevenue,CostOfGoods\n")
            for index in range(30000):
                fh.write("2025-%02d-15,SO-%06d,%.2f,%.2f\n"
                         % ((index % 12) + 1, index, 100.0 + index % 500, 60.0))
        report = self.assess(path)
        self.assertEqual(report.rows_checked, 30000)
        self.assert_report_valid(report)

    def test_every_adversarial_report_validates_against_the_schema(self):
        builders = (fixtures.multiple_failures, fixtures.warning_only,
                    fixtures.all_null_field, fixtures.ragged,
                    fixtures.negative_values, fixtures.outliers,
                    fixtures.missing_periods, fixtures.duplicate_records)
        for builder in builders:
            with self.subTest(fixture=builder.__name__):
                self.assert_report_valid(self.assess(builder(self.tmp)))


# ==========================================================================
# The quality layer never repairs data
# ==========================================================================

class TestNoRepair(AdversarialCase):

    def test_no_fixture_is_modified_by_a_quality_run(self):
        builders = (fixtures.clean, fixtures.multiple_failures, fixtures.warning_only,
                    fixtures.mixed_currency, fixtures.inconsistent_customers,
                    fixtures.duplicate_records, fixtures.negative_values)
        for builder in builders:
            path = builder(self.tmp)
            before = open(path, "rb").read()
            try:
                self.assess(path)
            except ConfigError:
                pass
            self.assertEqual(open(path, "rb").read(), before, builder.__name__)

    def test_duplicates_are_reported_not_removed(self):
        path = fixtures.duplicate_records(self.tmp)
        dataset = ingest.read(path)
        rows_before = dataset.row_count
        self.assess(path)
        self.assertEqual(ingest.read(path).row_count, rows_before)

    def test_findings_offer_remediation_rather_than_performing_it(self):
        report = self.assess(fixtures.duplicate_records(self.tmp))
        finding = report.by_check("duplicate_records")[0]
        self.assertIn("does not remove rows", finding.remediation)

    def test_missing_values_are_not_filled(self):
        path = fixtures.missing_values(self.tmp)
        self.assess(path)
        dataset = ingest.read(path)
        blanks = sum(1 for row in dataset.rows if row.get("NetRevenue") in (None, ""))
        self.assertGreater(blanks, 0, "blank values must remain blank")


if __name__ == "__main__":
    unittest.main()
