# 2026-09-11 — M9-C.7: scout return-contract enforcement — investigation and outcome

**Milestone:** 9 — External Intelligence & Disclosure Gate (M9-C.7)
**Status on completion:** `COMPLETED` — **Outcome B: no reliable runtime enforcement exists**
**Supersedes:** None.

---

## 1. Prompt / task performed

Investigate whether the real model-mediated scout runtime can **enforce** the M9-C.1 return
contract. Implement the smallest safe solution if a genuinely supported mechanism exists;
otherwise document the limitation and leave the fail-closed boundary intact. Do not invent a
mechanism, weaken the parser, extract JSON from prose, strip fences, retry, or accept wrapped
responses. No sibling skill, no command, no commit, no push.

## 2. Conclusion, stated first

> **The current model-mediated runtime provides no reliable machine-enforced mechanism for
> requiring a subagent to emit an exact bare JSON envelope. BusinessIQ therefore treats the
> scout response as untrusted model output and relies on strict fail-closed validation at the
> handoff boundary.**

Nothing was implemented to change that. The parser is unchanged. What this milestone adds is
the evidence for the conclusion, and tests that stop the conclusion being quietly reversed.

## 3. The runtime seam

```
skill / command (markdown)
      │  instructs
      ▼
    parent model ──Task(subagent_type="businessiq:biq-research-scout", prompt=brief)──► scout
      │                                                          WebSearch / WebFetch
      │  ◄──────── final assistant message, unstructured text ──────────────────────────┘
      ▼
  parse_result(payload, brief)        ← the trust boundary
      ▼
  normalise_records → EvidenceSet
```

The leg that returns is a **free-text assistant message**. There is no typed channel, no
envelope negotiated by the runtime, and no point between the scout and `parse_result()` at
which anything but the model decides the bytes.

## 4. Mechanisms investigated

| Mechanism | Exists? | Can it enforce the envelope? |
|---|---|---|
| Agent frontmatter output schema | **No** | The subagent runtime supports 17 frontmatter fields — `name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `effort`, `isolation`, `color`, `initialPrompt`, `experimental`. **None constrains output.** |
| `Task` / Agent dispatch parameter | **No** | The dispatch accepts `description`, `prompt`, `subagent_type`, `model`, `isolation`. No schema, no response format |
| Structured output / JSON mode for subagents | **No** | Documented behaviour is that subagents return unstructured text summaries. No output-schema concept exists at this seam |
| `SubagentStop` hook | **Partly** | It receives `last_assistant_message` and can **block** — but it **cannot rewrite**. Blocking means the subagent *continues*, i.e. a retry loop. See §6 |
| Stronger agent instructions | Yes | **Already tried and measured — it failed.** See §5 |
| Parent-model post-processing | Yes | This is manual extraction. It is the thing the milestone forbids, and §7 says why |
| Custom MCP server, `claude -p`, subprocess, second dispatch | — | Excluded by the brief, and by ADR-0014/ADR-0015 |

### An empirical finding about the validator

A scratch plugin was built declaring five invented agent frontmatter fields —
`output-schema`, `response-format`, `structured-output`, `output_format`, `schema`.
`claude plugin validate --strict` reported **only** a missing-author warning: the unknown
fields were **silently ignored**.

This matters more than it first appears. It means a future maintainer can "add enforcement"
by writing `output-schema:` into the agent file, see a clean validation, and believe the
contract is now machine-enforced when nothing at all has changed. That is the precise hazard
ADR-0001 was written about, and it is now guarded by a test.

## 5. Instructional compliance is not enforcement — with numbers

M9-C.1 rewrote the contract to be unambiguous: bare object, starts `{`, ends `}`, no fences,
no prose either side, no notes to the caller, with the consequence spelled out and sanctioned
channels offered for the caveats the scout kept wanting to add.

Live dispatches **since** that hardening:

| Run | Dispatches | Wrapped replies |
|---|---|---|
| M9-C.5 Company Analysis | 3 | **3** |
| M9-C.6 live classifier check | 1 | **1** |
| **Total** | **4** | **4** |

Every one returned a fenced envelope with trailing prose — "Notes on process", "A few notes
on this batch", "Notes for the parent agent (outside the returned envelope)". The envelope
*inside* each was well-formed and contract-conformant; the wrapper was the violation.

Four out of four is not proof of impossibility, but it is a measured result rather than an
argument: the strongest available instructional lever was pulled, and behaviour did not
change. Declaring the instruction a security boundary after that would be asserting a
control that observation contradicts.

## 6. Why the `SubagentStop` hook is not the answer

It is the only mechanism that comes close, so it is worth being precise about why it was
rejected rather than dismissing it.

It can see the final message and can block by exiting 2. It **cannot rewrite** — there is no
`updatedMessage` field for this event. So the only available action on a malformed reply is
"do not finish", which makes the subagent **continue**. That is:

- **a retry**, which the brief forbids outright;
- **a threat to the one-shot guarantee** — a continuing scout holds live `WebSearch` and
  `WebFetch`, so "try again" can mean "retrieve again", and M9-B's exactly-one-retrieval
  property is a disclosure property, not a performance one;
- **unbounded without a turn cap**, and capping it just relocates the failure;
- **still not a guarantee** — a scout that wrapped its reply once may wrap it again, and the
  hook cannot make it not.

A mechanism that converts a clean failure into a loop with the same failure at the end is
worse than the clean failure.

## 7. Why the parser must stay fail-closed

The temptation is real and should be named: in all four live runs the envelope inside the
prose was **valid**. Extracting it would have turned four "failed" retrievals into four
successful analyses, and it is one regular expression.

It is refused because the extraction would be a **trust decision made by pattern-matching on
untrusted text**. The scout's reply is model output that has just processed adversarial web
content. Deciding which span of that text is "the real envelope" is exactly the judgement an
attacker wants to influence — a retrieved page that induces a second JSON object in the reply
turns "find the JSON" into "find the attacker's JSON". `test_two_envelopes_concatenated` and
`test_the_envelope_nested_inside_a_wrapper_object` in M9-C.1 already pin both shapes as
failures.

The boundary is therefore: **the entire reply is the envelope, or there is no evidence.**
Strict, cheap, and impossible to argue with at the wrong moment.

## 8. Security analysis of the resulting boundary

Against the ten questions the brief poses — with no enforcement mechanism adopted, all of
them remain true of the *input*, and every one is answered by validation rather than by trust:

| Can the model still… | Yes/No | What stops it mattering |
|---|---|---|
| emit arbitrary prose | Yes | Whole reply rejected; no evidence produced |
| emit Markdown fences | Yes | A bare fence alone is tolerated by `_unfence`; fences **with prose** are rejected (pinned, M9-C.1) |
| emit malformed JSON | Yes | Rejected, structured failure |
| inject extra fields | Yes | Dropped against `ACCEPTED_RECORD_FIELDS`, and the drop is recorded |
| alter operation/query echoes | Yes | Both checked against the brief; mismatch is refused |
| fabricate dates | Yes | Never inferred; a fabricated date is *not* detectable — this remains a genuine residual risk, documented since M9-B |
| fabricate source tiers | Yes | Ignored entirely; tier is recomputed locally from host identity (M9-C.6) |
| have web content shape the envelope | Yes | Content is `UNTRUSTED_EXTERNAL_DATA`, withheld from instruction context, and cannot raise a tier or a disclosure tier |
| provide a trustworthy machine-readable boundary | **No** | This is the finding. The boundary is ours, not the runtime's |
| be independently validated by Python | **Yes** | Envelope name, operation, query, status, fields, bounds — all checked before a record is read |

The honest summary: the runtime guarantees **nothing** about the reply's shape. It does
guarantee the scout's **tool grant**, which is the control that actually matters — a context
holding `WebSearch` and `WebFetch` and nothing else cannot read business data whatever it
writes in its reply.

## 9. Changes made

No implementation change. One test file, and documentation.

**`tests/negative/test_m9c7_return_contract_boundary.py`** — 15 tests in three classes,
covering only what this investigation newly justifies (the M9-C.1 rejection matrix is not
duplicated):

| Class | Tests | Covers |
|---|---|---|
| `TestNoInertEnforcementIsDeclared` | 4 | The scout declares only fields the runtime actually supports, checked against the documented 17; **none of thirteen plausible-sounding enforcement fields** is declared; the tool grant is still exactly `WebSearch, WebFetch`; the contract is still stated for the model |
| `TestObservedLiveShapesAreRejected` | 5 | All four real wrapped shapes from M9-B, M9-C.5 (profile and positioning) and M9-C.6 are failures producing no evidence — and the same envelope, bare, is accepted |
| `TestViolationIsReportedHonestly` | 6 | The failure names the expected envelope, says nothing could be cited, is structured rather than an exception, leaks no records, never raises, and cannot be turned into a claim |

## 10. Files created

- `tests/negative/test_m9c7_return_contract_boundary.py`
- `docs/development/2026-09-11-m9c7-scout-return-contract-enforcement.md` — this record

## 11. Files modified

- `architecture.md` — where the scout trust boundary sits, and why
- `project_plan.md` — M9-C.7 outcome

**No change** to `lib/` (parser included), `agents/biq-research-scout.md`,
`commands/retrieval-slice.md`, any skill, any ADR, or any existing test.

## 12. Test results

```
focused (M9-C.7)   Ran 15 tests    OK
all M9 suites      Ran 616 tests   OK
full regression    Ran 1779 tests in 115.118s   OK (skipped=19)
                   ran 1779 | failures 0 | errors 0 | skipped 19
```

Baseline 1,764 at M9-C.6; +15 is exactly this task. **Skips unchanged at 19.** No existing
test was modified or weakened.

## 13. Live verification — deliberately not repeated

The brief permits live verification "only if it can materially establish the conclusion".
**It cannot add anything here.** Four post-hardening dispatches already returned wrapped
output, one of them in this same session with the raw reply fed through the boundary
uncompensated and correctly failing closed. A fifth dispatch would spend a real web retrieval
to re-observe a result already recorded four times, and a *passing* fifth run would not
establish enforcement either — one compliant reply is not a guarantee, which is the entire
point of §5. The existing evidence is used instead, and the four shapes are now pinned
deterministically so they re-run on every suite execution.

## 14. Decisions made

**No ADR.** The load-bearing decision at this seam is already ADR-0015 (scout dispatch is
model-mediated; the orchestration surface is markdown). M9-C.7 discovered a *property* of
that seam rather than deciding anything new: no enforcement mechanism exists, so the
fail-closed boundary that M9-A already shipped remains the design. Choosing **not** to adopt
the one near-miss mechanism (`SubagentStop`) is a rejection recorded in §6, not a new
architectural direction — and had it been adopted, *that* would have needed an ADR.

If the runtime later gains a real output-schema capability, adopting it would be a genuine
architectural decision and should carry one.

## 15. Remaining limitations

1. **Every live retrieval currently fails at the boundary.** This is the honest operational
   consequence and it is not cosmetic: the Company Analysis skill cannot presently complete a
   live run without a human or the parent model extracting the envelope, which is forbidden.
   **The capability is correct but not yet operationally usable end-to-end.**
2. **A fabricated publication date is still undetectable.** Unchanged since M9-B, and not in
   this milestone's scope.
3. **R-11** — the namespace trust-breadth policy question from M9-C.6, still open.

Limitation 1 is the one that matters for sequencing, and options for it — none of which are
in this milestone's scope — include accepting a bare fence as the contract (it is already
tolerated by the parser, and is the difference between four failures and four successes), or
having the orchestration surface treat a wrapped reply as a reportable research failure the
user sees. **Both are owner decisions and neither was taken here.**

## 16. Git commit reference

N/A. Branch `main`, no commit, nothing staged, nothing pushed.

**Final status: `M9-C.7 COMPLETED` — Outcome B. No enforcement mechanism exists; the parser
remains the boundary.**
