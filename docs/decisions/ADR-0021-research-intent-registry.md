# ADR-0021 — One immutable research-intent registry replaces the flat intent tables

**Date:** 2026-09-14
**Status:** Accepted
**Milestone:** M9-D.4

## Context

ADR-0019 grew `biq.research.contract.INTENTS` from five members to seven and deferred a
shape question to whichever milestone next needed it:

> If the tuple reaches a size where a reader cannot hold it, the next milestone to add one
> should consider a per-category intent table instead.

ADR-0020 took the enumeration to nine, answered the question *not yet*, and named the
condition for revisiting it:

> **Deferred, deliberately: the per-category intent table.** Nine members with a closed,
> validated tuple is still holdable. … `/industry-research` (M9-D.4) is the next milestone
> that may add one; if it needs more than one new intent, the table should be reconsidered
> then.

M9-D.4 turned out to be a different milestone from the one ADR-0020 anticipated:
`/industry-research` is not being built here, and **no intent is being added at all**. What
is being resolved is the deferred architecture question on its own, with the enumeration
frozen — which is the safest moment to move a structure, because nothing about its contents
is simultaneously in flight.

The argument for moving now is not that nine identifiers are unreadable. It is that the
*metadata around them* had already fragmented into three flat structures across two modules,
and the most important relationship was not written down anywhere:

| Structure | Lived in | Held |
|---|---|---|
| `INTENTS` | `research/contract.py` | the closed tuple `validate()` checks |
| `INTENT_TERMS` | `research/query.py` | the words each intent puts in the query |
| `SUBJECT_LEADS` | `research/query.py` | which intents phrase the subject first |
| *category → intent* | **nowhere** | recoverable only by reading three `SKILL.md` files |

Adding `LANDSCAPE` and `COMPARISON` in M9-D.3 meant editing three of those four by hand and
hoping none was missed, and a miss is silent in two of the three cases: an intent absent
from `INTENT_TERMS` builds a query with no intent word and still passes the gate; an intent
absent from `SUBJECT_LEADS` quietly changes word order. The fourth row is worse than
fragmented — the fact that `trends` is asked by three skills and `positioning` by two was a
property of the system that existed only in prose, so nothing could test it and nothing
could stop a future milestone from minting `COMPETITOR_TRENDS`.

## Decision

**One immutable structured registry — `lib/python/biq/research/intents.py` — is the
canonical representation of research-intent metadata. `INTENTS`, `INTENT_TERMS` and
`SUBJECT_LEADS` become views derived from it.**

Each intent is one `ResearchIntent` record carrying its identifier, its purpose, its
query term, whether the query leads with the subject, the categories that ask it, and the
production skills or commands that issue it. Categories are explicit values
(`company`, `market`, `competitor`), not something inferred from an intent's name.

**There is exactly one source of truth.** The three familiar names are not tables beside the
registry; they are computed from it at import, in its declaration order, and the modules
that used to own them now re-export the registry's objects. The tests assert *derivation*
rather than equality — `contract.INTENTS is intents.INTENTS` — because two structures that
merely agree today are two sources of truth with a delay fuse.

## Why

**Because parallel flat structures grow parallel bugs.** Four places to edit, three of which
fail silently, is a defect waiting for the next intent. One record per intent makes an
omission a syntax error rather than a behaviour change.

**Because the category relationship deserved to exist in code.** It is now declarative,
queryable (`intents_for_category`, `categories_for_intent`) and testable. The property that
`trends` is one shared identifier rather than three category-specific twins is now asserted
by a test instead of defended by a paragraph.

**Because the enumeration is frozen this milestone.** Moving a structure and changing its
contents in the same milestone makes it impossible to tell a refactor bug from a feature
bug. Nothing was added, so every query string can be pinned before and after and must match
byte for byte — and is.

**Because immutability is cheap here and matters.** Intent metadata decides the wording that
goes into a query, and query wording is what the disclosure gate assesses.

## Compatibility

**No identifier changed, no query moved, no caller was asked to migrate.**

- The nine identifiers are unchanged: `benchmark`, `profile`, `sizing`, `trends`,
  `positioning`, `overview`, `drivers`, `landscape`, `comparison`.
- `INTENTS` holds the same nine in the same order. It is derived from the registry's
  declaration order, which was chosen to reproduce the previous literal exactly.
- `INTENT_TERMS` and `SUBJECT_LEADS` keep their names, their module-level home in
  `query.py`, and their contents word for word.
- `contract.COMPANY`, `contract.CATEGORIES` and the other category constants are re-exported
  from the registry module, so every existing import path resolves unchanged.
- `research/__init__.py` gained the registry names additively. Nothing was removed from
  `__all__`.

**The compatibility boundary is explicit:** a compatibility name is a *derived alias*, never
a second definition. `INTENT_TERMS` is a read-only proxy over a mapping comprehended from
the registry, not a dict that happens to match it. Re-introducing a literal `INTENTS = (…)`
or `INTENT_TERMS = {…}` in `contract.py` or `query.py` is caught by a test that reads those
modules' source.

`INTENT_TERMS` changed type from `dict` to `types.MappingProxyType`. Reads, `in`, `.get()`
and iteration are unchanged; writes now raise `TypeError`. No production caller writes to
it — the query builder only calls `.get()` — and no test did either.

## Shared intents

**`TRENDS` and `POSITIONING` remain single shared identifiers.** `TRENDS` is listed once and
names `company`, `market` and `competitor`; `POSITIONING` is listed once and names `company`
and `competitor`. The registry expresses the sharing through the record's `categories`
field, so a category can list an intent without a copy of it existing.

Duplicating them per category — `COMPANY_TRENDS`, `COMPETITOR_TRENDS` — would make ownership
visually simpler and would be wrong for the reason ADR-0020 already gave: two names for one
question is exactly the ambiguity a closed enumeration exists to prevent, and a skill's
focus table already states the mapping in the one place a reader looks. A test now asserts
no identifier is category-prefixed or category-suffixed.

**`BENCHMARK` carries no category.** It is the default intent of every `ResearchRequest` and
`/retrieval-slice` issues it against `INDUSTRY`. Giving it an owner would record something
the code does not do, so its `categories` field is empty and a test pins that.

## Non-goals

- **No new research capability.** No intent, category, skill, command or agent was added.
  `/industry-research`, SWOT, strategy analysis and decision support remain unbuilt, and
  `industry` deliberately has no intent mappings — it stays a valid request category and
  gains its mappings in the milestone that builds its skill.
- **No query redesign.** Not one word of query wording changed. Twelve representative
  queries spanning all three skills and all nine intents are pinned as exact strings.
- **No retrieval redesign.** The gate, `open_retrieval`/`close_retrieval`, the scout
  protocol, evidence normalisation, source tiering and candidate-claim verification are
  untouched.
- **No category-specific duplicate identifiers.** See *Shared intents*.
- **The registry is not a framework.** It performs no retrieval, calls no gate, dispatches
  no scout, parses no evidence, creates no claim and synthesises nothing. A test reads its
  source and fails if any of those names appears in it.

## Security

**Registry metadata is not user-controlled.** The table is declared in source, closed, and
built at import from literals. Nothing in it is ever constructed from a subject, a
competitor name, a public term, a skill argument or retrieved content.

**User input cannot alter a research-intent definition.** This is the reason immutability is
a requirement rather than a preference: intent metadata decides the words that go into a
query, and the query text is precisely what the disclosure gate assesses. A registry a
caller could write to would be a registry that a hostile company name — or untrusted
retrieved content being paraphrased by a model — could write to, and the text the gate
assessed would then differ from the text the registry described. `ResearchIntent` is a
namedtuple, `INTENT_REGISTRY`, `INTENT_TERMS` and `CATEGORY_INTENTS` are
`MappingProxyType`, and the accessors return tuples. There is no write path.

**The disclosure gate remains authoritative.** The registry supplies wording; it grants
nothing. An intent outside the enumeration is still refused by `ResearchRequest.validate()`
before the gate sees it, `RetrievalRequest` still cannot be built without a gate decision,
and no path added here reaches retrieval. Source-tier assignment stays local and
scout-supplied tiers stay dropped; candidate claims stay `candidate` and `verified: false`.

## Future

**`/industry-research` adds its mappings here.** When that skill is built, `industry` joins
`ANALYSIS_CATEGORIES` and the intents it asks add `INDUSTRY` to their `categories` field.
If it needs a question no existing intent expresses, that intent is added as one new record
— which is now a single edit in a single file, which was the point.

**Strategy and decision support do not belong here.** `biq-strategy-recommendations` and
`biq-decision-support` are Layer 3 synthesis: they consume evidence rather than retrieve it,
and they issue class-7 recommendations, which is a different provenance class with a
different evidential bar. Adding a `strategy` category or a `recommendation` intent would
put a synthesis capability behind a retrieval gate and quietly imply that a recommendation
is something the scout can fetch. It is not.

**The registry's fields are the ones with a consumer today.** No speculative metadata was
added — no weighting, no priority, no default-tier, no per-intent staleness override.
Freshness windows stay in `sources.py`, where policy lives.

---

**Related:** ADR-0009 (the disclosure boundary) · ADR-0012 (component placement — this is
the placement rule applied to metadata) · ADR-0015 (model-mediated scout dispatch) ·
ADR-0017 (operation-bound line records) · ADR-0019 (market research intents, which deferred
this decision) · ADR-0020 (competitor research intents, which deferred it again and named
the condition). **Neither ADR-0019 nor ADR-0020 is amended:** both recorded the right
decision for their milestone, and this one resolves the question they left open rather than
overturning anything they decided.
