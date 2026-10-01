# 2026-09-22 — M13-DEF-06 remediation: a result is admissible only if its run executed

**Milestone:** M13 — test hardening and evals (M13.2)
**Status on completion:** M13.2 `IN PROGRESS`; **M13-DEF-06 `fixed_infrastructure`**; M13-DEF-05 `open`
**Supersedes:** None. It remediates the defect raised in
`docs/development/2026-09-22-m13-2-stage2-pilot.md`, which stands unchanged.

## 1. Prompt / task performed

"M13-DEF-06 remediation only — add deterministic guards so an eval result with zero turns / execution error can
never be recorded as an automated pass."

## 2. Objective

Make the failure the Stage 2 pilot exposed structurally impossible in this repository, and prove the guard is
load-bearing rather than decorative.

## 3. Changes made

1. **Wrote the rule once, in code.** `tests/unit/test_m13_eval_results.py` holds `run_admissibility()`,
   `classify_case()` and `classify_result()`. A run is admissible only if it took **at least one turn**, reported
   **no error**, carries a **recorded verdict**, and scored at least one grader. Anything the rule cannot
   establish is inadmissible — the default is refusal, never acceptance.
2. **Mapped admissibility onto the ADR-0039 §E.6 classes.** `automated_pass` requires every expected run (three,
   per §F) to be admissible and passing. An **executed** failing run outranks any unavailability, as §E.6 says.
   Everything else is `execution_unavailable`.
3. **Committed the pilot's own result shape as a fixture**,
   `tests/fixtures/eval_results/2026-09-22-stage2-pilot.json`, trimmed to the fields the rule reads and with the
   machine paths removed, so the exact regression is pinned.
4. **Wrote the rule down** in `docs/testing/eval-suite.md`, *Admitting a result*, with the table that decides each
   class — and a test that fails if that sentence leaves the document.
5. **Closed M13-DEF-06** as `fixed_infrastructure`, with a status basis that states precisely what is fixed and
   what is not.

**No new ADR.** This is ADR-0039 §E.6 enforced, not amended: §E.6 already defines `automated_pass` as a case
executed under §F and `execution_unavailable` as a run the platform refused. Nothing checked it. Writing an ADR
for a guard that implements an accepted rule would fail the bar in `docs/decisions/README.md`.

## 4. Files created

| File | Purpose |
|---|---|
| `tests/unit/test_m13_eval_results.py` | The admissibility rule and its 22 tests |
| `tests/fixtures/eval_results/2026-09-22-stage2-pilot.json` | The refused-run result shape, as a regression fixture |
| `docs/development/2026-09-22-m13-def-06-remediation.md` | This record |

## 5. Files modified

| File | Change |
|---|---|
| `docs/testing/eval-suite.md` | New *Admitting a result* section: the rule, why it exists, and the class table |
| `docs/testing/defects.md` | M13-DEF-06 → `fixed_infrastructure`, `blocks_m13_completion: no`, with its status basis; register row |
| `project_plan.md` | Known-issues row and the Stage 2 bullet |

**No production file was changed.** No case file, no evidence class, and no coverage row moved.

## 6. Files deleted

None.

## 7. Features implemented

None. Test-side governance only.

## 8. Tests performed

```
python tests/run_tests.py unit.test_m13_eval_results
python tests/run_tests.py unit.test_m13_eval_cases
python tests/run_tests.py unit.test_m13_coverage_matrix
python tests/run_tests.py unit.test_m13_manual_observation_pack
claude plugin validate . --strict
git diff --check
```

Plus a **mutation check**: the rule was replaced with three broken versions and the suite re-run each time, to
prove the tests fail when the guard is weakened.

**No evaluation was run.** `claude plugin eval` was not invoked.

## 9. Test results

| Check | Result |
|---|---|
| `unit.test_m13_eval_results` | **22 pass** (new) |
| `unit.test_m13_eval_cases` | 90 pass |
| `unit.test_m13_coverage_matrix` | 33 pass, 1 skip (pre-existing conditional) |
| `unit.test_m13_manual_observation_pack` | 16 pass |
| `claude plugin validate . --strict` | ✔ Validation passed |
| `git diff --check`, secret scan, personal-data scan | clean |

**Mutation check** — each mutant was caught:

| Mutation | Failing tests |
|---|---|
| Every run admissible (the defect's own behaviour) | **22** |
| The turn count ignored, error still checked | **11** |
| The rule sentence removed from the procedure | **1** |

The first mutant is the important one: restoring the pre-remediation behaviour fails every test in the module,
including the assertion that the Stage 2 pilot's result is not a pass.

## 10. Issues discovered

None new. The two open matters are unchanged and belong elsewhere: **M13-DEF-05** (the suite still does not fully
load — 24 graders and 3 cases pending), and the **environment condition** the pilot exposed, which is an owner
decision under ADR-0040 §2 and not a defect id.

One thing worth stating, because it shaped the rule: the pilot's grader passed *because* it was negatively worded.
"Did the assistant avoid asking for approval?" is satisfied by silence. The suite's approval and safety cases are
largely negative assertions, so an empty transcript scores well across exactly the cases where a false green is
most dangerous. The rule refuses the run before any grader verdict is consulted, which is the only ordering that
makes this safe.

## 11. Decisions made

No ADR, for the reason in section 3. One judgement recorded: **`fixed_infrastructure` claims the repository's
exposure is fixed, not that the platform is.** The harness still scores a refused run as a pass; that is recorded
verbatim in the defect and can be reported upstream. What changed is that such a result can no longer become an
`automated_pass` here — the harness's `casesPassed` and `overallScore` are recorded as observed, then classified.

## 12. Architecture changes

None.

## 13. Project-plan updates

M13-DEF-06 → `fixed_infrastructure`, `blocks_m13_completion: no`. **M13.2 stays `IN PROGRESS`; M13-DEF-05 stays
`open` and blocking.** No milestone advanced.

## 14. Documentation updates

`docs/testing/eval-suite.md`, `docs/testing/defects.md`, `project_plan.md`, and this record. The Stage 2 pilot
record and the 2026-09-20 execution record were not touched.

## 15. Remaining work

1. **Owner decision on the execution environment** — still the gate for everything downstream.
2. Re-run the Stage 2 pilot once in a viable environment, for the trace tool name and input delivery.
3. ADR-0044 stage 3 — the 24 pending graders and the three unloadable cases — then §E.1 again.
4. Unchanged: the twelve `manual_observation` scenarios, V-4, the Unix runtime verification.

## 16. Git commit reference

None. Nothing staged, committed or pushed. Base `21ee21b`.
