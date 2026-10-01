# 2026-09-18 — M13 contract finalization: ADR-0039 clarified and accepted

**Milestone:** 13 — Test Hardening & Evals, part M13-A (contract finalization, decision only)
**Status on completion:** COMPLETED (DECISION ONLY) for M13-A. ADR-0039 is **Accepted**. M13 stays `PLANNED`: M13.1 and
M13.2 have not started. Nothing is committed.
**Supersedes:** the status lines of `2026-09-18-post-m12b-roadmap-gate.md` only:

- ADR-0039 `Proposed`;
- M13-A `REVIEW (DECISION ONLY)`;
- the pending owner confirmation of M10, in its §15 item 2.

That record is otherwise left intact and unedited.

## 1. Prompt / task performed

A contract-finalization session for Milestone 13, run in a fresh session. The owner recorded six decisions:

1. **M10 is confirmed closed** for roadmap purposes, on the basis of its completed and checkpointed sub-milestones and
   remediation chain. Reconcile only current-status text.
2. **M13 is the next buildable milestone.**
3. **ADR-0039 is to be finalized and accepted**, subject to the contract clarifications the prompt lists.
4. **D-13 stays open and does not block M13.**
5. **D-14 stays open and is deferred to M14.**
6. **M9 stays incomplete** while its live smoke tests and other unfinished rows remain.

The prompt required the ADR to state thirteen specific points explicitly. These cover:

- the production-change prohibition;
- separate evidence classes, and unavailable execution never being a pass;
- the execution restrictions;
- the M12-C, D-13, D-14 and M9 positions;
- no reconstruction of the 24-scenario list;
- defect recording not authorising a fix.

It also required a defect model and preservation of the S1–S7 sets unless inspection proved an inconsistency.

The prompt ruled out:

- implementation, tests, eval harness code and fixtures;
- changes to `lib/`, `commands/`, `skills/`, `agents/` and `.mcp.json`;
- authentication and connector operations;
- edits to accepted ADRs;
- a commit or push.

## 2. Objective

Finalize ADR-0039 so it is internally consistent, contradicts no accepted ADR, states every required clarification, and
can be accepted. Reconcile current-status documentation with the owner's decisions. Leave all changes uncommitted.

## 3. Changes made

1. **Baseline** (§9).
   - The working tree was **not clean**. It held the uncommitted output of the post-M12-B roadmap gate: five modified
     documents plus the untracked ADR-0039 and the gate record.
   - Before proceeding, the full diff was read and confirmed to be exactly that gate's documentation, and nothing
     else. ADR-0039 existed only in the working tree, so finalizing it presupposes that state.
   - `HEAD` = `origin/main` = `990e88d5f13db65b2ecdf0737c7f613b83c6034d` after `git fetch origin`.
2. **Reading.**
   - In full: `CLAUDE.md`; ADR-0039 as proposed; the post-M12-B gate record; ADR-0007.
   - By section:
     - ADR-0037 §J, §K, §L and §M, and ADR-0038's header and context;
     - `architecture.md` §2, §8, §15, §16, §19 and §20;
     - `project_plan.md`: header, summary, M9 table, the M10 sub-milestone headings and Executive Report rows, M13,
       *Known issues* and *Documentation debt*;
     - `docs/testing/README.md`;
     - the M8 discriminability measurement in `2026-09-09-forecasting-anomaly.md`;
     - the R-05 threshold remark in `2026-09-10-m9-owner-decisions.md`.
   - Inspected: `tests/connector_fixtures.py`, `tests/integration/test_performance.py`, the `commands/` inventory, the
     test layout, `.gitignore`, `plugin.json`, and `git log` for the M10 checkpoints (`62580f3` to `4dc6562`).
3. **Source-set verification** (§11). Each of S1–S7 was counted against its repository source.
4. **ADR-0039 clarified, then accepted** (§11).
5. **Current-status reconciliation** (§13, §14).
6. **Validation** (§8, §9, §17).

## 4. Files created

- `docs/development/2026-09-18-m13-contract-finalization.md` (this record)

## 5. Files modified

Relative to the working tree left by the post-M12-B gate. All of these files were already uncommitted gate output, and
ADR-0039 is untracked.

- `docs/decisions/ADR-0039-m13-test-hardening-and-evals-contract.md` — clarified and accepted (§11 lists every change).
- `architecture.md`:
  - §15: connector absence no longer reads "via `evals/mocks/`". This is ADR-0039's own follow-up 3, performed on
    acceptance.
  - §15: the proposed-contract paragraph is replaced by the accepted contract's summary.
  - §19: row 0039 set to Accepted.
  - §20 item 1: R-01 wording updated.
- `project_plan.md`:
  - the header;
  - summary rows M9, M10 and M13;
  - the M10 note, recording the owner's confirmation;
  - the notes on the three M9 tier-test rows;
  - the M13 scope note, the M13-A section and table, and the sub-milestone table;
  - R-01, D-13 and D-14.
- `docs/decisions/README.md` — index row 0039 set to Accepted.
- `docs/README.md` — the "(proposed)" marker dropped from the ADR-0039 entry.

## 6. Files deleted

None.

## 7. Features implemented

None. This is a decision-only finalization. No test, fixture, eval case, harness code, measurement or product file was
added or changed.

## 8. Tests performed

- `git status --short --branch`
- `git fetch origin`
- `git rev-parse HEAD origin/main`
- `python tests/run_tests.py` — at baseline, and on the finished tree.
- `claude plugin validate . --strict`
- `git diff --check`, on tracked changes and on the two untracked files.
- **Secret-pattern scan** of every added line in the tracked diff and of the two untracked files.
- **Immutability checks:**
  - ADR-0001 to ADR-0038: blob hash compared with `HEAD:`;
  - `CLAUDE.md` and `.mcp.json`;
  - no path changed under `lib/`, `tests/`, `commands/`, `skills/`, `agents/`, `.claude-plugin/`, `config/`,
    `reference/` or `assets/`;
  - the post-M12-B gate record and `CONNECTORS.md`, which are untracked or uncommitted gate output. Their
    modification times (17:45 and 17:43) predate this session, and this task wrote to neither.

No eval was executed, and no platform probe was run in this session.

## 9. Test results

**Baseline** (tree = `990e88d` plus the uncommitted gate documentation, before any change in this task):

```
Ran 4684 tests in 250.855s
OK (skipped=26)
ran 4684 | failures 0 | errors 0 | skipped 26
```

This matches the expected baseline exactly. The finished tree is recorded in §17.

## 10. Issues discovered

- **Working tree not clean at start.** The prompt asked for a clean tree. The dirty state was the uncommitted
  post-M12-B gate output that this task finalizes, and that was verified by reading the whole diff. It is reported,
  not treated as a blocker.
- **An unsourced threshold in the Proposed §D.2.** It asserted "at most 1,024 characters" for *every* built
  component. Accepted architecture (§2, ADR-0013) defines that limit only for **skill** descriptions. It was narrowed
  to skills. That is the only inconsistency found against the prompt's rule on thresholds.
- **§E.1 used `--runs 1`**, which conflicted with the fixed `--runs 3 --threshold 1.0`. It now uses the full policy.
- **The proposed text had no "not authorised" outcome.** Without one, M13.2 could not complete accurately when no
  ceiling is given. Outcome (c) was added.
- **The M9 owner decisions asked for a discriminability threshold** "agreed before descriptions are written". None was
  ever recorded. ADR-0039 therefore records overlap without a threshold, and does not invent one.
- **No S1–S7 inconsistency.** Every count matches its source:

  | Set | Count | Source |
  |---|---|---|
  | S1 | 18 | the rows of the §16 table |
  | S2 | 15 | 13 named fixtures plus two Revision 2 items |
  | S3 | 12 | the §15 Layer-2 behaviours |
  | S4 | 19 | `commands/*.md` |
  | S5 | 13 | the rows of the §8 table |
  | S6 | 3 | `project_plan.md` M9 `PLANNED` tier rows |
  | S7 | 19 | the ADR-0037 §J categories |

No new debt or risk id was created.

## 11. Decisions made

**ADR-0039 accepted**, with the owner's clarifications. The changes to the Proposed text, all recorded inside the ADR:

1. **Status**: Accepted — 2026-09-18. Acceptance authorises no implementation and no eval execution. The Deciders line
   is updated.
2. **Context**:
   - three rows added: `test_performance.py`, `connector_fixtures.py`, and the §2 / ADR-0013 description limit with
     the absent overlap threshold;
   - a *Roadmap state at acceptance* block covering M10, M9, M12/M12-C, D-13 and D-14.
3. **Invariants I-1 to I-13 added**, one per required point:

   | Invariant | Point |
   |---|---|
   | I-1 | No production change to satisfy M13 (hard invariant), naming the five prohibited triggers |
   | I-2 | Separate evidence classes |
   | I-3 | Unavailable ≠ pass |
   | I-4 | Manual ≠ automated pass |
   | I-5 | Owner authorisation and `--max-cost-usd` |
   | I-6 | `--no-publish` |
   | I-7 | No connector, MCP, web or authentication |
   | I-8 | M12-C `BLOCKED` |
   | I-9 | D-13 not blocking |
   | I-10 | D-14 deferred |
   | I-11 | M9 incomplete |
   | I-12 | The 24-scenario list is not reconstructed |
   | I-13 | Recording a defect does not authorise a fix |

4. **§A.2 and §A.3.**
   - §A.2: the harness is the platform's `claude plugin eval`. M13's harness infrastructure is the cases, the
     §E.5 validator and the procedure. Defect and measurement records are in scope.
   - §A.3 adds prohibitions on:
     - building or scheduling the D-13 skills;
     - D-14 cleanup;
     - marking M9 complete;
     - thresholds no accepted architecture defines.
5. **§B.** The matrix opens with a note that ADR-0007's list is unavailable. The `behavioural-only` status now
   carries an evidence class and says demonstration requires `automated_pass`. Covering an S6 row does not complete
   M9. The source sets themselves are unchanged.
6. **§D.**
   - D.1 names M3's unedited 60k baseline.
   - D.2 limits the length assertion to skills, and states that no overlap score passes or fails.
   - D.3 is named leave-one-period-out.
   - **D.4 added** (measurement records: `M13-MEAS-D1..D3`, dated, reproducible, `executed` or
     `execution_unavailable`).
   - **D.5 added** (a poor measurement is recorded, never tuned).
7. **§E.1** has three outcomes:
   - (a) executed at `--runs 3 --threshold 1.0`. Only this can resolve R-01, and case discovery is explicitly not
     closure evidence;
   - (b) `execution_unavailable`;
   - (c) not authorised.

   Under (b) and (c), each S3 row gets a `manual_observation` scenario, performed under the §F restrictions.
8. **§E.6 added.** The closed vocabulary: `automated_pass`, `automated_fail`, `not_executed`,
   `execution_unavailable`, and the separate `manual_observation`. Classes are reported separately and never merged.
9. **§F.**
   - F.1: the owner's explicit per-execution authorisation, not transferable.
   - F.3: no MCP tool is callable from any server.
   - F.7: `--runs 3 --threshold 1.0` fixed.
   - F.9: `not_executed`.
   - F.10: reporting per class.
   - **F.11 added**: no authentication, connector or production system.
10. **§G.** The table uses the product and infrastructure classes, and adds the "not authorised" and "poor
    measurement" rows.
    - **G.1 added**: the defect record. The fields are:
      - `defect_id` (`M13-DEF-NN`);
      - `source` (`test`, `eval`, `measurement`);
      - `defect_class` (`product`, `infrastructure`);
      - `affected_component`, `reproducer`, `expected_behavior` and `observed_behavior`;
      - `status` (`open`, `fixed_infrastructure`, `withdrawn`);
      - `blocks_m13_completion`, set by rule;
      - `linked_reference` and `found`.

      Defects are not scored or ranked.
    - **G.2 added**: product defects are never fixed in M13. Infrastructure defects are fixed in M13.
11. **§H** adds the synthetic-fixture rule, following the `tests/connector_fixtures.py` precedent, and the
    no-authentication / HubSpot / empty-registry statement.
12. **§J** states that a manual observation is human evidence. **K.6 scope audit** added.
13. **§L.**
    - M13-A is marked met.
    - M13.1 accepts D.1 as `execution_unavailable` with a reason, and requires no open blocking defect.
    - M13.2 has outcomes (a), (b) and (c).
    - Explicit "means / does not mean" lists added.
14. **Relationship to ADR-0007** states the non-reconstruction, keeps the manual-labelling rule, and confirms that no
    accepted ADR is edited and that ADR-0037 and ADR-0038 are consistent.
15. **Follow-ups 1 and 3** are marked done. **An *Owner clarifications at acceptance* section** was added.

**Consistency check.** ADR-0039 amends and supersedes nothing:

- **ADR-0007** is applied: its manual-labelling rule is kept, and its revisit is routed through E.1.
- **ADR-0037** §J, §K, §L and §M, including M12-C and P-1 to P-5, are restated without change.
- **ADR-0038**'s lifecycle is untouched. HubSpot stays in state 1.
- **ADR-0010**'s approval model is unchanged.
- **ADR-0013**'s limit is cited as defined.

## 12. Architecture changes

`architecture.md` §15 now states the accepted M13 contract, and connector absence is no longer tested "via
`evals/mocks/`". Both are the accepted ADR's own follow-up. §19 and §20 now reflect acceptance. No other architectural
change.

## 13. Project-plan updates

- **M13-A:** `REVIEW (DECISION ONLY)` → `COMPLETED (DECISION ONLY)`.
- **M13:** stays `PLANNED`. This follows the M12 precedent, where the milestone stayed `PLANNED` after M12-A was
  accepted.
- **M13.1 and M13.2:** `PLANNED`, with M13.1 next.
- **M10:** `COMPLETED`. The owner's confirmation is recorded in the summary row and the section note. No M10 record
  or ADR was edited.
- **M9:** stays `IN PROGRESS`. Its summary row and three tier rows now point to S6 and state that covering them does
  not complete M9.
- **M12:** `COMPLETED` under OD-1, unchanged. **M12-C:** `BLOCKED`, unchanged.
- **R-01:** the closure condition is stated. The status is unchanged, `BLOCKED`.
- **D-13:** stays open, recorded as not blocking M13.
- **D-14:** stays open, recorded as deferred to M14.

## 14. Documentation updates

As §5. Not updated, deliberately:

- `README.md`, `docs/README.md`'s history list and the ADR-index omissions, all D-14;
- `docs/testing/README.md`, where M13.1 creates the matrix;
- `CONNECTORS.md`, already accurate for M12 and M12-C;
- the post-M12-B gate record, which is append-only and superseded here;
- every historical M10 record and ADR;
- `CLAUDE.md`.

## 15. Remaining work

1. **Owner:** review this finalization and the uncommitted working tree, which also holds the gate's output. Decide
   whether to checkpoint it.
2. **M13.1**, under its own implementation prompt through the Milestone gate.
3. **M13.2**, after M13.1. Its prompt states whether eval execution is authorised, and its `--max-cost-usd`.
4. Unchanged and outside M13:
   - M9's four fresh-session live smoke tests, which the owner runs;
   - M12-C, `BLOCKED`;
   - D-13, owner decision;
   - D-14, Milestone 14;
   - R-05, R-10, R-11 and R-12.

## 16. Git commit reference

N/A — nothing committed, amended or pushed, as instructed. Branch `main`, base `990e88d`.

## 17. Final validation (finished tree)

This section was written after the runs below. Afterwards, `git diff --check` and the secret scan were re-run over the
finished files.

- **Full suite:**

  ```
  Ran 4684 tests in 781.055s
  OK (skipped=26)
  ran 4684 | failures 0 | errors 0 | skipped 26
  ```

  This is identical to the baseline. The longer wall time is because strict validation ran concurrently.
  - One ADR-0039 wording edit (§E.6 class precedence) landed during this run.
  - No test reads ADR-0039: `grep` of `tests/` finds only ADR-0037 paths.
  - This record already existed when the run started.
- **`claude plugin validate . --strict`:** `✔ Validation passed`, exit 0.
- **`git diff --check`:** clean, with exit 0 and only CRLF-conversion warnings. The untracked files were checked with
  `git diff --no-index --check`: clean, and 0 lines with trailing whitespace.
- **Secret scan:** no token-shaped value, no URL and no email address. The only pattern hit is the
  public commit id `990e88d5…`.
- **Immutability:**
  - ADR-0001 to ADR-0038: 38 of 38 blob hashes equal `HEAD:`;
  - `git status --porcelain` is empty for `CLAUDE.md`, `.mcp.json`, `.gitignore`, `README.md`, `lib/`, `tests/`,
    `commands/`, `skills/`, `agents/`, `.claude-plugin/`, `config/`, `reference/` and `assets/`.
- **No authentication, connector operation, eval execution or network call** was made by this task. The only network
  operation was `git fetch origin`.
