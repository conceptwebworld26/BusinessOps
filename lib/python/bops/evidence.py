"""The evidence ledger — provenance carried from ingestion to output.

Implements `reference/evidence-ledger.md`. The point of making provenance *data* rather
than phrasing is that it survives summarisation: the executive summary is the most
condensed artifact in the system, and that is exactly where a prose convention loses track
of what was measured versus argued.

Classes 1-4 are evidential, 5-7 generative. That split drives presentation: they must be
visually distinct in every output.
"""

import re

USER_DATA = 1            # read from a file the user supplied
CONNECTED_DATA = 2       # pulled from an MCP-connected system
EXTERNAL_SOURCED = 3     # retrieved from public research
CALCULATED = 4           # computed by the engine from class 1 or 2
INTERPRETATION = 5       # a reading of classes 1-4
ASSUMPTION = 6           # modelled or assumed
RECOMMENDATION = 7       # a proposed action

CLASS_NAMES = {
    USER_DATA: "user-provided data",
    CONNECTED_DATA: "connected-system data",
    EXTERNAL_SOURCED: "external sourced",
    CALCULATED: "calculated metric",
    INTERPRETATION: "analytical interpretation",
    ASSUMPTION: "estimate / assumption",
    RECOMMENDATION: "recommendation",
}

EVIDENTIAL = frozenset({USER_DATA, CONNECTED_DATA, EXTERNAL_SOURCED, CALCULATED})
GENERATIVE = frozenset({INTERPRETATION, ASSUMPTION, RECOMMENDATION})

HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"

# A recommendation (class 7) is not issued unless all six are present.
RECOMMENDATION_FIELDS = ("evidence", "rationale", "expected_benefit",
                         "risks", "dependencies", "confidence")

# ADR-0031 fixes their shapes, so a class-7 claim cannot carry a placeholder where evidence
# belongs. This module checks shape only: whether an id names a real statement needs the
# synthesis set, which sits above this layer, so that resolution is the strategy engine's and is
# authoritative. The id spelling mirrors `synthesis.contract.synthesis_id()`; a test pins the two
# together so they cannot drift.
RECOMMENDATION_EVIDENCE_ID = re.compile(r"^sy-[0-9a-f]{12}$")
RECOMMENDATION_DEPENDENCY_FIELDS = ("text", "assumption_id")
CONFIDENCE_LEVELS = ("HIGH", "MEDIUM", "LOW")

# An external claim (class 3) is not issued unless all four are present. `reference/
# research-policy.md` says "citations are captured at retrieval; a citation never captured
# cannot be emitted" - which was prose until this rule existed. Making the claim
# unconstructible is what turns that sentence into a guarantee: there is no path by which an
# uncited external figure reaches a report, because the object cannot be built (owner
# decision 2026-09-10, closing F-1).
#
# `source` is an explicit constructor parameter; the other three arrive via **extra.
EXTERNAL_FIELDS = ("source", "citation", "source_date", "source_tier")

#: Source tiers from `reference/research-policy.md`. D is excluded outright, so a claim may
#: not even be constructed on one - an excluded source is not a weak citation, it is none.
SOURCE_TIERS = ("A", "B", "C")
EXCLUDED_SOURCE_TIER = "D"


class LedgerError(Exception):
    """A claim violates the ledger's rules — a defect, not a user error."""


class Claim:
    """One assertion, with exactly one provenance class."""

    __slots__ = ("statement", "provenance_class", "confidence", "source",
                 "formula", "inputs", "based_on", "caveats", "extra")

    def __init__(self, statement, provenance_class, confidence=None, source=None,
                 formula=None, inputs=None, based_on=None, caveats=None, **extra):
        if provenance_class not in CLASS_NAMES:
            raise LedgerError("unknown provenance class %r" % (provenance_class,))

        if provenance_class == CALCULATED and not formula:
            raise LedgerError(
                "a calculated metric must carry the formula that produced it")
        if provenance_class == USER_DATA and not source:
            raise LedgerError("user-provided data must name its source")
        if provenance_class == EXTERNAL_SOURCED:
            supplied = dict(extra)
            if source:
                supplied["source"] = source
            missing = [f for f in EXTERNAL_FIELDS if not supplied.get(f)]
            if missing:
                raise LedgerError(
                    "an external claim requires %s; missing: %s. A citation that was never "
                    "captured cannot be emitted."
                    % (", ".join(EXTERNAL_FIELDS), ", ".join(missing)))
            tier = str(supplied.get("source_tier", "")).strip().upper()
            if tier == EXCLUDED_SOURCE_TIER:
                raise LedgerError(
                    "source tier D (unattributable, AI-generated, content farms) is "
                    "excluded; it cannot support a claim.")
            if tier not in SOURCE_TIERS:
                raise LedgerError(
                    "source_tier must be one of %s; got %r."
                    % (", ".join(SOURCE_TIERS), supplied.get("source_tier")))
        if provenance_class == RECOMMENDATION:
            # `confidence` is an explicit parameter, so it never reaches **extra.
            supplied = dict(extra)
            if confidence:
                supplied["confidence"] = confidence
            missing = [f for f in RECOMMENDATION_FIELDS if not supplied.get(f)]
            if missing:
                raise LedgerError(
                    "a recommendation requires %s; missing: %s"
                    % (", ".join(RECOMMENDATION_FIELDS), ", ".join(missing)))
            based_on = _recommendation_shape(statement, confidence, based_on, extra)

        self.statement = statement
        self.provenance_class = provenance_class
        self.confidence = confidence
        self.source = source
        self.formula = formula
        self.inputs = dict(inputs or {})
        self.based_on = list(based_on or [])
        self.caveats = list(caveats or [])
        self.extra = extra

    @property
    def class_name(self):
        return CLASS_NAMES[self.provenance_class]

    @property
    def is_evidential(self):
        return self.provenance_class in EVIDENTIAL

    @property
    def label(self):
        """The FACT / INTERPRETATION marker shown in output."""
        if self.provenance_class in (USER_DATA, CONNECTED_DATA, CALCULATED):
            return "FACT"
        if self.provenance_class == EXTERNAL_SOURCED:
            return "SOURCED"
        if self.provenance_class == INTERPRETATION:
            return "INTERPRETATION"
        if self.provenance_class == ASSUMPTION:
            return "ASSUMPTION"
        return "RECOMMENDATION"

    def as_dict(self):
        record = {"statement": self.statement, "class": self.provenance_class,
                  "class_name": self.class_name, "label": self.label,
                  "confidence": self.confidence, "source": self.source,
                  "formula": self.formula, "inputs": self.inputs,
                  "based_on": self.based_on, "caveats": self.caveats}
        record.update(self.extra)
        return {k: v for k, v in record.items() if v not in (None, {}, [])}

    def __repr__(self):
        return "Claim(%s: %s)" % (self.label, self.statement[:60])


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _recommendation_shape(statement, confidence, based_on, extra):
    """Refuse a class-7 claim whose fields have the wrong shape; return its `based_on`.

    ADR-0031's canonical contract: a non-empty action, evidence as distinct synthesis statement
    ids, non-empty rationale and expected benefit, at least one non-empty risk, at least one
    dependency record `{text, assumption_id}`, a confidence level, and no other field. A text
    `based_on` is not provenance for a recommendation: it is either the evidence ids or absent.
    """
    if not _text(statement):
        raise LedgerError("a recommendation must state its action")
    unknown = sorted(set(extra) - set(RECOMMENDATION_FIELDS))
    if unknown:
        raise LedgerError(
            "a recommendation carries only %s; %s is not accepted"
            % (", ".join(RECOMMENDATION_FIELDS), ", ".join(unknown)))
    evidence = extra["evidence"]
    if (not isinstance(evidence, (list, tuple)) or not evidence
            or not all(isinstance(e, str) and RECOMMENDATION_EVIDENCE_ID.match(e)
                       for e in evidence)
            or len(set(evidence)) != len(evidence)):
        raise LedgerError(
            "a recommendation's evidence is a list of distinct synthesis statement ids; "
            "anything else is not evidence")
    for field in ("rationale", "expected_benefit"):
        if not _text(extra[field]):
            raise LedgerError("a recommendation's %s must be non-empty text" % field)
    risks = extra["risks"]
    if not isinstance(risks, (list, tuple)) or not risks or not all(_text(r) for r in risks):
        raise LedgerError("a recommendation's risks are a list of non-empty text")
    dependencies = extra["dependencies"]
    if not isinstance(dependencies, (list, tuple)) or not dependencies:
        raise LedgerError("a recommendation's dependencies are a non-empty list of records")
    for entry in dependencies:
        if (not isinstance(entry, dict)
                or set(entry) != set(RECOMMENDATION_DEPENDENCY_FIELDS)
                or not _text(entry["text"])
                or not (entry["assumption_id"] is None
                        or (isinstance(entry["assumption_id"], str)
                            and RECOMMENDATION_EVIDENCE_ID.match(entry["assumption_id"])))):
            raise LedgerError(
                "a recommendation dependency is exactly {text, assumption_id}: non-empty text "
                "and either no assumption or a synthesis statement id")
    if confidence not in CONFIDENCE_LEVELS:
        raise LedgerError("a recommendation's confidence is one of %s"
                          % ", ".join(CONFIDENCE_LEVELS))
    if based_on is not None and list(based_on) != list(evidence):
        raise LedgerError(
            "a recommendation's based_on, where given, is exactly its evidence ids; text is "
            "not provenance for a recommendation")
    return list(evidence)


class Ledger:
    """Every claim made during one analysis."""

    def __init__(self):
        self._claims = []
        self._caveats = []

    def add(self, claim):
        # Global caveats (e.g. a quality WARNING) attach to every claim, so they cannot be
        # dropped when a downstream step summarises.
        for caveat in self._caveats:
            if caveat not in claim.caveats:
                claim.caveats.append(caveat)
        self._claims.append(claim)
        return claim

    def record(self, statement, provenance_class, **kwargs):
        return self.add(Claim(statement, provenance_class, **kwargs))

    def add_global_caveat(self, caveat):
        """A caveat that must travel with every claim, past and future."""
        if caveat in self._caveats:
            return
        self._caveats.append(caveat)
        for claim in self._claims:
            if caveat not in claim.caveats:
                claim.caveats.append(caveat)

    @property
    def claims(self):
        return list(self._claims)

    def of_class(self, provenance_class):
        return [c for c in self._claims if c.provenance_class == provenance_class]

    def evidential(self):
        return [c for c in self._claims if c.is_evidential]

    def generative(self):
        return [c for c in self._claims if not c.is_evidential]

    def traceable(self, claim):
        """True if this claim rests on at least one evidential claim.

        Every major conclusion must trace to a class 1-4 entry; an interpretation that
        traces to nothing is an opinion and must be presented as one.
        """
        if claim.is_evidential:
            return True
        if not claim.based_on:
            return False
        evidential_ids = {c.statement for c in self.evidential()}
        return any(ref in evidential_ids for ref in claim.based_on)

    def untraceable(self):
        return [c for c in self.generative() if not self.traceable(c)]

    def summary(self):
        counts = {}
        for claim in self._claims:
            counts[claim.class_name] = counts.get(claim.class_name, 0) + 1
        return {"total": len(self._claims), "by_class": counts,
                "evidential": len(self.evidential()),
                "generative": len(self.generative()),
                "untraceable": len(self.untraceable()),
                "global_caveats": list(self._caveats)}

    def as_dict(self):
        return {"claims": [c.as_dict() for c in self._claims], "summary": self.summary()}

    def __len__(self):
        return len(self._claims)
