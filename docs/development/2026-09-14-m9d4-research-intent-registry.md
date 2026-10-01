# 2026-09-14 — M9-D.4 Research Intent Architecture Consolidation

**Milestone:** M9-D.4 — research-intent registry
**Status on completion:** COMPLETED
**Supersedes:** None

## 1. Prompt / task performed

Evaluate and, if safe, replace the flat research-intent representation with a per-category
research-intent registry, preserving every externally observable behaviour. The prompt
pre-resolved the design decision (one structured registry, exactly one source of truth),
fixed the category model at `company` / `market` / `competitor`, forbade adding any new
command, skill, intent, category or capability, and required the refactor to be
semantically neutral or to stop and report BLOCKED.

Explicitly out of scope and not done: `/industry-research`, SWOT, strategy analysis,
decision support, new skills, new commands, scout-protocol changes, disclosure-gate changes,
source-tier changes, candidate-claim changes, EvidenceSet changes, MCP servers, commits,
pushes.

## 2. Objective

Resolve the architecture question ADR-0019 deferred and ADR-0020 deferred a second time:
whether to keep extending a flat intent tuple, or move to a structured per-category table.
Move the representation without moving any behaviour.

## 3. Changes made

**Inspection first, because the prompt's stop conditions are mostly discovered, not
designed.** Before writing anything I established what the flat representation actually
was, who consumed it, and whether the intent count matched the prompt's expectation.

The metadata turned out to be in four places, three of them structures and one of them
nowhere:

| Structure | Lived in | Held |
|---|---|---|
| `INTENTS` | `research/contract.py` | the closed tuple `ResearchRequest.validate()` checks |
| `INTENT_TERMS` | `research/query.py` | the words each intent puts into the query text |
| `SUBJECT_LEADS` | `research/query.py` | which intents phrase the subject first |
| category → intent | **nowhere in code** | recoverable only from three `SKILL.md` focus tables |

**Stop-condition check 1 — the intent count.** The repository holds exactly nine genuine
production identifiers: `benchmark`, `profile`, `sizing`, `trends`, `positioning`,
`overview`, `drivers`, `landscape`, `comparison`. No compatibility alias and no unused
historical identifier was found. This matches the prompt's "exactly nine", so no discrepancy
needed reporting. Worth noting because the prompt's *required current intents* section lists
only eight under the three categories — the ninth is `BENCHMARK`, which is the
category-agnostic request default rather than a skill's question, and is discussed below.

**Stop-condition check 2 — a collision the prompt did not anticipate.** `lib/python/biq/
commands/query.py` also defines a module-level `INTENTS`. It belongs to the
`/ask-business-data` natural-language router and is unrelated to research intents. It was
left untouched; the name collision is pre-existing and out of scope.

**Baseline captured before any edit:** 2475 tests, 0 failures, 0 errors, 19 skipped —
identical to the baseline the prompt stated, so no explanation of a difference was needed.

**Then the registry.** `lib/python/biq/research/intents.py` was created holding one
`ResearchIntent` record per intent. The declaration order was chosen to reproduce the
previous `INTENTS` literal exactly, so every derived tuple comes out byte-identical to the
literal it replaced — verified by printing all four derived views and diffing them against
the originals before rewiring anything.

`contract.py` and `query.py` were then rewired to import from it rather than declare their
own. The historical comment block in `contract.py` explaining how the enumeration reached
nine was kept — it explains why two of the nine are shared rather than duplicated, which is
the registry's least obvious property — and retargeted from a docstring-comment above an
assignment to a plain comment, with a closing line noting that M9-D.4 changed where the
table lives and not what is in it.

`research/__init__.py` gained the registry names additively; nothing was removed from
`__all__`.

**The category question, decided rather than assumed.** `CATEGORIES` already contained four
values including `industry`, and moving the category identifiers into the registry module was
necessary to avoid the registry restating category strings as literals — which would have
been the second source of truth the prompt forbids. They are re-exported from `contract.py`,
so `contract.COMPANY` and every existing import path still resolve. `CATEGORY_LABEL` stayed
in `contract.py`: it is refusal wording, not intent metadata.

A separate `ANALYSIS_CATEGORIES` tuple names the three categories with a production skill.
`industry` is deliberately absent from it and no intent claims it — it remains a fully valid
request category, exactly as before, and gains mappings in the milestone that builds its
skill.

## 4. Files created

- `lib/python/biq/research/intents.py` — the canonical registry
- `tests/unit/test_m9d4_research_intent_registry.py` — 58 focused tests
- `docs/decisions/ADR-0021-research-intent-registry.md`
- `docs/development/2026-09-14-m9d4-research-intent-registry.md` — this record

## 5. Files modified

- `lib/python/biq/research/contract.py` — category and intent constants plus `INTENTS` now
  imported from the registry; the two literal declarations removed; the historical
  enumeration comment retained and retargeted
- `lib/python/biq/research/query.py` — the `INTENT_TERMS` and `SUBJECT_LEADS` literals
  replaced by an import of the registry's views
- `lib/python/biq/research/__init__.py` — registry names exported, additively
- `architecture.md` — new "The research-intent registry" subsection under Layer 2B; ADR
  index row
- `project_plan.md` — M9-D.4 row added as `COMPLETED`; `/industry-research` renumbered to
  M9-D.5+
- `docs/decisions/README.md` — ADR-0021 index row

## 6. Files deleted

None.

## 7. Features implemented

No feature. This milestone is a representation change with a deliberately empty behavioural
delta. What it adds is an accessor surface over metadata that already existed:
`INTENT_REGISTRY`, `CATEGORY_INTENTS`, `ANALYSIS_CATEGORIES`, `ResearchIntent`, `intent()`,
`intents_for_category()`, `categories_for_intent()` — all in `biq.research`, all read-only,
none user-reachable as a command or skill.

## 8. Tests performed

```
python tests/run_tests.py                                        # baseline, before any edit
python tests/run_tests.py unit.test_m9d4_research_intent_registry
<temporary mutation of one query_term, re-run, revert>           # teeth check
<M9 subset: all 26 test_m9*.py modules across unit/integration/negative>
python tests/run_tests.py                                        # full regression
claude plugin validate . --strict
```

## 9. Test results

**Baseline, before any change:**

```
Ran 2475 tests in 115.571s
OK (skipped=19)
ran 2475 | failures 0 | errors 0 | skipped 19
```

**Focused M9-D.4 suite:**

```
Ran 58 tests in 0.011s
OK
ran 58 | failures 0 | errors 0 | skipped 0
```

**Teeth check.** A passing test suite over a refactor proves nothing unless it can fail, so
one registry `query_term` was temporarily changed from `competitive landscape` to
`competitor competitive landscape` and the suite re-run:

```
ran 58 | failures 3 | errors 0 | skipped 0
```

The mutation was reverted and the suite re-run clean (`ran 58 | failures 0`). Three
independent assertions caught it: the preserved-wording pin, the byte-for-byte query pin,
and the category-leakage check.

**M9 subset — all 26 `test_m9*` modules:**

```
Ran 1372 tests in 0.368s
OK (skipped=2)
ran 1372 | failures 0 | errors 0 | skipped 2
```

**Full regression:**

```
Ran 2533 tests in 113.791s
OK (skipped=19)
ran 2533 | failures 0 | errors 0 | skipped 19
```

2533 = 2475 baseline + 58 new. **No existing test was modified, retargeted, weakened or
deleted** — the refactor preserved behaviour closely enough that the existing suite,
including the M9-D.2 and M9-D.3 assertions that read `contract_mod.INTENTS`,
`query_mod.INTENT_TERMS` and `query_mod.SUBJECT_LEADS` directly, passed unchanged.

**Plugin validation:**

```
Validating marketplace manifest: .claude-plugin\marketplace.json
✔ Validation passed
```

## 10. Issues discovered

**One vacuous assertion, found and fixed during the work.** The first draft of the
candidate-claim regression test passed a proposal with `evidence_refs: [<url>]`. The engine
refused it as `untraceable` — proposals are traced by `evidence_id`, not by reference URL —
so `candidate_claims` came back empty and the loop asserting `verified: false` iterated over
nothing and passed. It was caught by inspecting the actual return value rather than trusting
the green result. The test now follows the M9-D.3 pattern: ingest once to obtain the real
`evidence_id`, then propose against it, and assert the claim list is non-empty before
checking its status.

**No stop condition was triggered.** Specifically: nine genuine identifiers and no alias;
no caller relying on undocumented semantics; query output behaviourally identical; no second
source of truth required; shared intents representable directly; no disclosure, scout,
evidence or claim change needed; no skill required a behavioural change; no security bypass
found; full regression restored without weakening anything.

**Pre-existing, not touched:** D-11 (ADR-0017 and ADR-0018 missing from both ADR indexes)
remains open. ADR-0021 was added to both indexes. Correcting the two earlier omissions is
still an unrelated documentation change and was left alone.

**Pre-existing, noted:** `biq/commands/query.py` defines an unrelated module-level `INTENTS`
for the `/ask-business-data` router. Untouched.

## 11. Decisions made

`docs/decisions/ADR-0021-research-intent-registry.md` — one immutable research-intent
registry replaces the flat intent tables.

Three sub-decisions inside it are worth surfacing here because they were judgement calls:

- **`BENCHMARK` carries no category.** It is the default intent of every `ResearchRequest`
  and `/retrieval-slice` issues it against `INDUSTRY`. Assigning it to `company`, `market`
  or `competitor` would have made the category table look complete while recording something
  the code does not do. Its `categories` field is empty and a test pins that.
- **A namedtuple, not a hand-frozen class.** `Destination` in `contract.py` earns its
  hand-written `__setattr__` freeze because it carries an approval identity. This record
  carries declared constants, so the stdlib's own immutable type is the simpler answer and
  leaves no freeze logic of ours to get wrong.
- **Derived views re-export the registry's own objects**, asserted with `assertIs` rather
  than `assertEqual`. Two structures that merely agree today are two sources of truth with a
  delay fuse.

ADR-0019 and ADR-0020 were **not** modified. Both recorded the right decision for their
milestone; ADR-0021 resolves the question they left open rather than overturning either.

## 12. Architecture changes

`architecture.md` Layer 2B gained a **"The research-intent registry"** subsection recording:
that `intents.py` is the single source of truth for intent metadata; what the four flat
structures were before; the category→intent table for all four categories including
`industry`'s deliberate emptiness; that shared intents are one identifier with several
categories rather than per-category twins; that `benchmark` is category-agnostic; that the
registry is metadata-only and calls nothing; and that its immutability is a security
property because intent metadata decides the query wording the gate assesses.

The existing paragraph above it was left intact apart from one word — "refused by
`ResearchRequest.validate()` before the gate sees it" now says *enumeration* rather than
*tuple*, since the tuple is now derived.

`reference/research-policy.md` was **not** changed: it describes disclosure tiers, source
tiers, recency and conflicts, and contains no description of intent architecture to correct.

## 13. Project-plan updates

- **Added:** "Research-intent registry consolidation" — `COMPLETED`, M9-D.4, recording
  ADR-0021 and stating the deferred intent-architecture decision is resolved.
- **Changed:** `/industry-research` renumbered from "M9-D.4+" to "M9-D.5+", since M9-D.4
  became the consolidation. Status stays `PLANNED`; the test asserting it does not exist is
  untouched.
- **Unchanged, deliberately:** every M9-D.3 row. `biq-competitor-analysis` stays
  `COMPLETED` and `/competitor-analysis` stays `REVIEW`. The prompt instructed that M9-D.3
  be kept closed, and promoting its command out of `REVIEW` is a separate decision belonging
  to whoever reviews its live smoke result.
- **Unchanged:** industry research, SWOT, strategy and decision support are not marked
  complete anywhere.

## 14. Documentation updates

`architecture.md`, `project_plan.md`, `docs/decisions/README.md`,
`docs/decisions/ADR-0021-research-intent-registry.md`, this record.

No skill, command, agent or reference document was touched.

## 15. Remaining work

**None for M9-D.4.** The completion criteria are met: one canonical registry, immutable and
read-only, nine identifiers with no duplicates, explicit company/market/competitor mappings,
shared intents still shared, query terms and representative query output unchanged, all three
analysis skills behaviourally unchanged, no retrieval/disclosure/scout/evidence/claim change,
focused tests passing, M9 passing, full regression passing, plugin validation passing,
documentation updated, ADR created, plan updated, no commit, no push.

**Confirmation of no behaviour change.** Four independent lines of evidence, none of which
rests on reading the diff and concluding it looks safe:

1. **The existing suite passed unmodified.** 2475 pre-existing tests, including M9-D.2's and
   M9-D.3's direct assertions on `INTENTS`, `INTENT_TERMS` and `SUBJECT_LEADS`, and their
   byte-for-byte company and market query pins. Not one was edited.
2. **Twelve queries pinned as exact strings**, spanning all three production skills and all
   nine intents — including the two the pre-existing suite did not pin.
3. **The derived views were diffed against the pre-refactor literals** before rewiring, and
   are asserted equal to literals restated in the test file rather than to whatever the
   registry happens to say.
4. **The suite was shown able to fail**, by mutation, on exactly the property that matters.

**Deferred, with the condition stated:** `industry` has no intent mappings. It is a valid
request category and always was; it gains its mappings when `/industry-research` is built, by
adding it to `ANALYSIS_CATEGORIES` and to the `categories` field of the intents it asks. If
that skill needs a question no existing intent expresses, it is one new record in one file —
which was the point of the consolidation.

**Not deferred so much as refused:** strategy and decision support get no category or intent
here. They are Layer 3 synthesis consuming evidence rather than retrieving it, and a
`recommendation` intent would put a class-7 capability behind a retrieval gate and imply a
recommendation is something a scout can fetch.

## 16. Git commit reference

**N/A — no commit.** The prompt forbade committing and pushing. Working tree on `main`,
uncommitted. Files created and modified as listed in sections 4 and 5; no other file in the
repository was touched.
