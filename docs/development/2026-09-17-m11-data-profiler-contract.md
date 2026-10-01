# 2026-09-17 — M11 `biq-data-profiler` contract / architecture review

**Milestone:** 11 — Subagents (remaining two): `biq-data-profiler` contract
**Status on completion:** COMPLETED (DECISION ONLY) — Milestone 11 stays `IN PROGRESS`; profiler implementation `PLANNED`
**Supersedes:** None

## 1. Prompt / task performed

"Perform M11 — `biq-data-profiler` Contract / Architecture Review for BusinessIQ. This is a decision-only /
contract-definition milestone." Make the profiler implementation-ready without implementing it: define what it
does and does not do, its inputs, its `DataProfileResult` output, fact semantics (observed / calculated /
inferred), relationships to M3, M4, KPIs, Business Context and synthesis, provenance, privacy, whether an agent
is needed, tools, model limits, large data, determinism, source binding, identity, staleness, failure states,
re-entry, the exact implementation surface, and what stays outside M11. At most one ADR (ADR-0036). No
implementation, agent, skill, command, production code, profiler schema or profiler test; no edit to ADR-0002,
ADR-0006, ADR-0014 or ADR-0031–0035; no change to the M11 verification implementation; no forecast translator;
no live research; no commit or push.

## 2. Objective

Settle the profiler contract against the repository as it stands at `d388ccd`, reusing every existing home
(ADR-0012) and keeping raw data out of every model context.

## 3. Changes made

1. Read the profiler's existing definition: ADR-0006 (context-isolation subagent, file access, no web),
   ADR-0014 (stays in M11), `architecture.md` §4 (`biq-data-ingestion` → `dataset.json` + `profile.json`), §5,
   §9 step 4, §10, §13 (`profile` schema listed), §16, §17, and `reference/analysis-framework.md`.
2. Read what already computes profile-like facts: `ingest/workbook.inspect()` (`WorkbookFacts`),
   `ingest/readers.read()` (one sheet per `Dataset`, hidden sheets only when named), `normalize.profile_column()`
   (kind and ambiguity from the first 1,000 values), `ingest/canonical.build()` (100,000-row mode threshold),
   `privacy/sensitivity` (200-value sample), `privacy/classes`, `privacy/aggregation`, `analytics/presentation`,
   `mapping/semantic` (AUTO / CONFIRM thresholds, roles), `quality/contract`, `quality/checks.run()`,
   `quality/report` (grade, halted), `kpi/engine._calculate_one` and `kpi/contract.BUCKETS`,
   `commands/registry` (declared `required_roles`) and `commands/runner` (inline role check, source SHA-256,
   `config_digest`, `SOURCE_CHANGED`), `synthesis_set.register_claims()`.
3. Found the central tension: ADR-0006 justified a file-scanning subagent by the size of raw scan output, but
   since M2/M3 the engine turns bytes into bounded structure and no raw output reaches a model. A subagent for
   local files would isolate nothing, and one reading files with `Read`/`Bash` would put raw rows in a model
   context and let the model author facts.
4. Wrote ADR-0036 choosing a deterministic profiler (Option D over three subagent designs). While writing it,
   corrected three drafting assumptions against the code:
   - KPI availability is decided inside each calculator; there is no precondition-only entry point. The
     contract therefore keeps only the status bucket from `kpi.engine.calculate()` and discards values, rather
     than extracting or copying calculator logic.
   - The command role check is inline in `runner.run()`. The contract reports declared roles and mapping status
     and explicitly does not predict a command's outcome.
   - Tier 4 means no Python, so no profile can exist there; Tier-3 refusals (§5 rule 2) become a
     `reader_refused` source status rather than a "no reader" code.
   Aligned the implementation surface with names the architecture already holds: the `profile` schema (§13)
   and the `biq-data-ingestion` skill (§4), keeping the skill count at 20. Added an explicit layering rule
   (composition module beside `pipeline.py`, downward imports only).
5. Updated the decisions index, docs index, `architecture.md` and `project_plan.md`; wrote this record.

## 4. Files created

- `docs/decisions/ADR-0036-biq-data-profiler-contract.md`
- `docs/development/2026-09-17-m11-data-profiler-contract.md`

## 5. Files modified

- `architecture.md` — §5 data-profile contract paragraph; §8 least-privilege sentence; §10 intro and
  `biq-data-profiler` row (deferred); §17 large-data row; §19 decision table row 0036.
- `project_plan.md` — summary row 11; M11 status paragraph; the `biq-data-profiler · PLANNED` section replaced
  by `biq-data-profiler contract · COMPLETED (DECISION ONLY)` and `biq-data-profiler implementation · PLANNED
  (next)`.
- `docs/decisions/README.md` — index row 0036; "Amended / refined" note for ADR-0006.
- `docs/README.md` — ADR list entry.

## 6. Files deleted

None.

## 7. Features implemented

None. Decision only.

## 8. Tests performed

- `python tests/run_tests.py`
- `claude plugin validate . --strict`
- `git diff --check`

## 9. Test results

| Check | Result |
|---|---|
| Full suite | **ran 4,475, failures 0, errors 0, skipped 26** (`OK (skipped=26)`) — matches the baseline; nothing added |
| `claude plugin validate . --strict` | `✔ Validation passed` |
| `git diff --check` | exit 0, no whitespace errors (tracked files); the two new files checked separately for trailing whitespace, tabs and NUL bytes: none |

No profiler test was added (instructed).

## 10. Issues discovered

- ADR-0006's profiler justification no longer holds for local files (resolved by ADR-0036 as a refinement,
  without editing ADR-0006).
- `architecture.md` §17 already says the engine "streams" above 100,000 rows while M3 recorded true chunked
  streaming as deferred. The profiler contract neither implements nor relabels streaming; the pre-existing
  wording was not otherwise changed (out of scope).
- `docs/development/README.md` does not list records after M9-B. That is pre-existing index debt, left
  untouched as instructed.
- Skill frontmatter cannot restrict tools, so the skill's instruction not to open sources is advisory; the
  contract places the privacy guarantee on the value-free output plus a canary test (ADR-0036 §14).

## 11. Decisions made

[ADR-0036 — The data profiler contract](../decisions/ADR-0036-biq-data-profiler-contract.md), Accepted.

## 12. Architecture changes

The profiler moves from a planned file-scanning subagent to a planned deterministic capability. The subagent
stays allocated and deferred to model-mediated sources (M12). No built component changed.

## 13. Project-plan updates

- `biq-data-profiler` contract: `PLANNED` → `COMPLETED (DECISION ONLY)`.
- `biq-data-profiler` implementation: `PLANNED` (next).
- Milestone 11: stays `IN PROGRESS`. Verification and finalisation remains `COMPLETED`.

## 14. Documentation updates

As listed in §5. No change to `CLAUDE.md`, `README.md`, `reference/`, skills, commands or agents docs; the
output standards are unaffected because a profile is not a report.

## 15. Remaining work

Profiler implementation per ADR-0036 "Follow-up required". Outside M11: the subagent for connector catalogues
(M12), chunked streaming (Data Layer deferral), a synthesis forecast translator (separate decision).

## 16. Git commit reference

N/A — not committed (instructed). Branch `main`, base `d388ccd`.
