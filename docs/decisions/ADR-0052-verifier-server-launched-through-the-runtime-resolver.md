# ADR-0052 — The local verifier MCP server is launched through the runtime resolver

**Date:** 2026-09-27
**Status:** Accepted — 2026-09-27, by the project owner. The M14-5 prompt directs that R-13 be fixed where a
portable fix can be implemented "without violating an ADR/security boundary", and the owner authorised updating the
tests that pin the old entry. Subject to owner review of M14-5 as a whole.

- **What acceptance approves.** The written form of one `.mcp.json` entry, one launcher entry mode, and their tests.
  No analytical behaviour, verification rule, tool, argument, envelope or grant changes.
- **Implemented 2026-09-27**, in the same task.

**Deciders:** Project owner (fix directed in the M14-5 prompt). The problem was raised by M14-2 as Known issue R-13.
**Supersedes:** none.
**Amends:** [ADR-0035](ADR-0035-m11-blind-recomputation-boundary.md) §3, **in part**: the *command and arguments*
that declare `biq-verifier` in `.mcp.json`, and nothing else. The server's identity, its one tool, its closed input and
envelope, its silence on stderr, its Connector-gate approval (`CLAUDE.md` §13) and the agent's single-tool grant are
unchanged. ADR-0035's text and status line are not edited, following the practice of ADR-0043 and ADR-0045.
**Relates to:** ADR-0042 (the launcher and its import boundary), ADR-0045 (the resolver), ADR-0046 (WSL rule), ADR-0051
(the hooks already enter the engine this way), R-13.

## Context

ADR-0035 declared the server with "server identity only (`type`, `command`, `args`; no token)":

```json
{"type": "stdio", "command": "python",
 "args": ["${CLAUDE_PLUGIN_ROOT}/lib/python/biq/verification_server.py"]}
```

ADR-0045 then established that no BusinessIQ component names an interpreter. `lib/biq_run.sh` resolves `python`, then
`python3`, checks the version contract under `-I`, and hands off to the ADR-0042 launcher. Every command and skill, and
since ADR-0051 the hooks, enter the engine that way. The verifier entry predates ADR-0045 and was never migrated.

The consequence was observed directly. On this WSL2 host, which provides only `/usr/bin/python3`, Claude Code reported
`biq-verifier (ENOENT): "Executable not found in $PATH: python"`, so `--final` verification could not run (R-13).

## Problem

How should the verifier server be declared so that it starts wherever the rest of the engine starts, without an
absolute path, an environment-specific assumption or a weaker boundary?

## Options considered

### Option A — Replace `python` with `python3`

This moves the failure rather than removing it: hosts that provide only `python`, or only a Windows interpreter under
Git Bash, stop working instead. It repeats the choice ADR-0045 rejected for commands.

### Option B — Launch through the resolver with a dedicated launcher entry (chosen)

`"command": "sh", "args": ["${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh", "--verifier"]`. `lib/python/biq_run.py` gains an
exact `--verifier` mode. It runs the same layout check and import boundary as `-c` and `--guard`, then calls
`biq.verification_server.main()`. It runs no caller-supplied code and takes no argument.

### Option C — Route the server through `-c` with inline code

This works, but it puts executable text in `.mcp.json`, and it installs the engine write guard on a process that has
never had it. Option B keeps the declaration identity-only, and keeps the server's runtime behaviour exactly as it was.

## Decision

Option B.

## Reason

- **One interpreter choice, consistent with ADR-0045.** The same resolver, candidate order, version probe, WSL rule
  and `BIQ_PYTHON` override apply to the verifier as to everything else.
- **No absolute path.** The platform substitutes `${CLAUDE_PLUGIN_ROOT}` in `args` exactly as it did before.
- **No new dependency.** `sh` is already required: `README.md` *Quick start*, and every command and hook.
- **The boundary is stronger, not weaker.** The server now starts under `python -I`, behind the launcher's layout check
  and the verified `biq` origin, which the bare script path did not have. The declaration still carries identity
  only, with no token, header or environment. The connector-security tests that enforce that property pass unchanged
  in substance: they compare against the new approved entry.

## Consequences

**Positive**

- `--final` works on a host with only `python3`. Verified on 2026-09-27 on the host that exhibited R-13:
  `claude --plugin-dir <repo> mcp list`, run outside the repository, reported
  `plugin:businessiq:biq-verifier … ✔ Connected`.
- `tests/unit/test_m11_verification_server.py::DeclaredEntry` starts the server exactly as declared, on a `PATH`
  holding only a `python3`, and completes a real recomputation.

**Negative**

- A resolver failure (no usable Python) now prints the resolver's own actionable message on stderr before the server
  exits, where the old entry failed silently with `ENOENT`. The message names no path, value or environment content.

**Follow-up required**

- Index in `docs/decisions/README.md`, `docs/README.md` and `architecture.md` §19 (done in the same task).
- R-13 is recorded as resolved in `project_plan.md`.

## Revisit when

- The platform offers a supported way to declare a plugin MCP server with an interpreter it resolves itself.
- `sh` ceases to be a BusinessIQ prerequisite.
