# 2026-09-08 — Milestone 6: Internal Analytics Skills

**Milestone:** 6 — Internal Analytics Skills
**Status on completion:** `REVIEW` — awaiting Milestone 6 review
**Supersedes:** None. Follows
[2026-09-08-kpi-engine.md](2026-09-08-kpi-engine.md).

## 1. Prompt / task performed

Milestone 5 approved. Build the analytics interpretation layer above the KPI engine: the
full `biq-sales-intelligence` skill plus `biq-customer-intelligence`,
`biq-product-intelligence` and `biq-financial-analysis`, supported by deterministic
primitives for segmentation, cohorts, concentration and mix. Consume KPI results rather
than recomputing them, consume the quality gate rather than duplicating it, keep the one
materiality system, and never fabricate a finding. No Milestone 7 work: no new commands, no
forecasting, no anomaly detection.

## 2. Authoritative scope — and, for once, no gap

The M6 scope is enumerated in the repository. `project_plan.md` line 244 names
`biq-sales-intelligence` (full), `biq-customer-intelligence`, `biq-product-intelligence`,
`biq-financial-analysis` and `lib/python/biq/analytics/`; `architecture.md` section 4 Layer
2A names the same four skills alongside the KPI engine (Milestone 5), forecasting and
anomaly detection (both Milestone 8). The brief and the repository agree exactly.

This is worth recording because M4 and M5 both found the opposite — a count in
`architecture.md` with no enumeration anywhere (D-01, D-02). The skills were enumerated;
the taxonomies were not. That is the shape of the documentation debt, and it narrows what
D-01 and D-02 actually need.

Architecture note honoured: `biq-customer-intelligence` is specified as "behaviour only,
never inferred intent". The module and the skill both enforce it.

## 3. Architecture

```
contract.py       AnalysisFinding + AnalysisSet + Limitation; the four classifications
presentation.py   how an entity may be labelled, given its M3 sensitivity class
segmentation.py   grouping, ranking, movement, per-segment margin, first appearance
concentration.py  top-N, concentration ratios, members-for-half, HHI
mix.py            shares, mix shift in points, contribution to a net change
cohorts.py        acquisition cohorts and the retention curve
domain.py         shared scaffolding: prepare, emit_kpi, emit_dimension, emit_concentration
sales.py          revenue and order trend, dimension performance, mix, concentration
customers.py      population, new vs returning, retention, concentration, cohorts
products.py       contribution, growth, mix, per-product margin, ramp
financial.py      the profit walk as far as the data goes, and everything it cannot reach
```

One-way layering. Primitives know nothing about domains; domains consume KPI results and
never recompute them; skills read the `AnalysisSet` and do no arithmetic.

`pipeline.analyse(result, domains=...)` is the entry point, deliberately **separate** from
`pipeline.run()`. The Milestone 2 health check is a smaller job and does not pay for four
domains of analysis it does not use; `/business-health` is unchanged and still returns
`result.analyses == {}`.

## 4. The four classifications

`FACT` (evidence class 1) · `CALCULATION` (class 4) · `INTERPRETATION` (class 5) ·
`RECOMMENDATION` (class 7). The deterministic engine may emit only the first two —
`AnalysisSet.add` raises on anything else, so the boundary is enforced rather than
documented. Interpretation is the skill's job; a recommendation additionally needs all six
ledger fields, and `AnalysisFinding.as_claim()` delegates that rule to `evidence.Claim`
rather than restating it.

## 5. KPI integration — consumed, never recomputed

`domain.emit_kpi` reads a `KPIResult` and turns it into a finding whose `basis` is the
engine's own formula string, or turns its absence into a limitation carrying the engine's
own reason. A test asserts `finding.basis == result.kpis[metric].formula` for every
KPI-derived finding.

The clearest case is revenue growth. `sales.trend()` (Milestone 2) computes a half-over-half
change, and reusing it would have duplicated the `revenue_growth` formula. `sales.analyse`
instead derives only the *shape* of the series — period count, strongest month, weakest
month — and reads magnitude and direction from the KPI result, with a basis that says so:
`"revenue_growth KPI result (not recomputed here)"`.

Two quantities genuinely extend a KPI rather than restating it, and both are implemented
once and documented as extensions: `segmentation.margin_by_dimension` (gross margin per
segment) and `segmentation.margin_by_period` (gross margin per period). The Milestone 2
`sales.margin_series` now delegates to the latter and only applies its documented rounding,
so there is one implementation, not two.

## 6. Quality integration

`CRITICAL` — every domain returns `unavailable` with the halt reason and produces **no
finding at all**. `WARNING` — analysis proceeds and every quality caveat is attached to
every finding, past and future, via `AnalysisSet.add_caveat`; confidence drops from HIGH to
MEDIUM. `PASS` — nothing added. M4's checks are consumed, never re-run: a test asserts the
finding count on the quality report is unchanged after the analytics layer runs.

An unconfirmed column mapping becomes a caveat on every finding, naming the column and the
role.

## 7. Materiality

There is one materiality system and it is M2's. `segmentation.judge_movements` calls
`materiality.assess_amount`; `financial._margin_movement` calls `assess_margin` so a margin
is judged in percentage points; `concentration.judge_share` calls
`assess_share_of_revenue`. Nothing in the analytics layer defines a threshold.
`undetermined` survives as a distinct outcome — a comparison that cannot be made is not the
same as a movement that is too small.

## 8. Privacy

`presentation.LabelPolicy` reads the Milestone 3 classification and decides only how a
*label* is rendered. Two modes: `LOCAL` (the default — the analysis stays on the machine,
so entity labels are shown, because "your third-largest customer" is useless to the owner
who wants to phone them) and `SHAREABLE` (labels drawn from `restricted` or `never` columns
become stable rank-based pseudonyms).

Two rules hold in both modes because they are not presentation choices: no individual
transaction row is ever emitted, and a group below the k-anonymity floor reports a banded
count rather than an exact one. On the demo dataset, `Customer` is classified `never` and
`Salesperson` `restricted`, so a local result carries an explicit caveat that it must be
pseudonymised before it is shared. A test asserts the classification summary is byte-identical
before and after the analytics layer runs — nothing here weakens it.

## 9. Demo dataset — the honest picture

Retail Business Context, `northwind_sales.csv`, 2,204 rows, 24 months.

| Domain | Status | Findings | Limitations |
|---|---|---|---|
| Sales | available | 43 | 0 |
| Customer | available | 24 | 2 |
| Product | available | 20 | 1 |
| Financial | available | 7 | 10 |

Financial analysis reports **more limitations than findings**, and that is the correct
answer: a sales extract has no operating expenses, no balance sheet and no cash position,
so operating profit, EBITDA, working capital, DSO, DPO, burn and runway are each
`unavailable` with the missing field named. Nothing was estimated.

## 10. Bugs found and fixed

1. **Sales and customer intelligence reported the same list twice.** The first draft ran
   the full dimension block over the customer column inside sales analysis, producing ten
   per-customer movements that customer intelligence then repeated. Sales now takes the
   concentration figure only; per-customer movement belongs to the customer domain.
2. **"3 categorys".** Naive pluralisation in the concentration statement. Fixed with an
   explicit `plural()` helper rather than by rewording around it.
3. **A skipped dimension was invisible to a limitations-only reader.** It was recorded in
   `dimensions_skipped` but nowhere else. It is now recorded in both places.
4. **A test fixture generated 2025-01-33.** Day spacing overflowed the month at six rows
   per month, which the quality gate correctly rejected as an invalid date — the fixture
   was wrong, not the gate.
5. **A stale performance printer.** `TestPerformanceBaseline.tearDownClass` still printed a
   partial baseline table left over from Milestone 3, which the Milestone 5 `atexit`
   printer had already superseded. It broke on the new measurement tuple; removed.

## 11. Files created

```
lib/python/biq/analytics/contract.py
lib/python/biq/analytics/presentation.py
lib/python/biq/analytics/segmentation.py
lib/python/biq/analytics/concentration.py
lib/python/biq/analytics/mix.py
lib/python/biq/analytics/cohorts.py
lib/python/biq/analytics/domain.py
lib/python/biq/analytics/customers.py
lib/python/biq/analytics/products.py
lib/python/biq/analytics/financial.py
skills/biq-customer-intelligence/SKILL.md
skills/biq-product-intelligence/SKILL.md
skills/biq-financial-analysis/SKILL.md
tests/fixtures/build_analytics_fixtures.py
tests/unit/test_analytics_primitives.py
tests/integration/test_analytics_m6.py
tests/negative/__init__.py
tests/negative/test_analytics_negative.py
docs/development/2026-09-08-internal-analytics.md   (this file)
```

## 12. Files modified

| File | Change |
|---|---|
| `analytics/__init__.py` | Export the domains, primitives and contract; `analyse_all` |
| `analytics/sales.py` | Full `analyse()`; `margin_series` delegates to the new primitive |
| `pipeline.py` | `analyse()` entry point; `PipelineResult.analyses` |
| `skills/biq-sales-intelligence/SKILL.md` | Expanded from the M2 proof of concept |
| `config/businessiq.defaults.json` | New `analytics` section (top_n, ratios, cohort minimum, presentation) |
| `tests/integration/test_performance.py` | Analytics baseline; explicit measurement units; stale printer removed |
| `project_plan.md`, `README.md`, docs indexes | Status |

**No ADR body modified. `architecture.md` deliberately not modified.**

## 13. Test results

**698 tests, 0 failures, 0 errors** (17 skipped on the system interpreter).

| Stage | Cumulative | Added |
|---|---|---|
| M1 | 120 | 120 |
| M2 | 271 | 151 |
| M3 | 403 | 132 |
| M4 | 480 | 77 |
| M5 | 559 | 79 |
| **M6** | **698** | **139** |

60 primitive unit tests, 57 domain integration tests, 22 negative tests. No existing
assertion was weakened. `tests/negative/` is created here for the first time, matching the
layout `architecture.md` section 15 has always specified.

## 14. Performance

| Operation | Dataset | Time |
|---|---|---|
| 4 domains, 95 findings | demo, 2,204 rows | 0.07s |
| 4 domains, 37 findings | 30,000 rows | 0.46s |
| segmentation by product | 30,000 rows | 0.02s |

Measurement, not benchmarking. The analytics layer costs roughly twice the KPI engine on
the same data and remains a small fraction of ingestion.

## 15. Limitations

1. **Monthly granularity only**, inherited from `period_key`.
2. **Half-over-half comparison** rather than configurable comparison windows, matching the
   KPI engine.
3. **A cohort is defined by first appearance in the dataset**, so the earliest cohort is
   overstated and its retention understated. Stated as an assumption on every cohort
   finding rather than hidden by dropping the first cohort.
4. **Concentration is reported, not judged.** HHI and CR-N are numbers; whether a level is
   dangerous is judgement and belongs to a skill.
5. **`PipelineResult.as_dict()` is still not JSON-serialisable**, because the Milestone 2
   `analysis` dictionary carries raw `Decimal` values. Every `AnalysisSet` produced by
   Milestone 6 *is* serialisable and is tested to be. Pre-existing; not refactored here.
6. **Contribution-to-change shares can exceed 100%** when members move in opposite
   directions. This is arithmetically correct for a signed apportionment and is documented
   in the module, but it reads oddly without explanation, so the skills are told to explain
   it.
7. **The always-on token estimate uses a different estimator** from the one M1–M5 reported
   (see section 16), so the trend is stated in both.

## 16. Token / component measurement

Method, stated explicitly because it differs slightly from earlier milestones: the YAML
frontmatter block of each skill and command, in characters, divided by four.

| Component | ~tokens |
|---|---|
| `biq-sales-intelligence` | 144 |
| `biq-customer-intelligence` | 171 |
| `biq-product-intelligence` | 162 |
| `biq-financial-analysis` | 188 |
| `/business-health` | 101 |
| **Total always-on** | **~766** |

Applying the same estimator to the Milestone 5 component set (1 skill + 1 command) gives
~245 against the ~271 reported at the time — about a 10% estimator difference, not a change
in the components. Either way the shape is the same: five components now, up from two, and
still well under the self-imposed 3,000-token target. Extrapolated to the full 37-component
architecture at ~165 tokens each, the projection is ~6,100 tokens, which strengthens rather
than weakens R-09. **No description was trimmed to chase the target** — the four are written
to be mutually exclusive, which is what actually determines routing (ADR-0013).

## 17. Git commit reference

Branch `main`. **No commit made** — `CLAUDE.md` section 10 requires commits only on request.
Nothing pushed, no history rewritten.
