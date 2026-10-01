# 2026-09-13 — M9-C.17: first-party source registry and superseded-contract cleanup

**Milestone:** M9-C.17 — First-party source registry + superseded contract cleanup
**Status on completion:** `COMPLETED`
**Closes:** the M9-C.16 limitation that a company's own domain classified tier C inferred,
and the M9-C.16 observation that `open_retrieval()` still advertised the retired envelope.

---

## 1. Objective

Two tightly scoped changes, no new capability:

- **Part A** — stop production output naming the scout return contract ADR-0017 superseded.
- **Part B** — recognise legitimate first-party company sources at the correct tier, through
  a principled, secure mechanism rather than a Microsoft-shaped patch.

No live retrieval was performed. No command was implemented. Nothing was committed.

## 2. Part A — stale contract cleanup

`open_retrieval()` returned `envelope_expected: scout.SCOUT_RESULT_ENVELOPE`
(`biq.scout.result/1`) — the bare-envelope contract M9-C.15 retired.

**Consumer search before removal**, across `lib/`, `tests/`, `commands/`, `skills/`,
`agents/`, `reference/`, `config/`, `evals/` and `lib/schemas/`: the only production emitter
was `handoff.py:119`. Nothing read it, no test asserted it, no JSON schema required it, and
it is not one of `ScoutBrief`'s six fields, so it never reached a scout and could not affect
parsing (`close_retrieval` routes on payload type). Stop condition 4 therefore did not apply.

**Removed, not re-pointed.** Advertising the *new* protocol would have added a production
surface nobody asked for; the scout's return contract lives in `agents/biq-research-scout.md`
and ADR-0017, and `close_retrieval` enforces it. The docstring now records what the field was
and why it went, so the removal is not silently reversible.

**`SCOUT_RESULT_ENVELOPE` is kept.** It is still the internal canonical envelope
`parse_reply()` builds and `parse_result()` validates — exactly the thing M9-C.15 said to
preserve. Only the advertisement went.

**Other references audited, none removed:** `agents/biq-research-scout.md` names
`biq.scout.result/1` exactly once, as the format *not* to send (a test pins that count at
one, and the scout contract was out of scope anyway). ADR-0017 and the M9-C.1/C.15/C.16
development records describe the supersession as history and are untouched.

## 3. Part B — the first-party company registry

### The gap

M9-C.16 retrieved `news.microsoft.com` — Microsoft's own newsroom carrying Microsoft's own
reported FY2026 results — and the classifier returned **tier C, `inferred=True`**: "we do not
recognise this source". The set read `support: unsupported`, and a candidate claim on the
company's own published revenue was refused as "never the sole support for a material claim".

The tables knew authoritative bodies and third-party press. They had no concept of a company
as a source **about itself**, so every company fell to the unrecognised fallback.

### What was added

`sources.FIRST_PARTY_COMPANY_DOMAINS` — a map of registered domain → company name, and
`FIRST_PARTY_TIER = TIER_B`. `classify_tier()` consults it **after** the tier A and tier B
tables and **before** the unrecognised fallback, matching with the existing
`_matches_domain()` label-boundary rule. Ordering is deliberate: placing it last among the
recognised tables means it can never raise a source that already qualifies as authoritative
or as established press, and placing it before the fallback is the entire fix.

A match returns `inferred=False` and an explainable basis:

```
registered first-party company source (microsoft.com, Microsoft Corporation);
primary and attributable, but not independent, so never tier A
```

**One entry: `microsoft.com`.** A policy mechanism, not a catalogue. No second entry was
added, because none is currently justified by a real retrieval; genericity is proved by a
test that iterates every registry entry rather than by padding the table.

### Why tier B, and why a registry — ADR-0018

Recorded in full in `docs/decisions/ADR-0018-first-party-company-source-registry.md`: tier A
means *independent of the subject*, and a company is simultaneously the best-informed and
most interested source about itself; tier B ("quotable with attribution and date") is exactly
that shape. Five heuristic alternatives were considered and rejected, each because it hands
the tier back to whoever chooses a hostname — which is the M9-C.6 defect rebuilt. **Tier A
was not broadened.**

### Security properties, all reused rather than rewritten

No new URL parsing was written; `_host()` and `_matches_domain()` are used as they stand,
because a second host parser is a second set of bugs. Verified by test:

| Input | Result |
|---|---|
| `microsoft.com`, `www.`, `news.`, `blogs.`, `ir.` | **B**, recognised |
| `fake-microsoft.com`, `notmicrosoft.com` | **C**, inferred |
| `microsoft.com.evil.example`, `microsoft.example.com`, `evilnews.microsoft.com.example` | **C**, inferred |
| `about-microsoft.com`, `microsoft.co`, `microsoftonline.example`, `mymicrosoft.com`, `microsoft.com-login.example` | **C** |
| `https://news.microsoft.com@evil.example/` | **C** — the authority is `evil.example` |
| `https://user:pw@news.microsoft.com/`, `:8443`, trailing root dot, upper case | **B** — normalisation first |
| `[::1]`, `[2001:db8::1]` | **C**, unchanged |
| `sec.gov`, `ons.gov.uk`, `federalreserve.gov`, `ec.europa.eu` | **A**, unchanged |
| `reuters.com`, `ft.com` | **B**, unchanged; `fake-reuters.com`, `sec.gov.evil.example` still **C** |
| `apple.com`, `acmelogistics.com`, `someco.io` | **C** — absence from the table is the answer |
| tier D patterns, including on a registered host | **D** — exclusion still runs first and wins |

Tier remains recomputed locally from the reference URL on every ingestion. `source_tier` is
still not an accepted record field: a record asserting one has it dropped and the attempt
noted. A record claiming to be Microsoft while pointing at `fake-microsoft.com` classifies C.
Retrieved content instructing the engine to add a domain to the registry changes nothing —
asserted by test.

## 4. The one consequence that needs owner review

**A documented live verdict flips back.** M9-C.6 recorded that the M9-C.5 Microsoft
**TRENDS** evidence set correctly moved `supported` → `unsupported` once substring matching
was removed. Under ADR-0018 that set reads `supported` again — by explicit registry
recognition rather than by the defect, but with the same observable outcome.

For a claim *about Microsoft* that is right and is the point. For a claim about **the AI
market** sourced from Microsoft's own blog it is weaker than it looks: the source is primary
about itself and merely interested about its market. The tier tables classify a *source*, not
a source-claim pair, so they cannot express that difference today.

M9-C.6's own sentence — "a primary voice, but not an independent one" — remains correct; what
changed is the tier it maps to. **A claim-kind-aware refinement is a real open question and
is deliberately not decided here.** It is recorded as follow-up, not implied by this ADR.
This is flagged rather than buried because it is the only place where implementing the
mandated policy weakens a property an earlier security milestone established.

## 5. Test changes

**Added:** `tests/negative/test_m9c17_first_party_registry.py` — **45 tests** covering all
thirty requirements: registry basics, spoofing/lookalike protection, boundary and credential
/port/case/trailing-dot/IPv6 regression, tier A and D unchanged, registry integrity against
self-promotion and against retrieved content, the Part A cleanup, and evidence-policy
invariance.

**Retargeted, not deleted:** `tests/negative/test_m9c6_tier_boundary.py`, **39 → 42 tests**.
Four assertions pinned `microsoft.com` → tier C and had to move, because test requirement A.3
of this milestone (`news.microsoft.com` → tier B) targets exactly one of those hosts — the
supersession is intended, not incidental. **No spoofing assertion was touched**; all 35 other
tests in the file pass unchanged. What replaced them:

| Was | Now |
|---|---|
| `test_the_microsoft_case_that_started_this` asserted tier C | Asserts the **basis**: `microsoft.com` is never admitted by `ft.com` and never reads "secondary source". Plus a new `test_the_substring_route_that_caused_it_is_still_closed` over four unregistered lookalikes |
| `test_every_source_in_that_set_is_now_tier_c` | Asserts each tier comes from a **named local reason**, the two first-party hosts are B and recognised, the unrelated third party is still C and inferred |
| `test_the_set_is_no_longer_adequately_supported` | Split: a **new** test proves a set of only unrecognised sources is still `unsupported` (the coverage that assertion existed for), and a retargeted test states the flip explicitly and proves it rests on the registry entry by removing it |
| `test_the_vendor_pages_...` asserted tier C | `test_microsoft_on_microsoft_is_primary_but_never_independent` keeps the sentence and asserts the **ceiling**: B, and never A. Plus a generic test that no registry entry can reach tier A |

The file's docstring records the amendment and lists exactly which assertions moved.

Net coverage **grew** by 48 tests. Nothing was weakened to make anything pass.

## 6. Test results

```
$ python tests/run_tests.py
Ran 1981 tests in 109.710s
OK (skipped=19)
ran 1981 | failures 0 | errors 0 | skipped 19
```

Focused: `negative.test_m9c17_first_party_registry` **45** OK ·
`negative.test_m9c6_tier_boundary` **42** OK.

All eighteen other M9 modules pass at their M9-C.16 counts, unchanged:
`test_m9c15_production_protocol` 61 · `test_m9c9_shape_experiment` 22 ·
`test_m9c14_zero_record_and_full_path` 54 · `test_m9c1_bare_envelope_contract` 42 ·
`test_m9b_scout_contract` 62 · `test_m9c7_return_contract_boundary` 16 ·
`test_m9c3_company_analysis` 60 · `test_m9c8_handoff_provenance` 11 ·
`test_m9c4_conflict_transport` 53 · `test_m9_governance` 46 · `test_m9a_adversarial` 34 ·
`test_m9a_gate_forgery` 43 · `test_m9a_invariants` 57 · `test_m9a_research_core` 65 ·
`test_m9b_candidate_claims` 36 · `test_m9b_scout_security` 57 ·
`test_m9c2_advisory_guard_wording` 12.

```
$ claude plugin validate . --strict
Validation passed
```

## 7. What did not change

`BIQ-REC/1` / `BIQ-END/1`, `parse_reply()`, `parse_result()`, `normalise_records()`, the
scout agent definition, the disclosure gate, Tier 0/1/2/3 semantics, the k=5 floor, freshness
windows, conflict handling, the advisory heuristic, candidate-claim verification policy,
`SOLE_SUPPORT_TIERS`, tier D exclusion, and the canonical internal envelope. No MCP server, no
crawler, no company-domain database, no new command.

## 8. Limitations and deferred items

1. **Claim-kind-aware first-party weighting is not implemented** — section 4. The open
   question this milestone surfaced and did not answer.
2. **Registry of one.** `microsoft.com` only. Every other company's own domain is still tier
   C, so the M9-C.16 symptom will recur for the next company researched until an entry is
   added. Growth is deliberate and manual.
3. **No live verification.** Forbidden by this milestone's scope. The deterministic tests
   prove classifier behaviour; a fresh-session live run would only re-prove transport.
4. **Tier A namespace question (R-11) is untouched** and remains open.
5. **More sets will read `supported`**, so confidence discipline in the skills carries more
   weight than before. Tier B has never meant verified, and no claim policy changed.

## 9. Next milestone

**M9-D — `/company-analysis` command.** Not started here. The claim-kind-aware refinement in
section 4 should be put to the owner before or alongside it.

## 10. Git commit reference

N/A — no commit, no push, as instructed. Branch `main`, all changes uncommitted.
