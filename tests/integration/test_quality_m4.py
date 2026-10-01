"""Milestone 4 — the complete data quality layer.

Covers every family against a clean baseline and a deliberately broken fixture, the schema,
the severity model, the quality gate, threshold provenance, privacy, and behaviour under a
degraded processing mode.
"""

import json
import os
import shutil
import tempfile
import unittest

from bops import ingest, pipeline, quality
from bops import config as config_mod
from bops import mapping as mapping_mod
from bops.ingest import canonical as canonical_mod
from bops.quality import checks as quality_checks
from bops.quality import report as report_mod
from bops.runtime import tiers

from fixtures import build_quality_fixtures as fixtures
from fixtures import build_workbooks

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO_CSV = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
DEMO_CONTEXT = os.path.join(REPO, "assets", "demo-data", "business_context.json")


def demo_context():
    with open(DEMO_CONTEXT, encoding="utf-8") as fh:
        return json.load(fh)


class QualityCase(unittest.TestCase):
    """Runs the real quality engine over a file, with no mocking."""

    @classmethod
    def setUpClass(cls):
        cls.schema = report_mod.load_schema()

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bops-m4-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def assess(self, path, context_overrides=None, command_args=None):
        dataset = ingest.read(path)
        canonical = canonical_mod.build(dataset)
        semantic_map = mapping_mod.infer(dataset)
        business_context = None
        if context_overrides is not None:
            from bops.context import loader
            business_context = loader.resolve(overrides=context_overrides,
                                              load_files=False)
        config = config_mod.resolve(defaults=config_mod.load_defaults(),
                                    command_args=command_args)
        return quality_checks.run(dataset, semantic_map, config, canonical,
                                  business_context)


# ==========================================================================
# The 13 families: clean baseline and broken fixture
# ==========================================================================

class TestAllFamilies(QualityCase):

    def test_thirteen_families_are_registered(self):
        self.assertEqual(len(quality.CHECK_IDS), 13)
        self.assertEqual(len(set(quality.CHECK_IDS)), 13, "identifiers must be unique")

    def test_every_family_declares_a_complete_spec(self):
        for spec in quality.specs():
            self.assertTrue(spec.check_id)
            self.assertTrue(spec.title)
            self.assertTrue(spec.purpose)
            self.assertTrue(spec.detects)
            self.assertTrue(spec.severity_policy)
            self.assertIsInstance(spec.can_halt, bool)

    def test_clean_data_passes_every_family(self):
        report = self.assess(fixtures.clean(self.tmp))
        self.assertEqual(report.grade, quality.PASS, [f.message for f in report.findings])
        self.assertFalse(report.halted)

    def test_clean_data_still_runs_every_family(self):
        report = self.assess(fixtures.clean(self.tmp))
        ran = set(report.families_run)
        skipped = set(report.families_skipped)
        self.assertEqual(len(ran | skipped), 13)
        # On a well-formed sales file nothing should need skipping.
        self.assertEqual(skipped, set(), "families skipped: %s" % skipped)

    def test_each_broken_fixture_produces_its_expected_finding(self):
        for builder, check_id, severity, halts in fixtures.EXPECTATIONS:
            with self.subTest(family=check_id):
                report = self.assess(builder(self.tmp))
                findings = report.by_check(check_id)
                self.assertTrue(findings,
                                "%s produced no finding for %s" % (builder.__name__,
                                                                   check_id))
                severities = {f.severity for f in findings}
                self.assertIn(severity, severities,
                              "%s: expected %s, got %s" % (check_id, severity, severities))

    def test_each_broken_fixture_halts_or_continues_as_declared(self):
        for builder, check_id, severity, halts in fixtures.EXPECTATIONS:
            with self.subTest(family=check_id):
                report = self.assess(builder(self.tmp))
                if halts:
                    self.assertTrue(report.halted, "%s should halt" % check_id)
                else:
                    findings = report.by_check(check_id)
                    self.assertFalse(any(f.halts for f in findings),
                                     "%s must not halt" % check_id)

    def test_broken_formulas_family_fires_on_a_workbook(self):
        path = build_workbooks.formula_without_cached_value(self.tmp)
        dataset = ingest.read_xlsx(path, prefer_tier=tiers.TIER_STDLIB)
        canonical = canonical_mod.build(dataset)
        report = quality_checks.run(
            dataset, mapping_mod.infer(dataset),
            config_mod.resolve(defaults=config_mod.load_defaults()), canonical)
        findings = report.by_check("broken_formulas")
        self.assertTrue(findings)
        self.assertIn("formula_without_cached_value", {f.code for f in findings})

    def test_no_family_can_halt_unless_its_spec_permits(self):
        for builder, _cid, _sev, _halts in fixtures.EXPECTATIONS:
            report = self.assess(builder(self.tmp))
            for finding in report.findings:
                if finding.halts:
                    spec = quality.spec_for(finding.check_id)
                    self.assertTrue(spec.can_halt,
                                    "%s halted but its spec forbids it" % finding.check_id)

    def test_source_file_is_byte_identical_after_every_check(self):
        for builder, _cid, _sev, _halts in fixtures.EXPECTATIONS:
            path = builder(self.tmp)
            before = open(path, "rb").read()
            self.assess(path)
            self.assertEqual(open(path, "rb").read(), before,
                             "%s was modified by the quality run" % builder.__name__)


# ==========================================================================
# Severity model
# ==========================================================================

class TestSeverityModel(QualityCase):

    def test_info_only_grades_as_pass(self):
        report = self.assess(fixtures.missing_values_minor(self.tmp))
        self.assertTrue(all(f.severity == quality.INFO for f in report.findings),
                        [f.as_dict() for f in report.findings])
        self.assertEqual(report.grade, quality.PASS)
        self.assertFalse(report.halted)

    def test_warning_continues_but_is_reported(self):
        report = self.assess(fixtures.warning_only(self.tmp))
        self.assertEqual(report.grade, quality.WARNING)
        self.assertFalse(report.halted)
        self.assertTrue(report.warnings)

    def test_critical_halts(self):
        report = self.assess(fixtures.missing_values(self.tmp))
        self.assertEqual(report.grade, quality.CRITICAL)
        self.assertTrue(report.halted)

    def test_grade_is_the_highest_severity_present(self):
        report = self.assess(fixtures.multiple_failures(self.tmp))
        self.assertEqual(report.grade, quality.CRITICAL)

    def test_a_small_proportion_of_bad_numbers_only_warns(self):
        report = self.assess(fixtures.invalid_numbers_minor(self.tmp))
        findings = report.by_check("invalid_numbers")
        self.assertTrue(findings)
        self.assertEqual({f.severity for f in findings}, {quality.WARNING})
        self.assertFalse(report.halted)

    def test_unusual_but_valid_values_are_not_critical(self):
        """A negative or outlying value is not by itself unusable data."""
        for builder in (fixtures.negative_values, fixtures.outliers):
            report = self.assess(builder(self.tmp))
            self.assertFalse(report.halted, builder.__name__)

    def test_outliers_are_framed_as_data_integrity_not_fraud(self):
        report = self.assess(fixtures.outliers(self.tmp))
        findings = report.by_check("outliers")
        self.assertTrue(findings)
        text = " ".join((f.message + " " + (f.detail or "")) for f in findings).lower()
        self.assertNotIn("fraud", text)
        self.assertNotIn("suspicious activity", text)
        self.assertIn("decimal", text)

    def test_secondary_problems_are_not_hidden_by_a_critical_one(self):
        report = self.assess(fixtures.multiple_failures(self.tmp))
        families = {f.check_id for f in report.findings}
        self.assertGreaterEqual(len(families), 3, families)
        self.assertTrue(report.critical)
        self.assertTrue(report.warnings)


# ==========================================================================
# Schema
# ==========================================================================

class TestQualityReportSchema(QualityCase):

    def test_schema_uses_only_enforced_keywords(self):
        from bops import jsonschema_mini
        self.assertEqual(jsonschema_mini.unsupported_keywords(self.schema), set())

    def test_clean_report_validates(self):
        report = self.assess(fixtures.clean(self.tmp))
        self.assertEqual(report.validate(self.schema), [])

    def test_every_broken_fixture_report_validates(self):
        for builder, check_id, _sev, _halts in fixtures.EXPECTATIONS:
            with self.subTest(family=check_id):
                report = self.assess(builder(self.tmp))
                self.assertEqual(report.validate(self.schema), [])

    def test_report_carries_the_required_top_level_facts(self):
        document = self.assess(fixtures.warning_only(self.tmp)).as_dict()
        for key in ("schema_version", "grade", "halted", "completeness",
                    "rows_checked", "columns_checked", "findings", "checks",
                    "source", "finding_counts"):
            self.assertIn(key, document)

    def test_every_finding_is_machine_readable_and_explained(self):
        report = self.assess(fixtures.multiple_failures(self.tmp))
        for finding in report.findings:
            self.assertTrue(finding.check_id)
            self.assertTrue(finding.code)
            self.assertIn(finding.severity, (quality.INFO, quality.WARNING,
                                             quality.CRITICAL))
            self.assertTrue(finding.message)
            self.assertIsInstance(finding.halts, bool)

    def test_report_is_deterministic(self):
        path = fixtures.multiple_failures(self.tmp)
        first = json.dumps(self.assess(path).as_dict(), sort_keys=True, default=str)
        second = json.dumps(self.assess(path).as_dict(), sort_keys=True, default=str)
        self.assertEqual(first, second)

    def test_source_identity_is_recorded(self):
        document = self.assess(fixtures.clean(self.tmp)).as_dict()
        self.assertEqual(document["source"]["source_type"], "csv")
        self.assertTrue(document["source"]["source_name"])

    def test_invalid_document_is_rejected(self):
        bad = {"schema_version": "1.0.0", "grade": "SPLENDID", "halted": False,
               "rows_checked": 1, "findings": []}
        self.assertTrue(report_mod.validate_document(bad, self.schema))


# ==========================================================================
# Thresholds and configuration
# ==========================================================================

class TestThresholds(QualityCase):

    def test_finding_records_the_threshold_and_its_source(self):
        report = self.assess(fixtures.missing_values(self.tmp))
        finding = report.by_check("missing_values")[0]
        self.assertEqual(finding.threshold["key"], "quality.max_missing_pct")
        self.assertEqual(finding.threshold["source"], "default")
        self.assertIsNotNone(finding.observed)

    def test_observed_value_is_distinct_from_the_threshold(self):
        report = self.assess(fixtures.missing_values(self.tmp))
        finding = report.by_check("missing_values")[0]
        self.assertNotEqual(finding.observed, finding.threshold["value"])
        self.assertGreater(finding.observed, finding.threshold["value"])

    def test_command_argument_overrides_the_default(self):
        path = fixtures.missing_values(self.tmp)
        relaxed = self.assess(path, command_args={"quality": {"max_missing_pct": 99.0}})
        finding = relaxed.by_check("missing_values")[0]
        self.assertEqual(finding.threshold["source"], "command")
        self.assertEqual(finding.severity, quality.INFO)
        self.assertFalse(relaxed.halted)

    def test_tightening_a_threshold_creates_a_finding(self):
        path = fixtures.clean(self.tmp)
        self.assertEqual(self.assess(path).grade, quality.PASS)
        strict = self.assess(path, command_args={"quality": {"min_periods": 24}})
        self.assertTrue(strict.by_check("missing_periods"))

    def test_no_threshold_is_hard_coded_where_config_exists(self):
        for spec in quality.specs():
            for key in spec.thresholds:
                self.assertTrue(key.startswith("quality."), key)


# ==========================================================================
# Business Context interaction
# ==========================================================================

class TestBusinessContextInteraction(QualityCase):

    def test_missing_business_context_does_not_invalidate_good_data(self):
        report = self.assess(fixtures.clean(self.tmp), context_overrides=None)
        self.assertEqual(report.grade, quality.PASS)

    def test_currency_contradiction_is_detected_with_context(self):
        path = fixtures.currency_contradiction(self.tmp)
        without = self.assess(path)
        with_context = self.assess(path, context_overrides=demo_context())  # GBP
        self.assertFalse(any(f.code == "currency_contradiction"
                             for f in without.findings))
        self.assertTrue(any(f.code == "currency_contradiction"
                            for f in with_context.findings))
        self.assertTrue(with_context.halted)

    def test_quality_does_not_depend_on_kpi_applicability(self):
        """A not_applicable KPI is not a data-quality defect."""
        result = pipeline.run(DEMO_CSV, context_overrides=demo_context(),
                              load_context_files=False)
        self.assertEqual(result.kpis["net_revenue_retention"].status, "not_applicable")
        self.assertFalse(result.quality.halted)
        codes = {f.code for f in result.quality.findings}
        self.assertNotIn("net_revenue_retention", codes)


# ==========================================================================
# Privacy
# ==========================================================================

class TestPrivacyInReports(QualityCase):

    def test_sensitive_values_are_redacted_in_evidence(self):
        report = self.assess(fixtures.sensitive_columns(self.tmp))
        blob = json.dumps(report.as_dict(), default=str)
        self.assertNotIn("person1@example.com", blob)
        self.assertNotIn("person2@example.com", blob)

    def test_customer_labels_are_redacted_but_the_finding_still_fires(self):
        report = self.assess(fixtures.inconsistent_customers(self.tmp))
        findings = report.by_check("inconsistent_customers")
        self.assertTrue(findings)
        blob = json.dumps([f.as_dict() for f in findings], default=str)
        self.assertNotIn("Acme Ltd", blob)
        self.assertIn("redacted", blob)

    def test_counts_and_percentages_are_still_reported(self):
        report = self.assess(fixtures.inconsistent_customers(self.tmp))
        finding = report.by_check("inconsistent_customers")[0]
        self.assertIn("variant_groups", finding.evidence)
        self.assertGreater(finding.affected, 0)

    def test_field_names_are_reported_while_values_are_withheld(self):
        report = self.assess(fixtures.sensitive_columns(self.tmp))
        finding = report.by_check("inconsistent_customers")[0]
        self.assertEqual(finding.fields, ["Customer"])   # the name is safe to name
        blob = json.dumps(finding.as_dict(), default=str)
        self.assertNotIn("Acme", blob)                   # the values are not

    def test_no_credentials_leak_into_a_report(self):
        path = os.path.join(self.tmp, "creds.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("OrderDate,NetRevenue,api_key\n")
            for month in range(1, 7):
                fh.write("2025-%02d-15,1000.00,sk_live_abcdefghijklmnop\n" % month)
        blob = json.dumps(self.assess(path).as_dict(), default=str)
        self.assertNotIn("sk_live_abcdefghijklmnop", blob)


# ==========================================================================
# Processing mode
# ==========================================================================

class TestProcessingMode(QualityCase):

    def _sampled_report(self, path):
        dataset = ingest.read(path)
        canonical = canonical_mod.build(dataset, processing_mode=canonical_mod.SAMPLED,
                                        rows_examined=5)
        return quality_checks.run(
            dataset, mapping_mod.infer(dataset),
            config_mod.resolve(defaults=config_mod.load_defaults()), canonical)

    def test_sampled_run_is_never_reported_as_exhaustive(self):
        report = self._sampled_report(fixtures.clean(self.tmp))
        self.assertEqual(report.completeness, quality.PARTIAL)
        self.assertNotEqual(report.completeness, quality.EXHAUSTIVE)

    def test_every_finding_carries_the_partial_marker(self):
        report = self._sampled_report(fixtures.warning_only(self.tmp))
        for finding in report.findings:
            self.assertEqual(finding.completeness, quality.PARTIAL)

    def test_partial_processing_adds_a_caveat(self):
        report = self._sampled_report(fixtures.clean(self.tmp))
        self.assertTrue(any("not exhaustive" in c for c in report.caveats()))

    def test_partial_processing_raises_a_structural_finding(self):
        report = self._sampled_report(fixtures.clean(self.tmp))
        self.assertIn("partial_processing", {f.code for f in report.findings})

    def test_full_processing_is_exhaustive(self):
        report = self.assess(fixtures.clean(self.tmp))
        self.assertEqual(report.completeness, quality.EXHAUSTIVE)
        self.assertEqual(report.as_dict()["processing_mode"], canonical_mod.FULL)


# ==========================================================================
# The quality gate in the pipeline
# ==========================================================================

class TestQualityGate(QualityCase):

    def test_clean_data_passes_the_gate(self):
        result = pipeline.run(fixtures.clean(self.tmp), load_context_files=False)
        self.assertFalse(result.halted)
        self.assertTrue(result.kpis)

    def test_warning_data_passes_with_warnings_preserved(self):
        result = pipeline.run(fixtures.warning_only(self.tmp), load_context_files=False)
        self.assertFalse(result.halted)
        self.assertEqual(result.quality.grade, quality.WARNING)
        for claim in result.ledger.claims:
            self.assertTrue(claim.caveats, "warnings must travel with every claim")

    def test_critical_data_halts_the_gate(self):
        result = pipeline.run(fixtures.missing_values(self.tmp), load_context_files=False)
        self.assertTrue(result.halted)
        self.assertEqual(result.halted_at, "quality_gate")
        self.assertEqual(result.kpis, {})

    def test_gate_exposes_structured_findings(self):
        result = pipeline.run(fixtures.multiple_failures(self.tmp),
                              load_context_files=False)
        self.assertTrue(result.quality.check_results)
        self.assertEqual(result.quality.validate(self.schema), [])

    def test_gate_preserves_provenance(self):
        result = pipeline.run(fixtures.clean(self.tmp), load_context_files=False)
        source = result.quality.as_dict()["source"]
        self.assertEqual(source["source_type"], "csv")
        self.assertTrue(source["source_name"])


if __name__ == "__main__":
    unittest.main()
