# 2026-09-26 — M13-DEF-24 PreToolUse hook runtime feasibility experiment

**Milestone:** 13 — post-completion defect investigation (M13-DEF-24)
**Status on completion:** REVIEW (experiment only; M13-DEF-24 remains OPEN)
**Supersedes:** None. Extends `2026-09-26-m13-def-24-investigation.md`, which examined hooks statically only.

## 1. Prompt / task performed
Measure, with real fresh Claude Code sessions, whether a BusinessIQ-scoped `PreToolUse` hook can intercept
and deny a later `Bash`/`Write` call before it executes. Experiment only: no production fix, no commit, no
plugin eval, no MCP/web.

## 2. Objective
Demonstrate or refute the chain: model requests write → CLI invokes plugin-scoped PreToolUse hook → hook
returns deny → CLI prevents execution → write never occurs.

## 3. Changes made
All experiment material lived outside the repository and was deleted afterwards:

- `/tmp/biq-hook-experiment/`: a sentinel file (`ORIGINAL_CONTENT`), the hook script and the runners.
- Plugin **P** (`/tmp/biq-hook-plugin-P`): only `hooks/hooks.json`, with matcher `Bash|Write|Edit|MultiEdit|NotebookEdit`.
- Plugin **S** (`/tmp/biq-hook-plugin-S`): only a skill whose frontmatter declares the same `PreToolUse` hook.

Each plugin was loaded with `--plugin-dir` for a single session. No global/user settings were touched, and
nothing was installed.

The hook script did the following for each call:

- logged the payload and the sentinel's content *at hook time*;
- for a write aimed at the sentinel, returned `permissionDecision` `deny` or `ask`, with the reason
  `BIQ_HOOK_EXPERIMENT_DENY`;
- otherwise returned no output.

Sessions ran `claude -p --input-format stream-json --output-format stream-json --model sonnet --permission-prompts none --strict-mcp-config`.
A feeder sent each user turn only after the previous turn's `result` event. That gave three to four real turns
in **one process and one session_id**:

1. Turn A: `echo MODIFIED_CONTENT > sentinel`.
2. Turn B: a `Read`, then `echo APPENDED_CONTENT >> sentinel`.
3. Turn C: a `Read`, then the `Write` tool.

## 4. Files created
This record only.
## 5. Files modified
None.
## 6. Files deleted
None in the repository. The temporary experiment directory and both temporary plugins were removed.

## 7. Features implemented
None. No production hook exists; `hooks/` is absent from the repository.

## 8. Tests performed
Claude Code **2.1.283**, the version installed at run time (the investigation recorded 2.1.281).
Linux 6.18.33.2 WSL2, Python 3.14.4.

| Run | Hook scope | Mode | Decision | A Bash `>` | B Bash `>>` (after Read) | C Write (after Read) | Sentinel after |
|---|---|---|---|---|---|---|---|
| control | none | bypassPermissions | — | executed | executed | executed | modified |
| P-deny-bypass | plugin hooks.json | bypassPermissions | deny | blocked | blocked | blocked | ORIGINAL |
| P-deny-acceptEdits | plugin hooks.json | acceptEdits | deny | blocked | blocked | blocked | ORIGINAL |
| P-deny-manual | plugin hooks.json | manual (default) | deny | blocked | blocked | blocked | ORIGINAL |
| P-deny-dontAsk | plugin hooks.json | dontAsk | deny | blocked | blocked | blocked | ORIGINAL |
| P-deny-auto | plugin hooks.json | auto | deny | blocked | blocked | blocked | ORIGINAL |
| P-ask-bypass | plugin hooks.json | bypassPermissions | ask | prompt → auto-denied | same | same | ORIGINAL |
| P-ask-acceptEdits | plugin hooks.json | acceptEdits | ask | prompt → auto-denied | same | same | ORIGINAL |
| S-deny-bypass | skill frontmatter, skill invoked in turn 1 | bypassPermissions | deny | blocked | blocked | blocked | ORIGINAL |
| S-noactivate | skill frontmatter, skill never invoked | bypassPermissions | deny | **executed** | **executed** | **executed** | modified |
| P-deny-alt | plugin hooks.json | bypassPermissions | deny | model tried Bash → Write → Edit; then an a20-shape `cat > f <<'EOF'` heredoc | all four blocked | — | ORIGINAL |

## 9. Test results
- In every blocked case, the tool_result the model received was `is_error: true`, with the text
  `PreToolUse:<Tool> hook error: BIQ_HOOK_EXPERIMENT_DENY (...)`. The result event listed the call in
  `permission_denials`.
- The hook log recorded `sentinel_at_hook_time = ORIGINAL_CONTENT` for every intercepted call. The next
  `Read` in the same session also returned `ORIGINAL_CONTENT`. So the hook ran before the tool, and the
  tool body never ran.
- **Attribution.** The no-plugin control, run in the same mode (bypassPermissions) with the same prompts,
  executed all three writes. No outer sandbox or permission rule blocked them. In the deny runs the only
  difference was the hook, and the blocking message carried the hook's marker. The model did not decline
  voluntarily: it issued each tool call.
- **Ask.** Returning `ask` forced a permission prompt even under `bypassPermissions`. The hook's reason
  (with the marker) appeared in the permission-denied text. The prompt was answered by nobody
  (`--permission-prompts none`), so the call was auto-denied by the permission system, not by the hook.
  The CLI then told the model that later approval-requiring actions would be denied for the rest of the
  session.
- **Lifetime.** Plugin `hooks.json` hooks were active from session start through every later turn.
  Skill-frontmatter hooks became active only after the skill was invoked, and then stayed active for the
  three later turns tested. They were **not** active in a session where the skill was loaded but never
  invoked.

## 10. Issues discovered
- The experiment's crude write classifier gave a false positive: it denied a read-only
  `cat sentinel 2>&1` because it saw `>`. This is a property of the classifier, not of the runtime, but
  any real guard has a command-classification problem to solve.
- **Not measured:**
  - `ask` answered by an interactive human, both approve and reject;
  - `plan` mode;
  - behaviour inside `claude plugin eval`, which was prohibited;
  - hooks when the plugin is installed from a marketplace rather than loaded with `--plugin-dir`;
  - hooks inside subagents;
  - models other than sonnet;
  - Bash writes that avoid a textual reference to the target path (for example, a `cd` and then a
    relative path).

## 11. Decisions made
None. Adopting hooks would require an ADR admitting frontmatter or plugin `hooks`, and would revisit
ADR-0035's rejection of a hook-based Bash filter. The owner has not made that decision.

## 12. Architecture changes
None.
## 13. Project-plan updates
None. M13-DEF-24 remains OPEN.
## 14. Documentation updates
This record only.
## 15. Remaining work
Owner decision on an ADR amendment. The unmeasured conditions in §10.
## 16. Git commit reference
N/A: no commit.
