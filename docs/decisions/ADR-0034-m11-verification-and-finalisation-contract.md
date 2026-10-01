# ADR-0034 — The M11 verification and finalisation contract: deterministic integrity checks, blind recomputation, and a final lifecycle recorded beside an unedited draft

**Date:** 2026-09-17
**Status:** Accepted — partially superseded by [ADR-0035](ADR-0035-m11-blind-recomputation-boundary.md) (the recomputation basis and interface, the verifier agent's tool grant and model permissions, finding value representation; ADR-0035 §1 lists the clauses). All other decisions stand
**Deciders:** Project owner (M11 contract brief), recorded in the M11 contract review (decision only)
**Relates to:** ADR-0002 (figures come from code), ADR-0005 (seven classes), ADR-0006 (three subagents),
ADR-0010 (approval), ADR-0012 (placement), ADR-0015 (model-mediated dispatch), ADR-0017 (verbatim
replies), ADR-0022 (synthesis contract), ADR-0030 (SWOT), ADR-0031 (recommendations), ADR-0032 (Decision
Support), ADR-0033 (Executive Report). **No accepted ADR is amended.** This ADR decides the questions
ADR-0032 §13 and ADR-0033 §13 explicitly left to M11.

## Context

What the repository already fixes about M11, verified by reading it at `4dc6562`:

- **ADR-0006:** `biq-analysis-verifier` is one of three subagents, justified by *independent
  verification*: "an agent that cannot see how the first answer was derived is the only thing that can
  genuinely catch a confident wrong number."
- **`architecture.md` §10:** the verifier "independently recompute[s] headline figures, challenge[s]
  conclusions", is invoked "before `/executive-report` and `/decision-support` finalise — i.e. move a
  draft result to final", with tools "engine + dataset".
- **ADR-0032 §13:** every `DecisionResult` before M11 is `draft`; "finalise" means the verifier
  recomputing headline figures and challenging conclusions and, on a pass, "recording a verification
  beside the draft that moves it to `final`. The verifier never edits the package's parts. How it
  records its findings is M11's decision."
- **ADR-0033 §13:** `lifecycle` is `draft` or `final`; **verified is not a lifecycle value** but the act
  and record of the verifier "independently recomputing the report's headline figures (the summary's
  statements and the scorecard's values) against the engines, challenging its interpretations,
  confirming every binding and digest, and confirming every included artifact is shown whole and
  unaltered"; `final` is recorded beside the draft; the verifier never edits a section; **a `final`
  report may not include a `draft` decision package**, a precondition M11 must enforce. §8: the report
  shows any verification record M11 attaches to a package "exactly as carried". §14: `report_id` is
  content-addressed over the synthesis digest, component digests and framing — lifecycle is not in it.
- **ADR-0032 Consequences:** tradeoff and outcome text is "checked for evidence and figures, not for
  soundness — that remains human review."
- **ADR-0031 / ADR-0030 / ADR-0022:** `StrategyResult`, SWOT records and `SynthesisSet` have **no
  lifecycle**.
- **`project_plan.md` Milestone 11:** `biq-data-profiler` and `biq-analysis-verifier`; "the verifier
  finalises; it does not gate building."

What inspection of the code established, and which a contract must account for:

| Fact | Where | Consequence for M11 |
|---|---|---|
| Results bind to the **live** set object plus `strategy.synthesis_digest()` (SHA-256 of `SynthesisSet.to_json()`); every engine refuses a serialised copy | `strategy.py`, `decision_support.py`, `executive_report.py` | Integrity checks run in the process that holds the genuine objects. A separate process cannot receive them |
| The set digest covers every statement, including its `observed`, `comparison`, `change`, `change_pct`, materiality and provenance ids, and evidence sets, conflicts, limitations, confidence | `synthesis_set.as_dict()` | Statement figures are digest-protected |
| The **registered** `KPIResult` and analysis-finding objects are **not** in the set digest, yet the scorecard `value` and the anomaly block read from them | `synthesis_set._registry`; `executive_report._kpi_scorecard`, `_anomalies` | An in-memory change to a registered object is invisible to M10 binding. M11 must check registry-to-statement agreement |
| No source file is fingerprinted anywhere; a dataset registration is `{id, label: source path, detail: command id}`, **keyed by dataset id**, so a second command over the same dataset overwrites the command id | `synthesis_set.register_dataset`, `commands/joins.internal_statements` | Recomputation has no reliable basis today. M11 needs an additive per-registration basis with a SHA-256 of the source |
| `StrategyResult`, `DecisionResult` and `ExecutiveReportResult` retain their outputs but not the validated inputs they were built from | the three result classes | Reproduction by the owning engine needs additive read-only retention of those inputs |
| `ExecutiveReportResult._report` is not covered by its own digest | `executive_report.is_bound_to` | Report content integrity is proven by reproduction, not by the existing binding alone |
| Python cannot dispatch a subagent; agents are invoked by the model through the runtime | `architecture.md` §10, ADR-0015 | The verifier agent can only be a separate execution context the orchestration dispatches, joined by a verbatim reply |
| Schemas: package `verification` is `const "unverified"`; report `lifecycle` is `const "draft"` | `decision_support.schema.json`, `executive_report.schema.json` | M11 implementation extends both for `final`; drafts are unchanged |

## Problem

Define what verification is, what it checks and never checks, how a draft becomes `final` without its
content changing, where verification lives, what the `biq-analysis-verifier` agent and any model may and
may not do, and how every failure closes — precisely enough to implement M11 without reopening
architecture, and without contradicting ADR-0006, ADR-0031, ADR-0032 or ADR-0033.

## Options considered

### Option A — A model-mediated reviewer agent reads the draft and decides

The agent reads the report and its sources, re-derives what it can, and judges whether to finalise.
**Rejected.** Pass/fail would be non-deterministic and unreproducible; a model reading the claimed
figures is anchored by them, which is the opposite of ADR-0006's point; confidential figures and text
would be handed to a second context for no integrity gain; and a model "looks correct" verdict cannot
be tested. It also makes the model the decider of a trust transition, which ADR-0002 exists to prevent.

### Option B — Purely in-process deterministic verification; no agent

A Python module checks bindings, reproduces each artifact through its owning engine, and recomputes
figures in the same process. **Rejected as the whole answer.** It is deterministic, but recomputation in
the drafting process can reuse the very in-memory state it is checking, and it leaves ADR-0006's
accepted verifier agent with no role — an agent topology change that needs its own ADR.

### Option C — Replay the whole pipeline in the verifier agent from a recorded recipe

Record every construction step of the set and every model-authored input, and have the agent rebuild
everything in its own process. **Rejected.** It needs a construction log the synthesis layer does not
have — a second synthesis pipeline in all but name — and persistent replay state.

### Option D — Deterministic integrity verification in-process, plus blind recomputation in the isolated verifier agent

Every contract condition is checked by deterministic Python where the genuine objects live, including
reproduction through the owning engines. Headline figures are recomputed in the `biq-analysis-verifier`
agent's separate process from a **blind brief** that names what to recompute and from which
fingerprinted source, but never carries the claimed values; its output returns verbatim and is compared
deterministically in-process. **Chosen.**

## Decision

**M11 is the verification and finalisation boundary. A verifier — the deterministic module
`lib/python/biq/verification.py`, with the `biq-analysis-verifier` agent as the isolated execution
context for blind recomputation — checks that a draft `ExecutiveReportResult` or draft `DecisionResult`
faithfully and reproducibly represents the artifacts it is bound to, and produces a
`VerificationResult`. Only a `VerificationResult` that passed, for that exact draft, still bound,
permits `finalise()`, which returns a new final object holding the unedited draft and the verification
beside it. No model decides any check. Finalisation changes lifecycle fields only; business content,
`report_id` and every bound artifact stay byte-identical. Final means verified for integrity — never
approved, decided, accepted or executed.**

The verifier is not an analysis, synthesis, recommendation, research, forecasting, anomaly, scoring or
ranking engine, not a report editor, and not an execution system.

### 1. Scope: what is verified and what is finalised

| Artifact | Verified | Finalisable | Why |
|---|---|---|---|
| `ExecutiveReportResult` (draft) | Yes, as a subject | **Yes** | ADR-0033 §13 |
| `DecisionResult` (draft) | Yes, as a subject | **Yes** | ADR-0032 §13; also a precondition for a final report that includes packages (ADR-0033 §13) |
| `SynthesisSet` | As the bound foundation of a subject | No | No lifecycle (ADR-0022) |
| `StrategyResult` | As a bound component | No | No lifecycle (ADR-0031); a verified record is still a class-7 draft recommendation for a person |
| SWOT record | As a bound component | No | No lifecycle (ADR-0030) |
| `AnalysisSet`, `KPIResult`, `AnomalySet`, `EvidenceSet` | Only through the set's registry and statements | No | Not direct inputs (ADR-0022, ADR-0033 §1) |
| `ForecastSet` | Never | No | No approved synthesis path; the verifier reads none |

**Order of finalisation is fixed by the precondition:** packages are verified and finalised first; a
report meant to be final is assembled over those **final package objects** (ADR-0033 §8 already shows a
package's lifecycle "exactly as carried"), and that report draft is then verified and finalised. A report
draft that includes a draft package can never pass (§6, `lifecycle.packages_final`).

### 2. What the verifier never verifies

Verification checks faithful, reproducible representation of already-supported artifacts. It never
decides, and a passed verification never implies:

- whether a recommendation is strategically sound or an option wise (ADR-0032 Consequences: human review);
- whether a risk is serious enough, a tradeoff weighed well, or an interpretation's reasoning persuasive
  beyond its grounding chain;
- whether an external source is true — `SOURCED` content stays **untrusted** in a final artifact;
- whether a forecast is economically right (no forecast reaches a report);
- whether a materiality threshold, a KPI target or the Business Context is appropriate.

"**Challenging conclusions / interpretations**" (ADR-0006, ADR-0032 §13, ADR-0033 §13) is defined as
this deterministic re-challenge: every conclusion is re-grounded by its owning engine against the set as
it now stands — the citation rule, the interpretation-support chain, the ADR-0031 figure rule on every
authored text, and confidence re-derivation — by reproduction (§5). A conclusion that no longer grounds
fails. Soundness remains human review.

### 3. Inputs

| Input | Status | Rule |
|---|---|---|
| Draft subject | **Required, exactly one** | `type(...) is ExecutiveReportResult` or `DecisionResult`, built by its engine's `build()`, `lifecycle` `draft`. A serialised copy, a look-alike, a dict or a final object is refused before any check (§9) |
| Recomputation reply | **Required when the brief requests any figure**; absent otherwise | The verbatim stdout of `verification recompute` run by `biq-analysis-verifier` over the brief issued for this draft (§5.3). Parsed as untrusted data against a closed schema |
| Everything else | **Not inputs** | The verifier reads the set, components, retained inputs and configuration **from the draft object's own held references**. No parameter exists for a synthesis set, component, finding, status, lifecycle, confidence, trust, verification state or recomputed value, so none can be caller-supplied |

### 4. The binding graph

```
ExecutiveReportResult ── identity + SHA-256(set.to_json()) ──▶ SynthesisSet ──▶ registry (KPIResult, findings, datasets+basis, evidence sets)
        │── identity + SHA-256(to_json()) ──▶ StrategyResult ── identity + digest ──▶ same SynthesisSet
        │── identity + SHA-256(to_json()), supplied order ──▶ DecisionResult | FinalDecisionResult ──▶ same SynthesisSet, same StrategyResult object
        └── reproduction digest SHA-256(swot.to_json()) ──▶ SWOT record ──▶ rebuilt over same SynthesisSet
```

**Both identity and digest are required** wherever an object is bound; identity alone would accept an
object mutated in place, and a digest alone would accept a different object with equal content. The SWOT
record is bound by reproduction, as ADR-0033 decided. The verifier:

- recomputes `strategy.synthesis_digest(set)` and compares it with the draft's bound digest (a changed set
  fails even when identity holds);
- recomputes each component's serialisation digest and compares it with the digest recorded at build;
- confirms the report's `sources` block agrees with the held components one-for-one — an included flag
  with no held object is **missing**; two equal digests or identities are **duplicate**; a component
  whose own binding names a different set object or digest is **wrong-set**;
- confirms every package built with a `StrategyResult` holds the report's `StrategyResult` object;
- recomputes `report_id` by reproduction (§5.2); a draft whose `report_id` differs from the reproduced
  one is a **forged or stale identity**.

### 5. The three verification methods

Every check declares exactly one method. They are never substituted for one another.

**5.1 Source-binding verification** — the artifact is joined to its source by identity, digest and
id resolution, with no recomputation: set and component bindings (§4); every statement id resolving
exactly once through `grounding`; every `SOURCED` statement's evidence ids resolving to evidence items
registered in the set and passing the existing footing rules; and **registry agreement** — every
registered `KPIResult`'s status, value, currency and unit equal the fields of its KPI statement, and
every registered analysis or anomaly finding's `statement`, `observed`, `comparison`, `change`,
`change_pct`, `period` and materiality outcome equal its statement's (closing the gap the Context table
names). External figures are verified **only** this way: nothing is fetched and nothing external is
recomputed.

**5.2 Reproduction and textual equality** — the owning engine rebuilds the artifact from the validated
inputs the draft retained, over the same set object, and the rebuilt serialisation must equal the draft's
**byte for byte** (exact string equality of `to_json()` — the canonical serialisation each engine already
defines; no normalisation, no tolerance):

| Artifact | Rebuilt by | From |
|---|---|---|
| SWOT | `swot.build(set, placements)` | the record's own placements (as ADR-0033) |
| `StrategyResult` | `strategy.build(set, proposals)` | the proposals it retained |
| `DecisionResult` | `decision_support.build(set, request, strategy_result, config)` | the request and configuration it retained |
| `ExecutiveReportResult` | `executive_report.build(set, request, strategy_result, swot, decision_results, config)` | the request, components and configuration it retained |

Reproduction re-runs every rule in its one home — grounding, citation, figure rule, confidence
derivation, preference, summary selection, section assembly, `report_id` — so the verifier contains no
second copy of any of them. In addition, located **textual-equality** checks (§6) compare named parts
with their sources so that a failure says *where* and *what*, not merely that bytes differ. Reproduction
and located checks are both mandatory.

**5.3 Blind recomputation** — the headline figures are recomputed from the fingerprinted source by the
deterministic engines in a separate process that never sees the claimed values.

- **Headline figures (exact).** For a report: the figure fields (`observed`, `comparison`, `change`,
  `change_pct`, `period`), statement text and materiality outcome of **every engine-footed statement the
  report shows in any section** (a statement whose provenance includes a `kpi`, `analysis` or `anomaly`
  reference — this contains ADR-0033's minimum of the summary's statements, and adds findings and
  anomalies); and the `status`, `value`, `currency` and `unit` of **every KPI scorecard row**. For a
  package: the same fields of every engine-footed statement its evidence part cites. Figures inside
  recommendation or package **text** are verified by textual equality through the ADR-0031 figure rule
  during reproduction, never recomputed. `SOURCED` figures: source binding only. Report-level counts
  (`materiality_not_assessed`, `conflict_count`, `limitation_count`, `availability`): reproduction, not
  recomputation.
- **Recomputation basis.** Each registered `KPIResult` and `AnalysisSet` reached through the command path
  carries a basis recorded at registration: `command_id`, `source` (local path) and `source_sha256` of the
  bytes ingested. A headline figure with no basis is **not recomputable** and blocks finalisation; the
  verifier never guesses a command or a file.
- **The brief** (`verification.recomputation_brief(draft)`): closed, content-addressed `brief_id`
  (`rcb-` + 12 hex), listing per basis the command id, source path, `source_sha256` and the requested
  `kpi_id`s and `analysis_id`s. It carries **no** claimed value, statement text, report content,
  framing, research content or recommendation. An empty request list means recomputation is
  `not_required` and no agent is dispatched.
- **Execution.** The orchestration writes the brief to the session scratchpad and dispatches
  `businessiq:biq-analysis-verifier`, whose only action is to run `python -m biq.verification recompute
  <brief>` and return its stdout **verbatim** (the ADR-0017 pattern). The command hashes the source,
  refuses on a mismatch, runs `commands.run()` locally with configuration resolved the usual way, and
  emits recomputed fields for exactly the requested ids.
- **Comparison.** `verify()` parses the reply against a closed schema, requires its `brief_id` to equal
  the brief it issues for this draft, requires one entry per requested id and none other, and compares
  each recomputed field with the draft's by exact canonical string (`str(Decimal)` as the engines emit —
  ADR-0002; no tolerance, no rounding).
- **Why blind.** The recomputing context cannot anchor on a value it never received, and a fabricated or
  corrupted reply does not match except by recomputing correctly. A failed, empty or unparseable reply is
  `recomputation.reply` failed; it is never retried with edits and never substituted by an in-process
  shortcut — `verify()` has no parameter that accepts recomputed values as objects.

### 6. The check catalogue and categories

A check has a stable `check_id` (`<category>.<name>`), a category, a method, the subjects it applies to
(`report`, `package`), and outcome `passed`, `failed`, `not_applicable` or `not_run` (`not_run` only
where an earlier failed check makes it meaningless, e.g. every check after `input.genuine_draft` fails).
**Every applicable check runs every time; there is no short-circuit after the first failure.** The
catalogue below is the mandatory minimum for the implementation milestone:

| Category | Checks (method) | Fails when |
|---|---|---|
| `input_integrity` | `input.genuine_draft` (binding) | subject not engine-built, not a draft, or verification already `verified` |
| `binding_integrity` | `binding.synthesis` (binding) · `binding.strategy` · `binding.decision_packages` · `binding.swot` (reproduction digest) · `binding.sources_record` | identity or digest differs; component missing, duplicate or wrong-set; `sources` disagrees with held components |
| `synthesis_integrity` | `synthesis.genuine_strict` · `synthesis.quality_grade` · `synthesis.statement_ids` · `synthesis.registry_agreement` (all binding) | not genuine, strict, non-empty or fully graded; `CRITICAL`; an id resolves other than once; a registered object disagrees with its statement |
| `reproduction_integrity` | `reproduction.swot` · `reproduction.strategy` · `reproduction.decision_package` · `reproduction.report` (reproduction) | rebuilt serialisation differs by any byte, including `report_id` |
| `figure_recomputation` | `recomputation.reply` · `recomputation.source` · `recomputation.kpi` · `recomputation.statement` (recomputation) | reply missing, malformed, for another brief, incomplete or extra; source hash differs; any recomputed field differs; a headline figure has no basis |
| `section_integrity` | `section.set` · `section.order` · `section.status` · `section.availability` (textual equality) | not exactly the eleven ADR-0033 sections; order differs; a status not permitted for that section, or a reason not the fixed text; summary availability disagrees with the sections |
| `content_preservation` | `content.statements` · `content.summary` · `content.kpi` · `content.anomalies` · `content.strategy` · `content.swot` · `content.decision_packages` · `content.evidence_and_uncertainty` (textual equality) | any shown statement detail differs from `strategy.statement_detail()` for that id now, or is out of set order; the summary is not the ADR-0033 §4 selection; KPI rows differ from the registry or catalogue order; an anomaly block differs from its resolved finding or lacks the investigation note; a Strategy result, SWOT record or package differs from its source's `as_dict()` or its order; conflicts, limitations, assumptions, unsupported statements, unresolved dimensions or component confidences differ from their sources |
| `provenance_integrity` | `provenance.evidence_kinds` · `provenance.owned_content` · `provenance.framing` · `provenance.external_trust` · `provenance.outlook` (textual equality) | an evidence block holds anything but `FACT`/`CALCULATION`/`SOURCED`, or an interpretation lacks verified supports; an `ASSUMPTION` appears outside assumptions; a recommendation id, package part, framing text, metadata or verification artifact appears as a statement; framing is not verbatim with origin `user`; a `SOURCED` entry is not `untrusted`; `outlook` is not `not_available` with its fixed reason and no statements |
| `lifecycle_integrity` | `lifecycle.draft_input` · `lifecycle.packages_final` (binding) | the subject's lifecycle fields are not the draft constants; a report includes a package that is not a final object whose own verification passed and still binds |
| `boundary_integrity` | `boundary.fixed_text` · `boundary.forbidden_fields` (textual equality) | a human-decision, trust, order, lifecycle or no-decision text differs from its engine constant; any key for score, weight, rank, priority, severity, likelihood, rating, colour, target, owner, due date or execution state exists |
| `schema_integrity` | `schema.subject` · `schema.components` (textual equality) | a serialisation fails its closed schema |

Package subjects use the same catalogue with the report-only checks `not_applicable`, plus the
twelve-part order enforced by `reproduction.decision_package` and `content.decision_packages`.

**Findings.** Each failed check produces one finding per located failure:

| Field | Meaning |
|---|---|
| `finding_id` | `vf-` + 12 hex over `check_id`, component, location, expected, observed |
| `check_id`, `category`, `method` | from the catalogue |
| `component` | `{kind: report\|synthesis_set\|strategy_result\|swot\|decision_package\|dataset, ref}` — `report_id`, set digest, recommendation id, package digest, dataset id |
| `location` | section name and JSON pointer within the subject, or `null` |
| `expected`, `observed` | the condition and value as strings, redacted to ids and digests where the value is a figure or text (figures stay local, but a finding never becomes a second copy of report content) |
| `message` | fixed text per check; never model-written |

**Blocking.** There is no severity, no warning tier and no priority — `severity` is Decision Support's
business vocabulary and is not reused. **Every finding blocks finalisation.** Conditions that are valid
states are not findings at all: a `WARNING` quality grade, `outlook` `not_available`, an empty or
`not_supplied` section, no material statement, research-only sets with `recomputation` `not_required`.

**Ordering is presentation, never ranking.** Checks follow the catalogue order above. Findings follow
their check's position, then section order (ADR-0033 §3), then component position (set order, record
order, supplied package order), then JSON pointer lexically.

**Confidence and trust.** Verification output carries **no confidence and no trust grade**. A finding is
a deterministic statement about integrity, not an evidence class; a pass raises no statement's
confidence, support or trust, and never makes external content trusted.

### 7. `VerificationResult`

Built only by `verification.verify()`; closed schema `lib/schemas/verification.schema.json`.

| Field | Shape |
|---|---|
| `schema_version` | `"1.0.0"` |
| `analysis` | const `"verification"` |
| `verified_by` | const `"biq-analysis-verifier"` — the verifying capability, not a class-7 issuer |
| `verification_id` | `^ver-[0-9a-f]{12}$`, content-addressed over `subject`, `checks` and `findings` |
| `subject` | `{kind: executive_report\|decision_package, report_id (report) , digest: sha256 of the draft's to_json()}` |
| `status` | `passed` \| `failed` |
| `finalisation_permitted` | boolean, `true` iff `status` is `passed` iff `findings` is empty |
| `synthesis_digest` | the set digest recomputed at verification |
| `components` | `strategy {digest}` · `swot {digest}` · `decision_packages [{digest, lifecycle, verification_id}]` in supplied order |
| `recomputation` | `{status: completed\|not_required\|failed, brief_id, bases: [{dataset_id, command_id, source_sha256_recorded, source_sha256_observed}], figures_checked}` — counts and hashes, never figures |
| `checks` | every catalogue check with `check_id`, `category`, `method`, `outcome` — what was checked |
| `findings` | as §6, ordered as §6 |
| `verification_note`, `human_decision`, `trust_statement` | fixed engine-owned text |

**No timestamp.** Verification is a pure function of its inputs; a clock would break `verification_id`,
idempotence and byte-identical repetition. A presentation may state when it was shown, outside the
artifact.

`verify()` **returns** a `failed` result for a genuine draft that does not pass — the record of what
failed is the output — and **raises** `VerificationError` only for inputs that are not a genuine draft
(§9). `render(result)` formats it once, adding no finding and no explanation of its own.

### 8. Lifecycle and finalisation

```
build() ──▶ draft ──verify()──▶ VerificationResult(failed) ──▶ draft unchanged; finalise() refuses
                  └─verify()──▶ VerificationResult(passed) ──finalise(draft, result)──▶ final object
```

- **States:** `draft` and `final` only. `verification` is `unverified` (draft) or `verified` (final).
  No `verified`, `pending`, `almost final` or `rejected` lifecycle; no state is written onto the draft.
- **`finalise(draft, verification)`** requires `type(verification) is VerificationResult` produced by
  `verify()` **for this draft object** (it holds the draft reference and digest), `status` `passed`, and —
  re-checked at the moment of finalisation — the draft and every component still bound with their
  recorded digests. Any failure raises; nothing is emitted.
- **The final object** (`FinalExecutiveReportResult`, `FinalDecisionResult`) holds the unedited draft and
  the `VerificationResult`, has no setters, and exposes read-only `draft` and `verification`.
- **What changes, exactly.** Final serialisation is the draft's `as_dict()` with only these fields
  replaced — for a report: top-level `lifecycle` → `final`, `verification` → `verified`, `lifecycle_note`
  → the final note, and the same three fields inside `sections.reporting_frame`; for a package: the three
  top-level fields — plus one added top-level `verification_record`: `{verification_id, verified_by,
  subject_digest, synthesis_digest, recomputation_status, brief_id}`. **Everything else is byte-identical**,
  and final serialisation proves it every time: restoring those fields and removing `verification_record`
  must reproduce a serialisation whose SHA-256 equals `subject_digest`, and the draft must still be bound;
  otherwise serialisation refuses. A stale final is refused, never downgraded to draft.
- **`report_id` is unchanged by finalisation**: ADR-0033 §14 computes it over synthesis digest, component
  digests and framing, none of which change. A final report's identity is the pair (`report_id`,
  `verification_id`); a final package's is (draft digest, `verification_id`). A report assembled over
  final packages binds their final serialisation digests and therefore has its own, different
  `report_id` — it is different content.
- **Repetition and idempotence.** `verify()` over the same draft, set state, retained inputs and source
  bytes returns a byte-identical `VerificationResult` with the same `verification_id`; `finalise()` over
  the same pair returns an equal final object and stores nothing. A failed draft is never repaired or
  retried into a pass: correcting it means building a new draft through the owning engines and verifying
  that. Passing a final object to `verify()` or `finalise()` is refused — re-verify its `draft`.
- **No M10 path changes:** `build()` still produces drafts only.

### 9. Failure and empty states

| Situation | Behaviour |
|---|---|
| Not a genuine draft: serialised, look-alike, dict, forged token, final object, unknown type | `VerificationError`; no result |
| Genuine draft, set or component mutated, missing, duplicate or wrong-set | `failed` result with `binding_integrity` findings; draft unchanged |
| Forged or stale `report_id` / report content | `failed` (`reproduction.report`, `content.*`) |
| Registered KPI or finding changed in memory | `failed` (`synthesis.registry_agreement`, `recomputation.*`) |
| Recomputation needed but agent failed, reply absent, malformed, for another brief | `failed` (`recomputation.reply`) |
| Source file changed or unhashable | `failed` (`recomputation.source`) |
| Headline figure with no recomputation basis | `failed` (`recomputation.statement` or `.kpi`) |
| Report includes a draft package | `failed` (`lifecycle.packages_final`) |
| Research-only set, no engine-footed statement | recomputation `not_required`; may pass |
| Every check passes | `passed`, no findings; `finalise()` permitted |
| `finalise()` with a failed, foreign, serialised or stale verification | refused; nothing emitted |

### 10. Human-decision boundary

Verification is a technical integrity check; human approval is a business decision; they never merge.
Fixed text, engine-owned:

> **Final note.** *Final report. The analysis verifier confirmed that this report faithfully and
> reproducibly assembles the artifacts it is bound to and that its figures recompute from their source.
> Final means verified for integrity. It does not mean that any recommendation was accepted, any option
> chosen, any decision made or approved, or any action authorised.*

> **Verification human-decision statement.** *Verification checks integrity, not wisdom: it records no
> approval and makes no decision. Acting on anything in a final report or package - a system write, a
> message, an export or an overwrite - still needs a person's decision and explicit per-action approval,
> and financial transactions are prohibited.*

Verifying and finalising are read-only, local and in memory: no approval (ADR-0010). Writing a final
report as a new file in `./businessiq-output/`, overwriting, exporting or sending follow `CLAUDE.md` §9
unchanged, and any copy keeps its lifecycle and `verification_id`.

### 11. Persistence

In memory only, beside the draft: the `VerificationResult` and the final object that holds both. **No
file, database, ledger or cache is written by the verifier.** The brief and reply live in the session
scratchpad as transient working files, exactly as research replies do (ADR-0017); they carry ids, local
paths and hashes, never figures or text. A future persisted verification record needs its own decision.

### 12. `biq-analysis-verifier` and the model boundary

- **The canonical verifier is deterministic Python.** Every check, comparison, pass, fail and
  finalisation is decided by `lib/python/biq/verification.py`. **No model is in the core verification
  path.**
- **The agent** is ADR-0006's independent-verification subagent, and its independence is now concrete:
  a separate context and process that receives only the blind brief. Definition
  `agents/biq-analysis-verifier.md`, registered as the scout is; tool grant **`Bash` only** (to run the
  engine over the local dataset) — no `WebSearch`, `WebFetch`, `Write`, `Edit` or `Task`; holds no logic
  (`CLAUDE.md` §3). A boundary test asserts the declared grant, as for the scout (ADR-0014).
- **The agent's model may:** run the one fixed recompute command over the brief path it was given, and
  return stdout verbatim; report that the command failed.
- **The main-thread model may:** sequence the flow; present `verification.render()` unchanged; explain,
  in plain words, findings that are already listed.
- **No model may:** pass, fail, add, remove, suppress, soften or reorder a check or finding; edit, repair
  or summarise the brief or reply; supply recomputed values; change any report, package, record, point,
  figure, confidence or materiality; set a lifecycle or verification value; call an artifact final
  because it "looks correct"; grant trust; or present a draft or failed verification as final.
- **What leaves the drafting context:** the brief only. No claimed figure, statement text, framing,
  research content or report crosses to the agent.

### 13. Security and fail-closed rules

The implementation must refuse or fail: forged reports (token, `report_id`, content); a changed set,
`StrategyResult`, `DecisionResult` or SWOT; a changed recommendation, preference or SWOT placement; a
changed KPI value or anomaly figure (set, registry or recomputation); caller-supplied verification state,
final lifecycle, confidence, trust, findings or recomputed values; a reply for another brief; a final
report containing a draft package; and re-entry (§14). The verifier module imports no network library,
dispatches nothing and writes no file; the recompute command reads only the briefed local sources.
External content stays untrusted and is quoted, never obeyed. Every failure produces no final artifact.

### 14. No re-entry

`register_claims()` refuses, as it refuses recommendations, packages and reports: a `VerificationResult`
and its dict; any finding or check record; `FinalExecutiveReportResult`, `FinalDecisionResult` and their
dicts; and any record with `analysis: verification` or a verification-only field (`verification_id`,
`verified_by`, `verification_record`, `finding_id`, `check_id`, `brief_id`, `finalisation_permitted`).
No engine `build()` accepts a verification artifact as evidence. Report → verification → synthesis trust
laundering is closed.

### 15. What makes an artifact final

A report or package becomes `final` **only** when all hold:

1. the subject is a genuine draft built by its engine;
2. `verify()` ran every applicable mandatory check over it — binding, synthesis, reproduction, blind
   recomputation, sections, content, provenance, lifecycle, boundary and schema;
3. the `VerificationResult` has no finding (`status` `passed`);
4. for a report, every included package is a final object whose own verification passed and still binds;
5. at `finalise()` the draft, the set and every component are still bound with the digests verification
   recorded;
6. `finalise()` returns the final object without error.

**Human business approval is not part of this lifecycle and is never implied by it.**

## Reason

Option D keeps every accepted decision at once. ADR-0006's verifier agent gets a real, testable
independence — a context that never saw the numbers — instead of an ornamental role or a model verdict.
ADR-0002 holds: figures are recomputed by code and compared by code. ADR-0032 §13 and ADR-0033 §13 are
honoured literally: headline figures recomputed against the engines, conclusions re-challenged, bindings
and digests confirmed, components shown whole, the draft never edited, verification recorded beside it.
Reproduction through the owning engines means no rule gets a second home (ADR-0012). And the code facts in
Context — live-object binding, the unhashed registry, the missing source fingerprint — are each closed by
a named check rather than assumed away.

## Consequences

**Positive.** A final artifact is checkable end to end and reproducibly: same inputs, same verification
id. No model can finalise anything. The human-approval line is fixed text in both directions. Drafts and
the M10 engines keep their behaviour.

**Negative.** Finalisation needs the original source file, unchanged, on this machine, and the command
path's recomputation basis; a report whose internal figures were registered outside the command path can
stay a draft forever. A report with packages needs two verification passes (packages, then report).
`Bash` gives the agent a shell, so its "no web" property is a declared grant, not a sandbox — the brief
carrying no figures is what limits exposure. The orchestration is model-mediated, as ADR-0015 already
accepts for the scout: a context that skipped the agent could run the recompute command itself; blindness
of the brief, the reply's `brief_id` binding and the command file's sequencing tests are the controls.
"Verified" is narrower than a lay reader may assume, which is why the final note says so.

**Follow-up required — the M11 implementation milestone.**

- **New:** `lib/python/biq/verification.py` (`recomputation_brief`, `recompute` CLI, `verify`,
  `finalise`, `render`, `VerificationResult`, `FinalExecutiveReportResult`, `FinalDecisionResult`,
  `VerificationError`); `lib/schemas/verification.schema.json`; `agents/biq-analysis-verifier.md` with its
  boundary test; focused tests covering every check, every row of §9 and the re-entry refusals.
- **Additive seams, not policy:** a recomputation basis (`command_id`, `source`, `source_sha256`)
  recorded per registered `KPIResult` and `AnalysisSet` on the command path, with the source hashed at
  ingestion; read-only retention of validated inputs — `StrategyResult` proposals, `DecisionResult`
  request and configuration, `ExecutiveReportResult` request, configuration and component references;
  `executive_report.build()` accepting `FinalDecisionResult` objects and showing their lifecycle as
  carried; the `register_claims()` refusal extended (§14).
- **Schema extensions:** `decision_support.schema.json` and `executive_report.schema.json` admit `final`
  with `verification: "verified"`, the final note and a required `verification_record`; drafts are
  unchanged; the mirrored definitions stay pinned by test.
- **Orchestration:** `/executive-report` and `/decision-support` gain an opt-in finalisation step that
  issues the brief, dispatches the agent, verifies and finalises, presenting the draft with its findings
  when verification fails. No new command.
- **Not part of it:** a forecast translator; `biq-data-profiler` (separate M11 item); any persisted
  verification record; any model review of reasoning quality.

## Revisit when

- A synthesis forecast translator is approved (adds outlook checks and recomputation of forecast figures).
- A verification record must persist across sessions or leave the machine.
- A second source kind needs recomputation (connector data, M12) without a file to hash.
- A computable, defensible review of reasoning quality is proposed as a separate, non-finalising step.
- ADR-0006's agent topology is reopened.
