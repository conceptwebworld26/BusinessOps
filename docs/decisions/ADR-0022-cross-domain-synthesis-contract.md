# ADR-0022 — One synthesis contract, built from existing vocabularies, that promotes nothing

**Date:** 2026-09-14
**Status:** Accepted
**Milestone:** M10.1

## Context

Milestone 10 delivers four capabilities — `biq-swot`, `biq-strategy-recommendations`,
`biq-decision-support`, `biq-executive-report` — and all four need the same thing before
they can do anything useful: a set of statements drawn from both information domains, each
knowing what kind of statement it is, what it rests on, how far the evidence supports it,
and what could not be established.

Built independently, each of the four would have to answer the same questions for itself:
*may this internal figure be compared with that external one; does a tier C source support
a headline; what happens to confidence when two sources disagree; is a candidate claim a
fact yet.* Four implementations of those answers is four chances to get one wrong, and the
one that gets it wrong is the one that ships a fabricated comparison in an executive
summary — the most condensed and most-forwarded artifact in the system, and therefore the
worst place for a provenance failure to surface.

The material already exists and is well-specified. M1–M8 produce `AnalysisSet`,
`AnalysisFinding`, `KPIResult`, `ForecastSet`, `AnomalySet`, `Limitation` and
`MaterialityVerdict`. M9 produces `EvidenceSet`, `EvidenceItem`, locally-derived source
tiers, freshness verdicts, declared conflicts and candidate claims. `evidence.Ledger` has
held the seven provenance classes since ADR-0005. What does not exist is anything that
holds material from both domains at once, and the reason that gap is dangerous rather than
merely inconvenient is that **joining the domains is exactly where promotion happens**: an
external estimate quietly becoming a fact, a candidate claim quietly becoming a finding, a
tier C blog quietly becoming support, a source's advice quietly becoming our
recommendation.

## Decision

**One package — `lib/python/biq/synthesis/` — is the canonical intermediate representation
for cross-domain synthesis. It composes the existing contracts, adds exactly one new
statement kind, and contains no code path that raises the standing of anything.**

Five parts of that decision are load-bearing.

### 1. Vocabulary is reused, not restated

| Concept | Owner | Synthesis does |
|---|---|---|
| Statement kinds `FACT` / `CALCULATION` / `INTERPRETATION` / `ASSUMPTION` | `analytics.contract` | imports them |
| Provenance classes 1–7 | `evidence` | imports the class map |
| Source tiers, staleness, support adequacy, numeric conflict | `research.sources` | calls it |
| Declared conflicts | `EvidenceSet` + ADR-0016 | lifts them |
| Materiality thresholds and verdicts | `materiality` + config | carries the verdict across unchanged |
| Confidence values `HIGH` / `MEDIUM` / `LOW` | `evidence` | imports them |
| Advisory-language markers | `research.handoff` | imports the list |

The synthesis layer re-derives none of these. In particular it **does not re-judge
materiality**: a finding arrives with the verdict the configured policy already produced,
and a second threshold table in a second module would be a second policy by ADR-0012's
test, whichever one a reader happened to find first.

### 2. One new statement kind: `SOURCED`

The analytics contract has four kinds because internal analysis has no fifth case. Once
external material is in the same set, it needs one: *a named public source said this*.
That is evidence class 3, which the ledger has carried since ADR-0005 and which
`evidence.Claim.label` already spells `SOURCED`. The synthesis layer adopts that spelling
rather than minting `EXTERNAL_FACT`.

The kind is then **constrained by domain**, and that constraint is the whole mechanism
behind "external wording never becomes an internal fact":

- an external statement may be `SOURCED`, `INTERPRETATION` or `ASSUMPTION`;
- an internal statement may be `FACT`, `CALCULATION`, `INTERPRETATION` or `ASSUMPTION`.

There is no kind for external material to become a fact *as*. The defence is the absence of
a representation, not a check someone has to remember to run.

### 3. Support is a four-state view of M9's three-state policy

Downstream consumers need to distinguish *we checked and the evidence is too weak* from
*nothing was linked, so we could not check*. `research.sources.assess_support()` returns
three verdicts; the synthesis layer maps them and adds the fourth:

| M9 verdict | Synthesis state |
|---|---|
| `supported` | `supported` |
| `corroboration_only` | `partially_supported` |
| `unsupported` | `unsupported` |
| *(no resolvable provenance at all)* | `insufficient_evidence` |

This is a **view**, not a second policy: the tier rules are still M9's, and
`SUPPORT_FROM_TIER_ASSESSMENT` is the whole of the translation.

**A statement citing both domains takes the weaker of its two legs.** A statement resting
on internal computation and an external source is a cross-domain statement, and it is only
as good as its weaker half; taking the better half would let a tier C blog ride into a
report on the back of a correctly computed internal number.

### 4. Provenance is resolved, not trusted

Every reference names an object the set was actually given. A reference to an id nobody
registered raises rather than annotating, and the registries only accept typed objects —
`EvidenceSet`, `AnalysisSet`, `KPIResult` — never their serialised forms. A serialised
evidence set would carry `source_tier` as data, and a tier is something BusinessIQ derives
from a source's identity, never something it is told.

Where provenance genuinely does not exist it is stated as `unavailable` **with a reason**,
which grades the statement `insufficient_evidence`. Silence is not an option the
representation offers.

### 5. Recommendations are representable and unproducible

`RECOMMENDATION` is a reserved kind that the item contract refuses to construct, and the
serialised result carries a `recommendations` array that is always empty with a note saying
why. Downstream milestones will fill it through `evidence.Claim`, which already demands all
six class-7 fields.

The advisory-language guard closes the other half: a statement matching
`handoff.ADVISORY_MARKERS` is refused whatever kind it claims, so advice cannot enter as an
interpretation and be read back downstream as advice. The marker list is imported from M9
rather than copied, so the two guards cannot drift apart.

## Alternatives considered

**Let each M10 capability read the upstream objects directly.** Rejected: it is the
four-implementations problem above, and it puts the comparability rule — the single most
dangerous judgement in the system — in four places at once.

**Extend `AnalysisSet` to carry external evidence.** Rejected: `AnalysisSet` means *what
one analytical domain produced for one dataset*, and its `add()` deliberately refuses
anything but `FACT` and `CALCULATION`. Loosening that to admit untrusted external material
would weaken a boundary M6 established, to serve a consumer it was never meant to have.

**Store a `verified` flag defaulting to false.** Rejected, and the reasoning generalises: a
field exists to be set. With no verification path in the system, the only thing a
`verified` field could hold is a forgery, so the contract refuses the flag on arrival
instead of carrying it.

**Let conflicting figures be reduced when the sources agree closely.** Rejected —
ADR-0016 already settled that a declared conflict outranks numeric agreement, and in
sizing, two sources agreeing to within 5% on incompatible boundaries is coincidence rather
than corroboration. The synthesis layer therefore has no `resolve()`, no midpoint, and no
tier-weighted winner: a higher tier makes a source more attributable, not more correct.

## Consequences

**Good.**
The comparability rule, the support rule and the promotion boundary exist once and are
tested once. A downstream capability that wants to compare an internal figure with an
external one has exactly one way to try, and it refuses more often than it agrees. "Where
did this statement come from" is answerable from data, through `chain()` and
`provenance_index()`, without reading model reasoning.

**Costs, accepted.**
The weakest-leg rule will occasionally grade a sound cross-domain interpretation more
harshly than a human would, because one cited tier C corroborator drags the whole statement
down. That is the intended direction of error. The advisory-marker guard inherits M9's
false positives — a sentence containing "must " is refused even where it is descriptive —
which is a known and deliberate over-refusal, not a defect to tune away here.

`SOURCED` means the synthesis kind list is not identical to the analytics one, so a reader
who knows `analytics.contract` meets one unfamiliar member. The alternative was letting
external material share the `FACT` label, which is the failure this milestone exists to
prevent.

**Not decided here.** How SWOT, strategy, decision support and executive reporting *use*
this representation; what a class-7 recommendation looks like when M10.2 issues one; and
whether a live internal-plus-external analysis flows end to end, which needs a vertical
slice against real retrieval rather than deterministic fixtures.

## References

- ADR-0005 (seven-class evidence ledger) · ADR-0009 (disclosure boundary) ·
  ADR-0012 (component placement) · ADR-0016 (declared conflicts outrank numeric agreement) ·
  ADR-0018 (first-party company sources)
- `architecture.md` §7.5 The synthesis layer
- `reference/evidence-ledger.md`, `reference/materiality-policy.md`,
  `reference/research-policy.md`
- `lib/schemas/synthesis.schema.json`
