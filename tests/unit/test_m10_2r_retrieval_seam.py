"""M10.2-R — the retrieval → synthesis seam.

`synthesis.register_external()` accepts only an `EvidenceSet` **object**, and refuses a
serialised one deliberately: a dict would arrive carrying `source_tier` as data, and a tier
is something BusinessOps derives from the source rather than something it is told. But
`close_retrieval()` returns `evidence.as_dict()`, and `EvidenceSet` has no `from_dict`. The
M10.2 verification therefore had no public object-level path from a completed retrieval into
the synthesis layer and had to drive `ScoutRetriever` by hand — a second assembly of the
same pipeline, which is exactly what ADR-0012 forbids.

`close_retrieval_object()` closes that gap with the smallest possible seam: the same
`_close` assembly both public closers share, returning the set under `evidence_set` instead
of serialising it. Nothing about retrieval, parsing, tiering, freshness or conflicts
changes, and there is no second path to the network — these tests reach no network at all.

The success result deliberately has **no** `evidence` key, so a caller cannot reach for a
key that is sometimes a record and sometimes an object.
"""

import json
import os
import sys
import unittest
from decimal import Decimal

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"),
             os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import research as R                              # noqa: E402
from bops import synthesis as S                             # noqa: E402
from bops.research import contract as contract_mod          # noqa: E402
from bops.research import evidence_set as evidence_mod      # noqa: E402
from bops.research import gate as gate_mod                  # noqa: E402
from bops.research import retrieval as retrieval_mod        # noqa: E402
from bops.research import scout as scout_mod                # noqa: E402

SUBJECT = "logistics"
CATEGORY = R.INDUSTRY
AS_OF = "2026-09-15"

OFFICIAL = {"reference": "https://www.ons.gov.uk/economy/transport-storage-2026",
            "source": "Office for National Statistics",
            "title": "Transport and storage sector accounts, 2026",
            "publication_date": "2026-04-30", "source_type": "official_statistics",
            "content": "The sector was valued at GBP 142bn in 2026.",
            "claim_kind": "market_sizing"}

#: Carries a tier it has not earned, plus a verification flag. Both are outside
#: `ACCEPTED_RECORD_FIELDS`, so ingestion must drop them and classify the host itself.
BOASTFUL = {"reference": "https://research.example.invalid/logistics-2026",
            "source": "DEMO House", "title": "Logistics market 2026",
            "publication_date": "2026-05-01", "source_type": "research_house",
            "content": "The market was valued at GBP 210bn in 2026.",
            "claim_kind": "market_sizing", "source_tier": "A", "verified": True}


def _kwargs(operation):
    return dict(intent=R.SIZING, public_terms={"industry": "logistics"},
                operation=operation)


def _reply(operation, records):
    lines = ["%s %s %s" % (scout_mod.RECORD_TOKEN, operation, json.dumps(r))
             for r in records]
    lines.append("%s %s %d" % (scout_mod.END_TOKEN, operation, len(records)))
    return "\n".join(lines)


def _close_object(operation, records, **extra):
    return R.close_retrieval_object(_reply(operation, records), SUBJECT, CATEGORY,
                                    as_of=AS_OF, **dict(_kwargs(operation), **extra))


def _close_dict(operation, records, **extra):
    return R.close_retrieval(_reply(operation, records), SUBJECT, CATEGORY,
                             as_of=AS_OF, **dict(_kwargs(operation), **extra))


class SeamReturnsTheObject(unittest.TestCase):

    OPERATION = "m10-2r-seam-object"

    def setUp(self):
        self.result = _close_object(self.OPERATION, [OFFICIAL, BOASTFUL])

    def test_status_is_ok_and_both_records_were_accepted(self):
        self.assertEqual(self.result["status"], contract_mod.OK)
        self.assertEqual(self.result["accepted"], 2)

    def test_evidence_set_is_the_live_object(self):
        self.assertIsInstance(self.result["evidence_set"], evidence_mod.EvidenceSet)

    def test_success_result_carries_no_serialised_evidence_key(self):
        """One key, one meaning. A caller wanting a record calls `close_retrieval`."""
        self.assertNotIn("evidence", self.result)
        self.assertNotIn("instruction_safe", self.result)

    def test_the_object_feeds_register_external_directly(self):
        synthesis = S.SynthesisSet(subject="seam")
        registered = S.register_external(synthesis, self.result["evidence_set"],
                                         S.ORIGIN_INDUSTRY)
        self.assertEqual(sorted(registered),
                         sorted(i.id for i in self.result["evidence_set"].items))

    def test_evidence_ids_are_preserved_into_synthesis(self):
        synthesis = S.SynthesisSet(subject="seam")
        S.register_external(synthesis, self.result["evidence_set"], S.ORIGIN_INDUSTRY)
        for item in self.result["evidence_set"].items:
            ref = S.ProvenanceRef(S.P_EVIDENCE, item.id)
            self.assertIsNotNone(synthesis.resolve_ref(ref),
                                 "evidence %s did not survive the seam" % item.id)


class SeamRefusesASerialisedSet(unittest.TestCase):

    OPERATION = "m10-2r-seam-dict"

    def test_close_retrieval_dict_is_refused_by_register_external(self):
        record = _close_dict(self.OPERATION, [OFFICIAL])["evidence"]
        synthesis = S.SynthesisSet(subject="seam")
        with self.assertRaises(S.SynthesisError) as caught:
            S.register_external(synthesis, record, S.ORIGIN_INDUSTRY)
        self.assertIn("only an EvidenceSet object", str(caught.exception))

    def test_a_hand_built_lookalike_is_refused(self):
        class NotAnEvidenceSet(object):
            items = []
            conflicts = []
        synthesis = S.SynthesisSet(subject="seam")
        with self.assertRaises(S.SynthesisError):
            S.register_external(synthesis, NotAnEvidenceSet(), S.ORIGIN_INDUSTRY)


class TiersStayLocallyDerived(unittest.TestCase):

    OPERATION = "m10-2r-seam-tiers"

    def setUp(self):
        self.evidence = _close_object(self.OPERATION,
                                      [OFFICIAL, BOASTFUL])["evidence_set"]
        self.by_source = dict((i.source, i) for i in self.evidence.items)

    def test_scout_supplied_tier_is_not_an_accepted_field(self):
        self.assertNotIn("source_tier", scout_mod.ACCEPTED_RECORD_FIELDS)
        self.assertNotIn("verified", scout_mod.ACCEPTED_RECORD_FIELDS)

    def test_a_claimed_tier_a_is_classified_locally_as_c(self):
        self.assertEqual(self.by_source["DEMO House"].source_tier, "C")
        self.assertFalse(self.by_source["DEMO House"].may_stand_alone)

    def test_a_recognised_official_source_earns_its_tier_locally(self):
        self.assertEqual(self.by_source["Office for National Statistics"].source_tier, "A")

    def test_every_item_stays_untrusted_through_the_seam(self):
        for item in self.evidence.items:
            self.assertEqual(item.trust, R.UNTRUSTED)
            self.assertTrue(any("UNTRUSTED_EXTERNAL_DATA" in note
                                for note in item.notes))

    def test_trust_survives_registration_into_synthesis(self):
        synthesis = S.SynthesisSet(subject="seam")
        S.register_external(synthesis, self.evidence, S.ORIGIN_INDUSTRY)
        stored = synthesis.resolve_ref(
            S.ProvenanceRef(S.P_EVIDENCE, self.by_source["DEMO House"].id))
        self.assertEqual(stored.source_tier, "C")
        self.assertEqual(stored.trust, R.UNTRUSTED)


class FreshnessAndConflictsSurvive(unittest.TestCase):

    OPERATION = "m10-2r-seam-conflicts"

    def setUp(self):
        opened = _close_object(self.OPERATION, [OFFICIAL, BOASTFUL])
        self.evidence = opened["evidence_set"]
        official, boastful = self.evidence.items[0], self.evidence.items[1]
        self.declared = R.close_retrieval_object(
            _reply(self.OPERATION, [OFFICIAL, BOASTFUL]), SUBJECT, CATEGORY, as_of=AS_OF,
            conflicts=[{
                "subject": "logistics sector size, 2026",
                "reason": "The sources measure different boundaries.",
                "positions": [
                    {"evidence_id": official.id, "value": 142.0, "unit": "GBP bn",
                     "definition": "transport and storage sector accounts"},
                    {"evidence_id": boastful.id, "value": 210.0, "unit": "GBP bn",
                     "definition": "logistics market including contract services"}]}],
            **_kwargs(self.OPERATION))

    def test_freshness_is_carried_on_every_item(self):
        for item in self.evidence.items:
            self.assertIn(item.freshness["freshness"],
                          ("current", "dated", "undated"))
            self.assertIsNotNone(item.publication_date)

    def test_a_declared_conflict_was_recorded_on_the_object(self):
        self.assertEqual(self.declared["conflicts_not_recorded"], [])
        self.assertEqual(len(self.declared["evidence_set"].conflicts), 1)

    def test_the_conflict_reaches_synthesis_and_stays_unresolved(self):
        synthesis = S.SynthesisSet(subject="seam")
        S.register_external(synthesis, self.declared["evidence_set"], S.ORIGIN_INDUSTRY)
        self.assertEqual(len(synthesis.conflicts), 1)
        self.assertTrue(synthesis.unresolved_conflicts())
        self.assertFalse(hasattr(synthesis, "resolve_conflict"))


class SeamCannotProduceAnInternalStatement(unittest.TestCase):
    """The seam carries evidence in; it grants no new standing once it is there."""

    OPERATION = "m10-2r-seam-no-escalation"

    def setUp(self):
        self.evidence = _close_object(self.OPERATION, [OFFICIAL])["evidence_set"]
        self.synthesis = S.SynthesisSet(subject="seam")
        self.synthesis.register_dataset("ds-seam", label="seam.csv")
        S.register_external(self.synthesis, self.evidence, S.ORIGIN_INDUSTRY)
        self.item = self.evidence.items[0]

    def test_registering_evidence_creates_no_statements(self):
        self.assertEqual(len(self.synthesis.items), 0)

    def test_tier_a_evidence_still_cannot_found_an_internal_fact(self):
        """Tier is not the question; where the number came from is."""
        self.assertEqual(self.item.source_tier, "A")
        with self.assertRaises(S.SynthesisError):
            self.synthesis.add(S.SynthesisItem(
                S.FACT, S.ORIGIN_FINANCIAL, "Our sector was valued at GBP 142bn in 2026.",
                provenance=[S.ProvenanceRef(S.P_EVIDENCE, self.item.id)]))

    def test_tier_a_evidence_still_cannot_found_an_internal_calculation(self):
        with self.assertRaises(S.SynthesisError):
            self.synthesis.add(S.SynthesisItem(
                S.CALCULATION, S.ORIGIN_KPI, "Sector value is GBP 142bn.",
                provenance=[S.ProvenanceRef(S.P_EVIDENCE, self.item.id)],
                basis="sourced figure"))

    def test_the_sourced_path_through_the_seam_works(self):
        statement = S.sourced_statement(
            self.synthesis, S.ORIGIN_INDUSTRY,
            "The ONS reports the sector at GBP 142bn in 2026.",
            # ADR-0025: the source published "GBP 142bn"; the statement carries the
            # canonical quantity, decomposed at construction.
            evidence_ids=[self.item.id], observed=Decimal("142"),
            source_unit="GBP bn", period="2026")
        self.assertEqual(statement.kind, S.SOURCED)
        self.assertEqual(statement.domain, S.EXTERNAL)


class CloseRetrievalIsUnchanged(unittest.TestCase):
    """Back-compatibility: the serialising closer keeps its exact contract."""

    OPERATION = "m10-2r-seam-compat"

    def test_success_keys_are_unchanged(self):
        result = _close_dict(self.OPERATION, [OFFICIAL, BOASTFUL])
        self.assertEqual(
            sorted(result.keys()),
            ["accepted", "brief", "candidate_claims", "claims_not_produced",
             "conflicts_not_recorded", "evidence", "instruction_safe", "rejected",
             "status", "tier"])

    def test_result_is_still_json_serialisable(self):
        result = _close_dict(self.OPERATION, [OFFICIAL])
        self.assertTrue(json.dumps(result))

    def test_both_closers_agree_on_the_evidence(self):
        record = _close_dict(self.OPERATION, [OFFICIAL, BOASTFUL])["evidence"]
        obj = _close_object(self.OPERATION, [OFFICIAL, BOASTFUL])["evidence_set"]
        self.assertEqual(json.dumps(record, sort_keys=True, default=str),
                         json.dumps(obj.as_dict(), sort_keys=True, default=str))

    def test_a_malformed_reply_fails_the_same_way_on_both_closers(self):
        broken = "BOPS-REC/1 %s {not json}" % self.OPERATION
        as_dict = R.close_retrieval(broken, SUBJECT, CATEGORY, as_of=AS_OF,
                                    **_kwargs(self.OPERATION))
        as_object = R.close_retrieval_object(broken, SUBJECT, CATEGORY, as_of=AS_OF,
                                             **_kwargs(self.OPERATION))
        self.assertEqual(as_dict["status"], as_object["status"])
        self.assertNotEqual(as_dict["status"], contract_mod.OK)
        self.assertIsNone(as_dict["evidence"])

    def test_neither_closer_reaches_a_transport(self):
        """`_close` parses a reply it was handed; it never dispatches."""
        retriever = scout_mod.ScoutRetriever()
        self.assertFalse(retriever.available)
        self.assertEqual(retriever.briefs, [])


if __name__ == "__main__":
    unittest.main()
