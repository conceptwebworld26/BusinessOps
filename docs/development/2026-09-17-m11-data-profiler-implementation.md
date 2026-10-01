# 2026-09-17 — M11 `biq-data-profiler` implementation

**Milestone:** 11 — Subagents (remaining two): `biq-data-profiler` implementation (ADR-0036)
**Status on completion:** COMPLETED — Milestone 11 `COMPLETED`; the connector-catalogue subagent is Milestone 12 work
**Supersedes:** None

## 1. Prompt / task performed

"Implement M11 — biq-data-profiler according to the accepted contract in ADR-0036." Surface: new
`lib/python/biq/data_profile.py`, new `lib/schemas/profile.schema.json`, the existing skill location
`skills/biq-data-ingestion/SKILL.md`, the `register_claims()` refusal, focused tests and materially affected
documentation. No agent, MCP server, connector, command, forecast translator, M12 work, chunked streaming,
live research, source-data change, ADR edit, commit or push.

## 2. Objective

Build the deterministic local-file data profile exactly as ADR-0036 defines it, reusing the Data Layer, Data
Quality, the KPI engine and the command registry rather than duplicating them.

## 3. Changes made

1. Verified the starting state: `main` at `72f74dc`, equal to `origin/main`, clean, no operation in progress.
2. Read the contract and every module it names: `ingest/workbook`, `ingest/readers`, `ingest/dataset`,
   `ingest/canonical`, `normalize`, `privacy/sensitivity`, `privacy/classes`, `privacy/aggregation`,
   `analytics/presentation`, `mapping/semantic`, `quality/checks`, `quality/report`, `quality/contract`,
   `kpi/registry`, `kpi/engine`, `kpi/contract`, `kpi/primitives`, `commands/registry`, `commands/runner`,
   `context/loader`, `pipeline`, `synthesis/synthesis_set`, `verification` (construction-token pattern) and
   the workbook fixture builders.
3. Wrote `data_profile.py`:
   - `validate_request()` accepts exactly `sources`, `sheets`, `objective`, `presentation` and refuses
     everything else whole.
   - `build()` resolves Business Context and configuration exactly as `pipeline.run()` does and computes
     the configuration digest as `commands/runner` does. It then hashes and inspects every source before
     any cell is read (a named sheet that does not exist refuses the request), reads each planned sheet
     through `readers.read()`, re-hashes, and profiles each dataset.
   - Per dataset it runs `canonical.build()`, `mapping.infer()` and `quality.checks.run()`, then
     `kpi.registry.calculate()` when an objective names KPIs or a command.
   - Content-addressed refs `src-`, `dst-`, `col-` and the `dpr-` id; a construction token; no setter.
   - Serialisation re-hashes every bound source and refuses when any changed.
4. Wrote the closed schema `profile.schema.json` (the `profile` schema `architecture.md` §13 already lists).
5. Extended `SynthesisSet.register_claims()` with `_is_data_profile()`.
6. Created `skills/biq-data-ingestion/SKILL.md`, the architected Layer 1 skill, for local files only.
7. Wrote 80 focused tests, fixed two defects they found (below), and ran a mutation check: a canary
   injected into `render()` made the privacy test fail, and the module was restored.
8. Updated `project_plan.md`, `architecture.md`, `README.md`, `docs/skills/README.md`; wrote this record.

## 4. Files created

- `lib/python/biq/data_profile.py`
- `lib/schemas/profile.schema.json`
- `skills/biq-data-ingestion/SKILL.md`
- `tests/unit/test_m11_data_profiler.py`
- `docs/development/2026-09-17-m11-data-profiler-implementation.md`

## 5. Files modified

- `lib/python/biq/synthesis/synthesis_set.py` — `import re`; `_DATA_PROFILE_*` constants;
  `_is_data_profile()`; a refusal branch in `register_claims()` ahead of the existing ones.
- `project_plan.md` — summary row 11 and the Milestone 11 heading to `COMPLETED`; status paragraph; the
  implementation section.
- `architecture.md` — §5 "Contract defined; not yet built" → "Built"; §13 tree line for `data_profile.py`.
- `README.md` — a user-facing paragraph on profiling; the `agents/` line in the architecture sketch.
- `docs/skills/README.md` — a data-layer skill section.

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | User-reachable |
|---|---|---|
| Deterministic data profile | `lib/python/biq/data_profile.py` | Yes, through the skill |
| Closed profile schema | `lib/schemas/profile.schema.json` | Via `data_profile.validate_document()` |
| Profile re-entry refusal | `lib/python/biq/synthesis/synthesis_set.py` | Structural |
| Local-file profiling skill | `skills/biq-data-ingestion/SKILL.md` | Yes |

## 8. Tests performed

- `python tests/run_tests.py unit.test_m11_data_profiler`
- `python tests/run_tests.py` (full suite)
- `claude plugin validate . --strict`
- `git diff --check`

## 9. Test results

| Check | Result |
|---|---|
| `unit.test_m11_data_profiler` | ran 80, failures 0, errors 0, skipped 0 |
| Regression suites run individually | `unit.test_ingest` 31, `unit.test_engine_m3` 77, `integration.test_data_layer` 29 (7 skipped, pre-existing), `integration.test_quality_m4` 48, `integration.test_quality_adversarial` 27, `integration.test_kpi_engine` 76, `unit.test_command_registry` 40, `unit.test_m10_1_synthesis` 36, `unit.test_m10_1_synthesis_policy` 57, `unit.test_m10_1_synthesis_security` 33, `unit.test_m10_2r_retrieval_seam` 24, `unit.test_m10_2r_provenance_footing` 31, `unit.test_m10_2r14_local_join` 105, `unit.test_m10_3_1_swot` 117, `unit.test_m10_3_2_strategy` 123, `unit.test_m10_3_3_decision_support` 103, `unit.test_m10_3_4_executive_report` 73, `unit.test_m11_verification` 47, `unit.test_m11_verification_server` 8, `unit.test_m11_verifier_agent_boundary` 12 (7 runtime opt-in skipped) — all 0 failures, 0 errors |
| Full suite (final tree) | **ran 4,555, failures 0, errors 0, skipped 26** (`OK (skipped=26)`): the 4,475 baseline plus 80; skips unchanged |
| `claude plugin validate . --strict` | `✔ Validation passed` |
| `git diff --check` | exit 0 |
| Privacy mutation check | a canary injected into `render()` failed `Privacy` (1 failure of 6); the module was restored and `Privacy` passed again (6/6) |

The runtime agent-boundary tests (opt-in, real nested sessions) were not re-run: the verifier, its server
and its agent are unchanged.

## 10. Issues discovered

- **Implementation defects found by the focused tests and fixed:**
  - A mock in the changed-during-read test recursed, because `data_profile.readers` is the `readers`
    module itself.
  - The applicability wrapper `{command, kpis}` and a command entry `{command_id, required_roles}`
    carried none of ADR-0036's seven profile-only field names, so `register_claims()` accepted them.
    The refusal now also recognises profile ref values (`dpr-`/`src-`/`dst-`/`col-` + 12 hex),
    the profile fact shape (`basis` observed/calculated/inferred beside `examined`) and the two further
    profile-only fields `required_roles` and `overlap_rate`, and it recurses into nested records.
    This extends ADR-0036 §11's list in the same direction; nothing it already refused is now accepted.
- **Reader refusals arrive as messages.** The Data Layer raises `ConfigError` with text, not codes. The
  profiler maps known fragments to the closed reason codes through one table (`_READER_REASONS`) after
  removing quoted names. The message is never carried, anything unrecognised is `unreadable`, and a
  test pins each entry against the real reader. `unsupported_encoding` cannot occur through the CSV
  reader today (its Latin-1 fallback decodes any bytes); the mapping is tested directly.
- **Contract interpretations resolved from repository conventions (no ADR contradiction):**
  - `restricted`/`never` columns report name, kind, class and counts only. They withhold `role`,
    `currencies`, `day_first` and `date_coverage`, may still be a `unique_non_null` key candidate, are
    never a `mapped_role` candidate, and join no overlap. Command entries therefore report role status
    without a column ref.
  - Dataset-level facts keep ADR-0036's field names, each as a `{value, basis, operation, examined}`
    fact, so every fact carries its basis.
  - `duplicate_headers` lists positions, not names, so a `never`-classed name cannot reappear in
    shareable output.
  - `request` shows sources by `source_ref`, never by path, so shareable output and the id are
    location-independent; `source_path` appears in `local` presentation only.
  - Distinct counts and overlap use M3's normalised values (`canonical.normalized_rows()`), and so do
    non-null and empty counts, so one representation (with M3's missing vocabulary) underlies every
    count.
  - A KPI status comes from `kpi.registry.calculate()`, the call the pipeline makes, which delegates to
    `kpi.engine.calculate()`.
  - Hashing and canonical JSON are imported from `commands/runner` (named by ADR-0036), not duplicated.
  - Limitations are listed once per subject in discovery order; `sampled_inference` is per dataset.
- **Residual:** in `shareable` presentation M3's sensitivity reasons are carried verbatim and can include
  small sampled-value counts ("3 of 3 sampled values"); they are counts, never values.
- **Not exercised:** workbook reads at Tiers 1 and 2 (openpyxl is not installed on this machine). Tier 3
  and Tier 4 were exercised.

## 11. Decisions made

None new. Implements ADR-0036. No ADR created or edited.

## 12. Architecture changes

None beyond marking the ADR-0036 data profile built (`architecture.md` §5) and listing `data_profile.py`
in §13.

## 13. Project-plan updates

- `biq-data-profiler` implementation: `PLANNED` → `COMPLETED`.
- Milestone 11: `IN PROGRESS` → `COMPLETED` (as the plan recorded: "M11 is `COMPLETED` only when this
  lands"). The `biq-data-profiler` agent for connector catalogues remains Milestone 12 work.

## 14. Documentation updates

| File | Status | Reason |
|---|---|---|
| `project_plan.md` | UPDATED | Status and evidence |
| `architecture.md` | UPDATED | §5 built; §13 module listed |
| `README.md` | UPDATED | New user-facing capability; subagent count line |
| `docs/skills/README.md` | UPDATED | New skill indexed |
| `CLAUDE.md` | NOT REQUIRED | No governance change; skill count remains 20 |
| `docs/decisions/README.md`, `docs/README.md` ADR list | NOT REQUIRED | No new ADR |
| `docs/agents/README.md` | NOT REQUIRED | No agent added or changed |
| `docs/commands/README.md` | NOT REQUIRED | No command added |
| `reference/analysis-framework.md` | NOT REQUIRED | Step 4 "ingestion / data-profiler" remains accurate |
| `reference/output-standards.md` | NOT REQUIRED | A profile is not a report |
| `docs/development/README.md`, `docs/README.md` record list | DEFERRED | Pre-existing index gaps since M7/M9-B; out of scope |

## 15. Remaining work

Milestone 12: the connector layer, including any `biq-data-profiler` agent for connector catalogues under
its own contract. Outside M11: chunked streaming (Data Layer), a synthesis forecast translator.

## 16. Git commit reference

N/A — not committed (instructed). Branch `main`, base `72f74dc`.
