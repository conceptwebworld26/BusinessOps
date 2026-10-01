"""M10.1 - the cross-domain fixture end to end, and the contracts it must not disturb.

Covers matrix sections 10, 11, 14 and 73-77. The unit modules prove each rule in
isolation; this one proves they hold together on one object that contains every case at
once, and that adding the synthesis layer changed nothing underneath it.
"""

import json
import os
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"),
             os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import evidence as evidence_ledger                 # noqa: E402
from bops import materiality as materiality_mod              # noqa: E402
from bops import synthesis as S                              # noqa: E402
from bops.research import evidence_set as evidence_mod       # noqa: E402
from bops.research import sources as sources_mod             # noqa: E402

from fixtures import build_synthesis_fixtures as build      # noqa: E402


class CrossDomainFixture(unittest.TestCase):
    """Matrix 14 - the fixture contains every case the brief asks for."""

    def setUp(self):
        self.result, self.handles = build.build()

    def test_internal_revenue_and_growth_are_present(self):
        revenue = [i for i in self.result.items
                   if i.metric == "revenue" and i.origin == S.ORIGIN_SALES]
        self.assertEqual(len(revenue), 1)
        self.assertIsNotNone(revenue[0].change)
        self.assertIsNotNone(revenue[0].change_pct)

    def test_gross_margin_is_present_in_percentage_points(self):
        margin = next(i for i in self.result.items if i.metric == "gross_margin")
        self.assertEqual(margin.unit, "percent")
        self.assertEqual(margin.materiality["outcome"], materiality_mod.MATERIAL)
        self.assertIn("pp", margin.materiality["reason"])

    def test_a_product_and_a_customer_finding_are_present(self):
        origins = set(i.origin for i in self.result.items)
        self.assertIn(S.ORIGIN_PRODUCT, origins)
        self.assertIn(S.ORIGIN_CUSTOMER, origins)

    def test_a_forecast_and_an_anomaly_are_present(self):
        origins = set(i.origin for i in self.result.items)
        self.assertIn(S.ORIGIN_FORECAST, origins)
        self.assertIn(S.ORIGIN_ANOMALY, origins)
        forecast = next(i for i in self.result.items if i.origin == S.ORIGIN_FORECAST)
        self.assertIn(S.P_FORECAST, [r.kind for r in forecast.provenance])
        anomaly = next(i for i in self.result.items if i.origin == S.ORIGIN_ANOMALY)
        self.assertIn(S.P_ANOMALY, [r.kind for r in anomaly.provenance])

    def test_an_external_evidence_item_and_a_candidate_claim_are_present(self):
        self.assertGreaterEqual(self.result.summary()["evidence_items"], 1)
        self.assertEqual(self.result.summary()["candidate_claims"], 1)
        self.assertIs(self.result.candidate_claims[0]["verified"], False)

    def test_a_conflict_a_material_finding_and_a_limitation_are_present(self):
        self.assertEqual(len(self.result.unresolved_conflicts()), 1)
        self.assertGreaterEqual(len(self.result.material()), 1)
        self.assertGreaterEqual(len(self.result.limitations), 1)

    def test_the_fixture_carries_no_citation_that_could_pass_as_real(self):
        for evidence_set in self.result.as_dict()["evidence"]:
            for item in evidence_set["items"]:
                self.assertIn("example.invalid", item["reference"])
                self.assertTrue(item["source"].startswith(build.DEMO_PREFIX))
                self.assertTrue(any("Synthetic demo evidence" in note
                                    for note in item.get("notes", [])))

    def test_synthetic_demo_evidence_earns_no_tier_it_has_not_got(self):
        for evidence_set in self.result.as_dict()["evidence"]:
            for item in evidence_set["items"]:
                self.assertEqual(item["source_tier"], "C")
                self.assertFalse(item["may_stand_alone"])


class CrossDomainMerging(unittest.TestCase):
    """Matrix 10 - combining domains without implying they are comparable."""

    def setUp(self):
        self.result, self.handles = build.build()

    def test_internal_and_external_statements_are_separable_by_domain(self):
        internal = self.result.of_domain(S.INTERNAL)
        external = self.result.of_domain(S.EXTERNAL)
        self.assertTrue(internal and external)
        self.assertEqual(set(i.kind for i in external), {S.SOURCED})
        self.assertTrue(all(i.kind in (S.FACT, S.CALCULATION) for i in internal))

    def test_no_combined_internal_external_figure_is_produced_by_the_merge(self):
        # Every statement's value came from exactly one domain.
        for item in self.result.items:
            kinds = set(ref.kind for ref in item.provenance if ref.is_resolvable)
            external = kinds & set(S.contract.EXTERNAL_PROVENANCE)
            internal = kinds - set(S.contract.EXTERNAL_PROVENANCE)
            self.assertFalse(external and internal,
                             "%s mixes domains in one statement" % item.id)

    def test_an_incompatible_cross_domain_comparison_produces_no_figure(self):
        internal = next(i for i in self.result.items
                        if i.metric == "revenue" and i.origin == S.ORIGIN_SALES)
        external = next(i for i in self.result.items
                        if i.id == self.handles["sourced_id"])
        before = len(self.result)
        comparison = S.compare_values(self.result, internal, external,
                                      subject="revenue against industry size")
        self.assertEqual(comparison["status"], S.INCOMPATIBLE)
        self.assertEqual(len(self.result), before)
        mismatched = set(m["dimension"] for m in comparison["mismatched"])
        self.assertIn("currency", mismatched)
        self.assertIn("geography", mismatched)
        self.assertIn("period", mismatched)

    def test_the_cross_domain_conflict_keeps_both_positions_unaveraged(self):
        internal = next(i for i in self.result.items
                        if i.metric == "revenue" and i.origin == S.ORIGIN_SALES)
        external = next(i for i in self.result.items
                        if i.id == self.handles["sourced_id"])
        S.compare_values(self.result, internal, external, subject="revenue vs size")
        cross = next(c for c in self.result.conflicts
                     if c.kind == S.INTERNAL_EXTERNAL)
        values = [str(v) for v in cross.values()]
        # ADR-0025: the external figure is the same quantity the source published as
        # "310 USD bn", now carried in base units. Both positions still stand apart and
        # neither was averaged, which is what this test exists to assert.
        self.assertEqual(sorted(values), sorted(["1250000", "310000000000"]))
        self.assertIsNone(cross.as_dict().get("resolution"))


class DownstreamReadiness(unittest.TestCase):
    """Matrix 11 - the four consumers can read this without re-deriving the layers."""

    def setUp(self):
        self.result, self.handles = build.build()
        self.record = json.loads(self.result.to_json())

    def test_every_collection_a_consumer_needs_is_exposed(self):
        for key in ("items", "facts", "calculations", "sourced", "interpretations",
                    "assumptions", "recommendations", "evidence", "candidate_claims",
                    "conflicts", "material_findings", "limitations", "confidence",
                    "provenance_index", "summary"):
            self.assertIn(key, self.record, key)

    def test_buckets_hold_ids_not_duplicated_objects(self):
        for key in ("facts", "calculations", "sourced", "interpretations",
                    "material_findings"):
            for entry in self.record[key]:
                self.assertIsInstance(entry, str)
                self.assertTrue(entry.startswith("sy-"))
        ids = set(i["synthesis_id"] for i in self.record["items"])
        for key in ("facts", "calculations", "sourced", "material_findings"):
            self.assertTrue(set(self.record[key]) <= ids)

    def test_a_consumer_can_answer_where_did_this_come_from(self):
        for item in self.result.items:
            chain = self.result.chain(item)
            self.assertTrue(chain)
            for entry in chain:
                self.assertIn("kind", entry)
                if entry["kind"] == S.P_EVIDENCE:
                    self.assertIn("reference", entry)
                    self.assertIn("source_tier", entry)
                    self.assertIn("publication_date", entry)

    def test_confidence_explains_itself_without_prose(self):
        confidence = self.record["confidence"]
        self.assertIn(confidence["confidence"], ("HIGH", "MEDIUM", "LOW"))
        self.assertTrue(confidence["reasons"])
        self.assertEqual(len(confidence["reasons"]), len(confidence["explanations"]))
        for code in confidence["reasons"]:
            self.assertIn(code, S.REASON_TEXT)

    def test_the_summary_reports_the_shape_of_the_answer(self):
        summary = self.record["summary"]
        self.assertEqual(summary["items"], len(self.result))
        self.assertEqual(summary["recommendations"], 0)
        self.assertEqual(summary["unresolved_conflicts"], 1)
        self.assertEqual(sum(summary["support"].values()), len(self.result))


class UpstreamContractsUnchanged(unittest.TestCase):
    """Matrix 73-77 - the synthesis layer added behaviour without editing any of it."""

    def test_evidence_set_semantics_are_untouched(self):
        item = evidence_mod.EvidenceItem(
            source="X", reference="https://x.example.invalid/a", source_tier="C",
            retrieved_at="2026-09-14", publication_date="2026-06-01",
            as_of="2026-09-14")
        self.assertEqual(item.trust, evidence_mod.UNTRUSTED)
        self.assertTrue(item.usable)
        self.assertFalse(item.may_stand_alone)
        evidence = evidence_mod.EvidenceSet()
        evidence.add(item)
        self.assertEqual(evidence.support()["support"], sources_mod.UNSUPPORTED)
        self.assertEqual(evidence.as_dict()["schema_version"], "1.0.0")

    def test_the_claim_ledger_still_enforces_its_own_rules(self):
        with self.assertRaises(evidence_ledger.LedgerError):
            evidence_ledger.Claim("A calculated figure.", evidence_ledger.CALCULATED)
        with self.assertRaises(evidence_ledger.LedgerError):
            evidence_ledger.Claim("A recommendation.", evidence_ledger.RECOMMENDATION)
        with self.assertRaises(evidence_ledger.LedgerError):
            evidence_ledger.Claim("An external claim.", evidence_ledger.EXTERNAL_SOURCED,
                                  source="S", citation="c", source_date="2026-01-01",
                                  source_tier="D")

    def test_materiality_still_has_exactly_three_outcomes(self):
        self.assertEqual(
            sorted([materiality_mod.MATERIAL, materiality_mod.NOT_MATERIAL,
                    materiality_mod.UNDETERMINED]),
            sorted(["material", "not_material", "undetermined"]))

    def test_source_tier_policy_is_unchanged(self):
        self.assertEqual(sources_mod.TIERS, ("A", "B", "C", "D"))
        self.assertEqual(sources_mod.SOLE_SUPPORT_TIERS, ("A", "B"))
        self.assertEqual(sources_mod.EXCLUDED_TIER, "D")
        self.assertFalse(sources_mod.is_usable("D"))

    def test_the_scout_protocol_is_unchanged(self):
        from bops import research
        self.assertEqual(research.RECORD_TOKEN, "BOPS-REC/1")
        self.assertEqual(research.END_TOKEN, "BOPS-END/1")

    def test_synthesis_adds_no_research_intent_and_no_category(self):
        from bops import research
        self.assertEqual(research.CATEGORIES,
                         ("company", "market", "competitor", "industry"))
        self.assertEqual(len(research.INTENT_REGISTRY), len(research.INTENTS))

    def test_the_engine_still_emits_only_facts_and_calculations(self):
        from bops.analytics import contract as analytics_contract
        self.assertEqual(analytics_contract.ENGINE_EMITS, ("FACT", "CALCULATION"))
        analysis = analytics_contract.AnalysisSet("sales")
        with self.assertRaises(analytics_contract.AnalysisError):
            analysis.add(analytics_contract.AnalysisFinding(
                "x", "sales", analytics_contract.INTERPRETATION, "A reading."))

    def test_synthesis_defines_no_tier_or_disclosure_vocabulary_of_its_own(self):
        # It may *map from* M9's tier assessment - that is reuse - but it must not define
        # a tier, a tier list or a disclosure tier, which would be a second policy.
        for name in ("TIER_A", "TIER_B", "TIER_C", "TIER_D", "TIERS", "SOURCE_TIERS",
                     "EXCLUDED_TIER", "USABLE_TIERS", "classify_tier",
                     "DISCLOSURE_TIERS", "TIER_ZERO", "assess_support"):
            self.assertFalse(hasattr(S, name), name)
        for name in dir(S):
            self.assertNotIn("disclosure", name.lower())
        # The one tier-shaped name is a mapping whose keys are M9's own verdicts.
        self.assertEqual(set(S.SUPPORT_FROM_TIER_ASSESSMENT),
                         {sources_mod.SUPPORTED, sources_mod.CORROBORATION_ONLY,
                          sources_mod.UNSUPPORTED})


if __name__ == "__main__":
    unittest.main()
