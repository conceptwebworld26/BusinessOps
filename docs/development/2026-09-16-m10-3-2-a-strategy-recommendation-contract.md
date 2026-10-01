# 2026-09-16 — M10.3.2-A: Strategy recommendation contract (decision only)

**Milestone:** 10.3.2-A — class-7 recommendation contract for `biq-strategy-recommendations`
**Status on completion:** COMPLETED (DECISION ONLY)
**Supersedes:** None

## 1. Prompt / task performed

Resolve the architectural ambiguity around class-7 `RECOMMENDATION` claims so that M10.3.2
(`biq-strategy-recommendations` + `/strategy-analysis`) can be implemented without contradicting
approved architecture. Decision only: one new ADR (ADR-0031), documentation recording it, a
full regression run and strict validation. No production code, tests, schemas, skills or
commands; no Decision Support or Executive Report; no live research; no commit or push.

## 2. Objective

Answer, from repository evidence: where a recommendation lives, what carries it, how its support
is linked and verified, its fields and types, how expected benefit and confidence are expressed,
how partial, contested and incomparable support is handled, how the advisory guard coexists with
advisory text, what "decision owner" means, whether order or priority is allowed, what
propagates, and how Strategy relates to synthesis, SWOT, Decision Support and Executive Report.

## 3. Baseline

| Fact | Value |
|---|---|
| HEAD | `10ad661e69a16275275d86a28ece05775b889234` — *M10.3.1: SWOT synthesis consumer* |
| Branch | `main`, equal to `origin/main` after a read-only fetch, clean tree |
| Last full run | 4,108 tests, 0 failures, 0 errors, 19 skipped (M10.3.1) |
| ADRs | next free number **0031** |

## 4. Problem discovered

The repository both anticipated and prevented recommendations, in ways that disagreed:

| Source | Says |
|---|---|
| ADR-0022 §5 | Recommendations are "representable and unproducible"; "downstream milestones will fill" the `recommendations` array "through `evidence.Claim`" |
| `synthesis/contract.py` | M10.1 "establishes the representation a recommendation will later occupy"; class 7 "needs six fields and a decision owner" |
| `synthesis.schema.json` | `recommendations.maxItems: 0`; a non-empty array is "advice from a layer that has no decision owner" |
| `synthesis/__init__.py`, ADR-0022 headline | the package "decides nothing new", "issues no recommendation", promotes nothing |
| `evidence.py` | Class 7 requires `evidence, rationale, expected_benefit, risks, dependencies, confidence` by **truthiness only**; `confidence` caller-supplied; `based_on` free text; `Ledger.traceable()` matches statement text |
| `synthesis/contract.py` `DERIVED_FIELDS` | `confidence` is a conclusion and refused as input |
| `claim_ledger.schema.json` | Conditionals for classes 1, 3, 4; **none for class 7** |
| `reference/evidence-ledger.md` | evidence · rationale · expected benefit · risks · dependencies · confidence |
| `reference/output-standards.md` | action · rationale · expected benefit · risk · dependency · confidence (no evidence; singular) |
| `architecture.md` §4 | Decision Support uses "the 12-part framework" — defined nowhere in the repository |

**Found by probe during this milestone (in memory, no file changed):** a serialised recommendation
record passed to `SynthesisSet.register_claims()` is accepted and stored as a citable candidate
claim. Latent, because nothing produces class 7, but a re-entry path from advice into evidence.

## 5. Decision (ADR-0031)

- **Container:** `StrategyResult` beside one genuine strict `SynthesisSet`; never inside it. The
  synthesis `recommendations` array stays permanently empty and `synthesis.schema.json` is
  unchanged. This refines ADR-0022 §5's location sentence while keeping its substance.
- **Carrier:** a class-7 record whose ledger form is `evidence.Claim(RECOMMENDATION)`; `Claim`
  keeps owning the six-field rule.
- **Evidence:** synthesis statement ids resolved in that set; `FACT`/`CALCULATION`/`SOURCED` or an
  `INTERPRETATION` with ADR-0030-verified supports; at least one class 1/3/4 basis; statements
  graded `unsupported`/`insufficient_evidence` refused; multiple and mixed-domain evidence allowed;
  recommendations never cite recommendations.
- **Assumptions:** only as a dependency's `assumption_id`; never evidence, never the sole basis.
- **Fields:** authored `action`, `evidence`, `rationale`, `expected_benefit`, `risks` (list),
  `dependencies` (list of `{text, assumption_id}`); derived `confidence` and everything else.
  Plural canonical names, no aliases, none empty.
- **Expected benefit:** qualitative, or restating a figure already in a cited statement. Every
  figure in authored text must be quoted from a cited statement (ADR-0002, ADR-0029).
- **Confidence:** `synthesis.confidence.combine()` over the cited statements' and assumptions'
  existing reason codes — weakest level, reasons pooled. Never authored; never raised or lowered by
  the layer. No new level or reason code.
- **Partial / contested / incomparable / unresolved / low-confidence support:** allowed and carried;
  conflicts and assumptions force `LOW` through existing severe codes; no conflict presented as
  settled.
- **Advisory guard:** unchanged; recommendation text never becomes a `SynthesisItem`; M10.3.2 must
  add a `register_claims()` refusal for recommendation records.
- **Decision owner:** no personal field; `issued_by` names the issuing capability; the business
  decision is the user's (step 19).
- **Order / priority / score:** multiple allowed; deterministic, meaning-free order stated not to be
  a ranking; no priority, rank, score or weight.
- **Materiality:** inherited and never re-judged; `material` when any cited evidence is material.
- **Limitations, conflicts, caveats, unresolved dimensions:** carried per recommendation; set
  conflicts and limitations carried whole on the result.
- **Business Context:** framing only; never evidence; private fields never leave the machine.
- **Action boundary:** unchanged — generation is read-only; BusinessIQ never executes a
  recommendation.
- **SWOT:** no dependency; grounding rules shared with ADR-0030 must have one home.
- **Decision Support:** shares the record contract; its container and framework are not decided.
- **Executive Report:** may assemble records; never authors, edits, re-grades or re-orders by
  importance.

## 6. Alternatives considered

| Alternative | Repository-based reason it was not chosen |
|---|---|
| Recommendations inside `SynthesisSet.recommendations` | Needs the approved `synthesis.schema.json` changed (`maxItems: 0` and its "no decision owner" description), a write API and class-7 validation in a package whose charter is to decide nothing; breaks ADR-0030's read-only consumption; two issuers would contend for one foundation object |
| `evidence.Ledger` as the container | Resolves nothing; `traceable()` matches text; no domain or trust — cannot meet the anti-forgery requirement. Kept as the audit record |
| `Claim` alone as the whole contract | `evidence` accepts any truthy value, so it cannot stop fabricated evidence; tightening it to resolve synthesis ids would make `evidence.py` depend upward |
| Caller-supplied confidence (as `Claim` allows) | Contradicts synthesis's derived-confidence rule; lets the recommendation layer upgrade its own standing |
| Caller-supplied confidence that may only lower | No existing reason code expresses judgement uncertainty; adding one creates vocabulary for this layer alone. Action uncertainty belongs in `risks` |
| Conflict as an absolute blocker | No repository policy makes a conflict block a conclusion; research policy and ADR-0016 say present both and lower confidence |
| Assumptions as evidence | An assumption's provenance is unavailable by definition and the ledger requires class 1–4 grounding; as a dependency it is disclosed without justifying |
| Accepting singular aliases (`risk`, `dependency`) | No producer ever emitted them; two spellings would be two representations |

## 7. Changes made

1. `docs/decisions/ADR-0031-strategy-recommendation-contract.md` — new, Accepted.
2. `architecture.md` — §4 strategy row pointer; §7 *The recommendation contract* paragraph and
   table after the SWOT consumer; §7 class-7 ledger row cites ADR-0031; §19 index row.
3. `project_plan.md` — `M10.3.2-A … COMPLETED (DECISION ONLY)` section; M10.3.2 implementation
   listed as next; Decision Support and Executive Report moved to `M10.3.3 onward`.
4. `reference/evidence-ledger.md` — class-7 row clarified; new *Recommendations (class 7)*
   section stating the canonical fields and rules, marked as enforced from M10.3.2.
5. `reference/output-standards.md` — the *Action list* shape becomes the *Recommendation list*
   with the canonical fields, no priority, rank or score column.
6. `docs/decisions/README.md` — ADR-0031 row; *Amended / refined* line records ADR-0022 §5 refined
   by 0031 and that ADR-0022's status line was deliberately not annotated.
7. `docs/README.md` — ADR-0031 link.
8. This record.

## 8. Files created

- `docs/decisions/ADR-0031-strategy-recommendation-contract.md`
- `docs/development/2026-09-16-m10-3-2-a-strategy-recommendation-contract.md`

## 9. Files modified

`architecture.md`, `project_plan.md`, `reference/evidence-ledger.md`,
`reference/output-standards.md`, `docs/decisions/README.md`, `docs/README.md`.

## 10. Files deleted

None.

## 11. Tests performed

No tests added or modified (decision-only milestone).

```
python tests/run_tests.py
claude plugin validate . --strict
```

## 12. Test results

| Run | Result |
|---|---|
| Full suite, after all documentation changes | `ran 4108 \| failures 0 \| errors 0 \| skipped 19` — identical to the M10.3.1 baseline, which is the evidence that no code or test changed |
| `claude plugin validate . --strict` | `✔ Validation passed` (exit 0) |

## 13. Documentation governance

| File | Decision | Reason |
|---|---|---|
| `architecture.md` | UPDATED | Records the approved contract and the ADR index row only |
| `project_plan.md` | UPDATED | M10.3.2-A status; M10.3.2 named as next; historical entries preserved |
| `reference/evidence-ledger.md` | UPDATED | The decision resolves the class-7 field set it owns |
| `reference/output-standards.md` | UPDATED | Its action-list shape disagreed with the ledger; reconciled to the decided fields |
| `docs/decisions/README.md` | UPDATED | ADR-0031 row and the refinement of ADR-0022 §5 |
| `docs/README.md` | UPDATED | ADR-0031 link |
| `CLAUDE.md` | NOT REQUIRED | Development governance unchanged; §9 already classes strategy as read-only |
| `README.md` | NOT REQUIRED | No user-facing inventory change: nothing new is built |
| `docs/commands/README.md`, `docs/skills/README.md` | NOT REQUIRED | No command or skill added |
| `docs/development/README.md` | DEFERRED | Stale since M9-B; unrelated cleanup |
| Accepted ADRs (including ADR-0022) | NOT REQUIRED | Immutable; the refinement lives in ADR-0031 and the index. ADR-0022's status-line annotation, which the repository's convention would normally add, is left for the owner |
| Stale indexes (ADR-0017/0018/0023/0024 missing from `docs/decisions/README.md`; ADR list gaps in `docs/README.md`) | DEFERRED | Pre-existing, unrelated to this decision |

## 14. Remaining implementation work (M10.3.2)

- New `lib/python/biq/strategy.py`, closed `lib/schemas/strategy.schema.json`,
  `skills/biq-strategy-recommendations/SKILL.md`, `commands/strategy-analysis.md`, focused tests.
- Additive: class-7 conditional in `claim_ledger.schema.json`; a `register_claims()` refusal for
  recommendation records in `synthesis/synthesis_set.py`; one home for the ADR-0030 grounding
  checks shared with SWOT.
- Registry declarations: `strategy-analysis` from unbuilt to built; `decision-support` and
  `executive-report` stay guarded.
- Within the contract, for implementation to settle: numeric-token recognition for the figure rule
  (fail closed); the mechanism giving the grounding checks one home; command input syntax.

## 15. Explicitly unresolved

- Decision Support's "12-part framework" — undefined in the repository; a later milestone.
- Any prioritisation policy — none exists and none was created.
- ADR-0022 status-line annotation — owner decision.

## 16. Live research

**None.**

## 17. Git commit reference

**N/A — no commit, no push.** HEAD unchanged at `10ad661e69a16275275d86a28ece05775b889234`.
