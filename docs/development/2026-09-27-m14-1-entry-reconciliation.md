# 2026-09-27 — M14 entry and M14-1: entry and status reconciliation

**Milestone:** 14 — Documentation & Release
**Status on completion:** REVIEW — M14 `IN PROGRESS`; M14-1 is documentation-only and uncommitted
**Supersedes:** None

## 1. Prompt / task performed

The owner approved the M14 entry gate and made two decisions:

1. discard the unexplained working-tree `README.md` change by restoring the file exactly to HEAD;
2. delete the unexplained empty untracked `file.txt`.

The owner then asked M14-1 to reconcile the governance and status drift that the M14 entry-gate audit identified.

The following were excluded: the M14-2 `README.md` rewrite, and any change to production code, tests, schemas or
manifests. Also excluded: defect fixes, M9 smoke tests, M12-C, evaluations, MCP, connectors, tagging, publication,
staging, commit and push.

## 2. Objective

Make the governance documents state the repository's actual current state:

- M13 is `COMPLETED`;
- M14 is `IN PROGRESS`;
- M9 is `IN PROGRESS`;
- M12 is `COMPLETED` under OD-1, with M12-C `BLOCKED`.

Historical facts in dated records are not rewritten.

## 3. Changes made

### Entry cleanup (owner decisions)

- **Entry state.** HEAD and `origin/main` were both `595e910`. The only changes were ` M README.md` (4 bytes, `...`)
  and `?? file.txt`.
- **`README.md`.** Restored with `git restore --source=HEAD --worktree -- README.md`. `git diff -- README.md` is now
  empty, and the file is byte-identical to `HEAD:README.md` (329 lines). Its content was not edited. It keeps the stale
  "Milestone 7 of 14" banner, which is D-14's `README.md` part and now belongs to M14-2.
- **`file.txt`.** Checked before deletion: it was untracked, 0 bytes, and referenced nowhere except as a generic example
  name in ADR-0051 and the classifier tests, and in the M13-DEF-24 record noting it. It was deleted, and nothing else
  was deleted.
- **After cleanup.** The working tree was clean.

### M14-1 reconciliations

Each dated history bullet or superseded block in `project_plan.md` was left as written.

- **A. Commit status.** Stale "not committed" / "not yet committed" wording was replaced.
  - The defect-register rows for M13-DEF-04, -08 and -12 now say "committed in `8287e98`". The rows for M13-DEF-13 and
    -24 now say "committed in `595e910`".
  - In `project_plan.md`, the M13-DEF-13 status bullet, the M13-DEF-04 remediation heading and the Known-issues rows
    for M13-DEF-04, -08, -12, -13 and -24 received the same correction.
  - The 2026-09-20 "superseded" next-gate block still says "not committed", because it describes that date.
  - `defects.md`'s other "not committed" occurrences mean "not committed *as a test*" (M13-DEF-01, M13-DEF-04
    reproducer), and were left alone.
- **B. M13 summary row.** It now states only the accepted state:
  - M13.1 `COMPLETED` (`33f6e25`) and M13.2 `COMPLETED`, owner-accepted 2026-09-26 (`8287e98`);
  - R-01 closed and no blocking defect;
  - where each remediation is checkpointed;
  - which defects are open.

  The contradictory "M13.2 `IN PROGRESS` … seven of them blocking" text was removed from this current-status row. The
  history remains in the dated bullets and records.
- **C. R-01.** The §E.1 outcome row's notes now say "R-01 stayed `BLOCKED` at that point", followed by a
  current-status note: closed 2026-09-26 under §E.1 (a). The 2026-09-22 dated bullets are unchanged.
- **D. M13-DEF-11.** Its Known-issues cell now leads with the register's current status, `fixed_infrastructure`,
  `blocks_m13_completion: no`, and keeps the original wording marked "as first recorded".
- **E. M9 planning rows.** Three superseded rows were reconciled against the per-item rows below them:
  - the four skills → `COMPLETED`;
  - the three M9-C skills → `COMPLETED`;
  - the four external commands → `REVIEW`, with the owner-run live smoke test still outstanding.

  M9 stays `IN PROGRESS`, the smoke tests are not marked done, and the tier-test and `biq-external-research` rows stay
  `PLANNED`.
- **F. ADR indexes.** No index states an exclusion rule, and `docs/decisions/README.md` requires every accepted ADR to
  be listed in both `architecture.md` and `docs/README.md`. Each index now links all 51 ADRs.
  - `docs/decisions/README.md` gained 0017, 0018, 0023 and 0024.
  - `architecture.md` §19 gained 0017, 0018 and 0045–0049.
  - `docs/README.md` gained 0017–0024, 0026, 0027 and 0041–0051.

  Titles, dates and statuses come from each ADR's own header. No ADR file was edited.
- **G. Banners and history** (the non-README parts of D-14).
  - The `architecture.md` header no longer claims "Milestone 1 (Foundation) implemented". It now defers
    implementation status to `project_plan.md`, and its last-updated date is 2026-09-27.
  - `docs/README.md`'s development-history list gains a factual note that records from M8 onward are indexed by the
    date-ordered `development/` directory. No new narrative was written.
  - The D-14 row now says it is partly reconciled, with the `README.md` banner remaining for M14-2.
- **H. Stubs.** `docs/examples/README.md` and `docs/troubleshooting/README.md` no longer say "Empty until
  Milestone 13". No content was added.
- **I. Component counts.** The inventory on disk is 19 commands, 16 skills, 2 agents
  (`biq-research-scout`, `biq-analysis-verifier`) and 6 reference documents.
  - `architecture.md` §13's repository tree now states these shipped counts, and notes that `biq-data-profiler` is
    deferred (ADR-0036) and that §4 describes the 20-skill design. §4 itself is unchanged: its 20 skills are the
    architecture's designed set.
  - `CLAUDE.md` §3 says "(20 skills)". It was **not changed**, because D-07 records that amending `CLAUDE.md` is an owner
    decision. It is left for the owner (§10).
- **M14 status.** In `project_plan.md`:
  - the header reads "Milestone 14 — `IN PROGRESS`", and "Last updated" is 2026-09-27;
  - a dated M14-entry bullet was added;
  - the next gate is M14-2;
  - the summary row reads `IN PROGRESS`;
  - the M14 section heading reads `IN PROGRESS`, and a status table was added beneath the unchanged scope sentence.

## 4. Files created

- `docs/development/2026-09-27-m14-1-entry-reconciliation.md` (this record)

## 5. Files modified

- `project_plan.md`
- `docs/testing/defects.md`
- `architecture.md`
- `docs/decisions/README.md`
- `docs/README.md`
- `docs/examples/README.md`
- `docs/troubleshooting/README.md`

`README.md` was restored to HEAD, so it shows no diff.

## 6. Files deleted

`file.txt`: untracked and empty, deleted by owner decision.

## 7. Features implemented

None. No product code, test, schema or manifest changed.

## 8. Tests performed

- `python3 tests/run_tests.py`
- the documentation and governance test modules
- `claude plugin validate . --strict`
- `git diff --check`
- the M13.2 evaluation-fixture byte-identity check
- a secret scan over the changed files
- the scope audit

## 9. Test results

Reported with real output in the task report.

## 10. Issues discovered

- **`CLAUDE.md` §3 count.** It still says 20 skills, while 16 ship. Changing it is an owner decision (D-07). This is
  unresolved.
- **D-13's count.** D-13 records five unbuilt §4 skills, while the §4 design has 20 skills and 16 ship. The difference
  was not reconciled here, because it needs a component-by-component mapping, which is M14-3 reference work.
- **Stale reference indexes.** `docs/skills/README.md` ("six skills") and `docs/commands/README.md` ("ten" commands)
  are stale. They are per-component reference work for M14-3, and were not changed.

## 11. Decisions made

None beyond the owner's two entry decisions. No ADR was created or edited.

## 12. Architecture changes

None. Only the header status banner, the §13 inventory counts and the §19 index were reconciled.

## 13. Project-plan updates

- M14 → `IN PROGRESS`.
- M14-1 → `REVIEW`.
- The M13 summary row, the M9 rows, the Known-issues rows and D-14 were reconciled as described above.

## 14. Documentation updates

As §5.

## 15. Remaining work

- **M14-2:** the `README.md` rewrite, which also closes D-14's `README.md` part. **It has not been performed.**
- **Reference pages:** per-component pages, including the `docs/skills` and `docs/commands` indexes.
- **Content pages:** worked examples and the troubleshooting guide.
- **Packaging:** the observation left by ADR-0042.
- **Token cost:** the final measurement, which depends on the owner's D-10 decision.
- **Release:** tagging behind the publication gate.
- **Owner decision:** the `CLAUDE.md` count.

**Not performed:** product code changes, evaluations, MCP calls, connectors, tagging, publication, staging, commit or
push.

## 16. Git commit reference

N/A. Nothing was staged or committed. HEAD is `595e910`.
