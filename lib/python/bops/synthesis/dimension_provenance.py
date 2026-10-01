"""Where each comparability dimension came from, and whether that is good enough (ADR-0026).

`compatibility.compare()` asks whether two statements measure the same quantity, and it
answers by comparing seven dimension values for equality. Until M10.2-R.6 those seven values
were plain caller-supplied strings: nothing recorded where `currency: "USD"` came from, and
nothing could tell a value the source printed from one a model supplied because it seemed
obvious. M10.2-R.4 made that concrete - the run returned `unknown` only because the caller
declined to write `USD`, not because anything stopped them.

This module is the control that was missing. A `DimensionProvenance` says *this dimension,
this value, on this basis, from this evidence, at this location in it, applicable to this
period and scope* - and `resolve()` decides whether that claim survives contact with the
evidence registry. What survives reaches `compare()`; what does not reads as unstated, which
fails on `unknown` exactly as an absent dimension always has.

**Four bases, three admissible.**

    stated      the dimension appears in the statement's own cited evidence
    context     it appears elsewhere in the *same source document*, cited as its own item
    derived     a named, closed, fail-closed rule read it from text the source wrote
    asserted    somebody said so - recorded for audit, never admissible

**What is proved, and what is not.** Containment is checked, not meaning: `resolve()` proves
the excerpt is really in the retrieved source, byte for byte after whitespace folding. It
does **not** prove the excerpt *means* the value - that "Amounts are stated in US dollars"
establishes `USD` is a reading, and no code here pretends otherwise. What the check buys is
that the reading is now auditable against text the source demonstrably contains, instead of
resting on a caller's word. That boundary is stated here rather than hidden, because
pretending to semantic verification would be worse than not having it.

**Nothing here converts, normalises or reconciles anything.** There is no synonym table, no
canonicalisation of free text beyond the whitespace/case folding `compatibility` already
applies, and no rule that can derive `geography` or `methodology` at all.

**One dimension carries a predicate of its own.** M10.2-R.8 added the rule ADR-0025 always
implied and this layer was missing: a `stated` or `context` footing for `currency` is
admissible only where its excerpt prints the ISO 4217 code it claims. Before that, a footing
quoting "$4.2 billion" established `USD` - a measured gap, not a hypothetical one (ADR-0027
s4). A bare symbol and a currency name both still establish nothing.
"""

from .contract import DIMENSIONS, SynthesisError

# -- bases -------------------------------------------------------------------

STATED = "stated"
CONTEXT = "context"
DERIVED = "derived"
ASSERTED = "asserted"

#: Every basis a dimension may carry. Closed: an unrecognised basis is refused, never
#: treated as the weakest option, because "unknown basis" is a defect in the caller and a
#: silent downgrade would hide it.
BASES = (STATED, CONTEXT, DERIVED, ASSERTED)

#: The bases that may establish a dimension for compatibility. `ASSERTED` is deliberately
#: absent and there is no flag, mode or override that adds it.
ADMISSIBLE_BASES = (STATED, CONTEXT, DERIVED)

# -- derivation ---------------------------------------------------------------
#
# ADR-0025's `quantity.canonical_amount()` is the precedent and, for now, the whole
# registry: it reads the notation the source printed, it is decimal-exact, and it refuses
# rather than guesses - a bare "$" yields no currency. A derivation is admissible only on
# those terms, so the table below is closed, lives in code, and is reachable by no caller.

#: Rule identifiers permitted as `derivation`. Closed and immutable: there is no register
#: function, no plugin hook and no configuration key. A caller cannot add one.
DERIVATION_RULES = frozenset({
    "adr0025.canonical_amount.quantity_type",
    "adr0025.canonical_amount.currency_code",
})

#: Dimensions a derivation may establish **at all**. `geography` and `methodology` are
#: absent by decision, not by omission (ADR-0026): no rule may read a territory off a
#: company's identity, and no rule may read an accounting basis off a source's type.
DERIVABLE_DIMENSIONS = ("unit", "currency")

#: Dimensions for which no derivation rule may ever exist. Stated as data so a test can
#: assert the prohibition rather than trusting a comment.
NON_DERIVABLE_DIMENSIONS = tuple(d for d in DIMENSIONS if d not in DERIVABLE_DIMENSIONS)

#: Stated once so a test can assert it and a reader cannot miss it.
NEVER_INFERS = True


# -- the currency predicate (ADR-0027 s11) ------------------------------------
#
# ADR-0025 says a bare "$" establishes nothing, because at least four currencies print it.
# `quantity.parse_source_unit` holds that line for *notation*; until M10.2-R.8 nothing held
# it for a `stated` or `context` footing, so a footing quoting "$4.2 billion" could carry
# `value="USD"` all the way to `compare()`. That gap was measured, not theorised, and the
# predicate below closes it at the layer that was missing it.
#
# The shape is structural and is exactly the one `quantity.parse_source_unit` applies -
# three uppercase ASCII letters - because a closed list of world currencies is a maintenance
# burden that buys nothing, and a currency-*name* table is the first step towards the synonym
# engine ADR-0026 and ADR-0027 both refuse. A name therefore establishes nothing in v1, and
# that cost is recorded in ADR-0027 s23 rather than worked around here.

#: An ISO 4217 code's length. Named rather than inlined so the shape is one fact.
CURRENCY_CODE_LENGTH = 3

#: Punctuation stripped from a token's edges before the shape is read, so "(USD)" and "USD,"
#: are the code they print. Deliberately does not include "$", "-" or "/": stripping those
#: would turn "US$" into "US" and "USD-denominated" into something the source did not write.
_CODE_EDGE_PUNCTUATION = ".,;:!?()[]{}\"'"

#: Dimensions carrying a dimension-specific admissibility predicate beyond the bindings.
#: Stated as data so a test can assert the set rather than trusting a comment.
PREDICATED_DIMENSIONS = ("currency",)


def iso_currency_codes(excerpt):
    """Every distinct ISO 4217-shaped code the excerpt actually prints.

    Structural, not semantic: `USD` and `XQZ` are both codes by shape and `CEO` is too.
    That is deliberate - this function answers "did the source print a code here", and the
    caller then requires that code to be the one the footing claims, which is what keeps a
    three-letter word out.
    """
    codes = set()
    for token in str(excerpt or "").split():
        stripped = token.strip(_CODE_EDGE_PUNCTUATION)
        if (len(stripped) == CURRENCY_CODE_LENGTH and stripped.isascii()
                and stripped.isalpha() and stripped.isupper()):
            codes.add(stripped)
    return codes


def currency_excerpt_carries_code(value, excerpt):
    """Whether a currency footing's excerpt proves the code the footing claims.

    Three conditions, all necessary and all fail-closed:

    * the excerpt prints an ISO-shaped code at all - a bare `$`, `£`, `€` or `¥`, and a
      currency name such as "US dollars", do not;
    * it prints **exactly one** distinct code - an excerpt naming two currencies is
      ambiguous, and an ambiguous excerpt establishes nothing rather than the first one;
    * that code is the value the footing declares - otherwise the excerpt is evidence for
      some other currency, and a footing may not borrow it.

    Comparison uses `_fold`, this module's one normalisation, so a lowercase `value` still
    matches the uppercase code the source printed. Detection of the code itself stays
    uppercase-strict, because that is the shape ADR-0025 reads from notation and loosening
    it here would admit "usd" in prose that no source wrote as a code.
    """
    codes = iso_currency_codes(excerpt)
    if len(codes) != 1:
        return False
    return _fold(codes.pop()) == _fold(value)


# -- why a dimension was refused ---------------------------------------------
#
# Reason codes rather than prose, so a caller can branch and a test can assert the reason
# instead of the wording. Every one of these results in the dimension reading as unstated.

UNRESOLVED_EVIDENCE = "unresolved_evidence"
NOT_CITED = "evidence_not_cited_by_statement"
WRONG_OPERATION = "operation_mismatch"
WRONG_DOCUMENT = "document_mismatch"
EXCERPT_ABSENT = "excerpt_not_in_source"
NOT_APPLICABLE = "applicability_mismatch"
BASIS_INADMISSIBLE = "basis_inadmissible"
DERIVATION_UNKNOWN = "derivation_not_registered"
DERIVATION_FORBIDDEN = "derivation_forbidden_for_dimension"
VALUE_DISAGREES = "value_disagrees_with_statement"
CONTEXT_CONFLICT = "conflicting_admissible_values"
CURRENCY_CODE_ABSENT = "currency_code_not_in_excerpt"
NO_PROVENANCE = "no_dimension_provenance"

REASON_TEXT = {
    UNRESOLVED_EVIDENCE: "The cited evidence item is not registered in this set.",
    NOT_CITED: "The statement does not cite this evidence item, so it cannot be the "
               "statement's own stated source.",
    WRONG_OPERATION: "The evidence came from a different retrieval operation.",
    WRONG_DOCUMENT: "The context evidence is a different document from the statement's "
                    "own source. Cross-source context is not permitted.",
    EXCERPT_ABSENT: "The quoted excerpt does not appear in the retrieved source content.",
    NOT_APPLICABLE: "The context does not declare applicability to this statement's "
                    "period and scope.",
    BASIS_INADMISSIBLE: "An asserted dimension is recorded but never establishes "
                        "comparability.",
    DERIVATION_UNKNOWN: "The named derivation rule is not in the closed registry.",
    DERIVATION_FORBIDDEN: "No derivation rule may establish this dimension.",
    VALUE_DISAGREES: "The provenance states a different value from the statement.",
    CONTEXT_CONFLICT: "Two admissible sources establish different values; the dimension "
                      "is left unresolved and the disagreement is recorded.",
    CURRENCY_CODE_ABSENT: "The quoted excerpt does not print the ISO 4217 code this "
                          "footing claims. A bare currency symbol, a currency name, and an "
                          "excerpt naming two currencies all establish nothing (ADR-0025).",
    NO_PROVENANCE: "No dimension provenance was supplied for this dimension.",
}


def _fold(value):
    """Case- and whitespace-insensitive text, or `None`. Mirrors `compatibility._normalise`.

    Deliberately identical in strength to the comparison engine's folding and no stronger:
    anything more would be a synonym table by another name, which ADR-0026 puts out of
    scope.
    """
    if value is None:
        return None
    text = " ".join(str(value).split()).strip().lower()
    return text or None


class DimensionProvenance:
    """One dimension's footing: value, basis, evidence, locator and applicability.

    Immutable once built, for the reason every authorisation object in this codebase is:
    a footing that can be edited between the check and the comparison establishes nothing.
    Source identity, tier, freshness and retrieval date are **not** constructor arguments -
    they are read from the resolved `EvidenceItem` at resolution and serialisation time, so
    a caller has no field in which to assert a stronger source than the one it cites.
    """

    __slots__ = ("dimension", "value", "basis", "evidence_id", "source_excerpt",
                 "source_locator", "applicability", "derivation", "_frozen")

    def __init__(self, dimension, value, basis, evidence_id=None, source_excerpt=None,
                 source_locator=None, applicability=None, derivation=None, **forbidden):
        if forbidden:
            raise SynthesisError(
                "these fields are resolved from the cited evidence item and may not be "
                "supplied: %s. Source identity, tier, freshness and retrieval date are "
                "read from the evidence, never from the caller."
                % ", ".join(sorted(forbidden)))
        if dimension not in DIMENSIONS:
            raise SynthesisError(
                "%r is not one of the seven comparability dimensions: %s"
                % (dimension, ", ".join(DIMENSIONS)))
        if basis not in BASES:
            raise SynthesisError(
                "%r is not a dimension-provenance basis; one of %s"
                % (basis, ", ".join(BASES)))
        if basis in ADMISSIBLE_BASES and not (evidence_id and str(evidence_id).strip()):
            raise SynthesisError(
                "a %r dimension must name the evidence item it rests on; provenance that "
                "names nothing is not provenance." % (basis,))
        if basis == DERIVED:
            if dimension not in DERIVABLE_DIMENSIONS:
                raise SynthesisError(
                    "no derivation rule may establish %r. %s are established only by "
                    "what a source actually states (ADR-0026)."
                    % (dimension, " and ".join(NON_DERIVABLE_DIMENSIONS)))
            if derivation not in DERIVATION_RULES:
                raise SynthesisError(
                    "%r is not a registered derivation rule. The registry is closed and "
                    "holds: %s" % (derivation, ", ".join(sorted(DERIVATION_RULES))))
        elif derivation is not None:
            raise SynthesisError(
                "a derivation rule may be named only on a %r dimension" % (DERIVED,))
        if basis in (STATED, CONTEXT) and not (source_excerpt
                                               and str(source_excerpt).strip()):
            raise SynthesisError(
                "a %r dimension must quote the source text it rests on, so the reading "
                "can be audited against what the source actually contains." % (basis,))

        self.dimension = dimension
        self.value = value
        self.basis = basis
        self.evidence_id = str(evidence_id) if evidence_id is not None else None
        self.source_excerpt = source_excerpt
        self.source_locator = source_locator
        self.applicability = dict(applicability or {})
        self.derivation = derivation
        self._frozen = True

    # -- immutability -------------------------------------------------------

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False):
            raise SynthesisError(
                "dimension provenance is immutable once built; %r cannot be changed. "
                "Build a new one rather than editing a footing that has been resolved."
                % name)
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        raise SynthesisError("dimension provenance is immutable once built")

    @property
    def admissible_basis(self):
        """Whether the basis *could* establish a dimension. Bindings are checked at resolve."""
        return self.basis in ADMISSIBLE_BASES

    def as_dict(self, evidence=None):
        """The audit record. Source metadata comes from `evidence`, never from this object."""
        record = {
            "dimension": self.dimension,
            "value": self.value,
            "basis": self.basis,
            "evidence_id": self.evidence_id,
            "source_excerpt": self.source_excerpt,
            "source_locator": self.source_locator,
            "applicability": dict(self.applicability) or None,
            "derivation": self.derivation,
        }
        if evidence is not None:
            record.update({
                "source": evidence.source,
                "reference": evidence.reference,
                "operation": evidence.operation,
                "retrieved_at": evidence.retrieved_at,
                "freshness": evidence.freshness["freshness"],
                "source_tier": evidence.source_tier,
                "trust": evidence.trust,
            })
        return dict((k, v) for k, v in record.items() if v is not None)

    @classmethod
    def from_dict(cls, record):
        """Rebuild from a serialised record, keeping only the caller-authored fields.

        Source metadata present in the record is **discarded**, not read: on reload the
        evidence registry is the authority, and a serialised tier or freshness is exactly
        the kind of payload-carried metadata this architecture refuses everywhere else.
        """
        if not isinstance(record, dict):
            raise SynthesisError("dimension provenance must be a record")
        return cls(record.get("dimension"), record.get("value"), record.get("basis"),
                   evidence_id=record.get("evidence_id"),
                   source_excerpt=record.get("source_excerpt"),
                   source_locator=record.get("source_locator"),
                   applicability=record.get("applicability"),
                   derivation=record.get("derivation"))

    def __repr__(self):
        return "DimensionProvenance(%s=%r via %s)" % (self.dimension, self.value,
                                                      self.basis)


# -- authoring ---------------------------------------------------------------
#
# Every research skill that migrates to footings has the same small job: quote the passages
# one retrieved document actually states, and turn each quote into a footing. Written in
# four skills that would become four conventions, so it is written once, here, beside the
# type it builds (ADR-0027 s17).
#
# It is deliberately the only thing shared, and it is powerless. It looks up no evidence,
# binds no operation, compares no document, checks no applicability and reads no currency
# code - `resolve()` still judges every footing this builds against the registry, exactly
# as it judges one written by hand. A caller gains brevity here and no authority.


def source_footings(evidence_id, claims, basis=STATED, applicability=None, locator=None):
    """Author one source-quoted footing per dimension, in the fixed dimension order.

    `claims` maps a dimension to the `(value, source_excerpt)` pair the document supports:
    the value the footing claims, and the contiguous verbatim text it is read from. One
    call covers one evidence item on one basis, which is what keeps a caller explicit about
    *which* document each quote came from - a figure in one item and its context in another
    is two calls, never one call with a hidden default.

    Only `stated` and `context` are authored here. `derived` reads the notation a source
    printed rather than a quote and is produced by ADR-0025 canonicalisation; `asserted` is
    never admissible, and a convenience path able to emit one would be a convenience path
    for fabrication. Both stay constructible directly, where their reason is explicit.

    A mistyped dimension is refused rather than skipped: a silently dropped footing looks
    exactly like a dimension the source never stated, and those two must never be confused.
    """
    if basis not in (STATED, CONTEXT):
        raise SynthesisError(
            "a %r footing is not authored from a quoted excerpt: %r reads notation the "
            "source printed and belongs to the closed derivation registry, and %r never "
            "establishes a dimension at all. Construct either one directly."
            % (basis, DERIVED, ASSERTED))

    unknown = sorted(d for d in claims if d not in DIMENSIONS)
    if unknown:
        raise SynthesisError(
            "%s names no comparability dimension; the seven are %s"
            % (", ".join(repr(d) for d in unknown), ", ".join(DIMENSIONS)))

    built = []
    for dimension in DIMENSIONS:
        if dimension not in claims:
            continue
        claim = claims[dimension]
        if isinstance(claim, (str, bytes)) or not isinstance(claim, (tuple, list))                 or len(claim) != 2:
            raise SynthesisError(
                "the %r footing must be a (value, source_excerpt) pair; got %r. The "
                "excerpt is not optional - a value carrying no quoted text is an "
                "assertion, and an assertion establishes nothing." % (dimension, claim))
        value, excerpt = claim
        built.append(DimensionProvenance(
            dimension, value, basis, evidence_id=evidence_id, source_excerpt=excerpt,
            source_locator=locator, applicability=dict(applicability or {})))
    return built


# -- resolution ---------------------------------------------------------------


def _excerpt_present(excerpt, evidence):
    """Whether the quoted text really is in the retrieved source. Containment, not meaning."""
    needle = _fold(excerpt)
    if needle is None:
        return False
    for field in (evidence.content, evidence.title):
        haystack = _fold(field)
        if haystack is not None and needle in haystack:
            return True
    return False


def _applies(entry, item):
    """Whether the context declares applicability to this statement's period and scope.

    Both axes must be declared and must match the statement. An undeclared axis is not
    read as "applies everywhere" - that is the assumption this check exists to refuse, and
    a context note that does not say what it governs governs nothing.
    """
    declared = entry.applicability or {}
    for axis in ("period", "scope"):
        stated = _fold(declared.get(axis))
        target = _fold(getattr(item, axis, None))
        if stated is None or target is None or stated != target:
            return False
    return True


def _cited_evidence_ids(item):
    from .contract import P_EVIDENCE
    return set(str(ref.ref_id) for ref in item.provenance if ref.kind == P_EVIDENCE)


def _assess(entry, item, synthesis):
    """Judge one footing. Returns `(evidence_or_None, reason_or_None)`.

    Every check fails closed: an entry that cannot be shown to hold is refused, and the
    dimension then reads as unstated rather than as a match.
    """
    from .contract import P_EVIDENCE

    if not entry.admissible_basis:
        return None, BASIS_INADMISSIBLE

    if entry.basis == DERIVED:
        if entry.dimension not in DERIVABLE_DIMENSIONS:
            return None, DERIVATION_FORBIDDEN
        if entry.derivation not in DERIVATION_RULES:
            return None, DERIVATION_UNKNOWN

    evidence = synthesis._registry.get(P_EVIDENCE, {}).get(str(entry.evidence_id))
    if evidence is None:
        return None, UNRESOLVED_EVIDENCE

    cited = _cited_evidence_ids(item)

    # Operation binding. The operation id is minted per retrieval after the page was
    # written, so a page's author cannot know it; requiring every footing to share the
    # statement's operation is what stops evidence from one retrieval footing another.
    operations = set()
    for eid in cited:
        other = synthesis._registry[P_EVIDENCE].get(eid)
        if other is not None and other.operation is not None:
            operations.add(str(other.operation))
    if evidence.operation is not None and operations \
            and str(evidence.operation) not in operations:
        return None, WRONG_OPERATION

    if entry.basis in (STATED, DERIVED):
        # A stated or derived dimension rests on the statement's own source, not on a
        # neighbour: the derivation reads the notation *this* source printed.
        if str(entry.evidence_id) not in cited:
            return None, NOT_CITED
    elif entry.basis == CONTEXT:
        # Same document, established mechanically by identical reference. Same company,
        # same publisher and same filing family are judgements, and a judgement is exactly
        # what must not sit between an unstated dimension and a compatible verdict.
        references = set()
        for eid in cited:
            other = synthesis._registry[P_EVIDENCE].get(eid)
            if other is not None:
                references.add(_fold(other.reference))
        if _fold(evidence.reference) not in references:
            return None, WRONG_DOCUMENT
        if not _applies(entry, item):
            return None, NOT_APPLICABLE

    if entry.basis in (STATED, CONTEXT):
        if not _excerpt_present(entry.source_excerpt, evidence):
            return None, EXCERPT_ABSENT
        # Dimension-specific predicate (ADR-0027 s12-13). Containment is asked first and
        # deliberately: an excerpt the source never printed is absent, not merely
        # code-less, and the trail should say the more fundamental thing.
        if entry.dimension == "currency" and not currency_excerpt_carries_code(
                entry.value, entry.source_excerpt):
            return None, CURRENCY_CODE_ABSENT

    return evidence, None


def resolve(synthesis, item):
    """Resolve one statement's seven dimensions against its footings and the registry.

    Returns `(values, records)`. `values` is the seven-key dict `compatibility.compare()`
    reads - a dimension appears with its value only when an admissible, fully bound footing
    established it. `records` is the audit trail: every footing, admitted or refused, with
    the reason.

    **Where a dimension carries no footing at all**, the statement's declared value is
    passed through unchanged, exactly as before M10.2-R.6. That keeps this strictly
    additive: a caller that has not migrated behaves as it always did. A set built with
    `require_dimension_provenance=True` refuses that pass-through for external statements,
    which is how the gap is closed for callers who opt in. See ADR-0026's follow-up.
    """
    strict = bool(getattr(synthesis, "require_dimension_provenance", False))
    from .contract import EXTERNAL

    declared = item.declared_dimensions
    by_dimension = {}
    for entry in item.dimension_provenance:
        by_dimension.setdefault(entry.dimension, []).append(entry)

    values, records = {}, []
    for dimension in DIMENSIONS:
        entries = by_dimension.get(dimension, [])
        if not entries:
            if strict and item.domain == EXTERNAL and declared.get(dimension) is not None:
                values[dimension] = None
                records.append({"dimension": dimension, "admitted": False,
                                "basis": None, "reason": NO_PROVENANCE,
                                "explanation": REASON_TEXT[NO_PROVENANCE],
                                "declared": declared.get(dimension)})
            else:
                values[dimension] = declared.get(dimension)
            continue

        # Each footing is judged on its own bindings first. Whether it agrees with what
        # the statement declared is asked **afterwards**, and deliberately so: checking
        # agreement first would silence every competing footing before the disagreement
        # between two sources could be seen, which is precisely the finding worth keeping.
        admitted = []
        for entry in entries:
            evidence, reason = _assess(entry, item, synthesis)
            record = entry.as_dict(evidence if reason is None else None)
            record["admitted"] = reason is None
            if reason is not None:
                record["reason"] = reason
                record["explanation"] = REASON_TEXT[reason]
            records.append(record)
            if reason is None:
                admitted.append(entry)

        distinct = set(_fold(e.value) for e in admitted)
        if len(distinct) > 1:
            # Never a winner: not the newest, not the highest tier, not the first.
            values[dimension] = None
            records.append({"dimension": dimension, "admitted": False, "basis": None,
                            "reason": CONTEXT_CONFLICT,
                            "explanation": REASON_TEXT[CONTEXT_CONFLICT],
                            "values": sorted(str(e.value) for e in admitted)})
        elif admitted:
            if _fold(admitted[0].value) != _fold(declared.get(dimension)):
                values[dimension] = None
                records.append({"dimension": dimension, "admitted": False,
                                "basis": admitted[0].basis, "reason": VALUE_DISAGREES,
                                "explanation": REASON_TEXT[VALUE_DISAGREES],
                                "declared": declared.get(dimension),
                                "footed": admitted[0].value})
            else:
                values[dimension] = admitted[0].value
        else:
            values[dimension] = None

    return values, records


def conflicting_dimensions(records):
    """The dimensions whose footings disagreed, read back from a resolution trail."""
    return sorted(set(r["dimension"] for r in records
                      if r.get("reason") == CONTEXT_CONFLICT))
