# 2026-09-15 — M10.2-R.9: Company Analysis authors dimension footings

**Milestone:** M10.2-R.9 — Company Analysis dimension-footing migration
**Status on completion:** COMPLETED
**Supersedes:** None

---

## 1. Prompt / task performed

Migrate `skills/biq-company-analysis/SKILL.md` to the dimension-provenance architecture
established by M10.2-R.6, R.7 and R.8: make Company Analysis capable of authoring dimension
footings from retrieved external evidence, using the existing `DimensionProvenance`
mechanism, and prove the complete skill-level supply → validation → synthesis path on
deterministic in-memory fixtures.

The prompt carried a hard boundary list: no live research, no `WebSearch`, no `WebFetch`, no
scout dispatch, no attempt at R-12, no commit, no push, no reset of working-tree changes, no
change to `compatibility.py`, `quantity.py`, `research/scout.py`, `BIQ-REC/1`, `BIQ-END/1`,
the research intent registry, the disclosure gate, the evidence tier classifier, ADR-0025,
ADR-0026 or ADR-0027, no change to Market Analysis, Competitor Analysis or Industry
Research, no second provenance architecture, and no weakening, deletion or retargeting of an
existing test.

Nine parts: fresh-session and baseline verification; skill guidance; the footing creation
path; a synthetic fixture; the positive seven-dimension path; twenty-four negative controls;
output integrity; tests; documentation; and a security-boundary re-verification.

## 2. Objective

Close the migration gap M10.2-R.6 and R.8 both named and neither filled. The admissibility
control existed and the evidence record could carry source context, but **no shipped skill
authored a footing**, so the mechanism had no caller. This milestone gives it one, and does
it without moving any authority from Python to the model.

The division ADR-0027 fixed, and which this milestone implements unchanged:

| Stage | Who | What |
|---|---|---|
| Retrieval | scout | fetches the document; puts the figure **and its stated context** in `content` |
| Candidate extraction | the skill's model | locates the passage that states a dimension and quotes it verbatim |
| Admissibility | **Python** | evidence registry, operation, document, containment, applicability, dimension predicate, value agreement |

**A skill supplying a dimension value never becomes authoritative by supplying it.** That is
the property the negative controls exist to demonstrate rather than to assert.

## 3. Baseline

Established before any edit, in this session:

| Fact | Value |
|---|---|
| HEAD | `8d52b0e24343f2e9b9f586207d2ea841dce61289` (unchanged) |
| Branch | `main` |
| Working tree | 1 modified (`.gitignore`), 16 untracked paths — the pre-existing state |
| Tests | `Ran 3234 tests in 460.700s` · `OK (skipped=19)` · failures 0 · errors 0 |
| `claude plugin validate . --strict` | `✔ Validation passed` |
| `compatibility.py` md5 | `35a89e32f6fad71bc7c21abe9dbe4915` — matches the expected baseline |
| `quantity.py` md5 | `a43581d8ff7a29b92f5d200fb03818e1` — unchanged from R.8 |
| `research/scout.py` md5 | `fe2c4fac1736abea4aaf3c997fdd2b6e` — unchanged from R.8 |
| ADR-0027 | present, Accepted |
| M10.2-R.8 record | present (`docs/development/2026-09-15-m10-2r8-source-context-capture.md`) |
| Company Analysis skill | present, 211 lines, 27 contract tests in `test_m9c3_company_analysis.py` |
| R-12 | open, untouched |

The baseline matched the prompt exactly, so implementation proceeded.

### Fresh-session evidence

Reported as available evidence, not as proof: a session cannot verify its own history from
inside itself.

- The conversation begins with this task; no prior turns, no prior tool calls, no carried
  state.
- The `SessionStart` hook fired in this turn, which is what injected the `using-superpowers`
  skill text.
- The session scratchpad `…\d936951f-ab2c-44e9-9d09-17041102c2fa\scratchpad` existed and was
  **empty** (`total 0`), created at 22:06–22:07 on 2026-09-15.
- A transcript file for this session id, `d936951f-…-17041102c2fa.jsonl`, was created at
  22:07 — separate from every earlier session's transcript in the same directory.
- The git status supplied at session start is the repository's own pre-existing state, not
  anything this session produced.
- The baseline in §3 was re-measured here rather than recalled.

## 4. Architecture reviewed before editing

Read, not assumed: ADR-0025, ADR-0026, ADR-0027, the M10.2-R.8 development record, the
Company Analysis skill, `synthesis/dimension_provenance.py`, `synthesis/synthesis_set.py`
(`add`, `_require_internal_footing`, `_resolve_dimensions`, `register_external`, `load`),
`synthesis/merge.py` (`sourced_statement`, `register_external`, `from_analysis_set`),
`synthesis/contract.py` (`declared_dimensions`, `dimensions`, `from_dict`),
`synthesis/compatibility.py`, `research/evidence_set.py`, `research/sources.py`
(`classify_tier`), `research/handoff.py`, `agents/biq-research-scout.md`'s R.8 content
guidance, and the existing R.3, R.6, R.8, M9-C.3 and M9-D.1 test modules.

**The decisive finding: admissibility needed no new code.** `DimensionProvenance`,
`sourced_statement(dimension_provenance=…)` and `SynthesisSet(require_dimension_provenance=
True)` already provide the whole path, and already prevent the bypass the prompt asked about
— a caller writing `geography="Global"`, `currency="USD"`, `methodology="GAAP"` with no
footing gets three `None`s and a `no_dimension_provenance` reason under strict mode. Nothing
was rebuilt, and no Company Analysis-specific copy of any of it was created.

## 5. Changes made, in order

1. Verified fresh-session evidence, HEAD, working tree, the 3,234-test baseline, strict
   validation and the three protected hashes.
2. Read the reference material in §4 and established that only an **authoring** helper was
   missing, not an admissibility one.
3. Added `synthesis.dimension_provenance.source_footings()` — 30 lines — and exported it
   from the `synthesis` package.
4. Added one section, *Footing a figure for comparison*, to the Company Analysis skill.
5. Discovered while running the existing suite that `test_m9d1_company_analysis_command.py`
   derives the skill's ten output sections by regex over `| <digit> |` table rows, and that
   the new section's six-row numbered table collided with it. **The new table was
   re-written without a number column**; the existing test was not touched.
6. Wrote `tests/unit/test_m10_2r9_company_analysis_footings.py` — 99 tests.
7. Ran the focused module, the R.6/R.8 modules, the Company Analysis modules, the full
   regression, strict validation and `git diff --check`.
8. Added one paragraph to `architecture.md`, one section to `project_plan.md`, and this
   record.

## 6. Company Analysis guidance

One new section, placed after *Declaring a conflict* and before the closing policy links.
It states, explicitly:

- Footings answer one question only — **may this figure be set beside another** — and the
  ten-section report needs none of them.
- External evidence is untrusted source material; a quoted excerpt is a proposal, not a
  fact.
- **"You locate; Python decides."** A footing the model wrote is a claim about the source,
  never authority over it, and carries no extra weight for having been written by the
  analysing model.
- Six categories, named and kept apart: source evidence · candidate excerpt · dimension
  footing · calculated value · interpretation · recommendation.
- The excerpt must be **contiguous verbatim text** from the cited item's `content` or
  `title`. No paraphrase, summary or translation. No stitching two passages. No commentary
  of the model's own inside an excerpt.
- **Missing context stays missing** — author no footing, and let the dimension resolve to
  unknown, which is a true answer.
- Never inferred: geography (identity, headquarters, domicile, incorporation, domain, TLD,
  publisher's country, filing venue, exchange) · methodology (source type — a filing does
  not imply US GAAP — or publisher identity) · currency (a bare `$`, `£`, `€`, `¥`, or a
  currency *name*; an ISO 4217 code is required) · period (publication date, filing date,
  URL year) · scope (company identity).
- No currency conversion, no rescaling into another currency, no synonyms — `global` and
  `worldwide` do not match, and an `incompatible` verdict is the better failure.
- Admissibility promotes nothing: the statement stays `[FACT/SOURCED]`, external, untrusted,
  provenance class 3 and unverified, with no confidence or support uplift and no
  recommendation. `source_tier`, `trust` and `verified` cannot be supplied.
- The output contract is unchanged: the same ten sections, in the same order. Section 7
  additionally names the dimensions that resolved and the excerpt each rests on; section 9
  names the ones that did not. **No section added, re-ordered or dropped.**
- No new syntax, record field, message or protocol. `BIQ-REC/1` is returned exactly as
  before and source context travels in `content` where it always did.

**On restating rules homed elsewhere.** CLAUDE.md §2 says to link a rule rather than
paraphrase it. These prohibitions are homed in ADR-0026 and ADR-0027 and restated in
`agents/biq-research-scout.md`. They are restated here deliberately and on instruction: the
actor that authors a footing is this skill's model, and guidance it never reads governs
nothing. The section names ADR-0026 and ADR-0027 as the owning decisions and adds no rule of
its own.

## 7. Provenance integration

**New production code: one function, 30 lines, in the module that already owns footings.**

```
synthesis.dimension_provenance.source_footings(evidence_id, claims, basis=STATED,
                                               applicability=None, locator=None)
```

`claims` maps a dimension to the `(value, source_excerpt)` pair the document supports. One
call covers one evidence item on one basis, so a caller stays explicit about which document
each quote came from — a figure in one item and its context in another is two calls, never
one call with a hidden default.

What it deliberately does **not** do, verified by a test that greps its own source:

- no evidence lookup (`_registry`, `P_EVIDENCE`);
- no operation binding;
- no document binding;
- no containment check (`_excerpt_present`);
- no applicability check (`_applies`);
- no currency predicate (`currency_excerpt_carries_code`);
- no conflict handling.

All of those remain in `dimension_provenance._assess()` and `resolve()`, reached from
`SynthesisSet.add()`. A footing the helper built is judged exactly like one written by hand.

Three narrowing properties it adds at authoring time:

1. **`derived` and `asserted` are not authorable through it.** The first reads notation
   rather than a quote; the second establishes nothing, and a convenience path able to emit
   one would be a convenience path for fabrication. Both stay constructible directly, where
   the reason has to be written out.
2. **A mistyped dimension is refused, not skipped.** A silently dropped footing looks exactly
   like a dimension the source never stated, and those two must never be confused.
3. **A value with no excerpt is refused.** The pair is the unit of authorship.

It has no `source_tier`, `trust`, `verified`, `freshness` or `source` parameter, so forged
source metadata has no second doorway: the constructor raises `SynthesisError`, and the
helper raises `TypeError` for a parameter that does not exist.

**Nothing else in the synthesis layer changed.** `compatibility.compare()` is byte-identical
(md5 `35a89e32f6fad71bc7c21abe9dbe4915`), and no reason code, basis, derivation rule or
dimension was added.

## 8. Synthetic fixture

`tests/unit/test_m10_2r9_company_analysis_footings.py` builds one invented annual results
statement for one invented company. **Nothing is copied or paraphrased from a real filing.**

- Company: `Synthetic Logistics Ltd` — not a company.
- Document: `https://synthetic-logistics.example.invalid/fy2025-annual-results.htm` — a
  reserved host that can never resolve. The cross-document control uses
  `commentary.example.invalid`.
- Figure passage: *"Revenue, defined as total recognised sales before tax, was USD 12.5
  billion for fiscal year 2025."*
- Context passage, same document: *"The amount covers worldwide consolidated operations of
  Synthetic Logistics Ltd and is reported under US GAAP. Synthetic Logistics Ltd is
  registered at 1 Example Way, Springfield."*

The registered-address sentence is there on purpose: it is what the headquarters-inference
control quotes.

Two genuine `EvidenceItem`s in one genuine `EvidenceSet`, sharing one `reference` and one
operation, registered through `S.register_external`. **The tier is not chosen by the
fixture** — it is computed by `research.sources.classify_tier(reference, source)`, which
returns `("C", "… not on the recognised A or B lists …", inferred=True)` for a reserved
host, and that value is what the item carries. A fixture that picked a tier would be
asserting the thing the classifier exists to decide.

The statement is built by `S.sourced_statement(observed=Decimal("12.5"),
source_unit="USD billion", …)`, so the figure, its quantity type and its currency are
produced by ADR-0025 canonicalisation (`12500000000`, `currency`, `USD`) rather than
declared. The set is built with `require_dimension_provenance=True`.

Exercised end to end, with no fake objects and no direct call into resolution: evidence
registration · local tier classification · operation binding · same-document binding ·
excerpt containment · applicability · `DimensionProvenance` · strict `SynthesisSet`.

## 9. Positive seven-dimension path

| Dimension | Basis | Read from |
|---|---|---|
| `metric_definition` | `stated` | "defined as total recognised sales before tax" |
| `period` | `stated` | "for fiscal year 2025" |
| `currency` | `stated` | "was USD 12.5 billion" — prints the ISO code it claims |
| `unit` | `derived` | `adr0025.canonical_amount.quantity_type` |
| `geography` | `context` | "covers worldwide consolidated operations" |
| `scope` | `context` | "consolidated operations of Synthetic Logistics Ltd" |
| `methodology` | `context` | "is reported under US GAAP" |

All seven resolve. The resolution trail holds seven records, all `admitted: true`, each
carrying the source, reference, operation, retrieved date, freshness, tier and trust
**resolved locally from the evidence item** — none of it supplied by the caller, and none of
it written into the serialised footing.

The statement remains `SOURCED`, external, untrusted, evidence class 3 and unverified. A
footed statement and an unfooted one carry **identical** `support` and `confidence`, which is
the test that admissibility confers no uplift. `recommendations` is empty. The serialised
document validates against `lib/schemas/synthesis.schema.json`, and re-serialising is
byte-identical.

**The pair.** A synthetic internal twin — clearly marked synthetic test data, built through
`AnalysisSet` → `from_analysis_set` on a registered dataset, so it is engine-footed per
ADR-0023 and carries no dimension provenance — was compared with the external statement:

```
status      = compatible
matched     = 7
mismatched  = 0
unknown     = 0
may_combine = True
converted   = False
```

No arithmetic, ranking, forecast or recommendation was produced from that verdict, and
`compare_values()` left both sides' kind and trust exactly as they were.

## 10. Negative controls

Twenty-four from the prompt, plus eleven the API made available. Each asserts the **named
reason code**, because "it came out unknown" can be true for the wrong reason and a reason
code cannot.

| # | Attempt | Result |
|---|---|---|
| 1–7 | Remove the footing for each of the seven dimensions in turn | `no_dimension_provenance`; dimension `None`; the pair returns `unknown` naming exactly that dimension |
| 8 | `geography="Global"` on an `asserted` footing | `basis_inadmissible` |
| 9 | `methodology="US GAAP"` on an `asserted` footing | `basis_inadmissible` |
| 10 | `currency="USD"` quoting "was $12.5 billion" | `currency_code_not_in_excerpt` |
| 11 | `currency="USD"` quoting "Amounts are stated in US dollars" | `currency_code_not_in_excerpt` |
| 12 | Geography from the registered-address sentence | `value_disagrees_with_statement`; and `geography` has no derived path — the constructor refuses one |
| 13 | Methodology quoting the source type (`"source_type: filing"`) | `excerpt_not_in_source` — the metadata field is not content |
| 14 | Period quoting the publication date (`"2026-03-31"`) | `excerpt_not_in_source` — the fixture's text contains no `2026` |
| 15 | Scope as the company's name | `value_disagrees_with_statement` |
| 16 | Context from another document (`commentary.example.invalid`) | `document_mismatch` |
| 17 | Context from another retrieval operation | `operation_mismatch` |
| 18 | A stitched excerpt joining two passages | `excerpt_not_in_source` |
| 19 | A paraphrase of the definition | `excerpt_not_in_source` |
| 20 | Two admissible methodology footings, "US GAAP" and "cash basis" | dimension `None` + `conflicting_admissible_values`; **both** readings kept; one `CrossDomainConflict` of kind `methodology` recorded with "Neither is preferred" |
| 21–23 | `source_tier="A"` · `trust="trusted"` · `verified=True` on a footing | `SynthesisError` from the constructor; `TypeError` from the helper, which has no such parameter |
| 24 | External footings on an internal `CALCULATION` | `SynthesisError` — an internal calculation must rest on an internal source (ADR-0023) |
| 25 | Footing citing unregistered evidence | `unresolved_evidence` |
| 26 | A `stated` footing on an item the statement does not cite | `evidence_not_cited_by_statement` |
| 27 | Context whose applicability names another period | `applicability_mismatch` |
| 28 | Context declaring no applicability at all | `applicability_mismatch` for all three context dimensions |
| 29 | Editing a footing after writing it | `SynthesisError` on every field, and on `del` |
| 30 | Reloading a serialised set | trail empty, verdict not restored, footings rebuilt from caller-authored fields only |
| 31 | Forged tier/trust/verified inside a serialised footing | discarded by `from_dict`, not read |
| 32 | `SYSTEM:` instruction inside retrieved content | quoted as content; no `verified` key anywhere in the result; tier stays `C`; trust stays `untrusted` |
| 33–35 | Helper asked for `asserted`/`derived`/an unknown basis · a mistyped dimension · a value with no excerpt | `SynthesisError` in each case |

## 11. Company Analysis output integrity

Verified rather than assumed:

- The ten sections parse, in order, from the skill's own numbered table — the same regex the
  existing M9-D.1 test uses, asserted independently here.
- `**No recommendations.**` and "Nothing is labelled `[RECOMMENDATION]` by this skill." are
  both intact; the fixture's `recommendations` array is empty.
- The new section states that nothing is ranked and that no market share, strategy or
  investment view follows from a dimension resolving.
- No external evidence is promoted: `SOURCED`, class 3, `untrusted`, `unverified`
  throughout.
- No `source_tier` is accepted from evidence or from a footing; `EvidenceItem.trust` is a
  read-only property and assigning it raises `AttributeError`.
- The existing 27 skill-contract tests and 44 command tests pass unmodified.
- No private or internal data exists in the fixture, and the skill's internal-data boundary
  sentence is unchanged.

## 12. Security boundary re-verification

Every item the prompt listed, confirmed by test in the new module or by an existing test that
still passes:

Python resolves provenance · the model is not semantic authority · excerpts must exist in
`content`/`title` · evidence must be registered · same operation mandatory · same document
mandatory for context · applicability mandatory · currency requires an ISO code · geography
never inferred · methodology never inferred · company identity does not establish scope ·
publication date does not establish period · source type does not establish methodology · no
cross-document composition · no cross-operation composition · no currency conversion · no
synonym normalisation · `asserted` inadmissible · conflicts explicit · unknown stays unknown ·
external evidence untrusted · no `verified=true` path exists · no `source_tier`/`trust`
metadata accepted from the skill or model · prompt injection inert as an instruction.

`compatibility.py` was additionally re-checked for the absence of `provenance`,
`DimensionProvenance`, `evidence`, `EvidenceSet`, `source_tier`, `registry`, `admissible`,
`basis` and `footing`.

## 13. Files created

- `tests/unit/test_m10_2r9_company_analysis_footings.py` — 99 tests.
- `docs/development/2026-09-15-m10-2r9-company-analysis-footings.md` — this record.

## 14. Files modified

- `lib/python/biq/synthesis/dimension_provenance.py` — added `source_footings()` and its
  section comment. Nothing existing was changed.
- `lib/python/biq/synthesis/__init__.py` — exported `source_footings` (import list and
  `__all__`).
- `skills/biq-company-analysis/SKILL.md` — one new section, *Footing a figure for
  comparison*. Nothing existing was removed or reworded.
- `architecture.md` — one new paragraph naming the shared authoring helper.
- `project_plan.md` — one new M10.2-R.9 section.

## 15. Files deleted

None.

## 16. Tests performed

```
python tests/run_tests.py
claude plugin validate . --strict
git diff --check
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_2r9_company_analysis_footings
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_2r6_dimension_provenance tests.unit.test_m10_2r8_source_context
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m9c3_company_analysis tests.unit.test_m9d1_company_analysis_command tests.unit.test_m9_governance tests.unit.test_manifest
md5sum lib/python/biq/synthesis/compatibility.py lib/python/biq/quantity.py lib/python/biq/research/scout.py
```

## 17. Test results

Real output.

**Baseline, before any edit:**

```
Ran 3234 tests in 460.700s
OK (skipped=19)
BusinessIQ test suite
ran 3234 | failures 0 | errors 0 | skipped 19
```

**The new module:**

```
Ran 99 tests in 0.040s
OK
```

**M10.2-R.6 + R.8 together, unmodified:**

```
Ran 172 tests in 0.050s
OK
```

**Company Analysis skill, command, governance and manifest, unmodified:**

```
Ran 171 tests in 0.079s
OK
```

**Full regression, after all edits:**

```
Ran 3333 tests in 114.564s
OK (skipped=19)
ran 3333 | failures 0 | errors 0 | skipped 19
```

3,234 + 99 = 3,333. No existing test was deleted, weakened, disabled or retargeted.

**Strict validation:**

```
Validating marketplace manifest: …\.claude-plugin\marketplace.json
✔ Validation passed
```

**Protected hashes, re-measured after all edits:**

```
35a89e32f6fad71bc7c21abe9dbe4915  lib/python/biq/synthesis/compatibility.py
a43581d8ff7a29b92f5d200fb03818e1  lib/python/biq/quantity.py
fe2c4fac1736abea4aaf3c997fdd2b6e  lib/python/biq/research/scout.py
```

`git diff --check` reported no whitespace error.

## 18. Issues discovered

**A latent coupling between the skill's prose and a command test.**
`test_m9d1_company_analysis_command.py::test_the_order_matches_the_skills_own_numbered_table`
derives the ten output sections by regex over `| <digit> |` rows in the skill. Any future
numbered table anywhere in that skill will break it. The new section was written without a
number column, so nothing was changed in the test — but the coupling is fragile and worth
knowing about before the next skill edit. Not repaired here: the test is correct about what
it checks, and changing its regex is a change to an existing test.

**No defect was found** in the R.6 or R.8 implementation. Every admissibility check the
prompt asked about already existed and already held.

## 19. Decisions made

None requiring an ADR. This milestone implements ADR-0026 and ADR-0027 as approved, and the
one piece of new code is a convenience constructor with no authority, which is below the
ADR bar in `docs/decisions/README.md`.

**Proposed documentation change, not made:** ADR-0027 §17 says "None [of the four research
skills] is migrated by this ADR", which was true when written and is now one skill out of
date. Recording that `biq-company-analysis` was migrated by M10.2-R.9 would keep the ADR's
migration section current. It is **reported here rather than applied**, because the prompt
prohibits modifying ADR-0027 and an accepted decision's text is not this milestone's to
edit. `project_plan.md` carries the migration status meanwhile.

## 20. Architecture changes

One paragraph added to `architecture.md`, in the synthesis layer's dimension-admissibility
discussion, naming `synthesis.source_footings()` as the single shared authoring seam and
stating what it deliberately does not do. A genuinely new architectural fact — a new public
API in that layer — recorded in one paragraph. **Nothing existing was rewritten**, no ADR
was reopened, and none of the D-01/D-02/D-06/D-12 documentation gaps was touched.

## 21. Project-plan updates

One new section, `### M10.2-R.9 — Company Analysis dimension-footing migration ·
COMPLETED`, placed before `### M10.3 onward`, in the same table format the R.6 and R.8
sections use. M10.2-R stays `PARTIALLY VERIFIED`. No other status changed.

## 22. Documentation updates

- `architecture.md` — §20 above.
- `project_plan.md` — §21 above.
- `docs/development/2026-09-15-m10-2r9-company-analysis-footings.md` — this record.
- `docs/decisions/` — **not changed.** ADR-0025, ADR-0026 and ADR-0027 are untouched; see
  §19 for the proposed ADR-0027 note that was deliberately not applied.
- `docs/skills/` — not changed; it holds only a README with no per-skill page.
- `docs/development/README.md` — **not changed.** Its index has been stale since
  M9-B and carries no row for the M10.2-R.6 or R.8 records either; extending it for
  this record alone would leave it inconsistent, and repairing it is not this
  milestone's scope. Flagged so it is not lost.
- No unrelated documentation cleanup was performed.

## 23. Remaining limitations

1. **Containment is still not meaning.** The excerpt check proves the quoted text is in the
   source, not that it *means* the value. A footing that quotes a genuinely present sentence
   and reads it wrongly is admissible, and no code can detect that. ADR-0026 states this;
   the new skill guidance restates it as "you locate; Python decides", and the residual
   judgement is real. What the mechanism removes is the ability to supply a dimension with
   no source text at all.
2. **Supply still depends on guidance.** Whether the scout captures dimension-bearing text,
   and whether the skill quotes it faithfully, rests on two agent/skill definitions rather
   than on a type. Tests pin what the definitions say; nothing can pin a model's compliance.
3. **A source that does not state all seven dimensions cannot reach `compatible`.** The
   fixture states all seven because it was written to; the M10.2-R.4 live run found a real
   document that stated four. This milestone does not change how often an ALLOW is reachable
   in practice, and must not be read as evidence that it is common.
4. **A currency name still establishes nothing** (ADR-0027 §23, open by decision).
5. **Cross-document context stays prohibited**, so a figure in one document and its currency
   declaration in another remain uncombinable.
6. **Three research skills are unmigrated.** `biq-market-analysis`,
   `biq-competitor-analysis` and `biq-industry-research` author no footings and were
   deliberately untouched. They behave exactly as before, which the additive default
   guarantees.
7. **No command wires this up.** `/company-analysis` does not construct a strict
   `SynthesisSet` or author footings; the skill knows how, and nothing invokes it yet. The
   path is proved by test, not by a user-reachable flow.
8. **Nothing here is verified live.** Every fixture is synthetic and in-memory.

## 24. R-12 status

**Open, untouched, and not progressed.** No scout was dispatched, no hand-back was parsed,
and neither the return protocol nor the recovery position changed. This milestone was
designed specifically to prove the skill-level provenance path *without* depending on live
scout reliability, so it produces no evidence about R-12 in either direction.

## 25. Live research

**None.** No `WebSearch`, no `WebFetch`, no scout dispatch, no network access of any kind.
Every source in this milestone is an invented sentence on a reserved `.invalid` host.

## 26. Git commit reference

**N/A — no commit, no push.** HEAD is unchanged at
`8d52b0e24343f2e9b9f586207d2ea841dce61289`. The working tree carries the changes in §13–14
and nothing else; no existing working-tree change was reset or discarded.
