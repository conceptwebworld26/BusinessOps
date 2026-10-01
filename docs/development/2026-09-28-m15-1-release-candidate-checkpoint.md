# 2026-09-28 — M15-1: 0.1.0 release-candidate checkpoint

**Milestone:** 14 — Documentation & Release (release-candidate preparation)
**Status on completion:** checkpointed locally as "M15: prepare 0.1.0 release candidate". **BusinessIQ 0.1.0 is a release
candidate, not released.** OWNER RELEASE APPROVAL REQUIRED for the push, tag and publication.
**Supersedes:** In part, `2026-09-28-m15-release-preparation-audit.md` §9: the owner decisions listed there as open are
now decided. That record is not edited.

## 1. Prompt / task performed

"M15-1 — Final Release-Candidate Checkpoint". The owner:

- recorded the decisions for 0.1.0 (§2);
- asked for the four M15 files to be reviewed and kept;
- asked for a narrow `.gitignore` entry for `.claude/settings.local.json`;
- asked for concise 0.1.0 release notes, with current-facing links to them;
- asked for full validation and an artifact audit;
- asked for one local checkpoint commit.

Excluded: push, tag, GitHub release, marketplace publication, history rewriting and paid evaluations.

## 2. Owner decisions for 0.1.0

| Decision | Recorded where |
|---|---|
| Release version `0.1.0`; proposed tag `v0.1.0` | `project_plan.md` (release-tagging row, next gate), release notes |
| M13-DEF-14, -15 and -16 accepted as known model-behaviour limitations for 0.1.0; they stay `open` in the register | `project_plan.md` *Known issues*, release notes |
| The ≤ 3,000 always-on target is kept; the ~7,260 measurement is documented honestly | `project_plan.md` (token row), release notes |
| Whole-repository marketplace packaging accepted for 0.1.0, and not restructured | `project_plan.md` (packaging row), release notes |
| M9's remaining rows stay `IN PROGRESS`; D-13 and D-07 stay open | Unchanged in `project_plan.md`; release notes |
| No paid evaluation; saved-scout-reply pruning (ADR-0053 follow-up) deferred | This record |
| `.gitignore` protection for `.claude/settings.local.json` | `.gitignore` |

## 3. Work

- **The four M15 files, reviewed and kept.**
  - `project_plan.md` cites the M14 checkpoints `50d1f0e`, `5c1b15d`, `8e4ab17` and `57e92fa`; each resolves to a
    commit.
  - `CONNECTORS.md` carries the corrected anchor.
  - The development index lists every dated record, with none unlisted and none dangling.
  - The M15 audit record is accurate as of the audit.
- **`.gitignore`.** One line, `.claude/settings.local.json`, in the existing *Editors and OS* section. It is anchored to
  the repository root. Verified with the global excludes disabled: that file is ignored, another `.claude/` file is
  not, and no `.claude/` file was tracked.
- **Release notes.** No changelog convention exists, so the smallest fit is a new `docs/releases/` directory, registered
  in `docs/README.md`'s directory map as `<version>.md`, holding `docs/releases/0.1.0.md`. It summarises the shipped
  capabilities and the known limitations, and states throughout that 0.1.0 is a release candidate. The figures it quotes
  come from the repository:
  - 28 KPIs (`kpi.registry`);
  - 5 forecast methods and 3 anomaly detectors;
  - 18 commands, 16 skills and 2 subagents;
  - ~7,260 tokens always-on;
  - 633 files and about 9.7 MB.
- **Current-facing links.** The release notes are linked from `README.md` (the documentation table and *Current status*)
  and from `docs/README.md`.
- **Governance.** `project_plan.md` gained the decisions (§2), a dated M15-1 bullet, and a current-phase line and next
  gate that name the remaining owner actions. This record was added, with its row in the development index.

No source, test, configuration, manifest, hook, schema, ADR or historical record changed.

## 4. Validation

See the task report for:

- the full regression;
- strict validation;
- the link check;
- `git diff --check`;
- the artifact audit;
- the final diff review.

## 5. Remaining actions for the actual release

Each needs the owner's explicit approval (`CLAUDE.md` §13), as its own action:

1. Push `main` to `origin`.
2. Create the tag `v0.1.0` on the release-candidate commit, and push it.
3. Optionally, create a GitHub release from `docs/releases/0.1.0.md`.
4. Optionally, publish through the marketplace entry (`.claude-plugin/marketplace.json`).
5. Afterwards, record the release in `project_plan.md` and a dated record, and change the release notes' status from
   release candidate to released.

## 6. Git reference

This work is committed as the local checkpoint "M15: prepare 0.1.0 release candidate", on top of `57e92fa`. It is not
pushed, and not tagged.
