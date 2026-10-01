"""Limitations, gathered from every contributing layer and never quietly dropped.

Combining results is where limitations go to die. Four analyses each say what they could
not do; the synthesis reads well without any of them; the executive summary - the most
condensed artifact in the system - loses the lot. That failure is silent, which is what
makes it worth code.

So the rule here is one-directional: limitations only ever accumulate. There is no filter,
no severity cutoff and no "the other evidence covers it" suppression. The single reduction
performed is exact deduplication, because the same warning arriving from two domains is
one limitation reported twice, not two limitations.
"""

from ..analytics import contract as analytics_contract

Limitation = analytics_contract.Limitation

#: Codes the synthesis layer itself raises. Contributing layers keep their own codes;
#: these name situations that only exist once domains are combined.
INCOMPARABLE = "synthesis.incomparable_values"
UNRESOLVED_CONFLICT = "synthesis.unresolved_conflict"
PROVENANCE_UNAVAILABLE = "synthesis.provenance_unavailable"
EXTERNAL_UNSUPPORTED = "synthesis.external_unsupported"
NO_INPUTS = "synthesis.no_inputs"

#: Stated so a test can assert it: nothing in this module removes a limitation on the
#: grounds that the surrounding synthesis is otherwise well evidenced.
NEVER_SUPPRESSES = True


def as_limitation(value, default_code="unspecified"):
    """Accept a `Limitation`, a mapping, or a bare string; return a `Limitation`."""
    if isinstance(value, Limitation):
        return value
    if isinstance(value, dict):
        return Limitation(value.get("code") or default_code,
                          value.get("subject"),
                          value.get("reason"),
                          value.get("status") or analytics_contract.UNAVAILABLE)
    return Limitation(default_code, None, str(value))


def key(limitation):
    """Two limitations are the same limitation only when all four fields match."""
    limitation = as_limitation(limitation)
    return (limitation.code, limitation.subject, limitation.reason, limitation.status)


def merge(*groups):
    """Combine several collections, deduplicating exactly and preserving first-seen order.

    Order is first-seen rather than sorted so that the reading order follows the order the
    analysis actually ran in, which is the order a reader reconstructs the work in.
    """
    seen, ordered = set(), []
    for group in groups:
        for raw in (group or []):
            limitation = as_limitation(raw)
            identity = key(limitation)
            if identity in seen:
                continue
            seen.add(identity)
            ordered.append(limitation)
    return ordered


def codes(limitations):
    return [as_limitation(item).code for item in limitations or []]


def as_dicts(limitations):
    return [as_limitation(item).as_dict() for item in limitations or []]
