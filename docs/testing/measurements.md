# M13 measurements

ADR-0039 §D. Each measurement is **recorded, never tuned**: no threshold, method, description, limit or configuration
was changed to move a result (ADR-0039 I-1, D.4). A measurement describes the product, but it is not product
behaviour and not a test verdict. No pass/fail threshold exists for any of these, because none is defined by accepted
architecture. The only asserted limit is a platform limit; see D2.

Common context for all three:

| Item | Value |
|---|---|
| Date | 2026-09-18 |
| Commit | base `990e88d` (M13.1 uncommitted working tree) |
| Python | 3.13.1 |
| Claude Code | 2.1.276. It was not used by any measurement, and no eval was executed |
| Machine | the owner's Windows 11 development machine. Timings are machine- and load-dependent |

---

## M13-MEAS-D1 — large dataset

| Item | Value |
|---|---|
| Status | `executed` |
| Invocation | `BOPS_LARGE_DATASET=1 python tests/run_tests.py -v integration.test_m13_large_dataset` |
| Inputs | `tests/fixtures/build_m13_large_fixtures.large_csv(tmp, rows)`: deterministic synthetic CSV, 12 demo-compatible columns, 24 monthly periods, integer-pence money, labels `Synthetic …` / `SYN-…`. Written to a temporary directory and deleted afterwards; never committed |
| Stages | `pipeline.run` (ingestion → quality gate → KPI engine), then `commands.run("sales-analysis", …)` |
| Timing | Wall clock, pass 1, no tracing |
| Memory | Traced allocation peak across both stages, pass 2 under `tracemalloc` |
| Result | 6 tests, 0 failures. Every correctness assertion held at both sizes |

| Measure | 100,000 rows | 250,000 rows |
|---|---|---|
| File size (bytes) | 12,805,664 | 32,013,999 |
| Generate (s) | 0.23 | 2.13 |
| `pipeline.run` (s) | 19.25 | 73.61 |
| `/sales-analysis` (s) | 32.57 | 87.15 |
| `tracemalloc` peak (MiB) | 286.0 | 712.3 |
| Rows read / examined | 100,000 / 100,000 | 250,000 / 250,000 |
| Revenue: engine vs independent exact total | 46363683.39 = 46363683.39 | 115911263.02 = 115911263.02 |
| Source SHA-256 unchanged | yes | yes |
| Halted | no | no |
| `/sales-analysis` status | `ok` | `ok` |
| `processing_mode` / `complete` | `full` / true | **`streamed` / false** |
| Quality grade | `PASS` | **`WARNING`** |
| Revenue KPI status | `available` | **`partial`** |
| Global caveats | none | "Only 250000 of 250000 rows were examined (streamed processing); figures describe the examined portion." · "Data quality: Only 250000 of 250000 rows were examined (streamed processing). Quality findings describe the examined portion, not the whole dataset." |

**Observations**

1. **Correctness holds at both sizes.** Every row was read, the exact revenue total was reproduced, and the source
   was untouched.
2. **Above `LARGE_ROW_THRESHOLD` (100,000) the pass is mislabelled.** Every row was materialised and examined, yet it
   is recorded as `streamed` and incomplete. The caveats, the quality grade and the KPI status then describe a
   partial pass that did not happen. This is **product defect M13-DEF-03**: recorded, not fixed. It errs
   conservatively and never presents a sample as a full pass, so D.1's honesty assertion holds.
3. **Timing varies between runs.** An earlier D.1 run the same day, before the M13-DEF-02 test fix, took 18.60 s /
   31.51 s at 100k and 47.63 s / 82.95 s at 250k (`pipeline.run` / `/sales-analysis`), with identical peaks. Each
   figure is one observation, not a benchmark.
4. **Scope limits.** Large `.xlsx` was not measured: chunked streaming is an open Data Layer deferral (M3). M3's
   always-on 60,000-row baseline (`test_performance.py`) was not edited.

---

## M13-MEAS-D2 — description discriminability (R-05)

| Item | Value |
|---|---|
| Status | `executed` |
| Invocation | `python tests/run_tests.py unit.test_m13_discriminability`, which prints the summary. The full record comes from `measure()`, as in the module docstring |
| Method | Tier-scoped Jaccard over content words: lower-cased; `[a-z]+` runs of three or more letters; the stop-word list fixed in the module. M8 did not record its tokenisation or stop words, so these figures are **not directly comparable** with the M8 review's (command mean 0.085, max 0.192; skill mean 0.202, max 0.354), which also covered fewer components |
| Tiers | Commands: 18 model-invocable (`retrieval-slice` excluded, `disable-model-invocation: true`), 153 pairs. Skills: 16, 120 pairs |
| Assertions | Every command, skill and agent has a non-empty description; the measurement is deterministic. The 1,024-character skill limit was **not** committed as an assertion because two skills exceed it: **M13-DEF-01** |

| Tier | Components | Pairs | Mean | Max | Top three pairs |
|---|---|---|---|---|---|
| Command | 18 | 153 | 0.077 | 0.556 | `industry-research` / `market-analysis` 0.556 · `decision-support` / `strategy-analysis` 0.458 · `company-analysis` / `market-analysis` 0.415 |
| Skill | 16 | 120 | 0.097 | 0.633 | `bops-industry-research` / `bops-market-analysis` 0.633 · `bops-decision-support` / `bops-strategy-recommendations` 0.345 · `bops-company-analysis` / `bops-market-analysis` 0.340 |

**Observations**

1. **Industry research and market analysis overlap most, in both tiers.** This is the shared-shape concern the M9
   architecture review raised for the external-research skills. It is recorded against R-05 and is not a defect: no
   overlap threshold exists.
2. The three highest-overlap pairs per tier are M13.2's near-miss routing cases (ADR-0039 §E.3).
3. No description was changed.

### All pairs

#### Command tier: 18 components, 153 pairs, mean 0.077, max 0.556

| Pair | Jaccard |
|---|---|
| `industry-research` / `market-analysis` | 0.556 |
| `decision-support` / `strategy-analysis` | 0.458 |
| `company-analysis` / `market-analysis` | 0.415 |
| `company-analysis` / `industry-research` | 0.386 |
| `company-analysis` / `competitor-analysis` | 0.350 |
| `strategy-analysis` / `swot-analysis` | 0.308 |
| `executive-report` / `swot-analysis` | 0.280 |
| `executive-report` / `strategy-analysis` | 0.267 |
| `competitor-analysis` / `industry-research` | 0.250 |
| `competitor-analysis` / `market-analysis` | 0.229 |
| `decision-support` / `executive-report` | 0.228 |
| `decision-support` / `swot-analysis` | 0.192 |
| `benchmark-comparison` / `swot-analysis` | 0.190 |
| `product-analysis` / `profitability-analysis` | 0.189 |
| `benchmark-comparison` / `strategy-analysis` | 0.156 |
| `anomaly-detection` / `product-analysis` | 0.154 |
| `industry-research` / `strategy-analysis` | 0.147 |
| `customer-analysis` / `product-analysis` | 0.138 |
| `company-analysis` / `strategy-analysis` | 0.132 |
| `company-analysis` / `decision-support` | 0.129 |
| `decision-support` / `industry-research` | 0.128 |
| `ask-business-data` / `business-health` | 0.123 |
| `product-analysis` / `sales-analysis` | 0.121 |
| `benchmark-comparison` / `executive-report` | 0.118 |
| `anomaly-detection` / `profitability-analysis` | 0.115 |
| `anomaly-detection` / `customer-analysis` | 0.109 |
| `ask-business-data` / `profitability-analysis` | 0.109 |
| `market-analysis` / `strategy-analysis` | 0.108 |
| `profitability-analysis` / `revenue-forecast` | 0.098 |
| `competitor-analysis` / `decision-support` | 0.098 |
| `profitability-analysis` / `sales-analysis` | 0.094 |
| `business-health` / `profitability-analysis` | 0.093 |
| `customer-analysis` / `profitability-analysis` | 0.093 |
| `business-health` / `executive-report` | 0.091 |
| `decision-support` / `market-analysis` | 0.091 |
| `anomaly-detection` / `ask-business-data` | 0.090 |
| `customer-analysis` / `sales-analysis` | 0.089 |
| `product-analysis` / `revenue-forecast` | 0.088 |
| `competitor-analysis` / `strategy-analysis` | 0.086 |
| `benchmark-comparison` / `decision-support` | 0.086 |
| `ask-business-data` / `customer-analysis` | 0.085 |
| `ask-business-data` / `benchmark-comparison` | 0.083 |
| `anomaly-detection` / `revenue-forecast` | 0.082 |
| `ask-business-data` / `cash-flow-analysis` | 0.082 |
| `business-health` / `product-analysis` | 0.082 |
| `ask-business-data` / `product-analysis` | 0.079 |
| `executive-report` / `industry-research` | 0.078 |
| `customer-analysis` / `revenue-forecast` | 0.077 |
| `anomaly-detection` / `business-health` | 0.076 |
| `cash-flow-analysis` / `revenue-forecast` | 0.075 |
| `company-analysis` / `executive-report` | 0.073 |
| `business-health` / `sales-analysis` | 0.070 |
| `cash-flow-analysis` / `profitability-analysis` | 0.070 |
| `business-health` / `customer-analysis` | 0.069 |
| `company-analysis` / `swot-analysis` | 0.068 |
| `ask-business-data` / `sales-analysis` | 0.068 |
| `cash-flow-analysis` / `sales-analysis` | 0.068 |
| `benchmark-comparison` / `company-analysis` | 0.063 |
| `revenue-forecast` / `sales-analysis` | 0.062 |
| `anomaly-detection` / `sales-analysis` | 0.061 |
| `business-health` / `revenue-forecast` | 0.061 |
| `market-analysis` / `sales-analysis` | 0.061 |
| `profitability-analysis` / `strategy-analysis` | 0.061 |
| `competitor-analysis` / `swot-analysis` | 0.060 |
| `ask-business-data` / `revenue-forecast` | 0.059 |
| `business-health` / `swot-analysis` | 0.057 |
| `industry-research` / `sales-analysis` | 0.057 |
| `executive-report` / `market-analysis` | 0.057 |
| `ask-business-data` / `swot-analysis` | 0.056 |
| `competitor-analysis` / `executive-report` | 0.053 |
| `benchmark-comparison` / `profitability-analysis` | 0.053 |
| `executive-report` / `profitability-analysis` | 0.052 |
| `benchmark-comparison` / `business-health` | 0.050 |
| `benchmark-comparison` / `customer-analysis` | 0.050 |
| `business-health` / `cash-flow-analysis` | 0.049 |
| `cash-flow-analysis` / `customer-analysis` | 0.049 |
| `ask-business-data` / `executive-report` | 0.049 |
| `company-analysis` / `sales-analysis` | 0.048 |
| `industry-research` / `swot-analysis` | 0.048 |
| `business-health` / `company-analysis` | 0.048 |
| `cash-flow-analysis` / `product-analysis` | 0.046 |
| `market-analysis` / `profitability-analysis` | 0.046 |
| `business-health` / `market-analysis` | 0.044 |
| `profitability-analysis` / `swot-analysis` | 0.044 |
| `anomaly-detection` / `benchmark-comparison` | 0.043 |
| `benchmark-comparison` / `market-analysis` | 0.043 |
| `decision-support` / `profitability-analysis` | 0.043 |
| `sales-analysis` / `strategy-analysis` | 0.043 |
| `business-health` / `strategy-analysis` | 0.043 |
| `sales-analysis` / `swot-analysis` | 0.043 |
| `decision-support` / `sales-analysis` | 0.042 |
| `business-health` / `decision-support` | 0.042 |
| `business-health` / `industry-research` | 0.042 |
| `cash-flow-analysis` / `strategy-analysis` | 0.042 |
| `benchmark-comparison` / `industry-research` | 0.041 |
| `cash-flow-analysis` / `swot-analysis` | 0.041 |
| `competitor-analysis` / `sales-analysis` | 0.041 |
| `ask-business-data` / `decision-support` | 0.041 |
| `cash-flow-analysis` / `decision-support` | 0.041 |
| `product-analysis` / `strategy-analysis` | 0.041 |
| `benchmark-comparison` / `competitor-analysis` | 0.040 |
| `product-analysis` / `swot-analysis` | 0.040 |
| `decision-support` / `product-analysis` | 0.039 |
| `executive-report` / `sales-analysis` | 0.038 |
| `market-analysis` / `swot-analysis` | 0.038 |
| `cash-flow-analysis` / `executive-report` | 0.036 |
| `executive-report` / `product-analysis` | 0.035 |
| `executive-report` / `revenue-forecast` | 0.034 |
| `anomaly-detection` / `executive-report` | 0.033 |
| `benchmark-comparison` / `sales-analysis` | 0.033 |
| `benchmark-comparison` / `cash-flow-analysis` | 0.032 |
| `benchmark-comparison` / `product-analysis` | 0.031 |
| `ask-business-data` / `company-analysis` | 0.030 |
| `benchmark-comparison` / `revenue-forecast` | 0.029 |
| `industry-research` / `profitability-analysis` | 0.029 |
| `anomaly-detection` / `cash-flow-analysis` | 0.028 |
| `ask-business-data` / `market-analysis` | 0.028 |
| `customer-analysis` / `strategy-analysis` | 0.028 |
| `competitor-analysis` / `profitability-analysis` | 0.028 |
| `customer-analysis` / `swot-analysis` | 0.028 |
| `ask-business-data` / `strategy-analysis` | 0.027 |
| `customer-analysis` / `decision-support` | 0.027 |
| `market-analysis` / `product-analysis` | 0.027 |
| `ask-business-data` / `industry-research` | 0.027 |
| `business-health` / `competitor-analysis` | 0.027 |
| `competitor-analysis` / `customer-analysis` | 0.027 |
| `ask-business-data` / `competitor-analysis` | 0.026 |
| `cash-flow-analysis` / `competitor-analysis` | 0.026 |
| `competitor-analysis` / `product-analysis` | 0.025 |
| `revenue-forecast` / `strategy-analysis` | 0.025 |
| `anomaly-detection` / `strategy-analysis` | 0.025 |
| `revenue-forecast` / `swot-analysis` | 0.025 |
| `anomaly-detection` / `swot-analysis` | 0.025 |
| `decision-support` / `revenue-forecast` | 0.025 |
| `anomaly-detection` / `decision-support` | 0.024 |
| `customer-analysis` / `executive-report` | 0.024 |
| `company-analysis` / `profitability-analysis` | 0.016 |
| `customer-analysis` / `market-analysis` | 0.014 |
| `cash-flow-analysis` / `market-analysis` | 0.014 |
| `market-analysis` / `revenue-forecast` | 0.013 |
| `anomaly-detection` / `market-analysis` | 0.013 |
| `industry-research` / `revenue-forecast` | 0.012 |
| `anomaly-detection` / `industry-research` | 0.012 |
| `competitor-analysis` / `revenue-forecast` | 0.012 |
| `anomaly-detection` / `company-analysis` | 0.000 |
| `anomaly-detection` / `competitor-analysis` | 0.000 |
| `cash-flow-analysis` / `company-analysis` | 0.000 |
| `cash-flow-analysis` / `industry-research` | 0.000 |
| `company-analysis` / `customer-analysis` | 0.000 |
| `company-analysis` / `product-analysis` | 0.000 |
| `company-analysis` / `revenue-forecast` | 0.000 |
| `customer-analysis` / `industry-research` | 0.000 |
| `industry-research` / `product-analysis` | 0.000 |

Description lengths (characters): `anomaly-detection` 500, `ask-business-data` 464, `benchmark-comparison` 466, `business-health` 381, `cash-flow-analysis` 447, `company-analysis` 479, `competitor-analysis` 613, `customer-analysis` 453, `decision-support` 576, `executive-report` 692, `industry-research` 614, `market-analysis` 559, `product-analysis` 447, `profitability-analysis` 442, `revenue-forecast` 480, `sales-analysis` 417, `strategy-analysis` 529, `swot-analysis` 516

#### Skill tier: 16 components, 120 pairs, mean 0.097, max 0.633

| Pair | Jaccard |
|---|---|
| `bops-industry-research` / `bops-market-analysis` | 0.633 |
| `bops-decision-support` / `bops-strategy-recommendations` | 0.345 |
| `bops-company-analysis` / `bops-market-analysis` | 0.340 |
| `bops-company-analysis` / `bops-competitor-analysis` | 0.337 |
| `bops-customer-intelligence` / `bops-product-intelligence` | 0.329 |
| `bops-company-analysis` / `bops-industry-research` | 0.306 |
| `bops-financial-analysis` / `bops-product-intelligence` | 0.295 |
| `bops-competitor-analysis` / `bops-market-analysis` | 0.280 |
| `bops-competitor-analysis` / `bops-industry-research` | 0.254 |
| `bops-customer-intelligence` / `bops-financial-analysis` | 0.253 |
| `bops-product-intelligence` / `bops-sales-intelligence` | 0.217 |
| `bops-customer-intelligence` / `bops-sales-intelligence` | 0.208 |
| `bops-anomaly-detection` / `bops-product-intelligence` | 0.187 |
| `bops-anomaly-detection` / `bops-sales-intelligence` | 0.186 |
| `bops-forecasting` / `bops-product-intelligence` | 0.186 |
| `bops-financial-analysis` / `bops-sales-intelligence` | 0.173 |
| `bops-executive-report` / `bops-swot` | 0.167 |
| `bops-forecasting` / `bops-sales-intelligence` | 0.167 |
| `bops-strategy-recommendations` / `bops-swot` | 0.163 |
| `bops-customer-intelligence` / `bops-forecasting` | 0.162 |
| `bops-decision-support` / `bops-executive-report` | 0.156 |
| `bops-anomaly-detection` / `bops-forecasting` | 0.155 |
| `bops-executive-report` / `bops-strategy-recommendations` | 0.151 |
| `bops-anomaly-detection` / `bops-financial-analysis` | 0.149 |
| `bops-financial-analysis` / `bops-forecasting` | 0.133 |
| `bops-competitor-analysis` / `bops-swot` | 0.130 |
| `bops-benchmark-comparison` / `bops-company-analysis` | 0.124 |
| `bops-anomaly-detection` / `bops-customer-intelligence` | 0.122 |
| `bops-company-analysis` / `bops-product-intelligence` | 0.121 |
| `bops-benchmark-comparison` / `bops-industry-research` | 0.109 |
| `bops-decision-support` / `bops-swot` | 0.109 |
| `bops-company-analysis` / `bops-swot` | 0.102 |
| `bops-market-analysis` / `bops-swot` | 0.100 |
| `bops-benchmark-comparison` / `bops-market-analysis` | 0.099 |
| `bops-benchmark-comparison` / `bops-competitor-analysis` | 0.098 |
| `bops-forecasting` / `bops-market-analysis` | 0.093 |
| `bops-market-analysis` / `bops-sales-intelligence` | 0.092 |
| `bops-benchmark-comparison` / `bops-swot` | 0.091 |
| `bops-industry-research` / `bops-strategy-recommendations` | 0.090 |
| `bops-market-analysis` / `bops-strategy-recommendations` | 0.089 |
| `bops-company-analysis` / `bops-data-ingestion` | 0.087 |
| `bops-data-ingestion` / `bops-industry-research` | 0.087 |
| `bops-competitor-analysis` / `bops-product-intelligence` | 0.086 |
| `bops-company-analysis` / `bops-sales-intelligence` | 0.082 |
| `bops-company-analysis` / `bops-strategy-recommendations` | 0.081 |
| `bops-company-analysis` / `bops-financial-analysis` | 0.080 |
| `bops-data-ingestion` / `bops-market-analysis` | 0.078 |
| `bops-competitor-analysis` / `bops-data-ingestion` | 0.077 |
| `bops-product-intelligence` / `bops-swot` | 0.077 |
| `bops-market-analysis` / `bops-product-intelligence` | 0.076 |
| `bops-benchmark-comparison` / `bops-data-ingestion` | 0.075 |
| `bops-anomaly-detection` / `bops-data-ingestion` | 0.075 |
| `bops-data-ingestion` / `bops-product-intelligence` | 0.074 |
| `bops-benchmark-comparison` / `bops-executive-report` | 0.073 |
| `bops-industry-research` / `bops-swot` | 0.073 |
| `bops-industry-research` / `bops-sales-intelligence` | 0.073 |
| `bops-company-analysis` / `bops-forecasting` | 0.072 |
| `bops-competitor-analysis` / `bops-forecasting` | 0.070 |
| `bops-competitor-analysis` / `bops-strategy-recommendations` | 0.070 |
| `bops-data-ingestion` / `bops-swot` | 0.069 |
| `bops-financial-analysis` / `bops-market-analysis` | 0.069 |
| `bops-industry-research` / `bops-product-intelligence` | 0.069 |
| `bops-anomaly-detection` / `bops-company-analysis` | 0.068 |
| `bops-data-ingestion` / `bops-sales-intelligence` | 0.068 |
| `bops-data-ingestion` / `bops-financial-analysis` | 0.067 |
| `bops-company-analysis` / `bops-customer-intelligence` | 0.065 |
| `bops-forecasting` / `bops-industry-research` | 0.064 |
| `bops-financial-analysis` / `bops-industry-research` | 0.063 |
| `bops-customer-intelligence` / `bops-data-ingestion` | 0.062 |
| `bops-decision-support` / `bops-industry-research` | 0.062 |
| `bops-benchmark-comparison` / `bops-product-intelligence` | 0.060 |
| `bops-company-analysis` / `bops-decision-support` | 0.059 |
| `bops-financial-analysis` / `bops-swot` | 0.058 |
| `bops-sales-intelligence` / `bops-swot` | 0.057 |
| `bops-anomaly-detection` / `bops-market-analysis` | 0.057 |
| `bops-anomaly-detection` / `bops-competitor-analysis` | 0.056 |
| `bops-customer-intelligence` / `bops-market-analysis` | 0.055 |
| `bops-data-ingestion` / `bops-executive-report` | 0.055 |
| `bops-anomaly-detection` / `bops-swot` | 0.054 |
| `bops-benchmark-comparison` / `bops-strategy-recommendations` | 0.054 |
| `bops-competitor-analysis` / `bops-customer-intelligence` | 0.054 |
| `bops-customer-intelligence` / `bops-swot` | 0.052 |
| `bops-anomaly-detection` / `bops-industry-research` | 0.051 |
| `bops-benchmark-comparison` / `bops-sales-intelligence` | 0.051 |
| `bops-competitor-analysis` / `bops-financial-analysis` | 0.050 |
| `bops-customer-intelligence` / `bops-industry-research` | 0.050 |
| `bops-decision-support` / `bops-market-analysis` | 0.050 |
| `bops-competitor-analysis` / `bops-decision-support` | 0.049 |
| `bops-competitor-analysis` / `bops-sales-intelligence` | 0.049 |
| `bops-anomaly-detection` / `bops-benchmark-comparison` | 0.048 |
| `bops-data-ingestion` / `bops-forecasting` | 0.048 |
| `bops-forecasting` / `bops-swot` | 0.046 |
| `bops-benchmark-comparison` / `bops-financial-analysis` | 0.042 |
| `bops-data-ingestion` / `bops-strategy-recommendations` | 0.042 |
| `bops-executive-report` / `bops-financial-analysis` | 0.041 |
| `bops-benchmark-comparison` / `bops-decision-support` | 0.041 |
| `bops-data-ingestion` / `bops-decision-support` | 0.040 |
| `bops-financial-analysis` / `bops-strategy-recommendations` | 0.038 |
| `bops-executive-report` / `bops-sales-intelligence` | 0.037 |
| `bops-executive-report` / `bops-market-analysis` | 0.037 |
| `bops-competitor-analysis` / `bops-executive-report` | 0.036 |
| `bops-decision-support` / `bops-financial-analysis` | 0.036 |
| `bops-executive-report` / `bops-product-intelligence` | 0.034 |
| `bops-benchmark-comparison` / `bops-customer-intelligence` | 0.034 |
| `bops-anomaly-detection` / `bops-strategy-recommendations` | 0.032 |
| `bops-product-intelligence` / `bops-strategy-recommendations` | 0.031 |
| `bops-anomaly-detection` / `bops-decision-support` | 0.030 |
| `bops-company-analysis` / `bops-executive-report` | 0.028 |
| `bops-benchmark-comparison` / `bops-forecasting` | 0.025 |
| `bops-executive-report` / `bops-industry-research` | 0.025 |
| `bops-customer-intelligence` / `bops-executive-report` | 0.022 |
| `bops-sales-intelligence` / `bops-strategy-recommendations` | 0.022 |
| `bops-customer-intelligence` / `bops-strategy-recommendations` | 0.020 |
| `bops-decision-support` / `bops-product-intelligence` | 0.020 |
| `bops-anomaly-detection` / `bops-executive-report` | 0.011 |
| `bops-forecasting` / `bops-strategy-recommendations` | 0.011 |
| `bops-decision-support` / `bops-sales-intelligence` | 0.010 |
| `bops-customer-intelligence` / `bops-decision-support` | 0.000 |
| `bops-decision-support` / `bops-forecasting` | 0.000 |
| `bops-executive-report` / `bops-forecasting` | 0.000 |

Description lengths (characters): `bops-anomaly-detection` 532, `bops-benchmark-comparison` 684, `bops-company-analysis` 911, `bops-competitor-analysis` 1065, `bops-customer-intelligence` 638, `bops-data-ingestion` 968, `bops-decision-support` 796, `bops-executive-report` 629, `bops-financial-analysis` 708, `bops-forecasting` 493, `bops-industry-research` 1158, `bops-market-analysis` 978, `bops-product-intelligence` 602, `bops-sales-intelligence` 532, `bops-strategy-recommendations` 716, `bops-swot` 724

---

## M13-MEAS-D3 — forecast method-selection stability (R-10)

| Item | Value |
|---|---|
| Status | `executed` |
| Invocation | `python tests/run_tests.py integration.test_m13_selection_stability`, which prints the per-window selection. The full record comes from `measure()` |
| Series | Demo revenue, `assets/demo-data/northwind_sales.csv`: 24 monthly periods, 2024-01..2025-12, prepared by `forecast.series.prepare` as the engine does for its `revenue` target |
| Method | Leave-one-period-out. The full series, then each truncation removing one more trailing period, down to `forecast.min_history_periods` (12). The horizon is the production default per window (`resolve_horizon`, 6). The selector is production `validate.select`, unchanged |
| Assertions | Determinism only: the same input gives the same selection. Every window meets the minimum. The windows remove exactly one more trailing period each. 5 tests, 0 failures |

**Summary.**

- 13 windows.
- 4 distinct selections: `drift`, `linear_trend`, `moving_average`, `naive`.
- 4 changes between adjacent windows.
- The literal leave-one-out pair is **stable**: 24 periods → `linear_trend`; 23 periods → `linear_trend`.

| Periods | Removed | Last period | Horizon | Held back | Selected | Candidate MAPE % (backtest) |
|---|---|---|---|---|---|---|
| 24 | 0 | 2025-12 | 6 | 6 | `linear_trend` | linear_trend 10.94, drift 13.45, naive 21.85, moving_average 23.43, seasonal_naive 38.58 |
| 23 | 1 | 2025-11 | 6 | 6 | `linear_trend` | linear_trend 9.52, drift 15.72, moving_average 21.38, naive 23.70, seasonal_naive 40.29 |
| 22 | 2 | 2025-10 | 6 | 6 | `linear_trend` | linear_trend 9.64, drift 9.66, naive 11.34, moving_average 18.63, seasonal_naive 38.96 |
| 21 | 3 | 2025-09 | 6 | 6 | `linear_trend` | linear_trend 8.00, drift 9.54, naive 17.96, moving_average 18.23, seasonal_naive 41.89 |
| 20 | 4 | 2025-08 | 6 | 6 | `moving_average` | moving_average 9.69, linear_trend 11.50, drift 15.34, naive 23.56, seasonal_naive 42.00 |
| 19 | 5 | 2025-07 | 6 | 6 | `moving_average` | moving_average 10.04, naive 10.10, drift 22.81, linear_trend 25.12, seasonal_naive 42.28 |
| 18 | 6 | 2025-06 | 6 | 6 | `moving_average` | moving_average 8.47, naive 11.28, linear_trend 21.36, drift 30.71 |
| 17 | 7 | 2025-05 | 6 | 5 | `moving_average` | moving_average 8.61, naive 13.07, linear_trend 20.66, drift 30.11 |
| 16 | 8 | 2025-04 | 6 | 5 | `naive` | naive 10.19, moving_average 13.15, linear_trend 14.17, drift 18.91 |
| 15 | 9 | 2025-03 | 6 | 5 | `naive` | naive 13.68, drift 13.99, linear_trend 14.45, moving_average 18.21 |
| 14 | 10 | 2025-02 | 6 | 4 | `drift` | drift 14.07, naive 14.89, linear_trend 15.07, moving_average 18.86 |
| 13 | 11 | 2025-01 | 6 | 4 | `drift` | drift 6.87, linear_trend 11.54, naive 16.73, moving_average 26.56 |
| 12 | 12 | 2024-12 | 6 | 4 | `linear_trend` | linear_trend 14.48, drift 17.11, naive 25.16, moving_average 28.99 |

**Observations**

1. **Selection is stable to removing the final period, but not over longer truncations.** Four methods win across
   the 13 windows, and the backtest MAPE of the winner and the runner-up is often close. At 22 periods, for example,
   it is 9.64 % against 9.66 %. That is the fragility R-10 describes: "a method may be chosen because it fits those
   six" held-back periods.
2. Recorded against R-10. It is **not a defect**: no accepted architecture requires a particular stability, and none
   is invented here. Selection, priority, holdout and configuration are unchanged.

---

## Regression-suite wall clock — an observation, not an ADR-0039 §D measurement

This is **not** M13-MEAS-D1, D2 or D3, and it adds no measurement id. ADR-0039 defines no runtime threshold for the
regression suite, so this is recorded history, never a pass/fail result. Nothing was tuned: no test, configuration or
production file was changed for speed, and the invocation is the same in every row.

| Run | Date (IST) | Tree | Invocation | Tests | Failures | Errors | Skipped | Wall clock |
|---|---|---|---|---|---|---|---|---|
| M13.1 baseline | 2026-09-18 | `990e88d` + M13 contract documents | `python tests/run_tests.py -v` | 4,684 | 0 | 0 | 26 | 850.279 s (unittest) |
| M13.1 closing run | 2026-09-18 | M13.1 working tree | `python tests/run_tests.py -v` | 4,749 | 0 | 0 | 28 | 7,694.008 s (unittest) |
| M13.1 final remediation re-time | 2026-09-18, 23:07:26–23:14:21 | M13.1 working tree plus this pass's documentation and comment edits | `python tests/run_tests.py -v` | 4,749 | 0 | 0 | 28 | **414.476 s** (unittest); 415 s between `date` stamps |

Conditions at the start of the re-time:

- Windows 11, Python 3.13.1, the *Balanced* power scheme.
- About 1.0 GB of 16 GB RAM was free, and CPU load was 14 %.
- The only other Python process was the session plugin's idle `bops-verifier` server.
- No other test run was active.

The conditions of the earlier two runs were not recorded.

**Observations**

1. **The 7,694-second closing run did not reproduce.** The re-time ran the same 4,749 tests with the same result in
   414.5 s. The 7,694-second figure is therefore recorded as an **anomalous single observation**. It is not a
   regression, and no defect is recorded for it.
2. **Wall clock varies widely on this machine.** The re-time was also about half the 850-second baseline, although it
   ran 65 more tests. The M13.1 modules take about 2.1 s in isolation. The cause of the variance is **not
   established**, and none is assigned. Host load, memory pressure, sleep and power state are all possible, and none
   was measured for the earlier runs.
3. **The history is kept.** None of the three figures is a benchmark.
