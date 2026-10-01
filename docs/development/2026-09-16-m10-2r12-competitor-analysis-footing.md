# 2026-09-16 — M10.2-R.12: Competitor Analysis reaches the strict footing path

**Milestone:** M10.2-R.12 — migrate `/competitor-analysis` to the R.10/R.11 footing seam
**Status on completion:** COMPLETED
**Supersedes:** None

---

## 1. Prompt / task performed

Migrate the Competitor Analysis skill and `/competitor-analysis` command path to the strict
dimension-footing production path used by Company Analysis and Market Analysis, proving that
competitor analysis can represent and compare externally sourced quantitative claims without
weakening provenance, source-context, trust or compatibility controls.

Twelve parts: inspect without assuming the Company/Market flows are identical; preserve the
existing intents and behaviour; define the qualitative/quantitative boundary explicitly; wire
the production path; reuse the seam exactly; handle competitor-to-competitor comparison
correctly; add focused deterministic tests; test the real command-level flow; preserve output
semantics (no ranking, no winner, no scores); run the regression suites; update documentation
minimally; leave protected components alone.

## 2. Objective

R.11 showed the seam carried a second domain. Competitor Analysis is the third and the one
where a `compatible` verdict is most dangerous, because the whole point of the comparison is
to put **different companies'** figures beside one another — and the seven dimensions contain
no company.

## 3. Baseline

| Fact | Value |
|---|---|
| HEAD | `62580f3f9368b5924360d19e0e62c977ee39136a` — *M10.2: checkpoint through R.11* |
| Branch | `main`, in sync with `origin/main` |
| Working tree | clean at start |
| Tests before any edit | 3,566 |
| `compatibility.py` md5 | `35a89e32f6fad71bc7c21abe9dbe4915` |
| `quantity.py` md5 | `a43581d8ff7a29b92f5d200fb03818e1` |
| `research/scout.py` md5 | `fe2c4fac1736abea4aaf3c997fdd2b6e` |
| Competitor Analysis tests | 252, across `test_m9d3_competitor_analysis.py` and `test_m9d3_competitor_analysis_command.py` |
| ADRs | 0001–0016, 0019–0028; none allocated by this milestone |

## 4. What the inspection found

**The familiar defect, in the same place.** The skill's *Research flow* told its model to
close a retrieval with `R.close_retrieval(...)`, which serialises the evidence set — the one
shape `register_external()` refuses.

**The comparability test already existed in prose, and its rows do not map one-to-one.**
Unlike Market Analysis, where `scope` was missing from the table entirely, Competitor
Analysis's five rows cover all seven dimensions, with **two rows splitting in two**:

| Skill's row | Engine dimension(s) |
|---|---|
| metric definition | `metric_definition` |
| period | `period` |
| currency and unit | `currency` **and** `unit` |
| geography **or segment scope** | `geography` **and** `scope` |
| basis | `methodology` |

Row 4 is the one worth separating. `geography` is the territory; `scope` is which slice of
the company — consolidated group, a named segment, a business unit. A worldwide group figure
and a worldwide segment figure share a geography and are not the same quantity, and folding
them into one row is exactly how that pair gets compared by accident. Splitting them can only
refuse more often, so nothing in the mapping loosens the existing rule.

**Three things are genuinely different from the earlier domains:**

1. **The entity is not a dimension, and must not be.** `compare()` has no company field. Two
   rivals' revenue figures sharing all seven dimensions *are* compatible — correctly, because
   that is what permits them to sit in one row of section 4. The danger is not the verdict; it
   is what someone might do with it. So the guidance states the boundary in one sentence — *a
   compatible verdict authorises a row, not an order* — and the tests pin it.
2. **Comparison is usually external-to-external**, so `compare_values()` records a limitation
   and no cross-domain conflict. That is right: `internal_external` means *our number versus
   theirs*, and neither of two rivals' figures is ours.
3. **Two companies' filings are always two documents**, so ADR-0026's cross-document
   prohibition is not an edge case here — it is the normal shape of the data. One rival's
   disclosure can never foot another rival's figure.

**The decisive finding: no production code was needed.** `ORIGIN_COMPETITOR` is already in
`EXTERNAL_ORIGINS` and `footed_statement()` names no domain. **No file under `lib/` was
modified, created or deleted**, and a test asserts the seam's source contains none of
`competitor`, `ORIGIN_COMPETITOR`, `rival`, `company`, `market`, `industry`, `ranking` or
`share`.

## 5. Changes made, in order

1. Verified HEAD, the clean tree, the three protected hashes and the 252 existing tests.
2. Read the skill, the command, both existing test modules, the R.10 and R.11
   implementations, `research_footing.py` and the retrieval contracts.
3. Proved the path on a scratch script first: a `BIQ-REC/1` comparison reply →
   `close_retrieval_object` → two `footed_statement` calls → seven dimensions each →
   compatible between rivals, `incompatible` on a period mismatch, compatible against an
   internal figure, and a qualitative statement returning `unknown`.
4. Updated the skill: `close_retrieval_object` named in *Research flow*, and a new section,
   *Footing a figure for comparison*, placed after *No rankings, no scores* so the two are
   read together.
5. Updated the command: `dimension footing` added to the skill's ownership list; one new
   step 4, *Setting one company's figure beside another's*; the old step 4 renumbered 5.
6. Wrote `tests/unit/test_m10_2r12_competitor_analysis_footing.py` — 157 tests.
7. Ran the focused module, the Competitor Analysis modules, the R.6–R.11 provenance modules,
   the synthesis modules, the retrieval integrity modules, the full regression and strict
   validation.
8. Raised the one existing-test conflict with the user and applied the decided resolution.
9. Wrote the architecture paragraph, the project-plan section and this record.

## 6. The integration path

```
scout reply text (BIQ-REC/1), two filings, one comparison operation
 → research.close_retrieval_object(...)["evidence_set"]      genuine EvidenceSet (ADR-0024)
 → synthesis.footed_statement(retrieval, ORIGIN_COMPETITOR, text, item_id, stated={...})
      register_external → source_footings(STATED) → one DERIVED unit footing
      → sourced_statement(dimension_provenance=…) on SynthesisSet(strict) → resolve()
   … the same call again for the rival, passing synthesis= the same set
 → synthesis.compare_values(...) → compatibility.compare()
        external ↔ external   rival against rival — the characteristic case
        external ↔ internal   a rival's figure and the user's own, on one basis
```

Qualitative findings from the `landscape`, `positioning` and `developments` retrievals take
the untouched path — `sourced_statement(...)` with no `dimension_provenance` — into the
**same** strict set.

## 7. Guidance added

One new skill section, *Footing a figure for comparison*, deliberately placed immediately
after *No rankings, no scores*. It states:

- the five-to-seven mapping, with `geography` and `scope` separated and the note that nothing
  in the mapping loosens the five checks;
- **the entity is not one of the seven, and must not be** — and therefore *a `compatible`
  verdict authorises a row, not an order*;
- **footing does not touch identification** — an `observed` candidate with seven perfectly
  footed dimensions is still `observed`;
- what needs footing and what does not, as a two-row table naming the quantitative kinds
  (published revenue or reported sales, a published market share, unit volumes, published
  pricing figures, published growth rates, financial ratios) and the qualitative ones
  (positioning, feature observations, strategic moves, stated initiatives, product and
  service descriptions, source-stated strengths or constraints), with *sections 2, 3, 5, 6
  and 7 are normally entirely unfooted*;
- the production call, with `close_retrieval_object`, two `footed_statement` calls sharing one
  set, a qualitative `sourced_statement` and `compare_values` in one block;
- contiguous verbatim excerpts, no paraphrase/summary/translation, no stitching, missing
  context staying missing, and **two companies' filings are always two documents**;
- seven competitor-specific *never inferred* prohibitions — definition never from the word
  *revenue*; period never from the publication or filing date (two companies' "FY2025" are
  routinely twelve different months); currency never from a bare symbol, a name, or where the
  company is based; geography never from headquarters, incorporation, domicile or listing
  venue; scope never from company identity; methodology never from the source type (a filing
  implies neither IFRS nor US GAAP); unit never quoted;
- what footing does not change — the statement stays `SOURCED`/untrusted/class 3/unverified;
  **a self-claim stays a self-claim**; **no ranking follows**; **no market share follows**
  (a compatible pair of revenue figures is two numerators and no denominator); nothing is
  averaged, bridged or combined; the ten sections are unchanged.

The command gains one step in prose and no logic, including *comparable is not an order* and
the statement that a figure turning out comparable never promotes an `observed` candidate.

## 8. Fixture

Two invented results statements on reserved hosts, plus one trade-press item.

- `contoso-logistics.example.invalid` — *"Contoso Logistics reported total group revenue,
  defined as consolidated net sales excluding intra-group transactions, of USD 4.20 billion
  for fiscal year 2025. The figure covers worldwide operations of the consolidated group and
  is reported under IFRS."*
- `fabrikam-freight.example.invalid` — the same shape at USD 3.15 billion, plus variants for a
  prior fiscal year, a cold chain **segment** figure and a **US GAAP** basis.
- `trade-press.example.invalid` — a positioning and developments sentence, `claim_kind:
  positioning`, for the qualitative path.

Tiers are not chosen by the fixture: `classify_tier` returns `C`, inferred, for a reserved
host. Figures are canonicalised from `USD billion` notation by ADR-0025. The internal
counterpart is the user's own group revenue on the same definition, period, territory, slice
and basis, built through `AnalysisSet` → `from_analysis_set` on a registered dataset.

## 9. Positive results

All seven dimensions resolve for each rival — six `stated` plus one `derived` `unit` — and
`geography` (`worldwide`) and `scope` (`consolidated group`) resolve to different values.
Statements stay `SOURCED`, external, class 3, `untrusted`, unverified, with `support` and
`confidence` identical to an unfooted twin. The set validates against the schema,
`recommendations` is empty and no `verified` key appears.

```
rival A vs rival B, one basis        compatible   · 7 matched · 0 mismatched · 0 unknown
                                                 · may_combine True · converted False
rival A vs rival B, prior year       incompatible · mismatched: period
rival A vs rival B, segment figure   incompatible · mismatched: scope   (geography matches)
rival A vs rival B, US GAAP          incompatible · mismatched: methodology
rival A vs our own revenue           compatible   · 7 matched · may_combine True
our segment figure vs their group    incompatible · mismatched: scope
```

Nothing was averaged, converted or combined in any of them; the two rivals' values stayed
4,200,000,000 and 3,150,000,000, and neither side changed kind, trust, domain or value. The
larger figure gained no kind, trust, support or confidence from being larger.

## 10. Fail-closed controls

All run through the production path. Seven missing-dimension controls, each resolving to
`no_dimension_provenance` and stopping at `unknown` naming that dimension, against **both** a
rival and an internal figure; six-of-seven never compatible on either path; nothing-stated;
bare `$`, "US dollars" and a `CEO`-shaped token → `currency_code_not_in_excerpt`; `XQZ`
refused at construction; conflicting currencies, methodologies **and scopes** →
`conflicting_admissible_values`; a rival's filing footing the focal figure →
`document_mismatch`; `operation_mismatch`; `applicability_mismatch` for wrong period, wrong
scope and undeclared applicability; unnamed context item and unregistered evidence refused;
paraphrase, translation and stitching → `excerpt_not_in_source`; URL, bare domain, source
name, publication date, source type and local tier → `excerpt_not_in_source`; serialised
`close_retrieval` result refused by name; dict/list/string/`None`/serialised set/`EvidenceSet`
**subclass** refused; `blocked`, `insufficient_evidence`, `not_authorised` and a real
zero-record retrieval refused; non-strict set, non-set and internal origins refused;
declared-but-unfooted reads unstated; footed-and-declared refused; `evidence_ids`,
`dimension_provenance` and `unit` refused as caller fields; `unit` as a quotation refused;
`asserted` unreachable by any route; mistyped dimension and excerpt-less value refused;
`source_tier`/`trust`/`verified`/`freshness`/`source` have no parameter; and a `SYSTEM:`
instruction telling the page to rank the company first and mark itself verified tier A leaves
tier `C`, trust `untrusted`, no `verified` key and no recommendation.

**Two controls assert a limitation rather than a refusal**, in a class of their own
(`ContainmentIsNotMeaning`). A footing quoting the report's *title* to claim a fiscal year,
and one quoting the sentence that names the company to claim a scope, are both **admitted** —
the text really is in the source, and on this path the statement declares whatever the footing
claims. The guidance prohibits both; no code can catch either. What the tests assert is what
remains true: the reading is recorded against the text it rests on, and it agrees with nothing
by accident — set beside a source that stated the real value, each comes out `incompatible`.

## 11. The qualitative boundary, proved

A positioning finding carries no footings, an empty `dimension_resolution` and no conflict;
stays `SOURCED`, class 3, cited and traceable; may declare `period` and `geography`, which
`as_dict()` keeps while `dimensions` reads them unstated; returns `unknown` against a
quantitative figure and against every figure in the same run; and coexists with footed
statements in one strict, schema-valid set.

## 12. Files created

- `tests/unit/test_m10_2r12_competitor_analysis_footing.py` — 157 tests.
- `docs/development/2026-09-16-m10-2r12-competitor-analysis-footing.md` — this record.

## 13. Files modified

- `skills/biq-competitor-analysis/SKILL.md` — `close_retrieval_object` named in *Research
  flow*; one new section, *Footing a figure for comparison*. Nothing existing was removed or
  reworded, and the comparability test, the ten comparison dimensions, the market-share rule
  and *No rankings, no scores* are untouched.
- `commands/competitor-analysis.md` — `dimension footing` added to the skill's ownership list;
  one new step 4; the old step 4 renumbered 5.
- `tests/unit/test_m10_2r11_market_analysis_footing.py` — **one assertion narrowed on
  explicit user approval**; see §17.
- `architecture.md` — one new paragraph in the synthesis layer.
- `project_plan.md` — one new M10.2-R.12 section.

**No file under `lib/` was modified, created or deleted.** No ADR was created or edited.

## 14. Files deleted

None.

## 15. Tests performed

```
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_2r12_competitor_analysis_footing
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m9d3_competitor_analysis tests.unit.test_m9d3_competitor_analysis_command
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_2r6_dimension_provenance tests.unit.test_m10_2r8_source_context tests.unit.test_m10_2r9_company_analysis_footings tests.unit.test_m10_2r10_company_analysis_command_footing tests.unit.test_m10_2r11_market_analysis_footing tests.unit.test_m10_2r12_competitor_analysis_footing tests.unit.test_m10_2r_provenance_footing
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_1_synthesis tests.unit.test_m10_1_synthesis_security tests.unit.test_m10_1_synthesis_policy tests.unit.test_m10_2r_retrieval_seam tests.unit.test_m10_2r2_unit_semantics tests.unit.test_m10_2r3_allow_branch tests.unit.test_m10_2r_live_compatibility
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m9a_invariants tests.unit.test_m9a_research_core tests.unit.test_research_scout_boundary tests.unit.test_m9b_scout_contract tests.unit.test_m9c15_production_protocol tests.unit.test_m9_governance tests.unit.test_manifest
python tests/run_tests.py
claude plugin validate . --strict
md5sum lib/python/biq/synthesis/compatibility.py lib/python/biq/quantity.py lib/python/biq/research/scout.py
find lib -newermt "2026-09-16 10:00" -type f
```

## 16. Test results

Real output.

**The new module:** `Ran 157 tests in 0.064s` · `OK`

**Existing Competitor Analysis skill and command, unmodified:** `Ran 252 tests in 0.175s` ·
`OK`

**R.6 + R.8 + R.9 + R.10 + R.11 + R.12 provenance and footing:** `Ran 692 tests in 0.168s` ·
`OK`

**M10.1 synthesis, retrieval seam, unit semantics, allow branch:** `Ran 287 tests in 0.659s` ·
`OK`

**Retrieval integrity, scout boundary, protocol, governance, manifest:**
`Ran 328 tests in 0.110s` · `OK`

**Full regression, after all edits:**

```
Ran 3723 tests in 109.286s
OK (skipped=19)
ran 3723 | failures 0 | errors 0 | skipped 19
```

3,566 + 157 = 3,723.

**Strict validation:** `✔ Validation passed`

**Protected hashes, re-measured after all edits:**

```
35a89e32f6fad71bc7c21abe9dbe4915  lib/python/biq/synthesis/compatibility.py
a43581d8ff7a29b92f5d200fb03818e1  lib/python/biq/quantity.py
fe2c4fac1736abea4aaf3c997fdd2b6e  lib/python/biq/research/scout.py
```

All identical to the R.9, R.10 and R.11 baselines. `find lib -newermt` returned nothing.

## 17. Issues discovered

**An approved test contradicted the approved milestone, and the user decided.** R.11's
`test_competitor_and_industry_skills_are_untouched_by_this_milestone` asserted that *both*
`biq-competitor-analysis` and `biq-industry-research` name no footing symbols. It was correct
when written; R.12's own goal makes the competitor half of it false. Instruction 10 forbids
retargeting existing tests, so the conflict was **raised rather than resolved silently**, with
three options and a recommendation. The user chose to narrow the guard: the skill list is now
`("biq-industry-research",)`, the test is renamed `test_the_unmigrated_research_skill_is_
untouched`, and its docstring records what changed and why. The dropped property is
re-asserted more strongly in R.12's own `NoSecondMechanism`, which requires Competitor
Analysis to use the shared seam and requires the seam to contain no competitor-specific logic.
No other existing test was changed.

**Four of my own new tests were wrong on first run and were corrected, not the code.**
(a) A blanket ranking-token scan flagged `weakest`, which comes from the engine's own support
grading — *"the weakest of the internal and external assessments"* — and has been there since
M10.1; the scan now checks ranking-specific tokens and says why `weakest` is excluded.
(b) and (c) Two controls expected `excerpt_not_in_source` for a title quote and a
company-name quote; both quote text the source genuinely contains, so both are admitted. They
were rewritten as the honest containment-is-not-meaning controls described in §10.
(d) The cross-operation control silently passed evidence from the *same* registry entry,
because `evidence_id()` is content-addressed on (source, reference, retrieved_at) and the same
record in two retrievals mints one id — the collision recorded in the R.10 record §16. Varying
the source name makes the ids differ while keeping the reference identical, so the operation
check is the one that refuses.

**No defect was found** in the R.6, R.8, R.9, R.10 or R.11 implementation.

## 18. Decisions made

**None requiring an ADR.** ADR-0028 already names migrating the remaining research skills as
its follow-up, and this is that follow-up performed as written. No approved ADR was edited.

## 19. Documentation updates

- `architecture.md` — one new paragraph: the third domain, the absent entity dimension, the
  row-not-an-order boundary, `scope` as consolidated-versus-segment, and cross-document
  prohibition as the normal shape of competitor data.
- `project_plan.md` — one new `### M10.2-R.12 … COMPLETED` section before `### M10.3 onward`.
  M10.2-R stays `PARTIALLY VERIFIED`; no other status changed.
- `docs/development/2026-09-16-m10-2r12-competitor-analysis-footing.md` — this record.
- `docs/decisions/` — **not changed.** ADR-0026, ADR-0027 and ADR-0028 are untouched.
- `docs/README.md` — not changed; no new ADR to index. Its ADR list remains stale as flagged
  in the R.10 record.
- `docs/development/README.md` — **not changed.** Its index has been stale since M9-B.

## 20. Remaining limitations

1. **Containment is still not meaning**, and competitor analysis has two live versions of it
   (§10). Unchanged and unclosable by code.
2. **Supply still depends on guidance.** Whether the scout captures the definition, basis and
   scope sentences, and whether the skill quotes them faithfully, rests on two definitions
   rather than on a type.
3. **A source stating fewer than seven dimensions cannot reach `compatible`,** and rivals'
   filings state their consolidation basis and segment boundary less often than the fixture
   does. R.12 does not make a compatible verdict more frequent in practice.
4. **The entity is still not checked.** Two figures from two companies that genuinely share
   all seven dimensions are compatible, which is correct and is also the property most open to
   misreading. Nothing in code stops a reader concluding "larger, therefore leading"; what
   stops it is the guidance and the absence of any ranking machinery.
5. **A currency name still establishes nothing** (ADR-0027 §23, open by decision).
6. **Cross-document context stays prohibited**, which in this domain means a rival's figure
   and an analyst's definition of it can never be combined.
7. **Two records from one document cannot foot each other**, for the id-derivation reason in
   the R.10 record §16 — re-encountered here while writing the cross-operation control.
8. **The qualitative/quantitative split is guidance, not a type.** Nothing in code stops a
   skill routing a revenue figure through `sourced_statement()` unfooted; the strict set only
   guarantees that an unfooted dimension never reads as a match.
9. **One research skill remains unmigrated.** `biq-industry-research` is untouched.
10. **Nothing here is verified live.** Every fixture is synthetic and in-memory; R-12 produced
    no evidence in either direction.

## 21. R-12 status

**Open, untouched, and not progressed.** No scout was dispatched and no hand-back was parsed.
(The milestone label M10.2-R.12 and the open item R-12 are unrelated names that happen to
collide; this milestone produced no evidence about scout reliability.)

## 22. Live research

**None.** No `WebSearch`, no `WebFetch`, no scout dispatch, no network access of any kind.
Every source is an invented sentence on a reserved `.invalid` host.

## 23. Git commit reference

**N/A — no commit, no push.** HEAD is unchanged at
`62580f3f9368b5924360d19e0e62c977ee39136a`. The working tree carries the changes in §12–13
and nothing else.
