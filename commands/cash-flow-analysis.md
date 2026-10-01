---
description: Analyse cash and working capital from a spreadsheet or CSV — burn rate, runway, working capital, days sales outstanding and days payable outstanding, with the profitability context around them. Most sales extracts carry none of the required cash or balance-sheet fields, so the command's main job is stating precisely which metrics are unavailable and what field each one needs. Use when asked about runway, burn, cash position or working capital.
argument-hint: "[path to .xlsx or .csv]"
---

# /cash-flow-analysis

Report the cash position the data supports — and, far more often, say exactly why it cannot.

**This command sequences components. It contains no formula, no threshold and no policy.**

## Inputs

| Input | Required | Notes |
|---|---|---|
| Data file path | yes | `.xlsx` or `.csv`. If absent, ask — do not choose a file |

| Metric | Needs |
|---|---|
| Burn rate | date, revenue, cost, operating expense |
| Runway | the above plus a cash-balance column |
| Working capital | current assets and current liabilities |
| Days sales outstanding | receivables, revenue, date |
| Days payable outstanding | payables, cost, date |

A sales extract has none of these. **That is the expected answer, not a failure**, and it
must be reported as unavailability with the field named — never as a zero, a blank, or an
estimate.

## Steps

**1. Resolve Business Context** for currency and reporting period.

**2. Run the command.**

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import commands
run = commands.run('cash-flow-analysis', '<path>')
print(commands.render(run))
"
```

**3. Honour the quality gate.** A halt means no figures at all.

**4. Invoke `bops-financial-analysis`.** Pass it `run.analyses["financial"]`.

**5. Say whether the answer is complete, partial or unavailable.** If some cash metrics
computed and others did not, say which and why — a partial cash picture read as a complete
one is how a funding decision goes wrong.

## Output

Status · reporting basis · key findings · KPIs · analysis · limitations · data quality ·
evidence and provenance.

## Never fabricate

Cash balance, burn rate, runway, working capital, DSO and DPO are **never** inferred,
approximated or derived from a proxy. If runway is unavailable, no statement that depends
on runway may be made. This command performs no financial transaction and gives no
investment-execution instruction.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No file given | Ask for one. Do not choose a file |
| No cash or balance-sheet columns | State that cash-flow analysis is unavailable, and name the field each metric needs |
| Some cash fields present | State clearly that the picture is partial, and which parts are missing |
| Quality gate `CRITICAL` | Report the halt. No figures |
| Fewer periods than a burn calculation needs | Report insufficient history, not a zero burn |
| Asked to move money, pay an invoice or invest | Decline; this command reports and nothing more |
| Asked to forecast cash | Out of scope here — `/revenue-forecast` forecasts cash flow, and only where a cash-flow column exists |

## Approvals

**None required to run.** Read-only. Financial transactions are prohibited outright, not
gated (the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`).

## Scope

Cash and working capital only. Profit and margin are `/profitability-analysis`. No
forecasting, no scenario modelling, no external benchmarking.
