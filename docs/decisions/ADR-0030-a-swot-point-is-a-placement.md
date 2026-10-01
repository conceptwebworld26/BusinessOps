# ADR-0030 — A SWOT point is a placement of a synthesis statement, never new text

**Date:** 2026-09-16
**Status:** Accepted
**Deciders:** Project owner (M10.3.1 brief), implemented in M10.3.1

## Context

ADR-0022 built one synthesis representation for M10's four consumers and recorded, under
*Not decided here*, how SWOT, strategy, decision support and executive reporting would **use**
it. M10.2-R.10 to R.14 then made both halves of that representation reachable: four research
commands author strictly footed external statements, and the local join (ADR-0029) brings
internal analysis into the same strict set. Nothing yet read the result.

`architecture.md` §4 fixes one requirement for the first consumer: every SWOT point is tagged
*data-supported*, *externally-sourced* or *analytical-inference*. Verified by inspection, the
synthesis layer already carries the distinction those tags need — `FACT`/`CALCULATION` are
internal and internally footed (ADR-0023), `SOURCED` is external and untrusted, and
`INTERPRETATION` is constructible only through `merge.interpretation()`, which requires
supports already in the set and refuses advisory wording. `RECOMMENDATION` is refused
everywhere.

## Problem

What is a SWOT point, and where does its text, its tag and its grounding come from — so that a
SWOT cannot carry a claim nobody grounded, a relabelled source, or advice?

## Options considered

### Option A — A SWOT point is free text with a tag and citations
The model writes each point and lists the statement ids it rests on; code checks the ids exist.
Pros: natural prose. Cons: the text is new, unchecked assertion — an id check proves a citation
exists, not that the sentence says only what the citation supports. Recommendation language
would need a string filter, which is the brittle control the synthesis layer deliberately
avoided. The tag would be caller-chosen.

### Option B — Add a SWOT item kind (or quadrant field) to the synthesis representation
Pros: one object. Cons: changes an approved foundational contract and schema to serve one
consumer; ADR-0022 rejected exactly this shape of widening for `AnalysisSet`. Three more
consumers would each want a field.

### Option C — A SWOT point is a placement of an existing statement
A point is `{quadrant, tag, synthesis_id}` and nothing else. Its text, kind, support,
confidence, conflicts, materiality, limitations and chain are the statement's own. The tag is
**derived** from the kind and a disagreeing claim is refused. A reading not already in the set
is authored first through `synthesis.interpretation()`. A deterministic consumer module
checks grounding; the skill makes the quadrant judgement.

## Decision

**Option C.** Concretely:

1. `lib/python/biq/swot.py` consumes only a genuine `SynthesisSet` (`type(...) is`), built with
   `require_dimension_provenance=True`, non-empty, every item graded by `add()`.
2. A placement carries exactly `quadrant`, `tag`, `synthesis_id`. Any other field — text, score,
   rank, priority, weight, recommendation — is refused.
3. Tags are read from kinds: `FACT`/`CALCULATION` → data-supported, `SOURCED` →
   externally-sourced, `INTERPRETATION` → analytical-inference. `ASSUMPTION` and
   `RECOMMENDATION` have no tag. A mismatched claim is refused, never corrected.
4. **Side grounding.** Strengths and Weaknesses describe the internal side, Opportunities and
   Threats the external side. A data-supported point sits on the internal side, an
   externally-sourced point on the external side, and an inference on any side **at least one
   of its evidential supports** is on — so mixed support is allowed and absent support is not.
5. An inference's supports are read back from the note `interpretation()` already writes, via
   `merge.interpretation_supports()` — an additive reader beside the writer, with the prefix
   spelled once. The consumer checks each support exists once, precedes the reading, reaches
   evidence rather than an assumption, and that the supports account for exactly the
   provenance the reading carries; otherwise it is refused as forged.
6. Statements graded `unsupported` or `insufficient_evidence` are not points;
   `partially_supported` ones are, with their lowered confidence carried.
7. Conflicts, limitations and set confidence are carried whole, never filtered to the placed
   points. An empty quadrant carries an explicit empty state. Material statements left
   unplaced are listed. Point order is set order and is stated not to be a ranking.
8. The output schema (`lib/schemas/swot.schema.json`) is separate and closed
   (`additionalProperties: false` at every level), so no recommendation, score or rank field
   can appear. `synthesis.schema.json` is unchanged.

## Reason

Option C makes the two dangerous failures **unconstructible rather than filtered**: there is no
field for unsupported text and none for advice, and every word in a point already passed the
synthesis layer's provenance, footing and advisory guards. It reuses every existing judgement —
support, confidence, conflicts, materiality, limitations, dimension resolution — instead of
restating any, which ADR-0012 requires. It changes no foundational contract: the only engine
change outside the new module is an additive reader in `merge.py` whose writer output is
byte-identical. Option A's free text is the promotion path ADR-0022 exists to close; Option B
widens an approved schema for one of four consumers.

## Consequences

**Positive.** SWOT is small and fully deterministic in its grounding. Tags cannot be mislabelled.
The pattern — *consumers place or assemble synthesis statements; new readings enter only as
interpretations* — is available to the three remaining M10.3 consumers without deciding
anything for them.

**Negative.** A point's wording is the engine's or the research skill's sentence, which can be
drier than hand-written prose; anything more interpretive must be authored as an interpretation
first, adding a step. Favourable versus unfavourable is not machine-checkable: the engine proves
a Strength is internal and grounded, not that it is a strength — that remains model judgement
under human review. The supports note is text on the item; the reader cannot prove *who* wrote
it, only that it agrees with the chain the item actually carries. Two identical sentences
translated under one origin share an id and are refused as ambiguous, so internal analyses must
be translated under their own origins.

**Follow-up required.** None scheduled. Strategy recommendations, decision support and executive
reporting remain unbuilt; each decides its own use of the representation, and a class-7
recommendation still needs its own contract.

## Revisit when

- A consumer needs a point that genuinely combines several statements into one sentence that
  cannot be expressed as an interpretation.
- The synthesis representation gains a first-class supports field, at which point the note
  reader should be replaced by it.
- Evidence emerges that the internal/external side rule excludes a legitimate SWOT reading.
