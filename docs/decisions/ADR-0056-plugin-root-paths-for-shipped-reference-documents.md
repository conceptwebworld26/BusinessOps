# ADR-0056 — Commands and skills name the shipped reference documents by their plugin-root path

**Date:** 2026-09-30
**Status:** Accepted — 2026-09-30, by the project owner (the Milestone 3.1 review, confirmed in the BusinessOps
Milestone 4A prompt). Implemented in Milestone 3.1, which directed that the smallest correct fix be made if a live
test proved the relative paths broken. Amends
[ADR-0042](ADR-0042-plugin-root-anchored-isolated-engine-entry.md) in one respect only.
**Deciders:** Project owner (Prakash Meghani - Concept Web World)

## Context

Commands and skills tell Claude to read the policy documents in `reference/`, for example "Read
`reference/analysis-framework.md`". There are 76 such mentions in 24 files. Every recorded development run started
Claude Code in the repository root, where that relative path happens to resolve.

BusinessOps Milestone 3.1 tested an installed-style plugin. The built package was copied outside the development
repository and loaded with `claude --plugin-dir`, and headless sessions ran from a separate project directory:

- **Command.** `/businessops:business-health` read `reference/analysis-framework.md` against the working directory:
  `<project>\reference\analysis-framework.md`, "File does not exist".
- **Skill.** `businessops:bops-competitor-analysis` loaded with "Base directory for this skill: …\skills\
  bops-competitor-analysis". Claude read `reference/ambiguity-protocol.md` against that directory:
  `…\skills\bops-competitor-analysis\reference\ambiguity-protocol.md`, "File does not exist".
- A normal, undirected run of `/businessops:business-health` did not attempt the reads at all.

Anthropic's skills documentation (read 2026-09-30) says `${CLAUDE_SKILL_DIR}` is "the skill's subdirectory within the
plugin, not the plugin root". It names `${CLAUDE_PLUGIN_ROOT}` for "files bundled anywhere in the plugin, including
resources shared between the plugin's skills", and says Claude Code substitutes it in plugin skill content. ADR-0042
records the same substitution for plugin command bodies.

ADR-0042 decision 7 requires every engine-reaching command and skill to use the launcher line and carry "no other
path logic". Its static guard (M13-DEF-04, `tests/unit/test_m13_def04_static_guard.py`, and
`tests/unit/test_m13_def08_runtime_resolver.py`) enforces a broader form: `${CLAUDE_PLUGIN_ROOT}` may appear only in
the launcher line.

## Problem

How can a command or skill name a shared reference document so that it resolves in an installed plugin, without
opening a second way into the engine?

## Options considered

### Option A — Keep relative paths

Proven broken in an installed plugin.

### Option B — Paths relative to the skill directory (`../../reference/…`)

Works for skills, which receive a base directory. Plugin commands do not receive one, so their reads would still
resolve against the user's working directory. This also depends on the model resolving a relative path correctly.

### Option C — `${CLAUDE_PLUGIN_ROOT}/reference/<file>.md`, with a narrow amendment to the guard

The documented mechanism. It works the same way for commands and skills.

## Decision

Option C. Commands and skills write each reference as `` `${CLAUDE_PLUGIN_ROOT}/reference/<file>.md` ``. ADR-0042's
invariant is amended by exactly this one form:

- the token is backticked, names a file that exists in `reference/`, and appears in prose, never in a code block;
- the check removes such tokens from a line before applying the original rule, so any other `${CLAUDE_PLUGIN_ROOT}`
  on that line must still be the launcher line;
- nothing else changes: one launcher, the byte-identical launcher line, no `sys.path` logic, no environment lookup,
  and `bops` imported only inside launcher blocks.

A new test asserts that every reference token names a shipped document and that none sits in a code block.

## Reason

The live test proved the relative form broken for both commands and skills. Option C is the documented mechanism and
the only one that works for both. The amendment names a file to read. It cannot run code, change the engine's import
boundary, or reach the engine another way, and every original prohibition is still enforced.

## Consequences

**Positive** — commands and skills can read their policy documents in an installed plugin (verified live, 2026-09-30).
`scripts/build_distribution.py` already fails a build that names a `${CLAUDE_PLUGIN_ROOT}` path the package does not
contain.

**Negative** — the static guard is no longer the single rule "plugin root only in the launcher line". It is now that
rule plus one exception that is checked separately.

**Follow-up required** — none.
