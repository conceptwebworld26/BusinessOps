# 2026-09-11 — M9-C.6: source-tier classifier hardening

**Milestone:** 9 — External Intelligence & Disclosure Gate (M9-C.6)
**Status on completion:** `COMPLETED`
**Supersedes:** None. Remediates the defect recorded in
`docs/development/2026-09-11-m9c5-live-company-analysis.md`. **M9-C.5 keeps its historical
`APPROVED WITH LIMITATIONS` verdict** — the live run found the defect, and rewriting that
outcome would erase the finding that produced this milestone.

---

## 1. Prompt / task performed

Implement M9-C.6 — harden `sources.classify_tier()` so recognised domains match with safe
hostname/domain-boundary semantics, closing the substring self-promotion vector the M9-C.5
live verification exposed. Inspect first; stop and report if the recognised-source
representation cannot express domain boundaries. Preserve local tier authority, keep the
classifier deterministic and offline, add no DNS/WHOIS/network or LLM classification, do not
broaden the Tier-A trust model silently, weaken no existing test. Document the matching
rules, make the ADR decision explicit, dated record, plan update for M9-C.6 only. No commit,
no push.

## 2. Root cause

`classify_tier()` matched with `pattern in host` — unanchored substring containment.

```python
for pattern in TIER_A_PATTERNS:
    if pattern in host:                 # <- the defect
```

A tier is a trust statement, and the entire reason it is assigned locally is stated in the
code's own comment: *"the whole point of tiering is that a content farm cannot promote
itself."* Substring containment defeated exactly that. Anyone able to choose a hostname could
choose a tier, with no page content, no scout assertion and no injection required.

Every wrongly-elevated host also reported `inferred=False` — the system believed it had
**recognised** the source, so nothing downstream could tell the difference.

### A second cause the live report had not identified

Four `TIER_A_PATTERNS` entries were never domains at all: `eurostat`, `edgar`, `statistics`,
`centralbank`. These are bare keywords with **no safe boundary reading**. `statistics`
promoted any host containing the word — `my-statistics-blog.example` scored tier A — and
`centralbank` promoted `centralbanking.com`, a trade publication. Fixing only the matcher
would have left these as dead configuration or, worse, kept them matching by substring.

## 3. Changes made

### Inspection

| Question | Finding |
|---|---|
| What does the classifier receive? | A full URL or bare host; `_host()` already normalises. No new URL architecture needed |
| Can the configuration express boundaries? | **Yes.** Entries are domains (`reuters.com`) or namespaces (`.gov`) — both expressible. **Except** the four keyword fragments, which cannot |
| Do tests pin the old behaviour? | No test called `classify_tier` directly. Fixture hosts are `reuters.com`, `www.reuters.com`, `sec.gov`, `ons.gov.uk`, `www.gov.uk` — all legitimate, all retained |
| Does tier D use the same matcher? | No, and deliberately left alone — D matches host **and** source name by substring. Broad matching is safe in the exclusion direction |

No architectural gap. The smallest safe change was a boundary matcher plus removal of the
four unconfigurable fragments.

### Implementation

1. **`_matches_domain(host, pattern)`** — the whole fix. Strips a leading dot, then
   `host == domain or host.endswith("." + domain)`. A namespace needs no special case: after
   stripping, `.gov` gives exactly the hosts ending in a `gov` label.
2. **`_host()` hardened** — now also strips credentials (`user:pw@host`, taking the authority
   after the **last** `@`), an explicit port, IPv6 brackets, and a trailing root dot.
3. **`classify_tier()`** — the two elevation loops call `_matches_domain`. Tier D unchanged.
4. **Four keyword fragments removed** from `TIER_A_PATTERNS`, with the reasoning in the
   docstring.

### Matching semantics, before and after

| Host | Before | After |
|---|---|---|
| `reuters.com`, `www.reuters.com`, `business.reuters.com` | B | **B** (unchanged) |
| `fake-reuters.com`, `notreuters.com` | **B** | **C** |
| `reuters.com.evil.example` | **B** | **C** |
| `sec.gov`, `www.sec.gov` | A | **A** (unchanged) |
| `sec.gov.evil.example`, `my.gov.not-official.com` | **A** | **C** |
| `microsoft.com`, `news.microsoft.com` | **B** (via `ft.com`) | **C** |
| `soft.com`, `draft.com`, `aircraft.com` | **B** | **C** |
| `notimf.org` | **A** | **C** |
| `my-statistics-blog.example`, `centralbanking.com` | **A** | **C** |
| `ec.europa.eu/eurostat`, `www.sec.gov/Archives/edgar` | A | **A** (unchanged) |
| `randomblog.example/reuters.com/story` | C | **C** (unchanged) |

**Nothing legitimate lost.** Eurostat is under `.europa.eu`, EDGAR under `sec.gov`, the
national statistics offices under `.gov` / `.gov.uk` — all still listed, all still tier A.

## 4. Files created

- `tests/negative/test_m9c6_tier_boundary.py` — 39 tests
- `docs/development/2026-09-11-m9c6-tier-classifier-hardening.md` — this record

## 5. Files modified

| File | Change |
|---|---|
| `lib/python/biq/research/sources.py` | `_matches_domain()`; `_host()` hardened; two loops switched; four fragments removed |
| `reference/research-policy.md` | New *How a source is recognised* subsection |
| `architecture.md` | Label-boundary paragraph in *Source tiering, recency, conflicts* |
| `project_plan.md` | M9-C.6 status |

No change to scout permissions, disclosure gates, candidate-claim policy, conflict
behaviour, or any skill or command.

## 6. Files deleted

None.

## 7. Features implemented

No feature. A security correction plus the tests and documentation that keep it.

## 8. Tests performed

```bash
PYTHONPATH=lib/python python -m unittest tests.negative.test_m9c6_tier_boundary
PYTHONPATH=lib/python python -m unittest tests.unit.test_m9a_research_core \
    tests.unit.test_m9a_invariants tests.unit.test_m9b_candidate_claims \
    tests.unit.test_m9b_scout_contract tests.unit.test_m9c1_bare_envelope_contract \
    tests.unit.test_m9c2_advisory_guard_wording tests.unit.test_m9c3_company_analysis \
    tests.unit.test_m9c4_conflict_transport tests.unit.test_m9_governance \
    tests.negative.test_m9a_adversarial tests.negative.test_m9a_gate_forgery \
    tests.negative.test_m9b_scout_security tests.negative.test_m9c6_tier_boundary
python tests/run_tests.py
```

## 9. Test results

**Focused — 39 tests, all passing:**

```
Ran 39 tests in 0.002s
OK
```

| Class | Tests | Covers |
|---|---|---|
| `TestLiveAttackExamples` | 9 | Every hostname M9-C.5 showed elevated: hyphenated, prefix and suffix lookalikes; recognised domain as a left label; `.gov` mid-hostname; the Microsoft case; hosts merely ending in a recognised domain; the four removed fragments; and that a rejected lookalike reports `inferred=True` rather than "recognised" |
| `TestLegitimateSourcesKeepTheirTier` | 9 | Exact domain, `www.`, nested subdomain, each namespace; Eurostat and EDGAR still reachable via their real domains; recognised sources not marked inferred; **every configured pattern matches its own domain and its `www.` subdomain**; no pattern is a bare keyword |
| `TestHostNormalisation` | 9 | Case; trailing root dot; explicit port; credentials; a recognised domain in the userinfo; path/query/fragment cannot promote; optional scheme; malformed and empty input; IP literals |
| `TestUnchangedBehaviour` | 8 | Tier D exclusion, including matching on source name and beating a recognised domain; unknown domains still C and inferred; **source name cannot promote**; injected text cannot promote; deterministic; no network library reachable |
| `TestTheLiveRegressionCase` | 4 | The Microsoft TRENDS set is now all tier C and **`unsupported`**; the PROFILE set keeps its genuine tier A and stays `supported`; Microsoft's own pages are vendor pages |

**All M9 suites — 601 tests, all passing.** No existing test was weakened or modified; the
fixture hosts were already legitimate forms.

**Full regression — 1,764 tests, all passing:**

```
Ran 1764 tests in 428.431s
OK (skipped=19)
ran 1764 | failures 0 | errors 0 | skipped 19
```

Baseline 1,725 at M9-C.5; +39 is exactly this task. **Skips unchanged at 19.**

One focused test failed during development and was corrected: I had asserted that every
configured pattern contains a dot, which wrongly condemned the legitimate single-label
namespaces `.gov`, `.mil` and `.edu`. The invariant I actually wanted — every entry is a
domain **or** an explicit namespace — is what the test now asserts. The assertion was
corrected; the configuration was not.

## 10. Issues discovered

**The defect was wider than M9-C.5 reported.** The live run found the matcher; inspection
found the four keyword fragments, which were a second, independent promotion vector.

**Impact on existing tier assignments** — the live regression case, now asserted by test:

| M9-C.5 evidence set | Before | After |
|---|---|---|
| PROFILE | `supported` — on a genuine `sec.gov` tier A | `supported`, unchanged and for the right reason |
| TRENDS | `supported` — **on two mis-tiered `microsoft.com` pages** | **`unsupported`** |
| POSITIONING | `unsupported` | `unsupported`, unchanged |

So one live research verdict flips, which is the correct outcome: Microsoft writing about
Microsoft is a primary voice but not an independent one, and a set with no independent
source does not adequately support a material claim.

**A policy question deliberately not answered here.** The shipped configuration treats the
whole `.gov`, `.mil`, `.edu` and `.ac.uk` namespaces as elevated, not merely the named hosts
within them. M9-C.6 **preserved that trust model exactly** — the brief said not to broaden it
silently, and narrowing it silently would be the same error in the other direction. With
boundary matching those namespaces now mean what they appear to mean (registry-controlled
zones), which is defensible. Whether `.edu` should confer tier B on any university host is a
policy question for the owner, not a security fix.

## 11. Decisions made

**No ADR, and the determination was made explicitly rather than by omission.**

Against the bar in `docs/decisions/README.md`: the security property this restores was
already the documented intent, in `reference/research-policy.md`, in ADR-0009, and in the
classifier's own comment — *"a content farm cannot promote itself."* No new decision was
taken about what the policy should be; the implementation simply did not match it. The bar's
exclusion list names **bug fixes** explicitly, and no contract, invariant, layering rule or
component boundary moved.

The one genuine judgement call — removing four tier-A keyword fragments — is recorded in §3
rather than in an ADR, because it was forced by the fix rather than chosen: a bare keyword
has no safe boundary reading, so keeping it would have meant keeping substring matching for
those four entries, which is the defect. It narrows the trust model in the safe direction and
loses nothing legitimate.

**If the owner reads the trust-model narrowing as architectural rather than remedial, an ADR
should follow this record.** That is a reasonable reading and I am flagging it rather than
deciding it unilaterally.

## 12. Architecture changes

`architecture.md` gained a paragraph in *Source tiering, recency, conflicts* stating that
recognition is by DNS label boundary, naming the rejected forms, and recording that
classification is local, deterministic and offline.

## 13. Project-plan updates

M9-C.6 scope only: a new `COMPLETED` row for the classifier hardening, and the M9-C.3 and
M9-C.5 rows annotated to point at the remediation. **M9-C.5's `APPROVED WITH LIMITATIONS`
verdict is preserved**, as instructed — the limitation is now marked remediated rather than
rewritten away.

## 14. Documentation updates

`reference/research-policy.md` (the owning policy document for source tiering) gained a
*How a source is recognised* subsection with the admits/refuses table, the normalisation
rules and the offline guarantee. Plus `architecture.md`, this record, and the plan rows.

## 15. Remaining work

1. **Re-verification of the M9-C.5 live result is not required** — the regression is asserted
   deterministically in `TestTheLiveRegressionCase`, from the real hostnames that run
   returned. A fresh live retrieval would add nothing this does not already prove.
2. **Owner policy question:** whether whole-namespace elevation for `.gov`, `.mil`, `.edu`
   and `.ac.uk` is intended. Unchanged by this task.
3. **The three sibling skills** — market, competitor, industry — and **M9-D**, the four
   external commands. Neither started.

## 16. Git commit reference

N/A. Branch `main`, no commit created, nothing staged, nothing pushed.

---

## The rule now enforced

A recognised entry admits **the domain itself and its subdomains, and nothing else**:

| Configured | Admits | Refuses |
|---|---|---|
| `reuters.com` | `reuters.com`, `www.reuters.com`, `business.reuters.com` | `fake-reuters.com`, `notreuters.com`, `reuters.com.evil.example` |
| `.gov` | `sec.gov`, `www.bls.gov` | `sec.gov.evil.example`, `my.gov.not-official.com` |

Hostnames are normalised first — scheme, credentials, port, path, query, fragment, trailing
root dot, case. Path and query cannot promote. Every entry must be a domain or an explicit
namespace; bare keywords are not configurable. Tier D exclusion still matches broadly,
including on the source name, because it only ever removes trust. The classifier remains
local, deterministic and offline, and a test asserts no network library is reachable from it.

**Final status: `M9-C.6 COMPLETED`.**
