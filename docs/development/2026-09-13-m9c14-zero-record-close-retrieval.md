# 2026-09-13 — M9-C.14: zero-record representation and full `close_retrieval()` integration

**Milestone:** M9-C.14 — Zero-record representation and complete gate-issued handoff verification
**Status on completion:** `COMPLETED` — Outcome A: both open C.13 items closed; candidate still not adopted
**Supersedes:** None

---

## 1. Objective

Close the two verification items M9-C.13 left open, without adopting the candidate protocol:

1. Determine what `BIQ-END/1 <operation> 0` means, how it is currently represented, and
   whether the existing contracts are sufficient to express it safely.
2. Verify the **complete** production path — disclosure gate → `ScoutBrief` → scout handoff →
   `BIQ-REC/1`/`BIQ-END/1` → `parse_result()` → `normalise_records()` → `close_retrieval()` →
   `EvidenceSet` — using a real gate-issued authorisation rather than C.13's shim brief, and
   prove the operation identity stays bound along its whole length.

Verification and design only, except for the minimum change needed to make a verified
contract expressible.

## 2. Starting state

- M9-C.13 closed Outcome A: observed 8/8 live compliance, 29 records, candidate live-validated
  but not adopted. Its two named limitations are this milestone's scope.
- `agents/biq-research-scout.md` pristine at
  `04f0b30da8efcf4f4cf2644ee351dfd42d7d7f641c21ee2fc37d6d48b440d244`, carrying the production
  `biq.scout.result/1` contract and **not** the experimental protocol.
- 1812 tests passing; candidate matrix 22 tests; `claude plugin validate . --strict` passing.
- `tests/experimental/line_format.py` unimported by anything in `lib/`.

## 3. Zero-record semantics discovered

Answers read from the code, not assumed.

**3.1 What zero records currently means.** In the candidate adapter, the zero-record branch is
reachable **only** when a terminator was present *and* its declared count agreed with an empty
set of record lines. A missing terminator is refused earlier as `NO_TERMINATOR`, and a
disagreeing count earlier as `COUNT_MISMATCH`. So `BIQ-END/1 <operation> 0` has exactly one
possible meaning: **the scout searched and found nothing citable.** It is unambiguous.

**3.2 How it was represented.** As `NO_RECORDS` — a structural refusal returning
`(None, "no_records")`, i.e. **no envelope at all**. `close_retrieval()` was therefore never
reached, and the outcome could not be expressed in production vocabulary. Grep confirmed
`NO_RECORDS` was **defined, returned, and asserted by no test anywhere** — the path C.13
correctly called unvalidated.

**3.3 Where the status is created.** Three distinct places, and this is the crux:

| Producer | What it can say about an empty result |
|---|---|
| `line_format.to_envelope()` | `NO_RECORDS` refusal only — no status channel exists |
| `scout.parse_result()` | reads `status` from the envelope; `RESULT_NO_SOURCE` → `INSUFFICIENT_EVIDENCE` / `REASON_NO_ADEQUATE_SOURCE` |
| `handoff.close_retrieval()` | after normalisation, `if not normalised:` → the same `INSUFFICIENT_EVIDENCE` / `REASON_NO_ADEQUATE_SOURCE`, carrying `rejected` |

**The production contract was already sufficient.** `scout.RESULT_STATUSES` has carried
`no_reliable_source_found` since M9-B, `close_retrieval()` already renders it as a structured
research failure with `evidence: None`, and nothing about it needed redesigning. The gap was
solely that the **line protocol had no way to say it**, because the adapter spent the
zero-record case on a refusal.

**3.4 What `close_retrieval()` does with it.** Given an envelope with
`status: "no_reliable_source_found"`, `parse_result()` returns a failure *before* reading
records, so `close_retrieval()` returns
`{status: insufficient_evidence, reason: no_adequate_source, evidence: None, brief: {...}}` —
no `EvidenceSet`, no `candidate_claims` key at all, and the brief (hence the gate-issued
operation and approved query text) echoed back.

**3.5 Do the four distinctions exist?** Yes, all four, verified by test:

| Outcome | status | reason | distinguisher |
|---|---|---|---|
| No records found | `insufficient_evidence` | `no_adequate_source` | `rejected` empty |
| Records found, all unusable | `insufficient_evidence` | `no_adequate_source` | `rejected` populated and names why |
| Retrieval/tool failure | `unavailable` | `source_unavailable` | — |
| Malformed protocol | `unavailable` | `retrieval_unavailable` | (or `invalid_provenance` on an echo mismatch) |

The first two deliberately share a `(status, reason)` pair — both mean "nothing citable came
back" — and are told apart by `rejected`. The two *families* are firmly separated:
`insufficient_evidence` is a research answer, `unavailable` is a defect.

**3.6 Which distinctions the production contract actually requires.** Only the
status/reason pairs above. No new status, no new reason, no new envelope field was required,
and none was added.

## 4. Implementation change — one file, experimental only

`tests/experimental/line_format.py`, two edits:

1. The zero-record branch no longer refuses. Where declared count and record count agree at
   zero, the adapter now builds the canonical envelope with
   `status: "no_reliable_source_found"` and `records: []`.
2. `NO_RECORDS` retained as a name, annotated as no longer returned; `STATUS_OK` and
   `STATUS_NO_SOURCE` added as literals, spelled out rather than imported, preserving the
   experiment's deliberate rule of importing no production module.

**Why this is the smallest possible change.** The adapter's job is to turn lines into the
canonical envelope and hand it to production. A protocol-valid empty result *is* a canonical
envelope — one production already knows how to render safely. Expressing it needs no new
vocabulary anywhere else, and deciding what it *means* stays where it already was, in
`parse_result()` and `close_retrieval()`.

**Fail-closed behaviour is unchanged.** Failing closed is about evidence, and no evidence is
created on either path: the old behaviour produced no envelope, the new one produces an
envelope that production converts into a failure with `evidence: None`. Every structural
defect — missing terminator, count mismatch, malformed record, non-integer count, two
terminators, foreign operation — still refuses exactly as before, which the C.9 matrix
(22 tests, unchanged, still passing) and the new Case 4/5 tests both confirm.

No production module was touched. No gate semantics, tier policy, k=5 floor, advisory
heuristic, parser behaviour or scout definition changed.

## 5. The complete gate-issued path — and why no shim was needed

**Principal finding: the operation id is caller-supplied and gate-bound, not gate-minted.**
`ResearchRequest(..., operation=...)` carries it; `gate.assess()` binds it into the
`DisclosureDecision` and the ledger entry; `RetrievalRequest` reads it from the decision's
binding; `ScoutBrief` reads it from the request. `handoff._decide()` passes `operation=`
straight through, and `close_retrieval()` re-derives its brief from **identical request
parameters** — which the module docstring already states is the design: *"the request
parameters must be identical in both calls, which is deterministic and cheap."*

So C.13's shim was never necessary. The correct construction is to pass the same `operation`
to both halves, and the echo checks then line up. Every test in this milestone does that and
builds its brief through the real chain:

```
ResearchRequest -> gate.assess -> RetrievalRequest -> ScoutBrief
    -> BIQ-REC/1 / BIQ-END/1 reply -> to_envelope -> close_retrieval -> EvidenceSet
```

`ScoutBrief` refuses anything not carrying a gate-issued authorisation, and
`gate.is_gate_issued(decision)` is asserted directly, so the premise is tested rather than
assumed. The gate authorises the request at **tier 0** and *constructs the query text itself*
(`"logistics 2026 benchmark"` from the public terms) — the reply must echo the gate's text,
not a caller's, and that is asserted too.

**Operation binding proved at five stages** in one test: brief → envelope → normalised records
→ `EvidenceSet.operation` → every `EvidenceItem.operation` → the brief echoed back in the
result. One id, five places, asserted as a set equal to a single value.

## 6. Deterministic cases

`tests/negative/test_m9c14_zero_record_and_full_path.py` — **54 tests**, all on the real path.

| Case | Covered |
|---|---|
| Premise | gate authorises at tier 0, decision is gate-issued, brief carries exactly six fields, query text is the gate's, a brief cannot be built without an authorisation |
| **1 — Valid records** | 2 records + prose before and after → `close_retrieval` returns `ok`, accepted 2, rejected 0; `EvidenceSet` bound to the operation; every item bound; tier **A** assigned locally for `ons.gov.uk`/`gov.uk`; trust marked; prose changes nothing (bare reply yields an identical envelope); no claim unless asked |
| **2 — Zero records** | `BIQ-END/1 op 0` accepted as an envelope with `no_reliable_source_found`; `close_retrieval` → `insufficient_evidence`/`no_adequate_source`; **no `EvidenceSet`**; nothing fabricated; no claim even when one is proposed; explanation asserts no falsity; operation and approved query preserved; a zero count with record lines present still refused |
| **3 — Wrong operation** | records+terminator for another operation yield nothing; a mixed reply does not smuggle the foreign record in (count check catches it); an envelope naming a different operation → `invalid_provenance`; a substituted query text → `invalid_provenance` |
| **4 — Count mismatch** | overstated and understated counts both fail the whole reply; **no partial evidence** survives; two terminators are not one reply |
| **5 — Malformed protocol** | unparsable record JSON, a JSON array instead of an object, missing terminator, non-integer count, prose alone, and hostile inputs (`None`, `42`, bytes, empty, NUL, list, dict) — all refuse, none raise |
| **6 — Trust boundary** | a blog claiming `source_tier: "A"` plus forged `trust`, `operation`, `verified`, `tier_inferred`: tier **recomputed to C** locally, `tier_inferred` recomputed true, `may_stand_alone` false, trust forced to `untrusted`, operation taken from the brief, all five forged keys dropped **and named in a note**, absent publication date left absent (`freshness: undated`), and a material claim on it **refused** with "never the sole support" |
| Experiment guard | nothing in `lib/` imports the adapter; shipped envelope name and statuses unchanged; the production parser still refuses prose-wrapped envelopes; the scout definition still carries no `BIQ-REC/1`/`BIQ-END/1` |

Two defects in my own first draft were found and fixed by running it: `_outcome` collided with
a `unittest` internal, and I had asserted the wrong trust constant
(`scout.UNTRUSTED_EXTERNAL_DATA`, the note prefix, rather than `evidence_set.UNTRUSTED`, the
field value). Both were test bugs; no production or adapter behaviour was changed to
accommodate them, and the corrected assertions are stricter than the originals.

## 7. Live test

**Not performed, and not required.** Recorded explicitly against each element:

| Element | Validated by C.14 | How |
|---|---|---|
| Gate-issued operation identity | **yes** | real `gate.assess()`, `is_gate_issued` asserted |
| Real `ScoutBrief` construction | **yes** | production chain; constructor refuses non-authorised input |
| Actual scout return | **no** | inherited from M9-C.13's 8/8 live trial; unchanged here |
| Production parser / normaliser | **yes** | `parse_result()` and `normalise_records()`, unmodified |
| `close_retrieval()` | **yes** | run end-to-end, real brief, no shim |

The only leg a live dispatch could exercise is the scout's own authoring of protocol lines,
which C.13 already measured at 8/8 and which is not what C.14 asked. Re-running it would add
cost and no evidence. A live zero-record case was **not** attempted: producing one requires
choosing a question designed to fail, and manufacturing a zero-record response to obtain a
desired result is forbidden and would be worthless as evidence.

**Proposed for review, not run:** should a natural zero-record live observation be wanted, the
honest way to get one is to wait for it to occur during ordinary Tier-0 research rather than to
engineer it — for example, recording it opportunistically the first time a genuine benchmark
question on a narrow niche returns nothing citable. Note also that the live protocol cannot be
exercised at all while the pristine definition is in place, since it does not carry the
protocol; any future live leg implies either the trial definition or adoption.

## 8. Security and provenance observations

- **Nothing the scout says about its own authority survives.** Tier, trust, verification and
  operation are all locally owned, and a record asserting any of them is stripped — with the
  attempt recorded in a note, so the forgery is visible rather than merely ineffective.
- **Local tiering is authoritative and was not touched.** A blog naming itself tier A
  classifies C inferred, cannot stand alone, and is refused as the sole support for a material
  claim.
- **No fabricated dates.** An absent publication date stays absent and surfaces as
  `freshness: undated`.
- **No verified claim is reachable.** `handoff.CANDIDATE` is the only claim status and no
  constant naming a verified state exists — asserted mechanically.
- **The count check remains the anti-smuggling control.** A foreign line copied from a page is
  not a record, so the declared count disagrees and the whole reply fails — fail-closed on
  availability, never a forged acceptance. Unchanged by this milestone.
- **A zero-record result is absence of evidence, not evidence of absence.** Asserted: the
  reason is the evidence-absence reason, and the explanation contains no assertion of falsity.
- The gate, the k=5 privacy floor, disclosure-tier semantics and the advisory marker list were
  not modified.

## 9. Limitations

1. **The live scout leg is inherited, not re-verified.** C.14 proves the Python path; C.13's
   8/8 remains the only live evidence that a scout emits conforming lines.
2. **Zero records remain live-unobserved.** The semantics are now defined, expressible and
   deterministically tested, but no live retrieval has produced one.
3. **The protocol is still experimental.** `lib/` does not import the adapter, and the shipped
   contract remains the bare envelope, so the line protocol cannot reach a real retrieval
   without adoption.
4. **The adapter is the seam under test, not production code.** Its zero-record behaviour is
   now correct, but that correctness only matters once adoption moves the logic into `lib/`.
5. Tier-C-inferred dominance observed in C.13 is unaddressed here and remains an open
   recognised-host-registry question.

## 10. Tests performed and results

```
$ python tests/run_tests.py negative.test_m9c14_zero_record_and_full_path
Ran 54 tests in 0.038s
OK
ran 54 | failures 0 | errors 0 | skipped 0

$ python tests/run_tests.py negative.test_m9c9_shape_experiment
ran 22 | failures 0 | errors 0 | skipped 0
```

M9 contract and security modules, each run individually — all pass, zero failures, zero
errors: `unit.test_m9_governance` 46 · `unit.test_m9a_invariants` 57 ·
`unit.test_m9a_research_core` 65 · `unit.test_m9b_candidate_claims` 36 ·
`unit.test_m9b_scout_contract` 61 · `unit.test_m9c1_bare_envelope_contract` 38 ·
`unit.test_m9c2_advisory_guard_wording` 12 · `unit.test_m9c3_company_analysis` 60 ·
`unit.test_m9c4_conflict_transport` 53 · `negative.test_m9a_adversarial` 34 ·
`negative.test_m9a_gate_forgery` 43 · `negative.test_m9b_scout_security` 57 ·
`negative.test_m9c6_tier_boundary` 39 · `negative.test_m9c7_return_contract_boundary` 15 ·
`negative.test_m9c8_handoff_provenance` 11 · `negative.test_m9c9_shape_experiment` 22 ·
`negative.test_m9c14_zero_record_and_full_path` 54.

```
$ python tests/run_tests.py
Ran 1866 tests in 306.106s
OK (skipped=19)
ran 1866 | failures 0 | errors 0 | skipped 19

$ claude plugin validate . --strict
✔ Validation passed
```

1866 = 1812 before C.14 + 54 new. No existing test was modified.

## 11. Files created

- `tests/negative/test_m9c14_zero_record_and_full_path.py` — 54 deterministic tests.
- `docs/development/2026-09-13-m9c14-zero-record-close-retrieval.md` — this record.

## 12. Files modified

- `tests/experimental/line_format.py` — zero-record envelope; `NO_RECORDS` annotated;
  `STATUS_OK`/`STATUS_NO_SOURCE` added.
- `project_plan.md` — M9-C.14 row.

## 13. Files deleted

None.

## 14. Architecture changes

None. `architecture.md` deliberately untouched — adoption owns that change.

## 15. Production-adoption status

**Not adopted.** `BIQ-REC/1` / `BIQ-END/1` remains experimental: nothing in `lib/` imports the
adapter (asserted by test), the shipped contract is still `biq.scout.result/1`, the scout
definition still carries the bare-envelope contract, and no ADR was written.

## 16. Recommendation for next milestone

**M9-C.15 — formal `BIQ-REC/1` / `BIQ-END/1` adoption decision**, including the ADR and the
`architecture.md` update. Both C.13 blockers are now closed: the protocol is live-validated
(8/8, 29 records) and its complete production integration plus zero-record semantics are
deterministically verified on a real gate-issued path. Adoption should move the adapter logic
from `tests/experimental/` into `lib/python/biq/research/`, ship the protocol in the scout
definition as the sole contract, retire the bare-envelope requirement with its history
recorded, and keep the C.9/C.14 matrices as the regression floor. That is an owner decision,
not an implementation detail, and it is the one that unblocks `/company-analysis` and M9-D.

## 17. Git commit reference

N/A — no commit, no push, as instructed. Branch `main`, all changes uncommitted.
