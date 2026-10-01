# 2026-09-09 — Milestone 7: Internal Analytics Commands

**Milestone:** 7 — Internal Analytics Commands
**Status on completion:** `REVIEW` — awaiting Milestone 7 review
**Supersedes:** None. Follows
[2026-09-08-internal-analytics.md](2026-09-08-internal-analytics.md).

## 1. Objective

Build the user-facing command layer over the Milestone 6 analytics skills: seven thin
orchestrators that accept a request, establish Business Context, run the existing pipeline
and analytics, pass through quality, KPI, materiality, evidence and privacy information,
render a useful result, explain limitations, and never fabricate an analysis the data does
not support.

## 2. Authoritative scope

**Verified before implementation.**

| Question | Answer |
|---|---|
| Does the repository enumerate the M7 commands? | **Yes.** `project_plan.md` line 249-252 names all seven, matching the brief exactly |
| Does `architecture.md` enumerate them? | **No.** It states "17 commands" as a count (lines 38, 592) and names none |
| Conflict? | **No conflict — a gap**, and the same one M4 and M5 found for the quality families and the KPIs |

Recorded as **D-06**. The pattern is now consistent across three milestones: the repository
records *counts* of taxonomies and enumerates *components*. M6 confirmed the component side
is fine; M7 confirms the taxonomy side is not.

**A second, smaller finding: `CLAUDE.md` line 87 is stale.** It says commands take "the
plain user-facing name from `architecture.md` section 4"; section 4 is the *skill*
architecture and contains no command names. Recorded as **D-07**, not fixed — `CLAUDE.md`
is governance and amending it is an owner decision.

## 3. Was an ADR required?

**No, and this was checked rather than assumed.** `architecture.md` section 18 lists
"an analysis domain → new Layer-2 skill + **optional command** — ADR? No" and "an output
format → new renderer in the engine — ADR? No". `docs/decisions/README.md` says explicitly
not to write an ADR for "anything the architecture already anticipates as a
registration-only extension point". The command registry and its renderer are exactly
that, so no ADR was written and `architecture.md` was not modified.

## 4. Architecture

```
commands/<name>.md            the orchestrator a user invokes — thin, prose, no arithmetic
lib/python/biq/commands/
    registry.py               which command runs what, declared as data
    runner.py                 sequencing: pipeline → declared domains → routing
    query.py                  /ask-business-data — maps a question onto existing work
    sections.py               one view of the structured result, formatted at presentation
```

The split matters. The markdown file is the orchestrator a person reads and the model
follows; the Python is the deterministic part of that sequencing plus rendering. Neither
holds a formula, a threshold, a classification or a policy — a test asserts no command
markdown restates a KPI formula, and another asserts every KPI-derived finding carries the
engine's own formula string verbatim.

**Command execution is four steps and no arithmetic:** resolve the declaration, run the
pipeline, run the declared domains, and (for `/ask-business-data`) route the question and
read the answer out of those results.

An unreadable source is returned as a structured `CommandResult` rather than raised. A
command is a user-facing boundary and a traceback is not an answer; the error type is
recorded so the failure stays explicit.

## 5. Command-to-skill mapping

| Command | Domains run | Primary implementation |
|---|---|---|
| `/business-health` | sales, customer, product, financial | cross-domain orchestration |
| `/sales-analysis` | sales | `biq-sales-intelligence` |
| `/customer-analysis` | customer | `biq-customer-intelligence` |
| `/product-analysis` | product | `biq-product-intelligence` |
| `/profitability-analysis` | financial | `biq-financial-analysis` |
| `/cash-flow-analysis` | financial | `biq-financial-analysis` |
| `/ask-business-data` | resolved by the question | routing over internal analytics |

Two commands share the financial domain deliberately: profit and cash are two questions
about the same computation, and splitting the engine to match the two questions would give
the same number two homes. They differ only in `kpi_focus` — a presentation choice.

`/ask-business-data` runs **no** domain when a question routes to a metric: the KPI engine
has already produced it, so nothing runs that the answer does not use.

## 6. Coverage — the honest headline

Each command declares the metrics it foregrounds, and reports how many of them the data
supported: `complete`, `partial`, `unavailable` or `not_applicable`. This was added after
seeing `/cash-flow-analysis` return "ok" with seven profitability findings and zero cash
metrics — technically true and thoroughly misleading. It now leads with:

> **Cash Flow Analysis is unavailable from this dataset.** None of the 5 metrics this
> command reports could be produced: burn_rate, runway, working_capital,
> days_sales_outstanding, days_payable_outstanding. What follows is context from the same
> data, not a substitute for them.

## 7. Output contract

The Milestone 6 `AnalysisSet` / `AnalysisFinding` contract is reused unchanged; no competing
result model was introduced. `CommandResult` is a wrapper holding the declaration, the
pipeline result, the analyses and the outcome, with pass-through accessors — it stores no
analytical state of its own.

Sections: Status · Reporting basis · Key findings · KPIs · Analysis · Limitations · Data
quality · Evidence and provenance. `/ask-business-data` inserts an Answer section after
Status. Quality warnings appear before the numbers; `unavailable` and `not_applicable` are
never rendered as the same blank cell.

**`/business-health` embeds the Milestone 2 executive report whole** and adds the
cross-domain view after it, rather than re-laying-out its content. That report is the
behaviour the vertical slice proves; reproducing its sections here would be a second
implementation of the same output.

## 8. Quality, materiality, evidence, privacy

**Quality** — `CRITICAL` halts every command with no finding produced and no KPI shown;
`WARNING` proceeds with the caveat attached to every finding and confidence downgraded;
`PASS` is normal. Commands never re-run M4's checks — asserted by comparing the quality
finding count before and after.

**Materiality** — no command-specific threshold exists. Verdicts come from the M2/M6 system
and travel with the findings. Where nothing is material, the renderer says so explicitly
rather than leaving a reader to infer that no analysis ran.

**Evidence** — source, rows, processing mode, reader tier, quality grade, formula or
primitive basis, fields used, period, comparison period, caveats and confidence all survive
into the rendered output. The command layer adds **no** untraceable claim: asserted by
comparing the ledger before and after.

**Privacy** — the M3/M6 behaviour is preserved unchanged. `/customer-analysis` accepts a
`--shareable` mode that pseudonymises identifying labels; local mode carries the export
caveat. No rendered command output contains an individual transaction — asserted across all
six analytical commands. The sensitivity classification is byte-identical before and after
a command runs.

## 9. `/ask-business-data` routing

The concept vocabulary is **derived from metadata the repository already holds**: KPI
keywords come from each metric's own name and identifier (including bracketed
abbreviations, so "DSO" and "NRR" are askable), dimension keywords from the semantic roles.
Only the intent words — largest, movement, mix, contribution, concentration, repeat,
cohorts — are declared in the router, because nothing else in the system needs to know how a
person phrases a question. A metric added to the KPI catalogue becomes askable without
touching the router.

Four outcomes, never interchangeable: `routed` · `clarification_needed` · `unsupported` ·
`unavailable`. Guessing is not one of them.

Forecasting, anomaly detection and external research are recognised **by name** and refused
with the milestone that owns them, before any file is read. A sub-period question ("last
quarter") is answered over the whole range **with that stated as a caveat** — silently
widening it would answer a different question from the one asked.

## 10. Bugs found and fixed

1. **`/cash-flow-analysis` looked like a successful run with no cash in it.** Status "ok",
   seven findings, none of them about cash. Fixed by adding `focus_coverage()` and leading
   the report with the coverage verdict.
2. **Raw `Decimal` leaked into answer prose** — "Gross margin is 34.91428908796912955…".
   The answer statement now formats through the same presentation helpers the analytics
   layer uses; the structured value keeps full precision.
3. **A sub-period question was silently widened.** "What was revenue last quarter?" returned
   the full-period total with nothing said. Now flagged and caveated.
4. **The same finding was printed three times** in `/business-health`. Revenue concentration
   is computed by the sales, customer and financial analyses because each needs it; each
   recording it is correct, printing it three times is not. De-duplicated at render time
   only — the structured results are unchanged.
5. **A vacuous test assertion** I wrote (`assertIn(x, y + x)`, always true) was replaced
   with a real one on the finding's unit.

## 11. Test coverage

**820 tests, 0 failures, 0 errors** (17 skipped — every one an openpyxl Tier-1/Tier-2 case;
openpyxl is not installed on this machine and was not installed for this milestone).

| Stage | Cumulative | Added |
|---|---|---|
| M1 | 120 | 120 |
| M2 | 271 | 151 |
| M3 | 403 | 132 |
| M4 | 480 | 77 |
| M5 | 559 | 79 |
| M6 | 701 | 142 |
| **M7** | **820** | **119** |

32 registry and routing unit tests (pure — no dataset), 56 command integration tests, 29
negative tests, 2 performance tests. No existing assertion was weakened.

## 12. Demo dataset results

`northwind_sales.csv`, 2,204 rows, 24 months, retail context, quality `PASS`, processing
mode `full`, currency GBP.

| Command | Status | Findings | Limitations | Material | Coverage |
|---|---|---|---|---|---|
| `/business-health` | ok | 94 | 13 | 41 | complete 5/5 |
| `/sales-analysis` | ok | 43 | 0 | 18 | complete 5/5 |
| `/customer-analysis` | ok | 24 | 2 | 11 | partial 3/5 |
| `/product-analysis` | ok | 20 | 1 | 9 | partial 1/2 |
| `/profitability-analysis` | ok | 7 | 10 | 3 | partial 3/8 |
| `/cash-flow-analysis` | ok | 7 | 10 | 3 | **unavailable 0/5** |
| `/ask-business-data` | ok | 0 | 0 | 0 | n/a — one answer |

Absent metrics are named with the field each needs: CAC (marketing_spend), NRR (retail
business model), inventory turnover (inventory_value), operating profit / margin / EBITDA /
EBITDA margin (operating_expense, depreciation), ROI (investment), burn rate
(operating_expense), runway (cash_balance), working capital (current_assets,
current_liabilities), DSO (receivables), DPO (payables). Nothing was estimated.

## 13. Performance

| Operation | Dataset | Time |
|---|---|---|
| `/business-health` end to end incl. rendering | 2,204 rows | 0.63s |
| Each single-domain command | 2,204 rows | 0.57–0.59s |
| `/ask-business-data` | 2,204 rows | 0.59s |
| `/business-health` | 30,000 rows | 1.92s |
| `/sales-analysis` | 30,000 rows | 1.85s |

Measurement, not benchmarking. Most of a command's cost is ingestion and the canonical
build, not the analytics or the rendering. No optimisation attempted.

## 14. Token / component measurement

Same methodology as M6: frontmatter block characters ÷ 4.

| Component | ~tokens |
|---|---|
| 4 skills | 665 |
| `/ask-business-data` | 133 |
| `/customer-analysis` | 131 |
| `/cash-flow-analysis` | 126 |
| `/product-analysis` | 126 |
| `/profitability-analysis` | 124 |
| `/sales-analysis` | 122 |
| `/business-health` | 117 |
| 7 commands | 879 |
| **Total always-on** | **~1,544** |

Twelve components, ~1,544 tokens, against the self-imposed ≤3,000 target. Extrapolated to
the full 37-component architecture at ~129 tokens each: **~4,800**, above the target but
below the ~6,100 M6 projected — commands are cheaper per component than skills, which is
what a thin orchestrator should be. **No description was shortened to hit a number**; each
was written to be mutually exclusive, and each names what it does *not* cover.

## 15. Known limitations

1. **Whole-period only.** Monthly granularity, no sub-period filtering; a period-qualified
   question is caveated rather than answered narrowly.
2. **One file per run.** No multi-source joins, no incremental runs.
3. **The router matches vocabulary, not grammar.** "Which products contributed most to
   revenue?" routes to contribution-to-change; the largest-by-revenue reading is returned
   as a supporting finding rather than being chosen by parsing the sentence.
4. **`/business-health` renders two "Key findings" blocks** — the embedded M2 one and the
   cross-domain one. Deliberate (the M2 report is embedded whole) but visibly repetitive.
5. **`PipelineResult.as_dict()` is still not JSON-serialisable** (D-05, pre-existing).
   Every `CommandResult.as_dict()` *is*, and is tested to be.
6. **A cosmetic grammar defect in M6 output** — "2024-02 (1 customers)" in the cohort
   finding — was found while rendering commands. It is M6 code and was **not** fixed here,
   per the instruction not to modify unrelated functionality. Recorded as D-08.

## 16. Git commit reference

Branch `main`. **No commit made** — `CLAUDE.md` section 10 requires commits only on request.
Nothing pushed, no history rewritten.
