"""Every way the Milestone 6 analytics layer can be asked for something it cannot give.

The rule under test throughout: **explain the limitation, return a structured result, never
fabricate an insight, never raise an unhandled exception.** A missing column, an empty file,
a business model that makes a metric meaningless and a dataset the quality gate rejected are
four different answers, and the layer must not collapse them into one.
"""

import json
import os
import shutil
import tempfile
import unittest
from decimal import Decimal

from bops import analytics, pipeline
from bops import mapping as mapping_mod
from bops.analytics import contract, presentation, segmentation
from bops.errors import BusinessOpsError

from fixtures import build_analytics_fixtures as build
from fixtures import build_fixtures as legacy

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
DEMO_CONTEXT = os.path.join(REPO, "assets", "demo-data", "business_context.json")

DOMAINS = ("sales", "customer", "product", "financial")


def demo_context():
    with open(DEMO_CONTEXT, encoding="utf-8") as handle:
        return json.load(handle)


class NegativeCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m6-negative-")
        cls.paths = {
            "empty": build.empty(cls.directory),
            "single_period": build.single_period(cls.directory),
            "two_periods": build.two_periods(cls.directory),
            "zero_revenue": build.zero_revenue(cls.directory),
            "single_customer": build.single_customer(cls.directory),
            "no_dimensions": build.without(
                cls.directory, "Customer", "Product", "Category", "Region",
                "Salesperson", name="analytics_no_dimensions.csv"),
            "no_cost": build.without(cls.directory, "CostOfGoods"),
            "critical": legacy.critical_missing_revenue(cls.directory),
            "no_revenue_column": legacy.critical_no_revenue_column(cls.directory),
        }

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def run_pipeline(self, key, **kwargs):
        return pipeline.run(self.paths[key], load_context_files=False, **kwargs)

    def analyse(self, key, **kwargs):
        return analytics.analyse_all(self.run_pipeline(key, **kwargs))


# ==========================================================================
# Data that cannot support the analysis at all
# ==========================================================================

class TestUnusableData(NegativeCase):

    def test_an_empty_dataset_stops_at_the_gate_and_claims_nothing(self):
        result = self.run_pipeline("empty")
        self.assertTrue(result.halted)
        for name, analysis in analytics.analyse_all(result).items():
            self.assertEqual(analysis.status, contract.UNAVAILABLE, name)
            self.assertEqual(analysis.findings, [], name)
            self.assertTrue(analysis.reason, name)

    def test_a_quality_halt_produces_no_claim_in_any_domain(self):
        for name, analysis in self.analyse("critical").items():
            self.assertEqual(analysis.findings, [], name)
            self.assertIn("quality gate", analysis.reason, name)

    def test_no_revenue_column_is_reported_not_worked_around(self):
        result = self.run_pipeline("no_revenue_column")
        sets = analytics.analyse_all(result)
        for name in ("sales", "financial"):
            self.assertEqual(sets[name].status, contract.UNAVAILABLE, name)
            self.assertTrue(sets[name].reason, name)

    def test_a_missing_file_raises_a_business_error_not_a_stray_oserror(self):
        with self.assertRaises(BusinessOpsError):
            pipeline.run(os.path.join(self.directory, "no-such-file.csv"),
                         load_context_files=False)


# ==========================================================================
# Missing dimensions, one at a time
# ==========================================================================

class TestMissingDimensions(NegativeCase):

    def test_every_missing_dimension_is_named_in_two_places(self):
        sets = self.analyse("no_dimensions")
        sales = sets["sales"]
        for name in ("product", "category", "region", "salesperson", "customer"):
            self.assertIn(name, sales.dimensions_skipped, name)
        codes = {(item.code, item.subject) for item in sales.limitations}
        for name in ("product", "region", "salesperson"):
            self.assertIn(("unmapped_dimension", name), codes, name)

    def test_a_domain_whose_only_dimension_is_missing_is_unavailable(self):
        sets = self.analyse("no_dimensions")
        self.assertEqual(sets["customer"].status, contract.UNAVAILABLE)
        self.assertEqual(sets["product"].status, contract.UNAVAILABLE)

    def test_sales_still_reports_what_it_can_without_any_dimension(self):
        sales = self.analyse("no_dimensions")["sales"]
        self.assertEqual(sales.status, contract.AVAILABLE)
        self.assertTrue([f for f in sales.findings if f.metric == "revenue"])
        self.assertEqual([f for f in sales.findings if f.dimension], [])

    def test_a_missing_cost_column_removes_margin_from_three_domains_with_a_reason(self):
        sets = self.analyse("no_cost")
        subjects = set()
        for name in ("product", "financial"):
            subjects |= {item.subject for item in sets[name].limitations}
        self.assertIn("product profitability", subjects)
        self.assertIn("margin movement", subjects)
        for name in DOMAINS:
            for finding in sets[name].findings:
                self.assertNotEqual(finding.metric, "gross_margin",
                                    "%s reported a margin without a cost column" % name)


# ==========================================================================
# Not enough history
# ==========================================================================

class TestInsufficientHistory(NegativeCase):

    def test_one_period_yields_no_comparison_anywhere(self):
        for name, analysis in self.analyse("single_period").items():
            for finding in analysis.findings:
                self.assertIsNone(finding.comparison_period,
                                  "%s compared periods it does not have" % name)

    def test_cohorts_below_the_minimum_are_insufficient_not_empty(self):
        customer = self.analyse("two_periods")["customer"]
        limitation = [item for item in customer.limitations
                      if item.code.startswith("cohorts_")][0]
        self.assertEqual(limitation.status, contract.INSUFFICIENT_DATA)
        self.assertIn("periods", limitation.reason)

    def test_a_short_margin_series_is_reported_as_insufficient(self):
        financial = self.analyse("two_periods")["financial"]
        limitation = [item for item in financial.limitations
                      if item.code == "short_margin_series"][0]
        self.assertEqual(limitation.status, contract.INSUFFICIENT_DATA)


# ==========================================================================
# Degenerate arithmetic
# ==========================================================================

class TestDegenerateValues(NegativeCase):

    def test_zero_revenue_leaves_shares_undefined_rather_than_zero(self):
        result = self.run_pipeline("zero_revenue")
        segments = segmentation.segment(result.dataset, result.semantic_map,
                                        mapping_mod.PRODUCT)
        for item in segments:
            self.assertIsNone(item.share_pct)

    def test_zero_revenue_reports_the_cost_ratio_as_undefined(self):
        financial = self.analyse("zero_revenue")["financial"]
        codes = {item.code for item in financial.limitations}
        self.assertIn("zero_revenue", codes)
        self.assertEqual([f for f in financial.findings
                          if f.analysis_id == "financial.cost.ratio"], [])

    def test_no_domain_reports_a_value_of_none_as_if_it_were_a_number(self):
        for key in ("zero_revenue", "single_period", "two_periods"):
            for name, analysis in self.analyse(key).items():
                for finding in analysis.findings:
                    self.assertNotIn("None", finding.statement,
                                     "%s/%s leaked a null into prose" % (key, name))


# ==========================================================================
# Privacy under pressure
# ==========================================================================

class TestPrivacyNegative(NegativeCase):

    def test_a_customer_base_below_the_floor_is_banded_not_counted(self):
        customer = self.analyse("single_customer")["customer"]
        count = [f for f in customer.findings
                 if f.analysis_id == "customer.customers.count"][0]
        self.assertNotIn("1 distinct", count.statement)
        self.assertIn("1-9", count.statement)

    def test_shareable_presentation_never_leaks_an_identifying_value(self):
        result = pipeline.run(DEMO, context_overrides=demo_context(),
                              load_context_files=False)
        sets = analytics.analyse_all(result, presentation=presentation.SHAREABLE)
        blob = json.dumps({k: v.as_dict() for k, v in sets.items()})
        for name in ("Eastgate Retail", "M. Delacroix", "Zetland Markets"):
            self.assertNotIn(name, blob)

    def test_sensitivity_classification_is_never_weakened(self):
        result = pipeline.run(DEMO, context_overrides=demo_context(),
                              load_context_files=False)
        before = result.canonical.sensitivity_map().summary()
        analytics.analyse_all(result, presentation=presentation.SHAREABLE)
        after = result.canonical.sensitivity_map().summary()
        self.assertEqual(before, after)
        self.assertIn("Customer", after["never_externalizable"])


# ==========================================================================
# Unsupported requests
# ==========================================================================

class TestUnsupportedRequests(NegativeCase):

    def test_an_unknown_domain_is_refused_by_name(self):
        result = self.run_pipeline("two_periods")
        with self.assertRaises(KeyError) as caught:
            pipeline.analyse(result, domains=["forecast"])
        self.assertIn("forecast", str(caught.exception))

    def test_an_unknown_presentation_mode_is_refused(self):
        with self.assertRaises(ValueError):
            presentation.LabelPolicy(presentation="broadcast")

    def test_the_engine_refuses_to_emit_judgement(self):
        analysis = contract.AnalysisSet("sales")
        for finding_type in (contract.INTERPRETATION, contract.RECOMMENDATION,
                             contract.ASSUMPTION):
            with self.assertRaises(contract.AnalysisError):
                analysis.add(contract.AnalysisFinding(
                    "sales.x", "sales", finding_type, "A judgement.", basis="none"))

    def test_no_finding_states_a_forecast_or_an_anomaly(self):
        """Checked on statements only: a caveat that *disclaims* projection is correct."""
        result = pipeline.run(DEMO, context_overrides=demo_context(),
                              load_context_files=False)
        for name, analysis in analytics.analyse_all(result).items():
            for finding in analysis.findings:
                statement = finding.statement.lower()
                for word in ("forecast", "anomaly", "predicted", "projected",
                             "will be", "expected to"):
                    self.assertNotIn(word, statement,
                                     "%s/%s reads as a prediction"
                                     % (name, finding.analysis_id))

    def test_lifetime_value_carries_the_engine_disclaimer_that_it_is_observed(self):
        result = pipeline.run(DEMO, context_overrides=demo_context(),
                              load_context_files=False)
        customer = analytics.customers.analyse(result)
        clv = [f for f in customer.findings
               if f.metric == "customer_lifetime_value"][0]
        self.assertTrue(any("not a projected" in c.lower() for c in clv.caveats))


if __name__ == "__main__":
    unittest.main()
