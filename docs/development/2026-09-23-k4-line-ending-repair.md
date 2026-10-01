# 2026-09-23 — K.4 repair: LF restored in 59 tracked files, and a stale index lock recorded

**Milestone:** M13 — test hardening and evals (M13.2)
**Status on completion:** M13.2 `IN PROGRESS`; **ADR-0039 §K.4 now satisfied**; no defect status changed; no milestone
status changed
**Supersedes:** None. It carries out the first item of the minimum remaining work identified in
`2026-09-23-m13-2-closure-audit` reporting (the closure/readiness audit of the same day).

## 1. Prompt / task performed

The owner's non-paid K.4 remediation prompt: restore LF line endings in the tracked files affected by an LF→CRLF
conversion, without changing substantive content. No `claude plugin eval`, no credits, no product, engine, runtime,
eval-semantics, grader, coverage or contract change, no commit, push or staging, and none of
`git checkout|restore|reset|clean|stash`.

**No evaluation was run.** `claude plugin eval` was not invoked and no credit was spent.

## 2. Why K.4 was failing

ADR-0039 §K.4 requires "`git diff --check` is clean, and a secret-pattern scan of added lines finds only synthetic
canaries". It was failing on **two independent counts**:

| Cause | Scale |
|---|---|
| **59 tracked text files converted LF → CRLF** in the pre-existing uncommitted working tree. Git reports each `\r` as trailing whitespace | **24,470** diagnostic lines |
| **`docs/testing/defects.md` ended `\n\n`** — a trailing blank line introduced when the M13-DEF-12 record was appended | **1** diagnostic line (`new blank line at EOF`) |

Total before: **24,471** diagnostics across **60** files.

## 3. Line-ending policy, established from the repository only

No root `.gitattributes`; `core.autocrlf`, `core.eol` and the global `core.autocrlf` are all unset. The only
`.gitattributes` is `tests/fixtures/eval_inputs/.gitattributes` (`* -text`), which holds those byte-exact fixtures out
of text conversion.

The policy therefore comes from the tracked content itself: of **419** tracked files, **418 carry no `\r` in HEAD**. The
single exception is `assets/demo-data/northwind_sales.xlsx`, whose 475 `\r` bytes are binary payload, not line endings.
**LF is the repository's line ending, and no new policy was invented.**

## 4. The affected set, and the finding that made the repair safe

Detection was done in Python over bytes, comparing each modified tracked file's worktree content with its `HEAD`
content. **59 files** qualified: text, `\r\n` in the worktree, no `\r` in HEAD. Also established:

- **0** binary files in the set (no NUL bytes in either version);
- **0** files carrying a lone `\r` not part of `\r\n`;
- **0** files with `\r` in *both* worktree and HEAD, so nothing legitimately CRLF was touched;
- 33 of the 92 modified tracked files were already LF and were left alone.

**The decisive safety finding: all 59 differ from HEAD by line endings and nothing else.** Normalising each to LF makes
it byte-identical to its committed version. So the set carried **no M13 content changes at all**, and the repair could
not put any at risk.

That also settles a §A.3 question. Two of the 59 sit under `assets/`, which §A.3 places off limits to M13:

| File | Effect of the repair |
|---|---|
| `assets/demo-data/generate_demo_data.py` | becomes byte-identical to HEAD |
| `assets/demo-data/northwind_sales.csv` | becomes byte-identical to HEAD |

Restoring LF **removes** a pre-existing modification rather than introducing one, so this is a restoration of the
committed state, not a change to a protected path.

**A detection bug worth recording**, because it produced a wrong answer first: a shell pre-pass classified all 92
modified files as binary. The cause was `grep -qU $'\x00'` — bash cannot hold a NUL in a string, so the pattern was
**empty** and matched every non-empty file. The detection was redone in Python, where byte semantics are exact. The
first result was discarded, not built on.

## 5. The repair

- **59 files:** every `\r\n` replaced with `\n`, written in place with `open(p, 'r+b')` + `truncate()` so the inode and
  the file mode are untouched. No other byte was altered.
- **1 file:** `docs/testing/defects.md` lost exactly one trailing newline, asserted beforehand to end `\n\n` and not
  `\n\n\n`, and asserted afterwards to be identical once trailing newlines are discounted.
- The repository was **not** broadly normalised. Untracked files, unrelated modified files, generated evaluation output
  and gitignored results were not touched.

## 6. Content-integrity proof

Not an impression — a byte comparison, with a snapshot taken before the first write:

| Check | Result |
|---|---|
| BEFORE-content normalised to LF, sha256, vs AFTER-content normalised to LF | **59 / 59 identical, 0 mismatches** |
| Stronger: each repaired file now byte-identical to its `HEAD` blob | **59 / 59** |
| File-mode changes | **0** |
| Inode changes | **0** |
| Files still holding a `\r` | **0** |
| `defects.md` content identical ignoring trailing newlines | **yes**, delta −1 byte |

## 7. K.4 verification

| Check | Before | After |
|---|---|---|
| `git diff --check` | 24,471 diagnostics, 60 files | **clean — PASS** |
| Secret-pattern scan of added lines | — | **PASS — 0 hits** over 1,126 added lines |

The scan uses the repository's own K.4 patterns, `TOKEN_SHAPES` in `tests/unit/test_m13_eval_cases.py`, rather than an
invented mechanism.

## 8. A separate condition found and deliberately left alone: a stale `.git/index.lock`

`git status --short` still reports 92 modified files while `git diff --name-only` reports **33**. The difference is
exactly the 59 repaired files. The cause is git's stat cache: the repaired files' size and mtime changed, and the cache
cannot be refreshed because **`.git/index.lock` exists** (dated 2026-09-22 17:01:36, while `.git/index` is 13:19:42).
`git update-index --refresh` fails with `fatal: Unable to create '…/.git/index.lock': File exists.` and **no `git`
process is running** (`pgrep -a git` finds none), so the lock is stale.

**It was not removed.** It is `.git` internals, outside this task's stated scope, and K.4 does not depend on it —
`git diff --check` rehashes content and passes. `git diff` is the authoritative view of the working tree; `git status`
overstates the modified count by exactly 59 until the lock is cleared. **Recorded for the owner, not acted on.**

## 9. Regression and validation

| Check | Result |
|---|---|
| `python3 tests/run_tests.py` | **Ran 5072 tests — OK**, 0 failures, 0 errors, **31 skipped** |
| `claude plugin validate . --strict` | **✔ Validation passed** |
| `unit.test_m13_coverage_matrix` | Ran 33 — OK (skipped=1) |
| `unit.test_m13_eval_cases` | Ran 102 — OK |
| `unit.test_m13_def10_eval_grant` | Ran 30 — OK |
| `unit.test_m13_def08_runtime_resolver` | Ran 26 — OK |

Test count and skip count are **unchanged** from the pre-repair state (5072 / 31), which is the expected result for a
repair that alters no content. No new failure was introduced and no test was modified.

## 10. Files created and modified

**Created:** `docs/development/2026-09-23-k4-line-ending-repair.md` (this record).

**Modified:** 59 tracked files, CRLF → LF only, each now byte-identical to HEAD; and
`docs/testing/defects.md`, one trailing newline removed.

**No new defect ID was created.** The audit found no existing defect id for this condition, and the remediation prompt
directs that one must not be invented for bookkeeping, so the repair is recorded here. No defect status, milestone
status, ADR, coverage definition, case, grader, fixture, scaffold, prompt or contract was changed. `project_plan.md`,
`docs/testing/eval-suite.md` and the coverage matrix were deliberately **not** edited.

## 11. M13.2 impact

**§K.4 is now satisfied.** The remaining M13.2 completion blockers, unchanged by this task:

1. **The suite has not been executed** — 1 of 64 cases. §L (a) requires "the suite executed under §F". Needs owner
   authorisation, a realistic ceiling, and at least two invocations (§F.8 mandates different ablation per suite).
2. **M13-DEF-05** is `open` with `blocks_m13_completion: yes`. Its stated conditions are met; closure is an owner act.
3. **§K.5** — the matrix re-check against the closing run, which depends on item 1.
4. Recording a01's `automated_pass`, and the closing documentation.

## 12. Git commit reference

**No commit, no push, no staging.** Nothing reset, restored, cleaned, reverted or stashed. Branch `main`, HEAD
`21ee21b21213ad80273650f056ef2f318023742c`.
