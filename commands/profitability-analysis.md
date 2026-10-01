---
description: Analyse profitability from a spreadsheet or CSV — revenue, gross profit and margin, operating profit and margin, EBITDA and EBITDA margin, return on investment, the cost-to-revenue relationship, how margin and gross profit moved in percentage points, and profit concentration. States plainly which of these the supplied data cannot support instead of estimating them. Use when asked whether the business is profitable or what margin is doing.
argument-hint: "[path to .xlsx or .csv]"
---

# /profitability-analysis

Produce the profit picture from one business dataset, and be equally clear about its gaps.

**This command sequences components. It contains no formula, no threshold and no policy.**
Every metric comes from the Milestone 5 KPI engine; the movement figures come from the
financial analytics.

## Inputs

| Input | Required | Notes |
|---|---|---|
| Data file path | yes | `.xlsx` or `.csv`. If absent, ask — do not choose a file |

Needs a date column and a revenue column. A cost column enables gross profit, margin and
their movement. Operating profit, EBITDA and net margin additionally need an
operating-expense column, and a depreciation column for EBITDA.

## Steps

**1. Resolve Business Context** for currency and business model.

**2. Run the command.**

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import commands
run = commands.run('profitability-analysis', '<path>')
print(commands.render(run))
"
```

**3. Honour the quality gate.** A halt means no figures at all.

**4. Invoke `bops-financial-analysis`.** Pass it `run.analyses["financial"]`.
`bops.analytics.financial.unavailable_summary(...)` groups every gap by why — read it before
writing a word of summary.

## Output

Status · reporting basis · key findings · KPIs · analysis · limitations · data quality ·
evidence and provenance. On a typical sales extract there will be more limitations than
findings; that is the honest shape of the answer and it belongs near the top.

## The rule that matters most

**An unavailable financial input is never turned into an estimate.** Name the missing field
for each absent metric. Report margin movement in **percentage points**, never as a
percentage change of a percentage. Never present gross profit as profitability — without
operating expenses there is no statement about whether the business makes money.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No file given | Ask for one. Do not choose a file |
| No revenue column | Report that profitability analysis is not possible; name what is missing |
| Quality gate `CRITICAL` | Report the halt. No figures |
| No cost column | Report revenue only; state that margin, cost ratio and profit trend are unavailable |
| Operating or depreciation inputs absent | Report each metric as unavailable with its field named. Never estimate |
| Mixed currencies | Report the engine's refusal; BusinessOps does not convert |
| Fewer than four periods with revenue and cost | State that margin movement cannot be assessed |
| Asked to post an entry, move money or execute an investment | Decline; this command reports and nothing more |

## Approvals

**None required to run.** Read-only. This command performs no transaction, posts no
accounting entry and executes no investment — those are prohibited outright
(the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`), not gated.

## Scope

Profitability only. Cash, runway and working capital are `/cash-flow-analysis`; product and
customer rankings are their own commands. No forecasting, no external benchmarking.
