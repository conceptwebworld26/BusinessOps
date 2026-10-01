# ADR-0054 — BusinessOps product identity and the `bops` technical namespace

**Date:** 2026-09-30
**Status:** Accepted — 2026-09-30, by the project owner. The names were set by the owner in the BusinessOps
Milestone 1 prompt and implemented the same day; this record was written in Milestone 2, after the fact, so that the
decision has a home. Subject to owner review of Milestone 2.
**Deciders:** Project owner (Prakash Meghani - Concept Web World)

## Context

This repository began as a restored copy of the BusinessIQ codebase in a fresh git repository with no history. It is to
become a separate product, BusinessOps, submitted to Anthropic's plugin directory. In the BusinessIQ code the product
identity is load-bearing, not cosmetic (verified in the 2026-09-30 migration audit):

- the engine launcher refuses to run unless `.claude-plugin/plugin.json` names the expected plugin;
- the write guard recognises the plugin's own skills, commands and agents by the `<plugin>:` prefix;
- the research handback keys on the plugin-qualified scout agent name;
- Claude Code derives the verifier's MCP tool name from the plugin name
  (`mcp__plugin_<plugin>_<server>__<tool>`);
- runtime state, output and approval-store locations carry the product name.

Anthropic's marketplace reference describes a published plugin `name` as an immutable slug: renaming it after
publication breaks existing installs. BusinessIQ was never published under this repository, so the rename costs nothing
for existing users now, and would cost them their installs later.

## Problem

Which identifiers does the new product use, and is the historical record rewritten to match?

## Options considered

### Option A — Keep the BusinessIQ identifiers, change only the display name

Pros: no code change. Cons: ships another product's name as the permanent install slug and in every user-visible
path, approval code and error message; contradicts the product being independent.

### Option B — Rename the product identity only (`businessiq` → `businessops`), keep the `biq` prefix

Pros: smaller change. Cons: `biq` is an abbreviation of BusinessIQ and is user-visible in skill names
(`businessops:biq-swot`), agent names, the MCP server name and environment variables.

### Option C — Rename identity and prefix together, keep history unchanged

Pros: one consistent identity; history stays true. Cons: larger change, and a historical fixture's case ids no longer
equal the suite's.

## Decision

Option C.

- Display name **BusinessOps**; plugin and marketplace identifier **`businessops`**; install id
  `businessops@businessops`.
- Technical prefix **`bops`**: package `lib/python/bops/`, launchers `bops_run.py` and `bops_run.sh`, guard
  `bops_guard.sh`, skills `bops-*`, agents `bops-*`, MCP server `bops-verifier` (tool
  `mcp__plugin_businessops_bops-verifier__recompute`), variables `BOPS_*` and `BUSINESSOPS_LIVE_SMOKE`, approval codes
  `BOPS-W-…`, scout protocol markers `BOPS-REC` / `BOPS-END`.
- Runtime state `./.businessops/`, output `./businessops-output/`, user state `~/.claude/businessops/`.
- Rights holder **Prakash Meghani - Concept Web World**.
- **History is not rewritten.** `docs/development/`, `docs/decisions/` (including
  [ADR-0045](ADR-0045-businessiq-owned-portable-runtime-resolution.md), whose title and filename keep their original
  wording) and the SHA-256 pinned fixtures under `tests/fixtures/eval_results/` and `tests/fixtures/eval_inputs/` keep
  the BusinessIQ names. Current documents carry a lineage note instead.

## Reason

The identifiers are load-bearing and become permanent at publication, so they are settled before the first commit and
the first submission. Renaming the prefix in the same change avoids a second migration touching the same files.
Rewriting history would make dated records claim that BusinessOps did things that were done, and measured, under
another name.

## Consequences

**Positive** — one consistent identity in code, manifests, tests and current documentation; `claude plugin validate .
--strict` passes; the test suite's result is unchanged by the migration (2026-09-30 record).

**Negative** — a search for "BusinessIQ" still finds the historical records by design. One test translates recorded
routing case ids (`-biq-` → `-bops-`) when comparing a pinned fixture with the suite. Any local BusinessIQ state under
`~/.claude/businessiq/` is no longer read.

**Follow-up required** — none for the identity itself. The name must not change after publication; a later rename
would need the marketplace `renames` mechanism.

See `docs/development/2026-09-30-businessops-m1-identity-migration.md`.
