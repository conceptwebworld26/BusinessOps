---
description: Answer one plain-language question about a business spreadsheet or CSV by routing it to the metric or analysis that already computes it — "what was our gross margin", "which region grew fastest", "which products contributed most", "how many customers bought more than once", "why is runway unavailable". Use when the user has a question but does not know which analysis command to run. Answers only from the supplied file; never estimates, forecasts or researches.
argument-hint: "<question> [path to .xlsx or .csv]"
---

# /ask-business-data

Answer one question from the user's own data, or say precisely why it cannot be answered.

**This command routes; it does not compute.** The question is matched to a metric in the
KPI catalogue or to a dimension and intent the analytics layer already produces, and the
answer is *read out* of that result. There is no path here by which a question produces a
number the deterministic engine did not produce.

## Inputs

| Input | Required | Notes |
|---|---|---|
| Question | yes | One question. If absent or empty, ask for one |
| Data file path | yes | `.xlsx` or `.csv`. If absent, ask — do not choose a file |

## Steps

**1. Run the command.** Pass the question through unchanged; do not rephrase it into what
you think it should have been.

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import commands
run = commands.run('ask-business-data', '<path>', question='<question>')
print(commands.render(run))
"
```

**2. Report the outcome as given.** The router returns exactly one of four:

| Outcome | What to do |
|---|---|
| `answered` | Give the figure with its basis, and label it `[CALCULATION]` or `[FACT]`. Carry every caveat |
| `unavailable` | Report the engine's own reason verbatim, naming the missing field. Do not substitute a related metric |
| `clarification_needed` | Ask the listed clarifying question. Do not pick a candidate yourself |
| `unsupported` | Say which capability was asked for and which command owns it. Estimate nothing |

**3. Never guess a column.** If the concept needs a role the semantic map does not carry,
the answer is `unavailable` naming the role — not a substitution from a similar column.

**4. Offer the fuller analysis.** A routed answer is one figure. If the user wants the
picture around it, name the command that produces it (`/sales-analysis`,
`/customer-analysis`, `/product-analysis`, `/profitability-analysis`,
`/cash-flow-analysis`) rather than assembling one here.

## Output

Status · the answer with its basis, formula or primitive, fields used and caveats · the
other readings of the same question, where the router found them · reporting basis · data
quality.

## Limits to state, not work around

- **Whole-period only.** Figures cover the entire supplied range at monthly granularity. A
  question naming "last quarter" is answered over the full range with that stated — never
  silently treated as if the sub-period had been computed.
- **Interpretation is not this command's job.** It returns calculated results; the analysis
  skills interpret.
- **No forecasting, anomaly detection or external research.** Recognised and refused by
  name, never approximated.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No question | Ask for one |
| No file | Ask for one. Do not choose a file |
| Question matches nothing | Report clarification with what *can* be asked; never answer a nearby question instead |
| Question matches several metrics equally | Ask which one is meant |
| Question names two dimensions | Ask for one at a time |
| Quality gate `CRITICAL` | Report the halt. Answer nothing |
| Question asks for a forecast, an anomaly or a competitor | Refuse by name and say which command owns it |

## Approvals

**None required to run.** Read-only, one local file, nothing written.

## Scope

One question, one file, internal data only. It does not chain questions, remember previous
answers, or perform any analysis the existing commands do not already perform.
