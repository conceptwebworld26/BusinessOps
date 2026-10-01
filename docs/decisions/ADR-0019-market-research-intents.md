# ADR-0019 — Two research intents added for market analysis

**Date:** 2026-09-13
**Status:** Accepted
**Milestone:** M9-D.2

## Context

`biq.research.contract.INTENTS` enumerated five research intents, each mapped in
`biq.research.query.INTENT_TERMS` to the words that express it inside the query the gate
authorises:

| Intent | Query wording |
|---|---|
| `BENCHMARK` | `benchmark` |
| `PROFILE` | `company profile` |
| `SIZING` | `market size` |
| `TRENDS` | `trends` |
| `POSITIONING` | `market position` |

M9-D.2 builds `biq-market-analysis`, whose contract defines four research questions:
`overview`, `size-growth`, `trends` and `drivers-risks`. Two map onto existing intents
exactly — `size-growth` is `SIZING` and `trends` is `TRENDS`. The other two do not map onto
anything:

- **`overview`** asks what a market *is* — its definition, scope, geography and current
  state. The nearest existing intent is `PROFILE`, which the query builder renders as the
  literal words **"company profile"**. Sending `cold chain logistics company profile` to a
  web search is not a near-miss; it retrieves company pages for a question about a market,
  and it would have done so on the live smoke test.
- **`drivers-risks`** asks what *moves* a market — demand, supply, constraints. No existing
  intent expresses it. `TRENDS` is the closest and is a different question: what is changing
  is not the same as what is causing it, and using one intent for both would have made the
  `full` path issue two retrievals whose queries were byte-identical, which the skill's own
  rule against redundant retrievals forbids.

The alternative to adding intents was to smuggle the framing in elsewhere — appending words
to the subject, or inventing a public term whose only job is wording. Both put query
construction back in the caller's hands, which is precisely what `query.build()` exists to
prevent: the builder is deterministic so that an audit record reproduces a decision, and a
caller who hand-assembles phrasing around it breaks that property for every future request,
not just market ones.

## Decision

**Add two intents, `OVERVIEW` and `DRIVERS`, to the shared research core, and nothing else.**

```python
OVERVIEW = "overview"    # what a market is: definition, scope, current state
DRIVERS  = "drivers"     # what moves a market: demand, supply, constraints

INTENTS = (BENCHMARK, PROFILE, SIZING, TRENDS, POSITIONING, OVERVIEW, DRIVERS)
```

with the corresponding `INTENT_TERMS` entries `"market overview"` and
`"market drivers and constraints"`, and both names exported from `biq.research`.

**The change is strictly additive.** The five original intents keep their names, their
positions, their query wording and their behaviour. `query.build()`'s subject-leads rule
still fires only for `PROFILE` and `POSITIONING`, so no existing query moves by a byte —
asserted directly by `unit.test_m9d2_market_analysis.TestIntentAddition`, which pins
`Northwind Logistics logistics company profile` as a literal string.

## Why this is an extension, not a redesign

`contract.py` was written for this. Its own comment on the category constants says the
core is category-agnostic so that "the future company/market/competitor/industry skills
parameterise this core rather than each implementing their own request type". An intent is
one of the two axes of that parameterisation; the market skill is the first consumer to need
an axis value that company research did not.

Nothing else moved. This ADR does **not** change:

- the disclosure gate, the four tiers, or any tier check;
- the `BIQ-REC/1` / `BIQ-END/1` scout protocol (ADR-0017);
- source-tier classification or the first-party registry (ADR-0018);
- the declared-conflict transport (ADR-0016);
- candidate-claim policy, the evidence schema, or the claim ledger;
- `biq-company-analysis` or `/company-analysis`, which retrieve under the same three intents
  they always did.

## Consequences

**Good.** Market research asks market questions. The `full` path issues four distinct,
non-redundant queries, each gate-authorised under its own operation. Future research skills
that need a new question shape have a precedent with a bounded blast radius.

**The cost.** `INTENTS` is now a seven-member enumeration that two skills read differently,
and it will grow again when competitor and industry research land. The mitigation is that
the enumeration is closed and validated — `ResearchRequest.validate()` refuses an intent not
in the tuple, so an unregistered intent fails at the gate rather than producing a query
nobody designed. If the tuple reaches a size where a reader cannot hold it, the next
milestone to add one should consider a per-category intent table instead, which is a
refactor this decision does not block.

**Rejected: reuse `PROFILE` for market overview.** It produces a wrong query for every
market request, and the wrongness is invisible — the retrieval succeeds, returns plausible
sources about companies, and the report reads fine. A silent retrieval of the wrong thing is
the failure mode the whole research layer is built to avoid.

**Rejected: let the skill hand-assemble query text.** It moves query construction out of the
deterministic builder for one caller, which ends the property that an audit record
reproduces a decision.

## Related

ADR-0009 (disclosure tiers) · ADR-0015 (model-mediated dispatch) · ADR-0016 (declared
conflicts) · ADR-0017 (operation-bound line records) · ADR-0018 (first-party registry).
