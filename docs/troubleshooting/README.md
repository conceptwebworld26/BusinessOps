# Troubleshooting

Each entry follows the same pattern: symptom, likely cause, what to check, the supported resolution, and when to stop
and escalate. Every cause and resolution below is documented behaviour of the repository at commit `8e4ab17` or a
recorded open issue. **Where the repository documents no workaround, this page says so, rather than inventing one.**

*Escalating* means raising an issue on the repository
([github.com/conceptwebworld26/BusinessOps](https://github.com/conceptwebworld26/BusinessOps)) with the command, the
message and the Claude Code version. Never include your business data, credentials or customer names.

Contents:

- [Installing and loading](#installing-and-loading)
- [Python and the engine](#python-and-the-engine)
- [Input files and data quality](#input-files-and-data-quality)
- [KPIs and analysis](#kpis-and-analysis)
- [Forecasting](#forecasting)
- [Anomaly detection](#anomaly-detection)
- [Public research and privacy](#public-research-and-privacy)
- [Connected business systems](#connected-business-systems)
- [Approvals and the write guard](#approvals-and-the-write-guard)
- [Business Context](#business-context)
- [Final verification (`--final`)](#final-verification-is-unavailable)
- [For developers: validation and tests](#for-developers-validation-and-tests)

## Installing and loading

### A BusinessOps command is not found, or runs another plugin's command

- **Cause.** Either the plugin is not loaded in this session, or another plugin defines a command with the same
  name.
- **Check.** Run `claude plugin list` to see whether `businessops` is installed. If you loaded a clone, check that you
  started Claude Code with `claude --plugin-dir <path to the clone>/dist/businessops`.
- **Resolution.**
  - Load the plugin by either route in the `README.md` *Quick start*: the marketplace install, or `--plugin-dir` for
    one session.
  - For a name collision, use the plugin-qualified form, for example `/businessops:business-health`.
- **Note.** The project's own recorded runs used `--plugin-dir`. The marketplace route uses the standard plugin
  commands, and this project has not separately recorded it.
- **Escalate** if `claude plugin validate dist/businessops --strict` passes on the clone but the commands still do not
  appear.

### `/retrieval-slice` appears in the command list

- **Cause.** An older development copy of the plugin. Since BusinessOps M3 the M9-B integration harness lives in
  `dev/harness/retrieval-slice.md`, outside `commands/`, and is not part of the installable plugin.
- **Resolution.** Update to the current BusinessOps package. For research, use `/company-analysis`,
  `/market-analysis`, `/competitor-analysis` or `/industry-research`. See the
  [Command Reference](../commands/README.md#internal-not-a-user-command).


## Python and the engine

### "bops_run.sh: no usable Python interpreter found"

- **Cause.** The engine needs Python 3.9 or newer. The resolver (`lib/bops_run.sh`, ADR-0045) looks on `PATH` for
  `python`, then `python3`, and accepts only an interpreter that passes its version probe. The script exits with
  status 78.
- **Check.** Run `python3 --version` or `python --version`.
- **Resolution.** Install Python 3.9 or newer on `PATH` as `python` or `python3`. Alternatively, set `BOPS_PYTHON` to
  the **absolute** path of an existing interpreter, for example `BOPS_PYTHON=/usr/bin/python3`. A relative
  `BOPS_PYTHON` is refused.
- **Under WSL.** Windows interpreters (`python.exe`) are deliberately excluded from the automatic search, because they
  cannot open Linux paths (ADR-0046). Install a Linux Python inside WSL, or name one explicitly with `BOPS_PYTHON`.
- **Escalate** if a Python 3.9+ interpreter is on `PATH` and the resolver still refuses it.

### Every write-capable tool call is blocked with "BusinessOps write guard could not start"

- **Cause.** The write guard runs Python through the same resolver. If it cannot start, it **fails closed**, and
  write-capable tool calls are blocked, not allowed (ADR-0051).
- **Resolution.** Fix the interpreter as in the previous entry. To stop BusinessOps governing the session, disable the
  plugin with `claude plugin disable businessops`.
- **Escalate** if the guard fails with a working interpreter.

## Input files and data quality

### The command asks for a file instead of running

- **Cause.** Every data command requires a file path and never picks one for you. This is intended behaviour.
- **Resolution.** Give the path to a `.xlsx`, `.xlsm`, `.csv` or `.tsv` file.

### An Excel workbook cannot be read, or reads with a quality warning

- **Cause.** Excel is read through four tiers (see `README.md`, *Data sources and connectors*).
  - Tier 3, the standard-library parser, is used when `openpyxl` is unavailable, and raises a quality warning for
    unresolved formats.
  - Tier 4 means no usable reader. BusinessOps then asks for a CSV export.
  - Encrypted workbooks are refused.
  - Formulas are not evaluated: the cached value is read, and a missing cached value is reported, never invented.
- **Resolution.**
  - Export the sheet to CSV.
  - For tier 2, accept BusinessOps's one-time, consented install of `openpyxl` into
    `~/.claude/businessops/runtime/` when it is offered.
  - For a workbook whose formulas have no cached values, export it to CSV from the application that computes them.
- **Escalate** if a plain, unencrypted CSV fails to read.

### The run stops with a `CRITICAL` data-quality grade and shows no figures

- **Cause.** The quality gate halts on `CRITICAL`, by design. Presenting KPIs from data that failed validation would
  give them a validity they do not have.
- **Check.** The halt message names the failing check families and reasons.
- **Resolution.** Correct the problem in **a copy** of your data (BusinessOps never modifies the original), and run
  again. A `WARNING` grade does not halt: the caveat travels with every figure.

### BusinessOps asks which column is the revenue, customer or date column

- **Cause.** A column's business role was mapped only provisionally, below the confidence threshold. BusinessOps asks
  instead of guessing.
- **Resolution.** Answer the question. Figures that depend on that mapping are not relied on until you confirm it.

## KPIs and analysis

### A KPI shows "unavailable"

- **Cause.** A required field is missing, and the output names it. For example, operating profit needs
  `operating_expense`, and runway needs `cash_balance` and `operating_expense`.
- **Resolution.** Supply a file that contains the named field. BusinessOps never estimates an unavailable figure.
  On a sales extract, "unavailable" is the expected answer for cash and balance-sheet metrics
  ([Example 4](../examples/README.md#example-4--when-the-data-cannot-answer)).

### A KPI shows "not applicable"

- **Cause.** The metric is meaningless for the business model in your Business Context. For example, MRR, ARR and
  NRR do not apply to a transactional retail business.
- **Resolution.** None needed. If the business model is wrong, correct it in your Business Context
  ([below](#business-context)).

## Forecasting

### A forecast is refused as "insufficient data"

- **Symptom.** For example: "Revenue has 8 periods of history; 12 are required before a forecast is produced."
- **Cause.** The forecast engine requires at least `forecast.min_history_periods` periods of history. The shipped
  default is **12** (`config/businessops.defaults.json`, read by `lib/python/bops/forecast/engine.py`). Below it, no
  forecast is produced.
- **Resolution.** Supply a longer monthly history. Gaps count as absences, and the forecast uses the unbroken run, so
  a series with gaps may be shorter than it looks.
- **Escalate** if a series with at least the stated number of contiguous monthly periods is still refused.

### A forecast target is "unavailable"

- **Cause.** Operating expense and cash flow are forecast only from their own columns, never from sales. Gross profit
  needs a cost column.
- **Resolution.** Include the column for that target. This is not an error.

### The forecast horizon is shorter than requested

- **Cause.** The horizon is capped at half the observed history, and at 24 periods. The output states the reduction.
- **Resolution.** Supply more history, or accept the reduced horizon.

### The executive report's outlook says a forecast is not available

- **Cause.** No approved path carries a forecast into the synthesis set yet. This is documented behaviour, not a
  failure.
- **Resolution.** Run `/revenue-forecast` separately.

## Anomaly detection

### A metric is "insufficient data", or nothing is flagged

- **Cause.** Each period is scored against at least `anomaly.min_baseline_periods` prior periods, 6 by default, so
  the earliest periods cannot be scored. A constant series flags nothing. The scan always reports how many periods it
  checked, so "nothing found" can be told apart from "nothing looked at".
- **Resolution.** Supply more history, or try `--sensitivity high` to lower the thresholds. Sensitivity changes the
  thresholds, never the arithmetic.

### An anomaly is not explained, or is not called fraud

- **Cause.** This is intended behaviour. An anomaly is a deviation from a baseline. BusinessOps never assigns a cause,
  and never presents a deviation as fraud or wrongdoing. No approval unlocks that.

## Public research and privacy

### A research command returns "no reliable source found" or an empty section

- **Cause.** Nothing citable was retrieved for that question. Producing no analysis is a correct outcome, and
  BusinessOps never fills the gap from the subject's name or from training knowledge.
- **Check.** Make sure the session has web access. The `bops-research-scout` agent uses `WebSearch` and `WebFetch`.
- **Resolution.** Narrow or disambiguate the subject with the public options, `--geography`, `--industry` or
  `--period`.
- **Known limitation.** The behavioural evaluation recorded that BusinessOps sometimes omits this statement. See the
  defect register, [`docs/testing/defects.md`](../testing/defects.md).

### A research command reports "no verbatim capture of the scout's reply exists"

- **Cause.** The scout's reply reaches the engine only through the plugin's `PostToolUse` hook, which stores it byte
  for byte (ADR-0053). If that hook did not run (plugin hooks disabled, or the plugin loaded without its `hooks/`), there
  is no capture. The retrieval then fails closed, and the reply is never supplied by hand.
- **Check.** Confirm the plugin is loaded with its hooks. Hooks are auto-discovered from `hooks/hooks.json`.
- **Resolution.** Re-run the command in a session where plugin hooks run.
- **Escalate** if hooks run and the capture is still missing.

### A research command pauses after retrieval and asks you to `approve BOPS-W-…`

- **Cause.** The write guard (ADR-0051) allows engine code only where it can confine its effects. If the session
  runs the closing step in a form the guard cannot confine, for example from a script file instead of the documented
  inline call, the guard asks for approval before it runs. It never runs it silently. This was observed once, in the
  M14-5 live smoke test of `/competitor-analysis`.
- **Resolution.** Read what the message says the call does. If you accept it, reply with the exact
  `approve BOPS-W-…` code, and the session repeats the identical call. Otherwise decline, and the command stops with
  no report. Nothing is written either way. A non-interactive run (`claude -p`) cannot approve, so it stops there.
- **Escalate** if the documented inline closing call itself is blocked.

### The disclosure gate refuses a query (`not_authorised`)

- **Cause.** The query would disclose something beyond public terms. The gate also screens every request fragment
  against your workspace's business data (ADR-0050).
- **Resolution.** Ask about the public subject (the industry, market or company), not about your own figures.
  BusinessOps fetches the benchmark and compares locally (`/benchmark-comparison`).
- **Known limitation.** A Tier 2 query, which should be shown to you for per-query approval, may instead be refused
  outright. This is recorded as an open defect.
- **Escalate** if a query built only from public terms is refused.

### BusinessOps asks which company or market you mean

- **Cause.** The subject is ambiguous. BusinessOps asks, naming the candidates, instead of researching a guess.
- **Resolution.** Answer with the intended entity.

## Connected business systems

### A CRM, accounting or commerce connection does not work with BusinessOps

- **Cause.** No connected business system is available. The connector registry ships empty by design, and reading
  records from connected systems is blocked. Signing in to a server yourself does not make it usable by BusinessOps.
- **Resolution.** Export the data to a spreadsheet or CSV, and analyse the file. See `CONNECTORS.md`.
- **Escalate:** not applicable. This is the shipped state, not a fault.

## Approvals and the write guard

### A file write is blocked, with an approval code

- **Cause.** Once a session has used BusinessOps, consequential writes need explicit per-action approval (ADR-0051).
  Writing a **new** file under `./businessops-output/` does not.
- **Resolution.** If you want the write, reply `approve BOPS-W-XXXXXXXX`, using the code from the message. Then retry
  the **identical** action.
  - An approval is single-use and expires 10 minutes after you give it.
  - It is bound to the exact operation: a different target, operation or content needs a new approval.

### A write is refused with no approval path

- **Cause.** Some operations are prohibited outright:
  - changing an existing source-data file (`.csv`, `.tsv`, `.xlsx`, `.xlsm`, `.xls`);
  - force-pushing or rewriting git history;
  - tampering with the approval store.
- **Resolution.** Work on a copy of your data. There is no approval that unlocks these.

### BusinessOps asks for approval before a read-only analysis

- **Cause.** The behavioural evaluation recorded this as an open defect. Read-only analysis needs no approval
  (`CLAUDE.md` §9).
- **Resolution.** Confirm, and the analysis proceeds. See [`docs/testing/defects.md`](../testing/defects.md).

## Business Context

### The output says "relevance filtering is off", or uses the wrong currency

- **Cause.** No Business Context was found. BusinessOps looks for `./.businessops/business_context.json`, then
  `~/.claude/businessops/business_context.json`. Without either, nothing is suppressed, and the shipped default
  currency applies.
- **Resolution.** Create the file. The demo sample shows the shape:
  `mkdir -p .businessops && cp assets/demo-data/business_context.json .businessops/`, then edit it for your business.
  `/business-health --currency` also overrides the currency for one run.

### BusinessOps asks about an industry or business-model value, or reports a context contradiction

- **Cause.**
  - Industry and business model must come from a controlled vocabulary, so an unrecognised value triggers a question.
  - A contradiction between context and data (for example, context says GBP and the data is in USD) is reported as a
    quality finding, never silently overridden.
- **Resolution.** Correct the value in the context file, or confirm which source is right.

## Final verification is unavailable

### `--final` does not finalise, or the `bops-verifier` MCP server fails to connect

- **Symptom.** Claude Code reports that the `bops-verifier` MCP server failed to connect.
  `/decision-support --final` or `/executive-report --final` then presents the draft with verification findings.
- **Cause.** The server starts through the same interpreter resolver as the rest of the engine:
  `sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" --verifier` (ADR-0052). If the resolver finds no Python 3.9+, as
  `python` or `python3`, or if `sh` is unavailable, the server cannot start, and verification fails closed. Nothing
  is presented as final.
- **Check.**
  - Run `python3 --version` or `python --version`.
  - Run `claude --plugin-dir <path to the clone> mcp list` from a directory **outside** the repository, and look for
    `plugin:businessops:bops-verifier … ✔ Connected`.
  - Run it outside the repository because, inside it, Claude Code also reads the repository's `.mcp.json` as a
    project file, where `${CLAUDE_PLUGIN_ROOT}` is not set. That project entry always fails, and it is not the plugin's
    server.
- **Resolution.** Fix the interpreter as in
  ["no usable Python interpreter found"](#bops_runsh-no-usable-python-interpreter-found). `BOPS_PYTHON` applies to the
  verifier too. Until it connects, drafts remain fully usable, labelled `draft — unverified`.
- **Older copies.** A copy from before M14-5 declared the server as a bare `python`, and failed with "Executable not
  found in $PATH: python" on hosts that provide only `python3` (R-13, now fixed). Update the plugin.
- **Escalate** if the resolver finds a Python 3.9+ interpreter and the server still fails to connect.

## For developers: validation and tests

### `claude plugin validate --strict` fails on `plugin.json` with a `CLAUDE.md` advisory

- **Cause.** This is expected, and documented in `architecture.md` §2. Validating the manifest directly emits the
  advisory "CLAUDE.md at the plugin root is not loaded as project context". Under `--strict`, that advisory alone
  fails the run.
- **Resolution.** Run `claude plugin validate . --strict` from the repository root. It resolves to the marketplace
  manifest and passes.

### Running one test module fails with "No module named 'bops'"

- **Cause.** The engine lives in `lib/python`, and `tests/run_tests.py` puts it on the path for you.
- **Resolution.** Run the full suite with `python3 tests/run_tests.py`. For a single module, from `tests/`, run
  `PYTHONPATH=../lib/python python3 -m unittest <module>`.

### `claude plugin eval` fails with `EPERM` creating its sandbox socket

- **Cause.** Recorded as M13-DEF-11 (`fixed_infrastructure`): the evaluator's sandbox cannot initialise inside an
  already-sandboxed outer Claude Code session.
- **Resolution.** This is the documented operator action. Set the outer session to `No Sandbox` with `/sandbox`, and
  keep the evaluator's own sandbox enabled. See `docs/testing/defects.md`.
- **Caution.** Evaluations run on your credential and can incur cost. Run them only when you intend to.
