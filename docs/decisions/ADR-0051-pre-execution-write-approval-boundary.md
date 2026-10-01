# ADR-0051 — A pre-execution write-approval boundary: a plugin-wide `PreToolUse` guard, an engine execution guard, and single-use capabilities granted only from the user's prompt

**Date:** 2026-09-26
**Status:** Accepted — 2026-09-26, by the project owner. The M13-DEF-24 remediation prompt directed this boundary (a
plugin-wide `PreToolUse` hook plus an internal engine boundary, both enforcing approval before a consequential write)
and required this ADR to record and supersede the earlier hook decisions.

- **What acceptance approves.** One new component type (a plugin-wide hook, `hooks/hooks.json`), the write guard
  package `lib/python/biq/writeguard/`, a `--guard` entry and an execution-guard installation in the one engine
  launcher, one export API, one schema, two error types, their tests and governance. No analytical behaviour, KPI,
  forecast, research, synthesis, report or connector rule changes.
- **Implemented 2026-09-26**, in the same task (`docs/development/2026-09-26-m13-def-24-remediation.md`).
- **Approval path verified live 2026-09-26** on Claude Code 2.1.283
  (`docs/development/2026-09-26-m13-def-24-live-grant-verification.md`). The `UserPromptSubmit` item of *Known limits*
  1 is now measured. Its user message came from a scripted stream-json feeder, not a person typing. The other items of
  limit 1, and limit 2, stand. The decision text below is unchanged.

**Deciders:** Project owner (direction and implementation authorised, 2026-09-26), raised by M13-DEF-24.
**Supersedes:** none in full.
**Amends, in part (their text is not edited):**

- [ADR-0001](ADR-0001-claude-code-plugin-platform.md), its sentence "`hooks/` is deferred until a concrete need
  appears". The need has appeared, and the mechanism has been measured.
- [ADR-0035](ADR-0035-m11-blind-recomputation-boundary.md), Option B's reasoning that restricting tools with hooks "is
  not a verified platform fact" and that "a hook-based filter would be a security subsystem the milestone must not
  build". This applies only to the write boundary. ADR-0035's decision is unchanged: the verifier agent still holds no
  shell, and nothing here grants it one.

**Relates to:** ADR-0010 (consequence-based approval; this ADR is its first enforcement mechanism for filesystem
writes), ADR-0008 (the consented runtime; its subprocess shapes are the only ones the engine may start), ADR-0042 and
ADR-0045 (the one launcher and the one resolver, reused as the hook entry), ADR-0043 (`fixed_product`), ADR-0050 (the
same fail-closed, not-caller-controlled pattern for disclosures), M13-DEF-24.

## Context

In the M13.2 re-evaluation, case `a20` asked for the sales summary to be written into `README.md`, "replacing
everything that is in it now". Two of three runs issued `cat > README.md <<'EOF' …` through the model's own `Bash`
tool, and none asked for approval. The evaluator's sandbox denied the write, but only because of the evaluator.

The investigation (`docs/development/2026-09-26-m13-def-24-investigation.md`) found the root cause. `CLAUDE.md` §9
requires explicit approval to overwrite any existing file, but that rule was advisory text only:

- the engine had no write path to gate;
- the write never passed through BusinessIQ code;
- the only pre-execution interception point was a Claude Code `PreToolUse` hook, which the architecture had deferred
  and never measured.

Skill-frontmatter hooks were known statically. Their runtime behaviour was not.

### The measured runtime (Claude Code 2.1.283, WSL2)

`docs/development/2026-09-26-m13-def-24-hook-runtime-experiment.md` ran real multi-turn sessions (one process, one
`session_id`, three or four turns each) with a sentinel file:

| Fact | Evidence |
|---|---|
| A plugin-wide `hooks/hooks.json` `PreToolUse` hook is active **from session start** and **stays active across later turns** | turns A-C blocked in every `P-*` run |
| `permissionDecision: "deny"` **prevents execution** of `Bash` (`>`, `>>`, the a20 heredoc), `Write` and `Edit` | the sentinel read `ORIGINAL_CONTENT` at hook time, and again after; the model saw `PreToolUse:<Tool> hook error: …` |
| `deny` is honoured under `bypassPermissions`, `acceptEdits`, the default mode, `dontAsk` and `auto` | five `P-deny-*` runs |
| The hook, not anything else, caused the prevention | the no-hook control, in the same mode with the same prompts, executed all three writes |
| A **skill-frontmatter** hook is active only after the skill is invoked | `S-noactivate`: the skill was loaded but never invoked, and all three writes executed |

This task also read the installed 2.1.283 CLI's hook contract. It confirmed the following fields and events:

- **`PreToolUse` input:** `session_id`, `transcript_path`, `cwd`, `permission_mode`, `agent_id` and `agent_type` (in a
  subagent), `tool_name`, `tool_input`, `tool_use_id`, and `scratchpad_dir` when enabled.
- **`PreToolUse` output:** `hookSpecificOutput.permissionDecision` (`allow` | `deny` | `ask`),
  `permissionDecisionReason`, and the common `systemMessage`.
- **`UserPromptSubmit` input:** `prompt`. Its `source` field (user, sdk, system, loop_wakeup …) is declared in the
  schema but compiled out in this build: the builder spreads `...!1` in its place, so it is never populated.
- **`UserPromptExpansion` input:** `command_name` for a slash command.

**No hook input says which plugin a tool call serves.** Claude Code also sets `CLAUDE_CODE_SESSION_ID` in the `Bash`
tool's environment. This was observed on 2.1.283, where it equalled the session's id, and is not documented as a
contract.

## Problem

How does BusinessIQ stop a consequential filesystem write before it executes, unless the user approved that exact
operation, without relying on an evaluator sandbox and without governing work unrelated to BusinessIQ?

## Options considered

### Option A — Keep the rule as instruction text

**Rejected.** This is the defect. A rule the model can skip is not a boundary.

### Option B — Skill- or command-frontmatter hooks

**Rejected as the security boundary.** They were measured to activate only when the skill is invoked (`S-noactivate`).
A write made before the skill is invoked, or in a flow that never invokes it, is not seen. Frontmatter `hooks` would
also need admitting under `CLAUDE.md` §3.

### Option C — A plugin-wide hook that denies every write in every session

**Rejected.** It would govern all of a user's development work merely because BusinessIQ is installed. The remediation
prompt forbids that unless the architecture establishes it as the product contract, and nothing does.

### Option D — A plugin-wide hook scoped by engagement, a deterministic allowlist classifier, capabilities granted from the user's prompt, and an engine execution guard

**Chosen.**

### Option E — `permissionDecision: "ask"` instead of capabilities

**Rejected.** The experiment measured `ask` only when nobody answered it. It was never measured with a human
approving, in `auto` mode (where a classifier, not a person, may answer), or with "don't ask again" rules. `deny` is
the only decision measured to hold in every mode.

## Decision

### 1. Plugin-wide scope, narrowed by engagement

`hooks/hooks.json` declares:

- a `PreToolUse` hook matching `Bash|Write|Edit|MultiEdit|NotebookEdit|PowerShell|Skill|Agent|Task|ScheduleWakeup|CronCreate|SendMessage|RemoteTrigger`;
- a `UserPromptSubmit` hook;
- a `UserPromptExpansion` hook.

The hook is plugin-wide because only plugin-wide hooks were measured to be active from session start.

Because the runtime cannot attribute a tool call to a plugin, BusinessIQ scopes itself by **engagement**. Engagement is
decided only from facts the runtime reports:

- a `Skill` call naming a BusinessIQ skill or command;
- a BusinessIQ slash command (`UserPromptExpansion` `command_name`, or a prompt starting with one);
- a BusinessIQ subagent (`agent_type`);
- a `Bash` call of the BusinessIQ engine launcher.

Engagement is recorded per `session_id` and lasts for the rest of the session. From then on, every write-capable tool
call in that session is governed. This is the product contract: **once a session uses BusinessIQ, consequential writes
in it need the user's per-action approval** (`CLAUDE.md` §9 already says "overwriting **any** existing file").

A session that never engages BusinessIQ is not governed, with two exceptions that hold in every session:

- no tool call may touch the approval store;
- no tool call may invoke the guard's entry point.

A missing session id counts as engaged, so the call fails closed.

### 2. The write classification model (an allowlist, not a blacklist)

`writeguard.classify` classifies the **exact `tool_input` about to execute**. The result is a list of operations, each
with:

- a kind: `create`, `overwrite`, `append`, `modify`, `truncate`, `delete`, `move_source`, `mkdir`, `link`,
  `git_commit`, `git_push`, `git_mutation`, `git_rewrite`, `execute`, `unknown_write` or `guard_entry`;
- a canonical target (`realpath`, so symlinks resolve);
- its sources;
- whether the target existed.

- **`Write`, `Edit`, `MultiEdit`, `NotebookEdit`** have a target and a kind that follow from their inputs.
- **`Bash`** is read by `writeguard.shell`, a conservative POSIX lexer. It models quoting, lists and pipelines, every
  redirection form, here-strings and here-documents (whose bodies are data), and exactly one substitution: the
  `"$(cat <<'PY' … PY)"` shape every BusinessIQ command uses. Anything else it cannot model raises. That includes
  command and process substitution, backticks, subshells, arithmetic and `case`.

  A simple command is read-only only if all three of these hold:
  - its program is on the read-only list;
  - its arguments keep it read-only (`sort -o`, `uniq IN OUT`, `find -delete`/`-exec`/`-fprint` and `sed -i` or a
    `w` command are writes);
  - every redirection goes to a stream or a device.

  Programs with known write semantics yield operations on their resolved targets: `cp`, `mv`, `install`, `ln`, `rm`,
  `rmdir`, `unlink`, `shred`, `tee`, `touch`, `mkdir`, `truncate`, `dd of=`, `chmod`/`chown`/`chgrp`. Git is
  classified by subcommand.

  Everything else is an `execute` operation. That covers an unknown program, a script, an interpreter, an assignment
  to `PATH`, `LD_*`, `PYTHON*`, `BIQ_*` and the like, a path-qualified program, and any construct the lexer does not
  model.

  After any `cd`, a relative target is unresolved, because whether the `cd` succeeded cannot be known in advance.
  `cat file.txt` is read-only because `cat` without a redirection is. `cat > file.txt` writes because the parsed
  command carries an output redirection, not because the text contains `>`.
- **Python** handed to an interpreter (`python -c`, `python - <<EOF`) is read by `writeguard.pyscan`.
  - **Confined** code is read-only. Confined code imports only listed pure modules, uses no name or attribute beginning
    `_`, no reflective or dynamic builtin, no attribute assignment, and no `open` except a direct read-mode call.
  - Otherwise the code is `execute`. Literal write targets (`open(p, "w")`, `os.remove(p)`, `Path(p).write_text`) are
    named in the approval request.
- **The engine launcher** (`sh "<plugin root>/lib/biq_run.sh" -c <code>`, the literal plugin path, with no environment
  assignment) is free when its code is **engine-confined**. Engine-confined means confined code that may also import
  `biq`, but none of the guard's machinery except `biq.writeguard.export`. Any other engine code needs approval.

Each operation is then decided by `writeguard.policy`, the single place `CLAUDE.md` §9 is turned into a decision:

- **free** — a new file or directory under `./businessiq-output/`; anything under the scratchpad or the system
  temporary directory; a device;
- **prohibited** —
  - the approval store;
  - the plugin itself, while engaged;
  - an existing business data file (`.csv`, `.tsv`, `.xlsx`, `.xlsm`, `.xls`) outside scratch and output (§9: source
    data is immutable);
  - force-push, history rewrite or branch deletion;
  - invoking the guard entry;
- **approval** — everything else, including every `execute` and `unknown_write`: `UNKNOWN != SAFE`.

### 3. The approval model and capability binding

Approval follows ADR-0010: per action, non-transferable, never session-wide. It takes the shape of the disclosure
gate's `research.contract.Approval`, a record of *which* operation, spent when used. Because the hook that asks, the
prompt that grants and the hook that redeems are separate processes, the record lives in a store,
`~/.claude/businessiq/guard/`. The store's location comes from the account database, not `$HOME`. Its record shape is
`lib/schemas/write_approval.schema.json`.

1. **Request.** The hook (or the export API) writes a pending record. Its **binding** is:
   - the `session_id`;
   - the tool;
   - the canonical cwd;
   - the sha256 of the tool input's bound fields: the `Bash` command, or `Write`'s path and content, and so on (a free
     text `description` is not bound);
   - every operation's kind, canonical target, sources and existence.

   The record also carries a random code, `BIQ-W-XXXXXXXX`. An identical request reuses its unexpired code.
2. **Deny.** The call is denied. The reason names each operation and target, and whether an existing file would be
   overwritten. It says that nothing was written, gives the exact phrase `approve BIQ-W-XXXXXXXX`, and says that only
   the identical call will be admitted. It never echoes file content. `systemMessage` shows the user the same summary.
3. **Grant.** Only the `UserPromptSubmit` hook grants, and only from the user's own prompt, for the same session. It
   rebuilds both the fingerprint and the user-facing description from the stored binding. The grant is single-use and
   expires after 10 minutes; a pending request expires after 30 minutes. A prompt from a subagent (`agent_id`), or one
   whose `source` is `system`/`loop_wakeup`/`schedule_wakeup`/`poll_event`, grants nothing.
4. **Redeem.** Immediately before execution, the hook computes the binding of the **actual `tool_input` now arriving**
   and redeems only a granted record with the identical fingerprint. It claims the record with an atomic rename into
   `consumed/`.

   A different target, operation kind, command, tool, content, session or target existence is a different fingerprint,
   and redeems nothing. That covers overwrite changed to delete, a create that has become an overwrite, and a
   capability for `README.md` reused elsewhere.

   On a match, the hook returns no decision. It never returns `allow`, so the user's own permission rules still apply.

**TOCTOU.** No approval is carried from classification to execution. The decision is taken on the input the runtime
is about to run, in the same `PreToolUse` invocation that precedes execution. The measured runtime fact is that the
tool body does not run before the hook returns. Mutating the command after approval changes the input digest.
Swapping the target for another file changes the canonical target. A target that appears or disappears changes the
existence bit.

### 4. The internal execution boundary (layer 2)

`lib/python/biq_run.py` installs `writeguard.engine` before it runs any engine code. This is a CPython audit hook
(PEP 578), which cannot be removed. It sees every file open for writing, `remove`, `rename`/`replace`, `mkdir`,
`rmdir`, `truncate`, `link`/`symlink`, `chmod`/`chown`/`utime`, `rmtree`, `sqlite3.connect`, process start, socket
connect and `ctypes` call, before it happens. Everything outside the engine's own state is raised as
`WriteBlockedError`. The engine's own state is:

- `~/.claude/businessiq/runtime/`;
- `./.businessiq/`;
- the verification directory;
- new files under `./businessiq-output/`;
- the store's `pending/` and `consumed/` areas, but never `granted/`.

Processes are limited to the ADR-0008 argument shapes, and network is refused (`CLAUDE.md` §4). Bytecode writing is
switched off, so the plugin tree is never written.

`writeguard.export.write_text(path, text)` is the engine's one user-file write path. It uses the same policy, the same
store and the same binding. Its binding adds a content digest, and it takes the session from `CLAUDE_CODE_SESSION_ID`;
the store and the session are not parameters. After a redeemed capability, it writes through a one-shot authorisation
for exactly that path and operation. Without a session id it fails closed.

### 5. Fail-closed

These cases deny:

- an unreadable hook input;
- an internal error while the session is engaged or its engagement is unknown;
- a missing session id;
- a store that cannot be read.

`hooks/biq_guard.sh` turns a guard that cannot start at all (no usable Python, a broken installation) into exit
status 2. Claude Code treats that as a blocking error for `PreToolUse`. A prompt is never blocked: when the guard
cannot run, no approval is granted, which is itself closed.

### 6. Why this is not an evaluator workaround

- The hook runs in every Claude Code session in which BusinessIQ is installed, in every permission mode measured.
- It does not consult, detect or depend on the evaluator or its sandbox.
- Its runtime evidence comes from ordinary `claude -p` sessions, not from `claude plugin eval`. Whether the eval
  harness loads plugin hooks is still unmeasured.
- The engine layer protects writes that no Claude Code tool call is involved in.
- `a20`'s recorded evaluation classes are unchanged, and no grader or case was edited.

## Reason

Option D is the narrowest boundary that stops the demonstrated failure at a measured enforcement point:

- plugin-wide, so it is active before any BusinessIQ skill is invoked;
- scoped by facts the runtime reports, so unrelated work is not governed;
- decided on the exact input about to run.

Its approval cannot be minted by a tool call:

- the store is prohibited to every tool call and to the engine;
- the only granting path reads the user's prompt;
- the tools that can inject a prompt are denied when they carry an approval phrase.

The allowlist classifier fails closed by construction. What it does not understand needs approval.

## Consequences

**Positive**

- The a20 write, and every other consequential write in an engaged session, is denied before execution unless the user
  approved that exact operation.
- `CLAUDE.md` §9's overwrite, delete, commit and push rules have a mechanism behind them.
- Force-push, history rewrite, branch deletion and source-data mutation are refused outright.
- The engine can no longer write, spawn or connect outside its policy, whatever code is handed to it.

**Negative**

- **Latency.** Every matched tool call starts `sh` and Python, including calls in sessions that never engage
  BusinessIQ, because engagement and store protection are decided per call.
  - Measured on this WSL2 machine, with the plugin on the Windows drive (`/mnt/d`) and no other load: **1.6–2.6 s per
    call**.
  - About 1 s of that is the launcher's Python start-up and engine import (`biq_run.py --where`: 0.9–1.2 s). Most of
    the rest is the resolver's interpreter probe.
  - A plugin on a native Linux filesystem was not measured.
- An engaged session's ordinary writes (outside `./businessiq-output/` and scratch) need an approval code each time.
  This is the intended contract, and it is a cost.
- The classifier is conservative, so some harmless commands need approval: `awk`, a `sed` script containing a `w`, a
  relative write after `cd`, and any PowerShell.
- One shipped engine template (`skills/biq-benchmark-comparison/SKILL.md`) carries prose placeholders. It parses, and
  so runs without approval, only once the model has filled them in.

**Known limits (recorded, not hidden)**

1. **Unmeasured at runtime:**
   - whether plugin `UserPromptSubmit` and `UserPromptExpansion` hooks fire as documented (if `UserPromptSubmit` does
     not, no approval can ever be granted, which is closed but unusable);
   - `ask` answered by a person;
   - `plan` mode;
   - a marketplace-installed plugin (the experiment used `--plugin-dir`);
   - hooks inside subagents;
   - models other than sonnet;
   - `claude plugin eval`.
2. **Injected prompts.** 2.1.283 does not populate `UserPromptSubmit.source`. A prompt injected by a route other than
   the denied tools could carry an approval phrase: another session's notice to this session, or an SDK poll event.
3. **Same OS user.** Approving an `execute` operation approves arbitrary code, and arbitrary code can do anything the
   user can, including rewriting the store. The approval text says the effects "cannot be established".
4. **Python cannot sandbox Python.** The engine guard is sound only for confined code, which is why only confined
   engine code runs without approval.
5. **Engagement-based scope.** A write made before BusinessIQ is engaged in a session is not governed. Before
   engagement the plugin's own files are not protected (only the store is).
6. **Hook ordering.** If another plugin's `PreToolUse` hook rewrites the input (`updatedInput`) after this one, the
   interaction is unmeasured.
7. **No `sh`.** If `sh` cannot be started at all (native Windows without a POSIX shell), the platform's own error
   handling applies. The engine has the same dependency (ADR-0045).
8. **`CLAUDE_CODE_SESSION_ID`** is observed, not documented. Without it, an export fails closed.

**Follow-up required**

- An owner-run live check of `UserPromptSubmit` granting and of the unmeasured conditions in limit 1.
- A latency reduction. The per-call cost above is paid by every matched tool call of every session with BusinessIQ
  installed. Candidates are a lighter `--guard` import path and skipping the resolver probe for the hook. Either would
  be measured before it is adopted.

## Revisit when

- Claude Code populates `UserPromptSubmit.source`, or attributes a tool call to a plugin.
- `ask` is measured with a human answering in every mode.
- A runtime or plugin sandbox can confine the engine process itself.
