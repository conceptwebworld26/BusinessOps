# ADR-0035 — The M11 blind-recomputation boundary: an opaque request, one fixed operation, digests not values, and no shell for the verifier agent

**Date:** 2026-09-17
**Status:** Accepted
**Deciders:** Project owner (M11 contract-alignment brief), recorded in the M11-A contract-alignment remediation (decision only)
**Supersedes, in part:** [ADR-0034](ADR-0034-m11-verification-and-finalisation-contract.md) — only the
clauses listed in §1. Every other ADR-0034 decision stands unchanged.
**Relates to:** ADR-0001 (verified platform facts only), ADR-0002 (figures from code), ADR-0006 (three
subagents), ADR-0009 (disclosure), ADR-0014 (the tool grant is the boundary), ADR-0015 (model-mediated
dispatch; agents auto-discovered; named envelopes), ADR-0017 (verbatim replies), ADR-0022 (synthesis
contract), ADR-0033 (Executive Report). ADR-0031, ADR-0032 and ADR-0033 are not amended.

## Context

ADR-0034 decided that verification pass/fail is deterministic, that no model decides anything, and that
headline figures are recomputed "blind" by the `biq-analysis-verifier` agent. Its interface for that
recomputation contradicts its own boundary:

| ADR-0034 clause | What it says | Why it is not blind |
|---|---|---|
| §5.3 *The brief* | lists "the command id, source path, `source_sha256`" | the agent model receives a path to the confidential file |
| §12 | tool grant "**`Bash` only**" | a shell lets the agent model `cat`, `grep` or copy that file, or any other file, and reach the network |
| §5.3 *Execution*, §12 | the command "emits recomputed fields"; the agent returns "stdout **verbatim**" | the recomputed confidential values pass through the agent model's context |
| §11 | the brief and reply "carry ids, local paths and hashes, never figures or text" | false for the reply §5.3 defines |
| §6 *Findings* | `expected`, `observed` "redacted to ids and digests where the value is a figure or text" | a partial rule; "the condition and value as strings" still admits raw values elsewhere |
| Context, §5.3 *basis* | a per-registration basis of `command_id`, `source`, `source_sha256` | leaves unresolved that `register_dataset()`, `register_kpi()` and `register_analysis()` key by dataset id, `kpi_id` and `analysis_id`, so a later command silently overwrites an earlier registration |

What the repository establishes about constraining an agent:

- **The tool grant is the boundary, and nothing narrower is verified.** `agents/biq-research-scout.md`
  and `tests/unit/test_research_scout_boundary.py` treat the declared `tools` list as *the* security
  control (ADR-0014): "This agent's tool grant decides *what can possibly be read*." Agent frontmatter
  names whole tools; no verified mechanism restricts `Bash` to one command or one argument form, and
  ADR-0001 admits only verified platform fields. **A `Bash` grant is therefore an arbitrary shell. It is
  not a sandbox, and no instruction makes it one.**
- **Agents are auto-discovered; dispatch is model-mediated; replies are named, versioned envelopes**
  (ADR-0015: `biq.scout.result/1`).
- **There is no `.mcp.json` today.** Adding any MCP server passes the Connector gate (`CLAUDE.md` §13).
- **Runtime state lives under `./.businessiq/`** (gitignored), resolved by `config.py` from the working
  directory.
- **`commands.run()`** takes `command_id`, `source`, `question`, `presentation` and pipeline and engine
  keyword arguments; presentation changes dimension redaction, so it changes statements.
- **`SynthesisSet.as_dict()`** is the digested serialisation; `synthesis.schema.json` permits additional
  top-level properties.

## Problem

Define a recomputation interface in which the model-mediated agent can neither read the confidential
source nor see the values being verified, cannot substitute a file, dataset, path, URL or command, and
returns nothing sensitive — while deterministic Python keeps exact comparison and sole authority, the
ADR-0006 agent keeps a real role, and the recomputation basis is unambiguous.

## Options considered

### Option A — Keep `Bash`, constrain by instruction and a fixed command string

**Rejected.** The grant is the boundary (ADR-0014); an instruction inside a context that holds a shell
does not remove the shell. The path and the verbatim stdout remain visible. This is ADR-0014's Option A
failure mode in a new place.

### Option B — Keep `Bash`, restrict it with permission patterns or hooks

**Rejected for this contract.** Restricting a subagent's `Bash` to one command form is not a verified
platform fact in this repository (ADR-0001), shell parsing of compound commands is a known weak point,
and a hook-based filter would be a security subsystem the milestone must not build.

### Option C — Drop the agent; the deterministic layer recomputes in a child process

Structurally blind and simple. **Rejected as the decision.** It removes ADR-0006's verifier agent's only
role; changing the agent topology needs its own ADR, and the confidentiality problem does not require it.

### Option D — The agent holds exactly one fixed, registered operation that accepts only an opaque request id

The deterministic layer writes a closed recomputation request; a plugin-local MCP tool resolves it
internally, recomputes, writes **digests** to a machine-only record and returns only an allowlisted
status; deterministic Python compares. **Chosen.**

## Decision

**The `biq-analysis-verifier` agent holds no shell, no file tool and no web tool. Its entire grant is one
registered operation, `recompute`, whose only argument is an opaque request id. The operation resolves
the request, sources and command internally, never returns a business value, a path or text, and writes
only salted SHA-256 digests of recomputed values to a machine-only record. `verification.verify()` —
deterministic Python — reads that record, compares it with the draft's exact values, and alone decides
every outcome. No model receives the confidential source, a checked value or a recomputed value through
the verification channel.**

### 1. What this supersedes in ADR-0034

| ADR-0034 | Superseded by |
|---|---|
| Context row on dataset registration, and §5.3 *Recomputation basis* | §2 run registration |
| §3 *Recomputation reply* input | §4 relay input |
| §5.3 *The brief*, *Execution*, *Comparison*, *Why blind* | §3–§5 |
| §6 `figure_recomputation` checks, and the *Findings* `expected`/`observed` row | §6, §7 |
| §7 `recomputation` field; §8 `verification_record.brief_id` | §7 |
| §9 rows on the reply and source | §8 |
| §11 brief and reply persistence | §5 |
| §12 agent definition, tool grant, model permissions | §9 |
| §13 "the recompute command reads only the briefed local sources" | §3, §10 |
| §14 field `brief_id` | §7 (`request_id`, `record_id`) |
| Consequences: the `Bash` negative; Follow-up: the `recompute` CLI and `Bash` agent | Consequences below |

**Not superseded** — scope, what is never verified, the binding graph, source binding, reproduction, the
exact definition of headline figures, the check categories other than recomputation, blocking and
ordering, `VerificationResult` apart from its `recomputation` field, lifecycle and finalisation,
`report_id`, the human-decision boundary, re-entry, and what makes an artifact final.

### 2. The recomputation basis: a run registration

Dataset id alone is insufficient: it is a provenance label the caller chooses, several commands share
one, and `register_dataset()` overwrites. The basis is the **command run**.

- **What is hashed.** The complete byte content of the source file at its absolute path, with SHA-256.
- **When.** By `commands.run()`, immediately before the pipeline opens the file and again immediately
  after the run returns. If the two differ, or either read fails, the run is `unavailable` with a fixed
  reason and nothing from it may be registered.
- **Where it is carried.** Additively on `CommandResult` (`source_sha256`, `run_arguments`,
  `config_digest`, `run_id`).
- **`run_arguments`.** The canonical JSON of every argument to `commands.run()` except `source` —
  `question`, `presentation`, and every pipeline and engine keyword — because each can change a figure or
  a statement.
- **`config_digest`.** SHA-256 of the canonical JSON of `ResolvedConfig.as_dict()` the run used.
- **`run_id`.** `run-` + 12 hex, content-addressed over `{command_id, source_path (absolute),
  source_sha256, run_arguments, config_digest}`. Two runs differ in `run_id` exactly when one of those
  differs.
- **Which registration stores it.** A new run registry in the `SynthesisSet`: `commands.internal_statements()`
  registers the run once (`run_id` → the fields above plus the caller's `dataset_id` as a label) and
  records, for every `KPIResult` and `AnalysisSet` it registers, the `run_id` it came from. Registering a
  `kpi_id` or `analysis_id` already registered **from a different `run_id` is refused**; the same run is
  idempotent. So two analyses over the same dataset can never overwrite each other's basis, and a
  statement's provenance stays unambiguous.
- **Binding.** The run registry is part of `SynthesisSet.as_dict()` (additive top-level property), so
  every run's basis is covered by the synthesis digest the draft is bound to.
- **No basis, no recomputation.** A headline figure whose registered object has no `run_id` — it entered
  the set outside the command path — cannot be recomputed, and verification fails for it
  (`recomputation.request`, §6). No command, file or configuration is ever guessed.

### 3. The controlled operation

**One operation**, `recompute`, served by a plugin-local stdio MCP server (`biq-verifier`) whose code is
`lib/python/biq/verification_server.py`, declared in `.mcp.json` with server identity only (`type`,
`command`, `args`; no token) after the Connector gate. It is the only MCP server this decision adds.

**Input** — closed:

```json
{"request_id": "rcq-<16 hex>"}
```

No path, file, dataset, URL, command, configuration or value can be expressed. Any other key, or a value
not matching the pattern, is refused before any file is opened.

**Behaviour** — fixed, deterministic, local:

1. Resolve `./.businessiq/verification/requests/<request_id>.json` through the existing project-directory
   resolver. Nothing outside that directory is resolved from the request id.
2. Parse the request against its closed schema (§4). Require `request_id` to equal the content address of
   the request's canonical bytes; a request edited after issue is refused.
3. For each run in the request: hash the named source; if it differs from `source_sha256`, record
   `source_status: mismatched`, compute **nothing** for that run and trust nothing from it. Otherwise
   resolve configuration the usual way and require its digest to equal `config_digest` (else
   `config_status: mismatched`, compute nothing), then call `commands.run(command_id, source,
   **run_arguments)`.
4. For each requested item, compute a salted digest of each requested field's canonical string (§5).
5. Write the record (§5) with exclusive create; if a file with that `record_id` exists, it must be
   byte-identical, otherwise refuse.
6. Return the result envelope (below). **No exception text is ever returned.**

The operation imports no network library, dispatches nothing, prints no source content, and has no code
path that returns a value, a path, a hash of a value or statement text.

**Output** — closed, allowlisted, named per ADR-0015:

```json
{"protocol": "biq.verifier.result/1",
 "request_id": "rcq-<16 hex>",
 "status": "completed" | "failed",
 "record_id": "rcr-<16 hex>" | null,
 "error_code": null | "request_id_invalid" | "request_not_found" | "request_invalid"
             | "request_digest_mismatch" | "record_conflict" | "execution_error"}
```

`completed` means a record was written, not that anything matched — a source or configuration mismatch
is recorded in the record, and deciding what it means is `verify()`'s. The envelope carries no figure,
count, hash, path, dataset id, command id or message.

### 4. The request, the agent input and the relay

**The request** — written by `verification.issue_recomputation(draft)` in the deterministic layer, which
returns the `request_id` (or `None` when nothing needs recomputation). Closed schema
`biq.verifier.request/1`:

```json
{"protocol": "biq.verifier.request/1",
 "request_id": "rcq-<16 hex>",
 "runs": [{"run_id": "run-…", "command_id": "…", "source_path": "<absolute>",
           "source_sha256": "sha256:…", "run_arguments": {…}, "config_digest": "sha256:…",
           "items": [{"kind": "kpi" | "analysis", "id": "…", "fields": ["…"]}]}]}
```

Runs in run-registry order; items in the order ADR-0034 §5.3 fixes for headline figures; fields from the
fixed lists: `kpi` — `status`, `value`, `currency`, `unit`; `analysis` — `statement`, `observed`,
`comparison`, `change`, `change_pct`, `period`, `materiality`. **No claimed value, statement text, report
content, framing, research content or recommendation.** The request is written with exclusive create
(identical existing bytes accepted) to the directory in §3. The source path appears only here, on disk,
in a file the agent has no tool to open.

**The agent input** — the Task prompt carries **only** the `request_id` string. Not the path, the request
file, a dataset or command name, the draft, or any figure.

**The relay** — the agent returns the operation's result envelope unchanged. Because that envelope is
allowlisted and non-sensitive, relaying it verbatim is now safe. `verify(draft, relay)` treats the relay
as untrusted data: closed-schema parse; `protocol` exact; `request_id` equal to the id it re-derives for
this draft; `record_id` used only to locate a record whose own bytes must hash to it.

### 5. The record, digests and exact comparison

**The record** — written only by the operation, read only by `verify()`, never returned to a model.
Closed schema `biq.verifier.record/1`:

```json
{"protocol": "biq.verifier.record/1",
 "record_id": "rcr-<16 hex>",
 "request_id": "rcq-…",
 "request_sha256": "sha256:…",
 "runs": [{"run_id": "run-…",
           "source_status": "matched" | "mismatched" | "unreadable",
           "config_status": "matched" | "mismatched" | "not_checked",
           "run_status": "completed" | "unavailable" | "not_run",
           "items": [{"kind": "kpi" | "analysis", "id": "…", "status": "found" | "absent",
                      "digests": {"<field>": "sha256:…"}}]}]}
```

`request_sha256` is the digest of the request bytes the operation read; `record_id` is the content
address of the record's canonical bytes.

**Digests, not values.** For each field:

```
sha256( request_id ␟ run_id ␟ kind ␟ id ␟ field ␟ canonical )
```

where `␟` is U+001F and `canonical` is the field's exact string as the engine emits it (`str(Decimal)`,
the statement text, the status or outcome code), or the fixed marker `\u0000null` for an absent value.
**No rounding, trimming, case folding, unit conversion or other normalisation.** `verify()` computes the
same digest over the draft's exact string and compares digests; SHA-256 equality stands for exact string
equality. The salt makes a record's digests unusable outside its own request; it is **not** a secrecy
mechanism, and it is not claimed as one — the protection is that no value is written, returned or relayed.

**`verify()` then decides**, in order, each failure a finding (§6):

1. relay present and valid, `status` `completed`;
2. record exists, hashes to `record_id`, and its `request_id` and `request_sha256` equal the request
   `verify()` re-derives from the draft **now** (so a request altered on disk, a record for another
   request, or a stale record fails);
3. every requested run present once, none extra; `source_status` `matched`; `config_status` `matched`;
   `run_status` `completed` — otherwise **no digest from that run is trusted**;
4. every requested item present once with status `found`, none extra, every requested field present;
5. every digest equal.

**Working files.** Requests and records live in `./.businessiq/verification/` (gitignored runtime state).
They contain ids, the local source path (requests only), SHA-256s of files and configuration, run
arguments, statuses and salted digests — **never a figure or statement text**. `verify()` removes the
request and record it consumed once the `VerificationResult` is built, pass or fail; nothing else in the
directory is read or trusted. The verification artifacts themselves remain in memory only (ADR-0034 §11,
otherwise unchanged).

### 6. Recomputation checks

`figure_recomputation` checks, replacing ADR-0034's four:

| Check | Fails when |
|---|---|
| `recomputation.request` | the request cannot be issued (a headline figure with no run basis) |
| `recomputation.relay` | relay absent, malformed, wrong protocol, other `request_id`, or `status` `failed` (its `error_code` is carried) |
| `recomputation.record` | record missing, not hashing to `record_id`, or bound to a different or altered request |
| `recomputation.source` | a run's `source_status` is not `matched` |
| `recomputation.configuration` | a run's `config_status` is not `matched` |
| `recomputation.execution` | a run's `run_status` is not `completed` |
| `recomputation.coverage` | a requested run, item or field is absent, or an unrequested one present |
| `recomputation.kpi` | a KPI field digest differs |
| `recomputation.statement` | an analysis field digest differs |

### 7. Findings and the `recomputation` field without values

**Every finding, in every category** (not only recomputation), carries references and comparison codes,
never a business value or statement text:

| Field | Shape |
|---|---|
| `expected` | a reference to what was checked: e.g. `run:run-…/kpi:gross_margin/value`, `synthesis:sy-…/observed`, `section:kpi_scorecard`, `component:decision_package/sha256:…` |
| `observed` | a closed comparison code: `differs`, `absent`, `extra`, `mismatched`, `unreadable`, `not_run`, `malformed`, `unbound`, or a relay `error_code` |

A reader who needs the figure opens the draft, which already shows it, or reruns the analysis command.
This deliberately trades a convenience for the boundary: a finding is never a second channel for
confidential values. ADR-0034's `finding_id` is computed over these fields.

`VerificationResult.recomputation` becomes:

```
{status: completed | not_required | failed,
 executor: "biq-analysis-verifier",
 request_id, record_id,
 runs: [{run_id, dataset_id, command_id, source_status, config_status, run_status}],
 figures_checked}
```

and `verification_record.brief_id` becomes `request_id` and `record_id`. `register_claims()` also refuses
records carrying `request_id`, `record_id` or `analysis: verification` (replacing `brief_id`).

### 8. Failure states

| Situation | Outcome |
|---|---|
| Nothing requires recomputation | no request issued, no agent dispatched, `recomputation.status` `not_required` |
| Agent not dispatched, failed, or returned nothing | `recomputation.relay` |
| Model passes another `request_id` | the operation computes that request, if one exists, but `verify()` rejects the relay (`recomputation.relay`) — no substitution reaches a pass |
| Request file edited, or forged to name another file, command or configuration | operation refuses (`request_digest_mismatch`), or `verify()` finds `request_sha256` unequal to the request it re-derives (`recomputation.record`) |
| Source file changed since the run | `recomputation.source`; nothing from that run trusted |
| Configuration changed since the run | `recomputation.configuration` |
| Record for another request, altered, or stale | `recomputation.record` |
| Any figure differs | `recomputation.kpi` / `recomputation.statement`, located, no value shown |

Every one blocks finalisation (ADR-0034 §6, unchanged). None is retried with edits.

### 9. `biq-analysis-verifier`

- **Definition.** `agents/biq-analysis-verifier.md`, auto-discovered (ADR-0015). Frontmatter from the
  supported set only. **`tools`: exactly the one MCP tool name of `recompute`** — no `Bash`, `Read`,
  `Write`, `Edit`, `Glob`, `Grep`, `WebSearch`, `WebFetch` or `Task`. An explicit grant is required; an
  absent `tools` field inherits everything.
- **Role.** Invoke `recompute` once with the `request_id` it was given; return the envelope unchanged;
  if the call fails at the platform level, say so and return nothing else. It holds no logic
  (`CLAUDE.md` §3).
- **What its independence is, stated plainly.** The agent adds no verification judgement. ADR-0006's
  independence now rests on two structural facts: the recomputing process (the MCP server) never
  receives a claimed value, and the agent context has no tool that can read data. The agent is the
  isolated, zero-access context that initiates recomputation.
- **Boundary test** (as for the scout): the definition exists, frontmatter is supported, `tools` is
  explicit, equals the single operation, and contains no file, shell, web or dispatch tool; the body
  states that it receives only a request id and never sees values.

**The model may:** invoke `recompute` with the given `request_id`; relay the envelope or a platform
failure; in the main thread, present `verification.render()` output and explain findings already listed.

**The model must not:** read or ask for the source, request or record; calculate an expected or observed
figure; decide or describe equality; judge whether a mismatch is acceptable; add, change, suppress,
reorder or soften a finding; convert a failure into a warning; assign severity; decide finalisation; set
a lifecycle or verification value.

### 10. Confidentiality boundary

| Data | Verifier agent context | Operation envelope | Record / request on disk | `VerificationResult` |
|---|---|---|---|---|
| Source file contents, transactions, customer records | never | never | never | never |
| KPI and statement values, statement text | never | never | salted digests only (record) | never |
| Source path | never | never | request only | never (dataset id and run id only) |
| Source and configuration SHA-256 | never | never | yes | statuses only |

The recomputing process reads the source because it must; model visibility of the source and of every
checked value is zero on the verification path. **This does not claim the main-thread model has never seen
the draft's figures** — it rendered the draft — only that verification adds no exposure and trusts no
model with a value. Nothing is transmitted off the machine: the MCP transport is local stdio, the agent's
prompt carries an id, and no web tool exists on the path.

### 11. Platform facts to measure before implementation, and the rule if they fail

Measured, not assumed (ADR-0001, ADR-0015): (1) a plugin `.mcp.json` stdio server launches this module;
(2) the exact tool name it exposes; (3) an agent's `tools` field restricts the agent to that single MCP
tool and grants nothing implicitly; (4) `claude plugin validate . --strict` accepts both. The `.mcp.json`
entry passes the Connector gate.

**If any of (1)–(4) cannot be verified, the recomputation path is `BLOCKED`.** It is not replaced by a
`Bash` grant, a permission pattern, an in-process shortcut or a child-process executor without a new ADR.
Drafts are unaffected; artifacts whose verification needs no recomputation (`not_required`) may still be
verified and finalised; every other artifact stays a draft.

## Reason

Option D is the only option that makes the confidentiality property **structural** in the way ADR-0014
requires of the scout — decided by what the agent is *granted*, not by what it is *asked* — while keeping
ADR-0006's agent, ADR-0002's code-decided figures and ADR-0034's exact comparison. Returning digests to a
machine-only record, rather than values through the model, removes the verbatim-stdout exposure without
weakening comparison. Content-addressing the request, binding the record to it and re-deriving the
request in `verify()` closes substitution of a file, dataset, path, command or configuration. The run
registration removes the overwrite ambiguity at its source instead of working around it.

## Consequences

**Positive.** The verifier agent can read nothing and see no value. A model cannot redirect recomputation
to another file, command or configuration, and cannot make a mismatch pass. Findings never duplicate
confidential values. The recomputation basis is unambiguous and digest-bound.

**Negative.** BusinessIQ gains its first MCP server, a local one, with its Connector-gate review, launch
dependency and a small always-on tool description (ADR-0013). Findings no longer show observed values; a
reader reopens the draft or reruns the analysis. Registering the same `kpi_id` or `analysis_id` from two
different runs into one set is now refused where it silently overwrote — a stricter M10 behaviour that the
implementation must run the full suite against. Verification leaves working files in `./.businessiq/`
until consumed. The main-thread model can still call `recompute` directly instead of dispatching the
agent; that gains it nothing (the envelope is non-sensitive) and the command sequencing test is the
control, as ADR-0015 accepts for the scout. Recomputation is unavailable if the platform facts in §11
cannot be verified.

**Follow-up required — the M11 implementation milestone,** in place of ADR-0034's recomputation and agent
items: measure §11; `lib/python/biq/verification_server.py`; the `.mcp.json` entry (Connector gate);
`agents/biq-analysis-verifier.md` granted only `recompute`, with its boundary test; closed schemas for the
request, record and result envelope; `verification.issue_recomputation()` and the §5 comparison in
`verify()`; the run registration and source hashing in `commands.run()` and
`commands.internal_statements()`, the refusal of cross-run re-registration, and the run registry in
`SynthesisSet.as_dict()`; findings in the §7 shape. Everything else in ADR-0034's follow-up is unchanged.

## Revisit when

- A verified platform mechanism can restrict a subagent's shell to one argument form (Option B could be
  re-evaluated; Option A never).
- Connector sources (M12) need recomputation without a local file to hash.
- A second verification operation is proposed for the same server.
- ADR-0006's agent topology is reopened.
