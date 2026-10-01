"""Query construction: the smallest external question that answers the research request.

Two properties matter more than the wording it produces.

**Deterministic.** The same request builds the same query, byte for byte. Terms are emitted
in a fixed order rather than dictionary order, so a test can assert an exact string and a
gate decision can be reproduced from an audit record.

**It decides nothing.** The builder assembles a *candidate* query and reports what that
candidate would disclose. Whether it may be sent is `gate.assess()`'s decision, and the
builder has no ability to conclude that something is safe because the caller said so - the
caller's assertion is not an input to it. This separation is why `build()` returns a
`CandidateQuery` rather than a string: a bare string could be handed to retrieval by a
caller who skipped the gate, and a `CandidateQuery` carries no authorisation.

Tier 0 is the default and the ordinary case: a query built only from public terms. ADR-0009
observes that comparative questions ("is our margin typical?") do not need the internal
figure at all - they need the benchmark, which is a public fact. So the builder's job on
almost every request is to name a subject and its public context, and leave the comparison
to be computed locally afterwards.
"""

from .. import privacy as privacy_mod
from . import contract as contract_mod

#: Public term keys emitted into a query, in this order. Fixed rather than sorted so the
#: phrasing reads naturally ("B2B SaaS churn rate benchmark 2026") while staying
#: deterministic. A key not listed here is still emitted, after these, in sorted order.
TERM_ORDER = (
    "business_model", "industry", "product_category", "geographic_market", "region",
    "size_band", "employee_band", "revenue_band", "founding_year", "period",
)

#: Words that express the intent in the query itself, and the intents whose query reads
#: naturally with the subject first.
#:
#: Both were hand-written tables here until M9-D.4. They are now **views of the
#: research-intent registry** (`intents.py`, ADR-0021), imported under their existing names
#: so every caller and test that reads `query.INTENT_TERMS` or `query.SUBJECT_LEADS` keeps
#: working. Their contents are unchanged, byte for byte, and they are read-only: the query
#: builder looks intent wording up, and nothing in the pipeline may write it.
#:
#: Where an intent's phrasing needs to change, it changes in the registry record. A local
#: table here would be a second opinion about the same question, and the two would
#: eventually disagree about a word that ends up inside a gated query.
from .intents import INTENT_TERMS, SUBJECT_LEADS                   # noqa: E402,F401


class CandidateQuery:
    """A query that has been built but not authorised.

    Deliberately not a string. Retrieval accepts only a gate decision, so an object that
    cannot be mistaken for an approved query is the point of the type.
    """

    __slots__ = ("text", "terms", "subject", "category", "intent", "tier",
                 "destination", "descriptors", "narrowing_attributes")

    def __init__(self, text, terms, subject, category, intent, tier, destination,
                 descriptors=(), narrowing_attributes=()):
        self.text = text
        self.terms = list(terms)
        self.subject = subject
        self.category = category
        self.intent = intent
        self.tier = tier
        self.destination = destination
        self.descriptors = list(descriptors)
        self.narrowing_attributes = tuple(narrowing_attributes)

    @property
    def discloses_derived_context(self):
        return bool(self.descriptors)

    def as_dict(self):
        return {"text": self.text, "terms": list(self.terms), "subject": self.subject,
                "category": self.category, "intent": self.intent,
                "requested_tier": self.tier,
                "destination": self.destination.as_dict(),
                "narrowing_attributes": list(self.narrowing_attributes),
                "derived_values": [d.as_dict() for d in self.descriptors]}

    def __repr__(self):
        return "CandidateQuery(%r, tier=%s)" % (self.text[:60], self.tier)


def _ordered_terms(public_terms):
    """Public terms in a fixed, reproducible order."""
    known = [(k, public_terms[k]) for k in TERM_ORDER if k in public_terms]
    extra = [(k, public_terms[k]) for k in sorted(public_terms) if k not in TERM_ORDER]
    return known + extra


def _term_text(value):
    return str(value).strip()


def build(request):
    """Build the candidate query for one research request.

    Only `public` Business Context terms reach the text. A term whose class is anything
    else is dropped here *and* would be refused by the gate - two independent refusals,
    because this one is convenience and the gate's is the guarantee.
    """
    parts, terms = [], []

    for key, value in _ordered_terms(request.public_terms):
        text = _term_text(value)
        if not text:
            continue
        terms.append({"key": key, "value": text})
        parts.append(text)

    subject = _term_text(request.subject)
    if subject and subject not in parts:
        # The subject leads for entity research and trails for a benchmark, which is how
        # a person would phrase each.
        if request.intent in SUBJECT_LEADS:
            parts.insert(0, subject)
        else:
            parts.append(subject)

    # The intent word is dropped when the subject already says it, so a request about
    # "market trends" does not build "market trends trends".
    intent_term = INTENT_TERMS.get(request.intent)
    if intent_term and intent_term.lower() not in " ".join(parts).lower():
        parts.append(intent_term)

    # Derived context is appended only as a *banded* description, never as a raw value.
    # The gate decides whether it may be there at all; this is how it looks if permitted.
    descriptors = []
    for descriptor in request.derived_context:
        descriptors.append(descriptor)
        parts.append(_descriptor_phrase(descriptor))

    text = " ".join(p for p in parts if p)

    return CandidateQuery(
        text=text, terms=terms, subject=request.subject, category=request.category,
        intent=request.intent, tier=request.requested_tier,
        destination=request.destination, descriptors=descriptors,
        narrowing_attributes=request.narrowing_attributes())


def _descriptor_phrase(descriptor):
    """How a derived value appears in a query: banded or as a rate, never exact."""
    return "%s %s" % (descriptor.label, descriptor.value)


def safe_public_terms(public_terms):
    """Public terms with anything prohibited removed.

    Used when building the alternative offered alongside a refusal. A refusal that
    explained itself by printing the API key it had just declined to send would leak the
    value through the very message meant to protect it, so the alternative is built from
    the terms that survive the prohibition check rather than from the original request.
    """
    safe = {}
    for key, value in (public_terms or {}).items():
        if str(key).lower() in contract_mod.PROHIBITED_KEYS:
            continue
        if isinstance(value, (list, tuple, set, dict)):
            continue
        safe[key] = value
    return safe


def tier_zero_alternative(request):
    """The Tier 0 query that answers the same question without internal values.

    ADR-0009 requires a refusal to offer this where one exists, and it almost always does:
    strip the derived context and the question becomes a request for a public benchmark,
    which is what the user actually needed.
    """
    stripped = contract_mod.ResearchRequest(
        subject=request.subject, category=request.category, intent=request.intent,
        purpose=request.purpose,
        public_terms=safe_public_terms(request.public_terms),
        derived_context=(), requested_tier=0, destination=request.destination,
        operation=request.operation)
    candidate = build(stripped)
    return {"text": candidate.text, "tier": 0,
            "explanation": ("The same question can be answered by retrieving the public "
                            "benchmark and comparing locally, with no internal value "
                            "transmitted.")}


def public_terms_from_context(context, class_map=None):
    """Extract the externalizable Business Context values a Tier 0 query may use.

    Reads the schema's `x-privacy` annotations through the Milestone 1 helper rather than
    deciding for itself which fields are public - that classification has one home, and it
    is the schema.
    """
    from ..context import privacy as context_privacy

    if class_map is None:
        return {}
    subset = context_privacy.externalizable_subset(context, class_map)
    flat = {}
    for path, value in sorted(_flatten(subset).items()):
        if value in (None, "", [], {}):
            continue
        flat[path.split(".")[-1]] = value
    return flat


def _flatten(mapping, prefix=""):
    out = {}
    for key, value in (mapping or {}).items():
        path = "%s.%s" % (prefix, key) if prefix else key
        if isinstance(value, dict):
            out.update(_flatten(value, path))
        else:
            out[path] = value
    return out
