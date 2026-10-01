"""The Milestone 7 command layer, end to end.

Each command is exercised for its purpose, its inputs, its output, its limitation behaviour
and its privacy behaviour. The layer boundary is then asserted directly: a command
sequences and formats, and everything it reports was produced by the Milestone 5 engine or
the Milestone 6 analytics before the command layer saw it.
"""

import json
import os
import re
import shutil
import tempfile
import unittest
from decimal import Decimal

from bops import analytics, commands, materiality, pipeline
from bops import mapping as mapping_mod
from bops.analytics import contract as analytics_contract
from bops.analytics import presentation
from bops.commands import query, registry, runner
from bops.quality import contract as quality_contract

from fixtures import build_analytics_fixtures as build
from fixtures import build_fixtures as legacy

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
DEMO_CONTEXT = os.path.join(REPO, "assets", "demo-data", "business_context.json")


def demo_context():
    with open(DEMO_CONTEXT, encoding="utf-8") as handle:
        return json.load(handle)


class CommandCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m7-")
        cls.paths = {
            "full": build.full(cls.directory),
            "no_customer": build.without(cls.directory, "Customer"),
            "no_product": build.without(cls.directory, "Product", "Category"),
            "no_cost": build.without(cls.directory, "CostOfGoods"),
            "single_period": build.single_period(cls.directory),
            "two_periods": build.two_periods(cls.directory),
            "critical": legacy.critical_missing_revenue(cls.directory),
            "warning": legacy.warning_duplicates(cls.directory),
        }
        cls._runs = {}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def run_command(self, command_id, key="full", question=None,
                    presentation_mode=presentation.LOCAL, context=None):
        cache = (command_id, key, question, presentation_mode,
                 json.dumps(context, sort_keys=True) if context else None)
        if cache not in self._runs:
            self._runs[cache] = commands.run(
                command_id, self.paths.get(key, key), question=question,
                presentation=presentation_mode, context_overrides=context,
                load_context_files=False)
        return self._runs[cache]

    def demo(self, command_id, question=None, presentation_mode=presentation.LOCAL):
        return self.run_command(command_id, DEMO, question=question,
                                presentation_mode=presentation_mode,
                                context=demo_context())


# ==========================================================================
# /business-health
# ==========================================================================

class TestBusinessHealth(CommandCase):

    def test_it_runs_all_four_domains(self):
        run = self.demo("business-health")
        self.assertEqual(run.status, runner.OK)
        self.assertEqual(sorted(run.analyses),
                         ["customer", "financial", "product", "sales"])

    def test_it_reports_the_headline_metrics(self):
        run = self.demo("business-health")
        coverage = run.focus_coverage()
        self.assertEqual(coverage["status"], runner.COMPLETE)
        self.assertEqual(coverage["available"], 5)

    def test_the_rendered_report_keeps_the_milestone_two_snapshot(self):
        """The vertical slice's output is embedded whole, not re-laid-out."""
        run = self.demo("business-health")
        report = commands.render(run)
        for marker in ("# Business Health Snapshot", "## Reporting basis",
                       "## KPI scorecard", "## Key findings", "## Data quality",
                       "## Provenance", "## Confidence and limitations",
                       "3,467,850.16"):
            self.assertIn(marker, report, marker)

    def test_the_rendered_report_adds_the_cross_domain_view(self):
        report = commands.render(self.demo("business-health"))
        self.assertIn("## Analysis", report)
        self.assertIn("| customer |", report)
        self.assertIn("| financial |", report)

    def test_a_halt_stops_it_before_any_figure(self):
        run = self.run_command("business-health", "critical")
        self.assertEqual(run.status, runner.HALTED)
        self.assertEqual(run.findings(), [])
        report = commands.render(run)
        self.assertIn("Analysis stopped", report)
        self.assertNotIn("## KPI scorecard", report)


# ==========================================================================
# /sales-analysis
# ==========================================================================

class TestSalesAnalysis(CommandCase):

    def test_it_invokes_the_sales_domain_only(self):
        run = self.demo("sales-analysis")
        self.assertEqual(sorted(run.analyses), ["sales"])
        self.assertEqual(run.spec.skill, "bops-sales-intelligence")

    def test_it_reports_findings_across_every_mapped_dimension(self):
        run = self.demo("sales-analysis")
        dimensions = {f.dimension for f in run.findings() if f.dimension}
        self.assertEqual(dimensions,
                         {"product", "category", "region", "salesperson", "customer"})

    def test_a_missing_dimension_is_named_not_substituted(self):
        run = self.run_command("sales-analysis", "no_product")
        analysis = run.analyses["sales"]
        self.assertIn("product", analysis.dimensions_skipped)
        self.assertEqual([f for f in run.findings() if f.dimension == "product"], [])

    def test_the_rendered_report_carries_every_required_section(self):
        report = commands.render(self.demo("sales-analysis"))
        for heading in ("# Sales Analysis", "## Reporting basis", "## Key findings",
                        "## KPIs", "## Analysis", "## Limitations", "## Data quality",
                        "## Evidence and provenance"):
            self.assertIn(heading, report, heading)


# ==========================================================================
# /customer-analysis
# ==========================================================================

class TestCustomerAnalysis(CommandCase):

    def test_it_invokes_the_customer_domain_only(self):
        run = self.demo("customer-analysis")
        self.assertEqual(sorted(run.analyses), ["customer"])
        self.assertEqual(run.spec.skill, "bops-customer-intelligence")

    def test_no_customer_column_makes_it_unavailable_with_a_named_reason(self):
        run = self.run_command("customer-analysis", "no_customer")
        self.assertEqual(run.status, runner.UNAVAILABLE)
        self.assertIn("customer", run.reason)
        self.assertEqual(run.findings(), [])

    def test_shareable_presentation_pseudonymises_every_customer(self):
        run = self.demo("customer-analysis", presentation_mode=presentation.SHAREABLE)
        blob = json.dumps(run.as_dict())
        self.assertNotIn("Eastgate Retail", blob)
        self.assertIn("Customer #", blob)

    def test_local_presentation_carries_the_export_restriction(self):
        run = self.demo("customer-analysis")
        analysis = run.analyses["customer"]
        self.assertIn("Customer", analysis.restricted_dimensions)
        self.assertTrue(any("pseudonymised" in c for c in analysis.caveats))

    def test_no_individual_transaction_is_ever_rendered(self):
        report = commands.render(self.demo("customer-analysis"))
        self.assertNotIn("SO-", report)

    def test_it_reports_the_not_applicable_metric_separately_from_the_missing_one(self):
        run = self.demo("customer-analysis")
        report = commands.render(run)
        self.assertIn("**not applicable**", report)
        self.assertIn("**unavailable**", report)


# ==========================================================================
# /product-analysis
# ==========================================================================

class TestProductAnalysis(CommandCase):

    def test_it_invokes_the_product_domain_only(self):
        run = self.demo("product-analysis")
        self.assertEqual(sorted(run.analyses), ["product"])
        self.assertEqual(run.spec.skill, "bops-product-intelligence")

    def test_no_product_column_makes_it_unavailable(self):
        run = self.run_command("product-analysis", "no_product")
        self.assertEqual(run.status, runner.UNAVAILABLE)
        self.assertEqual(run.findings(), [])

    def test_absent_cost_removes_margin_and_says_so(self):
        run = self.run_command("product-analysis", "no_cost")
        self.assertEqual(run.status, runner.OK)
        subjects = {item.subject for _domain, item in run.limitations()}
        self.assertIn("product profitability", subjects)

    def test_it_reports_margin_and_concentration_on_the_demo_data(self):
        ids = {f.analysis_id for f in self.demo("product-analysis").findings()}
        self.assertIn("product.product.margin_spread", ids)
        self.assertIn("product.product.concentration", ids)

    def test_it_never_calls_a_later_first_appearance_an_anomaly(self):
        report = commands.render(self.demo("product-analysis"))
        self.assertNotIn("anomaly", report.lower())
        self.assertIn("cannot distinguish", report)


# ==========================================================================
# /profitability-analysis and /cash-flow-analysis
# ==========================================================================

class TestProfitabilityAnalysis(CommandCase):

    def test_it_invokes_the_financial_domain(self):
        run = self.demo("profitability-analysis")
        self.assertEqual(sorted(run.analyses), ["financial"])
        self.assertEqual(run.spec.skill, "bops-financial-analysis")

    def test_it_walks_the_profit_statement_and_stops_where_the_data_stops(self):
        run = self.demo("profitability-analysis")
        coverage = run.focus_coverage()
        self.assertEqual(coverage["status"], runner.PARTIAL)
        self.assertEqual(coverage["available"], 3)
        for kpi_id in ("operating_profit", "ebitda", "return_on_investment"):
            self.assertIn(kpi_id, coverage["missing"])

    def test_it_never_estimates_an_absent_metric(self):
        run = self.demo("profitability-analysis")
        for kpi_id, result in run.focus_kpis():
            if result is not None and not result.available:
                self.assertIsNone(result.value, kpi_id)

    def test_margin_movement_is_reported_in_percentage_points(self):
        run = self.demo("profitability-analysis")
        movement = [f for f in run.findings()
                    if f.analysis_id == "financial.margin.movement"]
        self.assertEqual(len(movement), 1)
        self.assertEqual(movement[0].unit, "percentage_points")
        self.assertIn("pp", commands.render(run))

    def test_the_partial_coverage_is_stated_before_the_numbers(self):
        report = commands.render(self.demo("profitability-analysis"))
        self.assertIn("is partial:", report)
        self.assertLess(report.index("is partial:"), report.index("## KPIs"))


class TestCashFlowAnalysis(CommandCase):

    def test_it_says_plainly_that_cash_analysis_is_unavailable_on_a_sales_extract(self):
        run = self.demo("cash-flow-analysis")
        coverage = run.focus_coverage()
        self.assertEqual(coverage["status"], runner.NONE_AVAILABLE)
        self.assertEqual(coverage["available"], 0)
        report = commands.render(run)
        self.assertIn("is unavailable from this dataset", report)

    def test_every_absent_cash_metric_names_the_field_it_needs(self):
        run = self.demo("cash-flow-analysis")
        expected = {"burn_rate": "operating_expense", "runway": "cash_balance",
                    "working_capital": "current_assets",
                    "days_sales_outstanding": "receivables",
                    "days_payable_outstanding": "payables"}
        for kpi_id, field in expected.items():
            result = run.kpis[kpi_id]
            self.assertFalse(result.available, kpi_id)
            self.assertIn(field, result.reason, kpi_id)

    def test_no_cash_figure_is_ever_fabricated(self):
        run = self.demo("cash-flow-analysis")
        for kpi_id, result in run.focus_kpis():
            self.assertIsNone(result.value, kpi_id)

    def test_it_shares_the_financial_domain_with_profitability(self):
        cash = self.demo("cash-flow-analysis")
        profit = self.demo("profitability-analysis")
        self.assertEqual(cash.spec.domains, profit.spec.domains)
        self.assertEqual(len(cash.findings()), len(profit.findings()))
        self.assertNotEqual(cash.spec.kpi_focus, profit.spec.kpi_focus)


# ==========================================================================
# /ask-business-data
# ==========================================================================

class TestAskBusinessData(CommandCase):

    def ask(self, question):
        return self.demo("ask-business-data", question=question)

    def test_a_metric_question_returns_the_engine_result_unchanged(self):
        run = self.ask("What was our gross margin?")
        self.assertEqual(run.answer.status, query.ANSWERED)
        self.assertIs(run.answer.kpi, run.kpis["gross_margin"])

    def test_a_dimension_question_returns_an_existing_finding(self):
        run = self.ask("Which region grew fastest?")
        self.assertEqual(run.answer.status, query.ANSWERED)
        finding = run.answer.finding
        self.assertIn(finding, run.analyses["sales"].findings)
        self.assertEqual(finding.dimension, "region")
        self.assertEqual(finding.direction, "increase")

    def test_a_decline_question_returns_the_largest_decrease(self):
        run = self.ask("Which product declined most?")
        self.assertEqual(run.answer.finding.direction, "decrease")

    def test_only_the_domain_the_question_needs_is_run(self):
        self.assertEqual(sorted(self.ask("What was our gross margin?").analyses), [])
        self.assertEqual(sorted(self.ask("Which region grew fastest?").analyses),
                         ["sales"])

    def test_an_unavailable_metric_returns_the_engine_reason_verbatim(self):
        run = self.ask("Why is runway unavailable?")
        self.assertEqual(run.answer.status, query.UNAVAILABLE)
        self.assertEqual(run.answer.reason, run.kpis["runway"].reason)
        self.assertIn("cash_balance", run.answer.reason)

    def test_an_ambiguous_question_asks_rather_than_guesses(self):
        run = self.ask("Which region and product grew fastest?")
        self.assertEqual(run.status, runner.CLARIFICATION_NEEDED)
        self.assertIsNone(run.result)
        self.assertEqual(run.answer.status, query.CLARIFICATION_NEEDED)

    def test_an_out_of_scope_question_is_refused_before_any_file_is_read(self):
        run = self.ask("What will revenue be next quarter?")
        self.assertEqual(run.status, runner.UNSUPPORTED)
        self.assertIsNone(run.result)
        self.assertIn("/revenue-forecast", run.reason)
        self.assertNotIn("Milestone", run.reason)

    def test_a_sub_period_question_carries_the_whole_period_caveat(self):
        run = self.ask("What was revenue last quarter?")
        self.assertEqual(run.answer.status, query.ANSWERED)
        self.assertTrue(run.answer.caveats)
        self.assertIn("does not filter to a sub-period", run.answer.caveats[0])

    def test_the_answer_is_rendered_with_its_basis(self):
        report = commands.render(self.ask("What was our gross margin?"))
        self.assertIn("## Answer", report)
        self.assertIn("Formula:", report)
        self.assertIn("evidence class 4", report)

    def test_supporting_readings_are_offered_not_hidden(self):
        run = self.ask("Which products contributed most to revenue?")
        self.assertTrue(run.answer.supporting)
        ids = {f.analysis_id for f in run.answer.supporting}
        self.assertTrue(any(i.endswith("largest") for i in ids))


# ==========================================================================
# Cross-command guarantees
# ==========================================================================

class TestCrossCommand(CommandCase):

    def test_each_command_runs_exactly_the_domains_it_declares(self):
        for spec in registry.COMMANDS:
            if spec.command_id == "ask-business-data":
                continue
            run = self.demo(spec.command_id)
            self.assertEqual(sorted(run.analyses),
                             sorted(run.analysis_keys), spec.command_id)

    def test_no_command_duplicates_a_calculation(self):
        """Every KPI-derived finding carries the engine's own formula, not a restatement."""
        checked = 0
        for spec in registry.COMMANDS:
            if not spec.domains:
                continue
            run = self.demo(spec.command_id)
            for finding in run.findings():
                if finding.metric and ".kpi." in finding.analysis_id:
                    self.assertEqual(finding.basis, run.kpis[finding.metric].formula,
                                     finding.analysis_id)
                    checked += 1
        self.assertGreater(checked, 0)

    def test_commands_preserve_the_kpi_results_exactly(self):
        direct = pipeline.run(DEMO, context_overrides=demo_context(),
                              load_context_files=False)
        run = self.demo("business-health")
        self.assertEqual({k: v.value for k, v in run.kpis.items()},
                         {k: v.value for k, v in direct.kpis.items()})
        self.assertEqual({k: v.status for k, v in run.kpis.items()},
                         {k: v.status for k, v in direct.kpis.items()})

    def test_commands_preserve_quality_caveats(self):
        run = self.run_command("sales-analysis", "warning")
        self.assertEqual(run.quality_grade, quality_contract.WARNING)
        self.assertTrue(run.findings())
        for finding in run.findings():
            self.assertTrue(any(c.startswith("Data quality:") for c in finding.caveats))
        report = commands.render(run)
        self.assertLess(report.index("Data quality: WARNING"),
                        report.index("## Reporting basis"))

    def test_commands_preserve_materiality_verdicts(self):
        run = self.demo("sales-analysis")
        judged = [f for f in run.findings() if f.materiality]
        self.assertTrue(judged)
        for finding in judged:
            self.assertIn(finding.materiality,
                          (materiality.MATERIAL, materiality.NOT_MATERIAL,
                           materiality.UNDETERMINED))
            self.assertTrue(finding.materiality_reason)
        self.assertTrue(run.material_findings())

    def test_commands_preserve_evidence_and_provenance(self):
        for spec in registry.COMMANDS:
            if not spec.domains:
                continue
            run = self.demo(spec.command_id)
            for finding in run.findings():
                self.assertTrue(finding.fields_used, finding.analysis_id)
                self.assertTrue(finding.provenance.get("source"), finding.analysis_id)
                self.assertTrue(finding.confidence, finding.analysis_id)

    def test_commands_preserve_privacy_classification(self):
        run = self.demo("customer-analysis")
        before = run.result.canonical.sensitivity_map().summary()
        self.demo("customer-analysis", presentation_mode=presentation.SHAREABLE)
        after = run.result.canonical.sensitivity_map().summary()
        self.assertEqual(before, after)
        self.assertIn("Customer", after["never_externalizable"])

    def test_an_unsupported_command_is_refused(self):
        with self.assertRaises(KeyError):
            commands.run("competitor-analysis", DEMO)

    def test_ask_business_data_never_bypasses_the_deterministic_engine(self):
        run = self.demo("ask-business-data", question="What was revenue?")
        self.assertIs(run.answer.kpi, run.kpis["revenue"])
        self.assertEqual(run.answer.kpi.value,
                         pipeline.run(DEMO, context_overrides=demo_context(),
                                      load_context_files=False).kpis["revenue"].value)

    def test_repeated_execution_is_identical(self):
        for command_id in ("sales-analysis", "product-analysis"):
            first = commands.render(self.demo(command_id))
            second = commands.render(commands.run(
                command_id, DEMO, context_overrides=demo_context(),
                load_context_files=False))
            self.assertEqual(first, second, command_id)

    def test_every_command_result_is_json_serialisable(self):
        for spec in registry.COMMANDS:
            run = self.demo(spec.command_id,
                            question="What was revenue?" if not spec.domains else None)
            json.dumps(run.as_dict())

    def test_the_command_layer_adds_no_untraceable_claim(self):
        direct = pipeline.run(DEMO, context_overrides=demo_context(),
                              load_context_files=False)
        before = len(direct.ledger.untraceable())
        run = self.demo("business-health")
        self.assertEqual(len(run.ledger.untraceable()), before)

    def test_no_command_emits_interpretation_or_recommendation(self):
        for spec in registry.COMMANDS:
            if not spec.domains:
                continue
            run = self.demo(spec.command_id)
            for finding in run.findings():
                self.assertIn(finding.finding_type, analytics_contract.ENGINE_EMITS)


class TestBusinessContext(CommandCase):

    def test_business_model_reaches_the_command_output(self):
        report = commands.render(self.demo("customer-analysis"))
        self.assertIn("| Business model | retail |", report)
        self.assertIn("| Currency | GBP |", report)

    def test_no_business_context_suppresses_nothing_and_says_so(self):
        run = self.run_command("customer-analysis", "full")
        self.assertIsNone(run.analyses["customer"].business_model)
        report = commands.render(run)
        self.assertIn("relevance filtering is off", report)

    def test_the_comparison_window_is_reported(self):
        report = commands.render(self.demo("sales-analysis"))
        self.assertIn("| Comparison window |", report)

    def test_business_model_still_drives_kpi_applicability(self):
        run = self.demo("customer-analysis")
        self.assertEqual(run.kpis["net_revenue_retention"].status, "not_applicable")


if __name__ == "__main__":
    unittest.main()
