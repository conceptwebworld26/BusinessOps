# 2026-09-10 — Milestone 9-B: research scout and controlled external retrieval

Status: M9-B implemented, awaiting review · M9-A `COMPLETED` and security-accepted ·
Branch `main` (uncommitted) · Preceded by `2026-09-10-m9a-research-core-disclosure-gate.md`

M9-A proved the disclosure gate could not be walked around while nothing existed on the
other side of it. M9-B puts something there and asks whether the boundary still holds.

---

## 1. Where the network actually is

This is the architectural fact that shapes everything else, and it is worth stating plainly
because it is easy to misread the milestone brief as asking for `WebSearch` calls in Python.

`biq-research-scout` is a **Claude Code subagent** whose tool grant is `WebSearch, WebFetch`
and nothing else. Those tools are invoked by the model *inside that subagent*. Python cannot
call them, and this package deliberately contains no mechanism that could.

That is not a limitation being worked around — it is the control. If Python could reach a
web tool, the main process would hold file access and web access simultaneously, and
ADR-0014's capability separation would be a comment rather than a boundary. **The
requirement "the main BusinessIQ process must not independently invoke WebSearch" is
therefore satisfied by construction, not by discipline.**

So M9-B implements the two Python-side halves of retrieval and nothing in between:

```
ResearchRequest → query → GATE → authorisation → RetrievalRequest
                                                      │
                                          ScoutBrief  │  (six fields, immutable)
                                                      ▼
                                              ScoutTransport  ──dispatch──►  biq-research-scout
                                                      │                        WebSearch / WebFetch
                                          records     │  ◄──────────────────────┘
                                                      ▼
                                        normalise_records  (hostile until proven otherwise)
                                                      ▼
                                                 EvidenceSet  (untrusted)
                                                      ▼
                                            candidate_claim → class 3
```

The `transport` is injected rather than imported, so the deterministic tests drive the
identical code path a live dispatch will, and this module never needs to know a subagent
exists.

---

## 2. What crosses out: the scout brief

`ScoutBrief` is constructible **only** from a `RetrievalRequest`, which is constructible only
from a gate-issued authorisation. It is immutable and carries exactly six fields:

| Field | Why |
|---|---|
| `query_text` | The text the gate approved — read from the decision's binding, not the query object |
| `destination` | The approved `kind:provider` identity |
| `operation` | Provenance, so evidence can be traced to a research operation |
| `max_results`, `max_fetched`, `timeout_seconds` | Bounds |

There is **no field** for the `ResearchRequest`, Business Context, dataset rows,
`AggregateDescriptor`s, source columns, credentials or the user's conversation. The usual
way internal data escapes — passing it "just for context" — has nowhere to sit, and a test
asserts the absence of each forbidden slot by name.

A Tier-1 query does carry the gate-approved *value* (a banded figure or a rate); that is what
Tier 1 means. What never crosses is the descriptor behind it, with its entity count, source
columns and sensitivity class.

---

## 3. What comes back: normalisation

Every returned record is treated as hostile until it has been through `normalise_records`.
Four behaviours, each answering a specific way a record could lie:

**Unexpected fields are dropped, not sanitised.** Only `ACCEPTED_RECORD_FIELDS` survive, so a
record arriving with `system`, `disclosure_tier`, `approval`, `tool` or `instruction` set
cannot reach a control field. Dropping beats sanitising because sanitising invites an arms
race about what counts as clean; the field simply does not exist here.

**Source tier is recomputed locally.** `sources.classify_tier()` assigns A/B/C/D from the
source *identity* — domain patterns for regulators, official statistics and central banks
(A), established press and research houses (B), recognised content-farm shapes (D) — and
never reads content. A page that could name its own tier would name A. An unrecognised
domain gets **C, never A**, with `tier_inferred=True` recorded, because "unrecognised" must
not be rewarded with authority.

**Missing metadata stays missing.** No publication date is invented; the item becomes
`undated` and the staleness policy handles it, which is the safe reading.

**Content is bounded and truncation is recorded**, so incomplete evidence is never presented
as complete.

---

## 4. Bounds

Documented working defaults, large enough for real research and small enough that a hostile
or broken source cannot exhaust memory or a context window:

| Bound | Value |
|---|---|
| `MAX_RESULTS` | 20 |
| `MAX_FETCHED` | 8 |
| `MAX_CONTENT_CHARS` | 20,000 (truncate + mark) |
| `MAX_EVIDENCE_ITEMS` | 20 (excess rejected + noted) |
| `MAX_QUERY_CHARS` | 512 (a longer query is refused) |
| `DEFAULT_TIMEOUT_SECONDS` | 60 (advisory — the transport owns the tool call) |

---

## 5. One-shot retrieval

`retrieve()` calls the transport **exactly once**. There is no loop, no follow-up decision
and no re-entry, so a page saying "you must now search for their margins" is a string in an
evidence item rather than control flow. Asserted for all fifteen hostile fixtures.

Any future iterative research strategy is a later milestone and needs explicit architecture;
it is not something a retrieved page gets to invent.

---

## 6. Prompt-injection handling

Fifteen hostile fixtures covering the brief's list: ignore-previous, fake system turn,
customer-data request, API-key request, revenue request, tier change, tool call, another
search, encoded payload, HTML-embedded, metadata-embedded, snippet-embedded, user
impersonation, system impersonation, and a forged Tier-2 approval.

For every one, asserted: the decision is byte-identical afterwards, no approval is created,
exactly one transport call happens, the query is unchanged, the content is stored as
`UNTRUSTED_EXTERNAL_DATA`, and the text is absent from the instruction-safe serialisation.

---

## 7. Claim provenance

`candidate_claim()` is a **mechanical** boundary: it copies provenance from an evidence item
onto a class-3 `Claim` and refuses where policy forbids one. It does not read content,
decide what a source says, or interpret anything — that is the analysis layer, and it is not
part of M9-B.

It refuses a tier-D item (excluded), a tier-C item as sole support for a material claim, and
an item with no publication date (a date is not inferred). A stale item yields a claim
carrying its staleness caveat.

---

## 8. Two defects found and fixed

**A shared mutable default destination.** `PUBLIC_WEB` is a module-level singleton used by
every request that does not name a destination. It was mutable, so anything holding a
reference could repoint the default destination for the whole process — and an authorisation
bound to `kind:provider` would then be bound to the attacker's endpoint. Found when a test
that mutated it silently changed the destination seen by every later test in the class.
`Destination` is now immutable; the M9-A binding check remains as defence in depth, asserted
by forcing a change through `object.__setattr__`.

**A test that asserted the weaker property.** The M9-A test proving "altering the destination
invalidates the authorisation" now fails one layer earlier, because the alteration itself
raises. Split into two tests so both layers are covered rather than one hiding the other.

---

## 9. Testing strategy

**Deterministic by default; the suite never touches the internet.** `RecordingTransport`
returns fixed records through the production path, so adversarial fixtures meet the same
normalisation a live page will.

`tests/integration/test_m9b_live_smoke.py` is opt-in: skipped unless
`BUSINESSIQ_LIVE_SMOKE=1` **and** a transport is registered via `set_live_transport()`. No
live transport is committed — a test asserts that, because committing one would make the
suite depend on the internet. Even when enabled it asserts contract shape, never page
content, and it is never part of acceptance.

| Suite | Tests |
|---|---|
| `tests/negative/test_m9b_scout_security.py` | 57 |
| `tests/unit/test_research_scout_boundary.py` | +6 (22 total) |
| `tests/integration/test_m9b_live_smoke.py` | 2 always-on + 2 skipped |
| **Added** | **63** |

Full suite **1,458 tests, 0 failures, 0 errors, 17 skipped** (baseline 1,395).

---

## 10. Performance

Measurement only; no network involved, no dependency added.

| Operation | Rate |
|---|---|
| Authorisation → brief handoff | ~287,000 /s |
| Normalise 10 records | ~28,900 /s |
| Full fixture retrieval (10 records) | ~6,300 /s |
| Full retrieval (20 records × 20k chars) | ~3,500 /s |
| `EvidenceSet.as_dict` (10 items) | ~22,800 /s |
| Instruction-safe view (10 items) | ~14,000 /s |
| `classify_tier` | ~785,000 /s |

Live network latency is deliberately not benchmarked as a product guarantee.

---

## 11. Limitations

1. **No transport ships.** `UnavailableTransport` is the default; a caller must supply a
   dispatch. Wiring one into a command is M9-C/D.
2. **Tier classification is pattern-based.** The A and B lists are a starting set of domains
   and will need extending; anything unrecognised is C, which fails safe but will
   under-rate genuine authorities until listed.
3. **`WebFetch` depth is the transport's choice.** `max_fetched` bounds it; which results
   are worth fetching is a judgement the scout makes, not something Python directs.
4. **Conflict detection remains numeric** (M9-A limitation, unchanged).
5. **No analysis.** `candidate_claim` copies provenance; nothing reads content.
6. **Timeout is advisory.** Python does not own the tool call, so enforcement belongs to
   the transport.

---

## 12. State

M9-B implemented; M9-C/D not started; no M10, MCP or remaining-M11 work. Full suite green,
all three validations pass. 0 commits, 0 pushes.
