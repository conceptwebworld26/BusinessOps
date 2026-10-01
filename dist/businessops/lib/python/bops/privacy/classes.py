"""Sensitivity classes — the single home for the vocabulary (ADR-0009, ADR-0012).

ADR-0009 defines four *disclosure tiers* (what may leave the machine, and under what
approval). This module defines the *field* classification that feeds them, at the finer
granularity ADR-0009 requires: "Classification is a property of the data, not the query:
every field carries a sensitivity class from ingestion onward."

Six classes, ordered by increasing sensitivity, each mapping to the highest disclosure tier
it is permitted at:

    public          tier 0   non-identifying; may be used to build a benchmark query
    derived_safe    tier 1   safe only as an aggregate that passes the ADR-0009 checks
    conditional     tier 2   externalizable only in a named situation (e.g. own company name)
    internal        tier 2   the user's business; leaves only with explicit per-query approval
    restricted      tier 2   sensitive; approval required and warned about loudly
    never           tier 3   NO approval path — credentials, PII, customer-level records

The split between `restricted` and `never` matters. ADR-0009's Tier 3 list is absolute: no
approval unlocks it. `restricted` is for material that is highly sensitive but not on that
list, so a future governed path could exist. Nothing may move from `never` to a lower class
without an ADR.

`context/privacy.py` imports these names, so Business Context fields and dataset fields share
one vocabulary rather than two that can drift.
"""

PUBLIC = "public"
DERIVED_SAFE = "derived_safe"
CONDITIONAL = "conditional"
INTERNAL = "internal"
RESTRICTED = "restricted"
NEVER = "never"

# Ordered least to most sensitive. Redaction and comparison rely on this order.
ORDER = (PUBLIC, DERIVED_SAFE, CONDITIONAL, INTERNAL, RESTRICTED, NEVER)

# The MINIMUM ADR-0009 disclosure tier at which each class may be disclosed. Higher tiers
# demand more approval, so a class permitted at tier 1 is also fine at tier 2, but NOT at
# tier 0 - tier 0 carries public terms only. None means no tier permits it, ever.
TIER_FOR_CLASS = {
    PUBLIC: 0,
    DERIVED_SAFE: 1,
    CONDITIONAL: 2,
    INTERNAL: 2,
    RESTRICTED: 2,
    NEVER: None,
}

# Anything unclassified is internal, never public. Defaulting open would make every new
# column a potential leak the first time someone forgets to classify it.
DEFAULT_CLASS = INTERNAL

# Classes that may never be transmitted, whatever approval is offered.
NO_APPROVAL_PATH = frozenset({NEVER})

HUMAN_LABEL = {
    PUBLIC: "public",
    DERIVED_SAFE: "derived-safe (aggregate only)",
    CONDITIONAL: "conditional",
    INTERNAL: "internal",
    RESTRICTED: "restricted",
    NEVER: "never externalizable",
}


def rank(sensitivity_class):
    """Position in ORDER; unknown classes rank as the most sensitive, not the least."""
    try:
        return ORDER.index(sensitivity_class)
    except ValueError:
        return len(ORDER) - 1


def most_sensitive(classes):
    """The strictest class in a collection — how a derived value inherits sensitivity."""
    classes = list(classes)
    if not classes:
        return DEFAULT_CLASS
    return max(classes, key=rank)


def required_tier(sensitivity_class):
    """Lowest disclosure tier that may carry this class, or None if none ever may."""
    return TIER_FOR_CLASS.get(sensitivity_class, None)


# Retained name for readability at call sites that ask "how far can this go?".
max_tier = required_tier


def permitted_at_tier(sensitivity_class, tier):
    """Whether a field of this class may be disclosed in a query at `tier`.

    Tier 0 carries public terms only, so a `derived_safe` aggregate does not qualify there
    even though it qualifies at Tier 1.
    """
    needed = required_tier(sensitivity_class)
    return needed is not None and tier >= needed


def is_externalizable(sensitivity_class):
    """True if any disclosure tier could ever carry this field."""
    return required_tier(sensitivity_class) is not None
