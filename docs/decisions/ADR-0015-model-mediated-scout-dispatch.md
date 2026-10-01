# ADR-0015 — Scout dispatch is model-mediated, and the orchestration surface is markdown

**Date:** 2026-09-10
**Status:** Accepted
**Relates to:** [ADR-0006](ADR-0006-three-subagents-not-eight.md) (three subagents),
[ADR-0009](ADR-0009-comparative-intelligence-privacy-boundary.md) (the disclosure boundary),
[ADR-0014](ADR-0014-retrieval-agent-ships-with-retrieval.md) (the scout ships with M9).
None is superseded. This decision fixes *how* the boundary those three describe is actually
crossed at runtime, and corrects a manifest convention that prevented it being crossed at all.
**Deciders:** Project owner, Claude (Milestone 9-B completion review)

## Context

M9-B built both Python halves of external retrieval — a `ScoutBrief` that can only be built
from a gate-issued authorisation, and `normalise_records()` that takes untrusted results
back — and joined them with `ScoutTransport`, an injected Python callable that a caller was
expected to supply in production.

No such caller was ever supplied, and the M9-B completion review established why: **there
is no programmatic dispatch API a plugin's Python may call.** A subagent is dispatched by
the orchestrating model through the runtime's Task mechanism. Every alternative was checked
against the installed runtime and rejected — `--agent` and `--agents` are session
configuration, `claude agents` manages background *sessions* rather than subagents, MCP
tools are called by the model, hooks fire from the model's tool use, and a subprocess
shell-out is the thing the boundary exists to prevent.

The first-party evidence is a plugin on the same machine: `feature-dev` ships three agents
and dispatches them from `commands/feature-dev.md` **in prose** — *"Launch 2-3 code-explorer
agents in parallel"*. There is no API call anywhere in it, because there is nothing to call.

A second problem surfaced while testing this. `plugin.json` declared
`"agents": ["./agents/biq-research-scout.md"]`, following the convention recorded in
`architecture.md` that agents must be listed file-by-file. Installing the plugin and running
`claude plugin details businessiq` reported **Agents (0)**. With the key removed, the same
command reported **Agents (1) biq-research-scout**. The manifest validated in both cases.
So the scout did not ship, had never shipped, and nothing in the repository would have said
so — the boundary test asserted the agent's *tool grant*, which is a property of a file, not
of what the runtime loads.

## Decision

**1. The dispatch is model-mediated, and that is the production boundary.**
Python builds the brief and ingests the result. The leg between them is performed by the
model reading an orchestration surface written in markdown. `ScoutTransport` is reclassified
as what it has always been — a **test double** that drives the production normalisation path
from fixtures — and is never a production transport.

**2. The orchestration surface for M9-B is one command, `/retrieval-slice`.**
It is an integration harness, not a research capability: it sequences the gate, one scout
dispatch and one normalisation so the vertical slice can be exercised and audited. It
answers no business question and writes no report. The four research skills (M9-C) and the
four research commands (M9-D) remain deferred and are the user-facing capability.

**3. The return direction is a named, versioned envelope.**
`biq.scout.result/1`, defined in `agents/biq-research-scout.md` and parsed by
`scout.parse_result()`. A test asserts the documented record fields and
`ACCEPTED_RECORD_FIELDS` are the same vocabulary, because they were written independently
and a documented field that ingestion drops is a silent data loss.

**4. Agents are auto-discovered. `plugin.json` must not declare them.**
Measured, not assumed. A test now asserts the key's absence and records the measurement.

## Consequences

**The capability separation stops being a claim about a file.** Because Python cannot reach
a web tool and cannot dispatch a subagent, the component holding file access and the
component holding web access are separated by the runtime rather than by discipline. A
programmatic dispatch API would be the thing to argue against, not the thing to want.

**Markdown is load-bearing.** Step 2 of `/retrieval-slice` is executable instruction, so it
is tested like code: one agent named, brief sent verbatim, dispatched once, gate not re-run
for a better answer. A prose change there is a behaviour change.

**Two checks now exist where one did.** The gate decides what may be asked; the envelope
check decides whether what came back belongs to this retrieval — operation and query text
must echo the brief, which is where "the query is fixed" stops being an instruction the
scout is asked to honour and becomes a property verified on return.

**The four research commands inherit a proven path rather than inventing one.** M9-D
sequences the same three steps behind a user-facing name.

**A cost:** the request parameters are passed twice, because `open_retrieval` and
`close_retrieval` run in separate processes and no authorisation survives between them. The
gate is therefore re-derived rather than handed over. That is the safe direction — there is
no serialised authorisation for a caller to forge — and it is deterministic, so the same
request yields the same brief.

## Alternatives rejected

| Alternative | Why not |
|---|---|
| A Python transport that shells out to `claude -p` | Gives the file-access process a web path; dissolves ADR-0006 and ADR-0014 |
| A Python transport calling an HTTP API | Same, plus a dependency and a credential the repository must never hold |
| Keep `ScoutTransport` and wait for a dispatch API | Waiting for a capability that does not exist is not a plan, and the interface invites someone to satisfy it unsafely |
| Build the four M9-D commands now | The owner deferred them; a harness proves the path without pre-empting that decision |
| Return free prose and parse it | A parser over prose is an injection surface; a named envelope is a contract |
