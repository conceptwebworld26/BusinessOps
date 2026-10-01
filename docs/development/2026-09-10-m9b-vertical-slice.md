# 2026-09-10 — M9-B: the retrieval vertical slice, and the defect that hid inside it

Status: **M9-B `ON HOLD`** · criterion #1 still `BLOCKED` · supersedes
`2026-09-10-m9b-scout-transport-investigation.md` on what is missing · branch `main`
(uncommitted)

The previous record established that scout dispatch is model-mediated and that M9-B was
missing an orchestration surface. This one builds that surface, closes the return contract,
adds candidate claims — and reports a defect found on the way that changes what "missing"
meant.

---

## 1. The defect: the scout never shipped

`plugin.json` declared:

```json
"agents": ["./agents/biq-research-scout.md"]
```

following a convention recorded in `architecture.md` that agents "must be listed
file-by-file". Installing the plugin and asking the runtime what it had loaded:

```
$ claude plugin details businessiq
  Skills (16)  …
  Agents (0)
```

**Zero.** With the key removed, the same command on the same files:

```
  Agents (1)  biq-research-scout
```

The manifest validated in both cases. So the retrieval agent had never shipped, could never
have been dispatched, and nothing in the repository would have said so — the boundary test
asserts the agent's *tool grant*, which is a property of a file on disk, not of what the
runtime loads. A green suite and a passing validator were both consistent with an agent that
did not exist at runtime.

This is the more useful half of the milestone. The earlier conclusion — "what is missing is
an orchestration surface" — was true but incomplete: a surface dispatching an agent that
does not load would have failed anyway, and the failure would have looked like a runtime
limitation rather than a manifest bug.

`architecture.md` is corrected, and `test_manifest.py` now asserts the key's absence with
the measurement written into the test, because the next person to read the old guidance
would reintroduce it.

---

## 2. The return contract

`normalise_records()` accepted a particular record shape; `agents/biq-research-scout.md`
described its output in prose. The two were written independently and had never been
compared. That is a silent data loss: a field the scout is told to send but ingestion drops
shows up only as thinner evidence than expected.

The contract is now `biq.scout.result/1`, stated in the agent definition and parsed by
`scout.parse_result()`:

```json
{"envelope": "biq.scout.result/1", "operation": "…", "query_text": "…",
 "status": "ok", "records": [ {"source": …, "reference": …, "title": …,
   "publication_date": …, "retrieved_at": …, "source_type": …, "content": …,
   "claim_kind": …} ]}
```

Four checks run before a single record is read, and each closes a way the boundary could be
crossed rather than a matter of tidiness:

| Check | Why |
|---|---|
| Envelope name | An arbitrary JSON object — including one a retrieved page contained — is not mistaken for a scout result |
| `operation` echoes the brief | A result cannot be attributed to a retrieval it did not come from |
| `query_text` echoes the brief | "The query is fixed" stops being an instruction the scout is asked to honour and becomes a property verified on return |
| `status` read before records | "No reliable source found" arrives as a structured failure, not an empty list that reads like a bug |

Two rules are stated to the scout in its own definition because they cannot be enforced
afterwards: **no invented publication dates** (omit the key; an undated item is handled
correctly, a fabricated date is undetectable) and **no `source_tier` field** (tier is
assigned locally from source identity, because a page that could name its own tier would
name A).

Code fences are tolerated around the JSON; arbitrary surrounding prose is not. A page can
contain a JSON object of its own, and a lenient parser would then have a choice to make.

---

## 3. The orchestration surface

`commands/retrieval-slice.md`, labelled in its own description as an **M9-B internal
retrieval vertical slice / integration harness**. It is not a research capability: it
answers no business question and writes no report. The four research skills (M9-C) and four
research commands (M9-D) remain unbuilt.

```
1. python …open_retrieval(…)   gate runs; six-field brief or a refusal
2. dispatch businessiq:biq-research-scout, once, brief verbatim   ← the model's leg
3. python …close_retrieval(payload, …)   parse → normalise → EvidenceSet
4. optional: proposals=[…]   candidate claims, where the evidence supports one
```

Step 2 is prose because it has to be: a subagent is dispatched by the model, and there is no
API to call. That makes the markdown executable instruction, so it is tested like code —
one agent named, brief sent verbatim, dispatched once, gate not re-run for a better answer,
harness self-labelled, `disable-model-invocation: true` so it never fires on its own.

`disable-model-invocation` matters more than it looks: a retrieval harness that can
auto-invoke is a retrieval nobody asked for.

**The gate runs in both halves.** The two Python calls are separate processes, so no
authorisation survives between them and `close_retrieval` re-derives the decision from the
same request. That is the safe direction — there is no serialised authorisation for a caller
to forge in between — at the cost of passing the request parameters twice.

---

## 4. Candidate claims

The `EvidenceSet` is the authoritative output: it records that a source said something. A
candidate claim records that *we are asserting it*, and nothing in M9-B verifies one — so
the distinction lives in the record rather than in a convention.

Claims are **opt-in**. With no proposals, none is produced, and that is the default. A
proposal is `{"evidence_id", "statement", "material"}`: the statement is the model's reading
of one item, because deciding what a source says is judgement and Python has none. What
Python has is the policy, and it applies it rather than trusting it:

| Refusal | Reason |
|---|---|
| `untraceable` | No item in *this* set carries that id |
| tier D | Excluded outright; an excluded source is not a weak citation, it is none |
| tier C alone, material | Corroboration only |
| no publication date | A date is not inferred |
| `not_a_source_claim` | Advisory or impact language — a guard, not a proof |
| `unresolved_conflict` | Sources disagree; conflicts are reported, never averaged |
| `statement_too_long` | A paragraph is where unsupported inference hides |

Every produced claim carries `status: candidate`, `verified: false`, its `evidence_id`,
source, citation, publication date, locally-assigned tier, freshness, and a `limitations`
list that always includes its own candidacy. A test asserts no code path in the module can
write `verified: True`.

**`candidate_claim: NOT PRODUCED — insufficient evidence` is a correct outcome** and is
never worked around.

---

## 5. Live retrieval: not executed

**REAL SCOUT DISPATCH STILL NOT EXECUTABLE — in this session.**

Attempted, with the gate-authorised brief as the entire prompt:

```
Agent type 'businessiq:biq-research-scout' not found. Available agents: claude,
claude-code-guide, Explore, feature-dev:code-architect, feature-dev:code-explorer,
feature-dev:code-reviewer, general-purpose, Plan, statusline-setup
```

A control probe with a deliberately invalid agent type returned the same class of error, so
unknown types **fail rather than silently falling back** to a general-purpose agent. That
matters: a silent fallback would have produced a plausible-looking result from an agent
holding file access, which is exactly the outcome this milestone must never report as
success.

The cause is sequencing, not capability. A plugin's agents register when a session starts;
BusinessIQ was installed *during* this session, so its agent is absent from this session's
registry. Nothing further can be done from inside it, and `claude -p` / `--bg` were not used
to work around it because the milestone brief prohibits them.

The gate half did run, and its output is what a dispatch would carry:

```
authorised ALLOW tier 0
{"query_text": "logistics 2026 gross margin benchmark",
 "destination": "public_web:public-web-search", "operation": "m9b-slice-2026-09-10",
 "max_results": 20, "max_fetched": 8, "timeout_seconds": 60}
```

Six fields. No subject, no business, no context, no conversation.

### Executing it

One session, three steps:

1. `claude --plugin-dir .` from the repository root (or use the installed plugin), then
   confirm with `claude plugin details businessiq` that it reports **Agents (1)**.
2. `/retrieval-slice` and follow the four steps in the command.
3. Verify against the transcript, not against the report: read the **Task tool's input**.
   It must be the six fields and nothing else. That is the only place the boundary can be
   observed directly, because the dispatch is the one leg Python does not perform.

Then confirm: exactly one dispatch; `WebSearch`/`WebFetch` visible in the subagent's
transcript; a `biq.scout.result/1` envelope returned; every item `UNTRUSTED_EXTERNAL_DATA`;
tiers recomputed locally; undated items still undated.

---

## 6. Testing

| Suite | Tests |
|---|---|
| `tests/unit/test_m9b_scout_contract.py` | 61 |
| `tests/unit/test_m9b_candidate_claims.py` | 36 |
| `tests/unit/test_command_registry.py` | +2 (35) |
| `tests/unit/test_manifest.py` | +1 |
| **Added** | **100** |

Full suite **1,562 tests, 0 failures, 0 errors, 19 skipped** (baseline 1,462). No test was
deleted, weakened or skipped. Two existing tests changed, both strengthened:
`test_manifest.py` now asserts the `agents` key is absent rather than tolerating it, and
`test_command_registry.py` distinguishes the harness from analytics commands and asserts it
has no runnable registry spec, rather than widening "every analytics command is declared".

Nothing in the suite reaches the network, and nothing simulates a dispatch: fixture
envelopes are fed to the same ingestion a live envelope meets, which is the honest half to
automate.

---

## 7. Limitations

1. **Live retrieval remains unexercised.** Everything downstream of the dispatch is tested
   against fixtures only.
2. **The advisory-language guard is a deny-list**, not a proof. It catches obvious
   recommendation and impact phrasing; whether a sentence exceeds its source is judgement,
   stated to the model in the command and not enforceable in Python.
3. **Conflict detection remains numeric** (M9-A limitation, unchanged), so a conflict about
   definitions rather than figures is not detected and would not block a claim.
4. **Tier classification is pattern-based**; unrecognised sources are C, which fails safe
   but under-rates genuine authorities until listed.
5. **`ScoutTransport` still exists** as a test double. It is documented as one, but the
   interface still invites someone to satisfy it with something that reaches the network.

---

## 8. State

M9-B on hold, criterion #1 blocked pending one live run. M9-C/M9-D not started; no M10, MCP
or remaining M11 work. Full suite green; plugin, marketplace and repository validation pass
with only the known R-08 advisory. 0 commits, 0 pushes.

The plugin was installed at user scope during this task (`claude plugin marketplace add ./`
then `claude plugin install businessiq@businessiq`) in order to test what the runtime
actually loads. That is a change outside the repository; it is what makes the live run
possible next session, and `claude plugin uninstall businessiq@businessiq` reverses it.
