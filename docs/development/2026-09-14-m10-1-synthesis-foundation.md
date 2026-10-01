# 2026-09-14 — M10.1 Cross-Domain Synthesis Foundation

**Milestone:** 10 — Synthesis & Executive Reporting (sub-milestone 10.1)
**Status on completion:** `COMPLETED`
**Supersedes:** None

## 1. Prompt / task performed

Build the deterministic cross-domain synthesis foundation: one shared, auditable
intermediate representation that can safely combine internal analytical findings, KPIs,
forecasts, anomaly findings, external EvidenceSet items, candidate claims, provenance,
conflicts, materiality, limitations, uncertainty and confidence — for later consumption by
SWOT, strategy, decision support and executive reporting, **none of which is implemented
here**.

Hard constraints carried through the whole task: no new slash commands, no new research
intents, no MCP connectors, no change to the scout protocol or `BIQ-REC/1` / `BIQ-END/1`,
no weakening of disclosure or source-tier rules, no change to the k=5 privacy floor, no
live external research, no commit, no push, no deleted tests.

## 2. Objective

Establish the trusted intermediate representation and the deterministic rules around it, so
that four downstream capabilities do not each re-derive the answers to *what kind of
statement is this*, *what does it rest on*, *may these two numbers be compared*, and *how
confident are we* — and so that none of them can promote a candidate claim, an external
quotation, or a source's advice into something it is not.

## 3. Changes made

**Baseline first.** Ran the complete suite before touching anything: 2,719 tests, 0
failures, 0 errors, 19 skipped — matching the stated M9-D.5 result exactly. Then read the
existing contracts rather than designing against assumptions: `evidence.Claim` / `Ledger`,
`analytics.contract` (`AnalysisFinding`, `AnalysisSet`, `Limitation`), `kpi.contract`,
`forecast.contract`, `anomaly.contract`, `materiality`, `research.evidence_set`,
`research.sources`, `research.handoff`, `research.intents`, and the configured materiality
thresholds.

That reading changed the design materially in three places:

1. **`analytics.contract` already owns the fact/calculation/interpretation/recommendation
   boundary**, complete with an `EVIDENCE_CLASS` map into the ledger. So the synthesis
   layer imports those four kinds rather than defining a parallel set.
2. **The four kinds are not enough once external material is present.** An external
   statement mapped onto `FACT` would carry evidence class 1 — *user-provided data* — which
   is precisely the mislabelling the milestone exists to prevent. Added one kind, `SOURCED`,
   mapping to the ledger's existing class 3, reusing the spelling `evidence.Claim.label`
   already produces. Then constrained kinds by domain, which is what actually makes
   "external wording never becomes an internal fact" structural: there is no kind for it to
   become.
3. **`sources.assess_support()` returns three verdicts, the brief asks for four.** Rather
   than writing a second support policy, mapped the three and added
   `insufficient_evidence` for the genuinely distinct case *nothing was linked, so we could
   not check*. The mapping constant is the whole of the translation.

**Built seven focused modules** rather than one broad one, splitting by responsibility as
section 16 of the brief directs: `contract` (statement kinds, provenance refs, item),
`compatibility` (the seven-dimension test), `conflicts` (six kinds, never settled),
`confidence` (named reason codes), `limitations` (accumulate and dedupe), `merge` (domain
translators), `synthesis_set` (the canonical result and every derived grade).

**Four corrections during implementation**, each found by a test rather than by inspection:

- `classify_tier()` returns `(tier, basis, inferred)`, not a bare tier — the forged-tier
  guard was unpacking it wrongly and rejected a legitimate fixture.
- `EvidenceSet.record_conflict()` takes `SourcePosition` objects, not dicts; the dict form
  is `close_retrieval`'s. Fixed the fixture rather than loosening the engine.
- `SynthesisSet.resolve()` read as an offer to settle a conflict on an object that holds
  conflicts. Renamed to `resolve_ref()`. A test asserting "there is no `resolve`" caught
  this, which is the test earning its place.
- A `CrossDomainConflict` built directly carried no `evidence_ids`, so it linked to nothing
  and effectively suppressed itself. Now derived from the positions when not supplied.

**No existing module was edited.** The engine gained a package; nothing already there
changed.

## 4. Files created

| Path | Purpose |
|---|---|
| `lib/python/biq/synthesis/__init__.py` | Public API and the package's reason for existing |
| `lib/python/biq/synthesis/contract.py` | Statement kinds, domains, origins, support states, `ProvenanceRef`, `SynthesisItem` |
| `lib/python/biq/synthesis/compatibility.py` | The seven-dimension comparability test; fails on unknown, never converts |
| `lib/python/biq/synthesis/conflicts.py` | Six conflict kinds, classification, `CrossDomainConflict`; no resolution path |
| `lib/python/biq/synthesis/confidence.py` | 15 named reason codes and the deterministic `HIGH`/`MEDIUM`/`LOW` derivation |
| `lib/python/biq/synthesis/limitations.py` | Accumulation and exact deduplication; no suppression |
| `lib/python/biq/synthesis/merge.py` | Domain translators, `sourced_statement`, `interpretation`, `compare_values` |
| `lib/python/biq/synthesis/synthesis_set.py` | `SynthesisSet`: registries, provenance resolution, support, confidence, serialisation |
| `lib/schemas/synthesis.schema.json` | The canonical serialised contract |
| `tests/fixtures/build_synthesis_fixtures.py` | Deterministic cross-domain fixture + shared test builders |
| `tests/unit/test_m10_1_synthesis.py` | Basic synthesis, provenance, fact boundaries, claims (36) |
| `tests/unit/test_m10_1_synthesis_policy.py` | Conflicts, materiality, confidence, limitations, comparability (57) |
| `tests/unit/test_m10_1_synthesis_security.py` | Forgery surface and deterministic serialisation (33) |
| `tests/integration/test_m10_1_cross_domain.py` | Cross-domain fixture end to end, upstream contracts unchanged (25) |
| `docs/decisions/ADR-0022-cross-domain-synthesis-contract.md` | The decision and its rejected alternatives |
| `docs/development/2026-09-14-m10-1-synthesis-foundation.md` | This record |

## 5. Files modified

| Path | Change |
|---|---|
| `architecture.md` | New §7 subsection *The synthesis layer (ADR-0022)*; ADR-0022 in §19; `research/` and `synthesis/` in the §13 tree; `synthesis` in the schema list |
| `project_plan.md` | Milestone 10 → `IN PROGRESS`; M10.1 task table `COMPLETED`; M10.2 scope restated |
| `docs/decisions/README.md` | ADR-0022 index row |

## 6. Files deleted

None. No test was deleted, weakened or skipped.

## 7. Features implemented

| Feature | Location | User-reachable? |
|---|---|---|
| Canonical `SynthesisSet` with deterministic serialisation | `synthesis/synthesis_set.py` | **No** — engine only |
| `SOURCED` kind + domain-constrained kinds | `synthesis/contract.py` | No |
| Provenance resolution against registered objects | `synthesis/synthesis_set.py` | No |
| Four-state support view of the M9 policy | `synthesis/contract.py`, `synthesis_set.py` | No |
| Six-kind conflict preservation | `synthesis/conflicts.py` | No |
| Seven-dimension comparability test | `synthesis/compatibility.py` | No |
| Deterministic confidence with traceable reasons | `synthesis/confidence.py` | No |
| Limitation accumulation | `synthesis/limitations.py` | No |
| Cross-domain merge translators | `synthesis/merge.py` | No |

**Nothing in M10.1 is user-reachable.** No command, no skill, no agent. It is the
foundation M10.2+ will read.

## 8. Tests performed

```
python tests/run_tests.py unit.test_m10_1_synthesis
python tests/run_tests.py unit.test_m10_1_synthesis_policy
python tests/run_tests.py unit.test_m10_1_synthesis_security
python tests/run_tests.py integration.test_m10_1_cross_domain
python tests/run_tests.py
claude plugin validate . --strict
```

## 9. Test results

Real output, in the order the commands were run.

```
ran 36 | failures 0 | errors 0 | skipped 0      unit.test_m10_1_synthesis
ran 57 | failures 0 | errors 0 | skipped 0      unit.test_m10_1_synthesis_policy
ran 33 | failures 0 | errors 0 | skipped 0      unit.test_m10_1_synthesis_security
ran 25 | failures 0 | errors 0 | skipped 0      integration.test_m10_1_cross_domain
```

Full regression:

```
Ran 2870 tests in 113.365s
OK (skipped=19)
ran 2870 | failures 0 | errors 0 | skipped 19
```

Baseline was 2,719 / 0 / 0 / 19. The delta is exactly +151, which is the sum of the four
new modules — no existing test changed state, and the skip count is unmoved.

Plugin validation:

```
Validating marketplace manifest: .claude-plugin\marketplace.json
✔ Validation passed
```

## 10. Issues discovered

- **The `SOURCED` gap was real and would have been silent.** Mapping an external statement
  onto `FACT` yields evidence class 1 (*user-provided data*). Nothing would have raised;
  the report would simply have described a research house's estimate as the user's own
  data. Closed by adding the kind and constraining kinds by domain.
- **The advisory-marker guard inherits M9's false positives.** A descriptive sentence
  containing `"must "` is refused. This is M9-C.2's known and deliberate over-refusal,
  imported rather than re-tuned; re-tuning it here would have created a second guard that
  could drift from the first.
- **`docs/decisions/README.md` is missing index rows for ADR-0017 and ADR-0018.** A
  pre-existing documentation gap, noticed while adding the ADR-0022 row. **Not fixed** —
  outside M10.1 scope, and the brief forbids repository changes outside it. Worth a
  one-line correction in whichever milestone next touches that file.
- **The weakest-leg rule will occasionally be harsh.** A sound cross-domain interpretation
  citing one tier C corroborator alongside solid internal computation grades as its weaker
  half. Deliberate, and the intended direction of error, but M10.2 should watch whether it
  suppresses statements that deserve to stand.

## 11. Decisions made

[ADR-0022 — One synthesis contract, built from existing vocabularies, that promotes
nothing](../decisions/ADR-0022-cross-domain-synthesis-contract.md).

An ADR was warranted on three of the README's criteria: it establishes a data contract four
future capabilities depend on, it would be expensive to undo once they do, and it changes a
load-bearing invariant by adding a statement kind to the evidence model.

## 12. Architecture changes

`architecture.md` gained *The synthesis layer (ADR-0022)* in §7, stating the layer's
purpose, inputs, outputs, the domain-constrained kind table, the provenance requirement, the
four-state support view, conflict preservation, materiality integration, confidence
derivation and the four downstream consumers. §13's tree and schema list and §19's decision
table were updated. No unrelated architecture was touched.

## 13. Project-plan updates

- Milestone 10 summary row: `PLANNED` → `IN PROGRESS` (10.1 done).
- Milestone 10 section: new M10.1 task table, all rows `COMPLETED`, with evidence.
- M10.2 onward restated as `PLANNED`, reading the M10.1 representation.

## 14. Documentation updates

`architecture.md`, `project_plan.md`, `docs/decisions/README.md`, ADR-0022, this record.
No reference document changed: M10.1 introduced no policy that belongs in `reference/` —
it composes policies those documents already state.

## 15. Remaining work

M10.1 proves the representation deterministically, against synthetic fixtures. It does
**not** prove that a real internal-plus-external analysis flows through it, because the
brief forbade live retrieval during implementation. That is a vertical slice, and it is the
natural next step.

Then M10.2: the first consumer. SWOT is the best candidate — it needs every part of the
representation (facts, sourced statements, interpretations, support, conflicts,
limitations, confidence) and needs no new policy, since "data-supported /
externally-sourced / analytical-inference" is already exactly the kind-and-domain split
M10.1 built.

## 16. Git commit reference

**N/A — no commit was made.** The milestone brief forbids committing and pushing, and
nothing was committed or pushed. `git status` shows the M10.1 files as the only change from
the state at task start; HEAD remains `8d52b0e`.
