"""Business Context: validation, precedence, gaps, privacy, contradictions (ADR-0011)."""

import json
import os
import shutil
import tempfile
import unittest

from bops import config
from bops.context import loader, privacy
from bops.errors import ConfigError, MissingContextError, VocabularyError


VALID = {
    "schema_version": "1.0.0",
    "identity": {
        "business_name": "Northwind Trading Ltd",
        "industry": "retail_consumer",
        "business_model": "retail",
        "size_band": "50-199",
        "products_services": ["Widget Pro", "Widget Lite"],
        "product_categories": ["home hardware", "garden tools"],
        "geographic_markets": ["United Kingdom", "Ireland"],
    },
    "reporting": {
        "currency": "GBP",
        "fiscal_year_start": "04-06",
        "date_format": "DD/MM/YYYY",
        "reporting_period": "monthly",
    },
    "analysis": {
        "materiality": {"absolute_amount": 5000, "percentage": 2.5},
        "terminology": {"bookings": "signed contract value before delivery"},
    },
}


class ContextTestCase(unittest.TestCase):
    """Shared schema/vocabulary so every test is offline and deterministic."""

    @classmethod
    def setUpClass(cls):
        cls.schema = loader.load_schema()
        cls.vocabulary = config.load_vocabulary()

    def resolve(self, **kwargs):
        kwargs.setdefault("schema", self.schema)
        kwargs.setdefault("vocabulary", self.vocabulary)
        kwargs.setdefault("load_files", False)
        return loader.resolve(**kwargs)


class TestValidation(ContextTestCase):
    def test_valid_context_passes(self):
        self.assertEqual(loader.validate(VALID, self.schema, self.vocabulary), [])

    def test_empty_context_is_valid(self):
        # Every field is optional; absence is a gap, not an error.
        self.assertEqual(loader.validate({}, self.schema, self.vocabulary), [])

    def test_unknown_property_rejected(self):
        bad = {"identity": {"unknown_field": "x"}}
        messages = loader.validate(bad, self.schema, self.vocabulary)
        self.assertTrue(any("unknown property" in m for m in messages), messages)

    def test_wrong_type_rejected(self):
        bad = {"identity": {"business_name": 12345}}
        messages = loader.validate(bad, self.schema, self.vocabulary)
        self.assertTrue(any("expected type string" in m for m in messages), messages)

    def test_currency_pattern_enforced(self):
        messages = loader.validate({"reporting": {"currency": "pounds"}},
                                   self.schema, self.vocabulary)
        self.assertTrue(any("pattern" in m for m in messages), messages)

    def test_fiscal_year_pattern_enforced(self):
        self.assertTrue(loader.validate({"reporting": {"fiscal_year_start": "13-45"}},
                                        self.schema, self.vocabulary))
        self.assertEqual(loader.validate({"reporting": {"fiscal_year_start": "04-06"}},
                                         self.schema, self.vocabulary), [])

    def test_materiality_bounds_enforced(self):
        messages = loader.validate({"analysis": {"materiality": {"percentage": 150}}},
                                   self.schema, self.vocabulary)
        self.assertTrue(any("maximum" in m for m in messages), messages)

    def test_validate_or_raise_raises_config_error(self):
        with self.assertRaises(ConfigError):
            loader.validate_or_raise({"identity": {"business_name": 1}},
                                     self.schema, self.vocabulary)


class TestControlledVocabulary(ContextTestCase):
    def test_unknown_business_model_rejected(self):
        messages = loader.validate({"identity": {"business_model": "crypto_defi_thing"}},
                                   self.schema, self.vocabulary)
        self.assertTrue(any("controlled vocabulary" in m for m in messages), messages)

    def test_rejection_lists_allowed_values_and_forbids_guessing(self):
        messages = loader.validate({"identity": {"business_model": "SAAS"}},
                                   self.schema, self.vocabulary)
        joined = " ".join(messages)
        self.assertIn("saas", joined)                      # shows the real option
        self.assertIn("Ask the user", joined)              # forbids nearest-match guessing

    def test_vocabulary_error_type_raised(self):
        with self.assertRaises(VocabularyError):
            loader.validate_or_raise({"identity": {"industry": "not_a_sector"}},
                                     self.schema, self.vocabulary)

    def test_all_known_business_models_accepted(self):
        for model in self.vocabulary["business_model"]["values"]:
            self.assertEqual(
                loader.validate({"identity": {"business_model": model}},
                                self.schema, self.vocabulary), [], model)

    def test_size_band_must_be_a_band_not_a_number(self):
        self.assertTrue(loader.validate({"identity": {"size_band": "137"}},
                                        self.schema, self.vocabulary))
        self.assertEqual(loader.validate({"identity": {"size_band": "50-199"}},
                                         self.schema, self.vocabulary), [])


class TestPrecedenceAndOverride(ContextTestCase):
    def test_project_overrides_user(self):
        ctx = loader.resolve(
            schema=self.schema, vocabulary=self.vocabulary, load_files=False,
            overrides=None)
        self.assertEqual(ctx.values, {})

    def test_command_override_wins(self):
        ctx = self.resolve(overrides={"reporting": {"currency": "USD"}})
        self.assertEqual(ctx.get("reporting.currency"), "USD")
        self.assertEqual(ctx.source_of("reporting.currency"), "command")

    def test_file_layers_and_precedence(self):
        tmp = tempfile.mkdtemp()
        try:
            user_dir = os.path.join(tmp, "user")
            project_dir = os.path.join(tmp, "project")
            os.makedirs(user_dir)
            os.makedirs(os.path.join(project_dir, ".businessops"))

            with open(os.path.join(user_dir, "business_context.json"), "w",
                      encoding="utf-8") as fh:
                json.dump({"reporting": {"currency": "EUR", "date_format": "DD/MM/YYYY"},
                           "identity": {"business_model": "saas"}}, fh)
            with open(os.path.join(project_dir, ".businessops", "business_context.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({"reporting": {"currency": "GBP"}}, fh)

            ctx = loader.resolve(project_dir=project_dir, user_dir=user_dir,
                                 overrides={"reporting": {"reporting_period": "quarterly"}},
                                 schema=self.schema, vocabulary=self.vocabulary)

            self.assertEqual(ctx.get("reporting.currency"), "GBP")          # project wins
            self.assertEqual(ctx.source_of("reporting.currency"), "project")
            self.assertEqual(ctx.get("reporting.date_format"), "DD/MM/YYYY")  # from user
            self.assertEqual(ctx.source_of("reporting.date_format"), "user")
            self.assertEqual(ctx.get("identity.business_model"), "saas")      # from user
            self.assertEqual(ctx.get("reporting.reporting_period"), "quarterly")
            self.assertEqual(ctx.source_of("reporting.reporting_period"), "command")
            self.assertEqual(ctx.sources, ["user", "project", "command"])
        finally:
            shutil.rmtree(tmp)

    def test_invalid_file_raises_rather_than_being_ignored(self):
        tmp = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmp, ".businessops"))
            with open(os.path.join(tmp, ".businessops", "business_context.json"), "w",
                      encoding="utf-8") as fh:
                json.dump({"identity": {"business_model": "invented_model"}}, fh)
            with self.assertRaises(VocabularyError):
                loader.resolve(project_dir=tmp, user_dir=tmp,
                               schema=self.schema, vocabulary=self.vocabulary)
        finally:
            shutil.rmtree(tmp)


class TestMissingContext(ContextTestCase):
    def test_missing_fields_are_explicit_markers_not_guesses(self):
        ctx = self.resolve()
        paths = {m.path for m in ctx.missing()}
        self.assertIn("identity.business_model", paths)
        self.assertIn("reporting.currency", paths)
        for marker in ctx.missing():
            self.assertIsInstance(marker, loader.MissingField)

    def test_missing_marker_states_what_it_unlocks(self):
        ctx = self.resolve()
        model = next(m for m in ctx.missing() if m.path == "identity.business_model")
        self.assertEqual(model.unlocks, "KPI relevance filtering")

    def test_require_raises_with_specific_fields(self):
        ctx = self.resolve(overrides={"reporting": {"currency": "GBP"}})
        with self.assertRaises(MissingContextError) as caught:
            ctx.require(["identity.business_model", "identity.industry"],
                        purpose="benchmark comparison")
        self.assertEqual(caught.exception.missing_fields,
                         ["identity.business_model", "identity.industry"])
        self.assertIn("benchmark comparison", str(caught.exception))

    def test_require_passes_when_present(self):
        ctx = self.resolve(overrides=VALID)
        self.assertTrue(ctx.require(["identity.business_model", "reporting.currency"]))

    def test_relevance_filtering_off_without_business_model(self):
        self.assertFalse(self.resolve().relevance_filtering_enabled())

    def test_relevance_filtering_on_with_business_model(self):
        ctx = self.resolve(overrides={"identity": {"business_model": "saas"}})
        self.assertTrue(ctx.relevance_filtering_enabled())

    def test_no_field_is_invented_when_absent(self):
        ctx = self.resolve()
        self.assertIsNone(ctx.get("identity.business_model"))
        self.assertFalse(ctx.has("identity.industry"))


class TestPrivacyClassification(ContextTestCase):
    def setUp(self):
        self.ctx = self.resolve(overrides=VALID)

    def test_public_fields_classified_public(self):
        for field in ("identity.industry", "identity.business_model",
                      "identity.size_band", "identity.geographic_markets",
                      "identity.product_categories"):
            self.assertEqual(self.ctx.privacy_class(field), privacy.PUBLIC, field)

    def test_business_name_is_conditional_not_public(self):
        self.assertEqual(self.ctx.privacy_class("identity.business_name"),
                         privacy.CONDITIONAL)

    def test_named_products_are_internal_not_public(self):
        self.assertEqual(self.ctx.privacy_class("identity.products_services"),
                         privacy.INTERNAL)

    def test_terminology_and_materiality_are_internal(self):
        self.assertEqual(self.ctx.privacy_class("analysis.terminology"), privacy.INTERNAL)
        self.assertEqual(self.ctx.privacy_class("analysis.materiality"), privacy.INTERNAL)

    def test_unknown_field_defaults_to_internal_never_public(self):
        self.assertEqual(self.ctx.privacy_class("identity.something_new"),
                         privacy.INTERNAL)

    def test_externalizable_subset_excludes_name_and_products(self):
        subset = self.ctx.externalizable()
        self.assertIn("identity.industry", subset)
        self.assertIn("identity.product_categories", subset)
        self.assertNotIn("identity.business_name", subset)
        self.assertNotIn("identity.products_services", subset)
        self.assertNotIn("analysis.terminology", subset)

    def test_business_name_included_only_when_explicitly_requested(self):
        self.assertIn("identity.business_name",
                      self.ctx.externalizable(include_business_name=True))

    def test_redaction_drops_internal_material(self):
        redacted = self.ctx.redacted()
        blob = json.dumps(redacted)
        self.assertNotIn("Northwind Trading Ltd", blob)
        self.assertNotIn("Widget Pro", blob)
        self.assertIn("retail_consumer", blob)

    def test_tier_mapping_matches_adr_0009(self):
        # M3 split the old catch-all `restricted` into `restricted` (tier 2, approval
        # possible) and `never` (tier 3, no approval path). The original assertion's intent
        # — that some class can never be disclosed — now belongs to `never`.
        self.assertEqual(privacy.TIER_FOR_CLASS[privacy.PUBLIC], 0)
        self.assertEqual(privacy.TIER_FOR_CLASS[privacy.DERIVED_SAFE], 1)
        self.assertEqual(privacy.TIER_FOR_CLASS[privacy.CONDITIONAL], 2)
        self.assertEqual(privacy.TIER_FOR_CLASS[privacy.INTERNAL], 2)
        self.assertEqual(privacy.TIER_FOR_CLASS[privacy.RESTRICTED], 2)
        self.assertIsNone(privacy.TIER_FOR_CLASS[privacy.NEVER])

    def test_no_business_context_field_was_weakened_by_the_m3_split(self):
        # The split would be a silent downgrade if any field had been classed `restricted`
        # under the old meaning. None was.
        class_map = privacy.classification_map(loader.load_schema())
        self.assertEqual([p for p, c in class_map.items() if c == privacy.RESTRICTED], [])

    def test_ordering_runs_least_to_most_sensitive(self):
        self.assertEqual(privacy.ORDER[0], privacy.PUBLIC)
        self.assertEqual(privacy.ORDER[-1], privacy.NEVER)


class TestContradictionDetection(ContextTestCase):
    def setUp(self):
        self.ctx = self.resolve(overrides=VALID)

    def test_currency_contradiction_detected(self):
        found = self.ctx.detect_contradictions({"reporting.currency": "USD"})
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].context_value, "GBP")
        self.assertEqual(found[0].observed_value, "USD")

    def test_currency_contradiction_warns_against_silent_conversion(self):
        found = self.ctx.detect_contradictions({"reporting.currency": "USD"})
        self.assertIn("no conversion is applied automatically", found[0].message())

    def test_agreement_produces_no_finding(self):
        self.assertEqual(self.ctx.detect_contradictions({"reporting.currency": "GBP"}), [])

    def test_comparison_is_case_insensitive_for_strings(self):
        self.assertEqual(self.ctx.detect_contradictions({"reporting.currency": "gbp"}), [])

    def test_absent_context_field_is_not_a_contradiction(self):
        # Nothing was stated, so nothing can conflict — that is a gap, not a conflict.
        ctx = self.resolve()
        self.assertEqual(ctx.detect_contradictions({"reporting.currency": "USD"}), [])

    def test_context_is_not_overwritten_by_observation(self):
        self.ctx.detect_contradictions({"reporting.currency": "USD"})
        self.assertEqual(self.ctx.get("reporting.currency"), "GBP")


class TestSummary(ContextTestCase):
    def test_summary_reports_state_without_leaking_internals(self):
        summary = self.resolve(overrides=VALID).summary()
        self.assertTrue(summary["relevance_filtering"])
        self.assertIn("identity.industry", summary["externalizable_fields"])
        self.assertNotIn("identity.business_name", summary["externalizable_fields"])
        self.assertNotIn("Northwind Trading Ltd", json.dumps(summary))


if __name__ == "__main__":
    unittest.main()
