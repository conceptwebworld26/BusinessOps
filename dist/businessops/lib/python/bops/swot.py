# -*- coding: utf-8 -*-
"""SWOT over the synthesis representation: a placement of statements, never new text.

M10.1 built the representation M10.3's consumers read, and R.10-R.14 made both halves of it
reachable. This module is the first consumer, and the design choice that makes it small is
that **a SWOT point adds no words of its own**. A point is an existing, graded statement in a
genuine `SynthesisSet`, placed in one quadrant. Its text is that statement's text, its kind,
support, confidence, conflicts, materiality and limitations are that statement's, and its tag
is read from its kind:

    FACT, CALCULATION   (internal)   -> data-supported
    SOURCED             (external)   -> externally-sourced
    INTERPRETATION      (either)     -> analytical-inference

So there is nothing here for a recommendation to hide in. A reading of the evidence that is
not already a statement - "the margin decline and the competitor's price cut point the same
way" - is authored first through `synthesis.interpretation()`, which requires the statements
it rests on and refuses advisory wording, and only then placed. An unsupported free-text
point is not refused by a filter; it is unconstructible, because a placement has no field to
carry text.

What remains is judgement and grounding, and they are split cleanly. **Which quadrant** - is
this favourable or unfavourable - is the model's reading and belongs to `bops-swot`. **Whether
the placement is grounded** is decided here, deterministically, and fails closed:

* the set must be the genuine, strict object a synthesis pass produced;
* the statement must exist in it exactly once, graded by the set;
* the claimed tag must be the tag its kind implies - a mislabel is refused, never corrected;
* an internal statement sits in Strengths or Weaknesses, an external one in Opportunities or
  Threats, and an inference sits on the side at least one of its evidential supports is on;
* an interpretation must name supports that are in the set, precede it, and account for the
  provenance it actually carries;
* a statement the set graded `unsupported` or `insufficient_evidence` is not a point.

It decides nothing else. It computes no figure, re-judges no materiality, resolves no
conflict, filters no limitation, invents no confidence and orders nothing by importance:
points appear in the order their statements entered the set, which is the order the analysis
ran in and is stated not to be a ranking. There is no score, no weight, no priority and no
recommendation slot anywhere in the result.
"""

import hashlib
import json

from .synthesis import contract as contract_mod
from .synthesis import grounding
from .synthesis import limitations as limitations_mod
from .synthesis import research_footing as footing_mod
from .synthesis import synthesis_set as set_mod

SCHEMA_VERSION = "1.0.0"
ANALYSIS = "swot"


class SwotError(contract_mod.SynthesisError):
    """A SWOT input violates its contract. Raised rather than degraded, always."""


# ---------------------------------------------------------------------------
# Quadrants and tags
# ---------------------------------------------------------------------------

STRENGTHS = "strengths"
WEAKNESSES = "weaknesses"
OPPORTUNITIES = "opportunities"
THREATS = "threats"

#: Presentation order, fixed. Not an order of importance.
QUADRANTS = (STRENGTHS, WEAKNESSES, OPPORTUNITIES, THREATS)

QUADRANT_TITLES = {STRENGTHS: "Strengths", WEAKNESSES: "Weaknesses",
                   OPPORTUNITIES: "Opportunities", THREATS: "Threats"}

#: Which side of the business each quadrant describes, in the synthesis layer's own domain
#: vocabulary rather than a second one.
QUADRANT_DOMAIN = {STRENGTHS: contract_mod.INTERNAL, WEAKNESSES: contract_mod.INTERNAL,
                   OPPORTUNITIES: contract_mod.EXTERNAL, THREATS: contract_mod.EXTERNAL}

DATA_SUPPORTED = "data-supported"
EXTERNALLY_SOURCED = "externally-sourced"
ANALYTICAL_INFERENCE = "analytical-inference"

TAGS = (DATA_SUPPORTED, EXTERNALLY_SOURCED, ANALYTICAL_INFERENCE)

#: The whole classification. `ASSUMPTION` is absent because an assumption is not evidence,
#: and `RECOMMENDATION` is absent because the synthesis layer refuses it and this consumer
#: has no use for one. A kind not in this map has no tag and cannot become a point.
TAG_OF_KIND = {
    contract_mod.FACT: DATA_SUPPORTED,
    contract_mod.CALCULATION: DATA_SUPPORTED,
    contract_mod.SOURCED: EXTERNALLY_SOURCED,
    contract_mod.INTERPRETATION: ANALYTICAL_INFERENCE,
}

#: Read from the one home of the grounding rules (ADR-0031), not restated here.
EVIDENTIAL_KINDS = grounding.EVIDENTIAL_KINDS
DISQUALIFYING_SUPPORT = grounding.DISQUALIFYING_SUPPORT

#: The only fields a placement may carry. There is no text, score, weight, rank, priority or
#: recommendation field, so none of those can be supplied.
PLACEMENT_FIELDS = ("quadrant", "tag", "synthesis_id")

EMPTY_STATE = "No supported point identified."

PLACEMENT_NOTE = (
    "Each point is a statement already in the synthesis set, placed in one quadrant. "
    "Whether it is favourable or unfavourable is an analytical judgement that requires "
    "human review; BusinessOps checked only that the placement is grounded. Points appear "
    "in the order the analysis produced them, which is not a ranking.")

#: Stated so a test can assert it: nothing here issues, ranks or scores anything.
ISSUES_RECOMMENDATIONS = False


def point_id(quadrant, synthesis_id):
    """Content-addressed, so the same placement always carries the same id."""
    seed = "%s|%s" % (quadrant, synthesis_id)
    return "swot-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# The input
# ---------------------------------------------------------------------------

def _grounded(check, *args):
    """Run one shared grounding check, reporting its refusal as this consumer's error."""
    try:
        return check(*args)
    except grounding.GroundingError as refusal:
        raise SwotError(str(refusal))


def genuine_synthesis(synthesis):
    """The strict `SynthesisSet` a synthesis pass produced, or a refusal.

    The identity, strictness, non-emptiness and grading checks are
    `synthesis.grounding.genuine_set()` — the one home ADR-0031 requires — reported as a
    `SwotError`.
    """
    return _grounded(grounding.genuine_set, synthesis)


def _one(index, synthesis_id):
    return _grounded(grounding.one, index, synthesis_id)


def _assess(synthesis, index, position, item):
    """`(tag, rests_on_domains)` for an eligible statement, or a `SwotError` saying why not.

    Only the tag is this consumer's rule. Whether the statement may be read as evidence at all
    is `synthesis.grounding.evidence_domains()`.
    """
    if not grounding.graded(item):
        raise SwotError(
            "statement %s was never graded by the synthesis set. Only statements that "
            "entered through SynthesisSet.add() carry a support and confidence verdict."
            % item.id)
    tag = TAG_OF_KIND.get(item.kind)
    if tag is None:
        raise SwotError(
            "statement %s is a %s, which has no SWOT tag. An assumption is not evidence and "
            "a recommendation is never a SWOT point." % (item.id, item.kind))
    domains = _grounded(grounding.evidence_domains, index, position, item)
    return tag, domains


# ---------------------------------------------------------------------------
# Candidates: a read-only view for the skill
# ---------------------------------------------------------------------------

def candidates(synthesis):
    """Every statement in the set, with its tag and whether it may become a point.

    Read-only and in set order. It places nothing: which quadrant a statement belongs in is
    the skill's judgement. It exists so that judgement starts from what the set actually
    holds and from the same eligibility rule `build()` enforces, rather than from memory.
    """
    synthesis = genuine_synthesis(synthesis)
    index = grounding.index(synthesis)
    listed = []
    for position, item in enumerate(synthesis.items):
        entry = {"synthesis_id": item.id, "kind": item.kind, "domain": item.domain,
                 "origin": item.origin, "statement": item.statement,
                 "support": item.support, "confidence": item.confidence,
                 "material": item.is_material, "tag": TAG_OF_KIND.get(item.kind),
                 "quadrants": [], "eligible": False, "reason": None}
        try:
            _one(index, item.id)
            _tag, domains = _assess(synthesis, index, position, item)
        except SwotError as refusal:
            entry["reason"] = str(refusal)
        else:
            entry["eligible"] = True
            entry["quadrants"] = [q for q in QUADRANTS if QUADRANT_DOMAIN[q] in domains]
        listed.append(entry)
    return listed


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def _placement(raw):
    if not isinstance(raw, dict):
        raise SwotError(
            "a placement is a record of %s; %r is not one"
            % (", ".join(PLACEMENT_FIELDS), type(raw).__name__))
    extra = sorted(set(raw) - set(PLACEMENT_FIELDS))
    if extra:
        raise SwotError(
            "a placement carries only %s; %s is not accepted. A SWOT point takes its text, "
            "support and confidence from the statement it places, and carries no score, "
            "rank, priority or recommendation." % (", ".join(PLACEMENT_FIELDS),
                                                  ", ".join(str(e) for e in extra)))
    missing = [name for name in PLACEMENT_FIELDS if not raw.get(name)]
    if missing:
        raise SwotError("a placement must state %s" % ", ".join(missing))
    quadrant, tag, synthesis_id = raw["quadrant"], raw["tag"], raw["synthesis_id"]
    if quadrant not in QUADRANTS:
        raise SwotError("%r is not a SWOT quadrant; the quadrants are %s"
                        % (quadrant, ", ".join(QUADRANTS)))
    if tag not in TAGS:
        raise SwotError("%r is not a SWOT point tag; the tags are %s"
                        % (tag, ", ".join(TAGS)))
    if not isinstance(synthesis_id, str):
        raise SwotError("a placement names its statement by synthesis id")
    return quadrant, tag, synthesis_id


def _point(synthesis, index, quadrant, claimed_tag, synthesis_id):
    position, item = _one(index, synthesis_id)
    tag, domains = _assess(synthesis, index, position, item)

    if claimed_tag != tag:
        raise SwotError(
            "statement %s is a %s and is tagged %s; it was placed as %s. A tag is read "
            "from the statement's kind and is never relabelled, so the placement is refused "
            "rather than corrected." % (synthesis_id, item.kind, tag, claimed_tag))

    side = QUADRANT_DOMAIN[quadrant]
    if side not in domains:
        if tag == ANALYTICAL_INFERENCE:
            raise SwotError(
                "inference %s is placed in %s, which describes the %s side of the business, "
                "but none of the statements it rests on is %s. Its supports may be mixed; "
                "they may not be absent from the side the quadrant describes."
                % (synthesis_id, quadrant, side, side))
        raise SwotError(
            "statement %s is %s and is placed in %s. Strengths and weaknesses are grounded "
            "in the business's own data; opportunities and threats in external evidence."
            % (synthesis_id, item.domain, quadrant))

    supports = []
    if tag == ANALYTICAL_INFERENCE:
        for _position, support in _grounded(grounding.interpretation_supports, index,
                                            position, item):
            supports.append({"synthesis_id": support.id, "kind": support.kind,
                             "domain": support.domain, "origin": support.origin,
                             "statement": support.statement})

    unresolved = {}
    if item.dimension_provenance:
        unresolved = footing_mod.dimension_report(item)[1]

    record = item.as_dict()
    return position, {
        "point_id": point_id(quadrant, item.id),
        "quadrant": quadrant,
        "tag": tag,
        "synthesis_id": item.id,
        "statement": item.statement,
        "kind": item.kind,
        "evidence_class": item.evidence_class,
        "origin": item.origin,
        "domain": item.domain,
        "trust": item.trust,
        "support": item.support,
        "confidence": item.confidence,
        "confidence_reasons": list((item.confidence_detail or {}).get("reasons") or []),
        "material": item.is_material,
        "materiality": record.get("materiality"),
        "provenance": record.get("provenance") or [],
        "chain": synthesis.chain(item),
        "rests_on": sorted(domains),
        "supports": supports,
        "conflict_refs": sorted(item.conflict_refs),
        "unresolved_dimensions": unresolved,
        "limitations": record.get("limitations") or [],
        "caveats": list(item.caveats),
    }


def build(synthesis, placements):
    """Assemble a SWOT from placements over a genuine strict synthesis set.

    `placements` is a list of `{"quadrant", "tag", "synthesis_id"}` records. Every one is
    checked; the first that is not grounded raises `SwotError` and nothing is returned, so a
    partly grounded SWOT is never presented as a whole one. An empty quadrant carries
    `EMPTY_STATE` and no points. Conflicts, limitations and the set's confidence are carried
    whole: nothing is filtered to the points that were placed.
    """
    synthesis = genuine_synthesis(synthesis)
    if not isinstance(placements, (list, tuple)):
        raise SwotError("placements are a list of records, one per point")

    index = grounding.index(synthesis)
    placed = {}
    by_quadrant = dict((quadrant, []) for quadrant in QUADRANTS)
    for raw in placements:
        quadrant, tag, synthesis_id = _placement(raw)
        if synthesis_id in placed:
            raise SwotError(
                "statement %s is placed twice (%s and %s). One statement is one point; "
                "the same evidence cannot be both favourable and unfavourable, and "
                "repeating it would count it twice." % (synthesis_id, placed[synthesis_id],
                                                        quadrant))
        placed[synthesis_id] = quadrant
        by_quadrant[quadrant].append(_point(synthesis, index, quadrant, tag, synthesis_id))

    quadrants = []
    for quadrant in QUADRANTS:
        points = [point for _position, point in sorted(by_quadrant[quadrant],
                                                       key=lambda pair: pair[0])]
        quadrants.append({"quadrant": quadrant, "title": QUADRANT_TITLES[quadrant],
                          "points": points,
                          "empty_state": None if points else EMPTY_STATE})

    return {
        "schema_version": SCHEMA_VERSION,
        "analysis": ANALYSIS,
        "subject": synthesis.subject,
        "as_of": synthesis.as_of,
        "business_model": synthesis.business_model,
        "currency": synthesis.currency,
        "quality_grade": synthesis.quality_grade,
        "trust_statement": set_mod.TRUST_STATEMENT,
        "placement": PLACEMENT_NOTE,
        "quadrants": quadrants,
        "material_not_placed": [item.id for item in synthesis.material()
                                if item.id not in placed],
        "conflicts": [conflict.as_dict() for conflict in synthesis.conflicts],
        "limitations": limitations_mod.as_dicts(synthesis.limitations),
        "confidence": synthesis.confidence().as_dict(),
    }


def to_json(result, indent=None):
    """Deterministic serialisation: sorted keys, JSON-safe throughout."""
    return json.dumps(result, sort_keys=True, indent=indent, default=str)


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

def render(result):
    """The SWOT as markdown, formatted once. Adds no sentence of analysis.

    Every line is either a heading, a statement already in the set, or a label for what the
    result carries. There is no summary paragraph, no "key takeaway", no next step and no
    recommendation section, because each of those would be new text nobody grounded.
    """
    lines = ["# SWOT — %s" % (result.get("subject") or "subject not stated"), ""]
    basis = [("Business model", result.get("business_model")),
             ("Currency", result.get("currency")),
             ("As of", result.get("as_of")),
             ("Data quality", result.get("quality_grade"))]
    stated = ["%s: %s" % (label, value) for label, value in basis if value]
    if stated:
        lines += [" · ".join(stated), ""]

    confidence = result["confidence"]
    lines.append("**Confidence:** %s" % confidence["confidence"])
    for explanation in confidence.get("explanations") or []:
        lines.append("- %s" % explanation)
    lines.append("")

    if result["limitations"]:
        lines.append("**Limitations** (%d)" % len(result["limitations"]))
        for limitation in result["limitations"]:
            lines.append("- `%s` %s — %s" % (limitation["code"],
                                             limitation.get("subject") or "",
                                             limitation.get("reason") or ""))
        lines.append("")
    if result["conflicts"]:
        lines.append("**Unresolved conflicts** (%d)" % len(result["conflicts"]))
        for conflict in result["conflicts"]:
            lines.append("- `%s` %s — %s" % (conflict["conflict_id"], conflict["subject"],
                                             conflict.get("reason") or ""))
        lines.append("")

    for quadrant in result["quadrants"]:
        lines += ["## %s" % quadrant["title"], ""]
        if not quadrant["points"]:
            lines += ["_%s_" % quadrant["empty_state"], ""]
            continue
        for point in quadrant["points"]:
            lines.append("- **[%s]** %s" % (point["tag"], point["statement"]))
            lines.append("  - `%s` · %s · %s · support %s · confidence %s%s"
                         % (point["synthesis_id"], point["kind"], point["domain"],
                            point["support"], point["confidence"],
                            " · material" if point["material"] else ""))
            for entry in point["chain"]:
                lines.append("  - rests on `%s:%s`%s" % (
                    entry["kind"], entry["ref_id"],
                    " — %s, tier %s, %s" % (entry["source"], entry["source_tier"],
                                            entry.get("publication_date") or "undated")
                    if entry.get("source") else ""))
            for support in point["supports"]:
                lines.append("  - reads `%s` (%s, %s)" % (support["synthesis_id"],
                                                          support["kind"],
                                                          support["domain"]))
            if point["confidence_reasons"]:
                lines.append("  - confidence reasons: %s"
                             % ", ".join(point["confidence_reasons"]))
            if point["conflict_refs"]:
                lines.append("  - contested: %s" % ", ".join(point["conflict_refs"]))
            if point["unresolved_dimensions"]:
                lines.append("  - unresolved dimensions: %s" % ", ".join(
                    "%s (%s)" % pair for pair in sorted(
                        point["unresolved_dimensions"].items())))
            for caveat in point["caveats"]:
                lines.append("  - caveat: %s" % caveat)
        lines.append("")

    if result["material_not_placed"]:
        lines.append("**Material statements not placed:** %s"
                     % ", ".join("`%s`" % i for i in result["material_not_placed"]))
        lines.append("")
    lines.append("_%s_" % result["placement"])
    return "\n".join(lines)


__all__ = [
    "build", "candidates", "render", "to_json", "genuine_synthesis", "point_id",
    "SwotError", "SCHEMA_VERSION", "ANALYSIS",
    "STRENGTHS", "WEAKNESSES", "OPPORTUNITIES", "THREATS", "QUADRANTS", "QUADRANT_TITLES",
    "QUADRANT_DOMAIN", "DATA_SUPPORTED", "EXTERNALLY_SOURCED", "ANALYTICAL_INFERENCE",
    "TAGS", "TAG_OF_KIND", "EVIDENTIAL_KINDS", "DISQUALIFYING_SUPPORT",
    "PLACEMENT_FIELDS", "EMPTY_STATE", "PLACEMENT_NOTE", "ISSUES_RECOMMENDATIONS",
]
