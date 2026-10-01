# 2026-09-16 — M10.2-R.13: Industry Research reaches the strict footing path

**Milestone:** M10.2-R.13 — migrate `/industry-research` to the R.10/R.11/R.12 footing seam
**Status on completion:** COMPLETED
**Supersedes:** None

---

## 1. Prompt / task performed

Migrate the Industry Research skill and `/industry-research` command path to the same strict
dimension-footing production path used by Company Analysis, Market Analysis and Competitor
Analysis, so that dimension-sensitive quantitative industry claims become safely comparable
while qualitative research, source provenance, trust boundaries and fail-closed compatibility
semantics are preserved.

Thirteen parts: inspect without assuming the other three flows apply; preserve the existing
intents and sections; establish the qualitative/quantitative boundary; wire the production
path; reuse the seam with no domain-specific provenance code; handle industry-size
comparisons including current-against-prior; add focused deterministic tests; add real
command-level integration tests; preserve neutrality; run the regression suites; handle the
expected evolution of the older protection test explicitly; update documentation minimally;
leave protected components alone.

## 2. Objective

R.12 left one research skill unmigrated. R.13 closes ADR-0028's stated follow-up and, with
it, the question of whether `footed_statement()` is a seam or three special cases.

## 3. Baseline

| Fact | Value |
|---|---|
| HEAD | `e41e97a800d22f51fd37fe20a7fa865b8f607a77` — *M10.2: checkpoint through R.12* |
| Branch | `main`, in sync with `origin/main`, clean tree |
| Tests before any edit | 3,723 |
| `compatibility.py` md5 | `35a89e32f6fad71bc7c21abe9dbe4915` |
| `quantity.py` md5 | `a43581d8ff7a29b92f5d200fb03818e1` |
| `research/scout.py` md5 | `fe2c4fac1736abea4aaf3c997fdd2b6e` |
| Industry Research tests | 182, across `test_m9d5_industry_research.py` and `test_m9d5_industry_research_command.py` |
| ADRs | 0001–0016, 0019–0028; none allocated by this milestone |

## 4. What the inspection found

**The familiar defect.** The skill's *Research flow* told its model to close a retrieval with
`R.close_retrieval(...)`, which serialises the evidence set — the one shape
`register_external()` refuses.

**A six-row compatibility test, and the closest prose-to-engine fit of the four.** Industry
Research is the only migrated skill whose table has six rows rather than five, and they map
onto the engine's seven with a single split:

| Skill's row | Engine dimension(s) |
|---|---|
| industry definition | `metric_definition` |
| geography | `geography` |
| period | `period` |
| currency and unit | `currency` **and** `unit` — the only row that splits |
| **measurement basis** | **`scope`** |
| methodology | `methodology` |

Row 5 is the finding. Company Analysis folds `scope` into "geography or segment scope";
Market Analysis leaves it implicit inside "definition"; Competitor Analysis folds it into the
geography row. Industry Research had already written it down as its own check —
*"revenue, gross output, value added; reported or adjusted"* — because industry sizing is
where it does the most work. Two honest releases can size one industry in one year and differ
by a factor of two purely because one measured gross output and the other value added, with
geography, period and methodology all matching. The engine returns `incompatible` on `scope`,
which is exactly what row 5 always meant.

**One comparison the other three rarely make: current against prior.** The engine's answer is
exact and needed writing down, because it is counter-intuitive. Two figures for two periods
are `incompatible` — they do not measure the same quantity, which is what "different period"
means. What makes a change-over-time reading defensible is therefore **not** a compatible
verdict; it is `incompatible` with `period` as the *only* mismatched dimension, six matched
and none unknown. That precondition is visible in the result and is the thing to report. And
a publication date establishes nothing in either direction — two releases a year apart that
state the same period are comparable; two published on one day that state different periods
are not.

**The decisive finding: no production code was needed.** `ORIGIN_INDUSTRY` is already in
`EXTERNAL_ORIGINS` and `footed_statement()` names no domain. **No file under `lib/` was
modified, created or deleted.**

## 5. Changes made, in order

1. Verified HEAD, the clean tree, the three protected hashes and the 182 existing tests.
2. Read the skill, the command, both existing test modules, the R.10/R.11/R.12
   implementations, `research_footing.py` and the retrieval contracts.
3. Proved the path on a scratch script first: a `BIQ-REC/1` sizing reply →
   `close_retrieval_object` → `footed_statement(ORIGIN_INDUSTRY)` → seven dimensions; gross
   output vs value added → `incompatible` on `scope`; current vs prior → `incompatible` on
   `period` only with six matched; different publication dates, same stated period →
   compatible; internal model → compatible; qualitative → `unknown`.
4. Updated the skill: `close_retrieval_object` named in *Research flow*, and a new
   `### Footing a figure for comparison` section placed inside *Industry size and growth*,
   immediately after the six-check test it operationalises.
5. Updated the command: `dimension footing` added to the skill's ownership list, and one new
   **step 5**. Step 4 was deliberately **not** renumbered — an existing M9-D.5 test pins the
   literal string *"**4. Present the skill's result.** Its ten sections, in its order,
   unchanged"*, and the new material belongs after presentation anyway.
6. Wrote `tests/unit/test_m10_2r13_industry_research_footing.py` — 162 tests.
7. Evolved the two older protection assertions (§7) and re-ran their modules.
8. Ran the focused module, the Industry Research modules, the R.6–R.13 provenance modules,
   the synthesis modules, the retrieval integrity modules, the other three research skills'
   modules, the full regression and strict validation.
9. Wrote the architecture paragraphs, the project-plan section and this record.

## 6. The integration path

```
scout reply text (BIQ-REC/1), claim_kind market_sizing
 → research.close_retrieval_object(...)["evidence_set"]      genuine EvidenceSet (ADR-0024)
 → synthesis.footed_statement(retrieval, ORIGIN_INDUSTRY, text, item_id, stated={...})
      register_external → source_footings(STATED) → one DERIVED unit footing
      → sourced_statement(dimension_provenance=…) on SynthesisSet(strict) → resolve()
   … the same call again for a second release, passing synthesis= the same set
 → synthesis.compare_values(...) → compatibility.compare()
        external ↔ external   two releases, or one release against a prior period
        external ↔ internal   a published figure and the user's own industry model
```

Qualitative findings from the `overview`, `trends`, `drivers-risks` and `structure`
retrievals take the untouched `sourced_statement(...)` path into the **same** strict set.

## 7. The older protection test, evolved on instruction

The milestone brief anticipated this and set the procedure; it was followed literally.

**The assertion.** R.11 added
`test_competitor_and_industry_skills_are_untouched_by_this_milestone`, asserting that
`biq-competitor-analysis` and `biq-industry-research` named none of `footed_statement`,
`source_footings`, `close_retrieval_object` or `DimensionProvenance`. R.12 narrowed it to
industry research alone (on explicit user approval) and renamed it
`test_the_unmigrated_research_skill_is_untouched`. R.12 also added its own
`test_industry_research_is_untouched_by_this_milestone`, asserting the same thing.

**Why it is now invalid.** R.13's approved goal is to migrate Industry Research. Both
assertions therefore assert something the approved architecture has deliberately changed.

**Whether a narrower boundary remains.** No. Four research skills exist —
`biq-company-analysis`, `biq-market-analysis`, `biq-competitor-analysis`,
`biq-industry-research` — and after R.13 all four are migrated. There is no unmigrated
research skill left to point the guard at.

**What replaced it.** Per the brief, a meaningful non-regression property about the shared
footing architecture, not a trivial always-pass. An absence was only ever a proxy for the
real invariant — **one mechanism, however many callers** — so that is now asserted directly,
in three complementary, non-duplicating places:

- **R.11's module** — `test_no_research_skill_declares_a_footing_helper_of_its_own`: no skill
  anywhere under `skills/` contains `company_footings`, `market_footings`,
  `competitor_footings`, `industry_footings`, `def source_footings` or
  `class DimensionProvenance`, and `source_footings` has exactly one definition in
  `dimension_provenance.py`.
- **R.12's module** — `test_the_one_seam_serves_every_external_origin_and_privileges_none`:
  `EXTERNAL_ORIGINS` has four members, the seam's source names none of them, and each one
  drives the seam to seven resolved dimensions with trust unchanged.
- **R.13's module** — `OneMechanismAcrossFourSkills`: all four skills exist, each names
  `footed_statement`, `source_footings` and `close_retrieval_object`, each requires
  `require_dimension_provenance=True`, the package exports each seam symbol exactly once, and
  a walk of the whole engine finds exactly one `def footed_statement` and one
  `def source_footings`.

Each is strictly stronger than the absence check it replaces: an absence check could never
have caught a skill growing a footing helper of its own, and these do. **Nothing unrelated in
either older module was touched** — both edits are confined to the single obsolete method.

## 8. Fixture

One invented statistical release and one invented sector review, on reserved hosts.

- `statistics-bureau.example.invalid` — *"The industrial refrigeration equipment industry,
  defined as manufacturers of compressors, condensers and controls sold for industrial cold
  storage, generated gross output of USD 46.8 billion in calendar year 2025. The estimate
  covers worldwide production measured as gross output at producer prices and was compiled on
  a bottom-up basis from establishment-level returns."*
- `sector-review.example.invalid` — the same shape at 49.1, plus variants on value added, a
  prior year, a wider boundary, a European scope, a top-down methodology and a later
  publication date.
- `trade-council.example.invalid` — a value-chain and barriers sentence, `claim_kind:
  industry_structure`, for the qualitative path.

Tiers are not chosen by the fixture: `classify_tier` returns `C`, inferred, for a reserved
host. Figures are canonicalised from `USD billion` notation by ADR-0025. The internal
counterpart is the user's own bottom-up industry model on the same definition, geography,
period, basis and methodology, built through `AnalysisSet` → `from_analysis_set` on a
registered dataset.

## 9. Positive results

All seven dimensions resolve — six `stated` plus one `derived` `unit` — with `scope`
resolving to *gross output at producer prices*, distinct from `geography` (*worldwide*) and
`methodology`. The statement stays `SOURCED`, external, class 3, `untrusted`, unverified, with
`support` and `confidence` identical to an unfooted twin; the set validates against the
schema; `recommendations` is empty; no `verified` key appears.

```
two releases, one basis              compatible   · 7 matched · 0 mismatched · 0 unknown
                                                  · may_combine True · converted False
gross output vs value added          incompatible · mismatched: scope
wider industry boundary              incompatible · mismatched: metric_definition
European vs worldwide                incompatible · mismatched: geography
top-down vs bottom-up                incompatible · mismatched: methodology
current vs prior period              incompatible · mismatched: period only · 6 matched
published 2026 vs 2027, same period  compatible   · 7 matched · may_combine True
published same day, periods differ   not combinable
release vs our own industry model    compatible   · 7 matched · may_combine True
internal model on another basis      incompatible · mismatched: scope
```

Nothing was averaged, converted, reconciled or combined in any of them; both values stayed
apart; neither side of any pair changed kind, trust, domain or value; `calculations` stayed
empty and no CAGR or growth rate appeared anywhere in the serialised set.

## 10. Fail-closed controls

All run through the production path. Seven missing-dimension controls, each resolving to
`no_dimension_provenance` and stopping at `unknown` naming that dimension, against both
another release and an internal model; six-of-seven never compatible on either path;
nothing-stated; bare `$`, "US dollars" and a `CEO`-shaped token →
`currency_code_not_in_excerpt`; `XQZ` refused at construction; conflicting currencies,
**measurement bases**, methodologies **and geographies** → `conflicting_admissible_values`; a
separately published methodology note footing the release → `document_mismatch`;
`operation_mismatch`; `applicability_mismatch` for wrong period, wrong basis and undeclared
applicability; unnamed context item and unregistered evidence refused; paraphrase, translation
and stitching → `excerpt_not_in_source`; URL, bare domain, source name, publication date,
source type and local tier → `excerpt_not_in_source`; serialised `close_retrieval` result
refused by name; dict/list/string/`None`/serialised set/`EvidenceSet` **subclass** refused;
`blocked`, `insufficient_evidence`, `not_authorised` and a real zero-record retrieval refused;
non-strict set, non-set and internal origins refused; declared-but-unfooted reads unstated;
footed-and-declared refused; `evidence_ids`, `dimension_provenance` and `unit` refused as
caller fields; `unit` as a quotation refused; `asserted` unreachable by any route; mistyped
dimension and excerpt-less value refused; `source_tier`/`trust`/`verified`/`freshness`/`source`
have no parameter; and a `SYSTEM:` instruction telling the page to mark itself verified tier A,
rank the industry first and recommend investment leaves tier `C`, trust `untrusted`, no
`verified` key and no recommendation.

**One control asserts a limitation rather than a refusal** (`ContainmentIsNotMeaning`). A
footing quoting the release's *title* to claim a measurement basis is **admitted** — the text
really is in the source, and on this path the statement declares whatever the footing claims.
The guidance prohibits it ("never from the word *size*"), no code can catch it, and the test
asserts what remains true: the reading is recorded against the text it rests on, and set beside
a release that stated its basis it comes out `incompatible` on `scope`.

## 11. Files created

- `tests/unit/test_m10_2r13_industry_research_footing.py` — 162 tests.
- `docs/development/2026-09-16-m10-2r13-industry-research-footing.md` — this record.

## 12. Files modified

- `skills/biq-industry-research/SKILL.md` — `close_retrieval_object` named in *Research
  flow*; one new `### Footing a figure for comparison` section. Nothing existing was removed
  or reworded; the six-check test, the forecast rules, *Industry structure*, *Concentration*
  and *No rankings, no scores* are untouched.
- `commands/industry-research.md` — `dimension footing` added to the skill's ownership list;
  one new step 5. **Step 4 was not renumbered**, deliberately (§5.5).
- `tests/unit/test_m10_2r11_market_analysis_footing.py` — the one obsolete assertion replaced
  (§7).
- `tests/unit/test_m10_2r12_competitor_analysis_footing.py` — the one obsolete assertion
  replaced (§7).
- `architecture.md` — two new paragraphs in the synthesis layer.
- `project_plan.md` — one new M10.2-R.13 section.

**No file under `lib/` was modified, created or deleted.** No ADR was created or edited.

## 13. Files deleted

None.

## 14. Tests performed

```
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_2r13_industry_research_footing
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m9d5_industry_research tests.unit.test_m9d5_industry_research_command
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_2r6_dimension_provenance tests.unit.test_m10_2r8_source_context tests.unit.test_m10_2r9_company_analysis_footings tests.unit.test_m10_2r10_company_analysis_command_footing tests.unit.test_m10_2r11_market_analysis_footing tests.unit.test_m10_2r12_competitor_analysis_footing tests.unit.test_m10_2r13_industry_research_footing tests.unit.test_m10_2r_provenance_footing
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m10_1_synthesis tests.unit.test_m10_1_synthesis_security tests.unit.test_m10_1_synthesis_policy tests.unit.test_m10_2r_retrieval_seam tests.unit.test_m10_2r2_unit_semantics tests.unit.test_m10_2r3_allow_branch tests.unit.test_m10_2r_live_compatibility
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m9a_invariants tests.unit.test_m9a_research_core tests.unit.test_research_scout_boundary tests.unit.test_m9b_scout_contract tests.unit.test_m9c15_production_protocol tests.unit.test_m9_governance tests.unit.test_manifest
PYTHONPATH="lib/python;tests" python -m unittest tests.unit.test_m9c3_company_analysis tests.unit.test_m9d1_company_analysis_command tests.unit.test_m9d2_market_analysis tests.unit.test_m9d2_market_analysis_command tests.unit.test_m9d3_competitor_analysis tests.unit.test_m9d3_competitor_analysis_command
python tests/run_tests.py
claude plugin validate . --strict
md5sum lib/python/biq/synthesis/compatibility.py lib/python/biq/quantity.py lib/python/biq/research/scout.py
find lib -newermt "2026-09-16 12:00" -type f
```

## 15. Test results

Real output.

**The new module:** `Ran 162 tests in 0.077s` · `OK`

**Existing Industry Research skill and command, unmodified:** `Ran 182 tests in 0.052s` · `OK`

**R.6 + R.8 + R.9 + R.10 + R.11 + R.12 + R.13 provenance and footing:**
`Ran 854 tests in 0.249s` · `OK`

**M10.1 synthesis, retrieval seam, unit semantics, allow branch:** `Ran 287 tests in 0.698s` ·
`OK`

**Retrieval integrity, scout boundary, protocol, governance, manifest:**
`Ran 328 tests in 0.114s` · `OK`

**The other three research skills and their commands, unmodified:**
`Ran 552 tests in 0.250s` · `OK`

**Full regression, after all edits:**

```
Ran 3885 tests in 232.231s
OK (skipped=19)
ran 3885 | failures 0 | errors 0 | skipped 19
```

3,723 + 162 = 3,885.

**Strict validation:** `✔ Validation passed`

**Protected hashes, re-measured after all edits:**

```
35a89e32f6fad71bc7c21abe9dbe4915  lib/python/biq/synthesis/compatibility.py
a43581d8ff7a29b92f5d200fb03818e1  lib/python/biq/quantity.py
fe2c4fac1736abea4aaf3c997fdd2b6e  lib/python/biq/research/scout.py
```

All identical to the R.9–R.12 baselines. `find lib -newermt` returned nothing.

## 16. Issues discovered

**Two of my own new tests were wrong on first run and were corrected, not the code.**
(a) A scan asserting `compatibility.py` says nothing about industries flagged the word
`industry` — which appears in that module's docstring, citing
`skills/biq-industry-research/SKILL.md` as the prose precedent for its own rule, and has done
since M10.1. The same class of mistake was made with `market` at R.11 and with `weakest` at
R.12; the assertion now checks the tokens that would mean the engine had learned about
provenance, evidence or a domain, and its docstring says why `industry` is excluded.
(b) A control expected `excerpt_not_in_source` for a title quote; `_excerpt_present` searches
`title`, so the quote is genuinely in the source and is admitted. It was rewritten as the
honest containment-is-not-meaning control in §10.

**One real constraint was found and respected rather than worked around.** The existing
M9-D.5 command test pins the literal string *"**4. Present the skill's result.** Its ten
sections, in its order, unchanged"*. Renumbering that step to 5 — as R.10, R.11 and R.12 all
did in their commands — would have broken it. The new step is therefore **step 5**, placed
after presentation, which also reads better: the comparison is an optional extra, not a
precondition of the report.

**No defect was found** in the R.6, R.8, R.9, R.10, R.11 or R.12 implementation.

## 17. Decisions made

**None requiring an ADR.** ADR-0028 named migrating the remaining research skills as its
follow-up; R.13 completes it. No approved ADR was edited, including to mark that follow-up
closed — that status lives in `project_plan.md`.

## 18. Documentation updates

- `architecture.md` — two new paragraphs: the fourth domain completing the set with `scope`
  as the measurement basis, and the current-against-prior semantics.
- `project_plan.md` — one new `### M10.2-R.13 … COMPLETED` section before `### M10.3 onward`,
  including the test-evolution record. M10.2-R stays `PARTIALLY VERIFIED`.
- `docs/development/2026-09-16-m10-2r13-industry-research-footing.md` — this record.
- `docs/decisions/` — **not changed.** ADR-0026, ADR-0027 and ADR-0028 are untouched.
- `docs/README.md` — not changed; no new ADR to index. Its ADR list remains stale as flagged
  in the R.10 record.
- `docs/development/README.md` — **not changed.** Its index has been stale since M9-B.

## 19. Remaining limitations

1. **Containment is still not meaning** (§10). Unchanged and unclosable by code.
2. **Supply still depends on guidance.** Whether the scout captures the definition,
   measurement basis and methodology sentences, and whether the skill quotes them faithfully,
   rests on two definitions rather than on a type.
3. **A source stating fewer than seven dimensions cannot reach `compatible`,** and statistical
   releases state their measurement basis more often than commercial reports do. R.13 does not
   make a compatible verdict more frequent in general.
4. **Current-against-prior remains `incompatible` by design.** The six-matched, period-only
   result is the precondition for a change-over-time reading, not the reading itself; producing
   the growth rate is a separate deliberate `[CALCULATION]` this path does not perform and
   nothing yet automates.
5. **A currency name still establishes nothing** (ADR-0027 §23, open by decision).
6. **Cross-document context stays prohibited**, which in this domain means a statistical
   release and its separately published methodology note can never be combined — a real and
   common pattern.
7. **Two records from one document cannot foot each other**, for the id-derivation reason in
   the R.10 record §16.
8. **The qualitative/quantitative split is guidance, not a type.** Nothing in code stops a
   skill routing an industry size through `sourced_statement()` unfooted; the strict set only
   guarantees that an unfooted dimension never reads as a match.
9. **All four research skills are migrated, so the absence-based guards are gone.** They are
   replaced by stronger positive invariants (§7), but a fifth research domain added later
   would need its own coverage rather than inheriting a guard.
10. **Nothing here is verified live.** Every fixture is synthetic and in-memory; R-12 produced
    no evidence in either direction.

## 20. R-12 status

**Open, untouched, and not progressed.** No scout was dispatched and no hand-back was parsed.
(The open item R-12 and the milestone label M10.2-R.12 are unrelated names that collide.)

## 21. Live research

**None.** No `WebSearch`, no `WebFetch`, no scout dispatch, no network access of any kind.
Every source is an invented sentence on a reserved `.invalid` host.

## 22. Git commit reference

**N/A — no commit, no push.** HEAD is unchanged at
`e41e97a800d22f51fd37fe20a7fa865b8f607a77`. The working tree carries the changes in §11–12
and nothing else.
