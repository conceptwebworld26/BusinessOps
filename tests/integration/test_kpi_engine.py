"""Milestone 5 — the full KPI engine.

Every metric is exercised on its happy path and on the paths where it must decline. The
declining paths matter more: the product's value rests on being able to say "the data does
not support this" instead of manufacturing a number.
"""

import json
import os
import shutil
import tempfile
import unittest
from decimal import Decimal

from bops import config as config_mod
from bops import ingest, kpi, mapping, pipeline
from bops.context import loader as context_loader
from bops.ingest import canonical as canonical_mod
from bops.kpi import catalog, engine as engine_mod, primitives
from bops.quality import checks as quality_checks

from fixtures import build_kpi_fixtures as fx
from fixtures import build_quality_fixtures as qfx

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO_CSV = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
DEMO_CONTEXT = os.path.join(REPO, "assets", "demo-data", "business_context.json")


def demo_context():
    with open(DEMO_CONTEXT, encoding="utf-8") as fh:
        return json.load(fh)


class KpiCase(unittest.TestCase):
    """Drives the real engine over a real file. Nothing is mocked."""

    @classmethod
    def setUpClass(cls):
        cls.schema = kpi.load_schema()

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bops-m5-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def compute(self, path, business_model=None, context_overrides=None,
                with_quality=False, kpi_ids=None):
        dataset = ingest.read(path)
        canonical = canonical_mod.build(dataset)
        semantic_map = mapping.infer(dataset)
        business_context = None
        if business_model is not None or context_overrides is not None:
            overrides = context_overrides or {"identity": {"business_model": business_model}}
            business_context = context_loader.resolve(overrides=overrides,
                                                      load_files=False)
        config = config_mod.resolve(defaults=config_mod.load_defaults())
        quality = None
        if with_quality:
            quality = quality_checks.run(dataset, semantic_map, config, canonical,
                                         business_context)
        return kpi.calculate(dataset, semantic_map, business_context, config, kpi_ids,
                             canonical=canonical, quality=quality)


# ==========================================================================
# Catalogue integrity
# ==========================================================================

class TestCatalogue(KpiCase):

    def test_the_approved_27_are_all_registered(self):
        self.assertEqual(len(catalog.APPROVED_27), 27)
        for kpi_id in catalog.APPROVED_27:
            self.assertIn(kpi_id, catalog.BY_ID, kpi_id)

    def test_identifiers_are_unique(self):
        ids = [d.kpi_id for d in catalog.CATALOGUE]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_definition_is_complete(self):
        for definition in catalog.CATALOGUE:
            self.assertTrue(definition.name, definition.kpi_id)
            self.assertTrue(definition.description, definition.kpi_id)
            self.assertTrue(definition.formula, definition.kpi_id)
            self.assertTrue(definition.inputs, definition.kpi_id)
            self.assertTrue(definition.unit, definition.kpi_id)
            self.assertTrue(definition.aggregation, definition.kpi_id)
            self.assertTrue(definition.category, definition.kpi_id)
            self.assertTrue(callable(definition.calculator), definition.kpi_id)

    def test_model_restricted_metrics_explain_why(self):
        for definition in catalog.CATALOGUE:
            if definition.applicable_models != catalog.ALL_MODELS:
                self.assertTrue(definition.not_applicable_reason, definition.kpi_id)

    def test_metrics_beyond_the_approved_list_are_declared(self):
        self.assertEqual(catalog.BEYOND_APPROVED, ("net_revenue_retention",))
        extra = catalog.BY_ID["net_revenue_retention"]
        self.assertIn("Not part of the approved 27", extra.calculation_notes)

    def test_catalogue_is_machine_readable(self):
        document = kpi.catalogue_as_dict()
        self.assertEqual(document["count"], 28)
        json.dumps(document)

    def test_formulas_live_only_in_the_engine(self):
        """No skill or command may restate a KPI formula."""
        for folder in ("skills", "commands"):
            base = os.path.join(REPO, folder)
            for root, _dirs, files in os.walk(base):
                for name in files:
                    text = open(os.path.join(root, name), encoding="utf-8").read()
                    for token in ("sum(revenue) - sum(cost", "/ sum(revenue) * 100"):
                        self.assertNotIn(token, text,
                                         "%s restates a KPI formula" % name)


# ==========================================================================
# Happy path: every metric computes on a complete dataset
# ==========================================================================

class TestHappyPath(KpiCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tmpdir = tempfile.mkdtemp(prefix="bops-m5-happy-")
        cls.path = fx.rich_business(cls.tmpdir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self.results = self.compute(self.path)

    def test_every_metric_has_a_result(self):
        self.assertEqual(len(self.results), 28)

    def test_every_metric_is_available_on_complete_data(self):
        absent = {k: v.status for k, v in self.results.items() if not v.available}
        # Runway is legitimately unbounded here: the fixture is cash-generative.
        self.assertEqual(set(absent), {"runway"}, absent)

    def test_hand_checkable_values(self):
        """36 rows x 1000 revenue, 600 cost, 100 opex, 20 depreciation."""
        expected = {
            "revenue": Decimal("36000"),
            "gross_profit": Decimal("14400"),
            "gross_margin": Decimal("40"),
            "operating_profit": Decimal("10800"),
            "operating_margin": Decimal("30"),
            "ebitda": Decimal("11520"),
            "ebitda_margin": Decimal("32"),
            "average_order_value": Decimal("1000"),
            "working_capital": Decimal("40000"),
            "inventory_turnover": Decimal("4.32"),
            "days_sales_outstanding": Decimal("90"),
            "customer_lifetime_value": Decimal("6000"),
            "win_rate": Decimal("50"),
            "conversion_rate": Decimal("5"),
            "average_sales_cycle": Decimal("20"),
            "mrr": Decimal("2400"),
            "arr": Decimal("28800"),
        }
        for kpi_id, value in expected.items():
            self.assertEqual(self.results[kpi_id].value, value, kpi_id)

    def test_monetary_metrics_carry_currency(self):
        for result in self.results.values():
            if result.available and result.unit == kpi.CURRENCY:
                self.assertTrue(result.currency, result.kpi_id)

    def test_percent_metrics_do_not_claim_a_currency(self):
        for result in self.results.values():
            if result.unit == kpi.PERCENT:
                self.assertIsNone(result.currency, result.kpi_id)

    def test_repeated_execution_is_identical(self):
        again = self.compute(self.path)
        for kpi_id, result in self.results.items():
            self.assertEqual(again[kpi_id].value, result.value, kpi_id)
            self.assertEqual(again[kpi_id].status, result.status, kpi_id)

    def test_source_is_not_mutated(self):
        before = open(self.path, "rb").read()
        self.compute(self.path)
        self.assertEqual(open(self.path, "rb").read(), before)


# ==========================================================================
# Unavailable: the field is simply not there
# ==========================================================================

class TestUnavailablePath(KpiCase):

    def test_sales_only_extract_leaves_many_metrics_unavailable(self):
        results = self.compute(fx.sales_only(self.tmp))
        unavailable = {k for k, v in results.items() if v.status == kpi.UNAVAILABLE}
        for kpi_id in ("operating_profit", "ebitda", "working_capital",
                       "days_sales_outstanding", "inventory_turnover",
                       "sales_pipeline_value", "win_rate", "conversion_rate"):
            self.assertIn(kpi_id, unavailable, kpi_id)

    def test_unavailable_names_the_specific_missing_field(self):
        results = self.compute(fx.sales_only(self.tmp))
        result = results["operating_profit"]
        self.assertIn("operating_expense", result.reason)
        self.assertIn("operating_expense", result.missing_inputs)

    def test_unavailable_never_returns_zero_or_null_as_a_value(self):
        results = self.compute(fx.sales_only(self.tmp))
        for result in results.values():
            if not result.available:
                self.assertIsNone(result.value, result.kpi_id)
                self.assertTrue(result.reason, result.kpi_id)

    def test_absent_and_unconfirmed_inputs_are_distinguished(self):
        """M5 section 8: field absent is a different problem from field unconfirmed."""
        path = os.path.join(self.tmp, "ambiguous.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("Period,Amount\n")
            for month in range(1, 7):
                fh.write("2025-%02d-15,%d\n" % (month, 1000 * month))
        results = self.compute(path)
        reason = results["revenue"].reason
        self.assertIn("provisional", reason)
        self.assertNotIn("Missing required field(s): revenue", reason)

    def test_every_metric_still_reports_when_nothing_is_mapped(self):
        path = os.path.join(self.tmp, "opaque.csv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write("ColA,ColB\nx,y\n")
        results = self.compute(path)
        self.assertEqual(len(results), 28)
        self.assertTrue(all(not r.available for r in results.values()))


# ==========================================================================
# Not applicable: the model makes it meaningless
# ==========================================================================

class TestNotApplicablePath(KpiCase):

    def test_retail_suppresses_recurring_revenue_metrics(self):
        results = self.compute(fx.rich_business(self.tmp), business_model="retail")
        for kpi_id in ("recurring_revenue", "mrr", "arr", "net_revenue_retention"):
            self.assertEqual(results[kpi_id].status, kpi.NOT_APPLICABLE, kpi_id)

    def test_saas_suppresses_inventory_turnover_and_aov(self):
        results = self.compute(fx.rich_business(self.tmp), business_model="saas")
        self.assertEqual(results["inventory_turnover"].status, kpi.NOT_APPLICABLE)
        self.assertEqual(results["average_order_value"].status, kpi.NOT_APPLICABLE)

    def test_saas_enables_recurring_revenue_metrics(self):
        results = self.compute(fx.rich_business(self.tmp), business_model="saas")
        for kpi_id in ("recurring_revenue", "mrr", "arr"):
            self.assertEqual(results[kpi_id].status, kpi.AVAILABLE, kpi_id)

    def test_services_business_suppresses_inventory_turnover(self):
        results = self.compute(fx.rich_business(self.tmp),
                               business_model="professional_services")
        self.assertEqual(results["inventory_turnover"].status, kpi.NOT_APPLICABLE)

    def test_not_applicable_is_not_unavailable(self):
        """The distinction the product depends on."""
        results = self.compute(fx.rich_business(self.tmp), business_model="retail")
        self.assertEqual(results["mrr"].status, kpi.NOT_APPLICABLE)
        self.assertNotEqual(results["mrr"].status, kpi.UNAVAILABLE)
        self.assertIn("subscription", results["mrr"].reason.lower())

    def test_not_applicable_holds_even_when_the_data_is_present(self):
        """The rich fixture HAS recurring revenue; retail still says not applicable."""
        results = self.compute(fx.rich_business(self.tmp), business_model="retail")
        self.assertEqual(results["recurring_revenue"].status, kpi.NOT_APPLICABLE)
        self.assertEqual(results["recurring_revenue"].missing_inputs, [])

    def test_missing_business_context_suppresses_nothing(self):
        results = self.compute(fx.rich_business(self.tmp), business_model=None)
        self.assertEqual([k for k, v in results.items()
                          if v.status == kpi.NOT_APPLICABLE], [])

    def test_unknown_business_model_suppresses_nothing(self):
        results = self.compute(fx.rich_business(self.tmp), business_model="other")
        na = {k for k, v in results.items() if v.status == kpi.NOT_APPLICABLE}
        # `other` is a real vocabulary value that no metric excludes except the
        # recurring-revenue family, which names its models explicitly.
        self.assertNotIn("gross_margin", na)


# ==========================================================================
# Insufficient data: inputs present, history too short
# ==========================================================================

class TestInsufficientDataPath(KpiCase):

    def setUp(self):
        super().setUp()
        self.results = self.compute(fx.single_period(self.tmp))

    def test_period_over_period_metrics_report_insufficient_data(self):
        for kpi_id in ("revenue_growth", "customer_retention", "customer_churn",
                       "customer_acquisition_cost", "customer_lifetime_value"):
            self.assertEqual(self.results[kpi_id].status, kpi.INSUFFICIENT_DATA, kpi_id)

    def test_insufficient_data_states_what_is_available_and_required(self):
        result = self.results["revenue_growth"]
        self.assertIn("1 periods available", result.reason)
        self.assertIn("2 required", result.reason)
        self.assertEqual(result.periods, 1)

    def test_insufficient_data_is_not_unavailable(self):
        """The inputs are all present; only the history is short."""
        result = self.results["revenue_growth"]
        self.assertEqual(result.missing_inputs, [])
        self.assertNotEqual(result.status, kpi.UNAVAILABLE)

    def test_single_period_metrics_still_compute(self):
        for kpi_id in ("revenue", "gross_profit", "gross_margin",
                       "average_order_value", "working_capital"):
            self.assertEqual(self.results[kpi_id].status, kpi.AVAILABLE, kpi_id)


# ==========================================================================
# Edge cases
# ==========================================================================

class TestEdgeCases(KpiCase):

    def test_zero_revenue_makes_margins_undefined_not_zero(self):
        results = self.compute(fx.zero_revenue(self.tmp))
        self.assertEqual(results["revenue"].value, Decimal("0"))
        for kpi_id in ("gross_margin", "operating_margin", "ebitda_margin"):
            self.assertEqual(results[kpi_id].status, kpi.UNAVAILABLE, kpi_id)
            self.assertIn("undefined", results[kpi_id].reason)

    def test_zero_investment_makes_roi_undefined(self):
        results = self.compute(fx.zero_investment(self.tmp))
        self.assertEqual(results["return_on_investment"].status, kpi.UNAVAILABLE)
        self.assertIn("undefined", results["return_on_investment"].reason)

    def test_no_decided_deals_makes_win_rate_undefined(self):
        results = self.compute(fx.all_open_deals(self.tmp))
        self.assertEqual(results["win_rate"].status, kpi.UNAVAILABLE)
        self.assertIn("undefined", results["win_rate"].reason)

    def test_no_repeat_customers_gives_zero_retention_not_an_error(self):
        results = self.compute(fx.no_repeat_customers(self.tmp))
        self.assertEqual(results["customer_retention"].value, Decimal("0"))
        self.assertEqual(results["customer_churn"].value, Decimal("100"))

    def test_cash_generative_business_has_zero_burn_and_unbounded_runway(self):
        results = self.compute(fx.cash_generative(self.tmp))
        self.assertEqual(results["burn_rate"].value, Decimal("0"))
        self.assertEqual(results["runway"].status, kpi.UNAVAILABLE)
        self.assertIn("cash-generative", results["runway"].reason)

    def test_loss_making_business_has_a_real_burn_and_finite_runway(self):
        results = self.compute(fx.loss_making(self.tmp))
        self.assertGreater(results["burn_rate"].value, 0)
        self.assertEqual(results["runway"].status, kpi.AVAILABLE)
        self.assertGreater(results["runway"].value, 0)

    def test_burn_rate_is_never_negative(self):
        results = self.compute(fx.cash_generative(self.tmp))
        self.assertGreaterEqual(results["burn_rate"].value, 0)

    def test_very_large_values_keep_full_precision(self):
        results = self.compute(fx.large_values(self.tmp))
        # 9 rows x 99999999999.99
        self.assertEqual(results["revenue"].value, Decimal("899999999999.91"))

    def test_decimal_arithmetic_has_no_binary_float_error(self):
        results = self.compute(fx.rounding_boundary(self.tmp))
        # 2 rows x 0.10 revenue, 0.20 cost
        self.assertEqual(results["revenue"].value, Decimal("0.20"))
        self.assertEqual(results["gross_profit"].value, Decimal("-0.20"))

    def test_empty_dataset_is_refused_at_ingestion(self):
        from bops.errors import ConfigError
        path = os.path.join(self.tmp, "empty.csv")
        open(path, "w").close()
        with self.assertRaises(ConfigError):
            self.compute(path)

    def test_a_calculator_error_becomes_a_structured_result(self):
        """A Python traceback is never a user-facing KPI outcome."""
        definition = catalog.BY_ID["revenue"]
        original = definition.calculator

        def explode(_definition, _context):
            raise ValueError("deliberate failure")

        definition.calculator = explode
        try:
            results = self.compute(fx.rich_business(self.tmp), kpi_ids=("revenue",))
        finally:
            definition.calculator = original
        self.assertEqual(results["revenue"].status, kpi.UNAVAILABLE)
        self.assertIn("could not be calculated", results["revenue"].reason)
        self.assertIn("deliberate failure", results["revenue"].reason)


# ==========================================================================
# Currency
# ==========================================================================

class TestCurrencySafety(KpiCase):

    def test_mixed_currency_refuses_monetary_metrics(self):
        results = self.compute(fx.mixed_currency(self.tmp))
        self.assertEqual(results["revenue"].status, kpi.UNAVAILABLE)
        self.assertIn("does not convert", results["revenue"].reason)

    def test_mixed_currency_does_not_silently_convert(self):
        results = self.compute(fx.mixed_currency(self.tmp))
        self.assertIsNone(results["revenue"].value)

    def test_context_currency_mismatch_refuses_monetary_metrics(self):
        path = fx.rich_business(self.tmp)
        with open(path, encoding="utf-8") as fh:
            text = fh.read().replace("1000.00", "$1000.00")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        results = self.compute(path, context_overrides={"reporting": {"currency": "GBP"}})
        self.assertEqual(results["revenue"].status, kpi.UNAVAILABLE)
        self.assertIn("No exchange rate is applied", results["revenue"].reason)

    def test_non_monetary_metrics_survive_a_currency_problem(self):
        results = self.compute(fx.mixed_currency(self.tmp))
        self.assertEqual(results["customer_retention"].status, kpi.AVAILABLE)

    def test_demo_currency_is_gbp_from_business_context(self):
        dataset = ingest.read(DEMO_CSV)
        results = kpi.calculate(dataset, mapping.infer(dataset),
                                context_loader.resolve(overrides=demo_context(),
                                                       load_files=False),
                                canonical=canonical_mod.build(dataset))
        self.assertEqual(results["revenue"].currency, "GBP")


# ==========================================================================
# Quality integration
# ==========================================================================

class TestQualityIntegration(KpiCase):

    def test_critical_quality_suppresses_every_metric(self):
        results = self.compute(qfx.missing_values(self.tmp), with_quality=True)
        self.assertTrue(all(not r.available for r in results.values()))
        self.assertIn("quality gate halted", results["revenue"].reason)

    def test_warning_quality_still_produces_metrics(self):
        results = self.compute(qfx.warning_only(self.tmp), with_quality=True)
        self.assertEqual(results["revenue"].status, kpi.AVAILABLE)

    def test_warning_caveats_travel_with_every_figure(self):
        results = self.compute(qfx.warning_only(self.tmp), with_quality=True)
        self.assertTrue(results["revenue"].caveats)

    def test_clean_quality_adds_no_caveats(self):
        results = self.compute(fx.rich_business(self.tmp), with_quality=True)
        self.assertEqual(results["revenue"].caveats, [])

    def test_a_warning_does_not_suppress_unrelated_metrics(self):
        results = self.compute(qfx.warning_only(self.tmp), with_quality=True)
        available = [k for k, v in results.items() if v.available]
        self.assertGreater(len(available), 3)


# ==========================================================================
# Cross-KPI consistency
# ==========================================================================

class TestCrossKpiConsistency(KpiCase):

    def setUp(self):
        super().setUp()
        self.results = self.compute(fx.rich_business(self.tmp))

    def value(self, kpi_id):
        return self.results[kpi_id].value

    def test_gross_profit_equals_revenue_minus_cost(self):
        revenue = self.value("revenue")
        profit = self.value("gross_profit")
        self.assertEqual(profit, revenue - Decimal("21600"))

    def test_gross_margin_equals_gross_profit_over_revenue(self):
        expected = self.value("gross_profit") / self.value("revenue") * 100
        self.assertEqual(self.value("gross_margin"), expected)

    def test_operating_margin_equals_operating_profit_over_revenue(self):
        expected = self.value("operating_profit") / self.value("revenue") * 100
        self.assertEqual(self.value("operating_margin"), expected)

    def test_ebitda_equals_operating_profit_plus_depreciation(self):
        self.assertEqual(self.value("ebitda"),
                         self.value("operating_profit") + Decimal("720"))

    def test_ebitda_margin_equals_ebitda_over_revenue(self):
        expected = self.value("ebitda") / self.value("revenue") * 100
        self.assertEqual(self.value("ebitda_margin"), expected)

    def test_aov_equals_revenue_over_orders(self):
        orders = self.results["average_order_value"].inputs_used["orders"]
        self.assertEqual(self.value("average_order_value"),
                         self.value("revenue") / orders)

    def test_arr_equals_mrr_times_twelve(self):
        self.assertEqual(self.value("arr"), self.value("mrr") * 12)

    def test_retention_and_churn_sum_to_one_hundred(self):
        self.assertEqual(self.value("customer_retention") + self.value("customer_churn"),
                         Decimal("100"))

    def test_operating_profit_never_exceeds_gross_profit(self):
        self.assertLessEqual(self.value("operating_profit"), self.value("gross_profit"))

    def test_dependent_metrics_share_one_revenue_total(self):
        """No metric may compute its own revenue differently."""
        revenue = self.value("revenue")
        self.assertEqual(self.results["gross_profit"].inputs_used["revenue"], revenue)
        self.assertEqual(self.results["gross_margin"].inputs_used["revenue"], revenue)
        self.assertEqual(self.results["average_order_value"].inputs_used["revenue"],
                         revenue)


# ==========================================================================
# Provenance and schema
# ==========================================================================

class TestProvenanceAndSchema(KpiCase):

    def setUp(self):
        super().setUp()
        self.path = fx.rich_business(self.tmp)
        self.results = self.compute(self.path, with_quality=True)

    def test_every_result_carries_provenance(self):
        for result in self.results.values():
            self.assertTrue(result.provenance, result.kpi_id)
            self.assertIn("source", result.provenance)
            self.assertIn("calculated_at", result.provenance)

    def test_available_results_name_their_formula_and_inputs(self):
        for result in self.results.values():
            if result.available:
                self.assertTrue(result.formula, result.kpi_id)
                self.assertTrue(result.inputs_used, result.kpi_id)

    def test_results_are_classified_as_calculated_metrics(self):
        for result in self.results.values():
            self.assertEqual(result.as_dict()["classification"], "calculated_metric")

    def test_absent_results_explain_the_missing_requirement(self):
        results = self.compute(fx.sales_only(self.tmp))
        for result in results.values():
            if not result.available:
                self.assertTrue(result.reason, result.kpi_id)

    def test_document_validates_against_the_schema(self):
        document = kpi.as_document(self.results, currency="GBP",
                                   business_model="retail", quality_grade="PASS")
        self.assertEqual(kpi.validate_document(document, self.schema), [])

    def test_schema_uses_only_enforced_keywords(self):
        from bops import jsonschema_mini
        self.assertEqual(jsonschema_mini.unsupported_keywords(self.schema), set())

    def test_document_includes_every_metric_including_absent_ones(self):
        results = self.compute(fx.sales_only(self.tmp))
        document = kpi.as_document(results)
        self.assertEqual(len(document["results"]), 28)
        self.assertGreater(document["counts"]["unavailable"], 0)

    def test_provenance_records_the_quality_grade(self):
        self.assertIn("quality_grade", self.results["revenue"].provenance)


# ==========================================================================
# Demo dataset — the honest full picture
# ==========================================================================

class TestDemoDataset(KpiCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.result = pipeline.run(DEMO_CSV, context_overrides=demo_context(),
                                  load_context_files=False)

    def test_all_28_metrics_are_reported(self):
        self.assertEqual(len(self.result.kpis), 28)

    def test_m2_figures_are_unchanged(self):
        kpis = self.result.kpis
        self.assertEqual(kpis["revenue"].value, Decimal("3467850.16"))
        self.assertEqual(kpis["gross_profit"].value, Decimal("1210775.23"))
        self.assertEqual(kpis["gross_margin"].value.quantize(Decimal("0.0001")),
                         Decimal("34.9143"))
        self.assertEqual(kpis["average_order_value"].value.quantize(Decimal("0.01")),
                         Decimal("1573.43"))

    def test_retail_context_marks_recurring_metrics_not_applicable(self):
        for kpi_id in ("recurring_revenue", "mrr", "arr", "net_revenue_retention"):
            self.assertEqual(self.result.kpis[kpi_id].status, kpi.NOT_APPLICABLE, kpi_id)

    def test_metrics_needing_absent_fields_are_unavailable_with_reasons(self):
        for kpi_id in ("operating_profit", "ebitda", "working_capital",
                       "inventory_turnover", "win_rate", "runway"):
            result = self.result.kpis[kpi_id]
            self.assertEqual(result.status, kpi.UNAVAILABLE, kpi_id)
            self.assertTrue(result.reason, kpi_id)

    def test_the_engine_does_not_manufacture_numbers(self):
        """The point of the whole milestone."""
        for result in self.result.kpis.values():
            if not result.available:
                self.assertIsNone(result.value, result.kpi_id)

    def test_the_honest_split_is_reported(self):
        counts = kpi.summary(self.result.kpis)
        self.assertEqual(counts["available"], 8)
        self.assertEqual(counts["not_applicable"], 4)
        self.assertEqual(counts["unavailable"], 16)
        self.assertEqual(counts["available"] + counts["unavailable"]
                         + counts["not_applicable"] + counts["insufficient_data"]
                         + counts["partial"], 28)


if __name__ == "__main__":
    unittest.main()
