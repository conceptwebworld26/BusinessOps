# 2026-09-15 — M10.2-R.10: the Company Analysis command reaches the strict footing path

**Milestone:** M10.2-R.10 — wire strict dimension footing into `/company-analysis`
**Status on completion:** COMPLETED
**Supersedes:** None

---

## 1. Prompt / task performed

Wire the existing strict external dimension-footing mechanism into the actual
`/company-analysis` execution path, without weakening any existing security, provenance,
evidence or trust rule. Reuse the R.6/R.8/R.9 implementation; create no second provenance
architecture; perform no live research; migrate no other research skill; make no commit and
no push.

Ten parts: inspect the current command and skill; integrate `synthesis.source_footings()`;
make a strict synthesis representation reachable for genuinely footed external facts;
preserve fail-closed behaviour; preserve the trust model; preserve retrieval object
integrity; add focused deterministic tests including a full list of negative controls; add
at least one end-to-end command-level test of the **real production code path**; update
documentation minimally; run the focused tests, the full suite and plugin validation.

## 2. Objective

R.9 closed the skill-level gap and left one sentence in its own limitations:

> **No command wires this up.** `/company-analysis` does not construct a strict
> `SynthesisSet` or author footings; the skill knows how, and nothing invokes it yet. The
> path is proved by test, not by a user-reachable flow.

This milestone makes the path user-reachable. Nothing about admissibility changes.

## 3. Baseline

Established before any edit, in this session:

| Fact | Value |
|---|---|
| HEAD | `8d52b0e24343f2e9b9f586207d2ea841dce61289` (unchanged) |
| Branch | `main` |
| Working tree | 1 modified (`.gitignore`), 16 untracked paths — the pre-existing state |
| Tests, before any edit | `Ran 3333 tests` · `OK (skipped=19)` (R.9's recorded total, re-measured as 3,430 after this milestone's 97) |
| `compatibility.py` md5 | `35a89e32f6fad71bc7c21abe9dbe4915` |
| `quantity.py` md5 | `a43581d8ff7a29b92f5d200fb03818e1` |
| `research/scout.py` md5 | `fe2c4fac1736abea4aaf3c997fdd2b6e` |
| ADRs present | 0001–0016, 0019–0027; next free number **0028** |
| R-12 | open, untouched |

## 4. What the inspection found

Two defects, and only the second was the one the prompt named.

**The command was already correct in shape.** `commands/company-analysis.md` is a
sequencer: it delegates everything downstream to the skill and contains no gate call, no
dispatch and no pipeline code. Three existing tests hold that line
(`test_it_contains_no_second_research_pipeline`,
`test_it_declares_that_it_performs_no_research_step_itself`,
`test_it_restates_no_tiering_or_evidence_rule`). Nothing about R.10 could be written into it
as code without breaking the placement rule and those tests, and correctly so.

**The skill's documented flow could not reach synthesis at all.** Its *Research flow*
section told the model to close a retrieval with `R.close_retrieval(...)`, which returns the
evidence set **serialised**. `synthesis.register_external()` accepts only the object and
refuses a dict, deliberately (ADR-0022, ADR-0024). So the documented production flow
terminated one call short of the synthesis layer, and R.9's example picked up from a
variable named `evidence` that the documented flow never produced.

**Nothing sequenced the five calls.** Between a completed retrieval and a comparison sit
`register_external`, `source_footings` (twice, for two bases), one `DimensionProvenance` for
`unit`, `sourced_statement(dimension_provenance=…)` and a `SynthesisSet` built with
`require_dimension_provenance=True`. That ordering existed only as an example in markdown
and as assembly inside R.9's test module — and its one load-bearing flag defaults to
`False`, which fails **open**.

There is no Python orchestrator for the research commands and there should not be
(ADR-0015: dispatch is model-mediated, the orchestration surface is markdown). So the
insertion point is not a command runner; it is one engine seam the skill calls, in one
process, because objects do not survive between two `python -c` invocations.

## 5. Changes made, in order

1. Verified HEAD, the working tree, the three protected hashes and the ADR numbering.
2. Read the command, the skill, `research/handoff.py`, `research/retrieval.py`,
   `research/evidence_set.py`, `research/scout.py`, `synthesis/merge.py`,
   `synthesis/synthesis_set.py`, `synthesis/dimension_provenance.py`,
   `synthesis/compatibility.py`, `synthesis/contract.py`, and the R.6/R.8/R.9 and M9-C.3 /
   M9-D.1 test modules.
3. Added `lib/python/biq/synthesis/research_footing.py` — `footed_statement()`,
   `evidence_from_retrieval()`, `dimension_report()` and the `FootedStatement` view.
4. Exported them from the `synthesis` package.
5. Proved the path on a scratch script before writing tests: a `BIQ-REC/1` reply →
   `close_retrieval_object` → `footed_statement` → seven resolved dimensions, tier `C`,
   trust `untrusted`, class 3.
6. Updated the skill: `close_retrieval_object` named in *Research flow*, and *Footing a
   figure for comparison* rewritten around the seam.
7. Updated the command: one new step, *Comparing a published figure with your own*.
8. Wrote `tests/unit/test_m10_2r10_company_analysis_command_footing.py` — 97 tests.
9. Ran the focused module, the R.6/R.8/R.9 and seam modules, the Company Analysis modules,
   the M10.1 synthesis modules, the full regression and strict validation.
10. Wrote ADR-0028, the architecture paragraph, the project-plan section and this record.

## 6. The integration path

```
scout reply text (BIQ-REC/1)
    -> research.close_retrieval_object(...)      parse, local tiering, operation binding
           ["evidence_set"]  -> genuine EvidenceSet object            (ADR-0024)
    -> synthesis.footed_statement(retrieval, ORIGIN_COMPANY, text, figure_id,
                                  stated={...}, context={...}, source_unit=...)
           -> register_external(...)                                   evidence registered
           -> source_footings(figure_id, stated, basis=STATED)         (ADR-0027)
           -> source_footings(context_id, context, basis=CONTEXT, applicability=...)
           -> DimensionProvenance("unit", <quantity type>, DERIVED,
                                  derivation="adr0025.canonical_amount.quantity_type")
           -> sourced_statement(..., dimension_provenance=footings)
           -> SynthesisSet(require_dimension_provenance=True).add()
                  -> dimension_provenance.resolve()                    (ADR-0026)
    -> synthesis.compare_values(set, internal_item, footed.statement)
           -> compatibility.compare()
```

`footed_statement()` returns a `FootedStatement` carrying the set, the item, the footings it
authored, `resolved` (what the document established) and `unresolved` (the rest, each with
its reason code) — which is exactly what the skill's output sections 7 and 9 need.

## 7. What the seam decides: nothing

The new module performs **no** evidence lookup, operation binding, document binding,
containment test, applicability test, currency predicate or conflict handling. All of those
stay in `dimension_provenance._assess()` and `resolve()`, reached from `SynthesisSet.add()`.
A test reads the module's own source and asserts the absence of `_registry`, `P_EVIDENCE`,
`_excerpt_present`, `_applies`, `currency_excerpt_carries_code`, `iso_currency_codes`,
`_assess`, `ADMISSIBLE_BASES`, `_fold` and `REASON_TEXT`, that it defines no reason code of
its own, and that it constructs exactly **one** `DimensionProvenance` — the `unit`
derivation whose rule is already in the closed registry.

What it adds is ordering, plus four refusals (ADR-0028):

1. **The evidence must be the object a completed retrieval produced.** `type(...) is
   EvidenceSet`; a serialised `close_retrieval()` result is refused *by name*, pointing at
   `close_retrieval_object`.
2. **The set must be strict.** A `SynthesisSet` without `require_dimension_provenance=True`
   is refused, and the seam's own default set always has it. ADR-0026's additive default is
   unchanged for every other caller.
3. **A dimension is either footed or declared, never both.** Whatever is footed is what the
   statement declares, so the two cannot disagree by typing; a caller supplying a footed
   dimension as a statement field is refused.
4. **A `context` footing names its own evidence item.** No default, because a figure in one
   document and its context in another is the composition ADR-0026 prohibits.

`asserted` has no parameter at all: the seam takes `stated` and `context` claims and nothing
else, and `source_footings()` already refuses `derived` and `asserted`.

## 8. Fixture

One invented results statement for one invented company, written the way ADR-0027 asks the
scout to capture a figure — the sentence stating the number together with the source-stated
context around it, in **one** `content` field. That matters for a reason the R.9 fixture did
not have to face: item ids are content-addressed on `(source, reference, retrieved_at)`, so
two records from one URL in one retrieval collide. In production, one document is one
evidence item, and all six quotable dimensions therefore rest on one item as `stated`
footings. The `context` basis is still exercised, and the cross-document and cross-operation
controls use genuinely separate documents and retrievals.

- Company: `Synthetic Freightworks Ltd` — not a company.
- Document: `https://synthetic-freightworks.example.invalid/fy2025-annual-results.htm`, a
  reserved host that can never resolve. The cross-document control uses
  `commentary.example.invalid`.
- Figure: *"Revenue, defined as total recognised sales before tax, was USD 12.5 billion for
  fiscal year 2025."*
- Context, same document: *"The amount covers worldwide consolidated operations of Synthetic
  Freightworks Ltd and is reported under US GAAP. Synthetic Freightworks Ltd is registered
  at 1 Example Way, Springfield."*

The tier is **not** chosen by the fixture: it is whatever `sources.classify_tier` returns
for a reserved host, which is `C`, inferred. The figure is canonicalised from the `USD
billion` notation by ADR-0025 rather than declared.

## 9. Positive path

| Dimension | Basis | Read from |
|---|---|---|
| `metric_definition` | `stated` | "defined as total recognised sales before tax" |
| `period` | `stated` | "for fiscal year 2025" |
| `currency` | `stated` | "was USD 12.5 billion" |
| `geography` | `stated` | "covers worldwide consolidated operations" |
| `scope` | `stated` | "consolidated operations of Synthetic Freightworks Ltd" |
| `methodology` | `stated` | "is reported under US GAAP" |
| `unit` | `derived` | `adr0025.canonical_amount.quantity_type` |

All seven resolve; `unresolved` is empty; all seven resolution records are `admitted: true`.
The figure canonicalises to `12500000000`, quantity type `currency`, code `USD`. The
statement stays `SOURCED`, external, evidence class 3, `untrusted`, unverified, with
`support` and `confidence` **identical** to an otherwise-identical unfooted statement. The
serialised set validates against `lib/schemas/synthesis.schema.json` and carries no
`verified` key anywhere.

Against a synthetic internal twin built through `AnalysisSet` → `from_analysis_set` on a
registered dataset (engine-footed per ADR-0023, carrying no dimension provenance):

```
status      = compatible
matched     = 7
mismatched  = 0
unknown     = 0
may_combine = True
converted   = False
```

Neither side's kind, trust, domain or value changed, no conflict was recorded, and no
combined figure was produced.

## 10. Negative controls

Every control runs through the production path — `close_retrieval_object` then
`footed_statement` — not against the helper in isolation.

| Group | Controls | Result |
|---|---|---|
| Missing dimension | each of the seven, dropped in turn | `no_dimension_provenance`; dimension `None`; the pair stops at `unknown` naming exactly that dimension |
| Six of seven | every single-drop combination | none reaches `compatible` |
| Nothing stated | no footings at all | seven unresolved, nothing resolved |
| Currency | bare `$` · "US dollars" · an excerpt printing `CEO` | `currency_code_not_in_excerpt` |
| Currency | `XQZ` claimed against `USD billion` notation | refused at construction (ADR-0025) |
| Currency | two admissible codes (`USD`, `EUR`) | `conflicting_admissible_values`; dimension `None`; conflict recorded, neither preferred |
| Bindings | context from another document | `document_mismatch` |
| Bindings | context from another retrieval operation | `operation_mismatch` |
| Bindings | applicability naming another period · no applicability | `applicability_mismatch` |
| Bindings | context with no `context_evidence_id` | `SynthesisError` — no default exists |
| Bindings | footing citing unregistered evidence | `SynthesisError` |
| Excerpt | paraphrase · stitched passages | `excerpt_not_in_source` |
| Excerpt | publication date · source type · reference URL · source name · local tier | `excerpt_not_in_source` — metadata is not content |
| Path | serialised `close_retrieval` result | refused, naming `close_retrieval_object` |
| Path | dict · list · string · serialised set · `EvidenceSet` **subclass** | `SynthesisError` |
| Path | retrieval status `blocked` / `insufficient_evidence` / `not_authorised` | `SynthesisError` |
| Path | non-strict `SynthesisSet` · a non-set | `SynthesisError` |
| Path | internal origin | `SynthesisError` |
| Assertion | declared-but-unfooted dimension | reads as unstated; `declared_dimensions` keeps the audit view |
| Assertion | footed **and** declared | `SynthesisError` |
| Assertion | `evidence_ids` · `dimension_provenance` · `unit` supplied by the caller | `SynthesisError` |
| Assertion | `unit` as a quotation | `SynthesisError` — it names a quantity type |
| Assertion | mistyped dimension · value with no excerpt | `SynthesisError` |
| Assertion | `source_tier` · `trust` · `verified` · `freshness` · `source` | no parameter exists |
| Trust | `SYSTEM:` instruction inside retrieved content | quoted as content; tier stays `C`, trust `untrusted`, no `verified` key |
| Trust | internal `CALCULATION` citing only this evidence | still refused (ADR-0023) |

**One control asserts a limitation rather than a refusal.** A footing quoting the fixture's
registered-address sentence to establish `United States` **is** admissible — the sentence is
genuinely in the source, and containment is not meaning. The test says so plainly, records
the excerpt the reading rests on, and then asserts the consequence that still holds: against
an internal figure stated as worldwide, the comparison is `incompatible` and the two values
stay apart. Pretending that route was blocked would be worse than documenting it.

## 11. Files created

- `lib/python/biq/synthesis/research_footing.py` — the seam.
- `tests/unit/test_m10_2r10_company_analysis_command_footing.py` — 97 tests.
- `docs/decisions/ADR-0028-command-path-footing-is-strict.md`.
- `docs/development/2026-09-15-m10-2r10-company-analysis-command-footing.md` — this record.

## 12. Files modified

- `lib/python/biq/synthesis/__init__.py` — exported the seam (import list, `__all__`,
  submodule list).
- `skills/biq-company-analysis/SKILL.md` — `close_retrieval_object` named in *Research
  flow*; *Footing a figure for comparison* rewritten around `footed_statement()`, with the
  underlying calls kept in prose. Nothing existing was removed or reworded.
- `commands/company-analysis.md` — `dimension footing` added to the skill's ownership list;
  one new step 4, *Comparing a published figure with your own*; the old step 4 renumbered 5.
- `architecture.md` — one new paragraph in the synthesis layer; ADR-0028 added to the
  decisions table.
- `project_plan.md` — one new M10.2-R.10 section.
- `docs/decisions/README.md`, `docs/README.md` — ADR-0028 index entries.

## 13. Files deleted

None.

## 14. Tests performed

```
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_2r10_company_analysis_command_footing
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_2r9_company_analysis_footings tests.unit.test_m10_2r6_dimension_provenance tests.unit.test_m10_2r8_source_context tests.unit.test_m10_2r_provenance_footing tests.unit.test_m10_2r_retrieval_seam
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m9c3_company_analysis tests.unit.test_m9d1_company_analysis_command tests.unit.test_m9_governance tests.unit.test_manifest tests.unit.test_m10_1_synthesis tests.unit.test_m10_1_synthesis_security tests.unit.test_m10_1_synthesis_policy
python tests/run_tests.py
claude plugin validate . --strict
md5sum lib/python/biq/synthesis/compatibility.py lib/python/biq/quantity.py lib/python/biq/research/scout.py
```

## 15. Test results

Real output.

**The new module:**

```
Ran 97 tests in 0.033s
OK
```

**R.6 + R.8 + R.9 + the provenance-footing and retrieval-seam modules, unmodified:**

```
Ran 326 tests in 0.069s
OK
```

**Company Analysis skill and command, governance, manifest and M10.1 synthesis, unmodified:**

```
Ran 297 tests in 0.070s
OK
```

**Full regression, after all edits:**

```
Ran 3430 tests in 130.100s
OK (skipped=19)
ran 3430 | failures 0 | errors 0 | skipped 19
```

3,333 + 97 = 3,430. No existing test was deleted, weakened, disabled or retargeted.

**Strict validation:**

```
Validating marketplace manifest: D:\Prakash\Claude\Plugins\BusinessIQ\BusinessIQ\.claude-plugin\marketplace.json
✔ Validation passed
```

**Protected hashes, re-measured after all edits:**

```
35a89e32f6fad71bc7c21abe9dbe4915  lib/python/biq/synthesis/compatibility.py
a43581d8ff7a29b92f5d200fb03818e1  lib/python/biq/quantity.py
fe2c4fac1736abea4aaf3c997fdd2b6e  lib/python/biq/research/scout.py
```

All three identical to the R.9 baseline.

## 16. Issues discovered

**The skill's Research flow named the wrong closer.** Documented in §4. Found by reading,
not by a failing test, because no test asserted that the flow the skill documents can reach
the synthesis layer. Repaired here.

**Evidence item ids collide for two records from one URL.** `evidence_id()` is
content-addressed on `(source, reference, retrieved_at)`, so a document returned as two
records in one retrieval yields two items with the same id and the registry keeps the
second. Not a security hole — a footing still binds to a real item — but it means the
`context` basis is not reachable for two records of one document through the production
path. In practice it should not need to be: ADR-0027 asks the scout to capture the figure
and its context together, in one `content`, which is what the fixture does. **Not repaired
here**: changing id derivation is a change to a retrieval contract R.10 is not scoped to
touch. Recorded so it is not lost.

**No defect was found** in the R.6, R.8 or R.9 implementation. Every admissibility check
reproduced through the command path behaved exactly as its own tests describe.

## 17. Decisions made

**ADR-0028** — the research command's footing path is one seam, and it is strict by
construction. It meets the bar in `docs/decisions/README.md` on two counts: it constrains
future work (the three unmigrated research skills migrate by calling it), and it narrows
ADR-0026's deliberately additive default for one path, which is a decision a reviewer would
otherwise ask about. **No accepted ADR was edited.** ADR-0027 §17 remains as written, and
the note R.9 proposed for it is still proposed and still not applied.

## 18. Architecture changes

One new paragraph in the synthesis layer's dimension-admissibility discussion, naming
`synthesis.footed_statement()`, its four refusals, and what it deliberately does not do; one
row added to the decisions table. Nothing existing was rewritten and no ADR was reopened.

## 19. Documentation updates

- `architecture.md` — §18 above.
- `project_plan.md` — one new `### M10.2-R.10 … COMPLETED` section before `### M10.3
  onward`. M10.2-R stays `PARTIALLY VERIFIED`; no other status changed.
- `docs/decisions/ADR-0028-command-path-footing-is-strict.md` — new.
- `docs/decisions/README.md`, `docs/README.md` — index rows.
- `docs/development/2026-09-15-m10-2r10-company-analysis-command-footing.md` — this record.
- `docs/README.md`'s ADR list is **stale** and was so before this milestone: it carries
  0001–0016, 0025 and now 0028, and is missing 0017–0024, 0026 and 0027. The new entry was
  added because the convention requires it; the pre-existing gap is flagged here rather than
  repaired, which is out of scope.
- `docs/development/README.md` — **not changed.** Its index has been stale since M9-B and
  carries no row for the R.6, R.8 or R.9 records either; R.9 flagged the same thing.
- `docs/skills/` — not changed; it holds only a README with no per-skill page.

## 20. Remaining limitations

1. **Containment is still not meaning** (§10). Unchanged by this milestone and unclosable by
   code.
2. **Supply still depends on guidance.** Whether the scout captures dimension-bearing text
   and whether the skill quotes it faithfully rests on two definitions rather than on a
   type. The seam removes the *ordering* from guidance; it cannot remove the *locating*.
3. **A source that does not state all seven dimensions cannot reach `compatible`.** The
   fixture states six quotable ones because it was written to. The M10.2-R.4 live run found
   a real document that stated four. This milestone does not make an ALLOW more frequent in
   practice and must not be read as evidence that it is.
4. **A currency name still establishes nothing** (ADR-0027 §23, open by decision).
5. **Cross-document context stays prohibited.**
6. **Two records from one document cannot foot each other** through the production path
   (§16).
7. **Three research skills remain unmigrated.** `biq-market-analysis`,
   `biq-competitor-analysis` and `biq-industry-research` are untouched and behave exactly as
   before.
8. **Nothing here is verified live.** Every fixture is synthetic and in-memory; no network
   was reached, no scout was dispatched, and R-12 produced no evidence in either direction.

## 21. R-12 status

**Open, untouched, and not progressed.** No scout was dispatched and no hand-back was
parsed. This milestone was designed to prove the command path without depending on live
scout reliability.

## 22. Live research

**None.** No `WebSearch`, no `WebFetch`, no scout dispatch, no network access of any kind.
Every source is an invented sentence on a reserved `.invalid` host.

## 23. Git commit reference

**N/A — no commit, no push.** HEAD is unchanged at
`8d52b0e24343f2e9b9f586207d2ea841dce61289`. The working tree carries the changes in §11–12
and nothing else; no existing working-tree change was reset or discarded.
