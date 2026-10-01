"""M9-C.8 — provenance is issued by the gate, never supplied by the payload.

The M9-C.8 investigation asked whether some other handoff could carry the scout's findings
into the evidence system now that the runtime cannot enforce the envelope. The candidate
that looks most attractive is **parent-model-mediated extraction**: let the parent read the
scout's wrapped reply and re-emit a clean envelope for Python to validate.

It is rejected, and this file pins the property that makes the rejection principled rather
than stylistic.

Today, `close_retrieval()` re-derives the request and the gate decision from its own
arguments. Subject, disclosure tier, destination, query text, operation and every retrieval
bound come from **that** derivation. The payload contributes records and nothing else — it
cannot describe the retrieval it claims to be part of. So even though the scout's reply is
untrusted model output, the *frame* around it is BusinessOps-controlled, and an evidence set
cannot be talked into misrepresenting where it came from.

Parent-mediated extraction would not change these fields either — but it would change who
authors the records inside them. The parent context can read business data; the scout
deliberately cannot (ADR-0006, ADR-0014). Moving authorship of the envelope to the parent
puts the one context that has seen internal data in charge of producing text that the
evidence set then labels external. The disclosure boundary would still exist on paper and
would no longer mean anything.

These tests therefore state the invariant any future handoff must preserve: **whatever
produces the records, the provenance is ours.**
"""

import unittest

from bops import research as R
from bops.research import scout as scout_mod

REQUEST = dict(subject="gross margin benchmark", category=R.INDUSTRY, intent=R.BENCHMARK,
               public_terms={"industry": "logistics", "period": "2026"},
               operation="m9c8-provenance-test")

RECORD = {"source": "Reuters", "reference": "https://www.reuters.com/business/margins",
          "title": "Where the margin went", "publication_date": "2026-02-11",
          "source_type": "press", "content": "Operators reported thinner margins.",
          "claim_kind": "financials"}


def payload(**overrides):
    brief = R.open_retrieval(**REQUEST)["brief"]
    body = {"envelope": scout_mod.SCOUT_RESULT_ENVELOPE,
            "operation": brief["operation"], "query_text": brief["query_text"],
            "status": scout_mod.RESULT_OK, "records": [RECORD]}
    body.update(overrides)
    return body


def close(body):
    fields = dict(REQUEST)
    subject = fields.pop("subject")
    category = fields.pop("category")
    return R.close_retrieval(body, subject, category, as_of="2026-09-11", **fields)


class TestProvenanceIsGateIssued(unittest.TestCase):
    """A payload may carry findings. It may not describe the retrieval."""

    def test_the_disclosure_tier_comes_from_the_gate(self):
        evidence = close(payload(disclosure_tier=2))["evidence"]
        self.assertEqual(evidence["disclosure_tier"], 0)

    def test_the_subject_comes_from_the_request(self):
        evidence = close(payload(subject="a different company entirely"))["evidence"]
        self.assertEqual(evidence["subject"], "gross margin benchmark")

    def test_the_destination_comes_from_the_request(self):
        evidence = close(payload(destination="internal_db:customer_ledger"))["evidence"]
        self.assertEqual(evidence["destination"]["kind"], "public_web")
        self.assertTrue(evidence["destination"]["permitted"])

    def test_the_category_comes_from_the_request(self):
        self.assertEqual(close(payload(category="company"))["evidence"]["category"],
                         "industry")

    def test_the_bounds_come_from_the_brief(self):
        """A payload cannot widen the retrieval it reports on."""
        result = close(payload(max_fetched=999, max_results=999))
        self.assertEqual(result["brief"]["max_fetched"], scout_mod.MAX_FETCHED)
        self.assertEqual(result["brief"]["max_results"], scout_mod.MAX_RESULTS)

    def test_the_query_text_is_the_one_the_gate_approved(self):
        evidence = close(payload())["evidence"]
        self.assertEqual(evidence["query_text"],
                         R.open_retrieval(**REQUEST)["brief"]["query_text"])

    def test_an_echo_that_does_not_match_is_refused_outright(self):
        """The echo is checked, not adopted: a mismatch discards the whole reply."""
        result = close(payload(query_text="logistics customer list 2026"))
        self.assertNotEqual(result["status"], R.OK)
        self.assertIsNone(result["evidence"])

    def test_the_trust_marking_is_not_negotiable(self):
        evidence = close(payload(trust="verified"))["evidence"]
        self.assertEqual(evidence["trust"], R.UNTRUSTED)
        for item in evidence["items"]:
            self.assertEqual(item["trust"], R.UNTRUSTED)

    def test_a_payload_cannot_declare_its_own_support_verdict(self):
        """Support is recomputed from the local tiers, whatever the payload asserts."""
        blog = dict(RECORD, source="Freight Insider",
                    reference="https://freightinsider.example/margins")
        evidence = close(payload(records=[blog],
                                 support={"support": "supported"}))["evidence"]
        self.assertEqual(evidence["items"][0]["source_tier"], "C")
        self.assertEqual(evidence["support"]["support"], "unsupported")

    def test_the_evidence_id_is_derived_locally_not_supplied(self):
        """Ids are computed from source, reference and retrieval date."""
        supplied = dict(RECORD)
        supplied["evidence_id"] = "ev-chosen-by-the-model"
        result = close(payload(records=[supplied]))
        self.assertEqual(result["status"], R.OK)
        self.assertNotEqual(result["evidence"]["items"][0]["evidence_id"],
                            "ev-chosen-by-the-model")

    def test_no_payload_field_creates_a_verified_claim(self):
        result = close(payload(verified=True, candidate_claims=[{"verified": True}]))
        self.assertEqual(result["candidate_claims"], [])


if __name__ == "__main__":
    unittest.main()
