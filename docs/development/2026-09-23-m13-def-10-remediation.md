# 2026-09-23 — M13-DEF-10: the evaluation grant set gains `Read`, and the resolver grant is untouched

**Milestone:** M13 — test hardening and evals (M13.2)
**Status on completion:** M13.2 `IN PROGRESS`; **M13-DEF-10 `fixed_infrastructure`** (deterministically corrected, not
live-verified); M13-DEF-05 `open` with its conditions met and closure recommended; M13-DEF-06, 07, 09
`fixed_infrastructure`; M13-DEF-08 `fixed_product`; ADR-0044 stage 3 complete; §E.1 outcome (a); R-01 ready for owner
closure
**Supersedes:** None. It follows `2026-09-22-m13-2-stage3-and-grant-defect.md`, and **corrects one factual claim made
there** (see §3).

## 1. Prompt / task performed

The owner's M13-DEF-10 remediation prompt: permit the minimum read-only discovery operation while preserving the narrow
runtime grant, decide it as an implementation decision rather than returning options, test it deterministically, and
update governance. No paid evaluation, no `claude plugin eval`, no `--max-cost-usd`, no web, no MCP, no authentication,
no publishing, and no change to production, runtime, resolver, engine, command, skill, agent, connector or MCP files.

**No evaluation was run.** `claude plugin eval` was not invoked and no evaluation credit was spent.

## 2. Root cause, restated precisely

The pilot's grant was `Bash(sh <plugin path>/lib/biq_run.sh:*)`. The agent fired the command correctly — `Skill` with
`{"skill": "businessiq:anomaly-detection", ...}` — then issued one read-only Bash call to locate the fixture, which did
not match the grant. With `--permission-mode dontAsk` the unmatched call was denied rather than prompted, and the agent
stopped. The resolver was never invoked in any of the three runs.

## 3. The investigation, and a correction to the previous record

The previous record offered two candidates and described the first as "the agent already holds `Read`". **That was wrong
on the facts**, and finding out why is what decided this task.

**Evidence, from the platform binary (2.1.280) and the kept runs — no evaluation involved:**

1. The child is launched with `--permission-mode dontAsk` and an explicit `--allowed-tools=` list, so anything outside
   that list is refused rather than prompted.
2. That list is built as
   `sf(cf(lf(r, cwd), [home, tmpDir, ...readRoots, ...add_dirs], readFiles), [cwd, tmpDir])`, where `r` is the operator
   grant list.
3. `cf` is the read-scope step. It scans the operator list for an entry whose **ruleContent is undefined** and whose
   tool is in the read set `{Read, Glob, Grep, LSP}`. **Only if one is found** does it add
   `Read(<dir>/**)`, `Glob(<dir>/**)` and `Grep(<dir>/**)` for home, tmpDir, the read roots and any `add_dirs`.
4. The pilot's only grant was `Bash(sh …:*)` — it carries a pattern, and `Bash` is not a read tool. So `cf` added
   **nothing**, and no read rule existed.
5. Therefore **`Read` was as denied as `Bash`**. The trace init event lists `Read` in the agent's tool *roster*, which is
   what misled the earlier analysis: being offered a tool is not being permitted to use it. The one-run pilot earlier on
   2026-09-22 had already said so out loud — it reported *both* `Bash` and `Read` blocked — because in that run the
   fixture was not staged either.
6. The kept run's `config/settings.json` carries only `sandbox` and `env`, with **no `permissions` block**, confirming
   the grant list is a command-line argument the case does not inherit.
7. `home` is `<run>/home` and the working directory is `<run>/home/cwd` (both observed), so **cwd is a subdirectory of
   home**. A read scope over home therefore covers the staged fixture.

## 4. The decision

**Add a bare `Read` to the operator grant set. Do not add `Bash(ls:*)`. Leave the resolver grant untouched.**

The authorised set is now exactly:

```
Read
Bash(sh <plugin path>/lib/biq_run.sh:*)
```

**Why `Read`, and why the spelling matters.** A *bare* `Read` is what triggers the read-scope step; `Read(<pattern>)`
would carry ruleContent, `cf` would skip it, and no scope would be computed — the same failure with extra ceremony. The
bare grant yields read, glob and grep over the run's own sandbox directories and nothing else: no shell, no write, no
network, no connector.

**Why `Bash(ls:*)` was rejected.** It keeps the discovery step inside the shell-execution tool, so its safety depends on
how the harness decomposes a compound command. `Read` makes that analysis unnecessary, because `Read` cannot execute
anything at all. `Read` is narrower **in kind**, not merely in degree: it takes the shell out of the discovery path
rather than narrowing what the shell may run. Under the prompt's priority order — existing read capability first, the
narrowest read-only Bash grant only if that is impossible, never generic shell — this is the first rung that is
technically available, since the "no new privilege" rung turned out not to exist.

**Why no prompt change.** Rewriting the case prompt to steer the agent away from a denied tool would tailor the test to
the harness and make the case less representative of the behaviour it exists to observe. A real user session holds
`Read`; denying it was an artefact of a grant set assembled for the engine call alone. Adding it makes the evaluation
**more** faithful, not less.

**Rejected outright, and recorded as such:** `Bash(sh:*)`, `Bash(python:*)`, `Bash(python *)`, a bare `Bash` or
wildcard-only pattern, and any write, edit, web-retrieval or connector-server grant.

## 5. Files created

| File | Purpose |
|---|---|
| `docs/development/2026-09-23-m13-def-10-remediation.md` | This record |

## 6. Files modified

| File | Change |
|---|---|
| `docs/testing/eval-suite.md` | *The grant set* rewritten: two authorised entries, why `Read` was not already available, why `Bash(ls:*)` was rejected, the exclusion table, and the deterministic-vs-live status. The stale "what blocks the next run" row and pre-flight item corrected |
| `docs/testing/defects.md` | M13-DEF-10 → `fixed_infrastructure`, with the correction to candidate 1, the remediation, the two-claim distinction, the residual, and the preserved pilot facts |
| `tests/unit/test_m13_def10_eval_grant.py` | Rewritten from a two-candidate menu to the decided configuration: 30 assertions |
| `project_plan.md` | Header bullet; M13-DEF-10 known-issue row; the grant task row `COMPLETED`; the M13.2 detail row |

**No case file was modified.** No production, runtime, resolver, engine, command, skill, agent, connector or MCP file was
modified.

## 7. Files deleted

None.

## 8. Tests

`tests/unit/test_m13_def10_eval_grant.py`, 30 assertions across six classes, covering every item Phase 5 listed:

| Requirement | Held by |
|---|---|
| The resolver grant remains present and unchanged | `test_the_resolver_grant_is_unchanged` |
| No generic Bash grant | `test_the_only_shell_grant_is_the_resolver_grant` |
| No Python grant | `test_each_excluded_grant_is_named_together_with_a_reason` (both spellings listed as excluded) |
| No web, connector or authentication grant | `test_no_web_connector_or_authentication_grant_appears` |
| No write or edit grant | `test_no_write_or_edit_grant_appears` |
| No forbidden absolute path in a case | `test_no_case_file_contains_a_bash_grant_or_an_absolute_path` |
| No case declares operator grants | `test_no_case_declares_allowed_tools` |
| The `Read` mechanism represented exactly | `test_the_read_grant_is_bare_because_a_pattern_would_not_compute_read_scopes`, `test_the_authorised_set_is_exactly_two_entries` |
| No expansion into arbitrary shell | `test_no_grant_can_expand_into_arbitrary_shell_execution` |
| `Bash(ls:*)` not introduced | `test_the_only_shell_grant_is_the_resolver_grant`, `test_the_rejected_shell_alternative_is_recorded_as_rejected` |
| a01 and all 64 cases still platform-valid | `ThePilotCaseRemainsValid` (4 tests) |
| ADR-0044 stage 3 untouched | `test_the_stage_3_mapping_is_untouched` (133 mapped) |
| The prior verdict not revised | `test_the_pilot_case_keeps_its_recorded_result` (`automated_fail`) |
| Deterministic ≠ live, in both documents | `TheDistinctionIsWrittenDown` (3 tests) |
| No fabricated success in any result fixture | `test_no_result_file_pretends_the_agent_succeeded` |

**No mock evaluation result was created**, and no fixture claims the agent succeeded.

Three of the new assertions failed on first run and were **correct to fail**: two caught forbidden tool-name literals I
had written into the procedure while explaining the harness's gated-tool list (removed, and the existing Safety guard
agreed), and one caught the defect record before it carried the deterministic-vs-live wording.

## 9. Results

| Command | Result |
|---|---|
| `unit.test_m13_def10_eval_grant` | **Ran 30 — OK** |
| `unit.test_m13_eval_cases` | **Ran 102 — OK** |
| `unit.test_m13_coverage_matrix` | **Ran 33 — OK (skipped=1)** |
| Full regression and strict validation | in the task report |

## 10. Issues discovered

1. **The previous record's candidate 1 was factually wrong** — `Read` was never permitted. Corrected in place in the
   defect record and in the procedure, with the evidence.
2. **A residual, recorded not hidden:** the `--allow-tools` help text lists the gated tools without mentioning `Read`.
   The harness's read-scope step consumes bare read tools from the operator list specifically, which is why the bare
   spelling is right, but that the CLI accepts the entry without complaint has not been observed.
3. **Stale procedure text** from the previous task, caught by the new tests and corrected.

## 11. Decisions made

No ADR. The grant set is evaluation procedure under ADR-0039 §F.5, not architecture; ADR-0045's invocation form and
ADR-0044's mapping are untouched.

## 12. Architecture changes

None. `architecture.md` was not modified.

## 13. Project-plan updates

M13-DEF-10 `open` → **`fixed_infrastructure`** (`blocks_m13_completion` `yes` → `no` by rule); the grant task row
`COMPLETED`; header bullet added. M13.2 stays `IN PROGRESS`. **No case class changed** and **no defect was closed that
requires an owner act** — M13-DEF-05 stays `open`, R-01 stays `BLOCKED` and ready for owner closure, M13 is not closed.

## 14. Documentation updates

`docs/testing/eval-suite.md`, `docs/testing/defects.md`, `project_plan.md`, and this record.

## 15. Remaining work

1. **One authorised evaluation** of `a01` at `--runs 3` with `--scaffold`, `--keep-temp` and the two-entry grant set,
   to verify live what has so far only been corrected deterministically.
2. The owner closes **R-01**, and **M13-DEF-05** if the 1-of-64 loader residual is acceptable.
3. The twelve `manual_observation` scenarios.
4. Staging for the remaining 37 `requires_business_file` cases.
5. Confirm the skill-only invocation spelling on the first routing case that runs.

## 16. Git commit reference

**No commit, no push, no staging.** Nothing reset, cleaned, reverted or stashed; all pre-existing uncommitted M13.2 work
intact. Branch `main`, base `21ee21b21213ad80273650f056ef2f318023742c`.
