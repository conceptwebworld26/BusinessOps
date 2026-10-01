# 2026-09-30 — BusinessOps Milestone 3.1: installed-package runtime verification

**Milestone:** BOPS-M3.1 — Installed-package runtime verification
**Status on completion:** REVIEW
**Supersedes:** None

## 1. Why M3.1 was required

Milestone 3 left two open questions before any Git operation:

1. Do the relative `reference/…` paths in commands and skills work in an installed plugin? M3 had tried a
   `${CLAUDE_PLUGIN_ROOT}` rewrite and reverted it, because it broke ADR-0042's static-guard invariant, without
   proof that anything was actually broken.
2. Can the local MCP verifier be launched directly instead of through `sh`? The directory's pre-submission checklist
   holds for a reviewer a local MCP server that is not started as a file with plain arguments.

The run that did this work was interrupted by an API connection error after the fix, the ADR and the rebuild. A
read-only recovery audit confirmed what had completed. This record covers both the interrupted run and the finishing
run.

## 2. The reference-path problem

76 backticked `reference/<file>.md` mentions in 24 files (8 commands, 15 skills, `agents/bops-research-scout.md`)
tell Claude to read, follow or cite the policy documents in `reference/`. Every recorded development run had started
Claude Code in the repository root, where the relative path happens to resolve.

## 3. Evidence before the fix

Test: the built package was copied outside the development repository and loaded with `claude -p … --plugin-dir
<copy>`. The sessions ran from a separate folder, outside any git repository, holding only the demo CSV. Evidence is
in [`docs/testing/evidence/2026-09-30-m3-1-installed-reference-test.txt`](../testing/evidence/2026-09-30-m3-1-installed-reference-test.txt).

- **Command** (`/businessops:business-health`, directed to follow its own read instruction): Claude read
  `<project>/reference/analysis-framework.md` and got "File does not exist".
- **Skill** (`businessops:bops-competitor-analysis`): the platform supplied "Base directory for this skill:
  …/skills/bops-competitor-analysis". Claude read `…/skills/bops-competitor-analysis/reference/ambiguity-protocol.md`
  and got "File does not exist".
- **Natural run** of `/businessops:business-health`: Claude did not attempt the reads at all.

Anthropic's skills documentation (read 2026-09-30) is consistent with this. `${CLAUDE_SKILL_DIR}` is "the skill's
subdirectory within the plugin, not the plugin root", and `${CLAUDE_PLUGIN_ROOT}` is the variable for "files bundled
anywhere in the plugin, including resources shared between the plugin's skills".

## 4. The fix

- All 76 mentions now read `` `${CLAUDE_PLUGIN_ROOT}/reference/<file>.md` ``, in the same 24 files, with no
  relative form left. Frontmatter was not touched, and no mention is in a description, so there is no always-on
  token cost.
- **Security-test change** (ADR-0056). `tests/unit/test_m13_def04_static_guard.py` and
  `tests/unit/test_m13_def08_runtime_resolver.py` remove backticked tokens that name one of the six shipped
  reference files before applying the original rule: `${CLAUDE_PLUGIN_ROOT}` appears only in the launcher line.
  Anything else on such a line still fails. A new test,
  `test_a_reference_token_names_a_shipped_document_and_is_never_in_a_code_block`, requires every token to name an
  existing file and never to sit in a code block. Negative controls were checked in memory: an unknown file name, a
  token plus another plugin-root use, and a token in a code block are all still caught.
- **ADR-0056** (Proposed) records the amendment, indexed in `architecture.md`, `docs/decisions/README.md` and
  `docs/README.md`.

## 5. Installed-package verification after the fix

On the rebuilt package, in the same setup, the command read `<copy>/reference/analysis-framework.md`
("# Reference — Analysis Framework") and the skill read `<copy>/reference/ambiguity-protocol.md`
("# Reference — Ambiguity Protocol"). Claude Code substituted `${CLAUDE_PLUGIN_ROOT}` with the actual installed
path.

## 6. MCP direct-launch investigation

- `lib/bops_run.sh` has no shebang and is not executable, so it cannot be launched as a file as it stands.
- Launching Python directly is Option A of ADR-0052, which was rejected: a fixed interpreter name fails on hosts
  that have only the other name (the R-13 defect).
- **Test**, in a scratch copy only: a `#!/bin/sh` line was added, the executable bit set, and `.mcp.json` pointed
  straight at the script. The script ran when executed from Git Bash, but `claude --plugin-dir <copy> mcp list`
  reported `✘ Failed to connect — CONNECTION_CLOSED` on native Windows. The production form reported
  `✔ Connected`.
- **Anthropic's checklist** (read 2026-09-30): "Start each local MCP server by running a file in the plugin with plain
  arguments, such as `node ${CLAUDE_PLUGIN_ROOT}/server.js`, not through a shell …" has the result **Held for a
  reviewer** ("MCP server command wasn't read"), not "Blocks". The page on MCP says nothing about how a stdio command
  is spawned on Windows.

**Decision: `.mcp.json` is unchanged.** Direct launch would break a documented supported environment (native Windows
with Git for Windows). The `sh` form carries a possible reviewer hold, which is a review risk, not a functional
defect.

## 7. Distribution validation and MCP verification (finishing run)

Evidence: [`docs/testing/evidence/2026-09-30-m3-1-distribution-validation.txt`](../testing/evidence/2026-09-30-m3-1-distribution-validation.txt)
and [`docs/testing/evidence/2026-09-30-m3-1-mcp-verification.txt`](../testing/evidence/2026-09-30-m3-1-mcp-verification.txt).

- `claude plugin validate dist/businessops --strict` and the `plugin.json` strict check both passed.
- The package is 188 files and 2,644,601 bytes, with a valid plugin root. It has 76 `${CLAUDE_PLUGIN_ROOT}/reference/`
  tokens, all resolving, and 0 relative references. It contains no developer, history, test or eval files, no file
  over 256 KiB, no binary, no symlink and no personal path.
- MCP from the package, as `.mcp.json` starts it: `claude mcp list` reported Connected. `initialize`, `tools/list`
  (`recompute` with its annotations) and `tools/call` all worked: a genuine sealed request came back `completed`
  with one record, and an unknown id returned `request_not_found`.

## 8. Test results

Full suite after the M3.1 changes: `Ran 5336 tests` — `FAILED (failures=47, errors=8, skipped=38)`. Against
Milestone 3 (5,335 tests, 47, 7, 38) there was one new test (the reference-token test, passing), no resolved failure,
and one new error, `test_no_gate_record_block_exists_in_the_repository`.

That error was caused by the finishing run itself. The evidence files had first been placed in
`docs/development/evidence/`, and that test opens every entry of `docs/development/` as a file. The evidence moved
to `docs/testing/evidence/`, and the test passes. The final full run, after this record was written, is reported in
`project_plan.md` (BOPS-M3.1) and the task report.

## 9. Cleanup

Deleted, each positively identified as created by the M3.1 live tests:

- in `~/.claude/businessops/guard/`, two pending approvals (`BOPS-W-MHALQ8ZG`, `BOPS-W-X8UKRDHW`) and five session
  markers. Each held one of the five test sessions' ids. The four empty directories the test had created were then
  removed; `~/.claude/businessops/` did not exist before 19:20 that day;
- the session scratchpad's `m31/` folder (502 files: two package copies, the test project and the logs) and two subset
  test logs.

Retained: Claude Code's own transcripts of the five headless sessions in `~/.claude/projects/` (managed by Claude
Code), `~/.claude/businessiq/` (unrelated) and the scratchpad files from earlier milestones.

## 10. Remaining risks

- The `sh`-launched MCP server may be held for a reviewer.
- On native Windows the write guard resolves `/dev/null` to `C:\dev\null`, so a read-only command with `2>/dev/null`
  asks for approval. This is the pre-existing failing test `test_17_read_with_shell_syntax_is_not_a_write`, now seen
  in a live session.
- Guard messages cite "CLAUDE.md section 9", which is not shipped.
- Cowork and chat are untested.

## 11. Git commit reference

N/A — no commit, no push, no remote.
