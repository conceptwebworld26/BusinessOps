# ADR-0053 — The scout's reply reaches the engine through a harness capture, never a model copy

**Date:** 2026-09-27
**Status:** Accepted — 2026-09-27, by the project owner. The M14-6 prompt requires the scout's reply to reach the
parser verbatim (M9 criterion 5), and authorises "the minimum safe change" at implementation level where skill wording
alone cannot achieve that. Subject to owner review of M14-6 as a whole.

- **What acceptance approves.** One `PostToolUse` hook entry, one exact launcher mode, one capture module, the
  classifier rule that keeps both harness-only, and the matching skill instructions. The line protocol (ADR-0017), the
  parser, tiering, the disclosure gate and the scout's tool grant are unchanged.
- **Implemented 2026-09-27**, in the same task.

**Deciders:** Project owner (the verbatim requirement and its definition, M14-6 prompt).
**Supersedes:** none.
**Amends:** [ADR-0017](ADR-0017-operation-bound-line-records.md) and `architecture.md` §10, **in part**: the *carrier*
of the scout's reply between the dispatch and `close_retrieval()`. Until now the orchestrating model wrote it to the
scratchpad. Now the harness-run hook captures it. ADR-0017's text and status are not edited.
**Relates to:** ADR-0014 and ADR-0015 (the scout and its dispatch), ADR-0051 (the write guard, whose store and
harness-only entries this reuses), ADR-0052 (the resolver route every entry takes), M9 criterion 5 (M9-D.1 record §15).

## Context

`architecture.md` §10: "the orchestration surface writes the scout's reply to the scratchpad and hands it to
`close_retrieval()` unedited, because extracting or repairing it would move authorship to the one context that can read
business data." M9 criterion 5 checks exactly this. Three live measurements, all on 2026-09-27 and all in fresh
`claude -p --plugin-dir` sessions:

1. **M14-5.** The skills said only "feed the scout's reply text". All three completed runs wrote just the de-indented
   protocol lines. Parsed records were identical, but the text was extracted.
2. **M14-6, skill wording only.** The skills were told to write the `Agent` tool result "exactly as you received it".
   All four runs then copied the whole framed result: the harness preamble, the indentation, the prose and the footer.
   Every non-whitespace character matched, yet each run turned every whitespace-only line into an empty line and added
   a final newline. It was a byte-level mismatch in 4 of 4 runs.
3. **A probe plugin** (scratchpad only) measured what a `PostToolUse` hook receives for an `Agent` call:
   - `tool_response.content` holds the subagent's own reply, before the harness frames and indents it;
   - `tool_input.prompt` holds the brief, and therefore the `operation`;
   - `session_id` and `tool_use_id` are also present.

A model regenerating text is not a verbatim channel. The harness already holds the exact text.

## Problem

How can the scout's reply reach the parser byte for byte, without a model in the path, and without creating a way to
forge a reply?

## Options considered

### Option A — Stronger wording only

This was measured, and it failed on whitespace in 4 of 4 runs. No wording removes the regeneration step.

### Option B — Capture in a `PostToolUse` hook, read by the engine (chosen)

The hook, run by the harness, stores `tool_response.content` for scout dispatches, keyed by the brief's operation.
`close_retrieval()` is given `R.handback_reply('<operation>')`.

### Option C — Let the scout write its own reply to a file

Rejected. The scout's grant is `WebSearch` and `WebFetch` only. That grant is the structural privacy boundary
(ADR-0006, ADR-0014), and giving it file access to fix a transcription problem would break it.

## Decision

Option B:

- **`hooks/hooks.json`** gains
  `PostToolUse` → matcher `Agent|Task` → `sh "${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh" --handback`.
- **`lib/python/biq_run.py`** gains an exact `--handback` mode. It runs behind the usual layout check and import
  boundary, runs no caller code and takes no argument.
- **`lib/python/biq/research/handback.py`:**
  - `capture()` acts only on a `PostToolUse` for `Agent` or `Task` with `subagent_type` `businessiq:biq-research-scout`
    and a JSON brief naming an operation id that matches `^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$`;
  - it joins the text blocks unchanged and writes UTF-8 with `newline=""` through a temporary file and an atomic
    rename;
  - `reply()` reads the capture back with `newline=""`, and raises `HandbackError` when none exists;
  - `main()` always exits 0, so a failed capture never disturbs the session and the retrieval fails closed instead.
- **The store** is `~/.claude/businessiq/guard/handback/`, inside the write guard's root, which every tool call is
  refused.
- **`writeguard/classify.py`** treats `--handback` like `--guard`, as a harness-only entry that is prohibited from any
  tool call.
- **The six skills that close a retrieval** now close inline from `R.handback_reply('<operation>')` and are told never to
  copy, write or retype the reply, and to report a failed retrieval if no capture exists.

## Reason

- **Verbatim by construction.** No model regenerates the text. What the parser reads is what the scout returned, with
  no frame, no indentation, no trimming and no line-ending translation.
- **Unforgeable from the session.** Only the harness-run hook writes the store. A tool call that writes there, or that
  invokes `--handback`, is refused with no approval path. This reuses the protections ADR-0051 already gives the
  approval store.
- **Smallest change that works.** The protocol, parser, gate, tiering and scout grant are untouched. The hook is a
  transport, and it decides nothing.

## Consequences

**Positive**

- M9 criterion 5 can now be met exactly, and it is checked by comparing texts, not parsed records.
- The model has one fewer transcription step, so its context carries less untrusted text.
- The failure mode is fail-closed: with no capture, the retrieval is reported as failed.

**Negative**

- The capture depends on the platform running plugin hooks. Where hooks are disabled, research retrievals fail
  closed.
- The latest dispatch for an operation replaces an earlier capture. A retrieval is dispatched once (ADR-0017), so a
  repeated id means the same retrieval was asked for again.
- Captures accumulate under the guard root. They are small, untrusted, text-only and hold no business data, but
  nothing prunes them yet.

**Follow-up required**

- Index in `docs/decisions/README.md`, `docs/README.md` and `architecture.md` §19; update `architecture.md` §2 and §10
  (done in the same task).
- Live verification of criterion 5 under this design: recorded in
  `docs/development/2026-09-27-m14-6-m9-smoke-protocol-remediation.md`.
- Owner option: a retention rule for old captures.

## Revisit when

- The platform offers the orchestrating model a way to pass a tool result on unchanged.
- The `PostToolUse` payload shape for `Agent` changes.
