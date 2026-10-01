# 2026-09-16 — M10.3.3-A: Decision Support contract (decision only)

**Milestone:** 10.3.3-A — contract for `biq-decision-support` + `/decision-support`
**Status on completion:** COMPLETED (DECISION ONLY)
**Supersedes:** None

## 1. Prompt / task performed

Define the Decision Support contract before implementation: the twelve-part output, inputs,
relationships to Strategy, SWOT and Executive Report, the M11 verifier / "finalise" lifecycle,
evidence, confidence, assumptions, criteria, tradeoffs, options, recommendations and the human
decision boundary. The owner supplied a twelve-part working framework to reconcile against the
approved architecture. Decision only: one new ADR (ADR-0032), documentation recording it, a full
regression run and strict validation. No code, tests, schemas, skill, command, verifier or
Executive Report; no change to ADR-0031 or any accepted ADR; no live research; no commit or push.

## 2. Baseline

| Fact | Value |
|---|---|
| HEAD | `93b68fb07f6dc27c7b053a5727f7b7c188dc70d6` — *M10.3.2: Strategy Recommendations* |
| Branch | `main`, equal to `origin/main` after a read-only fetch, clean tree |
| Last full run | 4,232 tests, 0 failures, 0 errors, 19 skipped |
| Next free ADR | 0032 |

## 3. Why the framework was undefined

`architecture.md` §4 has said "`biq-decision-support` (the 12-part framework)" since Revision 1.
A repository-wide search (every `.md`, `.py`, `.json`, `.yaml`, development history and ADRs) found
only that phrase and later records noting it was undefined. It is the same pattern as documentation
debt D-01, D-02 and D-06, whose recorded root is the product specification that was never committed.
Nothing else specified the output: ADR-0010 names "decision packages" as draft generation, ADR-0031
leaves Decision Support's container and framework undecided, `reference/output-standards.md` has no
decision-package shape, and `architecture.md` §10 uses "finalise" without defining it.

Business Context was inspected in full (`business_context.schema.json`): identity, reporting
preferences, KPI overrides, materiality thresholds, terminology and notes — **no objective,
constraint or decision field**. That fact decided parts 2, 3 and 5.

## 4. The approved twelve-part framework (ADR-0032)

| # | Field | Required | Contract in brief |
|---|---|---|---|
| 1 | `decision_question` | Yes | User-supplied framing; never inferred, never evidence |
| 2 | `business_context` | Yes (fields may be null) | `subject`, `business_model`, `currency` from the set; constraints user-supplied |
| 3 | `objective` | Yes (may be not stated) | User-supplied or not stated; never inferred |
| 4 | `options` | At least two | User-supplied, one per class-7 record in guidance, and the status quo; no option generator |
| 5 | `criteria` | May be empty | User-supplied, or a configured materiality threshold on request; no weights |
| 6 | `evidence` | At least one | Index of cited synthesis statements, resolved through `synthesis/grounding.py` |
| 7 | `assumptions` | May be empty | Registered `ASSUMPTION` statements named by records or tradeoffs; never evidence |
| 8 | `tradeoffs` | May be empty | Records with options, optional criteria, text, at least one evidence id, derived confidence |
| 9 | `risks` | May be empty | Per-option records; evidence optional; unevidenced risks labelled and `LOW` |
| 10 | `expected_outcomes` | May be empty | Per-option records, at least one evidence id, figures quoted only |
| 11 | `guidance` | Yes | ADR-0031 records, at most one grounded preferred option, divergences |
| 12 | `uncertainty` | Yes | Derived package and per-option confidence, conflicts, limitations, unresolved dimensions, evidence-gap next steps |

**Reconciliation.** None of the twelve contradicts an approved contract. Five needed their terms fixed
so they cannot weaken an existing rule: Business Context (framing only), objective (never inferred),
criteria (no weights or scores), guidance (no second recommendation kind), next steps (evidence gaps,
never actions).

## 5. Contract decisions

- **Container:** `DecisionResult` beside one genuine strict `SynthesisSet` — the ADR-0030/0031
  pattern; nothing written to the set.
- **Inputs:** set required; decision question required; objective, options, constraints and criteria
  optional and user-supplied; `StrategyResult` optional, bound to the same set; SWOT not an input;
  Business Context framing only. User framing text is stored verbatim, local, never evidence.
- **Evidence:** ADR-0031 resolution and eligibility through the shared grounding module; at least one
  cited statement per package; recommendation records appear only in guidance and never support a
  tradeoff, risk or outcome.
- **Options:** at least two; model-proposed options exist only as ADR-0031 records.
- **Criteria:** stated origin for any numeric threshold; no weight, score or rank.
- **Recommendations:** one contract. Strategy records packaged unchanged; Decision Support records
  issued as `biq-decision-support`; contradictions kept visible in `divergences`, never settled.
- **Preferred option:** only with criteria, a grounded class-7 record related to them, every other
  option assessed against the same criteria or labelled not assessable, and a named basis.
- **Confidence:** `confidence.combine()` for every tradeoff, risk, outcome, option and the package;
  existing codes only; unassessed options `LOW` with `insufficient_evidence`.
- **Materiality:** inherited; any materiality ordering is labelled presentation.
- **Scoring:** prohibited in every form, including preference ordering.
- **Figures:** the ADR-0031 rule on every authored text part.
- **Human boundary:** unchanged; next steps are evidence gaps with no owner, date or execution state.

## 6. M11 verifier lifecycle decision

`lifecycle` is `draft` or `final`. Every result M10.3.3 produces is `draft`, and no M10.3.3 path can
set `final`. "Finalise" means the M11 `biq-analysis-verifier` recomputing headline figures and
challenging conclusions against a draft and recording a verification beside it that moves it to
`final`; it never edits the package. So M10 does not depend on M11, M11 depends on M10 as planned, and
the dependency column needed no change — only the word needed a definition. How the verifier records
findings is M11's decision.

## 7. Rejected and deferred elements

| Element | Outcome | Repository-based reason |
|---|---|---|
| Objective inferred from data or context | Rejected | No context field holds one; inferring is guessing (ambiguity protocol) |
| Free option generation | Rejected | An ungrounded option is a recommendation without ADR-0031's structure; options enter as records instead |
| Criteria weights / weighted scoring / decision matrix | Rejected | No policy or computable basis exists; ADR-0031 and the research skills treat a score as a decision presented as an observation |
| Risk likelihood, severity or impact ratings | Rejected | A second scoring system |
| A Decision Support recommendation contract | Rejected | ADR-0031 is the one contract |
| Decision Support overriding Strategy | Rejected | Conflicts are preserved, never settled (ADR-0016, ADR-0022) |
| SWOT as a required input | Rejected | No repository dependency; SWOT point ids are not evidence |
| `StrategyResult` as a required input | Rejected | ADR-0031 left it open; nothing requires it |
| Waiting for M11 before implementing | Rejected | §10 attaches the verifier to finalising, not building |
| Verifier findings format | Deferred | M11 |
| Whether Executive Report needs final packages | Deferred | Executive Report milestone |
| Prioritisation policy | Deferred | None exists; none created |

## 8. Changes made

1. `docs/decisions/ADR-0032-decision-support-contract.md` — new, Accepted.
2. `architecture.md` — §4 row points at ADR-0032; §7 *The decision-support contract* section with
   the twelve-part table; §10 verifier row defines "finalise"; §19 index row.
3. `project_plan.md` — `M10.3.3-A … COMPLETED (DECISION ONLY)`; `M10.3.3 — Decision Support ·
   PLANNED`; `M10.3.4 onward` for Executive Report; M11 note that the verifier finalises and does not
   gate building.
4. `reference/output-standards.md` — *Decision package* shape.
5. `docs/decisions/README.md`, `docs/README.md` — ADR-0032 index entries.
6. This record.

## 9. Files created

- `docs/decisions/ADR-0032-decision-support-contract.md`
- `docs/development/2026-09-16-m10-3-3-a-decision-support-contract.md`

## 10. Files modified

`architecture.md`, `project_plan.md`, `reference/output-standards.md`, `docs/decisions/README.md`,
`docs/README.md`.

## 11. Files deleted

None.

## 12. Tests performed

No tests added or modified (decision-only milestone).

```
python tests/run_tests.py
claude plugin validate . --strict
```

## 13. Test results

| Run | Result |
|---|---|
| Full suite, after all documentation changes | `ran 4232 \| failures 0 \| errors 0 \| skipped 19` — identical to the M10.3.2 baseline, which is the evidence that no code or test changed |
| `claude plugin validate . --strict` | `✔ Validation passed` (exit 0) |

## 14. Documentation governance

| File | Decision | Reason |
|---|---|---|
| `architecture.md` | UPDATED | Records the contract, defines "finalise", indexes ADR-0032 |
| `project_plan.md` | UPDATED | M10.3.3-A status; M10.3.3 next; M11 lifecycle note |
| `reference/output-standards.md` | UPDATED | Had no decision-package shape |
| `docs/decisions/README.md`, `docs/README.md` | UPDATED | ADR-0032 entries |
| `CLAUDE.md` | CURRENT | Governance unchanged; §9 already classes decision support as read-only |
| `README.md` | CURRENT | "Not built yet" still correctly lists decision support; no inventory change |
| `docs/commands/README.md`, `docs/skills/README.md` | CURRENT | Nothing built |
| `reference/evidence-ledger.md` | CURRENT | Class 7 unchanged; Decision Support reuses it |
| `reference/analysis-framework.md`, `ambiguity-protocol.md`, `materiality-policy.md`, `research-policy.md` | CURRENT | Apply unchanged |
| `docs/development/README.md` | STALE BUT NON-BLOCKING | Stops at M9-B; unrelated cleanup |
| Accepted ADRs, including ADR-0031 | CURRENT | Immutable; none edited |

## 15. Implementation implications (M10.3.3)

- New Decision Support engine module, closed decision schema, `biq-decision-support`,
  `/decision-support`, focused tests; `decision-support` moves to built while `executive-report` stays
  guarded.
- The ADR-0031 record builder and figure rule must serve `issued_by: "biq-decision-support"` without
  changing Strategy's behaviour or its schema's issuer constant; one home in code, and any mirrored
  schema definition pinned to Strategy's by test (`jsonschema_mini` resolves local references only).
- Additive: the `register_claims()` refusal extended to decision-package records.
- Command input: required decision question; optional objective, options, constraints, criteria and
  public research subjects; existing internal, research and local-join paths reused.
- Left to implementation within the contract: id spellings, the status-quo label, how the status quo
  is excluded.

## 16. Remaining work

M10.3.3 implementation; M11 verification recording; Executive Report.

## 17. Live research

**None.**

## 18. Git commit reference

**N/A — no commit, no push.** HEAD unchanged at `93b68fb07f6dc27c7b053a5727f7b7c188dc70d6`.
