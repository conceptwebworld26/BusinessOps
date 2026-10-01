# 2026-09-15 — M10.2-R.8: source-context capture and currency-code admissibility

**Milestone:** M10.2-R.8 — Source-context capture and currency-code admissibility
**Status on completion:** COMPLETED
**Supersedes:** None

---

## 1. Prompt / task performed

Implement the approved M10.2-R.7 decision recorded in
`docs/decisions/ADR-0027-external-source-context-extraction.md`, in a fresh session, with a
hard boundary list: no commit, no push, no live research, no change to `compatibility.py`,
`quantity.py`, `research/scout.py`, `BIQ-REC/1`, `BIQ-END/1`, ADR-0025 or ADR-0026, no new
scout protocol, no new record field, no new record type, no attempt at R-12, and no
weakening, deletion or retargeting of an existing test.

Scope was four parts: scout `content` guidance; the ISO 4217 currency predicate; a focused
test module; documentation.

## 2. Objective

Make the evidence records that already exist capable of **carrying** the source context the
M10.2-R.6 `DimensionProvenance` mechanism needs, and close the currency gap M10.2-R.7
measured — without giving the scout or the model any new authority.

The division ADR-0027 fixed, and which this milestone implements unchanged:

| Stage | Who | What |
|---|---|---|
| Retrieval | scout | fetches the document; puts the figure **and its stated context** in `content` |
| Candidate extraction | the skill's model | quotes the passage that states a dimension into a footing |
| Admissibility | **Python** | evidence, operation, document, containment, applicability, dimension predicate, value agreement |

## 3. Baseline

Established before any edit, in this session:

| Fact | Value |
|---|---|
| HEAD | `8d52b0e24343f2e9b9f586207d2ea841dce61289` |
| Working tree | `.gitignore` modified; every other path untracked — unchanged from the stated baseline |
| Tests | `ran 3153 \| failures 0 \| errors 0 \| skipped 19` |
| `compatibility.py` md5 | `35a89e32f6fad71bc7c21abe9dbe4915` ✔ matches |
| `research/scout.py` md5 | `fe2c4fac1736abea4aaf3c997fdd2b6e` ✔ matches |
| `agents/biq-research-scout.md` md5 | `83c99362fb0e4f65be1af84731e5af74` ✔ matches |
| `quantity.py` md5 | `a43581d8ff7a29b92f5d200fb03818e1` (recorded here; no baseline value was given) |
| ADR-0025 / ADR-0026 | present, unmodified |
| ADR-0027 | present, decision-only |

The baseline matched in every checkable respect, so implementation proceeded.

**Fresh-session evidence.** The context window at task start held only the system prompt,
`CLAUDE.md` and this prompt — no prior conversation turns, no prior tool results, and no
carried-over findings from M10.2-R.7. Every fact in the Baseline table was re-derived here
by running `git rev-parse HEAD`, `git status --porcelain`, `md5sum` and
`python tests/run_tests.py`, not recalled. The git snapshot supplied to the session shows
one commit, `8d52b0e Initial BusinessIQ plugin setup`, which is the same HEAD the prompt
states.

## 4. Changes made

In the order they happened.

**1. Baseline verification.** HEAD, working tree, four md5s, and a full test run.

**2. Reading.** ADR-0027 in full; the relevant parts of ADR-0025 and ADR-0026 as ADR-0027
cites them; `synthesis/dimension_provenance.py`; `quantity.py`'s currency parsing;
`research/scout.py`'s `ACCEPTED_RECORD_FIELDS`, `MAX_CONTENT_CHARS` and protocol tokens;
`agents/biq-research-scout.md`; and `tests/unit/test_m10_2r6_dimension_provenance.py`.

A grep established that `DimensionProvenance` has exactly one test module and no callers in
`commands/` or `skills/`, so the blast radius of a narrowing predicate was one file.

**3. The currency predicate** in `lib/python/biq/synthesis/dimension_provenance.py`.

**4. The scout content guidance** in `agents/biq-research-scout.md`.

**5. The test module** `tests/unit/test_m10_2r8_source_context.py`.

**6. Documentation** — this record, plus the minimal `architecture.md` and
`project_plan.md` additions described in §12 and §13.

## 5. The currency gap discovered in M10.2-R.7

ADR-0027 §4 records it as a measured property, not a hypothesis, and §21.4 makes closing it
an acceptance criterion:

> A footing with `value="USD"`, `basis="context"` and `source_excerpt="$4.2 billion"`
> against content reading `"Revenue was $4.2 billion for FY2025."` resolves to
> `currency = USD`. Containment passes, every binding passes, and the value agrees with the
> statement.

The gap was one of **layering**, not of intent. ADR-0025 already said a bare `$` establishes
nothing, and `quantity.parse_source_unit` already held that line for *notation*. Nothing
held it for a footing, so the rule could be walked around by quoting the symbol instead of
parsing it. M10.2-R.6 closed the authority gap — a caller can no longer assert a dimension
— but a caller could still *quote* their way to one, because containment proves that text is
in the source, not that the text means the value.

## 6. The exact currency rule now implemented

> A `stated` or `context` footing for `currency` is admissible only where its
> `source_excerpt` prints **exactly one** ISO 4217-shaped code, and that code is the value
> the footing claims.

Three conditions, each fail-closed:

1. **A code is present.** Shape only: three uppercase ASCII letters, after stripping
   `.,;:!?()[]{}"'` from a whitespace-separated token's edges. This is the shape
   `quantity.parse_source_unit` already applies (ADR-0027 §11), extended with an ASCII
   restriction because every ISO 4217 code is ASCII and the restriction only narrows.
   `$`, `£`, `€`, `¥` and `US$` are not codes. Neither is `US1`, `U$D`, `USDD` or `US`.
2. **Exactly one distinct code.** An excerpt naming two currencies is ambiguous, and an
   ambiguous excerpt establishes **nothing** rather than the first, nearest or largest. The
   same code twice is corroboration, not conflict.
3. **The code is the claimed value.** Compared with `_fold`, this module's single
   normalisation, so a lowercase footing `value` still matches the uppercase code the source
   printed. Detection stays uppercase-strict: `usd` and `Usd` in an excerpt are prose, not a
   code, and establish nothing.

Refusal carries the new reason code `currency_code_not_in_excerpt`
(`dp.CURRENCY_CODE_ABSENT`), with an entry in `REASON_TEXT`.

**Ordering matters and is deliberate.** The predicate runs *after* containment, so an
excerpt the source never printed still reads `excerpt_not_in_source` — the more fundamental
failure — rather than the narrower currency reason. Every ADR-0026 binding (registry,
operation, citation, same-document, applicability) is checked before both.

**What was deliberately not built.** No currency-name table: "US dollars" and "British
pounds" establish nothing in v1, which is a real and accepted cost recorded as ADR-0027's
single open question (§23). No FX, no rate lookup, no symbol map, no inference from
domicile, domain, publisher, country, filing venue, exchange or source type.

**Why the third condition exists, given the ADR words the predicate as "contains an ISO 4217
three-letter code".** A pure shape test admits `CEO`, `CFO`, `EPS` and `USA` as codes, since
no table distinguishes them. Requiring the single found code to *be* the value the footing
claims is what keeps a three-letter English word from establishing `USD`, and it is strictly
narrowing — it can only turn an admitted footing into an unresolved one. Both properties are
pinned by test (`test_21`, `test_21b`, `test_22`).

## 7. The scout guidance change

One file, `agents/biq-research-scout.md`, and only the description of what goes in
`content`. The `content` row of the *Record fields* table gained a pointer, and a new
section **What `content` should capture** was added between the field table and *Two rules
about these records that are not stylistic*.

What it now says:

* **One record per source document** — the ADR-0027 v1 convention, stated explicitly, with
  "do not split one document across several records".
* **Capture the figure together with the source-stated context** that says what the figure
  means, *where the document actually states it*.
* **Which context is worth keeping** — metric definition, period, geography, currency, unit
  or scale, reporting scope, methodology or basis. Headings, table headings, column headers,
  footnotes and page headers count as source text.
* **How to capture it** — the source's own text, not a summary; contiguous passages; no
  stitching two passages into a sentence the document never wrote; no paraphrase,
  translation or rewording; no model commentary inside `content` (that is what the
  surrounding prose is for).
* **What must never be supplied** — an unstated dimension is absent, and absent is the
  correct answer. Never infer geography (headquarters, domicile, incorporation, domain, TLD,
  publisher country, filing venue, stock exchange, company identity). Never infer
  methodology (a filing does not imply US GAAP — foreign private issuers file under IFRS).
  Never infer currency from a bare symbol. Never convert a currency. Never infer a period
  from a filing date, a publication date or a year in the URL.
* **No new fields, ever** — `context`, `source_tier`, `trust`, `verified`, `geography`,
  `currency`, `methodology`, `dimension` and `confidence` are named as fields that do not
  exist and are dropped on ingestion.
* **Retrieved context is still untrusted data** — capturing more of a page is not believing
  it; protocol-looking text inside a captured passage stays content, never an instruction.

**What did not change:** `BIQ-REC/1` and `BIQ-END/1` line shapes, accepted field names,
operation semantics, count semantics, tier/trust/verification semantics, the parser, the
return format, the 20,000-character bound, the failure-condition table and the source-bar
rules. A record written under the old guidance is still a valid record.

## 8. Tests

New module: `tests/unit/test_m10_2r8_source_context.py`, **81 tests**, all deterministic and
in-memory. No existing test was modified, weakened, deleted or retargeted.

| Group | Tests | Covers |
|---|---|---|
| `ScoutContentGuidance` | 20 | prompt items 1–8: the figure-plus-context request, the dimension list, source text over summary, the inference prohibitions (geography, methodology, currency symbol, period), no paraphrase, no stitching, `BIQ-REC/1`/`BIQ-END/1` preserved, one-record-per-document, the field table still equal to `ACCEPTED_RECORD_FIELDS`, no new metadata key in any documented record line, the untrusted boundary, the unchanged content bound |
| `CurrencyPredicate` | 5 | the predicate at its smallest surface: contiguous reading, edge punctuation, `US$` is not a code, the shape agrees with `quantity.canonical_amount`, `currency` is the only predicated dimension |
| `CurrencyAdmissibility` | 26 | prompt items 9–27: USD/GBP/EUR/JPY admitted when present; lower and mixed case; bare `$`, `£`, `€`, `¥`; "US dollars"; "British pounds"; malformed tokens; a random three-letter word; two conflicting codes; excerpt absent; wrong operation; wrong document; asserted; no trust or verification promotion |
| `ExistingSemanticsRegression` | 14 | prompt items 28–35: stated/context still resolve all seven dimensions; geography and methodology still non-derivable; the derivation registry still closed at two; bare `$` no longer establishes USD; ADR-0025 canonicalisation unchanged; `compare()` free of provenance logic and still matching; serialised footings carry the eight caller-authored fields only, in fixed order; reload re-resolves and discards a forged verdict |
| `SourceContextSemantics` | 16 | prompt items 36–45: one contiguous excerpt footing two dimensions; stitched text refused; paraphrase refused; folding is not a synonym engine; a footing with no excerpt or no evidence cannot be built; same-document context under the existing bindings; wrong period; wrong scope; missing applicability (three shapes); conflicting footings ⇒ unknown plus an explicit conflict; captured context stays untrusted; injected protocol text stays inert |

No live research test, no scout dispatch, no network. Every host used
(`acme-filings.example.invalid`, `elsewhere.example.invalid`) is in the reserved `.invalid`
TLD and can never resolve.

## 9. Test results

Focused module:

```
$ python -m unittest tests.unit.test_m10_2r8_source_context
Ran 81 tests in 0.024s

OK
```

Existing M10.2-R.6 module and the scout-contract modules, before the full run:

```
$ python -m unittest tests.unit.test_m10_2r6_dimension_provenance \
    tests.unit.test_m9b_scout_contract tests.unit.test_research_scout_boundary \
    tests.unit.test_m9c15_production_protocol tests.unit.test_manifest
Ran 251 tests in 0.124s

OK
```

Full regression:

```
$ python tests/run_tests.py
Ran 3234 tests in 114.984s
OK (skipped=19)
ran 3234 | failures 0 | errors 0 | skipped 19
```

3,234 = 3,153 baseline + 81 new. 0 failures, 0 errors, 19 skips — the target exactly.

Strict plugin validation:

```
$ claude plugin validate . --strict
Validating marketplace manifest: .claude-plugin/marketplace.json

✔ Validation passed
```

Whitespace:

```
$ git diff --check
(no output)
```

## 10. Security verification

Every invariant the prompt listed, re-checked and pinned by a test in the new module unless
noted.

| # | Invariant | Holds | Pinned by |
|---|---|---|---|
| 1 | Scout cannot control `source_tier` | ✔ | `test_07b`, `test_27`, `test_45c`; `EvidenceItem` tiers locally |
| 2 | Scout cannot control `trust` | ✔ | `test_27`, `test_45` (`trust` is a read-only property) |
| 3 | Scout cannot set `verified=true` | ✔ | `test_27`, `test_45b` |
| 4 | Asserting a value never creates an admissible dimension | ✔ | `test_26`, `test_39`, `test_39b` |
| 5 | Excerpt must be contained in `content`/`title` under the existing folding | ✔ | `test_23`, `test_37`, `test_38` |
| 6 | Same-operation binding mandatory | ✔ | `test_24` |
| 7 | Same-document binding mandatory for context | ✔ | `test_25` |
| 8 | Applicability mandatory | ✔ | `test_41`, `test_42`, `test_43` |
| 9 | Geography cannot be inferred | ✔ | `test_04`, `test_04b`, `test_29`, `test_38b` |
| 10 | Methodology cannot be inferred | ✔ | `test_05`, `test_30` |
| 11 | Currency cannot be inferred from symbols | ✔ | `test_14`–`test_17`, `test_31` |
| 12 | Currency cannot be inferred from company/domain/source identity | ✔ | `test_03`, `test_05`; no such path exists in code |
| 13 | No FX conversion | ✔ | `quantity.py` unchanged; `test_32`; guidance forbids it |
| 14 | No synonym normalisation | ✔ | `test_38b`; `_fold` unchanged |
| 15 | No cross-document context composition | ✔ | `test_25` |
| 16 | No cross-operation context composition | ✔ | `test_24` |
| 17 | External evidence remains untrusted | ✔ | `test_27`, `test_45` |
| 18 | Asserted basis remains inadmissible | ✔ | `test_26` |
| 19 | Unknown remains unknown | ✔ | `test_33c` |
| 20 | Conflicts remain explicit and fail closed | ✔ | `test_22`, `test_44`, `test_44b` |
| 21 | No model summary becomes source truth | ✔ | `test_38`; guidance §*How to capture it* |
| 22 | Prompt injection in source content stays inert | ✔ | `test_45b`, `test_45c` |

Two of these deserve a note rather than a tick alone.

**Invariant 22 is about authority, not about text.** `test_45c` deliberately quotes injected
text that *is* genuinely in the retrieved content, and shows the honest outcome: containment
passes, because injected text is still text. What the injection cannot do is carry a tier, a
trust level or a verification, and the value it appears to state is only ever as good as the
untrusted document it was found in. That is the same boundary ADR-0026 drew — containment is
proved, meaning is not — and pretending otherwise would be worse than stating it.

**Invariant 5's folding strength is unchanged.** The predicate reads the raw excerpt, not the
folded one, and adds no normalisation to the containment check.

## 11. Files changed

**Created**

- `tests/unit/test_m10_2r8_source_context.py` — 81 tests
- `docs/development/2026-09-15-m10-2r8-source-context-capture.md` — this record

**Modified**

- `lib/python/biq/synthesis/dimension_provenance.py` — `CURRENCY_CODE_LENGTH`,
  `_CODE_EDGE_PUNCTUATION`, `PREDICATED_DIMENSIONS`, `iso_currency_codes()`,
  `currency_excerpt_carries_code()`, the `CURRENCY_CODE_ABSENT` reason code and its
  `REASON_TEXT` entry, the predicate call in `_assess()`, and one module-docstring paragraph
- `agents/biq-research-scout.md` — the `content` row of *Record fields*, plus the new
  *What `content` should capture* section
- `architecture.md` — see §12
- `project_plan.md` — see §13

**Deleted:** none.

## 12. Architecture changes

Three minimal additions to `architecture.md`, all inside sections that already describe this
mechanism:

1. *Containment is proved; meaning is not* gained one sentence recording the ISO-code rule
   for `currency` footings, naming ADR-0027 and the symbols and names that establish nothing.
2. The dimension-admissibility discussion gained a short paragraph, *Source context travels
   in the evidence record that already exists (ADR-0027)*, stating that context rides in the
   existing `BIQ-REC/1` `content` field with no new field, record type, protocol or
   scout-supplied metadata, and that Python remains the authority.
3. The ADR index gained the ADR-0027 row, which had been missing.

No section was rewritten, no decision reopened, and nothing unrelated was touched.

## 13. Project-plan updates

One new section, `### M10.2-R.8 — Source-context capture and currency-code admissibility ·
COMPLETED`, placed before `### M10.3 onward`, in the same table format the M10.2-R.6 section
uses. It records the guidance change, the protocol's untouched state with the scout md5, the
predicate, the closed R.7 gap, the deliberate absence of a currency table, the test count,
the regression numbers, strict validation, the guidance-dependence cost, and that M10.2-R
stays `PARTIALLY VERIFIED` with R-12 open.

No other status was changed.

## 14. Documentation updates

- `architecture.md` — §12 above.
- `project_plan.md` — §13 above.
- `docs/decisions/README.md` — **not changed**; its index already carries the ADR-0027 row.
- ADR-0025, ADR-0026 and ADR-0027's decision — **not changed**, as required.
- No unrelated documentation cleanup was performed.

## 15. Issues discovered

**A recording gap from M10.2-R.7.** That milestone produced ADR-0027 but left no section in
`project_plan.md`, no record in `docs/development/`, and no ADR-0027 row in
`architecture.md`'s ADR index. The index row was added here because ADR-0027 is this
milestone's governing decision and its absence from the index was an inconsistency this work
touches directly. The missing plan section and dev record for R.7 were **not** written: they
are that milestone's history, not this one's, and inventing them here would be fabricating a
record. The gap is flagged in the new plan section so it is not lost.

**No new defect was found in the R.6 implementation** beyond the currency gap ADR-0027
already documented.

## 16. Remaining limitations

1. **Half the mechanism is guidance.** What the scout captures rests on the agent
   definition, not on a type. A scout that ignores it yields records with no context and
   dimensions that stay unknown. That is the safe failure, and the architecture cannot
   detect it. ADR-0027 §22 accepted this; the tests pin the guidance's substance and nothing
   can pin the model's compliance.
2. **A currency name establishes nothing in v1.** A document saying only "amounts are stated
   in US dollars" leaves currency unknown. ADR-0027 §23 holds this open deliberately.
3. **Containment is still not meaning.** The excerpt proves the text is in the source, not
   that it means the value.
4. **The 20,000-character bound must now hold the figure and its context.** A long filing
   may truncate away the passage a footing needs; truncation is recorded and the footing
   then fails closed, but the evidence is silently poorer.
5. **Cross-document context stays prohibited.** A figure in one document and its currency
   declaration in another remain uncombinable.
6. **The shape test cannot tell `XQZ` from `USD`.** Both are ISO-shaped; no table
   distinguishes them, by decision. What a bogus code cannot do is disagree with the
   statement's own canonicalised currency and still be admitted.
7. **No research skill emits footings yet.** Migration of `biq-company-analysis`,
   `biq-market-analysis`, `biq-competitor-analysis` and `biq-industry-research` is follow-up
   work and was not done here.

## 17. R-12 status

**Open, untouched, and not progressed by this milestone.** ADR-0027 §18 is explicit that a
richer `content` field does not make a hand-back more likely to arrive. Nothing here changed
the parser, the return contract, the dispatch rule or the recovery position, and no scout was
dispatched.

## 18. Live research

**None.** No `WebSearch`, no `WebFetch`, no scout dispatch, no network access of any kind.
Every fixture is synthetic and in-memory, on reserved `.invalid` hosts.

## 19. Git commit reference

**N/A — no commit, no push.** HEAD is unchanged at
`8d52b0e24343f2e9b9f586207d2ea841dce61289`. The working tree carries the changes described
in §11 and nothing else.
