# ADR-0016 — Declared conflicts outrank numeric agreement

**Date:** 2026-09-11
**Status:** Accepted
**Deciders:** Project owner (M9-C.4 brief), implemented in M9-C.4

## Context

`EvidenceSet.record_conflict()` has existed since M9-A and works. Nothing on the
model-mediated research path could reach it: `close_retrieval()` took no conflict input and
returns the set as a dictionary, so the object owning the method never left the function.
`evidence["conflicts"]` was therefore always `[]` on the only path a skill uses.

The M9-B live retrieval measured the cost. The scout found a genuine definitional conflict —
CSIMarket's ~92% aggregate gross margin against freight-forwarder sell-minus-buy margins of
12–25% — described it accurately in prose, and the structured evidence set recorded
`conflicts: 0`. M9-C.3 shipped `biq-company-analysis` with that gap written into the skill as
a documented limitation, and noted that the three remaining research skills would inherit it.

The existing conflict model, verified by reading `sources.assess_conflict()`:

- it compares `SourcePosition` objects the caller supplies — it does **not** read retrieved
  text, so it never infers a conflict from prose;
- it decides `CONFLICTS` versus `AGREES` from a **numeric spread** against a 20% threshold;
- where positions are not numerically comparable it returns `AGREES`, with the statement
  *"Sources are not numerically comparable; no conflict detected between them."*
- it supports exactly three states — `AGREES`, `CONFLICTS`, `SINGLE`. There is **no**
  representation of a *resolved* conflict.

## Problem

How should an already-observed conflict reach the authoritative `EvidenceSet` — and what
happens when the model declares a conflict that the numeric test would call agreement?

## Options considered

### Option A — `conflicts=` transport, numeric assessment decides the status
Add the input; pass the positions to the existing `assess_conflict()` unchanged.
**Pros:** no change to conflict semantics; smallest diff.
**Cons:** fatal for the case that motivated the work. The M9-B conflict was *definitional*.
Two sources measuring incompatible things can report near-identical figures, and the numeric
test would file that as `AGREES` — recording agreement where the model observed disagreement.
The conflict disappears, which the research policy forbids.

### Option B — `conflicts=` transport, declaration sets the status
Add the input; a validated declaration records `CONFLICTS` whatever the spread, while the
numeric verdict is retained alongside as `numeric_assessment`.
**Pros:** definitional conflicts become representable; nothing is discarded; the arithmetic
remains visible to a reader. Python still never originates a conflict.
**Cons:** two things can now set one field, so the record must say which did — hence the
`declared` flag. Slightly more surface.

### Option C — infer conflicts during ingestion
Compare retrieved content automatically.
**Pros:** nothing to declare.
**Cons:** rejected outright by the brief and by the architecture. Python comparing arbitrary
text to decide meaning is exactly the inference the deterministic engine must not perform,
and it would make retrieved content the author of a structural fact.

## Decision

**Option B.** `close_retrieval(..., conflicts=[...])` accepts explicitly declared conflicts,
validated in `handoff._structured_conflicts()`. A declared conflict is recorded with status
`CONFLICTS` regardless of the numeric spread, carries `declared: true`, and keeps the numeric
verdict under `numeric_assessment`.

Three properties are fixed by this decision:

1. **Python never originates a conflict.** Only an explicit, validated declaration records
   one. Differing text, differing figures, and a page containing the word "conflict" all
   produce nothing.
2. **A declaration confers no authority.** `source`, `source_tier`, `source_date` and
   `freshness` are read from the evidence item the position names. A `source_tier` key on a
   position is **refused**, not honoured.
3. **No resolution mechanism is added.** The model supports unresolved conflicts only, and
   M9-C.4 keeps it that way. A conflict cannot be marked resolved, and preferring one source
   does not erase the record.

## Reason

The numeric test cannot see the thing that actually went wrong. Re-reading the M9-B result:
the scout's own note was *"sources disagree sharply because they define 'gross margin'
differently … this is a definitional conflict, not a factual one."* No threshold on figures
detects that. A design in which arithmetic can overrule an observation would have recorded
`AGREES` for the exact case the milestone exists to fix, so Option A fails on its own
motivating example — which is why the status follows the declaration.

Keeping `numeric_assessment` costs one key and preserves what Option A would have given:
a reader can still see that the figures alone would have read as agreement, which is often
the most informative thing about a definitional conflict.

The validation rules follow from the second property rather than from tidiness. A position
that could name its own tier would let a caller promote a content farm by asserting `"A"`,
which is the attack `sources.classify_tier()` exists to prevent; the accepted-field list is
therefore closed and a tier key is a refusal.

## Consequences

**Positive.** Conflicts reach the authoritative evidence set and the summary counts them.
The existing claim policy starts working as written — a declared conflict refuses a
single-source candidate claim in the same call, because conflicts are recorded first. The
three remaining research skills inherit a working transport rather than a documented gap.

**Negative.** `close_retrieval` grows a parameter and the conflict record grows two keys
(`declared`, `numeric_assessment`), so the shape differs between a declared conflict and a
computed one. A caller that declares a conflict carelessly can suppress its own claims —
correct behaviour, but surprising the first time. And the transport depends entirely on the
model choosing to declare: a conflict nobody notices is still invisible, exactly as before.

**Follow-up required.** None blocking. `biq-market-analysis`, `biq-competitor-analysis` and
`biq-industry-research` should use `conflicts=` from the start. M9-C.5's live verification is
the first end-to-end exercise of this path, and is where the M9-B scenario should be replayed
against the real thing.

## Revisit when

Two conditions would justify reopening this. First, if a legitimate need for a *resolved*
conflict state appears — the model has none, and inventing one was explicitly out of scope
here; that is a change to the evidence model and needs its own ADR. Second, if declared
conflicts prove to be reliably under-reported in live use, which would argue for surfacing
candidate conflicts to the model for confirmation — note that this is still not automatic
detection, and the line in the Decision above would have to be restated carefully.
