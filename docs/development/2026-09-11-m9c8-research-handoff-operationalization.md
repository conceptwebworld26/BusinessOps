# 2026-09-11 — M9-C.8: research handoff operationalization — investigation and outcome

**Milestone:** 9 — External Intelligence & Disclosure Gate (M9-C.8)
**Status on completion:** `COMPLETED` — **Outcome B: no safe supported handoff exists today**
**Supersedes:** None. Follows `2026-09-11-m9c7-scout-return-contract-enforcement.md`.

---

## 1. Prompt / task performed

Investigate whether a safe operational handoff architecture can be built without relying on
unsupported structured-output enforcement. Implement the smallest viable slice only if a
genuinely supported mechanism exists. No regex extraction, no permissive fences, no prose
stripping, no retries, no trust escalation, no custom MCP server. Keep the Company Analysis
operational status accurate. No sibling skill, no commit, no push.

## 2. Conclusion, stated first

> **No mechanism in the current runtime provides a trustworthy structured handoff from a
> model-mediated subagent into Python. The most attractive candidate — parent-model-mediated
> extraction — is not merely unsafe in degree but inverts the disclosure boundary the
> architecture is built on, and is rejected on that ground rather than on formatting.**

Nothing was implemented. The parser is untouched. What this milestone adds is the reasoning,
one architectural invariant pinned by tests, and an honest status for the feature.

## 3. Where trust changes hands

```
skill / command (markdown)          BusinessIQ-controlled
      ▼
parent model                        has file access, business data, full context
      ▼  Task(subagent_type=…, prompt=brief)
biq-research-scout                  WebSearch + WebFetch only. Cannot read business data
      ▼  WebSearch / WebFetch
retrieved pages                     hostile by assumption
      ▼
scout final message                 UNTRUSTED free text  ◄── trust is at its lowest here
      ▼
parse_result(payload, brief)        ◄══ THE BOUNDARY. Validates against a gate-issued brief
      ▼
normalise_records → EvidenceSet     BusinessIQ-controlled representation
      ▼
candidate claims                    policy-gated, never verified
```

The boundary is not only "is this JSON well-formed". It is the point where a **gate-issued
brief** is joined to **untrusted content**, and the brief wins every disagreement.

### The property that decides this milestone

Probed directly against the shipped code: a payload can carry records and **nothing else**.
Every field describing the retrieval is re-derived by `close_retrieval()` from its own
arguments, so a payload claiming `disclosure_tier: 2`, `destination: internal_db`,
`subject: "something else"`, `max_fetched: 999` changes none of them. Evidence ids are
computed locally; `trust` cannot be set; support is recomputed from local tiers.

**Whatever produces the records, the provenance is ours.** That is the invariant any
replacement handoff has to preserve, and it is now pinned by 11 tests.

## 4. Mechanisms investigated

| Mechanism | Exists? | Verdict |
|---|---|---|
| **A. Parent-model-mediated extraction** | Yes, trivially | **Rejected — inverts the boundary.** §5 |
| **B. Tool-mediated return with runtime schema validation** | **No** | Requires a tool whose input schema *is* the envelope. No built-in tool has one, and the only way to create one is a custom MCP server, excluded for v1. Nothing may be invented |
| **C. File-based handoff written by the scout** | Technically possible | **Rejected.** It requires granting the scout `Write`. The scout's lack of file access is the structural control behind ADR-0006/0009/0014 — it is *why* internal data cannot reach an external query. Trading it for output formatting would dismantle the milestone's central security property to fix a cosmetic one |
| **D. MCP return channel** | — | Excluded by the standing v1 decision: file-first, no custom MCP servers |
| **E. `TaskOutput` / background-task result** | Yes, but text | Deprecated, and for agent tasks it defers to the Agent result. Returns the same unstructured text. No structured channel |
| **F. Subagent-scoped `SubagentStop` hook writing the reply to a file** | **Genuinely available** | Does not solve this, but is the cleanest *future* option. §7 |

Mechanisms investigated and found not to exist are recorded in M9-C.7 and not re-derived
here: agent frontmatter output schema, Task dispatch schema parameter, structured output for
subagents.

## 5. Why parent-mediated extraction is rejected

This is the option worth taking seriously, because it is what actually happened by hand
during M9-C.5 and it would work today. The objection is not that it resembles regex.

**It moves authorship of the envelope from a context that cannot read business data to one
that can.**

The scout holds `WebSearch` and `WebFetch` and nothing else. That grant is the structural
reason ADR-0009's disclosure boundary is a property of the system rather than a promise:
internal data cannot reach an external query because the retrieving context cannot read it.
The parent model, by contrast, holds the file system, the dataset, the Business Context and
the entire conversation.

If the parent transcribes the envelope, then:

- **Provenance becomes unfalsifiable in the wrong direction.** Python would label as
  `UNTRUSTED_EXTERNAL_DATA` — external, retrieved, citable — bytes authored by the one
  context that has seen internal data. The label would be structurally wrong and nothing
  downstream could detect it.
- **A disclosure path opens that does not exist today.** Not maliciously; by ordinary
  helpfulness. A parent summarising a source "in context" can carry an internal figure into
  a field the evidence ledger will attribute to Reuters.
- **Injection gains a second hop.** Hostile page text already tries to instruct the scout.
  Under extraction it reaches a context with real capability, carrying an instruction about
  what to transcribe.
- **It is indistinguishable from the failure it replaces.** Python cannot tell a faithful
  transcription from an embellished one, so the strictness of `parse_result` would be
  preserved in form while its input became untrustworthy in a new way.

The current failure mode — a wrapped reply produces zero evidence — is loud, cheap and
honest. Extraction would replace it with a quiet path whose provenance claims are wrong.
That is a worse system, not a more usable one.

## 6. Threat model of the status quo

Answering the brief's questions against the boundary as it stands, since no new architecture
is adopted:

| Concern | Position today |
|---|---|
| **Trust** | Scout and page content influence records only; never the frame. §3 |
| **Injection — fake evidence, URLs, extra JSON** | A record without a citation is rejected; extra fields dropped and recorded; two envelopes or a nested envelope are refused outright (M9-C.1) |
| **Injection — fake tiers** | Impossible to honour: tier is recomputed locally from host identity, label-boundary matched since M9-C.6 |
| **Injection — fake dates** | **Residual risk, unchanged.** A fabricated publication date is not detectable. Undated is handled correctly; a plausible lie is not |
| **Provenance** | Operation, query, destination, tier, subject and bounds all gate-issued; evidence ids derived locally |
| **Integrity** | Operation and query echoes are *checked*, not adopted — a mismatch discards the whole reply |
| **Replay / duplication** | Operation echo binds a reply to its retrieval; duplicates are not counted as corroboration (M9-C.3) |
| **Disclosure** | The brief is six public fields; the scout has no channel to internal data. Preserved precisely because A and C were rejected |
| **Verification** | Python validates envelope, echoes, status, fields and bounds before reading a record; nothing reaches `verified=true` |

## 7. The cleanest future option, described but not implemented

Subagent frontmatter supports `hooks`, and a `SubagentStop` hook receives
`last_assistant_message` — the scout's exact final text. A hook runs as a local process, not
as the agent, so it needs no grant from the scout's tool list.

Such a hook could write the scout's reply **verbatim** to a session-scoped file that
`close_retrieval()` reads.

What that would and would not buy:

- **Would:** remove the parent model from the transcription path entirely. Python would
  validate the scout's actual bytes rather than a retyping — a real integrity gain over what
  M9-C.5 did by hand, and it preserves §3's invariant because the hook copies rather than
  authors.
- **Would not:** make live retrieval work. The file would contain the same wrapped text and
  the same strict parser would reject it. **It fixes authorship, not formatting.**

So it is not a solution to the operational blockage, and it is not proposed as one. It is
recorded because it is the only mechanism found that could carry a handoff without weakening
the boundary, and because any future work in this area should start from it rather than from
extraction. It would also require reversing the standing "no hook need identified" position
in `CLAUDE.md`, which is an owner decision.

## 8. What would actually unblock live research

Stated plainly because §7 does not, and the status in §9 depends on it. Three options, none
taken, all owner decisions:

1. **Accept a fenced envelope as the contract** — the parser already tolerates a bare fence
   via `_unfence`. This does *not* help alone: all four observed replies had prose *after*
   the fence.
2. **Change what the scout is asked to produce** so that the reply has no natural place for
   trailing commentary. M9-C.1 already tried the instructional half of this and it failed
   4/4; the untried half is changing the *shape of the task*, not the strength of the words.
3. **Surface the failure to the user** rather than treating it as an internal error, so a
   wrapped reply produces a visible "research unavailable — scout returned a malformed
   envelope" outcome instead of a silent dead end.

Option 3 is the only one that is purely presentational and risks nothing. It is not in this
milestone's scope.

## 9. Company Analysis operational status — accurate statement

| Component | Status |
|---|---|
| Deterministic tests | ✅ Passing |
| Research contracts, disclosure gate | ✅ Working |
| Source-tier classification | ✅ Working, hardened (M9-C.6) |
| Evidence set, conflict transport, candidate claims | ✅ Working |
| Live scout web retrieval | ✅ Performs real research |
| **Live handoff into the evidence system** | ❌ **BLOCKED** |

**Live Company Analysis is blocked at the handoff boundary.** Every component exists and is
correct; the feature is not operational end-to-end, and must not be described as such.

## 10. Files created

- `tests/negative/test_m9c8_handoff_provenance.py` — 11 tests
- `docs/development/2026-09-11-m9c8-research-handoff-operationalization.md` — this record

## 11. Files modified

- `architecture.md` — the handoff trust boundary and why authorship matters
- `project_plan.md` — M9-C.8 outcome; the blocked status restated accurately

**No change** to `lib/` (parser included), any agent, command, skill or ADR, and no existing
test was modified.

## 12. Test results

```
focused (M9-C.8)   Ran 11 tests    OK
all M9 suites      Ran 627 tests   OK
full regression    Ran 1790 tests in 113.429s   OK (skipped=19)
                   ran 1790 | failures 0 | errors 0 | skipped 19
```

Baseline 1,779 at M9-C.7; +11 is exactly this task. **Skips unchanged at 19.**

One test was corrected during development: `test_a_payload_cannot_declare_its_own_support_verdict`
was written as a tautology that asserted nothing. It now uses a tier-C record against a
payload claiming `supported`, and asserts the recomputed verdict is `unsupported`.

## 13. Live verification — not performed

The brief permits it only where it establishes something material. No mechanism was
implemented, so there is nothing new to exercise, and re-observing the known wrapped-output
behaviour would spend a real retrieval to confirm a result already recorded four times.

## 14. Decisions made

**No ADR.** The brief is explicit that an investigation does not earn one, and this
milestone decided nothing load-bearing: it rejected three candidate architectures and left
the shipped design in place. ADR-0015 already owns this seam.

The decision that *would* need an ADR — adopting hook-mediated handoff (§7), or changing
what the scout is asked to produce (§8) — has deliberately not been taken.

## 15. Remaining limitations

1. **Live external research is unusable end-to-end.** The single blocking issue; §8 lists
   the untaken options.
2. **A fabricated publication date remains undetectable.** Unchanged since M9-B.
3. **R-11** — namespace trust breadth, open since M9-C.6.
4. **Three sibling research skills and four commands** remain unbuilt — and building them now
   would multiply a capability that cannot complete a live run.

## 16. Git commit reference

N/A. Branch `main`, no commit, nothing staged, nothing pushed.

**Final status: `M9-C.8 COMPLETED` — Outcome B. No safe supported handoff exists; the
boundary and the parser are unchanged.**
