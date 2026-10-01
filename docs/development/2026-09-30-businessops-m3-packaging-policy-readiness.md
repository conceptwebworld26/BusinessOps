# 2026-09-30 — BusinessOps Milestone 3: packaging, policy and marketplace readiness

**Milestone:** BOPS-M3 — Packaging, policy & marketplace readiness
**Status on completion:** REVIEW
**Supersedes:** None

## 1. Prompt / task performed

Prepare a clean, installable distribution boundary for Anthropic's plugin directory, keeping this repository as the
complete development repository. Move `retrieval-slice` out of the shipped commands; manifest `displayName` and an
accurate description; a proprietary `LICENSE`, an `EULA.md` and a `PRIVACY.md`; MCP tool annotations; Windows and
Claude-application documentation; command-surface, write-guard, hook-cost and context-cost reviews; security audit;
tests. No commit, push, remote, tag, release or submission.

## 2. Changes made

1. **Distribution (ADR-0055, Proposed).** `scripts/build_distribution.py` builds the installable package from an
   explicit allowlist into `dist/businessops/`, which git ignores, with the plugin root at the package root. It makes
   two transformations: `experimental.evals` is removed from the packaged manifest, and links to unshipped documents
   are rewritten to the development repository on GitHub. It then checks the result. Result: 188 files, 2,642,929
   bytes, no problems. `tests/unit/test_distribution_build.py` (9 tests) enforces the boundary.
2. **`retrieval-slice`** moved from `commands/` to `dev/harness/retrieval-slice.md`, with a note on running it. Its
   three tests read the new path. The five inventory tests that count command files now also enumerate
   `dev/harness/`, so their counts are unchanged (10 engine commands, 38 blocks, S4 = 19) and the harness stays under
   the same checks. The two "exactly one launcher" tests ignore `dist/` (a build copy).
   `docs/commands/README.md` and `docs/troubleshooting/README.md` are updated.
3. **Manifests.** `displayName: "BusinessOps"`. The approved description, except "Every figure is computed
   deterministically" became "Every figure from your data is computed deterministically", because public-research
   figures are quoted from sources, not computed. Contact `hello@conceptwebworld.com`.
4. **`LICENSE`** rewritten: no "confidential" wording; an express grant to install and use through Anthropic's
   directory and Claude applications, subject to the EULA. **`EULA.md`** and **`PRIVACY.md`** added. Neither has been
   legally reviewed. The EULA has no governing-law clause, because no jurisdiction was decided.
5. **MCP.** The `recompute` tool carries `title`, `readOnlyHint: false`, `destructiveHint: false` and
   `openWorldHint: false`, from its behaviour: it creates a record file (create-only) and opens no network
   connection. One new test.
6. **README.** New sections: *Platform requirements*, *Where BusinessOps runs*, *Support*, *Privacy*, and a hook
   disclosure table. The "Failures block writes" bullet is corrected: without `sh` the guard cannot start and is not
   active. The demo examples use the CSV.
7. **Governance.** `CLAUDE.md` layout, `architecture.md` distribution row and ADR index, ADR-0055, `docs/README.md`,
   `docs/decisions/README.md`, `project_plan.md` current state, and this record.

## 3. Tried and reverted

- **Plugin-root reference paths.** Rewriting the 76 `reference/*.md` mentions in commands and skills to
  `${CLAUDE_PLUGIN_ROOT}/reference/...` broke 112 tests of the ADR-0042 static-guard invariant: the plugin root
  appears only in the launcher line. That is a security design decision, so the change was reverted exactly. The
  underlying risk (relative `reference/` reads in an installed plugin) is open and unverified.
- **Lazy engine imports.** Lazy `bops/__init__` imports cut guard import time from 36.6 ms to 30.4 ms, but the
  end-to-end hook time did not change (225 ms and 226 ms), so the change was reverted.

## 4. Test results

- Full suite: `Ran 5335 tests` — `FAILED (failures=47, errors=7, skipped=38)`. The failure set is identical to
  BOPS-M2 (5,324 tests, 47, 7, 38), with 11 new tests all passing.
- Package root (`dist/businessops/`): `claude plugin validate . --strict` passed, and
  `claude plugin validate .claude-plugin/plugin.json --strict` passed (it failed on the repository because of
  `CLAUDE.md`). `plugin details`: 34 commands and skills, 2 agents, 4 hooks, 1 MCP server, about 7,074 tokens
  always-on (about 7,210 before). Launcher isolated, plugin `businessops`. A sales analysis of the demo CSV ran from
  the package in a separate working directory and wrote nothing. MCP `initialize`, `tools/list` (with annotations)
  and `tools/call` worked. A scripted hook session showed each property: deny outside the output folder, allow a new
  output file, refuse an approval phrase smuggled through `SendMessage`, grant only from the user's prompt, single use,
  and store protection.

## 5. Git commit reference

N/A — no commit, no push, no remote.
