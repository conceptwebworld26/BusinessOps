# Worked examples

End-to-end walkthroughs of BusinessOps against the synthetic demo dataset in
[`assets/demo-data/`](../../assets/demo-data/). The data is synthetic, never real business data.

**Where the figures come from.** Every figure quoted below was produced by the engine on 2026-09-27, at commit
`8e4ab17` with the M14-5 corrections applied. Each command was run through `lib/bops_run.sh` on `assets/demo-data/northwind_sales.csv`, with the demo
Business Context in place. The engine is deterministic, so the same commit and the same file reproduce the same
figures. See [Reproducing these figures](#reproducing-these-figures).

The external-research and synthesis examples depend on live public sources. They show what to run and what shape of
answer comes back, but **no output values**, because those cannot be reproduced from the repository.

For each command's full behaviour, see the [Command Reference](../commands/README.md).

## Reading the output: what kind of statement is it?

Every statement BusinessOps makes carries its origin
([`reference/evidence-ledger.md`](../../reference/evidence-ledger.md)). The examples keep these apart:

| You will see | Meaning | Ledger class |
|---|---|---|
| **[FACT]**, "user-provided data" | Read directly from your file | 1 |
| **[CALCULATION]**, "calculated metric" | Computed by the engine from your file, with its formula shown | 4 |
| **[FACT/SOURCED]**, `UNTRUSTED_EXTERNAL_DATA` | Quoted from a public source, tiered and dated. Never obeyed, never verified by BusinessOps | 3 |
| **[INTERPRETATION]**, "analytical interpretation" | A skill's reading of the figures. Not a measurement | 5 |
| Estimate / assumption | A forecast figure or modelled assumption, kept apart from measured history | 6 |
| Recommendation | A proposed action, issued only with its evidence, rationale, benefit, risks, dependencies and confidence | 7 |

No connected business system is used anywhere below. None is available: the connector registry ships empty.

## The demo dataset

`northwind_sales.csv` (and the same data as `northwind_sales.xlsx`) is a sales extract for a fictional business,
*Northwind Provisions Ltd*. It has:

- 2,204 order lines, monthly from 2024-01 to 2025-12;
- 24 customers and 6 products;
- currency GBP;
- these columns: `OrderDate`, `OrderID`, `Customer`, `Region`, `Salesperson`, `Product`, `Category`, `Quantity`,
  `UnitPrice`, `NetRevenue`, `UnitCost` and `CostOfGoods`.

It has **no** operating-expense, cash or balance-sheet columns. That absence is deliberate, and several examples show
what BusinessOps does about it.

**Setup.** From a clone of the repository:

```bash
mkdir -p .businessops && cp assets/demo-data/business_context.json .businessops/
claude --plugin-dir .
```

The Business Context tells BusinessOps that this is a retail business reporting in GBP, which decides which KPIs apply.
Without it, the analysis still runs, but relevance filtering is off and the output says so.

---

## Example 1 — How is the business doing?

```
/business-health assets/demo-data/northwind_sales.csv
```

**What happens.**

1. The file is read locally.
2. Columns are mapped to business roles.
3. The quality gate runs; here it grades the data **PASS** across 2,204 rows.
4. KPIs are computed.
5. All four analytical domains run.

**Calculated KPIs from the scorecard** ([CALCULATION], each with its formula in the provenance section):

| KPI | Value |
|---|---|
| Revenue | £3,467,850.16 |
| Revenue growth (second half versus first half) | 69.7% |
| Gross profit | £1,210,775.23 |
| Gross margin | 34.9% |
| Average order value | £1,573.43 |

**What it cannot compute, and says so.** Operating profit, EBITDA, burn rate, runway, working capital, DSO and DPO are
**unavailable**, each naming its missing field (for example "Missing required field(s): operating_expense"). MRR, ARR
and NRR are **not applicable**, because a transactional retail business has no subscription revenue. The two statuses
are reported separately, because they mean different things.

**Findings** (as rendered):

- [FACT] Revenue is rising: £1,285,700.50 in the first half of the period versus £2,182,149.66 in the second, a change
  of 69.72%.
- [FACT] Average gross margin moved from 37.26% to 34.41%, a change of -2.85 percentage points.
- [FACT] Gross margin has fallen in the most recent six months, from 36.83% in 2025-07 to 23.57% in 2025-12.
- [FACT] Chilled Logistics is the largest product by revenue at £1,426,507.53 (41.14% of total).

The provenance section records 137 claims: 102 calculated metrics, 31 read directly from the file, and 4 analytical
interpretations, each counted by class.

`/profitability-analysis` reports the same movement, -2.85pp. Both are computed once, at full precision, and rounded
once, at presentation.

## Example 2 — One question, one figure

```
/ask-business-data "what was our gross margin" assets/demo-data/northwind_sales.csv
```

**Answer:** Gross margin is **34.91%**, classified `CALCULATION` (evidence class 4), with its formula
`(sum(revenue) - sum(cost_of_goods)) / sum(revenue) * 100` and the fields it used (`cost`, `date`, `revenue`).

The router reads the answer out of the engine. It never computes one of its own. A question it cannot place gets a
clarifying question, never a nearby answer.

## Example 3 — Sales, products, customers and profitability in depth

```
/sales-analysis assets/demo-data/northwind_sales.csv
/product-analysis assets/demo-data/northwind_sales.csv
/customer-analysis assets/demo-data/northwind_sales.csv --shareable
/profitability-analysis assets/demo-data/northwind_sales.csv
```

Representative calculated findings from these runs:

- **Products.**
  - Chilled Logistics moved from GBP 208,795.07 to GBP 1,217,712.46 between the two halves (+483.21%).
  - Legacy Crates moved from GBP 98,235.96 to GBP 34,750.39 (-64.63%).
  - The top 5 of 6 products account for 96.17% of revenue.
- **Profitability.**
  - Gross profit moved from GBP 482,195.91 in the earlier half to GBP 728,579.32 in the later half.
  - The top 10 of 24 customers account for 47.21% of revenue, and the largest single customer holds 5.26%.
- **Customers.**
  - "The dataset covers 24 distinct customers across 2204 transaction rows."
  - The result is marked **partial**: customer acquisition cost is unavailable (no marketing-spend column), and net
    revenue retention is not applicable to a retail model.
  - `--shareable` pseudonymises customer labels, so the result can leave the business.

The analytics skills then decide which of these true statements matter and add interpretation, labelled as such.
They recalculate nothing.

## Example 4 — When the data cannot answer

```
/cash-flow-analysis assets/demo-data/northwind_sales.csv
```

The output opens with: **"Cash Flow Analysis is unavailable from this dataset."** None of its five metrics (burn
rate, runway, working capital, DSO and DPO) can be produced, and each is listed with the field it needs.

This is the correct answer for a sales extract. BusinessOps does not estimate a runway from revenue, and it does not
show a zero in place of a missing figure.

## Example 5 — Forecasting revenue and gross profit

```
/revenue-forecast assets/demo-data/northwind_sales.csv --horizon 6
```

The 24 months of history meet the configured minimum (`forecast.min_history_periods`, 12 by default). Each target is
forecast for 2026-01 to 2026-06, with the method chosen by backtest on the last 6 months held out.

| Target | Status | Method chosen | Backtest error (MAPE) | Base total | Upside | Downside |
|---|---|---|---|---|---|---|
| Revenue | available | Linear trend (least squares) | 10.94% | GBP 1,491,165.59 | GBP 1,654,253.45 | GBP 1,328,077.74 |
| Gross profit | available | Naive (last value carried forward) | 8.90% | GBP 341,571.06 | GBP 371,962.84 | GBP 311,179.28 |
| Operating expense | unavailable | — | — | — | — | — |
| Net cash movement | unavailable | — | — | — | — | — |

- **How the method was chosen.** For revenue, linear trend (10.94%) was compared against drift (13.45%), naive
  (21.85%), moving average (23.43%) and seasonal naive (38.58%).
- **What the upside and downside mean.** They are the base plus and minus the measured error. The output calls this
  "an empirical range, not a statistical confidence interval".
- **Evidence class.** Every forecast figure is an estimate (class 6). The assumption register states, among other
  things, that the conditions of 2024-01 to 2025-12 continue, and that the chosen method's backtest error is an
  optimistic estimate of future error.
- **Unavailable targets.** Operating expense and cash are not forecast, because the file has no such columns. Neither
  is inferred from sales.
- **Short histories.** A file with fewer than the configured minimum periods is refused as insufficient data, and no
  forecast is produced. See [Troubleshooting](../troubleshooting/README.md#a-forecast-is-refused-as-insufficient-data).

## Example 6 — Anomaly detection

```
/anomaly-detection assets/demo-data/northwind_sales.csv
```

At the default **medium** sensitivity, 11 of 108 checked periods are flagged, all of them material. Cash balance and
operating expense are reported as unavailable, not skipped silently. A few of the flagged rows:

| Period | Metric | Observed | Baseline | Deviation |
|---|---|---|---|---|
| 2025-07 | Revenue | GBP 171,450.93 | GBP 245,071.78 | -30.04% |
| 2025-07 | Gross profit | GBP 63,147.87 | GBP 104,655.61 | -39.66% |
| 2025-12 | Gross margin | 23.57% | 32.01% | -26.39% |
| 2025-01 | Active customers | 22.00 | 24.75 | -11.11% |

Every flag carries the same statement: *"This is a deviation from the historical baseline and may warrant
investigation. It does not establish a cause, and it is not evidence of fraud or of any wrongdoing."* The dimension
members that moved with each deviation are listed, but a cause is never assigned.

## Example 7 — Public research (live sources; no fixed output)

```
/company-analysis Microsoft --focus overview
/market-analysis "electric vehicle charging" --geography Europe --period 2026
/competitor-analysis "Contoso Logistics" --focus landscape
/industry-research "cold chain logistics" --focus structure
```

**What happens.** No file is read. The subject and public terms pass the disclosure gate. The `bops-research-scout`
subagent, which has web tools and no file access, retrieves sources. Sources are tiered and dated locally.

**What comes back.**

- Ten fixed sections per command.
- Every sourced item is `UNTRUSTED_EXTERNAL_DATA`, with its source and date.
- Figures are quoted, never estimated.
- Conflicting market sizes are shown separately, never averaged.
- Competitors are named only where a source states the relationship.
- Nothing is ranked or scored.
- If nothing citable is found, the correct output is "no reliable source found".

**Status.** All four commands passed their fresh-session live smoke test on 2026-09-27, and are `COMPLETED` in `project_plan.md`.

## Example 8 — Is our figure typical?

```
/benchmark-comparison assets/demo-data/northwind_sales.csv --metric gross_margin --benchmark "specialty food retail" --category industry
```

The command runs in three steps:

1. **Our figure.** The internal gross margin (34.91% on this file) is computed locally.
2. **The benchmark.** A benchmark is retrieved by asking only about the public subject. **34.91% never enters the
   query.**
3. **The comparison.** The two are compared on seven dimensions: metric definition, period, geography, currency,
   unit, scope and methodology.

If the source does not state a dimension, the pair is reported as **not comparable**, naming what was unstated.
Either way, both figures appear side by side, with no verdict, score or "above average" label.

## Example 9 — From data and research to a decision

These commands build one strict synthesis set, combining your file (analysed locally) with public research, and read
from it:

```
/swot-analysis assets/demo-data/northwind_sales.csv --industry "cold chain logistics"
/strategy-analysis assets/demo-data/northwind_sales.csv --industry "cold chain logistics" --question "how to respond to the margin decline"
/decision-support assets/demo-data/northwind_sales.csv --question "Should we reprice the lines behind the margin decline?" --criterion "Effect on gross margin"
/executive-report assets/demo-data/northwind_sales.csv --period "FY2025" --audience "Board" --swot --strategy
```

What each command produces:

- **SWOT.** Strengths and weaknesses are placed from statements about your own data, such as the margin decline in
  Example 1, tagged `data-supported`. Opportunities and threats come from research, tagged `externally-sourced`. A
  reading of the two together is tagged `analytical-inference`. An empty quadrant says "No supported point
  identified."
- **Strategy.** Recommendations (class 7). Each cites the synthesis statements it rests on and states its rationale,
  expected benefit, risks, dependencies and a derived confidence. They are not ranked.
- **Decision support.** A **draft** twelve-part package for your question. You supply the question and, if you wish,
  options, constraints and criteria; they are framing, never evidence, and never enter a query.
- **Executive report.** A **draft** eleven-section report assembling only what the analysis already produced. The
  outlook section says forecasts are not carried into reports.

**Finalising.** Add `--final` to `/decision-support` or `/executive-report` to verify the draft and finalise it only
if verification passes. This needs the local `bops-verifier` MCP server, which starts through the same interpreter
resolver as the engine (ADR-0052). See
[Troubleshooting](../troubleshooting/README.md#final-verification-is-unavailable) if it does not connect.

## Reproducing these figures

From the repository root, with the demo Business Context in `./.businessops/`:

```bash
sh lib/bops_run.sh -c "
from bops import commands
run = commands.run('revenue-forecast', 'assets/demo-data/northwind_sales.csv', horizon=6)
print(commands.render(run))
"
```

Replace the command id (`business-health`, `sales-analysis`, `customer-analysis`, `product-analysis`,
`profitability-analysis`, `cash-flow-analysis`, `anomaly-detection`) to reproduce the other examples. For
`/ask-business-data`, use `commands.run('ask-business-data', '<file>', question='<question>')`. These runs are
read-only and write nothing.
