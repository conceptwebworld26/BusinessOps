# 2026-09-22 — ADR-0044 stage 3 from the pilot trace, and M13-DEF-10

**Milestone:** M13 — test hardening and evals (M13.2)
**Status on completion:** M13.2 `IN PROGRESS`; **ADR-0044 stage 3 complete**; **M13-DEF-10 raised, `open`,
blocking**; M13-DEF-05 `open` with both conditions met and closure recommended; M13-DEF-06, 07, 09
`fixed_infrastructure`; M13-DEF-08 `fixed_product`; **§E.1 outcome (a) recorded**; **R-01 ready for owner closure**
**Supersedes:** None. It follows `2026-09-22-m13-def-08-runtime-resolution.md` and records the governance consequences
of the three-run pilot run under that task's successor prompt.

## 1. Prompt / task performed

The owner's post-pilot governance prompt: complete ADR-0044 stage 3 from the observed trace, record the new
evaluation-grant defect, analyse the least-privilege remediation, add deterministic tests, and update governance. No
paid evaluation, no `claude plugin eval`, no product or runtime change, no change to the resolver or the approved
runtime architecture, no commit, push, staging, reset, revert or stash.

**No evaluation was run.** `claude plugin eval` was not invoked, and no evaluation credit was spent.

## 2. What the pilot gave us

The owner-authorised three-run pilot (Claude Code 2.1.280, `--runs 3 --threshold 1.0 --scaffold --keep-temp`,
$0.5576718 of a $5 ceiling) produced three admissible runs — 4 turns each, `error: null`, one scored grader each — and
three kept traces. In all three, byte-identically:

| Fact | Value |
|---|---|
| Tool identifier | **`Skill`** |
| Input | `{"skill": "businessiq:anomaly-detection", "args": "assets/demo-data/northwind_sales.csv"}` |
| Result | `Launching skill: businessiq:anomaly-detection` |
| Registered spellings (init event) | commands `businessiq:<command>`; skills `businessiq:biq-<skill>` |
| Agent tool roster | `Task`, `Bash`, `Read`, `Skill`, `TaskStop`, `ToolSearch` |
| Permission mode | `dontAsk` |
| Other tool identifiers | `Bash` only |

## 3. ADR-0044 stage 3

**No new ADR.** ADR-0044 planned stage 3 itself — "migrate the remaining 24 graders against what stage 2 observed" —
and its *Revisit when* names the trace as the trigger at which "stage 3 becomes mechanical". Completing it therefore
executes that decision rather than amending it. A dated **Implementation note — Stage 3** was appended to ADR-0044 in
the same form as the Phase 1 note already in the file; **no decision text, status line, requirement or prior note was
altered.**

**All 24 mapped:**

| Semantic check | Count | Platform grader |
|---|---|---|
| `command_invoked` | 21 (18 approval + 3 routing intended) | `tool_used`, `tool: Skill`, `input_match: businessiq:<command>`, `min: 1` |
| `command_not_invoked` | 3 (routing competing) | the same, with **`min: 0`** and `max: 0` |

**Totals: 133 of 133 mapped, 0 pending, 0 dropped, 174 platform graders emitted, 64 of 64 cases platform-loadable.**
`r17`, `r18` and `r19` now carry platform graders and `platform_status: loadable`.

### One deliberate deviation from the prompt's literal spec

The prompt specified `max: 0` for the absence graders. **`min: 0` was added, because `max: 0` alone can never succeed.**
The platform's `tool_used` evaluator is:

```js
let i = count_of_matching_calls,
    s = e.min ?? 1,
    g = e.max ?? Number.POSITIVE_INFINITY,
    h = i >= s && i <= g;
```

With `max: 0` and no `min`, the expected range is `1..0`, and no count satisfies it — the three near-miss absence
graders would have failed in every run whatever the agent did, which is exactly the kind of silently-broken assertion
ADR-0039's invariants exist to prevent. `min: 0, max: 0` is the only correct representation. This was read from the
2.1.280 binary, not assumed, and
`unit.test_m13_eval_cases.PlatformLayer.test_the_command_mapping_is_the_one_the_pilot_observed` holds it.

### The skill-spelling limitation, kept intact

The pilot observed a **command** invocation. No skill-only invocation occurred, so it does not independently prove the
routing cases' skill spelling. The 22 `skill_invoked` / `skill_not_invoked` graders keep their Phase 1 mapping —
`tool: Skill` with the bare skill name as `input_match`, which matches as a substring whichever prefix the runtime
uses — and the init event's `businessiq:biq-<skill>` is consistent with it. **Not claimed as proved.** The namespaces
cannot collide: `businessiq:market-analysis` is not a substring of `businessiq:biq-market-analysis`, nor the reverse.

## 4. M13-DEF-10

The narrow resolver grant permits the ADR-0045 engine call, but the agent's *first* Bash call was an exploratory
`ls assets/demo-data/northwind_sales.csv 2>&1; ls <plugin path>/assets/demo-data/northwind_sales.csv 2>&1`, which does
not match it. In `dontAsk` mode the unmatched call was denied outright rather than prompted
(`decision_reason_type: "mode"`), and the agent stopped. **The authorised resolver command was never attempted in any
run, so the grant that was given was never exercised.** Reproduced in 3 of 3 runs with byte-identical behaviour.

`infrastructure`, `open`, `blocks_m13_completion: yes` by rule. **Not a product defect**, on three pieces of evidence
from the same run: the scaffold staged the input byte-identically (M13-DEF-07's fix working live); the resolver was
never invoked, so M13-DEF-08 is untouched by it; and the agent explicitly declined to compute anomaly figures by hand
with the engine unreachable, which is ADR-0002 holding under adverse conditions.

## 5. Least-privilege analysis

The objective is to permit the minimal read-only discovery step before the resolver call, without widening the shell
boundary.

| Option | Verdict |
|---|---|
| **No new grant** — the agent already holds `Read`, and the staged fixture is in the run directory where reads are permitted | **Candidate.** Adds no privilege at all. Depends on the agent preferring `Read` to `Bash`, which it did not do in any of the three runs |
| **`Bash(ls:*)` beside the resolver grant** | **Candidate.** Read-only listing: no mutation, no network, no interpreter, no connector, no authentication. The resolver grant stays untouched |
| `Bash(sh:*)` | **Rejected.** Authorises any `sh -c '<anything>'`; materially broader than what it would replace and makes the shell boundary meaningless |
| `Bash(python:*)` / `Bash(python *)` | **Rejected.** Retired by ADR-0045; would not have matched the denied `ls` either |
| A bare `Bash` grant | **Rejected.** Defeats §F.5 outright |

**Neither candidate is claimed as a verified design**, because verifying either needs a paid run: the trace shows the
agent's first instinct, not whether either candidate carries it through. The choice is an owner decision.

**A constraint worth recording.** The grant cannot move into the case file. `execution.allowed_tools` exists in the
platform schema, but the resolver grant contains an absolute plugin path and ADR-0039 §E.5 forbids an absolute path in
a case file; §F.5 keeps grants operator-side on the command line. So the authoritative list lives in
`docs/testing/eval-suite.md` *The grant set*, and `unit.test_m13_def10_eval_grant` asserts the repository against it.

## 6. Files created

| File | Purpose |
|---|---|
| `tests/unit/test_m13_def10_eval_grant.py` | The grant contract: 15 assertions |
| `docs/development/2026-09-22-m13-2-stage3-and-grant-defect.md` | This record |

## 7. Files modified

| File | Change |
|---|---|
| 21 `case.yaml` (a01–a18, r17–r19) | 24 platform graders added; `platform_mapping` → `mapped` with `platform_graders`; `pending_reason` removed; `r17`–`r19` → `platform_status: loadable` |
| `docs/testing/grader-migration-map.json` | Stage 3 totals; per-grader rows; `stage3_evidence` added; `pending_mapping_finding` removed |
| `tests/unit/test_m13_eval_cases.py` | `PENDING_CHECKS` emptied with its reason; `command_not_invoked` added to the negative-check list; the pending-boundary test replaced by three (nothing pending, the machinery still fails closed, and the mapping is the observed one); manifest totals |
| `docs/testing/defects.md` | **M13-DEF-10** added; M13-DEF-05 records stage 3 landing and the 1-of-64 loader residual; register state re-verified |
| `docs/testing/eval-suite.md` | *The trace boundary* replaces *The pending boundary*; **The grant set** added; §E.1 outcome (a); R-01 ready for owner closure; the three-run pilot row; stale grant text corrected |
| `docs/decisions/ADR-0044-…md` | Dated **Implementation note — Stage 3** appended. No prior text altered |
| `docs/decisions/README.md` | The 0044 row records Phase 1 **and** Stage 3 |
| `project_plan.md` | Header bullet; R-01 ready for closure; **M13-DEF-10** known-issue row; §E.1 and G-3 rows `COMPLETED`; stage 3 task row; M13.2 rows |

## 8. Files deleted

None.

## 9. Tests performed and results

| Command | Result |
|---|---|
| `unit.test_m13_eval_cases` | **Ran 102 — OK** (was 100; 2 net added) |
| `unit.test_m13_def10_eval_grant` | **Ran 15 — OK** (new) |
| `unit.test_m13_eval_results` | **Ran 28 — OK** |
| `unit.test_m13_coverage_matrix` | **Ran 33 — OK (skipped=1)** |
| Full regression | recorded in the task report |
| `claude plugin validate . --strict` | recorded in the task report |

Two of the new grant tests failed on first run and were **correct to fail**: they caught stale text in
`eval-suite.md` left by the previous task, which still said the grant "must be stated by the owner before a run" after
the owner had stated it and it had been used. The document was corrected; the tests were not loosened.

## 10. Issues discovered

1. **`max: 0` alone is an impossible assertion** on this platform. Found by reading the evaluator rather than trusting
   the spec. Three graders would have been permanently unsatisfiable.
2. **M13-DEF-10**, recorded above.
3. **The platform's loader has been exercised on 1 of 64 case files.** The other 63 satisfy the contract under the
   §E.5 validator, which is the repository's reimplementation of it, not the loader. Recorded against M13-DEF-05 rather
   than glossed, because it is the only thing standing between that defect and closure.
4. **Stale governance text** from the previous task, caught by a new test and corrected.

## 11. Decisions made

**No ADR was written, and none was required.** ADR-0044 planned stage 3; a dated implementation note records its
completion, following the Phase 1 precedent in the same file.

## 12. Architecture changes

None. `architecture.md` was not modified. No product, runtime, analytical, engine or resolver file was touched.

## 13. Project-plan updates

- **§E.1 outcome: `IN PROGRESS` → `COMPLETED`, outcome (a).**
- **R-01: `BLOCKED` → `BLOCKED`, ready for owner closure.** §E.1 (a) reserves the recording to the owner.
- **G-3: `IN PROGRESS` → `COMPLETED`.** Nothing about the platform's mechanics remains unobserved.
- **ADR-0044 stage 3: `COMPLETED`.**
- **M13-DEF-10 added, `open`, blocking.** M13-DEF-05 stays `open`, conditions met, closure recommended.
- M13.2 stays `IN PROGRESS`. **No case class changed**: `a01` is `automated_fail` and the other 63 `not_executed`.

## 14. Documentation updates

`docs/testing/eval-suite.md`, `docs/testing/defects.md`, `docs/testing/grader-migration-map.json`,
`docs/decisions/ADR-0044-…md` (appended note only), `docs/decisions/README.md`, `project_plan.md`, and this record.

## 15. Remaining work

1. **The owner decides M13-DEF-10's grant**, then one evaluation can test the behaviour the case exists for.
2. **The owner closes R-01** and, if satisfied by the 1-of-64 loader residual, **M13-DEF-05**.
3. The twelve `manual_observation` scenarios remain outstanding.
4. Extend eval input staging to the remaining 37 `requires_business_file` cases (M13-DEF-07's stated scope).
5. Confirm the skill-only invocation spelling on the first routing case that runs.

## 16. Git commit reference

**No commit, no push, no staging.** Nothing reset, cleaned, reverted or stashed; all pre-existing uncommitted M13.2
work intact. Branch `main`, base `21ee21b21213ad80273650f056ef2f318023742c`.
