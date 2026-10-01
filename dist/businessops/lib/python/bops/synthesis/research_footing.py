# -*- coding: utf-8 -*-
"""The research command's footing path: one retrieval, one statement, one strict set.

M10.2-R.6 built dimension admissibility, R.8 gave the evidence record the source text a
footing quotes, and R.9 gave the research skills one authoring helper and told Company
Analysis how to use it. What none of them built was a path a **command** actually takes.
`close_retrieval()` hands its caller a serialised evidence set, `register_external()`
accepts only the object, and every step between "the scout replied" and "these two figures
may be compared" was assembled by hand inside a test. R.9 recorded that in its own
limitations - *no command wires this up* - and this module is the wiring:

    research.close_retrieval_object()  ->  EvidenceSet object           (ADR-0024)
    footed_statement()                 ->  register_external
                                       ->  source_footings              (ADR-0027)
                                       ->  sourced_statement
                                       ->  SynthesisSet.add -> resolve  (ADR-0026)
    synthesis.compare_values()         ->  compatibility.compare()

**It decides nothing.** There is no evidence lookup here, no operation or document binding,
no containment test, no applicability test, no currency predicate and no conflict handling:
every one of those stays in `dimension_provenance.resolve()`, reached from
`SynthesisSet.add()`, and judges a footing this module authored exactly as it judges one
written by hand. Ordering is the whole contribution, plus the four refusals that stop the
ordering being skipped:

* the evidence must be the object a **completed retrieval** produced, so a caller cannot
  hand-assemble a set that never went through parsing, local tiering and operation binding;
* the set must be **strict** (`require_dimension_provenance=True`), so a dimension the
  caller declared but no source footed reads as unstated rather than as a match;
* a dimension is **either footed or declared, never both**, because two descriptions of one
  value can disagree and only the footing is checked against the source;
* a `context` footing **names its own evidence item**, because a figure in one document and
  its context in another is the composition ADR-0026 prohibits, and a default would hide
  which document a quote came from.

Nothing here promotes anything. A footed statement is still `SOURCED`, still external,
still untrusted, still provenance class 3 and still unverified; no tier, trust, support or
confidence moves because a dimension resolved. There is no parameter for any of them.
"""

from collections import namedtuple

from .. import quantity as quantity_mod
from ..research import contract as research_contract
from ..research import evidence_set as evidence_mod
from . import dimension_provenance as dp_mod
from . import merge as merge_mod
from . import synthesis_set as set_mod
from .contract import DIMENSIONS, SynthesisError

#: The one derivation rule this path may name, and it is already in the closed registry in
#: `dimension_provenance.DERIVATION_RULES`. Named here so the seam reads a rule rather than
#: inventing one; a rule not in that registry is refused by the constructor either way.
UNIT_DERIVATION = "adr0025.canonical_amount.quantity_type"

#: Dimensions that are never read from a quotation. `unit` names a quantity type, which
#: ADR-0025 canonicalisation produces from the notation the source printed - quoting a
#: sentence to establish it would be a second, unchecked route to the same field.
NOT_QUOTABLE = ("unit",)

#: Statement fields this path owns. A caller supplying one would be building a second
#: citation or a second set of footings beside the ones that were just authored.
RESERVED_FIELDS = ("evidence_ids", "dimension_provenance", "unit")


class FootedStatement(namedtuple("FootedStatement",
                                 "synthesis statement footings resolved unresolved")):
    """One sourced statement, the footings authored for it, and what they established.

    `resolved` and `unresolved` are the two halves of the same verdict, read back from the
    item after the set resolved it: what reached `compatibility.compare()`, and what did
    not and why. They are a **view**, not a decision - nothing here can add a dimension the
    resolution refused.
    """

    __slots__ = ()

    @property
    def dimensions(self):
        """The resolved seven-key view `compatibility.compare()` reads."""
        return self.statement.dimensions

    def as_dict(self):
        """The record a markdown command reads off stdout. No source metadata is added."""
        return {"statement_id": self.statement.id,
                "kind": self.statement.kind,
                "resolved": dict(self.resolved),
                "unresolved": dict(self.unresolved),
                "footed_dimensions": [entry.dimension for entry in self.footings]}


def evidence_from_retrieval(retrieval):
    """The genuine `EvidenceSet` object a completed retrieval produced, or a refusal.

    Four checks, and the last is the one that matters: `type(...) is EvidenceSet`. A
    subclass may never have run `__init__`, and a look-alike carries none of the operation
    binding, locally derived tiering or retrieved content that every admissibility check
    downstream is made of - so neither is accepted however convincing it looks.
    """
    if not isinstance(retrieval, dict):
        raise SynthesisError(
            "a footed statement is built from what research.close_retrieval_object() "
            "returned, which is a record; %r is not one" % type(retrieval).__name__)
    if "evidence_set" not in retrieval and "evidence" in retrieval:
        raise SynthesisError(
            "this is a close_retrieval() result, which carries the evidence set "
            "serialised. A serialised set brings its source tiers along as data, and a "
            "tier is derived locally from the source rather than accepted from a payload. "
            "Call research.close_retrieval_object() instead (ADR-0024).")
    status = retrieval.get("status")
    if status != research_contract.OK:
        raise SynthesisError(
            "the retrieval did not complete (status %r), so there is nothing to foot. A "
            "refusal, a failed retrieval and one that returned nothing citable each "
            "produce no statement rather than an unfooted one." % (status,))
    evidence = retrieval.get("evidence_set")
    if type(evidence) is not evidence_mod.EvidenceSet:
        raise SynthesisError(
            "only the EvidenceSet object a completed retrieval produced may be footed. A "
            "dict, a subclass or a look-alike carries none of the operation binding, the "
            "locally derived tiers or the retrieved content a footing is checked against.")
    return evidence


def footed_statement(retrieval, origin, statement, figure_evidence_id, stated=None,
                     context=None, context_evidence_id=None, applicability=None,
                     locator=None, context_locator=None, synthesis=None, subject=None,
                     **statement_fields):
    """Record what one retrieved document said, with the dimensions that document footed.

    `stated` and `context` map a dimension to the `(value, source_excerpt)` pair the
    document supports, exactly as `synthesis.source_footings()` takes them - `stated`
    against the item the statement cites, `context` against an item named explicitly.
    Whatever is footed is also what the statement declares, so a footing and a declaration
    cannot disagree by typing; whatever is *not* footed may still be declared, and in a
    strict set it then reads as unstated, which is the point.

    `unit` is authored from the notation rather than from a quote: supplying `source_unit`
    canonicalises the figure (ADR-0025) and adds the one `derived` footing the closed
    registry permits. Supplying no notation leaves `unit` unfooted and therefore unstated,
    which fails a comparison on `unknown` - the correct outcome, not a gap to fill.

    Returns a `FootedStatement`. Raises `SynthesisError` rather than degrading whenever the
    path itself was not followed; a footing that merely fails to hold is not an error, it
    is an unresolved dimension, and it comes back in `unresolved` with its reason code.
    """
    evidence = evidence_from_retrieval(retrieval)

    owned = sorted(set(statement_fields) & set(RESERVED_FIELDS))
    if owned:
        raise SynthesisError(
            "%s is set by this path and may not be supplied: the statement cites the "
            "evidence item its figure came from, carries the footings authored here, and "
            "takes its unit from ADR-0025 canonicalisation of the source's own notation."
            % ", ".join(owned))

    stated = dict(stated or {})
    context = dict(context or {})
    unquotable = sorted((set(stated) | set(context)) & set(NOT_QUOTABLE))
    if unquotable:
        raise SynthesisError(
            "%s is not read from a quotation. It names a quantity type, which ADR-0025 "
            "canonicalisation produces from the notation the source printed; supply that "
            "notation as source_unit and the footing is authored from it."
            % ", ".join(unquotable))

    footings = []
    if stated:
        footings += dp_mod.source_footings(figure_evidence_id, stated,
                                           basis=dp_mod.STATED, locator=locator)
    if context:
        if not (context_evidence_id and str(context_evidence_id).strip()):
            raise SynthesisError(
                "a context footing must name the evidence item it was read from. The "
                "statement's own item is a legitimate answer and is written out; what is "
                "not legitimate is a default, because a figure in one document and its "
                "context in another is the composition ADR-0026 prohibits.")
        footings += dp_mod.source_footings(
            context_evidence_id, context, basis=dp_mod.CONTEXT,
            applicability=applicability, locator=context_locator)

    # The statement declares what the footings claim. Where a dimension is claimed twice,
    # the first reading is declared and the second is still resolved: two admissible
    # footings that disagree leave the dimension unresolved and record the disagreement,
    # which is a finding and must not be silenced by the declaration.
    declared = {}
    for footing in footings:
        declared.setdefault(footing.dimension, footing.value)

    source_unit = statement_fields.get("source_unit")
    if source_unit is not None:
        observed = statement_fields.get("observed")
        if observed is None:
            raise SynthesisError(
                "source notation was supplied with no figure to canonicalise")
        # The same call `sourced_statement` makes, so the footing names the quantity type
        # the statement will actually carry rather than one a caller typed beside it.
        quantity_type = quantity_mod.canonical_amount(observed, unit_text=source_unit)[1]
        footings.append(dp_mod.DimensionProvenance(
            "unit", quantity_type, dp_mod.DERIVED, evidence_id=figure_evidence_id,
            derivation=UNIT_DERIVATION))

    clash = sorted(set(statement_fields) & set(declared))
    if clash:
        raise SynthesisError(
            "%s is both footed and declared. A dimension is read from the source text "
            "that carries it or not at all: two descriptions of one value can disagree, "
            "and only the footing is checked against what the source contains."
            % ", ".join(clash))

    if synthesis is None:
        synthesis = set_mod.SynthesisSet(subject=subject or evidence.subject,
                                         require_dimension_provenance=True)
    elif not isinstance(synthesis, set_mod.SynthesisSet):
        raise SynthesisError("a footed statement may be added only to a SynthesisSet")
    elif not synthesis.require_dimension_provenance:
        raise SynthesisError(
            "a footed statement belongs only in a set built with "
            "require_dimension_provenance=True. Without it a dimension the caller "
            "declared but no source footed passes through unchecked, which is the "
            "pass-through ADR-0026 closes and the whole reason this path exists.")

    merge_mod.register_external(synthesis, evidence, origin)

    fields = dict(declared)
    fields.update(statement_fields)
    item = merge_mod.sourced_statement(
        synthesis, origin, statement, evidence_ids=[figure_evidence_id],
        dimension_provenance=footings, **fields)

    resolved, unresolved = dimension_report(item)
    return FootedStatement(synthesis, item, tuple(footings), resolved, unresolved)


def dimension_report(item):
    """`(resolved, unresolved)` for one statement, read back from its resolution trail.

    `resolved` holds only dimensions an admissible, fully bound footing established.
    `unresolved` maps each remaining dimension to the reason code its footing failed on, or
    to `no_dimension_provenance` where none was authored. Both are views of what the set
    already decided; neither recomputes anything.
    """
    values = item.dimensions
    reasons = {}
    for record in item.dimension_resolution:
        if record.get("reason") and record.get("dimension"):
            reasons.setdefault(record["dimension"], []).append(record["reason"])

    resolved, unresolved = {}, {}
    for dimension in DIMENSIONS:
        value = values.get(dimension)
        if value is not None:
            resolved[dimension] = value
        else:
            named = reasons.get(dimension) or [dp_mod.NO_PROVENANCE]
            unresolved[dimension] = named[-1]
    return resolved, unresolved
