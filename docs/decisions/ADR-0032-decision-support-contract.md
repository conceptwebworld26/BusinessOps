# ADR-0032 — The Decision Support contract: a twelve-part draft decision package beside the synthesis set

**Date:** 2026-09-16
**Status:** Accepted
**Deciders:** Project owner (M10.3.3-A brief, which supplied the twelve-part working framework), recorded in M10.3.3-A (decision only)
**Relates to:** ADR-0010 (approval), ADR-0022 (synthesis contract), ADR-0030 (SWOT), ADR-0031 (recommendation contract, unchanged). No accepted ADR is amended.

## Context

`architecture.md` §4 has described `biq-decision-support` since Revision 1 as "the 12-part
framework". A repository-wide search in the M10.3.3 readiness review found the phrase **named and
never defined**: no development record, reference document, ADR or component lists the twelve
parts. It is the same gap as documentation debt D-01, D-02 and D-06, whose recorded common root is
the product specification that was never committed. Everything else about Decision Support was
equally thin:

- ADR-0010 and `CLAUDE.md` §9 class decision support as read-only analysis and a "decision
  package" as draft generation needing no approval.
- ADR-0031 settles that Decision Support **shares the class-7 recommendation record contract
  unchanged**, with `issued_by` distinguishing the issuer, and leaves its container, its framework
  and whether it consumes a `StrategyResult` undecided.
- `architecture.md` §10 says `biq-analysis-verifier` (M11) runs "before `/executive-report` and
  `/decision-support` finalise", but "finalise" is undefined — and the plan lists M11 as depending
  on M10, which reads as circular.
- `reference/output-standards.md` defines no decision-package shape.
- Business Context (`business_context.schema.json`) holds identity, reporting preferences, KPI
  overrides, materiality thresholds and terminology. It holds **no** objective, constraint or
  decision field.

The M10.3.3-A brief supplied a twelve-part working framework to reconcile against the approved
architecture: Decision Question · Business Context · Objective / Desired Outcome · Options ·
Decision Criteria · Evidence · Assumptions · Tradeoffs · Risks · Expected Outcomes / Benefits ·
Recommendation / Decision Guidance · Uncertainty, Limitations & Next Steps.

## Problem

Define what Decision Support produces, from what, and under which existing rules — precisely
enough to implement and test — without a second recommendation contract, a second confidence or
materiality system, a scoring framework, or any change to ADR-0031.

## Reconciliation of the proposed framework

Each part was checked against the approved contracts. None contradicts them; five needed their
terms fixed so they cannot weaken an existing rule:

| Part | Conflict risk | Resolution |
|---|---|---|
| 2 Business Context | Context used as evidence | Framing only, as ADR-0030/0031 already hold; no citable form |
| 3 Objective | An objective the model infers becomes a claim nobody made | User-supplied only; Business Context has no objective field, and inferring one would be guessing (ambiguity protocol) |
| 5 Criteria | Weights or scores become a hidden ranking | No weight, score or rank field; numeric thresholds only with a stated origin |
| 11 Recommendation / Decision Guidance | "Guidance" becomes a second recommendation kind | Guidance is class-7 records under ADR-0031 plus at most one preferred option under a strict grounding rule |
| 12 Next Steps | Next steps become executable actions or unstructured advice | Next steps are evidence gaps tied to a limitation, conflict or unresolved dimension the package carries |

The framework is therefore adopted with those resolutions. The phrase "12-part framework" in
`architecture.md` §4 now means the twelve parts defined here.

## Decision

**Decision Support produces a `DecisionResult`: a draft, twelve-part decision package held beside
one genuine strict `SynthesisSet`, never inside it.** It structures a user's decision question
around options, criteria, evidence, tradeoffs, risks and expected outcomes; issues or packages
recommendations only through ADR-0031's class-7 record contract; derives every confidence from
existing reason codes; scores and weights nothing; and names a preferred option only when explicit
criteria and a grounded recommendation support it. Every `DecisionResult` produced before M11 is a
**draft**; "finalise" means the M11 verifier moving a draft to **final**.

### 1. Input contract

| Input | Status | Rule |
|---|---|---|
| Genuine strict `SynthesisSet` | **Required** | ADR-0030/0031 identity rules through `synthesis/grounding.py`: `type(...) is SynthesisSet`, strict, non-empty, every item graded. Never bypassed |
| Decision question | **Required**, user-supplied | Non-empty text. Absent or ambiguous → ask (ambiguity protocol); never inferred from data or context |
| Objective / desired outcome | Optional, user-supplied | Absent → recorded as not stated; never inferred |
| Options | Optional, user-supplied | Plus options formed from recommendation records and the status quo (§4). Fewer than two options in total → no package; ask |
| Criteria | Optional, user-supplied | Plus materiality thresholds from resolved configuration where the user asks for them (§5). None → the package has no preferred option |
| `StrategyResult` | **Optional, referenceable** | If supplied, `is_bound_to(synthesis)` must hold for the same set object; its records are packaged unchanged |
| SWOT result | **Not an input** | A SWOT point id is not evidence (ADR-0031); a SWOT consumes the same set independently and may sit beside a package in a command, never inside it |
| Business Context | Framing only | `subject`, `business_model`, `currency` through the set; public identity fields for framing text; never evidence |

User-supplied text (question, objective, options, constraints, criteria) is **framing**: stored
verbatim with `origin: "user"`, local only, never a synthesis statement, never evidence, never
transmitted.

### 2. The twelve parts

Field names are the contract; type shapes are contract-level, for the M10.3.3 schema to encode.
"Evidence" always means a list of synthesis statement ids resolved in the grounding set.

| # | Field | Purpose | Required | Shape | Evidence / provenance | Confidence / uncertainty | Interpretation? | Recommendation? | Business Context may populate? |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `decision_question` | What is being decided | Yes | `{text, origin: "user"}` | None — framing, never evidence | None | No | No | No |
| 2 | `business_context` | Who is deciding, framed | Yes (fields may be null) | `{subject, business_model, currency, constraints: [{text, origin: "user"}]}` | None — framing | None | No | No | Yes for `subject`, `business_model`, `currency`; constraints are user-supplied only |
| 3 | `objective` | The outcome the user wants | Yes (may be not stated) | `{text \| null, origin: "user" \| null, stated: bool}` | None — framing, never evidence | None | No | No | No |
| 4 | `options` | The courses of action compared | Yes, at least two | `[{option_id, label, origin: "user" \| "recommendation" \| "status_quo", recommendation_id \| null}]` | An option needs no evidence to exist; every claim **about** it must cite evidence | Per option, derived (§8) | No | Only as a reference to a record | No |
| 5 | `criteria` | What the user says matters | Yes (may be empty) | `[{criterion_id, text, origin: "user" \| "configuration", source: str \| null}]` | None — framing; a `configuration` criterion names the resolved threshold key and its provenance | None | No | No | Only materiality thresholds, through configuration |
| 6 | `evidence` | Every statement the package cites | Yes, at least one | `[evidence_detail]` — the ADR-0031 per-statement detail: id, kind, class, origin, domain, trust, statement, support, confidence and reasons, materiality, conflict refs, unresolved dimensions, chain, verified supports | Resolved through `grounding`; eligible kinds and disqualifying support exactly as ADR-0031 | Carried per statement | Interpretations with verified supports only | No | No |
| 7 | `assumptions` | What the package depends on but cannot evidence | Yes (may be empty) | `[{synthesis_id, statement, support, confidence, confidence_reasons, referenced_by: [ids]}]` | Must resolve to a registered `ASSUMPTION` statement; never evidence | Each lowers the confidence of whatever references it (ADR-0031) | No | No | No |
| 8 | `tradeoffs` | What choosing one option gives up relative to another | Yes (may be empty) | `[{tradeoff_id, option_ids: [≥1], criterion_ids: [], text, evidence: [≥1], assumption_ids: [], confidence, confidence_reasons}]` | At least one evidence id; figures quoted only | Derived per tradeoff | Yes — a labelled reading of the cited evidence | No | No |
| 9 | `risks` | What could go wrong with an option | Yes (may be empty) | `[{risk_id, option_id, text, evidence: [], confidence, confidence_reasons}]` | Evidence optional; an unevidenced risk is labelled as such and may contain no figure | Derived; no evidence → `LOW`, `insufficient_evidence` | Yes, labelled | No | No |
| 10 | `expected_outcomes` | What an option is expected to produce | Yes (may be empty) | `[{outcome_id, option_id, text, evidence: [≥1], confidence, confidence_reasons}]` | At least one evidence id; ADR-0031 expected-benefit rule | Derived per outcome | Yes, labelled | No | No |
| 11 | `guidance` | Recommendations and, where grounded, a preferred option | Yes | `{recommendations: [record], preferred_option: option_id \| null, preference_basis: {recommendation_id, criterion_ids} \| null, no_preference_reason: text \| null, divergences: [{recommendation_ids, note}]}` | Records under ADR-0031 exactly | Records carry derived confidence; the preference carries the confidence of its recommendation | Only inside records | Yes — class-7 records only | No |
| 12 | `uncertainty` | What is uncertain, missing or contested, and what would reduce it | Yes | `{confidence, confidence_reasons, options: [{option_id, confidence, confidence_reasons}], conflicts: [], limitations: [], unresolved_dimensions: [], next_steps: [{text, addresses: {kind: "limitation" \| "conflict" \| "unresolved_dimension", ref}}]}` | Every next step references a limitation code, conflict id or unresolved dimension the package carries | Package and per-option confidence derived (§8) | No | No | No |

### 3. Evidence and provenance

- **One set, resolution not text.** Every evidence id resolves in the grounding set through
  `synthesis/grounding.py`; unknown, ambiguous, out-of-set and non-statement ids (SWOT point,
  recommendation, evidence-item, candidate-claim) are refused — ADR-0031 rules 1–3, unchanged.
- **Eligible evidence** is `FACT`, `CALCULATION`, `SOURCED`, or an `INTERPRETATION` whose supports
  pass the shared checks. `unsupported` and `insufficient_evidence` statements are refused. Mixed
  internal and external evidence is allowed; each statement keeps its own origin, domain, trust and
  class.
- **Minimum.** A package cites at least one evidence statement somewhere; a package citing none is
  not produced, because it would present a decision with nothing under it (fail loudly).
- **Recommendation records** are admitted as evidence **only for the guidance part**, and only as the
  records themselves: a record never supports a tradeoff, risk, outcome or another record, because
  recommendations never support recommendations (ADR-0031 rule 6).
- **Conflicts, incomparable values and unresolved dimensions** are allowed and carried, never
  settled — ADR-0031's handling table applies to every part that cites evidence.
- **The evidence part is an index.** It lists exactly the statements cited anywhere in the package,
  each once, in set order; nothing uncited appears in it.

### 4. Options

- **Sources, closed:** user-supplied (`origin: "user"`); one option per recommendation record in
  `guidance.recommendations` (`origin: "recommendation"`, label = the record's action); and the
  status quo (`origin: "status_quo"`, label "Make no change"), included whenever the user does not
  exclude it.
- **BusinessIQ does not generate options freely.** An option the model wants to add is authored as a
  class-7 record under ADR-0031 — with evidence, rationale, expected benefit, risks, dependencies
  and derived confidence — and becomes an option through that record. There is no option generator.
- **At least two options** are required; otherwise no package is produced and the user is asked.
- A user option is framing: it exists without evidence, and any tradeoff, risk or outcome about it
  must cite evidence or be absent.

### 5. Criteria

- **User-supplied**, or a materiality threshold from resolved configuration **when the user asks**
  for it, recorded with `origin: "configuration"` and its source (the precedence chain's origin).
  Business Context contributes criteria only through those configured thresholds.
- **Numeric thresholds** are allowed with that stated origin. They are not evidence and ground no
  figure except by quotation of the criterion itself.
- **No weights, no scores, no ranks.** There is no weight field, criteria are never combined
  numerically, and no option is scored against them. Relating an option to a criterion is a
  tradeoff or outcome with cited evidence, in text.

### 6. Assumptions, tradeoffs, risks, expected outcomes

- **Assumptions** reuse `synthesis.assumption()` statements. They may be named by a recommendation
  dependency (ADR-0031) or by a tradeoff's `assumption_ids`; they are never evidence, never the sole
  basis of anything, and each one makes whatever names it `LOW` through its existing reason codes.
- **Tradeoffs** are first-class records, not a matrix: at least one option, at least one evidence
  id, optional criteria and assumptions, text that is a labelled reading. They may not be inferred
  without evidence.
- **Risks** are per-option records. Evidence is optional because a risk is a caution; an unevidenced
  risk is labelled, derives `LOW`, and may state no figure. There is no likelihood, severity, impact
  score or risk rating.
- **Expected outcomes** are per-option records with at least one evidence id, qualitative by default,
  quantitative only by quoting a figure a cited statement prints — ADR-0031's expected-benefit rule.
  No estimated value, uplift, saving or return is authored.
- **Figures everywhere.** Every figure in any authored text of the package — tradeoffs, risks,
  outcomes, next steps, a divergence note — must be printed by a statement that part cites, or by a
  criterion that part references; the figure-grounding rule is the ADR-0031 rule, applied by the
  same implementation, and fails closed.

### 7. Recommendations and the relationship to Strategy

- **One contract.** Decision Support issues recommendations only as ADR-0031 class-7 records, with
  `issued_by: "biq-decision-support"`. It packages `StrategyResult` records unchanged, keeping
  `issued_by: "biq-strategy-recommendations"`. No second recommendation contract exists.
- **Strategy is optional, never mandatory.** Decision Support may run with no `StrategyResult`.
- **No overwriting.** Decision Support never edits, re-grades, merges or drops a Strategy record.
- **Contradiction is allowed and visible.** Where a Decision Support record or preferred option
  points a different way from a packaged Strategy record, both records stay whole and
  `guidance.divergences` names the record ids with a note quoting only what the records state.
  Neither has authority over the other; the user decides.

### 8. Confidence and uncertainty

Existing semantics only — `HIGH` / `MEDIUM` / `LOW` from `synthesis.confidence`, existing reason codes,
no new level or code, nothing authored:

- **Record confidence:** ADR-0031, unchanged.
- **Tradeoff, risk and outcome confidence:** `confidence.combine()` over the reason codes of the
  statements (and assumptions) that record cites. None cited → `combine([])` → `LOW` with
  `insufficient_evidence`, which is already the module's behaviour.
- **Per-option confidence:** `combine()` over every tradeoff, risk, outcome and recommendation that
  references the option. An option nothing assesses is `LOW` with `insufficient_evidence`.
- **Package confidence:** `combine()` over the per-option confidences and the guidance records.
- **Missing information** lowers confidence only through those codes and is surfaced as limitations
  and next steps; it is never filled.

### 9. Materiality

Inherited, never re-judged. Each evidence statement carries its own verdict; a configured threshold
may be a criterion (§5); ordering evidence by materiality is presentation only and must be labelled
so. No second materiality framework exists.

### 10. Scoring and prioritisation

- **Prohibited:** numeric scores, weights, ranks, priorities, severity or likelihood ratings,
  attractiveness indices, decision matrices of numbers, "top" or "best" claims, and any ordering of
  options by preference.
- **A preferred option is permitted only when all hold:** at least one criterion exists; the
  preferred option has a class-7 record in `guidance.recommendations` (existing or issued here) whose
  evidence the package's tradeoffs or outcomes relate to those criteria; every other option has at
  least one tradeoff or outcome against the same criteria, or is labelled not assessable; and
  `preference_basis` names the record and criteria. Otherwise `preferred_option` is `null` and
  `no_preference_reason` says why. The preference carries its record's derived confidence, so a
  contested basis makes it `LOW`. At most one option is preferred; the others are not ordered.
- **Order is presentation.** Options: user order, then recommendation records in record order, then
  the status quo. Tradeoffs, risks and outcomes: option order, then the set position of their
  earliest cited statement, then id. The package states that order is not preference.

### 11. Business Context

Framing only (§1–2). It is not evidence, has no provenance kind, cannot be cited, cannot introduce a
figure, and its private fields never leave the machine (ADR-0009).

### 12. Human decision and action boundary

Unchanged (ADR-0010, `CLAUDE.md` §9): producing a decision package is draft, read-only analysis and
needs no approval. BusinessIQ never executes a decision or a recommendation. Next steps are evidence
gaps, not actions; they carry no owner, date, execution state or instruction. Exporting, writing to
a system, communicating a decision, overwriting a file or taking any action needs explicit
per-action approval; financial transactions and source-data modification remain prohibited.

### 13. The M11 verifier and "finalise"

- **Lifecycle:** `lifecycle` is `draft` or `final`. **Every `DecisionResult` produced by M10.3.3 is
  `draft`**, and no M10.3.3 code path can set `final`. A draft is the "decision package … in
  conversation or scratchpad" ADR-0010 already classes as draft generation.
- **"Finalise"** means the M11 `biq-analysis-verifier` independently recomputing headline figures and
  challenging conclusions against a draft and, if it passes, recording a verification beside the
  draft that moves it to `final`. The verifier never edits the package's parts. How it records its
  findings is M11's decision.
- **No circularity.** M10.3.3 does not wait for M11: deterministic Decision Support produces drafts.
  M11 depends on M10 (as planned) because it verifies M10's drafts. `architecture.md` §10 is
  unchanged in substance; this ADR defines the word.
- **Output honesty.** A draft is presented as unverified wherever it appears, including any export
  a user approves.

### 14. Executive Report

Executive Report may consume `DecisionResult`s (draft or final, with the lifecycle shown). It
assembles: it never authors, edits, re-grades, reorders by importance or drops a part, record,
preference, divergence, confidence, conflict, limitation or caveat. Whether it requires `final`
packages is its own milestone's decision; architecture already places the verifier before it
finalises too.

## Security constraints the implementation must meet

1. Consume only a genuine strict `SynthesisSet`; resolve every evidence and assumption id through
   `synthesis/grounding.py`; refuse fake, ambiguous, out-of-set and non-statement ids.
2. A referenced `StrategyResult` must be bound to the same set object; its records are carried
   unchanged.
3. Refuse any authored confidence, support, trust, verification, tier, lifecycle, weight, score,
   rank, priority, severity or likelihood.
4. Preserve every statement's origin, domain, trust and class; external evidence stays untrusted.
5. Never treat source metadata or Business Context as evidence.
6. Apply the ADR-0031 figure rule to every authored text part; fail closed.
7. Never let a decision package or any of its records re-enter synthesis: the `register_claims()`
   refusal must cover decision-package records as it covers recommendation records.
8. Retrieve nothing, dispatch nothing, read no file, transmit nothing; user framing text stays local.
9. Fail closed: a refused package raises and nothing is emitted.

## Consequences

**Positive.** "The 12-part framework" finally means something testable. Decision Support reuses the
synthesis set, the grounding home, the ADR-0031 record contract, the figure rule, the confidence
module and the materiality policy, so it adds structure rather than new policy. A preferred option
exists only where criteria and a grounded recommendation support it. Strategy and Decision Support
can disagree without either silently winning. The M10/M11 sequencing is no longer circular.

**Negative.** A package needs a decision question and at least two options, so an open-ended "what
should we do?" routes to `/strategy-analysis` instead. Without user criteria there is never a
preferred option. Unevidenced risks and unassessed options read `LOW`, which is honest and will look
harsh. Everything before M11 is a draft. The text of tradeoffs and outcomes is checked for evidence
and figures, not for soundness — that remains human review.

## Explicit non-goals

No implementation, schema, skill, command or test; no change to ADR-0031, `evidence.Claim`,
`synthesis.schema.json`, `strategy.schema.json`, the confidence vocabulary or the materiality
policy; no weighting, scoring or ranking framework; no option generator; no Executive Report
design; no M11 verifier design beyond the lifecycle boundary; no live research.

## Implementation implications for M10.3.3

- **New:** a Decision Support engine module, a closed decision schema, `biq-decision-support`,
  `/decision-support`, focused tests, registry changes moving `decision-support` to built while
  `executive-report` stays guarded.
- **Shared, not duplicated:** the ADR-0031 record builder and figure rule must be usable with
  `issued_by: "biq-decision-support"` without changing Strategy's behaviour or its schema's issuer
  constant; the recommendation record rule keeps one home in code. Because `jsonschema_mini`
  resolves only local references, any mirrored record definition in the decision schema must be
  pinned to Strategy's by a test.
- **Additive:** extend the `register_claims()` re-entry refusal to decision-package records.
- **Command input:** a required decision question; optional objective, options, constraints, criteria
  and public research subjects; the internal analysis, research and local-join paths reused as
  `/strategy-analysis` reuses them.
- **Left to implementation within this contract:** id spellings, the exact status-quo label, and how
  a user excludes the status quo.

## Revisit when

- M11 defines how verification is recorded, which may add a field to `final` packages.
- A defensible, computable prioritisation policy is proposed.
- Users need options with no decision question, or a single-option assessment.
- Executive Report needs a part this contract lacks.
