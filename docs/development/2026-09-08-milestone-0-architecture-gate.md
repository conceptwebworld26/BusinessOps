# 2026-09-08 — Milestone 0: Architecture Gate

**Milestone:** 0 — Architecture & Governance
**Status on completion:** `REVIEW` — awaiting external architecture approval
**Supersedes:** None

## 1. Prompt / task performed

Design the complete technical architecture for **BusinessIQ — AI Business Intelligence,
Strategic Analysis & Decision Support**, a Claude plugin. Explicitly scoped as an
architecture gate: inspect the repository, determine the real Claude/plugin environment and
its supported capabilities, design the architecture and governance structure, identify
limitations and unsupported requirements, and produce an architecture report for external
review. Explicitly **not** to implement the plugin, activate it, deploy it, connect real
accounts, add credentials, or make destructive changes. Any files created were to be limited
to project-governance and documentation.

## 2. Objective

Establish a verified, buildable architecture and the governance machinery (instructions,
architecture record, plan, history, decisions, report format) that all later milestones run
on — with every platform claim grounded in an actual probe rather than assumption.

## 3. Changes made

### Phase 1 — Repository inspection

Repository was effectively empty: `.gitignore` only, plus `.git`. Contrary to the session's
environment banner ("Is a git repository: false"), it **is** a git repository — on `main`,
clean, one commit (`8d52b0e Initial BusinessIQ plugin setup`), remote
`https://github.com/conceptwebworld26/BusinessIQ`, tracking `origin/main`. No package
manifest, no source, no configuration, no CI.

### Phase 2 — Environment probing

Rather than assume plugin conventions, the real tooling and four installed plugins were
inspected: `marketing@knowledge-work-plugins` (8 skills, 13 MCP servers, no commands),
`superpowers@claude-plugins-official` (14 skills, hooks, marketplace manifest),
`feature-dev` (1 command, 3 agents), `code-review` (1 command).

Findings — all verified, not assumed:

| Area | Finding |
|---|---|
| CLI | Claude Code 2.1.263; `claude plugin validate/details/init/eval/tag` all present |
| Manifest | `.claude-plugin/plugin.json`, schema `https://anthropic.com/claude-code/plugin.schema.json` |
| Auto-discovery | `commands/`, `skills/<name>/SKILL.md`, `.mcp.json`, `hooks/hooks.json` are found without manifest entries — validated `--strict` |
| **Agents constraint** | `"agents": ["./agents"]` **fails** with `agents.0: Invalid input`; individual `.md` paths pass. Found by direct experiment. |
| Eval hook | `experimental.evals` accepted by the validator |
| Skill frontmatter | `name`, `description`, `argument-hint`, `user-invocable` |
| Command frontmatter | `description`, `argument-hint`, `allowed-tools`, `disable-model-invocation`, `hide-from-slash-command-tool` |
| Agent frontmatter | `name`, `description`, `tools`, `model`, `color` |
| Token cost | `marketing` ~872 tok always-on / 8 skills; `code-review` ~20 / 1 command; `feature-dev` ~238 / 1 command + 3 agents |
| **`plugin eval` gated** | Both `claude plugin eval` and `eval init` exit with "plugin eval is currently in early access" — not enabled on this account |
| Connector pattern | `marketing/CONNECTORS.md` uses `~~category` placeholders — tool-agnostic; adopted |

### Phase 3 — Runtime probing

| Runtime | Result |
|---|---|
| Python | 3.13.1 present — **stdlib only**; pandas, numpy, openpyxl, scipy, pyarrow, dateutil, duckdb all absent |
| Node / npm | 24.19.0 / 11.17.0 present |
| bun, uv | Absent |

### Phase 4 — Feasibility probe (the load-bearing one)

The riskiest assumption in the design was that Excel ingestion is possible with zero
dependencies. A probe (`scratchpad/xlsx_probe.py`) built a valid `.xlsx` with `zipfile` and
then read it back using only `zipfile` + `xml.etree.ElementTree`. It correctly recovered
sheet names, resolved shared strings, returned typed cells, and converted Excel serial
`45000` → `2023-03-15` (handling the 1900 leap-year bug). **Verified feasible.**

Not covered by the probe, and therefore scheduled as Milestone 2 work rather than left as an
open question: `styles.xml` number-format parsing to distinguish date cells from plain
numbers, inline strings, the 1904 date system, formula cells, and streaming for large
workbooks.

### Phase 5 — Connector availability survey

The 466 KB local plugin catalogue was searched for MCP servers for all sixteen named
systems. Only **HubSpot** and **Slack** have verified endpoints. Nothing was found for
QuickBooks, Xero, Google Sheets, Google Drive, Excel/OneDrive or Salesforce; NetSuite,
Shopify, Stripe and the databases appear only as developer-tooling skill packages, not
business-data servers. This materially changes what v1 can deliver (risk R-02) and makes the
file-upload path load-bearing rather than a fallback.

### Phase 6 — Architecture design and documentation

Designed a five-layer architecture (Foundation → Data → Analytics/Intelligence → Synthesis →
Orchestration) over a deterministic compute engine: 25 skills, 17 thin commands, 3
subagents. Wrote the governance set and seven ADRs.

## 4. Files created

```
CLAUDE.md
architecture.md
project_plan.md
docs/README.md
docs/templates/task-report.md
docs/templates/dev-record.md
docs/templates/adr.md
docs/decisions/README.md
docs/decisions/ADR-0001-claude-code-plugin-platform.md
docs/decisions/ADR-0002-deterministic-compute-engine.md
docs/decisions/ADR-0003-commands-orchestrate-skills-hold-logic.md
docs/decisions/ADR-0004-capability-based-connector-abstraction.md
docs/decisions/ADR-0005-seven-class-evidence-ledger.md
docs/decisions/ADR-0006-three-subagents-not-eight.md
docs/decisions/ADR-0007-two-layer-testing-strategy.md
docs/development/2026-09-08-milestone-0-architecture-gate.md   (this file)
```

Plus empty directories: `docs/architecture/`, `docs/testing/`, `docs/integrations/`,
`docs/skills/`, `docs/commands/`, `docs/agents/`, `docs/examples/`, `docs/troubleshooting/`.

## 5. Files modified

None. `.gitignore` was read but left untouched.

## 6. Files deleted

None in the repository. Outside it, a throwaway `sample-probe` plugin scaffolded into
`~/.claude/skills/` to learn the canonical layout was removed immediately after inspection.
Probe artifacts (`xlsx_probe.py`, `probe.xlsx`, a validation probe plugin) remain in the
session scratchpad, outside the repository.

## 7. Features implemented

None. This was an architecture and governance milestone by design — no plugin components,
no engine code, nothing user-reachable.

## 8. Tests performed

No software tests, because no software was written. The following **verification probes**
were executed:

```
claude plugin validate <probe> --strict     # agents-as-directory  -> FAILED (expected)
claude plugin validate <probe> --strict     # agents-as-file-paths -> PASSED
claude plugin validate <probe> --strict     # auto-discovery + experimental.evals -> PASSED
claude plugin details marketing@knowledge-work-plugins
claude plugin details code-review@claude-plugins-official
claude plugin details feature-dev@claude-plugins-official
claude plugin eval --help ; claude plugin eval init --bare smoke
python xlsx_probe.py
python -c "import pandas, numpy, openpyxl"
```

## 9. Test results

| Probe | Result |
|---|---|
| Manifest with `"agents": ["./agents"]` | `✘ agents.0: Invalid input` — directory form rejected |
| Manifest with explicit agent file paths | `✔ Validation passed` |
| Manifest relying on auto-discovery + `experimental.evals` | `✔ Validation passed` |
| `plugin details` × 3 | Token-cost model captured (see Phase 2) |
| `claude plugin eval` / `eval init` | `plugin eval is currently in early access` — **unavailable** |
| `xlsx_probe.py` | `sheets: ['Sales']` · `header: ['Date','Customer','Revenue']` · `date parsed: 2023-03-15` · `number typed: 15250.75 float` · `stdlib-only xlsx read OK` |
| `import pandas` | `ModuleNotFoundError` — confirms stdlib-only constraint |

**No BusinessIQ test suite exists yet.** Nothing in this milestone should be read as a
passing product test.

## 10. Issues discovered

| ID | Issue |
|---|---|
| R-01 | `claude plugin eval` is early-access gated on this machine — behavioural evals can be authored but not executed here |
| R-02 | No verified MCP servers for accounting, spreadsheet, commerce or database categories; only HubSpot (CRM) and Slack (chat). Section 23 of the requirement cannot be delivered as written |
| R-03 | Python is not guaranteed on every end-user machine; a runtime probe with a documented degradation path is required in M2 |
| R-04 | xlsx edge cases (number formats/date cells, inline strings, 1904 dates, formulas, streaming) not yet handled |
| R-05 | Always-on token budget (~3.4k projected against a 4k ceiling) is a hard design constraint on component count |

Also noted: the session banner reported "Is a git repository: false" while the directory is
in fact a git repository with a remote. Cosmetic, but worth knowing before relying on the
banner.

## 11. Decisions made

ADR-0001 through ADR-0007 — see `docs/decisions/`. In brief: Claude Code plugin using only
verified conventions; deterministic stdlib-only compute engine with no model arithmetic for
reported figures; commands orchestrate while skills hold all logic; capability-based
connector abstraction with no invented endpoints; seven-class evidence ledger; three
subagents rather than eight; fixture tests primary with evals secondary.

## 12. Architecture changes

`architecture.md` created — this is the initial architecture, so there is no prior state to
diff against.

## 13. Project-plan updates

`project_plan.md` created. Milestone 0 tasks moved to `COMPLETED` except external review,
which is `REVIEW` and blocking. Milestones 1–13 are `PLANNED`. Risks R-01 to R-05 registered;
R-01 `BLOCKED` (external), `.mcp.json` population `BLOCKED` behind the Connector gate.

## 14. Documentation updates

Entire governance set created: `CLAUDE.md`, `architecture.md`, `project_plan.md`, the `docs/`
tree with its index, three templates, an ADR system with its README and seven records, and
this development record.

## 15. Remaining work

Everything after the gate. Immediately next, subject to approval: **Milestone 1 — Plugin
Skeleton & Foundation Skills** (manifest + marketplace entry, README/LICENSE/CONNECTORS,
config defaults and resolver, the five Layer-0 skills, the `tests/run_tests.py` harness, and
a first measurement of always-on token cost against the 4k ceiling).

## 16. Git commit reference

Branch `main`. No commit made — `CLAUDE.md` section 10 requires that commits happen only on
request. All sixteen new files are uncommitted in the working tree. Nothing pushed.
