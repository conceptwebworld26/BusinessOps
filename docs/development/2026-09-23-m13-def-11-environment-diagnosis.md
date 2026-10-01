# 2026-09-23 — M13-DEF-11: nested sandboxing, diagnosed without an evaluation

**Milestone:** M13 — test hardening and evals (M13.2)
**Status on completion:** M13.2 `IN PROGRESS`; **M13-DEF-11 raised, `open`, blocking**; M13-DEF-10
`fixed_infrastructure` **and now live-validated**; ADR-0044 stage 3 complete **and live-validated**; M13-DEF-05 `open`,
ready for owner closure; M13-DEF-06, 07, 09 `fixed_infrastructure`; M13-DEF-08 `fixed_product`; §E.1 outcome (a);
R-01 ready for owner closure
**Supersedes:** None. It records the third owner-authorised evaluation of 2026-09-23 and the diagnosis that followed.

## 1. Prompt / task performed

The owner's M13-DEF-11 environment diagnosis prompt: establish whether the correct environment for the next M13.2
evaluation is an outer Claude Code session with **no sandbox** while the evaluator keeps its own, and remediate if
possible. Explicitly non-paid: no `claude plugin eval`, no case, no credits, no MCP, no web retrieval, no
authentication, no production or eval-semantics change, no weakening of sandbox security, no bypass flags, no
installation, no commit, push or staging.

**No evaluation was run.** `claude plugin eval` was not invoked and no evaluation credit was spent.

## 2. What the third evaluation had established

The 2026-09-23 three-run evaluation (Claude Code 2.1.280, `--runs 3 --threshold 1.0 --scaffold --keep-temp`, grants
`Read` and `Bash(sh <plugin path>/lib/biq_run.sh:*)`, **$0.6249854** of a $5 ceiling) reached further than any run before
it. Three admissible runs, 6/6/5 turns, no execution error:

- **Zero `permission_denied` events in all three runs.** The grant set worked.
- `Glob` returned `assets/demo-data/northwind_sales.csv` — the staged fixture, at the relative path the prompt names.
- The agent issued the **exact authorised resolver command**, `sh "<plugin>/lib/biq_run.sh" -c "…"`.
- **`g-command-ran` passed 3 of 3** ("Skill called 1x"), the first deterministic trace-mapped grader ever to score.
- The agent's tool roster gained `Glob` and `Grep`, which the 2026-09-22 roster lacked — the observable signature of the
  bare `Read` grant causing the harness to compute read scopes.

So M13-DEF-07, M13-DEF-10 and ADR-0044 stage 3 are all validated live. The engine was still not reached, because every
Bash attempt returned:

```
Sandbox is required but failed to initialize: EPERM: operation not permitted,
listen '<run>/tmp/srt-mux-<pid>-<n>.sock'. Restart to retry.
```

## 3. The diagnosis, established experimentally with no evaluation

**Hypothesis:** the evaluator's per-command sandbox cannot initialise inside an outer session that is itself sandboxed.

**Test:** create an `AF_UNIX` socket and `bind()` + `listen()` it — the operation the error names — in this session, and
again with the outer sandbox off. Nothing else changed.

| Property | Outer sandbox on | Outer sandbox off |
|---|---|---|
| user namespace | `user:[4026532354]` (non-initial) | `user:[4026531837]` (initial) |
| `uid_map` | `1000 1000 1` | `0 0 4294967295` |
| `Seccomp` | mode **2**, 1 filter | mode **0**, 0 filters |
| `AF_UNIX` `bind`+`listen` | **EPERM (errno 1)** | **OK** |

The error the evaluator reported is reproduced exactly, outside any evaluation, and disappears when the outer sandbox is
off. **Diagnosis confirmed.**

**The evaluator's refusal is correct behaviour, not a fault.** Its generated child settings carry
`allowUnsandboxedCommands: false` and `failIfUnavailable: true`, so when confinement cannot be built the granted command
is refused rather than run unconfined. That is the safety property working.

## 4. Two sandboxes, and why only one changes

| Layer | During the failing run | Role | Action |
|---|---|---|---|
| **Outer Claude Code session** | sandboxed, `Sandbox BashTool, with auto-allow` | confines the **operator's** shell | **set to `No Sandbox`** |
| **Evaluator (child) sandbox** | `enabled: true`, `failIfUnavailable: true`, `allowUnsandboxedCommands: false` | the security boundary for the **plugin under test** | **unchanged** |

**Selecting `No Sandbox` for the outer session cannot disable the evaluator's sandbox**, and the evidence is direct: the
evaluator **generates** its child settings rather than inheriting them. The outer session ran with auto-allow **on**,
while all three child configs recorded `autoAllowBashIfSandboxed: false`; the child config's only keys are `sandbox` and
`env`, with no `permissions` block, and its `env` is just `DISABLE_AUTOUPDATER: 1`. Grants reach the child through
`--allowed-tools` on the command line, not through inherited settings.

`/sandbox` offers exactly three modes — `No Sandbox`, `Sandbox BashTool, with auto-allow`, and
`Sandbox BashTool, with regular permissions` — so the required mode exists.

## 5. What this task could not do

**The outer session's sandbox was not changed.** `/sandbox` is an interactive command the operator runs; it is not a
tool available to this session, and the settings files that would express it
(`.claude/settings.json`, `~/.claude/settings.json`) are explicitly non-writable here. The prompt also forbids
environment-variable overrides, which is the only other route. **One operator action remains**, and it is the whole of
the remediation.

## 6. Files created

| File | Purpose |
|---|---|
| `docs/development/2026-09-23-m13-def-11-environment-diagnosis.md` | This record |

## 7. Files modified

| File | Change |
|---|---|
| `docs/testing/defects.md` | **M13-DEF-11** added (`infrastructure`, `open`, blocking) with the experiment, the two-sandbox distinction, the remediation, and an ADR-0040 note raised for the owner; register row and state header |
| `docs/testing/eval-suite.md` | Recorded state: the third evaluation, the 2026-09-23 environment condition, the corrected "what blocks the next run" row, and a new pre-flight item 1a requiring the outer session to be `No Sandbox` |
| `project_plan.md` | Header bullet; M13-DEF-11 known-issue row; M13.2 detail row |

**No production, runtime, resolver, engine, command, skill, agent, connector, MCP, test-logic or eval-case file was
modified.** No eval-case semantics changed.

## 8. A governance question raised, not decided

M13-DEF-11 is an **environment** condition, not a fault in M13's own tests, fixtures, graders, scaffolds or validator —
which is what ADR-0039 §G.1's `infrastructure` class describes. The repository has precedent for the other treatment: on
2026-09-22 the earlier "no sandbox backend" condition was recorded in `eval-suite.md` as an environment-unavailability
question for the owner under **ADR-0040 §2**, explicitly "**not** a defect id.

It is recorded here as `infrastructure` because this prompt directed a defect record, and that classification makes it
`blocks_m13_completion: yes` **by rule**. If the owner prefers the ADR-0040 treatment — a recorded environment gap that
blocks nothing by rule — this record should be withdrawn in favour of it. **An owner decision, not taken here.**

## 9. Tests

No source change was made, so the full suite was not run. The smallest relevant deterministic modules — the ones that
read the documents this task edited — were run:

| Module | Result |
|---|---|
| `unit.test_m13_coverage_matrix` (defect register contract) | **Ran 33 — OK (skipped=1)** |
| `unit.test_m13_eval_cases` (procedure and case contract) | **Ran 102 — OK** |
| `unit.test_m13_def10_eval_grant` (grant set and defect records) | **Ran 30 — OK** |

**No test was manufactured for the environment itself.** The environment finding is recorded as evidence, not asserted
as a passing test, because the remediation has not been applied and cannot be verified without a run.

## 10. Issues discovered

1. **M13-DEF-11**, above.
2. **The previous record's "not live-verified" caveat on M13-DEF-10 can now be lifted** — the third evaluation supplied
   exactly the missing observation. Recorded in `eval-suite.md`; the defect's own status was already
   `fixed_infrastructure`.
3. **ADR-0044 stage 3 is live-validated** by `g-command-ran` passing 3 of 3.

## 11. Remaining work

1. **The operator sets the outer session to `No Sandbox`** via `/sandbox`.
2. One authorised evaluation of `a01` at `--runs 3` with `--scaffold`, `--keep-temp` and the two-entry grant set.
3. The owner closes **R-01**, and **M13-DEF-05** if the 1-of-64 loader residual is acceptable; and decides the
   ADR-0040 question on M13-DEF-11.
4. The twelve `manual_observation` scenarios; staging for the remaining 37 `requires_business_file` cases.

## 12. Git commit reference

**No commit, no push, no staging.** Nothing reset, reverted or stashed; all pre-existing uncommitted M13.2 work intact.
Branch `main`, base `21ee21b21213ad80273650f056ef2f318023742c`.
