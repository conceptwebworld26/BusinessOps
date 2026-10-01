"""M10.2-R — the compatibility branches, in the shapes live retrieval actually produced.

M10.2 could not exercise the compatibility ALLOW branch: every live pair it found failed
on *unknown*, because the sources stated no geography and no methodology, and the check
fails on unknown rather than assuming a match. The M10.2-R live session (2026-09-15) ran
four bounded Tier-0 retrievals and produced three distinct outcomes, all three carried
here so the branch that fired on real evidence cannot silently stop firing:

  * **ALLOW.** Two sources reporting the *same compilation* — a statistical agency's
    release and a press article citing it — state all seven dimensions and agree on every
    one. `compare` returns `compatible`, `may_combine` is true, and nothing is converted
    or combined. This is the branch M10.2 left unexercised.
  * **INCOMPATIBLE with no unknowns.** Two sources measuring the same subject under
    different definitions state all seven dimensions and differ on three. This is a
    stronger refusal than M10.2 ever saw and must not be collapsed into the unknown case:
    "they disagree about what they measured" and "they did not say" are different findings.
  * **INCOMPATIBLE with unknowns.** The M10.2 shape, kept because it is still the common
    one: a definition mismatch alongside dimensions no source stated.

The fifth test is the sharpest available statement of ADR-0023, and the live session is
what made it available: the strongest external evidence the tiering model recognises — a
tier-A official statistic — still cannot found an internal `FACT`. Tier is not footing.

Fixtures only. The hosts are reserved or, for tier A, the domain the existing synthesis
fixtures already use; nothing here reaches the network, and the figures are the shapes the
live sources produced rather than the live values.
"""

import os
import sys
import unittest
from decimal import Decimal

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"),
             os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import synthesis as S                             # noqa: E402

from fixtures.build_synthesis_fixtures import (            # noqa: E402
    demo_evidence, evidence_set_with, new_set,
)

#: The seven dimensions, stated and agreeing, as the live ALLOW pair carried them.
AGREED = {
    "metric_definition": "retail e-commerce sales, not seasonally adjusted",
    "period": "Q4 2024",
    "geography": "demo territory",
    "currency": "USD",
    # ADR-0025: the pair published "USD bn"; the dimension carries the quantity type
    # and the values below are stated in base units.
    "unit": "currency",
    "scope": "all retail e-commerce sales",
    "methodology": "DEMO Statistics quarterly retail e-commerce survey",
}


def _agency_and_press():
    """A tier-A statistical agency and a tier-C press article citing it.

    The live pair's shape exactly: the agency release carried no publication date the
    fetch could confirm, and the press article did.
    """
    agency = demo_evidence(tier="A", host="ons.gov.uk", source="DEMO Statistics",
                           publication_date=None,
                           content="Quarterly retail e-commerce, Q4 2024.")
    press = demo_evidence(tier="C", host="press.example.invalid", source="DEMO Press",
                          publication_date="2026-06-01",
                          content="Citing DEMO Statistics for Q4 2024.")
    return agency, press


def _set_with(*items):
    result = new_set(currency="USD")
    S.register_external(result, evidence_set_with(*items), S.ORIGIN_MARKET)
    return result


class AllowBranchOnLiveShapedEvidence(unittest.TestCase):
    """Two sources reporting one compilation. The branch M10.2 could not reach."""

    def setUp(self):
        self.agency, self.press = _agency_and_press()
        self.result = _set_with(self.agency, self.press)
        self.left = S.sourced_statement(
            self.result, S.ORIGIN_MARKET,
            "DEMO Statistics reports Q4 2024 retail e-commerce sales of USD 352.9 bn.",
            evidence_ids=[self.agency.id], metric="market_size",
            observed=Decimal("352900000000"), **AGREED)
        self.right = S.sourced_statement(
            self.result, S.ORIGIN_MARKET,
            "DEMO Press, citing DEMO Statistics, reports Q4 2024 retail e-commerce "
            "sales of USD 352.9 bn.",
            evidence_ids=[self.press.id], metric="market_size",
            observed=Decimal("352900000000"), **AGREED)

    def test_all_seven_dimensions_stated_and_matching_is_compatible(self):
        comparison = S.compare(self.left, self.right)
        self.assertEqual(comparison["status"], S.COMPATIBLE)
        self.assertEqual(sorted(comparison["matched"]), sorted(S.DIMENSIONS))
        self.assertEqual(comparison["mismatched"], [])
        self.assertEqual(comparison["unknown"], [])

    def test_may_combine_is_true_only_here(self):
        self.assertTrue(S.may_combine(S.compare(self.left, self.right)))

    def test_a_compatible_comparison_has_no_mismatch_summary(self):
        self.assertIsNone(S.mismatch_summary(S.compare(self.left, self.right)))

    def test_nothing_is_converted_even_when_compatible(self):
        self.assertFalse(S.compare(self.left, self.right)["converted"])
        self.assertTrue(S.NEVER_CONVERTS)

    def test_compare_values_records_no_limitation_on_the_allow_path(self):
        before = len(self.result.limitations)
        S.compare_values(self.result, self.left, self.right, subject="e-commerce Q4")
        self.assertEqual(len(self.result.limitations), before)

    def test_compare_values_records_no_conflict_on_the_allow_path(self):
        S.compare_values(self.result, self.left, self.right, subject="e-commerce Q4")
        self.assertEqual(list(self.result.conflicts), [])

    def test_compatibility_does_not_mark_the_values_incomparable(self):
        S.compare_values(self.result, self.left, self.right, subject="e-commerce Q4")
        for item in (self.left, self.right):
            self.assertNotIn(S.INCOMPARABLE_VALUES, item.confidence_reasons)

    def test_a_compatible_comparison_produces_no_combined_figure(self):
        """Comparability is a precondition, never permission granted in passing."""
        comparison = S.compare_values(self.result, self.left, self.right,
                                      subject="e-commerce Q4")
        for forbidden in ("observed", "value", "combined", "ratio", "share",
                          "difference", "midpoint"):
            self.assertNotIn(forbidden, comparison)

    def test_compatibility_is_about_the_quantity_not_the_source_strength(self):
        """A tier-A and a tier-C statement are still comparable, and still graded apart."""
        self.assertTrue(S.may_combine(S.compare(self.left, self.right)))
        self.assertEqual(self.left.support, S.SUPPORTED)
        self.assertEqual(self.right.support, S.PARTIALLY_SUPPORTED)

    def test_an_undated_tier_a_source_still_names_its_weakness(self):
        """The reason is *derived* by the set, not supplied: it appears in the detail."""
        self.assertEqual(self.left.confidence_reasons, [])
        self.assertIn(S.UNDATED_EXTERNAL, self.left.confidence_detail["reasons"])
        self.assertIn(S.TIER_C_ONLY, self.right.confidence_detail["reasons"])

    def test_neither_statement_is_ever_trusted(self):
        for item in (self.left, self.right):
            self.assertEqual(item.trust, S.UNTRUSTED)
            self.assertEqual(item.kind, S.SOURCED)


class IncompatibleWithEveryDimensionStated(unittest.TestCase):
    """The live pair that differed on definition, scope and methodology, stating all seven.

    Distinct from the unknown case and must stay distinct: this is "the sources measured
    different things and said so", not "the sources did not say".
    """

    def setUp(self):
        self.a = demo_evidence(source="DEMO Agency Press",
                               host="press.example.invalid")
        self.b = demo_evidence(source="DEMO Research House",
                               host="research.example.invalid")
        self.result = _set_with(self.a, self.b)
        self.left = S.sourced_statement(
            self.result, S.ORIGIN_MARKET,
            "DEMO Agency Press reports retail e-commerce sales of USD 1.19 tn.",
            evidence_ids=[self.a.id], metric="market_size", observed=Decimal("1190000000000"),
            metric_definition="retail e-commerce sales", period="full year 2024",
            geography="demo territory", currency="USD", unit="currency",
            scope="retail trade, e-commerce channel",
            methodology="DEMO Statistics quarterly retail e-commerce survey")
        self.right = S.sourced_statement(
            self.result, S.ORIGIN_MARKET,
            "DEMO Research House reports online retail sales of USD 1.17 tn.",
            evidence_ids=[self.b.id], metric="market_size", observed=Decimal("1170000000000"),
            metric_definition="online retail sales", period="full year 2024",
            geography="demo territory", currency="USD", unit="currency",
            scope="DEMO Research House addressable retail base",
            methodology="DEMO Research House proprietary retail base")

    def test_it_is_incompatible(self):
        self.assertEqual(S.compare(self.left, self.right)["status"], S.INCOMPATIBLE)

    def test_no_dimension_is_unknown(self):
        self.assertEqual(S.compare(self.left, self.right)["unknown"], [])

    def test_the_three_differing_dimensions_are_each_named(self):
        named = {entry["dimension"]
                 for entry in S.compare(self.left, self.right)["mismatched"]}
        self.assertEqual(named, {"metric_definition", "scope", "methodology"})

    def test_close_figures_do_not_become_comparable(self):
        """1.19 and 1.17 look like agreement. They measure different things."""
        self.assertFalse(S.may_combine(S.compare(self.left, self.right)))

    def test_compare_values_records_the_limitation_and_marks_both_sides(self):
        S.compare_values(self.result, self.left, self.right, subject="e-commerce 2024")
        codes = [limitation.code for limitation in self.result.limitations]
        self.assertIn(S.INCOMPARABLE, codes)
        for item in (self.left, self.right):
            self.assertIn(S.INCOMPARABLE_VALUES, item.confidence_reasons)

    def test_same_domain_pairs_record_no_cross_domain_conflict(self):
        S.compare_values(self.result, self.left, self.right, subject="e-commerce 2024")
        self.assertEqual(list(self.result.conflicts), [])


class IncompatibleWithUnknownDimensions(unittest.TestCase):
    """The M10.2 shape, still the common one: a mismatch alongside unstated dimensions."""

    def setUp(self):
        self.a = demo_evidence(source="DEMO Press", host="press.example.invalid")
        self.b = demo_evidence(source="DEMO House", host="research.example.invalid")
        self.result = _set_with(self.a, self.b)
        self.left = S.sourced_statement(
            self.result, S.ORIGIN_INDUSTRY,
            "DEMO Press reports chip sales of USD 627.6 bn.",
            evidence_ids=[self.a.id], metric="industry_size",
            metric_definition="semiconductor chip sales", period="2024",
            geography="global", currency="USD", unit="currency",
            scope=None, methodology=None, observed=Decimal("627600000000"))
        self.right = S.sourced_statement(
            self.result, S.ORIGIN_INDUSTRY,
            "DEMO House reports industry revenue of USD 626 bn.",
            evidence_ids=[self.b.id], metric="industry_size",
            metric_definition="semiconductor industry revenue", period="2024",
            geography="global", currency="USD", unit="currency",
            scope=None, methodology="DEMO House preliminary estimate",
            observed=Decimal("626000000000"))

    def test_a_mismatch_outranks_an_unknown_in_the_reported_status(self):
        self.assertEqual(S.compare(self.left, self.right)["status"], S.INCOMPATIBLE)

    def test_the_unstated_dimensions_are_still_reported(self):
        unknown = {entry["dimension"]
                   for entry in S.compare(self.left, self.right)["unknown"]}
        self.assertEqual(unknown, {"scope", "methodology"})

    def test_an_absent_dimension_is_never_a_matching_dimension(self):
        comparison = S.compare(self.left, self.right)
        self.assertNotIn("scope", comparison["matched"])
        self.assertNotIn("methodology", comparison["matched"])

    def test_the_summary_names_the_mismatch_and_each_unknown(self):
        summary = S.mismatch_summary(S.compare(self.left, self.right))
        self.assertIn("metric_definition differs", summary)
        self.assertIn("scope not stated on both sides", summary)
        self.assertIn("methodology not stated on the left value", summary)


class TierAEvidenceIsStillNotInternalFooting(unittest.TestCase):
    """ADR-0023 at its strongest: the best external source there is, is still external.

    Every earlier footing test cites tier-C commercial research, which leaves open the
    reading that the rule is really about source quality. It is not. An official
    statistic carries the highest tier the model assigns and still cannot found an
    internal statement, because footing is about *whose data it is*, not how good it is.
    """

    def setUp(self):
        self.agency = demo_evidence(tier="A", host="ons.gov.uk",
                                    source="DEMO Statistics")
        self.result = _set_with(self.agency)
        self.ref = S.ProvenanceRef(S.P_EVIDENCE, self.agency.id)

    def test_tier_a_evidence_cannot_found_an_internal_fact(self):
        with self.assertRaises(S.SynthesisError) as caught:
            self.result.add(S.SynthesisItem(
                S.FACT, S.ORIGIN_FINANCIAL, "Our sales were USD 352.9 bn in Q4 2024.",
                provenance=[self.ref]))
        self.assertIn("internal FACT", str(caught.exception))

    def test_tier_a_evidence_cannot_found_a_material_internal_fact(self):
        with self.assertRaises(S.SynthesisError):
            self.result.add(S.SynthesisItem(
                S.FACT, S.ORIGIN_FINANCIAL, "Our sales were USD 352.9 bn in Q4 2024.",
                provenance=[self.ref],
                materiality={"outcome": "material", "reason": "headline figure"}))

    def test_tier_a_evidence_cannot_found_an_internal_calculation(self):
        with self.assertRaises(S.SynthesisError):
            self.result.add(S.SynthesisItem(
                S.CALCULATION, S.ORIGIN_KPI, "Market size is USD 352.9 bn.",
                provenance=[self.ref], basis="sourced figure"))

    def test_the_same_evidence_supports_a_sourced_statement_perfectly_well(self):
        """The remedy is never to weaken the rule; it is to use the right kind."""
        item = S.sourced_statement(
            self.result, S.ORIGIN_MARKET,
            "DEMO Statistics reports Q4 2024 retail e-commerce sales of USD 352.9 bn.",
            evidence_ids=[self.agency.id], metric="market_size", **AGREED)
        self.assertEqual(item.kind, S.SOURCED)
        self.assertEqual(item.domain, S.EXTERNAL)
        self.assertEqual(item.support, S.SUPPORTED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
