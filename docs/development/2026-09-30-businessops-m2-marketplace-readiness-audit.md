# 2026-09-30 — BusinessOps Milestone 2: Claude Marketplace readiness, governance and packaging audit

**Milestone:** BOPS-M2 — Claude Marketplace readiness, governance & packaging audit
**Status on completion:** REVIEW
**Supersedes:** None

## 1. Prompt / task performed

An audit plus controlled readiness preparation. Covered: current official Anthropic requirements for listing a plugin
in the directory; the manifests; licence and EULA governance; `commands/retrieval-slice.md`; the `CLAUDE.md`
contradictions; the `project_plan.md` current state; an ADR for the migration; the contact email; package scope;
security and privacy; Windows, Python and hook portability; dependencies; first-time-user UX; description accuracy.
No feature work, commit, push, remote, tag, release or submission.

## 2. Objective

Establish, from official sources and the repository, what stands between this repository and a directory submission,
and fix only what was clearly required and safe.

## 3. Official sources consulted (2026-09-30)

- Plugin manifest reference: https://code.claude.com/docs/en/plugins-reference
- Marketplace reference: https://code.claude.com/docs/en/plugins/marketplace-reference
- Skills (invocation control): https://code.claude.com/docs/en/skills
- Hooks: https://code.claude.com/docs/en/hooks
- Setup and system requirements: https://code.claude.com/docs/en/setup
- Publish to the directory: https://claude.com/docs/directory/publish (the target of clau.de/plugin-directory-submission)
- Submit your plugin: https://claude.com/docs/plugins/submit
- Plugin pre-submission checklist: https://claude.com/docs/plugins/pre-submission-checklist
- Plugin feature support across platforms: https://claude.com/docs/plugins/platform-support
- Anthropic Software Directory Policy: https://support.claude.com/en/articles/13145358-anthropic-software-directory-policy
- Anthropic Software Directory Terms: https://support.claude.com/en/articles/13145338-anthropic-software-directory-terms
- anthropics/claude-plugins-official and anthropics/claude-plugins-community (GitHub READMEs)

The two support-site articles were read through a summarising fetch, not verbatim. Their wording must be checked on
the live pages before it is relied on.

## 4. Requirements stated by Anthropic (as read on 2026-09-30)

- **Submission route.** The directory is the Claude Marketplace. There is no separate Marketplace submission. Submit a
  "Plugin bundle" at claude.ai/directory/manage, from a Pro, Max, Team or Enterprise account.
- **Repository.** GitHub. It can be private while validating and submitting, but must be public before the listing
  goes live. The portal checks that the connected GitHub account can push to it.
- **Manifest.** `.claude-plugin/plugin.json` in the submitted folder (blocks if absent). `name`: lowercase letters,
  digits and hyphens, at most 64 characters, not a reserved word, not already taken. `description`, `author` and
  `version` are warnings if missing. Component keys must not sit inside `experimental`. `license` is described as an
  "SPDX identifier". An unknown top-level key is stripped with a warning.
- **README and licence.** A README of at least 40 words outside code blocks (blocks if absent), and a `LICENSE` file or
  a `license` field (blocks if both are missing).
- **Files.** More than 512 files, a non-image file over 256 KiB, or a non-image binary: held for a reviewer. No OS junk
  files (blocks). No symlinks, submodules or LFS for loaded files. File names valid on Windows and macOS. No
  `export-ignore` / `export-subst` in `.gitattributes`. Repository under 50 MiB archived and fewer than 10,000 entries.
- **What the plugin runs.** No real credentials anywhere. A local MCP server should run a file with plain arguments,
  "not through a shell" (held for a reviewer otherwise). Hook and MCP paths must be written in full from
  `${CLAUDE_PLUGIN_ROOT}`. Pinned launchers only.
- **Security scan.** It looks for undisclosed behaviour: sending data elsewhere, hidden code, changing Claude's
  permission settings. The README should describe everything the plugin runs, sends or fetches.
- **Review.** Each version gets automated validation and a security scan, and a person reviews a new listing. Raise
  `version` with every release. Listings are subject to the Directory Terms and Policy.
- **Policy (summarised reading).** A privacy-policy link and verified support contact are required. So are
  descriptions that precisely match functionality, three working example prompts, and MCP tool annotations
  (`readOnlyHint`, `destructiveHint`, `title`). No financial transactions.
- **Surfaces.** A listing reaches claude.ai chat, the desktop and mobile apps, Cowork and Claude Code. Chat ignores
  agents, hooks and local MCP servers. Cowork runs local MCP servers only when the session runs on the user's computer.
- **Naming.** A published plugin `name` is an immutable slug; renaming it breaks installs.

## 5. Changes made

1. `CLAUDE.md`: "agents listed explicitly" → "agents must NOT be listed, ADR-0015" (matches `architecture.md` and
   `tests/unit/test_manifest.py:50`). "20 skills" → "16 skills" (16 on disk).
2. `docs/decisions/ADR-0054-businessops-product-identity-and-bops-namespace.md`: the migration decision, indexed in
   `docs/decisions/README.md`, `architecture.md` and `docs/README.md`. ADR-0045 is unchanged.
3. `tests/unit/test_m13_grader_contract.py`: the synthetic resolver trace used a personal machine path
   (`/mnt/d/Prakash/...`). It now uses a neutral installed-plugin path of the same shape. Graders do not match on the
   path.
4. `project_plan.md`: a *BusinessOps — current state* section at the top, BOPS-M1 `COMPLETED`, BOPS-M2 `REVIEW`,
   readiness items BOPS-R1 to R8, and the BOPS-K1 root cause. History is unchanged.
5. This record, plus one row appended to `docs/development/README.md`.

## 6. Files created

- `docs/decisions/ADR-0054-businessops-product-identity-and-bops-namespace.md`
- `docs/development/2026-09-30-businessops-m2-marketplace-readiness-audit.md`

## 7. Files modified

`CLAUDE.md`, `project_plan.md`, `architecture.md` (one ADR index row), `docs/README.md` (one ADR link),
`docs/decisions/README.md` (one index row), `docs/development/README.md` (one index row),
`tests/unit/test_m13_grader_contract.py` (one string).

## 8. Features implemented

None.

## 9. Findings

The findings are recorded in `project_plan.md` as BOPS-R1 to BOPS-R8, with the root cause of BOPS-K1. The full
analysis, including the proposed licence structure and packaging boundary, is in the task report for this milestone.

## 10. Decisions made

ADR-0054 (the identity decision, recorded after the fact). No other decision was taken; each owner decision is listed
as open in `project_plan.md`.

## 11. Git commit reference

N/A — no commit, no push, no remote.
