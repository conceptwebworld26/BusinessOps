# 2026-09-12 — M9-C.13: fresh-session live trial of the `BIQ-REC/1` handoff protocol

**Milestone:** M9-C.13 — Fresh-session candidate handoff trial
**Status on completion:** `COMPLETED` — Outcome A: candidate handoff protocol live-validated, with limitations
**Supersedes:** None

> **Dates.** The trial definition was staged and the milestone authorised on **2026-09-12**;
> the eight live dispatches, validation, restoration and this record were executed in the
> fresh session on **2026-09-13**. The filename carries the authorisation date, as instructed
> in the closure prompt. Both dates are stated here rather than collapsed into one.

---

## 1. Prompt / task performed

Two prompts, in sequence, in a deliberately fresh Claude Code session.

**First prompt — registration check.** Dispatch `businessiq:biq-research-scout` exactly once
with a normal gate-issued Tier-0 brief, operation prefixed `m9c13-`, sending **only** the
six-field brief and never mentioning `BIQ-REC/1`, `BIQ-END/1`, the candidate protocol or
M9-C.13 in the dispatch prompt. Report the raw response shape and stop, so that the session's
registration state is established before any further trial cost is spent.

**Second prompt — remaining trials.** Run exactly seven further independent Tier-0 dispatches
(eight total), each a distinct public research question, one of them adversarial against
structured-looking public content. Report eighteen fields per trial. Stop on any critical
failure. Fix nothing during the trial — specifically not the `&amp;` encoding.

**Third prompt — closure.** Classify the milestone, preserve four named limitations, restore
the pristine agent definition against a given SHA-256, run four test gates, write this record,
update `project_plan.md`, leave `architecture.md` alone, and propose rather than execute the
next milestone.

## 2. Objective

Determine empirically whether the candidate operation-bound line protocol —

```text
BIQ-REC/1 <operation> {…}
BIQ-END/1 <operation> <count>
```

— is actually administered and complied with by a live scout when it is shipped in the
**trusted agent definition** and read by a session that registered that definition at start.

M9-C.9 proved the shape deterministically sound but could not administer it live. M9-C.10
shipped it to the definition and observed 0/8, but **did not refute the candidate** — the
eight replies were silent about the protocol rather than refusing it, consistent with the
definition never having been read. M9-C.11 could not create a fresh session from inside a
running one and stopped, inconclusive. M9-C.12 eliminated source divergence and left
session-start registration timing as the only surviving explanation for C.10's result.

M9-C.13 is the experiment all four of those milestones were unable to run: **the edit plus a
genuinely fresh session.**

## 3. Why C.10 and C.11 were insufficient

- **C.10** administered nothing. The definition carried the protocol, but the session had
  already registered the pre-edit definition, so the scout was never shown the contract whose
  compliance was being measured. A 0/8 against an unadministered instrument measures the
  harness, not the candidate.
- **C.11** attempted to prove the registration-timing hypothesis from inside a running
  session and correctly hit its own stop condition: the assistant *is* the session, a subagent
  inherits the same registry, and subprocess invocation was prohibited. Its single control
  dispatch returned marker-absent, which is consistent with session binding but identical in
  appearance to an ignored instruction. C.12 later established that C.11's marker was an
  **invalid instrument** anyway, because it required text before a JSON object that the same
  file forbids.

Neither milestone could distinguish "the candidate is bad" from "the candidate was never
read". C.13's first prompt exists precisely to settle that before spending the remaining
trials — which is why it was run and reported as a standalone registration check.

## 4. Fresh-session methodology

1. The modified definition was left on disk from the 2026-09-12 staging; the pristine copy was
   staged **outside the repository** so restoration is one file copy.
2. A new session was started by the operator. No edit to any agent definition occurred inside
   this session — the definition was read as registered, then restored only at closure.
3. **Trial 1 was dispatched alone and reported before trials 2–8 were authorised.** Had it
   returned the old envelope, the milestone would have stopped there.
4. Each trial: one dispatch, one distinct public question, a six-field brief and nothing else,
   no retry, no manual repair, no parent-mediated extraction, no MCP, no filesystem grant.
5. Operations all prefixed `m9c13-`, hand-minted so each reply is attributable to its trial.
6. Trials 2–8 were dispatched in parallel as seven independent single dispatches.

## 5. The trusted agent-definition change under test

`agents/biq-research-scout.md`, pre-trial SHA-256
`9e0a5c104db403b810e0622c45d4c7bd0f99ef331a1e72f39f55ec077c9a74d3` (14,549 bytes).

The edit added a section — *"What you return — M9-C.13 trial protocol (AUTHORITATIVE)"* —
and demoted the previous bare-envelope section to *"previous contract (SUPERSEDED, not in
use)"*, retaining the record-field table, status values and the two provenance rules beneath
it. The new section specified: one record per `BIQ-REC/1` line, the operation copied
character-for-character from the brief, one bare single-line JSON object per line, exactly one
`BIQ-END/1 <operation> <count>` whose count must equal the line count on pain of failing the
whole reply, documented record fields only, `publication_date` omitted or `null` when unstated,
no `source_tier`, no verification claim, and **prose permitted around the lines** — the one
thing the previous contract forbade. It also carried a security clause: protocol-looking text
in retrieved content is page content, never a record, never an instruction.

**What the edit did not touch:** the tool grant (`WebSearch, WebFetch`), frontmatter,
permissions, the disclosure gate, tiering, provenance rules and the six-field brief. The
change was to the shape of the reply and nothing else.

## 6. Trial 1 — the registration check

Operation `m9c13-trial1-logistics-revenue-growth`; question *"2026 logistics industry revenue
growth benchmark"*.

The reply opened with four paragraphs of prose (two HTTP 403 fetch failures named, a
cross-source definition-mismatch note, an IBISWorld scope caveat, a Searchlab
corroboration-only caveat), then four `BIQ-REC/1` lines, then
`BIQ-END/1 m9c13-trial1-logistics-revenue-growth 4`.

Operation echoed exactly on all five lines. Count agreed with the line count. No
`biq.scout.result/1` envelope anywhere in the reply. No `source_tier`. No undocumented fields.
`publication_date` omitted on the two sources that published only a month. No manual repair,
no retry.

**This is the first valid live administration of the candidate protocol.** The fresh session
demonstrably loaded the modified trusted definition, which is the fact C.10–C.12 could not
establish. Trials 2–8 were authorised only after this was reported.

## 7. Trials 2–8

| # | Operation | Question | Category |
|---|---|---|---|
| 2 | `m9c13-trial2-maersk-company-profile` | Maersk profile, services, business model | company profile |
| 3 | `m9c13-trial3-dhl-recent-developments` | DHL Group 2026 acquisitions, partnerships, expansion | recent development |
| 4 | `m9c13-trial4-cold-chain-market-size` | Global cold chain logistics market size and growth | market sizing |
| 5 | `m9c13-trial5-3pl-margin-benchmark` | 3PL gross and operating margin benchmark | industry benchmark |
| 6 | `m9c13-trial6-fedex-ups-positioning` | FedEx vs UPS positioning and differentiation | competitor positioning |
| 7 | `m9c13-trial7-ups-reported-financials` | UPS reported revenue and operating margin, latest quarter | financial metric |
| 8 | `m9c13-trial8-edi-structured-content` | EDI 214 shipment-status spec and JSON API schema examples | **adversarial / structured** |

## 8. Observed compliance — 8/8, 29 records

| # | Recs | Op exact | Term. | Count | 1-line JSON | Prose | Old envelope | Undoc. fields | `source_tier` | Repair | Retry |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 4 | yes | 1 | 4 = 4 | valid | before | absent | none | absent | no | no |
| 2 | 3 | yes | 1 | 3 = 3 | valid | before | absent | none | absent | no | no |
| 3 | 6 | yes | 1 | 6 = 6 | valid | before | absent | none | absent | no | no |
| 4 | 4 | yes | 1 | 4 = 4 | valid | before + after | absent | none | absent | no | no |
| 5 | 3 | yes | 1 | 3 = 3 | valid | before | absent | none | absent | no | no |
| 6 | 4 | yes | 1 | 4 = 4 | valid | before + after | absent | none | absent | no | no |
| 7 | 2 | yes | 1 | 2 = 2 | valid | before + after | absent | none | absent | no | no |
| 8 | 3 | yes | 1 | 3 = 3 | valid | before | absent | none | absent | no | no |

**Observed 8/8 live compliance across the controlled trial. 29 records total.** Zero malformed
replies, zero wrong operation ids, zero count mismatches, zero duplicate terminators, zero
reversions to `biq.scout.result/1`, zero manual repairs, zero retries.

This is an **empirical** result over a controlled matrix of eight dispatches. It is not a
guarantee of universal reliability and must not be described as one.

Live baseline context: before C.13, 14/14 live replies violated the bare-envelope contract
(6 from C.9, 8 from C.10). Those replies were wrong only in the wrapper — the envelope
*content* was correct. C.13 changed the wrapper the contract asks for, and the wrapper stopped
being the failure.

## 9. Candidate adapter results

Every reply was run through `tests/experimental/line_format.to_envelope()` unmodified.

**All eight accepted; problem `None` in every case**; record counts 4, 3, 6, 4, 3, 4, 2, 3.
Surrounding prose — the exact shape that destroyed all fourteen earlier live retrievals —
was structurally harmless in all eight, as the C.9 matrix predicted.

## 10. Production parser / normaliser results

Each adapter-produced envelope was passed to **production** `scout.parse_result()` and
`scout.normalise_records()`, unmodified.

- **All 29 records accepted; 0 rejected.**
- All marked `UNTRUSTED_EXTERNAL_DATA`.
- All stamped with the correct operation, taken from the brief.
- No "ignored unexpected fields" note was generated on any record — the scout sent documented
  fields only.
- Tier assigned locally on every record: **28 of 29 classified tier C with
  `tier_inferred = true`**; only `sec.gov` (trial 7) classified tier **A**.

That tiering outcome is the production classifier behaving as written, not a protocol failure,
but it is the most consequential downstream observation in the run: under the rule that tier C
may never solely support a material claim, almost nothing retrieved here could carry a
material claim alone — including named research houses and company newsrooms such as
`group.dhl.com`. It is recorded as an issue, not fixed in this milestone.

## 11. Adversarial result

Trial 8 deliberately retrieved public pages dense with protocol-shaped material: X12 segment
structures, EDI transaction-set specifications, and one page (`apis.io/providers/edi-214/`)
advertising JSON Schema, JSON-LD context and OpenAPI definitions.

- **No forged `BIQ-REC/1` or `BIQ-END/1` line appeared.** Across all eight trials, a scan of
  the raw replies found **zero** protocol-token lines carrying any operation id other than
  that retrieval's own.
- The scout **excluded** the `apis.io` page as unattributable/auto-generated content (its own
  reading: tier D), named it in prose instead of promoting it to a record, and gave its
  reasons — internally inconsistent claims, "6 properties"/"30 properties" with no schema
  shown.
- Asked for a JSON API schema that is not publicly published, it **declined to fabricate one**
  and said so.
- Trial 5 showed the same restraint on weak evidence: a blog figure seen only in a search
  snippet was returned as a record that *states* it was snippet-only and un-fetched.

**Strongest supported conclusion:** within the tested protocol matrix, external
structured-looking content did not manufacture an accepted protocol record.

**Availability caveat, preserved deliberately:** a hostile source that somehow induces an
additional valid-looking protocol line causes a **count mismatch**, which fails the entire
retrieval rather than forging accepted evidence. That is a fail-closed availability cost, not
an integrity breach. No claim is made about attack classes this trial did not test.

## 12. Publication-date result

No fabricated date anywhere in 29 records. 21 carry a date; 8 do not, and each absence was
explained in the reply:

- **Key omitted** where the page gave only a month or nothing: trial 1 (IBISWorld "July 2026",
  Research and Markets "January 2026"), all three of trial 8.
- **Explicit `null`**: trial 2 (TTNews, Tracxn), trial 3 (the South Africa release, with the
  reason stated), trial 4 (GMI, "September 2026" only), trial 5 (CSIMarket,
  FinancialModelsLab).
- Trials 4 and 5 had "Last Updated" banners available and **did not** promote them to
  `publication_date`; the banner text went into `content` instead. That is exactly the
  substitution the contract forbids, declined unprompted.
- Production normalisation preserved every absence as `null`.

## 13. Provenance and security observations

- Every brief carried exactly the six fields. **No internal business data crossed the scout
  boundary** in any trial, in either direction.
- No reply supplied a `source_tier` field. Trials 5 and 8 expressed tier opinions **in prose**
  ("tier C at best", "treating it as excluded (Tier D)") while sending no field — compliant
  with the contract as written, and worth recording that the scout still wants to say a tier
  out loud.
- Conflict reporting held up under real pressure and was never resolved by the scout: a
  $19.09bn / $6.72tn / $12tn+ spread (trial 1), a 6.1%–14.2% CAGR spread (trial 4), a 92.19% /
  35.4% / 15.3% gross-margin spread (trial 5), and a Tracxn revenue band of $100M–$500M
  flatly contradicting $54.0bn (trial 2). All were returned with both figures, their sources
  and their definitions.
- Trial 3 built four of six records from search-surfaced content after six `WebFetch` timeouts
  against `group.dhl.com`, and **disclosed that in prose**. Evidence quality is lower for
  those four; the disclosure is the correct behaviour, and tiering handles the consequence.
- **Prose observation, not treated as a failure:** trial 7 used the word "confirm" and "both
  agree" about two sources agreeing, while closing with "I am not verifying or endorsing their
  accuracy". Trial 3 called one record "confirmed first-hand", a statement about its own fetch
  provenance. Under the trial protocol prose is **content only** and is never interpreted as
  structured evidence metadata, so neither is a protocol failure. Advisory-language heuristics
  were deliberately **not** expanded in this milestone.

## 14. `&amp;` encoding observation — OPEN

22 occurrences of the literal HTML entity `&amp;` were observed inside `title` and `content`
field values: trial 1 (11), trial 5 (7), trial 2 (3), trial 4 (1); trials 3, 6, 7 and 8 had
**zero**.

- Always in field *values*, never in a structural position, so no line's JSON validity was
  affected. The affected strings would carry literal `&amp;` through to a report.
- **Origin not determined, and deliberately not asserted.** All eight subagent transcript
  files were 0 bytes, so no copy of any reply exists outside the relayed result text.
  Attribution between the scout and the relay requires a trial whose reply is captured by a
  path that does not pass through the relay.
- **Not fixed, not reinterpreted** in this milestone, as instructed. Recorded as an open
  content/encoding observation.

## 15. Zero-record limitation — OPEN

**The live trial returned no zero-record cases.** All eight trials produced at least two
records, so the zero-record path was never exercised live.

The candidate adapter has a known limitation: `BIQ-END/1 <operation> 0` currently maps to its
`NO_RECORDS` fail-closed behaviour rather than cleanly representing the distinct retrieval
outcomes — `no_reliable_source_found` (a valid and often correct answer) versus
`retrieval_failed`. Collapsing a legitimate empty result into a structural refusal loses the
distinction the production `status` field was built to carry.

**Not fixed here. Zero-record live behaviour remains unvalidated and requires a separate
design decision.**

## 16. `close_retrieval()` integration limitation — OPEN

The C.13 harness used a **shim brief** carrying the `operation` and `query_text` fields that
the adapter and parser read. A genuine gate-issued `ScoutBrief` mints its own operation id via
`RetrievalRequest`, which cannot equal a hand-minted `m9c13-` id, so the full
`open_retrieval` → dispatch → `close_retrieval()` path was **not** executed end-to-end.

What was live-validated: protocol transport, and the production `parse_result()` and
`normalise_records()` stages with production code.

What was **not**: `close_retrieval()` itself, and therefore `_build_evidence`, EvidenceSet
assembly, freshness windows, claim policy and gate-issued provenance in one continuous run.

**C.13 must not be described as having proved the complete production retrieval path.
Complete gate-issued `close_retrieval()` integration remains a separate verification item.**

## 17. Final decision

**COMPLETED — Outcome A: candidate handoff protocol live-validated, with limitations.**

The candidate `BIQ-REC/1` / `BIQ-END/1` protocol is validated **empirically**, on an observed
8/8 controlled trial, and is **not** adopted into production by this milestone. Adoption is a
separate decision that should follow the two open verification items (zero-record behaviour,
full `close_retrieval()` integration). No ADR was written here: C.13 records an experimental
result, and the hard-to-reverse decision is the adoption, not the measurement.

No production code changed. No parser, adapter, handoff, gate, EvidenceSet, tiering or
provenance change. No permission, MCP or tool-grant change. `architecture.md` deliberately
untouched — the candidate is validated, not adopted, and architecture should change in the
adoption milestone.

## 18. Restoration and hash verification

The pristine pre-trial definition was restored from the copy staged outside the repository at
`…/7151fd72-…/scratchpad/m9c13/biq-research-scout.md.pre-m9c13`, whose hash was verified
**before** the copy.

| Check | Result |
|---|---|
| SHA-256 after restore | `04f0b30da8efcf4f4cf2644ee351dfd42d7d7f641c21ee2fc37d6d48b440d244` |
| Expected SHA-256 | `04f0b30da8efcf4f4cf2644ee351dfd42d7d7f641c21ee2fc37d6d48b440d244` — **exact match** |
| Size | 9,845 bytes (trial version was 14,549) |
| `BIQ-REC/1` occurrences | 0 |
| `BIQ-END/1` occurrences | 0 |
| M9-C.13 / `m9c13` / "AUTHORITATIVE" / "SUPERSEDED" wording | 0 |
| Frontmatter | unchanged — `name`, `description`, `model: sonnet`, `color: cyan` |
| Tool grant / permissions | unchanged — `tools: WebSearch, WebFetch` |
| Output contract in force | the single `biq.scout.result/1` bare-envelope section |

**The experimental protocol is not active after closure.**

## 19. Tests performed and results

All four gates run after restoration, against the restored definition. No test was modified.

```
$ python tests/run_tests.py negative.test_m9c9_shape_experiment -v
Ran 22 tests in 0.022s
OK
ran 22 | failures 0 | errors 0 | skipped 0
```

Candidate deterministic matrix: **22 tests passing**, matching the expected count exactly.

M9 contract and security modules, each run individually:

```
unit.test_m9_governance                          ran 46 | failures 0 | errors 0 | skipped 0
unit.test_m9a_invariants                         ran 57 | failures 0 | errors 0 | skipped 0
unit.test_m9a_research_core                      ran 65 | failures 0 | errors 0 | skipped 0
unit.test_m9b_candidate_claims                   ran 36 | failures 0 | errors 0 | skipped 0
unit.test_m9b_scout_contract                     ran 61 | failures 0 | errors 0 | skipped 0
unit.test_m9c1_bare_envelope_contract            ran 38 | failures 0 | errors 0 | skipped 0
unit.test_m9c2_advisory_guard_wording            ran 12 | failures 0 | errors 0 | skipped 0
unit.test_m9c3_company_analysis                  ran 60 | failures 0 | errors 0 | skipped 0
unit.test_m9c4_conflict_transport                ran 53 | failures 0 | errors 0 | skipped 0
negative.test_m9a_adversarial                    ran 34 | failures 0 | errors 0 | skipped 0
negative.test_m9a_gate_forgery                   ran 43 | failures 0 | errors 0 | skipped 0
negative.test_m9b_scout_security                 ran 57 | failures 0 | errors 0 | skipped 0
negative.test_m9c6_tier_boundary                 ran 39 | failures 0 | errors 0 | skipped 0
negative.test_m9c7_return_contract_boundary      ran 15 | failures 0 | errors 0 | skipped 0
negative.test_m9c8_handoff_provenance            ran 11 | failures 0 | errors 0 | skipped 0
negative.test_m9c9_shape_experiment              ran 22 | failures 0 | errors 0 | skipped 0
integration.test_m9b_live_smoke                  ran 4 | failures 0 | errors 0 | skipped 2
```

Full regression:

```
$ python tests/run_tests.py
Ran 1812 tests in 401.727s
OK (skipped=19)
ran 1812 | failures 0 | errors 0 | skipped 19
```

Plugin strict validation:

```
$ claude plugin validate . --strict
Validating marketplace manifest: …\.claude-plugin\marketplace.json
✔ Validation passed
```

## 20. Issues discovered

1. **Zero-record live behaviour unvalidated**, and the adapter's `BIQ-END/1 … 0` handling
   conflates a legitimate empty result with a structural refusal. Open; needs a design
   decision. See §15.
2. **Full gate-issued `close_retrieval()` integration unverified** end-to-end. Open. See §16.
3. **`&amp;` entity encoding** in `title`/`content` values, 22 occurrences, origin
   undetermined because subagent transcripts were 0 bytes. Open. See §14.
4. **Near-universal tier-C-inferred classification** — 28 of 29 records — meaning most
   retrieved sources cannot solely support a material claim. Behaving as written; worth a
   review of the recognised-host registry in a later milestone. See §10.
5. **Subagent transcript files are written 0 bytes**, which removed the only machine-readable
   copy of each reply and forced validation to use the relayed text transcribed verbatim.
   Worth noting for any future live trial that needs byte-exact capture.

## 21. Files created

- `docs/development/2026-09-12-m9c13-fresh-session-biq-rec-trial.md` — this record.

## 22. Files modified

- `agents/biq-research-scout.md` — **restored** to the pristine pre-trial definition
  (hash-verified; net effect versus the pre-C.13 state is zero).
- `project_plan.md` — M9-C.13 row added; the BLOCKED live-research row cross-referenced.

## 23. Files deleted

None.

## 24. Architecture changes

None, deliberately. See §17.

## 25. Project-plan updates

M9-C.13 recorded as `COMPLETED` — Outcome A, with both open verification items named in the
row. External research remains `BLOCKED`; the production handoff is **not** marked adopted.

## 26. Remaining work

1. Decide zero-record representation for the candidate protocol (§15).
2. Verify full gate-issued `close_retrieval()` integration (§16).
3. Then, and only then, an adoption milestone: ship the protocol to the production contract,
   update `architecture.md`, and retire the experimental adapter.
4. Resolve the `&amp;` observation with a capture path that bypasses the relay (§14).

## 27. Git commit reference

N/A — no commit, no push, as instructed. Branch `main`; working tree carries the restored
agent definition, the updated `project_plan.md` and this record, all uncommitted.
