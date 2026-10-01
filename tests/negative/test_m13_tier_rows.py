"""M13.1 deterministic gap closure for the M9 tier-test rows (ADR-0039 sections B and C.4).

Coverage-matrix row **S6-02** - "Tier 3 refused; small-denominator blocked; re-identifying
combo blocked". Tier 3 and the small-denominator floor were already pinned at the gate
(`unit.test_m9a_invariants`). The re-identification check was pinned only as an engine
primitive (`unit.test_engine_m3.TestAggregationPrimitives`) and across a sequence of queries
(`TestInvariant13_CrossQueryNarrowing`); no test asserted that the **disclosure gate itself**
blocks one query whose own attribute combination re-identifies. These tests do, through
`research.assess`, on synthetic terms only.

"Blocked" means what the disclosure model says it means: a re-identifying combination can
never pass Tier 1 (which requires a clean whole-query re-identification check), and at Tier 2
it is only a request for the user's per-query approval of the verbatim text - never
authorised by itself. This is the deterministic half; whether a session shows no approval
prompt for the Tier-0 questions is behavioural (S3-07, M13.2).

No network, no retrieval, no model: `assess` constructs and judges the query locally.
"""

import unittest
from decimal import Decimal

from bops import research as R
from bops.privacy import aggregation as agg, classes as pc
from bops.research import contract as contract_mod

#: Two highly narrowing attributes plus an industry: close to naming one firm.
TWO_HIGHLY_NARROWING = {"industry": "synthetic-industry", "revenue_band": "band-a",
                        "employee_band": "band-b"}
#: Four ordinary narrowing attributes: over the whole-query limit of three.
FOUR_NARROWING = {"industry": "synthetic-industry", "region": "synthetic-region",
                  "size_band": "band-c", "product_category": "synthetic-category"}
#: One narrowing attribute: within the limit, so the same request otherwise passes.
SAFE_TERMS = {"business_model": "B2B SaaS"}


def _derived_safe_rate():
    """A derived-safe rate over 40 entities: passes every Tier-1 check on its own."""
    return agg.AggregateDescriptor("churn rate", Decimal("8.0"), agg.RATE, 40,
                                   source_sensitivity=pc.DERIVED_SAFE)


def _request(public_terms, requested_tier):
    return R.ResearchRequest(subject="churn", category=R.INDUSTRY, public_terms=public_terms,
                             derived_context=[_derived_safe_rate()],
                             requested_tier=requested_tier)


class ReidentifyingCombinationAtTheGate(unittest.TestCase):

    def test_the_control_request_passes_tier_one(self):
        decision = R.assess(_request(SAFE_TERMS, 1))
        self.assertEqual(decision.decision, R.ALLOW)

    def test_two_highly_narrowing_attributes_are_refused_at_tier_one(self):
        decision = R.assess(_request(TWO_HIGHLY_NARROWING, 1))
        self.assertEqual(decision.decision, R.REFUSE)
        self.assertIn(contract_mod.REASON_REIDENTIFICATION, decision.failed_checks)

    def test_too_many_narrowing_attributes_are_refused_at_tier_one(self):
        decision = R.assess(_request(FOUR_NARROWING, 1))
        self.assertEqual(decision.decision, R.REFUSE)
        self.assertIn(contract_mod.REASON_REIDENTIFICATION, decision.failed_checks)

    def test_at_tier_two_a_reidentifying_query_is_never_authorised_by_itself(self):
        for terms in (TWO_HIGHLY_NARROWING, FOUR_NARROWING):
            with self.subTest(terms=sorted(terms)):
                decision = R.assess(_request(terms, 2))
                self.assertEqual(decision.decision, R.ALLOW_WITH_APPROVAL)
                self.assertIn(contract_mod.REASON_REIDENTIFICATION, decision.failed_checks)
                self.assertFalse(decision.authorised)

    def test_a_refused_query_offers_no_query_text_to_send(self):
        decision = R.assess(_request(TWO_HIGHLY_NARROWING, 1))
        self.assertTrue(decision.refused)
        self.assertFalse(decision.authorised)

    def test_the_decision_is_deterministic(self):
        first = R.assess(_request(TWO_HIGHLY_NARROWING, 1)).as_dict()
        second = R.assess(_request(TWO_HIGHLY_NARROWING, 1)).as_dict()
        first.pop("operation", None)
        second.pop("operation", None)
        self.assertEqual(first, second)
