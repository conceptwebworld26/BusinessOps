# 2026-09-26 — M13-DEF-24 remediation: a pre-execution write-approval boundary (ADR-0051)

**Milestone:** Product remediation outside M13 (ADR-0039 I-13, §G.2). Milestone 13 stays `COMPLETED`; no later
milestone is started.
**Status on completion:** REVIEW — M13-DEF-24 is `fixed_product` (ADR-0043), verified deterministically and by the
recorded runtime experiment. Not committed, and not live-evaluated.
**Supersedes:** None. It completes the remediation that `2026-09-26-m13-def-24-investigation.md` left blocked, using the
evidence in `2026-09-26-m13-def-24-hook-runtime-experiment.md`. Neither record is edited.

## 1. Prompt / task performed

The owner asked for M13-DEF-24 to be remediated properly. The fix was to rest on the runtime experiment's finding that
a plugin-wide `PreToolUse` hook can block `Bash`, `Write` and `Edit` before they execute. It required:

- **Governance:** a new ADR that supersedes or amends the earlier hook decisions without editing them.
- **Two enforcement layers:**
  - a plugin-wide hook covering `Bash`, `Write`, `Edit`, `MultiEdit` and `NotebookEdit`;
  - an engine-side boundary for writes BusinessIQ performs itself.
- **Classification:** a semantic write classifier, not a string blacklist, that fails closed.
- **Capabilities:** approvals bound to the exact operation, with no caller-controlled flag and attention to TOCTOU.
- **Tests:** the 27 listed security tests, with hook tests kept separate from capability tests.
- **Validation:** the listed checks.

Excluded: commit, push, the plugin eval harness, paid evaluation, MCP, web, authentication, publishing, and any change
to the M13.2 evaluation fixtures.

## 2. Objective

No consequential filesystem write executes in a BusinessIQ session unless the user approved that exact operation. The
check happens before execution, is decided on the exact input about to run, fails closed, and does not govern sessions
that never use BusinessIQ.

## 3. Changes made

1. **Read the governing material.**
   - The plan, the investigation and the experiment records.
   - ADR-0001, ADR-0035, ADR-0043 and ADR-0050, and `architecture.md` §§2, 8, 12, 13, 16, 19 and 20.
   - The engine's existing write sites:
     - `runtime/tiers.py`, which writes the runtime directory and runs the venv/pip subprocesses;
     - `verification.py` and `connectors/catalogue.py`, which write `./.businessiq/`;
     - `ingest/readers.py`, which runs the managed reader subprocess.
   - All 34 shipped engine blocks, which come in two shapes: `-c "…"` and `-c "$(cat <<'PY' … PY)"`.
2. **Read the installed CLI's hook contract (2.1.283).** This was done by extracting strings from the installed binary;
   no model session was run.
   - **`PreToolUse` input:** `session_id`, `transcript_path`, `cwd`, `permission_mode`, `agent_id` and `agent_type`,
     `tool_name`, `tool_input`, `tool_use_id`, and `scratchpad_dir` when enabled.
   - **`PreToolUse` output:** `hookSpecificOutput.permissionDecision` with `permissionDecisionReason`, plus
     `systemMessage`.
   - **`UserPromptSubmit`:** has `prompt`. Its schema declares `source`, but the builder spreads `...!1` in its place,
     so `source` is never populated in this build.
   - **`UserPromptExpansion`:** has `command_name`.
   - **Plugin attribution:** no field attributes a tool call to a plugin.
   - **Session id in `Bash`:** `CLAUDE_CODE_SESSION_ID` is set in the tool's environment. It was observed equal to the
     session id.
   - **Tool names:** `MultiEdit`, `NotebookEdit` and `PowerShell` are real tool names in this build.
   - **Precedent:** an official plugin uses a `UserPromptExpansion` matcher of the form `^plugin:command$`.
3. **Chose the scope from those facts.**
   - Plugin-wide, because only plugin-wide hooks were measured active from session start.
   - Narrowed by *engagement*: a BusinessIQ `Skill` call, slash command, subagent or engine-launcher call. The runtime
     reports all of these, but it does not report plugin attribution.
4. **Implemented `lib/python/biq/writeguard/`.** Stdlib only.
   - `shell.py`: a conservative POSIX lexer that raises on anything it does not model.
   - `pyscan.py`: the confinement check and literal write-target detection for Python code.
   - `policy.py`: zones and the free, approval and prohibited decision.
   - `classify.py`: the allowlist tool-call classifier.
   - `capability.py`: the request, grant and redeem store.
   - `hook.py`: the three event handlers, fail-closed.
   - `engine.py`: the audit-hook execution guard.
   - `export.py`: the one user-file write path.
5. **Wired it in.**
   - `lib/python/biq_run.py` gained `--guard <event>` and installs the engine guard before `-c` code.
   - `hooks/hooks.json` and `hooks/biq_guard.sh` were added. The wrapper turns a guard that cannot start into exit 2.
   - `lib/python/biq/errors.py` gained `WriteBlockedError` and `WriteApprovalRequired`.
   - `lib/schemas/write_approval.schema.json` was added.
6. **Found and closed a bypass in my own first design.** The export API first took `store=` and `session_id=`
   parameters. That let confined engine code build a fake store under `./.businessiq/` (a zone the engine may write),
   grant itself there, and pass that store in. The fix:
   - both parameters became private (`_write`), which confined code cannot name;
   - confined engine code may now import only `biq.writeguard.export` from the guard package;
   - the engine guard refuses any write to `granted/`.
7. **Found and fixed two implementation faults through the tests.**
   - CPython reports an absent `dir_fd` as `-1`, not `None`, so every `mkdir` was at first refused.
   - `sort` was missing from the read-only list, so its `-o` handling was unreachable.
8. **Amended one existing test file, narrowly.** In `negative.test_m13_approval_boundaries`, two textual scans ("no
   engine module mentions `git push`" and "no string constant `git`") necessarily match the classifier, which must
   recognise git commands in order to deny them.
   - `biq/writeguard/` is excluded from those two scans.
   - A stricter replacement test pins that the write guard imports nothing that launches processes or opens sockets,
     and makes no process-launching `os` call.
   - The other three tests in that file are unchanged.
9. **Kept the approval matrix closed.** `unit.test_m13_coverage_matrix` counts every table row in `architecture.md` §8
   as an approval class. The enforcement description added to §8 is therefore a list, not a table, and ADR-0039's
   closed set S5 stays at 13.
10. **Wrote the governance:** ADR-0051, the decisions index, `architecture.md`, `CLAUDE.md` §3, the defect register,
    `project_plan.md` and this record.

## 4. Files created

- `hooks/hooks.json`
- `hooks/biq_guard.sh`
- `lib/python/biq/writeguard/__init__.py`
- `lib/python/biq/writeguard/shell.py`
- `lib/python/biq/writeguard/pyscan.py`
- `lib/python/biq/writeguard/policy.py`
- `lib/python/biq/writeguard/classify.py`
- `lib/python/biq/writeguard/capability.py`
- `lib/python/biq/writeguard/hook.py`
- `lib/python/biq/writeguard/engine.py`
- `lib/python/biq/writeguard/export.py`
- `lib/schemas/write_approval.schema.json`
- `tests/unit/test_m13_def24_write_classifier.py`
- `tests/unit/test_m13_def24_hook_decision.py`
- `tests/integration/test_m13_def24_write_boundary.py`
- `docs/decisions/ADR-0051-pre-execution-write-approval-boundary.md`
- `docs/development/2026-09-26-m13-def-24-remediation.md` (this record)

## 5. Files modified

- `lib/python/biq_run.py`: the `--guard` entry, and `install()` before `-c` code.
- `lib/python/biq/errors.py`: two error types.
- `tests/negative/test_m13_approval_boundaries.py`: the scoped scans and one replacement test (§3 item 8).
- `CLAUDE.md` §3: `hooks/` in the layout, the placement rule for hooks, and the guard store as runtime state.
- `architecture.md`: §2 hooks row, §8 enforcement subsection, §12, §13, the §16 row, the §19 table and §20 item 13.
- `docs/decisions/README.md`: the index row and the amendments line.
- `docs/testing/defects.md`: register state, the M13-DEF-24 row, record `status`, and the status basis.
- `project_plan.md`: the M13-DEF-24 row, and the `hooks/` row removed from *Deferred*.

`architecture.md`, `docs/decisions/README.md`, `docs/testing/defects.md` and `project_plan.md` already carried
uncommitted M13-DEF-13 edits. Those edits were left as they were.

## 6. Files deleted

None in the repository. Outside it, a smoke run created empty `~/.claude/businessiq/guard/sessions/` directories, which
did not exist before (15:23). They were removed with `rmdir`, and `Store.engaged()` no longer creates directories on a
read. A stray empty directory, created by `mktemp` beside the repository, was removed the same way.

## 7. Features implemented

- **Pre-execution write guard.** `hooks/`, `writeguard/hook.py`, `classify.py`, `shell.py`, `pyscan.py`, `policy.py`.
  Active in any Claude Code session with the plugin installed. It governs a session once BusinessIQ is engaged.
- **Write approvals.** `writeguard/capability.py`.
  - The user reads the denial, which names the operation and target and states that nothing was written.
  - The user replies `approve BIQ-W-XXXXXXXX`.
  - The identical call then proceeds once.
- **Engine execution guard.** `writeguard/engine.py`, installed by `biq_run.py` in every engine process.
- **Export API.** `biq.writeguard.export.write_text(path, text)`. Engine code can reach it. No command uses it yet.

## 8. Tests performed

```
python3 tests/run_tests.py unit.test_m13_def24_write_classifier
python3 tests/run_tests.py unit.test_m13_def24_hook_decision
python3 tests/run_tests.py integration.test_m13_def24_write_boundary
python3 tests/run_tests.py negative.test_m13_approval_boundaries
python3 tests/run_tests.py unit.test_m13_def13_research_boundary
python3 tests/run_tests.py            # full regression
claude plugin validate . --strict
git diff --check
```

Also:

- **Mutations:** seven single-point mutations, each restored and verified by hash.
- **Validator check:** a scratch copy of the plugin, validated first with the real `hooks.json` and then with a
  deliberately broken one.
- **Latency:** measured with `/usr/bin/time`.
- **Also run:** the secret scan, the fixture byte-identity check, and the M11 and approval test groups. Their results
  are in the task report.

## 9. Test results

**Focused suites.** All pass.

| Suite | Tests | Result |
|---|---|---|
| `unit.test_m13_def24_write_classifier` | 42 | 0 failures |
| `unit.test_m13_def24_hook_decision` | 34 | 0 failures |
| `integration.test_m13_def24_write_boundary` | 15 | 0 failures |
| `negative.test_m13_approval_boundaries` | 5 (1 new) | 0 failures |

That makes 92 new tests.

**Case map.** The prompt's cases map to the tests as follows:

- Cases 1-17, 22, 23 and 27 are covered at the classifier.
- Cases 18-24 and 27 are covered at the hook and capability level.
- Cases 23 and 24 are also covered through `hooks/biq_guard.sh` → `biq_run.sh` → `biq_run.py --guard`. There the a20
  heredoc receives `deny`, and `README.md`'s sha256 is unchanged.
- Case 25 is the full regression.
- Case 26 is covered twice:
  - all 34 shipped engine blocks classify as engine calls, and the 33 that parse are free;
  - `sales-analysis` runs through the launcher with the guard installed.

**Mutations.** Each file was restored byte-identically afterwards.

| Mutation | Suite | Result |
|---|---|---|
| M1 redirects ignored | classifier | 13 failures |
| M1 redirects ignored | hook | 14 failures |
| M2 hook never governs | hook | 18 failures |
| M3 redeem ignores binding | hook | 7 failures |
| M4 launcher skips `install()` | integration | 11 failures, 1 error |
| M5 wrapper fails open | integration | 1 failure |
| M6 engine code unscreened | classifier | 5 failures |
| M7 export skips capability | integration | 1 failure, 1 error |

**Validation.**

- `claude plugin validate . --strict`: passed.
- The scratch-copy check confirmed that the validator checks `hooks/hooks.json`. The real file passes; a hook of
  unknown `type` fails.

**Full regression.** The final run's counts are in the task report. An intermediate run found 1 failure (the §8 table
rows, fixed in §3 item 9).

**Latency.** Measured on WSL2, with the plugin on `/mnt/d` and no other load: 1.6–2.6 s per hook call. Of that,
`biq_run.py --where` accounts for 0.9–1.2 s.

## 10. Issues discovered

- **README.md is already reduced to three dots.** The working-tree `README.md` holds 4 bytes (`...`) against 329 lines
  at `HEAD`. It was modified before this task began: `M README.md` appears in the session's initial git status. This
  task did not touch it and did not restore it, because restoring means overwriting a file, which needs the owner's
  approval. That is why `README.md` did not receive the user-facing note about `approve BIQ-W-…`.
- **`file.txt` is untracked and empty.** It predates this task and was left alone.
- **`docs/README.md` lists ADRs only up to ADR-0040.** ADR-0041 to ADR-0050 are missing. This is pre-existing drift,
  which this task did not extend or fix.
- **Consent for the Tier-2 bootstrap is still a caller argument.** An observation for the owner, not changed here:
  `tiers.bootstrap(consent=True)` is reachable from confined engine code, and the engine guard admits its fixed
  pip/venv argument shapes. So consent for the Tier-2 install, which `CLAUDE.md` §9 says needs explicit approval, is
  asserted by the caller rather than granted by the user. This predates ADR-0051, and ADR-0008 is unchanged. It is
  proposed for owner triage as a candidate defect. No register id was allocated.
- **Plugin-root validation warns about `CLAUDE.md`.** `claude plugin validate .claude-plugin/plugin.json --strict`
  warns that "CLAUDE.md at the plugin root is not loaded as project context". This is pre-existing. The repository's
  standard check, `claude plugin validate . --strict`, passes.
- **ADR-0051's known limits.** They are recorded, not hidden:
  - `UserPromptSubmit` granting is unmeasured at runtime;
  - the unpopulated `source` field;
  - the same-OS-user trust model;
  - engagement scope;
  - latency.

## 11. Decisions made

[ADR-0051](../decisions/ADR-0051-pre-execution-write-approval-boundary.md) was accepted under the owner's remediation
prompt. It amends ADR-0001 in part (the hooks deferral) and ADR-0035 in part (Option B's hook reasoning, for the write
boundary only). Neither ADR's text is edited.

## 12. Architecture changes

`architecture.md`:

- §2: hooks are active.
- §8: the two-layer enforcement.
- §12: boundary enforcement.
- §13: `hooks/`, `writeguard/`, `write_approval`, and the guard store as runtime state.
- §16: the write row.
- §19: the ADR-0051 row.
- §20: item 13.

## 13. Project-plan updates

- M13-DEF-24 moves from `open` (remediation blocked) to **`fixed_product`**, not committed.
- The *Deferred* `hooks/` row is removed.
- Milestone statuses are unchanged: M13 stays `COMPLETED`, and M14 is not started.

## 14. Documentation updates

As §5. Not updated:

- `README.md`, for the reason in §10.
- `docs/README.md`, for the pre-existing drift in §10.
- No `docs/skills|commands|agents|integrations/` page describes the write path, so none needed changing.

## 15. Remaining work

- **An owner-run live check.** Confirm that a plugin `UserPromptSubmit` hook grants, and that the flow works in `plan`
  mode, from a marketplace install, inside subagents and under `claude plugin eval` (ADR-0051 limit 1). No paid run
  was made here.
- **A latency reduction for the hook path.** Measure it before adopting it.
- **Owner triage** of the Tier-2 bootstrap consent observation.
- **The `README.md` state** (§10) needs the owner's decision.

## 16. Git commit reference

N/A. Nothing was staged, committed or pushed. Branch `main`, HEAD `8287e98f483d82d70502e959388ab0b0708f1e1f`. The
uncommitted M13-DEF-13 remediation is still in the working tree. Its code and test files were not changed by this
task.
