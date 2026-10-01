"""Functional coverage of the M9-A research core.

The invariant suite proves the boundary holds. This one proves the parts do their jobs:
requests validate, queries build deterministically, freshness and support are computed to
the policy's numbers, conflicts survive intact, and every failure comes back as a structured
value rather than an exception or a guess.
"""

import json
import unittest
from decimal import Decimal

from bops import research as R
from bops.privacy import aggregation as agg, classes as pc
from bops.research import contract as contract_mod, gate as gate_mod
from bops.research import query as query_mod, sources as sources_mod

D = Decimal
RETRIEVED = "2026-03-01"


def item(tier="A", published="2026-02-01", kind=sources_mod.FINANCIALS, source="ONS",
         reference="https://ons.gov.uk/x", content=None, as_of=RETRIEVED):
    return R.EvidenceItem(source=source, reference=reference, source_tier=tier,
                          retrieved_at=RETRIEVED, publication_date=published,
                          claim_kind=kind, content=content, as_of=as_of)


# ==========================================================================
# A. Request contract
# ==========================================================================

class TestResearchRequest(unittest.TestCase):

    def test_a_well_formed_request_validates(self):
        request = R.ResearchRequest("churn", R.INDUSTRY,
                                    public_terms={"industry": "logistics"})
        self.assertEqual(request.validate(), [])
        self.assertTrue(request.valid)

    def test_all_four_categories_are_supported(self):
        for category in R.CATEGORIES:
            self.assertTrue(R.ResearchRequest("x", category).valid, category)

    def test_an_unsupported_category_is_named(self):
        problems = dict(R.ResearchRequest("x", "astrology").validate())
        self.assertIn(contract_mod.REASON_UNSUPPORTED_CATEGORY, problems)

    def test_an_empty_subject_is_refused(self):
        problems = dict(R.ResearchRequest("   ", R.MARKET).validate())
        self.assertIn(contract_mod.REASON_AMBIGUOUS_SUBJECT, problems)

    def test_an_unrecognised_intent_is_refused(self):
        problems = dict(R.ResearchRequest("x", R.MARKET, intent="vibes").validate())
        self.assertIn(contract_mod.REASON_AMBIGUOUS_SUBJECT, problems)

    def test_narrowing_attributes_come_from_the_terms_actually_sent(self):
        request = R.ResearchRequest("x", R.MARKET, public_terms={
            "industry": "logistics", "region": "South", "period": "2026"})
        self.assertEqual(request.narrowing_attributes(), ("industry", "region"))

    def test_sensitivity_is_public_when_nothing_is_derived(self):
        self.assertEqual(R.ResearchRequest("x", R.MARKET).sensitivity(), pc.PUBLIC)

    def test_sensitivity_inherits_the_strictest_derived_value(self):
        request = R.ResearchRequest("x", R.MARKET, derived_context=[
            agg.AggregateDescriptor("a", 1, agg.RATE, 40,
                                    source_sensitivity=pc.DERIVED_SAFE),
            agg.AggregateDescriptor("b", 1, agg.RATE, 40,
                                    source_sensitivity=pc.RESTRICTED)])
        self.assertEqual(request.sensitivity(), pc.RESTRICTED)

    def test_the_request_serialises(self):
        json.dumps(R.ResearchRequest("x", R.MARKET,
                                     public_terms={"industry": "y"}).as_dict())


# ==========================================================================
# B. Query construction
# ==========================================================================

class TestQueryConstruction(unittest.TestCase):

    def request(self, **kwargs):
        fields = {"subject": "churn rate", "category": R.INDUSTRY,
                  "public_terms": {"business_model": "B2B SaaS", "period": "2026"}}
        fields.update(kwargs)
        return R.ResearchRequest(**fields)

    def test_a_benchmark_query_reads_naturally(self):
        self.assertEqual(R.build(self.request()).text,
                         "B2B SaaS 2026 churn rate benchmark")

    def test_construction_is_deterministic(self):
        first, second = R.build(self.request()), R.build(self.request())
        self.assertEqual(first.text, second.text)

    def test_term_order_does_not_depend_on_dict_order(self):
        a = R.build(self.request(public_terms={"business_model": "B2B SaaS",
                                               "period": "2026"}))
        b = R.build(self.request(public_terms={"period": "2026",
                                               "business_model": "B2B SaaS"}))
        self.assertEqual(a.text, b.text)

    def test_the_subject_leads_for_entity_research(self):
        text = R.build(self.request(subject="Acme Corp", category=R.COMPETITOR,
                                    intent=R.PROFILE, public_terms={})).text
        self.assertTrue(text.startswith("Acme Corp"), text)

    def test_the_intent_word_is_not_duplicated(self):
        text = R.build(self.request(subject="market trends", intent=R.TRENDS,
                                    public_terms={})).text
        self.assertEqual(text, "market trends")

    def test_an_empty_term_is_dropped(self):
        text = R.build(self.request(public_terms={"industry": "", "period": "2026"})).text
        self.assertNotIn("  ", text)

    def test_a_candidate_query_is_not_a_string(self):
        """So it cannot be mistaken for something retrieval will accept."""
        self.assertNotIsInstance(R.build(self.request()), str)

    def test_the_tier_zero_alternative_drops_derived_context(self):
        request = self.request(derived_context=[
            agg.rate_descriptor("churn", 8, 100, entity_count=40)], requested_tier=1)
        alternative = R.tier_zero_alternative(request)
        self.assertEqual(alternative["tier"], 0)
        self.assertNotIn("8.0", alternative["text"])

    def test_safe_public_terms_strips_prohibited_keys(self):
        safe = query_mod.safe_public_terms(
            {"industry": "logistics", "api_key": "sk-live-x", "rows": "1,2"})
        self.assertEqual(safe, {"industry": "logistics"})


# ==========================================================================
# C. Source tiers
# ==========================================================================

class TestSourceTiers(unittest.TestCase):

    def test_the_four_tiers_are_defined_with_uses(self):
        for tier in sources_mod.TIERS:
            self.assertTrue(sources_mod.TIER_USE[tier])
            self.assertTrue(sources_mod.TIER_DESCRIPTION[tier])

    def test_tiers_a_and_b_may_stand_alone(self):
        for tier in ("A", "B"):
            self.assertTrue(sources_mod.may_stand_alone(tier))

    def test_tier_c_may_not_stand_alone(self):
        self.assertTrue(sources_mod.is_usable("C"))
        self.assertFalse(sources_mod.may_stand_alone("C"))

    def test_tier_d_is_not_usable(self):
        self.assertFalse(sources_mod.is_usable("D"))

    def test_tiers_are_case_insensitive_but_validated(self):
        self.assertEqual(sources_mod.normalise_tier("a"), "A")
        with self.assertRaises(sources_mod.SourceTierError):
            sources_mod.normalise_tier("Z")

    def test_support_with_no_source_is_unsupported(self):
        self.assertEqual(sources_mod.assess_support([])["support"],
                         sources_mod.UNSUPPORTED)

    def test_support_naming_tier_d_explains_the_exclusion(self):
        result = sources_mod.assess_support(["D"])
        self.assertEqual(result["support"], sources_mod.UNSUPPORTED)
        self.assertIn("excluded", result["reason"])

    def test_the_research_layer_and_ledger_agree_on_usable_tiers(self):
        from bops import evidence as evidence_mod
        self.assertEqual(tuple(sources_mod.USABLE_TIERS),
                         tuple(evidence_mod.SOURCE_TIERS))


# ==========================================================================
# D. Staleness
# ==========================================================================

class TestStaleness(unittest.TestCase):

    def test_the_three_windows_match_the_policy(self):
        self.assertEqual(sources_mod.STALENESS_DAYS[sources_mod.FINANCIALS], 365)
        self.assertEqual(sources_mod.STALENESS_DAYS[sources_mod.MARKET_SIZING], 730)
        self.assertEqual(sources_mod.STALENESS_DAYS[sources_mod.POSITIONING], 545)

    def test_a_recent_financial_source_is_current(self):
        result = sources_mod.assess_freshness("2026-01-01", sources_mod.FINANCIALS,
                                              as_of="2026-03-01")
        self.assertEqual(result["freshness"], sources_mod.CURRENT)

    def test_a_financial_source_beyond_a_year_is_dated(self):
        result = sources_mod.assess_freshness("2024-01-01", sources_mod.FINANCIALS,
                                              as_of="2026-03-01")
        self.assertEqual(result["freshness"], sources_mod.DATED)
        self.assertIn("must not be presented as current", result["statement"])

    def test_the_boundary_day_is_still_current(self):
        result = sources_mod.assess_freshness("2025-03-01", sources_mod.FINANCIALS,
                                              as_of="2026-03-01")
        self.assertEqual(result["age_days"], 365)
        self.assertEqual(result["freshness"], sources_mod.CURRENT)

    def test_market_sizing_gets_a_longer_window(self):
        for kind, expected in ((sources_mod.FINANCIALS, sources_mod.DATED),
                               (sources_mod.MARKET_SIZING, sources_mod.CURRENT)):
            self.assertEqual(
                sources_mod.assess_freshness("2024-06-01", kind,
                                             as_of="2026-03-01")["freshness"],
                expected, kind)

    def test_an_undated_source_is_undated_not_current(self):
        result = sources_mod.assess_freshness(None, as_of="2026-03-01")
        self.assertEqual(result["freshness"], sources_mod.UNDATED)

    def test_an_unknown_claim_kind_uses_the_shortest_window(self):
        self.assertEqual(sources_mod.staleness_window("something-else"), 365)

    def test_staleness_is_deterministic_given_a_reference_date(self):
        args = ("2024-01-01", sources_mod.FINANCIALS, "2026-03-01")
        self.assertEqual(sources_mod.assess_freshness(*args),
                         sources_mod.assess_freshness(*args))

    def test_a_stale_item_is_kept_not_discarded(self):
        evidence = R.EvidenceSet()
        evidence.add(item(published="2020-01-01"))
        self.assertEqual(len(evidence), 1)
        self.assertEqual(len(evidence.stale()), 1)
        self.assertEqual(len(evidence.current()), 0)


# ==========================================================================
# E. Conflicts
# ==========================================================================

class TestConflicts(unittest.TestCase):

    def position(self, value, source, tier="A", **kwargs):
        return sources_mod.SourcePosition(
            evidence_id="ev-%s" % source, value=value, source=source,
            source_tier=tier, **kwargs)

    def test_a_single_source_is_not_a_conflict(self):
        result = sources_mod.assess_conflict([self.position(100, "ONS")])
        self.assertEqual(result["status"], sources_mod.SINGLE)

    def test_close_figures_agree(self):
        result = sources_mod.assess_conflict(
            [self.position(100, "ONS"), self.position(110, "IMF")])
        self.assertEqual(result["status"], sources_mod.AGREES)

    def test_divergent_figures_conflict(self):
        result = sources_mod.assess_conflict(
            [self.position(100, "ONS"), self.position(400, "Vendor", tier="C")])
        self.assertEqual(result["status"], sources_mod.CONFLICTS)
        self.assertEqual(result["confidence_effect"], "lowered")

    def test_a_conflict_keeps_every_position_intact(self):
        result = sources_mod.assess_conflict(
            [self.position(100, "ONS"), self.position(400, "Vendor", tier="C")])
        self.assertEqual(len(result["positions"]), 2)
        self.assertEqual({p["source"] for p in result["positions"]}, {"ONS", "Vendor"})

    def test_a_conflict_is_never_averaged(self):
        result = sources_mod.assess_conflict(
            [self.position(100, "A"), self.position(400, "B")])
        values = {p["value"] for p in result["positions"]}
        self.assertEqual(values, {100, 400})
        self.assertNotIn(250, values)

    def test_differing_definitions_are_offered_as_the_likely_reason(self):
        result = sources_mod.assess_conflict([
            self.position(100, "ONS", definition="revenue only"),
            self.position(400, "IMF", definition="revenue plus services")])
        self.assertIn("different definitions", result["likely_reason"])

    def test_no_reason_is_invented_when_the_positions_show_none(self):
        result = sources_mod.assess_conflict(
            [self.position(100, "A"), self.position(400, "B")])
        self.assertIsNone(result["likely_reason"])

    def test_a_conflict_survives_in_the_evidence_set(self):
        evidence = R.EvidenceSet(operation="op")
        evidence.record_conflict("market size", [
            self.position(100, "ONS"), self.position(400, "Vendor", tier="C")])
        self.assertTrue(evidence.has_conflict())
        self.assertIn("market size", json.dumps(evidence.as_dict()))


# ==========================================================================
# F. Evidence set
# ==========================================================================

class TestEvidenceSet(unittest.TestCase):

    def test_evidence_requires_a_source(self):
        with self.assertRaises(R.EvidenceError):
            R.EvidenceItem(source="", reference="https://x", source_tier="A",
                           retrieved_at=RETRIEVED)

    def test_evidence_requires_a_citation(self):
        with self.assertRaises(R.EvidenceError):
            R.EvidenceItem(source="ONS", reference="", source_tier="A",
                           retrieved_at=RETRIEVED)

    def test_evidence_requires_a_retrieval_timestamp(self):
        with self.assertRaises(R.EvidenceError):
            R.EvidenceItem(source="ONS", reference="https://x", source_tier="A",
                           retrieved_at=None)

    def test_evidence_requires_a_tier(self):
        with self.assertRaises(sources_mod.SourceTierError):
            R.EvidenceItem(source="ONS", reference="https://x", source_tier=None,
                           retrieved_at=RETRIEVED)

    def test_the_identifier_is_deterministic(self):
        self.assertEqual(item().id, item().id)

    def test_different_sources_get_different_identifiers(self):
        self.assertNotEqual(item(source="ONS").id, item(source="IMF").id)

    def test_only_evidence_items_may_enter_a_set(self):
        with self.assertRaises(R.EvidenceError):
            R.EvidenceSet().add({"source": "ONS"})

    def test_the_set_reports_its_own_coverage(self):
        evidence = R.EvidenceSet()
        evidence.add(item(tier="A"))
        evidence.add(item(tier="D", source="farm", reference="https://farm"))
        evidence.add(item(tier="C", source="blog", reference="https://blog",
                          published="2019-01-01"))
        summary = evidence.summary()
        self.assertEqual(summary["items"], 3)
        self.assertEqual(summary["usable"], 2)
        self.assertEqual(summary["excluded"], 1)

    def test_support_is_computed_from_usable_tiers_only(self):
        evidence = R.EvidenceSet()
        evidence.add(item(tier="D", source="farm", reference="https://farm"))
        evidence.add(item(tier="C", source="blog", reference="https://blog"))
        self.assertEqual(evidence.support(material=True)["support"],
                         sources_mod.UNSUPPORTED)

    def test_the_set_serialises(self):
        evidence = R.EvidenceSet(operation="op", subject="x", category=R.MARKET)
        evidence.add(item())
        json.dumps(evidence.as_dict())
        json.dumps(evidence.as_instruction_safe_dict())


# ==========================================================================
# G. Failure contracts
# ==========================================================================

class TestFailureContracts(unittest.TestCase):

    def test_every_failure_carries_status_reason_and_explanation(self):
        failure = R.failure(R.UNAVAILABLE, contract_mod.REASON_RETRIEVAL_UNAVAILABLE,
                            "No retrieval backend is available.")
        self.assertEqual(failure.status, R.UNAVAILABLE)
        self.assertTrue(failure.reason)
        self.assertTrue(failure.explanation)
        self.assertFalse(failure.ok)

    def test_a_failure_states_whether_an_alternative_exists(self):
        without = R.failure(R.UNAVAILABLE, "x", "y")
        with_alt = R.failure(R.BLOCKED, "x", "y", alternative={"text": "safe query"})
        self.assertFalse(without.has_alternative)
        self.assertTrue(with_alt.has_alternative)

    def test_an_unknown_status_is_a_defect(self):
        with self.assertRaises(R.ResearchError):
            R.ResearchFailure("probably_fine", "x", "y")

    def test_every_declared_status_is_constructible(self):
        for status in R.STATUSES:
            self.assertTrue(R.ResearchFailure(status, "code", "text"))

    def test_a_failure_serialises(self):
        json.dumps(R.failure(R.BLOCKED, "x", "y", alternative={"t": 1}).as_dict())

    def test_retrieval_unavailable_is_a_value_not_an_exception(self):
        decision = R.assess(R.ResearchRequest("x", R.MARKET,
                                              public_terms={"industry": "y"}))
        result = R.NullRetriever().retrieve(R.RetrievalRequest(decision))
        self.assertIsInstance(result, R.ResearchFailure)
        self.assertEqual(result.status, R.UNAVAILABLE)


# ==========================================================================
# H. Ledger integration and determinism
# ==========================================================================

class TestLedgerAndDeterminism(unittest.TestCase):

    def test_the_gate_produces_a_ledger_entry(self):
        decision = R.assess(R.ResearchRequest("x", R.MARKET,
                                              public_terms={"industry": "y"}))
        entry = R.ledger_entry(decision)
        self.assertEqual(entry["kind"], "disclosure_decision")
        self.assertEqual(entry["decision"], R.ALLOW)
        self.assertEqual(entry["transmitted_text"], decision.query_text)

    def test_a_refusal_is_ledgered_without_a_transmitted_text(self):
        decision = R.assess(R.ResearchRequest(
            "x", R.MARKET, public_terms={"api_key": "sk-live-x"}))
        entry = R.ledger_entry(decision)
        self.assertEqual(entry["decision"], R.REFUSE)
        self.assertIsNone(entry["transmitted_text"])

    def test_an_unapproved_tier_two_ledgers_no_transmitted_text(self):
        descriptor = agg.AggregateDescriptor("x", D("1"), agg.RATE, 40,
                                             source_sensitivity=pc.INTERNAL)
        decision = R.assess(R.ResearchRequest(
            "x", R.MARKET, derived_context=[descriptor], requested_tier=2))
        entry = R.ledger_entry(decision)
        self.assertEqual(entry["decision"], R.ALLOW_WITH_APPROVAL)
        self.assertIsNone(entry["transmitted_text"])
        self.assertIsNotNone(entry["proposed_text"])

    def test_the_decision_serialises(self):
        decision = R.assess(R.ResearchRequest("x", R.MARKET,
                                              public_terms={"industry": "y"}))
        json.dumps(decision.as_dict())

    def test_repeated_assessment_is_identical(self):
        def run():
            request = R.ResearchRequest("churn", R.INDUSTRY,
                                        public_terms={"business_model": "B2B SaaS"})
            return json.dumps(R.assess(request).as_dict(), sort_keys=True)
        self.assertEqual(run(), run())

    def test_the_evidence_set_round_trips_through_json(self):
        evidence = R.EvidenceSet(operation="op")
        evidence.add(item(content="some retrieved text"))
        restored = json.loads(json.dumps(evidence.as_dict()))
        self.assertEqual(restored["trust"], R.UNTRUSTED)
        self.assertEqual(restored["items"][0]["source_tier"], "A")


if __name__ == "__main__":
    unittest.main()
