---
description: Run an end-to-end business health check on a sales spreadsheet or CSV — ingest, validate, compute KPIs, then summarise across sales, customers, products and the profit statement in one executive snapshot with material movements, data-quality caveats and full provenance. Use when asked how the business is doing overall, for a health check, or for a KPI scorecard from a data file.
argument-hint: "[path to .xlsx or .csv] [--sheet NAME] [--currency GBP]"
---

# /business-health

Orchestrate the BusinessOps pipeline over one business dataset and produce an executive
snapshot across all four analytical domains.

**This command sequences components. It contains no formulas, no thresholds and no policy.**
Every figure comes from the engine; every rule comes from a `reference/` document. If you
are about to write arithmetic or restate a definition here, it belongs somewhere else.

## Inputs

| Input | Required | Notes |
|---|---|---|
| Data file path | yes | `.xlsx` or `.csv`. If absent, ask — do not pick a file |
| `--sheet` | no | Worksheet name; defaults to the first sheet |
| `--currency` | no | Overrides the currency from Business Context |

Internal data only, one file, no external research.

## Steps

**1. Load Business Context and read the policy you need.**
Resolve Business Context. Read `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md` for the pipeline contract
and `${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md` for presentation. If the run produces a material
movement, also read `${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md`; if anything is ambiguous, read
`${CLAUDE_PLUGIN_ROOT}/reference/ambiguity-protocol.md`.

If Business Context is absent, **do not guess it.** Proceed with relevance filtering off,
say so in the output, and offer to set it up.

**2. State information requirements.**
A health check needs a date column and a revenue column at minimum. Cost enables profit and
margin. Customer, product, category, region and salesperson each enable a dimension of
analysis; absent ones are skipped and named.

**3. Run the command.**

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import commands
run = commands.run('business-health', '<path>')
print(commands.render(run))
"
```

This performs steps 4 through 11 of the analysis framework — ingestion with the reader tier
recorded, semantic mapping with confidence, the quality gate, KPI calculation with Business
Context relevance, materiality and the evidence ledger — and then runs all four analytical
domains and renders the executive snapshot followed by the cross-domain view.

**4. Honour the quality gate.**
If `run.status` is `halted`, the run stopped at the quality gate. **Report the halt and
stop.** Do not present KPIs, findings or conclusions — they would imply a validity the data
does not have. The rendered output already handles this correctly; do not work around it.

**5. Handle unconfirmed mappings.**
If `run.semantic_map.needs_confirmation()` is non-empty, put the confirmation question to
the user before they rely on any dependent figure. Use
`run.semantic_map.clarification_request()` for the exact wording. Never silently accept a
provisional mapping.

**6. Invoke the analysis skills for the domains that matter.**
`run.analyses` holds one `AnalysisSet` per domain. Pass the relevant ones to
`bops-sales-intelligence`, `bops-customer-intelligence`, `bops-product-intelligence` and
`bops-financial-analysis`. They decide which true statements are worth reporting and add
interpretation. **They recalculate nothing.**

**7. Present the snapshot.**
The renderer produces the required sections: reporting basis, KPI scorecard (with
`unavailable` and `not_applicable` explained separately), key findings grouped by
direction, data quality, provenance, confidence and limitations — then the cross-domain
table, the material movements across all four domains, and the limitations behind them.
Lead with any data-quality warning, before the numbers, never as a footnote.

A domain that is `unavailable` says so with the missing column named; a metric that is
`not_applicable` says so with the business-model reason. Do not invent a metric to fill a
section, and do not present an empty section as though nothing had happened.

## Trying it on the demo data

A synthetic dataset ships with the plugin. Business Context is read from
`./.businessops/business_context.json`, so to see relevance filtering in action, copy the
demo context into place first:

```bash
mkdir -p .businessops && cp assets/demo-data/business_context.json .businessops/
```

Without that step the analysis still runs, but with no business model known: relevance
filtering is off, the currency falls back to the shipped default, and the output says so
rather than guessing. That contrast is itself a useful demonstration.

## Validation

Before presenting, confirm: the quality gate was honoured; every KPI shown carries a status;
`unavailable` and `not_applicable` are distinguished; every finding is labelled `[FACT]`,
`[CALCULATION]` or `[INTERPRETATION]`; the reader tier and data source appear in the basis
line; quality warnings appear before the figures.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No file given | Ask for one. Do not choose a file |
| File unreadable or not `.xlsx`/`.csv` | Report the problem and the supported formats |
| Quality gate `CRITICAL` | Report the halt and its reasons. No KPIs, no findings |
| No date or revenue column | Report that a health check is not possible; name what is missing |
| Mapping unconfirmed | Ask before any dependent figure is relied on |
| A domain is unavailable | Report it and why; do not drop the section silently |
| No usable Excel reader (tier 4) | Ask for a CSV export |

## Approvals

**None required to run.** This command is read-only: it reads one file, computes locally,
and writes nothing. Under the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`, read-only analysis needs no approval.

Approval **is** required if the user then asks to write the report to a file that already
exists, export it off-machine, or send it to anyone.

## Scope

Cross-domain summary. For depth in one domain use `/sales-analysis`, `/customer-analysis`,
`/product-analysis`, `/profitability-analysis` or `/cash-flow-analysis`; for a single
question use `/ask-business-data`. It does not forecast, detect anomalies, perform external
research, or benchmark against an industry — those are `/revenue-forecast`,
`/anomaly-detection`, the research commands and `/benchmark-comparison`.
