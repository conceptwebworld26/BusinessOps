"""Milestone 3 — cross-tier equivalence and adversarial data-layer behaviour.

**Equivalence, precisely defined.** Tier 1 and Tier 3 are equivalent for a workbook when:

  1. the same sheet is selected,
  2. the column names match exactly and in order,
  3. the row count matches,
  4. for every cell, the *canonical value* matches — dates as `date`, numbers as numeric,
     text as text.

Metadata is explicitly **not** required to match: the reader tier differs by definition, and
each reader legitimately emits its own warnings. Comparing those would test the readers'
implementation rather than the data they produce.
"""

import datetime
import os
import shutil
import tempfile
import unittest

from bops import ingest
from bops.errors import ConfigError
from bops.ingest import canonical as canonical_mod
from bops.ingest import workbook as workbook_mod
from bops.runtime import tiers

from fixtures import build_workbooks

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO_XLSX = os.path.join(REPO, "assets", "demo-data", "northwind_sales.xlsx")


def openpyxl_available():
    try:
        import openpyxl  # noqa: F401
        return True
    except ImportError:
        return False


def canonical_value(value):
    """Reduce a cell to the form both tiers must agree on."""
    if isinstance(value, datetime.datetime):
        return value.replace(microsecond=0)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    return value


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bops-m3-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


# ==========================================================================
# Cross-tier equivalence
# ==========================================================================

@unittest.skipUnless(openpyxl_available(),
                     "openpyxl absent; Tier 1 cannot be compared here")
class TestCrossTierEquivalence(FixtureCase):

    def assert_equivalent(self, path, sheet=None):
        tier1 = ingest.read_xlsx(path, sheet, prefer_tier=tiers.TIER_OPENPYXL_SYSTEM)
        tier3 = ingest.read_xlsx(path, sheet, prefer_tier=tiers.TIER_STDLIB)

        self.assertEqual(tier1.sheet, tier3.sheet, "sheet selection differs")
        self.assertEqual(tier1.columns, tier3.columns, "columns differ")
        self.assertEqual(tier1.row_count, tier3.row_count, "row count differs")

        for index, (a, b) in enumerate(zip(tier1.rows, tier3.rows)):
            for column in tier1.columns:
                self.assertEqual(
                    canonical_value(a.get(column)), canonical_value(b.get(column)),
                    "row %d column %r: tier1=%r tier3=%r"
                    % (index, column, a.get(column), b.get(column)))
        return tier1, tier3

    def test_corpus_is_equivalent_across_tiers(self):
        for name, builder in build_workbooks.CORPUS:
            with self.subTest(fixture=name):
                self.assert_equivalent(builder(self.tmp))

    def test_demo_workbook_is_equivalent(self):
        self.assert_equivalent(DEMO_XLSX)

    def test_dates_agree(self):
        tier1, tier3 = self.assert_equivalent(build_workbooks.rich_types(self.tmp))
        self.assertEqual(tier1.rows[0]["Date"], datetime.date(2023, 3, 15))
        self.assertEqual(tier3.rows[0]["Date"], datetime.date(2023, 3, 15))

    def test_formula_cached_values_agree(self):
        tier1, tier3 = self.assert_equivalent(build_workbooks.rich_types(self.tmp))
        self.assertEqual(canonical_value(tier1.rows[0]["Computed"]), 2469.12)
        self.assertEqual(canonical_value(tier3.rows[0]["Computed"]), 2469.12)

    def test_shared_and_inline_strings_agree(self):
        tier1, tier3 = self.assert_equivalent(build_workbooks.rich_types(self.tmp))
        self.assertEqual(tier1.rows[0]["Label"], "alpha")
        self.assertEqual(tier3.rows[0]["Mixed"], "inline")

    def test_hidden_sheet_is_skipped_by_both(self):
        tier1, tier3 = self.assert_equivalent(build_workbooks.multi_sheet(self.tmp))
        self.assertEqual(tier1.sheet, "Visible")
        self.assertEqual(tier3.sheet, "Visible")

    def test_canonical_view_agrees_across_tiers(self):
        path = build_workbooks.rich_types(self.tmp)
        c1 = canonical_mod.build(
            ingest.read_xlsx(path, prefer_tier=tiers.TIER_OPENPYXL_SYSTEM))
        c3 = canonical_mod.build(
            ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB))
        self.assertEqual(c1.columns, c3.columns)
        for column in c1.columns:
            self.assertEqual(c1.field(column).kind, c3.field(column).kind, column)
            self.assertEqual(c1.field(column).sensitivity.sensitivity,
                             c3.field(column).sensitivity.sensitivity, column)


class TestTierIndependentBehaviour(FixtureCase):
    """What must hold at Tier 3 whether or not openpyxl exists."""

    def test_1904_date_system_is_honoured(self):
        path = build_workbooks.date_1904_system(self.tmp)
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        value = dataset.rows[0]["Date"]
        self.assertIsInstance(value, datetime.date)
        # 1904 epoch: serial 43000 is four years and a day later than under 1900.
        self.assertEqual(value.year, 2021)

    def test_multi_sheet_selection_prefers_visible(self):
        path = build_workbooks.multi_sheet(self.tmp)
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        self.assertEqual(dataset.sheet, "Visible")
        self.assertEqual(sorted(dataset.sheets), ["Hidden", "Visible"])

    def test_hidden_sheet_read_only_when_named_and_warns(self):
        path = build_workbooks.multi_sheet(self.tmp)
        dataset = ingest.read_xlsx(path, sheet_name="Hidden",
                                   prefer_tier=tiers.TIER_STDLIB)
        self.assertEqual(dataset.sheet, "Hidden")
        self.assertIn("hidden_sheet_read", {w.code for w in dataset.warnings})

    def test_unknown_number_format_warns_and_does_not_guess(self):
        path = build_workbooks.unknown_number_format(self.tmp)
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        codes = {w.code for w in dataset.warnings}
        self.assertIn("unresolved_number_format", codes)
        # Read as a plain number, never guessed into a date.
        self.assertEqual(dataset.rows[0]["Value"], 123)

    def test_empty_rows_are_skipped_and_gaps_preserved(self):
        path = build_workbooks.empty_rows_and_missing(self.tmp)
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        self.assertEqual(dataset.row_count, 2)
        self.assertIsNone(dataset.rows[1]["Amount"])


# ==========================================================================
# Formulas, external references, macros, encryption
# ==========================================================================

class TestFormulaAndReferenceSafety(FixtureCase):

    def test_formula_cached_value_used_never_evaluated(self):
        path = build_workbooks.rich_types(self.tmp)
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        self.assertEqual(dataset.rows[0]["Computed"], 2469.12)

    def test_missing_cached_value_is_none_and_warns(self):
        path = build_workbooks.formula_without_cached_value(self.tmp)
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        self.assertIsNone(dataset.rows[0]["Value"])
        self.assertIn("formula_without_cached_value",
                      {w.code for w in dataset.warnings})

    def test_shared_formulas_are_detected_and_not_evaluated(self):
        path = build_workbooks.shared_formula(self.tmp)
        facts = workbook_mod.inspect(path)
        self.assertGreater(facts.shared_formula_count, 0)
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        self.assertEqual([r["Value"] for r in dataset.rows], [2, 4])  # cached only

    def test_external_reference_detected_and_not_followed(self):
        path = build_workbooks.external_reference(self.tmp)
        facts = workbook_mod.inspect(path)
        self.assertTrue(facts.external_links)
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        codes = {w.code for w in dataset.warnings}
        self.assertIn("external_reference_cached", codes)
        self.assertEqual(dataset.rows[0]["Value"], 99)      # cached value only

    def test_external_reference_warning_says_it_may_be_stale(self):
        path = build_workbooks.external_reference(self.tmp)
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        warning = next(w for w in dataset.warnings
                       if w.code == "external_reference_cached")
        self.assertIn("stale", warning.message)
        self.assertIn("not opened", warning.message)

    def test_macro_workbook_is_read_without_executing_macros(self):
        path = build_workbooks.macro_enabled(self.tmp)
        facts = workbook_mod.inspect(path)
        self.assertTrue(facts.macro_enabled)
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        self.assertEqual(dataset.rows[0]["Value"], 1)
        notes = " ".join(w.message for w in dataset.warnings)
        self.assertIn("never executed", notes)

    def test_encrypted_workbook_fails_clearly_without_bypass(self):
        path = build_workbooks.encrypted(self.tmp)
        with self.assertRaises(ConfigError) as caught:
            ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        message = str(caught.exception)
        self.assertIn("encrypted", message.lower())
        self.assertIn("unprotected copy", message)
        # No hint of an attempt to break in.
        self.assertNotIn("password attempt", message.lower())


# ==========================================================================
# Adversarial inputs
# ==========================================================================

class TestAdversarialInputs(FixtureCase):

    def test_corrupt_archive_fails_clearly(self):
        with self.assertRaises(ConfigError) as caught:
            ingest.read_xlsx(build_workbooks.corrupt_zip(self.tmp),
                             prefer_tier=tiers.TIER_STDLIB)
        self.assertIn("not a readable .xlsx", str(caught.exception))

    def test_malformed_worksheet_xml_fails_clearly(self):
        with self.assertRaises(ConfigError) as caught:
            ingest.read_xlsx(build_workbooks.malformed_xml(self.tmp),
                             prefer_tier=tiers.TIER_STDLIB)
        self.assertIn("malformed XML", str(caught.exception))

    def test_duplicate_headers_do_not_crash(self):
        dataset = ingest.read_xlsx(build_workbooks.duplicate_headers(self.tmp),
                                   prefer_tier=tiers.TIER_STDLIB)
        self.assertGreaterEqual(dataset.row_count, 1)

    def test_mixed_currency_is_critical_not_summed(self):
        from bops import pipeline
        path = build_workbooks.mixed_currency_csv(self.tmp)
        result = pipeline.run(path, load_context_files=False)
        self.assertTrue(result.halted)
        messages = " ".join(f.message for f in result.quality.critical)
        self.assertIn("currencies", messages)
        self.assertIn("does not convert", messages)

    def test_ambiguous_numbers_are_flagged_not_guessed(self):
        from bops import pipeline
        path = build_workbooks.ambiguous_numbers_csv(self.tmp)
        result = pipeline.run(path, load_context_files=False)
        # M4 renamed this code when the check moved into the `invalid_numbers` family.
        codes = {f.code for f in result.quality.findings}
        self.assertIn("ambiguous_numbers", codes)
        self.assertEqual(
            {f.check_id for f in result.quality.findings if f.code == "ambiguous_numbers"},
            {"invalid_numbers"})

    def test_unsupported_extension_is_refused_with_guidance(self):
        with self.assertRaises(ConfigError) as caught:
            ingest.read(os.path.join(self.tmp, "thing.pdf"))
        self.assertIn(".csv", str(caught.exception))

    def test_source_file_is_never_modified_by_any_path(self):
        for builder in (build_workbooks.rich_types, build_workbooks.external_reference,
                        build_workbooks.shared_formula):
            path = builder(self.tmp)
            before = open(path, "rb").read()
            try:
                ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
            except ConfigError:
                pass
            self.assertEqual(open(path, "rb").read(), before, path)


# ==========================================================================
# Tier 4
# ==========================================================================

class TestTier4Guidance(unittest.TestCase):

    def test_guidance_states_reason_structure_and_loss(self):
        guidance = workbook_mod.csv_export_guidance("book.xlsx", "no reader available")
        self.assertEqual(guidance["reason"], "no reader available")
        self.assertTrue(guidance["source_untouched"])
        self.assertTrue(guidance["required_structure"])
        self.assertTrue(guidance["information_lost"])

    def test_rendered_guidance_is_actionable_and_reassuring(self):
        text = workbook_mod.format_csv_guidance(
            workbook_mod.csv_export_guidance("book.xlsx", "no reader available"))
        self.assertIn("CSV", text)
        self.assertIn("not modified", text)
        self.assertIn("date column", text)

    def test_tier4_dispatch_raises_the_guidance(self):
        from bops.ingest import readers
        original = readers.tier_mod.resolve
        readers.tier_mod.resolve = lambda **kw: readers.tier_mod.ReaderTier(
            readers.tier_mod.TIER_CSV_FALLBACK, "forced for test")
        try:
            with self.assertRaises(ConfigError) as caught:
                readers.read_xlsx(DEMO_XLSX)
            self.assertIn("export", str(caught.exception).lower())
        finally:
            readers.tier_mod.resolve = original


if __name__ == "__main__":
    unittest.main()
