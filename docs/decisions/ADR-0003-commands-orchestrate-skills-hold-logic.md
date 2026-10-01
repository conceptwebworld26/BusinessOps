# ADR-0003 — Commands orchestrate, skills hold logic

**Date:** 2026-09-08
**Status:** Accepted — refined by [ADR-0012](ADR-0012-component-placement-rule.md)
> **Refinement note (2026-09-08):** the command/skill layering below stands. ADR-0012 adds
> the distinction this ADR lacked — between skills, reference documents and engine code —
> which moved the five Layer-0 "foundation skills" to `reference/`. Original text preserved.
**Deciders:** Project owner, Claude (architecture gate)

## Context

The specification names 17 slash commands and describes a large body of reusable analysis
logic, while also requiring "centralize reusable logic; avoid duplicated business logic".

Verified platform behaviour: a skill carrying `argument-hint` becomes user-invocable as a
slash command. The installed `marketing` plugin uses exactly this — it ships eight skills,
no `commands/` directory, and users invoke `/marketing:brand-review`. Meanwhile
`code-review` and `feature-dev` ship `commands/` with no skills. Both patterns are valid.

## Problem

Should each user-facing capability be a single skill (marketing pattern), or a thin command
that orchestrates shared skills?

## Options considered

### Option A — One skill per capability, no commands
17 self-contained skills, each user-invocable.

- Pros: one artifact per capability; fewest files; proven by the `marketing` plugin.
- Cons: `/business-health` and `/executive-report` both need KPI logic, quality gating,
  materiality and formatting. With no lower layer, that logic is copied into every skill
  that needs it. Seventeen copies of the margin definition is exactly the duplication the
  specification prohibits, and it guarantees drift.

### Option B — Thin commands over a layered skill library
17 commands declaring objective, inputs, skill sequence, gates and failure conditions; 25
skills holding all logic in five layers.

- Pros: every rule defined once; a fix to materiality or the evidence ledger propagates
  everywhere immediately; commands stay small and readable; skills remain independently
  model-invocable during free-form conversation, so `/sales-analysis` and "how did sales do
  last quarter?" reach the same logic.
- Cons: more files; two always-on token costs per capability (command ~55 tok + skills).

### Option C — Commands containing the logic, no skills
- Pros: fewest indirections.
- Cons: same duplication problem as A, plus the logic becomes unreachable outside an
  explicit slash command — natural-language requests would get ad-hoc analysis instead of
  the governed pipeline. Rejected.

## Decision

**Option B.** `commands/*.md` are thin orchestrators containing no formulas and no
definitions. `skills/biq-*/SKILL.md` hold all business logic in five layers (Foundation,
Data, Analytics, Intelligence, Synthesis) with a strict downward-only dependency rule.

## Reason

The deciding factor is that the foundation layer — materiality, evidence provenance, output
formatting, the never-guess protocol — is used by *every* capability. Options A and C make
those cross-cutting rules impossible to define once. Layer 0 exists precisely so that
"what counts as material" and "how is a claim attributed" have exactly one definition each,
and that is the property most likely to decay silently under duplication.

The token cost of Option B is bounded and measurable (~935 tok for commands, inside the 4k
ceiling in `architecture.md`) and buys the single-source guarantee.

## Consequences

**Positive** — one definition per rule; commands readable at a glance; skills reachable
both by command and by natural language; layered dependencies make the blast radius of a
change obvious.

**Negative** — 42 component files instead of 17; contributors must learn which layer a
change belongs in; always-on token cost is roughly doubled per capability.

**Follow-up required** — code review must reject any command that restates a definition
already owned by a skill. `CLAUDE.md` section 2 principle 2 encodes the rule.

## Revisit when

The always-on token budget is breached, or a layer proves to have only one consumer — in
which case merge it into that consumer rather than keeping a layer for symmetry.
