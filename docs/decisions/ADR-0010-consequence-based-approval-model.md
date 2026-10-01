# ADR-0010 — Consequence-based approval model

**Date:** 2026-09-08
**Status:** Accepted
**Supersedes:** the "human review" gate as described in `architecture.md` §8 step 19 and the
permission table in §9 as originally written
**Deciders:** Project owner (architecture review), Claude

## Context

The original data flow ended with "19 Human review and decision ── GATE" and described three
gates that "can stop a workflow", with human review "mandatory before any external action".
Architecture review flagged that this reads as though every analytical workflow needs
approval **before execution** — which would make BusinessIQ unusable. Running
`/sales-analysis` on a spreadsheet the user just handed over is a read-only computation with
no external consequence. Asking permission for it is friction that trains users to approve
without reading, which then degrades the approvals that genuinely matter.

## Problem

Where exactly does approval belong, and what is "human review" if it is not a gate?

## Options considered

### Option A — approve before every workflow
- Pros: nothing surprising ever happens.
- Cons: approval fatigue. A prompt before every analysis is noise, and noise is how a
  genuinely consequential prompt gets waved through. Actively harmful to safety.

### Option B — approve on write only
- Pros: simple rule.
- Cons: too coarse at the boundary. Drafting a report locally, saving it into the user's
  project, and emailing it to the board are all "writes" with radically different
  consequences.

### Option C — grade by consequence: does it leave the machine, and can it be undone?

## Decision

**Option C.** Approval is a function of **consequence**, not of activity. Two axes decide it:
does the effect leave the user's machine, and how reversible is it?

| Class | Examples | Approval |
|---|---|---|
| **Read-only analysis** | KPI, sales, customer, product, profitability, cash-flow, forecasting, anomaly detection, company/market/competitor/industry research, SWOT, strategy, decision support | **None.** Runs on request. |
| **External research at Tier 0/1** | Benchmark and public-entity queries built from public terms (ADR-0009) | **None** — nothing confidential is transmitted |
| **Draft generation** | Executive reports, scorecards, decision packages held in the conversation or the session scratchpad | **None.** Drafts are free. |
| **New local file** in a designated output directory | `./businessiq-output/report-2026-09-08.md` | **None**, but the path is always stated |
| **Overwrite any existing file** | Replacing a prior output, or any user file | **Explicit** — names the file |
| **Modify original source data** | Editing the user's spreadsheet or ledger | **Prohibited** — never, with or without approval |
| **External research at Tier 2** | A query carrying user-specified internal context | **Explicit**, showing the verbatim text to be sent |
| **Export off-machine** | Cloud drive, shared workspace, artifact, anything with a URL | **Explicit** — names destination and audience |
| **System writes** | CRM, accounting, commerce, database mutation | **Explicit** — names system, record, and change |
| **Communication / publication** | Message, email, chat post, publish | **Explicit** — names recipients, shows content |
| **Financial transactions** | Any payment or transfer | **Prohibited** by design; out of scope |
| **Repository** | `git commit` on request; `git push` | Commit on request; **push never without an explicit instruction** |

**Approval is per action and non-transferable.** Approving one export does not approve the
next. There is no session-wide "yes to everything" mode.

### What "human review" means

Step 19 of the analysis pipeline is renamed **"Human decision"** and is explicitly *not* a
gate on execution. It expresses the product's purpose: BusinessIQ produces decision-*ready*
analysis for a person to act on, and does not act on business decisions itself. The gate is
attached to the **consequential action**, if and when one is requested — not to the analysis
that informs it.

Accordingly the pipeline has **two** gates that can halt a workflow, not three:

- **Quality gate** (step 6) — `CRITICAL` data quality halts, because continuing would
  mislead.
- **Disclosure gate** (step 5) — a Tier 2 query halts pending approval; Tier 3 is refused.

Materiality (step 10) filters what is reported; it does not halt. The consequential-action
gate sits *after* the pipeline, triggered by a request to do something with the output.

## Reason

Grading by consequence rather than by activity puts friction exactly where it buys something.
Read-only analysis has no consequence to gate — the data is already the user's, on their
machine, and no effect escapes it. Meanwhile the things that genuinely warrant a pause
(off-machine transmission, record mutation, communication) become *more* salient once they
are the only prompts a user sees.

The reversibility axis is what separates cases Option B collapses: a new file in an output
directory is trivially undoable and needs only disclosure; an overwrite destroys something
and needs consent; an email cannot be recalled at all and needs consent plus a preview.

## Consequences

**Positive** — the product is usable for its primary purpose without friction; approval
prompts become rare and therefore actually read; the two remaining pipeline gates both have
a clear safety rationale.

**Negative** — the rule is a matrix rather than a one-liner, so it must be implemented
consistently across every command; "designated output directory" is new state requiring
configuration and documentation.

**Follow-up required** — `CLAUDE.md` §9 replaced with this matrix; every command's
frontmatter `allowed-tools` set to match its class; tests assert that read-only commands
never prompt and that each explicit-approval class does.

## Revisit when

A new action class appears that the two axes do not cleanly place.
