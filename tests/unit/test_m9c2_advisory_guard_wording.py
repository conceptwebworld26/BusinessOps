"""M9-C.2 — the harness must describe the advisory guard as what it is.

`commands/retrieval-slice.md` said Python "will refuse a claim that ... reads as advice".
It does not. It refuses a claim matching `handoff.ADVISORY_MARKERS`, a fixed phrase list.
The M9-B live verification proposed "Logistics firms should target a gross margin above 20%
to stay competitive" — advice by any reading — and the engine accepted it, because no marker
covers a bare "firms should".

That gap is not a bug: `handoff.py` calls the list "a guard, not a proof" and says outright
that no string check can decide whether a sentence exceeds its source. The bug was a command
file promising semantic detection the engine never claimed, to a model that reads that file
as its instructions. A model told the machine will catch advice has less reason to police
its own wording, which is precisely the check that actually holds here.

These tests keep the document honest, and — more usefully — keep it *coupled to the code*.
`test_the_documented_counter_example_is_still_accepted` fails if anyone later adds "firms
should" to the marker list, forcing the example in the document to be corrected in the same
change rather than quietly becoming false. Nothing here asserts the list's contents, so
expanding it stays possible; what is asserted is that the document and the behaviour agree.

No implementation is touched by this milestone, and none is touched by this file.
"""

import os
import unittest

from bops import research as R
from bops.research import handoff as handoff_mod

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SLICE_MD = os.path.join(REPO, "dev", "harness", "retrieval-slice.md")  # BusinessOps M3: moved out of commands/

REQUEST = dict(subject="gross margin benchmark", category=R.INDUSTRY, intent=R.BENCHMARK,
               public_terms={"industry": "logistics", "period": "2026"},
               operation="m9c2-wording-test")

RECORD = {"source": "Logistics Weekly",
          "reference": "https://www.logisticsweekly.com/margins",
          "title": "Where the margin went", "publication_date": "2026-02-11",
          "source_type": "press", "content": "Operators reported thinner margins.",
          "claim_kind": "financials"}


def read_command():
    return open(SLICE_MD, "rb").read().decode("utf-8")


def propose(statement, material=False):
    """Run one proposal through the shipped ingestion path. No dispatch, no network."""
    brief = R.open_retrieval(**REQUEST)["brief"]
    payload = {"envelope": "bops.scout.result/1", "operation": brief["operation"],
               "query_text": brief["query_text"], "status": "ok", "records": [RECORD]}
    fields = dict(REQUEST)
    subject = fields.pop("subject")
    category = fields.pop("category")
    first = R.close_retrieval(payload, subject, category, as_of="2026-09-10", **fields)
    evidence_id = first["evidence"]["items"][0]["evidence_id"]
    return R.close_retrieval(
        payload, subject, category, as_of="2026-09-10",
        proposals=[{"evidence_id": evidence_id, "statement": statement,
                    "material": material}], **fields)


# ---------------------------------------------------------------------------
# A. The document no longer promises what the engine does not do
# ---------------------------------------------------------------------------

class TestTheWordingIsAccurate(unittest.TestCase):

    def test_the_superseded_claim_is_gone(self):
        """'reads as advice' described a classifier that was never implemented."""
        self.assertNotIn("reads as advice", read_command().lower())

    def test_the_refusal_is_described_as_a_marker_match(self):
        self.assertIn("contains a recognised advisory marker", read_command().lower())

    def test_the_guard_is_named_a_heuristic_not_a_classifier(self):
        body = read_command().lower()
        self.assertIn("heuristic guard, not a semantic classifier", body)

    def test_it_forbids_describing_the_guard_as_comprehensive(self):
        body = read_command().lower()
        self.assertIn("must not be described as comprehensive advice detection", body)

    def test_it_states_that_acceptance_proves_nothing(self):
        body = read_command().lower()
        self.assertIn("not thereby non-advisory", body)
        self.assertIn("never read acceptance as permission", body)

    def test_it_points_at_the_actual_mechanism(self):
        body = read_command()
        self.assertIn("ADVISORY_MARKERS", body)
        self.assertIn("lib/python/bops/research/handoff.py", body)

    def test_the_other_policy_checks_are_still_documented(self):
        """Correcting one clause must not quietly drop the rest of the policy."""
        body = read_command().lower()
        for clause in ("names no item in this set", "tier-d source",
                       "tier c alone when material", "carries no publication date",
                       "unresolved conflict"):
            self.assertIn(clause, body)

    def test_it_still_states_candidate_and_unverified(self):
        body = read_command()
        self.assertIn("`status: candidate`", body)
        self.assertIn("`verified: false`", body)


# ---------------------------------------------------------------------------
# B. The document and the behaviour agree — and stay coupled
# ---------------------------------------------------------------------------

class TestTheDocumentMatchesTheEngine(unittest.TestCase):

    def test_a_recognised_marker_is_still_refused(self):
        result = propose("We should target a gross margin above 20% to stay competitive.")
        self.assertEqual(result["candidate_claims"], [])
        self.assertEqual(result["claims_not_produced"][0]["reason"], "not_a_source_claim")

    def test_the_documented_counter_example_is_still_accepted(self):
        """Pins the example in the command file to the engine's actual behaviour.

        If a later change adds "firms should" to `ADVISORY_MARKERS`, this fails — and the
        document that cites this sentence as accepted must be corrected in the same change.
        """
        result = propose(
            "Logistics firms should target a gross margin above 20% to stay competitive.")
        self.assertEqual(result["claims_not_produced"], [])
        self.assertEqual(len(result["candidate_claims"]), 1)

    def test_even_an_accepted_advisory_statement_stays_unverified(self):
        """The guard missing one is survivable because nothing downstream trusts a claim."""
        claim = propose(
            "Logistics firms should target a gross margin above 20% to stay competitive."
        )["candidate_claims"][0]
        self.assertEqual(claim["status"], "candidate")
        self.assertFalse(claim["verified"])

    def test_the_marker_list_is_still_a_plain_sequence_of_phrases(self):
        """No classifier was smuggled in: the mechanism is what the document says it is."""
        self.assertTrue(handoff_mod.ADVISORY_MARKERS)
        for marker in handoff_mod.ADVISORY_MARKERS:
            self.assertIsInstance(marker, str)


if __name__ == "__main__":
    unittest.main()
