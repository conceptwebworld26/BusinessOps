# ADR-0023 — An internal statement is defined by its provenance, not by its declared origin

**Date:** 2026-09-15
**Status:** Accepted
**Milestone:** M10.2-R
**Supersedes:** nothing. **Amends:** ADR-0022 (the domain constraint it describes was
necessary but not sufficient).

## Context

ADR-0022 established that the synthesis layer promotes nothing, and named the mechanism:
`EXTERNAL_KINDS` excludes `FACT` and `CALCULATION`, so *"external source wording never
becomes an internal fact — there is no kind for it to become."*

The M10.2 live verification showed that the mechanism did not hold, because the constraint
is evaluated against the **origin the caller declared**, not against the provenance the
statement actually carries. `SynthesisItem.__init__` computes `domain` from `origin` via
`DOMAIN_OF_ORIGIN`, then checks the kind against that domain. A caller naming
`ORIGIN_FINANCIAL` — an internal origin — while attaching a single `P_EVIDENCE` reference
passed every check and produced this, from live tier-C research-house evidence:

```json
{"kind": "FACT", "domain": "internal", "trust": "internal", "evidence_class": 1,
 "statement": "Our industry is USD 1,043.12 billion in 2026.",
 "provenance": [{"kind": "evidence", "ref_id": "ev-d8ac91afb7da"}]}
```

Class 1 is *measured from the user's own data*. Nothing downstream — SWOT, strategy,
decision support, executive reporting, all of which read this representation rather than
the upstream objects — could distinguish that item from a figure the engine computed from
the user's spreadsheet. The support grade (`partially_supported`, tier C only) and
confidence (`LOW`) did fire, so the item was visibly weak; but weak and *mislabelled about
where it came from* are different failures, and only the second one defeats the property
the whole layer exists to hold.

Three further facts shaped the remedy:

1. **No production merge helper could produce it.** `from_analysis_set`, `from_kpi_result`,
   `sourced_statement`, `interpretation` and `assumption` all attach provenance themselves.
   The hole was reachable only by constructing `SynthesisItem` directly — which is exported
   public API, and which is precisely what the M10 capabilities will do.
2. **The published JSON Schema admitted the record too**, so serialisation was not a second
   line of defence.
3. **The same hole existed for `CALCULATION`** (class 4), and materiality bought no
   protection: the material variant was accepted as readily as the non-material one.

## Decision

**A statement that asserts something about the business must rest on at least one
provenance reference that resolves, against this set's registries, to an internal source.
The declared origin is not evidence of anything.**

Concretely:

- `INTERNALLY_FOOTED_KINDS = (FACT, CALCULATION)` — the two kinds that read downstream as
  *this is true of us*. `SOURCED`, `INTERPRETATION` and `ASSUMPTION` are unaffected: they
  already say on their face that they are a quotation, a reading, or a model.
- `INTERNAL_PROVENANCE` is the complement of `EXTERNAL_PROVENANCE` within
  `RESOLVABLE_KINDS` — dataset, calculation, KPI, finding, forecast, anomaly.
  `P_UNAVAILABLE` is in neither, because provenance that asserts nothing cannot be footing.
- The check lives in `SynthesisSet.add()`, not in `SynthesisItem.__init__`, because
  **resolution needs the registries** and the item does not have them. An item alone cannot
  know whether `finding:financial.kpi.revenue` names anything real.
- The rule is *at least one* internal reference, not *only* internal ones. An item that
  genuinely rests on the user's data does not stop doing so because it cites a source
  alongside it.

### What is deliberately not consulted

`domain`, `origin`, `trust`, `evidence_class`, the caller's `confidence`, and any
`source_tier` carried on the cited object. Every one of those is caller- or
payload-influenced, and reading any of them would reintroduce the defect in a new place.
The only question asked is whether a reference points at an internal object **this set was
actually given**. Dressing an external chain as `P_FINDING` fails at the pre-existing
unresolved-reference check, which runs first.

### The schema mirrors the rule, and does not replace it

`lib/schemas/synthesis.schema.json` gains an `anyOf` on `definitions.item` expressing the
same constraint for records that never passed through the object model. This required
adding `contains` to `jsonschema_mini` — `items` would have demanded that *every* reference
be internal, which is a different and wrong rule.

**The runtime remains authoritative.** The schema is defence in depth for a hand-built or
transported record, and a schema constraint would have been the wrong primary control: it
validates output, and the whole point is to refuse the object at construction.

## Consequences

**Good.** The property ADR-0022 claimed is now enforced by the thing it is about. A
downstream capability cannot label external evidence as internal by choosing an origin
string, whatever else it declares. The failure is loud, at `add()` time, with a message
naming what was cited and what was needed.

**Cost.** `SynthesisItem` construction is no longer the whole validation story: an item is
valid only relative to a set. That is already true of provenance resolution, so it adds no
new concept, but it does mean a caller cannot fully validate an item in isolation.

**Accepted narrowing.** An internal `FACT` whose chain is genuinely unavailable can no
longer be recorded as a `FACT`. That is intended: a class-1 statement with no traceable
internal source is the exact shape this ADR exists to refuse. Such material belongs as an
`ASSUMPTION` with `ProvenanceRef.unavailable(reason)`, or as a limitation.

**Not addressed here.** This ADR governs where a statement's footing comes from. It does
not change support, confidence, materiality, conflict handling or the compatibility test,
and it introduces no path for recommendations — class 7 remains reserved.

## Verification

Regression tests carry the three M10.2 probes verbatim as
`test_live_shaped_escalation_*` in `tests/unit/test_m10_2r_provenance_footing.py`. They
must never be weakened: each one was accepted by the code before this decision.
