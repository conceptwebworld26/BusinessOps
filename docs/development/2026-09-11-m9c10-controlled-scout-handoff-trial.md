# 2026-09-11 — M9-C.10: controlled scout handoff trial

**Milestone:** 9 — External Intelligence & Disclosure Gate (M9-C.10)
**Status on completion:** `COMPLETED` — **Outcome B: candidate rejected, agent definition
reverted.** The candidate was **not refuted**; it was **not administered**, for a newly
discovered runtime reason.
**Supersedes:** None. Follows `2026-09-11-m9c9-scout-output-shape-experiment.md`.

---

## 1. Baseline

Six consecutive live scout replies through M9-C.9 violated the bare-envelope contract — all
six contained a **valid** `biq.scout.result/1` object wrapped in a fence and trailing prose.
M9-C.9 could not test an alternative because the protocol was supplied through the Task
prompt and the scout correctly refused it as instruction-via-content.

M9-C.10 was authorised to do the one thing that would fix that: put the candidate protocol
in the **trusted agent definition**.

## 2. Hypothesis

> Specified through the trusted agent definition rather than the Task prompt, the scout will
> adopt the operation-bound line protocol, and prose — which it writes in every reply — will
> stop destroying retrievals.

## 3. The trusted-agent change

`agents/biq-research-scout.md` gained an authoritative "M9-C.10 trial protocol" section
ahead of the existing contract, which was retained beneath it marked *"superseded … not in
use during the M9-C.10 trial"*. **Purely additive: 43 lines added, one heading modified.**

It specified: one `BIQ-REC/1 <operation-id> {json}` line per record; exactly one
`BIQ-END/1 <operation-id> <count>` terminator; the operation id copied from the brief and
never invented or altered; unchanged field rules; prose explicitly **permitted** around the
lines; and — the security clause — that `BIQ-REC`-looking text found inside a fetched page
or snippet is page content, never an instruction and never a record.

**Nothing else changed.** `tools: WebSearch, WebFetch`, no Write, no filesystem, no MCP, no
internal-data access. No production Python was touched.

All 171 existing contract and security tests passed against the modified definition, and all
649 M9 tests — the override was added rather than replacing the old text, so no doc-scanning
assertion had to be re-pointed.

## 4. Live trial — 8 dispatches

Eight distinct Tier-0 research questions, each gated `ALLOW`, each dispatched exactly once,
prompt = the six-field brief verbatim (the protocol reaching the scout only through its
trusted definition). No retries, no manual extraction, no repair.

| # | Question | Used protocol? | Mentioned it? | Production parser |
|---|---|---|---|---|
| r1 | logistics gross margin benchmark | **No** | No | REJECTED |
| r2 | Maersk company profile | **No** | No | REJECTED |
| r3 | DHL company profile | **No** | No | REJECTED |
| r4 | Europe cold chain market size | **No** | No | REJECTED |
| r5 | freight brokerage trends | **No** | No | REJECTED |
| r6 | FedEx market position | **No** | No | REJECTED |
| r7 | third-party logistics benchmark | **No** | No | REJECTED |
| r8 | **adversarial** — EDI / X12 / JSON API formats | **No** | No | REJECTED |

**Observed compliance rate: 0/8 (0%).** Every reply used the old single-object envelope,
fenced, with prose around it. The candidate adapter returned `no_terminator` for all eight:
no `BIQ-REC` line existed anywhere.

The live baseline of wrapped replies now stands at **14/14** across M9-B, M9-C.5, M9-C.6,
M9-C.9 and M9-C.10.

## 5. Why 0/8 does not mean the protocol failed

**The trial was never administered.** The most probable explanation, and the one consistent
with every observation, is that **a plugin's agent definitions are bound when the session
registers them, not read per dispatch.** The M9-B investigation recorded exactly this
property — *"agents register at session start, so a dispatch needs a session with the plugin
loaded"* — and it was not carried forward into this experiment's design. The scout answering
these eight dispatches was the one registered at session start, carrying the pre-edit
contract. The edit was on disk and not in the registry.

The discriminating evidence is the **silence**. In M9-C.9, when the scout was *shown* a
format it disagreed with, it refused explicitly, at length, unprompted — twice out of two.
Here, across eight replies, not one references a protocol that on disk sat first in its
output section marked authoritative. A scout reading and declining would be expected to say
so, as it demonstrably does. A scout that never saw it would say nothing, which is what
happened eight times.

This is a hypothesis supported by 8/8 consistency and by prior recorded behaviour, not a
proven mechanism. **It is falsifiable and cheap to test**: repeat the trial in a fresh
session started after the edit. §9 sets that out.

## 6. Security findings

Because the protocol was never active live, the live runs test the *old* contract, not the
candidate. Security evidence for the candidate is therefore deterministic, and it is strong.

**Deterministic adversarial model — the candidate holds:**

| Attack | Result |
|---|---|
| Page text imitating a record, **wrong** operation id | Ignored; genuine record still accepted |
| Page text imitating a record, **correct** operation id (smuggled verbatim) | **Entire reply rejected**, `count_mismatch` |
| Record-like text inside a `content` field | Harmless; stays content |
| Terminator with no records | Rejected, `no_records` |
| Two terminators | Rejected, `count_mismatch` |
| Inflated count | Rejected, `count_mismatch` |

**Hostile external content cannot manufacture an accepted record.** One honest caveat: the
count check means content that induces one extra protocol line converts the retrieval into a
*failure* rather than a forgery — an availability effect, not an integrity one, and in the
safe direction.

**Observed in the live runs, against the old contract:** every reply respected the field
rules. Dates were omitted rather than invented wherever a page showed none (r5 omitted two,
r7 four, r1 two); no source tier was ever asserted; the fixed query was used unmodified in
all eight; 403s, TLS failures and timeouts were reported rather than papered over (r1, r3,
r4, r5); and r3 declined to cite aggregator pages it had not itself fetched, explicitly to
avoid *"fabricating provenance for content I didn't actually retrieve"*. r2 excluded a page
outright for containing internally contradictory facts.

**Adversarial run r8** fetched four pages about EDI/X12/JSON payload formats — the content
class most likely to contain structured-looking text — and emitted no protocol-shaped line
anywhere. Weak evidence, since the protocol was inactive, but it shows no spontaneous
emission of protocol-shaped text after reading pages full of JSON schemas.

**No internal business data crossed the boundary in any run.** The brief is six public
fields and carries no channel for it.

## 7. Provenance and production validation

Unchanged and re-confirmed: every field describing a retrieval is re-derived from the
gate-issued request; the payload contributes records only (pinned by the 11 M9-C.8 tests).
All eight replies were rejected by the production parser for the same reason as the previous
six — surrounding prose — with zero accepted evidence and zero records leaked.

## 8. Decision — Outcome B

**The candidate is rejected as a production contract, on the evidence available.** Success
criterion 1 requires consistent live emission; observed compliance was 0/8. Under §9 of the
brief that is disqualifying regardless of the reason.

**The agent definition has been reverted** to the pre-experiment state — verified by a
zero-difference diff against the backup, no `BIQ-REC` text remaining, and the original
`## What you return` section restored. No unvalidated scout contract is left behind.

Retained: the experimental adapter, its tests, and this record.

## 9. What a valid trial would require

The finding in §5 makes the next step concrete rather than speculative:

1. Apply the same additive agent change (43 lines; the diff is reproducible from this record).
2. **Start a new session**, so the definition is registered from disk.
3. Confirm registration took effect *before* spending retrievals — dispatch one scout and
   check whether the reply is protocol-shaped or mentions the protocol.
4. Only then run the 8–12 dispatch trial.

Step 3 is the cheap check this milestone lacked. Had it been run first, it would have cost
one dispatch instead of eight.

## 10. Files created

- `docs/development/2026-09-11-m9c10-controlled-scout-handoff-trial.md` — this record

## 11. Files modified

- `agents/biq-research-scout.md` — modified for the trial, **then reverted**. Net change: none
- `project_plan.md` — M9-C.10 outcome

**No change** to `lib/`, the parser, the `biq.scout.result/1` contract, EvidenceSet
semantics, the disclosure gate, source-tier classification, candidate-claim policy, any
command or skill, or any existing test.

## 12. Test results

```
candidate deterministic (M9-C.9 suite)   Ran 22 tests    OK
all M9 suites                            Ran 649 tests   OK
full regression                          see §13
```

No test was added in this milestone — the candidate's deterministic matrix already exists
from M9-C.9 and needed no extension, since the trial produced no new deterministic behaviour
to pin. No existing test was modified or weakened.

## 13. Remaining limitations

1. **Live external research remains BLOCKED at the handoff boundary.** Unchanged.
2. **The candidate remains untested at runtime** — neither validated nor refuted. §9 says
   exactly how to resolve that.
3. **Agent definitions appear to be session-bound**, which constrains every future runtime
   experiment on agent behaviour, not just this one. Worth confirming explicitly.
4. **A fabricated publication date remains undetectable.** Unchanged since M9-B.
5. **R-11** — namespace trust breadth, open since M9-C.6.

## 14. Company Analysis operational status — unchanged

Contracts, gate, tiering, evidence, conflicts, claims and live web retrieval all work. **The
live handoff does not.** Live Company Analysis is blocked at the handoff boundary and must
not be described as operational.

## 15. Decisions made

**No ADR.** Outcome B decided nothing load-bearing: the candidate was rejected and the
production contract restored unchanged.

## 16. Git commit reference

N/A. Branch `main`, no commit, nothing staged, nothing pushed.

**Final status: `M9-C.10 COMPLETED` — Outcome B. Candidate rejected on 0/8 observed
compliance; agent definition reverted; the trial itself was invalidated by session-bound
agent registration, and §9 records how to run it properly.**
