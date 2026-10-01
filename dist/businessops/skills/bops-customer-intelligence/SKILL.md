---
name: bops-customer-intelligence
description: Use when interpreting computed customer results — how many customers there are, how many are new versus returning, retention and churn, revenue concentration across the customer base, which customers grew or declined, and how acquisition cohorts behave over time. Describes observed behaviour only, never inferred intent, motivation or propensity. Reads the BusinessOps customer analysis; it does not read files, compute totals, rank products, analyse margin, or forecast. Trigger phrases include "who are our best customers", "are we losing customers", "customer retention", "how concentrated is our revenue", "are customers coming back".
---

# Customer Intelligence

Describe what customers **did** — appeared, returned, grew, stopped. Never what they wanted,
felt, intended or are likely to do. A sales file records transactions; it does not record
motivation, and inventing one would be the most damaging thing this skill could do.

## What this skill does and does not do

| Does | Does not |
|---|---|
| Report counts, shares, retention, churn, concentration and cohort behaviour | Infer intent, loyalty, satisfaction or propensity |
| Read the deterministic customer analysis | Read files or compute totals |
| Treat "new" and "returning" as observations bounded by the data window | Claim a customer is new when the file simply starts too late |
| Handle customer identifiers conservatively | List individual transactions or contact details |
| Say when the customer base is too small to describe safely | Report a group of two as if it were a cohort |
| Distinguish retention from concentration | Conflate "customers stay" with "revenue is safe" |

**You never calculate.** Retention, churn and lifetime value come from the KPI engine;
counts, cohorts and concentration come from `lib/python/bops/analytics/customers.py`.

## Inputs

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import pipeline
result = pipeline.run('<path>')
customers = pipeline.analyse(result, domains=['customer'])['customer']
print(customers.status, len(customers.findings), len(customers.limitations))
"
```

The `AnalysisSet` carries `status`, `findings` (each `FACT` or `CALCULATION`, with basis,
fields used, periods and caveats), `limitations`, `restricted_dimensions` (the columns that
identify individuals) and `presentation` (`local` or `shareable`).

## Method

**1. Check `status` first.** `unavailable` with no customer column means customer analysis
is not possible — say that and name the missing column. Do not substitute order counts for
customer counts; they are different quantities.

**2. Report the population before the individuals.** How many customers, over how many
rows, how uneven the distribution is. A median far below the mean is the shape of a
concentrated base, and it is more decision-relevant than any single customer's name.

**3. Read retention and concentration as separate questions.** A business can retain every
customer and still be dangerously exposed if two of them are half the revenue. Report both;
never let one stand in for the other.

**4. Respect the cohort caveat.** A customer trading before the file begins is
indistinguishable from a genuinely new one, so the earliest cohort is overstated and its
retention understated. Every cohort finding carries that assumption — repeat it, do not
strip it.

**5. Handle identity conservatively.** Name customers only when the analysis did — check
`dimension_redacted` on each finding. If `restricted_dimensions` is non-empty the result is
for local use; say so before anyone exports it. Never list individual transactions, email
addresses or contact details, and never reconstruct one customer's activity from
aggregates.

**6. Do not make customer-level recommendations on thin evidence.** "This customer's
revenue fell 40%" over two months of data is a movement, not a relationship problem. Where
the base is below the k-anonymity floor, the counts you receive are banded — report the
band, and say why an exact figure is not being given.

**7. Label every statement** `[FACT]`, `[CALCULATION]`, `[INTERPRETATION]` or
`[ASSUMPTION]`, and never assert cause. "Revenue from the top ten customers rose" is a
calculation; "our account management improved" is not in the data.

## Output

Lead with the population and its concentration, then retention and churn, then the material
customer movements, then cohorts. Close with limitations at the same prominence as the
findings — an unavailable acquisition cost is part of the answer, not an omission.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No customer column | Report that customer analysis is not possible and name what is missing |
| Quality gate halted the run | Report the halt. Produce no customer findings |
| Fewer periods than the cohort minimum | Report the counts; state that cohort behaviour cannot yet be observed |
| Customer base below the k-anonymity floor | Report banded counts and say why |
| Retention KPI `unavailable` or `not_applicable` | Report the engine's reason verbatim; do not substitute a repeat-purchase rate for it |
| Asked why a customer left | State that the data records transactions, not reasons |

Related policy: `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md`, `${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md`,
`${CLAUDE_PLUGIN_ROOT}/reference/ambiguity-protocol.md`, `${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md`.
