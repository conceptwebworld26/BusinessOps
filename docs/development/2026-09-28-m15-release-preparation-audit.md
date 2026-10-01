# 2026-09-28 — M15: final release-preparation audit

**Milestone:** 14 — Documentation & Release (the release-preparation audit before tagging)
**Status on completion:** REVIEW — audit complete. One current-facing status correction is left uncommitted, as the prompt
requires. **OWNER RELEASE APPROVAL REQUIRED.** BusinessIQ is **not released**.
**Supersedes:** None

## 1. Prompt / task performed

"M15 — Final Release Preparation Audit". The prompt asked for these audits and outputs:

- version;
- manifest and marketplace;
- exact package inventory, with accidental artifacts;
- git history;
- release-note convention;
- documentation consistency;
- full validation;
- a version and tag recommendation.

Excluded: push, tag, publication, release creation, history rewriting, source changes and new commits.

## 2. Starting state

- HEAD `57e92fae06161cd40e4fdd2c93c90557dc092202` ("M14: complete documentation, remediation, and release validation"),
  on `main`.
- `origin/main` at `595e910`; local `main` is 4 commits ahead (`50d1f0e`, `5c1b15d`, `8e4ab17`, `57e92fa`).
- Working tree clean, no stash, no local tags.

## 3. Version audit

**The authoritative product version is `0.1.0`.** It is declared in `.claude-plugin/plugin.json`, the manifest
`architecture.md` §2 names as required.

| Where | Value | Role |
|---|---|---|
| `.claude-plugin/plugin.json` `version` | `0.1.0` | **Authoritative** |
| `.claude-plugin/marketplace.json` `plugins[0].version` | `0.1.0` | Mirrors the manifest |
| `lib/python/biq/__init__.py` `__version__` | `0.1.0` | Mirrors the manifest |
| `README.md` *Current status* | "manifest version is `0.1.0`. No release has been tagged." | Accurate |
| `architecture.md` header "Version: 0.2.0" | `0.2.0` | The **architecture document's** revision number (Revision 2), not the product version. Not a mismatch |
| `SCHEMA_VERSION` in `decision_support.py`, `data_profile.py`, `executive_report.py`, `strategy.py`, `swot.py` and `verification.py` | `1.0.0` | Artifact **schema** versions, independent of the product version |
| `verification_server.py` `SERVER_VERSION` | `1.0.0` | MCP server protocol identity |
| `tests/integration/test_m13_def04_engine_entry.py` | `…/plugin cache/businessiq/0.1.0` | A simulated install path, not a version assertion |

**History.** The manifest entered the repository with `0.1.0` at `62580f3` (M10.2) and has never changed.

**Absences:**

- no changelog or release-notes file exists;
- no local tag exists;
- remote tags could not be read, because that needs GitHub credentials and none were used or changed;
- no pre-release label appears anywhere.

**Proposed release version: `0.1.0`.**

- It is the declared, never-released version.
- Changing it would invent a version the repository does not establish.
- The pre-1.0 number matches the documented state: M9 is still `IN PROGRESS`, and owner decisions are open.

**Proposed tag: `v0.1.0`.** The repository has no tag convention, so the tag *name format* is an owner decision.
`v0.1.0` is the conventional form for a semantic-version manifest, and it is only a proposal.

## 4. Manifest and marketplace audit

| Check | Result |
|---|---|
| Plugin identity | `name` `businessiq`, version `0.1.0`, MIT, author, homepage and repository present. `marketplace.json` names marketplace and plugin `businessiq`, `source: ./` |
| Component discovery | No component keys, by design: `architecture.md` §2 records that declaring `agents` made them stop shipping |
| Commands | 19 files (18 user-facing plus the internal `/retrieval-slice`); frontmatter within the allowed fields |
| Skills | 16; each `name` matches its directory; frontmatter within the allowed fields |
| Agents | 2 (`biq-research-scout`, `biq-analysis-verifier`); allowed fields only |
| Hooks | `PreToolUse`, `UserPromptSubmit` and `UserPromptExpansion` run `hooks/biq_guard.sh`; `PostToolUse` (`Agent`, `Task`) runs `lib/biq_run.sh --handback`. Every referenced file exists |
| MCP | `biq-verifier`: `sh ${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh --verifier`; the file exists |
| Entry points | Every command and skill enters the engine only through `${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh` |
| Evals | `experimental.evals: evals`, with 64 `case.yaml` files |
| Live discovery | `claude --plugin-dir <repo> plugin details businessiq`, with no install: **businessiq 0.1.0** — Skills (35: 19 commands and 16 skills), Agents (2), Hooks (4), MCP servers (1), ~7,260 tokens always-on |
| Strict validation | Passed (§8) |

Every component the manifest discovers exists, and every intended component is discovered. No component was added.

## 5. Release package inventory

**What installs.** `source: ./` means a marketplace install copies the repository's **tracked** files: **633 files,
9,708,817 bytes (about 9.7 MB)**. That is the M14-4 figure of 626 plus the seven files added in M14-4 to M14-6.

| Class | Files | Size |
|---|---|---|
| Required runtime and product (`commands/`, `skills/`, `agents/`, `hooks/`, `lib/`, `reference/`, `config/`, `.claude-plugin/`, `.mcp.json`) | 182 | 2.35 MB |
| User-facing documentation (`README.md`, `CONNECTORS.md`, `LICENSE`, `docs/` except development material) | 18 | 0.14 MB |
| Development documentation (`CLAUDE.md`, `project_plan.md`, `architecture.md`, `.gitignore`, `docs/development`, `decisions`, `testing`, `templates`) | 191 | 3.31 MB |
| Tests, including 5 committed M13 evaluation-evidence records under `tests/fixtures/eval_results/` | 136 | 3.24 MB |
| Evaluation material (`evals/`, required by `experimental.evals`) | 102 | 0.26 MB |
| Examples and demo data (`assets/demo-data/`) | 4 | 0.41 MB |
| Scratch, debug or temporary; build or cache; secret or credential-like | **0** | — |

**No accidental artifact is tracked.** In particular:

- no smoke-test trace, JSONL, log, `.pyc`, `__pycache__`, editor file or `.env*`;
- no session or account artifact;
- nothing under `evals/results/`.

Nothing was removed.

**Local, ignored, and not part of a marketplace install:**

- `__pycache__/` directories;
- `evals/results/` (3.3 MB of local evaluation run output, ignored by `.gitignore`);
- `.claude/settings.local.json` and `.claude/.cc-writes/`, this machine's Claude Code settings. These are ignored by the
  user's **global** git ignore, not by the repository's.

A `--plugin-dir` load of this particular working copy would see them. A clone would not.

**Development material ships.** `docs/`, `tests/` and `evals/` are included, and this is inherent to `source: ./`. The
repository establishes no exclusion mechanism, and none was invented. This is the standing packaging owner decision.

**Hygiene recommendation (owner choice, not applied).** Add `.claude/settings.local.json` to the repository's own
`.gitignore`, so that a contributor without that global rule cannot commit local settings.

## 6. Git and release history

| Commit | Parent | Content |
|---|---|---|
| `57e92fa` | `8e4ab17` | M14: complete documentation, remediation, and release validation (M14-4 to M14-6) |
| `8e4ab17` | `5c1b15d` | M14.3: reconcile component documentation |
| `5c1b15d` | `50d1f0e` | M14.2: redesign product README |
| `50d1f0e` | `595e910` | M14.1: reconcile milestone and governance documentation |
| `595e910` | — | `origin/main`, M13 remediation |

These four local commits are the release-candidate history. Branch `main`; no tags; nothing untracked at the start. No
history was changed.

## 7. Release notes and documentation consistency

**Release notes.** No changelog or release-note convention exists, and the governance does not require one:

- `CLAUDE.md` §13 gates a tag or release behind owner approval, and names no artifact;
- the M14 scope in `project_plan.md` lists release tagging, not release notes.

So none was created. Release notes are a decision for the owner at release time.

**Consistency.** These sources were cross-checked:

- `README.md`, `architecture.md`, `project_plan.md`;
- the manifests;
- the three ADR indexes (ADR-0052 and ADR-0053 are in all three);
- the development index (all records through M14-6);
- the defect register.

They agree on:

- **inventory:** 18 user-facing commands, 1 internal harness, 16 skills, 2 subagents;
- **external research:** all four commands live-verified and `COMPLETED`;
- **connectors:** the registry is empty by design;
- **release status:** not released, not tagged;
- **known limitations.**

**One stale current-facing area, corrected.** `project_plan.md` still described M14-4 to M14-6 (and the M14-1 to M14-3
rows) as "uncommitted" or `REVIEW`. That affected:

- the current-phase line, the next gate and the M14 summary row;
- the six M14 item rows, which are now `COMPLETED` with their checkpoint SHAs: `50d1f0e`, `5c1b15d`, `8e4ab17` and
  `57e92fa`;
- the resolution notes of the items fixed in M14: R-13, R-15, R-16, M13-DEF-01, M13-DEF-03, the M9 command rows, D-10,
  D-13 and D-14.

**One broken link, corrected.** The repository-wide link check (206 files, 606 links) found `CONNECTORS.md` pointing at
`README.md#file-first-by-design`. That heading was removed by the M14-2 README redesign (`5c1b15d`). The link now points
at `README.md#data-sources-and-connectors`, where the four-tier Excel reader is described.

**Not changed:**

- M14 stays `IN PROGRESS`, because release tagging is `PLANNED`, and OWNER RELEASE APPROVAL REQUIRED;
- dated history bullets and the defect register's historically framed "uncommitted at recording" notes.

## 8. Validation

- **Full regression** (`python3 tests/run_tests.py`): `Ran 5324 tests in 551.643s`, `OK (skipped=31)`,
  `ran 5324 | failures 0 | errors 0 | skipped 31`, exit 0.
- **After the `CONNECTORS.md` link fix:** the 10 modules that read documentation, `project_plan.md` or `CONNECTORS.md`
  were re-run: 395 tests, OK.
- **`claude plugin validate . --strict`:** passed.
- **Links:** 206 documentation files, 606 links. The one pre-existing broken anchor was fixed (§7), and every other link
  resolves.
- **`git diff --check`:** clean.
- **Tree:** 3 files modified (`project_plan.md`, `CONNECTORS.md`, `docs/development/README.md`) and 1 new (this record),
  all uncommitted. HEAD is `57e92fa`.

## 9. Remaining owner decisions

1. **OWNER RELEASE APPROVAL REQUIRED:** push, tag (proposed `v0.1.0` for version `0.1.0`), GitHub release and marketplace
   publication.
2. The tag name format, since no convention exists.
3. Whether release notes accompany the release.
4. Packaging: accept that development material ships, or restructure.
5. The token-cost overrun: ~7,260 always-on against the ≤ 3,000 target.
6. M13-DEF-14, -15 and -16: accept as known model-behaviour limitations, or schedule remediation.
7. D-13 and D-07.
8. M9 rows outside M14: the `biq-external-research` skill and three tier-test rows (M9 stays `IN PROGRESS`).
9. Optionally: a retention rule for reply captures (ADR-0053), and the `.gitignore` hygiene entry (§5).

## 10. Git reference

- No commit, tag, push or publication.
- The `project_plan.md` correction and this record are uncommitted.
- HEAD remains `57e92fa`.
