# ADR-0027 — Source context travels inside the evidence record; the protocol does not change

**Date:** 2026-09-15
**Status:** Accepted
**Deciders:** Owner, via the M10.2-R.7 scoped decision milestone

## 1. Status

Accepted. Decision-only: no production code, test, schema, scout definition or protocol was
changed by this ADR. It specifies the contract M10.2-R.8 implements.

## 2. Context

M10.2-R.6 shipped `DimensionProvenance` and source-context admissibility (ADR-0026): a
dimension reaches `compatibility.compare()` only when a footing names the evidence it rests
on, quotes text genuinely present in that evidence, is bound to the same retrieval operation
and the same source document, and declares applicability to the statement's period and scope.

That milestone closed the *authority* gap — a caller can no longer establish a dimension by
asserting a value. It left the *supply* gap open, and named it:

> "Live source-context extraction is not implemented. The scout brief does not ask for
> dimension-bearing text, and changing it touches the agent contract, which needs its own
> decision."

M10.2-R.4 is the concrete case. A live retrieval returned two compliant records for
Microsoft FY2025 revenue. A token audit over the entire scout reply found no occurrence of
`usd`, `dollar`, `worldwide`, `global`, `geograph`, `gaap`, `asc 606`, `accrual` or
`methodolog`. Three dimensions were unresolvable not because the architecture refused them
but because the retrieved text did not contain them.

## 3. Problem statement

How should BusinessIQ retrieve and represent external source context so that
`metric_definition`, `period`, `geography`, `currency`, `unit`, `scope` and `methodology`
can be **proven from the source**, without the scout or the model becoming the semantic
authority?

## 4. Existing architecture

Established by inspection, not assumption:

* **`ACCEPTED_RECORD_FIELDS`** (`research/scout.py`) is a closed set of ten:
  `source`, `reference`, `url`, `title`, `publication_date`, `retrieved_at`, `source_type`,
  `content`, `snippet`, `claim_kind`. Any other key is dropped and the drop is noted.
* **`content` is already a free-text field bounded at `MAX_CONTENT_CHARS = 20000`**, and
  `snippet` is an accepted alias for it. Longer content is truncated and the truncation is
  recorded in the item's notes.
* **`EvidenceItem`** carries `id`, `source`, `reference`, `title`, `publication_date`,
  `retrieved_at`, `source_tier`, `source_type`, `content`, `claim_kind`, `freshness`,
  `operation`, `notes`, `excluded_reason`. `trust` is a read-only property fixed at
  `untrusted`.
* **`evidence_id()` is content-addressed over `(source, reference, retrieved_at)`**, so two
  records from one URL in one retrieval collide on id and the registry retains the last.
* **`dimension_provenance._excerpt_present()` searches `content` and `title`**, after
  whitespace collapse and case folding — the same folding strength `compatibility._normalise`
  uses, and deliberately no stronger.
* **`DimensionProvenance`** holds `dimension`, `value`, `basis`, `evidence_id`,
  `source_excerpt`, `source_locator`, `applicability`, `derivation`. Source identity, tier,
  freshness and retrieval date are refused as constructor input and resolved from the cited
  item.
* **`DERIVATION_RULES`** is a two-entry `frozenset`, both ADR-0025 canonicalisation rules;
  `DERIVABLE_DIMENSIONS` is `("unit", "currency")`.

**The decisive observation: the field needed already exists.** Dimension-bearing text can
travel in `content` today. What is missing is that nothing *asks* the scout to capture it,
and nothing constrains how a footing may read it.

### Two properties measured during this milestone

**A bare currency symbol currently establishes a currency code.** A footing with
`value="USD"`, `basis="context"` and `source_excerpt="$4.2 billion"` against content reading
`"Revenue was $4.2 billion for FY2025."` resolves to `currency = USD`. Containment passes,
every binding passes, and the value agrees with the statement. This directly contradicts
ADR-0025's own position that `$` "establishes nothing (it is used by at least four
currencies)". **This is a real gap in the R.6 implementation, found by inspection here, and
closing it is a v1 requirement of this ADR.**

**The id collision fails closed.** Where two records share `(source, reference,
retrieved_at)`, the registry keeps the last and a footing quoting text that lived only in the
dropped record returns `excerpt_not_in_source`. Verified empirically. The collision is lossy,
never permissive.

## 5. Security requirements

Any design must preserve, unchanged:

1. `BIQ-REC/1` and `BIQ-END/1` line shapes, exact operation binding, count semantics and
   fail-closed parsing.
2. No scout-controlled `source_tier`, `trust` or `verified` state.
3. No arbitrary provenance metadata reachable from external content.
4. `compatibility.compare()` byte-identical and free of provenance, evidence, tier and
   registry logic.
5. ADR-0025: `unit` is a quantity type, currency is separate, magnitude normalisation is
   deterministic, no FX, no magnitude-qualified unit tokens.
6. ADR-0026: `asserted` never admissible; no geography or methodology derivation; source type
   never establishes methodology; company identity never establishes geography; external
   evidence stays `SOURCED` and untrusted.

## 6. Considered alternatives

**A — Existing record fields only, richer `content`.** The scout captures the passages that
state the dimensions alongside the passage that states the figure, all in `content`.
*Pros:* zero protocol change, zero parser change, zero change to `ACCEPTED_RECORD_FIELDS`;
`_excerpt_present` already searches the right surface; every existing record stays valid.
*Cons:* relies on the agent's content guidance rather than on a typed field; a 20,000-char
bound must now hold the figure *and* its context.

**B — Add a bounded `context` field to `BIQ-REC/1`.** *Cons:* widens
`ACCEPTED_RECORD_FIELDS`, which is a security surface; creates a second place text can live,
so a footing could quote `context` text that `content` contradicts; the parser and the agent
contract both change. Buys nothing `content` does not already provide.

**C — Dimension-specific fields on `BIQ-REC/1`** (`record.currency`, `record.geography`, …).
*Cons:* **fatal.** It makes the scout the semantic authority — exactly what ADR-0026 exists
to prevent. A model-supplied `geography` field is an assertion with a schema, and it would
arrive looking like evidence.

**D — A separate context record type.** *Cons:* a second protocol, a second terminator
semantics, a second parser path, and a second thing R-12 can drop. It also collides with the
content-addressed id, since context records would share their document's reference.

**E — Structured document metadata block.** *Cons:* same authority problem as C, plus a new
bounded structure to validate.

## 7. Decision

**Option A. Source context travels inside the evidence record's existing `content` field.
`BIQ-REC/1`, `BIQ-END/1`, `ACCEPTED_RECORD_FIELDS` and the parser do not change.**

The only change to the scout is **guidance about what to capture in `content`** — a
documentation change to `agents/biq-research-scout.md`'s *Record fields* table. That is not a
protocol change: the line shape, the operation binding, the count semantics and the
fail-closed parsing are untouched, and a record written under the old guidance remains a
valid record.

Authority is divided in three, and Python holds the last word:

| Stage | Who | What |
|---|---|---|
| Retrieval | scout | fetches the document, puts the figure **and its stated context** in `content` |
| Candidate extraction | the skill's model | locates which passage states which dimension and quotes it verbatim into a footing |
| Admissibility | **Python** | resolves the evidence, checks operation, document, containment, applicability, value agreement, and the dimension-specific predicates below |

A model-supplied dimension value is never trusted because the scout returned it, and never
trusted because a skill wrote it. It is admissible only when Python can show the quoted text
is in the retrieved source and every binding holds.

## 8. Exact v1 evidence/context contract

**One record per source document.** The scout returns one `BIQ-REC/1` record per document it
retrieved, whose `content` carries the passage stating the figure **and** the passages
stating that figure's period, scope, currency, geography and methodology *where the document
states them*. Where the document does not state one, nothing is added — an absent dimension
stays absent and resolves to unknown.

**Excerpt semantics.** A `source_excerpt` must be a **contiguous verbatim substring** of the
cited item's `content` or `title`, matched after whitespace collapse and case folding.

| Category | Admissible for a footing |
|---|---|
| Source text, contiguous, verbatim | **Yes** |
| Deterministic normalisation (whitespace collapse, case folding) | **Yes** — applied equally to both sides by `_excerpt_present` |
| HTML entity decoding | **Yes, upstream only** — whatever text is stored in `content` is the authority; the excerpt must match *that*. No decoding happens at admissibility time |
| Non-contiguous passages joined into one excerpt | **No** — containment fails, and joining is composition |
| Model summary | **No** |
| Model paraphrase | **No** |
| Model translation | **No** |
| Model-calculated value | **No** (the ADR-0025 canonicalisations are `derived`, and read stated notation) |
| Model-inferred dimension | **No** |

A dimension may carry **several** footings from the same document; identical values
corroborate, differing values conflict (§14). One excerpt **may** establish several
dimensions — a sentence stating both period and geography backs two footings — and each
dimension still needs its own footing entry.

**Locator.** `source_locator` is **optional, audit-only, and never required for
admissibility**. It is never validated and never invented: a locator proves nothing the
excerpt does not, and requiring one would create pressure to fabricate it. Where the source
offers a natural locator — a page, section, heading, table or anchor — recording it is
encouraged; where it does not, the field is omitted.

## 9. Scout contract impact

**No protocol change.** `BIQ-REC/1`, `BIQ-END/1`, the operation binding, the count semantics,
the fail-closed parsing and `ACCEPTED_RECORD_FIELDS` are all unchanged, and remain so.

**One guidance change, in a follow-up milestone:** the *Record fields* table's description of
`content` gains an instruction to capture the dimension-bearing passages alongside the
figure, and a restatement that a dimension the document does not state must not be supplied.
`content` remains bounded at 20,000 characters; where a document's context does not fit, the
truncation note already records that the item is incomplete, and a footing quoting lost text
fails closed.

**Explicitly not added:** any `source_tier`, `verified`, `trust`, `context`, `geography`,
`currency`, `methodology` or `dimension` field. The scout gains no new authority.

## 10. EvidenceItem impact

**None.** `EvidenceItem` is reused unchanged and remains the sole source-context carrier
(ADR-0026 §13–14). No new type, no second registry, no new field. Local tiering, operation
binding, freshness, the untrusted marking and content-addressed identity all apply to context
for free, which is the whole reason for reusing it.

## 11. DimensionProvenance impact

**No new fields.** The eight existing ones are sufficient and remain the serialised set.

**One new admissibility predicate**, dimension-specific, implemented in
`dimension_provenance._assess()`:

> **A `stated` or `context` footing for `currency` is admissible only if its excerpt contains
> an ISO 4217 three-letter code.** A bare symbol — `$`, `£`, `€`, `¥` — establishes nothing,
> and neither does a currency *name*.

This closes the gap measured in §4 and restates ADR-0025's rule at the layer that was missing
it. Checking for a three-letter uppercase code is deterministic and needs no table beyond the
structural shape `quantity.parse_source_unit` already applies.

A currency **name** ("US dollars") is deliberately not sufficient in v1: mapping names to
codes needs a lookup table, and although ISO 4217 is a closed published standard rather than
a synonym engine, admitting one table invites the next. This is recorded as the single open
question in §23.

## 12. Dimension-by-dimension admissibility table

| Dimension | May be established by | May **never** be established by |
|---|---|---|
| `metric_definition` | `stated`/`context` excerpt naming what is counted | derivation of any kind; a metric label alone |
| `period` | `stated`/`context` excerpt naming the period | a filing date; a URL year; a publication date |
| `geography` | `stated`/`context` excerpt naming the territory, **including** a heading, table heading, footnote or page header that is present in `content` or `title` | any derivation; company headquarters or domicile; domain, country or TLD; "consolidated" (a scope word); synonym normalisation — `global` and `worldwide` do **not** match |
| `currency` | `derived` via ADR-0025 from stated notation carrying an ISO code; **or** `stated`/`context` whose excerpt **contains an ISO 4217 code** | a bare `$`, `£`, `€` or `¥`; a currency name; company domicile; source host; source type |
| `unit` | `derived` via ADR-0025 in practice — canonicalisation produces it at construction. A `stated`/`context` footing is permitted but redundant: its value must still be a canonical quantity type and must still agree with the statement | any excerpt asserting a magnitude-qualified label; any token outside the closed quantity vocabulary |
| `scope` | `stated`/`context` excerpt naming the reporting entity or boundary | company identity; assuming consolidation because a company was named |
| `methodology` | `stated`/`context` excerpt containing the stated basis — `US GAAP`, `IFRS`, `reported`, `adjusted`, `organic`, `constant currency`, `accrual basis`, a stated survey method | any derivation; **source type** (`filing` does not imply GAAP — foreign private issuers file under IFRS); publisher identity |

Headings, table headings, footnotes and page headers count as source context **only** when
they are genuinely present in the retrieved `content` or `title` of the same item, are bound
by an excerpt, and do not contradict the statement's own excerpt. They are not a separate
category and get no separate field.

## 13. Binding rules

Every footing must satisfy all of these; any failure yields an unresolved dimension and a
reason code in the trail:

1. **Registry** — `evidence_id` resolves in the set's `P_EVIDENCE` registry.
2. **Operation** — the cited evidence shares the statement's retrieval operation.
   **Mandatory, retained.** The operation id is minted per retrieval after any page was
   written, so a page author cannot know it; this is what stops evidence from one retrieval
   footing another.
3. **Citation** — for `stated` and `derived`, the cited item is one the statement itself
   cites.
4. **Same document** — for `context`, the cited item's `reference` equals a reference the
   statement cites, compared after the same folding. **"Same document" means identical
   normalised reference, and v1 retains that rule unchanged.** Not same publisher, not same
   domain, not same company, not a similar URL — each of those is a judgement, and a
   judgement must not sit between an unstated dimension and a compatible verdict.
5. **Containment** — the excerpt is a contiguous substring of that item's `content` or
   `title` after folding.
6. **Applicability** — the footing declares **both** `period` and `scope`, and both match the
   statement. **There is no document-wide default.** Context that does not say what it
   governs governs nothing; context scoped to a section must declare that scope; context with
   no identifiable applicability is inadmissible.
7. **Dimension predicate** — §12, notably the ISO-code rule for `currency`.
8. **Value agreement** — the footing's value matches the statement's declared value.

A caller cannot establish admissibility by supplying a dimension value. The value is the
*last* thing checked, and it is checked against evidence, not accepted as evidence.

## 14. Conflict rules

Unchanged from ADR-0026, and extended to the cases this ADR introduces:

| Situation | Result |
|---|---|
| Two excerpts in the same document, same value | Corroboration; dimension resolves |
| Two excerpts in the same document, different values | **Dimension unknown + explicit conflict** |
| Statement excerpt contradicts a context excerpt | **Dimension unknown + explicit conflict** — inline does not automatically win |
| Two documents disagree | Not reachable in v1: cross-document context is prohibited |
| Two operations disagree | Not reachable: operation binding refuses |
| Conflicting applicability | The footing whose applicability does not match simply does not apply; if two match and disagree in value, conflict |

No silent winner. No averaging. No recency winner. No source-tier winner. Conflicts are
preserved, and the dimension stays unresolved.

## 15. Serialization rules

Unchanged from ADR-0026. The serialised footing carries exactly: `dimension`, `value`,
`basis`, `evidence_id`, `source_excerpt`, `source_locator`, `applicability`, `derivation`.

**No additional fields, and specifically no redundant source metadata.** `source`,
`reference`, `source_tier`, `trust`, `freshness` and `retrieved_at` are resolved locally from
the `EvidenceItem` and live only in the re-derived resolution trail. On reload, footings are
rebuilt from caller-authored fields only; any serialised source metadata is discarded, and
`resolved_dimensions` and the trail are not restored. A serialised admissibility verdict is a
verdict nobody re-checked.

Footings continue to serialise in fixed seven-dimension order.

## 16. Backward compatibility

**Fully backward compatible. No backward-incompatible parser change is required.**

* Context is **optional**. A record whose `content` carries no dimension-bearing text is a
  valid record.
* A statement with no footings behaves exactly as before ADR-0026: declared dimensions pass
  through, unless the set was built with `require_dimension_provenance=True`.
* A statement whose footings cannot be satisfied produces **unresolved dimensions**, never an
  error and never a false match.
* `ACCEPTED_RECORD_FIELDS` is unchanged, so every existing record parses identically.
* The new ISO-code predicate for `currency` is strictly narrowing. It can only turn a
  currently-admitted footing into an unresolved one, which is the safe direction, and no
  shipped skill authors currency footings yet.

## 17. Research skill migration implications

Applies to `biq-company-analysis`, `biq-market-analysis`, `biq-competitor-analysis` and
`biq-industry-research`. **None is migrated by this ADR.**

**What their future scout brief must request:** nothing new in the brief itself — the brief's
six fields are unchanged and carry no field for this. The request lives in the *agent
definition's* content guidance, which is shared by all four.

**Can existing research outputs support dimension provenance?** Opportunistically and
unreliably. Existing `content` is "what the source says" and sometimes already includes
surrounding context; where it happens to contain the dimension-bearing passage, a footing
works today. Nothing guarantees it.

**Migration shape: one shared infrastructure change first, then skill-by-skill.** The agent
content guidance and the footing-authoring convention are shared and change once. Each skill
then adopts footings independently, and can be migrated and reviewed on its own. Doing it
skill-by-skill from the start would produce four conventions.

**What stays unchanged:** the disclosure gate, the four-tier model, intents, the query
builder, source tiering, staleness, conflict handling, the one-dispatch-per-retrieval rule,
and every skill's prohibition on estimating, averaging and recommending.

## 18. R-12 boundary

Three separate things, and this ADR touches only the first:

1. **Source-context architecture** — what a record *contains*. Decided here.
2. **Scout return contract** — the `BIQ-REC/1`/`BIQ-END/1` shape. Unchanged, and out of scope.
3. **R-12 operational reliability** — whether the scout's hand-back *delivers* its record
   lines at all. Unchanged, still open.

**This ADR does not resolve R-12 and must not be read as progress on it.** A richer `content`
field does not make a hand-back more likely to arrive. The M10.2-R.4 run observed one clean
first delivery, which is one data point against a historically intermittent failure, and
nothing here changes that.

## 19. Explicit non-goals

* No change to `BIQ-REC/1`, `BIQ-END/1`, the parser, or `ACCEPTED_RECORD_FIELDS`.
* No change to `compatibility.compare()`.
* No change to ADR-0025 or ADR-0026.
* No second protocol, no second evidence type, no second registry.
* No cross-source or cross-document context composition.
* No cross-operation context.
* No semantic synonym engine, and no free-text normalisation beyond the existing folding.
* No geography or methodology inference, derivation or vocabulary.
* No FX, no rate table, no currency-name mapping.
* No trust, verification, support or confidence promotion from admissibility.
* No fix to the content-addressed id (§ below).
* No live research, and no claim about live behaviour.

## 20. Follow-up implementation milestone

**M10.2-R.8 — Source-context capture and currency-code admissibility.**

*Likely to change:* `agents/biq-research-scout.md` (content guidance only) ·
`lib/python/biq/synthesis/dimension_provenance.py` (the ISO-code predicate for `currency`,
one new reason code) · `tests/unit/` (new module) · ADR index · development record.

*Explicitly not changed:* `research/scout.py`, `compatibility.py`, `quantity.py`, the
schemas, the commands, the skills.

## 21. Acceptance criteria for that implementation

1. `BIQ-REC/1`, `BIQ-END/1` and `ACCEPTED_RECORD_FIELDS` byte-identical in semantics; parser
   untouched.
2. `compatibility.py` md5 unchanged at `35a89e32f6fad71bc7c21abe9dbe4915`.
3. ADR-0025 and ADR-0026 unmodified.
4. A `currency` footing whose excerpt carries only `$`, `£`, `€` or `¥` is **refused**, with a
   named reason code — the §4 gap closed, pinned by test.
5. A `currency` footing whose excerpt carries an ISO 4217 code is admitted when every other
   binding passes.
6. A currency **name** without a code is refused in v1.
7. Old records with no context still parse and produce unresolved dimensions, never errors.
8. Every ADR-0026 binding still enforced; every R.6 attack test still passes.
9. Regression: 3,153 + new tests, 0 failures, 0 errors, 19 skips; `--strict` passes.
10. No existing test deleted, weakened or retargeted.
11. No live research; no scout dispatch; no commit; no push.

## 22. Consequences

**Positive**
* The supply gap closes without touching the protocol, the parser, or any security surface.
  The smallest possible change to `BIQ-REC/1` is no change at all.
* A measured, real gap — a bare `$` establishing USD — is closed rather than carried forward.
* `EvidenceItem` stays the one carrier, so context inherits local tiering, operation binding,
  freshness and the untrusted marking with no new code.
* The id collision stops mattering for v1, because one-record-per-document does not rely on
  two items sharing a reference.

**Negative**
* **Correctness now depends partly on agent guidance rather than on a typed field.** A scout
  that ignores the guidance yields records with no context and dimensions that stay unknown.
  That is the safe failure, but it is a failure the architecture cannot detect or enforce.
* **The 20,000-character bound must now hold the figure and its context.** A long filing may
  truncate away the very passage a footing needs. Truncation is recorded and the footing then
  fails closed, but the evidence is silently poorer.
* **Containment is still not meaning.** The excerpt proves the text is in the source, not that
  it means the value. ADR-0026 said this; it remains true and remains the residual judgement.
* **A currency name will not establish a currency in v1**, so a document saying only "amounts
  in US dollars" leaves currency unknown. A real and accepted cost.
* Cross-document context stays prohibited, so a figure in one document and its currency
  declaration in another remain uncombinable.

## 23. Open questions

One, and it is genuinely open rather than deferred:

**Should a closed ISO 4217 currency-*name* table be admitted for the `currency` dimension?**
It is a published, closed, external standard, not a judgement about meaning — which makes it
categorically different from a `global`/`worldwide` synonym table. Admitting it would let
"amounts are stated in US dollars" establish `USD`, which is a common and genuinely
unambiguous phrasing. Against: it is still a mapping from words to a value, and the line
between "closed standard" and "synonym engine" is easier to hold at *no tables at all*. v1
decides **no**; the question deserves a deliberate answer rather than drifting into one.

Everything else this milestone raised is decided above.

## Revisit when

A document-identity model exists that can establish "same reporting package" mechanically —
reopening §13 rule 4 and nothing else. Also revisit if the content bound proves too small in
practice, or if the id collision starts to bite because multi-record-per-document retrieval
becomes necessary.
