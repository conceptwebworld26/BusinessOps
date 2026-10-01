# Internal analytics commands

Reference for the seven commands that analyse your own spreadsheet or CSV:

`/business-health` · `/sales-analysis` · `/customer-analysis` · `/product-analysis` ·
`/profitability-analysis` · `/cash-flow-analysis` · `/ask-business-data`

Each command's file under `commands/` is its authoritative specification. This page explains them and does not
replace them. Index: [Command Reference](README.md).

## Purpose

Turn one local business file into KPIs and findings that are computed by the deterministic engine, checked by
the quality gate, and interpreted by an analytics skill. The data never leaves the machine.

## When to use which

| You want to know… | Use | Skill that interprets |
|---|---|---|
| How the business is doing overall | [`/business-health`](../../commands/business-health.md) | Cross-domain, over the four skills below |
| How sales moved, where and why the total changed | [`/sales-analysis`](../../commands/sales-analysis.md) | [`bops-sales-intelligence`](../../skills/bops-sales-intelligence/SKILL.md) |
| Who the customers are, whether they are retained, how concentrated revenue is | [`/customer-analysis`](../../commands/customer-analysis.md) | [`bops-customer-intelligence`](../../skills/bops-customer-intelligence/SKILL.md) |
| Which products and categories earn revenue and margin | [`/product-analysis`](../../commands/product-analysis.md) | [`bops-product-intelligence`](../../skills/bops-product-intelligence/SKILL.md) |
| Whether the business is profitable and what margin is doing | [`/profitability-analysis`](../../commands/profitability-analysis.md) | [`bops-financial-analysis`](../../skills/bops-financial-analysis/SKILL.md) |
| Burn, runway and working capital | [`/cash-flow-analysis`](../../commands/cash-flow-analysis.md) | [`bops-financial-analysis`](../../skills/bops-financial-analysis/SKILL.md) |
| One specific question, without knowing which command answers it | [`/ask-business-data`](../../commands/ask-business-data.md) | Routes to an existing metric or analysis |

Use `/business-health` for breadth and the domain commands for depth. Use `/ask-business-data` for one figure.

## Inputs

| Input | Commands | Notes |
|---|---|---|
| File path (`.xlsx` or `.csv`) | All | Required. If it is missing, the command asks and never picks a file |
| Question | `/ask-business-data` | Required. Passed through unchanged |
| `--sheet NAME` | `/business-health`, `/sales-analysis` | Defaults to the first sheet |
| `--currency` | `/business-health` | Overrides the Business Context currency |
| `--shareable` | `/customer-analysis` | Pseudonymises customer labels for a result leaving the business |

**Columns each command needs.** Each command needs a date column, plus:

- a revenue column for `/business-health`, `/sales-analysis`, `/profitability-analysis` and
  `/cash-flow-analysis`;
- a customer column for `/customer-analysis`;
- a product or category column for `/product-analysis`.

Optional columns switch on more analysis. Cost enables margin. Operating expense and depreciation enable operating
profit and EBITDA. Cash, receivables and payables enable the cash metrics. A missing optional column is named in
the output, never substituted.

**Business Context** (`./.businessops/business_context.json`) is optional. When it is present, it decides which KPIs
apply to your business model. When it is absent, the commands proceed with relevance filtering off and say so.

## Outputs

The standard sections are: status, reporting basis, key findings (material first), KPIs, analysis, limitations,
data quality, and evidence and provenance.

- **`/business-health`** adds the cross-domain table and the material movements across all four domains.
- **`/ask-business-data`** returns exactly one of four outcomes:
  - `answered`, with the figure and its basis;
  - `unavailable`, naming the missing field;
  - `clarification_needed`;
  - `unsupported`.

Every KPI carries a status. `unavailable` (a field is missing, and it is named) is reported separately from
`not_applicable` (the metric means nothing for this business model).

## Important behaviour

- **The quality gate halts.** A `CRITICAL` grade stops the run, and no KPI or finding is shown.
- **Mappings are confirmed, not assumed.** If a column's business role is only provisional, the command asks before
  you rely on any figure that depends on it.
- **Skills interpret and never recalculate.** Every figure comes from `lib/python/bops/`.
- **Unavailable is never turned into an estimate.** This applies especially to cash, burn, runway, working capital,
  DSO, DPO, operating profit and EBITDA, which a typical sales extract cannot support. For `/cash-flow-analysis`,
  "unavailable, and here is the field each metric needs" is the expected answer on a sales file.
- **Margin movement is in percentage points**, never a percentage change of a percentage.

## Limitations

- Internal data only. Forecasting is `/revenue-forecast`, anomalies are `/anomaly-detection`, and external comparison
  is `/benchmark-comparison`.
- Monthly granularity over the whole supplied range. `/ask-business-data` answers over the full range and says so
  when a question names a sub-period.
- Customer analysis describes observed behaviour only: never intent, motivation or future behaviour.
- No financial transaction, accounting entry or investment is ever executed. These are prohibited outright
  (`CLAUDE.md` §9).
- A `.xlsx` file with no usable Excel reader (tier 4) cannot be read. The command asks for a CSV export instead.

## Evidence and provenance

Each finding is labelled `[FACT]`, `[CALCULATION]` or `[INTERPRETATION]`, under the seven-class ledger of
[`reference/evidence-ledger.md`](../../reference/evidence-ledger.md). The reporting-basis line names the data source
and the reader tier. Data-quality warnings appear before the figures. Customer counts below the k-anonymity floor are
banded, and a result with restricted dimensions must be pseudonymised (`--shareable`) before it is exported.

## Examples

```
/business-health assets/demo-data/northwind_sales.xlsx
/sales-analysis assets/demo-data/northwind_sales.csv
/customer-analysis assets/demo-data/northwind_sales.csv --shareable
/ask-business-data "which region grew fastest" assets/demo-data/northwind_sales.csv
```

The synthetic demo dataset (`northwind_sales.csv` / `.xlsx`) and its sample Business Context are in `assets/demo-data/`. `/business-health`'s file shows how to
copy the sample context into place.

## Approvals

None are needed to run these commands: they are read-only (`CLAUDE.md` §9). Overwriting a file, exporting off the
machine or sending the result needs explicit per-action approval.

## Related

- Skills: [Skill Reference](../skills/README.md), *Internal analytics*.
- Policy: [`reference/analysis-framework.md`](../../reference/analysis-framework.md),
  [`reference/materiality-policy.md`](../../reference/materiality-policy.md),
  [`reference/output-standards.md`](../../reference/output-standards.md),
  [`reference/ambiguity-protocol.md`](../../reference/ambiguity-protocol.md).
- Records: [Milestone 6](../development/2026-09-08-internal-analytics.md) and
  [Milestone 7](../development/2026-09-09-internal-analytics-commands.md).
- Next: [Forecasting and anomalies](forecasting-and-anomalies.md) and
  [`/benchmark-comparison`](benchmark-comparison.md).
