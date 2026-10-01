# ADR-0001 — Claude Code plugin as the delivery platform

**Date:** 2026-09-08
**Status:** Accepted
**Deciders:** Project owner, Claude (architecture gate)

## Context

BusinessIQ is specified as "a Claude plugin". Before designing against that, the actual
platform and its real conventions were probed on this machine rather than assumed.

Verified facts (Claude Code 2.1.263, Windows 11):

- Plugin manifest lives at `.claude-plugin/plugin.json`; schema
  `https://anthropic.com/claude-code/plugin.schema.json`.
- `claude plugin validate <path> --strict` exists and enforces the schema.
- `commands/`, `skills/<name>/SKILL.md`, `.mcp.json` and `hooks/hooks.json` are
  auto-discovered from conventional directories — omitting them from the manifest works and
  passes `--strict`.
- `agents` **must** be listed as individual `.md` file paths. `"agents": ["./agents"]` fails
  validation with `agents.0: Invalid input`. Verified by direct experiment.
- `experimental.evals` is an accepted manifest field pointing at an eval-suite directory.
- Supported frontmatter, surveyed across four installed plugins:
  skills — `name`, `description`, `argument-hint`, `user-invocable`;
  commands — `description`, `argument-hint`, `allowed-tools`, `disable-model-invocation`,
  `hide-from-slash-command-tool`; agents — `name`, `description`, `tools`, `model`, `color`.
- `claude plugin details <name>` reports per-component always-on and on-invoke token cost.
  Measured: `marketing` ~872 tok always-on for 8 skills; `code-review` ~20 tok for 1
  command; `feature-dev` ~238 tok for 1 command + 3 agents.
- A repo can ship `.claude-plugin/marketplace.json` and be installed directly from GitHub
  (the `superpowers` plugin does exactly this).

## Problem

Which delivery mechanism should BusinessIQ use, and which platform features may the
architecture rely on?

## Options considered

### Option A — Claude Code plugin using only verified conventions
Uses commands, skills, agents, MCP declarations and the eval hook, all confirmed by probe.
Installs from the existing GitHub repo via a marketplace manifest.

- Pros: matches the requirement; every mechanism verified locally; no invention.
- Cons: constrained by what the platform actually supports; always-on token cost is real.

### Option B — Standalone CLI/service that Claude calls
Full control over runtime and dependencies.

- Pros: unconstrained compute; easy packaging of pandas etc.
- Cons: not a plugin; requires install and hosting; abandons the requirement outright.

### Option C — Plugin plus speculative platform features
Design against hooks, LSP, output styles, channels and eval as if all were available.

- Pros: richer on paper.
- Cons: `claude plugin eval` is **early-access gated on this machine** (verified: exits with
  "plugin eval is currently in early access"). Designing against unavailable features
  produces an architecture that cannot be built or tested.

## Decision

**Option A.** BusinessIQ is a Claude Code plugin using `commands/`, `skills/`, `agents/`,
`.mcp.json` and `.claude-plugin/marketplace.json`. The manifest relies on auto-discovery
for commands, skills, MCP and hooks, and lists agents explicitly by file path. `hooks/` is
deferred until a concrete need appears. `experimental.evals` is declared, with the
early-access limitation recorded openly.

## Reason

Every mechanism in Option A was confirmed by running the real tooling — including the
non-obvious `agents` constraint, which would otherwise have been discovered as a
Milestone-1 failure. Option B discards the stated requirement. Option C would have built
the testing strategy on a feature this account cannot execute.

## Consequences

**Positive** — the skeleton will validate on first attempt; conventions match installed
Anthropic plugins, so the plugin behaves the way users expect; token cost is measurable at
every milestone.

**Negative** — always-on token cost scales with component count, making the 25-skill /
17-command design a real constraint (budget: 4k tokens, see `architecture.md`). Behavioural
evals cannot be executed here.

**Follow-up required** — measure `claude plugin details businessiq` at the end of every
milestone; keep `docs/testing/` records of manually executed behavioural scenarios while
`plugin eval` is unavailable.

## Revisit when

`claude plugin eval` becomes generally available, or the always-on budget is breached and
component consolidation is needed.
