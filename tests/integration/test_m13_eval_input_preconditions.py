"""M13.2 eval input fixtures establish their preconditions through the unchanged pipeline.

ADR-0041 section 7: each committed fixture under `tests/fixtures/eval_inputs/` has the fewest
rows and columns that establish its precondition *through the unchanged product pipeline*,
and section 1 admits a fixture only where `assets/demo-data/` cannot establish it. This module
checks both halves against the engine as shipped, reading the committed files, never a rebuild:

- EVI-01: revenue is only provisionally mapped, and that is the dataset's only quality finding;
- EVI-02: the quality gate grades `CRITICAL` and halts, and every analytical command stops;
- EVI-03: the quality gate passes, and the revenue forecast is refused for its four periods;
- the demo dataset maps revenue automatically, does not halt, and holds more periods than the
  forecast minimum, so it could stand in for none of the three.

These are properties of the **inputs**. What the model should do with them is the eval
case's to state and a grader's to observe; nothing here is a case's answer key.
"""

import json
import os
import unittest

from bops import commands, pipeline
from bops.commands import runner
from bops.mapping import semantic
from bops.quality import contract as quality_contract

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIXTURES = os.path.join(REPO, "tests", "fixtures", "eval_inputs")
DEMO = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")
CONFIG = os.path.join(REPO, "config", "businessops.defaults.json")

EVI_01 = os.path.join(FIXTURES, "s3_01_monthly_amounts.csv")
EVI_02 = os.path.join(FIXTURES, "s3_02_order_revenue.csv")
EVI_03 = os.path.join(FIXTURES, "s3_03_monthly_revenue.csv")

ANALYTICAL_COMMANDS = ("business-health", "sales-analysis", "customer-analysis",
                       "product-analysis", "profitability-analysis", "cash-flow-analysis")


def run(path):
    return pipeline.run(path, load_context_files=False)


def min_history():
    with open(CONFIG, encoding="utf-8") as handle:
        return json.load(handle)["forecast"]["min_history_periods"]


class AmbiguousRevenueColumn(unittest.TestCase):
    """EVI-01, bound to `evals/behaviour/b01-ambiguous-column`."""

    @classmethod
    def setUpClass(cls):
        cls.result = run(EVI_01)

    def test_revenue_is_mapped_only_provisionally(self):
        mapping = self.result.semantic_map.mappings[semantic.REVENUE]
        self.assertEqual(mapping.status, semantic.CONFIRM_REQUIRED)
        self.assertGreaterEqual(mapping.confidence, semantic.CONFIRM_THRESHOLD)
        self.assertLess(mapping.confidence, semantic.AUTO_THRESHOLD)

    def test_the_clarification_names_the_column(self):
        request = " ".join(self.result.semantic_map.clarification_request())
        self.assertIn("Amount", request)

    def test_the_ambiguity_is_the_only_quality_finding(self):
        quality = self.result.quality
        self.assertFalse(quality.halted)
        self.assertEqual(quality.grade, quality_contract.WARNING)
        self.assertEqual([f.check_id for f in quality.findings], ["incomplete_dataset"])

    def test_every_other_role_maps_automatically(self):
        others = [m for role, m in self.result.semantic_map.mappings.items()
                  if role != semantic.REVENUE]
        self.assertTrue(others)
        self.assertTrue(all(m.status == semantic.AUTO for m in others))


class CriticalQualityResult(unittest.TestCase):
    """EVI-02, bound to `evals/behaviour/b02-critical-quality-halt`."""

    def test_the_gate_grades_critical_and_halts(self):
        quality = run(EVI_02).quality
        self.assertTrue(quality.halted)
        self.assertEqual(quality.grade, quality_contract.CRITICAL)
        self.assertEqual([f.check_id for f in quality.findings], ["missing_values"])

    def test_the_mapping_is_not_what_halts_it(self):
        mappings = run(EVI_02).semantic_map.mappings
        self.assertTrue(all(m.status == semantic.AUTO for m in mappings.values()))

    def test_every_analytical_command_stops_with_no_findings(self):
        for command_id in ANALYTICAL_COMMANDS:
            with self.subTest(command=command_id):
                result = commands.run(command_id, EVI_02, load_context_files=False)
                self.assertEqual(result.status, runner.HALTED)
                self.assertEqual(result.findings(), [])


class FourPeriodHistory(unittest.TestCase):
    """EVI-03, bound to `evals/behaviour/b03-short-history-forecast`."""

    @classmethod
    def setUpClass(cls):
        cls.result = run(EVI_03)
        cls.forecast = pipeline.forecast(cls.result).as_dict()

    def test_the_quality_gate_passes(self):
        self.assertFalse(self.result.quality.halted)
        self.assertEqual(self.result.quality.grade, quality_contract.PASS)
        self.assertEqual(self.result.quality.findings, [])

    def test_the_history_is_four_monthly_periods(self):
        self.assertEqual(self.forecast["periods"], ["2025-01", "2025-02", "2025-03", "2025-04"])
        self.assertLess(len(self.forecast["periods"]), min_history())

    def test_the_revenue_forecast_is_refused_for_insufficient_history(self):
        revenue = [l for l in self.forecast["limitations"] if l["subject"] == "Revenue"]
        self.assertEqual(len(revenue), 1)
        self.assertEqual(revenue[0]["status"], "insufficient_data")
        self.assertEqual(self.forecast["findings"], [])


class TheDemoDatasetCannotStandIn(unittest.TestCase):
    """ADR-0041 section 1: a fixture is admissible only where the demo data cannot serve."""

    @classmethod
    def setUpClass(cls):
        cls.result = run(DEMO)

    def test_it_maps_revenue_automatically(self):
        self.assertEqual(self.result.semantic_map.mappings[semantic.REVENUE].status, semantic.AUTO)

    def test_it_does_not_halt(self):
        self.assertFalse(self.result.quality.halted)
        self.assertNotEqual(self.result.quality.grade, quality_contract.CRITICAL)

    def test_it_holds_at_least_the_forecast_minimum(self):
        periods = pipeline.forecast(self.result).as_dict()["periods"]
        self.assertGreaterEqual(len(periods), min_history())


if __name__ == "__main__":
    unittest.main()
