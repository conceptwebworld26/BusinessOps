---
name: bops-product-intelligence
description: Use when interpreting computed product and category results — which lines earn the most revenue and the most gross profit, how each grew or declined, how the product mix shifted, per-product margin where cost data supports it, product concentration, and which lines first appear part-way through the data. Reads the BusinessOps product analysis; it does not read files, compute totals, analyse customers, assess whole-business profitability, or forecast. Trigger phrases include "which products sell best", "what should we drop", "product margin", "which lines are declining", "what is our product mix".
---

# Product Intelligence

Judge a product on every axis the data supports, not on the one that is easiest to sort by.

## The rule that matters most

**A product is not weak because it is small.** It may be small and growing, small and the
most profitable line you sell, or small and the reason a large customer stays. Before you
describe any line as under-performing, weigh all of:

| Axis | Where it comes from |
|---|---|
| Absolute contribution | revenue and share of total |
| Growth | half-over-half movement, with its materiality verdict |
| Margin | per-product gross margin, when a cost column exists |
| Mix | share of revenue and how many points it moved |
| Time in the data | first period observed — a line present for six of twenty-four months is not comparable to one present throughout |
| Business context | what the business model makes relevant |

If cost data is absent, per-product margin is `unavailable` and you say so. Ranking by
revenue alone and calling the bottom "poor performers" is exactly the error this skill
exists to prevent.

## What this skill does and does not do

| Does | Does not |
|---|---|
| Interpret the deterministic product analysis | Read files, compute totals, or restate a formula |
| Report contribution, growth, mix, margin, concentration and first appearance | Analyse customers, regions or the whole-business P&L |
| Distinguish "sells the most" from "earns the most" | Treat revenue rank as profitability |
| State when a line simply appears later in the data | Call that a launch, a trend or an anomaly |
| Name material movements with their thresholds | Report every fluctuation as significant |

## Inputs

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import pipeline
result = pipeline.run('<path>')
products = pipeline.analyse(result, domains=['product'])['product']
print(products.status, len(products.findings), len(products.limitations))
"
```

For the full picture per line, `bops.analytics.products.profile(...)` returns one row per
product carrying revenue, share, rank, movement, margin and first period together — use it
rather than assembling those from separate findings.

## Method

**1. Check `status` and `caveats`.** No product or category column means product analysis
is not possible; say so and name the column that is missing.

**2. Report contribution before ranking.** What each line is worth, and what share of the
total it holds. Concentration matters here for the same reason it does for customers: six
products where two are 60% of revenue is a different business from six evenly balanced.

**3. Separate revenue leadership from profit leadership.** When the largest line by revenue
is not the largest by gross profit, that difference is usually the finding.

**4. Read a later first-appearance carefully.** A line whose earliest record is month seven
either started then or was not recorded before. The analysis states both readings and
chooses neither; do the same. It is **not** an anomaly, and calling it one is out of scope.

**5. Compare like with like.** A product present for half the window will show a smaller
total than one present throughout. Say so when it applies rather than letting the ranking
imply otherwise.

**6. Label every statement** `[FACT]`, `[CALCULATION]`, `[INTERPRETATION]` or
`[ASSUMPTION]`, and never assert cause. That a line grew while another fell is a
calculation; that one cannibalised the other is not in the data.

**7. A recommendation to discontinue a line needs all six parts** — evidence, rationale,
expected benefit, risks, dependencies, confidence — and the risks section must address what
the analysis cannot see: attach rate, customer relationships, and contribution to fixed
overhead. If you cannot supply all six, name what to investigate instead.

## Output

Lead with contribution and mix, then growth and decline with their materiality, then margin
where available, then concentration, then the lines that appear late. Close with the
limitations — an absent cost column is part of the answer.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No product or category column | Report that product analysis is not possible; name the missing column |
| Quality gate halted the run | Report the halt. Produce no product findings |
| No cost column | Report revenue and growth; state that margin is unavailable and what that prevents |
| Fewer than two periods | Report totals and mix only; state that no growth can be assessed |
| Asked which product to drop, on revenue alone | Give the full picture and say what the data cannot answer |
| Asked to forecast product demand | Out of scope; say so |

Related policy: `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md`, `${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md`,
`${CLAUDE_PLUGIN_ROOT}/reference/ambiguity-protocol.md`, `${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md`.
