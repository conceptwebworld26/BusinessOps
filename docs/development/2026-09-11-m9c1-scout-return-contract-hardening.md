# 2026-09-11 — M9-C.1: scout return-contract hardening

**Milestone:** 9 — External Intelligence & Disclosure Gate (M9-C.1)
**Status on completion:** `COMPLETED`
**Supersedes:** None as a whole. It **corrects one factual statement** made in
`docs/development/2026-09-10-m9b-live-verification-closure.md` §10 item A, and repeated in
the `project_plan.md` deferred row that this task closes. See §10 below. That record's
findings, evidence and acceptance verdicts are otherwise unaffected.

---

## 1. Prompt / task performed

Implement M9-C.1 — scout return-contract hardening. Make the model-mediated
`biq-research-scout` return contract explicit and enforceable: the scout must return only
the bare `biq.scout.result/1` JSON envelope, with no surrounding prose, Markdown fences,
commentary, explanations or headings. Update the agent contract, review the existing
return-contract tests, add tests covering the requirement in both directions, preserve the
parser's fail-closed behaviour without loosening it, determine explicitly whether an ADR is
required, write a dated development record, and update `project_plan.md` only for M9-C.1
status. No commit, no push, no unrelated M9-C work.

## 2. Objective

Close the first of the two items deferred from M9-B: remove the ambiguity that let the live
scout return `prose → fenced JSON → prose`, and put the requirement under test so it cannot
drift back.

## 3. Changes made

1. **Read the existing contract before changing it** — and found the premise needed
   correcting. `agents/biq-research-scout.md` already opened its return section with *"One
   JSON object and nothing else. No prose before it, no prose after it, no commentary
   between records."* The requirement was not missing. What was wrong sat in the next
   sentence: *"anything outside the object is discarded and a malformed object returns no
   evidence at all."* That reads as **surrounding prose is harmless — it gets stripped**,
   which is false and is a plausible reason the live scout felt free to add commentary.
   The defect was a misleading reassurance, not a missing rule. See §10.
2. **Rewrote the "What you return" preamble** into an unambiguous, itemised requirement:
   bare object only, the reply starts with `{` and ends with `}`, no Markdown fences (with
   an explicit note that the fenced example in the document is documentation formatting and
   not part of the reply), no prose either side, no notes addressed to the requesting agent,
   no headings or lists, documented fields only.
3. **Replaced the false reassurance** with what actually happens: a wrapped reply *fails
   closed and yields no evidence at all*, and everything the scout retrieved is discarded
   with it — with the reason, that tolerating text around a JSON object is how a retrieved
   page's own JSON could be selected instead of the scout's.
4. **Gave the scout somewhere to put what it wanted to say.** The live scout had a real
   caveat (two HTTP 403s, a definitional conflict) and no field for it, so it wrote prose.
   The contract now states there is no out-of-band channel and names the three that exist:
   `status`, which records are returned, and each record's `content`. A matching row was
   added to the Failure conditions table.
5. **Reviewed the existing tests** in `tests/unit/test_m9b_scout_contract.py` (61 tests).
   Most of the requested matrix was already covered, including
   `test_prose_around_the_envelope_is_not_tolerated`. The genuine gaps were: leading-only
   and trailing-only text as separate cases, the exact live `prose → fence → prose` shape,
   the document-side assertions for the newly explicit wording, and a pinned statement of
   the fence asymmetry. Nothing existing was deleted or weakened.
6. **Added `tests/unit/test_m9c1_bare_envelope_contract.py`** — 38 tests in four classes,
   covering the document and the behaviour.
7. **No `lib/` change.** The parser was already fail-closed on surrounding prose; it was
   not touched, in either direction.

## 4. Files created

- `tests/unit/test_m9c1_bare_envelope_contract.py` — 38 tests.
- `docs/development/2026-09-11-m9c1-scout-return-contract-hardening.md` — this record.

## 5. Files modified

- `agents/biq-research-scout.md` — the "What you return" preamble rewritten; one row added
  to Failure conditions. The record-field table, status table, bounds, echo requirements
  and all eight Rules are **unchanged**.
- `project_plan.md` — M9-C.1 status only (§13).

## 6. Files deleted

None.

## 7. Features implemented

No runtime feature. The deliverable is an enforceable contract: a document a model reads as
its instructions, and tests that hold both the document and the ingestion behaviour in
place. Not user-reachable, and not intended to be.

## 8. Tests performed

```bash
# focused, first
PYTHONPATH=lib/python python -m unittest tests.unit.test_m9c1_bare_envelope_contract -v

# full regression
python tests/run_tests.py
```

## 9. Test results

**Focused — 38 tests, all passing:**

```
Ran 38 tests in 0.017s
OK
```

| Class | Tests | Covers |
|---|---|---|
| `TestTheContractIsExplicit` | 10 | The document requires a bare object, forbids fences, disclaims its own example fence, forbids prose either side, forbids notes to the caller, no longer claims surrounding text is merely discarded, states the whole reply is lost, names the only channels available |
| `TestTheBareEnvelopeStillWorks` | 4 | Bare object accepted; bare JSON string accepted; surrounding whitespace is not prose; a fence alone still tolerated by the parser (pinned asymmetry) |
| `TestSurroundingTextIsRefused` | 10 | The exact live `prose → fence → prose` shape; leading-only; trailing-only; a heading before; a bullet list after; a trailing fragment; prose inside the fence; two envelopes concatenated; the envelope nested in a wrapper object; an explanation instead of an envelope |
| `TestExistingValidationSurvives` | 14 | Wrong envelope name; substituted operation; substituted query echo; unrecognised status; malformed JSON; undocumented field dropped; scout-supplied `source_tier` does not survive; missing and explicit-`null` publication dates never inferred; evidence bound; content bound; content still untrusted; `no_reliable_source_found` still structured; parsing never raises |

**Full regression — 1,600 tests, all passing:**

```
Ran 1600 tests in 124.261s
OK (skipped=19)
ran 1600 | failures 0 | errors 0 | skipped 19
```

Baseline was 1,562 / 0 / 0 / 19 at the M9-B closure; +38 is exactly this task's additions.
**No failures. Skips unchanged at 19** — the same pre-existing set, none introduced here.

The 61 existing tests in `test_m9b_scout_contract.py` passed unchanged against the rewritten
document, which is the check that mattered: several of them scan that file for the record
vocabulary, the status values, the bounds and the six brief fields.

## 10. Issues discovered

**A correction to the M9-B closure record.** That record's §10 item A stated:
*"`agents/biq-research-scout.md` documents the envelope's shape but never says the return
must be *only* the envelope, and the scout used that latitude."* **The first half is
wrong.** The document did say it, in the first line of "What you return". The `project_plan.md`
deferred row repeated the same error and has been corrected as part of closing it.

The accurate finding, which this task acted on, is narrower and more useful: the contract
stated the rule and then immediately undercut it by describing surrounding text as
*discarded*, which invites a model to conclude that adding prose costs nothing. A rule
followed by a reassurance that breaking it is harmless is weaker than no rule, and that is
what the live run exercised. The remedy was to make the consequence explicit and to give
the scout a sanctioned place for what it was trying to say — not merely to restate the
prohibition louder.

**A deliberate asymmetry, now pinned rather than silent.** The document forbids Markdown
fences; the parser still accepts an envelope wrapped in one and nothing else, via
`scout._unfence()`. This is intentional and is asserted by
`test_a_fence_alone_is_still_tolerated_by_the_parser`, whose docstring carries the reason: a
fence leaves no ambiguity about which object is the payload, whereas free text does. The
parser was **not** tightened to reject fences — that would remove a harmless safety net and
change shipped behaviour for no security gain — and it was **not** loosened to accept prose.

**No new issue found in `lib/`.** The parser behaved correctly throughout, both in the live
M9-B run and against all 24 refusal shapes added here.

## 11. Decisions made

**No ADR. This determination was made explicitly, against the bar in
`docs/decisions/README.md`, not by omission.**

The bar asks for an ADR when a decision constrains future work, is expensive to undo,
rejects an option a reviewer would expect, changes a load-bearing invariant, or would
puzzle someone in six months. Measured against it:

- The **data contract is unchanged**: `biq.scout.result/1`, the same fields, the same
  bounds, the same echo requirements. Nothing downstream shifts.
- The **seam is unchanged**. ADR-0015 already establishes model-mediated dispatch, and
  ADR-0006/0009/0014 the boundary and topology. This task states an existing requirement
  more clearly and tests it.
- **No load-bearing invariant moved** — evidence model, permission model, internal/external
  boundary and agent topology are all untouched.
- The README's exclusion list names **wording changes** explicitly.

The one borderline consideration, recorded here rather than in an ADR because it is small
and local: a reviewer might expect the parser to be taught to extract an envelope from
surrounding prose. That option was rejected — it would make the parser permissive to
exactly the shape that could let a retrieved page's own JSON be selected, which is the
attack the current behaviour prevents. The reasoning lives in the test docstring that pins
it, where someone changing that behaviour will actually encounter it.

## 12. Architecture changes

None. `architecture.md` was not modified and needs no modification: it describes the seam
and the envelope, both unchanged. **No architectural decision changed.**

## 13. Project-plan updates

Minimal, and confined to M9-C.1:

- The M9-C deferred row *"Scout return contract must require a **bare** envelope"* →
  `COMPLETED`, retitled M9-C.1, with its note corrected (it had repeated the §10 error) and
  pointed at this record.
- The `9-B approved` paragraph gained one sentence noting that the first deferred item is
  now closed and the second remains open.

The second deferred item — advisory-language documentation — is **untouched and still
`DEFERRED`**. No other row, milestone or status was edited.

## 14. Documentation updates

`agents/biq-research-scout.md` and `project_plan.md` as described. `architecture.md`,
`CLAUDE.md`, `commands/retrieval-slice.md`, `reference/`, every skill, and every existing
development record were left alone. `commands/retrieval-slice.md` in particular was **not**
touched: its known wording defect is the second deferred item and is not in this scope.

## 15. Remaining work

1. **M9-C.2 — advisory-language documentation.** `commands/retrieval-slice.md` claims
   semantic advice detection; `handoff.ADVISORY_MARKERS` is a fixed phrase list. Correct the
   documentation, not the heuristic. Still `DEFERRED` in the plan.
2. **M9-C proper** — the four research skills; then **M9-D**, the four external commands.
   Neither started.
3. **Optional, not required:** a live re-run of `/retrieval-slice` against the hardened
   contract would show whether the clearer wording changes what the scout actually emits.
   The contract is enforced by ingestion either way, so this is evidence about model
   compliance, not about correctness.

## 16. Git commit reference

N/A. Branch `main`, no commit created, nothing staged, nothing pushed.

---

## Contract now enforced

The scout's reply must be **exactly one bare `biq.scout.result/1` JSON object**:

| Requirement | Enforced by |
|---|---|
| Bare JSON object, reply starts `{` and ends `}` | Contract §"What you return"; `TestTheContractIsExplicit`, `TestTheBareEnvelopeStillWorks` |
| Envelope exactly `biq.scout.result/1` | `parse_result` name check; `test_a_wrong_envelope_name_is_refused` |
| No Markdown code fences | Contract (document-side); parser tolerates a bare fence by design — `test_a_fence_alone_is_still_tolerated_by_the_parser` |
| No prose before or after | `parse_result` fails closed; 10 refusal tests |
| No commentary or explanation outside the envelope | Contract; `test_it_forbids_notes_addressed_to_the_caller` |
| Only the documented fields | `ACCEPTED_RECORD_FIELDS`; `test_an_undocumented_record_field_is_dropped_and_recorded` |
| No invented source tiers | `sources.classify_tier()`; `test_a_scout_supplied_source_tier_does_not_survive` |
| No invented publication dates; `null` preserved | `test_a_missing_publication_date_is_never_inferred`, `test_a_null_publication_date_is_preserved_as_missing` |
| Operation and query echo — **unchanged** | `parse_result`; two refusal tests |
| Bounds — **unchanged** | `MAX_EVIDENCE_ITEMS` 20, `MAX_CONTENT_CHARS` 20,000; two bound tests |

**Security boundary unchanged.** The scout gained no file or repository access, no internal
business data, and no tool beyond `WebSearch, WebFetch`. It still cannot set a source tier
or mark anything verified. Disclosure-gate behaviour, Tier 0/1/2/3 policy and candidate-claim
policy were not touched. No conflict resolution, interpretation, recommendation or research
command was added.

**Parser remained fail-closed.** No code in `lib/` changed.

**Final status: `M9-C.1 COMPLETED`.**
