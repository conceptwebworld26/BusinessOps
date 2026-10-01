# 2026-09-08 — Milestone 5: Full KPI Engine

**Milestone:** 5 — KPI Engine (full)
**Status on completion:** `REVIEW` — awaiting Milestone 5 review
**Supersedes:** None. Follows
[2026-09-08-data-quality.md](2026-09-08-data-quality.md).

## 1. Prompt / task performed

Milestone 4 approved. Expand the M2 seven-metric proof of concept into the complete KPI
engine: approximately 27 approved metrics, each with a declared input contract, applicability
by business model, and a result that explains itself. Deterministic Decimal arithmetic, no
duplicated formulas, integration with Business Context and the M4 quality gate, and an
honest demonstration on the demo dataset. No Milestone 6 work.

## 2. Authoritative taxonomy — and a documentation gap, again

**Verified against the repository**, and the finding mirrors M4's exactly:

| Question | Answer |
|---|---|
| Does `architecture.md` enumerate the KPIs? | **No.** Line 239 says "~27 KPIs" — the count only |
| Is the list anywhere in the repo? | **No.** No document enumerates EBITDA, burn rate, DSO, win rate or the rest |
| Where does it come from? | The **product specification's "KPI Analysis / Potential KPIs"**, delivered in this project's first prompt, which lists exactly twenty-seven metrics. Never committed |
| Corroborating evidence in the repo | `CLAUDE.md` line 232 uses *"feat(kpi-engine): add DSO and DPO calculators"* as its example commit message — DSO and DPO are items 24 and 25 of that list |
| Conflict between architecture and specification? | **No conflict — a gap.** They agree on the count; the repository simply does not record which twenty-seven |

**This is documentation debt, recorded not resolved.** Per the M5 instruction, `architecture.md`
was **not** edited. It is now the second instance of the same pattern (M4 found it for the
13 quality families), which suggests the underlying issue is that the product specification
was never committed to the repository at all.

**One further discrepancy found:** M2 implemented `net_revenue_retention`, which is **not**
among the approved 27 — it was added in M2 to demonstrate the `not_applicable` bucket.
Removing it would regress M2, so it is retained, declared separately in
`BEYOND_APPROVED`, and its definition records why. The catalogue is therefore **27 approved
+ 1 retained = 28**.

## 3. Result buckets — a second reconciled discrepancy

The M5 brief names four buckets: `available` · `unavailable` · `not_applicable` ·
`insufficient_data`. `architecture.md` section 6 names four different ones: `computed` ·
`partial` · `unavailable` · `not_applicable`.

They differ on two names, and `partial` is not `insufficient_data`: `partial` produced a
value from an incomplete pass, while `insufficient_data` produced nothing because the
history is too short. Both are real states, so **both are kept** — five in total — with
`COMPUTED` retained as an alias of `AVAILABLE` so earlier callers keep working. Reported
rather than silently resolved.

## 4. Architecture

```
contract.py     KPIDefinition (what a metric is) + KPIResult (what happened) + buckets
primitives.py   every arithmetic operation - totals, safe division, periods, currency
catalog.py      the 28 definitions and their calculators
engine.py       decision order, error containment, serialisation
registry.py     stable facade; M2 call signature preserved
```

**Decision order, and it matters:** quality gate → applicability → currency safety → input
contract → calculation. Applicability precedes availability because telling a consultancy
"we could not compute inventory turnover" is unhelpful when the honest answer is that it
does not apply to them.

Every formula lives in `catalog.py` or `primitives.py` and nowhere else — a test walks
`skills/` and `commands/` asserting no formula string appears there.

## 5. Input contracts

`_require()` returns **(absent, unconfirmed)** separately, because they are different
problems with different fixes: an absent field needs supplying, an unconfirmed one needs a
decision. M2 made this distinction; my first M5 draft collapsed it, and the M2 regression
tests caught the regression (§9).

Twelve new semantic roles were added for the catalogue: operating expense, depreciation,
inventory value, cash balance, receivables, payables, current assets, current liabilities,
marketing spend, lead count, deal stage, pipeline value, deal opened/closed, recurring
revenue and investment. A dataset without them is not deficient — the metrics that need
them report `unavailable` naming the field.

## 6. Currency

`resolve_currency` returns `(currency, error)`. An error — mixed currencies, or data
contradicting Business Context — refuses **monetary metrics only**; percentages and counts
still compute, because a retention rate is unaffected by a currency question. Nothing is
ever converted, and no rate service is ever consulted.

## 7. Quality integration

A `CRITICAL` quality report suppresses **every** metric with an explicit reason. A `WARNING`
lets metrics compute and attaches the quality caveats to each result, so they survive into
whatever consumes them. A clean report adds nothing. M4's checks are consumed, never
duplicated.

## 8. Demo dataset — the honest picture

All 28 metrics reported: **8 available · 16 unavailable · 4 not_applicable · 0
insufficient_data**. The M2 figures are unchanged (revenue £3,467,850.16, gross profit
£1,210,775.23, gross margin 34.9143%, AOV £1,573.43).

Sixteen metrics decline because the demo file is a sales extract with no opex, inventory,
cash, balance-sheet, pipeline or marketing columns. Four decline because a retail business
has no recurring revenue. **Not one metric was manufactured**, which is the point of the
milestone.

## 9. Bugs found and fixed

1. **Lost the absent-vs-unconfirmed distinction.** My `_require()` merged "field missing"
   and "field provisional" into one message, dropping behaviour M2 had and the M5 brief
   requires. Caught by the M2 regression tests; restored with the original wording.
2. **`runway` returned `available` with a null value** when the business is cash-generative,
   which would render as a blank cell in a scorecard and read as a defect. It now returns
   `unavailable` with a reason that says the quantity is unbounded, not missing.
3. **`analytics` imported a private helper** (`_period_key`) that moved into `primitives`.
   Repointed at the public function.
4. **Two compatibility aliases** were needed: `KPIResult.inputs` → `inputs_used` and
   `KPIDefinition.requires` → `inputs`.

**One deliberate behaviour change, documented:** M2 quantized percentages inside the engine
(4 dp). `CLAUDE.md` section 4 says rounding happens once, at presentation — so the engine
now carries full Decimal precision and the renderer rounds. The M2 assertions were updated
to compare at presentation precision, which is equally strict, not weaker.

## 10. Files created

```
lib/python/biq/kpi/contract.py
lib/python/biq/kpi/primitives.py
lib/python/biq/kpi/catalog.py
lib/python/biq/kpi/engine.py
lib/schemas/kpi_results.schema.json
tests/fixtures/build_kpi_fixtures.py
tests/integration/test_kpi_engine.py
docs/development/2026-09-08-kpi-engine.md   (this file)
```

## 11. Files modified

| File | Change |
|---|---|
| `kpi/registry.py` | Rewritten as the facade; M2 signature preserved |
| `kpi/__init__.py` | Export the catalogue, engine and serialisation |
| `mapping/semantic.py` + `__init__.py` | Twelve new business roles and their patterns |
| `analytics/sales.py` | Use the public `period_key` primitive |
| `pipeline.py` | Pass canonical + quality into the engine; record `partial` results |
| `tests/unit/test_engine_m2.py`, `tests/integration/test_vertical_slice.py` | Precision assertions at presentation precision |
| `tests/integration/test_performance.py` | KPI baseline; honest rate column |
| `project_plan.md`, `README.md`, docs indexes | Status |

**No ADR body modified. `architecture.md` deliberately not modified.**

## 12. Test results

**559 tests, 0 failures, 0 errors** (17 skipped on the system interpreter; 1 with openpyxl).

| Stage | Cumulative | Added |
|---|---|---|
| M1 | 120 | 120 |
| M2 | 271 | 151 |
| M3 | 403 | 132 |
| M4 | 480 | 77 |
| **M5** | **559** | **79** |

Every metric has a happy path, an unavailable path, and — where meaningful — a
not_applicable and an insufficient_data path. Cross-KPI consistency is asserted directly
(gross profit = revenue − COGS; gross margin = gross profit ÷ revenue; ARR = MRR × 12;
retention + churn = 100), including that dependent metrics share one revenue total rather
than each computing their own.

## 13. Performance

| Operation | Dataset | Time |
|---|---|---|
| 28 metrics | demo, 2,204 rows | 0.03s |
| 28 metrics | 480 rows, 24 periods | 0.01s |
| 28 metrics | 30,000 rows | 0.22s |

Measurement, not benchmarking. The rows/s column is deliberately omitted for KPI runs — the
result is a set of metrics, not rows, and a rate would be meaningless.

## 14. Limitations

1. **Monthly granularity only.** `period_key` buckets by calendar month; weekly or daily
   businesses will see coarser periods than they keep books in.
2. **Customer lifetime value is observed, not projected.** A projected CLV needs a retention
   curve and a discount rate — that is forecasting, deliberately out of scope.
3. **New-customer detection is bounded by the data window.** A customer trading before the
   file begins cannot be distinguished from a genuinely new one, which affects CAC.
4. **EBITDA assumes interest and tax are excluded from operating expenses.** Stated as an
   assumption on the result.
5. **DSO and DPO treat each period as 30 days.** Exact figures need real period boundaries.
6. **Win rate recognises a fixed vocabulary** of won/lost stage labels; unrecognised labels
   are treated as undecided rather than guessed.
7. **Half-over-half comparison** is used for period-over-period metrics rather than
   configurable comparison windows.

## 15. Git commit reference

Branch `main`. **No commit made** — `CLAUDE.md` section 10 requires commits only on request.
Nothing pushed, no history rewritten.
