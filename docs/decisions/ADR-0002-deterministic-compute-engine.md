# ADR-0002 — Deterministic, stdlib-only compute engine

**Date:** 2026-09-08
**Status:** Accepted — amended in part by [ADR-0008](ADR-0008-tiered-xlsx-ingestion.md)
> **Amendment note (2026-09-08):** the core decision below — deterministic code, not model
> arithmetic, produces every reported figure — stands unchanged. The "stdlib only, no
> dependencies" clause was amended by ADR-0008 after probes showed a hand-written xlsx
> parser cannot reach production robustness alone. The stdlib reader survives as the
> offline tier. Original text preserved below.
**Deciders:** Project owner, Claude (architecture gate)

## Context

BusinessIQ produces numbers that CFOs and boards will act on: margins, runway, forecasts,
variance. A wrong number delivered confidently is the single most damaging failure this
product can have — worse than no answer, because it is actionable.

Verified runtime facts on this machine:

- Python 3.13.1 present; **stdlib only** — pandas, numpy, openpyxl, scipy, pyarrow,
  dateutil and duckdb are all absent.
- Node 24.19.0 and npm 11.17.0 present; bun and uv absent.
- A probe proved a **zero-dependency Python stdlib xlsx reader is viable**: using only
  `zipfile` and `xml.etree.ElementTree` it discovered sheets, resolved shared strings,
  returned typed cells, and converted an Excel serial date (45000 → 2023-03-15) correctly
  including the 1900 leap-year bug.

## Problem

Where do reported figures come from — model arithmetic, or executed code? And if code,
what may it depend on?

## Options considered

### Option A — Model computes in context
Claude reads the data and does the arithmetic in its response.

- Pros: no engine to build; trivially portable.
- Cons: arithmetic on hundreds of rows is not reliable; results are not reproducible; there
  is nothing to unit-test; large datasets do not fit in context at all. Disqualifying for a
  financial product.

### Option B — Engine requiring pandas/numpy/openpyxl
The conventional data-analysis stack.

- Pros: powerful, familiar, fast to write.
- Cons: none of it is installed here, so BusinessIQ would fail on first run on this very
  machine. A plugin that requires `pip install` before it works is a plugin most users
  abandon at the first error.

### Option C — Stdlib-only engine, optional accelerators
Pure Python 3.9+ standard library, with pandas/duckdb used only if detected and only where
results are provably identical.

- Pros: works on any machine with Python and nothing else — proven by probe; deterministic;
  unit-testable; reproducible; scales by streaming and aggregating rather than by loading.
- Cons: more code to write (xlsx parsing, statistics, date handling); slower than a compiled
  numeric stack on very large inputs.

## Decision

**Option C.** All reported figures are produced by `lib/python/biq/`, written against the
Python 3.9+ standard library only, with no network access. Optional accelerators may be used
where detected, but every path has a stdlib fallback producing identical results. Money uses
`decimal.Decimal`; rounding happens once, at presentation.

**Model arithmetic is never the source of a reported figure.** The model interprets,
contextualises and explains; it does not compute.

## Reason

The probe removed the main objection to Option C by proving the hardest part — Excel
ingestion without openpyxl — is achievable in roughly forty lines of stdlib code. That makes
zero-install portability free rather than expensive. Options A and B each fail on this very
machine: A on reliability, B on missing dependencies.

The additional benefit is testability: a deterministic engine can be covered by fixture
tests that run offline and free, which is what makes the "never claim a test passed" rule in
`CLAUDE.md` enforceable rather than aspirational.

## Consequences

**Positive** — reproducible numbers; a real test suite; no install friction; large datasets
handled by streaming and aggregation instead of context.

**Negative** — meaningful implementation cost in Milestones 2–4; xlsx edge cases must be
handled by hand (`styles.xml` number formats to distinguish date cells, inline strings, the
1904 date system, formula cells, streaming for large workbooks) — all known and scheduled,
none unknown.

**Follow-up required** — Milestone 2 must ship a **runtime probe**: detect Python, else
Node, else fall back to a strictly row-capped in-context path with mandatory disclosure that
figures were not engine-computed. Python's presence cannot be assumed on every user's
machine (risk R-03).

## Revisit when

The plugin platform gains a guaranteed managed runtime, or a bundled dependency mechanism
makes pandas available without a user-visible install step.
