# 2026-09-26 — M13.2 availability-completion evaluation of ten routing cases

**Milestone:** 13 — Test Hardening & Evals (M13.2, behavioural evals)
**Status on completion:** IN PROGRESS
**Supersedes:** None. The closing evaluation and the 34-case re-evaluation stand unchanged.

## 1. Prompt / task performed

The owner's one further evaluation, within the $47.74 left of the 34-case re-evaluation's $75 authorisation: run exactly
`r02`–`r09`, `r15` and `r16`, three runs each, in a fresh session window, with a 20-turn budget for the routing runs,
the established flags and grants, ADR-0047 routing and ADR-0049 classification; record it separately; assess
ADR-0039 §L; no product, grader or historical change, no manual observation, no commit, push or staging.

## 2. Objective

Obtain admissible live evidence for the ten cases the re-evaluation lost to platform limits, and assess M13.2 against
§L.

## 3. Changes made

1. **Turn budget.** `claude plugin eval` 2.1.281 has no `--max-turns` flag (its help mentions `max_turns` only as a
   case bound). The platform's case schema supports `execution.max_turns` (integer, at most 200, default 10), so
   `max_turns: 20` was added under `execution` in the ten case files and nowhere else — a runtime setting, no prompt,
   grader or evidence field changed. A validator test confines it to those ten cases.
2. **Execution.** A resumable runner issued ten single-case invocations (`--case 'r02*'` … `'r16*'`, simulated to match
   exactly the ten), `--ablation with-without`, `--runs 3 --threshold 1.0 --no-publish --mocks record --scaffold
   --keep-temp --trust-plugin`, exactly the `Read` and resolver grants, each `--max-cost-usd` = $47.74 less this
   evaluation's spend less $1.00 (first $46.74, last $32.03). All ten ran to completion in one session window.
3. **Record.** `tests/fixtures/eval_results/2026-09-26-availability-10-cases.json` and tests binding it; a M13-DEF-17 note;
   `eval-suite.md`; `project_plan.md`; this record.

## 4. Files created

- `tests/fixtures/eval_results/2026-09-26-availability-10-cases.json`
- `docs/development/2026-09-26-m13-2-availability-completion.md` (this record)

## 5. Files modified

- `evals/routing/{r02..r09,r15,r16}-*/case.yaml` (`execution.max_turns: 20` only)
- `tests/unit/test_m13_eval_cases.py` (one test), `tests/unit/test_m13_eval_results.py` (result-file count 4 → 5; 5 tests)
- `docs/testing/defects.md`, `docs/testing/eval-suite.md`, `project_plan.md`

## 6. Files deleted

None.

## 7. Features implemented

None.

## 8. Tests performed

The ten paid invocations, then `python3 tests/run_tests.py -v`, `claude plugin validate . --strict`,
`git diff --check`, the secret scan, the scope audit and the K.5 re-check (task report).

## 9. Test results

**Evaluation:** 10 of 10 attempted; 60 runs requested and launched, 60 admissible; **10 `automated_pass`**, 0
`automated_fail`, 0 `execution_unavailable`, 0 `not_executed`; $17.6052 (remaining authorisation $30.14).

| Case | With-plugin (turns) | Route taken (with-plugin) |
|---|---|---|
| r02 | P16 P10 P9 | command, then skill |
| r03 | P8 P7 P9 | command, then skill |
| r04 | P7 P8 P7 | command, then skill |
| r05 | P7 P6 P7 | command, then skill |
| r06 | P4 P4 P4 | skill only (no owning command) |
| r07 | P11 P7 P8 | command only (runs 1–2), command then skill (run 3) |
| r08 | P18 P16 P7 | command, then skill |
| r09 | P6 P6 P6 | `profitability-analysis`, then skill |
| r15 | P5 P5 P11 | skill only (runs 1–2), command then skill (run 3) |
| r16 | P11 P11 P15 | command, then skill |

The without-plugin arm failed its routing grader in every run, as expected without the plugin. No session limit, turn
limit or other error occurred, and no LLM grader ran in these routing cases, so ADR-0049 was not exercised.

## 10. Issues discovered

- **Turn budget.** Five with-plugin runs used more than 10 turns (up to 18). The 20-turn budget resolved the r15 and
  r16 limit; no run reached it.
- **No product finding** in these ten cases; no new defect. M13-DEF-17 gained further live evidence.

## 11. Decisions made

None. `execution.max_turns: 20` is the owner-directed turn budget, applied through the platform's supported field.

## 12. Architecture changes

None made. See §13 on `architecture.md`.

## 13. Project-plan updates — ADR-0039 §L assessment

| §L condition for M13.2 | Result | Evidence |
|---|---|---|
| Every E.3 case authored | PASS | 64 cases |
| E.5 passing | PASS | `unit.test_m13_eval_cases` in the regression |
| Exactly one §E.1 outcome | PASS | Outcome (a) |
| (a) executed under §F; every case's §E.6 class and per-run results recorded | PASS | Closing evaluation (64 cases, case files), 34-case re-evaluation and this evaluation, each in its own fixture; every one of the 34 corrected cases now has admissible live evidence under the amended contract |
| Defects recorded, none `blocks_m13_completion: yes` | PASS | M13-DEF-01 to M13-DEF-24; every infrastructure defect is fixed; product defects do not block by rule |
| K.1–K.6 | PASS, subject to this task's runs | Task report |
| Documentation: `project_plan.md`, a dated record, the task report | PASS | This record |
| Documentation: **`architecture.md` §15/§20 where facts changed** | **FAIL** | §15 still says "M13.2 suite (authored, not executed)" and §20 "Until a case executes, R-01 stands"; neither reflects the executions or ADR-0044 to ADR-0049. Editing it was outside this evidence-only task |
| A commit only on the owner's request | NOT APPLICABLE | No commit requested |

**M13.2 remains IN PROGRESS.** Outstanding: the `architecture.md` §15/§20 update; the owner's decision on how the three
evaluation records jointly stand as M13.2's evaluation evidence (the case files and coverage matrix still carry the
closing evaluation's classes, with the later evaluations recorded beside them); owner closure of R-01, whose §E.1 (a)
evidence exists; and owner acceptance.

## 14. Documentation updates

`docs/testing/eval-suite.md`, `docs/testing/defects.md`, `project_plan.md`, this record.

## 15. Remaining work

As in §13. Separately, the product defects M13-DEF-13 to M13-DEF-16 and M13-DEF-24 await owner-assigned remediation.

## 16. Git commit reference

N/A. Nothing staged, committed or pushed. Branch `main`, HEAD `21ee21b21213ad80273650f056ef2f318023742c`.
