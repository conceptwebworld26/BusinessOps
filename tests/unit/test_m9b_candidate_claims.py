"""Candidate claims: derived, unverified, and refused far more often than produced.

The `EvidenceSet` is the authoritative output of a retrieval — it records that a source
said something. A candidate claim is a **derived, intermediate, unverified** reading of one
evidence item: it records that *we are asserting it*. Nothing in M9-B verifies a claim, so
the distinction has to survive in the record rather than in a convention someone remembers.

These tests cover the half that is policy rather than judgement. Deciding what a source
says is the model's job and Python has no opinion on it; deciding whether a claim is
*allowed* to stand on a given item is entirely mechanical, and that is what is asserted
here — traceability, provenance, tier rules, dating, conflicts, and the line between
reporting a source and advising a business.
"""

import unittest

from bops import research as R
from bops.research import evidence_set as evidence_mod
from bops.research import handoff as handoff_mod
from bops.research import scout as scout_mod
from bops.research import sources as sources_mod

REQUEST = dict(subject="gross margin benchmark", category=R.INDUSTRY, intent=R.BENCHMARK,
               public_terms={"industry": "logistics", "period": "2026"},
               operation="m9b-claim-test")

#: A tier-A, dated, quotable record — the only shape that should ever yield a claim.
TIER_A = {"source": "Office for National Statistics",
          "reference": "https://www.ons.gov.uk/economy/transport-storage-2026",
          "title": "Transport and storage sector accounts, 2026",
          "publication_date": "2026-04-30", "source_type": "official_statistics",
          "content": "Gross margin across the sector averaged 14.2% in the year to March.",
          "claim_kind": "financials"}

STATEMENT = "ONS reports sector gross margin averaged 14.2% in the year to March 2026."


def envelope(records):
    brief = R.open_retrieval(**REQUEST)["brief"]
    return {"envelope": scout_mod.SCOUT_RESULT_ENVELOPE,
            "operation": brief["operation"], "query_text": brief["query_text"],
            "status": scout_mod.RESULT_OK, "records": records}


def close(records, proposals=None):
    fields = dict(REQUEST)
    subject = fields.pop("subject")
    category = fields.pop("category")
    return R.close_retrieval(envelope(records), subject, category, as_of="2026-09-10",
                             proposals=proposals, **fields)


def first_id(records):
    return close(records)["evidence"]["items"][0]["evidence_id"]


class TestCandidateClaimsAreOptIn(unittest.TestCase):
    """The evidence set is the output. A claim is only ever produced on request."""

    def test_no_claim_is_produced_unless_one_is_proposed(self):
        result = close([TIER_A])
        self.assertEqual(result["candidate_claims"], [])
        self.assertEqual(result["claims_not_produced"], [])

    def test_the_evidence_set_is_produced_whether_or_not_a_claim_is(self):
        self.assertEqual(len(close([TIER_A])["evidence"]["items"]), 1)

    def test_an_empty_proposal_list_produces_nothing(self):
        self.assertEqual(close([TIER_A], [])["candidate_claims"], [])


class TestLinkageAndProvenance(unittest.TestCase):

    def produced(self, records=None, **proposal):
        records = records or [TIER_A]
        fields = {"evidence_id": first_id(records), "statement": STATEMENT}
        fields.update(proposal)
        result = close(records, [fields])
        self.assertEqual(len(result["candidate_claims"]), 1,
                         result["claims_not_produced"])
        return result

    def test_it_carries_the_evidence_id_it_came_from(self):
        self.assertEqual(self.produced()["candidate_claims"][0]["evidence_id"],
                         first_id([TIER_A]))

    def test_the_evidence_id_names_an_item_in_the_same_set(self):
        result = self.produced()
        ids = {i["evidence_id"] for i in result["evidence"]["items"]}
        self.assertIn(result["candidate_claims"][0]["evidence_id"], ids)

    def test_it_preserves_source_and_citation(self):
        claim = self.produced()["candidate_claims"][0]
        self.assertEqual(claim["source"], TIER_A["source"])
        self.assertEqual(claim["citation"], TIER_A["reference"])

    def test_it_preserves_the_publication_date(self):
        self.assertEqual(self.produced()["candidate_claims"][0]["source_date"],
                         "2026-04-30")

    def test_it_preserves_the_source_tier(self):
        self.assertEqual(self.produced()["candidate_claims"][0]["source_tier"], "A")

    def test_the_tier_is_the_local_one_never_the_envelope_s(self):
        records = [dict(TIER_A, source_tier="D")]
        claim = self.produced(records=records)["candidate_claims"][0]
        self.assertEqual(claim["source_tier"], "A")

    def test_it_is_class_three_external_sourced(self):
        self.assertEqual(self.produced()["candidate_claims"][0]["class"], 3)

    def test_the_statement_is_carried_verbatim(self):
        self.assertEqual(self.produced()["candidate_claims"][0]["statement"], STATEMENT)

    def test_it_records_when_the_evidence_was_retrieved(self):
        self.assertEqual(self.produced()["candidate_claims"][0]["retrieved_at"],
                         "2026-09-10")


class TestCandidateStatus(unittest.TestCase):

    def claim(self, records=None, **proposal):
        records = records or [TIER_A]
        fields = {"evidence_id": first_id(records), "statement": STATEMENT}
        fields.update(proposal)
        produced = close(records, [fields])["candidate_claims"]
        self.assertEqual(len(produced), 1)
        return produced[0]

    def test_it_is_marked_candidate(self):
        self.assertEqual(self.claim()["status"], handoff_mod.CANDIDATE)

    def test_it_is_marked_unverified(self):
        self.assertIs(self.claim()["verified"], False)

    def test_nothing_in_the_module_can_mark_a_claim_verified(self):
        source = open(handoff_mod.__file__, "rb").read().decode("utf-8")
        self.assertNotIn('"verified": True', source)
        self.assertNotIn("verified=True", source)

    def test_it_states_its_candidacy_in_its_own_limitations(self):
        self.assertTrue(any("Candidate only" in line
                            for line in self.claim()["limitations"]))

    def test_a_dated_source_carries_its_staleness_into_the_limitations(self):
        claim = self.claim(records=[dict(TIER_A, publication_date="2020-01-01")])
        self.assertEqual(claim["freshness"], "dated")
        self.assertTrue(len(claim["limitations"]) >= 2)

    def test_an_inferred_tier_is_carried_into_the_limitations(self):
        records = [dict(TIER_A, source="Somewhere",
                        reference="https://margins-explained.example/answer")]
        claim = self.claim(records=records, material=False)
        self.assertTrue(any("tier was inferred" in line
                            for line in claim["limitations"]))


class TestRestrictions(unittest.TestCase):
    """Every rule here is a refusal the harness must make on its own."""

    def refuse(self, records, proposal):
        result = close(records, [proposal])
        self.assertEqual(result["candidate_claims"], [], "a claim was produced")
        self.assertEqual(len(result["claims_not_produced"]), 1)
        refusal = result["claims_not_produced"][0]
        self.assertEqual(refusal["status"], "not_produced")
        self.assertTrue(refusal["explanation"])
        return refusal

    def test_a_claim_traceable_to_no_evidence_is_refused(self):
        refusal = self.refuse([TIER_A], {"evidence_id": "ev-000000000000",
                                         "statement": STATEMENT})
        self.assertEqual(refusal["reason"], "untraceable")

    def test_a_claim_with_no_evidence_id_at_all_is_refused(self):
        self.assertEqual(self.refuse([TIER_A], {"statement": STATEMENT})["reason"],
                         "untraceable")

    def test_a_tier_d_source_cannot_support_a_claim(self):
        records = [dict(TIER_A, source="Content Mill",
                        reference="https://ezinearticles.example/logistics-margins")]
        self.assertEqual(close(records)["evidence"]["items"][0]["source_tier"], "D")
        self.refuse(records, {"evidence_id": first_id(records), "statement": STATEMENT})

    def test_a_tier_c_source_cannot_solely_support_a_material_claim(self):
        records = [dict(TIER_A, source="Somewhere",
                        reference="https://margins-explained.example/answer")]
        self.assertEqual(close(records)["evidence"]["items"][0]["source_tier"], "C")
        self.refuse(records, {"evidence_id": first_id(records), "statement": STATEMENT,
                              "material": True})

    def test_the_same_tier_c_source_may_support_a_non_material_claim(self):
        """The rule is about material claims, not about tier C being worthless."""
        records = [dict(TIER_A, source="Somewhere",
                        reference="https://margins-explained.example/answer")]
        result = close(records, [{"evidence_id": first_id(records),
                                  "statement": STATEMENT, "material": False}])
        self.assertEqual(len(result["candidate_claims"]), 1)

    def test_an_undated_source_cannot_support_a_claim(self):
        records = [{k: v for k, v in TIER_A.items() if k != "publication_date"}]
        self.refuse(records, {"evidence_id": first_id(records), "statement": STATEMENT})

    def test_a_recommendation_is_refused(self):
        refusal = self.refuse([TIER_A], {
            "evidence_id": first_id([TIER_A]),
            "statement": "We recommend raising prices to match the sector margin."})
        self.assertEqual(refusal["reason"], "not_a_source_claim")

    def test_an_impact_judgement_is_refused(self):
        self.refuse([TIER_A], {
            "evidence_id": first_id([TIER_A]),
            "statement": "This means we are underperforming the sector."})

    def test_an_empty_statement_is_refused(self):
        self.assertEqual(
            self.refuse([TIER_A], {"evidence_id": first_id([TIER_A]),
                                   "statement": "   "})["reason"], "no_statement")

    def test_a_paragraph_length_statement_is_refused(self):
        self.assertEqual(
            self.refuse([TIER_A], {"evidence_id": first_id([TIER_A]),
                                   "statement": "x " * 400})["reason"],
            "statement_too_long")

    def test_malformed_proposals_are_refused_rather_than_raising(self):
        result = close([TIER_A], ["not a proposal", None, 7])
        self.assertEqual(result["candidate_claims"], [])
        self.assertEqual(len(result["claims_not_produced"]), 3)

    def test_a_refusal_never_silently_becomes_a_claim(self):
        result = close([TIER_A], [
            {"evidence_id": "ev-000000000000", "statement": STATEMENT},
            {"evidence_id": first_id([TIER_A]),
             "statement": "We should raise prices."}])
        self.assertEqual(result["candidate_claims"], [])
        self.assertEqual(len(result["claims_not_produced"]), 2)


class TestConflictsAreNeverResolvedSilently(unittest.TestCase):
    """Two credible sources disagreeing is a result to report, not one to average."""

    def conflicted_set(self):
        evidence = evidence_mod.EvidenceSet(
            operation=REQUEST["operation"], subject=REQUEST["subject"],
            category=REQUEST["category"])
        for reference in ("https://www.ons.gov.uk/economy/transport-storage-2026",
                          "https://www.gov.uk/dft/logistics-margins-2026"):
            evidence.add(evidence_mod.EvidenceItem(
                source="Office for National Statistics", reference=reference,
                source_tier="A", retrieved_at="2026-09-10",
                publication_date="2026-04-30", as_of="2026-09-10"))
        evidence.record_conflict("sector gross margin", [
            sources_mod.SourcePosition(evidence.items[0].id, 14.2,
                                       "Office for National Statistics", "A"),
            sources_mod.SourcePosition(evidence.items[1].id, 31.0,
                                       "Department for Transport", "A")])
        return evidence

    def test_the_fixture_really_does_conflict(self):
        self.assertTrue(self.conflicted_set().has_conflict())

    def test_no_claim_stands_while_a_conflict_is_unresolved(self):
        evidence = self.conflicted_set()
        produced, refused = handoff_mod._candidate_claims(
            evidence, [{"evidence_id": evidence.items[0].id, "statement": STATEMENT}])
        self.assertEqual(produced, [])
        self.assertEqual(refused[0]["reason"], "unresolved_conflict")

    def test_the_refusal_says_conflicts_are_not_averaged(self):
        evidence = self.conflicted_set()
        _produced, refused = handoff_mod._candidate_claims(
            evidence, [{"evidence_id": evidence.items[0].id, "statement": STATEMENT}])
        self.assertIn("averaged", refused[0]["explanation"].lower())

    def test_a_set_without_a_conflict_is_unaffected(self):
        self.assertEqual(len(close([TIER_A], [{"evidence_id": first_id([TIER_A]),
                                               "statement": STATEMENT}])
                              ["candidate_claims"]), 1)


class TestNoInternalDataInTheClaimLayer(unittest.TestCase):

    def test_a_claim_carries_nothing_from_the_business_side(self):
        import json
        result = close([TIER_A], [{"evidence_id": first_id([TIER_A]),
                                   "statement": STATEMENT}])
        blob = json.dumps(result["candidate_claims"]).lower()
        for forbidden in ("business_context", "dataset", "descriptor", "aggregate",
                          "credential", "api_key", "token", "secret", "approval",
                          "conversation", "customer", "transaction"):
            self.assertNotIn(forbidden, blob)

    def test_the_claim_layer_names_no_tool(self):
        import re
        source = open(handoff_mod.__file__, "rb").read().decode("utf-8")
        code = re.sub(r'""".*?"""', "", source, flags=re.S)
        code = "\n".join(line.split("#")[0] for line in code.split("\n"))
        for tool in ("WebSearch", "WebFetch", "Read", "Bash", "Task", "Agent"):
            self.assertNotIn(tool, code)


if __name__ == "__main__":
    unittest.main()
