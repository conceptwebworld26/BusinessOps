# 2026-09-22 — M13.2 evaluation-harness remediation: the case can reach its input, and what still stops it

**Milestone:** M13 — test hardening and evals (M13.2)
**Status on completion:** M13.2 `IN PROGRESS`; **M13-DEF-07 `fixed_infrastructure`**; **M13-DEF-08 `open` (product,
owner decision)**; **M13-DEF-09 `fixed_infrastructure`**; M13-DEF-05 `open`; M13-DEF-06 `fixed_infrastructure`
**Supersedes:** None. It follows `2026-09-22-m13-2-stage2-pilot.md` and `2026-09-22-m13-def-06-remediation.md`, and
records the second 2026-09-22 pilot, which those two predate.

## 1. Prompt / task performed

The owner's post-Stage-2 remediation prompt: remediate the evaluation infrastructure so the next authorised pilot can
actually exercise the command under test. Explicitly **no** `claude plugin eval`, no paid evaluation, no web, no MCP,
no authentication, no production change made merely to satisfy the evaluator, no commit, no push, and no discarding of
existing uncommitted M13.2 work. Eight phases: inspect, fix input staging, resolve the interpreter, trace preservation,
ADR-0044 stage 3, defect governance, documentation, testing.

**No evaluation was run in this task.** `claude plugin eval` was not invoked. The only process this task started was
`bash`, running the four-line scaffold under test, and the repository's own test suite.

## 2. Objective

Make the 2026-09-22 pilot's failure diagnosable and, where the cause is ours, fixed — while keeping the failure itself
on the record as `automated_fail`, because ADR-0039 §E.6 says an observed failure outranks an unavailability.

## 3. Changes made

### 3.1 The platform contract, read from the binary (no run, no model)

Claude Code 2.1.278 is a single ELF binary. Its embedded case schema and eval runner were read with `strings`. This
established, as fact rather than inference:

| Fact | Consequence |
|---|---|
| The case schema's `context` block holds `scaffold_script`, `history_file` and `add_dirs` | A case *can* stage its own input; nothing else in the schema delivers a file |
| `scaffold_script` resolves against the **case directory** (`vo()` → `Ci(e.caseDir, …)`) | The bare name `scaffold.sh`, in the case directory, is the correct spelling — and ADR-0039 §A.2 already puts it there |
| The runner is `bash <script>`, `cwd` = the run's working directory, env = `PATH`, `HOME`, `USERPROFILE`, `TMPDIR`, `TMP`, `TEMP`, `TERM`, `GIT_CONFIG_NOSYSTEM`, `USER_TYPE`, `NODE_ENV`, 120s timeout, stderr captured | A copy to a repository-relative path makes that path resolve for the agent. **`CLAUDE_PLUGIN_ROOT` is absent**, so the script must derive the repository root from `$0` — which is also what keeps an absolute path out of the file |
| Without `--scaffold`: "its `scaffold_script` is not run … the case runs against an unstaged workspace" | The flag is required, and §F.6 already authorises it under a condition |
| `add_dirs` grants reads only, and only inside the case directory or the plugin under test | A viable read grant, but it does not make a *relative* path resolve, so it does not satisfy the case as written |
| The grader union is exactly `regex`, `tool_order`, `tool_used`, `file_exists`, `llm`, `baseline` | Independently reproduces what `tests/unit/test_m13_eval_cases.PLATFORM_GRADERS` already held — a useful cross-check of ADR-0044 Phase 1 |
| `tool_used.input_match` is evaluated as `new RegExp(n.input_match).test(e.inputText)` | `input_match` is a **JS RegExp over the tool call's input text**, so a command name used as a substring does not depend on the identifier's spelling or prefix |
| `--keep-temp` "preserve[s] each run's sandbox (workspace + trace.jsonl)" | The one supported way to obtain the trace ADR-0044 stage 3 needs |

### 3.2 The pilot's assumptions, each confirmed or corrected

The prompt asked that four assumptions be established from local evidence, not guessed.

1. **The relative business-file path was not available inside the sandbox — confirmed.** The run's working directory is
   a fresh directory that is not the repository; the case declared no `context`, so nothing was copied into it.
2. **The repository copy cannot simply be read from the agent sandbox — confirmed.** The harness passes an explicit
   `--allowed-tools` list built from the run `cwd`, `tmpDir` and the declared read roots. With `add_dirs` empty, the
   repository path was not a read root, which is exactly what the agent reported: "`Read` … blocked by your current
   permission mode".
3. **`python3` is present while `python` is absent — confirmed.** `command -v python` prints nothing; `command -v
   python3` prints `/usr/bin/python3`; `python3 -V` prints `Python 3.14.4`; `dpkg-query -l python-is-python3` reports
   no package.
4. **"The two grants therefore do not match a python3 command" — confirmed, but the conclusion drawn from it was
   wrong.** The grants are not the defect. `Bash(python:*)` and `Bash(python *)` match ADR-0042's accepted invocation
   exactly; all 14 command bodies invoke bare `python` and `grep -rl python3 commands/` matches **0** files. The grants
   name precisely what the product asks for. What does not exist is the interpreter. See §3.4.

### 3.3 Input staging — fixed (M13-DEF-07)

The mechanism is the one accepted governance already provides for, and the obstacle was our own validator:

- **ADR-0039 §F.6:** "`--scaffold` is used only if a case's scaffold script does nothing but copy repository synthetic
  inputs into the scaffold directory. E.5 reads every scaffold script and asserts this."
- **ADR-0039 §A.2** admits under `evals/`: "`case.yaml` or `prompt.md`, its graders, and any scaffold script §F.6
  permits".
- **ADR-0039 §E.5's fourth assertion lists exactly four items, and `--scaffold` is not among them.**

`tests/unit/test_m13_eval_cases.py` had nevertheless put `--scaffold` in `FORBIDDEN_FLAGS`, promised "no scaffold
script" in its docstring, and rejected any file in a case directory other than `case.yaml`. It was stricter than the
ADR it implements, and the effect was not a safe default: the one mechanism that could stage an input was unreachable,
so no case ever tried and the gap stayed invisible until a paid run hit it.

Both artefacts therefore changed together — a scaffold alone would have been rejected by the validator; a relaxed
validator alone would have staged nothing.

`evals/approval/a01-read-only-anomaly-detection/scaffold.sh`, four effective lines:

```bash
set -eu
repo=$(cd "$(dirname "$0")/../../.." && pwd)
mkdir -p assets/demo-data
cp "$repo/assets/demo-data/northwind_sales.csv" assets/demo-data/northwind_sales.csv
```

It runs no interpreter, reaches no network, starts no server, authenticates to nothing, writes only inside the run
directory, and copies one file one way — the user's source data is never written to (`CLAUDE.md` §2 principle 7).

**The guard is a reader, not a ban.** `Scaffold` in the validator holds the §F.6 assertion: every effective line must
match one of four permitted forms, so the script cannot acquire an interpreter, a network call or an outside write
without the test failing; what it copies must equal the case's declared `inputs` **both ways**; each destination must
equal its source path, so the staged path is the path the prompt names; every `mkdir -p` must hold something copied;
and the file must be ASCII, Unix-terminated, and free of absolute paths, grant tokens and URLs.

**The effect is proved by running it.** `tests/integration/test_m13_eval_scaffold.py` reproduces the harness
invocation exactly — `bash <script>`, the run directory as `cwd`, and *only* the ten variables the harness passes — and
asserts the declared path resolves, the bytes are identical, nothing else is created, a rerun is safe, a directory name
with spaces works, and the repository copy's size and mtime are unchanged.

**Scope, stated rather than implied.** One case is staged. The other **37** `requires_business_file` cases are not, and
`UNSTAGED_COUNT = 37` asserts that number so extending the mechanism must lower it deliberately. The mechanism is
proved on one case before it is copied 37 times.

### 3.4 The interpreter — NOT fixed; an owner decision (M13-DEF-08)

This is the stop condition the prompt named: *"If the existing grant contract cannot be satisfied without changing the
authorized command policy, DO NOT silently change it. Record the exact owner decision required and stop that portion."*

The preferred resolution order was worked through and each option rejected for a stated reason:

1. **Expose `/usr/bin/python3` as `python` through a platform setup mechanism.** `execution.env` exists and would carry
   a `PATH`, but no `python` executable exists anywhere on the machine for a `PATH` to find. Creating one needs either a
   scaffold that does more than copy inputs — which §F.6 forbids and the new `Scaffold` guard rejects — or an absolute
   `/usr/bin` path in the case file, which the validator's no-absolute-path and no-environment-dependence assertions
   forbid. **No platform-supported mechanism exists.**
2. **Install a package.** Prohibited by the prompt, and by `CLAUDE.md` §4 without an ADR.
3. **Grant `Bash(python3:*)` instead.** That changes the authorised grant policy. Not done silently, and not done.
4. **Therefore: stop and record.**

**Why an evaluation-side shim was rejected rather than deferred.** A scaffold-created `python` shim plus a `PATH` entry
would make the case green while every real user on this platform stayed broken — the evaluator would be repaired into
silence about the very defect it found. That inverts the prompt's own rule against changing production behaviour to
satisfy the evaluator.

**Why it is a `product` defect.** §G.1 defines `product` as BusinessIQ behaviour. The evidence is not confined to the
evaluator: on this machine no BusinessIQ command can enter its engine, through any of the 14 command bodies, and the
`README.md` invocation `python tests/run_tests.py` fails too — the suite runs only as `python3 tests/run_tests.py`.
ADR-0042's *Requirements* 4 asks that the entry work "on Windows and Unix-like systems, with no hard-coded path"; the
path is not hard-coded, but the interpreter **name** is, and Debian and Ubuntu ship Python 3 only as `python3` under
PEP 394. It is also the residue of M13-DEF-04, whose register entry still lists "Unix-like runtime verification" as
open.

**The owner decision required**, in outline:

| Option | What it costs | What it leaves |
|---|---|---|
| **(a)** Provide `python` on the evaluation machine (e.g. the distribution's `python-is-python3`, or a `python` on `PATH` outside the repository) | No repository change; the authorised grants stay exactly as they are; the next pilot can run unchanged | The product defect stands for other users on such platforms |
| **(b)** Amend ADR-0042 to `python3` across the 14 commands | A production change, its own prompt and an ADR amendment; must be checked against Windows, where `python3` is often the absent one | Fixes users and the evaluator together |
| **(c)** Resolve an interpreter inside the launcher | A larger production change and an ADR; adds a resolution path to a deliberately minimal entry | Most portable |

M13 does not choose, and does not fix: ADR-0039 I-13 and §G.2 reserve product defects to the owner. Recording a defect
does not authorise fixing it.

### 3.5 Trace preservation — fixed (M13-DEF-09)

`--keep-temp` is confirmed by the CLI as preserving "each run's sandbox (workspace + trace.jsonl)". The procedure named
no diagnostic flag, so the pilot's `tracePath` pointed at a deleted file and the one question ADR-0044 stage 2 exists
to settle could not be answered by a run that had already been paid for.

`docs/testing/eval-suite.md` now requires `--keep-temp` on any run whose purpose includes a trace-dependent question —
every run while the 24 graders are pending — and carries a table of what the preserved sandbox is read for: turns, tool
calls with their exact names, whether the command fired and how it appears, whether the input was staged, what the
shell grant resolved to, and which graders scored. It also states that a pending mapping is completed from observed
trace events **or not at all**.

Separately, the harness's default results directory, `evals/results/`, broke three §E.5 layout assertions. That output
is generated and already gitignored, so the layout assertions now step over it; the contract is unchanged for
everything else.

### 3.6 ADR-0044 stage 3 — narrowed, deliberately not completed

The mapping's **shape** is now settled: `tool_used`, with `command_invoked` → `min: 1` and `command_not_invoked` →
`max: 0`; `tool` is an exact identifier compared with `===`; `input_match` is a JS RegExp over the tool input text, so
the identifier's spelling and prefix do not matter to a name used as a substring.

The **identifier** is not settled. Claude Code 2.1.278 collects plugin commands of `type: prompt` whose `loadedFrom`
is `plugin` into its slash-command tool skills, and the eval help names `tool_used: Skill` as the plugin-fired
indicator under ablation; together those make **`Skill`** the leading candidate. It was **not written in**, for three
reasons:

1. Both facts come from reading the binary, not from a trace, and ADR-0044 stage 3 requires an observed trace.
2. The `input_match` text a BusinessIQ command produces has not been observed at all.
3. A third question is genuinely behavioural: whether the agent invokes the command as a tool rather than following the
   command file as text — which is part of what `command_invoked` exists to observe. A mapping cannot settle it.

Writing the candidate in would turn an inference into an apparent observation and would make the three near-miss cases
platform-loadable on it, which is what the pending boundary exists to prevent. **Totals are unchanged: 109 mapped, 24
pending, 61 of 64 cases loadable, 0 dropped.** The full finding, including what would settle it, is recorded in
`docs/testing/grader-migration-map.json` under `pending_mapping_finding`.

### 3.7 The pilot's own result, recorded as it happened

The second 2026-09-22 pilot executed: 5 turns, `error: null`, one scored grader, 20s, **$0.1712634** of a $5 ceiling.
`g-no-approval-request` failed on judge votes `FAIL PASS FAIL`. The case is **`automated_fail`**.

The case file does not assert that class by hand. `EvidenceAndMatrix.test_the_pilot_class_is_the_one_the_admissibility_
rule_computes` loads `classify_result` from `tests/unit/test_m13_eval_results.py`, applies it to the committed result
shape, and asserts the answer equals the case file's `evidence_class`. The two cannot drift.

**M13-DEF-06 is not reopened.** The pilot's failure is evidence its rule works. The rule met its first genuinely
executed run and admitted it, and it was tempting to classify an environmentally-caused failure as
`execution_unavailable` — §E.6 forbids exactly that, because a rule that also refused executed failures would let any
infrastructure problem erase a real observed failure, which is M13-DEF-06's error with the sign reversed. Both shapes
are now pinned: `2026-09-22-stage2-pilot.json` (refused, must not be admitted) and `2026-09-22-pilot-executed.json`
(executed and failing, must be admitted).

**Three things are kept apart** in `eval-suite.md`, because the one executed run conflates them otherwise:
evaluation-infrastructure failure (**yes**), observed automated grader failure (**yes**), and BusinessIQ behaviour
(**untested** — the command never ran). No summary may present the second as though it were the third.

## 4. Files created

| File | Purpose |
|---|---|
| `evals/approval/a01-read-only-anomaly-detection/scaffold.sh` | Stages that case's one declared input (§F.6) |
| `tests/integration/test_m13_eval_scaffold.py` | The execution proof: 8 tests under the harness invocation |
| `tests/fixtures/eval_results/2026-09-22-pilot-executed.json` | The executed-and-failing result shape, as a regression fixture |
| `docs/development/2026-09-22-m13-2-eval-harness-remediation.md` | This record |

## 5. Files modified

| File | Change |
|---|---|
| `evals/approval/a01-read-only-anomaly-detection/case.yaml` | `context.scaffold_script`; `evidence_class` → `automated_fail` with its reason; header comment corrected |
| 21 case files (a01–a18, r17–r19) | The 24 pending graders' `pending_reason` narrowed to the established finding |
| `tests/unit/test_m13_eval_cases.py` | `context` admitted to the reader and the key set; `--scaffold` removed from `FORBIDDEN_FLAGS` with the reason; layout assertions admit the scaffold and step over `results/`; new `Scaffold` class (11 assertions); evidence assertions record the pilot and derive its class from the rule; `STAGED_CASES`, `UNSTAGED_COUNT`, `PILOT_RESULT`, `NESTED_KEYS`, `SCAFFOLD_NAME`, `RESULTS_DIR`, `PILOT_REASON` added, `ATTEMPTED_REASON` removed |
| `tests/unit/test_m13_eval_results.py` | `EXECUTED` fixture; new `TheExecutedPilotIsAdmittedAndFails` class (6 assertions); committed-result count 1 → 2 |
| `docs/testing/eval-suite.md` | Recorded state as of 2026-09-22; the three-way distinction; layout; the settled pre-flight items; `--scaffold` and `--keep-temp` requirements and what the sandbox is read for; the narrowed pending boundary; the admissibility rule's second direction |
| `docs/testing/defects.md` | M13-DEF-07, M13-DEF-08, M13-DEF-09 added; register state re-verified; M13-DEF-05 and M13-DEF-06 notes updated |
| `docs/testing/grader-migration-map.json` | `note` corrected; `pending_mapping_finding` added; 24 `pending_reason` values narrowed. Totals unchanged |
| `docs/testing/coverage-matrix.md` | S3-11 and S5-01 → `automated_fail`, with cells stating the run never reached the command and the requirement is still untested |
| `project_plan.md` | The executed pilot; §E.1 not satisfied and R-01 still `BLOCKED`; M13.2 rows; three known-issue rows; two new task rows |

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | User-reachable? |
|---|---|---|
| Eval input staging for a `requires_business_file` case | `evals/approval/a01-…/scaffold.sh` + `context.scaffold_script` | No — evaluation infrastructure only |
| The §F.6 static assertion | `tests/unit/test_m13_eval_cases.Scaffold` | No |
| Staging execution proof | `tests/integration/test_m13_eval_scaffold.py` | No |
| Evidence class derived from the admissibility rule, not asserted by hand | `tests/unit/test_m13_eval_cases.EvidenceAndMatrix` | No |

No production feature was added or changed.

## 8. Tests performed

```
python3 -m unittest tests.unit.test_m13_eval_cases
python3 -m unittest tests.unit.test_m13_eval_results
python3 -m unittest tests.integration.test_m13_eval_scaffold
python3 -m unittest tests.unit.test_m13_coverage_matrix
python3 tests/run_tests.py
claude plugin validate . --strict
```

`claude plugin eval` was **not** run. No model was invoked, no network reached, no MCP tool called, no authentication
performed, nothing published.

## 9. Test results

| Command | Result |
|---|---|
| `tests.unit.test_m13_eval_cases` | **Ran 100 tests — OK** (90 before; the 3 failures the pilot's output caused are gone) |
| `tests.unit.test_m13_eval_results` | **Ran 28 tests — OK** (22 before) |
| `tests.integration.test_m13_eval_scaffold` | **Ran 8 tests — OK** |
| `tests.unit.test_m13_coverage_matrix` + the two eval modules | **Ran 161 tests — OK (skipped=1)** |
| `python3 tests/run_tests.py` | **Ran 4956 tests in 293.735s — OK (skipped=29)** |
| `claude plugin validate . --strict` | **✔ Validation passed** |

Baseline for honesty: before this task the validator failed 3 tests, all caused by the pilot writing
`evals/results/2026-09-22T13-11-30-725Z/` into a directory the layout contract did not admit
(`test_the_five_suites_exist_and_nothing_else`, and `test_every_file_under_evals_is_a_case_yaml` twice).

Secret scan and personal-data scan over the 32 changed files: no token-shaped string, no credential assignment, no
email address, no URL outside the reserved domains.

## 10. Issues discovered

| ID | Class | Status |
|---|---|---|
| **M13-DEF-07** | infrastructure | `fixed_infrastructure` — staging implemented and proved; 37 cases still unstaged, asserted |
| **M13-DEF-08** | **product** | **`open` — an owner decision is required. It blocks the next pilot** |
| **M13-DEF-09** | infrastructure | `fixed_infrastructure` — `--keep-temp` required; layout assertions step over `results/` |

Also discovered, and recorded inside M13-DEF-07 rather than as its own id: the static validator forbade the very
mechanism ADR-0039 §F.6 permits. A guard stricter than its own governance does not fail safely.

## 11. Decisions made

**No ADR was written, and none is needed.** Every mechanism used is authorised by accepted text: §F.6 authorises the
scaffold, §A.2 places it in the case directory, §E.5's list never contained `--scaffold`, and §E.6 fixes the evidence
class. The one decision that *would* need an ADR — changing ADR-0042's interpreter name — is left to the owner
(M13-DEF-08) and was not taken.

## 12. Architecture changes

None. `architecture.md` was not modified: no layer, contract, extension point or approval rule changed, and the
evaluation harness is not part of the product architecture.

## 13. Project-plan updates

- M13.2 stays **`IN PROGRESS`**.
- §E.1 outcome: `COMPLETED (b)` → **`IN PROGRESS` — not satisfied**. §E.1 requires `--runs 3`; both pilots were
  authorised for one run, so no outcome is recorded from them.
- **R-01 stays `BLOCKED`.** Execution is now demonstrably available, which is the evidence outcome (a) rests on, but
  (a) may be recorded only from a conforming measurement.
- Static validator and coverage matrix rows updated; two new task rows (input staging; the interpreter, `BLOCKED` on
  the owner).
- Three known-issue rows added. **M13-DEF-05 stays `open` and still blocks M13.2 completion.**

## 14. Documentation updates

`docs/testing/eval-suite.md`, `docs/testing/defects.md`, `docs/testing/coverage-matrix.md`,
`docs/testing/grader-migration-map.json`, `project_plan.md`, and this record. ADR-0044 was **not** rewritten: nothing
architectural changed, its stage 3 boundary still stands, and accepted history is left intact.

## 15. Remaining work

1. **The owner decides M13-DEF-08.** Nothing else unblocks the pilot case: staging is fixed, and a rerun without an
   interpreter produces the same failure.
2. Then one run of `a01-read-only-anomaly-detection` at `--runs 3`, with `--scaffold` and `--keep-temp`, under a stated
   ceiling. That run both attempts §E.1 properly and yields the trace stage 3 needs.
3. Read the preserved trace and complete the 24 mappings **from it**, or leave them pending with the reason.
4. Extend staging to the remaining 37 `requires_business_file` cases, lowering `UNSTAGED_COUNT`.
5. The twelve `manual_observation` scenarios remain outstanding.

## 16. Git commit reference

**No commit, no push, no staging.** Nothing was reset, cleaned, reverted or stashed; all pre-existing uncommitted
M13.2 work is intact. Branch `main`, base `21ee21b21213ad80273650f056ef2f318023742c`, working tree dirty as before
plus this task's 32 files.
