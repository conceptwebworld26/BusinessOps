# ADR-0007 — Two-layer testing strategy

**Date:** 2026-09-08
**Status:** Accepted
**Deciders:** Project owner, Claude (architecture gate)

## Context

BusinessIQ has two distinct failure modes, and they need different tests:

1. **Wrong numbers** — a margin calculated incorrectly, a date parsed as a serial integer,
   a duplicate counted twice.
2. **Wrong behaviour** — guessing at an ambiguous column, forecasting from four data points,
   labelling an anomaly as fraud, emitting an uncited external claim, writing without asking.

The specification's testing section lists 24 scenarios spanning both kinds.

Verified: `claude plugin eval` exists, supports `case.yaml` cases, LLM graders, `--ablation`
with a no-plugin baseline, and `--mocks` MCP stand-ins from `evals/mocks/` — which is
precisely how "MCP unavailable" would be tested. **However, it is early-access gated and
not enabled on this account**: both `claude plugin eval` and `claude plugin eval init`
exit with "plugin eval is currently in early access".

## Problem

What carries the correctness burden, given that the platform's behavioural test harness
cannot currently be executed here?

## Options considered

### Option A — Evals only
- Pros: tests the thing users actually experience.
- Cons: cannot run here at all. Also slow, costs money per run, and non-deterministic — a
  poor fit for asserting that gross margin is exactly 42.7%.

### Option B — Fixture tests only
- Pros: fast, free, offline, deterministic, runnable by anyone.
- Cons: cannot test judgement. Nothing would verify that the model refuses to guess a column
  or declines a forecast — and those guardrails are half the product's value.

### Option C — Both, with fixture tests primary
`tests/` carries correctness: stdlib `unittest`, run by `python tests/run_tests.py`, with
unit, integration and negative suites over a fixture corpus (clean xlsx/csv, missing values,
duplicates, invalid dates, invalid numbers, missing revenue, missing costs, currency
mismatch, outliers, insufficient history, unsupported KPI, large dataset).
`evals/` carries behaviour: authored now, version-controlled, executed when access allows.

## Decision

**Option C**, with fixture tests as the primary and mandatory layer. Every failure mode in
`architecture.md` (Error Handling) and every command needs a negative test before its
milestone can be marked `COMPLETED`.

While `plugin eval` is unavailable, behavioural guarantees are covered by **scripted manual
scenarios** recorded with their real transcripts in `docs/testing/`. These are explicitly
labelled as manually executed, never as automated passes.

## Reason

Splitting by failure mode puts each assertion on the harness that can actually make it.
Deterministic arithmetic belongs in deterministic tests; judgement belongs in evals. This
also makes ADR-0002's determinism decision pay off twice — a stdlib engine with no network
is exactly what makes a free, offline, always-runnable suite possible.

Authoring eval cases now despite the gate is deliberate: the cases are the specification of
correct behaviour, and writing them shapes the skills. Not running them is a limitation to
declare, not a reason to skip the design work.

## Consequences

**Positive** — correctness is verifiable today, offline, by anyone; the `CLAUDE.md` rule
"never claim a test passed without running it" becomes enforceable; behavioural intent is
captured and ready the moment eval access arrives.

**Negative** — behavioural guardrails rely on manual verification until then, which is
slower and less repeatable. Manual results must be recorded honestly, including failures.

**Follow-up required** — `tests/run_tests.py` ships in Milestone 1 and must run green before
that milestone closes. `docs/testing/` gains a coverage matrix mapping each of the 24
specified scenarios to the test that covers it and the layer it runs on.

## Revisit when

`claude plugin eval` becomes available on this account — at which point the manual scenarios
in `docs/testing/` are migrated to `case.yaml` and the eval layer is promoted to CI.
