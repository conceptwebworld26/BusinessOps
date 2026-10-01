# ADR-0024 — One retrieval assembly, two closers: the `EvidenceSet` reaches synthesis as an object

**Date:** 2026-09-15
**Status:** Accepted
**Milestone:** M10.2-R

## Context

`synthesis.register_external()` accepts only an `EvidenceSet` **object** and refuses a
serialised one, deliberately (ADR-0022): *"a dict would arrive carrying `source_tier` as
data, and the whole point of local tiering is that a tier is something BusinessIQ derives
from a source's identity rather than something it is told."*

`close_retrieval()` — the public end of the M9 retrieval path — returns
`evidence.as_dict()`. `EvidenceSet` has no `from_dict`, and correctly so: rebuilding a set
from its own serialisation is the exact operation that would let a tier travel as payload.

The two decisions are each right and together left no public path. The M10.2 verification
needed the object and had to get it by constructing a `ResearchRequest`, calling
`gate.assess`, building a `RetrievalRequest`, and driving `ScoutRetriever` with a transport
of its own — a second assembly of the same pipeline, in a verification harness, diverging
from production the moment either changed. ADR-0012 forbids exactly that: one rule, one
home.

The M10 capabilities all read the synthesis representation. Every one of them will need
this path.

## Decision

**`close_retrieval_object()` returns the live `EvidenceSet` under `evidence_set`. Both
public closers delegate to one private `_close()`, so there is one assembly and the two
cannot disagree.**

```
completed retrieval → close_retrieval_object(...)["evidence_set"] → synthesis.register_external(...)
```

- `close_retrieval()` is unchanged in contract: same keys, same shapes, still
  `json.dumps`-able. It now calls `_close()` and serialises the result.
- `close_retrieval_object()` returns the same result with `evidence_set` (the object) in
  place of `evidence` and `instruction_safe`.
- The success result carries **no** `evidence` key. A key that is sometimes a record and
  sometimes a live object is a key nobody can serialise safely; a caller that wants the
  record calls the other function.
- Failure and refusal results are returned unchanged by both.

Nothing else moves. Same parsing, same operation binding, same `BIQ-REC/1` / `BIQ-END/1`
contract, same local tiering, same freshness, same conflict transport, same candidate-claim
policy, no new transport, no new network behaviour, no scout change.

## Consequences

**Good.** The verification harness and the production path are now the same code. Local
tier derivation, the untrusted-trust boundary, evidence ids, freshness and declared
conflicts all reach synthesis intact because they are never serialised on the way.
`register_external()` keeps refusing dicts, which remains the control that matters.

**Cost.** Two public closers instead of one, and a caller must pick. The alternative —
returning the object under the existing `evidence` key — would have broken every caller
that serialises the result, including the skills that print it.

**Not a widening.** The seam carries evidence *in*; it grants no standing once there.
Registering an `EvidenceSet` still creates zero statements, and tier-A evidence arriving
through it still cannot found an internal `FACT` or `CALCULATION` (ADR-0023).
