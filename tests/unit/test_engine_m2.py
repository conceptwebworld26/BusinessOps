"""Semantic mapping, quality checks, KPI registry, materiality, evidence and rendering.

Direct unit coverage of the Milestone 2 engine modules, exercised without the pipeline so a
failure localises to one module.
"""

import datetime
import unittest
from decimal import Decimal

from bops import config as config_mod
from bops import evidence, materiality
from bops import mapping as mapping_mod
from bops import render
from bops.evidence import LedgerError
from bops.ingest.dataset import Dataset
from bops.kpi import registry as kpi_registry
from bops.mapping import semantic
from bops.quality import checks as quality_checks


def make_dataset(columns, rows, source="test.csv"):
    return Dataset(columns, rows, "csv", source)


def sales_rows(months=6, revenue=1000.0, cost=600.0):
    rows = []
    for month in range(1, months + 1):
        rows.append({
            "OrderDate": datetime.date(2025, month, 15),
            "OrderID": "SO-%03d" % month,
            "Customer": "Acme",
            "Product": "Widget",
            "Region": "North",
            "Salesperson": "Rep A",
            "Quantity": 10,
            "NetRevenue": revenue,
            "CostOfGoods": cost,
        })
    return rows


SALES_COLUMNS = ["OrderDate", "OrderID", "Customer", "Product", "Region",
                 "Salesperson", "Quantity", "NetRevenue", "CostOfGoods"]


def default_config():
    return config_mod.resolve(defaults=config_mod.load_defaults())


# ==========================================================================
# Semantic mapping
# ==========================================================================

class TestSemanticMapping(unittest.TestCase):
    def test_clear_names_and_content_map_automatically(self):
        result = semantic.infer(make_dataset(SALES_COLUMNS, sales_rows()))
        self.assertEqual(result.mappings[semantic.REVENUE].column, "NetRevenue")
        self.assertEqual(result.mappings[semantic.REVENUE].status, semantic.AUTO)

    def test_name_alone_is_not_enough_when_content_contradicts(self):
        """A column called Revenue full of text must not be mapped as revenue."""
        rows = [{"OrderDate": datetime.date(2025, 1, 1), "Revenue": "not a number"}
                for _ in range(10)]
        result = semantic.infer(make_dataset(["OrderDate", "Revenue"], rows))
        revenue = result.mappings.get(semantic.REVENUE)
        self.assertTrue(revenue is None or revenue.status != semantic.AUTO)

    def test_generic_name_lands_in_the_confirm_band(self):
        rows = [{"Period": datetime.date(2025, m, 1), "Amount": 100.0 * m}
                for m in range(1, 7)]
        result = semantic.infer(make_dataset(["Period", "Amount"], rows))
        revenue = result.mappings[semantic.REVENUE]
        self.assertEqual(revenue.status, semantic.CONFIRM_REQUIRED)
        self.assertGreaterEqual(revenue.confidence, semantic.CONFIRM_THRESHOLD)
        self.assertLess(revenue.confidence, semantic.AUTO_THRESHOLD)

    def test_unit_price_does_not_win_the_revenue_role(self):
        columns = ["OrderDate", "UnitPrice", "NetRevenue"]
        rows = [{"OrderDate": datetime.date(2025, m, 1), "UnitPrice": 10.0,
                 "NetRevenue": 100.0} for m in range(1, 7)]
        result = semantic.infer(make_dataset(columns, rows))
        self.assertEqual(result.mappings[semantic.REVENUE].column, "NetRevenue")

    def test_one_column_fills_only_one_role(self):
        result = semantic.infer(make_dataset(SALES_COLUMNS, sales_rows()))
        used = [m.column for m in result.mappings.values()]
        self.assertEqual(len(used), len(set(used)))

    def test_unmapped_roles_are_reported(self):
        result = semantic.infer(make_dataset(["OrderDate", "NetRevenue"],
                                             [{"OrderDate": datetime.date(2025, 1, 1),
                                               "NetRevenue": 10.0}]))
        self.assertIn(semantic.CUSTOMER, result.unmapped_roles)

    def test_confirmed_requires_auto_status(self):
        rows = [{"Period": datetime.date(2025, m, 1), "Amount": 100.0}
                for m in range(1, 7)]
        result = semantic.infer(make_dataset(["Period", "Amount"], rows))
        self.assertFalse(result.confirmed(semantic.REVENUE))

    def test_require_separates_missing_from_unconfirmed(self):
        rows = [{"Period": datetime.date(2025, m, 1), "Amount": 100.0}
                for m in range(1, 7)]
        result = semantic.infer(make_dataset(["Period", "Amount"], rows))
        missing, unconfirmed = result.require([semantic.REVENUE, semantic.CUSTOMER])
        self.assertIn(semantic.CUSTOMER, missing)
        self.assertIn(semantic.REVENUE, unconfirmed)

    def test_profit_is_derivable_from_revenue_and_cost(self):
        result = semantic.infer(make_dataset(SALES_COLUMNS, sales_rows()))
        self.assertEqual(semantic.derivable_profit(result), "derived")

    def test_clarification_request_names_the_column(self):
        rows = [{"Period": datetime.date(2025, m, 1), "Amount": 100.0}
                for m in range(1, 7)]
        result = semantic.infer(make_dataset(["Period", "Amount"], rows))
        self.assertIn("Amount", " ".join(result.clarification_request()))


# ==========================================================================
# Quality checks
# ==========================================================================

class TestQualityChecks(unittest.TestCase):
    def setUp(self):
        self.config = default_config()

    def _run(self, dataset):
        return quality_checks.run(dataset, semantic.infer(dataset), self.config)

    def test_clean_data_passes(self):
        report = self._run(make_dataset(SALES_COLUMNS, sales_rows()))
        self.assertEqual(report.grade, quality_checks.PASS)
        self.assertFalse(report.halted)

    def test_check_families_are_registered(self):
        # M4 replaced the M2/M3 groupings with the approved 13-family taxonomy. The
        # concerns those groupings covered must all still be represented.
        names = [name for name, _ in quality_checks.FAMILIES]
        self.assertEqual(len(names), 13)
        for expected in ("missing_values", "duplicate_records", "invalid_dates",
                         "invalid_numbers", "currency_consistency",
                         "incomplete_dataset"):
            self.assertIn(expected, names)

    def test_empty_dataset_is_critical(self):
        report = self._run(make_dataset(SALES_COLUMNS, []))
        self.assertEqual(report.grade, quality_checks.CRITICAL)
        self.assertTrue(report.halted)

    def test_missing_revenue_column_is_critical(self):
        rows = [{"OrderDate": datetime.date(2025, 1, 1), "Note": "x"}]
        report = self._run(make_dataset(["OrderDate", "Note"], rows))
        self.assertEqual(report.grade, quality_checks.CRITICAL)

    def test_high_missing_rate_in_revenue_is_critical(self):
        rows = sales_rows(10)
        for row in rows[:9]:
            row["NetRevenue"] = None
        report = self._run(make_dataset(SALES_COLUMNS, rows))
        self.assertEqual(report.grade, quality_checks.CRITICAL)

    def test_duplicate_order_ids_warn_but_do_not_halt(self):
        rows = sales_rows(4)
        for row in rows:
            row["OrderID"] = "SAME"
        report = self._run(make_dataset(SALES_COLUMNS, rows))
        self.assertEqual(report.grade, quality_checks.WARNING)
        self.assertFalse(report.halted)

    def test_inconsistent_casing_is_flagged(self):
        rows = sales_rows(4)
        rows[0]["Customer"] = "acme"
        rows[1]["Customer"] = "ACME"
        report = self._run(make_dataset(SALES_COLUMNS, rows))
        self.assertTrue(any("inconsistent" in f.code for f in report.findings))

    def test_negative_revenue_warns_and_is_not_removed(self):
        rows = sales_rows(4)
        rows[0]["NetRevenue"] = -100.0
        report = self._run(make_dataset(SALES_COLUMNS, rows))
        self.assertTrue(any(f.code == "negative_revenue" for f in report.findings))
        self.assertFalse(report.halted)

    def test_cost_exceeding_revenue_is_flagged(self):
        rows = sales_rows(4, revenue=100.0, cost=500.0)
        report = self._run(make_dataset(SALES_COLUMNS, rows))
        self.assertTrue(any(f.code == "cost_exceeds_revenue" for f in report.findings))

    def test_future_dates_warn(self):
        rows = sales_rows(4)
        rows[0]["OrderDate"] = datetime.date(datetime.date.today().year + 3, 1, 1)
        report = self._run(make_dataset(SALES_COLUMNS, rows))
        self.assertTrue(any(f.code == "future_dates" for f in report.findings))

    def test_grade_is_the_highest_severity_present(self):
        report = quality_checks.QualityReport([
            quality_checks.Finding("x", "a", quality_checks.INFO, "i"),
            quality_checks.Finding("x", "b", quality_checks.WARNING, "w")], 10)
        self.assertEqual(report.grade, quality_checks.WARNING)

    def test_info_only_grades_as_pass(self):
        report = quality_checks.QualityReport([
            quality_checks.Finding("x", "a", quality_checks.INFO, "i")], 10)
        self.assertEqual(report.grade, quality_checks.PASS)

    def test_halt_reason_lists_the_critical_findings(self):
        report = quality_checks.QualityReport([
            quality_checks.Finding("x", "a", quality_checks.CRITICAL, "boom")], 10)
        self.assertIn("boom", report.halt_reason())


# ==========================================================================
# KPI registry
# ==========================================================================

class TestKpiRegistry(unittest.TestCase):
    def setUp(self):
        self.config = default_config()
        self.dataset = make_dataset(SALES_COLUMNS, sales_rows(6, 1000.0, 600.0))
        self.map = semantic.infer(self.dataset)

    def _calc(self, context=None):
        return kpi_registry.calculate(self.dataset, self.map, context, self.config)

    def test_revenue_is_the_exact_sum(self):
        result = self._calc()["revenue"]
        self.assertEqual(result.value, Decimal("6000.00"))

    def test_gross_profit_and_margin_are_consistent(self):
        results = self._calc()
        self.assertEqual(results["gross_profit"].value, Decimal("2400.00"))
        self.assertEqual(results["gross_margin"].value, Decimal("40.0000"))

    def test_average_order_value_uses_distinct_orders(self):
        result = self._calc()["average_order_value"]
        self.assertEqual(result.value, Decimal("1000.00"))
        self.assertEqual(result.inputs["orders"], 6)

    def test_money_uses_decimal_not_float(self):
        self.assertIsInstance(self._calc()["revenue"].value, Decimal)

    def test_every_computed_kpi_carries_its_formula(self):
        for result in self._calc().values():
            self.assertTrue(result.formula, result.kpi_id)

    def test_missing_cost_makes_margin_unavailable(self):
        columns = [c for c in SALES_COLUMNS if c != "CostOfGoods"]
        rows = [{k: v for k, v in r.items() if k != "CostOfGoods"}
                for r in sales_rows(6)]
        dataset = make_dataset(columns, rows)
        results = kpi_registry.calculate(dataset, semantic.infer(dataset),
                                         None, self.config)
        self.assertEqual(results["gross_margin"].status, kpi_registry.UNAVAILABLE)
        self.assertIn("Insufficient data", results["gross_margin"].reason)

    def test_unavailable_names_the_missing_field(self):
        results = self._calc()
        self.assertIn("inventory_value", results["inventory_turnover"].reason)

    def test_not_applicable_depends_on_business_model(self):
        class Ctx:
            def __init__(self, model):
                self.model = model

            def get(self, key):
                return self.model if key == "identity.business_model" else None

        retail = self._calc(Ctx("retail"))["net_revenue_retention"]
        saas = self._calc(Ctx("saas"))["net_revenue_retention"]
        self.assertEqual(retail.status, kpi_registry.NOT_APPLICABLE)
        self.assertNotEqual(saas.status, kpi_registry.NOT_APPLICABLE)

    def test_no_business_model_suppresses_nothing(self):
        result = self._calc(None)["net_revenue_retention"]
        self.assertNotEqual(result.status, kpi_registry.NOT_APPLICABLE)

    def test_bucket_groups_all_four_statuses(self):
        grouped = kpi_registry.bucket(self._calc())
        for status in (kpi_registry.COMPUTED, kpi_registry.PARTIAL,
                       kpi_registry.UNAVAILABLE, kpi_registry.NOT_APPLICABLE):
            self.assertIn(status, grouped)

    def test_unconfirmed_mapping_blocks_computation(self):
        rows = [{"Period": datetime.date(2025, m, 1), "Amount": 100.0}
                for m in range(1, 7)]
        dataset = make_dataset(["Period", "Amount"], rows)
        results = kpi_registry.calculate(dataset, semantic.infer(dataset),
                                         None, self.config)
        self.assertEqual(results["revenue"].status, kpi_registry.UNAVAILABLE)
        self.assertIn("provisional", results["revenue"].reason)

    def test_registry_holds_the_formulas(self):
        """Formulas live here and nowhere else."""
        for kpi in kpi_registry.REGISTRY.values():
            self.assertTrue(kpi.formula)
            self.assertTrue(kpi.requires)


# ==========================================================================
# Materiality
# ==========================================================================

class TestMateriality(unittest.TestCase):
    def setUp(self):
        self.config = default_config()

    def test_large_absolute_move_is_material(self):
        verdict = materiality.assess_amount("x", 120000, 100000, self.config)
        self.assertTrue(verdict.is_material)
        self.assertEqual(verdict.threshold_used, "absolute_amount")

    def test_small_relative_move_is_material(self):
        verdict = materiality.assess_amount("x", 1080, 1000, self.config)
        self.assertTrue(verdict.is_material)
        self.assertEqual(verdict.threshold_used, "percentage")

    def test_tiny_move_is_not_material(self):
        verdict = materiality.assess_amount("x", 1010, 1000, self.config)
        self.assertEqual(verdict.outcome, materiality.NOT_MATERIAL)

    def test_missing_input_is_undetermined_not_immaterial(self):
        verdict = materiality.assess_amount("x", 1000, None, self.config)
        self.assertEqual(verdict.outcome, materiality.UNDETERMINED)
        self.assertNotEqual(verdict.outcome, materiality.NOT_MATERIAL)

    def test_margin_uses_percentage_points(self):
        verdict = materiality.assess_margin("m", 32.0, 35.0, self.config)
        self.assertTrue(verdict.is_material)
        self.assertEqual(verdict.unit, "percentage_points")
        self.assertEqual(verdict.absolute_change, Decimal("-3.0"))

    def test_small_margin_move_is_not_material(self):
        verdict = materiality.assess_margin("m", 34.5, 35.0, self.config)
        self.assertFalse(verdict.is_material)

    def test_verdict_names_threshold_source(self):
        verdict = materiality.assess_amount("x", 120000, 100000, self.config)
        self.assertEqual(verdict.threshold_source, "default")

    def test_user_threshold_overrides_default(self):
        config = config_mod.resolve(
            defaults=config_mod.load_defaults(),
            project_context={"analysis": {"materiality": {"absolute_amount": 5}}})
        verdict = materiality.assess_amount("x", 1010, 1000, config)
        self.assertTrue(verdict.is_material)
        self.assertEqual(verdict.threshold_source, "project")

    def test_zero_base_with_small_move_is_undetermined(self):
        verdict = materiality.assess_amount("x", 100, 0, self.config)
        self.assertEqual(verdict.outcome, materiality.UNDETERMINED)

    def test_filter_material_keeps_only_material(self):
        verdicts = [materiality.assess_amount("a", 120000, 100000, self.config),
                    materiality.assess_amount("b", 1010, 1000, self.config)]
        self.assertEqual(len(materiality.filter_material(verdicts)), 1)


# ==========================================================================
# Evidence ledger
# ==========================================================================

class TestEvidenceLedger(unittest.TestCase):
    def test_calculated_claim_requires_a_formula(self):
        with self.assertRaises(LedgerError):
            evidence.Claim("x = 5", evidence.CALCULATED)

    def test_user_data_claim_requires_a_source(self):
        with self.assertRaises(LedgerError):
            evidence.Claim("rows read", evidence.USER_DATA)

    def test_recommendation_requires_all_six_fields(self):
        with self.assertRaises(LedgerError):
            evidence.Claim("do x", evidence.RECOMMENDATION, evidence_="a")

    def test_recommendation_accepted_with_all_six(self):
        """Amended by M10.3.2: ADR-0031 fixes the six fields' shapes, not just their presence."""
        claim = evidence.Claim(
            "do x", evidence.RECOMMENDATION, evidence=["sy-0123456789ab"], rationale="r",
            expected_benefit="b", risks=["k"],
            dependencies=[{"text": "d", "assumption_id": None}], confidence="LOW")
        self.assertEqual(claim.label, "RECOMMENDATION")
        self.assertEqual(claim.based_on, ["sy-0123456789ab"])

    def test_recommendation_placeholders_are_not_evidence(self):
        """The M10.2-era truthiness check accepted evidence="e"; ADR-0031 refuses it."""
        with self.assertRaises(LedgerError):
            evidence.Claim(
                "do x", evidence.RECOMMENDATION, evidence="e", rationale="r",
                expected_benefit="b", risks="k", dependencies="d", confidence="LOW")

    def test_unknown_class_rejected(self):
        with self.assertRaises(LedgerError):
            evidence.Claim("x", 99)

    def test_labels_distinguish_fact_from_interpretation(self):
        fact = evidence.Claim("v", evidence.CALCULATED, formula="a+b")
        interpretation = evidence.Claim("v", evidence.INTERPRETATION)
        self.assertEqual(fact.label, "FACT")
        self.assertEqual(interpretation.label, "INTERPRETATION")

    def test_evidential_and_generative_split(self):
        self.assertTrue(evidence.Claim("v", evidence.CALCULATED,
                                       formula="f").is_evidential)
        self.assertFalse(evidence.Claim("v", evidence.INTERPRETATION).is_evidential)

    def test_global_caveat_applies_to_past_and_future_claims(self):
        ledger = evidence.Ledger()
        first = ledger.record("a", evidence.CALCULATED, formula="f")
        ledger.add_global_caveat("quality warning")
        second = ledger.record("b", evidence.CALCULATED, formula="f")
        self.assertIn("quality warning", first.caveats)
        self.assertIn("quality warning", second.caveats)

    def test_untraceable_interpretation_is_detected(self):
        ledger = evidence.Ledger()
        ledger.record("floating opinion", evidence.INTERPRETATION)
        self.assertEqual(len(ledger.untraceable()), 1)

    def test_interpretation_based_on_evidence_is_traceable(self):
        ledger = evidence.Ledger()
        ledger.record("revenue = 10", evidence.CALCULATED, formula="sum")
        claim = ledger.record("revenue looks strong", evidence.INTERPRETATION,
                              based_on=["revenue = 10"])
        self.assertTrue(ledger.traceable(claim))

    def test_summary_counts_by_class(self):
        ledger = evidence.Ledger()
        ledger.record("a", evidence.CALCULATED, formula="f")
        ledger.record("b", evidence.INTERPRETATION)
        summary = ledger.summary()
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["evidential"], 1)
        self.assertEqual(summary["generative"], 1)


# ==========================================================================
# Rendering
# ==========================================================================

class TestRendering(unittest.TestCase):
    def test_money_uses_currency_symbol(self):
        self.assertEqual(render.money(1234.5, "GBP"), "£1,234.50")
        self.assertEqual(render.money(1234.5, "USD"), "$1,234.50")

    def test_unknown_currency_falls_back_to_code(self):
        self.assertEqual(render.money(10, "XYZ"), "XYZ 10.00")

    def test_european_number_format(self):
        self.assertEqual(render.money(1234.5, "EUR", "1.234,56"), "€1.234,50")

    def test_negative_money_keeps_symbol(self):
        self.assertEqual(render.money(-50, "GBP"), "-£50.00")

    def test_rounding_happens_once_at_presentation(self):
        self.assertEqual(render.money(Decimal("10.005"), "USD"), "$10.01")

    def test_none_renders_as_not_available(self):
        self.assertEqual(render.money(None, "USD"), "n/a")
        self.assertEqual(render.percent(None), "n/a")

    def test_margin_movement_uses_percentage_points(self):
        self.assertEqual(render.points(Decimal("-3.07")), "-3.07pp")
        self.assertEqual(render.points(Decimal("2.5")), "+2.50pp")


if __name__ == "__main__":
    unittest.main()
