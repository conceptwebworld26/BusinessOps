"""Milestone 2 vertical slice — the six required scenarios, end to end.

Nothing here mocks the pipeline. Each scenario drives real ingestion, real mapping, the real
quality gate, the real KPI engine and the real renderer, so a failure means the architecture
is wrong rather than a stub drifted.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal

from bops import analytics, evidence, pipeline, render
from bops.context import loader as context_loader
from bops.kpi import registry as kpi_registry
from bops.mapping import semantic
from bops.quality import checks as quality_checks
from bops.runtime import tiers

from fixtures import build_fixtures

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO_DIR = os.path.join(REPO, "assets", "demo-data")
DEMO_CSV = os.path.join(DEMO_DIR, "northwind_sales.csv")
DEMO_XLSX = os.path.join(DEMO_DIR, "northwind_sales.xlsx")
DEMO_CONTEXT_FILE = os.path.join(DEMO_DIR, "business_context.json")


def demo_context():
    with open(DEMO_CONTEXT_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def run_demo(**kwargs):
    kwargs.setdefault("context_overrides", demo_context())
    kwargs.setdefault("load_context_files", False)
    return pipeline.run(DEMO_CSV, **kwargs)


class FixtureMixin:
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bops-m2-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


# ==========================================================================
# Scenario A — clean data, full pipeline
# ==========================================================================

class TestScenarioACleanData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = run_demo()

    def test_demo_dataset_exists_and_is_committed(self):
        self.assertTrue(os.path.exists(DEMO_CSV))
        self.assertTrue(os.path.exists(DEMO_XLSX))

    def test_ingestion_succeeds(self):
        self.assertEqual(self.result.dataset.row_count, 2204)
        self.assertEqual(self.result.dataset.column_count, 12)
        self.assertEqual(self.result.dataset.source_type, "csv")

    def test_dataset_spans_24_months(self):
        series = self.result.analysis["revenue_trend"]["series"]
        self.assertEqual(len(series), 24)
        self.assertEqual(series[0][0], "2024-01")
        self.assertEqual(series[-1][0], "2025-12")

    def test_mapping_succeeds_for_every_required_role(self):
        for role in (semantic.DATE, semantic.REVENUE, semantic.COST,
                     semantic.CUSTOMER, semantic.PRODUCT, semantic.REGION,
                     semantic.SALESPERSON, semantic.QUANTITY):
            self.assertTrue(self.result.semantic_map.confirmed(role), role)

    def test_quality_gate_passes(self):
        self.assertEqual(self.result.quality.grade, quality_checks.PASS)
        self.assertFalse(self.result.halted)

    def test_five_kpis_computed(self):
        computed = kpi_registry.bucket(self.result.kpis)[kpi_registry.COMPUTED]
        self.assertGreaterEqual(len(computed), 5)
        for kpi_id in ("revenue", "revenue_growth", "gross_profit",
                       "gross_margin", "average_order_value"):
            self.assertEqual(self.result.kpis[kpi_id].status, kpi_registry.COMPUTED)

    def test_kpi_values_are_exact_and_reproducible(self):
        # Deterministic dataset + deterministic engine = assertable figures.
        # Money is exact. Percentages carry full precision in the engine and are rounded
        # once at presentation (CLAUDE.md section 4), so the margin is asserted at the
        # precision it is presented with - equally strict, not weaker.
        self.assertEqual(self.result.kpis["revenue"].value, Decimal("3467850.16"))
        self.assertEqual(self.result.kpis["gross_profit"].value, Decimal("1210775.23"))
        self.assertEqual(
            self.result.kpis["gross_margin"].value.quantize(Decimal("0.0001")),
            Decimal("34.9143"))
        self.assertEqual(
            self.result.kpis["average_order_value"].value.quantize(Decimal("0.01")),
            Decimal("1573.43"))

    def test_gross_profit_equals_revenue_minus_cost(self):
        revenue = self.result.kpis["revenue"].value
        profit = self.result.kpis["gross_profit"].value
        margin = self.result.kpis["gross_margin"].value
        self.assertEqual(margin.quantize(Decimal("0.01")),
                         (profit / revenue * 100).quantize(Decimal("0.01")))

    def test_rerunning_gives_identical_figures(self):
        again = run_demo()
        for kpi_id, result in self.result.kpis.items():
            self.assertEqual(again.kpis[kpi_id].value, result.value, kpi_id)

    def test_analysis_produces_findings(self):
        findings = analytics.build_findings(
            self.result, lambda v: render.money(v, "GBP"))
        self.assertGreater(len(findings), 4)
        self.assertTrue(any(f["direction"] == "positive" for f in findings))
        self.assertTrue(any(f["direction"] == "negative" for f in findings))

    def test_planted_trends_are_actually_found(self):
        """The dataset documents specific trends; the analysis must surface them."""
        findings = analytics.build_findings(
            self.result, lambda v: render.money(v, "GBP"))
        text = " ".join(f["statement"] for f in findings)
        self.assertIn("Legacy Crates", text)        # the declining product
        self.assertIn("Chilled Logistics", text)    # the launch product
        self.assertIn("North", text)                # the strongest region
        self.assertIn("margin", text.lower())       # the margin compression

    def test_margin_compression_is_detected_and_material(self):
        verdict = self.result.analysis["margin_materiality"]
        self.assertEqual(verdict.outcome, "material")
        self.assertLess(self.result.analysis["margin_later_pct"],
                        self.result.analysis["margin_earlier_pct"])

    def test_executive_output_is_generated_with_required_sections(self):
        findings = analytics.build_findings(
            self.result, lambda v: render.money(v, "GBP"))
        output = render.render(self.result, findings)
        for section in ("Business Health Snapshot", "Reporting basis", "KPI scorecard",
                        "Key findings", "Data quality", "Provenance",
                        "Confidence and limitations"):
            self.assertIn(section, output, section)

    def test_output_uses_business_context_currency(self):
        output = render.render(self.result, [])
        self.assertIn("£", output)
        self.assertNotIn("$", output)


# ==========================================================================
# Scenario B — deliberately broken data must halt
# ==========================================================================

class TestScenarioBBrokenData(FixtureMixin, unittest.TestCase):
    def _run(self, path):
        return pipeline.run(path, context_overrides=demo_context(),
                            load_context_files=False)

    def test_missing_revenue_values_halt_the_pipeline(self):
        result = self._run(build_fixtures.critical_missing_revenue(self.tmp))
        self.assertTrue(result.halted)
        self.assertEqual(result.halted_at, "quality_gate")
        self.assertEqual(result.quality.grade, quality_checks.CRITICAL)

    def test_no_revenue_column_halts_the_pipeline(self):
        result = self._run(build_fixtures.critical_no_revenue_column(self.tmp))
        self.assertTrue(result.halted)
        self.assertTrue(any("revenue" in f.message.lower() for f in result.quality.critical))

    def test_invalid_dates_halt_the_pipeline(self):
        result = self._run(build_fixtures.critical_invalid_dates(self.tmp))
        self.assertTrue(result.halted)

    def test_no_kpis_are_produced_when_halted(self):
        result = self._run(build_fixtures.critical_missing_revenue(self.tmp))
        self.assertEqual(result.kpis, {})

    def test_halt_reason_explains_why(self):
        result = self._run(build_fixtures.critical_missing_revenue(self.tmp))
        reason = result.halt_reason
        self.assertIn("quality gate", reason.lower())
        self.assertIn("misleading", reason.lower())

    def test_output_does_not_pretend_to_be_valid(self):
        result = self._run(build_fixtures.critical_missing_revenue(self.tmp))
        output = render.render(result, [])
        self.assertIn("Analysis stopped", output)
        self.assertIn("No KPIs, findings or conclusions are reported", output)
        # Nothing that would imply a usable result
        self.assertNotIn("KPI scorecard", output)
        self.assertNotIn("Key findings", output)

    def test_source_data_is_never_repaired(self):
        path = build_fixtures.critical_missing_revenue(self.tmp)
        before = open(path, "rb").read()
        self._run(path)
        self.assertEqual(open(path, "rb").read(), before)

    def test_warnings_alone_do_not_halt(self):
        result = self._run(build_fixtures.warning_duplicates(self.tmp))
        self.assertFalse(result.halted)
        self.assertEqual(result.quality.grade, quality_checks.WARNING)
        self.assertTrue(result.kpis)

    def test_warnings_survive_into_the_evidence(self):
        result = self._run(build_fixtures.warning_duplicates(self.tmp))
        summary = result.ledger.summary()
        self.assertTrue(summary["global_caveats"])
        for claim in result.ledger.claims:
            self.assertTrue(claim.caveats, "every claim must carry the quality caveat")

    def test_warnings_appear_before_the_numbers_in_output(self):
        result = self._run(build_fixtures.warning_duplicates(self.tmp))
        output = render.render(result, [])
        self.assertLess(output.index("Data quality: WARNING"), output.index("KPI scorecard"))


# ==========================================================================
# Scenario C — Business Context drives KPI relevance
# ==========================================================================

class TestScenarioCBusinessContextRelevance(unittest.TestCase):
    def test_not_applicable_comes_from_the_business_model(self):
        result = run_demo()
        nrr = result.kpis["net_revenue_retention"]
        self.assertEqual(nrr.status, kpi_registry.NOT_APPLICABLE)
        self.assertIn("recurring", nrr.reason.lower())

    def test_same_kpi_is_attempted_for_a_saas_model(self):
        """Proves the classification comes from context, not a hard-coded result."""
        context = demo_context()
        context["identity"]["business_model"] = "saas"
        result = pipeline.run(DEMO_CSV, context_overrides=context,
                              load_context_files=False)
        # For SaaS it is applicable, so it must NOT be not_applicable any more.
        self.assertNotEqual(result.kpis["net_revenue_retention"].status,
                            kpi_registry.NOT_APPLICABLE)

    def test_inventory_turnover_is_unavailable_not_not_applicable(self):
        """Applicable to a retailer, but the dataset has no inventory column."""
        result = run_demo()
        turnover = result.kpis["inventory_turnover"]
        self.assertEqual(turnover.status, kpi_registry.UNAVAILABLE)
        self.assertIn("inventory_value", turnover.reason)

    def test_unavailable_and_not_applicable_are_distinguished_in_output(self):
        result = run_demo()
        output = render.render(result, [])
        self.assertIn("**unavailable**", output)
        self.assertIn("**not applicable**", output)
        self.assertIn("different statements", output)

    def test_missing_context_suppresses_nothing_and_says_so(self):
        result = pipeline.run(DEMO_CSV, context_overrides=None,
                              load_context_files=False)
        self.assertFalse(result.context.relevance_filtering_enabled())
        # Nothing is suppressed by model when no model is known.
        self.assertNotEqual(result.kpis["net_revenue_retention"].status,
                            kpi_registry.NOT_APPLICABLE)
        output = render.render(result, [])
        self.assertIn("relevance filtering is off", output)

    def test_missing_context_is_reported_not_guessed(self):
        result = pipeline.run(DEMO_CSV, context_overrides=None,
                              load_context_files=False)
        missing = {m.path for m in result.context.missing()}
        self.assertIn("identity.business_model", missing)
        self.assertIsNone(result.context.get("identity.business_model"))


# ==========================================================================
# Scenario D — ambiguous mapping must ask, not guess
# ==========================================================================

class TestScenarioDAmbiguousMapping(FixtureMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.path = build_fixtures.ambiguous_mapping(self.tmp)
        self.result = pipeline.run(self.path, context_overrides=demo_context(),
                                   load_context_files=False)

    def test_generic_amount_column_is_not_silently_accepted(self):
        revenue = self.result.semantic_map.mappings.get(semantic.REVENUE)
        self.assertIsNotNone(revenue, "a plausible candidate should be found")
        self.assertEqual(revenue.status, semantic.CONFIRM_REQUIRED)
        self.assertFalse(revenue.usable_without_confirmation)

    def test_confidence_sits_in_the_confirm_band(self):
        revenue = self.result.semantic_map.mappings[semantic.REVENUE]
        self.assertGreaterEqual(revenue.confidence, semantic.CONFIRM_THRESHOLD)
        self.assertLess(revenue.confidence, semantic.AUTO_THRESHOLD)

    def test_quality_gate_raises_a_confirmation_warning(self):
        codes = {f.code for f in self.result.quality.findings}
        self.assertIn("mapping_needs_confirmation", codes)

    def test_kpis_depending_on_the_unconfirmed_column_are_not_computed(self):
        revenue_kpi = self.result.kpis.get("revenue")
        self.assertEqual(revenue_kpi.status, kpi_registry.UNAVAILABLE)
        self.assertIn("provisional", revenue_kpi.reason)

    def test_clarification_request_is_specific(self):
        questions = self.result.semantic_map.clarification_request()
        self.assertTrue(questions)
        joined = " ".join(questions)
        self.assertIn("Amount", joined)
        self.assertIn("Confirm", joined)

    def test_unconfirmed_mapping_is_recorded_as_an_assumption(self):
        assumptions = self.result.ledger.of_class(evidence.ASSUMPTION)
        self.assertTrue(assumptions)
        self.assertTrue(any("provisional" in c.statement for c in assumptions))


# ==========================================================================
# Scenario E — Tier 3 degraded XLSX
# ==========================================================================

class TestScenarioETier3Xlsx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = pipeline.run(DEMO_XLSX, context_overrides=demo_context(),
                                  load_context_files=False,
                                  prefer_tier=tiers.TIER_STDLIB)

    def test_tier_3_is_recorded_on_the_dataset(self):
        tier = self.result.dataset.reader_tier
        self.assertEqual(tier.tier, tiers.TIER_STDLIB)
        self.assertTrue(tier.degraded)

    def test_tier_appears_in_provenance(self):
        provenance = self.result.dataset.provenance()
        self.assertEqual(provenance["reader_tier"]["tier"], tiers.TIER_STDLIB)

    def test_supported_data_is_read_correctly(self):
        self.assertEqual(self.result.dataset.row_count, 2204)
        self.assertEqual(self.result.dataset.column_count, 12)

    def test_dates_shared_strings_and_inline_strings_all_resolve(self):
        import datetime
        first = self.result.dataset.rows[0]
        self.assertIsInstance(first["OrderDate"], datetime.date)   # styled date cell
        self.assertIsInstance(first["Customer"], str)              # shared string
        self.assertIsInstance(first["Category"], str)              # inline string
        self.assertIsInstance(first["NetRevenue"], float)

    def test_sheet_detection(self):
        self.assertEqual(self.result.dataset.sheets, ["Sales"])
        self.assertEqual(self.result.dataset.sheet, "Sales")

    def test_degraded_limitation_is_surfaced_not_hidden(self):
        codes = {w.code for w in self.result.dataset.warnings}
        self.assertIn("degraded_reader_tier", codes)
        warning = next(w for w in self.result.dataset.warnings
                       if w.code == "degraded_reader_tier")
        self.assertIn("refused rather than guessed", warning.message)

    def test_limitation_reaches_the_quality_report(self):
        messages = " ".join(f.message for f in self.result.quality.findings)
        self.assertIn("stdlib parser", messages)

    def test_no_silent_false_confidence(self):
        self.assertNotEqual(self.result.quality.grade, quality_checks.PASS)
        output = render.render(self.result, [])
        self.assertIn("stdlib xlsx parser", output)


# ==========================================================================
# Scenario F — Tier 1 XLSX, and cross-tier equivalence
# ==========================================================================

def _openpyxl_available():
    try:
        import openpyxl  # noqa: F401
        return True
    except ImportError:
        return False


@unittest.skipUnless(_openpyxl_available(),
                     "openpyxl is not installed; Tier 1 cannot be exercised here")
class TestScenarioFTier1Xlsx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = pipeline.run(DEMO_XLSX, context_overrides=demo_context(),
                                  load_context_files=False,
                                  prefer_tier=tiers.TIER_OPENPYXL_SYSTEM)

    def test_tier_1_is_recorded(self):
        tier = self.result.dataset.reader_tier
        self.assertEqual(tier.tier, tiers.TIER_OPENPYXL_SYSTEM)
        self.assertFalse(tier.degraded)

    def test_values_match_the_expected_fixture(self):
        self.assertEqual(self.result.dataset.row_count, 2204)
        self.assertEqual(self.result.kpis["revenue"].value, Decimal("3467850.16"))

    def test_no_bootstrap_occurs(self):
        # Tier 1 means openpyxl was already importable; nothing may be installed.
        self.assertIsNone(tiers.read_state())


class TestCrossTierEquivalence(unittest.TestCase):
    """Tier 1 and Tier 3 must agree on the same workbook, or the difference is documented."""

    def test_tier3_xlsx_matches_csv_row_for_row(self):
        from bops import ingest
        csv_dataset = ingest.read_csv(DEMO_CSV)
        xlsx_dataset = ingest.read_xlsx(DEMO_XLSX, prefer_tier=tiers.TIER_STDLIB)
        self.assertEqual(csv_dataset.row_count, xlsx_dataset.row_count)
        self.assertEqual(csv_dataset.columns, xlsx_dataset.columns)
        for index in (0, 500, 1500, 2203):
            for column in ("OrderDate", "Customer", "Region", "Product",
                           "Quantity", "NetRevenue", "CostOfGoods"):
                self.assertEqual(csv_dataset.rows[index][column],
                                 xlsx_dataset.rows[index][column],
                                 "row %d column %s" % (index, column))

    @unittest.skipUnless(_openpyxl_available(), "openpyxl is not installed")
    def test_tier1_and_tier3_agree(self):
        from bops import ingest
        tier1 = ingest.read_xlsx(DEMO_XLSX, prefer_tier=tiers.TIER_OPENPYXL_SYSTEM)
        tier3 = ingest.read_xlsx(DEMO_XLSX, prefer_tier=tiers.TIER_STDLIB)
        self.assertEqual(tier1.row_count, tier3.row_count)
        self.assertEqual(tier1.columns, tier3.columns)
        for index in (0, 1000, 2203):
            self.assertEqual(tier1.rows[index], tier3.rows[index], "row %d" % index)


# ==========================================================================
# The end-to-end integration test
# ==========================================================================

class TestEndToEndIntegration(unittest.TestCase):
    """dataset -> ingestion -> mapping -> quality -> KPI -> context -> analysis
    -> provenance -> output, with nothing mocked."""

    def test_full_chain_from_file_to_executive_output(self):
        result = pipeline.run(DEMO_XLSX, context_overrides=demo_context(),
                              load_context_files=False,
                              prefer_tier=tiers.TIER_STDLIB)

        # ingestion
        self.assertEqual(result.dataset.row_count, 2204)
        self.assertIsNotNone(result.dataset.reader_tier)
        # mapping
        self.assertTrue(result.semantic_map.confirmed(semantic.REVENUE))
        # quality
        self.assertFalse(result.halted)
        # KPI
        self.assertEqual(result.kpis["revenue"].value, Decimal("3467850.16"))
        # business context
        self.assertEqual(result.kpis["net_revenue_retention"].status,
                         kpi_registry.NOT_APPLICABLE)
        # analysis
        findings = analytics.build_findings(result, lambda v: render.money(v, "GBP"))
        self.assertTrue(findings)
        # provenance
        summary = result.ledger.summary()
        self.assertGreater(summary["evidential"], 0)
        # output
        output = render.render(result, findings)
        self.assertIn("KPI scorecard", output)
        self.assertIn("northwind_sales.xlsx", output)

    def test_provenance_survives_from_source_to_output(self):
        result = run_demo()
        findings = analytics.build_findings(result, lambda v: render.money(v, "GBP"))
        output = render.render(result, findings)

        # class 1: the source file is named in the output
        self.assertIn("northwind_sales.csv", output)
        # class 4: formulas are shown for calculated figures
        self.assertIn("sum(revenue)", output)
        # the FACT / INTERPRETATION distinction is visible
        self.assertIn("[FACT]", output)
        # the ledger itself distinguishes evidential from generative
        self.assertGreater(len(result.ledger.evidential()), 0)
        self.assertGreater(len(result.ledger.of_class(evidence.CALCULATED)), 0)

    def test_every_calculated_claim_carries_its_formula(self):
        result = run_demo()
        for claim in result.ledger.of_class(evidence.CALCULATED):
            self.assertTrue(claim.formula, claim.statement)
            self.assertTrue(claim.inputs, claim.statement)

    def test_every_user_data_claim_names_its_source(self):
        result = run_demo()
        for claim in result.ledger.of_class(evidence.USER_DATA):
            self.assertTrue(claim.source, claim.statement)

    def test_materiality_filters_rather_than_halts(self):
        result = run_demo()
        verdicts = [v for _row, v in result.analysis["product_materiality"]]
        self.assertTrue(any(v.is_material for v in verdicts))
        self.assertTrue(any(not v.is_material for v in verdicts))
        self.assertFalse(result.halted)      # immaterial findings never stop the run

    def test_materiality_can_be_undetermined(self):
        result = run_demo()
        verdict = analytics.undetermined_example(result, result.config)
        self.assertEqual(verdict.outcome, "undetermined")
        self.assertIn("missing", verdict.reason.lower())

    def test_materiality_names_the_threshold_and_its_source(self):
        result = run_demo()
        verdict = result.analysis["margin_materiality"]
        self.assertEqual(verdict.threshold_used, "margin_percentage_points")
        self.assertIn(verdict.threshold_source, ("project", "default", "user", "command"))

    def test_pipeline_result_is_json_serialisable(self):
        result = run_demo()
        json.dumps(result.as_dict(), default=str)


if __name__ == "__main__":
    unittest.main()
