# 2026-10-01 — BusinessOps M4: single-repository distribution architecture

**Milestone:** BOPS-M4 — First Git commit, then repository publication and directory submission preparation
(step: finalize the single-repository distribution architecture)
**Status on completion:** REVIEW
**Supersedes:** the separate-distribution-repository plan in
[`2026-10-01-businessops-distribution-repository-preparation.md`](2026-10-01-businessops-distribution-repository-preparation.md)
(its build and validation results stand)

## 1. Prompt / task performed

The owner decided that BusinessOps has exactly one GitHub repository,
<https://github.com/conceptwebworld26/BusinessOps>. It is the reviewable source repository and holds the validated
installable package under `dist/businessops/`. No `BusinessOps-Plugin` repository. The task: correct the package's
repository URL, keep the BOPS-R16 fix and the README lineage removal, keep the development material public, rebuild
and validate the package, check current Anthropic requirements, document the decision, commit once, and push to the
existing repository.

## 2. Decision

[ADR-0057](../decisions/ADR-0057-one-public-repository-for-source-and-package.md), amending ADR-0055:

- one public repository holds the source, tests, evals, ADRs, records, evidence and the builder, plus the committed
  package `dist/businessops/`. `.gitignore` changes from ignoring all of `dist/` to `/dist/*` with
  `!/dist/businessops/`, so only the package is tracked; throwaway copies and probes under `dist/` stay ignored;
- a directory submission names the plugin path `dist/businessops`;
- the packaged manifests keep the source's `homepage` and `repository`, the BusinessOps repository.

## 3. Changes

- `scripts/build_distribution.py`: the `BusinessOps-Plugin` URL rewrite added earlier the same day was removed, so the
  packaged manifests equal the source's apart from the existing `experimental.evals` removal. Kept: the generated
  package `.gitignore` (`__pycache__/`, `*.py[cod]`, with two comment lines) and the build check that rejects bytecode
  or a different `.gitignore` (BOPS-R16).
- `README.md`: the *Project lineage* section, which named BusinessIQ as the predecessor, stays removed. The lineage is
  still recorded in development documents that do not ship (`architecture.md`, `project_plan.md`, ADR-0054,
  historical records).
- `tests/unit/test_distribution_build.py`, now 15 tests, adds:
  - the generated `.gitignore` is exactly the hygiene file;
  - no plugin file references `.gitignore`;
  - the build check rejects bytecode and a foreign `.gitignore`;
  - the packaged manifests equal the source's and name the BusinessOps repository;
  - the README presents BusinessOps alone;
  - **the committed `dist/businessops/` equals a fresh build** (line endings normalised).
- `.gitignore`: the `dist/businessops/` exception.
- `dist/businessops/`: the package, now committed.
- Documentation: ADR-0057; the `architecture.md` distribution row and ADR index; `docs/decisions/README.md`;
  `docs/README.md`; a dated update banner on the earlier M4 record (its body unchanged); this record; index and
  evidence rows; `project_plan.md`.

## 4. Package

Evidence: [`docs/testing/evidence/2026-10-01-single-repository-package-validation.txt`](../testing/evidence/2026-10-01-single-repository-package-validation.txt).

- **189 files, 2,650,014 bytes.** Against the approved 188-file, 2,650,190-byte package:
  - `.gitignore` added (+186 bytes);
  - `README.md` changed (lineage section removed, −362 bytes);
  - the manifests' URLs are unchanged, so `plugin.json` and `marketplace.json` are identical to the approved package;
  - the other 185 files are identical.
- `claude plugin validate dist/businessops --strict` and the `plugin.json` strict check both passed.
- No file over 256 KiB, no binary, symlink, bytecode, secret, personal path, `CLAUDE.md` or BusinessIQ mention.
  113 reference tokens with no unresolved `${CLAUDE_PLUGIN_ROOT}` path.
- MCP, run against a byte-identical throwaway copy: Connected; `initialize`, `tools/list` (with annotations) and a real
  `recompute` (completed) all worked; unknown id → `request_not_found`; malformed request → `request_id_invalid`;
  unknown tool → JSON-RPC `invalid params`.
- BOPS-R16, shown earlier the same day on a copy: running the plugin wrote 88 `.pyc` files, and git ignored all of
  them.

## 5. Current Anthropic requirements (official pages, read 2026-10-01)

- **Repository.** GitHub; can be private while validating and submitting, and must be public before the listing goes
  live. The connected GitHub account must be able to push to it. The BusinessOps repository is public and owned by
  the submitting account.
- **Plugin in a subfolder.** "The repository doesn't have to be dedicated to the plugin. If the plugin is one folder
  in a larger repository, give that folder as the plugin path; the directory reads and scans only that folder." So a
  repository that also holds tests, docs and development material is acceptable; only `dist/businessops/` is the
  plugin.
- **Subfolder rules.**
  - Hook and MCP command paths must be written in full from `${CLAUDE_PLUGIN_ROOT}` (blocks otherwise). All five
    commands comply.
  - Scripts that a hook or MCP server runs must not use other shell variables, command substitutions or calls to
    other plugin files (held for a reviewer otherwise). `hooks/bops_guard.sh` and `lib/bops_run.sh` do use them, so a
    reviewer hold is expected (BOPS-R17).
- **Repository-level limits.** Fewer than 10,000 files and folders (1,033), under 50 MiB archived and 256 MiB unpacked
  (12.0 MiB), valid file names, no case collisions, no symlinks, submodules or LFS pointers, and no `.gitattributes`
  at the root, above or inside the plugin folder. All met.
- **Plugin folder.** README of at least 40 words (4,056), `LICENSE` and `license`, at most 512 files (189), no
  non-image file over 256 KiB and no binaries: met.
- **Directory Policy** (summarising fetch). Privacy policy (`PRIVACY.md`), verified support contact
  (`hello@conceptwebworld.com`), documentation, at least three working examples (15 in the README), sample data for
  testing (the demo dataset): met. Tool annotations are worded for remote MCP servers; BusinessOps' server is local and
  carries them anyway.

## 6. Remaining owner decisions and risks

- **BOPS-R17.** A reviewer hold is expected for the hook and MCP scripts, because the plugin is in a subfolder.
- **BOPS-R18.** The README's self-hosted install (`claude plugin marketplace add conceptwebworld26/BusinessOps`) uses
  the root marketplace entry (`"source": "./"`), so it installs the whole development tree, not `dist/businessops/`.
- Unchanged: BOPS-R10, R13, R15; Cowork and chat untested; licence documents not legally reviewed.

## 7. Git

One commit, "M4: finalize single-repository distribution architecture", on top of `b5b762a` and `58a91b4`, pushed to
`origin` (the BusinessOps repository) without force. See the task report for hashes and verification.
