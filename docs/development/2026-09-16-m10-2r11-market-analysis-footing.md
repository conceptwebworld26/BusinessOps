# 2026-09-16 — M10.2-R.11: Market Analysis reaches the strict footing path

**Milestone:** M10.2-R.11 — migrate `/market-analysis` to the R.10 footing seam
**Status on completion:** COMPLETED
**Supersedes:** None

---

## 1. Prompt / task performed

Migrate the Market Analysis skill and `/market-analysis` command path so that externally
sourced quantitative/comparable facts use the strict dimension-footing production path
established by M10.2-R.10, to prove that the R.10 seam is reusable across another research
domain without weakening any security or provenance boundary.

Ten parts: inspect the current implementation without assuming it matches Company Analysis;
update the skill's guidance; wire the production path; preserve the canonical intents;
preserve the distinction between qualitative research and dimension-sensitive quantitative
claims; add focused deterministic tests including a full list of fail-closed controls; add a
real command-level integration test that is not a renamed copy of R.10's; run the regression
suites; update documentation minimally; leave protected components alone.

## 2. Objective

R.10 ended with one open question. `footed_statement()` had exactly one caller, so nothing
distinguished "a seam" from "the Company Analysis path with a general-sounding name". The
test of that is whether a second domain can use it, and what the second domain needs that
the first did not.

## 3. Baseline

Established before any edit, in this session:

| Fact | Value |
|---|---|
| HEAD | `8d52b0e24343f2e9b9f586207d2ea841dce61289` (unchanged) |
| Branch | `main` |
| Working tree | 1 modified (`.gitignore`), 16 untracked paths — the pre-existing state |
| Tests, before any edit | 3,430 (R.10's recorded total) |
| `compatibility.py` md5 | `35a89e32f6fad71bc7c21abe9dbe4915` |
| `quantity.py` md5 | `a43581d8ff7a29b92f5d200fb03818e1` |
| `research/scout.py` md5 | `fe2c4fac1736abea4aaf3c997fdd2b6e` |
| Market Analysis tests | 190, across `test_m9d2_market_analysis.py` and `test_m9d2_market_analysis_command.py` |
| ADRs | 0001–0016, 0019–0028; no new number allocated by this milestone |

## 4. What the inspection found

**The same defect R.10 found, in the same place.** The skill's *Research flow* told its model
to close a retrieval with `R.close_retrieval(...)`, which returns the evidence set
serialised — the one shape `register_external()` refuses — so the documented flow could not
reach the synthesis layer.

**One thing Company Analysis did not have: the rule already existed in prose.** *The
market-size compatibility test* is a five-row table stating exactly what R.6 built, in the
skill that needs it most, and an existing test pins `**all five must hold**`. That is a
second statement of a rule the engine owns, which under ADR-0012 is the condition to link
rather than paraphrase. R.11 does not delete it — it is correct, it is what a reader needs,
and deleting it would be a regression in guidance. It connects it: the section added below
maps the five rows onto the engine's seven dimensions and says which code enforces them.

**The mapping exposed a real gap in the prose.** Five rows, seven dimensions:

| Skill's row | Engine dimension |
|---|---|
| market definition | `metric_definition` |
| geography | `geography` |
| unit and currency | `unit` **and** `currency` — one row, two dimensions |
| time period | `period` |
| methodology or basis | `methodology` |
| *(folded inside "definition")* | **`scope`** |

`scope` is the one market sizing needs more than any other research question. A total
addressable market and a served market can share a definition, a geography, a period, a
currency and a method and still be different quantities. The engine has always asked it;
the table left it implicit. Recording the mapping makes the engine stricter than the prose,
never weaker, which is the only direction this may go.

**Three things are genuinely different from Company Analysis**, and they shaped the work:

1. **The characteristic comparison is external-to-external.** Company Analysis sets a
   published figure beside the user's own. Market sizing asks whether two *published* sizes
   measure one quantity. `compare()` needs no change for this, and `compare_values()`
   correctly records a limitation without a cross-domain conflict, because neither figure is
   the user's.
2. **Most of the report is not footable.** Sections 4–7 are qualitative. Forcing seven
   dimensions onto "automation adoption is rising" would be fabrication in the one place
   nothing would check it.
3. **The share trap.** A market share is a ratio between a numerator and a denominator, not
   a comparison of like with like. The engine says `incompatible` on `scope` when revenue is
   set beside a TAM, and that verdict is correct rather than a limitation.

**The decisive finding: no production code was needed.** `ORIGIN_MARKET` is already in
`EXTERNAL_ORIGINS`, `footed_statement()` names no domain, and `compare()` reads seven
dimensions without knowing what produced them. **No file under `lib/` was modified, created
or deleted in this milestone**, and a test asserts the seam's source contains neither
`company` nor `market`.

## 5. Changes made, in order

1. Verified HEAD, the working tree, the three protected hashes and the 190 existing Market
   Analysis tests.
2. Read the skill, the command, both existing test modules, the R.10 implementation,
   `research_footing.py`, `dimension_provenance.py` and the retrieval contracts.
3. Proved the path on a scratch script before writing guidance: a `BIQ-REC/1` sizing reply →
   `close_retrieval_object` → `footed_statement(ORIGIN_MARKET)` → seven resolved dimensions;
   a matching internal model → compatible; a wider definition → incompatible; a qualitative
   statement in the same strict set → declared period kept, resolved period `None`.
4. Updated the skill: `close_retrieval_object` named in *Research flow*, and a new section,
   *Footing a size figure for comparison*.
5. Updated the command: `dimension footing` added to the skill's ownership list; one new
   step 4, *Relating one size figure to another*; the old step 4 renumbered 5.
6. Wrote `tests/unit/test_m10_2r11_market_analysis_footing.py` — 136 tests.
7. Ran the focused module, the Market Analysis modules, the R.6/R.8/R.9/R.10 provenance
   modules, the synthesis modules, the retrieval integrity modules, the full regression and
   strict validation.
8. Wrote the architecture paragraphs, the project-plan section and this record.

## 6. The integration path

```
scout reply text (BIQ-REC/1), claim_kind market_sizing
 → research.close_retrieval_object(...)["evidence_set"]      genuine EvidenceSet (ADR-0024)
 → synthesis.footed_statement(retrieval, ORIGIN_MARKET, text, sized_id, stated={...})
      register_external → source_footings(STATED) → one DERIVED unit footing
      → sourced_statement(dimension_provenance=…) on SynthesisSet(strict) → resolve()
 → synthesis.compare_values(...) → compatibility.compare()
        external ↔ external   two published sizes
        external ↔ internal   a published size and the user's own market model
```

Qualitative findings from the same run take the untouched path —
`sourced_statement(synthesis, ORIGIN_MARKET, …)` with no `dimension_provenance` — into the
**same** strict set.

## 7. Guidance added

One new skill section, *Footing a size figure for comparison*, placed after the five-check
table it operationalises and before *Forecasts and growth rates*. It states:

- the five-to-seven mapping and why `scope` is the seventh;
- **what needs footing and what does not** — a two-row table separating quantitative
  comparable claims (size, published CAGR, volume, a measured share) from qualitative ones
  (trend, driver, constraint, structure), and the sentence that matters most: *a qualitative
  finding carrying no footings is complete work, not incomplete work*;
- the production call, with `close_retrieval_object`, `footed_statement`, a qualitative
  `sourced_statement` and `compare_values` in one block;
- contiguous verbatim excerpts, no paraphrase, summary, translation or stitching, no
  cross-document context, and missing context staying missing;
- seven market-specific *never inferred* prohibitions — definition never from the market's
  name; geography never from the publisher's country, domain, TLD or the currency quoted;
  period never from the publication date or title year; currency never from a bare symbol or
  a currency name; scope never from the phrase "market size"; methodology never from the
  source type; unit never quoted at all;
- what footing does not change — the statement stays `SOURCED`/untrusted/class 3/unverified,
  a footed CAGR becomes *comparable* and never *true*, nothing is averaged, `compatible` is
  not an instruction to combine, **a share is not a comparison**, and the ten sections are
  unchanged.

The command gains one step in prose and no logic: it names the comparison, states that a
dimension no source stated stays unknown, says qualitative findings take none of this, and
refuses any combined figure, midpoint, growth rate or market share following from a verdict.

## 8. Fixture

Two synthetic sizing reports and one trade commentary, on reserved hosts that can never
resolve.

- Report A, `synthetic-sizing.example.invalid`: *"The cold chain logistics market, defined as
  refrigerated warehousing and transport only, was valued at USD 278.4 billion for calendar
  year 2025. The estimate covers the global total addressable market and was produced on a
  bottom-up basis from operator revenue."*
- Report B, `second-sizing.example.invalid`: the same market on a wider boundary
  (warehousing, transport, packaging, monitoring and last-mile), USD 412.0 billion — the
  factor-of-three disagreement market sizing is famous for, in miniature.
- A third variant agrees with A on every dimension and differs only in the figure.
- Trade commentary, `trade-commentary.example.invalid`, `claim_kind: market_trends`, for the
  qualitative path.

Tiers are not chosen by the fixture: `sources.classify_tier` returns `C`, inferred, for a
reserved host, and that is what the items carry. Figures are canonicalised from `USD billion`
notation by ADR-0025.

The internal counterpart is the user's **own bottom-up market model**, built through
`AnalysisSet` → `from_analysis_set` on a registered dataset. That is the honest internal
analogue of a published market size: the user's revenue is a numerator, not the same
quantity. The analytics domain is `financial` because that is the internal domain producing
currency aggregates; no new internal domain was invented.

## 9. Positive results

| Dimension | Basis | Read from |
|---|---|---|
| `metric_definition` | `stated` | "defined as refrigerated warehousing and transport only" |
| `period` | `stated` | "for calendar year 2025" |
| `currency` | `stated` | "was valued at USD 278.4 billion" |
| `geography` | `stated` | "covers the global total addressable market" |
| `scope` | `stated` | "the global total addressable market" |
| `methodology` | `stated` | "produced on a bottom-up basis from operator revenue" |
| `unit` | `derived` | `adr0025.canonical_amount.quantity_type` |

All seven resolve. The statement stays `SOURCED`, external, class 3, `untrusted`, unverified,
with `support` and `confidence` identical to an unfooted twin. The set validates against
`lib/schemas/synthesis.schema.json`, `recommendations` is empty, and no `verified` key
appears anywhere.

```
two published sizes, one definition   compatible   · 7 matched · may_combine True
two published sizes, wider boundary   incompatible · mismatched: metric_definition
published size vs own market model    compatible   · 7 matched · 0 mismatched · 0 unknown
                                                   · may_combine True · converted False
own revenue vs total addressable      incompatible · mismatched: scope
```

Nothing was averaged, converted or combined in any of the four, and neither side of any pair
changed kind, trust, domain or value.

## 10. Fail-closed controls

All run through the production path — `close_retrieval_object` then `footed_statement`.

| Group | Controls | Result |
|---|---|---|
| Missing dimension | each of the seven, dropped in turn | `no_dimension_provenance`; `unknown` naming exactly that dimension, against an internal figure **and** against a second source |
| Six of seven | every single-drop combination, both comparison directions | none reaches `compatible` |
| Nothing stated | no footings at all | seven unresolved |
| Currency | bare `$` · "US dollars" · a `CEO`-shaped token | `currency_code_not_in_excerpt` |
| Currency | `XQZ` against `USD billion` notation | refused at construction (ADR-0025) |
| Conflicting context | two currency codes · two methodologies | `conflicting_admissible_values`; dimension `None`; disagreement recorded, neither preferred |
| Bindings | context from another document · another operation | `document_mismatch` · `operation_mismatch` |
| Bindings | applicability with a wrong period · a wrong scope · none declared | `applicability_mismatch` |
| Bindings | context with no named evidence item · unregistered evidence | `SynthesisError` |
| Excerpt | paraphrase · translation · stitched passages | `excerpt_not_in_source` |
| Metadata | reference URL · bare domain · source name · publication date · source type · local tier | `excerpt_not_in_source` |
| Path | serialised `close_retrieval` result | refused, naming `close_retrieval_object` |
| Path | dict · list · string · `None` · serialised set · `EvidenceSet` **subclass** | `SynthesisError` |
| Path | `blocked` · `insufficient_evidence` · `not_authorised` · a real zero-record retrieval | `SynthesisError` |
| Path | non-strict `SynthesisSet` · a non-set · internal origins | `SynthesisError` |
| Assertion | declared-but-unfooted dimension | reads as unstated; `declared_dimensions` keeps the audit view |
| Assertion | footed **and** declared · `evidence_ids` · `dimension_provenance` · `unit` | `SynthesisError` |
| Assertion | `unit` as a quotation · mistyped dimension · value with no excerpt | `SynthesisError` |
| Assertion | `asserted` basis, by any route | no parameter exists; `source_footings` refuses it |
| Assertion | `source_tier` · `trust` · `verified` · `freshness` · `source` | no parameter exists |
| Trust | `SYSTEM:` instruction inside retrieved content | quoted as content; tier `C`, trust `untrusted`, no `verified` |

**One control asserts a limitation rather than a refusal**, as R.10's did. `_excerpt_present`
searches `title` as well as `content`, so a footing quoting the report's title to establish
the market definition really is quoting the source and admissibility cannot catch it. The
guidance prohibits it — *never from the market's name* — and the test says so plainly, then
asserts what still holds: set beside a source that published an actual boundary, the pair is
`incompatible` on `metric_definition`.

## 11. The qualitative boundary, proved

- A trend statement carries no footings, an empty `dimension_resolution`, and no conflict.
- It remains `SOURCED`, class 3, cited, and resolvable to its evidence item.
- It may declare `period` and `geography`: `as_dict()` keeps them for sections 4 and 8, while
  `dimensions` reads them as unstated.
- It therefore **cannot reach `compatible` by accident** — compared with a footed size it
  returns `unknown`.
- Footed and unfooted statements coexist in one strict set, which still validates against the
  schema.

## 12. Files created

- `tests/unit/test_m10_2r11_market_analysis_footing.py` — 136 tests.
- `docs/development/2026-09-16-m10-2r11-market-analysis-footing.md` — this record.

## 13. Files modified

- `skills/biq-market-analysis/SKILL.md` — `close_retrieval_object` named in *Research flow*;
  one new section, *Footing a size figure for comparison*. Nothing existing was removed or
  reworded, and the five-check table is untouched.
- `commands/market-analysis.md` — `dimension footing` added to the skill's ownership list;
  one new step 4; the old step 4 renumbered 5.
- `architecture.md` — two new paragraphs in the synthesis layer.
- `project_plan.md` — one new M10.2-R.11 section.

**No file under `lib/` was modified, created or deleted.** No ADR was created or edited.

## 14. Files deleted

None.

## 15. Tests performed

```
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_2r11_market_analysis_footing
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m9d2_market_analysis tests.unit.test_m9d2_market_analysis_command
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_2r6_dimension_provenance tests.unit.test_m10_2r8_source_context tests.unit.test_m10_2r9_company_analysis_footings tests.unit.test_m10_2r10_company_analysis_command_footing tests.unit.test_m10_2r_provenance_footing
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_1_synthesis tests.unit.test_m10_1_synthesis_security tests.unit.test_m10_1_synthesis_policy tests.unit.test_m10_2r_retrieval_seam tests.unit.test_m10_2r2_unit_semantics tests.unit.test_m10_2r3_allow_branch tests.unit.test_m10_2r_live_compatibility
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m9a_invariants tests.unit.test_m9a_research_core tests.unit.test_research_scout_boundary tests.unit.test_m9b_scout_contract tests.unit.test_m9c15_production_protocol tests.unit.test_m9_governance tests.unit.test_manifest
python tests/run_tests.py
claude plugin validate . --strict
md5sum lib/python/biq/synthesis/compatibility.py lib/python/biq/quantity.py lib/python/biq/research/scout.py
find lib -newermt "2026-09-16 00:00" -type f -name "*.py"
```

## 16. Test results

Real output.

**The new module:**

```
Ran 136 tests in 0.052s
OK
```

**Existing Market Analysis skill and command, unmodified:**

```
Ran 190 tests in 0.078s
OK
```

**R.6 + R.8 + R.9 + R.10 provenance and footing modules, unmodified:**

```
Ran 399 tests in 0.092s
OK
```

**M10.1 synthesis, the retrieval seam, unit semantics and the allow branch, unmodified:**

```
Ran 287 tests in 0.672s
OK
```

**Retrieval integrity, scout boundary, protocol, governance and manifest, unmodified:**

```
Ran 328 tests in 0.139s
OK
```

**Full regression, after all edits:**

```
Ran 3566 tests in 470.142s
OK (skipped=19)
ran 3566 | failures 0 | errors 0 | skipped 19
```

3,430 + 136 = 3,566. No existing test was deleted, weakened, disabled or retargeted.

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

All three identical to the R.9 and R.10 baselines. `find lib -newermt 2026-09-16` returned
nothing: no engine file was touched at all.

## 17. Issues discovered

**One test of mine was wrong and was corrected, not the code.** A first draft asserted that
`compatibility.py` contains no occurrence of the word "market". It always has — its docstring
uses *"a market growing 4%"* as its motivating example, and it references the
industry-research skill by name. Asserting the absence of something that was never true is a
broken test, not a finding; the assertion now checks the tokens that actually matter
(`provenance`, `EvidenceSet`, `evidence`, `source_tier`, `registry`, `admissible`, `footing`,
`ORIGIN_`) and says in its docstring why "market" is excluded.

**A documentation-placement tension, resolved by linking rather than deleting.** The skill's
five-check table states a rule the engine owns. ADR-0012 says link rather than paraphrase.
Deleting the table would have been the literal reading and the wrong call: it predates the
engine's enforcement, an existing test pins it, and it is what a reader of the skill needs.
The new section names the engine as the enforcer and maps the rows onto the dimensions, which
is the link ADR-0012 asks for, with the prose kept.

**No defect was found** in the R.6, R.8, R.9 or R.10 implementation. Every control reproduced
through a second domain behaved exactly as its own tests describe.

## 18. Decisions made

**None requiring an ADR.** ADR-0028 already names migrating the remaining research skills as
its own follow-up, and this is that follow-up performed as written. No approved ADR was
edited — including to record that the follow-up is now one skill further on. That status
lives in `project_plan.md`.

## 19. Documentation updates

- `architecture.md` — two new paragraphs: the seam carrying a second domain with no engine
  change, and footing being required of quantitative claims rather than of research.
- `project_plan.md` — one new `### M10.2-R.11 … COMPLETED` section before `### M10.3 onward`.
  M10.2-R stays `PARTIALLY VERIFIED`; no other status changed.
- `docs/development/2026-09-16-m10-2r11-market-analysis-footing.md` — this record.
- `docs/decisions/` — **not changed.** No ADR was created, and ADR-0026, ADR-0027 and
  ADR-0028 are untouched.
- `docs/README.md` — not changed; no new ADR to index. Its ADR list remains stale as flagged
  in the R.10 record.
- `docs/development/README.md` — **not changed.** Its index has been stale since M9-B and
  carries no row for the R.6, R.8, R.9 or R.10 records either.

## 20. Remaining limitations

1. **Containment is still not meaning**, and market sizing's version of it is the title-as-
   definition route in §10. Unchanged by this milestone and unclosable by code.
2. **Supply still depends on guidance.** Whether the scout captures the boundary, basis and
   scope sentences, and whether the skill quotes them faithfully, rests on two definitions
   rather than on a type.
3. **A source stating fewer than seven dimensions cannot reach `compatible`,** and market
   reports state their methodology and scope less often than the fixture does. R.11 does not
   make an ALLOW more frequent in practice and must not be read as evidence that it is; if
   anything, market sizing is the domain where the honest answer is most often *not
   comparable*.
4. **A currency name still establishes nothing** (ADR-0027 §23, open by decision).
5. **Cross-document context stays prohibited**, so a size in one report and the definition it
   was computed on in another remain uncombinable — a real pattern in market research, where
   methodology often sits in a separate methodology note.
6. **Two records from one document cannot foot each other** through the production path, for
   the id-derivation reason recorded in the R.10 record §16.
7. **The qualitative/quantitative split is guidance, not a type.** Nothing in code stops a
   skill from routing a size figure through `sourced_statement()` unfooted; what the strict
   set guarantees is only that an unfooted dimension never reads as a match.
8. **Two research skills remain unmigrated.** `biq-competitor-analysis` and
   `biq-industry-research` are untouched and behave exactly as before.
9. **Nothing here is verified live.** Every fixture is synthetic and in-memory; no network
   was reached, no scout was dispatched, and R-12 produced no evidence in either direction.

## 21. R-12 status

**Open, untouched, and not progressed.** No scout was dispatched and no hand-back was parsed.

## 22. Live research

**None.** No `WebSearch`, no `WebFetch`, no scout dispatch, no network access of any kind.
Every source is an invented sentence on a reserved `.invalid` host.

## 23. Git commit reference

**N/A — no commit, no push.** HEAD is unchanged at
`8d52b0e24343f2e9b9f586207d2ea841dce61289`. The working tree carries the changes in §12–13
and nothing else; no existing working-tree change was reset or discarded.
