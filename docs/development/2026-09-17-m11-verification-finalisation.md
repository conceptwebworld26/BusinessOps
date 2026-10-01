# 2026-09-17 — M11: Verification and finalisation

**Milestone:** 11 — verification and finalisation implementation (ADR-0034, ADR-0035)
**Status on completion:** COMPLETED
**Supersedes:** None. The M11-A records (`2026-09-17-m11-a-verification-finalisation-contract.md`,
`2026-09-17-m11-a-contract-alignment-remediation.md`) described the platform facts as unmeasured; §2 below
records the measurement, and those records are left intact.

## 1. Prompt / task performed

Implement M11 exactly as ADR-0034 and ADR-0035 accepted it: a deterministic verifier with blind
recomputation through one local MCP tool held by a single-tool agent, findings without values,
finalisation that changes lifecycle only, the run registry, re-entry protection, schemas, orchestration,
focused tests including the load-bearing agent-boundary test, and documentation. No ADR edit, forecast
translator, live research, unrelated MCP server, generic tool runner, business-data write, commit or push.

## 2. Baseline and measured platform facts

| Fact | Value |
|---|---|
| HEAD | `2696a7954838ac58c370b71c0083c6a780f2b831` = `origin/main`; clean tree |
| Last full run | 4,408 tests, 0 failures, 0 errors, 19 skipped |

**Platform feasibility (M11-A gate, measured before this milestone; re-measured here).** All required facts
A–I passed:

| # | Fact | Result |
|---|---|---|
| A | A plugin `.mcp.json` stdio server launches | PASS |
| B | The tool name is `mcp__plugin_<plugin>_<server>__<tool>` — here `mcp__plugin_businessiq_biq-verifier__recompute` | PASS |
| C | An agent whose `tools` names only that tool is restricted to it | PASS, with the caveat below |
| D | The tool accepts exactly one closed argument; others are refused server-side | PASS |
| E | The tool returns a deliberately closed envelope | PASS |
| F | The agent's model context holds only the id and the envelope | PASS |
| G | Tool, path and command substitution are blocked | PASS |
| H | `claude plugin validate . --strict` accepts the architecture | PASS — **but not evidence**: strict validation also passed an agent with `tools: 42` and a `.mcp.json` without a command |
| I | The Connector gate covers the local server | PASS — explicit approval obtained for the exact entry |

**Caveat on C.** A literal "No such tool available: Bash" error for the restricted agent was never
captured: both Haiku and Sonnet decline to emit calls for tools absent from their definitions. The evidence
is structural — a controlled agent without the `tools` field executes Bash, Read, Glob, ToolSearch and a
decoy MCP tool in the same session configuration; the restricted agent executes none of them; the platform
logs `ToolSearchTool is not available` for the restricted agent's requests only; the decoy server's own log
shows no call. `tests/unit/test_m11_verifier_agent_boundary.py` now re-measures this at runtime.

**The measured evidence, in detail** (M11-A feasibility gate, Claude Code 2.1.274, a throwaway scratch
plugin and synthetic canary files, all deleted afterwards; not committed at M11-A by design):

| Fact | What was run | What was observed |
|---|---|---|
| A — stdio launch | Scratch plugin, `.mcp.json` `{"type": "stdio", "command": "python", "args": ["${CLAUDE_PLUGIN_ROOT}/server.py"]}`, loaded with `--plugin-dir` | Debug log "Successfully connected (transport: stdio)"; session init status `connected`; `${CLAUDE_PLUGIN_ROOT}` expanded; server named `plugin:<plugin>:<server>` |
| B — tool name | Session init tool list | `mcp__plugin_biqprobe_probe-verifier__recompute` for the probe; `mcp__plugin_businessiq_biq-verifier__recompute` measured directly on an exported copy of HEAD with the production-shaped entry |
| C — one-tool agent | Same model, prompt and session permissions (Bash, Read, Glob, Write and both decoy MCP tools permitted), agent with and without `tools` | Control agent **executed** `cat` and `Read` on a decoy file (content returned), `Glob` over the sealed request directory (both request paths listed), a second tool on the same server (via ToolSearch) and a tool on another server; its `Write` was blocked only by a permission heuristic ("suspicious Windows path pattern"), i.e. by convention. Restricted agent executed only `recompute`; the decoy servers logged no call; the platform logged `ToolSearchTool is not available` for the restricted agent's requests only |
| D — closed input | Eleven argument shapes sent to the server over JSON-RPC: extra `source_path`, `command`, `url`, `config`, `figure`; shell syntax; path traversal; absolute path; non-string; missing; non-object | Every one returned `request_id_invalid`; the server log shows the raw arguments reached the server, so enforcement is server-side, not a client schema check |
| E — closed output | The same calls, plus a forced internal exception whose text held a canary | Exactly `{protocol, request_id, status, record_id, error_code}` in one text block every time; the exception returned `execution_error` with no text; a stderr canary stayed on stderr |
| F — model visibility | Production-shaped run: the agent given only the request id; canaries planted in the source file, the request file, the source path, a figure value, server stderr and exception text | **0 hits** across the stream output, both persisted main transcripts, the persisted subagent transcript and the debug log; the subagent's only user turn was the request id; the control run *did* hit its canaries, so the scan works |
| G — substitution | Restricted agent told to use Bash, Read, other MCP tools, ToolSearch, paths and commands | None reached; injection and path strings refused by the server |
| H — strict validation | `claude plugin validate --strict` on the probe, on HEAD with the server and agent added, and on a plugin with `tools: 42`, an unknown agent field and a `.mcp.json` with no command | All passed — so strict validation checks neither agents nor `.mcp.json` and is **not** security evidence. (The plugin-manifest form fails only on the pre-existing root `CLAUDE.md` warning, R-08) |
| I — Connector gate | `CLAUDE.md` §13 ("any MCP server"), `architecture.md` §11 | Covered by the existing gate; explicit approval for the exact entry was obtained at the start of this milestone |

Also observed at the gate: the platform injects the working directory, date, user email, model and other
plugins' MCP *instructions* (not their tools) into a subagent's context, none of it business data; a failing
MCP server's stderr is copied into Claude Code's debug log; two servers with identical command and arguments
are de-duplicated; a server can report `failed` briefly after a crash before a later launch connects.

**New facts measured in this milestone.** The plugin's server resolves `./.businessiq/verification/` from the
session's project directory, the same directory `verify()` resolves; a main-thread model may wrap the relayed
envelope in one markdown code fence, which `verify()` unwraps and nothing else; `--allowedTools`,
`--mcp-config` and `--agents` are variadic, so a nested session's prompt must follow `-p` directly.

## 3. Changes made

1. **Connector gate.** Stopped before `.mcp.json` and obtained explicit approval for the exact entry
   (`biq-verifier`, `stdio`, `python`, `${CLAUDE_PLUGIN_ROOT}/lib/python/biq/verification_server.py`). The
   approval treats `args` as server identity under `CLAUDE.md` §7; no token, URL or secret.
2. **Run registration.** `commands.run()` hashes the source before and after the run, and records
   `source_path`, `source_sha256`, `run_arguments`, `config_digest` and a content-addressed `run_id`; a source
   that changes during the run makes it `unavailable` with no basis. `SynthesisSet` gains a run registry
   (`register_run`, `bind_run`, `check_run_binding`, `run_for`, `registered_runs`) included in `as_dict()`.
   `commands.internal_statements()` binds every finding and KPI to its run and `commands.kpi_statements()`
   registers all of a run's KPIs in catalogue order; every refusal happens before anything is registered.
3. **Retained inputs.** `StrategyResult.proposals`, `DecisionResult.request`/`config`, and the report's
   `request`, `config`, `strategy_result`, `swot`, `decision_results` views.
4. **Engine** `lib/python/biq/verification.py`. The 46-check catalogue in the ADR-0034/0035 order; located
   findings with reference and comparison code only; deterministic ordering; content-addressed
   `verification_id`; `finalise()` returning final objects that re-prove the draft digest on every
   serialisation; the fixed `recompute_request()` operation.
5. **Server** `lib/python/biq/verification_server.py`, **agent** `agents/biq-analysis-verifier.md`,
   **`.mcp.json`**.
6. **Schemas.** New `verification.schema.json`; `decision_support` and `executive_report` admit `final`
   through closed `oneOf` branches, mirrored and pinned.
7. **Re-entry.** `register_claims()` refuses verification artifacts and fields.
8. **Orchestration.** `--final` in both commands; both skills document the flow; the executive-report
   skill's KPI path now uses `commands.kpi_statements()`.
9. **Tests**, **guard amendments** (§8), then documentation (§14).

Defects found and fixed during the milestone, before any test was recorded as passing: a refused run
registration partially mutated the set; interpretations were treated as engine-footed figures; raw report
structures were compared with JSON-loaded rebuilds; the server silenced streams at import time; digest
checks reported `passed` when every run was unusable (now `not_run`); a relay wrapped in a code fence was
refused; the runtime test harness swallowed its prompt, passed vacuously, shared decoy evidence across
sessions and mis-encoded its cleanup glob.

## 4. Files created

- `lib/python/biq/verification.py`, `lib/python/biq/verification_server.py`
- `lib/schemas/verification.schema.json`
- `agents/biq-analysis-verifier.md`, `.mcp.json`
- `tests/unit/test_m11_verification.py`, `tests/unit/test_m11_verification_server.py`,
  `tests/unit/test_m11_verifier_agent_boundary.py`
- `docs/agents/biq-analysis-verifier.md`
- `docs/development/2026-09-17-m11-verification-finalisation.md` (this record)

## 5. Files modified

- `lib/python/biq/commands/runner.py`, `commands/joins.py`, `commands/__init__.py` — run basis and binding
- `lib/python/biq/synthesis/synthesis_set.py` — run registry; re-entry refusal
- `lib/python/biq/strategy.py`, `decision_support.py`, `executive_report.py` — retained inputs; final packages
- `lib/schemas/decision_support.schema.json`, `executive_report.schema.json` — `final`
- `commands/executive-report.md`, `commands/decision-support.md` — `--final`
- `skills/biq-executive-report/SKILL.md`, `skills/biq-decision-support/SKILL.md` — finalisation flow
- `tests/unit/test_m10_2r14_local_join.py`, `test_m10_3_4_executive_report.py`,
  `test_research_scout_boundary.py` — guards amended
- `architecture.md`, `project_plan.md`, `README.md`, `docs/agents/README.md`, `docs/commands/README.md`,
  `docs/skills/README.md`

## 6. Files deleted

None in the repository. Temporary probe projects, nested-session transcripts and scratch verification
directories created by tests and probes were removed.

## 7. Features implemented

| Feature | Location | User-reachable |
|---|---|---|
| Verification and finalisation | `verification.py` | Yes, `--final` |
| Blind recomputation operation | `verification_server.py`, `.mcp.json` | Through `biq-analysis-verifier` only |
| Run registration | `commands.run()`, `SynthesisSet` | Internal |

## 8. Tests performed

```
python tests/run_tests.py unit.test_m11_verification
python tests/run_tests.py unit.test_m11_verification_server
python tests/run_tests.py unit.test_m11_verifier_agent_boundary
BIQ_AGENT_BOUNDARY_RUNTIME=1 python tests/run_tests.py unit.test_m11_verifier_agent_boundary
python tests/run_tests.py unit.test_m10_3_4_executive_report
python tests/run_tests.py unit.test_m10_3_3_decision_support
python tests/run_tests.py unit.test_m10_3_2_strategy
python tests/run_tests.py unit.test_m10_3_1_swot
python tests/run_tests.py unit.test_m10_1_synthesis_security
python tests/run_tests.py unit.test_command_registry
python tests/run_tests.py unit.test_m9d5_industry_research_command
python tests/run_tests.py unit.test_m10_2r14_local_join
python tests/run_tests.py unit.test_research_scout_boundary
python tests/run_tests.py
claude plugin validate . --strict
git diff --check
```

Guards amended, each with its reason recorded in the test: `test_research_scout_boundary` (the verifier agent
now exists; `biq-data-profiler` still must not); `test_m10_3_4_executive_report` (the schema admits `final` only
with `verified` and a record; `build()` still has no path to it); `test_m10_2r14_local_join` (the two
run-registration helpers join the function list; neither translates).

## 9. Test results

Runs made after the last code change (Python 3.13.1):

| Run | Result |
|---|---|
| `unit.test_m11_verification` | ran 47, failures 0, errors 0, skipped 0 |
| `unit.test_m11_verification_server` | ran 8, failures 0, errors 0, skipped 0 |
| `unit.test_m11_verifier_agent_boundary` (offline) | ran 12, failures 0, errors 0, skipped 7 (runtime opt-in) |
| `unit.test_m11_verifier_agent_boundary` with `BIQ_AGENT_BOUNDARY_RUNTIME=1` | **ran 12, failures 0, errors 0, skipped 0** |
| `unit.test_m10_3_4_executive_report` | ran 73, failures 0, errors 0, skipped 0 |
| `unit.test_m10_3_3_decision_support` | ran 103, failures 0, errors 0, skipped 0 |
| `unit.test_m10_3_2_strategy` | ran 123, failures 0, errors 0, skipped 0 |
| `unit.test_m10_3_1_swot` | ran 117, failures 0, errors 0, skipped 0 |
| `unit.test_m10_1_synthesis_security` | ran 33, failures 0, errors 0, skipped 0 |
| `unit.test_command_registry` | ran 40, failures 0, errors 0, skipped 0 |
| `unit.test_m9d5_industry_research_command` | ran 51, failures 0, errors 0, skipped 0 |
| `unit.test_m10_2r14_local_join` | ran 105, failures 0, errors 0, skipped 0 |
| `unit.test_research_scout_boundary` | ran 22, failures 0, errors 0, skipped 0 |
| `unit.test_manifest` | ran 15, failures 0, errors 0, skipped 0 |
| Full suite | **ran 4,475, failures 0, errors 0, skipped 26** (19 pre-existing + 7 opt-in runtime) |
| `claude plugin validate . --strict` | Validation passed — not evidence for the agent boundary |
| `git diff --check` | clean |

The runtime boundary run shows: the plugin's `biq-verifier` server connected and served
`mcp__plugin_businessiq_biq-verifier__recompute`; in production the agent made exactly one call, `recompute`
with only the request id, the relayed envelope verified `passed` in a separate process, and the whole production transcript held neither the source file's name, a source row nor any computed figure; told to use
Bash, Read, Glob, a decoy MCP tool, ToolSearch and extra arguments, the agent executed none of them, the decoy
server logged no call, the canary never appeared, and the platform logged ToolSearch unavailable for the
agent's requests; a control agent without the grant executed those tools under the same session
configuration.

## 10. Issues discovered

- **Process boundary.** Results bind live objects, so a finalisation spans two Python processes around the
  agent dispatch; the draft is rebuilt deterministically and `verify()` refuses a reply for any other draft.
- **Stricter registration.** Registering a KPI or finding from a different run into one set is now refused
  where M10 overwrote silently. No existing test depended on the overwrite.
- **`CLAUDE.md` §7 wording** lists `.mcp.json` identity as "type/url/command"; a stdio server needs `args`.
  Approved at the gate as identity; `CLAUDE.md` unchanged.
- **Period figures supplied by a caller** for a finding with no period of its own are shown but cannot be
  recomputed; such a statement fails `recomputation.statement` rather than passing unverified.
- **Runtime boundary evidence needs an account and network**; it is opt-in and reported separately.
- **Not fixed (pre-existing, unrelated):** the plan's milestone summary table and "Last updated" line; the
  missing scout page under `docs/agents/`.

## 11. Decisions made

None beyond ADR-0034 and ADR-0035. Implementation choices within them: `commands.kpi_statements()` as the
run-bound KPI path; one optional code fence unwrapped in a relay; recomputation checks `not_run` when no run
is usable; the Connector-gate approval of the exact entry.

## 12. Architecture changes

`architecture.md` §7 records the M11 contract as built with its enforcement and measured facts; §13 lists the
new modules, schema and the `.mcp.json` entry. No decided contract changed.

## 13. Project-plan updates

*M11 — Verification and finalisation implementation*: `PLANNED` → `COMPLETED`. Milestone 11 stays
`IN PROGRESS` (`biq-data-profiler`). The forecast translator stays a separate decision.

**Pre-checkpoint remediation (same day).** The milestone summary table still showed Milestone 11 as
`PLANNED`, contradicting its section. It now reads `IN PROGRESS` with the verification and finalisation work
`COMPLETED` and `biq-data-profiler` `PLANNED`, the heading paragraph says so plainly, and `biq-data-profiler`
has its own `PLANNED` entry. The milestone is not marked `COMPLETED` as a whole because the repository defines
`biq-data-profiler` as part of Milestone 11 (the plan's "Subagents (remaining two)"; ADR-0014: "remain in
Milestone 11"), and moving it would be an architecture change, not a status correction. The same review added
one runtime boundary assertion that the production transcript never carries the source file name, a source
row or a computed figure (the fact-F measurement, now permanent), and re-ran every suite (§9).

## 14. Documentation updates

As §5. `reference/output-standards.md` unchanged (its verification bullet already matches). `CLAUDE.md`
unchanged. ADR-0031 to ADR-0035 unchanged.

## 15. Remaining work

`biq-data-profiler`; a forecast translator (separate decision); a persisted verification record, if ever
needed (separate decision).

## 16. Git commit reference

N/A — nothing staged, committed or pushed.
