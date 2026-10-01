# Forecasting and anomaly commands

Reference for `/revenue-forecast` and `/anomaly-detection`. Both read your own spreadsheet or CSV and use internal
history only. The authoritative specifications are
[`commands/revenue-forecast.md`](../../commands/revenue-forecast.md) and
[`commands/anomaly-detection.md`](../../commands/anomaly-detection.md). Index: [Command Reference](README.md).

## Purpose

- **`/revenue-forecast`** projects revenue and gross profit forward. It uses a method chosen by backtest, gives base,
  upside and downside scenarios with their assumptions, and gives a measured uncertainty band. If the history cannot
  support a forecast, it refuses plainly.
- **`/anomaly-detection`** finds the periods that deviate from their own historical baseline. It reports the observed
  value, the baseline, the size of the deviation, its materiality, and the dimension members underneath it.

The skills that interpret them are [`bops-forecasting`](../../skills/bops-forecasting/SKILL.md) (reading a
`ForecastSet`) and [`bops-anomaly-detection`](../../skills/bops-anomaly-detection/SKILL.md) (reading an `AnomalySet`).

## When to use them

- "What will revenue be next quarter?", "give me a best and worst case": use `/revenue-forecast`.
- "Does anything look unusual?", "which months were odd?": use `/anomaly-detection`.
- For what happened, rather than what might happen or what stood out, use the
  [internal analytics](internal-analytics.md) commands.

## Inputs

| Command | Argument | Meaning | Default |
|---|---|---|---|
| `/revenue-forecast` | path | The `.xlsx` or `.csv` file | required |
| | `--horizon N` | Periods to forecast | `forecast.default_horizon_periods` (6) |
| | `--target NAME` | `revenue`, `gross_profit`, `operating_expense` or `cash_flow` | all four |
| | `--method NAME` | Force one method instead of backtest selection | backtest chooses |
| `/anomaly-detection` | path | The `.xlsx` or `.csv` file | required |
| | `--sensitivity` | `low`, `medium` or `high`. This moves thresholds, never the arithmetic | `anomaly.sensitivity` (medium) |
| | `--shareable` | Pseudonymise identifying dimension values | local mode |

Both need a date column. The forecast also needs the column for each target: a revenue column, a cost column for
gross profit, and operating-expense or cash columns for those two targets.

## Outputs

**Forecast, per target:**

- status;
- the selected method and why it won;
- the training and validation periods;
- the backtest error;
- the uncertainty band and its basis;
- base, upside and downside totals with their assumptions;
- the per-period forecast with its band;
- the assumption register.

**Anomaly scan:**

- which metrics were scanned and which were unavailable;
- every flagged period, with its observed value, baseline, deviation, score, detector and status (`unusual` or
  `material_anomaly`);
- the dimension members that moved with each flagged deviation.

Periods checked and found normal are kept, so "nothing found" can be told apart from "nothing looked at".

## Important behaviour

The engine's rules, as implemented in `lib/python/bops/forecast/` and `lib/python/bops/anomaly/`:

- **Minimum forecast history.** A target is forecast only when its history reaches `forecast.min_history_periods`,
  which is **12 periods** by default (`config/businessops.defaults.json`, read by `forecast/engine.py`). Below that,
  the target is `insufficient_data`, and the output gives the count and the requirement. This was re-verified on
  2026-09-27: an 8-period series is refused with "8 periods of history; 12 are required".
- **Method selection.** The candidates are naive, 3-period moving average, drift, linear trend and seasonal naive.
  Each is considered only if the history is long enough for it, and seasonal naive needs 13 monthly periods. When at
  least 6 periods are available, which the default minimum always guarantees, the candidates are backtested on
  held-out periods. The lowest-error method is chosen, and its error sets the band.
- **Horizon.** The horizon is at most half the observed history, and never more than 24 periods. A larger request is
  reduced, and the reduction is stated.
- **No inference across series.** Operating expense and cash flow are forecast only from their own columns, never
  from sales. Gaps are treated as absences, not zeros. The forecast uses the unbroken run.
- **Anomaly baseline.** Each period is scored against a trailing baseline of at least `anomaly.min_baseline_periods`
  prior periods (6 by default). Only a *triggering* detector can flag a period. A *corroborating* one is measured
  and reported but cannot flag on its own. Materiality decides what leads, not the raw score.
- **The quality gate halts both commands.** A `WARNING` grade proceeds, but its caveat travels into every scenario or
  finding.

## Limitations

- **A forecast is an estimate with a measured error, not a guarantee.** No probability or confidence interval is
  attached to any scenario.
- No external, market or economic data is used.
- Forecasts are not carried into `/executive-report`, whose outlook section says so.
- **An anomaly is a deviation, never a cause.** It is never presented as fraud, theft, manipulation or misconduct,
  and no approval unlocks that framing. Attribution locates a deviation. It does not explain it.
- No individual transactions or raw customer records appear in either output.

## Evidence and provenance

Forecast findings carry provenance class 6 (estimate / assumption), and the assumption register is recorded in
the ledger, so projected figures stay visibly separate from measured history
([`reference/evidence-ledger.md`](../../reference/evidence-ledger.md)). Anomaly findings are calculations on your
own data. Each carries the engine's note that the deviation may warrant investigation and establishes no cause.

## Examples

```
/revenue-forecast assets/demo-data/northwind_sales.xlsx --horizon 6
/revenue-forecast sales.csv --target gross_profit --horizon 3
/anomaly-detection assets/demo-data/northwind_sales.csv --sensitivity high
```

## Approvals

None are needed to run: both commands are read-only. Overwriting, exporting or sending the result needs explicit
per-action approval (`CLAUDE.md` §9).

## Related

- [Milestone 8 record](../development/2026-09-09-forecasting-anomaly.md).
- [`reference/materiality-policy.md`](../../reference/materiality-policy.md),
  [`reference/output-standards.md`](../../reference/output-standards.md).
- [Internal analytics](internal-analytics.md) · [Synthesis and reporting](synthesis-and-reporting.md).
