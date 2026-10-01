# 2026-09-17 — Executive Report implementation (ADR-0033)

**Milestone:** 10.3.4 implementation — `biq-executive-report` + `/executive-report`
**Status on completion:** COMPLETED
**Supersedes:** None

## 1. Prompt / task performed

Implement Executive Report exactly as ADR-0033 accepted it: an `ExecutiveReportResult` assembled over one
genuine strict `SynthesisSet`, with optional bound `StrategyResult`, `DecisionResult`s and SWOT; eleven
fixed sections with explicit empty states; a rule-selected executive summary; digest binding; draft-only
lifecycle; no recommendations, scores, targets or forecast bypass; re-entry closed; a thin command, a
skill, a closed schema, focused tests, registry changes and documentation. No commit, no push, no forecast
translator, no M11 verifier, no ADR change, no live research, no MCP change.

## 2. Baseline

| Fact | Value |
|---|---|
| HEAD | `adf04a64319502bc48c26ac9b2626e9826e34176` — *M10.3.4: Executive Report contract*; equal to `origin/main`; clean tree |
| Last full run | 4,335 tests, 0 failures, 0 errors, 19 skipped |

**Session recovery (same day).** The implementing session was interrupted by a laptop restart before its
task report. A second session recovered the state without discarding anything: HEAD and `origin/main` still
`adf04a6`, every uncommitted change belonging to this milestone (state B — partial, uncommitted, resumable).
It re-ran the suite over the recovered tree (4,406 tests, 0 failures, 0 errors, 19 skipped — the figure
recorded below was accurate), audited the implementation against ADR-0033 clause by clause, and closed the
two conformance gaps listed in §10. Everything else was kept as found.

## 3. Changes made

1. **Additive seams.** `SynthesisSet.registered_kpis()`, `registered_datasets()` and
   `registered_evidence_sets()` (read-only views of what the set registered; ADR-0033 follow-up list);
   `DecisionResult.strategy_result` (read-only). `register_claims()` now also refuses
   `analysis: executive_report` and records carrying report-only fields.
2. **Engine** `lib/python/biq/executive_report.py`: `build()`, `ExecutiveReportResult`, `render()`,
   `package_entry()`, `lifecycle_label()`.
3. **Schema** `lib/schemas/executive_report.schema.json`, generated so the Strategy, SWOT and Decision
   Support schemas are imported under prefixes and pinned by test.
4. **Command** `commands/executive-report.md` and **skill** `skills/biq-executive-report/SKILL.md`.
5. **Guards.** `executive-report` moved to built in `test_command_registry.py`
   (`UNBUILT_SYNTHESIS_COMMANDS` now empty; `UNBUILT_COMMAND` is a name that is not a command, asserted
   to have no command file), and the absence tests in the SWOT, Strategy, Decision Support and M9-D.5
   suites amended to assert the built surfaces instead.
6. **Focused tests**, then documentation.
7. **Recovery-session conformance fixes.** `executive_summary.availability` — the status of sections 3 and
   5–9, copied from those sections (ADR-0033 §4 item 7), so the summary is assembled after them; and
   each anomaly entry's resolved finding now carries `observed`, `baseline`, `deviation`, `deviation_pct`,
   `unit` and `currency` — the finding's own `observed`, `comparison`, `change` and `change_pct`, passed
   through unrounded (§6). Schema, `render()`, skill table and two focused tests follow.

## 4. Files created

- `lib/python/biq/executive_report.py`
- `lib/schemas/executive_report.schema.json`
- `skills/biq-executive-report/SKILL.md`
- `commands/executive-report.md`
- `tests/unit/test_m10_3_4_executive_report.py`
- `docs/development/2026-09-17-m10-3-4-executive-report.md` (this record)

## 5. Files modified

- `lib/python/biq/synthesis/synthesis_set.py` — three read-only registry views; re-entry refusal extended
- `lib/python/biq/decision_support.py` — read-only `strategy_result` property
- `tests/unit/test_command_registry.py`, `test_m10_3_1_swot.py`, `test_m10_3_2_strategy.py`,
  `test_m10_3_3_decision_support.py`, `test_m9d5_industry_research_command.py` — guards
- `architecture.md` — §4 status, §7 consumers and contract section marked built with enforcement notes,
  §13 tree
- `project_plan.md` — *Executive Report implementation* `PLANNED` → `COMPLETED`
- `README.md`, `docs/commands/README.md`, `docs/skills/README.md` — inventory
- `commands/strategy-analysis.md`, `commands/swot-analysis.md`, `commands/decision-support.md` — the
  "Executive reporting is not built" scope line only

## 6. Files deliberately unchanged

Every ADR (ADR-0031, ADR-0032, ADR-0033 included); `CLAUDE.md` (no governance change);
`reference/output-standards.md` (its *Executive report* shape already matches the implementation);
`lib/python/biq/strategy.py`, `swot.py`, `synthesis/merge.py`, the forecast, anomaly and KPI engines;
`.mcp.json`, `.claude-plugin/`, `agents/`, `config/`.

## 7. Features implemented

| Feature | Location | User-reachable |
|---|---|---|
| Draft eleven-section executive report | `executive_report.build()` / `render()` | Yes, via `/executive-report` |
| Read-only registry views | `SynthesisSet.registered_*()` | Internal seam |
| Report re-entry refusal | `SynthesisSet.register_claims()` | Internal guard |

**How statements are placed.** Each statement is classified once, in set order. An `ASSUMPTION` goes to
`evidence_and_uncertainty.assumptions`. Any other statement is tested with `grounding.evidence_domains()`;
if refused it goes to `evidence_and_uncertainty.not_supported` with grounding's reason. A readable statement
gets `strategy.statement_detail()` and appears where its origin places it: `kpi` → the KPI row it rests on;
`anomaly` → `anomalies`; anything else → `findings` (evidence, then interpretations). Every readable material
statement also appears in the summary. Forecast-origin statements are always assumptions; `outlook` is
always `not_available`.

## 8. Tests performed

```
python tests/run_tests.py unit.test_m10_3_4_executive_report
python tests/run_tests.py unit.test_m10_3_3_decision_support
python tests/run_tests.py unit.test_m10_3_2_strategy
python tests/run_tests.py unit.test_m10_3_1_swot
python tests/run_tests.py unit.test_m10_1_synthesis_security
python tests/run_tests.py unit.test_command_registry
python tests/run_tests.py unit.test_m9d5_industry_research_command
python tests/run_tests.py
claude plugin validate . --strict
git diff --check
```

## 9. Test results

Runs made after the last code change (recovery session, Python 3.13.1):

| Run | Result |
|---|---|
| `unit.test_m10_3_4_executive_report` | ran 73, failures 0, errors 0, skipped 0 |
| `unit.test_m10_3_2_strategy` | ran 123, failures 0, errors 0, skipped 0 |
| `unit.test_m10_3_3_decision_support` | ran 103, failures 0, errors 0, skipped 0 |
| `unit.test_m10_3_1_swot` | ran 117, failures 0, errors 0, skipped 0 |
| `unit.test_m10_1_synthesis_security` | ran 33, failures 0, errors 0, skipped 0 |
| `unit.test_command_registry` | ran 40, failures 0, errors 0, skipped 0 |
| `unit.test_m9d5_industry_research_command` | ran 51, failures 0, errors 0, skipped 0 |
| Full suite | ran 4,408, failures 0, errors 0, skipped 19 (recovered tree before fixes: 4,406) |
| `claude plugin validate . --strict` | Validation passed |
| `git diff --check` | clean |

## 10. Issues discovered

- **Found and fixed in recovery: the summary omitted §4 item 7 (availability).** No field reported the
  status of sections 3 and 5–9; the tests pinned only items 1–6.
- **Found and fixed in recovery: anomaly entries omitted §6's observed value, baseline and deviation** as
  resolved fields. The figures were present only inside the statement text.

- **The anomaly engine's own investigation note contains the word "fraud"** ("it is not evidence of fraud
  or of any wrongdoing"). The report adds no such word; the test checks everything except that upstream
  note.
- **A SWOT record is bound by reproduction, not identity.** A SWOT built over a different set whose
  statements, subject and metadata are byte-identical reproduces exactly and is accepted, because it is
  the same content this set produces; any difference refuses it. `swot.build()` returns a plain record, so
  there is no object to bind.
- **`StrategyResult` and `DecisionResult` are immutable only by convention** (`__slots__`, private state).
  The report detects tampering with their private state through the serialisation digest; tests do exactly
  that.
- **KPI rows show no prior or change today**, because `from_kpi_result()` statements carry no comparison.
  Period-over-period movement appears as findings.
- **The dataset label is whatever the translator registered** — for `commands.internal_statements()` the
  local source path. It stays local and is shown as registered.

## 11. Decisions made

None beyond ADR-0033. Implementation choices within it: fixed empty-state reason texts; entry key
`statement_detail` (distinctive, so the re-entry guard can recognise report entries); report `lifecycle`
schema `const "draft"` until M11 defines `final`; `UNBUILT_COMMAND` replaced by a non-command name.

## 12. Architecture changes

`architecture.md` §4 and §7 record Executive Report as built with its enforcement notes; §13 lists the module
and schema. No decided contract changed.

## 13. Project-plan updates

*Executive Report implementation*: `PLANNED` → `COMPLETED`. Milestone 11 unchanged (`PLANNED`).

## 14. Documentation updates

As §5. `reference/output-standards.md` not required.

## 15. Remaining work

- A synthesis forecast translator and its grading rule (separate decision; enables `outlook`).
- KPI targets, if an engine ever computes target variance.
- M11: the analysis verifier and `final` reports.

## 16. Git commit reference

N/A — no commit made, nothing pushed.
