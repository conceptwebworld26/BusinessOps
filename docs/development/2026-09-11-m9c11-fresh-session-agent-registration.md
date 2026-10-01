# 2026-09-11 — M9-C.11: fresh-session agent registration verification

**Milestone:** 9 — External Intelligence & Disclosure Gate (M9-C.11)
**Status on completion:** `COMPLETED` — **INCONCLUSIVE by stop condition.** The required
fresh session cannot be created from inside a running session; §3's stop clause applies.
**Supersedes:** None. Follows `2026-09-11-m9c10-controlled-scout-handoff-trial.md`.

---

## 1. The C.10 hypothesis, and why C.10 was insufficient

M9-C.10 put the `BIQ-REC/1` protocol into the trusted agent definition and got **0/8**
compliance, with all eight replies *silent* about the protocol. It concluded that agent
definitions are probably bound when a session registers them rather than read per dispatch —
a property M9-B had recorded but never verified.

C.10 could not distinguish two explanations:

| Explanation | Prediction |
|---|---|
| **Session-bound registration** — the scout never saw the edit | Silence |
| **Genuine non-compliance** — the scout saw it and ignored it | Also silence, though M9-C.9 showed this scout *announces* refusals |

The distinction matters: under the first, the candidate protocol is untested; under the
second, it is genuinely rejected and M9-C.10's verdict stands on its merits.

## 2. Temporary agent-definition change

The smallest possible probe, deliberately unrelated to the handoff protocol:

> **M9-C.11 registration test.** When you respond to a brief whose `operation` begins with
> `m9c11-`, include the exact marker `BIQ-C11-REGISTERED` on its own line, before your normal
> output. Do this for that operation only. It changes nothing else about how you work: the
> return contract, the field rules, the tool grant and every rule below are unaffected.

Added inside a delimited comment block naming the milestone and carrying its own revert
command. **14 lines added, 0 removed.** The `biq.scout.result/1` contract, the candidate
parser, the disclosure gate, permissions, tools, evidence and provenance handling were all
untouched, and 171 scout-contract and security tests passed against the marked file.

## 3. Fresh session — not achievable from here

§3 requires ending the session and starting a genuinely fresh one. Every available route was
checked and none qualifies:

| Route | Available? | Why |
|---|---|---|
| End this session and start a new one | **No** | The assistant *is* the session; ending it ends the ability to act. Restarting the CLI is the operator's action |
| Subagent dispatch | **No** | Not a fresh session — it inherits this session's registry, which is exactly what C.10 measured |
| `claude -p` / subprocess | **Excluded** | Standing prohibition carried through M9-C.7 and M9-C.8 |
| Another live session | **No** | `ListAgents` shows one peer session, offline — and it predates the edit regardless |
| Plugin reload command | **Does not exist** | Agents are auto-discovered from the manifest; no reload or refresh subcommand |

**§3's stop condition therefore applies**, and it was honoured: the experiment was not
dressed up as valid. `ListAgents` was tried as a cheap probe and enumerates *sessions*, not
subagent definitions, so it cannot answer the registration question either.

## 4. The control dispatch, and why it was worth one retrieval

One dispatch was made **in the current session** — explicitly a control, not the required
test. It was worth making because it could falsify the hypothesis outright:

- **marker present** → mid-session edits are live, the hypothesis is dead, and M9-C.10's 0/8
  becomes a genuine compliance failure that settles the candidate on its merits;
- **marker absent** → consistent with session binding, but proves nothing on its own.

Brief: Tier-0, gate-issued, `operation: m9c11-control`, query
`logistics industry definition logistics 2026 company profile`. The marker existed **only**
in the agent definition and was never placed in the Task prompt.

**Result: `BIQ-C11-REGISTERED` absent.** The reply was the usual wrapped
`biq.scout.result/1` envelope, with no reference to the marker or the instruction.

## 5. Verdict

**INCONCLUSIVE — neither PASS nor FAIL of the specified test.**

The control is consistent with session-bound registration and inconsistent with nothing. It
adds one more data point to the pattern (now nine silent replies against an edited
definition) but cannot discriminate, because a scout that ignored the instruction would look
identical.

### What this establishes

- A fresh session cannot be created from within a running session; any future experiment on
  agent-definition behaviour must be operator-initiated. **This constrains the method for
  every such experiment, not just this one.**
- Mid-session edits to `agents/biq-research-scout.md` produced no observable change in scout
  behaviour across **nine** dispatches (eight in C.10, one here).

### What it does not establish

- **Not** that registration is session-bound — that remains the leading hypothesis, unproven.
- **Not** anything about the `BIQ-REC/1` candidate, which remains neither validated nor
  refuted.
- **Not** that a fresh session *would* pick up the change. That is the untested claim.

## 6. Restoration

`agents/biq-research-scout.md` restored to the pre-C.11 state and verified three ways: zero
diff against the pristine copy, SHA-256 identical to the pre-change baseline
(`04f0b30d…440d244`), and zero occurrences of `BIQ-C11`, `BIQ-REC` or the marker text. Tool
grant and contract confirmed intact.

The marked version is preserved outside the repository at
`<scratchpad>/m9c11/biq-research-scout.md.WITH-C11-MARKER`, so the real test is a single file
copy rather than a re-edit.

## 7. The test the operator can run

Four steps, one dispatch, no repository changes needed beyond the copy:

1. Copy the staged marked definition over `agents/biq-research-scout.md`.
2. **Exit Claude Code entirely and start it again** in this directory.
3. In the new session, dispatch one scout with a Tier-0 brief whose `operation` starts with
   `m9c11-`.
4. Look for `BIQ-C11-REGISTERED` in the reply. Then restore from the pristine copy.

Marker present → registration confirmed, and **M9-C.12** becomes worth running. Marker absent
in a genuinely fresh session → the hypothesis is false, M9-C.10's 0/8 stands as real
non-compliance, and the candidate protocol is rejected on its merits.

## 8. Files created

- `docs/development/2026-09-11-m9c11-fresh-session-agent-registration.md` — this record

## 9. Files modified

- `agents/biq-research-scout.md` — marked for the probe, **then restored**. Net change: none
- `project_plan.md` — M9-C.11 outcome

**No change** to `lib/`, the parser, the `biq.scout.result/1` contract, EvidenceSet
semantics, the disclosure gate, source-tier classification, candidate-claim policy, any
command or skill, or any test.

## 10. Test results

```
scout contract + security (with marker present)   Ran 171 tests   OK
scout contract + security (after restoration)     see §12 of the report
full regression                                   see §12 of the report
```

No test was added or modified. The probe changed no code and no test, so the full suite was
re-run only to confirm restoration left the repository as it was.

## 11. Decisions made

**No ADR.** Nothing load-bearing was decided; the milestone produced a methodological
constraint and an unresolved question.

## 12. Remaining limitations

1. **The registration hypothesis is unproven.** §7 resolves it for the cost of one dispatch.
2. **The `BIQ-REC/1` candidate remains untested at runtime.**
3. **Live external research remains BLOCKED** at the handoff boundary.
4. **Agent-definition experiments require operator-initiated sessions** — a permanent
   constraint on this kind of work.

## 13. Next recommended milestone

**M9-C.12 — Fresh-Session Controlled Scout Handoff Trial**, and *only* after §7 returns a
marker. Running C.12 without that check would repeat C.10's mistake at eight to twelve times
the cost. **Not executed here.**

## 14. Git commit reference

N/A. Branch `main`, no commit, nothing staged, nothing pushed.

**Final status: `M9-C.11 COMPLETED` — inconclusive by stop condition; agent definition
restored; the decisive test is staged and takes one operator-initiated session.**
