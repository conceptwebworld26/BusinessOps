---
description: Forecast revenue and gross profit from a spreadsheet or CSV — a backtested method chosen from the history, base, upside and downside scenarios with the assumption behind each, a measured uncertainty band, and a plain refusal where history is too short or the field is absent. Operating expense and cash flow are forecast only when those columns exist; neither is ever inferred from sales. Use when asked what revenue will be, to project next quarter, or for a best and worst case.
argument-hint: "[path to .xlsx or .csv] [--horizon 6] [--target revenue]"
---

# /revenue-forecast

Produce a forecast from one business dataset — or say precisely why one cannot be produced.

**This command sequences components. It contains no formula, no threshold and no policy.**
The method is chosen by backtest in `lib/python/bops/forecast/`, the minimum history comes
from configuration, and the assumption register comes from the engine. If you are about to
extend a trend by hand, stop: the number belongs to the engine or does not exist.

## Inputs

| Argument | Meaning | Default |
|---|---|---|
| path | The `.xlsx` or `.csv` to read | required |
| `--horizon N` | Periods to forecast | `forecast.default_horizon_periods` (6) |
| `--target NAME` | `revenue`, `gross_profit`, `operating_expense`, `cash_flow` | all four |
| `--method NAME` | Force one method instead of backtest selection | backtest chooses |

## Sequence

1. Run the pipeline (`pipeline.run`) — ingestion, normalisation, mapping, quality gate,
   KPIs. **A `CRITICAL` grade halts here** and no forecast is produced.
2. Run `pipeline.forecast(result, horizon=...)`. This resolves the horizon against the
   available history, backtests every adequate method, selects the lowest-error one,
   builds the three scenarios and registers every assumption.
3. Render with `commands.render`. Present the caveats before the figures.
4. Hand the `ForecastSet` to **`bops-forecasting`** for interpretation.

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import commands
run = commands.run('revenue-forecast', '<path>', horizon=6)
print(commands.render(run))
"
```

## What it reports

Per target: status, the selected method and why it won, the training and validation
periods, the backtest error, the uncertainty band and its basis, base/upside/downside
totals with their assumptions, the per-period forecast with its band, and the assumption
register.

## What it does not do

- Forecast below the configured minimum history (default 12 periods) — it refuses instead.
- Forecast further than half the observed history, or beyond 24 periods.
- Infer operating expense from cost of goods, or cash flow from revenue.
- Attach a probability or a confidence interval to any scenario.
- Use external, market or economic data. This is internal history only.
- Detect anomalies (`/anomaly-detection`) or analyse historical profit
  (`/profitability-analysis`).

## Failure conditions

| Condition | Behaviour |
|---|---|
| Quality `CRITICAL` | Halt; report the reason; no forecast |
| Quality `WARNING` | Proceed; the caveat travels into every scenario and lowers confidence |
| No date or revenue column | `unavailable`, naming the missing role |
| History shorter than the minimum | `insufficient_data` with the count and the requirement |
| Horizon larger than history supports | Produce the supported horizon; state the reduction |
| History has gaps | Forecast from the unbroken run; report the gaps as genuine absences |
| No target could be forecast | The set reports `insufficient_data`; every limitation names its field |

Related: `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md` (class 6, assumption register),
`${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md`, `skills/bops-forecasting/SKILL.md`.
