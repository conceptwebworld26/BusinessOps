---
name: bops-sales-intelligence
description: Use when interpreting computed sales results — the revenue and order trend, which region, salesperson, product line or period moved, how the revenue mix shifted, what drove the net change, and how concentrated revenue is. Reads the BusinessOps sales analysis; it never reads spreadsheets, computes totals, analyses per-product margin, models customer behaviour, or forecasts. Trigger phrases include "how are sales doing", "which region is growing", "what changed in revenue", "who is selling most", "where did the growth come from".
---

# Sales Intelligence

Turn a computed sales analysis into observations a business owner can act on — and be
honest about the line between what the data says and what you think it means.

## What this skill does and does not do

| Does | Does not |
|---|---|
| Read the deterministic sales analysis and decide what matters | Read files, compute totals, or restate a formula |
| Separate FACT and CALCULATION from INTERPRETATION | Blend them into one confident voice |
| Name material movements and their size | Assert a *cause* the data cannot show |
| Report revenue and order trend, dimension performance, mix and concentration | Analyse per-product margin (`bops-product-intelligence`) or customer behaviour (`bops-customer-intelligence`) |
| Surface quality caveats alongside every figure | Bury caveats in a footnote |
| Say when something cannot be determined | Fill a gap with a plausible number |

**You never calculate.** Every figure comes from `lib/python/bops/analytics/`. If you find
yourself doing arithmetic, stop: the number you want either exists in the analysis or is not
available, and "not available" is a valid answer.

## Inputs

Run the pipeline, then the sales domain:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import pipeline
result = pipeline.run('<path>')
sales = pipeline.analyse(result, domains=['sales'])['sales']
print(sales.status, len(sales.findings), len(sales.limitations))
"
```

The returned `AnalysisSet` carries:

- `status` — `available`, `unavailable`, `not_applicable` or `insufficient_data`
- `findings` — each already classified `FACT` or `CALCULATION`, with its basis, the fields
  it used, the periods compared, its materiality verdict and its caveats
- `limitations` — everything the analysis could not do, and why
- `dimensions_covered` / `dimensions_skipped` — which columns existed and which did not
- `caveats` — quality warnings and unconfirmed mappings, already attached to every finding
- `metrics_used` — the KPI results consumed rather than recomputed

## Method

**1. Read `status` and `caveats` first.** If the status is not `available`, report the
reason and stop. If the run halted at the quality gate, say so and produce no findings —
do not describe what the numbers "would have shown". If a mapping is unconfirmed, every
figure that depends on it is provisional, and you say so at the point of use.

**2. Lead with material movements.** Materiality has already been judged; each finding
carries the verdict and which threshold fired. Immaterial movements are excluded from the
headline, not deleted — report them if asked.

**3. Cover what exists, name what does not.** Revenue trend and order volume; the strongest
and weakest region, salesperson, product line and category; how the mix shifted; what drove
the net movement; how concentrated revenue is. `dimensions_skipped` tells you which
dimensions were unavailable — name them rather than passing over them silently.

**4. Read a mix shift for what it is.** A share moving from 16% to 56% of revenue is a
structural change in what the business sells. Report the shift; do not attribute the
revenue or margin consequence to it unless a finding establishes that link.

**5. Label every statement.**

- `[FACT]` — read from the data (evidence class 1)
- `[CALCULATION]` — produced by the engine (class 4)
- `[INTERPRETATION]` — your reading of those (class 5)
- `[ASSUMPTION]` — anything assumed (class 6)

`FACT` and `CALCULATION` come from the analysis. `INTERPRETATION` is yours, and must name
the findings it rests on.

**6. Never assert cause.** The analysis shows that Chilled Logistics grew and that margin
fell. It does **not** show that one caused the other. Write:

> `[INTERPRETATION]` The revenue mix moved 39.6 points toward one product line while gross
> margin fell 2.9 points. Both movements are in the data; it does not establish that one
> caused the other. Per-product margin over time would test it.

Not:

> Margin fell because of the shift to Chilled Logistics.

**7. A recommendation needs all six parts.** Evidence, rationale, expected benefit, risks,
dependencies and confidence — all six or you do not issue one. Naming what to investigate
is not a recommendation and is usually more useful.

## Output

Group findings as **positive**, **negative** and **other observations**, each carrying its
label, its materiality where judged, and its basis. Lead with the movement that matters
most to the business, which is rarely the largest number. Close with the limitations — at
the same prominence as the findings, never as a footnote.

## Failure conditions

| Condition | Behaviour |
|---|---|
| `status` is `unavailable` after a quality halt | Report the halt and its reason. Produce no findings |
| No revenue or date mapping | State that sales analysis is not possible and name the missing column |
| Mapping unconfirmed | Proceed, but mark every dependent figure provisional |
| Fewer than two periods | Report totals only; state that no trend can be assessed |
| A dimension is unmapped | Report it from `dimensions_skipped`; do not substitute another |
| Asked to forecast or explain *why* | Say that this skill reports what happened; forecasting and causal attribution are out of scope |

Related policy: `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md` (provenance and confidence),
`${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md` (thresholds), `${CLAUDE_PLUGIN_ROOT}/reference/ambiguity-protocol.md`
(never guess), `${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md` (presentation).
