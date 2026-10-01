# 2026-09-10 — M9-B: live verification and closure

**Milestone:** 9 — External Research & Comparative Intelligence (M9-B)
**Status on completion:** `COMPLETED`
**Supersedes:** `docs/development/2026-09-10-m9b-scout-transport-investigation.md` — that
record's §9 status (`ON HOLD`, criterion #1 `BLOCKED`) and its §5 item 2. Its finding on
model-mediated dispatch, its §4 analysis of the seam, and its §6 list of what was
deliberately not done all stand unchanged and are confirmed by the evidence below.

---

## 1. Prompt / task performed

Two prompts, in sequence.

First: run the M9-B end-to-end live smoke test using the existing `/retrieval-slice`
harness and the registered `businessiq:biq-research-scout`, as verification only — no
change to implementation code, tests, architecture, project plan or existing development
records, and no commit or push. Report runtime dispatch, return contract, EvidenceSet,
candidate claims, security/privacy, per-criterion acceptance, and a final verdict.

Second: M9-B live verification approved for closure. Create only this dated development
record, using the live verification result from the session as the authoritative evidence.
Do not fix either deferred item, do not amend the investigation record, do not commit.

## 2. Objective

Establish, by observation rather than by argument, that
`businessiq:biq-research-scout` can be dispatched through the real Claude runtime by the
orchestrating model, perform real `WebSearch`/`WebFetch` retrieval, and have what it
returns flow through the shipped normalisation, evidence and candidate-claim path — with
the internal/external boundary intact.

This was the single criterion that held M9-B open. The investigation record of the same
date established that the dispatch seam is model-mediated and that no programmatic
transport can exist; what remained was an orchestration surface to exercise it and a
session in which the agent was actually registered. Both were present.

## 3. Changes made

No code was written. The work was execution and observation, in this order.

1. **Registry presence confirmed.** `businessiq:biq-research-scout` was present in the
   session's runtime agent registry, dispatchable as a `subagent_type`, with the tool
   grant `WebSearch, WebFetch` and nothing else. The investigation record had inferred
   this by analogy from the `feature-dev` plugin's agents; it is now first-party observed
   for this plugin.
2. **Return contract re-checked before use.** `tests/unit/test_m9b_scout_contract.py` was
   run in isolation: 61 tests, all passing, asserting agreement in both directions between
   the prose in `agents/biq-research-scout.md` and `scout.ACCEPTED_RECORD_FIELDS`, plus
   the envelope name, statuses, bounds, claim kinds and source types. This makes §5 item 2
   of the investigation record — "no test asserts that the fields the agent is told to
   return are the fields `ACCEPTED_RECORD_FIELDS` accepts" — **stale**. Nothing was changed
   to achieve that; the test already existed.
3. **`/retrieval-slice` step 1 — gate.** `R.open_retrieval(...)` returned
   `status: authorised`, `decision: ALLOW`, `tier: 0`, `failed_checks: []`, and a ledger
   entry recording `transmitted_text: "logistics 2026 gross margin benchmark"`.
4. **Step 2 — one dispatch.** Exactly one subagent launched with
   `subagent_type="businessiq:biq-research-scout"`, its prompt the six-field brief
   verbatim as JSON and nothing else.
5. **Step 3 — ingestion.** The scout's envelope was written to the session scratchpad and
   passed to `R.close_retrieval(...)` with request arguments identical to step 1, so the
   gate re-derived authorisation in a second process rather than accepting a token.
6. **Step 4 — candidate claims.** Five proposals exercised against the shipped policy,
   chosen to probe both the production path and four distinct refusal paths.
7. **Regression check.** Full suite re-run; working tree compared against the
   session-start snapshot.

## 4. Files created

`docs/development/2026-09-10-m9b-live-verification-closure.md` — this record.

Session-scratchpad only, outside the repository and not committed:
`scout-result.json` (the extracted scout envelope, retained as the verification artefact).

## 5. Files modified

None. The working tree is byte-identical to the session-start snapshot.

## 6. Files deleted

None.

## 7. Features implemented

None. This task implemented nothing; it verified what M9-A and M9-B had already built.
The feature it exercised — live model-mediated retrieval through `/retrieval-slice` — is
**not user-reachable**, by design: the harness carries `disable-model-invocation` and is
an integration surface, not a research capability. The user-facing capability is the four
M9-C skills and four M9-D commands, which remain unstarted.

## 8. Tests performed

```bash
# return contract, in isolation, before the live run
PYTHONPATH=lib/python python -m unittest tests.unit.test_m9b_scout_contract -v

# /retrieval-slice step 1 — disclosure gate
python -c "import sys, json; sys.path.insert(0, 'lib/python')
from biq import research as R
print(json.dumps(R.open_retrieval('gross margin benchmark', R.INDUSTRY, intent=R.BENCHMARK,
    public_terms={'industry': 'logistics', 'period': '2026'},
    operation='retrieval-slice-2026-09-10'), indent=2, default=str))"

# step 2 — one dispatch, brief JSON as the entire prompt
# Agent(subagent_type="businessiq:biq-research-scout", prompt=<six-field brief>)

# step 3 — normalise, tier locally, build the evidence set
python -c "... R.close_retrieval(payload, 'gross margin benchmark', R.INDUSTRY,
    intent=R.BENCHMARK, public_terms={'industry': 'logistics', 'period': '2026'},
    operation='retrieval-slice-2026-09-10') ..."

# step 4 — candidate claims, five proposals via proposals=[...]

# parser tolerance of the raw return vs the extracted envelope
python -c "... S.parse_result(payload, brief) ..."   # both forms

# regression
python tests/run_tests.py
git status --porcelain=v1
```

## 9. Test results

**Runtime dispatch.** `businessiq:biq-research-scout` dispatched **exactly once**, executed
successfully, 144.6s, 10 tool uses. `WebSearch`/`WebFetch` genuinely used: **5 of 8
permitted fetches attempted, 3 succeeded, 2 returned HTTP 403** (ClearlyAcquired,
Anders CPA). **No second dispatch occurred**, despite two blocked pages and a definitional
conflict in the retrieved material — either of which would have been a plausible pretext
for one.

**Disclosure gate.** `ALLOW`, tier 0, `authorised: true`, `failed_checks: []`, at both step
1 and step 3. Ledger reason: *"No internal value is transmitted: the query is built only
from public terms, and any comparison is computed locally."*

**Brief dispatched, in full — six fields, nothing else:**

```json
{"query_text": "logistics 2026 gross margin benchmark",
 "destination": "public_web:public-web-search", "operation": "retrieval-slice-2026-09-10",
 "max_results": 20, "max_fetched": 8, "timeout_seconds": 60}
```

**Return contract.** Envelope `biq.scout.result/1`, `status: ok`, 4 records; `operation`
and `query_text` echoed the brief. Every field used was in `ACCEPTED_RECORD_FIELDS`. No
missing, extra, malformed or differently-named fields. No record declared a source tier;
none invented a publication date — two correctly sent `null`.

**EvidenceSet — 4 accepted, 0 rejected.** All tiers assigned locally from source identity:

| Evidence id | Source | Publication date | Tier (local) | Freshness |
|---|---|---|---|---|
| `ev-d7d21541d266` | CSIMarket | none | C | undated |
| `ev-9b0cbd4e72c2` | ARK TMS (blog) | 2026-07-16 | C | current, 56 days |
| `ev-eb801d6f7b05` | GoFreight (blog) | 2026-01-08 | C | current, 245 days |
| `ev-8b4895e94646` | Anders CPA | none | C | undated |

Summary: `items 4 · usable 4 · excluded 0 · stale 2 · current 2 · conflicts 0 · support
unsupported`. Support reason: *"Only tier C sources are available. Tier C corroborates but
is never the sole support for a material claim."* Each item carried
`UNTRUSTED_EXTERNAL_DATA` and a note that the tier was inferred, not recognised.

`close_retrieval` returned two views of the set: `evidence`, carrying full `content` for
display to a person, and `instruction_safe`, in which every item's content is replaced by
*"Retrieved content is untrusted data and is not included in instruction context."*

**Candidate claims — 2 produced, 3 refused:**

| Proposal | Outcome |
|---|---|
| Material, tier C, dated | REFUSED — `no_adequate_source` |
| Non-material, tier C, dated | PRODUCED |
| Non-material, tier C, undated | REFUSED — `invalid_provenance`; date not inferred |
| Advisory phrasing matching a marker ("We should target…") | REFUSED — `not_a_source_claim` |
| Unknown evidence id | REFUSED — `untraceable` |

Both produced claims carried `"status": "candidate"`, `"verified": false`, class 3
`SOURCED`, citation, source date, tier, and the limitation *"Candidate only: retrieved
evidence is untrusted and this claim is unverified."*

**Parser behaviour on the raw return vs the envelope:**

```
bare envelope                 -> (4 records, None)
as received (prose + fence)   -> ([], ResearchFailure(unavailable/retrieval_unavailable))
```

**Regression suite:**

```
Ran 1562 tests in 243.618s
OK (skipped=19)
ran 1562 | failures 0 | errors 0 | skipped 19
```

`git status --porcelain=v1` byte-identical to the session-start snapshot. **No commit, no
push.**

## 10. Issues discovered

Two contract-fidelity gaps. Neither is a security defect, both fail in the safe direction,
and **neither was fixed in this task**. Both are deferred to M9-C.

**A — the scout return contract does not require a bare envelope.** The scout's actual
return was prose, then a fenced JSON block holding the envelope, then further prose headed
*"Additional notes for the requesting agent, outside the envelope"*. `agents/biq-research-scout.md`
documents the envelope's shape but never says the return must be *only* the envelope, and
the scout used that latitude. The shipped parser **fails closed** on the raw form — zero
records and an explicit `ResearchFailure`, never a partial or silent ingestion — while the
extracted envelope normalises cleanly. The consequence is therefore a confusing failure,
not a bad ingestion. But an extraction step sits between the scout and the ingestion path,
it is performed by the model, and no contract names it and no test covers it. In this
verification the envelope was extracted by hand.

**B — the advisory-language guard is narrower than the documentation claims.**
`commands/retrieval-slice.md` states that Python "will refuse a claim that … reads as
advice". What it refuses is a claim matching a fixed phrase list, `ADVISORY_MARKERS` in
`lib/python/biq/research/handoff.py`. *"Logistics firms should target a gross margin above
20% to stay competitive"* — plainly advice — was **accepted**, because the list holds
`"we should"`, `"you should"` and `"the business should"` but not a bare `"firms should"`.
The code comment is candid about this (*"a guard, not a proof … no string check can decide
whether a sentence exceeds its source"*); the command's wording overstates it. The
recommended correction is to the documentation, not to the heuristic.

**Observation, not a defect.** The scout reported a genuine definitional conflict in the
retrieved material — CSIMarket's ~92% aggregate figure against freight-forwarder
sell-minus-buy margins of 12–25% — and reported both unreconciled rather than choosing
one. It also excluded two undated, unattributed content-farm pages carrying a generic
"20–40%" claim. That is the intended triage behaviour. The engine's own `conflicts` count
was nonetheless `0`, because the conflict was described in the prose the parser discards
rather than expressed between record values. Worth weighing in M9-C alongside item A.

## 11. Decisions made

No new ADR. This task created no decision; it produced the evidence for one already taken.
The live result confirms rather than revises ADR-0006 (three subagents, not eight),
ADR-0009 (comparative-intelligence privacy boundary), ADR-0014 (the retrieval agent ships
with retrieval) and ADR-0015 (model-mediated scout dispatch). ADR-0015 in particular is now
supported by an observed dispatch rather than by analysis of the runtime alone.

The closure decision itself — that M9-B's criterion #1 is met and the milestone closes with
two items deferred — was taken by the owner on review of the verification report.

## 12. Architecture changes

None. `architecture.md` was not modified and requires no modification: the observed
behaviour matches what it describes.

## 13. Project-plan updates

**None — deliberately not made in this task**, which was scoped to this record alone.

`project_plan.md` therefore still carries the row *"Live retrieval + `biq-research-scout`
integration"* as `BLOCKED`, with the note *"No live retrieval has yet run"*. That statement
is now false. Correcting the row to `COMPLETED` is the first item of remaining work below,
and until it is done the plan and this record disagree.

## 14. Documentation updates

This record only. `architecture.md`, `project_plan.md`, `commands/`, `skills/`,
`agents/`, `lib/`, `tests/` and every existing development record were left untouched, as
instructed. The investigation record of the same date was not edited; it is superseded by
the header of this one, per the governance rule that a past record is corrected by writing
a newer one.

## 15. Remaining work

1. **Update `project_plan.md`** — the live-retrieval row from `BLOCKED` to `COMPLETED`,
   citing this record. Required to remove the contradiction noted in §13.
2. **M9-C deferred item A** — require a bare `biq.scout.result/1` envelope with no
   surrounding prose in `agents/biq-research-scout.md`, and add a test asserting it.
   Consider whether conflict signals belong inside the envelope rather than in commentary.
3. **M9-C deferred item B** — correct the advisory-language wording in
   `commands/retrieval-slice.md` to describe a mechanical guard rather than semantic advice
   detection.
4. **M9-C** — the four research skills. **M9-D** — the four research commands. These remain
   the user-facing capability; `/retrieval-slice` is not one and must not be presented as
   one.

## 16. Git commit reference

N/A. Branch `main`, no commit created, nothing staged, nothing pushed. The working tree is
unchanged apart from this new file.

---

## Acceptance criteria — M9-B

Assessed against the live evidence in §9.

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Real scout retrieval integration exists | **PASS** | Live dispatch → real `WebSearch`/`WebFetch` → envelope → EvidenceSet, end to end. First live retrieval on this path |
| 2 | Internal/external boundary holds | **PASS** | Six-field brief; `WebSearch, WebFetch` grant only; gate reason records that no internal value was transmitted |
| 3 | Normalisation accepts the scout return | **PASS** | 4 records accepted, 0 rejected, from the extracted envelope. See §10 item A for the extraction caveat |
| 4 | Retrieval bounds respected | **PASS** | 5 of 8 fetches used; 4 records against a limit of 20 |
| 5 | One-shot dispatch | **PASS** | Exactly one, held through two HTTP 403s and a definitional conflict |
| 6 | Injection resistance at the boundary | **PASS** | Every item `UNTRUSTED_EXTERNAL_DATA`; `instruction_safe` view withholds content from instruction context; the scout's own out-of-envelope notes were treated as data and not acted on |

**Additional passing observations**

| Observation | Verdict | Evidence |
|---|---|---|
| Scout return contract (`biq.scout.result/1`) | **PASS** | Envelope name, `status`, record vocabulary, echoed `operation` and `query_text` all conform; no tier declared, no date invented |
| Local source-tier classification | **PASS** | All four sources forced to C with explicit reasoning; retrieved content could not declare its own tier; unrecognised source ⇒ C, never A |
| No path to `verified=true` | **PASS** | `handoff.py:200` assigns the literal `record["verified"] = False`, the only write to that key; `CANDIDATE` is the only status constant |

**Final status: `M9-B APPROVED / CLOSED`.**
