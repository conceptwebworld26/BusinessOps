# ADR-0031 — The strategy recommendation contract: a class-7 claim resolved against a synthesis set, held beside it

**Date:** 2026-09-16
**Status:** Accepted
**Deciders:** Project owner (M10.3.2-A brief), recorded in M10.3.2-A (decision only)
**Refines:** ADR-0022 §5, on *where* recommendations are held. ADR-0022's text is unchanged;
see *Relationship to ADR-0022* below.

## Context

`biq-strategy-recommendations` and `/strategy-analysis` are M10.3.2. They are the first
capability that may issue a **provenance class 7** statement — a proposed action — and every
earlier layer was built to refuse one:

- `evidence.Claim` (ADR-0005) accepts class 7 only with all six `RECOMMENDATION_FIELDS` —
  `evidence`, `rationale`, `expected_benefit`, `risks`, `dependencies`, `confidence` — and the
  action is `Claim.statement`. The check is **truthiness only**: `evidence="e"` constructs.
  `confidence` is caller-supplied. `based_on` is free text, and `Ledger.traceable()` matches it
  against evidential claims' *statement text*, never against an identifier.
  `claim_ledger.schema.json` has conditionals for classes 1, 3 and 4 and **none for class 7**.
- The synthesis layer (ADR-0022) refuses `RECOMMENDATION` at `SynthesisItem` construction,
  refuses advisory wording on every item through `handoff.ADVISORY_MARKERS`, exposes a
  read-only `SynthesisSet.recommendations` that always returns `[]`, and serialises
  `"recommendations": []` with `DEFERRED_NOTE`. `synthesis.schema.json` caps that array at
  `maxItems: 0` and describes a non-empty one as "advice from a layer that has no decision
  owner".
- Synthesis confidence is a **derived conclusion**: `confidence` is in `DERIVED_FIELDS` and
  refused as input, and `synthesis.confidence.assess()` derives `HIGH`/`MEDIUM`/`LOW` from
  named reason codes.
- ADR-0030 established that a Layer-3 consumer reads a genuine strict `SynthesisSet`
  without modifying it, verifies interpretation supports through
  `merge.interpretation_supports()`, and refuses statements graded `unsupported` or
  `insufficient_evidence`.
- **Found while deciding (probed in memory, nothing changed):** `SynthesisSet.register_claims()`
  accepts any record that is not marked verified and carries no non-candidate status. A
  serialised recommendation passed to it today is stored as a citable candidate claim, which
  `sourced_statement(claim_ids=…)` could then cite. No production code produces class 7, so the
  path is latent — but it is a re-entry path.

## Problem

The repository holds unresolved disagreements that M10.3.2 cannot implement around:

1. ADR-0022 §5 says downstream milestones "will fill" the synthesis `recommendations` array
   through `evidence.Claim`; the approved schema caps it at zero and says the synthesis layer
   has no decision owner.
2. `Claim` cannot, by itself, prevent a fabricated or unresolved evidence link.
3. `Claim` takes confidence from its caller; synthesis refuses confidence as an input.
4. `reference/evidence-ledger.md` names *evidence, rationale, expected benefit, risks,
   dependencies, confidence*; `reference/output-standards.md`'s action list names *action,
   rationale, expected benefit, risk, dependency, confidence* — no evidence, singular risk and
   dependency, and no types in either.
5. Partial, contested and incomparable support; the numeric rule for expected benefit; the
   "decision owner"; ordering and priority; propagation of materiality, conflicts,
   limitations and Business Context — none is defined for class 7.

## Existing constraints this decision must respect

ADR-0002 (no model arithmetic in a reported figure) · ADR-0005 (seven closed classes; every
major conclusion traces to class 1–4) · ADR-0009 (internal data stays local) · ADR-0010
(approval follows consequence; generation is read-only; step 19 is not a gate on execution) ·
ADR-0012 (one home per rule; layers depend downward) · ADR-0016 (declared conflicts are never
settled) · ADR-0022 (nothing is promoted; `RECOMMENDATION` is never a synthesis item; the
advisory guard) · ADR-0023 (internal footing) · ADR-0026/0028 (strict footing) · ADR-0029
(a compatible verdict authorises no arithmetic) · ADR-0030 (consumers read, never modify, the
set) · `reference/research-policy.md` (conflicts: present both, lower confidence) ·
`reference/ambiguity-protocol.md` (never guess, never invent) ·
`reference/materiality-policy.md` (never re-judged).

## Options considered — the container

### Option A — Recommendations inside `SynthesisSet.recommendations`

- **ADRs:** matches ADR-0022 §5's forward-looking sentence. Contradicts the approved schema's
  `maxItems: 0` and its "no decision owner" description, the synthesis package charter
  ("decides nothing new … issues no recommendation", stated in `synthesis/__init__.py`,
  `contract.py` and ADR-0022's decision headline), and ADR-0030's read-only consumption.
- **Schema:** `synthesis.schema.json` must change — `maxItems` lifted, a recommendation
  definition added, its description rewritten.
- **`SynthesisSet`:** gains a write API and class-7 validation, so the foundation would hold
  strategy logic; `as_dict`, `summary`, `DEFERRED_NOTE` and the security test pinning the
  empty collection all change.
- **Provenance:** evidence and advice would share the object every consumer reads. A SWOT
  built before and after strategy would read different sets, and the set's byte-identical
  serialisation would depend on which downstream capability had run.
- **Backward compatibility:** breaks the M10.1 serialised contract that `recommendations` is
  empty.
- **Complexity:** higher, and concentrated in a foundational package.
- **Decision Support / Executive Report:** two issuers (`DEFERRED_NOTE` names both strategy and
  decision support) writing into one shared foundation object, with no rule for whose
  recommendations a set holds.

### Option B — Recommendations in a strategy result that references a genuine set

- **ADRs:** consistent with the synthesis charter, the schema as approved, ADR-0012 layering and
  ADR-0030. Refines ADR-0022 §5's sentence on *where* recommendations are filled; keeps its
  substance — class 7 through `evidence.Claim` with all six fields, and "representable and
  unproducible" for the synthesis layer itself.
- **Schema:** `synthesis.schema.json` unchanged; a new isolated strategy schema.
- **`SynthesisSet`:** unchanged except one additive refusal closing the re-entry path above.
- **Provenance:** recommendations cannot become synthesis evidence by construction, because
  they never enter the set; resolution against the set is read-only.
- **Backward compatibility:** fully compatible; nothing existing emits class 7.
- **Complexity:** a consumer module following an established pattern.
- **Decision Support / Executive Report:** both consume or issue through the same record
  contract without contending for a shared object.

### Option C — The evidence `Ledger` as the container

`Ledger` is an existing per-analysis claim store, but it resolves nothing: `traceable()` matches
text, and it has no notion of a synthesis set, a domain or trust. On its own it cannot meet the
anti-forgery requirement. It remains the **audit record** (below), not the container.

## Decision

**Option B.** A strategy recommendation is a class-7 recommendation record, built only by a
deterministic strategy engine module that resolves every reference against **one genuine
strict `SynthesisSet`**. The record's ledger form is `evidence.Claim` with
`provenance_class = RECOMMENDATION`. Records are held in a **`StrategyResult`** beside the set,
never inside it. The synthesis `recommendations` array stays empty permanently and
`synthesis.schema.json` keeps `maxItems: 0`.

### Relationship to ADR-0022

ADR-0022 §5 decided two things: that recommendations are representable but unproducible by the
synthesis foundation, and that they are issued through `evidence.Claim` with all six class-7
fields. **Both stand.** Its sentence "downstream milestones will fill it" described a location
the same milestone's approved schema then closed. This ADR resolves that contradiction in favour
of the enforced contract: the reserved array is a permanent, empty marker that no advice lives in
the evidence layer, and downstream capabilities hold recommendations in their own results. ADR-0022
is not edited; this refinement is recorded in the ADR index.

## Contract definition

### Authored fields — exactly six, supplied by the skill

| Field | Type | Rule |
|---|---|---|
| `action` | string, non-empty | The proposed action. Serialised as `Claim.statement`. |
| `evidence` | list of synthesis statement ids, non-empty | Resolved per *Evidence and provenance* below. |
| `rationale` | string, non-empty | Why the evidence leads to the action. |
| `expected_benefit` | string, non-empty | Per *Expected benefit* below. |
| `risks` | list of non-empty strings, at least one | What could make the action wrong or harmful. |
| `dependencies` | list of records `{text, assumption_id}`, at least one | `text` non-empty; `assumption_id` is `null` or the id of an `ASSUMPTION` statement in the same set. |

Any other authored field is refused — including `confidence`, `support`, `trust`, `verified`,
`source_tier`, `priority`, `rank`, `score`, `weight` and `decision_owner`.

**`confidence` is the sixth class-7 field and is never authored**: it is derived (below) and
written onto the record and its `Claim`. That is how the ledger's six-field rule and the
synthesis rule that confidence is a conclusion are both satisfied.

**Canonical names are these, plural where plural.** `risks` and `dependencies` match
`evidence.RECOMMENDATION_FIELDS`; `action` names the statement. **No aliases** (`risk`,
`dependency`, `benefit`, `statement`) are accepted: no producer has ever emitted them, so there is
nothing to be compatible with, and two spellings would be two representations.

**No field may be empty.** `dependencies` always has a real entry, because every recommendation
depends at least on its cited evidence remaining current and correctly scoped; stating that is a
dependency, not padding.

### Derived fields — computed by the engine, never accepted

`recommendation_id` (content-addressed from the action and the sorted evidence ids) ·
`issued_by` (the issuing capability — `biq-strategy-recommendations` here) · `provenance_class` 7
and label `RECOMMENDATION` · `confidence` and `confidence_reasons` · `support` · `rests_on`
(evidence domains) · `material` · per-evidence detail (kind, evidence class, origin, domain,
trust, support, confidence and reasons, materiality verdict, conflict refs, unresolved dimensions,
provenance chain, and verified supports for an interpretation) · cited assumptions and their
reasons · `limitations` · `caveats` · `conflicts` (full records of every conflict any cited or
assumed statement touches).

### `StrategyResult`

Framing copied from the set (`subject`, `as_of`, `business_model`, `currency`,
`quality_grade`) · the synthesis trust statement · a fixed human-decision statement ·
`recommendations` · an explicit empty state when there are none (*"No supported recommendation
identified."*) · `material_not_cited` (material statements no recommendation cites) · every set
conflict and limitation, carried whole · the set's own confidence. Closed schema; no field for
priority, rank, score or weight at any depth.

### Ledger form

Each record converts to `evidence.Claim(action, RECOMMENDATION, confidence=<derived>,
based_on=<evidence ids>, caveats=<carried caveats>, evidence=…, rationale=…,
expected_benefit=…, risks=…, dependencies=…)`. The six-field rule stays owned by `Claim` and is
not restated. **Traceability of a class-7 claim is established by resolution against the set at
build time, not by `Ledger.traceable()`**, which matches text and is not relied upon here.

## Evidence and provenance rules

1. **One genuine strict set.** The input must be `type(...) is SynthesisSet`, built with
   `require_dimension_provenance=True`, non-empty, every item graded by `add()` — ADR-0030's
   identity rules, unchanged. Every id in a recommendation resolves in **that** set.
2. **Resolution, not text.** Each evidence id must identify exactly one statement. Unknown,
   ambiguous, non-string or out-of-set ids are refused. A SWOT point id, a recommendation id,
   an evidence-item id or a candidate-claim id is not a synthesis statement id and is refused.
3. **Eligible evidence kinds:** `FACT`, `CALCULATION` (internal, internally footed per
   ADR-0023), `SOURCED` (external) and `INTERPRETATION` whose supports pass ADR-0030's
   verification — present once, earlier in the set, not circular, not resting on an
   assumption, and accounting for exactly the provenance the interpretation carries.
4. **Minimum evidential basis:** at least one cited statement must be class 1, 3 or 4, or an
   interpretation whose verified chain reaches one. An interpretation may be the direct basis
   only on that condition.
5. **Assumptions supplement, never justify.** An `ASSUMPTION` statement may appear only as a
   dependency's `assumption_id`, never in `evidence`. It therefore can never be the sole or any
   part of the evidential basis — it is disclosed as something the action depends on.
6. **Recommendations never support recommendations.** They have no synthesis id, so none can be
   cited.
7. **Mixed domains are allowed.** Internal, external and mixed evidence may support one
   recommendation. Each statement keeps its own origin, domain, trust and evidence class; the
   recommendation adopts none of them and upgrades none of them.
8. **Disqualifying support.** A statement graded `unsupported` or `insufficient_evidence` is not
   evidence (ADR-0030). If no eligible evidence remains, no recommendation is issued.
9. **Figures are quoted, never produced.** Every numeric figure appearing in `action`,
   `rationale`, `expected_benefit` or `risks` must appear in the statement text of a cited
   **evidence** statement. A figure in a dependency's `text` may additionally quote its own
   cited assumption, where it remains labelled as assumed. No new figure, difference, ratio,
   share, projection or estimate may be authored (ADR-0002, ADR-0029). The check fails closed.

### Expected benefit

Qualitative by default. It may state a figure **only** by restating one already present in a
cited statement — a `CALCULATION` the engine produced or a `SOURCED` figure with its source — and
that figure keeps its original meaning, period and attribution. There is no numeric
expected-value field, and no estimated benefit, uplift, saving or return may be authored.

## Confidence rules

- **Derived, never supplied.** For each cited evidence statement and each cited assumption, take
  the reason codes the set already derived (`confidence_detail.reasons`) and assess them with
  `synthesis.confidence.assess()`. The recommendation's confidence is
  `synthesis.confidence.combine()` over those assessments: the **weakest** level, with every
  reason pooled.
- **Consequences of that single rule:** any unresolved conflict, unsupported or insufficient
  footing, unavailable provenance or data-quality warning on a cited statement makes the
  recommendation `LOW` (those codes are already `SEVERE`); a cited assumption makes it `LOW`,
  because its provenance is unavailable by definition — consistent with the ledger's "`LOW` when
  heavily assumption-dependent"; one ordinary reason such as tier-C-only support yields `MEDIUM`;
  `HIGH` requires every cited statement to be `HIGH`.
- **No second system.** No new level, no new reason code, no numeric score, no probability. The
  recommendation layer can neither raise nor lower the derived level; uncertainty about the
  action itself belongs in `risks`.
- **Support** is `weakest_support()` over the cited evidence — the synthesis four-state view.

## Conflict and uncertainty handling

| Support condition | Recommendation |
|---|---|
| `unsupported` / `insufficient_evidence` statement | Not evidence; refused |
| No eligible evidence left | Not issued |
| `partially_supported` | Allowed; derived confidence carries the reason (e.g. `tier_c_only_support`) |
| Unresolved conflict touching cited evidence | Allowed; confidence necessarily `LOW`; every touched conflict carried in full with all positions; the conflict is never presented as settled |
| Incomparable values (`incomparable_values`) | Allowed; reason carried; the recommendation may not treat the pair as comparable — and cannot state a gap, because no such figure exists to quote |
| Unresolved dimensions on footed evidence | Allowed; carried per evidence statement with reason codes |
| `LOW`-confidence statement | Allowed; the recommendation is `LOW` |
| Set or statement limitations | Carried; never filtered |

This follows existing policy rather than adding one: research policy says conflicts are
presented and lower confidence, ADR-0016 and synthesis say they are never settled, and the
ambiguity protocol says never guess. Nothing in the repository makes a conflict an absolute
blocker, and this decision does not create one; it makes the conflict impossible to hide.

## Advisory guard

**Unchanged and not relaxed.** Recommendation text is advisory by definition and lives only in
the recommendation record and its class-7 `Claim` — **never** in a `SynthesisItem`. The guard
keeps refusing advisory wording in every synthesis statement, interpretation and sourced
statement, so external content still cannot inject advice upstream. The strategy layer has no
path that turns recommendation text into a synthesis statement, and advice found in retrieved
content never becomes a BusinessIQ recommendation (`TRUST_STATEMENT`).

## Decision owner

**No decision-owner field and no personal identity.** The "decision owner" that `contract.py`
and the synthesis schema name is resolved as two abstract roles:

- the **issuing layer** — the capability that owns the decision to *issue* a recommendation,
  recorded as `issued_by` (`biq-strategy-recommendations`, and later `biq-decision-support`);
- the **business decision** — the user's, per analysis-framework step 19 *Human decision*,
  stated as a fixed sentence on every `StrategyResult`.

## Multiple recommendations, order, priority, scoring

- **Multiple** recommendations are permitted. A duplicate `recommendation_id` is refused.
- **Order** is deterministic and carries no meaning: by the set position of each
  recommendation's earliest cited evidence statement, then by `recommendation_id`. The result
  states that order is not a ranking.
- **Priority, rank, score and weight** are prohibited: no field exists for them, and none is
  derived. No "top", "first priority" or "most important" recommendation is presented.
  The repository has no prioritisation policy and this decision defines none.

## Materiality

Inherited, never re-judged. Each cited statement's materiality verdict is carried unchanged. A
recommendation is `material` when at least one cited evidence statement is material; mixed
materiality is visible per statement; a recommendation resting only on non-material evidence is
permitted and marked `material: false` (immaterial does not mean invisible). No threshold is
applied at this layer.

## Limitations and uncertainty

Carried onto each recommendation: every cited statement's limitations (exact deduplication only),
confidence reasons, unresolved dimensions, conflict records and caveats — including a
pseudonymisation caveat, which must survive into any export request. Carried onto the
`StrategyResult`: every set limitation and conflict, whole, and the set's confidence.

## Business Context

**Framing, never evidence.** It supplies the result's `subject`, `business_model` and `currency`
through the set, and may inform which actions are relevant to the business. It has no provenance
kind, cannot be cited, cannot satisfy the evidential minimum, and cannot introduce a figure. Its
private fields never leave the machine (ADR-0009).

## Human-review and action boundary

Confirmed, not changed (ADR-0010, `CLAUDE.md` §9): generating recommendations is read-only
analysis or draft output and needs no approval. **BusinessIQ never executes a recommendation.**
Carrying one out — a system write, a message, an export, an overwrite — requires explicit
per-action approval naming what changes; modifying source data and financial transactions remain
prohibited; write-back is out of scope for v1.

## Relationship to synthesis, SWOT, Decision Support and Executive Report

- **Synthesis:** consumed directly and read-only. No change to its representation, schema or
  confidence vocabulary.
- **SWOT:** no dependency. Strategy consumes the `SynthesisSet`, not a SWOT result; a SWOT point
  id is not evidence. The eligibility rules are identical to ADR-0030's and must have **one home**
  (ADR-0012): the implementation may share them but must not duplicate them, must not require a
  SWOT result, and must not introduce a generic consumer framework.
- **Decision Support:** shares this **recommendation record contract** unchanged — authored
  fields, resolution rules, derived confidence, figure rule, ledger form — with `issued_by`
  distinguishing the issuer. Its container, its "12-part framework" (named in `architecture.md`
  §4 and defined nowhere in the repository) and whether it consumes a `StrategyResult` are not
  decided here.
- **Executive Report:** may consume `StrategyResult`s and recommendation records. It assembles and
  performs no fresh analysis, so it may not author, edit, re-grade, re-order by importance or
  drop fields, confidence, conflicts, limitations or caveats of a recommendation. The M11 verifier
  timing (before `/executive-report` and `/decision-support` finalise) is unchanged.

## Security constraints the implementation must meet

1. Resolve all support against one genuine strict synthesis set; refuse fake, ambiguous and
   out-of-set ids and any non-statement id.
2. Refuse authored confidence, support, trust, verification, tier, priority, rank, score and
   weight.
3. Preserve every cited statement's origin, domain, trust and evidence class; never promote
   external evidence to internal fact or any statement's standing.
4. Never use source metadata (tier, date, host, `source_type`) as provenance for a
   recommendation; provenance is the cited statement chain.
5. Refuse any figure not present in cited statement text.
6. Never let recommendation output re-enter synthesis: no strategy path calls a synthesis
   authoring function with recommendation text, and **`SynthesisSet.register_claims()` must
   refuse a record that is a recommendation** (class 7, label `RECOMMENDATION`, or carrying a
   `recommendation_id`) — closing the latent re-entry path found above. This is an additive
   refusal in M10.3.2, not a change to any existing acceptance.
7. Never read files, run analyses, retrieve, dispatch the scout or build evidence; never
   transmit anything.
8. Fail closed: a refused recommendation raises and is not partially emitted.

## Consequences

**Positive.** Every recommendation is traceable to real statements by identifier; fabricated
evidence has no field to occupy; confidence is explainable from reason codes already in use; the
foundation and every consumer's view of it stay exactly as approved; Strategy and Decision
Support share one contract; the latent re-entry path is closed deliberately rather than
discovered in production.

**Negative.** ADR-0022 §5's stated location is not used, so the synthesis `recommendations` array
is a permanent empty marker, and a reader must follow this ADR to find where recommendations
live. The confidence rule is conservative: any cited assumption or any unresolved conflict makes a
recommendation `LOW`, and `HIGH` needs every cited statement to be `HIGH`. The figure rule will
refuse some legitimate prose (a year or count not present in cited text). The engine proves a
recommendation is grounded, not that it is wise — that remains model judgement under human
review. Recommendations built only on tier-C external evidence are at best `MEDIUM`.

## Explicit non-goals

No implementation; no skill, command, schema or test; no change to `evidence.Claim`,
`synthesis.schema.json`, the confidence vocabulary, compatibility semantics, `BIQ-REC/1` or
`DimensionProvenance`; no prioritisation, ranking or scoring framework; no Decision Support
framework; no Executive Report design; no live research.

## Implementation implications for M10.3.2

Expected, for that milestone to confirm:

- **New:** a strategy engine module (`lib/python/biq/strategy.py`), `lib/schemas/strategy.schema.json`
  (closed), `skills/biq-strategy-recommendations/SKILL.md`, `commands/strategy-analysis.md`,
  focused tests, and registry declarations moving `strategy-analysis` from unbuilt to built while
  keeping `decision-support` and `executive-report` guarded.
- **Additive changes:** a class-7 conditional in `claim_ledger.schema.json` requiring the six
  fields; the `register_claims()` refusal in `synthesis_set.py`; a single home for the grounding
  checks ADR-0030 introduced.
- **Unchanged:** `synthesis.schema.json`, `SynthesisItem`, `DEFERRED_KINDS`, the advisory guard,
  `evidence.RECOMMENDATION_FIELDS`, `compatibility.py`, `quantity.py`, `research/`,
  `dimension_provenance.py`, `research_footing.py`, `commands/joins.py`.
- **Left to implementation, within this contract:** exact numeric-token recognition for the figure
  rule (must fail closed); the mechanism by which the ADR-0030 grounding checks get a single home;
  the command's input syntax.

## Revisit when

- A prioritisation policy is proposed with a defensible basis the repository can compute.
- Decision Support's framework is defined and needs a field this contract lacks.
- Recommendations need to rest on something no synthesis statement can represent.
- The confidence rule proves systematically harsher than the evidence warrants in live use.
