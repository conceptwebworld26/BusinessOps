# Command Reference

The index of BusinessOps's slash commands. Each command's full specification (its inputs, steps, failure
conditions and approvals) lives in its own file, `commands/<name>.md`, which is authoritative. The family
pages linked below are reference pages: they explain when to use each command, what goes in and comes out,
and where its limits are. They do not repeat the specification.

*Inventory verified against `commands/` on 2026-09-27 (M14-3).* Status for each command is owned by
[`project_plan.md`](../../project_plan.md).

## At a glance

| | Count |
|---|---|
| Command files in `commands/` | 18 |
| **User-facing commands** | **18** |
| Internal test harness (not shipped) | 1 (`dev/harness/retrieval-slice.md`) |

Every command is a thin orchestrator. It sequences engine calls and skills and computes nothing itself
(ADR-0003, ADR-0012). The plugin-qualified form also works, for example `/businessops:sales-analysis`.

## User-facing commands

The argument hints below are summaries. The exact hint for each command is in the frontmatter of its file.

### Your own data: internal analytics

Reference page: **[Internal analytics](internal-analytics.md)**. Each command reads one local `.xlsx` or `.csv`
file, runs the deterministic pipeline and quality gate, and hands the result to its skill. No external research.

| Command | Answers | Arguments | Skill |
|---|---|---|---|
| [`/business-health`](../../commands/business-health.md) | How is the business doing overall, across sales, customers, products and the profit statement? | `[file] [--sheet NAME] [--currency GBP]` | Cross-domain, over the four analytics skills |
| [`/sales-analysis`](../../commands/sales-analysis.md) | Revenue and order trend; which dimension moved; mix; contribution; concentration | `[file] [--sheet NAME]` | `bops-sales-intelligence` |
| [`/customer-analysis`](../../commands/customer-analysis.md) | Population, new versus returning, retention, churn, concentration, cohorts | `[file] [--shareable]` | `bops-customer-intelligence` |
| [`/product-analysis`](../../commands/product-analysis.md) | Contribution, growth, mix, per-product margin, concentration, first appearance | `[file]` | `bops-product-intelligence` |
| [`/profitability-analysis`](../../commands/profitability-analysis.md) | The profit walk as far as the data goes, and margin movement in points | `[file]` | `bops-financial-analysis` |
| [`/cash-flow-analysis`](../../commands/cash-flow-analysis.md) | Burn, runway, working capital, DSO, DPO, or precisely why each is unavailable | `[file]` | `bops-financial-analysis` |
| [`/ask-business-data`](../../commands/ask-business-data.md) | One question, routed to the metric or analysis that already computes it | `<question> [file]` | Routing over internal analytics |

### Your own data: forecasting and anomalies

Reference page: **[Forecasting and anomalies](forecasting-and-anomalies.md)**.

| Command | Answers | Arguments | Skill |
|---|---|---|---|
| [`/revenue-forecast`](../../commands/revenue-forecast.md) | Backtested forecast of revenue and gross profit, with base, upside and downside scenarios, assumptions, band and validation | `[file] [--horizon 6] [--target revenue]` | `bops-forecasting` |
| [`/anomaly-detection`](../../commands/anomaly-detection.md) | Periods deviating from their own baseline, with the baseline, deviation, materiality and contributors | `[file] [--sensitivity medium] [--shareable]` | `bops-anomaly-detection` |

These nine data commands (this table and the one above) are the ones declared in `lib/python/bops/commands/registry.py`.
They are machine-readable through `bops.commands.catalogue_as_dict()` and `bops.commands.mapping_table()`.

### Public research

Reference page: **[External research](external-research.md)**. These commands read **no** business file. Each
query is built from public terms, passes the disclosure gate, and is retrieved by the `bops-research-scout`
subagent.

| Command | Answers | Arguments | Skill |
|---|---|---|---|
| [`/company-analysis`](../../commands/company-analysis.md) | What one named company does, its dated developments, positioning, publicly reported figures and risks | `<company> [--focus overview\|developments\|positioning\|full] [--industry] [--market] [--period] [--window]` | `bops-company-analysis` |
| [`/market-analysis`](../../commands/market-analysis.md) | One named market: definition, size and growth where a source states it, trends, drivers, risks | `<market> [--focus overview\|size-growth\|trends\|drivers-risks\|full] [--geography] [--industry] [--period] [--window]` | `bops-market-analysis` |
| [`/competitor-analysis`](../../commands/competitor-analysis.md) | Who competes with one named company and on what evidence, compared without ranking | `<company> [--competitors "A, B"] [--focus landscape\|comparison\|positioning\|developments\|full] [--geography] [--industry] [--period] [--window]` | `bops-competitor-analysis` |
| [`/industry-research`](../../commands/industry-research.md) | One named industry as a system: boundaries, size, trends, drivers, risks, structure, with nothing scored | `<industry> [--focus overview\|size-growth\|trends\|drivers-risks\|structure\|full] [--geography] [--period] [--product-category] [--window]` | `bops-industry-research` |

**Plan status.** All four are `COMPLETED` in `project_plan.md`. Each passed its fresh-session live smoke test on
2026-09-27 (M14-6), with the scout's reply reaching the parser byte for byte (ADR-0053). Milestone 9 stays
`IN PROGRESS` for its other planned rows.

### Your figure against a public benchmark

Reference page: **[`/benchmark-comparison`](benchmark-comparison.md)**.

| Command | Answers | Arguments | Skill |
|---|---|---|---|
| [`/benchmark-comparison`](../../commands/benchmark-comparison.md) | Is our figure typical? One internal figure set beside one public benchmark, joined locally | `<file> --metric NAME --benchmark "<public subject>" [--category] [--industry] [--geography] [--period]` | `bops-benchmark-comparison` |

### Synthesis and reporting

Reference page: **[Synthesis and reporting](synthesis-and-reporting.md)**. Each command builds one strict
synthesis set from your file (analysed locally) and optional public research, and hands it to its skill.

| Command | Answers | Arguments | Skill |
|---|---|---|---|
| [`/swot-analysis`](../../commands/swot-analysis.md) | Strengths, weaknesses, opportunities and threats, each point tagged and traced | `<file> [--market] [--industry] [--competitor] [--geography] [--period]` | `bops-swot` |
| [`/strategy-analysis`](../../commands/strategy-analysis.md) | Class-7 recommendations with evidence, rationale, benefit, risks, dependencies and derived confidence | `<file> [research subjects] [--question "<text>"]` | `bops-strategy-recommendations` |
| [`/decision-support`](../../commands/decision-support.md) | A draft twelve-part decision package for one decision you name | `<file> --question "<text>" [--objective] [--option]... [--constraint]... [--criterion]... [--no-status-quo] [research subjects] [--final]` | `bops-decision-support` |
| [`/executive-report`](../../commands/executive-report.md) | A draft eleven-section report assembling what has already been analysed | `<file> [--period] [--audience] [--objective] [--question]... [--constraint]... [--swot] [--strategy] [--decision "<text>"]... [research subjects] [--final]` | `bops-executive-report` |

`--final` verifies a draft through the `bops-analysis-verifier` subagent and finalises it only on a passed
verification. On a machine that provides Python 3 only as `python3`, the verifier server cannot start, so
`--final` is unavailable there (Known issue **R-13** in `project_plan.md`).

## Behaviour common to every command

- **Coverage first.** Every data command reports a coverage verdict (`complete`, `partial`, `unavailable` or
  `not_applicable`) before its numbers. A command whose whole subject is absent says so, rather than filling
  the space with adjacent findings.
- **The quality gate halts.** A `CRITICAL` data-quality grade stops the run before any figure is presented.
- **Read-only by default.** No command needs approval to run. Overwriting a file, exporting off the machine or
  sending anything needs explicit per-action approval (`CLAUDE.md` §9). Writing a **new** file into
  `./businessops-output/` does not need approval.
- **Internal data stays local.** No command sends a figure, band or description from your data to an external
  service. Research queries are built from public terms only (ADR-0009, ADR-0050).

## Internal: not a user command

Since BusinessOps M3 the harness is in `dev/harness/`, outside `commands/`: it is not auto-discovered, not part
of the installable plugin and not shown in the `/` menu.

| Command file | Classification | Evidence |
|---|---|---|
| [`dev/harness/retrieval-slice.md`](../../dev/harness/retrieval-slice.md) | **Internal test harness** (M9-B integration harness) | Its frontmatter describes it as an "internal retrieval vertical slice / integration harness" that "answers no business question". It carries `disable-model-invocation: true`, so the model never selects it. `project_plan.md` (M9-B) records that it is "not a research capability". `docs/testing/measurements.md` excludes it from the model-invocable set, and coverage-matrix row S4-15 tests its negative path |

The file is auto-discovered like any other command, so the harness can still be typed by hand, but it is not a
supported way to research anything. Use the four public-research commands instead. It is deliberately left out
of the user-facing count and of `README.md`.

## Design count

`architecture.md` §1 draws the orchestration layer as "commands/ (17)". That count comes from the Revision 2
design and never had an enumerated list behind it (D-06). `architecture.md` §13 records the shipped state: 19
command files. This page is the enumerated inventory.
