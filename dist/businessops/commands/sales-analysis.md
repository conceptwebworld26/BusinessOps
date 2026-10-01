---
description: Analyse sales performance from a spreadsheet or CSV — revenue and order trend, which product, category, region or salesperson moved and by how much, how the revenue mix shifted, what drove the net change, and how concentrated revenue is. Use when asked how sales are doing, which region or rep is growing, what changed in revenue, or where growth came from. Reads one local file; no forecasting, no external research.
argument-hint: "[path to .xlsx or .csv] [--sheet NAME]"
---

# /sales-analysis

Produce the sales picture from one business dataset.

**This command sequences components. It contains no formula, no threshold and no policy.**
Every figure comes from the engine; every rule comes from a `reference/` document. If you
are about to write arithmetic here, it belongs in `lib/python/bops/`.

## Inputs

| Input | Required | Notes |
|---|---|---|
| Data file path | yes | `.xlsx` or `.csv`. If absent, ask — do not choose a file |
| `--sheet` | no | Worksheet name; defaults to the first sheet |

Needs a date column and a revenue column. Product, category, region, salesperson and
customer each enable a dimension; absent ones are named, never substituted.

## Steps

**1. Resolve Business Context** as usual. If absent, proceed with relevance filtering off
and say so — do not guess it.

**2. Run the command.**

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import commands
run = commands.run('sales-analysis', '<path>')
print(commands.render(run))
"
```

This performs ingestion, semantic mapping, the quality gate, KPI calculation and the
deterministic sales analytics, then renders the standard sections.

**3. Honour the quality gate.** If `run.status` is `halted`, report the halt and stop. Do
not present findings — the rendered output already handles this; do not work around it.

**4. Confirm unconfirmed mappings** before the user relies on any dependent figure.
`run.semantic_map.clarification_request()` gives the exact wording.

**5. Invoke `bops-sales-intelligence`.** Pass it `run.analyses["sales"]`. It decides which
true statements are worth reporting and adds interpretation. It recalculates nothing.

## Output

Status · reporting basis · key findings (material first) · KPIs · analysis · limitations ·
data quality · evidence and provenance. Limitations appear at the same prominence as
findings, never as a footnote.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No file given | Ask for one. Do not choose a file |
| File unreadable | Report the problem and the supported formats |
| Quality gate `CRITICAL` | Report the halt and its reasons. No KPIs, no findings |
| No date or revenue column | Report that sales analysis is not possible; name what is missing |
| A dimension is unmapped | Report it from `dimensions_skipped`; do not substitute another |
| Fewer than two periods | Report totals; state that no trend can be assessed |
| Asked to forecast or explain *why* | Out of scope — say so and report what happened instead |

## Approvals

**None required to run.** Read-only: it reads one file, computes locally, writes nothing
(the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`). Approval **is** required to overwrite a file, export off-machine,
or send the result to anyone.

## Scope

Sales only. Customer behaviour is `/customer-analysis`, per-product margin is
`/product-analysis`, and the profit statement is `/profitability-analysis`. No forecasting,
no anomaly detection, no external research or benchmarking.
