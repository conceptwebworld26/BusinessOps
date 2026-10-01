"""Normalization, canonical dataset, sensitivity classification and aggregation (M3)."""

import datetime
import os
import unittest
from decimal import Decimal

from bops import normalize, privacy
from bops.ingest import canonical as canonical_mod
from bops.ingest.dataset import Dataset
from bops.privacy import aggregation, classes, sensitivity


def make_dataset(columns, rows):
    return Dataset(columns, rows, "csv", "test.csv")


# ==========================================================================
# Number normalization
# ==========================================================================

class TestNumberNormalization(unittest.TestCase):
    def n(self, raw, **kw):
        return normalize.normalize_number(raw, **kw)

    def test_thousands_and_decimal_anglo(self):
        self.assertEqual(self.n("1,234.56").value, Decimal("1234.56"))

    def test_thousands_and_decimal_european(self):
        self.assertEqual(self.n("1.234,56").value, Decimal("1234.56"))

    def test_space_thousands_separator(self):
        self.assertEqual(self.n("1 234,56").value, Decimal("1234.56"))

    def test_currency_symbol_detected_and_stripped(self):
        result = self.n("£1,234.56")
        self.assertEqual(result.value, Decimal("1234.56"))
        self.assertEqual(result.currency, "GBP")
        self.assertEqual(result.kind, normalize.CURRENCY)

    def test_iso_code_detected(self):
        self.assertEqual(self.n("USD 500").currency, "USD")

    def test_accounting_negative_parentheses(self):
        self.assertEqual(self.n("(1,234.56)").value, Decimal("-1234.56"))

    def test_percent_sign(self):
        result = self.n("45%")
        self.assertEqual(result.kind, normalize.PERCENT)
        self.assertEqual(result.value, Decimal("45"))

    def test_whitespace_tolerated(self):
        self.assertEqual(self.n("  42  ").value, 42)

    def test_missing_representations(self):
        for text in ("", "  ", "n/a", "NULL", "-", "#N/A"):
            self.assertTrue(self.n(text).is_missing, text)

    def test_money_uses_decimal_not_float(self):
        self.assertIsInstance(self.n("0.1").value, Decimal)
        self.assertEqual(self.n("0.1").value + self.n("0.2").value, Decimal("0.3"))

    def test_float_input_avoids_binary_error(self):
        self.assertEqual(self.n(0.1).value, Decimal("0.1"))

    # -- the ambiguity that must never be guessed --------------------------

    def test_single_comma_three_digits_is_ambiguous(self):
        result = self.n("1,234")
        self.assertTrue(result.is_ambiguous)
        self.assertTrue(result.confirm_required)
        self.assertEqual(result.original, "1,234")

    def test_single_dot_three_digits_is_ambiguous(self):
        self.assertTrue(self.n("1.234").is_ambiguous)

    def test_ambiguity_preserves_the_original_value(self):
        self.assertEqual(self.n("1.234").value, "1.234")

    def test_ambiguity_warning_explains_both_readings(self):
        warning = self.n("1.234").warning
        self.assertIn("1.234", warning)
        self.assertIn("1234", warning)

    def test_explicit_convention_resolves_ambiguity(self):
        self.assertEqual(self.n("1.234", assume_separator="european").value,
                         Decimal("1234"))
        self.assertEqual(self.n("1.234", assume_separator="anglo").value,
                         Decimal("1.234"))

    def test_unambiguous_grouping_is_not_flagged(self):
        self.assertEqual(self.n("1,234,567").value, Decimal("1234567"))
        self.assertEqual(self.n("12,5").value, Decimal("12.5"))

    def test_non_numeric_text_stays_text(self):
        self.assertEqual(self.n("abc").kind, normalize.TEXT)


# ==========================================================================
# Date normalization
# ==========================================================================

class TestDateNormalization(unittest.TestCase):
    def d(self, raw, **kw):
        return normalize.normalize_date(raw, **kw)

    def test_iso_date(self):
        self.assertEqual(self.d("2025-01-15").value, datetime.date(2025, 1, 15))

    def test_iso_datetime(self):
        result = self.d("2025-01-15 09:30:00")
        self.assertEqual(result.kind, normalize.DATETIME)

    def test_written_month_forms(self):
        self.assertEqual(self.d("15 Jan 2025").value, datetime.date(2025, 1, 15))
        self.assertEqual(self.d("January 15, 2025").value, datetime.date(2025, 1, 15))

    def test_day_over_twelve_decides_order(self):
        self.assertEqual(self.d("15/01/2025").value, datetime.date(2025, 1, 15))
        self.assertEqual(self.d("01/15/2025").value, datetime.date(2025, 1, 15))

    def test_genuinely_ambiguous_date_is_not_guessed(self):
        result = self.d("03/04/2025")
        self.assertTrue(result.is_ambiguous)
        self.assertTrue(result.confirm_required)
        self.assertIn("April", result.warning)
        self.assertIn("March", result.warning)

    def test_explicit_order_resolves(self):
        self.assertEqual(self.d("03/04/2025", day_first=True).value,
                         datetime.date(2025, 4, 3))
        self.assertEqual(self.d("03/04/2025", day_first=False).value,
                         datetime.date(2025, 3, 4))

    def test_column_evidence_infers_order(self):
        self.assertTrue(normalize.infer_day_first(["03/04/2025", "25/04/2025"]))
        self.assertFalse(normalize.infer_day_first(["03/04/2025", "04/25/2025"]))
        self.assertIsNone(normalize.infer_day_first(["03/04/2025", "05/06/2025"]))

    def test_invalid_calendar_date_is_not_forced(self):
        self.assertNotEqual(self.d("31/02/2025").kind, normalize.DATE)

    def test_datetime_with_midnight_becomes_a_date(self):
        result = self.d(datetime.datetime(2025, 1, 15, 0, 0))
        self.assertEqual(result.kind, normalize.DATE)


class TestBooleanAndText(unittest.TestCase):
    def test_boolean_forms(self):
        for text in ("true", "YES", "y", "1"):
            self.assertIs(normalize.normalize_boolean(text).value, True, text)
        for text in ("false", "No", "n", "0"):
            self.assertIs(normalize.normalize_boolean(text).value, False, text)

    def test_text_whitespace_collapsed(self):
        self.assertEqual(normalize.normalize_text("  a   b  ").value, "a b")


# ==========================================================================
# Column profiling
# ==========================================================================

class TestColumnProfile(unittest.TestCase):
    def test_numeric_column(self):
        profile = normalize.profile_column("Amount", ["1.50", "2.75", "3.00"])
        self.assertEqual(profile.kind, normalize.DECIMAL)

    def test_date_column(self):
        profile = normalize.profile_column("D", ["2025-01-15", "2025-02-15"])
        self.assertEqual(profile.kind, normalize.DATE)

    def test_currency_detected_at_column_level(self):
        profile = normalize.profile_column("A", ["£1.00", "£2.00"])
        self.assertEqual(profile.currencies, ["GBP"])

    def test_mixed_currency_warns(self):
        profile = normalize.profile_column("A", ["£1.00", "$2.00"])
        self.assertEqual(profile.currencies, ["GBP", "USD"])
        self.assertTrue(profile.has_mixed_currency)
        self.assertTrue(any("must not be summed" in w for w in profile.warnings))

    def test_integers_and_decimals_are_one_decimal_column(self):
        profile = normalize.profile_column("A", ["1", "2.5", "3"])
        self.assertEqual(profile.kind, normalize.DECIMAL)
        self.assertFalse(profile.is_mixed)

    def test_genuinely_mixed_column_is_flagged(self):
        profile = normalize.profile_column("A", ["1", "text", "2025-01-15", "x"])
        self.assertTrue(profile.is_mixed)

    def test_missing_counted(self):
        profile = normalize.profile_column("A", ["1", None, "", "n/a", "2"])
        self.assertEqual(profile.missing_count, 3)

    def test_ambiguous_counted_and_explained(self):
        profile = normalize.profile_column("A", ["1.234", "5.678"])
        self.assertEqual(profile.ambiguous_count, 2)
        self.assertTrue(profile.warnings)


# ==========================================================================
# Sensitivity classification
# ==========================================================================

class TestSensitivityClassification(unittest.TestCase):
    def test_credentials_are_never_externalizable(self):
        for column in ("api_key", "Password", "access_token", "client_secret"):
            self.assertEqual(sensitivity.classify_field(column).sensitivity,
                             classes.NEVER, column)

    def test_personal_identifiers_are_never(self):
        for column in ("Email", "Phone", "Address", "Postcode", "DateOfBirth"):
            self.assertEqual(sensitivity.classify_field(column).sensitivity,
                             classes.NEVER, column)

    def test_customer_identity_is_never(self):
        for column in ("Customer", "ClientName", "Contact"):
            self.assertEqual(sensitivity.classify_field(column).sensitivity,
                             classes.NEVER, column)

    def test_individual_people_and_transactions_are_restricted(self):
        for column in ("Salesperson", "OrderID", "InvoiceNo"):
            self.assertEqual(sensitivity.classify_field(column).sensitivity,
                             classes.RESTRICTED, column)

    def test_monetary_measures_are_derived_safe(self):
        for column in ("NetRevenue", "CostOfGoods", "Quantity", "UnitPrice"):
            self.assertEqual(sensitivity.classify_field(column).sensitivity,
                             classes.DERIVED_SAFE, column)

    def test_business_dimensions_are_public(self):
        for column in ("Region", "Category", "OrderDate", "Country"):
            self.assertEqual(sensitivity.classify_field(column).sensitivity,
                             classes.PUBLIC, column)

    def test_unknown_column_defaults_to_internal_never_public(self):
        result = sensitivity.classify_field("zzz_unmatched")
        self.assertEqual(result.sensitivity, classes.INTERNAL)
        self.assertNotEqual(result.sensitivity, classes.PUBLIC)

    def test_content_escalates_over_an_innocent_header(self):
        """A column called Notes full of email addresses must not stay internal."""
        result = sensitivity.classify_field(
            "Notes", ["a@b.com", "c@d.org", "e@f.net"])
        self.assertEqual(result.sensitivity, classes.NEVER)
        self.assertTrue(any("content" in r for r in result.reasons))

    def test_single_credential_in_a_sample_is_enough(self):
        values = ["ordinary text"] * 50 + ["sk_live_abcdefghijklmnop"]
        self.assertEqual(sensitivity.classify_field("Notes", values).sensitivity,
                         classes.NEVER)

    def test_classification_is_deterministic(self):
        values = ["a@b.com", "plain"]
        first = sensitivity.classify_field("Notes", values).sensitivity
        for _ in range(5):
            self.assertEqual(sensitivity.classify_field("Notes", values).sensitivity,
                             first)

    def test_reasons_are_recorded_for_audit(self):
        self.assertTrue(sensitivity.classify_field("Customer", ["Acme"]).reasons)

    def test_dataset_classification_and_summary(self):
        dataset = make_dataset(["Region", "Customer", "NetRevenue"],
                               [{"Region": "North", "Customer": "Acme",
                                 "NetRevenue": 10.0}])
        smap = sensitivity.classify_dataset(dataset)
        self.assertEqual(smap.never_externalizable_columns(), ["Customer"])
        self.assertEqual(smap.externalizable_columns(), ["Region"])
        self.assertEqual(smap.dataset_sensitivity(), classes.NEVER)


class TestSensitivityClasses(unittest.TestCase):
    def test_tier_mapping(self):
        self.assertEqual(classes.max_tier(classes.PUBLIC), 0)
        self.assertEqual(classes.max_tier(classes.DERIVED_SAFE), 1)
        self.assertEqual(classes.max_tier(classes.RESTRICTED), 2)
        self.assertIsNone(classes.max_tier(classes.NEVER))

    def test_never_has_no_approval_path(self):
        self.assertFalse(classes.is_externalizable(classes.NEVER))
        self.assertIn(classes.NEVER, classes.NO_APPROVAL_PATH)

    def test_most_sensitive_wins(self):
        self.assertEqual(
            classes.most_sensitive([classes.PUBLIC, classes.NEVER, classes.INTERNAL]),
            classes.NEVER)

    def test_unknown_class_ranks_as_most_sensitive(self):
        self.assertEqual(classes.rank("nonsense"), len(classes.ORDER) - 1)

    def test_permitted_at_tier(self):
        self.assertTrue(classes.permitted_at_tier(classes.PUBLIC, 0))
        self.assertFalse(classes.permitted_at_tier(classes.DERIVED_SAFE, 0))
        self.assertFalse(classes.permitted_at_tier(classes.NEVER, 3))


# ==========================================================================
# Privacy-preserving aggregation
# ==========================================================================

class TestAggregationPrimitives(unittest.TestCase):
    def test_entity_counting(self):
        rows = [{"c": "a"}, {"c": "b"}, {"c": "a"}, {"c": None}]
        self.assertEqual(aggregation.count_entities(rows, "c"), 2)

    def test_banding_never_reveals_an_exact_figure(self):
        self.assertEqual(aggregation.band_count(137), "50-199")
        self.assertIn("1m-5m", aggregation.band_amount(2500000, "GBP"))

    def test_rate_calculation(self):
        self.assertEqual(aggregation.as_rate(35, 100), Decimal("35.0"))

    def test_rate_descriptor_is_tier1_eligible(self):
        descriptor = aggregation.rate_descriptor("churn", 8, 100, entity_count=40)
        assessment = aggregation.assess_disclosure(descriptor)
        self.assertTrue(assessment.permitted)
        self.assertEqual(assessment.tier, 1)

    def test_exact_amount_fails_the_banding_check(self):
        # Classified explicitly: since 2026-09-10 an unclassified aggregate fails closed on
        # `sensitivity_unresolved` before any other check runs, which would mask the
        # banding failure this test exists to prove. The fail-closed behaviour itself is
        # covered in tests/unit/test_m9_governance.py.
        descriptor = aggregation.AggregateDescriptor(
            "revenue", Decimal("3467850.16"), aggregation.EXACT, 40,
            source_sensitivity=classes.DERIVED_SAFE)
        assessment = aggregation.assess_disclosure(descriptor)
        self.assertFalse(assessment.permitted)
        self.assertIn("banding", assessment.failed_checks)

    def test_banded_amount_passes(self):
        descriptor = aggregation.banded_amount_descriptor(
            "revenue", Decimal("3467850.16"), entity_count=40, currency="GBP")
        self.assertTrue(aggregation.assess_disclosure(descriptor).permitted)

    def test_small_group_fails_the_k_floor(self):
        descriptor = aggregation.rate_descriptor("churn", 1, 3, entity_count=3)
        assessment = aggregation.assess_disclosure(descriptor)
        self.assertFalse(assessment.permitted)
        self.assertIn("aggregation_floor", assessment.failed_checks)

    def test_unknown_entity_count_fails_closed(self):
        descriptor = aggregation.AggregateDescriptor(
            "x", Decimal("1"), aggregation.RATE, None)
        self.assertFalse(aggregation.assess_disclosure(descriptor).permitted)

    def test_never_class_is_refused_outright(self):
        descriptor = aggregation.AggregateDescriptor(
            "x", "banded", aggregation.BANDED, 100,
            source_sensitivity=classes.NEVER)
        assessment = aggregation.assess_disclosure(descriptor)
        self.assertFalse(assessment.permitted)
        self.assertIsNone(assessment.tier)
        self.assertIn("never_externalizable", assessment.failed_checks)

    def test_reidentification_evaluates_the_whole_query(self):
        safe = aggregation.assess_reidentification(["industry", "region"])
        self.assertFalse(safe["risky"])
        risky = aggregation.assess_reidentification(
            ["industry", "region", "revenue_band", "employee_band", "founding_year"])
        self.assertTrue(risky["risky"])

    def test_two_highly_narrowing_attributes_are_risky(self):
        result = aggregation.assess_reidentification(["revenue_band", "employee_band"])
        self.assertTrue(result["risky"])

    def test_reidentification_failure_blocks_disclosure(self):
        descriptor = aggregation.rate_descriptor("margin", 35, 100, entity_count=50)
        assessment = aggregation.assess_disclosure(
            descriptor,
            query_attributes=["industry", "region", "revenue_band", "employee_band",
                              "founding_year"])
        self.assertFalse(assessment.permitted)
        self.assertIn("reidentification", assessment.failed_checks)

    def test_assessment_always_explains_itself(self):
        assessment = aggregation.assess_disclosure(
            aggregation.rate_descriptor("x", 1, 2, entity_count=10))
        self.assertTrue(assessment.reasons)


# ==========================================================================
# Canonical dataset
# ==========================================================================

class TestCanonicalDataset(unittest.TestCase):
    def setUp(self):
        self.dataset = make_dataset(
            ["OrderDate", "Customer", "NetRevenue"],
            [{"OrderDate": "2025-01-15", "Customer": "Acme", "NetRevenue": "£1,000.00"},
             {"OrderDate": "2025-02-15", "Customer": "Beta", "NetRevenue": "£2,000.00"}])
        self.canonical = canonical_mod.build(self.dataset)

    def test_field_names_are_normalized_but_originals_kept(self):
        field = self.canonical.field("NetRevenue")
        self.assertEqual(field.name, "net_revenue")
        self.assertEqual(field.original_name, "NetRevenue")

    def test_raw_and_normalized_views_are_both_available(self):
        self.assertEqual(self.canonical.raw_rows()[0]["NetRevenue"], "£1,000.00")
        self.assertEqual(self.canonical.normalized_rows()[0]["NetRevenue"],
                         Decimal("1000.00"))

    def test_normalization_does_not_mutate_the_source(self):
        self.canonical.normalized_rows()
        self.assertEqual(self.dataset.rows[0]["NetRevenue"], "£1,000.00")

    def test_currency_detected(self):
        self.assertEqual(self.canonical.currencies(), ["GBP"])
        self.assertFalse(self.canonical.has_mixed_currency())

    def test_sensitivity_attached_per_field(self):
        self.assertEqual(self.canonical.never_externalizable_columns(), ["Customer"])

    def test_processing_mode_recorded_and_complete(self):
        self.assertEqual(self.canonical.processing_mode, canonical_mod.FULL)
        self.assertTrue(self.canonical.complete)

    def test_provenance_carries_everything_downstream_needs(self):
        provenance = self.canonical.provenance()
        for key in ("processing_mode", "rows_examined", "complete", "currencies",
                    "fields", "sensitivity", "normalization"):
            self.assertIn(key, provenance)

    def test_sampled_mode_marks_the_result_incomplete(self):
        canonical = canonical_mod.CanonicalDataset(
            self.dataset, [], processing_mode=canonical_mod.SAMPLED, rows_examined=1)
        self.assertFalse(canonical.complete)

    def test_mixed_currency_raises_a_dataset_warning(self):
        dataset = make_dataset(["Amount"], [{"Amount": "£1.00"}, {"Amount": "$2.00"}])
        canonical = canonical_mod.build(dataset)
        self.assertTrue(canonical.has_mixed_currency())
        self.assertTrue(any("no conversion" in w for w in canonical.warnings))

    def test_name_normalization_rules(self):
        self.assertEqual(canonical_mod.normalize_name("Net Revenue"), "net_revenue")
        self.assertEqual(canonical_mod.normalize_name("NetRevenue"), "net_revenue")
        self.assertEqual(canonical_mod.normalize_name("net-revenue "), "net_revenue")


if __name__ == "__main__":
    unittest.main()
