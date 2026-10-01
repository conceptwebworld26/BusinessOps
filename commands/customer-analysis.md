---
description: Analyse the customer base from a spreadsheet or CSV — how many customers, how many are new versus returning, repeat behaviour, retention and churn, revenue contribution and concentration, which customers grew or declined, and how acquisition cohorts behave. Describes observed behaviour only, never intent or motivation. Use when asked who the best customers are, whether customers are being lost or retained, or how concentrated revenue is across them.
argument-hint: "[path to .xlsx or .csv] [--shareable]"
---

# /customer-analysis

Produce the customer picture from one business dataset.

**This command sequences components. It contains no formula, no threshold and no policy.**
Retention, churn and lifetime value come from the KPI engine; counts, cohorts and
concentration come from the analytics layer.

## Inputs

| Input | Required | Notes |
|---|---|---|
| Data file path | yes | `.xlsx` or `.csv`. If absent, ask — do not choose a file |
| `--shareable` | no | Pseudonymise customer labels for a result leaving the business |

Needs a date column and a customer column. Without a customer column the analysis is
`unavailable` — order counts are not customer counts and must not stand in for them.

## Steps

**1. Resolve Business Context.** Business model decides which customer metrics apply; a
retail dataset has no net revenue retention, and that is `not_applicable`, not missing.

**2. Run the command.**

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import commands
run = commands.run('customer-analysis', '<path>')   # presentation='shareable' if asked
print(commands.render(run))
"
```

**3. Honour the quality gate.** A halt means no customer findings at all.

**4. Invoke `bops-customer-intelligence`.** Pass it `run.analyses["customer"]`.

**5. Check `restricted_dimensions` before anyone exports.** If it is non-empty the result
is for local use and must be pseudonymised first — rerun with `presentation='shareable'`.

## Output

Status · reporting basis · key findings · KPIs · analysis · limitations · data quality ·
evidence and provenance. Cohort findings carry the data-window assumption; repeat it.

## Privacy

Never emit individual transaction rows, email addresses or contact details. Counts below
the k-anonymity floor arrive banded — report the band and say why an exact figure is not
given. Do not reconstruct one customer's activity from aggregates. Do not weaken any
sensitivity classification.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No file given | Ask for one. Do not choose a file |
| No customer column | Report that customer analysis is not possible; name what is missing |
| Quality gate `CRITICAL` | Report the halt. No customer findings |
| Fewer periods than the cohort minimum | Report counts; state that cohort behaviour cannot yet be observed |
| Customer base below the k-floor | Report banded counts and say why |
| Retention KPI `unavailable` / `not_applicable` | Report the engine's reason verbatim; never substitute a repeat rate |
| Asked why a customer left, or what they will do next | State that the data records transactions, not reasons or futures |

## Approvals

**None required to run.** Read-only. Approval **is** required to export, publish or send
the result anywhere — and a local-mode result must be pseudonymised first.

## Scope

Customers only. No intent, motivation, sentiment, propensity or future behaviour. Products
are `/product-analysis`; the profit statement is `/profitability-analysis`.
