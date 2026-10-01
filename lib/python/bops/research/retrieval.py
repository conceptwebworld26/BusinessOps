"""The retrieval boundary. Nothing here retrieves anything.

Milestone 9-A builds the *shape* of retrieval and leaves the act of it to 9-B, so this
module contains no network call, no HTTP client and no tool invocation. What it does
contain is the reason a caller cannot skip the gate:

    RetrievalRequest.__init__ accepts a DisclosureDecision, not a query.

There is no constructor taking a string, no keyword that bypasses the check, and an
unauthorised decision raises. A caller who wants to retrieve must hold a decision the gate
produced and, at Tier 2, an approval matching that exact text and destination. The ordering
"gate, then retrieve" is therefore not a convention anyone has to remember - it is the only
way to build the object retrieval consumes.

The second boundary is what comes back. `Retriever.retrieve()` returns an `EvidenceSet`
whose every item is untrusted data, and this module never re-reads the gate decision
afterwards. Retrieved text cannot raise a tier, alter a query or trigger another retrieval,
because nothing here consults it for those purposes - the decision is immutable once made,
and the code that made it has already finished.
"""

from . import contract as contract_mod
from . import evidence_set as evidence_mod
from . import gate as gate_mod


class RetrievalError(contract_mod.ResearchError):
    """A retrieval was attempted without a valid, authorised disclosure decision."""


class RetrievalRequest:
    """A query cleared for transmission. Constructible only from an authentic authorisation.

    Four checks, and the first two are the ones that matter. `isinstance` would accept a
    subclass that never ran `__init__`, and a type check accepts anything of that shape, so
    neither establishes that the gate ran. What does is asking the gate whether it issued
    *this object*: `is_gate_issued` is an identity question against a registry only
    `assess()` writes to, which a forged, subclassed or `object.__new__`-constructed
    decision cannot satisfy however convincing it looks.

    Frozen after construction for the same reason the decision is: an authorisation that
    can be edited between the check and the call authorises nothing.
    """

    __slots__ = ("decision", "query_text", "destination", "operation", "subject",
                 "category", "_frozen")

    def __init__(self, decision):
        if type(decision) is not gate_mod.DisclosureDecision:
            raise RetrievalError(
                "retrieval accepts only a DisclosureDecision produced by the disclosure "
                "gate; a raw query, a ResearchRequest or a look-alike cannot be retrieved")
        if not gate_mod.is_gate_issued(decision):
            raise RetrievalError(
                "this decision was not issued by the disclosure gate. Retrieval requires "
                "an authorisation gate.assess() actually produced, not an object of the "
                "same type")
        if decision.refused:
            raise RetrievalError(
                "the disclosure gate refused this query; retrieval must not run. %s"
                % ("; ".join(decision.reasons) or ""))
        if not decision.binding_intact:
            raise RetrievalError(
                "the query or destination has been altered since the gate assessed it; "
                "what would be transmitted is not what was authorised")
        if not decision.authorised:
            raise RetrievalError(
                "this disclosure requires explicit per-query approval that has not been "
                "granted; call decision.authorise(approval) with an approval matching "
                "this exact text and destination")

        self.decision = decision
        # Read from the decision's binding, never from the mutable query object.
        self.query_text = decision.query_text
        self.destination = decision.destination
        self.operation = decision.operation
        self.subject = decision.request.subject if decision.request else None
        self.category = decision.request.category if decision.request else None
        self._frozen = True

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False):
            raise RetrievalError(
                "a retrieval request is immutable once built; %r cannot be changed. "
                "Re-run the gate for different terms." % name)
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        raise RetrievalError("a retrieval request is immutable once built")

    @property
    def tier(self):
        return self.decision.tier

    def as_dict(self):
        return {"query_text": self.query_text,
                "destination": self.destination.as_dict(),
                "tier": self.tier, "operation": self.operation,
                "subject": self.subject, "category": self.category}

    def __repr__(self):
        return "RetrievalRequest(%r, tier=%s)" % (self.query_text[:50], self.tier)


class Retriever:
    """The retrieval interface. M9-A ships the boundary; M9-B ships an implementation.

    A subclass implements `_fetch`, which receives the approved query text and returns raw
    source records. It never sees the `ResearchRequest`, the Business Context or any
    descriptor - only the string the gate cleared - so an implementation has nothing
    internal to leak even if it wanted to.
    """

    #: Set by a subclass that can actually retrieve.
    available = False
    name = "abstract"

    def retrieve(self, request, as_of=None):
        """Retrieve for an approved request. Returns an `EvidenceSet` or a failure.

        Re-verifies the authorisation at the point of use rather than trusting that
        construction checked it. `RetrievalRequest` could be subclassed, and an
        authorisation could in principle be invalidated between building the request and
        calling this - so the check that matters is repeated where the call actually
        happens, which costs nothing and removes a window.
        """
        if type(request) is not RetrievalRequest:
            raise RetrievalError(
                "retrieve() accepts only a RetrievalRequest built from an authorised "
                "disclosure decision")
        if not gate_mod.is_gate_issued(request.decision):
            raise RetrievalError(
                "the authorisation behind this request was not issued by the disclosure "
                "gate")
        if not request.decision.authorised or not request.decision.binding_intact:
            raise RetrievalError(
                "the authorisation behind this request is no longer valid; retrieval "
                "must not run")

        if not self.available:
            return contract_mod.failure(
                contract_mod.UNAVAILABLE,
                contract_mod.REASON_RETRIEVAL_UNAVAILABLE,
                "No retrieval backend is available. Live retrieval runs only through "
                "the bops-research-scout agent, dispatched by the research commands; "
                "this retriever performs none.",
                alternative=None, retriever=self.name)

        records = self._fetch(request.query_text, request.destination)
        return self._to_evidence(request, records, as_of=as_of)

    def _fetch(self, query_text, destination):        # pragma: no cover - abstract
        raise NotImplementedError(
            "a Retriever subclass implements _fetch(query_text, destination)")

    def _to_evidence(self, request, records, as_of=None):
        """Wrap raw records as untrusted evidence. Shared by every implementation."""
        evidence = evidence_mod.EvidenceSet(
            operation=request.operation, subject=request.subject,
            category=request.category, query_text=request.query_text,
            destination=request.destination.as_dict(), disclosure_tier=request.tier)
        for record in records or []:
            evidence.add(evidence_mod.EvidenceItem(
                source=record.get("source"), reference=record.get("reference"),
                source_tier=record.get("source_tier"),
                retrieved_at=record.get("retrieved_at"),
                title=record.get("title"),
                publication_date=record.get("publication_date"),
                source_type=record.get("source_type"),
                content=record.get("content"),
                claim_kind=record.get("claim_kind", "financials"),
                operation=request.operation, as_of=as_of))
        return evidence


class NullRetriever(Retriever):
    """The M9-A default: structurally correct, deliberately incapable.

    Its existence lets the whole path be exercised end to end - request, gate, approval,
    retrieval boundary, evidence set - and proves the ordering holds, while guaranteeing
    that no network call can occur in this milestone.
    """

    available = False
    name = "null"


class FixtureRetriever(Retriever):
    """Returns pre-supplied records. For deterministic tests only, never for production.

    Takes the same path as a real retriever, so an adversarial fixture - a page whose text
    contains instructions - exercises exactly the code a live page would.
    """

    name = "fixture"

    def __init__(self, records=()):
        self.records = list(records)
        self.available = True
        self.calls = []

    def _fetch(self, query_text, destination):
        # Recorded so a test can assert retrieval ran once, or not at all.
        self.calls.append({"query_text": query_text,
                           "destination": destination.identity()})
        return self.records
