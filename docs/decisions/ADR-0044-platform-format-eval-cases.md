# ADR-0044 — The eval case file is written in the platform's own case format, and carries the BusinessIQ semantic record beside it in the same file

**Date:** 2026-09-22
**Status:** Accepted 2026-09-22
**Deciders:** Project owner. Investigated under the M13-DEF-05 remediation prompt; accepted with Phase 1 authorised in the same decision.

## Context

M13.2 authored 64 eval cases in a repository-local schema, `biq-eval-case/1`, defined in
`docs/testing/eval-suite.md`. That schema was designed **without a platform reference**, which the document has
stated since it was written: the harness contract was listed as open item G-3, to be verified at execution time.

The first owner-authorised execution, on 2026-09-20, was refused at case load:

```
✗ …\evals\approval\a01-read-only-anomaly-detection\case.yaml: missing required field schema_version (e.g. "1.0")
64 case file(s) failed to load
```

No case ran, `costUsd` was 0, and the refusal was recorded as **M13-DEF-05** (infrastructure, open, blocking).
The natural reading of that one error is that one field is missing.

**That reading is wrong.** On 2026-09-22 the Claude Code 2.1.278 executable was inspected read-only — no evaluation
was run, no model was invoked — and it contains both the case loader and an embedded authoring guide. The loader's
validation is source-level evidence, not inference:

| Fact | Evidence |
|---|---|
| `schema_version` is a required string; its major part must be ≤ 1, so `"1.0"` and `"1.1"` are valid | `fs()` validator: `parseInt` of the part before `.`, compared with the binary's max major |
| `name` is required (non-empty string) | the case schema's `name: ce().min(1)` |
| `execution` is a required object, and `execution.prompt` must be non-empty unless a `prompt.md` supplies it | the schema, plus the explicit check emitting `execution.prompt is required (a prompt.md body, or execution.prompt in case.yaml)` |
| `graders` must hold **at least one** grader, each exactly one of six types — `regex`, `tool_order`, `tool_used`, `file_exists`, `llm`, `baseline` — each with a `name`, and grader names must be unique in a case | the discriminated union, `.min(1)`, and the duplicate-name refinement |
| **Unknown top-level keys are stripped, not rejected**; unknown keys **inside a grader are rejected** | the top-level object does not call `.strict()`; every grader variant does |
| `runs` defaults to 3, `tags` to `[]`, `context` to `{add_dirs: []}` | the schema's defaults |
| A second layout exists: `prompt.md` + `graders/*.md`. When no `case.yaml` is present the loader synthesises `schema_version: "1.1"` and `name` = the directory's basename | the prompt.md/graders loader and its merge function |
| A negative tool assertion is `min: 0`, `max: 0` **and** `arm: both`; `min` defaults to 1; `tool: Skill` without `arm` is display-only under ablation | the embedded authoring guide, verbatim |
| Cases run in a **sandbox cwd**, with no absolute paths permitted in prompts or graders, and only a read-only tool set by default | the embedded authoring guide, verbatim |

Measured against that contract, the repository's 64 cases fail on **four** counts, not one: no `schema_version`, no
`name`, no `execution` block (the prompt is a top-level `prompt:`), and 133 graders written in a vocabulary
(`kind`, `check`, `property`, `command`, `skill`, `why_not_deterministic`) that no platform grader type accepts —
and grader objects reject unknown keys.

Adding `schema_version: "1.0"` to all 64 files would therefore move the error, not fix it. No case would load.

## Problem

How should the 64 authored cases be made loadable and runnable, without losing the ADR-0039 semantic record each
case carries (`coverage_rows`, `evidence_class`, `evidence_reason`, `purpose`, `expected_property`, `safety`,
`tool_grants`, `why_not_deterministic`), and without inventing platform behaviour that has not been observed?

## Options considered

### Option A — Add `schema_version: "1.0"` and nothing else

The change the remediation prompt assumed. **Rejected on evidence:** the loader requires `name`, `execution.prompt`
and platform-typed graders as well. Nothing would load, and 64 files would carry a field that buys nothing.

### Option B — Rewrite the cases in the platform format, dropping the BusinessIQ fields

Pros: the smallest files, and exactly what the platform documents.
**Rejected:** it destroys the §E.6 evidence class per case, the coverage-row binding that makes the matrix
traceable (ADR-0039 §B, §E.3), the safety declarations, and the `why_not_deterministic` justification §E.4 requires
for every LLM grader. The §E.5 static validator would have nothing left to validate, and M13's whole evidence
model is built on those fields.

### Option C — One file, two layers: platform keys plus the BusinessIQ semantic keys (recommended)

Each `case.yaml` carries the platform's required keys **and** keeps its BusinessIQ keys, which the loader strips
because the top-level object is not strict. The platform keys are derived mechanically from the semantic ones:
`name` from `id`, `execution.prompt` from `prompt`, `graders[].name` from `graders[].id`, and each grader's type
from its `check`.

Pros: one file per case, as ADR-0039 §E.2 requires; the semantic record and the executable case cannot drift apart,
because they are the same document; the validator keeps its subject; nothing is lost.
Cons: the file carries two vocabularies and a reader must be told which is which; the derivation must be enforced
by the validator or the two layers can contradict each other.

### Option D — Split the layers: platform `case.yaml`, semantic `case.biq.yaml`

Pros: each file speaks one vocabulary.
Cons: two files per case to keep in sync; the validator would police a cross-file link rather than a document; and
ADR-0039 §E.2 names `case.yaml` as the case. **Rejected** as strictly worse than C for the same result.

## Decision

**Option C**, with the grader mapping split explicitly into what the evidence settles and what it does not.

**Mapping that the extracted contract settles** (109 of 133 graders):

| BusinessIQ `check` | Count | Platform grader |
|---|---|---|
| `llm_judgement` | 45 | `type: llm`, `criteria` carried over verbatim, `focus: last_message` |
| `response_matches` | 17 | `type: regex`, `match: contains` |
| `response_not_matches` | 2 | `type: regex`, `match: not_contains` |
| `skill_invoked` | 20 | `type: tool_used`, `tool: Skill`, `input_match: <skill>`, `arm: both` |
| `skill_not_invoked` | 3 | `type: tool_used`, `tool: Skill`, `input_match: <skill>`, `min: 0`, `max: 0`, `arm: both` |
| `tool_not_invoked` | 21 | `type: tool_used`, `min: 0`, `max: 0`, `arm: both` |
| `agent_not_dispatched` | 1 | `type: tool_used` over the dispatch tool, `min: 0`, `max: 0`, `arm: both` — **the tool's trace name is unconfirmed** |

**Mapping that the evidence does NOT settle** (24 graders, and the reason this ADR does not simply order the
migration):

- `command_invoked` (21) and `command_not_invoked` (3) assert that a **plugin slash command** ran. The platform has
  no command grader, and the binary does not document the tool name a plugin command appears under in the run
  trace. The symbol `getSlashCommandToolSkills` suggests commands are surfaced to the model as `Skill`-tool
  entries, but **a function name is not a trace contract**, and this repository does not guess platform behaviour.
- Input delivery is equally unsettled: cases run in a sandbox cwd, while every case prompt names a repository-
  relative input path such as `assets/demo-data/northwind_sales.csv`. Whether that resolves through
  `context.add_dirs`, a scaffold, or copied inputs is unknown. A case that loads but cannot see its input scores 0
  and reads as "the plugin did nothing" — the guide warns about exactly this.

**Therefore the proposed remediation is staged, and only stage 1 is a pure translation:**

1. **Stage 1 — migrate the evidenced 109 graders and the four structural keys**, leaving the 24 command graders and
   the input question untouched. Extend the §E.5 validator to check both layers and their derivation.
2. **Stage 2 — one owner-authorised pilot** of a single case whose graders are all evidenced, run to read the
   **trace**: it names the tool a command fires under, and shows whether the input resolved. One run, one ceiling.
3. **Stage 3 — migrate the remaining 24 graders** against what stage 2 observed, then re-attempt §E.1.

Each stage is its own prompt. No stage guesses.

## Reason

The contract is not inferred: it was read out of the shipping binary, including the loader's own validation and the
authoring guide it carries. That evidence is what rules out Option A, which the remediation prompt had reasonably
assumed, and what makes Option C's derivation mechanical rather than a matter of taste.

The staging exists for one reason: 24 graders and the input path depend on facts only a run can show. ADR-0039's
invariants forbid recording unobserved platform behaviour as fact (I-2 to I-4), and G-3 has been deliberately open
since M13.2 was authored. Migrating all 64 cases now would require inventing a tool name — the one thing the
remediation prompt, and this repository's governance, both forbid.

## Consequences

**Positive.** The case file becomes loadable by the platform while remaining the BusinessIQ evidence record. The
ADR-0039 §E.6 vocabulary, the coverage-row binding and the §E.4 justification survive untouched. The unknowns are
named and each has a cheap, bounded way to settle it.

**Negative.** All 64 files change, in two further passes rather than one. The case file carries two vocabularies,
which is a documentation burden `eval-suite.md` must take on. Stage 2 costs one authorised run that will not
produce a scored result for its own sake — it is bought for the trace.

**Follow-up required.** `docs/testing/eval-suite.md` must document both layers and the mapping table; the §E.5
validator must enforce the derivation and both layers; M13-DEF-05 stays open until stage 3 lands and a case loads;
G-3 keeps the two questions above, now stated precisely instead of generally.


## Implementation note — 2026-09-22, Phase 1

Accepted and implemented the same day, as far as Phase 1 reaches. Three concrete details the
decision text did not fix, each established from the contract rather than chosen:

1. **The semantic layer moved to `biq_graders`, and the file is now `biq-eval-case/2`.** The
   platform's `graders` key is a *known* key, strictly typed per element, so the BusinessIQ
   graders could not stay in it. Every other semantic key keeps its name, because unknown
   top-level keys are stripped.
2. **`tool_used` cannot express the repository's tool patterns.** The platform matches the tool
   name with `===`, so an anchored alternation such as `^(Agent|Task|WebSearch|WebFetch|mcp__.+)$`
   was expanded into one `tool_used` grader per exact name, plus — for the `mcp__` family, which
   no exact name can cover — one `regex` grader with `not_contains` over `trace`. 109 semantic
   graders therefore produce **150** platform graders. At `--threshold 1.0` a conjunction of
   graders is equivalent to the single assertion it replaces.
3. **`agent_not_dispatched` became a `regex` over `trace`, not a `tool_used`.** The decision table
   above proposed `tool_used` over "the dispatch tool", but that tool's trace name is no better
   established than a command's. Asserting that the agent's name never appears anywhere in the
   trace needs no tool name and is **stricter** than the original, never weaker.
4. **`(?i)` became `flags: 'i'`.** JavaScript's `RegExp` has no inline flag group and throws on
   one; the platform carries flags in their own field. Twelve patterns were translated this way,
   and their meaning is unchanged.

**A fourth detail is a partial failure of this ADR's own target**, recorded rather than worked
around: three near-miss routing cases — `r17-near-miss-market-analysis`,
`r18-near-miss-decision-support` and `r19-near-miss-company-analysis` — have **only**
`command_invoked` / `command_not_invoked` graders. The platform requires at least one grader, so
these three cannot load until stage 2 settles the trace tool name. They carry
`platform_status: pending_trace_mapping` and **no** `graders` key. 61 of 64 cases are
platform-loadable; the suite is not, until stage 3.

## Implementation note — 2026-09-22, Stage 3

Appended in the same form as the Phase 1 note above. **No decision text, status line, requirement or prior note is
altered.** Stage 3 was planned by this ADR ("migrate the remaining 24 graders against what stage 2 observed"), so
completing it executes this decision rather than amending it, and no new ADR is required.

**The evidence.** The owner-authorised three-run pilot of `a01-read-only-anomaly-detection` (2026-09-22, Claude Code
2.1.280, `--runs 3 --threshold 1.0 --scaffold --keep-temp`, $0.5577 of a $5 ceiling) produced three kept traces. In all
three, byte-identically:

- tool identifier **`Skill`**;
- input `{"skill": "businessiq:anomaly-detection", "args": "assets/demo-data/northwind_sales.csv"}`;
- result `Launching skill: businessiq:anomaly-detection`;
- the init event's registered spellings: commands as `businessiq:<command>`, skills as `businessiq:biq-<skill>`;
- the only other tool identifier in any trace was `Bash`.

This is the fact the staging existed to obtain, and it confirms the candidate the Phase 1 work deliberately declined to
write in without a trace.

**The mapping, applied to all 24.**

| Semantic check | Count | Platform grader |
|---|---|---|
| `command_invoked` | 21 | `tool_used`, `tool: Skill`, `input_match: businessiq:<command>`, `min: 1` |
| `command_not_invoked` | 3 | the same, with **`min: 0`** and `max: 0` |

**`min: 0` is not decoration.** The platform evaluates a `tool_used` grader as `min = e.min ?? 1`,
`max = e.max ?? Infinity`, verdict `count >= min && count <= max`. With `max: 0` and no `min` the expected range is
`1..0`, which no count can satisfy, so an absence grader written that way could never succeed. The remediation prompt
specified `max: 0`; `min: 0` was added because the platform's own arithmetic requires it, and a test holds it.

**Totals: 133 of 133 mapped, 0 pending, 0 dropped, 174 platform graders emitted, 64 of 64 cases platform-loadable.**
The three near-miss cases `r17`, `r18` and `r19` now carry platform graders and `platform_status: loadable`.

**One limitation, recorded rather than smoothed over.** The pilot observed a **command** invocation. No skill-only
invocation occurred, so it does not independently prove the routing cases' skill spelling. The 22 `skill_invoked` and
`skill_not_invoked` graders keep their Phase 1 mapping — `tool: Skill` with the bare skill name as `input_match`, which
matches as a substring whichever prefix the runtime uses — and the init event's `businessiq:biq-<skill>` is consistent
with it. The two namespaces cannot collide: `businessiq:market-analysis` is not a substring of
`businessiq:biq-market-analysis`, nor the reverse.

**What this does not settle.** §E.1 was re-attempted by the same pilot and recorded as outcome (a), but the case is
`automated_fail`: the engine was never reached, because the evaluator denied a read-only `ls` before the resolver ran
(**M13-DEF-10**). And the platform's own loader has been exercised on 1 of 64 case files; the other 63 are asserted by
the §E.5 validator, not observed loading.

## Revisit when

The platform's case schema major version rises above 1 (the binary refuses a higher major outright); the harness
documents a grader for slash-command invocation; or a run shows the trace tool name for commands, at which point
stage 3 becomes mechanical and this ADR's staging has served its purpose.
