# 2026-09-26 — M13.2 documentation closure and R-01 resolution

**Milestone:** 13 — Test Hardening & Evals (M13.2, behavioural evals)
**Status on completion:** REVIEW — M13.2 ready for owner acceptance; `project_plan.md` keeps it `IN PROGRESS` until the owner accepts
**Supersedes:** None. Earlier records stay as written.

## 1. Prompt / task performed

The owner's documentation-only closure task: reconcile `architecture.md` §15 and §20 with the executed M13.2
evaluations, close R-01 as the evaluation-execution gap, document the three-record evidence model, keep every
historical record, case evidence field, product file and ADR unchanged, run no evaluation, and reassess ADR-0039 §L.

## 2. Objective

Remove the last §L gap found on 2026-09-26: documentation that still described the suite as unexecuted.

## 3. Changes made

1. **`architecture.md` §15.** The 2026-09-18 limitation note gains a dated resolution (cases execute; R-01 closed),
   keeping its text as history. The M13.2 paragraph is retitled *authored and executed*; it records the copy-only
   scaffolds, `a20`'s ADR-0048 precondition fixture, the three separate result records and how they relate, the
   ADR-0044 to ADR-0049 contract, that **no live judge split has occurred** (so ADR-0049 is verified deterministically
   only), and where the defects are.
2. **`architecture.md` §20.** Item 1 no longer says the suite is unexecuted: R-01 is closed and what remains is
   operational (owner authorisation, cost ceilings, session limits, turn budgets). Item 7 no longer says routing is
   unmeasured.
3. **`project_plan.md`.** R-01 → **Closed 2026-09-26 (M13.2)** by the owner's decision under ADR-0039 §E.1 (a),
   scoped to the evaluation-execution gap, with its history kept; the 2026-09-26 status bullet's outstanding clause
   updated.
4. **Not changed**, being history or out of scope: R-01 mentions in dated records, in ADRs, in `eval-suite.md`'s
   *Recorded state (2026-09-22)* section and in the coverage matrix's outcome-(b) notes; R-05, whose closure was not
   asked for.

## 4. Files created

- `docs/development/2026-09-26-m13-2-documentation-closure.md` (this record)

## 5. Files modified

- `architecture.md` (§15, §20 only), `project_plan.md`

## 6. Files deleted

None.

## 7. Features implemented

None.

## 8. Tests performed

`python3 tests/run_tests.py -v`, `claude plugin validate . --strict`, `git diff --check`, the secret scan, the scope
audit and the K.5 re-check.

## 9. Test results

Recorded in the task report.

## 10. Issues discovered

None.

## 11. Decisions made

R-01 closure, by the owner, in the prompt. No ADR.

## 12. Architecture changes

Factual reconciliation of §15 and §20 only; no architectural decision changed.

## 13. Project-plan updates — ADR-0039 §L, reassessed

| Condition | Result |
|---|---|
| Every E.3 case authored; E.5 passing | PASS |
| Exactly one §E.1 outcome, (a) | PASS |
| (a): executed under §F, every case's §E.6 class and per-run results recorded | PASS — three separate records; every case attempted and classified, and every case has admissible live evidence |
| Defects recorded under §G.1, none `blocks_m13_completion: yes` | PASS — M13-DEF-01 to M13-DEF-24; every infrastructure defect fixed; product defects do not block by rule |
| K.1–K.6 | PASS (task report) |
| Documentation: `project_plan.md`, `architecture.md` §15/§20 where facts changed, dated record, task report | PASS |
| A commit only on the owner's request | NOT APPLICABLE — none requested |

**M13.2 is ready for owner acceptance.** Following the M13.1 precedent (implemented, then owner-approved and
checkpointed), `project_plan.md` keeps M13.2 `IN PROGRESS` until the owner accepts it.

## 14. Documentation updates

`architecture.md`, `project_plan.md`, this record.

## 15. Remaining work

Owner acceptance of M13.2 (and, at the owner's request, a commit). Separately, remediation of the open product
defects M13-DEF-01, -03, -13 to -16 and -24, which M13 does not fix.

## 16. Git commit reference

N/A. Nothing staged, committed or pushed. Branch `main`, HEAD `21ee21b21213ad80273650f056ef2f318023742c`.
