# 2026-09-10 — Milestone 9-A: external research core, disclosure gate and evidence contracts

Status: M9-A implemented, awaiting review · M8 `COMPLETED` · M9 `IN PROGRESS` (9-A of 9-A…D)
· Branch `main` (uncommitted) · Preceded by `2026-09-10-m9-owner-decisions.md`

The first implementation sub-milestone of M9. It builds the path an external question
travels and the gate that stands in it. **No retrieval is implemented**: there is no network
call anywhere in the new code, and no research skill or command exists.

---

## 1. Architecture

One path, and no way around it:

```
ResearchRequest ──► QueryBuilder ──► DISCLOSURE GATE ──┬─► REFUSE  (+ Tier 0 alternative)
                                                       ├─► ALLOW_WITH_APPROVAL ──► Approval
                                                       └─► ALLOW
                                                              │
                                              RetrievalRequest│  (constructible only here)
                                                              ▼
                                                          Retriever ──► EvidenceSet
                                                                            │
                                                                            ▼
                                                                      Claim ledger
```

The ordering is not a convention anyone has to remember. `RetrievalRequest.__init__` takes
a `DisclosureDecision` and nothing else — no constructor accepts a string, a
`ResearchRequest` or a `CandidateQuery` — and it raises on a refused or unapproved
decision. A caller who wants to retrieve must hold the gate's output, so "did the gate run?"
cannot be got wrong by forgetting.

### Package layout

```
lib/python/biq/research/
    contract.py       ResearchRequest, Destination, Approval, ResearchFailure
    query.py          CandidateQuery, deterministic construction, Tier 0 alternative
    gate.py           DisclosureDecision, assess(), record_disclosure(), ledger_entry()
    retrieval.py      RetrievalRequest, Retriever, NullRetriever, FixtureRetriever
    evidence_set.py   EvidenceItem, EvidenceSet, the untrusted-data boundary
    sources.py        tiers A–D, staleness windows, conflict representation
lib/schemas/
    evidence_set.schema.json
    claim_ledger.schema.json
```

### Reuse, not reimplementation

| Needed | Reused from | Not rebuilt |
|---|---|---|
| Sensitivity classes, class→tier, `most_sensitive` | M3 `privacy/classes.py` | No second taxonomy |
| k-floor, banding, re-identification, `assess_disclosure` | M3 `privacy/aggregation.py` | **No second privacy policy** |
| Cross-query accumulation | M9 governance `DisclosureAccumulator` | — |
| Approval | M1 `errors.ConsentRequiredError`, the `consent_request()` shape | No second approval subsystem |
| Claims and the ledger | M6 `evidence.py`, seven classes | No second evidence model |
| Externalizable Business Context fields | M1 `context/privacy.py`, schema `x-privacy` | No second classification |

The gate supplies what a *query* has that an aggregate does not — a destination, an
approval, an operation and the text that would actually be transmitted — and defers on
everything else.

---

## 2. Contracts

**`ResearchRequest`** carries subject, category, intent, purpose, public terms, derived
context (as `AggregateDescriptor`s), requested tier, destination, approval, operation and
source requirements. The shape is the control: there is no field a raw row, a customer name
or a ledger can occupy, and `validate()` refuses one that arrives anyway. Categories are
`company`, `market`, `competitor`, `industry` — one core, parameterised, so the four future
skills do not each implement a request type.

**`Destination`** names the provider and kind. Only `public_web` is permitted in M9; an
MCP-connected source is Milestone 12 and is refused here. Approval binds to
`kind:provider`, so approving a query for one destination does not authorise another.

**`Approval`** is single-use and bound to the exact text and destination. `matches()` fails
for a different query, a different destination, an ungranted approval or a spent one.

**`ResearchFailure`** is a value, not an exception: status, machine-readable reason code,
human explanation, and whether a safe alternative exists. Eleven failure states are
defined, covering retrieval unavailable, source unavailable, insufficient evidence,
ambiguous source, ambiguous tier, blocked disclosure, approval required, stale-only
evidence, conflicting evidence, invalid provenance and unsupported category.

---

## 3. Query construction

Deterministic: terms are emitted in a fixed order (`TERM_ORDER`) rather than dictionary
order, so the same request builds the same string byte for byte and an audit record can be
reproduced. `build()` returns a `CandidateQuery` — deliberately not a string, so it cannot
be mistaken for something retrieval will accept.

The builder decides nothing. It assembles a candidate and reports what that candidate would
disclose; whether it may be sent is the gate's decision. The caller's assertion that
something is safe is not an input to it.

`tier_zero_alternative()` builds the query that answers the same question without internal
values, and does so from **prohibition-filtered** terms — a refusal that explained itself by
printing the API key it had just declined to send would leak through the very message meant
to protect (see Security findings).

---

## 4. Disclosure gate

`gate.assess()` is the one authoritative decision, returning `ALLOW`,
`ALLOW_WITH_APPROVAL` or `REFUSE`. Order:

1. **Structural validity** — prohibited content, unsupported category, unresolved
   sensitivity, invalid tier. Refused before the privacy layer sees the request, because
   some contents must not be inspected at all.
2. **Destination** — an unpermitted provider is refused rather than attempted.
3. **Tier 0** — no derived context means nothing internal is transmitted, so there is
   nothing to assess. Checked before the aggregate machinery, because running an aggregate
   assessment over an empty list would invent a verdict.
4. **Per-value assessment** — each descriptor goes through `assess_disclosure`, which
   already joins the class→tier rule to the four ADR-0009 checks and now also takes the
   operation's accumulator.
5. **Escalation or refusal** — a Tier-1 failure escalates to Tier 2 *unless* what failed can
   never be approved (`never`-classified data, unresolved sensitivity, or a k-floor breach),
   in which case there is no path and the refusal says so.

Ambiguity resolves **upward in strictness**: an uncertain tier becomes the stricter one, an
unresolved sensitivity refuses, an unknown destination refuses.

`ledger_entry()` records the decision and the text, including refusals — a reviewer needs to
see what was *not* sent as much as what was. `transmitted_text` is null unless the
disclosure was actually authorised.

### Tier behaviour

| Tier | Behaviour |
|---|---|
| **0** | Default. Built only from public terms; the comparison is computed locally. All four ADR-0009 examples pass with no approval prompt. A Tier 0 request carrying derived context is **refused, not promoted**. |
| **1** | Every disclosed value must independently pass: class permitted at Tier 1, k ≥ 5, banded not exact, whole-query re-identification including accumulated state. Passing the four checks is necessary, not sufficient. |
| **2** | Explicit, single-use, per-query, per-destination approval via the existing `ConsentRequiredError` / `consent_request()` shape. Never session-wide, never inferred. |
| **3** | No approval path. `never`-classified data, credentials, customer names, transactions and raw ledgers are refused, with the Tier 0 alternative offered and the prohibited value never echoed. |

---

## 5. Evidence, sources, staleness, conflicts

**Evidence is untrusted by construction.** `EvidenceItem.trust` is a read-only property
fixed at `untrusted` — there is deliberately no `TRUSTED` constant, since nothing promotes
external text and a constant naming that state would exist only to be misused.
`as_instruction_safe_dict()` omits the raw content entirely and is the serialisation
anything assembling context should read; `EvidenceSet.add` refuses an item that tries to
populate an instruction, policy, tool or authorisation field, rather than sanitising it —
sanitising invites an arms race about what counts as clean.

**Source tiers** A/B/C/D from the research policy. A and B may stand alone; C corroborates
only and is `unsupported` as sole support for a material claim; D is excluded and cannot
become a claim at all. A tier is never inferred when evidence is insufficient —
`normalise_tier(None)` raises.

**Staleness** uses the policy's windows: financials 365 days, market sizing 730, positioning
545; an unknown claim kind gets the *shortest* window, so unclassified material ages fastest
rather than slowest. `as_of` is a parameter rather than `today()`, so the result is
deterministic and a fixture asserts a fixed answer. Stale evidence is **kept and labelled**,
never discarded — it is evidence of what was true then.

**Conflicts** are represented, never resolved: every position kept whole with source, tier,
date, definition and scope; spread reported; confidence lowered; a likely reason stated only
when the positions themselves show one (differing definitions, scopes or years). Nothing is
averaged — averaging two market sizes produces a third number nobody published.

---

## 6. Security invariants

All fifteen are asserted in `tests/unit/test_m9a_invariants.py`, named after the invariant
so a failure report names the guarantee that broke.

| # | Invariant | Held by |
|---|---|---|
| 1 | No retrieval before the gate | `RetrievalRequest` accepts only a `DisclosureDecision` |
| 2 | No raw internal data reaches retrieval | `PROHIBITED_KEYS`, collection-valued term refusal, retriever sees only cleared text |
| 3 | Tier 0 transmits no internal value | No derived context ⇒ no value in the query |
| 4 | Tier 1 needs class permission **and** every check | `assess_disclosure` joins both |
| 5 | Tier 2 needs explicit single-use approval | `Approval.matches` + `spend()` |
| 6 | Tier 3 has no approval path | `_unapprovable()` refuses before escalation |
| 7 | k < 5 never passes | `resolve_k_floor` hard minimum |
| 8 | Unresolved sensitivity never passes | `UNRESOLVED` fails closed |
| 9 | External content cannot alter the decision | Decision immutable; nothing re-reads it |
| 10 | Class-3 claims need provenance | `Claim` validation (M9 governance step) |
| 11 | Tier-D cannot become a claim | Excluded in both `sources` and `evidence` |
| 12 | Tier-C cannot solely support a material claim | `assess_support(material=True)` |
| 13 | Cross-query narrowing is caught | `DisclosureAccumulator` through the gate |
| 14 | Approval cannot be reused | Bound to text + destination, single-use |
| 15 | Retrieval rejects an unapproved request | `RetrievalRequest` raises |

---

## 7. Tests

| Suite | Tests | Covers |
|---|---|---|
| `tests/unit/test_m9a_invariants.py` | 57 | The fifteen security invariants |
| `tests/unit/test_m9a_research_core.py` | 65 | Request, query, tiers, staleness, conflicts, evidence, failures, determinism |
| `tests/negative/test_m9a_adversarial.py` | 34 | Exfiltration, privacy bypass, hostile content, approval abuse, evidence abuse, gate ordering |
| **Added** | **156** | |

Full suite: **1,353 tests, 0 failures, 0 errors, 17 skipped** (baseline 1,197). No existing
test was weakened or modified.

Adversarial fixtures cover eight hostile page shapes — direct override, fake system turn,
fake developer turn, tool invocation, second-retrieval request, policy override, encoded
payload and HTML comment — each asserted not to change the tier, trigger a second
retrieval, create an approval, or reach an instruction-safe view.

---

## 8. Performance

Measurement only; no optimisation performed. Stdlib only, no new dependency.

| Operation | Rate |
|---|---|
| Gate, Tier 0 (small) | ~217,000 /s |
| Gate, Tier 1 (1 descriptor) | ~123,000 /s |
| Gate, Tier 1 (10 descriptors, medium) | ~24,500 /s |
| Gate, Tier 1 with accumulator | ~115,000 /s |
| Query build (small) | ~336,000 /s |
| 50 records → `EvidenceSet` | ~1,900 /s |
| Conflict over 6 positions | ~201,000 /s |

The gate is far cheaper than the retrieval it guards, so there is no incentive to skip it.

---

## 9. Security findings

**One real defect, found by a test in this milestone and fixed.** The Tier 0 alternative
offered alongside a refusal was built from the original request's public terms — including
the prohibited one. A request carrying `api_key: sk-live-…` was correctly refused, and the
refusal's alternative query then contained the key. The value would have been echoed in the
very message meant to protect it. Fixed by `query.safe_public_terms()`, which strips
prohibited keys and collection-valued terms before the alternative is built; asserted by
`test_a_refusal_does_not_echo_the_value_it_refused` and, across twelve exfiltration shapes,
by `test_no_refusal_echoes_the_value_it_refused`.

---

## 10. Known limitations

1. **No retrieval.** `NullRetriever` is the default and returns `retrieval_unavailable`.
   Live retrieval and the scout integration are M9-B.
2. **`FixtureRetriever` is for tests only.** It takes the production path deliberately, so
   adversarial fixtures exercise real handling, but it must never be wired into a command.
3. **Conflict detection is numeric.** Two prose claims that contradict each other are not
   detected as a conflict; only comparable figures are.
4. **The 20% conflict threshold is a convention**, not a measured value. It separates a
   rounded restatement from a genuine disagreement and may need tuning against real sources.
5. **Re-identification remains heuristic** (R-07, unchanged), now with the accumulation
   improvement from the governance step.
6. **No skill or command consumes this core yet** — by design; M9-B onward.
7. **`public_terms_from_context()` is untested against a live Business Context** because no
   caller exists yet; it reads the M1 helper rather than reimplementing classification.

---

## 11. State

M9-A implemented; M9-B/C/D not started; no M10, MCP or remaining-M11 work. Full suite green,
all three validations pass. 0 commits, 0 pushes.


---

# Targeted security audit — 2026-09-10 (gate-authorisation integrity)

Appended after the M9-A record above. Where it contradicts a claim made earlier in this
document, **the audit is authoritative**.

## Finding: the claimed invariant did not hold

Section 1 above states that because `RetrievalRequest.__init__` accepts a
`DisclosureDecision` and nothing else, "retrieval cannot be constructed without a gate
decision". That was true and close to worthless. Requiring a **type** is not requiring a
**provenance**, and the type was publicly constructible.

Six routes reached the retriever with a payload containing named customers, an exact
monetary level and an API key. Each was executed against the repository, not reasoned about:

| # | Route | Result before the fix |
|---|---|---|
| 1 | `DisclosureDecision(ALLOW, …)` constructed directly | retrieval ran |
| 2 | `object.__new__` to skip `__init__` | retrieval ran |
| 3 | Mutating `decision.query.text` after assessment | retriever saw the substituted text |
| 4 | `decision.decision = ALLOW` on a refusal | refusal flipped to ALLOW |
| 5 | `decision.approval = Approval(..., granted=True)` | self-granted approval accepted |
| 6 | Mutating `RetrievalRequest.query_text` after construction | retriever saw the substituted text |

One earlier claim did hold: `Retriever._fetch` receives only `(query_text, destination)`,
so the retriever genuinely cannot reach the request, Business Context or descriptors.

## Fix

Three mechanisms, none cryptographic, all inside the existing architecture.

**Gate-issued.** `DisclosureDecision.__init__` requires a module-private issuance
capability, and a module-private `_issue()` helper is the only thing that registers a
decision in a `WeakSet`. Registration is deliberately **separated from construction**: if
both lived in `__init__`, obtaining the capability would be enough to mint an object the
registry vouches for. Split, an attacker needs the capability *and* write access to the
registry — two deliberate acts against two named private controls, at which point they are
editing the module rather than calling it, which no design defends against.

**Immutable.** `__setattr__` and `__delattr__` raise once issued. `authorise()` is the one
controlled write, validates before it writes, and reaches through `object.__setattr__`;
`approval` is a read-only property.

**Bound.** The exact text, destination identity and tier assessed are captured at issue.
`query_text` returns the bound text rather than whatever the query object now says, and
`binding_intact` re-checks before every authorisation. Mutating a `CandidateQuery` no longer
changes what may be sent — it invalidates the authorisation, which is the safe direction.

`RetrievalRequest` now checks exact type (not `isinstance`, which a subclass satisfies),
registry membership, refusal, binding and authorisation, and is itself frozen.
`Retriever.retrieve()` re-verifies at the point of use rather than trusting construction.

One behavioural tightening: a `ResearchRequest.approval` is no longer auto-attached by the
gate. Approval must go through `authorise()`, which matches ADR-0010's "explicit" and broke
no existing test.

## Verification

All nine routes re-tested after the fix, including capability theft and serialised reload:
**every one blocked, and the retriever was invoked zero times across all attacks.**

42 tests added in `tests/negative/test_m9a_gate_forgery.py`, each named for the route it
closes. Full suite **1,395 tests, 0 failures, 0 errors, 17 skipped** — no existing test was
weakened or modified.

## Residual

Python has no enforceable privacy. A caller who imports `_ISSUE` *and* writes to `_ISSUED`
can still mint an authorisation — but that is indistinguishable from editing `gate.py`, and
no in-language mechanism prevents it. What the fix removes is every route reachable through
the **public API**, which is what "structural" can honestly mean here.
