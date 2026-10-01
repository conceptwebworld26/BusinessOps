"""Disagreements, carried across the domain boundary without being settled.

`research.sources.assess_conflict()` already decides whether two *sources* disagree, and
`EvidenceSet.record_conflict()` already stores that. This module does two things neither
can: it says **what kind** of disagreement it is, and it lets an internal figure disagree
with an external one - a case the research layer cannot represent, because it never sees
internal data.

The kind matters because the remedies differ. Two sources reporting different numbers for
the same defined quantity is a genuine numeric dispute and lowers confidence. Two sources
reporting different numbers because one counts aftermarket parts and the other does not is
not a dispute at all; it is two answers to two questions, and averaging them would invent
a third quantity nobody measured.

What this module deliberately does **not** have is any way to settle a conflict. There is
no `resolve()`, no winner, no midpoint, no weighting by tier. A higher tier makes a source
more attributable, not more correct, so tier never decides a disagreement here.
"""

import hashlib
import json

from ..research import sources as sources_mod
from .contract import EXTERNAL, INTERNAL, SynthesisError

DEFINITIONAL = "definitional"
NUMERIC = "numeric"
SCOPE = "scope"
TEMPORAL = "temporal"
METHODOLOGY = "methodology"
INTERNAL_EXTERNAL = "internal_external"

CONFLICT_KINDS = (DEFINITIONAL, NUMERIC, SCOPE, TEMPORAL, METHODOLOGY, INTERNAL_EXTERNAL)

KIND_REASON = {
    DEFINITIONAL: "The sources define the subject differently, so the figures count "
                  "different things. They are not two estimates of one quantity.",
    NUMERIC: "The sources report materially different values for what appears to be the "
             "same quantity.",
    SCOPE: "The sources measure different scopes or territories.",
    TEMPORAL: "The figures refer to different periods.",
    METHODOLOGY: "The figures were produced by different measurement methodologies.",
    INTERNAL_EXTERNAL: "An internal figure and an external estimate disagree. Neither is "
                       "presumed correct: they may measure different things, and the "
                       "internal figure is not evidence about the external subject.",
}

#: Stated so a test can assert it: nothing in this module averages, weights, ranks or
#: otherwise reduces competing positions to one number.
NEVER_RESOLVES = True


def conflict_id(kind, subject, positions):
    """Content-addressed, so the same disagreement recorded twice carries one id."""
    seed = json.dumps([kind, subject, positions], sort_keys=True, default=str)
    return "cf-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def _differs(positions, field):
    seen = set()
    for position in positions:
        value = position.get(field)
        seen.add(None if value is None else " ".join(str(value).split()).lower())
    seen.discard(None)
    return len(seen) > 1


def classify(positions, declared=False):
    """Name the kind of disagreement from what the positions actually differ on.

    Order matters and is deliberate: a definitional difference outranks a numeric one,
    because once two sources are counting different things the numeric gap is a
    consequence rather than the disagreement.
    """
    positions = [p if isinstance(p, dict) else p.as_dict() for p in positions]
    if _differs(positions, "definition"):
        return DEFINITIONAL
    if _differs(positions, "scope"):
        return SCOPE
    if _differs(positions, "methodology"):
        return METHODOLOGY
    if _differs(positions, "period") or _differs(positions, "source_date"):
        return TEMPORAL
    return NUMERIC


class CrossDomainConflict:
    """One preserved disagreement: who said what, why they differ, and nothing more.

    The original `assess_conflict` record is kept verbatim in `assessment`. This object
    annotates it; it never edits it, because the research layer's verdict is the
    authoritative one and a second opinion stored in the same place would be ambiguous.
    """

    __slots__ = ("id", "kind", "subject", "reason", "positions", "assessment",
                 "unresolved", "domains", "evidence_ids", "item_ids", "notes")

    def __init__(self, kind, subject, positions, reason=None, assessment=None,
                 unresolved=True, domains=(), evidence_ids=(), item_ids=(), notes=None):
        if kind not in CONFLICT_KINDS:
            raise SynthesisError("unknown conflict kind %r" % (kind,))
        positions = [p if isinstance(p, dict) else p.as_dict() for p in positions]
        if len(positions) < 2:
            raise SynthesisError(
                "a conflict needs at least two positions; one position is a finding, "
                "not a disagreement")
        self.kind = kind
        self.subject = subject
        self.positions = positions
        self.reason = reason or KIND_REASON[kind]
        self.assessment = assessment
        self.unresolved = bool(unresolved)
        self.domains = tuple(sorted(set(domains)))
        # Derived from the positions when not supplied, so a conflict built directly is
        # linked to the evidence it disputes exactly as one lifted from an evidence set
        # is. A conflict nothing can find is a conflict that suppresses itself.
        self.evidence_ids = tuple(sorted(set(evidence_ids) or set(
            str(p["evidence_id"]) for p in positions if p.get("evidence_id"))))
        self.item_ids = tuple(sorted(set(item_ids) or set(
            str(p["synthesis_id"]) for p in positions if p.get("synthesis_id"))))
        self.notes = list(notes or [])
        self.id = conflict_id(kind, subject, positions)

    @classmethod
    def from_evidence_conflict(cls, record, subject=None):
        """Lift one `EvidenceSet.conflicts` entry into the synthesis layer.

        The entry's own `status` decides whether it is unresolved; this module does not
        second-guess it. A `declared` conflict stays a conflict even where the numbers
        look close, which is exactly what ADR-0016 bought.
        """
        if not isinstance(record, dict):
            raise SynthesisError("an evidence conflict must be a record")
        positions = record.get("positions") or []
        kind = classify(positions, declared=bool(record.get("declared")))
        status = record.get("status")
        return cls(
            kind,
            subject or record.get("subject"),
            positions,
            reason=record.get("reason"),
            assessment=record,
            unresolved=(status == sources_mod.CONFLICTS),
            domains=(EXTERNAL,),
            evidence_ids=[p.get("evidence_id") for p in positions
                          if isinstance(p, dict) and p.get("evidence_id")])

    @classmethod
    def between_domains(cls, subject, internal_position, external_position, reason=None,
                        notes=None):
        """Record that an internal figure and an external estimate do not agree.

        Both positions are kept whole. The internal figure is not treated as ground truth
        for the external subject, and the external estimate is not treated as a correction
        to the internal one: they are two measurements whose comparability has to be
        established separately, by `compatibility.compare`.
        """
        for position, expected in ((internal_position, INTERNAL),
                                   (external_position, EXTERNAL)):
            if not isinstance(position, dict):
                raise SynthesisError("a conflict position must be a record")
            if position.get("domain") not in (None, expected):
                raise SynthesisError(
                    "position declared domain %r where %r was required"
                    % (position.get("domain"), expected))
        internal_position = dict(internal_position, domain=INTERNAL)
        external_position = dict(external_position, domain=EXTERNAL)
        positions = [internal_position, external_position]
        return cls(INTERNAL_EXTERNAL, subject, positions, reason=reason,
                   unresolved=True, domains=(INTERNAL, EXTERNAL),
                   evidence_ids=[p.get("evidence_id") for p in positions
                                 if p.get("evidence_id")],
                   item_ids=[p.get("synthesis_id") for p in positions
                             if p.get("synthesis_id")],
                   notes=notes)

    def values(self):
        """Every competing value, kept as a list. There is deliberately no aggregate."""
        return [p.get("value") for p in self.positions]

    def as_dict(self):
        record = {
            "conflict_id": self.id,
            "kind": self.kind,
            "subject": self.subject,
            "reason": self.reason,
            "unresolved": self.unresolved,
            "domains": list(self.domains),
            "positions": list(self.positions),
            "evidence_ids": list(self.evidence_ids),
            "item_ids": list(self.item_ids),
            "assessment": self.assessment,
            "notes": list(self.notes),
            "resolution": None,
            "resolution_statement": (
                "Preserved, not resolved. Competing positions are never averaged, and a "
                "higher source tier does not make a conflicting source false."),
        }
        return dict((k, v) for k, v in record.items() if v not in (None, [], {}))

    def __repr__(self):
        return "CrossDomainConflict(%s: %s)" % (self.kind, self.subject)


def merge(conflicts):
    """Deduplicate by content-addressed id, preserving first-seen order."""
    seen, ordered = set(), []
    for conflict in conflicts:
        if conflict.id in seen:
            continue
        seen.add(conflict.id)
        ordered.append(conflict)
    return ordered
