# BusinessOps

**Business intelligence, strategic analysis and decision support, as a Claude Code plugin.**

BusinessOps turns your business spreadsheets and reliable public research into KPIs, analysis, forecasts, anomaly reports
and decision-ready drafts.

- **Figures come from code.** Every figure is computed by a deterministic Python engine, never by model arithmetic.
- **Claims carry their evidence.** Every claim says where it came from and how confident BusinessOps is in it.

It is not a general-purpose chatbot. It is a structured decision-support system with written rules about what it will
and will not claim. When the data cannot support an answer, it says so.

---

## What BusinessOps does

- **Analyses your own data.** It reads a spreadsheet or CSV, checks its quality, and reports on:
  - KPIs;
  - sales;
  - customers;
  - products;
  - profitability;
  - cash and working capital.
- **Forecasts and finds anomalies.** It forecasts revenue and gross profit with backtested methods and measured
  uncertainty. It flags periods that deviate from their own history.
- **Researches public information.** It covers companies, markets, competitors and industries, using public sources
  only. Every figure is quoted from a dated, cited source, never estimated.
- **Compares against benchmarks locally.** Your figure is computed on your machine. Only public terms go into the
  benchmark query.
- **Synthesises decision material.** It builds SWOT analyses, strategy recommendations, decision packages and executive
  reports, all assembled from evidence that has already been established.
- **Separates fact from judgement.** Output distinguishes facts, calculations, interpretations and recommendations, and
  states confidence and limitations.

## Who it is for

- business owners and founders;
- executives, such as the CEO, COO and CFO;
- FP&A teams;
- business analysts;
- sales and operations managers;
- consultants.

It is aimed at small and mid-sized businesses whose data lives in spreadsheets and exports.

## How it works

1. **Understand the question and the business.** It uses the question you ask and your optional
   [Business Context](#business-context). If the question is ambiguous, it asks rather than guesses.
2. **Read and validate the data.**
   - Your file is read without being modified.
   - Its columns are mapped to business meaning.
   - It passes a data-quality gate. A critical quality problem stops the analysis rather than producing a
     plausible-looking wrong answer.
3. **Calculate deterministically.** KPIs, analytics, forecasts and anomaly baselines are computed by the engine.
4. **Research publicly, when the command calls for it.** Queries are built from public terms and pass a disclosure
   gate. Retrieved content is treated as untrusted and is tiered and dated.
5. **Separate what is known from what is inferred.** Each claim is classed: your data, a calculation, a public source,
   an interpretation, an assumption or a recommendation.
6. **Produce a decision-ready result.** It states what is supported, what is not, and how confident BusinessOps is.
7. **Leave decisions to you.** Recommendations are drafts. BusinessOps never executes an action. Anything consequential
   needs your explicit approval (see [Approval and write safety](#approval-and-write-safety)).

## Key capabilities

The 18 user commands below are backed by 16 skills and 2 subagents.

**Your own data** (a spreadsheet or CSV):

| Command | What it answers |
|---|---|
| `/business-health` | An end-to-end snapshot across sales, customers, products and profit, with material movements |
| `/sales-analysis` | Revenue and order trend, which product, region or salesperson moved, mix shift and concentration |
| `/customer-analysis` | Customer counts, new versus returning, retention and churn, concentration, growth and decline |
| `/product-analysis` | Contribution, growth and decline, mix shift, and per-product margin where cost data allows |
| `/profitability-analysis` | Gross, operating and EBITDA margin, return on investment, and how margins moved |
| `/cash-flow-analysis` | Burn, runway, working capital, DSO and DPO. Most sales extracts lack these fields, so it names what is missing |
| `/ask-business-data` | One plain-language question, routed to the metric or analysis that already computes it |
| `/revenue-forecast` | Revenue and gross-profit forecast: base, upside and downside scenarios, with a measured uncertainty band |
| `/anomaly-detection` | Periods that deviate from their own baseline, with size, materiality and the breakdown beneath |

**Public research** (public sources only):

| Command | What it answers |
|---|---|
| `/company-analysis` | What one named company does, its dated developments, its positioning and its reported figures |
| `/market-analysis` | One market's definition, size and growth where a source states them, trends, and demand and supply drivers |
| `/competitor-analysis` | The competitive landscape around one company, compared on source-stated dimensions |
| `/industry-research` | One industry's definition, size, trends, drivers and risks, and structure |
| `/benchmark-comparison` | One figure from your file compared with a public benchmark. The two are joined only on your machine |

**Synthesis and decisions** (your file plus public research):

| Command | What it produces |
|---|---|
| `/swot-analysis` | A SWOT in which every point is a statement the analysis already produced, tagged by where it came from |
| `/strategy-analysis` | Recommendations, each citing its evidence, with rationale, benefit, risks, dependencies and a derived confidence |
| `/decision-support` | A draft package for one decision: options, criteria, evidence, tradeoffs, risks and what remains uncertain |
| `/executive-report` | A draft report in eleven fixed sections, assembled from what the analysis established. It writes no analysis of its own |

**Profiling a file before analysis.** Ask "what's in this spreadsheet?" and BusinessOps profiles 1–20 local files. It
reports sheets, columns, completeness, date ranges, candidate keys and key overlap, and whether a command has the
columns it needs. The profile shows no cell values and computes no KPI.

**Final verification.** Add `--final` to `/decision-support` or `/executive-report` to have the draft verified.
- Deterministic code checks that the draft faithfully represents what it was built from.
- Every figure is recomputed from your file in a separate process.
- The draft is finalised only if every check passes. If any check fails, you get the draft back with the findings.
- **Final means verified for integrity, never approved.** The decision stays yours.

Across all commands:
- **No scoring, ranking or execution.** Synthesis output never scores, ranks or rates options, and never executes a
  recommendation.
- **Figures are quoted, never estimated.** Any figure must already appear in cited evidence.
- **Unsupported points are said to be unsupported, not padded.**

## Data sources and connectors

| Source | Status |
|---|---|
| **Local files** (`.xlsx`, `.xlsm`, `.csv`, `.tsv`) | **Available.** The primary path, and designed to stay fully functional with no connector at all |
| **Business Context** (a local JSON file) | **Available.** See [Business Context](#business-context) |
| **Public research** | **Available** through the research commands. Retrieval runs through a dedicated research agent, which uses web search and fetch and has no access to your files |
| **Connected business systems** (CRM, accounting, commerce, databases) | **Not available.** The connector registry ships empty by design. No connector is registered, supported or usable today |

- **The connector groundwork exists.** A connector architecture exists: a registry, a value-free discovery catalogue,
  and a connection lifecycle. It admits a connector only after that connector's tools have been measured and approved.
  None has been.
- **Signing in grants nothing.** Connecting a server yourself in Claude Code does not make it usable by BusinessOps.
- **Reading records from connected systems is blocked** pending platform prerequisites.
- **Which vendor servers exist, and why none is admitted yet**, is in [`CONNECTORS.md`](CONNECTORS.md).
- **Using data from a business system today:** export it to a spreadsheet or CSV and analyse the file.

Excel files are read through four tiers, best available first:

| Tier | Reader | Install |
|---|---|---|
| 1 | `openpyxl`, if already importable | None |
| 2 | `openpyxl` in an isolated BusinessOps runtime at `~/.claude/businessops/runtime/`, run out of process | One-time, **only with your consent** |
| 3 | Built-in standard-library parser | None |
| 4 | Guided CSV export | None |

- **Nothing risky is executed or followed.** Encrypted workbooks are refused, macros are never executed, external
  workbook references are never followed, and formulas are not evaluated. The cached value is read, and a missing one is
  reported rather than invented.
- **The reader is recorded.** Every dataset records which tier read it, and a degraded tier raises a quality warning.

## Privacy and data boundaries

- **Your data is not sent anywhere.** Your files are analysed on your machine. Research answers comparative questions by
  fetching the public benchmark and comparing locally. "Is our 35% margin typical?" becomes a query about the industry,
  never about your margin.
- **Four disclosure tiers:**

  | Tier | What may be sent | Approval |
  |---|---|---|
  | 0 | Public terms only | None |
  | 1 | Aggregated, banded statistics that pass anonymity and re-identification checks | None |
  | 2 | Anything more | Your per-query approval, with the exact text shown first |
  | 3 | Credentials, personal data, customer names and transaction-level records | **Never sent, with no approval path** |

- **Your own values are screened out of queries.** Before any research request goes out, it is checked against the
  non-public values in the business data files in your working directory. A value from one of those files never goes
  into a Tier 0 query, and a value classed as never-disclosable is refused at every tier.
- **The research agent cannot read your files.** It has no file-system access, so it cannot read your data even if
  instructed to.
- **External content is data, not instruction.** Retrieved pages may be adversarial. Instructions found in them are
  never followed, and they can never raise a disclosure tier.
- **No secrets are stored.** BusinessOps stores no credentials. Authentication belongs to MCP servers and their own
  sign-in flows.

These are enforced boundaries with recorded limits (see [Limitations](#limitations)). They are not a guarantee.

## Approval and write safety

Approval follows consequence, not activity:

| Action | Approval |
|---|---|
| Read-only analysis, research at Tiers 0 and 1, draft reports | None |
| Writing a **new** file under `./businessops-output/` | None; the path is stated |
| Overwriting or deleting a file; any other write | Explicit, per action |
| Tier 2 research; exporting off the machine; sending a message; `git commit` or `git push` | Explicit, per action |
| Modifying your original source data; financial transactions; force-pushing or rewriting git history | Prohibited |

Approval is per action. There is no session-wide "yes to everything".

**The write guard.** Once a Claude Code session has used BusinessOps, file-writing tool calls are checked before they
run. That covers `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit` and `PowerShell`.

- **Read-only commands run normally.**
- **An unapproved consequential write is blocked before it happens.** The message names each operation and its target
  and states that nothing was written. It gives a code. To allow that exact operation once, reply:

  ```
  approve BOPS-W-XXXXXXXX
  ```

  Then retry the identical action.
- **An approval is tightly bound.** It is single-use and expires 10 minutes after you give it. It covers only that
  exact operation: another target, another operation (such as append instead of overwrite) or other content needs a new
  approval.
- **Some operations have no approval path.** Changing an existing source-data file (`.csv`, `.tsv`, `.xlsx`, `.xlsm`,
  `.xls`), force-pushing or rewriting git history, and tampering with BusinessOps's approval store are refused outright.
- **The engine is guarded too.** It cannot write, start a process or open a network connection outside its own
  runtime state. The one exception is creating new files under `./businessops-output/`.
- **Failures block writes.** If the guard starts but cannot decide (for example, no usable Python), write-capable tool
  calls are blocked rather than allowed. One exception: if the shell `sh` is missing (native Windows without Git for
  Windows), the guard cannot start at all, Claude Code reports a hook error, and **the guard is not active**; see
  [Platform requirements](#platform-requirements). To stop BusinessOps governing a session, disable the plugin with
  `claude plugin disable businessops`.

**How the guard is built: plugin hooks.** BusinessOps ships Claude Code hooks (`hooks/hooks.json`). You should know
exactly what they do:

| Hook | Runs on | What it does |
|---|---|---|
| `PreToolUse` | `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `PowerShell`, `Skill`, `Agent`, `Task`, `ScheduleWakeup`, `CronCreate`, `SendMessage`, `RemoteTrigger` | Notes when a session starts using BusinessOps. In such a session, checks each write-capable call and **denies** a consequential write that has no approval. In any session, refuses a call that would touch BusinessOps' own approval store, or a scheduling or messaging call that carries an approval phrase |
| `UserPromptSubmit` | Every prompt you type | Looks for `approve BOPS-W-…` in **your own** prompt and grants that one pending approval |
| `UserPromptExpansion` | Slash commands | Notes when you run a BusinessOps slash command |
| `PostToolUse` | `Agent`, `Task` | Saves the research agent's reply byte for byte, so the engine reads it exactly |

- The guard only ever **denies**. It never approves a tool call and never changes Claude's permission settings, so
  every call it lets through still meets your own permission settings and prompts.
- The hooks run in every Claude Code session while the plugin is enabled, not only in sessions that use BusinessOps.
  Each check starts a short Python process, which adds a fraction of a second to each of the tool calls listed above.
  In a session that never uses BusinessOps, nothing is denied except calls that touch BusinessOps' own approval
  store.
- The hooks run locally and send nothing anywhere. What they store is listed in [PRIVACY.md](PRIVACY.md).

## Platform requirements

BusinessOps' analysis runs in a local Python engine, reached through POSIX shell scripts.

| Requirement | Details |
|---|---|
| **Python 3.9 or newer** | On `PATH` as `python` or `python3`, or named by setting `BOPS_PYTHON` to the interpreter's absolute path. The engine uses the Python standard library only. Reading `.xlsx` files can use the optional `openpyxl` library, which BusinessOps installs only with your consent |
| **A POSIX shell, `sh`** | Present on macOS, Linux and WSL. **On native Windows, install [Git for Windows](https://git-scm.com/downloads/win)**, which provides Git Bash |

| Operating system | Status |
|---|---|
| macOS, Linux, WSL | Supported: the environment BusinessOps was designed and tested for |
| Native Windows **with** Git for Windows | Supported. BusinessOps' own test suite has known Windows-specific test-environment failures; see `project_plan.md` in the development repository |
| Native Windows **without** Git for Windows | **Not supported for local analysis.** Without `sh`, the hooks, the local verifier server and every engine command fail to start. Claude Code shows a hook error on tool calls and **the write guard is not active** |

**Without the local runtime** (no Python 3.9+, or no `sh`), nothing that computes a figure works: no KPIs, analytics,
forecasts, anomaly scans, data profiles, verification or synthesis. BusinessOps then says so instead of estimating. It
never fills the gap with model arithmetic.

## Where BusinessOps runs

Claude applications load different parts of a plugin. Claude Code is BusinessOps' primary, fully supported
environment.

| Claude application | What loads | What to expect |
|---|---|---|
| **Claude Code** (terminal, IDE extensions, desktop app's Code tab) | Commands, skills, agents, hooks and the local verifier server | Full functionality, given the platform requirements above |
| **Cowork** (Claude desktop app) | Commands, skills, agents and hooks; the local verifier server only when the Cowork session runs on your computer | Depends on whether the session can run BusinessOps' local Python engine. Not verified by this project |
| **claude.ai chat** (web, desktop and mobile) | Commands and skills only. Agents, hooks and local servers are not loaded | Not supported for analysis: there is no local engine, no write guard, no research agent and no verifier |

Source: Anthropic's [plugin platform-support table](https://claude.com/docs/plugins/platform-support).

## Quick start

Check [Platform requirements](#platform-requirements) first.

**Where the plugin is.** The [BusinessOps repository](https://github.com/conceptwebworld26/BusinessOps) holds the
plugin's source, tests, evaluations and development records. The installable plugin is the folder
`dist/businessops/`, built from that source by `scripts/build_distribution.py`. The material outside that folder is
there on purpose, so the plugin can be reviewed together with the code, tests and records it was built from. Every
route below installs or loads `dist/businessops/`, not the whole repository.

**From Anthropic's plugin directory.** BusinessOps' directory submission uses the plugin path `dist/businessops`, and
the directory reads only that folder. When BusinessOps is listed there, add it from the directory; no command below
is needed.

**Install from the BusinessOps marketplace.** The repository is also a Claude Code marketplace named `businessops`.
Its catalogue entry for the `businessops` plugin points at `./dist/businessops`, so only that folder is installed:

```bash
claude plugin marketplace add conceptwebworld26/BusinessOps
claude plugin install businessops@businessops
```

The first command adds the marketplace and the second installs the plugin from it (`plugin@marketplace`).

**Or load a local clone for one session:**

```bash
git clone https://github.com/conceptwebworld26/BusinessOps.git
cd BusinessOps
claude --plugin-dir dist/businessops
```

The project's own recorded runs used `--plugin-dir`. The marketplace install uses Claude Code's standard plugin
commands. That route has not been separately recorded by this project.

**Try it on the bundled synthetic dataset.** From a clone of the repository:

```bash
mkdir -p .businessops && cp assets/demo-data/business_context.json .businessops/
```

Then, in Claude Code:

```
/business-health assets/demo-data/northwind_sales.csv
```

If another plugin defines a command with the same name, use the plugin-qualified form, for example
`/businessops:business-health`. You can also just ask in plain language, for example "what's in this spreadsheet?" or
"which region grew fastest?".

## Example usage

The examples use the bundled synthetic Northwind dataset, or a file of your own.

```
/sales-analysis assets/demo-data/northwind_sales.csv
/customer-analysis assets/demo-data/northwind_sales.csv --shareable
/profitability-analysis assets/demo-data/northwind_sales.csv
/ask-business-data "which region grew fastest" assets/demo-data/northwind_sales.csv
/revenue-forecast assets/demo-data/northwind_sales.csv --horizon 6
/anomaly-detection assets/demo-data/northwind_sales.csv --sensitivity high
```

```
/company-analysis Microsoft --focus overview
/market-analysis "electric vehicle charging" --geography Europe --period 2026
/competitor-analysis "<company>" --focus landscape
/industry-research cold chain logistics --focus structure
/benchmark-comparison sales.xlsx --metric revenue --benchmark "cold chain logistics"
```

```
/swot-analysis sales.xlsx --industry "cold chain logistics"
/strategy-analysis sales.xlsx --industry "cold chain logistics"
/decision-support sales.xlsx --question "Should we reprice the lines behind the margin decline?" --criterion "Effect on gross margin"
/executive-report sales.xlsx --period "FY2025" --audience "Board" --strategy --swot
```

## Forecasting and anomaly detection: what to expect

**Forecasts**
- **Method.** The method is chosen from naive, 3-period moving average, drift, linear trend and seasonal naive.
  - With at least six periods of history, candidates are backtested on held-out periods and the lowest-error method is
    chosen. That error becomes the uncertainty band.
  - A forecast needs at least the configured minimum history (`forecast.min_history_periods`, 12 periods by default).
    With less, no forecast is produced: the target is reported as insufficient data, stating its periods and the
    requirement.
  - Seasonal forecasting needs more than a year of monthly history.
- **Short or missing data.** A forecast is refused when the history is too short or the field is absent.
- **No inference from sales.** Operating expense and cash flow are forecast only when those columns exist; neither is
  inferred from sales.
- **Assumptions are stated.** Scenarios state their assumptions. Missing periods are treated as absent, not as zero.
- **A forecast is an estimate with a measured error, not a guarantee.** Forecasts are not yet carried into executive
  reports, whose outlook section says so.

**Anomalies**
- **What counts.** A deviation is measured against the metric's own history, which needs at least 6 baseline periods
  by default. Sensitivity is `low`, `medium` (the default) or `high`.
- **What it does not say.** Anomaly detection describes deviations only. It never establishes a cause and **never
  treats an anomaly as fraud**.

## Evidence and interpretation

Every claim carries one of seven provenance classes:

| Class | Meaning |
|---|---|
| User-provided data | Read from a file you supplied |
| Connected-system data | Pulled from a connected system. None is available today |
| External sourced | Retrieved from public research, with source, date and source tier |
| Calculated metric | Computed by the engine, with its formula and inputs |
| Analytical interpretation | A reading of the above, framed explicitly as interpretation |
| Estimate / assumption | Modelled or assumed, flagged and entered in an assumption register |
| Recommendation | A proposed action with its evidence, rationale, benefit, risks, dependencies and confidence |

- **Citations are never fabricated.** Where no reliable source is found, BusinessOps says so.
- **Confidence is derived from the evidence, not chosen.**
- **Caveats travel with the claim.** Data-quality caveats stay attached to the claims they affect.

## Business Context

Business Context tells BusinessOps about the business it is analysing. Every field is optional:

- **Identity:** industry, business model, size band, products and categories, and markets.
- **Reporting:** fiscal year, currency and formats.
- **Analysis:** materiality thresholds, KPI definition overrides and terminology.

How it is stored and used:

- **Location.** `./.businessops/business_context.json` in your project, which is kept out of version control.
  `~/.claude/businessops/business_context.json` is also supported for single-business use. The project file wins.
- **Precedence.** A command argument, then the project context, then the user context, then the shipped defaults
  (`config/businessops.defaults.json`).
- **Validation.** Industry and business model come from a controlled vocabulary. An unrecognised value triggers a
  question. A contradiction between context and data (for example, context says GBP and the data is in USD) is reported
  as a quality finding, never silently overridden.
- **KPI relevance.** Context decides which KPIs apply to your business model. A metric can be available,
  **unavailable** (the missing field is named) or **not applicable** (meaningless for your model). Without context,
  nothing is suppressed, and the output says relevance filtering is off.
- **Privacy.** Context is confidential and classified field by field. Only a small public subset can shape a research
  query: industry, business model, size band, market and product categories.

The demo dataset ships a sample at `assets/demo-data/business_context.json`.

## Documentation

| Document | What it covers |
|---|---|
| [`architecture.md`](https://github.com/conceptwebworld26/BusinessOps/blob/main/architecture.md) | What the system is, and why |
| [`project_plan.md`](https://github.com/conceptwebworld26/BusinessOps/blob/main/project_plan.md) | Milestones and current status |
| [`CONNECTORS.md`](CONNECTORS.md) | Connector landscape and why none is admitted yet |
| [`reference/`](reference/) | Policy documents: evidence ledger, research policy, materiality, output standards |
| [`docs/decisions/`](https://github.com/conceptwebworld26/BusinessOps/blob/main/docs/decisions/README.md) | Architecture decision records |
| [`docs/testing/defects.md`](https://github.com/conceptwebworld26/BusinessOps/blob/main/docs/testing/defects.md) | The defect register |
| [`docs/examples/`](https://github.com/conceptwebworld26/BusinessOps/blob/main/docs/examples/README.md) | Worked examples on the bundled demo data |
| [`docs/troubleshooting/`](https://github.com/conceptwebworld26/BusinessOps/blob/main/docs/troubleshooting/README.md) | Troubleshooting guide: symptom, cause, check, resolution |
| [`docs/releases/0.1.0.md`](https://github.com/conceptwebworld26/BusinessOps/blob/main/docs/releases/0.1.0.md) | Release notes for version 0.1.0 (release candidate) |
| [`docs/development/`](https://github.com/conceptwebworld26/BusinessOps/tree/main/docs/development) | Dated development history |
| [`CLAUDE.md`](https://github.com/conceptwebworld26/BusinessOps/blob/main/CLAUDE.md) | How this project is developed |

## Current status

- **Version and development stage.** The plugin manifest version is `0.1.0`, prepared as a release candidate; see the
  [0.1.0 release notes](https://github.com/conceptwebworld26/BusinessOps/blob/main/docs/releases/0.1.0.md). No release has been tagged. Development
  is in its documentation and release milestone.

| Area | Status |
|---|---|
| Internal analysis, KPIs, data quality, forecasting, anomaly detection | Implemented |
| Synthesis: SWOT, strategy, decision support, executive report, final verification | Implemented |
| Write guard and approval flow | Implemented |
| External research commands | Implemented. All four passed their live smoke test in a fresh session (2026-09-27) |
| Connected business systems | Not available: registry empty, record reads blocked |
| Forecasts in executive reports | Not yet available |
| Further skills described in the architecture | Planned, not scheduled |

- **Behavioural evaluation.** The behavioural evaluation suite (64 cases) has been executed, and its results and the
  defects it found are recorded in [`docs/testing/defects.md`](https://github.com/conceptwebworld26/BusinessOps/blob/main/docs/testing/defects.md).

## Limitations

**Data and analysis**
- **Large files.** A large CSV is loaded whole, not streamed. Very large files need corresponding memory.
- **Connected systems.** None are available (see [Data sources and connectors](#data-sources-and-connectors)).

**Behaviour observed in evaluation.** These are recorded as open defects:
- BusinessOps sometimes asks for approval or confirmation before read-only analysis that needs none.
- It sometimes omits a statement it is meant to make, such as a clarifying question, or "No reliable source found"
  when research finds nothing.
- A Tier 2 research query may be refused outright instead of being shown to you for approval.

**Write guard**
- **Scope.** It governs a session only once BusinessOps has been used in it.
- **Temporary directory.** Files under the system temporary directory are treated as scratch, outside the approval
  boundary.
- **Latency.** Every checked tool call starts a shell and Python, which adds a little time to each call.
- **Prompt origin.** The platform does not yet report where a prompt came from. BusinessOps blocks the approval phrase
  in the tools it knows can inject prompts, but it cannot distinguish every injected prompt from one you typed.

**Environment**
- **Final verification.** `--final` starts a local MCP server through the same interpreter resolver as the rest of the
  engine, so it needs Python 3.9 or newer on `PATH` as `python` or `python3` (or `BOPS_PYTHON`), and a POSIX shell.
- **Research quality.** It is bounded by what is publicly published.

Full details: [`architecture.md`](https://github.com/conceptwebworld26/BusinessOps/blob/main/architecture.md) §20 and [`docs/testing/defects.md`](https://github.com/conceptwebworld26/BusinessOps/blob/main/docs/testing/defects.md).

## Development and architecture

- **Deterministic engine.** Every reported number originates in `lib/python/bops/`, a standard-library-only Python
  engine, never in model arithmetic.
- **One home for each rule.** Computation lives in the engine, policy in a reference document, judgement in a skill, and
  sequencing in a command.
- **Layered.** Context and policy, then data, analytics, intelligence, synthesis and orchestration. Each layer depends
  only on the layers below it.
- **Fails loudly.** Insufficient or poor-quality data stops a workflow with a stated reason.
- **Source data is immutable.** Normalisation happens on a derived working copy.

```bash
python3 tests/run_tests.py              # full test suite: standard library only, offline, deterministic
python3 scripts/build_distribution.py   # rebuild the installable plugin into dist/businessops/
claude plugin validate dist/businessops --strict                           # the package's marketplace manifest
claude plugin validate dist/businessops/.claude-plugin/plugin.json --strict  # the package's plugin manifest
claude plugin validate . --strict                                          # this repository's marketplace catalogue
```

## Support

Questions, problems and security concerns: **krayonsglobal@gmail.com**. Please include your operating system, your
Claude application and version, and the command you ran. Do not send confidential business data.

## Privacy

BusinessOps has no telemetry and sends your business data nowhere itself; analysis runs on your computer. Claude
processes your conversation under your agreement with Anthropic. Details are in [PRIVACY.md](PRIVACY.md).

## License

Proprietary. Copyright (c) 2026 Prakash Meghani - Krayons Global. All rights reserved. You may install and use
BusinessOps under the [End User License Agreement](EULA.md); see [`LICENSE`](LICENSE).
