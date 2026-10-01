# -*- coding: utf-8 -*-
"""R-16: one margin movement, one value, one rounding.

Before M14-5 the same half-over-half gross-margin movement on the demo data rendered as
-2.84 percentage points in `/business-health` and -2.85pp in `/profitability-analysis`. The cause
was not formatting: the pipeline averaged monthly margins that `sales.margin_series()` had already
rounded to two places, so it rounded twice (CLAUDE.md section 4: rounding is applied once, at
presentation). The full-precision movement is -2.8454, which rounds half up to -2.85.

These tests pin the single computation and the single presentation rounding.
"""

import os
import sys
import unittest
from decimal import Decimal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.join(REPO, "lib", "python") not in sys.path:
    sys.path.insert(0, os.path.join(REPO, "lib", "python"))

from bops import commands, materiality, pipeline                          # noqa: E402
from bops.analytics import findings, segmentation                         # noqa: E402
from bops.config import resolve                                           # noqa: E402

DEMO = os.path.join(REPO, "assets", "demo-data", "northwind_sales.csv")


class MarginMovementIsComputedOnce(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result = pipeline.run(DEMO)

    def test_the_pipeline_halves_are_the_full_precision_halves(self):
        full = segmentation.margin_by_period(self.result.dataset, self.result.semantic_map)
        earlier, later = segmentation.series_halves(full)
        self.assertEqual(self.result.analysis["margin_earlier_pct"], earlier)
        self.assertEqual(self.result.analysis["margin_later_pct"], later)

    def test_the_movement_is_not_computed_from_the_rounded_series(self):
        rounded = [v for _p, v in self.result.analysis["margin_series"]]
        midpoint = len(rounded) // 2
        twice_rounded = (sum(rounded[midpoint:], Decimal("0")) / (len(rounded) - midpoint)
                         - sum(rounded[:midpoint], Decimal("0")) / midpoint)
        movement = (self.result.analysis["margin_later_pct"]
                    - self.result.analysis["margin_earlier_pct"])
        self.assertNotEqual(movement, twice_rounded)

    def test_both_commands_report_the_same_movement_on_the_demo_data(self):
        health = commands.render(commands.run("business-health", DEMO))
        profit = commands.render(commands.run("profitability-analysis", DEMO))
        self.assertIn("a change of -2.85 percentage points", health)
        self.assertIn("a change of -2.85pp", profit)
        self.assertNotIn("-2.84", health)
        self.assertNotIn("-2.84", profit)


class OnePresentationRounding(unittest.TestCase):
    """A tie at the third place rounds half up; binary-float `%.2f` would round it down."""

    def test_the_tie_case_differs_between_float_formatting_and_half_up(self):
        # -2.125 is exact in binary, so `%.2f` rounds the tie to even; half up does not.
        self.assertEqual("%.2f" % Decimal("-2.125"), "-2.12")    # the rule these tests replace

    def test_the_materiality_reason_rounds_half_up(self):
        verdict = materiality.assess_margin("Gross margin", Decimal("35.130"),
                                            Decimal("37.255"), resolve())
        self.assertIn("Margin moved -2.13pp", verdict.reason)

    def test_the_finding_rounds_half_up(self):
        self.assertEqual(str(findings._two_places(Decimal("-2.125"))), "-2.13")
        self.assertEqual(str(findings._two_places(Decimal("37.255"))), "37.26")


if __name__ == "__main__":                                   # pragma: no cover
    unittest.main()
