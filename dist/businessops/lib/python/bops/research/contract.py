"""The external-research contracts: what may be asked, and what comes back when it cannot.

Milestone 9 is the first in which information may leave the machine, so the shapes in this
module are chosen to make the unsafe thing hard to express rather than merely forbidden.

Three ideas do most of the work:

**A request names its subject, never its data.** A `ResearchRequest` carries the entity
being researched, the category, the intent and - optionally - *derived* context in the form
of `AggregateDescriptor`s that the Milestone 3 privacy layer already knows how to judge.
There is no field in which a raw row, a customer name or a ledger extract can be placed, and
`validate()` refuses one that arrives anyway.

**Failure is a value, not an exception.** A research question that cannot be answered safely
is an ordinary outcome - blocked disclosure, no adequate source, conflicting evidence - and
each returns a structured `ResearchFailure` naming the reason and whether a safe alternative
exists. A traceback is not a research answer.

**Nothing here retrieves.** This module has no network access, no I/O and no knowledge of
how retrieval happens; see `retrieval.py` for the boundary and why it can only be crossed
with a gate decision in hand.
"""

from .. import privacy as privacy_mod
from ..privacy import aggregation as aggregation_mod

# -- research categories -----------------------------------------------------

#: Re-exported from `intents.py`, which is the single home for category and intent
#: metadata since M9-D.4 (ADR-0021). They are imported rather than restated so that
#: `contract.COMPANY`, `contract.CATEGORIES` and every existing caller of them keep
#: working without a second definition existing anywhere.
from .intents import (                                              # noqa: E402,F401
    ANALYSIS_CATEGORIES, CATEGORIES, CATEGORY_INTENTS, COMPANY, COMPETITOR, INDUSTRY,
    INTENT_REGISTRY, MARKET, ResearchIntent,
)

#: Human wording, used in refusals so a message names the category the user asked about.
CATEGORY_LABEL = {
    COMPANY: "company research",
    MARKET: "market research",
    COMPETITOR: "competitor research",
    INDUSTRY: "industry research",
}

# -- research intent ---------------------------------------------------------

#: The eleven intent identifiers, and the closed tuple `validate()` checks against, are
#: re-exported from the registry in `intents.py` (ADR-0021). Before M9-D.4 they were
#: declared here and the enumeration was a hand-maintained literal; `INTENTS` is now
#: derived from the registry's declaration order and holds exactly what it always held.
from .intents import (                                              # noqa: E402,F401
    BENCHMARK, COMPARISON, DEFINITION, DRIVERS, INTENTS, LANDSCAPE, OVERVIEW,
    POSITIONING, PROFILE, SIZING, STRUCTURE, TRENDS,
)

# How the enumeration reached eleven, kept here because it explains why four of them are
# shared rather than duplicated - which is the registry's least obvious property:
#
# M9-D.2 added `OVERVIEW` and `DRIVERS` (ADR-0019). The addition was strictly additive:
# the five original intents kept their names, their query wording and their behaviour, so
# `bops-company-analysis` was unaffected. They exist because a market has two research
# questions a company does not - *what is this market* and *what moves it* - and the
# nearest existing intent, `PROFILE`, phrases itself as "company profile", which would
# have sent a market question looking for company pages.
#
# M9-D.3 added `LANDSCAPE` and `COMPARISON` on the same terms (ADR-0020), and reused
# `POSITIONING` and `TRENDS` rather than minting competitor-specific twins of questions
# the enumeration already asks. Competitor research has two questions no earlier skill
# had - *who competes here* and *how do these named entities compare* - and neither has
# an existing intent whose query wording expresses it. The other two do: `POSITIONING`
# is already documented as "how entities compare publicly", and `TRENDS` is already the
# intent `bops-company-analysis` uses for recent developments.
#
# M9-D.4 changed where that table lives, not what is in it (ADR-0021).
#
# M9-D.5 added `DEFINITION` and `STRUCTURE` for industry research and reused `SIZING`,
# `TRENDS` and `DRIVERS`, on the same test. The full reasoning lives beside the records
# in `intents.py`, which is where the table is.

# -- outcome status ----------------------------------------------------------

OK = "ok"
BLOCKED = "blocked"                    # the disclosure gate refused
APPROVAL_REQUIRED = "approval_required"
UNAVAILABLE = "unavailable"            # retrieval could not run
INSUFFICIENT_EVIDENCE = "insufficient_evidence"
AMBIGUOUS = "ambiguous"
INVALID_REQUEST = "invalid_request"

STATUSES = (OK, BLOCKED, APPROVAL_REQUIRED, UNAVAILABLE, INSUFFICIENT_EVIDENCE,
            AMBIGUOUS, INVALID_REQUEST)

# -- reason codes ------------------------------------------------------------
#
# Stable identifiers so a caller can branch on the reason without parsing prose, and so a
# test can assert the *reason* rather than the wording.

REASON_PROHIBITED_CONTENT = "prohibited_content"
REASON_UNRESOLVED_SENSITIVITY = "unresolved_sensitivity"
REASON_TIER_NOT_PERMITTED = "tier_not_permitted"
REASON_AGGREGATION_FLOOR = "aggregation_floor"
REASON_BANDING = "banding"
REASON_REIDENTIFICATION = "reidentification"
REASON_DESTINATION_NOT_PERMITTED = "destination_not_permitted"
REASON_APPROVAL_REQUIRED = "approval_required"
REASON_APPROVAL_MISMATCH = "approval_mismatch"
REASON_RETRIEVAL_UNAVAILABLE = "retrieval_unavailable"
REASON_SOURCE_UNAVAILABLE = "source_unavailable"
REASON_NO_ADEQUATE_SOURCE = "no_adequate_source"
REASON_STALE_ONLY = "stale_only_evidence"
REASON_CONFLICTING = "conflicting_evidence"
REASON_INVALID_PROVENANCE = "invalid_provenance"
REASON_UNSUPPORTED_CATEGORY = "unsupported_category"
REASON_AMBIGUOUS_TIER = "ambiguous_tier"
REASON_AMBIGUOUS_SUBJECT = "ambiguous_subject"
#: ADR-0050. A request fragment carries a value from the workspace's business data.
REASON_INTERNAL_VALUE = "internal_business_value"
#: ADR-0050. The workspace's business data could not be screened, so nothing is sent.
REASON_BOUNDARY_UNVERIFIABLE = "internal_boundary_unverifiable"

# -- prohibited content ------------------------------------------------------

#: Field names that must never appear in a research request. Matched on the *key*, so a
#: caller cannot smuggle a ledger in by calling it something plausible - the check is
#: deliberately about shape, and `validate()` additionally refuses any value that is a
#: collection of rows.
PROHIBITED_KEYS = frozenset({
    "rows", "records", "transactions", "transaction", "ledger", "raw", "raw_data",
    "customer", "customers", "customer_name", "customer_names", "contact", "contacts",
    "email", "emails", "phone", "credential", "credentials", "token", "tokens",
    "api_key", "apikey", "secret", "secrets", "password", "account_number", "iban",
    "card", "card_number", "ssn", "national_id",
})


class ResearchError(Exception):
    """A research request or result violates its contract - a defect, not a user error."""


def _plain(value):
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if hasattr(value, "as_dict"):
        return value.as_dict()
    return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)


class Destination:
    """Where a query would be sent, and whether that is permitted at all.

    Named rather than implied because ADR-0009 requires the user to see the destination
    alongside the text at Tier 2, and because approval is tied to a destination: approving
    a query for one provider must not authorise the same query to another.
    """

    __slots__ = ("provider", "kind", "description", "_frozen")

    #: The only retrieval kind M9 contemplates. An MCP-connected source is Milestone 12 and
    #: would need its own entry plus its own review.
    PUBLIC_WEB = "public_web"

    def __init__(self, provider, kind=PUBLIC_WEB, description=None):
        self.provider = provider
        self.kind = kind
        self.description = description
        self._frozen = True

    def __setattr__(self, name, value):
        """Immutable once built.

        `PUBLIC_WEB` below is a module-level singleton shared by every request that does
        not name a destination. While it was mutable, anything holding a reference could
        repoint the default destination for the whole process - and an authorisation bound
        to `kind:provider` would then be bound to the attacker's endpoint. Found when a
        test that mutated it silently changed the destination seen by every later test.
        """
        if getattr(self, "_frozen", False):
            raise ResearchError(
                "a destination is immutable; %r cannot be changed. Build a new "
                "Destination rather than repointing an existing one." % name)
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        raise ResearchError("a destination is immutable")

    @property
    def permitted(self):
        """Only public-web retrieval is permitted in M9."""
        return self.kind == self.PUBLIC_WEB

    def identity(self):
        """The value approval is bound to."""
        return "%s:%s" % (self.kind, self.provider)

    def as_dict(self):
        return {"provider": self.provider, "kind": self.kind,
                "description": self.description, "permitted": self.permitted}

    def __eq__(self, other):
        return isinstance(other, Destination) and self.identity() == other.identity()

    def __hash__(self):
        return hash(self.identity())

    def __repr__(self):
        return "Destination(%s)" % self.identity()


#: The default destination: ordinary public web search, no provider preference.
PUBLIC_WEB = Destination("public-web-search")


class Approval:
    """One granted Tier-2 disclosure. Single-use, and bound to what was shown.

    ADR-0010 makes approval per-action and non-transferable, so an `Approval` is not a flag
    meaning "the user said yes". It records *which* text, to *which* destination, and is
    spent when used. Every reuse path a caller might reach for - same query different
    destination, same destination different query, a second use of the same object - is a
    mismatch rather than a convenience.
    """

    __slots__ = ("query_text", "destination", "granted", "_spent")

    def __init__(self, query_text, destination, granted=False):
        self.query_text = query_text
        self.destination = destination
        self.granted = bool(granted)
        self._spent = False

    @property
    def spent(self):
        return self._spent

    def matches(self, query_text, destination):
        """Whether this approval authorises exactly this disclosure, and is still unspent."""
        if not self.granted or self._spent:
            return False
        if self.query_text != query_text:
            return False
        return Destination.identity(self.destination) == Destination.identity(destination)

    def spend(self):
        """Consume the approval. A second call authorises nothing."""
        if self._spent:
            raise ResearchError("this approval has already been used; approval is "
                                "single-use and cannot authorise a second disclosure")
        self._spent = True
        return self

    def as_dict(self):
        return {"query_text": self.query_text,
                "destination": self.destination.as_dict()
                if isinstance(self.destination, Destination) else str(self.destination),
                "granted": self.granted, "spent": self._spent}

    def __repr__(self):
        return "Approval(granted=%s, spent=%s)" % (self.granted, self._spent)


class ResearchRequest:
    """One external research question, with everything the gate needs to judge it.

    The shape is the point. `subject`, `category` and `intent` describe *what is being
    asked about*; `public_terms` carries the non-confidential vocabulary a Tier 0 query is
    built from; `derived_context` carries `AggregateDescriptor`s and nothing else. There is
    no field for a row, a name or a figure, so the common way to leak - passing data
    "just as context" - has nowhere to go.
    """

    __slots__ = ("subject", "category", "intent", "purpose", "public_terms",
                 "derived_context", "requested_tier", "destination", "approval",
                 "operation", "source_requirements", "notes")

    def __init__(self, subject, category, intent=BENCHMARK, purpose=None,
                 public_terms=None, derived_context=(), requested_tier=0,
                 destination=None, approval=None, operation=None,
                 source_requirements=None, notes=None):
        self.subject = subject
        self.category = category
        self.intent = intent
        self.purpose = purpose
        self.public_terms = dict(public_terms or {})
        self.derived_context = list(derived_context)
        self.requested_tier = requested_tier
        self.destination = destination or PUBLIC_WEB
        self.approval = approval
        self.operation = operation
        self.source_requirements = source_requirements
        self.notes = list(notes or [])

    # -- derived views ------------------------------------------------------

    def narrowing_attributes(self):
        """Attribute names in this request that narrow toward one organisation.

        Read from the public terms rather than declared separately, so the thing judged for
        re-identification is the thing actually being sent.
        """
        return tuple(sorted(
            key for key in self.public_terms
            if key in aggregation_mod.NARROWING_ATTRIBUTES))

    def sensitivity(self):
        """The strictest class across the derived context, or `public` when there is none.

        A Tier 0 request carries no derived context at all, so its sensitivity is that of
        the public terms - which is `public` by construction, because anything else is
        refused by `validate()`.
        """
        classes = [d.source_sensitivity for d in self.derived_context]
        if not classes:
            return privacy_mod.PUBLIC
        return privacy_mod.most_sensitive(classes)

    def has_unresolved_sensitivity(self):
        return any(not d.sensitivity_resolved for d in self.derived_context)

    # -- validation ---------------------------------------------------------

    def validate(self):
        """Structural refusal of anything that must never be asked. Returns reasons.

        An empty list means the request is *well-formed*, not that it may be disclosed -
        that is the gate's decision and this method deliberately does not anticipate it.
        """
        problems = []

        if self.category not in CATEGORIES:
            problems.append((REASON_UNSUPPORTED_CATEGORY,
                             "%r is not a supported research category; M9 covers %s."
                             % (self.category, ", ".join(CATEGORIES))))
        if self.intent not in INTENTS:
            problems.append((REASON_AMBIGUOUS_SUBJECT,
                             "%r is not a recognised research intent." % (self.intent,)))
        if not self.subject or not str(self.subject).strip():
            problems.append((REASON_AMBIGUOUS_SUBJECT,
                             "The research subject is empty; there is nothing to research."))
        if self.requested_tier not in (0, 1, 2):
            problems.append((REASON_AMBIGUOUS_TIER,
                             "Requested tier %r is not 0, 1 or 2. Tier 3 material has no "
                             "approval path and cannot be requested."
                             % (self.requested_tier,)))

        problems.extend(self._prohibited_content_problems())

        if self.has_unresolved_sensitivity():
            problems.append((REASON_UNRESOLVED_SENSITIVITY,
                             "One or more derived values carry unresolved sensitivity. An "
                             "unclassified aggregate is not assumed safe."))
        return problems

    def _prohibited_content_problems(self):
        """Refuse raw records, names, transactions and secrets wherever they are hidden."""
        problems = []
        for key, value in sorted(self.public_terms.items()):
            lowered = str(key).lower()
            if lowered in PROHIBITED_KEYS:
                problems.append((REASON_PROHIBITED_CONTENT,
                                 "The term %r names data that may never be transmitted at "
                                 "any tier." % key))
                continue
            # A public term is a term, not a table. Anything iterable-but-not-text is a
            # collection of records wearing a different name.
            if isinstance(value, (list, tuple, set, dict)):
                problems.append((REASON_PROHIBITED_CONTENT,
                                 "The term %r carries a collection of values; a query term "
                                 "is a single public value, never a set of records." % key))

        for descriptor in self.derived_context:
            if not privacy_mod.is_externalizable(descriptor.source_sensitivity):
                problems.append((REASON_PROHIBITED_CONTENT,
                                 "%r is derived from %s data, which has no approval path "
                                 "at any tier."
                                 % (descriptor.label, descriptor.source_sensitivity)))
            label = str(descriptor.label).lower()
            if any(token in label for token in ("customer name", "transaction", "ledger",
                                                "credential", "token", "secret")):
                problems.append((REASON_PROHIBITED_CONTENT,
                                 "%r names prohibited material." % descriptor.label))
        return problems

    @property
    def valid(self):
        return not self.validate()

    def as_dict(self):
        return {
            "subject": self.subject, "category": self.category, "intent": self.intent,
            "purpose": self.purpose, "public_terms": _plain(self.public_terms),
            "derived_context": [d.as_dict() for d in self.derived_context],
            "requested_tier": self.requested_tier,
            "destination": self.destination.as_dict(),
            "operation": self.operation,
            "narrowing_attributes": list(self.narrowing_attributes()),
            "sensitivity": self.sensitivity(),
            "source_requirements": self.source_requirements,
            "notes": list(self.notes),
        }

    def __repr__(self):
        return "ResearchRequest(%s/%s: %r, tier=%s)" % (
            self.category, self.intent, self.subject, self.requested_tier)


class ResearchFailure:
    """A research question that could not be answered safely - an outcome, not an error.

    Carries a machine-readable `reason` so a caller can branch, prose so a person can
    understand, and `alternative` because ADR-0009 requires a refusal to offer the Tier 0
    path where one exists. The alternative is a description, never the prohibited value.
    """

    __slots__ = ("status", "reason", "explanation", "alternative", "details")

    def __init__(self, status, reason, explanation, alternative=None, details=None):
        if status not in STATUSES:
            raise ResearchError("unknown research status %r" % (status,))
        self.status = status
        self.reason = reason
        self.explanation = explanation
        self.alternative = alternative
        self.details = dict(details or {})

    @property
    def ok(self):
        return False

    @property
    def has_alternative(self):
        return bool(self.alternative)

    def as_dict(self):
        record = {"status": self.status, "reason": self.reason,
                  "explanation": self.explanation, "alternative": self.alternative,
                  "has_alternative": self.has_alternative,
                  "details": _plain(self.details)}
        return {k: v for k, v in record.items() if v not in (None, {}, [])}

    def __repr__(self):
        return "ResearchFailure(%s/%s)" % (self.status, self.reason)


def failure(status, reason, explanation, alternative=None, **details):
    """Shorthand used throughout the research layer."""
    return ResearchFailure(status, reason, explanation, alternative, details or None)
