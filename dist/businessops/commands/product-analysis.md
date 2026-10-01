---
description: Analyse products and categories from a spreadsheet or CSV — revenue contribution and share, growth and decline with materiality, mix shift, per-product gross margin where cost data allows, ranking, the split between the revenue leader and the profit leader, concentration, and lines first observed part-way through the data. Use when asked which products sell best, which are declining, what the product mix is, or which lines actually earn money.
argument-hint: "[path to .xlsx or .csv]"
---

# /product-analysis

Produce the product picture from one business dataset.

**This command sequences components. It contains no formula, no threshold and no policy.**

## Inputs

| Input | Required | Notes |
|---|---|---|
| Data file path | yes | `.xlsx` or `.csv`. If absent, ask — do not choose a file |

Needs a date column and a product or category column. A cost column enables per-product
margin; without one, margin is `unavailable` and ranking by revenue alone must not be
presented as a verdict on which lines are worth selling.

## Steps

**1. Resolve Business Context.** Business model decides which product metrics apply —
inventory turnover means nothing to a consultancy.

**2. Run the command.**

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import commands
run = commands.run('product-analysis', '<path>')
print(commands.render(run))
"
```

For the full per-line picture, `bops.analytics.products.profile(run.result.dataset,
run.result.semantic_map)` returns revenue, share, rank, movement, margin and first period
together — use it rather than assembling those from separate findings.

**3. Honour the quality gate.** A halt means no product findings at all.

**4. Invoke `bops-product-intelligence`.** Pass it `run.analyses["product"]`.

## Output

Status · reporting basis · key findings · KPIs · analysis · limitations · data quality ·
evidence and provenance.

## What this command must not say

A product is not weak because it is small. Before describing any line as under-performing,
weigh absolute contribution, growth, margin, mix, and how long it has been in the data.
Never assert that customers dislike a product, that a line will fail, or that it should be
discontinued — none of that is in a sales file. A line whose first record is later than the
file's opening period either launched then or was not recorded before; state both readings
and choose neither. That is **not** an anomaly, and calling it one is out of scope.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No file given | Ask for one. Do not choose a file |
| No product or category column | Report that product analysis is not possible; name what is missing |
| Quality gate `CRITICAL` | Report the halt. No product findings |
| No cost column | Report revenue and growth; state that margin is unavailable and what that prevents |
| Fewer than two periods | Report totals and mix; state that no growth can be assessed |
| Asked which product to drop, on revenue alone | Give the full picture and say what the data cannot answer |
| Asked to forecast product demand | Out of scope; say so |

## Approvals

**None required to run.** Read-only. Approval **is** required to overwrite, export or send.

## Scope

Products and categories only. Customers are `/customer-analysis`; the profit statement is
`/profitability-analysis`. No forecasting, no anomaly detection, no external research.
