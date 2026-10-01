# 2026-09-22 — M13-DEF-05: the platform case contract, established; remediation designed, not performed

**Milestone:** M13 — test hardening and evals (M13.2)
**Status on completion:** M13.2 `IN PROGRESS`; M13-DEF-05 `open`
**Supersedes:** None. It establishes the root cause that
`docs/development/2026-09-20-m13-2-e1-execution.md` recorded as a single missing field. That record's account of
the execution stays correct and is left intact.

## 1. Prompt / task performed

"BusinessIQ — M13-DEF-05 Evaluation Infrastructure Remediation": make the 64 M13.2 case files compatible with the
actual harness, with the expected change being `schema_version: "1.0"` added to each. The prompt required the
contract to be established first (§4), forbade blindly adding further metadata (§5), forbade running any
evaluation (§9), and directed that if a closure criterion fails, the exact blocker be reported instead of a
claimed fix (§17).

## 2. Objective

Establish what the Claude Code evaluation harness actually requires of a case file, and remediate M13-DEF-05 if —
and only if — the remediation is a faithful, evidence-backed change.

## 3. Changes made

1. **Read the contract out of the shipping binary.** `claude plugin eval --help` for the flag surface, then a
   read-only scan of `claude.exe` (2.1.278) for the case loader. The bundle contains both the loader's validation
   and an embedded authoring guide. No evaluation was run; no model was invoked.
2. **Measured the 64 cases against it.** They miss the contract on four counts, not one.
3. **Did not add `schema_version`.** The prompt's default change is ruled out by its own escape clause ("unless the
   actual harness proves otherwise"): adding it loads nothing, and would touch 64 files for no effect.
4. **Designed the migration** and wrote it up as **ADR-0044 (Proposed)**, staged so that no stage guesses.
5. **Corrected the defect record and the documentation** that had described the cause as a missing field.

## 4. Files created

| File | Purpose |
|---|---|
| `docs/decisions/ADR-0044-platform-format-eval-cases.md` | Proposed migration architecture |
| `docs/development/2026-09-22-m13-def-05-investigation.md` | This record |

## 5. Files modified

| File | Change |
|---|---|
| `docs/testing/eval-suite.md` | New *The platform's actual contract* section; status banner, blocking-defect row and G-3 row corrected |
| `docs/testing/defects.md` | M13-DEF-05: root cause established, register row and `affected_component` corrected; status unchanged |
| `project_plan.md` | Known-issues row: real root cause, ADR-0044 pointer |
| `docs/decisions/README.md` | ADR-0044 indexed as Proposed |

**No case file, no test, and no production file was changed.**

## 6. Files deleted

None.

## 7. Features implemented

None. This task changed no executable behaviour of any kind.

## 8. Tests performed

No new tests were written, because nothing executable changed. The existing guards were run to prove the
documentation edits did not break their invariants, plus the standard repository checks:

```
python tests/run_tests.py unit.test_m13_eval_cases
python tests/run_tests.py unit.test_m13_coverage_matrix
python tests/run_tests.py unit.test_m13_manual_observation_pack
claude plugin validate . --strict
git diff --check
```

The full 4,879-test regression was **not** run: the prompt restricted it to production-relevant changes, and there
were none.

## 9. Test results

| Check | Result |
|---|---|
| `unit.test_m13_eval_cases` | 59 pass |
| `unit.test_m13_coverage_matrix` | 33 pass, 1 skip (pre-existing conditional) |
| `unit.test_m13_manual_observation_pack` | 16 pass |
| `claude plugin validate . --strict` | ✔ Validation passed |
| `git diff --check` | clean |
| Secret scan | clean |
| Personal-data scan | clean |

**Evaluation cases executed: 0. `claude plugin eval` invoked: No. Model calls from the harness: 0. Cost: $0.**

## 10. Issues discovered

**M13-DEF-05's root cause is four structural mismatches, not a missing field.** The loader requires
`schema_version`, `name`, an `execution` block with a non-empty `prompt`, and at least one grader of one of six
strict types. The repository's 133 graders use a `kind` / `check` / `property` vocabulary; grader objects reject
unknown keys, so they cannot be carried as extras. Top-level unknown keys **are** stripped, which is what makes a
dual-layer file possible at all.

**Two facts no document supplies**, both now inside G-3 and both needing a run:

- the trace tool name a plugin **slash command** fires under — 24 graders depend on it;
- how a case's input reaches the sandbox cwd, given that prompts name repository-relative paths and the guide
  forbids absolute ones.

**No new defect was raised.** Both belong to M13-DEF-05 and G-3, which already exist.

## 11. Decisions made

**ADR-0044 (Proposed)** — one case file carrying the platform's keys and the BusinessIQ semantic keys, with the
platform keys derived mechanically from the semantic ones, and a three-stage migration: translate the 109
evidenced graders; buy the two unknowns with one authorised pilot read for its trace; finish the remaining 24.

An ADR is warranted under `docs/decisions/README.md`'s bar: it fixes a data contract, it is expensive to undo once
64 files and the validator depend on it, and it rejects the change the prompt expected.

**It is Proposed, not Accepted.** The owner accepts ADRs in this repository, as with ADR-0042.

## 12. Architecture changes

None. `architecture.md` lists accepted ADRs only, so ADR-0044 is not indexed there yet.

## 13. Project-plan updates

The M13-DEF-05 known-issues row now carries the established root cause and the ADR-0044 pointer. **M13.2 remains
`IN PROGRESS`; M13-DEF-05 remains `open` and blocking.** No status was advanced.

## 14. Documentation updates

`docs/testing/eval-suite.md`, `docs/testing/defects.md`, `project_plan.md`, `docs/decisions/README.md`, the new ADR
and this record. `coverage-matrix.md` and `manual-observation-pack.md` needed no change: no evidence class moved.

## 15. Remaining work

1. **Owner decision on ADR-0044.** Everything below depends on it.
2. Stage 1 — migrate the four structural keys and the 109 evidenced graders; extend the §E.5 validator to both
   layers and their derivation.
3. Stage 2 — one authorised pilot run, read for its trace.
4. Stage 3 — migrate the remaining 24 graders, then re-attempt §E.1.
5. Unchanged and still open: the twelve `manual_observation` scenarios, V-4, and the Unix runtime verification.

## 16. Git commit reference

None. Nothing staged, committed or pushed. Base `21ee21b`.
