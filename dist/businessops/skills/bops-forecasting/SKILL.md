---
name: bops-forecasting
description: Use when interpreting a computed forecast — projected revenue or gross profit, the base, upside and downside scenarios, the assumptions behind each, the uncertainty band and the backtest that measured it. Reads the BusinessOps forecast; it never reads spreadsheets, fits models, invents a scenario, or forecasts a metric the engine declined. Trigger phrases include "what will revenue be", "forecast next quarter", "project gross profit", "best and worst case", "how reliable is this forecast".
---

# Forecasting

Turn a computed forecast into something a business owner can plan against — while keeping
the line between what was measured and what was modelled impossible to miss.

## What this skill does and does not do

| Does | Does not |
|---|---|
| Read the deterministic forecast and explain what it assumes | Fit a model, choose a method, or do arithmetic |
| Present base, upside and downside as one set of conditional outcomes | Present any of them as what will happen |
| State the uncertainty band and where its width came from | Call that band a confidence interval |
| Report the backtest result honestly, including a poor one | Imply accuracy because a number was produced |
| Explain why a target was refused | Estimate a metric the engine marked unavailable |
| Keep forecasts visually separate from actuals | Blend a projection into a table of measured history |

**You never calculate and you never choose the method.** Every figure comes from
`lib/python/bops/forecast/`. If you find yourself extending a trend in your head, stop: the
number you want either exists in the `ForecastResult` or is not available.

## Inputs

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import pipeline
result = pipeline.run('<path>')
forecasts = pipeline.forecast(result, horizon=6)
print(forecasts.status, len(forecasts.forecasts), len(forecasts.limitations))
"
```

The returned `ForecastSet` carries, per target: `status`, `method`, `method_rationale`,
`history`, `historical_period`, `forecast_period`, `horizon`, `scenarios` (each with its
`assumption`), `assumptions` (the register), `uncertainty`, `validation`, `caveats` and
`confidence`.

## Method

**1. Lead with what the forecast is.** Every figure is an estimate — provenance class 6 —
about a period that has not happened. Say so before the first number, not after the last.

**2. Name the method and why it won.** The engine backtests every adequate method and picks
the lowest error; `method_rationale` says which and by how much. A reader who does not know
whether the line is a trend fit or last month repeated cannot judge the forecast.

**3. Report the validation result even when it is bad.** A MAPE of 24% means this method
missed by about a quarter on history it had not seen. That is the single most useful
sentence in the output. If `validation.performed` is false, say plainly that nothing was
tested and why.

Carry the selection caveat with it. The reported error is the *lowest* of every candidate
scored on that one holdout, and the method was chosen on it, so it flatters the method and
the band derived from it is correspondingly narrow. The engine says so in
`validation.statement()` and registers it as an assumption; do not drop it.

**4. Present the band as what it is.** The uncertainty band is measured error or observed
volatility, not a statistical confidence interval, and `statistical_interval` is False in
the data. Never write "95% confident" or attach a probability to a scenario.

**5. Give every scenario its assumption.** Upside and downside are meaningless without the
stated adjustment that produces them. Read them straight from the assumption register;
never invent a fourth scenario or adjust a band because it looks too narrow.

**6. Use conditional language throughout.** "Forecast", "estimated", "under these
assumptions", "scenario". Never "will be", "guaranteed", "certain" or "definitely" — the
engine lists these in `forecast.FORBIDDEN_CERTAINTY` and the tests assert against them.

**7. Explain a refusal as a fact about the data.** Below twelve periods there is no
forecast, and that is a finding, not a failure. Name the field or the history the target
needed. Operating expense is never inferred from cost of goods; cash flow is never derived
from sales.

**8. Label every statement** `[FACT]`, `[CALCULATION]`, `[INTERPRETATION]` or
`[ASSUMPTION]`. Forecast values are assumptions; the history behind them is fact.

**9. A recommendation needs all six parts**, and any recommendation resting on a forecast
must state the uncertainty band and the validation result among its risks.

## Output

Order: what was forecast and over what horizon · the method and its backtest · the
uncertainty band · base, upside and downside with their assumptions · the assumption
register · **what could not be forecast and why** · quality caveats · confidence. A quality
warning appears before the figures.

Actuals and forecasts never share a table without a column that distinguishes them.

## Failure conditions

| Condition | Behaviour |
|---|---|
| Quality gate halted the run | Report the halt. Produce no forecast |
| Fewer than the configured minimum periods (default 12) | State the count and the requirement. Offer the observed trend as description, not projection |
| Requested horizon exceeds what history supports | Report the horizon actually produced and why it was reduced |
| No date column | State that no time series can be built |
| No operating-expense column | Operating expense is unavailable. Never substitute cost of goods |
| No cash column | Cash flow is unavailable. Never derive it from revenue |
| History has gaps | Carry the engine's note: a missing period is not a zero period |
| Constant or zero-baseline series | Report that the band is a default and percentage comparisons are undefined |
| Asked for a probability, a guarantee, or a target to commit to | Decline; give the scenario range and its stated assumptions instead |
| Asked to forecast from external or market data | Out of scope — this skill forecasts internal history only |

Related policy: `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md` (class 6 and the assumption register),
`${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md`, `${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md`.
