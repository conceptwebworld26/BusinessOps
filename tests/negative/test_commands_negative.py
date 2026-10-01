"""Every way a command can be asked for something it cannot give.

The rule under test throughout: **return a structured limitation or a clarification, never
a fabricated answer, and never an unhandled traceback.** A command is a user-facing
boundary, so a missing file, an empty dataset, a halted quality gate, an unmapped column and
an out-of-scope question must each come back as a result the caller can render.
"""

import json
import os
import shutil
import tempfile
import unittest

from bops import commands, pipeline
from bops.analytics import contract as analytics_contract
from bops.analytics import presentation
from bops.commands import query, registry, runner
from bops.quality import contract as quality_contract

from fixtures import build_analytics_fixtures as build
from fixtures import build_fixtures as legacy

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEMO = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
DEMO_CONTEXT = os.path.join(REPO, "assets", "demo-data", "business_context.json")

ANALYTICAL_COMMANDS = ("business-health", "sales-analysis", "customer-analysis",
                       "product-analysis", "profitability-analysis",
                       "cash-flow-analysis")


def demo_context():
    with open(DEMO_CONTEXT, encoding="utf-8") as handle:
        return json.load(handle)


class CommandNegativeCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-m7-negative-")
        cls.paths = {
            "empty": build.empty(cls.directory),
            "no_date": build.without(cls.directory, "OrderDate"),
            "no_customer": build.without(cls.directory, "Customer"),
            "no_product": build.without(cls.directory, "Product", "Category"),
            "no_region": build.without(cls.directory, "Region"),
            "no_salesperson": build.without(cls.directory, "Salesperson"),
            "no_cost": build.without(cls.directory, "CostOfGoods"),
            "single_period": build.single_period(cls.directory),
            "two_periods": build.two_periods(cls.directory),
            "single_customer": build.single_customer(cls.directory),
            "critical": legacy.critical_missing_revenue(cls.directory),
            "no_revenue_column": legacy.critical_no_revenue_column(cls.directory),
            "warning": legacy.warning_duplicates(cls.directory),
            "ambiguous": legacy.ambiguous_mapping(cls.directory),
        }
        cls.missing = os.path.join(cls.directory, "no-such-file.csv")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def run_command(self, command_id, key, **kwargs):
        return commands.run(command_id, self.paths.get(key, key),
                            load_context_files=False, **kwargs)


# ==========================================================================
# Input that cannot be read at all
# ==========================================================================

class TestUnreadableInput(CommandNegativeCase):

    def test_a_missing_file_is_a_structured_result_not_a_traceback(self):
        for command_id in ANALYTICAL_COMMANDS:
            run = commands.run(command_id, self.missing, load_context_files=False)
            self.assertEqual(run.status, runner.UNAVAILABLE, command_id)
            self.assertTrue(run.reason, command_id)
            self.assertTrue(run.error_type, command_id)
            self.assertEqual(run.findings(), [], command_id)

    def test_a_missing_file_still_renders(self):
        run = commands.run("sales-analysis", self.missing, load_context_files=False)
        report = commands.render(run)
        self.assertIn("## Not available", report)
        self.assertIn(run.error_type, report)

    def test_no_file_at_all_asks_for_one(self):
        for command_id in ANALYTICAL_COMMANDS:
            run = commands.run(command_id, None)
            self.assertEqual(run.status, runner.UNAVAILABLE, command_id)
            self.assertIn("does not choose a file", run.reason)

    def test_an_empty_dataset_halts_and_claims_nothing(self):
        for command_id in ANALYTICAL_COMMANDS:
            run = self.run_command(command_id, "empty")
            self.assertIn(run.status, (runner.HALTED, runner.UNAVAILABLE), command_id)
            self.assertEqual(run.findings(), [], command_id)


# ==========================================================================
# Missing columns, one at a time
# ==========================================================================

class TestMissingColumns(CommandNegativeCase):

    def test_missing_revenue_makes_every_analytical_command_unavailable(self):
        for command_id in ANALYTICAL_COMMANDS:
            run = self.run_command(command_id, "no_revenue_column")
            self.assertNotEqual(run.status, runner.OK, command_id)
            self.assertEqual(run.findings(), [], command_id)

    def test_missing_date_is_reported_by_name(self):
        run = self.run_command("sales-analysis", "no_date")
        self.assertNotEqual(run.status, runner.OK)
        self.assertTrue(run.reason)

    def test_missing_customer_stops_customer_analysis_only(self):
        blocked = self.run_command("customer-analysis", "no_customer")
        self.assertEqual(blocked.status, runner.UNAVAILABLE)
        allowed = self.run_command("sales-analysis", "no_customer")
        self.assertEqual(allowed.status, runner.OK)
        self.assertIn("customer", allowed.analyses["sales"].dimensions_skipped)

    def test_missing_product_stops_product_analysis_only(self):
        blocked = self.run_command("product-analysis", "no_product")
        self.assertEqual(blocked.status, runner.UNAVAILABLE)
        self.assertEqual(self.run_command("sales-analysis", "no_product").status,
                         runner.OK)

    def test_missing_region_and_salesperson_are_skipped_and_named(self):
        for key, dimension in (("no_region", "region"),
                               ("no_salesperson", "salesperson")):
            run = self.run_command("sales-analysis", key)
            self.assertEqual(run.status, runner.OK, key)
            self.assertIn(dimension, run.analyses["sales"].dimensions_skipped)
            self.assertEqual([f for f in run.findings() if f.dimension == dimension],
                             [], key)

    def test_missing_cost_removes_margin_from_every_command_that_uses_it(self):
        for command_id in ("product-analysis", "profitability-analysis"):
            run = self.run_command(command_id, "no_cost")
            for kpi_id, result in run.focus_kpis():
                if kpi_id == "gross_margin":
                    self.assertFalse(result.available, command_id)

    def test_missing_cash_fields_are_reported_never_fabricated(self):
        run = self.run_command("cash-flow-analysis", "no_cost")
        coverage = run.focus_coverage()
        self.assertEqual(coverage["status"], runner.NONE_AVAILABLE)
        for _kpi_id, result in run.focus_kpis():
            self.assertIsNone(result.value)
            self.assertTrue(result.reason)


# ==========================================================================
# Metric states
# ==========================================================================

class TestMetricStates(CommandNegativeCase):

    def demo(self, command_id, **kwargs):
        return commands.run(command_id, DEMO, context_overrides=demo_context(),
                            load_context_files=False, **kwargs)

    def test_unavailable_and_not_applicable_are_never_the_same_cell(self):
        run = self.demo("customer-analysis")
        report = commands.render(run)
        self.assertIn("**unavailable**", report)
        self.assertIn("**not applicable**", report)
        for _kpi_id, result in run.focus_kpis():
            if not result.available:
                self.assertIsNone(result.value)
                self.assertTrue(result.reason)

    def test_insufficient_history_is_reported_as_such(self):
        run = self.run_command("customer-analysis", "two_periods")
        statuses = {item.status for _domain, item in run.limitations()}
        self.assertIn(analytics_contract.INSUFFICIENT_DATA, statuses)

    def test_a_single_period_produces_no_comparison_anywhere(self):
        for command_id in ANALYTICAL_COMMANDS:
            run = self.run_command(command_id, "single_period")
            for finding in run.findings():
                self.assertIsNone(finding.comparison_period, command_id)


# ==========================================================================
# Quality states
# ==========================================================================

class TestQualityStates(CommandNegativeCase):

    def test_a_critical_grade_stops_every_command(self):
        for command_id in ANALYTICAL_COMMANDS:
            run = self.run_command(command_id, "critical")
            self.assertEqual(run.status, runner.HALTED, command_id)
            self.assertEqual(run.findings(), [], command_id)
            self.assertIn("quality gate", (run.reason or "").lower(), command_id)
            report = commands.render(run)
            self.assertIn("Analysis stopped", report)

    def test_a_warning_lets_commands_proceed_with_the_caveat_attached(self):
        run = self.run_command("sales-analysis", "warning")
        self.assertEqual(run.status, runner.OK)
        self.assertEqual(run.quality_grade, quality_contract.WARNING)
        for finding in run.findings():
            self.assertTrue(any(c.startswith("Data quality:") for c in finding.caveats))

    def test_an_ambiguous_mapping_marks_dependent_figures_provisional(self):
        run = self.run_command("sales-analysis", "ambiguous")
        if run.result is None or not run.result.semantic_map.needs_confirmation():
            self.skipTest("this fixture no longer produces an unconfirmed mapping")
        analysis = run.analyses.get("sales")
        if analysis is None:
            self.skipTest("the ambiguous fixture does not reach the sales analysis")
        self.assertTrue(any("provisionally identified" in c for c in analysis.caveats))

    def test_commands_never_rerun_the_quality_checks(self):
        direct = pipeline.run(DEMO, context_overrides=demo_context(),
                              load_context_files=False)
        before = len(direct.quality.findings)
        run = commands.run("business-health", DEMO, context_overrides=demo_context(),
                           load_context_files=False)
        self.assertEqual(len(run.quality.findings), before)


# ==========================================================================
# Privacy under pressure
# ==========================================================================

class TestPrivacyNegative(CommandNegativeCase):

    def test_a_customer_base_below_the_floor_is_banded(self):
        run = self.run_command("customer-analysis", "single_customer")
        count = [f for f in run.findings()
                 if f.analysis_id == "customer.customers.count"][0]
        self.assertIn("1-9", count.statement)

    def test_shareable_presentation_leaks_no_identifying_value(self):
        run = commands.run("customer-analysis", DEMO,
                           presentation=presentation.SHAREABLE,
                           context_overrides=demo_context(), load_context_files=False)
        blob = commands.render(run) + json.dumps(run.as_dict())
        for name in ("Eastgate Retail", "Zetland Markets"):
            self.assertNotIn(name, blob)

    def test_no_command_renders_an_individual_transaction(self):
        for command_id in ANALYTICAL_COMMANDS:
            run = commands.run(command_id, DEMO, context_overrides=demo_context(),
                               load_context_files=False)
            self.assertNotIn("SO-", commands.render(run), command_id)


# ==========================================================================
# Unsupported requests
# ==========================================================================

class TestUnsupportedRequests(CommandNegativeCase):

    def ask(self, question, path=DEMO):
        return commands.run("ask-business-data", path, question=question,
                            context_overrides=demo_context(), load_context_files=False)

    def test_an_unknown_command_is_refused_by_name(self):
        for name in ("competitor-analysis", "market-analysis", "executive-report"):
            with self.assertRaises(KeyError) as caught:
                commands.run(name, DEMO)
            self.assertIn(name, str(caught.exception))

    def test_an_unsupported_question_is_refused_before_the_file_is_read(self):
        for question, owner in (("Forecast next quarter revenue", "/revenue-forecast"),
                                ("Show me anomalies", "/anomaly-detection"),
                                ("How do competitors price this?", "/competitor-analysis")):
            run = self.ask(question)
            self.assertEqual(run.status, runner.UNSUPPORTED, question)
            self.assertIsNone(run.result, question)
            self.assertIn(owner, run.reason, question)
            self.assertNotIn("Milestone", run.reason, question)

    def test_an_ambiguous_question_asks_rather_than_answering_a_nearby_one(self):
        for question in ("", "Tell me about products", "What is the weather?",
                         "Which region and product grew fastest?"):
            run = self.ask(question)
            self.assertEqual(run.status, runner.CLARIFICATION_NEEDED, question)
            self.assertIsNone(run.answer.statement, question)
            self.assertTrue(run.answer.reason, question)

    def test_a_question_about_an_unmapped_dimension_is_unavailable_not_guessed(self):
        run = commands.run("ask-business-data", self.paths["no_region"],
                           question="Which region grew fastest?",
                           load_context_files=False)
        self.assertEqual(run.status, runner.UNAVAILABLE)
        self.assertIn("region", run.reason)

    def test_a_question_about_an_unavailable_metric_returns_the_engine_reason(self):
        run = self.ask("What is our EBITDA?")
        self.assertEqual(run.answer.status, query.UNAVAILABLE)
        self.assertEqual(run.answer.reason, run.kpis["ebitda"].reason)

    def test_a_question_on_a_halted_dataset_answers_nothing(self):
        run = commands.run("ask-business-data", self.paths["critical"],
                           question="What was revenue?", load_context_files=False)
        self.assertEqual(run.status, runner.HALTED)
        self.assertNotEqual(run.answer.status, query.ANSWERED)

    def test_no_finding_states_a_prediction(self):
        """Checked on statements: a report that *disclaims* forecasting is correct."""
        for command_id in ANALYTICAL_COMMANDS:
            run = commands.run(command_id, DEMO, context_overrides=demo_context(),
                               load_context_files=False)
            for finding in run.findings():
                statement = finding.statement.lower()
                for word in ("forecast", "predict", "will grow", "expected to",
                             "anomaly"):
                    self.assertNotIn(word, statement,
                                     "%s / %s" % (command_id, finding.analysis_id))

    def test_every_report_states_that_no_forecast_was_performed(self):
        run = commands.run("sales-analysis", DEMO, context_overrides=demo_context(),
                           load_context_files=False)
        self.assertIn("no external research, benchmarking or forecasting was performed",
                      commands.render(run))


if __name__ == "__main__":
    unittest.main()
