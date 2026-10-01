"""M10.1 - the synthesis foundation: statements, provenance, boundaries and claims.

Covers matrix sections 1-4 (basic synthesis, provenance, fact boundaries, claims) from the
milestone brief. Conflicts, materiality, confidence, limitations and compatibility are in
`test_m10_1_synthesis_policy`; the forgery and serialisation cases are in
`test_m10_1_synthesis_security`.
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

from bops import materiality as materiality_mod            # noqa: E402
from bops import synthesis as S                            # noqa: E402
from bops.analytics import contract as analytics_contract  # noqa: E402
from bops.research import evidence_set as evidence_mod     # noqa: E402


from fixtures import build_synthesis_fixtures as build      # noqa: E402
from fixtures.build_synthesis_fixtures import (             # noqa: E402
    TEST_DATASET as DATASET, dataset_ref, demo_evidence, evidence_set_with, new_set,
)


class BasicSynthesis(unittest.TestCase):
    """Matrix 1-7."""

    def test_empty_input_produces_an_empty_but_honest_set(self):
        result = S.SynthesisSet()
        self.assertEqual(len(result), 0)
        self.assertEqual(result.items, [])
        self.assertEqual(result.conflicts, [])
        # An empty synthesis is not a confident one.
        self.assertEqual(result.confidence().level, S.LOW)
        self.assertIn(S.confidence.INSUFFICIENT_EVIDENCE, result.confidence().reasons)

    def test_one_internal_fact(self):
        result = new_set()
        item = result.add(S.SynthesisItem(
            S.FACT, S.ORIGIN_SALES, "The dataset covers 2026-Q1.",
            provenance=[dataset_ref()], period="2026-Q1"))
        self.assertEqual(item.kind, S.FACT)
        self.assertEqual(item.domain, S.INTERNAL)
        self.assertEqual(item.evidence_class, 1)
        self.assertEqual(item.support, S.SUPPORTED)
        self.assertEqual(result.summary()["items"], 1)

    def test_one_calculation_must_name_its_basis(self):
        result = new_set()
        item = result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_KPI, "Gross margin was 38.4%.",
            provenance=[dataset_ref()], basis="gross_profit / revenue",
            observed=Decimal("38.4"), unit="percent"))
        self.assertEqual(item.evidence_class, 4)
        self.assertEqual(item.basis, "gross_profit / revenue")
        with self.assertRaises(S.SynthesisError):
            S.SynthesisItem(S.CALCULATION, S.ORIGIN_KPI, "A number.",
                            provenance=[dataset_ref()])

    def test_one_interpretation_rests_on_named_statements(self):
        result = new_set()
        fact = result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_SALES, "Revenue rose 16.8% on the prior quarter.",
            provenance=[dataset_ref()], basis="sum(net_revenue)"))
        reading = S.merge.interpretation(
            result, S.ORIGIN_SALES,
            "The quarter's growth is concentrated in a single product line.",
            supports=[fact.id])
        self.assertEqual(reading.kind, S.INTERPRETATION)
        self.assertEqual(reading.evidence_class, 5)
        self.assertIn(dataset_ref(), reading.provenance)

    def test_interpretation_of_nothing_is_refused(self):
        result = new_set()
        with self.assertRaises(S.SynthesisError):
            S.merge.interpretation(result, S.ORIGIN_SALES, "Things look good.",
                                   supports=[])

    def test_interpretation_citing_an_unknown_statement_is_refused(self):
        result = new_set()
        with self.assertRaises(S.SynthesisError) as caught:
            S.merge.interpretation(result, S.ORIGIN_SALES, "A reading.",
                                   supports=["sy-000000000000"])
        self.assertIn("not a statement in this set", str(caught.exception))

    def test_multiple_internal_domains_stay_separable(self):
        result, _handles = build.build(include_external=False)
        origins = set(item.origin for item in result.items)
        self.assertEqual(
            origins,
            {S.ORIGIN_SALES, S.ORIGIN_FINANCIAL, S.ORIGIN_PRODUCT, S.ORIGIN_CUSTOMER,
             S.ORIGIN_FORECAST, S.ORIGIN_ANOMALY})
        self.assertEqual(result.summary()["by_domain"], {"internal": 7})

    def test_external_evidence_registers_without_creating_statements(self):
        result = new_set()
        evidence = evidence_set_with(demo_evidence())
        ids = S.register_external(result, evidence, S.ORIGIN_INDUSTRY)
        self.assertEqual(len(ids), 1)
        # Registration makes evidence citable. It asserts nothing on its own.
        self.assertEqual(len(result), 0)
        self.assertEqual(result.summary()["evidence_items"], 1)

    def test_mixed_internal_and_external_coexist_without_merging(self):
        result, _handles = build.build()
        self.assertEqual(result.summary()["by_domain"], {"external": 2, "internal": 7})
        for item in result.items:
            if item.domain == S.EXTERNAL:
                self.assertEqual(item.trust, S.UNTRUSTED)
            else:
                self.assertEqual(item.trust, "internal")


class Provenance(unittest.TestCase):
    """Matrix 8-13."""

    def test_internal_provenance_is_preserved_through_the_merge(self):
        result, handles = build.build(include_external=False)
        revenue = next(i for i in result.items if i.metric == "revenue"
                       and i.origin == S.ORIGIN_SALES)
        kinds = set(ref.kind for ref in revenue.provenance)
        self.assertIn(S.P_FINDING, kinds)
        self.assertIn(S.P_DATASET, kinds)
        chain = result.chain(revenue)
        self.assertTrue(all(entry["resolved"] for entry in chain))

    def test_evidence_ids_are_preserved_on_sourced_statements(self):
        result, handles = build.build()
        sourced = next(i for i in result.items if i.id == handles["sourced_id"])
        refs = [ref.ref_id for ref in sourced.external_refs()]
        self.assertEqual(refs, [handles["evidence"]["narrow"]])
        chain = result.chain(sourced)
        self.assertEqual(chain[0]["source_tier"], "C")
        self.assertEqual(chain[0]["trust"], S.UNTRUSTED)

    def test_claim_ids_are_preserved_and_resolvable(self):
        result, handles = build.build()
        claim_id = handles["claim_ids"][0]
        item = result.add(S.SynthesisItem(
            S.SOURCED, S.ORIGIN_INDUSTRY,
            "A candidate reading of the narrow-scope source is on record.",
            provenance=[S.ProvenanceRef(S.P_CLAIM, claim_id)]))
        chain = result.chain(item)
        self.assertTrue(chain[0]["resolved"])
        self.assertEqual(chain[0]["status"], "candidate")
        self.assertFalse(chain[0]["verified"])

    def test_missing_provenance_is_stated_not_omitted(self):
        result = new_set()
        with self.assertRaises(S.SynthesisError) as caught:
            S.SynthesisItem(S.FACT, S.ORIGIN_SALES, "Something happened.")
        self.assertIn("must carry provenance", str(caught.exception))

        stated = result.add(S.SynthesisItem(
            S.ASSUMPTION, S.ORIGIN_FORECAST,
            "Seasonality is assumed flat across the horizon.",
            provenance=[S.ProvenanceRef.unavailable(
                "No seasonal history is available for this dataset.")]))
        self.assertEqual(stated.support, S.INSUFFICIENT_EVIDENCE)
        self.assertFalse(stated.has_provenance())

    def test_unavailable_provenance_must_say_why(self):
        with self.assertRaises(S.SynthesisError):
            S.ProvenanceRef(S.P_UNAVAILABLE)

    def test_forged_provenance_is_rejected(self):
        result = new_set()
        with self.assertRaises(S.SynthesisError) as caught:
            result.add(S.SynthesisItem(
                S.SOURCED, S.ORIGIN_MARKET, "A source said something.",
                provenance=[S.ProvenanceRef(S.P_EVIDENCE, "ev-deadbeefcafe")]))
        self.assertIn("references no registered source object", str(caught.exception))

    def test_a_reference_with_no_id_is_rejected(self):
        for kind in (S.P_EVIDENCE, S.P_FINDING, S.P_KPI, S.P_DATASET):
            with self.assertRaises(S.SynthesisError):
                S.ProvenanceRef(kind)

    def test_provenance_must_be_ref_objects_not_bare_strings(self):
        with self.assertRaises(S.SynthesisError):
            S.SynthesisItem(S.FACT, S.ORIGIN_SALES, "A fact.",
                            provenance=["ev-1234"])

    def test_provenance_survives_serialisation_and_reload(self):
        result, _handles = build.build()
        record = result.as_dict()
        reloaded = S.load(record)
        self.assertEqual(len(reloaded), len(result))
        for original, restored in zip(result.items, reloaded):
            self.assertEqual(original.id, restored.id)
            self.assertEqual([r.as_dict() for r in original.provenance],
                             [r.as_dict() for r in restored.provenance])
            self.assertEqual(original.support, restored.support)
            self.assertEqual(original.confidence, restored.confidence)


class FactBoundaries(unittest.TestCase):
    """Matrix 14-18."""

    def test_a_fact_stays_a_fact(self):
        result = new_set()
        item = result.add(S.SynthesisItem(
            S.FACT, S.ORIGIN_SALES, "The file contains 4,120 orders.",
            provenance=[dataset_ref()]))
        self.assertEqual(item.kind, S.FACT)
        self.assertEqual(item.evidence_class, 1)
        self.assertEqual(result.as_dict()["facts"], [item.id])
        self.assertEqual(result.as_dict()["interpretations"], [])

    def test_a_calculation_stays_a_calculation(self):
        result = new_set()
        item = result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_KPI, "Revenue totalled 1,250,000 GBP.",
            provenance=[dataset_ref()], basis="sum(net_revenue)"))
        self.assertEqual(result.as_dict()["calculations"], [item.id])
        self.assertEqual(result.as_dict()["facts"], [])

    def test_an_interpretation_stays_an_interpretation(self):
        result = new_set()
        base = result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_SALES, "Revenue rose 16.8%.",
            provenance=[dataset_ref()], basis="sum(net_revenue)"))
        reading = S.merge.interpretation(
            result, S.ORIGIN_SALES, "The rise is concentrated in one quarter.",
            supports=[base.id])
        self.assertEqual(result.as_dict()["interpretations"], [reading.id])
        self.assertEqual(reading.evidence_class, 5)
        self.assertFalse(reading.is_evidential is False and reading.kind == S.FACT)

    def test_a_recommendation_cannot_be_introduced(self):
        with self.assertRaises(S.SynthesisError) as caught:
            S.SynthesisItem(S.RECOMMENDATION, S.ORIGIN_SALES, "Do the thing.",
                            provenance=[dataset_ref()])
        self.assertIn("reserved for a downstream milestone", str(caught.exception))
        self.assertNotIn(S.RECOMMENDATION, S.SYNTHESIS_EMITS)

    def test_external_content_cannot_become_an_internal_fact(self):
        # There is no kind for it to become: FACT and CALCULATION are internal-only.
        for kind in (S.FACT, S.CALCULATION):
            with self.assertRaises(S.SynthesisError) as caught:
                S.SynthesisItem(kind, S.ORIGIN_INDUSTRY, "The industry is worth 310bn.",
                                provenance=[S.ProvenanceRef(S.P_EVIDENCE, "ev-x")],
                                basis="quoted")
            self.assertIn("external statement may not be", str(caught.exception))

    def test_internal_data_cannot_borrow_the_sourced_label(self):
        with self.assertRaises(S.SynthesisError) as caught:
            S.SynthesisItem(S.SOURCED, S.ORIGIN_SALES, "Our revenue was 1.25m.",
                            provenance=[dataset_ref()])
        self.assertIn("internal statement may not be", str(caught.exception))

    def test_sourced_carries_evidence_class_three(self):
        result, handles = build.build()
        sourced = next(i for i in result.items if i.id == handles["sourced_id"])
        self.assertEqual(sourced.kind, S.SOURCED)
        self.assertEqual(sourced.evidence_class, 3)

    def test_a_sourced_statement_must_cite_something(self):
        result = new_set()
        with self.assertRaises(S.SynthesisError) as caught:
            S.sourced_statement(result, S.ORIGIN_MARKET, "The market is large.")
        self.assertIn("must cite at least one", str(caught.exception))


class Claims(unittest.TestCase):
    """Matrix 19-23."""

    def test_a_candidate_claim_stays_candidate(self):
        result, _handles = build.build()
        for claim in result.candidate_claims:
            self.assertEqual(claim["status"], "candidate")
            self.assertIs(claim["verified"], False)

    def test_nothing_promotes_a_candidate(self):
        result, handles = build.build()
        claim_id = handles["claim_ids"][0]
        result.add(S.SynthesisItem(
            S.SOURCED, S.ORIGIN_INDUSTRY, "The candidate reading is cited here.",
            provenance=[S.ProvenanceRef(S.P_CLAIM, claim_id)]))
        record = result.as_dict()
        self.assertTrue(all(c["verified"] is False for c in record["candidate_claims"]))
        self.assertTrue(all(c["status"] == "candidate"
                            for c in record["candidate_claims"]))

    def test_verified_true_is_refused_not_downgraded(self):
        result = new_set()
        with self.assertRaises(S.SynthesisError) as caught:
            result.register_claims([{"statement": "x", "evidence_id": "ev-1",
                                     "verified": True}])
        self.assertIn("No verification path exists", str(caught.exception))

    def test_a_non_candidate_status_is_refused(self):
        result = new_set()
        with self.assertRaises(S.SynthesisError) as caught:
            result.register_claims([{"statement": "x", "status": "confirmed"}])
        self.assertIn("nothing in synthesis promotes it", str(caught.exception))

    def test_an_unsupported_statement_is_identified_as_such(self):
        result = new_set()
        evidence = evidence_set_with(demo_evidence(tier="C"))
        S.register_external(result, evidence, S.ORIGIN_MARKET)
        item = S.sourced_statement(
            result, S.ORIGIN_MARKET, "A tier C source states the market grew.",
            evidence_ids=[evidence.items[0].id],
            materiality={"outcome": materiality_mod.MATERIAL,
                         "reason": "Above the configured threshold."})
        # Material + tier C only == unsupported, per the existing source policy.
        self.assertEqual(item.support, S.UNSUPPORTED)
        self.assertIn(S.confidence.UNSUPPORTED_STATEMENT,
                      item.confidence_detail["reasons"])
        self.assertEqual(item.confidence, S.LOW)

    def test_insufficient_evidence_is_distinct_from_unsupported(self):
        result = new_set()
        item = result.add(S.SynthesisItem(
            S.ASSUMPTION, S.ORIGIN_FORECAST, "A flat seasonal profile is assumed.",
            provenance=[S.ProvenanceRef.unavailable("No seasonal history exists.")]))
        self.assertEqual(item.support, S.INSUFFICIENT_EVIDENCE)
        self.assertNotEqual(item.support, S.UNSUPPORTED)
        self.assertIn(S.confidence.INSUFFICIENT_EVIDENCE,
                      item.confidence_detail["reasons"])

    def test_tier_d_evidence_supports_nothing(self):
        result = new_set()
        item = evidence_mod.EvidenceItem(
            source="Content Farm", reference="https://contentfarm.example.invalid/x",
            source_tier="D", retrieved_at="2026-09-14",
            publication_date="2026-06-01", as_of="2026-09-14")
        evidence = evidence_set_with(item)
        S.register_external(result, evidence, S.ORIGIN_MARKET)
        self.assertFalse(item.usable)
        statement = S.sourced_statement(
            result, S.ORIGIN_MARKET, "An excluded source says something.",
            evidence_ids=[item.id])
        self.assertEqual(statement.support, S.UNSUPPORTED)


class SupportMapping(unittest.TestCase):
    """The four-state support view is a view of the one M9 policy, not a second one."""

    def test_mapping_covers_every_m9_verdict(self):
        from bops.research import sources as sources_mod
        for verdict in (sources_mod.SUPPORTED, sources_mod.CORROBORATION_ONLY,
                        sources_mod.UNSUPPORTED):
            self.assertIn(verdict, S.SUPPORT_FROM_TIER_ASSESSMENT)
            self.assertIn(S.SUPPORT_FROM_TIER_ASSESSMENT[verdict], S.SUPPORT_STATES)

    def test_a_tier_a_source_supports_a_material_statement(self):
        result = new_set()
        item = demo_evidence(tier="A", host="ons.gov.uk", source="DEMO Statistics")
        evidence = evidence_set_with(item)
        S.register_external(result, evidence, S.ORIGIN_INDUSTRY)
        statement = S.sourced_statement(
            result, S.ORIGIN_INDUSTRY, "An official source states the figure.",
            evidence_ids=[item.id],
            materiality={"outcome": materiality_mod.MATERIAL, "reason": "Material."})
        self.assertEqual(statement.support, S.SUPPORTED)

    def test_two_legs_take_the_weaker(self):
        result = new_set()
        weak = demo_evidence(tier="C")
        evidence = evidence_set_with(weak)
        S.register_external(result, evidence, S.ORIGIN_INDUSTRY)
        item = result.add(S.SynthesisItem(
            S.INTERPRETATION, S.ORIGIN_INDUSTRY,
            "Internal performance reads differently against the external picture.",
            provenance=[dataset_ref(), S.ProvenanceRef(S.P_EVIDENCE, weak.id)],
            materiality={"outcome": materiality_mod.MATERIAL, "reason": "Material."}))
        # Internal leg alone would be `supported`; the external leg is not.
        self.assertEqual(item.support, S.UNSUPPORTED)
        self.assertEqual(item.support_detail["internal"]["support"], S.SUPPORTED)
        self.assertEqual(item.support_detail["external"]["support"], S.UNSUPPORTED)


if __name__ == "__main__":
    unittest.main()
