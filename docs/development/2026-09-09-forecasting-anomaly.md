# 2026-09-09 — Milestone 8: Forecasting & Anomaly Detection

Status: `REVIEW` · Branch: `main` (uncommitted) · Preceded by
`2026-09-09-internal-analytics-commands.md`

---

## 1. Objective

Add the two analytical capabilities that reason about what history implies — a forecast of
periods that have not happened, and a scan for periods that do not look like the ones
before them — inside the existing architecture, without a parallel engine, a second
materiality system or a second evidence model.

## 2. Authoritative M8 scope

Taken from the repository, not from the brief:

| Source | What it fixes |
|---|---|
| `project_plan.md` M8 | "Forecast methods with adequacy predicates; scenario bands and assumption register; anomaly detectors with contributor attribution; `/revenue-forecast`, `/anomaly-detection`; insufficient-history and forecast-failure tests" |
| `architecture.md` §5 | Skills `biq-forecasting` ("refuses below minimum history; actuals never merged with forecast") and `biq-anomaly-detection` ("never classifies anything as fraud") |
| `architecture.md` §13 | Engine packages `forecast/` and `anomaly/`; schemas `forecast`, `anomaly` |
| `architecture.md` §14 | `forecast.min_history_periods` 12, `default_horizon_periods` 6, scenarios base/upside/downside; `anomaly.sensitivity` medium, `min_baseline_periods` 6 |
| `architecture.md` §18 | "A forecast method / anomaly detector — register with its adequacy predicate" — no ADR |
| `architecture.md` §9 | Worked example for `/revenue-forecast --horizon 6m` |

So: **2 engine packages, 2 schemas, 2 skills, 2 commands.** Nothing else.

### Scope discrepancies found and how they were resolved

| # | Discrepancy | Resolution |
|---|---|---|
| 1 | `project_plan.md` says M8 depends on **M5** only. It cannot: forecasting consumes the canonical dataset and privacy classification (M3), the quality gate (M4), materiality/evidence/presentation (M6) and the command layer (M7). | Recorded as **D-09**. Implemented against the real dependency set. The plan line was not edited — the dependency column is owner-governed. |
| 2 | The brief asks for OpEx and cash-flow forecasting; the demo dataset carries neither field, and `architecture.md` names only `/revenue-forecast`. | Narrowest consistent reading: both are **registered targets** that report `unavailable` naming the field they need. No inference, no substitution. |
| 3 | The brief lists "sales forecasting" as distinct from revenue. | Not implemented as a separate target: sales *is* the revenue series in this data model, and a second path would give one question two answers (ADR-0012). Documented in `engine.TARGETS`. |
| 4 | The brief asks for forecast-vs-actual; no command exposes it. | Built as a reusable engine capability (`forecast/variance.py`) with no command, since no command is authorised. |

## 3. Architecture

M8 attaches to the existing pipeline as two **optional passes**, siblings of the M6
analytics rather than a layer above them:

```
data → ingest → normalize → map → quality → KPI ─┬─ M6 analytics   → analysis Skills
                                                 ├─ M8 forecast    → biq-forecasting
                                                 └─ M8 anomaly     → biq-anomaly-detection
                                                                       ↓
                                                                   commands
```

`pipeline.forecast()` and `pipeline.detect_anomalies()` mirror `pipeline.analyse()`. Both
file their output in `result.analyses` under `"forecast"` / `"anomaly"`, so every existing
consumer of an `AnalysisSet` reads them unchanged.

Neither engine reads a file, calls a network, or uses randomness.

### Reuse, not reimplementation

| Needed | Reused from | Not rebuilt |
|---|---|---|
| Series construction | `kpi.primitives.series_by_period` | No second way to sum revenue by month |
| Quality halt, caveat propagation, provisional-mapping notes, privacy policy | `analytics.domain.prepare()` | No copy of the quality gate |
| Materiality | `materiality.assess_amount` / `assess_margin` | No anomaly-specific thresholds |
| Evidence classes and the ledger | `evidence.py` | No parallel provenance model |
| Privacy labels, k-floor, pseudonymisation | `analytics.presentation.LabelPolicy` | No second privacy gate |
| Output contract | `analytics.contract.AnalysisSet` / `AnalysisFinding` | `ForecastSet` and `AnomalySet` are subclasses |
| Command orchestration | `commands.registry` / `runner` / `sections` | Two registry rows + two renderers |

`ForecastSet.adopt()` and `AnomalySet.adopt()` re-wrap the `AnalysisSet` that
`domain.prepare()` already built, which is why neither module contains a quality check.

## 4. Files created

```
lib/python/biq/forecast/__init__.py      contract.py  series.py  methods.py
                        validate.py      variance.py  engine.py
lib/python/biq/anomaly/__init__.py       contract.py  baselines.py
                       detectors.py      engine.py
lib/schemas/forecast.schema.json         lib/schemas/anomaly.schema.json
skills/biq-forecasting/SKILL.md          skills/biq-anomaly-detection/SKILL.md
commands/revenue-forecast.md             commands/anomaly-detection.md
tests/fixtures/build_forecast_fixtures.py
tests/unit/test_forecast_methods.py      tests/unit/test_anomaly_detectors.py
tests/integration/test_forecast_m8.py    tests/integration/test_anomaly_m8.py
tests/negative/test_m8_negative.py
docs/development/2026-09-09-forecasting-anomaly.md
```

## 5. Files modified

| File | Change |
|---|---|
| `lib/python/biq/pipeline.py` | Added `forecast()` and `detect_anomalies()` entry points. Nothing existing altered. |
| `lib/python/biq/commands/registry.py` | Added `FORECAST`/`ANOMALY` sections, the `engine` field, and two `CommandSpec` rows. `DEFAULT_SECTIONS` pinned to the M7 eight so no M7 command grew a section. |
| `lib/python/biq/commands/runner.py` | Dispatches on `spec.engine`; `analysis_keys` generalises the aggregate views. |
| `lib/python/biq/commands/sections.py` | Two renderers added; `RENDERERS` extended. |
| `tests/unit/test_command_registry.py` | `EXPECTED_COMMANDS` split into `M7_COMMANDS` + `M8_COMMANDS`; the "unknown command" example moved to an M9 name. |
| `tests/integration/test_commands_m7.py` | Domain assertion now reads `run.analysis_keys`; unknown-command example moved. |
| `tests/negative/test_commands_negative.py` | Unknown-command list moved to M9+ names. |
| `tests/integration/test_performance.py` | Added the M8 measurement class. |
| `project_plan.md` | M8 → `REVIEW`; task table; D-09; R-09 update. |
| `docs/commands/README.md`, `docs/skills/README.md` | Two rows each. |

No M1–M7 behaviour was changed. The four M7 test edits re-point milestone-scoped
assertions at the new command set; none was weakened, and a new test asserts every M7
command is still declared.

## 6. Forecasting methods

Five, registered with adequacy predicates in `forecast/methods.py`:

| Method | Min history | What it assumes |
|---|---|---|
| `naive` | 2 | The last period repeats |
| `moving_average` | 3 | The recent mean holds; no direction |
| `drift` | 4 | The last value continues at the average step |
| `linear_trend` | 6 | A least-squares line through all history continues |
| `seasonal_naive` | 13 | The same month a year earlier repeats |

An **adequacy predicate** is the method's own statement of what it needs to *mean*
anything, not merely to compute. Seasonal naive with eleven months has no same-month to
copy, so it is not a weak forecast but a meaningless one.

**Selection is evidence-driven.** Every adequate method is backtested on held-out history
and the lowest-error one wins; ties break on declared priority, so selection is
deterministic. `method_rationale` names the winner, its error, and every method it beat.

No ML dependency was added. The engine remains stdlib-only; all arithmetic is `Decimal`.

## 7. Forecast contracts

`ForecastResult` carries: `forecast_id`, `metric`, `status`, `reason`, `unit`, `currency`,
`frequency`, `history`, `historical_period`, `forecast_period`, `horizon`, `method`,
`method_rationale`, `parameters`, `scenarios`, `assumptions`, `uncertainty`, `validation`,
`quality_grade`, `provenance`, `caveats`, `confidence`, `depends_on`, `min_history`.

Input contract per target: metric, time dimension, historical periods and values,
frequency, currency, Business Context, quality status, minimum history, comparison window,
scenario configuration. Frequency is **monthly or unsupported** — never inferred.

## 8. Scenario model and the assumption register

Three scenarios, each an assumption plus its arithmetic consequence:

- **base** — the method's output, unadjusted.
- **upside / downside** — base ± the band width, with the adjustment stated and quantified.

`reference/evidence-ledger.md` requires class-6 statements to be "flagged, and entered in
the assumption register". `AssumptionRegister` is that register: method appropriateness,
continuity, gaps, absent validation, derivation, and one entry per scenario. On the demo
dataset it holds **11 entries**.

Scenario language is conditional throughout; `contract.FORBIDDEN_CERTAINTY` lists the
wording that would turn an estimate into a promise, and the tests assert against it.

## 9. Uncertainty

The band is **not** a confidence interval, and `statistical_interval` is a required
constant `false` in the schema. Width is measured, in preference order:

1. `empirical_error_band` — the backtest MAPE.
2. `historical_volatility_band` — mean absolute period-over-period movement.
3. A default 5% band when history is flat and offers no evidence of movement.

Clamped to [1%, 60%]. The **lower** bound matters: a method that reproduced held-out
history exactly backtests at 0% error, and carrying that through would make all three
scenarios identical — presenting a forecast as certain.

The four things kept apart: model output · scenario assumption · uncertainty · user
assumption.

## 10. Validation

Holdout backtest. Holdout size is the horizon, capped at a third of history, and requires
at least 6 periods; below that no split leaves enough to train on. Records method, training
period, validation period, period counts, MAPE, MAE, and every candidate compared.

MAPE excludes zero actuals (undefined) and counts how many were excluded, so a mostly-zero
series cannot produce a flatteringly small error. MAE is reported alongside for that reason.

Where no backtest is possible, `validation.status` is `insufficient_data` with the reason,
and the forecast says plainly it is unvalidated — it does not silently omit the section.

## 11. Forecast vs actual

`forecast/variance.py` compares a forecast against actuals that arrive later: actual,
forecast, absolute variance, percentage variance, direction, materiality. Materiality comes
from the existing policy. Percentage variance is **withheld with a reason** when the
forecast was zero. Periods with actuals but no forecast are reported as `uncovered` rather
than dropped. Variance findings are `CALCULATION` — both halves are now observed.

Reusable engine capability; no command exposes it (none is authorised in M8).

## 12. Horizon

Default 6. Never more than half the observed history, and never more than 24. An over-long
request is **reduced and the reduction stated**, not silently honoured. A horizon below 1 is
refused (`is None` rather than a truth test, so `--horizon 0` is a refusal rather than a
default — a bug found by the unit tests, see §19).

## 13. Anomaly methods

Three detectors with adequacy predicates and configurable thresholds:

| Detector | Min prior periods | Baseline | Score |
|---|---|---|---|
| `robust_deviation` | 4 | Median trailing step carried forward; MAD of past residuals | sigma-equivalent |
| `mean_deviation` | 4 | Mean trailing step carried forward; stdev of past residuals | sigma |
| `seasonal_deviation` | 13 | Same month last year, grown by the typical year-on-year rate | % |

All baselines are **trailing only** — a period is judged against periods before it, so a
large month cannot raise its own baseline and hide itself.

Three design corrections were needed to make the scan usable, each caught by measuring the
false-positive rate on the demo dataset (§19). The resulting baseline is trend-aware,
robust to a single outlier in the window, and scored against the spread of *past prediction
errors* rather than the spread of the projections. A spread floor of 1% of the baseline
level prevents a run of similar residuals from collapsing the spread and inflating every
later score.

**Sensitivity** (`low`/`medium`/`high`) moves thresholds only, never the arithmetic.

## 14. Anomaly status, materiality and severity

Status vocabulary, as the brief requires: `normal`, `unusual`, `material_anomaly`,
`insufficient_data`.

Two independent judgements meet:

- **status** — how far the observation is from its baseline (the detector).
- **materiality** — whether it is big enough to matter (the existing M2/M6 policy,
  `assess_amount` for amounts, `assess_margin` for margins in percentage points).

`material_anomaly` requires **both**. No anomaly-specific threshold system was created.

## 15. Anomaly evidence and contributor attribution

Every observation carries what changed, observed value, baseline (method, centre, spread,
periods, window), deviation, deviation %, score, threshold, period, materiality, detector,
caveats. Findings are `CALCULATION` (evidence class 4) — a deviation is measured.

`architecture.md` calls for **contributor attribution**: for a flagged period, each
dimension member's value is compared with its own mean across the baseline periods, and the
largest movers *in the same direction as the deviation* are named with their share of the
movement. Attribution answers **where**, never **why**.

The scan keeps every checked period in `observations`, not only the flagged ones, so
"nothing was found" is distinguishable from "nothing was looked at".

## 16. Fraud boundary

Mandatory and enforced as data, not documentation:

- `contract.FRAUD_LANGUAGE` — 16 forbidden terms, asserted against every emitted statement,
  caveat, limitation and finding in the integration tests.
- `contract.CAUSAL_LANGUAGE` — causal phrasings, asserted the same way.
- `contract.INVESTIGATION_NOTE` — the strongest permitted statement, attached to every
  flagged finding and published in the structured output as `fraud_boundary`.

> This is a deviation from the historical baseline and may warrant investigation. It does
> not establish a cause, and it is not evidence of fraud or of any wrongdoing.

No fraud-detection capability was built, and no approval unlocks that framing.

## 17. Privacy, Business Context, quality, KPI

**Privacy.** Reuses the M3/M6 classification. Contributor labels pass through
`LabelPolicy.label()`, so identifying values are pseudonymised in SHAREABLE mode; the
k-floor and banding are unchanged; no individual transaction is rendered (asserted).

**Business Context.** The existing mechanism only. Currency, reporting period, comparison
window and business model reach both engines through `domain.prepare()`. No second context
system.

**Quality.** `CRITICAL` halts — no forecast is produced and no period is scanned. `WARNING`
proceeds with the caveat attached to every finding, and lowers forecast confidence to `LOW`.
`PASS` is normal. Neither engine re-runs a quality check (asserted).

**KPI.** No formula recreated. Series come from `kpi.primitives`; gross profit is derived
from the revenue and cost roles and says so in an assumption; `unavailable`,
`not_applicable` and `insufficient_data` statuses are respected and propagated.

## 18. Interpretation boundary

`ForecastSet` widens the M6 emission rule by exactly one class — `ASSUMPTION` (class 6),
because an estimate about a future period is the one thing the historical analytics layer
must never produce. `INTERPRETATION` and `RECOMMENDATION` stay forbidden in both engines,
and the M6 `AnalysisSet` was **not** widened (asserted by a test).

`AnomalySet` adds no class at all: an anomaly is a `CALCULATION`.

## 19. Bugs found and fixed

| # | Found by | Problem | Fix |
|---|---|---|---|
| 1 | Unit test | `resolve_horizon(0, …)` treated an explicit horizon of 0 as absent and silently returned the default 6 | `is None` test instead of a truth test |
| 2 | Integration test | A perfectly regular series backtests at 0% error, so base/upside/downside came out identical — a forecast presented as certain | `MIN_BAND_PCT` floor of 1%; `_clamp()` |
| 3 | Demo measurement | **49% of periods flagged.** A trailing *level* baseline is always below the current value in a growing business, so ordinary growth read as anomalous | Baselines scored on period-over-period movement, not level |
| 4 | Demo measurement | Seasonal detector then dominated: a business up ~90% year-on-year cleared a fixed 40% bar every month | Seasonal centre carried forward by the typical year-on-year rate; refuses before one full YoY pair exists |
| 5 | Unit test | A single spike produced **two** flags — the spike and the return to normal — because the expectation anchored on the previous value alone | Anchor is the median of every window value carried forward, so one outlier is one projection in twelve |
| 6 | Unit test | A straight linear ramp flagged: compounding a growth rate through a linear series overshoots, and the model error was indistinguishable from an anomaly | Additive `period_steps` rather than growth rates — degenerates exactly on both flat and linear series |
| 7 | Demo measurement | Scores exploded when past residuals happened to cluster (a +5.4% month scoring 5.8σ) | Spread floor: no baseline is treated as tighter than 1% of its own level |

Items 3–7 were all found by measuring the flag rate on the demo dataset rather than by a
failing assertion, which is why the demo run is treated as a test artifact and not only as
a demonstration. Flag rate: **49% → 39% → 26%**, with every remaining flag a deviation of
15% or more.

## 20. Testing

| Suite | Tests |
|---|---|
| `tests/unit/test_forecast_methods.py` | 42 |
| `tests/unit/test_anomaly_detectors.py` | 43 |
| `tests/integration/test_forecast_m8.py` | 65 |
| `tests/integration/test_anomaly_m8.py` | 54 |
| `tests/negative/test_m8_negative.py` | 49 |
| `tests/integration/test_performance.py` | +5 |
| `tests/unit/test_command_registry.py` | +1 |
| **Total added** | **259** |

Every adversarial case the brief lists is covered. Forecasting: one period, two periods,
insufficient history, missing date, missing metric, irregular periods, zero baseline,
constant series, strong trend, seasonality, missing cost, missing cash, CRITICAL, WARNING,
ambiguous mapping, unavailable KPI, not-applicable KPI, unsupported frequency, unsupported
horizon, determinism. Anomaly: empty dataset, insufficient history, constant series,
isolated spike, isolated drop, multiple anomalies, zero baseline, negative values, missing
periods, missing metric, CRITICAL, WARNING, ambiguous mapping, privacy-sensitive customer
data, determinism.

### Full regression

```
ran 1079 | failures 0 | errors 0 | skipped 17
Ran 1079 tests in 369.629s — OK (skipped=17)
```

M7 baseline 820 → **1079**. Skips unchanged at 17, all pre-existing (Tier-2 runtime and
optional-dependency paths). No test was weakened.

## 21. Demo dataset results

`assets/demo-data/northwind_sales.csv` — 2,204 rows, 24 periods (2024-01…2025-12), quality
**PASS**, processing mode **full**.

**Forecast** — set `available`, horizon 6, 6 findings, 2 limitations, 11 assumptions:

| Target | Status | Method | History | MAPE | Band | Base | Confidence |
|---|---|---|---|---|---|---|---|
| revenue | available | linear_trend | 24 | 10.94% | ±10.94% | 1,491,165.59 | MEDIUM |
| gross_profit | available | naive | 24 | 8.90% | ±8.90% | 341,571.06 | MEDIUM |
| operating_expense | unavailable | — | — | — | — | — | — |
| cash_flow | unavailable | — | — | — | — | — | — |

Both refusals name the field required and state that the metric is never inferred from cost
of goods / derived from sales. **No cash-flow or OpEx forecast was manufactured.**

**Anomaly** — set `available`, sensitivity `medium`, 108 periods checked, **26 flagged**,
26 material, 2 limitations:

| Metric | Scan | Checked | Flagged |
|---|---|---|---|
| revenue | available | 18 | 4 |
| cost | available | 18 | 4 |
| gross_profit | available | 18 | 7 |
| gross_margin | available | 18 | 6 |
| order_count | available | 18 | 4 |
| active_customers | available | 18 | 1 |
| operating_expense | unavailable | 0 | 0 |
| cash_balance | unavailable | 0 | 0 |

Largest: revenue 2025-02 (−26.97%) and 2025-11 (+37.06%) — the two biggest swings in the
series. Privacy: local presentation, contributors named by product; no transaction rendered.

## 22. Performance

Measurement, not optimisation. Both engines run on top of an already-completed pipeline run.

| Operation | Scale | Time |
|---|---|---|
| forecast: 4 targets | 2.2k rows, 24 periods | 0.03s |
| forecast: 4 targets | 30k rows | 0.39s |
| forecast: backtest 5 methods | 24 periods | <0.01s |
| anomaly: 8 metrics | 2.2k rows, 108 periods checked | 0.32s |
| anomaly: 8 metrics | 30k rows | 0.88s |
| command `/revenue-forecast` | 2.2k rows | ~2.5s |
| command `/anomaly-detection` | 2.2k rows | ~2.9s |

Command timings are dominated by the pipeline run beneath them, not by M8.

## 23. Token / component measurement (R-09)

Frontmatter characters ÷ 4, the M6/M7 methodology.

| Milestone | Components | Always-on tokens | Per component |
|---|---|---|---|
| M6 | 4 skills | 661 | 165 |
| M7 | 4 skills + 7 commands = 11 | 1,534 | 139 |
| **M8** | **6 skills + 9 commands = 15** | **2,097** | **140** |

New: `/anomaly-detection` 147, `/revenue-forecast` 141, `biq-anomaly-detection` 143,
`biq-forecasting` 132.

Extrapolated to the full 37-component architecture: **~5,172**, against the self-imposed
≤3,000 target. Above the M7 projection (~4,800) because M8's four components are slightly
above the running average — both commands describe a refusal boundary as well as a
capability, and that is load-bearing text.

**Nothing was merged and no description was shortened to hit a number.** All 15 components
remain mutually distinguishable, and each names what it does *not* cover. R-09 remains open
and is now materially worse; ADR-0013's prescription (merge overlapping components if the
trend holds) is an owner decision at M10, when the component count roughly doubles.

## 24. Plugin validation

| Command | Result |
|---|---|
| `validate .claude-plugin/plugin.json` | passed with 1 warning |
| `validate .claude-plugin/marketplace.json --strict` | passed |
| `validate . --strict` | passed |

The single warning is the known R-08 advisory (root `CLAUDE.md` not shipped as plugin
context), unchanged. The two new skills and two new commands add no further warnings.

## 25. Risks

| Risk | Effect of M8 |
|---|---|
| R-01 eval gated | Unchanged — `BLOCKED`, external |
| R-02 connectors | Unchanged — M8 is internal-data only |
| R-03 Python availability | Unchanged — no new runtime requirement |
| R-04 Tier-3 XLSX | Unchanged |
| R-05 discriminability | **Slightly raised** — 15 components now; the two new commands overlap in trigger vocabulary with `/profitability-analysis` ("what will profit be"). Routing evals remain M13 |
| R-06 supply chain | Unchanged — no dependency added; engine remains stdlib-only |
| R-07 re-identification | Unchanged — contributor attribution reuses the existing policy and adds no new disclosure path |
| R-08 CLAUDE.md advisory | Unchanged — confirmed by this validation run |
| R-09 token cost | **Materially worse** — 1,534 → 2,097; extrapolation 4,800 → 5,172. Evidence recorded above; not optimised, per instruction |

**New:** **R-10 — forecast method selection is backtest-driven on short histories.** With 24
periods the holdout is 6, so selection rests on 6 observations and can pick a method that
happens to fit those six. Mitigated by reporting every candidate's error and by never
claiming statistical validity, but a user comparing two runs on adjacent datasets may see
different methods chosen. Open.

Debt D-05, D-06, D-07 and D-08 are preserved untouched. **D-09** is new (§2.1).

## 26. Limitations

1. **Monthly only.** The engine's period key is a calendar month (M5). Weekly, quarterly
   and fiscal-calendar forecasting are not supported; frequency is monthly or unsupported.
2. **One file per run.** No multi-source joins.
3. **No probability.** The band is empirical. Nothing in M8 produces a statistically valid
   interval, and the contract refuses to call one that.
4. **Method selection can be unstable on short history** (R-10).
5. **Contributor attribution is single-dimension** — the first mapped dimension in priority
   order, not a multi-dimensional decomposition.
6. **Anomaly scanning is deliberately sensitive**; materiality, not the detector, is what
   keeps the output short. A volatile series will still produce a long list.
7. **A sustained trend change produces consecutive flags** — the demo's six consecutive
   gross-margin flags are one story, and summarising them is the skill's job, not the
   engine's.
8. **No forecast-vs-actual command.** The capability exists; no command exposes it.
9. `PipelineResult.as_dict()` is still not JSON-serialisable (**D-05**, pre-existing). Every
   `ForecastSet` and `AnomalySet` **is**, and is tested to be.

## 27. Remaining work

None for M8. Outstanding items belong to later milestones or await owner decisions: R-02
connectors, R-05/R-10 routing and stability evals (M13), R-09 against ADR-0013, and D-05
through D-09.

## 28. Git

No commit, no push, no amend, no rebase during this milestone. Branch `main`; HEAD remains
`8d52b0e Initial BusinessIQ plugin setup`.

---

# Milestone 8 focused review gate — 2026-09-09

Appended after the M8 implementation record above, not merged into it. Sections 1–28
describe what was built; this section describes what a focused review of three areas found
and changed. Where the review contradicts a claim made above, the review is authoritative
and says so explicitly.

## R-1. R-09 / ADR-0013

**What ADR-0013 actually defines.** Re-read in full. It corrects an earlier invented
4,000-token "platform ceiling", records that a 42-component probe measured ~2,617 tokens
with no cap, warning or error, and concludes:

1. Target **≤ 3,000 tokens always-on**, explicitly labelled *self-imposed*.
2. Measure per milestone with `claude plugin details businessiq` and record it.
3. **The real constraint is description discriminability, not tokens.**
4. "What happens if the budget is exceeded: **nothing breaks.**" The prescribed response is
   to **merge components whose descriptions overlap** — and "never to truncate
   descriptions, since a description too thin to match is worse than one costing 110
   tokens."
5. Revisit when Anthropic documents an aggregate limit, or **measured routing accuracy
   degrades**.

**Does M8 cross the threshold?** No. The measured value is **2,097 tokens across 15
components — 70% of the self-imposed target.** The ~5,172 figure is an extrapolation to a
hypothetical 37-component future, not a measurement, and ADR-0013 exists precisely to stop
the architecture being optimised against a number nobody has hit.

**Does M8 violate the ADR?** No. Nothing was truncated, nothing was merged, and no
description was shortened to hit a target.

**Correction to section 23 above.** That section called R-09 "materially worse". The review
does not support that wording as written:

| Milestone | Components | Always-on | Per component |
|---|---|---|---|
| M6 | 4 | 661 | 165 |
| M7 | 11 | 1,534 | 139 |
| M8 | 15 | 2,097 | **140** |

Per-component cost is flat (139 → 140). The total grew because the component count grew,
which is the architecture working as designed. The honest statement is: **the measured
value remains comfortably inside the self-imposed target; only the extrapolation exceeds
it, and the extrapolation is not what the ADR asks to be governed by.** R-09 stays open as
a watch item.

**Discriminability — the constraint the ADR actually names.** Measured as Jaccard overlap
of content words between component descriptions, within each competing tier:

| Tier | Pairs | Mean overlap | Max overlap |
|---|---|---|---|
| Command vs command | 36 | 0.085 | 0.192 (`/product-analysis` vs `/profitability-analysis`) |
| Skill vs skill | 15 | 0.202 | 0.354 (`biq-customer-intelligence` vs `biq-product-intelligence`) |

**Correction to section 25 above.** That section recorded R-05 as "slightly raised" by M8,
naming `/revenue-forecast` vs `/profitability-analysis` as the concern. Measurement
contradicts it: that pair scores **0.097**, well below the command-tier maximum of 0.192,
and their distinguishing vocabulary is disjoint (forecast: *backtested, band, downside,
scenario, horizon*; profitability: *ebitda, margin, percentage points, profitable*). The
highest overlaps in both tiers are **pre-existing M6/M7 pairs**, not M8 ones. M8 did not
worsen discriminability.

**Methodology gap found.** ADR-0013 prescribes `claude plugin details businessiq` and lists
recording its output as a follow-up. That command resolves only an *installed* plugin;
BusinessIQ is not installed, and `--plugin-dir` is not an accepted option on this CLI
version. M6, M7 and M8 therefore all used the same proxy — frontmatter characters ÷ 4 —
which is internally consistent across milestones but is **not** the procedure the ADR
names. Recorded as **D-10**. Installing the plugin to satisfy the ADR would change global
user state and was not done as part of a review gate; it is an owner decision.

**Decision: no token or component change was made.** None is required by ADR-0013 and
making one would be the exact error the ADR was written to prevent.

## R-2. Forecast uncertainty

Verified against implementation, schema, renderer, skill, command and tests.

**Already correct — no change required:**

- MAPE is treated as empirical error throughout; the band kind is `empirical_error_band`.
- `statistical_interval` is a required constant `false` in the schema and a read-only
  property in code; every band statement carries "not a statistical confidence interval".
- No probability, p-value, significance level or `0.82`-style pseudo-confidence anywhere.
- `confidence` and `uncertainty` are separate fields of different types — a qualitative
  ledger grade versus a numeric band — and are never combined.
- Scenario bands are presented as illustrative cases under stated assumptions.
- A scan of the whole M8 surface for distributional vocabulary returned only *negations*.

**Finding U-1 — the backtest error is a selection statistic (fixed).** `validate.select`
scores every adequate method on one holdout and picks the lowest, then reported that error
as "the error of this method on held-out history". A statistic used to *choose* is
optimistic as an estimate of the chosen thing, and the uncertainty band is derived from it,
so the band is correspondingly narrow. The output did not say so.

*Change:* `Validation.statement()` now discloses it ("This is the lowest error among 5
methods scored on the same holdout, and the method was selected on it, so it flatters the
method and the band derived from it is correspondingly narrow"), a matching class-6 entry
was added to the assumption register, and the schema's `mape` description records it. No
statistical model, no dependency, no change to any number.

**Finding U-2 — `confidence` semantics were under-documented (fixed).** The field was
correct but the schema described only "never HIGH". It now states that it is the evidence
ledger's qualitative grade, that it is not a probability, and that `uncertainty.pct` carries
the width separately.

## R-3. Anomaly detector correctness

This is where the review found real defects. Five fixed.

**Finding A-1 — the baseline was biased, and the bias landed entirely in the deviation
(fixed).**

*Evidence:* on 8%/month compounding growth, **23 of 24 periods were flagged**. Measured
directly: at index 20 the predictor's median residual was +2,097 while the spread it was
scored against was 639 — the offset was three times the spread.

*Root cause:* `centre` was a raw projection while `spread` was the dispersion of that
projector's residuals. An additive step cannot fit a compounding series, so the systematic
offset went wholly into the deviation and none of it into the spread, guaranteeing a large
score for every ordinary period.

*Change:* the centre is corrected by the predictor's own recent offset
(`centre = projection + median(residuals)`), and the spread is measured around that same
offset, putting both on one footing. On flat and straight-line series every residual is
zero and the baseline is unchanged.

*Result:* compounding growth at 3%/month and 8%/month now flags **nothing**.

**Finding A-2 — a fragile detector could overrule a robust one (fixed).**

*Evidence:* an isolated spike produced **two** flags — the spike and the recovery. At the
recovery period `robust_deviation` correctly reported deviation 0, while `mean_deviation`
reported centre 32,727 against an actual of 10,000 and flagged it.

*Root cause:* any adequate detector could raise a flag. The mean is dragged by an outlier
inside its own window, which is exactly the window that follows a spike — so the detector
known to fail there was overruling the one built to survive it.

*Change:* detectors now carry `triggers`. `robust_deviation` is authoritative;
`mean_deviation` is corroborating — still measured, scored and reported, but it cannot raise
a flag alone.

**Finding A-3 — the seasonal detector rested on a single, possibly anomalous observation
(fixed).**

*Evidence:* with spikes in March 2024 and January 2025, March 2025 was flagged as "75%
below last March" — because last March *was* the spike.

*Root cause:* the seasonal baseline is one prior observation. It cannot distinguish "this
year is unusual" from "last year was unusual", and outvoting a bad prior year needs three
or more same-month observations, which a business with two or three years of history never
has.

*Change:* `seasonal_deviation` is corroborating only. The year-on-year comparison is still
measured and reported; it no longer triggers.

**Finding A-4 — attribution divided currency by orders (fixed).**

*Evidence:* the demo output contained contributor shares of **14,140%** (order volume) and
**−2,986%** (gross margin).

*Root cause:* attribution is always measured in revenue, and `share_pct` divided that
revenue movement by the period's deviation — which for `order_count` is a number of orders
and for `gross_margin` is percentage points. A unit mismatch.

*Change:* a share is claimed only when both sides are currency. Non-currency metrics still
name the members that moved, without a fabricated ratio, and carry a caveat saying
contributors are measured in revenue. The renderer no longer prints "unavailable of the
movement".

**Finding A-5 — the score unit implied statistics it does not have (fixed).** Scores were
reported as "3.92 sigma" / "5.83 sigma-equivalent". A reader who sees "3 sigma" infers
roughly one-in-370 — a probability the engine never computes, since it fits no distribution
and tests none. The unit is now **"x typical error"**, which is exactly what the ratio is.
The `MAD_SCALE` constant is retained (it puts the robust and non-robust detectors on one
comparable scale) but its comment no longer justifies itself by appeal to normality.
Thresholds and arithmetic are unchanged; only the label moved.

**Verified, no change required:**

- **No future leakage.** Proven by truncation, not inspection: for five series shapes and
  every cut point, the verdict *and the score* for every period are identical whether or not
  later periods exist. Windows, residuals, bias correction and year-on-year rates are all
  drawn strictly from periods before the one being judged. A later spike cannot change an
  earlier verdict. Forecast training and validation slices are disjoint, and no forecast
  point is ever a period that was observed.
- **Materiality stays separate.** Holding the data fixed and changing only the materiality
  policy moves `material_anomaly` → `unusual` while leaving score and deviation
  bit-identical. No anomaly-specific threshold system exists.
- **Robust spread.** Identical residuals, clustered residuals, zero MAD, zero standard
  deviation and zero baselines all handled; the 1% floor suppresses a 5% wobble on a
  trending series while a 4× spike on the same series is still flagged.
- **Attribution answers where, not why.** No causal or fraud vocabulary in any contributor
  label or emitted string.
- **Privacy.** SHAREABLE pseudonymises identifying contributors, the k-floor is the existing
  one, and no raw transaction reaches the serialised scan.

## R-4. Demo dataset recheck

`assets/demo-data/northwind_sales.csv` — 2,204 rows, 24 periods, quality **PASS**, mode
**full**.

**Forecast — unchanged in substance.** revenue (linear_trend, MAPE 10.94%, band ±10.94%,
base 1,491,165.59) and gross_profit (naive, MAPE 8.90%, band ±8.90%, base 341,571.06)
available; operating_expense and cash_flow unavailable, naming the field each needs.
Assumptions rose 11 → **13** (the new selection-bias entry per validated target), and the
validation statement now discloses the selection.

**Anomaly — changed, and this is expected.**

| | M8 as reported | After review |
|---|---|---|
| Periods checked | 108 | 108 |
| Flagged | 26 (24.1%) | **11 (10.2%)** |
| Material | 26 | 11 |
| Triggering detector | robust, mean and seasonal | **robust only** |

Per metric: revenue 1, gross_profit 3, gross_margin 4, order_count 2, active_customers 1;
operating_expense and cash_balance unavailable.

**Why the count fell.** Every removed flag came from a defect above, not from a threshold
change — no threshold, sensitivity or materiality value was altered. The 15 removed flags
were: recoveries and outlier-contaminated windows reported by `mean_deviation` (A-2), a
year-on-year comparison against a contaminated prior year (A-3), and periods whose score was
inflated by uncorrected model bias (A-1). The survivors are the substantive ones — the
2025-07 revenue and gross-profit fall, the sustained gross-margin decline through H2 2025,
and the 2024-09/10 order-volume rise.

## R-5. Tests

55 review tests added in `tests/integration/test_m8_review.py`, covering no-future-leakage
(by truncation), growth shapes, seasonality, spike/recovery, robust-spread degeneracy,
materiality separation, attribution units, privacy, and the absence of any distributional
claim. Two assertions in the new file were themselves wrong when first written and were
corrected: a bare `95%`/`99%` screen matched ordinary percentages such as "13.99% of the
baseline", and the sanctioned *denials* ("not a statistical confidence interval")
legitimately contain the phrases being screened for.

No existing test was weakened. **Every M8 test written before this review still passes
unchanged**, which is the main evidence that the detector fixes corrected behaviour rather
than moved goalposts.

```
ran 1134 | failures 0 | errors 0 | skipped 17
```

M8 as reported 1,079 → **1,134** (+55). Skips unchanged at 17, all pre-existing.

## R-6. Performance

Re-measured because detector code changed. Forecast is unchanged in substance.

| Operation | Scale | Before | After |
|---|---|---|---|
| forecast: 4 targets | 2.2k rows | 0.03s | 0.02s |
| forecast: 4 targets | 30k rows | 0.39s | 0.47s |
| anomaly: 8 metrics | 2.2k rows | 0.32s | 0.26s |
| anomaly: 8 metrics | 30k rows | 0.88s | 0.84s |
| `/revenue-forecast` | 2.2k rows | ~2.5s | 2.79s |
| `/anomaly-detection` | 2.2k rows | ~2.9s | 2.92s |

The bias correction adds no measurable cost: the residuals it uses were already computed
for the spread. Differences are run-to-run noise on a shared machine. No optimisation was
performed.

## R-7. A defect introduced and fixed during this review

Recorded because it was self-inflicted and because the guard it produced is now part of the
suite.

**Problem.** After the documentation edits, `claude plugin validate .claude-plugin/plugin.json`
failed: *"frontmatter: YAML frontmatter failed to parse … At runtime this command loads with
empty metadata (all frontmatter fields silently dropped)"* on `commands/anomaly-detection.md`.
A command that loads with no description does not route at all, so this is a functional
failure, not a cosmetic one.

**Root cause.** Two things had to combine. The description contained a bare `: ` inside an
unquoted YAML scalar ("Describes deviations only: it never establishes a cause"), which YAML
reads as a nested mapping; that alone had been tolerated. The edits were applied with Python
in text mode, which on Windows silently rewrote the file with CRLF line endings, and the
stray carriage return turned the tolerated colon into a parse error.

**Fix.** LF restored on the eleven files this review had rewritten through Python — and only
those; the roughly forty other files in the repository that already carried CRLF were left
alone, as unrelated cleanup. The colon was removed from the description ("Describes
deviations only, and never establishes a cause") so the frontmatter cannot break again
regardless of line endings. Always-on token cost is unchanged at 2,097.

**Guard added.** `TestComponentFrontmatterParses` (4 tests) reads every command and skill as
**bytes** — text mode hides exactly the newline translation that caused this — and asserts
each has a delimited frontmatter block, no unquoted value containing `": "`, no continuation
line, and only supported fields. The pre-existing M7 frontmatter test read in text mode and
could not have caught it.

**Verification.** `validate .claude-plugin/plugin.json` back to passing with the single known
R-08 advisory; `marketplace.json --strict` and `. --strict` pass. Final suite:
`ran 1134 | failures 0 | errors 0 | skipped 17`.

## R-8. Remaining limitations

Two are now proven rather than assumed, and both are characteristics of a trailing-window
detector rather than defects:

1. **A sustained step change is flagged for several periods.** A permanent level shift is
   genuinely unusual against history, and the offset correction needs post-step periods
   before it follows. Bounded, not eliminated: the run of flags ends well inside the
   baseline window and the tail is clean. Asserted as such.
2. **Seasonality is not modelled by any triggering detector.** `robust_deviation` follows a
   trend, not a repeating shape, so a strongly seasonal series produces some false positives
   at the turns — under a third of periods, asserted. Now that `seasonal_deviation` is
   corroborating, nothing triggers on year-on-year structure. Fixing this means seasonal
   decomposition, which is new functionality and out of scope for a review gate.

**New debt: D-10** — ADR-0013's prescribed measurement command has never been runnable
here; M6–M8 used a consistent proxy instead.

R-10 (backtest selection instability) is unchanged as a risk, but its most misleading
consequence — reporting a selection statistic as a clean out-of-sample error — is now
disclosed in the output rather than only in this record.


---

## Final status

**Milestone 8 approved by the project owner on 2026-09-10.**

The milestone is closed as `COMPLETED` in `project_plan.md`. Approval covers the
implementation and its recorded state; it closes nothing else. Specifically:

- **Risks R-01 through R-10 remain open** at the status recorded above and in
  `project_plan.md`. R-09 (always-on token growth) stays an active watch item, governed by
  ADR-0013, which remains authoritative: no component may be merged and no description
  shortened on the strength of the extrapolated figure. R-10 (backtest selection
  instability) stays documented.
- **Debt D-05 through D-10 remain open**, including D-10, the discrepancy between
  ADR-0013's prescribed measurement command and the proxy actually used since M6.
- **Every limitation in section R-8 stands.** Approval means the milestone was accepted
  with those limitations understood, not that they were resolved.

State at approval: 1,134 tests, 0 failures, 0 errors, 17 skipped; plugin validation passing
with the single known R-08 advisory; 2,097 always-on tokens across 15 components.

No M8 code was changed to record this approval — the closure is documentation only.

**Next:** the Milestone 9 architecture and scope review. M9 is the first milestone in which
information may leave the machine, so it opens with a gate rather than an implementation
task. The questions that gate must answer are in
`docs/development/2026-09-10-m8-closure-m9-gate-preparation.md`.
