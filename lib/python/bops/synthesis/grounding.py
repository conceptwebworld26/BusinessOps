# -*- coding: utf-8 -*-
"""Grounding: whether a statement in a synthesis set may be read as evidence at all.

ADR-0030 introduced these checks for the first consumer and ADR-0031 requires every consumer
that rests something on a synthesis statement to apply **the same** checks from **one** home
(ADR-0012). They live here, beside the representation they read, because each is a question
about the set rather than about any consumer:

* is this the genuine strict set a synthesis pass produced, with every item graded by `add()`;
* does an id identify exactly one statement in it;
* is the statement evidence — a fact, a calculation, a sourced statement, or an interpretation
  whose recorded supports are real, earlier, non-circular, reach evidence rather than an
  assumption, and account for exactly the provenance the interpretation carries;
* did the set grade it as something a reader may rest on.

Nothing here decides anything new. It computes no figure, grades nothing, promotes nothing and
changes nothing; every verdict it reads — support, confidence, provenance, the supports note —
was written by the set or by `merge.interpretation()`. It knows nothing about the capabilities
that call it, and a consumer-specific rule (a quadrant, a recommendation field) stays with that
consumer.
"""

from . import confidence as confidence_mod
from . import contract as contract_mod
from . import merge as merge_mod
from . import synthesis_set as set_mod


class GroundingError(contract_mod.SynthesisError):
    """A statement or set cannot be read as grounded evidence. Raised, never degraded."""


#: Kinds that are evidence rather than a reading of it: an interpretation's chain must end here.
EVIDENTIAL_KINDS = (contract_mod.FACT, contract_mod.CALCULATION, contract_mod.SOURCED)

#: Kinds a consumer may rest something on directly.
READABLE_KINDS = EVIDENTIAL_KINDS + (contract_mod.INTERPRETATION,)

#: Support verdicts that disqualify a statement. `partially_supported` is not here: it is
#: carried with its lowered confidence, never silently upgraded or dropped.
DISQUALIFYING_SUPPORT = (contract_mod.UNSUPPORTED, contract_mod.INSUFFICIENT_EVIDENCE)


def graded(item):
    """Whether the set actually graded this item on `add()`, rather than it arriving whole."""
    return (type(item) is contract_mod.SynthesisItem
            and item.support in contract_mod.SUPPORT_STATES
            and item.confidence in confidence_mod.LEVELS)


def genuine_set(synthesis):
    """The strict `SynthesisSet` a synthesis pass produced, or a refusal.

    `type(...) is SynthesisSet` because a subclass may never have run `__init__`, and a
    serialised set or a look-alike carries support, confidence and provenance as data nobody
    graded. Strictness is required because external statements are read, and without it a
    dimension no source footed would pass through unchecked (ADR-0026, ADR-0028).
    """
    if type(synthesis) is not set_mod.SynthesisSet:
        raise GroundingError(
            "only the SynthesisSet object a synthesis pass produced is read. A serialised "
            "set, a subclass or a look-alike carries its support, confidence and provenance "
            "as data that nothing graded, so none is accepted.")
    if synthesis.require_dimension_provenance is not True:
        raise GroundingError(
            "only a set built with require_dimension_provenance=True is read. Without it an "
            "external dimension the caller declared but no source footed passes through "
            "unchecked, which ADR-0026 closes on every command path.")
    if not synthesis.items:
        raise GroundingError(
            "the synthesis set holds no statements. Reading nothing presents an empty result "
            "as an analysis; run the internal analysis or the research first, and report what "
            "could not be done rather than an empty result.")
    ungraded = [getattr(item, "id", repr(item)) for item in synthesis.items
                if not graded(item)]
    if ungraded:
        raise GroundingError(
            "statement(s) %s were never graded by the synthesis set. Only statements that "
            "entered through SynthesisSet.add() carry a support and confidence verdict, and "
            "a set holding anything else is not the set a synthesis pass produced."
            % ", ".join(str(i) for i in ungraded))
    return synthesis


def index(synthesis):
    """`synthesis_id -> [(position, item)]`, in the order the set holds them."""
    found = {}
    for position, item in enumerate(synthesis.items):
        found.setdefault(item.id, []).append((position, item))
    return found


def one(index_, synthesis_id):
    """`(position, item)` for the single statement an id names, or a refusal."""
    entries = index_.get(synthesis_id) if isinstance(synthesis_id, str) else None
    if not entries:
        raise GroundingError(
            "%r is not a statement in this synthesis set. An id the set never produced is "
            "not evidence." % (synthesis_id,))
    if len(entries) > 1:
        raise GroundingError(
            "%r identifies %d statements in this set. A reference must trace to exactly one; "
            "translate each analysis under its own origin so their statements stay distinct."
            % (synthesis_id, len(entries)))
    return entries[0]


def interpretation_supports(index_, position, item):
    """The statements an interpretation rests on, verified against the set, in note order.

    Supports are read back from the note `merge.interpretation()` wrote. The note alone proves
    nothing, so each named statement must exist once, **precede** the interpretation (the
    writer can cite only what is already there) and have been graded. Deeper checks — the
    chain reaching evidence, no cycle, provenance accounted for — are `interpretation_domains`.
    """
    supports = merge_mod.interpretation_supports(item)
    if supports is None:
        raise GroundingError(
            "interpretation %s records its supports more than once; two accounts of what a "
            "reading rests on are not one account" % item.id)
    if not supports:
        raise GroundingError(
            "interpretation %s names no supporting statements. A reading that traces to "
            "nothing in the set is an opinion and nothing may rest on it." % item.id)
    resolved = []
    for support_id in supports:
        if support_id == item.id:
            raise GroundingError(
                "interpretation %s rests on itself through %s; a circular chain supports "
                "nothing" % (item.id, support_id))
        support_position, support = one(index_, support_id)
        if support_position >= position:
            raise GroundingError(
                "interpretation %s cites %s, which entered the set after it. A reading can "
                "rest only on statements that already existed." % (item.id, support_id))
        if not graded(support):
            raise GroundingError(
                "interpretation %s cites %s, which the set never graded"
                % (item.id, support_id))
        resolved.append((support_position, support))
    return resolved


def interpretation_domains(index_, position, item, trail=()):
    """The evidential domains an interpretation's verified chain reaches, or a refusal.

    A note naming statements the item does not actually rest on is refused as forged: the
    provenance the interpretation carries must be exactly what its supports account for.
    """
    domains, accounted = set(), set()
    for support_position, support in interpretation_supports(index_, position, item):
        if support.id in trail:
            raise GroundingError(
                "interpretation %s rests on itself through %s; a circular chain supports "
                "nothing" % (item.id, support.id))
        if support.kind == contract_mod.INTERPRETATION:
            domains |= interpretation_domains(index_, support_position, support,
                                              trail + (item.id,))
        elif support.kind in EVIDENTIAL_KINDS:
            domains.add(support.domain)
        else:
            raise GroundingError(
                "interpretation %s rests on %s, a %s. An assumption is not evidence, and a "
                "reading must trace to a fact, a calculation or a sourced statement."
                % (item.id, support.id, support.kind))
        accounted.update(support.provenance_keys())

    if set(item.provenance_keys()) != accounted:
        raise GroundingError(
            "interpretation %s carries provenance its named supports do not account for. "
            "Supports are recorded by synthesis.interpretation(); a note that disagrees "
            "with the chain the statement actually carries is not accepted." % item.id)
    return domains


def evidence_domains(index_, position, item):
    """The evidential domains a statement rests on, if it may be read as evidence at all.

    Refuses an ungraded item, a kind that is not evidence or a reading of evidence, a kind in
    the wrong domain, a statement with no resolvable provenance, a statement the set graded
    `unsupported` or `insufficient_evidence`, and an interpretation whose chain does not hold.
    """
    if not graded(item):
        raise GroundingError(
            "statement %s was never graded by the synthesis set. Only statements that "
            "entered through SynthesisSet.add() carry a support and confidence verdict."
            % item.id)
    if item.kind not in READABLE_KINDS:
        raise GroundingError(
            "statement %s is a %s, which is not evidence. An assumption is not evidence and a "
            "recommendation never supports anything." % (item.id, item.kind))
    if item.kind in (contract_mod.FACT, contract_mod.CALCULATION) \
            and item.domain != contract_mod.INTERNAL:
        raise GroundingError("statement %s claims %s outside the internal domain"
                             % (item.id, item.kind))
    if item.kind == contract_mod.SOURCED and item.domain != contract_mod.EXTERNAL:
        raise GroundingError("statement %s claims %s outside the external domain"
                             % (item.id, item.kind))
    if not item.has_provenance():
        raise GroundingError(
            "statement %s has no resolvable provenance. A statement with no evidence behind "
            "it cannot be rested on." % item.id)
    if item.support in DISQUALIFYING_SUPPORT:
        raise GroundingError(
            "the synthesis set graded statement %s %s. Evidence the set does not support is "
            "not rested on." % (item.id, item.support))
    if item.kind == contract_mod.INTERPRETATION:
        return interpretation_domains(index_, position, item)
    return {item.domain}
