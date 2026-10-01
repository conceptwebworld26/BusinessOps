# ADR-0026 — A dimension is admissible for compatibility only where its provenance says a source stated it

**Date:** 2026-09-15
**Status:** Accepted
**Deciders:** Owner, via the M10.2-R.5 scoped decision milestone

## Context

The M10.2-R.4 live verification (2026-09-15) ran a real Tier 0 retrieval through the real
scout, the real parser and the real retrieval→synthesis seam, and compared a live external
statement against an internal figure. It returned `unknown`: four of the seven dimensions
matched, three — `geography`, `currency`, `methodology` — were unstated on both sides.

That verdict was correct. What the run also exposed is that it was correct *by the caller's
restraint rather than by any control*. Tracing the implementation establishes the following,
by inspection:

* **Five of the seven dimensions are unvalidated caller text.** `metric_definition`,
  `period`, `geography`, `scope` and `methodology` are plain keyword arguments to
  `synthesis.merge.sourced_statement()`, stored as attributes on `SynthesisItem`. Nothing
  checks them against anything.
* **There is no per-dimension provenance anywhere.** `ProvenanceRef` is statement-level: it
  says which evidence a *statement* rests on, never which evidence a *dimension* rests on.
* **`compatibility.compare()` tests the dimension by exact equality** after case-folding and
  whitespace collapse, and converts nothing (`NEVER_CONVERTS = True`).
* **So a caller writing `currency="USD"` from background knowledge would have produced
  `compatible`, and nothing in the serialised record would have shown it was a guess.** In
  M10.2-R.4 the only thing that prevented it was the operator declining to write it.
* **One mechanism already does this safely, and it is the precedent for the whole
  decision.** `quantity.canonical_amount()` (ADR-0025) derives `unit` and `currency` from
  the notation the source printed, and refuses when the text does not state: a bare `$`
  yields `currency=None` rather than USD, because four currencies use that symbol.

## Problem

An external source frequently states a dimension *somewhere in the document* without
repeating it in the sentence carrying the figure. "Amounts are stated in US dollars" sits in
a header; "Total revenue was $281.7 billion" sits in a table. Should BusinessIQ be able to
use the first to establish the currency of the second — and if so, how, without that
mechanism becoming a doorway for a model to supply whatever dimension makes a comparison
pass?

## Options considered

### Option A — Keep strict statement-only semantics, change nothing
**Pros:** simplest; zero work; `compare()` untouched.
**Cons:** does **not** close the hole. It cannot distinguish a stated dimension from an
asserted one, so its safety is procedural rather than structural. It also makes a live
`ALLOW` unnecessarily rare where a source genuinely does state everything, just not in one
sentence.

### Option B — A dedicated `SourceContext` descriptor type
**Pros:** explicit; provenance-bearing.
**Cons:** `EvidenceItem` *already is* a source-context carrier — it has an id, a reference, a
locally derived tier, an operation binding, freshness and an untrusted marking. A parallel
evidence-like type would need every one of those controls re-implemented, and would then be
able to drift from them. A second home for one concept is what ADR-0012 forbids.

### Option C — Dimension-specific provenance, with `EvidenceItem` as the sole carrier
Each stated dimension records where it came from: the evidence item, the basis, the verbatim
source text, the locator, and the period and scope the footing governs. Resolution happens
before construction; `compare()` sees an already-resolved view.

### Option D — Deterministic source rules
A registry deriving dimensions from source properties.
**Cons as a general mechanism:** a rule keyed on source *type* ("it is a 10-K, therefore US
GAAP") encodes a regulatory generalisation as if it were an observation, and is wrong for
foreign private issuers filing under IFRS. That is a hidden assumption wearing a registry's
clothes.

### Option E — Model-derived context
Allow the model to supply dimensions from general knowledge.
**Cons:** fatal. Model inference is provenance class 5 at best, and class 5 may never
establish that two figures measure the same quantity. It would make `ALLOW` easy and
meaningless.

## Decision

**Option C, with Option D admitted narrowly inside it.**

1. **The seven dimensions are unchanged:** `metric_definition`, `period`, `geography`,
   `currency`, `unit`, `scope`, `methodology`.
2. **Four bases exist:** `stated`, `context`, `derived`, `asserted`.
3. **`asserted` is never admissible.** It is retained and serialised for audit, and reads as
   unstated wherever dimensions are resolved for comparison. There is no flag, mode or
   override that admits it.
4. **`stated` is admissible** only where the footing cites an evidence item the statement
   itself cites, and the quoted excerpt is genuinely present in that item's retrieved
   content.
5. **`context` is admissible** only where the cited evidence item is in the same
   `EvidenceSet`, from the same retrieval operation, from the **same source document**
   (identical reference), quotes text genuinely present in that item, and declares an
   applicability covering the target statement's period and scope.
6. **`derived` is admissible** only through an enumerated rule in a closed registry that
   reads information the source actually stated, is deterministic, and fails closed. It may
   not use company identity, source host, or source type alone, and may not use general
   model knowledge.
7. **`geography` has no derived path.**
8. **`methodology` has no derived path.**
9. **Source type may never establish methodology.**
10. **Company identity may never establish geography.**
11. **A bare `$` does not establish USD**, exactly as ADR-0025 already requires.
12. **Currency conversion remains prohibited**, with no approval path.
13. **`EvidenceItem` remains the sole source-context carrier.**
14. **No second `SourceContext` object is introduced.**
15. **Cross-source context is prohibited in v1.** Same document, established mechanically by
    identical reference. Same company, same publisher, same filing family and same reporting
    package are judgements, and a judgement must not sit between an unstated dimension and a
    compatible verdict.
16. **Dimension provenance is immutable once built** and bound to its evidence.
17. **Dimension provenance is re-resolved on deserialisation.** A serialised admissibility
    verdict is a verdict nobody re-checked, and is not restored.
18. **`compatibility.compare()` remains unchanged**, byte for byte.
19. **Comparability implies nothing else.** It does not confer trust, verification, support
    uplift, confidence uplift or a recommendation.
20. **External evidence remains `SOURCED`, external and untrusted**, before and after.
21. **Conflicting admissible footings leave the dimension unresolved** and record an explicit
    conflict. Never the newest, never the highest tier, never the first, never an average.
22. **Synonym tables are out of scope.**
23. **Free-text normalisation beyond the existing case/whitespace folding is out of scope.**

### What is proved, and what is not

The check is **containment, not meaning**. `resolve()` proves the quoted excerpt really is
in the retrieved source. It does **not** prove the excerpt *means* the value: that "Amounts
are stated in US dollars" establishes `USD` is a reading, and no code pretends otherwise.

What the check buys is that the reading is auditable against text the source demonstrably
contains, instead of resting on a caller's word. That is a genuine and substantial narrowing
— it is not semantic source verification, and this ADR says so rather than implying a
guarantee the implementation does not deliver.

## Reason

**The hole was never strictness; it was indistinguishability.** Before this decision the
architecture could not tell `currency="USD"` read off a filing's header from `currency="USD"`
supplied because Microsoft is American. Both serialised identically, and both compared
identically. Adding provenance does not weaken the seven-dimension rule — it is what makes
the rule enforceable rather than merely followed.

**`EvidenceItem` is the right carrier because it already carries every control.** Local
tiering, operation binding, freshness, the untrusted marking and content-addressed identity
all apply to a context item for free. A new type would have to earn each of them again.

**Same-document is the only binding that can be checked mechanically.** Identical reference
is a string comparison. "Same reporting package" requires a document-identity model that does
not exist, and inferring one from URL shape is the M9-C.6 defect rebuilt. Cross-source
context can be relaxed later by a successor ADR once such a model exists; relaxing later is
cheap, and un-relaxing after reports have been issued is not.

**Derivation is admitted only on ADR-0025's terms because ADR-0025 already proved those
terms safe.** `canonical_amount()` reads stated notation and refuses when absent. That is the
whole test, and a rule that cannot pass it is an assumption, not a derivation.

**`compare()` stays unchanged because it must remain the audit surface.** It reports which
dimension failed and why; a module that resolved its inputs before testing them could not
also be the record of what did not resolve. Resolution therefore happens at
`SynthesisSet.add()` — beside `_require_internal_footing()`, which ADR-0023 put there for
exactly this shape of question — and `compare()` reads the result.

## Consequences

**Positive**
* A dimension's footing is now part of the record. "Where did `USD` come from" has an
  answer that came from data.
* The three assertions M10.2-R.5 found unblocked — unsupported currency, geography from
  multinationality, methodology from source type — are now refused structurally.
* `compatibility.py` is untouched, so the strictest module in the layer keeps its full
  regression surface.
* An `ALLOW` becomes reachable where a source genuinely states all seven dimensions,
  without any dimension being assumed.

**Negative**
* **The mechanism is additive, and the residual gap is real.** A dimension carrying no
  footing at all is passed through unchanged, exactly as before, so an unmigrated caller
  behaves as it always did. `SynthesisSet(require_dimension_provenance=True)` closes it for
  callers who opt in. Migrating the research skills to supply footings is follow-up work and
  is **not** done by this ADR — the same phasing ADR-0025 used, and the same honest cost.
* Free-text dimensions are still compared by exact equality, so `"global"` and `"worldwide"`
  — two truthful words for one idea — return `incompatible` rather than matching. A synonym
  table would fix that and is deliberately refused: it is a mechanism for silently equating
  things sources did not equate. Failing to *incompatible* fails safe.
* Requiring an excerpt means a caller must quote the source, which is more work than
  asserting a value. That is the point.

**Follow-up required**
* Migrate the four research skills to emit dimension footings, then consider making
  `require_dimension_provenance` the default.
* Improve retrieval so dimension-bearing text is captured — the scout brief does not
  currently ask for it. **Not part of this ADR**, and it needs its own decision because it
  touches the agent contract.
* A live verification of the `ALLOW` branch remains outstanding.

## Revisit when

A document-identity model exists that can establish "same reporting package" mechanically —
at which point point 15, and only point 15, is what is being reopened. Also revisit if a
derivation rule is proposed that passes the ADR-0025 test for a dimension other than `unit`
and `currency`.
