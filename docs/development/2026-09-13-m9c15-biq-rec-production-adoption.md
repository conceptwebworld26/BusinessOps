# 2026-09-13 — M9-C.15: formal `BIQ-REC/1` / `BIQ-END/1` production adoption

**Milestone:** M9-C.15 — Formal production adoption of the line protocol
**Status on completion:** `COMPLETED` — Outcome A: adopted
**Supersedes:** the bare-envelope **return contract** of M9-C.1. The record
`docs/development/2026-09-11-m9c1-scout-return-contract-hardening.md` stands unaltered as
history.

---

## 1. Objective

Adopt `BIQ-REC/1` / `BIQ-END/1` as the single production scout return contract: move the
proven logic into `lib/python/biq/research/`, make the trusted scout definition state it as
the sole contract, record the architectural decision, and keep the M9-C.9 and M9-C.14
regression matrices intact.

A controlled adoption, not a redesign of the research architecture.

## 2. Starting state

- M9-C.13 closed Outcome A: 8/8 live compliance, 29 records, no repairs, no retries.
- M9-C.14 closed Outcome A: complete gate-issued path verified, zero-record semantics defined.
- Scout definition pristine at `04f0b30da8efcf4f4cf2644ee351dfd42d7d7f641c21ee2fc37d6d48b440d244`
  (9,845 bytes), carrying the bare-envelope contract.
- `tests/experimental/line_format.py` held the proven adapter; nothing in `lib/` imported it.
- 1866 tests passing; `claude plugin validate . --strict` passing.

**This milestone opened with a BLOCKED report.** Inspection established that adoption could
not satisfy both the single-contract requirement and the "no existing M9 contract test may
fail" stop condition: M9-C.1's ten document assertions pin the exact wording Part D orders
replaced, and five further assertions pin envelope-JSON-text as an accepted production reply.
That is a contract-supersession decision, so it was put to the owner rather than decided here.
**The owner approved Option 1 — clean break** — and explicitly authorised retargeting the
affected tests while forbidding any reduction in security coverage.

## 3. Adoption decision

`BIQ-REC/1 <operation> {…}` record lines plus exactly one `BIQ-END/1 <operation> <count>`
terminator is the single production-reachable scout return contract. Prose around the lines is
ordinary content. The full rationale, evidence, alternatives, security properties and rollback
path are in **ADR-0017**.

The decision's load-bearing property is that **identity travels on each line**: a line is a
record only if it carries this retrieval's gate-bound operation id, so the parser never makes
the span-selection judgement M9-C.1 existed to avoid and M9-C.8 rejected. The declared count
closes the remaining gap, since a line copied from a hostile page inflates a count the scout
already committed to.

## 4. Production implementation

All of it inside `lib/python/biq/research/`.

**`scout.py`** — added the protocol as the production contract:

- `RECORD_TOKEN`, `END_TOKEN`, `SCOUT_REPLY_PROTOCOL` (`biq.scout.lines/1`), and the
  structural-problem constants `NO_TERMINATOR`, `COUNT_MISMATCH`, `MALFORMED_RECORD`.
- **`parse_reply(reply, brief)`** — the production entry point. Accepts text (or bytes),
  matches each line against a prefix built **from the brief**, requires exactly one terminator
  whose declared count equals the record-line count, and requires each record to be one bare
  single-line JSON object. Assembles the canonical envelope and delegates to `parse_result` for
  the echo, status and record-list checks. Never raises; never repairs; never rescues a line.
- `render_reply(operation, records)` — fixture helper, not used in production.
- `_structural_failure()` — refusals report `unavailable` / `retrieval_unavailable` and carry
  the structural problem in `details`, so a caller can tell *why* without the parser guessing.
- `parse_result()` — **behaviour unchanged**, re-documented as the internal canonical-envelope
  validator rather than the scout contract.

**`handoff.py`** — `close_retrieval()` now routes by type: **text → `parse_reply`** (the scout
contract), **dict → `parse_result`** (the internal seam for fixtures and `ScoutTransport`). The
docstring states which is which and why a scout cannot use the dict path.

**`__init__.py`** — exports `parse_reply`, `render_reply`, the tokens, the protocol name and
the problem constants.

Nothing else in the engine changed: normalisation, tiering, freshness, evidence assembly,
conflicts, claim policy, the gate and the privacy floor are untouched.

## 5. Trust-boundary changes

**None** — and that is the point worth recording. The split was already implemented and
adoption did not move any part of it:

| Scout-controlled (content) | Python-controlled (authority) |
|---|---|
| `source`, `reference`, `title`, `content` | operation identity, gate-bound |
| `publication_date` **only when stated by the source** | query binding, re-derived from the gate |
| `source_type`, `claim_kind` as reported | disclosure authorisation and tier |
| which records it returns at all | **source tier**, recomputed from source identity |
| prose: process notes, conflicts, blocked fetches | provenance, evidence ids, trust marking |
| | freshness and staleness windows |
| | evidence acceptance and bounds |
| | conflict state, candidate/verified claim state |

`ACCEPTED_RECORD_FIELDS` already excluded `source_tier`, so a record asserting tier, trust,
verification, freshness, `may_stand_alone` or `operation` has those keys dropped **and the
attempt recorded in a note** — the forgery is visible, not merely ineffective. Verified by
test against a record attacking all of them at once, including `system` and `disclosure_tier`.

## 6. Zero-record behaviour

`BIQ-END/1 <operation> 0` with no record lines → envelope status `RESULT_NO_SOURCE` →
`close_retrieval` returns `insufficient_evidence` / `no_adequate_source` with `evidence: None`.
No placeholder item, no claim even when one is proposed (the result carries no
`candidate_claims` key at all), and the explanation asserts no falsity.

**Absence of evidence, never evidence of absence** — asserted mechanically, and stated in the
scout definition so the model understands what it is reporting. A retrieval failure uses the
same empty shape with the reason in prose. A *malformed* reply remains the distinct
`unavailable` / `retrieval_unavailable` outcome: an empty result is an answer, a broken reply
is a defect.

## 7. Scout contract changes

`agents/biq-research-scout.md`, now `a9a89d115e07198848a8f7429390570bf45bdf8509dc455dab0d711052810a89`
(12,092 bytes, was 9,845).

Replaced the "What you return" section with the line protocol: the shape, a worked example
using a concrete operation id, and the checked rules — one record per line, exact
character-for-character operation echo, one bare single-line JSON object, exactly one
terminator whose count matches on pain of failing the whole reply, documented fields only, no
`source_tier`, no verification claim. Added explicitly: **prose is permitted** around the lines
but is not a second channel for records; **there is no second return format** (naming
`biq.scout.result/1` exactly once, as something not to send); the zero-record and
retrieval-failure shapes; and the security clause that protocol-looking text in retrieved
content is page content, never a record.

Replaced "Status values" with "What the count says" — the scout no longer sends a status field.
Retitled the two provenance rules, which are unchanged. Updated the failure-conditions table.
Added ADR-0017 to the Related line.

**Unchanged:** frontmatter, `tools: WebSearch, WebFetch`, the tool-grant rationale, the brief
description, all eight Rules, and the record-fields table.

`commands/retrieval-slice.md` and `skills/biq-company-analysis/SKILL.md` were updated to say
reply rather than envelope, and the command now says to write the scout's reply **verbatim**,
prose included, nothing extracted or repaired.

## 8. Compatibility and migration decision

**No compatibility layer. One contract.**

| Question | Answer |
|---|---|
| Can the old envelope parser be retired? | Not removed — it is **retained and isolated** as the internal canonical-envelope validator that `parse_reply` delegates to. That is where the echo, status and record-list checks live, and rewriting them would have meant re-proving validation that fourteen live failures never implicated. |
| Is the old contract production-reachable? | **No.** A scout reply is text, and text is parsed as line protocol. JSON text — bare or fenced — finds no terminator and fails closed. Asserted by test in four files. |
| Is any dual-format path kept? | **No.** The dict path on `close_retrieval` is the fixture/`ScoutTransport` seam, documented as such; a scout cannot use it. |
| Dead code left? | **No.** `tests/experimental/line_format.py` was superseded by the production implementation and removed, along with its now-empty package. A test asserts the file is gone. |

## 9. ADR reference

**ADR-0017 — The scout returns operation-bound line records, not an envelope.** Accepted,
2026-09-13. Documents the decision, the 14/14 failure history, M9-C.13 and M9-C.14 evidence,
six rejected alternatives, why this protocol specifically, security and provenance properties,
zero-record semantics, fail-closed behaviour, how M9-C.1's coverage is preserved, consequences
including what adoption does *not* make true, and a three-step rollback. Supersedes the M9-C.1
return contract; modifies no earlier ADR.

## 10. Architecture changes

`architecture.md`, "Where the scout trust boundary sits", rewritten to make the line protocol
authoritative: the shape, the operation and count bindings as the replacement for span
selection, the explicit scout-controlled vs Python-controlled table, zero-record semantics,
fail-closed behaviour, and a closing paragraph stating that a reliable transport is not a
truthful source — retrieved content stays untrusted and may be wrong, stale, conflicting,
incomplete or low-quality. The subagent-invocation section now says the orchestration surface
passes the reply **verbatim** and why.

No speculative architecture was added; every sentence describes implemented behaviour.

## 11. Company Analysis impact

Inspected only, as instructed. `skills/biq-company-analysis/SKILL.md` already consumes
`open_retrieval`/`close_retrieval` with identical request arguments and reads `evidence`,
`accepted`, `rejected`, `candidate_claims` and `claims_not_produced` — none of which changed
shape. The only correction needed was the sentence telling the model to feed "the returned
envelope"; it now says the scout's **reply text**. `test_m9c3_company_analysis` (60 tests)
passes unchanged.

**The research handoff is production-ready for the existing Company Analysis path.** That is a
statement about the Python path and the contract, both verified here. It is **not** a claim of
live production readiness: no live Company Analysis run has been demonstrated end-to-end, and
§12 explains why that could not be done in this session.

## 12. Live smoke test — not performed, with reason

Not run, and forcing it would have produced misleading evidence.

Agent definitions bind when a session registers them (M9-C.10's 0/8, explained by M9-C.12).
**This session registered the pre-adoption definition**, so a dispatch now would exercise the
bare-envelope contract, not the one just adopted — reproducing precisely the invalidity that
made M9-C.10 inconclusive. The alternatives were all prohibited: modifying the definition
beyond the production contract, extracting or repairing output by hand, or substituting a shim
for the runtime path.

The adopted text is substantively the text M9-C.13 validated **8/8** — same tokens, same
operation-echo and count rules, same one-bare-object-per-line requirement, same
documented-fields-only and no-`source_tier` rules, same date handling, same prose permission,
same security clause (each verified present in the shipped file).

**Recommended:** one narrow live dispatch as the first action of the next session, which will
have registered the adopted definition. Until it runs, live external research is marked
`REVIEW`, not operational.

## 13. Security result

No security regression, and nothing weakened to make a test pass:

- **Fail-closed, verified across four files:** wrong operation, count over- and understated,
  missing terminator, duplicate terminator, malformed record JSON, non-object record,
  non-integer count, foreign-operation line mixed with valid ones, prose alone, and a JSON
  envelope sent as text — every one yields no evidence, never a partial set.
- **No partial evidence:** a two-record reply with a count of three discards both records.
- **Hostile structured content cannot manufacture a record:** a page quoting `BIQ-REC/1`,
  `BIQ-END/1` and a forged operation id inside `content` still produces exactly one record, the
  real one; pasted lines bearing a guessed operation id are ignored entirely; a verbatim copy
  bearing *this* operation breaks the count and fails the reply.
- **Forged authority is dropped and noted** — tier, trust, verification, provenance, freshness,
  `may_stand_alone`, plus `system` and `disclosure_tier`.
- **Tier recomputed locally:** a blog claiming A classifies C inferred, cannot stand alone, and
  a material claim on it is refused with "never the sole support".
- **No verified-claim path exists**, asserted mechanically.
- **Dates never invented:** omitted and explicit-null both stay absent; the retrieval date is
  never substituted.
- **Gate, four-tier disclosure model, k=5 floor, advisory markers, tool grant:** untouched.

## 14. Tests

New: `tests/unit/test_m9c15_production_protocol.py` — **61 tests** covering the twenty
properties the adoption review required, every one on the real gate-issued chain.

Retargeted, preserving intent (the owner's explicit authorisation; no security assertion
weakened, no test deleted):

| File | Change | Count |
|---|---|---|
| `tests/unit/test_m9c1_bare_envelope_contract.py` | Name and structure kept; header records the supersession. 10 document assertions re-pointed at the adopted contract; 3 envelope-text acceptance tests replaced by line-protocol acceptance plus an explicit refusal of the retired shape; `TestSurroundingTextIsRefused` **re-documented in place** with two new binding tests rather than deleted; a new test asserts the retired wording is gone. | 38 → **42** |
| `tests/negative/test_m9c9_shape_experiment.py` | Retargeted from the experimental adapter to `parse_reply`; one test's premise inverted (the envelope is no longer a scout contract). | **22**, unchanged |
| `tests/negative/test_m9c14_zero_record_and_full_path.py` | Retargeted to `parse_reply`; the five-stage binding proof now also asserts a reply read against another retrieval's brief yields nothing; two guard tests inverted. | **54**, unchanged |
| `tests/unit/test_m9b_scout_contract.py` | Documented-status check retargeted to the outcome vocabulary; envelope-text acceptance replaced by line-protocol acceptance, an explicit refusal, and a dict-path test. | 61 → **62** |
| `tests/negative/test_m9c7_return_contract_boundary.py` | Document half retargeted; "the same envelope bare is accepted" became "the same records in the adopted protocol are accepted", plus a new test that the four historical live shapes stay refused; the failure must now name the line protocol. | 15 → **16** |

Removed: `tests/experimental/line_format.py` and its package — superseded by the production
implementation.

```
$ python tests/run_tests.py
Ran 1933 tests in 114.056s
OK (skipped=19)
ran 1933 | failures 0 | errors 0 | skipped 19
```

Per-module, all passing: `unit.test_m9c15_production_protocol` 61 ·
`negative.test_m9c9_shape_experiment` 22 · `negative.test_m9c14_zero_record_and_full_path` 54 ·
`unit.test_m9c1_bare_envelope_contract` 42 · `unit.test_m9b_scout_contract` 62 ·
`negative.test_m9c7_return_contract_boundary` 16 · `unit.test_m9c3_company_analysis` 60 ·
plus the remaining M9 contract and security modules unchanged.

Two defects in my own new tests were found by running them and fixed in the tests, not in
production: a helper named `_outcome` collided with a `unittest` internal, and several document
assertions compared against text that markdown line-wrapping had split (fixed by normalising
whitespace, not by loosening the assertion).

## 15. Plugin validation

```
$ claude plugin validate . --strict
✔ Validation passed
```

## 16. Remaining limitations

1. **No live dispatch against the adopted definition.** §12. This is the one gap between
   "adopted and verified" and "demonstrated operational", and it is why live external research
   is `REVIEW` rather than `COMPLETED`.
2. **Adoption does not make external research truthful.** It makes transport and the trust
   boundary reliable. Sources remain potentially wrong, stale, conflicting, incomplete or
   low-quality; tiering, freshness, conflict recording and candidate-claim policy continue to
   do that work after every retrieval.
3. **Availability cost, accepted.** A hostile page that induces an extra valid-looking line
   fails the whole retrieval rather than forging evidence.
4. **Tier-C-inferred dominance** observed in M9-C.13 (28 of 29 records) is unaddressed — a
   recognised-host-registry question, not a protocol one.
5. **The canonical envelope remains in the codebase** as an internal structure. Isolated and
   documented, not production-reachable from a scout, and deliberately retained because it is
   where validation lives.

## 17. Next milestone

**M9-C.16 — live production smoke test and Company Analysis end-to-end demonstration.** First
action in a session that has registered the adopted definition: one narrow Tier-0 dispatch,
verifying that the production parser ingests a real scout reply with no manual extraction or
repair. If it passes, the live-research item moves from `REVIEW` to `COMPLETED` and M9-D
(`/company-analysis` and the remaining commands) is unblocked. If it fails, the ADR's rollback
section applies.

## 18. Git commit reference

N/A — no commit, no push, as instructed. Branch `main`, all changes uncommitted.
