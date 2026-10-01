# 2026-09-23 — §F.6 scaffold coverage: the remaining 37 business-file cases stage their fixtures

**Milestone:** M13 — test hardening and evals (M13.2)
**Status on completion:** M13.2 **`IN PROGRESS`**; M13-DEF-07 `fixed_infrastructure` with its **scope now completed**
(not reopened); M13-DEF-05 still `open` and blocking; §E.1 outcome **(a)** unchanged; **no evaluation run**
**Supersedes:** None. It carries out item 3 of the minimum remaining work from the 2026-09-23 closure audit, after the
K.4 line-ending repair.

## 1. Prompt / task performed

The owner's §F.6 scaffold-preparation prompt, carrying three authoritative owner decisions: the 12 manual-observation
scenarios are **not** required under the recorded E.1 outcome (a); §F.9 permits a suite execution to stop at a hard
ceiling with unreached cases recorded `not_executed`; and the closing suite execution will be authorised at a **$75 hard
ceiling**. Non-paid: no `claude plugin eval`, no credits, no commit, push or staging, no reset/restore/clean/stash.

**No evaluation was run.** `claude plugin eval` was not invoked and no credit was spent. No manual scenario was created
or executed, and `docs/testing/manual/` still does not exist.

## 2. Preflight counts, confirmed before anything was written

| Check | Value |
|---|---|
| Total cases | **64** |
| `requires_business_file: true` | **38** |
| Already carrying a scaffold | **1** (`a01-read-only-anomaly-detection`) |
| Lacking a scaffold | **37** |
| Declared inputs per business-file case | **exactly 1**, for all 38 |
| Inputs that exist and sit under an admitted root | **38 / 38** |
| Ambiguous, missing or inconsistent mappings | **0** |

The counts matched the audit exactly, so no stop condition fired.

## 3. Where each mapping came from

Nothing was inferred. For every case the scaffold was derived from three facts already in its own file: its declared
`inputs` (exactly one path), that the same path appears verbatim in its `prompt`, and that the file exists under
`assets/demo-data/` or `tests/fixtures/eval_inputs/`. Each of those was asserted at generation time, so a case with an
undeclared, absent or prompt-mismatched fixture could not have produced a scaffold.

| Fixture | Cases |
|---|---|
| `assets/demo-data/northwind_sales.csv` | 35 (34 newly staged + the pilot case) |
| `tests/fixtures/eval_inputs/s3_01_monthly_amounts.csv` | 1 |
| `tests/fixtures/eval_inputs/s3_02_order_revenue.csv` | 1 |
| `tests/fixtures/eval_inputs/s3_03_monthly_revenue.csv` | 1 |

The destination is always the **same relative path** as the source, which is what makes the path the prompt names
resolve inside the run directory.

## 4. What was added

37 `scaffold.sh` files, one per case directory, each with the same four effective lines as the approved pilot scaffold
and differing only in its fixture path:

```sh
set -eu
repo=$(cd "$(dirname "$0")/../../.." && pwd)
mkdir -p <fixture directory>
cp "$repo/<fixture>" <fixture>
```

All 38 scaffolds now share **one** line shape — `set`, `repo=$(cd`, `mkdir`, `cp` — verified across the set. The
repository root comes from `$0` because the harness passes a scaffold no `CLAUDE_PLUGIN_ROOT`, which is also what keeps
absolute paths out of the files.

Each of the 37 case files gained the declaration, inserted at exactly the position the pilot case carries it:

```yaml
context:
  scaffold_script: scaffold.sh
```

**Nothing else in any case file changed** — no prompt, grader, expected property, safety declaration, tool grant,
routing key, coverage definition, evidence class or contract. No production, engine or runtime file was touched.

## 5. The validator change: a hand-kept list became an invariant

`STAGED_CASES` (a literal tuple) and `UNSTAGED_COUNT = 37` existed only while the mechanism was proved on one case.
Extending them to 38 entries would have been a list to maintain by hand. They were replaced by the invariant the
situation now supports:

> **A case declares a scaffold if and only if it requires a business file.**

Asserted in both directions, plus `BUSINESS_FILE_COUNT = 38` so that adding or removing a business-file case has to move
that number deliberately. The assertion is **not** tautological: one side is the `requires_business_file` field, the
other is the presence of `context.scaffold_script` *and* the file on disk, and a mismatch in either direction fails.

Two assertions were added rather than duplicated: every scaffold stages its own case's declared input and that input
exists under an admitted root and appears in the prompt; and no business-file case is left without one. The existing
§F.6 content guard — four permitted line forms, two-way input agreement, source equal to destination, ASCII/LF/final
newline, no absolute path, grant token or URL — already covered the rest and was reused unchanged.

## 6. Validation

| Property required | Result |
|---|---|
| Business-file cases | **38** |
| Business-file cases with a scaffold | **38** |
| Business-file cases missing a scaffold | **0** |
| Scaffolds on non-business-file cases | **0** |
| Declared set equals the on-disk set | **yes** |
| Each scaffold references only its declared fixture | asserted for all 38 |
| The fixture exists | asserted for all 38 |
| Destination matches the case contract | source equals destination, asserted |
| Staged bytes byte-identical to the source | **38 / 38**, by execution |
| No extra files staged | **38 / 38** — the run directory holds exactly the one fixture |
| No absolute host-specific path | **0 hits** across all 38 scaffolds and all 64 case files |
| No network, package, auth, MCP or web behaviour | **0 hits** (`curl`, `wget`, `http`, `pip`, `apt-get`, `sudo`, `ssh`, interpreters, connector and web tool names) |
| Fixtures unmodified by staging | size and mtime unchanged after running all 38 |

`integration.test_m13_eval_scaffold` now runs **all 38** scaffolds under the harness's exact invocation — `bash <script>`,
the run directory as the working directory, and only the ten variables the harness passes — rather than the pilot case
alone.

## 7. Platform contract

| | |
|---|---|
| Total cases | 64 |
| Platform-loadable | **64 / 64** |
| Platform-contract problems | **0** |
| Graders mapped | **133 / 133**, 0 pending, 0 dropped |
| Semantic case content changed | **no** — only the `context.scaffold_script` declaration the established contract requires |
| Manual-observation pack | untouched; `docs/testing/manual/` still absent; not required under owner decision 1 |
| §E.1 outcome | **(a)**, unchanged |

## 8. Regression

| Check | Result |
|---|---|
| `python3 tests/run_tests.py` | **Ran 5076 tests — OK**, 0 failures, 0 errors, **31 skipped** |
| `claude plugin validate . --strict` | **✔ Validation passed** |
| `git diff --check` | **clean** |
| K.4 secret scan (repository's own `TOKEN_SHAPES`) | **PASS** — 0 hits over 1,126 added tracked lines, and 0 hits in a direct scan of all 38 scaffolds and all 64 case files |
| `unit.test_m13_eval_cases` | Ran 103 — OK (was 102; the hand-kept-list test became two invariant tests) |
| `integration.test_m13_eval_scaffold` | Ran 11 — OK (was 8) |
| `unit.test_m13_coverage_matrix` · `unit.test_m13_def10_eval_grant` · `unit.test_m13_eval_results` | 33 (skipped=1) · 30 · 28 — all OK |

Test count 5072 → **5076** (+4: two net in the case validator, three in the scaffold suite, less one replaced). Skip
count **unchanged at 31**.

## 9. Environment observation

`.git/index.lock` is still present and was **not** touched, per the prompt. It remains stale (no `git` process running),
so `git status --short` continues to overstate the modified count; `git diff --name-only` is the authoritative view.
Recorded in `2026-09-23-k4-line-ending-repair.md`.

## 10. What this does and does not establish

**Does:** the suite is now *structurally* ready for the closing execution — every case that needs a business file can
reach it, every case is platform-loadable, and every grader is mapped.

**Does not:** it runs nothing. **M13-DEF-05 remains `open` with `blocks_m13_completion: yes`**, §L (a) still requires the
suite executed under §F, §K.5's matrix re-check still depends on that run, a01's `automated_pass` is still unrecorded,
and **M13.2 remains `IN PROGRESS`**. Nothing was closed and no status was advanced.

## 11. Remaining work

1. **The closing suite execution** — owner-gated, $75 hard ceiling, at least two invocations because §F.8 mandates
   different ablation per suite.
2. Record every case's §E.6 class and per-run results; re-check the matrix against that closing run (§K.5).
3. Close **M13-DEF-05**; close **R-01** under §E.1 (a) if the owner chooses.
4. Governance cleanup of the two documents that overstate the manual-observation requirement under outcome (a).

## 12. Git commit reference

**No commit, no push, no staging.** Nothing reset, restored, cleaned, reverted or stashed. Branch `main`, HEAD
`21ee21b21213ad80273650f056ef2f318023742c`.
