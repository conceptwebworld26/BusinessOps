# ADR-0029 — The local join is a surface of its own, and it sequences only

**Date:** 2026-09-16
**Status:** Accepted
**Milestone:** M10.2-R.14

## Context

ADR-0009 made the **local join** the default answer to a comparative question: the query
carries only public terms, the benchmark comes back, and *"the comparison is computed
locally by the engine"*. `architecture.md` §1 and §7 repeat it, and all four research skills
carry the failure-condition row *"that comparison fetches the public side and joins
**locally** — never send the internal figure."*

Nothing joined locally.

M10.1 built both halves of the representation. M10.2-R.10 through R.13 made the **external**
half user-reachable: four research commands now reach `synthesis.footed_statement()` through
their real paths. The internal half never moved. `from_analysis_set()` and
`from_kpi_result()` were implemented, tested, and — verified by inspection at R.13 — called
by **nothing outside the test suite**. `commands/runner.py`, `pipeline.py` and `render/`
contain no reference to synthesis at all. Every R.10–R.13 test built its internal comparison
twin by hand inside the test, which is exactly the pattern R.10's own record condemned as
proving the mechanism while proving nothing about the product.

So the capability the seven-dimension footing architecture exists to authorise — setting our
number beside theirs — had no user-reachable surface, and the headline promise of ADR-0009
was undeliverable.

## Problem

Where does the local join live, and what is it allowed to do?

## Options considered

### Option A — extend a research command to read the user's file
The comparison is initiated where the comparative question is asked, so `/company-analysis`
and friends look like natural homes. But each of the four carries *"reads no business file,
sends no internal data"* in its own description, and tests pin it. Adding file access would
break an approved, test-pinned contract on four surfaces at once, and would put confidential
data inside the commands specifically built never to touch it.

### Option B — extend an internal analytics command to retrieve a benchmark
The mirror image, and it fails the same way: `/sales-analysis` and friends say *"no external
research"* in their own descriptions, and `/business-health` says *"Internal data only, one
file, no external research."* Adding retrieval would break that contract and put the
disclosure gate inside commands that currently cannot reach it.

### Option C — a general-purpose orchestration command
One command that takes a natural-language comparative question and plans the analysis and the
research. Rejected: it is a planner, not a join, and it would own judgement that already has
four homes.

### Option D — one bounded command and skill whose whole job is the join
A surface that names an internal metric and a public benchmark subject, invokes the existing
analysis path for one and the existing research path for the other, and joins them.

## Decision

**Option D. `/benchmark-comparison` and `biq-benchmark-comparison` are the local-join
surface, and `commands.local_join()` is its engine seam. The seam sequences; it decides
nothing.**

```
commands.run(...)                      -> CommandResult (genuine AnalysisSet / KPIResult)
research.close_retrieval_object(...)   -> genuine EvidenceSet              (ADR-0024)
commands.local_join(...)               -> from_analysis_set / from_kpi_result
                                       -> synthesis.footed_statement()     (ADR-0028)
                                       -> one SynthesisSet(strict)
                                       -> synthesis.compare_values()
```

Five properties define it.

1. **Retrieve first, join second.** The seam receives a retrieval that has **already
   closed**. The external request was built, gated, dispatched and normalised before any
   internal figure was in scope, so the internal number cannot influence what was asked.

2. **The privacy guarantee is structural, not procedural.** The seam imports no gate, no
   query builder and no retrieval request. It *cannot* construct or alter an outbound query
   even if instructed to. A test asserts the absent imports, which is stronger than a rule
   someone has to remember.

3. **It reuses both existing translators and the existing footing seam.** No second internal
   translation mechanism, no second external footing mechanism, no new provenance, no new
   compatibility rule, no new protocol field.

4. **It is domain-agnostic.** No `company`, `market`, `competitor`, `industry`, metric or
   market-share branch lives in it; a test reads its source and fails on any of them. The
   upstream skill decides which analysis and which research question; the seam only orders
   them.

5. **Provenance stays independent.** Our figure remains an internal `CALCULATION`,
   evidence class 4, engine-footed on the registered dataset (ADR-0023) with no dimension
   provenance. Theirs remains `SOURCED`, class 3, untrusted, unverified, with its seven
   footings. Comparing two statements transfers nothing in either direction.

**It lives in the orchestration layer.** A local join needs a `CommandResult`, which the
command layer owns; `synthesis/` sits below the command layer and may not depend upward
(CLAUDE.md §2.3). Putting the seam in `commands/` keeps the dependency pointing down and
leaves the synthesis package with no knowledge that commands exist.

**One additive change to an M10.1 translator.** `from_kpi_result()` gains
`metric_definition`, `geography`, `scope` and `methodology`, mirroring `from_analysis_set()`
exactly. All four default to `None`, so every existing caller's output is byte-identical.
The asymmetry was an accident of sequencing — M10.1 predates the dimension architecture —
and it made a KPI unusable for the comparison this ADR exists to enable.

**Nothing is combined.** A `compatible` verdict says two figures measure the same quantity
and may be reported side by side. It is not an instruction to average, convert, difference
or rank them, and no combined figure is produced anywhere on this path. The surface
describes; it issues no recommendation and no verdict on whether the business is doing well.

## Reason

Options A and B each break a test-pinned contract on a surface built to have the opposite
property, and put confidential data or the disclosure boundary somewhere it was deliberately
excluded. That is the repository demonstrating that extension is architecturally
inappropriate, which is what justifies a new surface rather than a wider one.

Option D is bounded because the join is genuinely small: both halves already exist and are
tested, so the new code is ordering plus refusals. Making the privacy property structural
rather than procedural is what makes it safe to be small — there is no code path from the
seam to anything outbound, so the guarantee does not depend on the seam behaving well.

## Consequences

**Positive.** ADR-0009's default capability is deliverable for the first time. The internal
half of M10.1 gains its first production caller. M10.3's four consumers — SWOT, strategy,
decision support, executive reporting — become possible, because a representation that can
hold only external statements cannot express an internal strength or weakness.

**Negative.** A fifth research-shaped surface to maintain, and one more skill an author must
know. The seam takes a caller-supplied `SynthesisSet` so both halves can share one, which
means strictness is a refusal at call time rather than a property of the type. And the
internal dimensions are the caller's description of its own analysis: the engine can refuse a
comparison, but it cannot check that *"whole business, all segments"* truthfully describes
the file — the internal mirror of ADR-0026's containment-is-not-meaning boundary.

**Two limitations this decision does not close, recorded rather than fixed.**

- **A percentage metric cannot reach `compatible`.** `currency` is meaningless for a margin,
  so it is unstated on both sides, and `compatibility.compare()` treats unstated as
  `unknown`. Architecture.md's own headline example — *"our gross margin is 35% —
  typical?"* — therefore returns `unknown` on `currency`. Closing it means changing
  compatibility semantics, which is protected.
- **The disclosure gate refuses terms by key name.** A caller labelling an internal figure
  with a key not on the prohibited list is authorised, and the value reaches the query text.
  This is a pre-existing M9-A property that the local join neither introduces nor can fix —
  the seam builds no query. The controls today are the seam's structural inability to
  transmit and the skill's explicit prohibition. Strengthening the gate is its own milestone.

**Follow-up required.** Neither limitation above is scheduled here. M10.3's consumers now
read a representation that can hold both domains.

## Revisit when

- A comparative capability needs more than one internal figure against one benchmark, at
  which point the surface's "one metric, one benchmark" shape is the thing to reopen.
- The gate's key-name basis is strengthened, which would make the second limitation above
  a gate guarantee rather than a guidance one.
- Compatibility semantics gain a way to express "this dimension does not apply", which would
  make percentage comparisons reachable.
