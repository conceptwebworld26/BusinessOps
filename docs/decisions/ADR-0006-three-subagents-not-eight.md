# ADR-0006 — Three subagents, not eight

**Date:** 2026-09-08
**Status:** Accepted — unchanged by the 2026-09-08 architecture review
**Deciders:** Project owner, Claude (architecture gate)

## Context

The specification proposes eight subagents — Data Analyst, Finance Analyst, Sales Analyst,
Forecasting, Market Research, Competitive Intelligence, Strategy Analyst, Executive Analyst
— and explicitly asks: "Do not create unnecessary subagents. Recommend which should actually
exist."

Measured cost on this machine: each agent adds roughly 80 tokens to **every** session
always-on, plus 570–850 tokens each time it fires (`feature-dev` reference data). More
importantly, a subagent starts cold: it does not inherit the conversation, so anything the
user said must be re-derived or re-passed.

## Problem

Which of the eight are genuine subagents, and which are skills wearing a job title?

## Options considered

### Option A — Build all eight as specified
- Pros: matches the prompt literally; reads as a convincing org chart.
- Cons: ~640 tokens always-on for role personas; each agent must load the same skill a
  main-thread call would have loaded anyway, so the work is duplicated with a round trip
  added; agents lose the conversational context that strategy and executive work depends on
  most. An "org chart" is a poor architecture: the human division of labour in a finance
  team reflects human working memory limits, not an agent runtime's constraints.

### Option B — No subagents
- Pros: simplest; nothing always-on.
- Cons: gives up the three things subagents genuinely provide. Profiling a 200k-row
  multi-sheet workbook in the main thread burns the context the analysis needs. Researching
  five competitors serially is slow and floods context with raw pages. And nothing
  independently checks a headline number before it enters a board pack.

### Option C — Three agents, each justified by a mechanism
Apply a three-justification test: an agent exists only for **context isolation**,
**parallel fan-out**, or **independent verification**. Everything else is a skill.

- `biq-data-profiler` — isolation. Raw scan output is enormous and worthless once
  summarised.
- `biq-research-scout` — fan-out + isolation. One instance per entity; raw pages never reach
  the main thread.
- `biq-analysis-verifier` — independent verification. The one case where *not* sharing
  context is the entire point.

## Decision

**Option C.** Three subagents. The other five proposals become skills:
Finance Analyst → `biq-financial-analysis`; Sales Analyst → `biq-sales-intelligence`;
Forecasting → `biq-forecasting`; Market Research and Competitive Intelligence → parameterised
instances of `biq-research-scout`; Strategy Analyst → `biq-strategy-recommendations`;
Executive Analyst → `biq-executive-report` + `biq-report-composer`.

Every future subagent proposal must pass the three-justification test and get an ADR.

## Reason

The test cleanly separates the two cases. Profiling and research move *bulk material* that
must not enter the main context — the defining property of a subagent. Financial and sales
analysis move *reasoning* that must stay close to the user's stated question — the defining
property of a skill.

Verification is the interesting one, and it is worth the cost precisely because context
isolation is normally a drawback: an agent that cannot see how the first answer was derived
is the only thing that can genuinely catch a confident wrong number. That is the failure
mode this product must not have.

A useful side effect: the tool split makes the internal/external boundary structural rather
than advisory. `biq-research-scout` is granted web tools and **no file access**;
`biq-data-profiler` is granted file access and **no web tools**. Internal business data
therefore cannot reach a research query by accident — the agent that runs the query has no
way to read it.

## Consequences

**Positive** — always-on cost drops from ~640 to ~240 tokens; no duplicated logic between
agents and skills; the internal/external boundary is enforced by capability, not by
instruction; verification exists where it actually matters.

**Negative** — the delivered agent list is smaller than the specification proposed, and must
be explained. Sales, finance and strategy work runs in the main thread and so consumes main
context — acceptable, because that work is reasoning-dense and data-light by the time it
runs (the engine has already aggregated).

**Follow-up required** — Milestone 10 includes a test asserting `biq-research-scout` has no
file-access tools.

## Revisit when

A workflow appears with genuinely parallel, context-heavy sub-tasks that none of the three
covers — multi-entity consolidation across many separate ledgers is the likely candidate.
