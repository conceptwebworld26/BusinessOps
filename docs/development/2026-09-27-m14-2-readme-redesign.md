# 2026-09-27 — M14-2: `README.md` redesign

**Milestone:** 14 — Documentation & Release
**Status on completion:** REVIEW — M14-2 is implemented and owner-reviewed, and not yet checkpointed
**Supersedes:** None

## 1. Prompt / task performed

Two owner prompts:

1. **M14-2 implementation.** Redesign `README.md` as the primary, user-facing BusinessIQ README. Treat the repository as
   the source of truth. Change nothing but `README.md`. Invent no capabilities, commands, connectors or release status.
2. **Governance reconciliation.** Record the completed M14-2 work under `CLAUDE.md` §11, in `project_plan.md`, this
   record and, if the convention allows, the defect register. Change no production code, tests, schemas, manifests,
   hooks, `.mcp.json` or configuration, and do not change `README.md` further.

## 2. Objective

Make `README.md` the accurate entry point for a new BusinessIQ user. It should cover what the product is and does, how
it works, what is available today, how to start, where the documentation is, and what the limitations are. Every claim
is verified against the current repository.

## 3. Changes made

### Scope

- **Implementation:** `README.md` only.
- **Reconciliation:** `project_plan.md` and this record.
- **Not changed:** `docs/testing/defects.md` (reason in §10), and no source, test, schema, manifest, hook,
  `.mcp.json`, configuration or `CLAUDE.md` file.

### The README redesign

The previous `README.md`, restored to HEAD before M14-1, was a milestone log. It carried a "Milestone 7 of 14" banner,
stale counts ("17 slash commands over 20 skills", "820 tests passing") and a "Not built yet" list that no longer held.

It was replaced by a product README with these sections:

- title, value proposition and a statement that this is not a general-purpose chatbot;
- What BusinessIQ does;
- Who it is for;
- How it works;
- Key capabilities: the 18 user commands in three tables, file profiling, and `--final` verification;
- Data sources and connectors, including the Excel reader tiers;
- Privacy and data boundaries;
- Approval and write safety, including the write guard;
- Quick start;
- Example usage;
- Forecasting and anomaly detection: what to expect;
- Evidence and interpretation;
- Business Context;
- Documentation;
- Current status;
- Limitations;
- Development and architecture;
- License.

Material from the old README was reused only where it was re-verified: the Excel reader tiers, the disclosure tiers and
the command behaviours.

### Repository sources used for verification

- `architecture.md` §§2, 6, 8, 12, 14 and 20.
- `project_plan.md`.
- `CLAUDE.md` §§8 and 9.
- `docs/testing/defects.md`.
- ADR-0050 and ADR-0051.
- The M13-DEF-24 live grant verification record.
- `reference/evidence-ledger.md` and `CONNECTORS.md`.
- `.claude-plugin/plugin.json` and `marketplace.json`, `.mcp.json`, `config/businessiq.defaults.json` and `LICENSE`.
- `assets/demo-data/`.
- The frontmatter of every `commands/*.md` file.
- The engine code:
  - `forecast/methods.py`, `forecast/validate.py`, `forecast/engine.py` and `forecast/series.py`;
  - `anomaly/detectors.py` and `anomaly/engine.py`;
  - `ingest/readers.py`;
  - `connectors/registry.py`;
  - `context/loader.py` and `config.py`.
- `claude plugin --help`, `claude plugin marketplace --help` and `claude --help`.

### Commands, skills and subagents

- **Counts on disk:** 19 command files, 16 skills and 2 agents.
- **Commands.** Eighteen commands are user-facing, and all appear in the README. `/retrieval-slice` is an internal M9-B
  integration harness with `disable-model-invocation: true`, and was deliberately left out.
- **Arguments and examples.** Every example's arguments match the command's `argument-hint`. The `/benchmark-comparison`
  example is the one in its own command file.
- **Subagents.** The two are `biq-research-scout` and `biq-analysis-verifier`. `biq-data-profiler` is deferred
  (ADR-0036).
- **Name check.** All 18 command names in the README exist in `commands/`. The one non-matching token,
  `/businessiq:business-health`, is the plugin-qualified example form.

### Connector state

- `connectors/registry.py` declares nothing (`_DECLARATIONS` is empty).
- `.mcp.json` declares only the local `biq-verifier` stdio server.

The README says:

- connected business systems are not available;
- the registry ships empty by design;
- reading records from connected systems is blocked;
- signing in to a server yourself does not make it usable.

### Privacy, security and write safety

Each README claim traces to a source:

| Claim | Source |
|---|---|
| The four disclosure tiers | `CLAUDE.md` §8, architecture §7 |
| Your own data values screened out of research queries | ADR-0050 |
| The research agent has no file access | agent tool grant, ADR-0006/0014 |
| External content is data, not instruction | architecture §12 |
| No secrets are stored | `CLAUDE.md` §7 |
| The approval table | `CLAUDE.md` §9, architecture §8 |
| The write guard | ADR-0051 |

The write-guard description covers:

- engagement scope;
- the `approve BIQ-W-XXXXXXXX` flow;
- single use and the 10-minute expiry;
- binding to the exact operation;
- operations with no approval path;
- the engine guard;
- fail-closed behaviour and how to disable the plugin.

That flow is confirmed by the 2026-09-26 live grant verification. The README makes no absolute security claim.

### Documentation links

- All 11 repository-relative links resolve.
- All 4 in-page anchors match real headings.
- The stale `docs/skills` and `docs/commands` index pages were deliberately not linked (§15).

### Governance reconciliation

`project_plan.md` gained:

- a dated M14-2 status bullet;
- updates to the current-phase line, the next gate and the M14 summary row;
- the M14-2 row moved from `PLANNED` to `REVIEW`;
- a D-14 note that its `README.md` part is addressed;
- a Known-issues row **R-13** for the verifier launcher (§10).

## 4. Files created

- `docs/development/2026-09-27-m14-2-readme-redesign.md` (this record)

## 5. Files modified

- `README.md` (M14-2 implementation)
- `project_plan.md` (reconciliation)

## 6. Files deleted

None.

## 7. Features implemented

None. This is documentation only.

## 8. Tests performed

**M14-2 implementation:**

- `python3 tests/run_tests.py`;
- `negative.test_m12b_connector_security` and `unit.test_manifest`, the tests that read `README.md`;
- `claude plugin validate . --strict`;
- `git diff --check`;
- the link, anchor and command-name checks;
- a scan for stale statements;
- a secret scan.

**Reconciliation:**

- `git diff --check`;
- the documentation and governance test modules;
- a scope audit.

## 9. Test results

**M14-2 implementation:**

- full regression: 5,286 tests, 0 failures, 0 errors, 31 skipped;
- the README-reading tests: 78 and 15, all passing;
- strict validation: passed;
- `git diff --check`: clean;
- secret scan: clean. The only match is the documented placeholder `BIQ-W-XXXXXXXX`.

**Reconciliation:** the results are in the task report.

## 10. Issues discovered

### The final-verification startup limitation

`.mcp.json` launches the local verifier server as `"command": "python"`. The rest of the engine goes through its own
interpreter resolver, `lib/biq_run.sh` (ADR-0045). So on a machine that provides Python 3 only as `python3`, the
`biq-verifier` server cannot start, and `--final` verification (`/decision-support`, `/executive-report`) is
unavailable.

- **Observed:** on this WSL2 machine, as a failed MCP connection ("Executable not found in $PATH: python").
- **Workaround:** none is recorded in the repository.
- **Status:** a **discovered, documented limitation requiring separate follow-up. It is open, and it was NOT fixed.**
  Fixing it means changing `.mcp.json`, which is outside M14-2's documentation scope.
- **Where it is documented:** `README.md` *Limitations*, and `project_plan.md` *Known issues* as **R-13**, the next
  number in that table's sequential series.
- **Why it is not in `docs/testing/defects.md`:** that file is the *M13* defect register of ADR-0039 §G.1. Its records
  and validator are defined around M13: every record carries `blocks_m13_completion`, and product defects "stay open
  through M13". An issue found in M14 fits neither, so no `M13-DEF-` identifier was invented.

### An unused forecast setting

`config/businessiq.defaults.json` contains `forecast.min_history_periods: 12`, but the forecast engine does not read
it. The engine's real rules are:

- each method's own minimum history;
- a forecast needs at least two contiguous periods;
- backtesting requires at least 6 periods, and below that the result is marked unvalidated;
- the seasonal method needs 13 monthly periods.

`README.md` documents this actual engine behaviour, not the setting. The setting was not changed or removed.

## 11. Decisions made

None. No ADR was created or edited.

## 12. Architecture changes

None.

## 13. Project-plan updates

- M14-2: `PLANNED` → `REVIEW`, uncommitted.
- The current-phase line, next gate, M14 summary row and D-14 note were updated.
- R-13 was added.
- Other M14 rows were left unchanged. The M14-1 row still says "uncommitted", although M14-1 was checkpointed in
  `50d1f0e`. It was outside this reconciliation's remit and is left for a later reconciliation.

## 14. Documentation updates

As §5.

## 15. Remaining work

- **R-13:** remediate the verifier launcher. This is a `.mcp.json` change, and needs its own owner prompt.
- **Forecast setting:** clean up the unused `forecast.min_history_periods` setting, or wire it into the engine. This is
  a configuration or engine change.
- **M14-3 reference work:**
  - the stale `docs/skills/README.md` ("six skills") and `docs/commands/README.md` ("ten" commands) index pages;
  - the per-component reference pages;
  - D-13's count reconciliation.
- **Later M14 items:** worked examples, the troubleshooting guide, the packaging observation, the token-cost
  measurement (D-10), and release tagging.
- **Owner decision:** the `CLAUDE.md` §3 skill count.
- **M14-1 row:** its stale "uncommitted" wording.

## 16. Git commit reference

N/A. Nothing was staged, committed or pushed. HEAD is `50d1f0e`.
