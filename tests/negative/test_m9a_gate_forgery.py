"""Gate-authorisation integrity: can retrieval be reached without the gate having run?

The M9-A report claimed that because `RetrievalRequest.__init__` accepts a
`DisclosureDecision` and nothing else, "retrieval cannot be constructed without a gate
decision". That was true and almost worthless: requiring a *type* is not requiring a
*provenance*, and the type was publicly constructible. The audit that produced these tests
retrieved a payload containing customer names and an API key through six separate routes.

The property actually needed, and the one asserted here:

    retrieval is reachable only from an authentic, gate-issued, immutable authorisation
    bound to the exact query text, destination and tier that were assessed.

Each test names the route it closes. A failure here means the disclosure gate can be
walked around, which is the single worst defect this system can have.
"""

import json
import unittest
from decimal import Decimal

from bops import research as R
from bops.privacy import aggregation as agg, classes as pc
from bops.research import gate as gate_mod, query as query_mod, retrieval as retrieval_mod

D = Decimal

#: What an attacker would want to send. Contains material that could never pass the gate:
#: named customers, an exact monetary level, and a credential.
PAYLOAD = ("Acme Corp customers: Fenwick Provisions GBP 412000, Globex GBP 388000; "
           "api_key sk-live-abcdef123456")


def payload_query(text=PAYLOAD):
    return query_mod.CandidateQuery(
        text=text, terms=[], subject="x", category=R.COMPANY, intent=R.PROFILE,
        tier=0, destination=R.PUBLIC_WEB)


def genuine_allow():
    """A real Tier 0 authorisation."""
    return R.assess(R.ResearchRequest(
        "churn", R.INDUSTRY, public_terms={"business_model": "B2B SaaS"}))


def genuine_tier_two():
    descriptor = agg.AggregateDescriptor("avg deal", D("12"), agg.RATE, 40,
                                         source_sensitivity=pc.INTERNAL)
    return R.assess(R.ResearchRequest("deals", R.MARKET,
                                      derived_context=[descriptor], requested_tier=2))


def spy():
    return R.FixtureRetriever([{"source": "s", "reference": "https://s",
                                "source_tier": "A", "retrieved_at": "2026-03-01"}])


# ==========================================================================
# A. Direct construction
# ==========================================================================

class TestDecisionCannotBeConstructed(unittest.TestCase):

    def test_the_public_constructor_refuses_without_the_issuance_capability(self):
        with self.assertRaises(R.ResearchError) as caught:
            gate_mod.DisclosureDecision(
                gate_mod.ALLOW, 0, 0, payload_query(), R.PUBLIC_WEB, None)
        self.assertIn("issued by gate.assess()", str(caught.exception))

    def test_no_decision_state_can_be_constructed_directly(self):
        for state in gate_mod.DECISIONS:
            with self.assertRaises(R.ResearchError, msg=state):
                gate_mod.DisclosureDecision(
                    state, 0, 0, payload_query(), R.PUBLIC_WEB, None)

    def test_a_directly_constructed_decision_never_reaches_retrieval(self):
        retriever = spy()
        try:
            forged = gate_mod.DisclosureDecision(
                gate_mod.ALLOW, 0, 0, payload_query(), R.PUBLIC_WEB, None)
            retriever.retrieve(R.RetrievalRequest(forged))
        except Exception:
            pass
        self.assertEqual(retriever.calls, [], "retrieval ran on a forged decision")


# ==========================================================================
# B. Construction that skips __init__
# ==========================================================================

class TestForgeryThatSkipsInit(unittest.TestCase):

    def new_forged(self):
        """An object of the right type that never ran `__init__`."""
        forged = object.__new__(gate_mod.DisclosureDecision)
        for name, value in (
                ("decision", gate_mod.ALLOW), ("tier", 0), ("requested_tier", 0),
                ("query", payload_query()), ("destination", R.PUBLIC_WEB),
                ("request", None), ("reasons", []), ("failed_checks", []),
                ("assessments", []), ("alternative", None), ("operation", None),
                ("_bound_text", PAYLOAD),
                ("_bound_destination", R.PUBLIC_WEB.identity()),
                ("_bound_tier", 0), ("_approval", None), ("_issued", True)):
            object.__setattr__(forged, name, value)
        return forged

    def test_it_is_the_right_type_but_not_gate_issued(self):
        forged = self.new_forged()
        self.assertIsInstance(forged, gate_mod.DisclosureDecision)
        self.assertFalse(gate_mod.is_gate_issued(forged))

    def test_it_reports_itself_unauthorised(self):
        self.assertFalse(self.new_forged().authorised)

    def test_retrieval_refuses_it(self):
        with self.assertRaises(R.RetrievalError):
            R.RetrievalRequest(self.new_forged())

    def test_a_subclass_that_skips_init_is_refused(self):
        class Impostor(gate_mod.DisclosureDecision):
            def __init__(self):                       # never calls super()
                pass
        with self.assertRaises(R.RetrievalError):
            R.RetrievalRequest(Impostor())

    def test_stealing_the_issuance_capability_is_not_enough(self):
        """The capability mints an object; only the gate registers one."""
        from bops.research.gate import _ISSUE
        forged = gate_mod.DisclosureDecision(
            gate_mod.ALLOW, 0, 0, payload_query(), R.PUBLIC_WEB, None, _issuer=_ISSUE)
        self.assertFalse(gate_mod.is_gate_issued(forged))
        self.assertFalse(forged.authorised)
        with self.assertRaises(R.RetrievalError):
            R.RetrievalRequest(forged)


# ==========================================================================
# C. Mutation of a genuine decision
# ==========================================================================

class TestDecisionIsImmutable(unittest.TestCase):

    def test_no_attribute_can_be_reassigned(self):
        decision = genuine_allow()
        for name, value in (("decision", gate_mod.ALLOW), ("tier", 0),
                            ("requested_tier", 0), ("query", payload_query()),
                            ("destination", R.Destination("elsewhere")),
                            ("request", None), ("reasons", []), ("failed_checks", []),
                            ("alternative", None), ("operation", "x")):
            with self.assertRaises(R.ResearchError, msg=name):
                setattr(decision, name, value)

    def test_no_attribute_can_be_deleted(self):
        decision = genuine_allow()
        with self.assertRaises(R.ResearchError):
            del decision.decision

    def test_a_refusal_cannot_be_edited_into_an_allow(self):
        refused = R.assess(R.ResearchRequest(
            "x", R.COMPANY, public_terms={"api_key": "sk-live-abcdef123456"}))
        self.assertEqual(refused.decision, gate_mod.REFUSE)
        with self.assertRaises(R.ResearchError):
            refused.decision = gate_mod.ALLOW
        self.assertEqual(refused.decision, gate_mod.REFUSE)
        self.assertFalse(refused.authorised)

    def test_the_tier_cannot_be_lowered_after_assessment(self):
        decision = genuine_tier_two()
        with self.assertRaises(R.ResearchError):
            decision.tier = 0

    def test_an_approval_cannot_be_assigned_around_authorise(self):
        decision = genuine_tier_two()
        forged = R.Approval(decision.query_text, decision.destination, granted=True)
        with self.assertRaises(R.ResearchError):
            decision.approval = forged
        self.assertFalse(decision.authorised)


# ==========================================================================
# D. Binding: the assessed text is the authorised text
# ==========================================================================

class TestBinding(unittest.TestCase):

    def test_query_text_reports_what_was_assessed(self):
        decision = genuine_allow()
        assessed = decision.query_text
        decision.query.text = PAYLOAD                 # the query object is still mutable
        self.assertEqual(decision.query_text, assessed)

    def test_altering_the_query_invalidates_the_authorisation(self):
        decision = genuine_allow()
        decision.query.text = PAYLOAD
        self.assertFalse(decision.binding_intact)
        self.assertFalse(decision.authorised)

    def test_retrieval_refuses_an_altered_query(self):
        decision = genuine_allow()
        decision.query.text = PAYLOAD
        with self.assertRaises(R.RetrievalError):
            R.RetrievalRequest(decision)

    def test_a_destination_cannot_be_repointed_at_all(self):
        """Since M9-B the destination is immutable, so this fails one layer earlier."""
        decision = genuine_allow()
        with self.assertRaises(R.ResearchError):
            decision.destination.provider = "attacker-endpoint"
        self.assertTrue(decision.binding_intact)

    def test_forcing_a_destination_change_still_invalidates_the_binding(self):
        """Defence in depth: even reaching past immutability with `object.__setattr__`,
        the binding captured at issue no longer matches and retrieval refuses."""
        decision = genuine_allow()
        object.__setattr__(decision.destination, "provider", "attacker-endpoint")
        self.assertFalse(decision.binding_intact)
        self.assertFalse(decision.authorised)
        with self.assertRaises(R.RetrievalError):
            R.RetrievalRequest(decision)
        # Restore, so the shared default destination is not left repointed for later tests.
        object.__setattr__(decision.destination, "provider", "public-web-search")

    def test_the_payload_never_reaches_a_retriever_through_substitution(self):
        retriever = spy()
        decision = genuine_allow()
        decision.query.text = PAYLOAD
        try:
            retriever.retrieve(R.RetrievalRequest(decision))
        except R.RetrievalError:
            pass
        self.assertEqual(retriever.calls, [])

    def test_an_authorisation_cannot_be_reused_for_a_different_query(self):
        first, second = genuine_allow(), R.assess(R.ResearchRequest(
            "margin", R.INDUSTRY, public_terms={"industry": "logistics"}))
        self.assertNotEqual(first.query_text, second.query_text)
        self.assertEqual(R.RetrievalRequest(first).query_text, first.query_text)
        self.assertEqual(R.RetrievalRequest(second).query_text, second.query_text)


# ==========================================================================
# E. Serialisation
# ==========================================================================

class TestSerialisationIsNotAuthorisation(unittest.TestCase):

    def test_there_is_no_deserialiser(self):
        for name in ("from_dict", "loads", "from_json", "parse", "deserialize",
                     "deserialise"):
            self.assertFalse(hasattr(gate_mod.DisclosureDecision, name), name)

    def test_a_serialised_decision_is_a_record_not_a_capability(self):
        record = json.loads(json.dumps(genuine_allow().as_dict()))
        self.assertIsInstance(record, dict)
        with self.assertRaises(R.RetrievalError):
            R.RetrievalRequest(record)

    def test_an_edited_serialised_decision_cannot_be_reloaded(self):
        record = genuine_allow().as_dict()
        record["decision"] = gate_mod.ALLOW
        record["transmitted_text"] = PAYLOAD
        with self.assertRaises(R.RetrievalError):
            R.RetrievalRequest(record)


# ==========================================================================
# F. Retrieval boundary
# ==========================================================================

class TestRetrievalBoundary(unittest.TestCase):

    def test_retrieval_request_refuses_every_non_decision(self):
        request = R.ResearchRequest("x", R.MARKET, public_terms={"industry": "y"})
        for bad in (request, R.build(request), PAYLOAD, None, 42, {}, []):
            with self.assertRaises(R.RetrievalError):
                R.RetrievalRequest(bad)

    def test_a_retrieval_request_is_immutable(self):
        built = R.RetrievalRequest(genuine_allow())
        for name in ("query_text", "destination", "decision", "operation"):
            with self.assertRaises(R.RetrievalError, msg=name):
                setattr(built, name, PAYLOAD)

    def test_a_subclassed_retrieval_request_is_refused_at_the_call(self):
        genuine = genuine_allow()

        class Impostor(retrieval_mod.RetrievalRequest):
            def __init__(self):
                for name, value in (("decision", genuine), ("query_text", PAYLOAD),
                                    ("destination", R.PUBLIC_WEB), ("operation", None),
                                    ("subject", "x"), ("category", R.COMPANY),
                                    ("_frozen", True)):
                    object.__setattr__(self, name, value)

        retriever = spy()
        with self.assertRaises(R.RetrievalError):
            retriever.retrieve(Impostor())
        self.assertEqual(retriever.calls, [])

    def test_retrieve_refuses_every_non_request(self):
        retriever = spy()
        for bad in (genuine_allow(), PAYLOAD, None, {}):
            with self.assertRaises(R.RetrievalError):
                retriever.retrieve(bad)
        self.assertEqual(retriever.calls, [])

    def test_a_refused_decision_never_becomes_a_retrieval_request(self):
        refused = R.assess(R.ResearchRequest(
            "x", R.COMPANY, public_terms={"customer_names": "Acme, Globex"}))
        with self.assertRaises(R.RetrievalError):
            R.RetrievalRequest(refused)

    def test_the_retriever_receives_only_the_authorised_text_and_destination(self):
        retriever = spy()
        decision = genuine_allow()
        retriever.retrieve(R.RetrievalRequest(decision))
        self.assertEqual(sorted(retriever.calls[0]), ["destination", "query_text"])
        self.assertEqual(retriever.calls[0]["query_text"], decision.query_text)

    def test_the_retrieval_request_exposes_no_request_context_or_descriptors(self):
        descriptor = agg.rate_descriptor("churn", 8, 100, entity_count=40)
        decision = R.assess(R.ResearchRequest(
            "churn", R.INDUSTRY, public_terms={"business_model": "B2B SaaS"},
            derived_context=[descriptor], requested_tier=1))
        built = R.RetrievalRequest(decision)
        for forbidden in ("public_terms", "derived_context", "context", "descriptors"):
            self.assertFalse(hasattr(built, forbidden), forbidden)


# ==========================================================================
# G. Approval integrity
# ==========================================================================

class TestApprovalIntegrity(unittest.TestCase):

    def test_authorise_is_the_only_route_to_an_approval(self):
        decision = genuine_tier_two()
        self.assertIsNone(decision.approval)
        decision.authorise(R.Approval(decision.query_text, decision.destination,
                                      granted=True))
        self.assertIsNotNone(decision.approval)

    def test_an_ungranted_approval_raises_consent_required(self):
        from bops.errors import ConsentRequiredError
        decision = genuine_tier_two()
        with self.assertRaises(ConsentRequiredError):
            decision.authorise(R.Approval(decision.query_text, decision.destination,
                                          granted=False))

    def test_an_approval_for_other_text_is_refused(self):
        decision = genuine_tier_two()
        with self.assertRaises(R.ResearchError):
            decision.authorise(R.Approval(PAYLOAD, decision.destination, granted=True))

    def test_an_approval_for_another_destination_is_refused(self):
        decision = genuine_tier_two()
        with self.assertRaises(R.ResearchError):
            decision.authorise(R.Approval(decision.query_text,
                                          R.Destination("elsewhere"), granted=True))

    def test_an_allow_decision_cannot_be_authorised(self):
        with self.assertRaises(R.ResearchError):
            genuine_allow().authorise(
                R.Approval("anything", R.PUBLIC_WEB, granted=True))

    def test_a_forged_decision_cannot_be_authorised(self):
        forged = object.__new__(gate_mod.DisclosureDecision)
        object.__setattr__(forged, "_issued", True)
        object.__setattr__(forged, "decision", gate_mod.ALLOW_WITH_APPROVAL)
        with self.assertRaises(R.ResearchError):
            forged.authorise(R.Approval(PAYLOAD, R.PUBLIC_WEB, granted=True))

    def test_a_spent_approval_stops_authorising(self):
        decision = genuine_tier_two()
        approval = R.Approval(decision.query_text, decision.destination, granted=True)
        decision.authorise(approval)
        self.assertTrue(decision.authorised)
        approval.spend()
        self.assertFalse(decision.authorised)
        with self.assertRaises(R.RetrievalError):
            R.RetrievalRequest(decision)

    def test_a_request_supplied_approval_does_not_auto_authorise(self):
        """Approval must be explicit; attaching one to the request is not consent."""
        descriptor = agg.AggregateDescriptor("x", D("1"), agg.RATE, 40,
                                             source_sensitivity=pc.INTERNAL)
        probe = R.assess(R.ResearchRequest("x", R.MARKET,
                                           derived_context=[descriptor],
                                           requested_tier=2))
        smuggled = R.Approval(probe.query_text, probe.destination, granted=True)
        decision = R.assess(R.ResearchRequest("x", R.MARKET,
                                              derived_context=[descriptor],
                                              requested_tier=2, approval=smuggled))
        self.assertFalse(decision.authorised)
        self.assertIsNone(decision.approval)


# ==========================================================================
# H. The genuine paths still work
# ==========================================================================

class TestGenuinePathsUnaffected(unittest.TestCase):

    def test_a_tier_zero_authorisation_retrieves(self):
        decision = genuine_allow()
        self.assertTrue(gate_mod.is_gate_issued(decision))
        self.assertTrue(decision.authorised)
        retriever = spy()
        evidence = retriever.retrieve(R.RetrievalRequest(decision),
                                      as_of="2026-03-01")
        self.assertEqual(len(retriever.calls), 1)
        self.assertEqual(len(evidence), 1)

    def test_a_tier_one_authorisation_retrieves(self):
        descriptor = agg.rate_descriptor("churn", 8, 100, entity_count=40)
        decision = R.assess(R.ResearchRequest(
            "churn", R.INDUSTRY, public_terms={"business_model": "B2B SaaS"},
            derived_context=[descriptor], requested_tier=1))
        self.assertEqual(decision.decision, gate_mod.ALLOW)
        self.assertTrue(R.RetrievalRequest(decision))

    def test_a_tier_two_authorisation_retrieves_exactly_once(self):
        decision = genuine_tier_two()
        approval = R.Approval(decision.query_text, decision.destination, granted=True)
        decision.authorise(approval)
        retriever = spy()
        retriever.retrieve(R.RetrievalRequest(decision), as_of="2026-03-01")
        approval.spend()
        with self.assertRaises(R.RetrievalError):
            R.RetrievalRequest(decision)
        self.assertEqual(len(retriever.calls), 1)

    def test_a_refusal_is_still_a_structured_value_not_an_exception(self):
        refused = R.assess(R.ResearchRequest(
            "x", R.COMPANY, public_terms={"api_key": "sk-live-abcdef123456"}))
        self.assertEqual(refused.decision, gate_mod.REFUSE)
        self.assertTrue(refused.reasons)
        self.assertTrue(refused.alternative)

    def test_the_ledger_entry_still_records_the_decision(self):
        entry = R.ledger_entry(genuine_allow())
        self.assertEqual(entry["decision"], gate_mod.ALLOW)
        self.assertTrue(entry["authorised"])


if __name__ == "__main__":
    unittest.main()
