# ADR-0057 — One public repository holds the source and the built package

**Date:** 2026-10-01
**Status:** Accepted — 2026-10-01, by the project owner. Amends
[ADR-0055](ADR-0055-distribution-package-built-from-an-allowlist.md) in one respect: where the built package is
published. The build itself is unchanged.
**Deciders:** Project owner (Prakash Meghani - Concept Web World)

## Context

ADR-0055 builds the installable package from an allowlist into `dist/businessops/` and expected it to be published to
a separate distribution repository. A name was chosen (`BusinessOps-Plugin`), but no such repository was created.

Anthropic's *Submit your plugin* page (read 2026-10-01): "The repository doesn't have to be dedicated to the plugin.
If the plugin is one folder in a larger repository, give that folder as the plugin path; the directory reads and
scans only that folder." The pre-submission checklist applies stricter rules to a plugin in a subfolder:

- hook and MCP command paths must be written in full from `${CLAUDE_PLUGIN_ROOT}` (blocks otherwise);
- scripts that a hook or MCP server runs must not use other shell variables, command substitutions or calls to other
  plugin files (held for a reviewer otherwise).

## Problem

Where do the reviewable source and the installable package live?

## Options considered

### Option A — A separate distribution repository (ADR-0055 as written)

Pros: the plugin sits at a repository root, which avoids the subfolder rules. Cons: two repositories to keep in step,
and reviewers see the package apart from the tests, decisions and evidence behind it.

### Option B — One public repository; the package committed under `dist/businessops/`

Pros: one place for the source, tests, security controls, decisions, evidence and the exact package that is
submitted, with one history. Cons: the package is a subfolder, so its hook and MCP scripts are expected to be held for
a reviewer ("Scripts the validator couldn't follow").

## Decision

Option B. <https://github.com/conceptwebworld26/BusinessOps> is the only repository. It is both the reviewable source
repository and the home of the validated package:

- the package is built by `scripts/build_distribution.py` into `dist/businessops/` and committed. `.gitignore` ignores
  everything else under `dist/` (`/dist/*` with `!/dist/businessops/`);
- a submission names the plugin path `dist/businessops`;
- the packaged manifests keep the source's `homepage` and `repository`, the BusinessOps repository;
- `tests/unit/test_distribution_build.py` asserts that the committed package equals a fresh build, so it cannot drift
  from its source.

No `BusinessOps-Plugin` repository is created.

## Reason

The owner prefers one reviewable public repository: Anthropic can review the shipped package together with the
source, tests, security controls and records it was built and validated from. Anthropic's documentation supports a
plugin in a repository subfolder.

## Consequences

**Positive** — one repository and one history; the submitted package is visible beside its source and evidence.

**Negative** — submissions from the subfolder are expected to be held for a reviewer over the hook and MCP scripts
(`hooks/bops_guard.sh`, `lib/bops_run.sh`), in addition to the `sh`-launched MCP server hold (BOPS-R10). Each release
must rebuild and commit `dist/businessops/`; the drift test enforces it.

**Follow-up required** — the README's self-hosted install (`claude plugin marketplace add
conceptwebworld26/BusinessOps`) uses the repository root's marketplace entry (`"source": "./"`), so it installs the
development tree, not `dist/businessops/`. This is an owner decision, recorded as BOPS-R18.
