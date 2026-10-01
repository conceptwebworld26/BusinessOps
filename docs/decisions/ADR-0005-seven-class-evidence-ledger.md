# ADR-0005 — Seven-class evidence ledger

**Date:** 2026-09-08
**Status:** Accepted
**Deciders:** Project owner, Claude (architecture gate)

## Context

BusinessIQ mixes material of very different epistemic weight in a single output: a figure
read from the user's ledger, a market size from a research house, a margin the engine
computed, an inference Claude drew, an assumption inside a forecast, and a recommended
action. Presented in one voice, a reader cannot tell which is which — and will act on all of
them equally.

The specification requires distinguishing seven categories, requires source attribution and
date-awareness for external material, prohibits fabricated citations, and requires that
major conclusions be traceable to evidence.

## Problem

How is provenance represented so that it survives from retrieval through analysis to the
final report, rather than being a stylistic instruction that erodes under summarisation?

## Options considered

### Option A — Prose convention
Instruct skills to "clearly distinguish facts from interpretation" in their wording.

- Pros: no machinery.
- Cons: provenance lives only in phrasing, so it is lost at every summarisation step —
  precisely where the executive report is assembled. Unenforceable and untestable.

### Option B — Binary fact/interpretation split
Two classes.

- Pros: simple.
- Cons: collapses distinctions that matter operationally. "Revenue was £2.1m" (from the
  ledger) and "the market is worth £4bn" (from a 2023 vendor report) are both "facts" but
  warrant completely different trust. A calculated margin and an assumed growth rate are
  both "not raw data" but are not remotely equivalent.

### Option C — Seven-class ledger as structured data
Every claim is a record carrying its class, its source, its date where applicable, and its
confidence. Classes 1–4 are evidential (user data, connected-system data, external sourced,
calculated); 5–7 are generative (interpretation, estimate/assumption, recommendation).
Schema: `lib/schemas/claim_ledger.schema.json`.

- Pros: provenance is data, so it survives aggregation, can be rendered consistently, and
  can be **tested** — an eval can assert that no class-3 claim lacks a source. Citations
  captured at retrieval time cannot be fabricated later, because a citation that was never
  captured does not exist in the ledger. The 1–4 / 5–7 split maps directly onto the
  presentation rule: evidential and generative material must be visually distinct.
- Cons: every skill must emit ledger entries; more discipline required.

## Decision

**Option C.** The seven classes are: (1) user-provided data, (2) connected-system data,
(3) external sourced, (4) calculated metric, (5) analytical interpretation,
(6) estimate/assumption, (7) recommendation. Every assertion carries exactly one.
Classes 5–7 are rendered visually distinct from 1–4. Every major conclusion traces to at
least one class 1–4 entry. Confidence (`HIGH`/`MEDIUM`/`LOW`) is stated explicitly, never
implied by tone.

The ledger is **closed at seven classes**. Adding one requires an ADR.

## Reason

Provenance has to be structural to survive. The report that matters most — the executive
report — is the most summarised artifact in the system, and summarisation is exactly where a
prose convention fails. Making provenance data means the guarantee holds at the end of a
five-step pipeline, not just in the skill that first produced the claim.

Closing the class list at seven is deliberate: an open list would drift into a taxonomy
nobody applies consistently, which is the same failure as Option A with more ceremony.

## Consequences

**Positive** — fabricated citations become structurally difficult rather than merely
prohibited; traceability is assertable in tests; readers can see at a glance what is
measured versus argued; confidence is explicit.

**Negative** — implementation discipline in every analysis skill; outputs are more verbose
than an unattributed narrative.

**Follow-up required** — `skills/biq-evidence-ledger` owns the definitions;
`claim_ledger.schema.json` and `evidence_set.schema.json` land in Milestone 8; eval cases
assert no uncited class-3 claim.

## Revisit when

A genuine eighth category appears repeatedly in practice and cannot be honestly expressed as
one of the seven.
