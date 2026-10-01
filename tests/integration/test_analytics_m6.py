"""The Milestone 6 analytics layer, end to end.

Each domain is exercised for the happy path, unavailable data, insufficient data, a quality
warning, a quality halt, a Business Context variation, provenance, privacy and repeated
execution. The layer boundaries are asserted directly: analytics consumes KPI results and
never recomputes them, consumes M4 quality and never re-checks it, and reuses the single
materiality system rather than introducing a second one.
"""

import json
import os
import shutil
import tempfile
import unittest
from decimal import Decimal

from bops import analytics, evidence, materiality, pipeline
from bops import mapping as mapping_mod
from bops.analytics import contract, presentation
from bops.kpi import contract as kpi_contract
from bops.quality import contract as quality_contract

from fixtures import build_analytics_fixtures as build
from fixtures import build_fixtures as legacy

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
DEMO_CONTEXT = os.path.join(REPO, "assets", "demo-data", "business_context.json")

SAAS_CONTEXT = {
    "schema_version": "1.0.0",
    "identity": {"business_name": "Testco", "business_model": "saas"},
    "reporting": {"currency": "GBP"},
}


def _without_timestamps(value):
    """Strip the KPI engine's `calculated_at` stamp so determinism can be asserted."""
    if isinstance(value, dict):
        return {k: _without_timestamps(v) for k, v in value.items()
                if k != "calculated_at"}
    if isinstance(value, list):
        return [_without_timestamps(v) for v in value]
    return value


def demo_context():
    with open(DEMO_CONTEXT, encoding="utf-8") as handle:
        return json.load(handle)


class AnalyticsIntegrationCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m6-")
        cls.paths = {
            "full": build.full(cls.directory),
            "single_period": build.single_period(cls.directory),
            "two_periods": build.two_periods(cls.directory),
            "single_customer": build.single_customer(cls.directory),
            "no_customer": build.without(cls.directory, "Customer"),
            "no_product": build.without(cls.directory, "Product", "Category"),
            "no_region": build.without(cls.directory, "Region"),
            "no_salesperson": build.without(cls.directory, "Salesperson"),
            "no_cost": build.without(cls.directory, "CostOfGoods"),
            "empty": build.empty(cls.directory),
            "critical": legacy.critical_missing_revenue(cls.directory),
            "warning": legacy.warning_duplicates(cls.directory),
            "ambiguous": legacy.ambiguous_mapping(cls.directory),
        }
        cls._runs = {}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def run_pipeline(self, key, context=None, command_args=None):
        cache_key = (key, json.dumps(context, sort_keys=True) if context else None,
                     json.dumps(command_args, sort_keys=True) if command_args else None)
        if cache_key not in self._runs:
            self._runs[cache_key] = pipeline.run(
                self.paths.get(key, key), context_overrides=context,
                command_args=command_args, load_context_files=False)
        return self._runs[cache_key]

    def analyse(self, key, context=None, presentation_mode=presentation.LOCAL):
        result = self.run_pipeline(key, context)
        return analytics.analyse_all(result, presentation=presentation_mode)

    def demo(self, presentation_mode=presentation.LOCAL):
        return self.analyse(DEMO, demo_context(), presentation_mode)


# ==========================================================================
# Sales intelligence
# ==========================================================================

class TestSalesIntelligence(AnalyticsIntegrationCase):

    def test_happy_path_produces_classified_findings(self):
        sales = self.analyse("full")["sales"]
        self.assertEqual(sales.status, contract.AVAILABLE)
        self.assertTrue(sales.findings)
        for finding in sales.findings:
            self.assertIn(finding.finding_type, contract.ENGINE_EMITS)
            self.assertTrue(finding.statement)

    def test_every_mapped_dimension_is_covered_and_missing_ones_are_named(self):
        sales = self.analyse("no_region")["sales"]
        self.assertIn("region", sales.dimensions_skipped)
        self.assertNotIn("region", sales.dimensions_covered)
        self.assertIn("product", sales.dimensions_covered)

    def test_missing_salesperson_is_skipped_not_substituted(self):
        sales = self.analyse("no_salesperson")["sales"]
        self.assertIn("salesperson", sales.dimensions_skipped)
        self.assertEqual([f for f in sales.findings if f.dimension == "salesperson"], [])

    def test_a_single_period_warns_at_the_gate_rather_than_halting(self):
        """One period is a warning, not a critical defect — the run continues."""
        result = self.run_pipeline("single_period")
        self.assertFalse(result.halted)
        self.assertEqual(result.quality.grade, quality_contract.WARNING)

    def test_a_single_period_reports_insufficient_data_not_a_trend(self):
        result = self.run_pipeline("single_period")
        sales = analytics.sales.analyse(result)
        self.assertEqual(sales.status, contract.AVAILABLE)
        codes = {item.code for item in sales.limitations}
        self.assertIn("single_period", codes)
        self.assertIn("no_comparison_period", codes)
        for item in sales.limitations:
            self.assertEqual(item.status, contract.INSUFFICIENT_DATA)
        self.assertEqual([f for f in sales.findings if f.change is not None], [])

    def test_a_missing_comparison_period_never_produces_a_movement(self):
        sales = analytics.sales.analyse(self.run_pipeline("single_period"))
        self.assertEqual([f for f in sales.findings if ".movement." in f.analysis_id], [])
        self.assertEqual([f for f in sales.findings if f.comparison_period], [])

    def test_no_revenue_column_makes_sales_analysis_unavailable(self):
        sales = self.analyse("critical")["sales"]
        self.assertEqual(sales.status, contract.UNAVAILABLE)
        self.assertTrue(sales.reason)

    def test_order_volume_is_reported_separately_from_revenue(self):
        sales = self.analyse("full")["sales"]
        orders = [f for f in sales.findings if f.analysis_id.endswith("orders.trend")]
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].unit, "count")

    def test_repeated_execution_is_identical(self):
        first = self.analyse("full")["sales"].as_dict()
        second = analytics.sales.analyse(self.run_pipeline("full")).as_dict()
        self.assertEqual(json.dumps(first, sort_keys=True),
                         json.dumps(second, sort_keys=True))


# ==========================================================================
# Customer intelligence
# ==========================================================================

class TestCustomerIntelligence(AnalyticsIntegrationCase):

    def test_happy_path_covers_population_retention_and_cohorts(self):
        customer = self.analyse("full")["customer"]
        self.assertEqual(customer.status, contract.AVAILABLE)
        ids = {f.analysis_id for f in customer.findings}
        self.assertIn("customer.customers.count", ids)
        self.assertIn("customer.customers.repeat", ids)
        self.assertIn("customer.customers.cohorts", ids)

    def test_no_customer_column_is_unavailable_with_a_named_reason(self):
        customer = self.analyse("no_customer")["customer"]
        self.assertEqual(customer.status, contract.UNAVAILABLE)
        self.assertIn("customer", customer.reason)
        self.assertEqual(customer.findings, [])
        self.assertTrue(customer.limitations)

    def test_insufficient_history_blocks_cohorts_but_not_counts(self):
        customer = self.analyse("two_periods")["customer"]
        self.assertEqual(customer.status, contract.AVAILABLE)
        codes = {item.code: item for item in customer.limitations}
        self.assertIn("cohorts_insufficient_data", codes)
        self.assertEqual(codes["cohorts_insufficient_data"].status,
                         contract.INSUFFICIENT_DATA)
        self.assertIn("customer.customers.count",
                      {f.analysis_id for f in customer.findings})

    def test_a_single_customer_is_reported_as_a_band(self):
        customer = self.analyse("single_customer")["customer"]
        count = [f for f in customer.findings
                 if f.analysis_id == "customer.customers.count"][0]
        self.assertIn("1-9", count.statement)
        self.assertTrue(any("k-anonymity" in c for c in count.caveats))

    def test_the_cohort_window_assumption_travels_with_the_finding(self):
        customer = self.analyse("full")["customer"]
        cohort = [f for f in customer.findings
                  if f.analysis_id == "customer.customers.cohorts"][0]
        self.assertTrue(cohort.assumptions)
        self.assertIn("before the file begins", cohort.assumptions[0])

    def test_customer_names_never_appear_in_shareable_presentation(self):
        customer = self.demo(presentation.SHAREABLE)["customer"]
        blob = json.dumps(customer.as_dict())
        self.assertNotIn("Eastgate Retail", blob)
        self.assertIn("Customer #", blob)
        for finding in customer.findings:
            if finding.dimension == "customer" and finding.dimension_value is not None:
                self.fail("a customer value survived shareable presentation")

    def test_local_presentation_flags_the_export_restriction(self):
        customer = self.demo()["customer"]
        self.assertIn("Customer", customer.restricted_dimensions)
        self.assertTrue(any("pseudonymised" in c for c in customer.caveats))

    def test_no_individual_transaction_is_ever_emitted(self):
        customer = self.demo()["customer"]
        blob = json.dumps(customer.as_dict())
        self.assertNotIn("SO-", blob)


# ==========================================================================
# Product intelligence
# ==========================================================================

class TestProductIntelligence(AnalyticsIntegrationCase):

    def test_happy_path_reports_contribution_growth_mix_and_margin(self):
        product = self.analyse("full")["product"]
        self.assertEqual(product.status, contract.AVAILABLE)
        ids = {f.analysis_id for f in product.findings}
        self.assertIn("product.product.largest", ids)
        self.assertIn("product.product.concentration", ids)
        self.assertIn("product.product.margin_spread", ids)

    def test_no_product_column_is_unavailable(self):
        product = self.analyse("no_product")["product"]
        self.assertEqual(product.status, contract.UNAVAILABLE)
        self.assertEqual(product.findings, [])

    def test_absent_cost_removes_margin_and_says_so(self):
        product = self.analyse("no_cost")["product"]
        self.assertEqual(product.status, contract.AVAILABLE)
        subjects = {item.subject for item in product.limitations}
        self.assertIn("product profitability", subjects)
        self.assertEqual([f for f in product.findings
                          if f.analysis_id.endswith("margin_spread")], [])

    def test_profile_reports_every_axis_together(self):
        result = self.run_pipeline("full")
        rows = analytics.products.profile(result.dataset, result.semantic_map)
        self.assertTrue(rows)
        for row in rows:
            for field in ("revenue", "share_pct", "rank", "margin_pct", "first_period"):
                self.assertIn(field, row)

    def test_a_later_entrant_is_stated_as_a_data_window_fact_not_an_anomaly(self):
        product = self.demo()["product"]
        entrants = [f for f in product.findings
                    if f.analysis_id.endswith("later_entrants")]
        self.assertEqual(len(entrants), 1)
        self.assertEqual(entrants[0].finding_type, contract.FACT)
        self.assertIn("cannot distinguish", entrants[0].statement)
        self.assertNotIn("anomaly", entrants[0].statement.lower())

    def test_revenue_leader_and_profit_leader_are_distinguished(self):
        product = self.demo()["product"]
        ids = {f.analysis_id for f in product.findings}
        self.assertIn("product.product.margin_spread", ids)


# ==========================================================================
# Financial analysis
# ==========================================================================

class TestFinancialAnalysis(AnalyticsIntegrationCase):

    def test_happy_path_walks_the_profit_statement_as_far_as_the_data_goes(self):
        financial = self.analyse("full")["financial"]
        self.assertEqual(financial.status, contract.AVAILABLE)
        metrics = {f.metric for f in financial.findings}
        self.assertIn("revenue", metrics)
        self.assertIn("gross_profit", metrics)
        self.assertIn("gross_margin", metrics)

    def test_unavailable_metrics_are_reported_never_estimated(self):
        financial = self.analyse("full")["financial"]
        summary = analytics.financial.unavailable_summary(financial)
        self.assertIn(contract.UNAVAILABLE, summary)
        subjects = dict(summary[contract.UNAVAILABLE])
        self.assertIn("Operating profit", subjects)
        self.assertIn("operating_expense", subjects["Operating profit"])
        for finding in financial.findings:
            self.assertNotIn(finding.metric, ("operating_profit", "ebitda", "runway"))

    def test_margin_movement_is_reported_in_percentage_points(self):
        financial = self.demo()["financial"]
        movement = [f for f in financial.findings
                    if f.analysis_id == "financial.margin.movement"]
        self.assertEqual(len(movement), 1)
        self.assertEqual(movement[0].unit, "percentage_points")
        self.assertIn("pp", movement[0].statement)

    def test_no_cost_column_removes_margin_movement_with_a_reason(self):
        financial = self.analyse("no_cost")["financial"]
        subjects = {item.subject for item in financial.limitations}
        self.assertIn("margin movement", subjects)

    def test_no_revenue_column_makes_financial_analysis_unavailable(self):
        financial = self.analyse("critical")["financial"]
        self.assertEqual(financial.status, contract.UNAVAILABLE)

    def test_concentration_is_reported_as_a_financial_exposure(self):
        financial = self.demo()["financial"]
        ids = {f.analysis_id for f in financial.findings}
        self.assertTrue(any(i.endswith("concentration") for i in ids))


# ==========================================================================
# Layer boundaries
# ==========================================================================

class TestKpiIntegration(AnalyticsIntegrationCase):

    def test_kpi_findings_carry_the_engine_formula_verbatim(self):
        result = self.run_pipeline("full")
        sets = analytics.analyse_all(result)
        checked = 0
        for analysis in sets.values():
            for finding in analysis.findings:
                if finding.metric and finding.analysis_id.startswith(
                        "%s.kpi." % analysis.analysis_type):
                    self.assertEqual(finding.basis,
                                     result.kpis[finding.metric].formula)
                    checked += 1
        self.assertGreater(checked, 0)

    def test_revenue_growth_is_consumed_not_recomputed(self):
        result = self.run_pipeline("full")
        sales = analytics.sales.analyse(result)
        direction = [f for f in sales.findings
                     if f.analysis_id == "sales.revenue.direction"]
        self.assertEqual(len(direction), 1)
        self.assertEqual(direction[0].observed, result.kpis["revenue_growth"].value)
        self.assertIn("not recomputed", direction[0].basis)

    def test_segment_totals_agree_with_the_revenue_kpi(self):
        result = self.run_pipeline("full")
        sales = analytics.sales.analyse(result)
        segments = analytics.segmentation.segment(
            result.dataset, result.semantic_map, mapping_mod.PRODUCT)
        self.assertEqual(analytics.segmentation.total_of(segments),
                         result.kpis["revenue"].value)
        self.assertTrue(sales.metrics_used)

    def test_unavailable_and_not_applicable_kpis_become_distinct_limitations(self):
        customer = self.demo()["customer"]
        by_code = {item.code for item in customer.limitations}
        self.assertIn("kpi_unavailable", by_code)
        self.assertIn("kpi_not_applicable", by_code)

    def test_business_model_changes_which_metrics_apply(self):
        retail = self.demo()["customer"]
        saas = self.analyse(DEMO, SAAS_CONTEXT)["customer"]
        retail_na = {item.subject for item in retail.limitations
                     if item.status == contract.NOT_APPLICABLE}
        saas_na = {item.subject for item in saas.limitations
                   if item.status == contract.NOT_APPLICABLE}
        self.assertIn("Net revenue retention (NRR)", retail_na)
        self.assertNotIn("Net revenue retention (NRR)", saas_na)

    def test_no_business_context_suppresses_nothing(self):
        customer = self.analyse("full")["customer"]
        self.assertIsNone(customer.business_model)
        self.assertEqual([item for item in customer.limitations
                          if item.status == contract.NOT_APPLICABLE], [])


class TestQualityIntegration(AnalyticsIntegrationCase):

    def test_a_critical_grade_produces_no_analytical_claim_in_any_domain(self):
        sets = self.analyse("critical")
        result = self.run_pipeline("critical")
        self.assertTrue(result.halted)
        for name, analysis in sets.items():
            self.assertEqual(analysis.status, contract.UNAVAILABLE, name)
            self.assertEqual(analysis.findings, [], name)
            self.assertIn("quality gate", analysis.reason)
            self.assertIn("quality_gate", {i.code for i in analysis.limitations})

    def test_a_warning_lets_analysis_proceed_with_the_caveat_attached(self):
        result = self.run_pipeline("warning")
        self.assertEqual(result.quality.grade, quality_contract.WARNING)
        sales = analytics.sales.analyse(result)
        self.assertEqual(sales.status, contract.AVAILABLE)
        self.assertTrue(sales.caveats)
        for finding in sales.findings:
            self.assertTrue(any(c.startswith("Data quality:") for c in finding.caveats))

    def test_a_warning_downgrades_confidence(self):
        clean = analytics.sales.analyse(self.run_pipeline("full"))
        warned = analytics.sales.analyse(self.run_pipeline("warning"))
        self.assertEqual(clean.default_confidence, evidence.HIGH)
        self.assertEqual(warned.default_confidence, evidence.MEDIUM)

    def test_an_unconfirmed_mapping_marks_dependent_figures_provisional(self):
        result = self.run_pipeline("ambiguous")
        if not result.semantic_map.needs_confirmation():
            self.skipTest("this fixture no longer produces an unconfirmed mapping")
        sales = analytics.sales.analyse(result)
        self.assertTrue(any("provisionally identified" in c for c in sales.caveats))

    def test_analytics_does_not_rerun_quality_checks(self):
        result = self.run_pipeline("full")
        before = len(result.quality.findings)
        analytics.analyse_all(result)
        self.assertEqual(len(result.quality.findings), before)


class TestMaterialityIntegration(AnalyticsIntegrationCase):

    def test_verdicts_come_from_the_one_materiality_system(self):
        sales = self.demo()["sales"]
        judged = [f for f in sales.findings if f.materiality is not None]
        self.assertTrue(judged)
        for finding in judged:
            self.assertIn(finding.materiality,
                          (materiality.MATERIAL, materiality.NOT_MATERIAL,
                           materiality.UNDETERMINED))
            self.assertTrue(finding.materiality_reason)

    def test_an_uncomparable_movement_is_undetermined_not_immaterial(self):
        verdict = materiality.assess_amount(
            "Revenue versus last year", Decimal("100"), None,
            self.run_pipeline("full").config)
        self.assertEqual(verdict.outcome, materiality.UNDETERMINED)

    def test_only_material_movements_are_reported_as_movements(self):
        sales = self.demo()["sales"]
        movements = [f for f in sales.findings if ".movement." in f.analysis_id]
        self.assertTrue(movements)
        for finding in movements:
            self.assertEqual(finding.materiality, materiality.MATERIAL)


class TestProvenanceAndEvidence(AnalyticsIntegrationCase):

    def test_every_finding_names_its_basis_fields_and_source(self):
        for analysis in self.demo().values():
            for finding in analysis.findings:
                self.assertTrue(finding.fields_used, finding.analysis_id)
                self.assertTrue(finding.provenance.get("source"), finding.analysis_id)
                self.assertTrue(finding.confidence, finding.analysis_id)
                if finding.finding_type == contract.CALCULATION:
                    self.assertTrue(finding.basis, finding.analysis_id)

    def test_provenance_records_the_source_rows_and_quality_grade(self):
        sales = self.demo()["sales"]
        self.assertEqual(sales.provenance["source"], "northwind_sales.csv")
        self.assertEqual(sales.provenance["rows"], 2204)
        self.assertEqual(sales.provenance["quality_grade"], quality_contract.PASS)
        self.assertTrue(sales.provenance["complete"])

    def test_provenance_records_the_reader_tier_when_one_was_used(self):
        """A CSV has no reader tier; a workbook does, and it must survive into analytics."""
        workbook = os.path.join(REPO, "assets", "demo-data", "northwind_sales.xlsx")
        result = pipeline.run(workbook, context_overrides=demo_context(),
                              load_context_files=False)
        sales = analytics.sales.analyse(result)
        self.assertIn("reader_tier", sales.provenance)

    def test_findings_enter_the_ledger_with_their_class_intact(self):
        result = pipeline.run(DEMO, context_overrides=demo_context(),
                              load_context_files=False)
        before = len(result.ledger)
        untraceable_before = len(result.ledger.untraceable())
        pipeline.analyse(result)
        self.assertGreater(len(result.ledger), before)
        self.assertEqual(len(result.ledger.untraceable()), untraceable_before)
        classes = {c.provenance_class for c in result.ledger.claims}
        self.assertIn(evidence.CALCULATED, classes)

    def test_the_engine_emits_no_interpretation_or_recommendation(self):
        for analysis in self.demo().values():
            self.assertEqual(analysis.of_type(contract.INTERPRETATION), [])
            self.assertEqual(analysis.of_type(contract.RECOMMENDATION), [])

    def test_every_analysis_set_is_json_serialisable(self):
        for analysis in self.demo().values():
            json.dumps(analysis.as_dict())


class TestCrossLayerRegression(AnalyticsIntegrationCase):

    def test_the_milestone_two_health_check_is_unchanged(self):
        from bops import render
        result = pipeline.run(DEMO, context_overrides=demo_context(),
                              load_context_files=False)
        findings = analytics.build_findings(
            result, lambda v: render.money(v, "GBP"))
        report = render.render(result, findings)
        self.assertIn("3,467,850.16", report)
        self.assertEqual(result.analyses, {})

    def test_running_the_analytics_layer_does_not_change_the_kpis(self):
        result = pipeline.run(DEMO, context_overrides=demo_context(),
                              load_context_files=False)
        before = {k: v.value for k, v in result.kpis.items()}
        pipeline.analyse(result)
        after = {k: v.value for k, v in result.kpis.items()}
        self.assertEqual(before, after)

    def test_an_unknown_domain_is_refused(self):
        result = self.run_pipeline("full")
        with self.assertRaises(KeyError):
            pipeline.analyse(result, domains=["astrology"])

    def test_domains_can_be_run_selectively(self):
        result = pipeline.run(self.paths["full"], load_context_files=False)
        sets = pipeline.analyse(result, domains=["sales"])
        self.assertEqual(sorted(sets), ["sales"])


class TestDemoDataset(AnalyticsIntegrationCase):

    def test_every_domain_produces_a_result_on_the_demo_data(self):
        sets = self.demo()
        self.assertEqual(sorted(sets), ["customer", "financial", "product", "sales"])
        for name, analysis in sets.items():
            self.assertEqual(analysis.status, contract.AVAILABLE, name)
            self.assertTrue(analysis.findings, name)

    def test_the_demo_figures_agree_with_the_kpi_engine(self):
        result = pipeline.run(DEMO, context_overrides=demo_context(),
                              load_context_files=False)
        sales = analytics.sales.analyse(result)
        revenue = [f for f in sales.findings if f.metric == "revenue"][0]
        self.assertEqual(revenue.observed, result.kpis["revenue"].value)
        self.assertEqual(revenue.currency, "GBP")

    def test_the_demo_dataset_reports_its_gaps_as_well_as_its_findings(self):
        financial = self.demo()["financial"]
        self.assertTrue(financial.limitations)
        self.assertGreater(len(financial.limitations), len(financial.findings))

    def test_repeated_execution_over_the_demo_data_is_identical(self):
        """Byte-identical apart from the run timestamp, which is metadata, not a result."""
        first = _without_timestamps({k: v.as_dict() for k, v in self.demo().items()})
        second_result = pipeline.run(DEMO, context_overrides=demo_context(),
                                     load_context_files=False)
        second = _without_timestamps(
            {k: v.as_dict() for k, v in analytics.analyse_all(second_result).items()})
        self.assertEqual(json.dumps(first, sort_keys=True),
                         json.dumps(second, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
