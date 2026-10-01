"""Optional live smoke test for scout retrieval. Skipped unless explicitly enabled.

The deterministic suite must never depend on the internet: a test that fails because a
website changed is a test that teaches the team to ignore failures. So everything in the
M9-B security and normalisation suites runs against fixtures, and this module exists only
for the occasional manual check that a real dispatch still fits the contract.

It is skipped unless **both** are true:

    BUSINESSOPS_LIVE_SMOKE=1                     the operator opted in
    a transport is registered via `set_live_transport()`   something can actually dispatch

Even then it asserts contract shape, never content: "the returned records normalise into
citable evidence", not "the third result mentions churn". Web pages change; the contract
does not.

Nothing here runs in CI, and a failure here is never part of M9-B acceptance.
"""

import os
import unittest

from bops import research as R
from bops.research import scout as scout_mod

#: Set by an operator wiring a real scout dispatch in a REPL or a manual harness. Left
#: None in the repository on purpose - there is no importable live transport, so this
#: module cannot reach the network by itself.
_LIVE_TRANSPORT = None


def set_live_transport(transport):
    """Register a dispatch for a manual smoke run. Not called anywhere in the repository."""
    global _LIVE_TRANSPORT
    _LIVE_TRANSPORT = transport
    return transport


def live_enabled():
    return os.environ.get("BUSINESSOPS_LIVE_SMOKE") == "1" and _LIVE_TRANSPORT is not None


@unittest.skipUnless(live_enabled(),
                     "live smoke test: set BUSINESSOPS_LIVE_SMOKE=1 and register a "
                     "transport via set_live_transport()")
class TestLiveScoutSmoke(unittest.TestCase):
    """Contract shape against a real dispatch. Never asserts page content."""

    def authorised(self):
        request = R.ResearchRequest(
            "gross margin", R.INDUSTRY, intent=R.BENCHMARK,
            public_terms={"industry": "logistics", "period": "2026"},
            operation="live-smoke")
        decision = R.assess(request)
        self.assertEqual(decision.decision, R.ALLOW)
        self.assertEqual(decision.tier, 0)
        return R.RetrievalRequest(decision)

    def test_a_live_tier_zero_retrieval_produces_citable_evidence(self):
        scout = scout_mod.ScoutRetriever(_LIVE_TRANSPORT)
        result = scout.retrieve(self.authorised())

        if isinstance(result, R.ResearchFailure):
            # A failure is a legitimate outcome for a live run, and must be structured.
            self.assertIn(result.status, R.STATUSES)
            self.assertTrue(result.reason)
            self.assertTrue(result.explanation)
            return

        self.assertTrue(len(result) >= 1)
        for item in result:
            self.assertTrue(item.source)
            self.assertTrue(item.reference)
            self.assertIn(item.source_tier, ("A", "B", "C", "D"))
            self.assertEqual(item.trust, R.UNTRUSTED)
            self.assertTrue(item.retrieved_at)

    def test_a_live_retrieval_still_makes_exactly_one_dispatch(self):
        transport = _LIVE_TRANSPORT
        before = len(getattr(transport, "calls", []) or [])
        scout_mod.ScoutRetriever(transport).retrieve(self.authorised())
        after = len(getattr(transport, "calls", []) or [])
        if after or before:
            self.assertEqual(after - before, 1)


class TestLiveSmokeIsOptional(unittest.TestCase):
    """These run always: the point is that the suite is offline by default."""

    def test_no_live_transport_is_registered_in_the_repository(self):
        self.assertIsNone(_LIVE_TRANSPORT,
                          "a live transport must never be committed; the deterministic "
                          "suite would then depend on the internet")

    def test_the_live_suite_is_disabled_without_the_environment_flag(self):
        if os.environ.get("BUSINESSOPS_LIVE_SMOKE") != "1":
            self.assertFalse(live_enabled())


if __name__ == "__main__":
    unittest.main()
