---
name: bops-financial-analysis
description: Use when interpreting computed financial results — revenue, gross profit and margin, operating profit and margin, EBITDA, working capital, days sales and payable outstanding, burn rate and runway, how margin and gross profit moved over time, the cost-to-revenue relationship, and revenue concentration risk. States plainly which of these the supplied data cannot support instead of estimating them. Reads the BusinessOps financial analysis; it does not read files, compute totals, rank products or customers, post accounting entries, execute transactions, or forecast. Trigger phrases include "are we profitable", "what is our margin doing", "cash runway", "working capital", "cost of goods", "can we afford".
---

# Financial Analysis

Report the profit and cash picture the data supports, and be equally clear about the part
it does not.

## The rule that matters most

**An unavailable financial input is never turned into an estimate.** A sales extract has no
operating expenses, no balance sheet and no cash position. The correct output for one is a
short set of margin facts plus an explicit statement that profitability below gross level,
working capital and runway are unavailable, naming the missing field for each. Supplying a
plausible operating margin would be the single most damaging thing this skill could do —
someone might make a funding decision on it.

Four states, kept distinct in every sentence:

| State | Meaning |
|---|---|
| **Actual** | Read from the data |
| **Calculated** | Derived by the engine from actuals, with its formula recorded |
| **Unavailable** | A required input is absent — the field is named |
| **Insufficient data** | The input exists but there is too little history |
| **Assumption** | Something the engine had to assume, always stated |

## What this skill does and does not do

| Does | Does not |
|---|---|
| Interpret the deterministic financial analysis | Read files, compute totals, or restate a formula |
| Report profit, margin, movement, cost ratio, working capital, cash metrics | Rank products or customers — that is another skill |
| Name every unavailable metric and its missing field | Estimate, extrapolate or "approximate" it |
| Report margin movement in percentage points | Report it as a percentage change of a percentage |
| Flag revenue concentration as a financial exposure | Assert a going-concern conclusion |
| Say what the analysis cannot see | Present gross profit as if it were the bottom line |

**This skill performs no transactions.** It does not post accounting entries, initiate
payments, execute investments, or take any consequential financial action. It reads numbers
and reports them. If asked to do otherwise, decline and say what it can do instead.

## Inputs

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import pipeline
result = pipeline.run('<path>')
financial = pipeline.analyse(result, domains=['financial'])['financial']
print(financial.status, len(financial.findings), len(financial.limitations))
"
```

`bops.analytics.financial.unavailable_summary(financial)` groups everything the engine could
not produce by why — read it before writing a word of the summary.

## Method

**1. Read the limitations before the findings.** On a typical sales file there will be more
of them than findings. That is the honest shape of the answer and it belongs near the top,
not in a closing note.

**2. Walk the profit statement in order** — revenue, gross profit, gross margin — and stop
where the data stops. Say explicitly: "operating profit, EBITDA and net margin are
unavailable because no operating-expense column is present."

**3. Report margin movement in points.** A margin moving from 37.3% to 34.4% moved 2.9
percentage points. Never describe that as a 7.8% fall in margin; the two readings are
different numbers and readers act on the wrong one.

**4. Treat concentration as a financial exposure, not a sales fact.** Where a small number
of customers or products carry most of the revenue, that is a risk statement about the cash
line, and it belongs in this analysis as well as in the sales one.

**5. Never present gross profit as profitability.** Without operating expenses there is no
statement about whether the business makes money, and saying otherwise is wrong rather than
merely incomplete.

**6. Label every statement** `[FACT]`, `[CALCULATION]`, `[INTERPRETATION]` or
`[ASSUMPTION]`. Where the engine attached an assumption — that interest and tax are
excluded from operating expenses, that a period is treated as thirty days — carry it
through; do not quietly drop it.

**7. A recommendation needs all six parts** and, for anything touching cash or funding, the
risks section must state which inputs were unavailable. If runway is unavailable, no
recommendation that depends on runway may be issued.

## Output

Order: reporting basis and currency · what the data supports · margin and its movement ·
cost relationship · cash and balance-sheet metrics where available · concentration exposure
· **what is unavailable and why** · assumptions · confidence. Any quality warning appears
before the figures, never after.

## Failure conditions

| Condition | Behaviour |
|---|---|
| Quality gate halted the run | Report the halt. Produce no financial figures |
| No revenue column | State that financial analysis is not possible; name what is missing |
| No cost column | Report revenue only; state that margin, cost ratio and profit trend are unavailable |
| Operating, cash or balance-sheet inputs absent | Report each as unavailable with the field named. Never estimate |
| Mixed currencies in the data | Report the refusal from the engine; BusinessOps does not convert |
| Fewer than four periods with revenue and cost | State that margin movement cannot be assessed |
| Asked to forecast cash, post an entry or move money | Decline; state that this skill reports, and name what it can do |

Related policy: `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md`, `${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md`,
`${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md`, the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md` (approval follows consequence).
