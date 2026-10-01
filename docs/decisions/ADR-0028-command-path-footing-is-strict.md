# ADR-0028 — The research command's footing path is one seam, and it is strict by construction

**Date:** 2026-09-15
**Status:** Accepted
**Milestone:** M10.2-R.10

## Context

Three decisions built the dimension-admissibility mechanism and each is correct on its own
terms:

- **ADR-0024** made the completed retrieval hand back an `EvidenceSet` **object**
  (`close_retrieval_object`), because `register_external()` refuses a serialised set.
- **ADR-0026** made a dimension admissible only where a footing shows a source stated it,
  and made the mechanism **strictly additive**: a dimension with no footing is passed
  through unchanged unless the set was built with `require_dimension_provenance=True`.
  Opt-in was the right default, because it let unmigrated callers keep working unchanged.
- **ADR-0027** put the source's own context in the `content` field the record already had,
  and added `synthesis.source_footings()` as the one shared authoring helper.

M10.2-R.9 then migrated `skills/biq-company-analysis/SKILL.md` and proved the whole path on
deterministic fixtures. Its own limitations recorded what was still missing:

> **No command wires this up.** `/company-analysis` does not construct a strict
> `SynthesisSet` or author footings; the skill knows how, and nothing invokes it yet. The
> path is proved by test, not by a user-reachable flow.

Two facts made that more than a gap in convenience. The skill's Research flow told its model
to close a retrieval with `close_retrieval()`, which returns the set **serialised** — the
one shape `register_external()` refuses — so the documented flow could not reach synthesis
at all. And every step between a completed retrieval and a comparison existed only as an
example in markdown and as assembly inside R.9's test module: five calls in a fixed order,
with a default (`require_dimension_provenance`) that is `False`.

## Problem

Where does the sequencing between a completed retrieval and a footed, comparable statement
live, and what is its default strictness?

## Options considered

### Option A — Leave it as guidance; each research skill assembles the five calls
No new code. But the ordering is then re-derived by a model on every run, the opt-in flag is
the one step easiest to omit, and omitting it fails **open**: a caller who declares
`geography="Global"` and forgets `require_dimension_provenance=True` gets a `compatible`
verdict the evidence never supported. Four skills would become four assemblies, which is
what ADR-0012 exists to prevent and what ADR-0024 was written to stop happening to
retrieval.

### Option B — One sequencing seam in the engine, inheriting ADR-0026's additive default
One home, one ordering. But a seam whose strictness is a parameter has the same failure
mode as option A, one argument further in, and a default of `False` on a path that exists
*only* to produce comparable statements is a default nobody should want.

### Option C — One sequencing seam that is strict by construction
The same seam, with no way to build a loose set through it: a non-strict set is refused
rather than accepted. Costs the ability to reach this path from an unmigrated caller, which
is not a capability anyone asked for.

### Option D — Make `require_dimension_provenance=True` the global default
Simple to state, and it would silently change every existing caller's behaviour, which is
exactly what ADR-0026 chose additivity to avoid. Rejected: it reopens an accepted decision
in order to fix a path that decision did not cover.

## Decision

**`synthesis.footed_statement()` is the single seam from a completed retrieval to a
strictly footed external statement, and it is strict by construction.**

```
close_retrieval_object()  →  footed_statement()  →  compare_values()
                             register_external
                             source_footings
                             sourced_statement(dimension_provenance=…)
                             SynthesisSet(require_dimension_provenance=True)
```

Four refusals define it, and each closes a way the ordering could be skipped:

1. the evidence must be the object a **completed** retrieval produced —
   `type(...) is EvidenceSet`, a serialised `close_retrieval()` result refused by name;
2. the set must be strict — a set built without `require_dimension_provenance=True` is
   refused, and the seam's own default set always has it;
3. a dimension is **either footed or declared, never both** — whatever is footed is what the
   statement declares, so the two cannot disagree by typing;
4. a `context` footing **names its own evidence item** — no default, because a figure in one
   document and its context in another is the composition ADR-0026 prohibits.

**The seam decides nothing.** It performs no evidence lookup, no operation or document
binding, no containment test, no applicability test, no currency predicate and no conflict
handling. All of those stay in `dimension_provenance.resolve()`, reached from
`SynthesisSet.add()`, and a footing this seam authored is judged exactly as one written by
hand. `derived` is authorable through it for `unit` alone, from the notation the source
printed, naming the rule already in the closed registry; `asserted` has no parameter at all.

ADR-0026's additive default is **unchanged** for every other caller.

## Reason

The failure modes of options A and B are not hypothetical, they are the shape of the gap
M10.2-R.4 measured and ADR-0026 was written for: an unfooted dimension that reads as a
match. A flag defaulting to `False` on the one path whose entire purpose is comparability is
a fail-open default, and every other authorisation object in this codebase — the disclosure
decision, the retrieval request, the dimension footing — is constructible only in its safe
state. This path is now built the same way.

The cost of option C is the inability to produce a loose statement through this seam. That is
the intended behaviour, not a limitation: a caller who wants ADR-0026's additive
pass-through still has `sourced_statement()` unchanged.

## Consequences

**Positive.** `/company-analysis` reaches the strict path through shipped code rather than
through an example. There is one ordering, in one place, tested against the real retrieval
assembly from the scout's `BIQ-REC/1` reply text onward. The three remaining research skills
migrate by calling it, not by copying it. A dimension that no source stated stays `unknown`
on this path with no argument a caller can pass to change that.

**Negative.** A fifth public function in the synthesis layer, and one more name a skill
author must know. The seam accepts a caller-built `SynthesisSet` so an internal twin can
share it, which means the strictness check is a refusal at call time rather than a property
of the type. And it does not — cannot — check that a quoted excerpt *means* the value it is
offered for: ADR-0026's containment-not-meaning boundary is unchanged and unclosable.

**Follow-up required.** `biq-market-analysis`, `biq-competitor-analysis` and
`biq-industry-research` remain unmigrated and behave exactly as before. Migrating each is
calling this seam; none is done here.

## Revisit when

- A research skill needs a footed statement whose figure and context genuinely come from two
  documents. That is prohibited by ADR-0026, not by this seam, and reopening it means
  reopening that decision first.
- The additive default in ADR-0026 is retired in favour of strictness everywhere, at which
  point refusal (2) becomes redundant rather than wrong.
- A second path into `sourced_statement()` appears in production code. Two paths is the
  condition this ADR exists to prevent, and the right response is to fold it into this one.
