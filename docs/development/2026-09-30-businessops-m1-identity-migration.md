# 2026-09-30 — BusinessOps Milestone 1: product identity and technical namespace migration

**Milestone:** BOPS-M1 — Product identity & technical namespace migration
**Status on completion:** REVIEW
**Supersedes:** None

## 1. Prompt / task performed

Convert the repository, restored from a BusinessIQ backup into a fresh, commit-less repository, into
the independent product **BusinessOps** for Claude Marketplace submission. Migrate the active
identity (`BusinessIQ` → `BusinessOps`, `businessiq` → `businessops`) and the internal technical
prefix (`biq` → `bops`), keep historical records and SHA-pinned evidence unchanged, make licensing
and rights-holder attribution consistent ("Prakash Meghani - Concept Web World"), no commit, no
push, no remote.

## 2. Objective

No unintentional stale BusinessIQ identity in the active implementation, with the plugin, its
runtime and its tests internally consistent under the new identifiers.

## 3. Changes made

1. **Baseline.** The full suite was run before any change: 5,324 tests, 47 failures, 7 errors,
   38 skipped. All 54 are Windows-host environment failures (symlink privilege WinError 1314, the
   resolver's path handling under Git Bash, POSIX path assumptions in write-classifier tests).
2. **Renames** (plain moves; the repository has no commits):
   `lib/python/biq/` → `lib/python/bops/`; `lib/python/biq_run.py` → `bops_run.py`;
   `lib/biq_run.sh` → `bops_run.sh`; `hooks/biq_guard.sh` → `bops_guard.sh`;
   `config/businessiq.defaults.json` → `businessops.defaults.json`; 16 `skills/biq-*` →
   `skills/bops-*`; 2 `agents/biq-*.md` and 2 `docs/agents/biq-*.md` → `bops-*`; 19
   `evals/routing/*-biq-*` case directories → `*-bops-*`.
3. **Scoped content migration** by a token-aware script (not a repository-wide replace): 332
   active files. Excluded: `.git`, `.claude`, `docs/development/`, `docs/decisions/`,
   `tests/fixtures/eval_results/`, `tests/fixtures/eval_inputs/`, `evals/results/`, bytecode,
   `project_plan.md` and `LICENSE` (edited by hand). Links and filenames that point into historical
   records (for example `ADR-0045-businessiq-owned-portable-runtime-resolution.md`) were shielded and
   keep their exact bytes. `biq` was matched only as a whole token (not inside another word).
4. **Load-bearing identifiers now agree:** manifest `name` `businessops`; launcher
   `PLUGIN_NAME = "businessops"`; write guard `PLUGIN_PREFIX = "businessops:"`; research handback
   agent `businessops:bops-research-scout`; MCP server `bops-verifier`, tool
   `mcp__plugin_businessops_bops-verifier__recompute`, declared by `bops-analysis-verifier`;
   state `.businessops/`, `businessops-output/`, `~/.claude/businessops/{runtime,guard}/`;
   variables `BOPS_PYTHON`, `BOPS_GUARD_ROOT`, `BOPS_LARGE_DATASET`, `BOPS_AGENT_BOUNDARY_RUNTIME`,
   `BUSINESSOPS_LIVE_SMOKE`; approval codes `BOPS-W-…`; scout protocol `BOPS-REC` / `BOPS-END`;
   eval case schema `bops-eval-case/2`; gate fence `bops-connector-gate`; error base
   `BusinessOpsError`.
5. **One migration-caused test failure, fixed in the test.** The SHA-pinned closing evaluation
   records the routing cases under their historical ids (`r01-positive-biq-…`).
   `tests/unit/test_m13_eval_cases.py` gained `current_case_id()`, which translates only that one
   segment; the fixture is unchanged.
6. **Licence and branding.** `LICENSE` rights holder → "Prakash Meghani - Concept Web World"
   (three places, text otherwise unchanged). Manifests: author and owner "Prakash Meghani - Concept
   Web World", `license` `LicenseRef-BusinessOps-Proprietary` (an SPDX-style reference to the
   proprietary `LICENSE`), homepage and repository `https://github.com/conceptwebworld26/BusinessOps`.
   `README.md` and `architecture.md` no longer say MIT.
7. **Lineage notes** in `architecture.md`, `README.md`, `docs/releases/0.1.0.md` and
   `docs/testing/README.md`; `project_plan.md` gained a BusinessOps header, a *BusinessOps
   milestones* section and known issue BOPS-K1. Its BusinessIQ milestone history is unchanged.
8. Local `.claude/settings.local.json` (gitignored) now enables `bops-verifier`. Stale ignored
   `__pycache__/` directories were deleted. `evals/results/` (ignored) was left as it was.

## 4. Files created

- `docs/development/2026-09-30-businessops-m1-identity-migration.md` (this record)

## 5. Files modified

332 active files by the scoped migration, plus by hand: `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `LICENSE`, `README.md`, `architecture.md`, `CLAUDE.md`
(alignment), `project_plan.md`, `docs/releases/0.1.0.md`, `docs/testing/README.md`,
`tests/unit/test_m13_eval_cases.py`, `docs/development/README.md` (one index row appended),
`.claude/settings.local.json` (local).

## 6. Files deleted

None tracked. Ignored bytecode (`__pycache__/`) only.

## 7. Features implemented

None. Identity and namespace only; no behaviour, scope or algorithm changed.

## 8. Tests performed

```
python tests/run_tests.py                              # before and after
claude plugin validate . --strict
claude plugin validate .claude-plugin/plugin.json --strict
claude --plugin-dir . plugin details businessops
sh lib/bops_run.sh --where
sh lib/bops_run.sh --verifier   # MCP initialize + tools/list over stdio
sha256sum of the pinned tests/fixtures/eval_results files; eval_inputs manifest check
```

## 9. Test results

- Before: `Ran 5324 tests` — `FAILED (failures=47, errors=7, skipped=38)`.
- After: `Ran 5324 tests` — `FAILED (failures=47, errors=7, skipped=38)`. The failing set is the
  baseline set, test names normalised `biq` → `bops`; no migration-caused failure remains.
- `claude plugin validate . --strict`: passed. `plugin.json --strict`: the one known `CLAUDE.md`
  advisory only (architecture.md, *Validator advisory*).
- `plugin details businessops`: 35 commands and skills, agents `bops-analysis-verifier` and
  `bops-research-scout`, 4 hooks, MCP server `bops-verifier`; about 7,210 tokens always-on.
- Launcher: `"plugin": "businessops"`, isolated mode. Verifier server: `serverInfo.name`
  `bops-verifier`, one tool `recompute`.
- Pinned hashes unchanged (`77a088d5…`, `ee59fea7…`, `ff828b70…`); eval-input manifest: 0 mismatches.

## 10. Issues discovered

- **BOPS-K1** (`project_plan.md`, *Known issues*): `python3` on the development host is the
  Microsoft Store App Execution Alias, the source of the "Python was not found" hook messages.
  Recorded only; nothing about PATH, aliases, Python or the hooks was changed.
- The 54 Windows-environment test failures predate this milestone.

## 11. Decisions made

No ADR: the prompt limited new documentation to this migration record. Needing owner review: the
licence identifier `LicenseRef-BusinessOps-Proprietary`, and whether a rename ADR is wanted.

## 12. Architecture changes

Identifiers only, recorded in the `architecture.md` lineage note. No structural change.

## 13. Project-plan updates

BOPS-M1 added as `REVIEW`; BOPS-K1 added as open.

## 14. Documentation updates

Current-facing documentation migrated; historical records unchanged.

## 15. Remaining work

Owner review; first commit; BOPS-K1; the 54 Windows-environment test failures.

## 16. Git commit reference

N/A — no commit, no push, no remote.
