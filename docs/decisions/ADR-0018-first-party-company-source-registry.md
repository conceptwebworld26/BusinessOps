# ADR-0018 — First-party company sources are tier B, by explicit registry

**Date:** 2026-09-13
**Status:** Accepted
**Supersedes:** no ADR. It **amends the expectations** of M9-C.6 recorded in
`docs/development/2026-09-11-m9c6-tier-classifier-hardening.md` — specifically that
`microsoft.com` hosts classify tier C. That development record is historical and is not
rewritten; M9-C.6's security fix (label-boundary matching) is retained in full and reused
here rather than replaced.
**Relates to:** [ADR-0005](ADR-0005-seven-class-evidence-ledger.md) (provenance classes and
confidence, unchanged), [ADR-0009](ADR-0009-comparative-intelligence-privacy-boundary.md)
(the disclosure boundary, unchanged), [ADR-0016](ADR-0016-declared-conflicts-outrank-numeric-agreement.md)
(conflicts, unchanged), [ADR-0017](ADR-0017-operation-bound-line-records.md) (the scout
return contract — this decision also retires the last production reference to the contract
ADR-0017 superseded).
**Deciders:** Project owner (policy decision issued with M9-C.17), Claude (implementation)

## Context

M9-C.16's live verification retrieved Microsoft's own newsroom — `news.microsoft.com`,
carrying Microsoft's own reported FY2026 results — and the classifier returned
**tier C, `inferred=True`**: "we do not recognise this source."

That is wrong in a way with consequences, not merely an untidy label:

- the evidence set reported `support: unsupported`;
- a candidate claim on the company's own published revenue figure was **refused** with
  "Tier C corroborates but is never the sole support for a material claim";
- so the most direct available source for a fact about a company could not support a
  statement about that company.

The cause is that the recognised-source tables list authoritative bodies (tier A) and
established third-party press and research houses (tier B), and have no concept of a company
as a source **about itself**. Every company therefore fell to the unrecognised fallback.

The obvious repairs are all worse than the problem, which is why this needed a decision
rather than a patch.

## Decision

**A company's own domain is a recognised source at tier B, and recognition comes only from
an explicit registry held in code.**

`sources.FIRST_PARTY_COMPANY_DOMAINS` maps a registered domain to the company's name.
`classify_tier()` consults it **after** the tier A and tier B tables and **before** the
unrecognised fallback, matching with the existing `_matches_domain()` label-boundary rule.
A match returns `(TIER_B, "registered first-party company source (<domain>, <company>); primary
and attributable, but not independent, so never tier A", False)`.

### Why tier B and not tier A

Tier A in this system does not mean "accurate" or "close to the facts". It means
**independent of the subject** — a regulator, a statistical office, a central bank, a court
filing: a body with no stake in the number. A company is usually the *best-informed* source
about itself and simultaneously the *most interested* one, and those two properties do not
cancel out.

Tier B is exactly the right shape for that: *quotable with attribution and date*. It permits
"Microsoft's 29 July 2026 press release reported FY2026 revenue of $331.8 billion" and it
does not permit "Microsoft's FY2026 revenue was $331.8 billion" stated as independently
established fact. It also lets a first-party figure stand alone for a material claim, which
is the M9-C.16 gap closing, while leaving the attribution requirement that makes the claim
honest.

Promoting a company to tier A would mean a company's self-reported figures carried the same
authority as its regulatory filing. The filing is already tier A via `sec.gov`; the press
release should not be. **Tier A is not broadened by this decision.**

### Why an explicit registry and not a heuristic

Every heuristic considered hands the tier to whoever chooses a hostname, which is precisely
the M9-C.6 defect rebuilt with extra steps:

| Rejected | Why |
|---|---|
| "Any `.com` is a company, so tier B" | Promotes the entire commercial internet, content farms included. It is the substring defect with a longer pattern |
| "If the host matches the subject name, it is first-party" | The subject is caller-supplied text. A retrieval for "Acme" would promote `acme-reviews-blog.example`, and a hostile page could pick a name |
| "Trust the record's `source_type: press`" | The record is untrusted external data. A field a scout supplies cannot decide a tier; that is the attack `classify_tier` exists to prevent |
| WHOIS / DNS / certificate inspection | Requires the network. The engine has no network by design (ADR-0002), and a classifier that needs one cannot run at all |
| A bought or bundled company-domain database | A dependency, a refresh cadence, and a very large trusted surface, to solve a problem one table entry solves today |

An explicit table is deterministic, offline, auditable, explainable, and adds exactly the
trust a human deliberately put in it. Its cost — someone must add an entry — is the property
that makes it safe.

### Security requirements carried over from M9-C.6, unchanged

The registry reuses `_host()` and `_matches_domain()` rather than parsing URLs again, because
a second host parser is a second set of bugs. Therefore, unchanged and tested:

- a registered domain admits itself and its subdomains, and nothing else;
- `fake-microsoft.com`, `notmicrosoft.com`, `microsoft.com.evil.example`,
  `microsoft.example.com` and `evilnews.microsoft.com.example` are **tier C**;
- no unanchored substring matching exists anywhere in the classifier;
- URL credentials, ports, case, scheme, trailing root dot and IPv6 literals normalise first,
  so `https://news.microsoft.com@evil.example/` is a host in `evil.example` and gets nothing;
- tier D exclusion still runs **first** and still wins over every recognition table;
- a record's own `source_tier` is still not an accepted field: it is dropped and the attempt
  noted;
- tier is still recomputed locally from the reference URL on every ingestion.

### Scope

One entry: `microsoft.com`. Entries are added when a real retrieval shows one is needed,
never speculatively. This is a policy mechanism, not a company-domain catalogue.

## Consequences

**A documented live verdict changes, and this is the part to review.** M9-C.6 recorded that
the M9-C.5 Microsoft **TRENDS** evidence set correctly flipped `supported` → `unsupported`
once substring matching was removed. Under this decision that set reads `supported` again —
by explicit registry recognition rather than by the defect, but with the same observable
outcome.

For a claim *about Microsoft*, that is right and is the whole point. For a claim about **the
AI market** sourced from Microsoft's blog, it is weaker than it looks: the source is primary
about itself and merely interested about its market. The tier tables classify a *source*, not
a source-claim pair, so they cannot currently express that difference.

M9-C.6's own words were "a primary voice, but not an independent one", and that remains the
correct reading. What this decision changes is the tier that sentence maps to. **A claim-kind-
aware refinement — first-party evidence weaker for market and competitor claims than for
claims about the company itself — is a real open question and is deliberately not decided
here.** It is recorded as follow-up work, not as an implied consequence of this ADR.

Also:

- More retrievals will produce `support: supported`, so **confidence discipline in the
  skills matters more, not less**. Tier B has never meant verified, and nothing in the claim
  policy changed: a candidate claim is still `status: candidate`, `verified: false`, and no
  path produces a verified claim.
- Every classification remains explainable: the basis string names the registered domain and
  the company, so a report can say *why* a source was tiered, not just what it got.
- Rollback is one dictionary. Empty `FIRST_PARTY_COMPANY_DOMAINS` and behaviour is exactly
  M9-C.6's.

## The superseded-protocol cleanup, recorded here for completeness

M9-C.17 also removed `envelope_expected: biq.scout.result/1` from `open_retrieval()`'s
return. It was unconsumed, never reached a scout, and could not affect parsing — but
production output naming a contract ADR-0017 retired is a defect whatever reads it. The
`SCOUT_RESULT_ENVELOPE` constant is **kept**: it is still the internal canonical envelope
that `parse_reply()` builds and `parse_result()` validates. Nothing about `BIQ-REC/1` /
`BIQ-END/1` changed.
