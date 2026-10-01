# ADR-0012 — Component placement: where each business rule lives

**Date:** 2026-09-08
**Status:** Accepted
**Refines:** ADR-0003 (commands orchestrate, skills hold logic) — the layering stands; this
adds the missing distinction between skills, reference documents and engine code
**Deciders:** Project owner (architecture review), Claude

## Context

Architecture review asked for the 25-skill design to be *verified* rather than reduced:
which of them genuinely need to be model-invoked, which are deterministic computation, which
are shared foundation material, which are orchestration — and where the boundary sits so
that no business rule is implemented twice across skills, commands, agents and the engine.

Reviewing the 25 against that question exposed a real conflation. Five of them — the
Layer-0 "foundation skills" — are never invoked by name and contain no workflow. They are
*policy*: the pipeline definition, the provenance classes, the materiality rules, the output
conventions, the never-guess protocol. Two others (`biq-connector-broker`,
`biq-report-composer`) are mostly mechanical resolution and assembly.

Official Anthropic skill guidance, read during this review, is explicit that at startup only
each skill's `name` and `description` are pre-loaded, and that everything else should be
pulled in on demand via progressive disclosure. Policy that must apply to *every* workflow is
in fact **more** reliably delivered by a command instructing "read this file" than by hoping
a skill auto-fires.

## Problem

What decides whether a piece of business logic is a SKILL.md, a reference document, engine
code, or command text?

## Decision

**A single placement test, applied to every rule:**

| Ask | If yes | Home |
|---|---|---|
| Is it deterministic computation with no judgement? | | **Python engine** — `lib/python/biq/` |
| Is it a definition, policy or table that other components consult but nobody invokes? | | **Reference document** — `reference/` |
| Does it require the model to exercise judgement, interpret, or decide when to stop — and would a user ever ask for it in natural language? | | **Skill** — `skills/<name>/SKILL.md` |
| Is it purely sequencing: which components run, in what order, with which gates? | | **Command** — `commands/<name>.md` |

**Agents hold no unique business logic at all.** They load the same skills and references as
the main thread; their only distinctive property is isolation, fan-out or independent
verification (ADR-0006). Any rule found only inside an agent is a bug.

### Result of applying the test

**Engine (`lib/python/biq/`)** — xlsx/CSV readers, type and date normalisation, quality check
implementations, KPI calculators, segmentation/cohort/concentration maths, forecast methods,
anomaly detectors, materiality threshold arithmetic, currency/number/date formatting,
document rendering. No prose, no judgement.

**Reference documents (`reference/`, 0 always-on tokens, loaded on instruction)** — 6:
`analysis-framework.md` (the 19-step pipeline), `evidence-ledger.md` (the seven provenance
classes and confidence rules), `materiality-policy.md`, `output-standards.md`,
`ambiguity-protocol.md`, `research-policy.md` (source tiering, staleness windows, conflict
handling). These were the five Layer-0 "skills" plus the policy tables extracted from
`biq-external-research`.

**Skills (`skills/`) — 20**, each requiring judgement and each plausibly asked for in words:

| Layer | Skills |
|---|---|
| Context (1) | `biq-business-context` *(new, ADR-0011)* |
| Data (3) | `biq-data-ingestion` (now including connector resolution), `biq-semantic-mapping`, `biq-data-quality` |
| Analytics (7) | `biq-kpi-engine`, `biq-sales-intelligence`, `biq-customer-intelligence`, `biq-product-intelligence`, `biq-financial-analysis`, `biq-forecasting`, `biq-anomaly-detection` |
| Intelligence (5) | `biq-external-research`, `biq-company-analysis`, `biq-market-analysis`, `biq-competitor-analysis`, `biq-industry-research` |
| Synthesis (4) | `biq-swot`, `biq-strategy-recommendations`, `biq-decision-support`, `biq-executive-report` |

**Merged, with reasons** — `biq-connector-broker` into `biq-data-ingestion`: source
resolution is only ever used when loading business data, and splitting it created a skill
nobody invokes with a hand-off nobody needs; its capability map becomes a reference table.
`biq-report-composer` into `biq-executive-report` (judgement) plus engine rendering
(mechanics): "assembly primitives" was not a judgement boundary.

**Commands (`commands/`) — 17, unchanged.** Each names its objective, inputs, component
sequence and gates. No formulas, no definitions, no policy text.

### The non-duplication rule

Every business rule has **exactly one home**. Concretely:

- A formula appears in the engine and nowhere else. Skills describe *when and why* it
  applies; they never restate it.
- A policy appears in one reference document. Skills and commands link to it; they never
  paraphrase it.
- A workflow appears in one skill. Commands sequence skills; they never inline a skill's
  steps.
- Agents duplicate nothing.

Review rejects any change that restates a rule already homed elsewhere.

## Reason

The test replaces "how many skills should there be?" — which has no principled answer — with
"what kind of thing is this?", which does. Applying it moved seven components without losing
a single business rule: the logic is all still present, just homed where its nature says it
belongs.

Moving the five foundation components to reference documents is the substantive improvement.
They were never discoverable by natural language, so as skills they paid an always-on cost
for a trigger that would never fire, and relied on auto-invocation to deliver policy that
must apply universally. As reference documents they cost nothing at startup and are loaded
by explicit instruction — more reliable and cheaper at once.

## Consequences

**Positive** — no business rule has two homes; policy delivery is explicit rather than
hopeful; always-on cost falls (measured: 42 components = ~2,617 tok; the revised 37-component
shape projects lower); each remaining skill has a genuine natural-language trigger, which
improves description discriminability (ADR-0013 concern).

**Negative** — commands and skills must *remember* to read the relevant reference document;
if one forgets, policy silently does not apply. Mitigation: the reference read is an explicit
numbered step in every command, and eval cases assert provenance and materiality behaviour
end to end rather than trusting the instruction.

**Follow-up required** — Milestone 1 creates `reference/` with the six documents and wires
the read step into the command template.

## Revisit when

A reference document grows a workflow with decision points (it should become a skill), or a
skill turns out never to be invoked in natural language and to contain no judgement (it
should become a reference).
