"""External research: the disclosure boundary and everything that crosses it.

Milestone 9-A. This package builds the path an external question travels and the gate that
stands in it. It performs **no retrieval** - there is no network call anywhere in it - and
it defines no research skill or command; those are later sub-milestones consuming this core.

    ResearchRequest      contract.py      what may be asked, and what a refusal looks like
    CandidateQuery       query.py         the smallest query that answers it, deterministic
    DisclosureDecision   gate.py          the one authoritative decision
    RetrievalRequest     retrieval.py     constructible only from an authorised decision
    EvidenceSet          evidence_set.py  retrieved material, held as untrusted data
    source tiers         sources.py       quality, freshness and disagreement

The single ordering the package exists to guarantee:

    request -> query -> GATE -> retrieval -> evidence -> claims

No path skips the gate, because `RetrievalRequest` cannot be built without its output, and
nothing downstream re-opens the decision: retrieved content is data, and a page cannot raise
a tier it arrived after.

Privacy policy is not reimplemented here. `privacy/aggregation.py` already joins the
class-to-tier rule to the four ADR-0009 checks; this package supplies what a query has that
an aggregate does not - a destination, an approval, an operation - and defers on the rest.
"""

from .contract import (                                              # noqa: F401
    AMBIGUOUS, APPROVAL_REQUIRED, BENCHMARK, BLOCKED, CATEGORIES, CATEGORY_LABEL,
    COMPANY, COMPARISON, COMPETITOR, DEFINITION, DRIVERS, INDUSTRY,
    INSUFFICIENT_EVIDENCE, INTENTS, LANDSCAPE,
    INVALID_REQUEST, MARKET, OK, OVERVIEW, POSITIONING, PROFILE, PUBLIC_WEB, SIZING,
    STATUSES, STRUCTURE, TRENDS, UNAVAILABLE,
    Approval, Destination, ResearchError, ResearchFailure, ResearchRequest, failure,
)
from .intents import (                                               # noqa: F401
    ANALYSIS_CATEGORIES, CATEGORY_INTENTS, INTENT_REGISTRY, INTENT_TERMS, SUBJECT_LEADS,
    ResearchIntent, categories_for_intent, intent, intents_for_category,
)
from .gate import (                                                  # noqa: F401
    ALLOW, ALLOW_WITH_APPROVAL, DECISIONS, REFUSE, DisclosureDecision, assess,
    is_gate_issued, ledger_entry, record_disclosure,
)
from .query import CandidateQuery, build, tier_zero_alternative     # noqa: F401
from .retrieval import (                                            # noqa: F401
    FixtureRetriever, NullRetriever, RetrievalError, RetrievalRequest, Retriever,
)
from .evidence_set import (                                         # noqa: F401
    EvidenceError, EvidenceItem, EvidenceSet, UNTRUSTED, evidence_id,
)
from .scout import (                                                # noqa: F401
    ACCEPTED_RECORD_FIELDS, MAX_CONTENT_CHARS, MAX_EVIDENCE_ITEMS, MAX_FETCHED,
    MAX_QUERY_CHARS, MAX_RESULTS, RESULT_FAILED, RESULT_NO_SOURCE, RESULT_OK,
    RESULT_STATUSES, SCOUT_RESULT_ENVELOPE, SCOUT_REPLY_PROTOCOL, RECORD_TOKEN,
    END_TOKEN, NO_TERMINATOR, COUNT_MISMATCH, MALFORMED_RECORD,
    UNTRUSTED_EXTERNAL_DATA, RecordingTransport,
    ScoutBrief, ScoutError, ScoutRetriever, ScoutTransport, UnavailableTransport,
    candidate_claim, normalise_records, parse_reply, parse_result, render_reply,
)
from .handoff import (                                              # noqa: F401
    AUTHORISED, NOT_AUTHORISED, close_retrieval, close_retrieval_object, open_retrieval,
)
from .handback import HandbackError                                 # noqa: F401
from .handback import reply as handback_reply                       # noqa: F401
from . import sources                                               # noqa: F401

__all__ = [
    # M14-6: the scout's reply as the harness captured it (ADR-0053)
    "handback_reply", "HandbackError",
    # request and outcomes
    "ResearchRequest", "ResearchFailure", "ResearchError", "failure",
    "Destination", "PUBLIC_WEB", "Approval",
    "CATEGORIES", "COMPANY", "MARKET", "COMPETITOR", "INDUSTRY", "CATEGORY_LABEL",
    "INTENTS", "BENCHMARK", "PROFILE", "SIZING", "TRENDS", "POSITIONING",
    "OVERVIEW", "DRIVERS", "LANDSCAPE", "COMPARISON",
    # M9-D.5 industry research
    "DEFINITION", "STRUCTURE",
    # research-intent registry (M9-D.4, ADR-0021) - the canonical table the names above
    # are views of
    "INTENT_REGISTRY", "ResearchIntent", "CATEGORY_INTENTS", "ANALYSIS_CATEGORIES",
    "INTENT_TERMS", "SUBJECT_LEADS", "intent", "intents_for_category",
    "categories_for_intent",
    "STATUSES", "OK", "BLOCKED", "APPROVAL_REQUIRED", "UNAVAILABLE",
    "INSUFFICIENT_EVIDENCE", "AMBIGUOUS", "INVALID_REQUEST",
    # query
    "CandidateQuery", "build", "tier_zero_alternative",
    # gate
    "assess", "DisclosureDecision", "ALLOW", "ALLOW_WITH_APPROVAL", "REFUSE",
    "DECISIONS", "record_disclosure", "ledger_entry", "is_gate_issued",
    # retrieval boundary
    "RetrievalRequest", "Retriever", "NullRetriever", "FixtureRetriever",
    "RetrievalError",
    # evidence
    "EvidenceSet", "EvidenceItem", "EvidenceError", "evidence_id", "UNTRUSTED",
    "sources",
    # scout boundary (M9-B)
    "ScoutBrief", "ScoutRetriever", "ScoutTransport", "UnavailableTransport",
    "RecordingTransport", "ScoutError", "normalise_records", "candidate_claim",
    "UNTRUSTED_EXTERNAL_DATA", "MAX_RESULTS", "MAX_FETCHED", "MAX_CONTENT_CHARS",
    "MAX_EVIDENCE_ITEMS", "MAX_QUERY_CHARS", "ACCEPTED_RECORD_FIELDS",
    "SCOUT_RESULT_ENVELOPE", "RESULT_STATUSES", "RESULT_OK", "RESULT_NO_SOURCE",
    "RESULT_FAILED",
    # the adopted production scout contract (ADR-0017)
    "parse_reply", "render_reply", "parse_result", "SCOUT_REPLY_PROTOCOL",
    "RECORD_TOKEN", "END_TOKEN", "NO_TERMINATOR", "COUNT_MISMATCH",
    "MALFORMED_RECORD",
    # model-mediated handoff (M9-B vertical slice)
    "open_retrieval", "close_retrieval", "close_retrieval_object",
    "AUTHORISED", "NOT_AUTHORISED",
]
