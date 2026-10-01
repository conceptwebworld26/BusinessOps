# ADR-0017 — The scout returns operation-bound line records, not an envelope

**Date:** 2026-09-13
**Status:** Accepted
**Supersedes:** the bare `biq.scout.result/1` **return contract** hardened by M9-C.1
(`docs/development/2026-09-11-m9c1-scout-return-contract-hardening.md`). That development
record is historical and is not rewritten. No earlier ADR is superseded.
**Relates to:** [ADR-0014](ADR-0014-retrieval-agent-ships-with-retrieval.md) (the scout ships
with retrieval), [ADR-0015](ADR-0015-model-mediated-scout-dispatch.md) (dispatch is
model-mediated; this decision changes only what comes *back*),
[ADR-0009](ADR-0009-comparative-intelligence-privacy-boundary.md) (the disclosure boundary,
unchanged), [ADR-0005](ADR-0005-seven-class-evidence-ledger.md) (provenance classes,
unchanged), [ADR-0016](ADR-0016-declared-conflicts-outrank-numeric-agreement.md) (untouched).
**Deciders:** Project owner, Claude (M9-C.15 adoption review)

## Decision

A research scout reply is **text containing one self-identifying line per record, followed by
exactly one terminator line**:

```text
BIQ-REC/1 <operation> {"reference": "https://…", "source": "…", …}
BIQ-END/1 <operation> <count>
```

This is the **single production-reachable scout return contract**. `parse_reply()` in
`lib/python/biq/research/scout.py` is the only entry point a production retrieval uses. Prose
around the record lines is ordinary content: it cannot break the reply and cannot become
evidence.

The `biq.scout.result/1` envelope is **retained as an internal representation only** —
`parse_reply` assembles one from the lines it accepted and hands it to `parse_result`, where
the echo, status and record-list checks already lived. A scout cannot send one: a reply is
text, and text is parsed as line protocol.

## Context — the problem that forced this

M9-C.1 required the scout's entire reply to be one bare JSON object, for a sound reason: if
arbitrary text may surround a JSON object, then choosing which object is the payload becomes a
trust decision made by pattern-matching, and a retrieved page can contain a JSON object of its
own. The contract was hardened in both document and behaviour, and the parser was never
loosened.

**Fourteen consecutive live replies violated it**, across M9-B, M9-C.5, M9-C.6 and M9-C.9 —
six then eight. In every single case the envelope *inside* the reply was correct and the
records were usable; what broke was the wrapper, because the model wrote a closing "Notes on
process:" that the contract could not survive. Each violation discarded the entire retrieval.

Three milestones then established that this was not fixable by instruction:

- **M9-C.7** found no runtime enforcement mechanism: no frontmatter field, no hook, nothing
  constrains a subagent's output shape. The contract is advisory to the model by construction.
- **M9-C.8** rejected parent-mediated extraction — pulling the envelope out of the prose —
  precisely because it reintroduces the pattern-matching trust decision M9-C.1 existed to
  avoid.
- **M9-C.9** showed the scout will actively *refuse* a prompt-embedded contract change, which
  is the M9-C.1 hardening working as a defence, and which means no output shape can be tested
  live without first shipping it in the trusted agent definition.

The choice was therefore between a contract the model reliably violates, and a contract shaped
to what the model reliably does.

## Evidence

**M9-C.13 — live validation** (`docs/development/2026-09-12-m9c13-fresh-session-biq-rec-trial.md`).
The protocol was shipped in the trusted definition and exercised in a genuinely fresh session.
Trial 1 was dispatched and reported alone as a registration check, then seven more:

- **8/8 observed compliance, 29 records.** Exact operation echo on every line, one terminator
  each with a correct count, valid single-line JSON throughout, zero reversions to the
  envelope, zero undocumented fields, zero `source_tier` fields, **zero manual repairs, zero
  retries**.
- **No fabricated publication date.** Eight absences, each declared; "Last Updated" banners
  were available and declined unprompted.
- **Adversarial trial passed.** A question deliberately retrieving X12/EDI specs and a page
  advertising JSON Schema and OpenAPI definitions produced **no forged protocol line**; the
  scout excluded an auto-generated page as tier D, named it in prose, and declined to
  fabricate a schema that is not published.

**M9-C.14 — deterministic path and zero-record semantics**
(`docs/development/2026-09-13-m9c14-zero-record-close-retrieval.md`). The complete gate-issued
path was verified with a real `ScoutBrief`: `ResearchRequest` → `gate.assess` →
`RetrievalRequest` → `ScoutBrief` → reply → parse → normalise → `close_retrieval` →
`EvidenceSet`, with the operation bound at every stage. It also established that the operation
id is **caller-supplied and gate-bound, not gate-minted**, and that both halves of a retrieval
re-derive from identical request parameters by design.

**M9-C.15 — this decision.** 61 new production-contract tests, plus the M9-C.9 (22) and
M9-C.14 (54) matrices retargeted at the shipped parser. 1933 tests pass.

## Alternatives investigated and rejected

| Alternative | Why rejected |
|---|---|
| **Keep the bare envelope, strengthen the wording** | Tried. The instructional half failed 14/14 live. M9-C.7 established there is no enforcement to add. |
| **Extract the envelope from surrounding prose** | Rejected by M9-C.8 and still rejected: choosing which span of untrusted text is the payload is exactly the trust decision that lets a retrieved page's own JSON be selected. |
| **Accept a fenced envelope** | Insufficient alone — every observed live reply carried prose *outside* the fence as well. |
| **Tool-mediated return with runtime schema validation** | No such mechanism exists for subagent output (M9-C.7). |
| **Dual production protocols** (accept both shapes) | Rejected in this milestone. Two reachable contracts means the authoritative one is ambiguous, the retired one keeps acquiring dependencies, and every future security argument has to be made twice. |
| **Surface "research unavailable" to the user and accept the loss** | Purely presentational; leaves the feature non-functional. |

## Why this protocol specifically

Three properties, and the third is the one that makes the first two safe:

1. **Prose becomes structurally harmless.** The model's strongest habit stops destroying
   retrievals, which is the entire observed failure mode.
2. **A line is self-identifying.** No span-selection decision is made: a line either begins
   with the exact token and this retrieval's operation id, or it is not a record.
3. **The operation id is a per-retrieval secret from the page's point of view.** It is minted
   by the caller, bound by the gate, and carried in the brief — so a page author, writing
   before the retrieval existed, cannot author a matching line. The declared count closes the
   remaining gap: a line copied verbatim out of a hostile page inflates the count the scout
   committed to, and a disagreeing count fails the whole reply.

## Security and provenance properties

Unchanged by adoption, and asserted by the regression floor:

- **Python owns every trust decision.** Operation identity, query binding, disclosure
  authorisation, source tier, provenance, freshness, evidence acceptance, conflict state and
  candidate/verified claim state are all computed locally. A record asserting `source_tier`,
  `trust`, `verified`, `freshness`, `may_stand_alone` or `operation` has those keys **dropped**,
  with the attempt recorded in a note so the forgery is visible rather than merely ineffective.
- **Tier is recomputed from source identity.** A blog claiming tier A classifies C inferred,
  cannot stand alone, and is refused as the sole support for a material claim.
- **No verified claim is reachable.** `CANDIDATE` is the only claim status; no constant naming
  a verified state exists.
- **Retrieved content is data.** Every item is marked `UNTRUSTED_EXTERNAL_DATA`; an instruction
  inside `content` is reported, never followed.
- **Dates are never invented.** An absent publication date stays absent and surfaces as
  `undated`.
- **The disclosure gate, the four-tier model and the k=5 privacy floor are untouched.**
- **The tool grant is untouched:** `WebSearch, WebFetch`.

## Zero-record semantics

`BIQ-END/1 <operation> 0` — a terminator whose declared count is zero, with no record lines —
means **the scout searched and found nothing citable**. It is the one state that reaches that
point in the parser, because a missing terminator and a disagreeing count are both refused
first.

It assembles an envelope carrying `RESULT_NO_SOURCE`, and `close_retrieval()` renders it as
`insufficient_evidence` / `no_adequate_source` with **`evidence: None`**. Nothing is
fabricated, no placeholder item is created, and no claim can be produced from it even when one
is proposed.

**It is absence of evidence, never evidence of absence.** A zero-record retrieval must never
be read as establishing that the proposition researched is false, and the failure explanation
deliberately asserts nothing of the kind. A retrieval failure uses the same empty shape, with
the reason given in the scout's prose.

## Fail-closed behaviour

Every one of these yields no records at all — never a partial set:

wrong operation · count mismatch (over or under) · missing terminator · duplicate terminator ·
malformed record JSON · a record that is not an object · non-integer count · a foreign
operation line mixed among valid ones · prose alone · a JSON envelope sent as text.
Undocumented fields are dropped; invalid provenance (an operation or query echo that does not
match the brief) is refused. Parsing never raises, on any input including `None`, integers,
bytes, lists and NUL bytes.

A structural refusal reports `unavailable` / `retrieval_unavailable` — a defect. An empty
result reports `insufficient_evidence` / `no_adequate_source` — a research answer. Keeping
those distinct is deliberate.

## How the superseded contract's coverage is preserved

M9-C.1's tests are **retargeted, not deleted**. `tests/unit/test_m9c1_bare_envelope_contract.py`
keeps its name and its two-directional structure — the document half and the behaviour half —
with every assertion re-pointed at the adopted contract and a header recording the supersession.
Where an assertion is no longer applicable because the protocol intentionally changed (prose is
now permitted), it is replaced by the strongest equivalent property for the new contract: that
prose cannot become evidence, that only a valid line for *this* operation is a record, and that
a violation salvages nothing. Tests were added, not removed: that file went from 38 to 42.

Three M9-B assertions and three M9-C.7 assertions were retargeted the same way. The M9-C.9 and
M9-C.14 matrices now drive the shipped parser and keep their original counts (22 and 54).

## Consequences

**Good.** Live retrieval becomes usable: the observed failure mode is gone by construction,
not by asking the model to suppress a habit. Prose is now a legitimate channel for process
notes, conflicts and blocked fetches, so the scout has somewhere to put what it previously put
in a place that destroyed the reply. One contract, one parser, one place to reason about the
boundary.

**Costs, accepted.** The protocol is BusinessIQ-specific and must be carried in the trusted
agent definition. A hostile page that induces an extra valid-looking line causes the whole
retrieval to fail rather than forging evidence — a fail-closed availability cost, deliberately
chosen over an integrity risk. And the canonical envelope remains in the codebase as an
internal structure, which is a small amount of indirection kept on purpose: it is where the
echo and status checks live, and moving them would have meant rewriting validation that
fourteen live failures never called into question.

**What adoption does not do.** It does not make external research *truthful*. It makes the
transport and the trust boundary reliable. Sources remain potentially wrong, stale,
conflicting, incomplete or low-quality, and BusinessIQ must continue to classify and validate
evidence after retrieval — which is what tiering, freshness, conflict recording and candidate
claims exist for.

## Rollback

The decision is reversible, and cheaply, because nothing downstream changed shape:

1. Restore the previous `agents/biq-research-scout.md` return-contract section (the pristine
   pre-adoption file is recorded by hash in the M9-C.13 and M9-C.14 development records:
   `04f0b30da8efcf4f4cf2644ee351dfd42d7d7f641c21ee2fc37d6d48b440d244`).
2. In `handoff.close_retrieval`, route text to `parse_result` instead of `parse_reply`.
3. Revert the retargeted assertions in the five test files named above.

`parse_reply` could then be deleted without touching normalisation, tiering, evidence
assembly, conflicts, claims or the gate — none of which this decision modified. What rollback
would *not* recover is the live evidence: 14/14 replies violated the restored contract, so
reverting reinstates a known-broken path and should only follow a replacement for it.
