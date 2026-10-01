# ADR-0020 — Two research intents added for competitor analysis, and two reused

**Date:** 2026-09-14
**Status:** Accepted
**Milestone:** M9-D.3

## Context

ADR-0019 grew `biq.research.contract.INTENTS` from five members to seven and closed with an
explicit hand-off to this milestone:

> `INTENTS` is now a seven-member enumeration that two skills read differently, and it will
> grow again when competitor and industry research land. … If the tuple reaches a size where
> a reader cannot hold it, the next milestone to add one should consider a per-category
> intent table instead.

M9-D.3 is that milestone. `biq-competitor-analysis` defines four research questions —
`landscape`, `comparison`, `positioning` and `developments` — so the decision ADR-0019
deferred has to be made now, and it is really two decisions: **how many intents to add**, and
**whether a flat enumeration is still the right shape**.

On the first: two of the four map onto existing intents and two do not.

- **`positioning`** is `POSITIONING`, whose own comment in `contract.py` already reads *"how
  entities compare publicly"*. That is not a near-miss; it is the same question, and the
  query builder renders it `market position`, which is what a competitor-positioning
  retrieval wants.
- **`developments`** is `TRENDS` — *"what is changing"*. `biq-company-analysis` has mapped
  its own `developments` focus onto `TRENDS` since M9-C.3 and ships that way, so a second
  intent for the same question would give the enumeration two names for one thing and leave
  a reader guessing which skill meant which.
- **`landscape`** — *who competes here, on what terms* — has no existing intent. The closest
  is `POSITIONING`, which is a different question: where one entity sits is not who the
  entities are, and using one intent for both would have made the `full` path issue two
  retrievals with byte-identical query text, which the skill's own rule against redundant
  retrievals forbids.
- **`comparison`** — *how do these named entities compare on observable dimensions* — has
  none either, and the query wording is the reason it matters: a comparison retrieval that
  phrased itself as `market position` returns positioning pages for a question about
  side-by-side dimensions.

On the second: seven is not nine's problem. The enumeration is closed, validated and read in
one place; the cost of a per-category table is that `ResearchRequest` would need to know
which categories may carry which intents, which is a second validation surface for a
correctness property the flat tuple already gives for free.

## Decision

**Add two intents, `LANDSCAPE` and `COMPARISON`, reuse `POSITIONING` and `TRENDS` for the
other two competitor questions, and keep the flat enumeration.**

```python
LANDSCAPE = "landscape"      # who competes with whom, and on what terms
COMPARISON = "comparison"    # how named entities compare on observable dimensions

INTENTS = (BENCHMARK, PROFILE, SIZING, TRENDS, POSITIONING, OVERVIEW, DRIVERS,
           LANDSCAPE, COMPARISON)
```

with the corresponding `INTENT_TERMS` entries `"competitive landscape"` and
`"competitor comparison"`, both names exported from `biq.research`, and both added to
`query.SUBJECT_LEADS` so the query reads `Contoso Logistics competitive landscape` rather
than `competitive landscape Contoso Logistics`.

`SUBJECT_LEADS` is itself new — it names the tuple that was previously inline in
`query.build()` as `(PROFILE, POSITIONING)`. Extracting it changes no behaviour for any
existing intent and makes the subject-order rule assertable rather than buried in a
conditional.

**The change is strictly additive.** The seven earlier intents keep their names, their
positions, their query wording and their behaviour. No existing query moves by a byte —
`unit.test_m9d3_competitor_analysis.TestIntentAddition` pins both
`Northwind Logistics logistics company profile` (M9-D.1) and
`cold chain logistics market overview` (M9-D.2) as literal strings.

**No new claim kind.** Competitor research reuses `financials`, `market_sizing` and
`positioning`, which is the whole of `sources.STALENESS_DAYS`; a competitive relationship
ages like a positioning statement, a scale figure like a financial one, and a share estimate
like a market size. A test pins the three.

## Why this is an extension, not a redesign

`contract.py` was written for this. Its own comment on the category constants says the core
is category-agnostic so that "the future company/market/competitor/industry skills
parameterise this core rather than each implementing their own request type". An intent is
one of the two axes of that parameterisation; competitor research is the third consumer, and
it needed two axis values rather than four because the enumeration had already grown toward
the questions it asks.

Nothing else moved. This ADR does **not** change:

- the disclosure gate, the four tiers, or any tier check;
- the `BIQ-REC/1` / `BIQ-END/1` scout protocol (ADR-0017);
- source-tier classification or the first-party registry (ADR-0018);
- the declared-conflict transport (ADR-0016);
- candidate-claim policy, the evidence schema, or the claim ledger;
- `biq-company-analysis`, `biq-market-analysis` or their commands, which retrieve under the
  same intents they always did.

## Consequences

**Good.** Competitor research asks competitor questions. The `full` path issues four
distinct, non-redundant queries, each gate-authorised under its own operation — verified
directly, by building all four and asserting four distinct query strings rather than by
asserting four distinct intent constants. Reuse keeps the enumeration honest: a reader
looking for "what is changing" finds one intent, not one per skill.

**The cost.** `INTENTS` is now nine members, and the mapping from a skill's focus value to an
intent is no longer one-to-one — `developments` means `TRENDS` in two skills and
`positioning` means `POSITIONING` in two. That indirection is stated in each skill's focus
table, which is the one place a reader looks, and a test reads the mapping out of the skill's
own table rather than restating it.

**Deferred, deliberately: the per-category intent table.** Nine members with a closed,
validated tuple is still holdable. The condition ADR-0019 set — a reader cannot hold it —
has not been met, and meeting it speculatively would add a category/intent compatibility
matrix that nothing currently needs. `/industry-research` (M9-D.4) is the next milestone that
may add one; if it needs more than one new intent, the table should be reconsidered then.
This decision does not block that refactor.

**Rejected: a dedicated `DEVELOPMENTS` intent.** It duplicates `TRENDS` for the question
`biq-company-analysis` already asks under `TRENDS`, and two names for one question is exactly
the confusion a closed enumeration exists to prevent. The cost of reuse is an indirection in
one table; the cost of duplication is a permanent ambiguity in the core.

**Rejected: a dedicated `COMPETITOR_POSITIONING` intent.** Same reason. `POSITIONING` is
already documented as "how entities compare publicly", which is the competitor question in
the words the enumeration already used.

**Rejected: reuse `POSITIONING` for `landscape` as well.** It produces byte-identical query
text for two of the four `full` retrievals, which is a redundant retrieval by any reading —
and the wrongness would be invisible, because the second retrieval succeeds and returns
plausible sources.

**Rejected: let the skill hand-assemble query text.** It moves query construction out of the
deterministic builder for one caller, which ends the property that an audit record reproduces
a decision. ADR-0019 rejected this for the same reason and the reason has not changed.

## Security implications

None that change an existing control, and one worth stating explicitly.

An intent is **query wording**, not authority. Adding one cannot raise a disclosure tier,
promote a source, verify a claim or widen what may be transmitted: a request carrying a new
intent goes through the same `ResearchRequest.validate()` and the same `gate.assess()` as
every other, and an intent outside the tuple is refused before the gate sees it.

The one new transmission shape M9-D.3 introduces is **competitor names as public terms**
(`competitor_1`, `competitor_2`, …). A company name is public by construction, is not a
member of `aggregation.NARROWING_ATTRIBUTES`, and therefore adds no re-identification risk
to a Tier 0 query — asserted by test. A name is data: it is emitted into query text and has
no path to changing a tier, verifying a claim or authorising a disclosure. A name long enough
to carry an instruction is refused by `ScoutBrief`'s existing `MAX_QUERY_CHARS` cap, which is
the second, independent refusal behind the skill's own rule that an instruction-shaped name
is ambiguous input and goes to the ambiguity protocol rather than into a retrieval.

## Related

ADR-0009 (disclosure tiers) · ADR-0015 (model-mediated dispatch) · ADR-0016 (declared
conflicts) · ADR-0017 (operation-bound line records) · ADR-0018 (first-party registry) ·
ADR-0019 (market research intents, which deferred this decision here).
