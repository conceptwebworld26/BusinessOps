# ADR-0055 — The installable package is built from an allowlist into its own plugin root

**Date:** 2026-09-30
**Status:** Accepted — 2026-09-30, by the project owner (the Milestone 3 review, confirmed in the BusinessOps
Milestone 4A prompt). The owner set the direction in the BusinessOps Milestone 3 prompt: keep this
repository as the complete development repository, and ship a separate distribution with the plugin root at its
root. The mechanism below was chosen and implemented in Milestone 3.
**Deciders:** Project owner (Prakash Meghani - Concept Web World)

## Context

Anthropic's directory reads a plugin from a GitHub repository folder, and "people who install the plugin get only
the plugin folder" (plugin pre-submission checklist, read 2026-09-30). This repository's plugin folder was its root,
so every install carried the tests, evals, development history, decision records and tooling: 639 files, 9.75 MB.
The checklist holds a version for a reviewer at more than 512 files, at a non-image file over 256 KiB, and at a
non-image binary; the repository met all three. The checklist also applies stricter script checks to a plugin in a
repository subfolder than to one at a repository root.

A trace of what the plugin reads at runtime (Milestone 3) found:

- commands and skills enter the engine only through `${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh`, and read
  `reference/*.md`;
- the engine reads `config/`, `lib/schemas/` and `.mcp.json`;
- the only runtime read of `docs/` is the connector Gate record in `docs/development/`, used only when a connector
  is declared, and the registry ships empty;
- nothing at runtime reads `tests/`, `evals/`, `CLAUDE.md`, `architecture.md` or `project_plan.md`.

## Problem

How do users receive only the runtime plugin, while this repository keeps its complete history and stays the one
source of truth?

## Options considered

### Option A — Remove developer material from this repository

Pros: one repository. Cons: destroys the development history and tests that this project's governance requires.

### Option B — Move the plugin into a subfolder of this repository

Pros: one repository, one source. Cons: the checklist's stricter subfolder rules would hold the hook and MCP scripts
for a reviewer; every path in the repository would move.

### Option C — Keep a hand-maintained copy of the plugin in a distribution folder or repository

Pros: a clean root. Cons: two copies of every runtime file, which drift apart.

### Option D — Build the package from an explicit allowlist

Pros: a clean plugin root; one source for every file; a build that fails when a runtime file is missing or when
developer material would ship. Cons: a build step before each release; a published distribution repository must be
refreshed from the build.

## Decision

Option D. `scripts/build_distribution.py` copies an explicit allowlist into `dist/businessops/` (ignored by git),
with the plugin root at the package root:

- shipped: `.claude-plugin/`, `.mcp.json`, `agents/`, `commands/`, `skills/`, `hooks/`, `lib/`, `config/`,
  `reference/`, `README.md`, `LICENSE`, `EULA.md`, `PRIVACY.md`, `CONNECTORS.md`, and the demo dataset as text
  (`assets/demo-data/northwind_sales.csv`, `business_context.json`);
- not shipped: `tests/`, `evals/`, `docs/`, `dev/`, `scripts/`, `.claude/`, `CLAUDE.md`, `architecture.md`,
  `project_plan.md`, the demo-data generator and the `.xlsx` copy of the demo data.

It makes exactly two transformations. `experimental.evals` is removed from the packaged `plugin.json`, because
`evals/` is not shipped. Relative Markdown links to unshipped documents are rewritten to the same file in the
development repository on GitHub. It then checks the package: runtime references, forbidden paths, file sizes,
binaries, symlinks, links and personal paths. `tests/unit/test_distribution_build.py` enforces the boundary.

The internal M9-B harness moved from `commands/` to `dev/harness/`, so it is never discovered or shipped.

## Reason

The directory installs exactly one plugin folder. Building that folder from the development repository keeps one
source for every file and makes the boundary a tested property instead of a manual step. Option B was rejected on
the checklist's own subfolder rules, Option C on drift, and Option A on governance.

## Consequences

**Positive** — the package is 188 files and 2.6 MB with no binary, no file over 256 KiB and no developer material.
Both `claude plugin validate --strict` checks pass on it, including the `plugin.json` check that failed on this
repository because of `CLAUDE.md`.

**Negative** — a release needs a build and a refresh of the distribution repository. Connector Gate records in
`docs/development/` are not shipped: if a connector is ever declared, its Gate record needs a shipped home first.

**Follow-up required** — owner decisions: the name of the distribution repository, and the release procedure that
publishes a build to it.
