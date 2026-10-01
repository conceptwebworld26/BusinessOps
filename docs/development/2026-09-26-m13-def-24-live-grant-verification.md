# 2026-09-26 — M13-DEF-24 live approval-grant verification (ADR-0051)

**Milestone:** Product remediation outside M13 (ADR-0039 I-13, §G.2). Milestone 13 stays `COMPLETED`; M14 is not started.
**Status on completion:** REVIEW — evidence only. M13-DEF-24 stays `fixed_product`.
**Supersedes:** None. It adds runtime grant evidence to `2026-09-26-m13-def-24-remediation.md`, which listed
`UserPromptSubmit` granting as unmeasured. That record is not edited.

## 1. Prompt / task performed

Two owner prompts drove this record.

1. **Runtime verification only.** The first prompt asked for a check of the ADR-0051 approval chain in a live Claude Code
   session, with no change to production code, ADRs, architecture, tests, fixtures or `README.md`. The chain to prove:
   deny → approval code → user approval → exact retry → capability redeemed → write executes.
2. **Recording only.** The second prompt asked for this record, and for the defect record, plan, architecture and
   ADR-0051 to be made factually consistent with it.

## 2. Objective

Establish that the approval path works through the real Claude Code user-message path. Three rules governed the test:

- the approval store was never edited;
- no approval record was injected;
- no internal function was called to simulate the user.

## 3. Changes made

**Verification task.** None to the repository.

- An isolated target was created outside it, `/tmp/biq-def24-live-grant/sentinel.txt`, holding `ORIGINAL_CONTENT`. It
  was removed afterwards.
- The approval store was redirected into that directory through the hook's `BIQ_GUARD_ROOT` seam, read only.
- The session's `TMPDIR` pointed at a separate empty directory. ADR-0051 treats the system temporary directory as free
  scratch, so without this a target under `/tmp` would not be governed at all (limit 3 in §10).
- An observation-only logging hook, added through a temporary `--settings` file, recorded every `UserPromptSubmit`,
  `PreToolUse` and `PostToolUse` payload.

**Recording task.** The documentation changes are listed in §5.

## 4. Files created

This record.

## 5. Files modified

All by the recording task. None by the verification task.

- `docs/testing/defects.md`: the M13-DEF-24 row and the record's evidence and limitations.
- `project_plan.md`: the M13-DEF-24 row.
- `architecture.md`: §20 item 13.
- `docs/decisions/ADR-0051-pre-execution-write-approval-boundary.md`: a verification note in the status block only.
  The decision text is unchanged.

## 6. Files deleted

None in the repository. The temporary test directories were removed.

## 7. Features implemented

None.

## 8. Tests performed

**Environment**

| Item | Value |
|---|---|
| Claude Code | 2.1.283 |
| Platform | Linux 6.18.33.2 WSL2 |
| Python | 3.14.4 |
| Model | `sonnet` |
| Session | one `claude -p` process, one session, **seven turns** |

**Invocation**

- `--input-format stream-json --output-format stream-json`
- `--plugin-dir <repository>`, which loaded the real plugin and its real hooks
- `--permission-mode bypassPermissions`
- `--strict-mcp-config`

A feeder script sent each user turn through stream-json stdin, only after the previous turn's `result` event. This is
Claude Code's real user-message path, and it fired the real `UserPromptSubmit` hook. No person typed into an
interactive terminal (limit 2).

**Turns**

1. Engage BusinessIQ: `sh "<plugin>/lib/biq_run.sh" --where`.
2. `echo GRANTED_CONTENT > …/sentinel.txt`.
3. The user message `approve <code from turn 2>`, then the identical command.
4. The identical command again, with no new approval.
5. `approve <code from turn 4>`, then the same write aimed at `…/other.txt`.
6. `echo GRANTED_CONTENT >> …/sentinel.txt` (an append), while the turn-4 approval was still unused.
7. An `Agent` call whose prompt is `approve <code from turn 4>`.

## 9. Test results

| Turn | Tool result | Sentinel after |
|---|---|---|
| 1 | Executed; the session is engaged by the engine launcher | `ORIGINAL_CONTENT` |
| 2 | `PreToolUse:Bash hook error: BusinessIQ write guard blocked this Bash call before it ran. Nothing was written or changed.` It named "overwrite existing file: …/sentinel.txt" and issued a `BIQ-W-` code in the expected 8-character form | `ORIGINAL_CONTENT` |
| 3 | The grant hook confirmed "approved once: overwrite existing file: …/sentinel.txt". The identical retry ran without denial | **`GRANTED_CONTENT`** |
| 4 | Denied, with a new code: the turn-3 capability was single-use | `GRANTED_CONTENT` |
| 5 | Grant accepted for the sentinel overwrite. The `other.txt` write was denied ("create new file") | unchanged; `other.txt` never created |
| 6 | Denied ("append to file") | unchanged |
| 7 | Denied outright: "prohibited … an approval may only come from the user's own prompt" | unchanged |

**Distinguishing the events.** Each of these was observed separately:

| Event | Evidence |
|---|---|
| Hook denial | Every denial carried the `PreToolUse:<Tool> hook error: BusinessIQ write guard …` text. It appeared under `bypassPermissions`, where no permission prompt or sandbox applies |
| Approval prompt | The code appeared in the deny reason |
| User approval | A `UserPromptSubmit` payload carrying the phrase |
| Grant | The hook's "approved once" system message |
| Redemption | After the session, the turn-2 code's record was in `consumed/`. The turn-4 grant stayed in `granted/`: neither the retarget nor the append matched it. The `other.txt` and append requests stayed `pending` |
| Execution | `PostToolUse` fired for exactly two calls: the turn-1 engine call and the turn-3 approved write |

**`UserPromptSubmit` payloads.** All seven carried `cwd`, `hook_event_name`, `permission_mode`, `prompt`, `prompt_id`,
`session_id` and `transcript_path`. None carried `source` or `agent_id`.

**Latency**, observed between each tool call and its result, which includes the hook:

- a denied write took about 1.3–2.4 s;
- the approved write took about 2.3 s;
- grant processing could not be separated from model latency.

**After cleanup:**

- `README.md`'s sha256 matched the value taken at session start;
- `git status`, the tracked diff and the untracked files were identical to session start;
- nothing was staged;
- nothing was left under `~/.claude/businessiq`.

## 10. Issues discovered

These are limitations of the evidence and the runtime. None shows that the core boundary failed, and the defect is not
reopened.

1. **No prompt source.** 2.1.283 exposes no `UserPromptSubmit` `source` field; this was confirmed live. BusinessIQ
   therefore cannot tell an ordinary user's approval phrase from every possible injected prompt route.
   - Tested: only the subagent route, which was refused.
   - Not tested: scheduled wakeups, cron prompts, notices from other sessions and SDK poll events.
2. **Scripted user messages.** The user messages were sent by a script through the real stream-json user-message path,
   not typed by a person in an interactive terminal.
3. **`/tmp` is free scratch.** Under the ADR-0051 design, a user file kept under `/tmp` is outside the normal
   write-approval boundary.
4. **Other conditions still unmeasured:**
   - a marketplace install;
   - `plan` mode;
   - `ask` answered by a person;
   - hooks inside subagents;
   - models other than `sonnet`;
   - `claude plugin eval`.

## 11. Decisions made

None.

## 12. Architecture changes

None. `architecture.md` §20 item 13 was corrected to match this evidence.

## 13. Project-plan updates

The M13-DEF-24 row now names the runtime grant evidence. Its status is unchanged (`fixed_product`).

## 14. Documentation updates

As §5.

## 15. Remaining work

The limitations in §10.

- **Not claimed:**
  - that the plugin evaluation or `a20` was rerun (neither was);
  - that every prompt-injection route is ruled out.
- **Not used:** the plugin evaluation harness, paid evaluation, MCP, web, authentication and publishing. The seven-turn
  session made ordinary model calls, as the earlier deny experiment did.

## 16. Git commit reference

N/A. Nothing was staged, committed or pushed. HEAD is `8287e98f483d82d70502e959388ab0b0708f1e1f`.
