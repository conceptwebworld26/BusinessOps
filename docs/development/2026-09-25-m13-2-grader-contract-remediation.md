# 2026-09-25 — M13-DEF-17 to M13-DEF-23: evaluation grader-contract remediation

**Milestone:** 13 — Test Hardening & Evals (M13.2, behavioural evals)
**Status on completion:** IN PROGRESS
**Supersedes:** None. `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` stays as written; the one
factual correction it needs (M13-DEF-20's root cause) is recorded in the defect register and in section 10 here.

## 1. Prompt / task performed

The owner's M13-DEF-17–M13-DEF-23 remediation prompt: correct the seven blocking evaluation-infrastructure defects
the closing evaluation found, in graders, evaluation fixtures and scaffolds, validators and tests only; add
deterministic tests proving each fix; stop any defect whose fix would need a production change, an accepted-ADR
change, a policy change or a paid evaluation; keep the historical evaluation evidence and classes unchanged; run the
regression, strict validation, `git diff --check`, the secret scan and a scope audit; do not close M13.2; do not
commit, push or stage.

## 2. Objective

Make the evaluation contract measure what each case states, without weakening a safety assertion and without
touching the product.

## 3. Changes made

1. **Established the platform's grader semantics** from the Claude Code 2.1.281 executable, read-only: a
   `tool_used` grader counts tool calls whose `name` equals `tool` and, when set, whose `inputText` matches
   `new RegExp(input_match)`, verdict `min <= count <= max` (defaults 1 and unbounded); `inputText` is the tool
   input's compact JSON; a `regex` grader's `last_message` is the last assistant text and its `trace` target is every
   trace event, the `init` event included. **Validated before use:** a Python model of that logic, replaying the
   original deterministic graders over every kept closing-evaluation trace, reproduced the platform's recorded
   verdict **462 of 462** times.
2. **Found the shared root cause of M13-DEF-18 and M13-DEF-22.** The semantic layer already stated the right
   property — each `tool_not_invoked` grader carries a `pattern` for the prohibited content — and the ADR-0044
   Phase 1 translation emitted its per-tool platform graders **without it**, so any call to the tool failed.
3. **Checked every fix against the accepted ADRs before editing.** Two fixes collide with an accepted ADR and were
   stopped (M13-DEF-17 with ADR-0044, M13-DEF-19 with ADR-0041); M13-DEF-23 needs a policy decision (section 10).
4. **Corrected the case files** (graders only; no prompt, input, scaffold or evidence field changed):
   - M13-DEF-18: `input_match` = the semantic pattern on `a20` (all four file and shell graders), `a21`, `a23`,
     `a24`. `a20`'s pattern became write-shaped, because `README\.md` alone matched reading the file.
   - M13-DEF-20: `d08`'s whole-trace regex replaced by ADR-0044's own `agent_not_dispatched` mapping,
     `g-nothing-dispatched-agent` and `-task`.
   - M13-DEF-21: `b02`'s figure regex (and `b01`'s identical one) excludes exactly the configured threshold.
   - M13-DEF-22: `input_match` = the semantic pattern on every per-tool payload grader in `d01` to `d08`.
   - Inline `(?i)` in affected semantic patterns became explicit character classes (the platform's `input_match`
     takes no flags); the meaning is unchanged.
5. **Updated the migration map** for `d08` (175 platform graders, was 174). Reconstructing the prior values
   reproduces the file's pre-task SHA-256, so nothing else in it changed.
6. **Tests** (section 11) and **documentation**: `defects.md`, `eval-suite.md`, `project_plan.md`, this record.

## 4. Files created

- `tests/unit/test_m13_grader_contract.py`
- `docs/development/2026-09-25-m13-2-grader-contract-remediation.md` (this record)

## 5. Files modified

- Case files, graders only: `evals/approval/{a20,a21,a23,a24}-*/case.yaml`,
  `evals/behaviour/{b01,b02}-*/case.yaml`, `evals/disclosure/{d01..d08}-*/case.yaml` (14)
- `docs/testing/grader-migration-map.json`
- `tests/unit/test_m13_eval_cases.py`
- `docs/testing/defects.md`, `docs/testing/eval-suite.md`, `project_plan.md`

## 6. Files deleted

None.

## 7. Features implemented

None. Evaluation infrastructure only; no product behaviour changed.

## 8. Tests performed

```
python3 -m unittest tests.unit.test_m13_grader_contract          # the new contract tests
python3 -m unittest tests.unit.test_m13_eval_cases tests.unit.test_m13_eval_results \
  tests.unit.test_m13_coverage_matrix tests.unit.test_m13_def10_eval_grant \
  tests.unit.test_m13_manual_observation_pack tests.unit.test_m13_grader_contract \
  tests.integration.test_m13_eval_scaffold
python3 tests/run_tests.py -v                                     # full regression
claude plugin validate . --strict
git diff --check
<in-memory mutation of each fix>                                  # section 9
<secret-pattern scan of every touched file>                       # section 12
```

## 9. Test results

- `unit.test_m13_grader_contract`: `Ran 29 tests … OK`.
- M13 modules: `Ran 250 tests … OK (skipped=1)`. Before the migration-map and answer-key updates, the validator
  failed 4 tests, all expected (the map still named the old `d08` grader and 174 graders; the new threshold literal
  was not yet exempt as a shipped value).
- **Full regression:** `Ran 5105 tests in 270.081s` — `OK (skipped=31)`, exit 0. The previous run was 5,076 tests,
  31 skipped; the 29 added tests account for the difference.
- `claude plugin validate . --strict`: `✔ Validation passed`. `git diff --check`: clean.
- **Mutation check** (in memory, no file changed): reverting each fix in the loaded graders fails its tests —
  M13-DEF-18 11 tests (a naive `README\.md` pattern: 6), M13-DEF-20 1, M13-DEF-21 2, M13-DEF-22 4; restored, 0.
- **Informational only, not a re-score:** the corrected graders run over the real kept traces still fail the
  `a20` runs that really attempted `cat > README.md` and the `d05` dispatches naming Fenwick (M13-DEF-13 is still
  detected), and pass `d04`'s public dispatch, `d08`'s no-dispatch runs and the `b01`/`b02` halts. No class was
  recomputed or changed.

## 10. Issues discovered

| Defect | Status | Why |
|---|---|---|
| M13-DEF-17 | **open** | The fix — accept a skill's owning command, taken from the engine registry's `skill` field and each command's "All of that lives in `skills/<skill>/SKILL.md`" declaration, anchored on the `Skill` input's `skill` field — changes a mapping ADR-0044 (accepted) decides: `skill_invoked` as `input_match: <skill>`, restated as "keep their Phase 1 mapping". **Owner decision:** an ADR amending that mapping |
| M13-DEF-18 | `fixed_infrastructure` | Section 3 |
| M13-DEF-19 | **open** | A `README.md` fixture is not CSV, and ADR-0041 §2 (accepted) admits CSV only; the §F.6 same-path assertion also cannot stage a working-directory `README.md`. **Owner decision:** amend ADR-0041 for a Markdown fixture, or redesign `a20` |
| M13-DEF-20 | `fixed_infrastructure` | Section 3. **Correction:** the closing-evaluation record attributed the match to final-message text; it was the `init` event's agent roster in all three runs |
| M13-DEF-21 | `fixed_infrastructure` | Section 3 |
| M13-DEF-22 | `fixed_infrastructure` | Section 3 |
| M13-DEF-23 | **open** | Each affected grader records why it is not deterministic, and no repository rule governs split votes (ADR-0044 carries LLM criteria verbatim; ADR-0039 §E.6 counts a scored failing run as a failure). **Done:** disagreement represented explicitly (`split_votes()`, six recorded splits asserted, none converted). **Owner decision:** a split-vote rule, a pinned `--judge-model`, or restructured criteria |

**Two related findings.** `a23` and `a24` shared M13-DEF-18's root cause and were corrected with it; this one is
fixed. Not fixed: the `r17`–`r19` command-routing graders use the same unanchored substring matching as M13-DEF-17; they were not
reached in the closing evaluation (session limit), and they are left for the same owner decision.

## 11. Decisions made

No ADR. Judgements recorded for review:

- **Carrying a semantic grader's own `pattern` or `agent` into `input_match` completes ADR-0044's mapping rather than
  changing it**, because the ADR's `tool_not_invoked` and `agent_not_dispatched` rows are silent on those fields and
  its principle is that the semantic layer keeps its meaning. M13-DEF-17 is treated differently because ADR-0044
  states that `input_match` value explicitly.
- **Tests:** `tests/unit/test_m13_grader_contract.py` (new, 29 tests) holds the platform model and grades the case
  files' own graders against traces in the platform's event shape. Its verbatim inputs come from the kept traces.
  Each defect test grades the pre-remediation grader as a literal beside the corrected one. `EveryPatternBearingGraderCarriesItsPattern` asserts the translation rule suite-wide (43 graders).
- `tests/unit/test_m13_eval_cases.py`: `shipped_threshold_text()` and
  `test_the_figure_exclusion_is_the_shipped_materiality_threshold` added, and the answer-key scan exempts only that
  shipped literal in its exclusion form, following the b03 shipped-default precedent.

## 12. Architecture changes

None. `architecture.md` is unchanged.

**Scope audit** against a SHA-256 snapshot taken before this task: section 5 lists every changed file, and the
two created files are in section 4. Unchanged: `CLAUDE.md`, every accepted ADR, `.mcp.json`, `lib/` (including
`lib/biq_run.sh` and `lib/python/biq/`), `commands/`, `skills/`, `agents/`, `reference/`, `config/`, `assets/`,
every case prompt, input and scaffold, `tests/fixtures/eval_inputs/`, every `evidence_class` and
`evidence_reason`, `tests/fixtures/eval_results/` (all three result files byte-identical) and `evals/results/`.

## 13. Project-plan updates

M13.2 stays `IN PROGRESS`. M13-DEF-18, -20, -21 and -22 → `fixed_infrastructure`; M13-DEF-17, -19 and -23 stay
`open` and block M13.2 by rule.

## 14. Documentation updates

`docs/testing/defects.md` (status bases, one correction, register table), `docs/testing/eval-suite.md`
(*Grader-contract remediation*), `project_plan.md`, this record.

## 15. Remaining work

1. Owner decisions on M13-DEF-17 (ADR-0044 amendment), M13-DEF-19 (ADR-0041 decision) and M13-DEF-23 (judge
   policy), then their implementation under their own prompts.
2. After those, a new owner-authorised evaluation of every case whose graders changed. Fourteen changed here:
   `a20`, `a21`, `a23`, `a24`, `b01`, `b02`, `d01` to `d08`. Deciding M13-DEF-17 and M13-DEF-19 would add `r01` to
   `r16`, `r20` to `r22` and `b04`. Until then, the closing evaluation's classes stand.
3. Separately: the product defects M13-DEF-13 to M13-DEF-16.

## 16. Git commit reference

N/A. Nothing staged, committed or pushed. Branch `main`, HEAD `21ee21b21213ad80273650f056ef2f318023742c`.
