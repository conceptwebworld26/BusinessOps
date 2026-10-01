# 2026-10-01 — BusinessOps: distribution repository preparation

**Milestone:** BOPS-M4 — First Git commit, then repository publication and directory submission preparation
(step: prepare and validate the distribution package)
**Status on completion:** REVIEW
**Supersedes:** None

## 1. Prompt / task performed

Prepare and validate the clean installable package that will become the root of a separate BusinessOps distribution
repository, using the existing builder as the only packaging mechanism. The development repository's commit,
history, remote and source stay unchanged. No distribution repository, remote, push, submission or publication.

## 2. Build source and builder

- Source: development repository `main` at `58a91b4a1d178f922944ddd37f4b2332c09a40ae`, clean working tree, tracking
  `origin/main` (<https://github.com/conceptwebworld26/BusinessOps>), no tags.
- Builder: `python scripts/build_distribution.py`, unchanged (ADR-0055). Output: `dist/businessops/` (gitignored).
  The builder replaces a previous build only when that build's `plugin.json` names `businessops`.
- The builder copies an explicit allowlist: `.claude-plugin/`, `.mcp.json`, `agents/`, `commands/`, `config/`,
  `hooks/`, `lib/`, `reference/`, `skills/`, `README.md`, `LICENSE`, `EULA.md`, `PRIVACY.md`, `CONNECTORS.md`, and
  `assets/demo-data/northwind_sales.csv` and `business_context.json`. It excludes bytecode.
- It makes two transformations: it removes `experimental.evals` from the packaged `plugin.json`, and it rewrites
  relative Markdown links to unshipped documents into links to the development repository on GitHub. It then checks
  the package for missing `${CLAUDE_PLUGIN_ROOT}` targets, forbidden paths, files over 256 KiB, binaries, symlinks,
  more than 512 files, broken links and personal paths.

## 3. Result

Evidence: [`docs/testing/evidence/2026-10-01-distribution-package-validation.txt`](../testing/evidence/2026-10-01-distribution-package-validation.txt).

| Check | Result |
|---|---|
| Builder | exit 0, `"problems": []` |
| Files / bytes | **188 / 2,650,190** |
| Compared with the approved M4A.1 package | 0 files added, removed or changed (SHA-256 per file) |
| Top level | `.claude-plugin/`, `.mcp.json`, `agents/`, `assets/`, `commands/`, `config/`, `CONNECTORS.md`, `EULA.md`, `hooks/`, `lib/`, `LICENSE`, `PRIVACY.md`, `README.md`, `reference/`, `skills/` |
| Files over 256 KiB, binaries, symlinks, bytecode, OS junk files | 0 each; largest file `assets/demo-data/northwind_sales.csv`, 244,323 bytes |
| Development material | none: no `tests/`, `evals/`, `docs/`, `dev/`, `scripts/`, `.claude/`, `.git/`, `CLAUDE.md`, `architecture.md`, `project_plan.md`, `.gitignore`, demo `.xlsx` or generator |
| Secrets, personal paths | none. Emails: `hello@conceptwebworld.com`, plus `reuters.com@evil.example` in a code comment |
| `CLAUDE.md` | not shipped; not named by any instruction, policy or manifest file |
| Reference paths | 113 `${CLAUDE_PLUGIN_ROOT}/reference/` tokens, all resolving; 0 relative |
| README | 4,105 words outside code blocks, 15 example prompts. 9 links into the development repository, all present in `origin/main` (spot-checked on GitHub) |
| `claude plugin validate dist/businessops --strict` | passed; the `plugin.json` strict check also passed |
| Package test modules (13) | no failure outside the known native-Windows baseline (7, all in `unit.test_m13_def24_write_classifier`) |
| MCP (run against a byte-identical copy of the package) | `mcp list` reported Connected. `initialize` worked with no instructions published. `tools/list` returned `recompute` with its annotations. A real sealed request completed (1 record); unknown id → `request_not_found`; malformed id and extra argument → `request_id_invalid`; unknown tool → JSON-RPC `invalid params` |
| Identity | `businessops` / BusinessOps, `bops-verifier`, `mcp__plugin_businessops_bops-verifier__recompute`, Prakash Meghani - Concept Web World, `hello@conceptwebworld.com`, `LicenseRef-BusinessOps-Proprietary`, 0.1.0 |

The package is suitable to become the root of a separate Git repository. `.claude-plugin/plugin.json` is at its
root, the packaged `marketplace.json` uses `"source": "./"`, and nothing in it depends on the development
repository's layout.

## 4. Finding: running the package in place writes Python bytecode

Before this rebuild, `dist/businessops/` held 207 files. The 19 extra files were `__pycache__/*.pyc`, written when
the M4A and M4A.1 checks ran the engine and the MCP server directly from the package. The launcher runs Python in
isolated mode (`-I`), which ignores `PYTHONDONTWRITEBYTECODE`. A `.pyc` file is a non-image binary, which the
directory holds for a reviewer.

For this milestone, the MCP checks ran against a byte-identical throwaway copy, and the package kept 0 bytecode
files.

**Recommendation for the distribution repository (owner decision):** never run the plugin from the repository's
working tree, and/or add a `.gitignore` that excludes `__pycache__/` and `*.pyc`. The builder does not create one;
adding it is a repository-specific file and was not done here.

## 5. Current official requirements (re-read 2026-10-01)

- The pre-submission checklist and *Submit your plugin* pages are unchanged in every point that applies to this
  package. Results: README ≥ 40 words (blocks); `LICENSE` or `license` (blocks); more than 512 files, a non-image file
  over 256 KiB or a non-image binary (held for a reviewer); a local MCP server started through a shell (held for a
  reviewer, BOPS-R10); symlinks and OS junk files (block); `.gitattributes` `export-ignore`, `export-subst` and
  content filters (validation stops).
- Repository: on github.com, with the connected account able to push. It can be **private** while validating and
  submitting (with the Claude GitHub App installed and consent to source upload), and **must be public before the
  listing goes live**. A plugin at the repository root avoids the stricter subfolder script checks.
- Directory Policy (summarising fetch, not verbatim): privacy policy for software that "collects user data or
  connects to a remote service"; verified support contact; documentation; "at least three working examples"; a test
  account with sample data. Tool annotations are worded for **remote** MCP servers. The plugin's server is local, and
  its annotations are present anyway.
- No change to the package is needed for any of these.

## 6. Other observations (owner decisions, no change made)

- The README's *Project lineage* section names BusinessIQ as the predecessor. The directory shows the README as the
  listing description, so that text would be public in the listing.
- `plugin.json` `homepage` and `repository` point to the development repository. That works, since it is public, but
  the distribution repository's own URL could be preferred once it is named.

## 7. Files

Development repository only, uncommitted, for review:

- created: this record; `docs/testing/evidence/2026-10-01-distribution-package-validation.txt`;
- updated: `docs/development/README.md` (index row), `docs/testing/README.md` (evidence row), `project_plan.md`
  (BOPS-M4 progress, BOPS-R16).

Nothing in the package changed, and the development commit `58a91b4` is unchanged. No distribution repository, remote,
push, submission or publication.
