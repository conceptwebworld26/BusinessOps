# 2026-09-10 — M9-B: is there a real scout transport? (supersedes the M9-B completion claim)

Status: **M9-B `ON HOLD`** · supersedes the acceptance claim in
`2026-09-10-m9b-research-scout-retrieval.md` · no code changed · branch `main` (uncommitted)

---

## 1. Why this record exists

The M9-B report asserted two things that cannot both be true:

- acceptance criterion #1 — *"Real scout retrieval integration exists."* — marked **PASS**
- limitation 1 — *"No transport ships … nothing retrieves out of the box."*

The second is correct. The first was not, and marking it PASS was a reporting error, not a
code defect. This record resolves the contradiction by establishing what the runtime
actually supports, and corrects the status.

The question it had to answer: **is there a supported mechanism by which the BusinessIQ
plugin can invoke `biq-research-scout`, and if so, is it implemented?**

---

## 2. What was checked

Every mechanism that could plausibly close the loop, checked against this machine rather
than against documentation or recollection.

| Candidate | Evidence | Verdict |
|---|---|---|
| Python calls `WebSearch` / `WebFetch` | Neither name occurs anywhere in `lib/` outside docstrings; no `urllib`, `requests`, `httpx`, `aiohttp`, `socket` or `http.client` import exists | **No.** They are model-invoked tools, not a library |
| `claude -p --agent biq-research-scout …` | `--agent <agent>` sets *the session's* agent; reaching it from Python means spawning a process | **Excluded.** A subprocess shell-out, prohibited by the task and against ADR-0014's intent |
| `--agents <json>` | Help text: *"JSON object defining custom agents"* — session configuration at launch | **No.** Declares agents; does not dispatch one |
| `claude agents` | `claude agents --help` → *"Manage background agents"*, i.e. background **sessions** (`--bg`, `attach`, `logs`, `rm`) | **No.** A different concept from a subagent |
| An MCP server exposed by the plugin | MCP tools are called by the model, never by plugin Python | **No.** The same seam, one layer further out |
| Hooks | Fire in response to the model's tool use | **No.** Model-mediated by definition |
| **The model dispatches the subagent** | See section 3 | **Yes — and it is the only one** |

---

## 3. The finding

**Plugin-provided agents are dispatched by the orchestrating model, through the Task tool.
There is no programmatic dispatch API available to plugin code.**

Two pieces of first-party evidence on this machine:

1. Agents supplied by an installed plugin appear in the session's agent registry under
   `<plugin>:<agent>` and are dispatchable as a `subagent_type` — `feature-dev:code-architect`,
   `feature-dev:code-explorer` and `feature-dev:code-reviewer` are present in this session
   from the official `feature-dev` plugin. Installed BusinessIQ would likewise expose
   `businessiq:biq-research-scout`.
2. That plugin's own command dispatches them **in prose**, not in code —
   `commands/feature-dev.md` reads *"Launch 2-3 code-explorer agents in parallel"*. There is
   no API call anywhere in the plugin, because there is nothing to call.

So the supported path is real, and it looks like this:

```
command / skill (markdown)
        │  instructs
        ▼
      model  ──Task(subagent_type="businessiq:biq-research-scout", prompt=brief)──►  scout
        │                                                          WebSearch / WebFetch
        │  ◄──────────────── structured result ────────────────────────────────────┘
        ▼
      Python   normalise_records → EvidenceSet → candidate_claim
```

Python owns both ends and none of the middle.

---

## 4. What this means for the M9-B design

M9-B modelled the seam as **`ScoutTransport.dispatch(brief)` — a Python callable to be
injected**. That shape presumes a dispatcher exists that Python could hold. None does, and
none can. `UnavailableTransport` is therefore not a placeholder awaiting a real
implementation; it is the permanent and only truthful Python-side answer.

The actual runtime seam is a **serialisation boundary with the model in the middle**: a
brief goes out as data, a result comes back as data, and the leg between them is performed
by the model. `ScoutTransport` remains sound as a *test double* — it drives the production
normalisation path from fixtures, which is exactly what the security suite needs — but it
is not, and cannot become, a transport.

This is not an unfortunate limitation. It is the same fact that makes ADR-0006 and ADR-0014
structural: because Python cannot reach a web tool, the component holding file access and
the component holding web access are separated by the runtime rather than by discipline. A
programmatic dispatch API, if one existed, would be the thing to argue against.

---

## 5. What is genuinely missing

Not a runtime capability — **an orchestration surface**, plus the half of the contract that
would let one work mechanically:

1. **No caller.** Nothing in `commands/` or `skills/` mentions the scout, so the model is
   never told to dispatch it. The four research commands are M9-D and the four research
   skills are M9-C; both are unstarted and unapproved.
2. **No return contract.** `agents/biq-research-scout.md` describes the scout's behaviour
   in prose but never specifies the machine-readable shape it must emit.
   `scout.normalise_records()` expects a particular record shape. The two ends were written
   independently and **have never been matched against each other** — no test asserts that
   the fields the agent is told to return are the fields `ACCEPTED_RECORD_FIELDS` accepts.
   This is the real integration gap underneath the reporting contradiction.
3. **No exercised path.** No live retrieval has run, here or anywhere. The opt-in smoke
   test cannot run either, because the transport it would need cannot exist.

Item 2 is the smallest piece of genuine M9-B work remaining and is recommended as the
completion step. It is not done in this task: the brief was to resolve the contradiction
and to stop at the boundary that is genuinely supported, not to extend scope.

---

## 6. What was not done, deliberately

- No transport was written. A Python function returning records would be a fixture wearing
  the word "live", which is the thing the owner explicitly ruled out.
- No subprocess, shell-out, browser automation or SDK dependency. Each would give the
  file-access component a web path and dissolve ADR-0014.
- `FixtureRetriever` and `RecordingTransport` were left labelled as what they are.
- No M9-C or M9-D work began.
- No `lib/` code changed. Nothing was found wrong with it — the code never claimed live
  retrieval; the report did.

---

## 7. Verification

Full suite re-run to confirm the documentation correction changed no behaviour:

```
Ran 1462 tests in 113.393s
OK (skipped=19)
ran 1462 | failures 0 | errors 0 | skipped 19
```

`claude plugin validate .claude-plugin/marketplace.json --strict` → passed.
`claude plugin validate .claude-plugin/plugin.json --strict` → the single known R-08
advisory (CLAUDE.md at plugin root is not loaded as plugin context), unchanged.

---

## 8. Manual verification procedure

Live smoke testing cannot be automated here, because automating it would require exactly
the Python transport that cannot exist. The manual equivalent, for an operator who wants to
confirm the path end to end once an orchestration surface exists:

1. **Load the plugin for one session** — `claude --plugin-dir .` from the repository root.
   This registers `businessiq:biq-research-scout` in that session's agent registry without
   installing anything.
2. **Produce a genuine Tier-0 brief.** Run, and keep the output:

   ```bash
   python -c "
   import sys, json; sys.path.insert(0, 'lib/python')
   from biq import research as R
   from biq.research import scout as S
   req = R.ResearchRequest('gross margin benchmark', R.INDUSTRY, intent=R.BENCHMARK,
                           public_terms={'industry': 'logistics', 'period': '2026'},
                           operation='manual-smoke')
   dec = R.assess(req)
   print(json.dumps(S.ScoutBrief(R.RetrievalRequest(dec)).as_dict(), default=str))
   "
   ```

   Observed on 2026-09-10 — `ALLOW`, tier 0, and six fields with nothing internal in them:

   ```json
   {"query_text": "logistics 2026 gross margin benchmark",
    "destination": "public_web:public-web-search", "operation": "manual-smoke",
    "max_results": 20, "max_fetched": 8, "timeout_seconds": 60}
   ```

3. **Dispatch once.** Ask the session to launch the `businessiq:biq-research-scout` subagent
   with that JSON as its entire prompt — nothing added, no conversation carried in.
4. **Check what actually crossed.** In the transcript, read the Task tool's input. It must be
   the six fields and nothing else. This is the only place the boundary can be observed
   directly, because the dispatch is the one leg Python does not perform.
5. **Ingest.** Feed the scout's returned records to `scout.normalise_records()` and build the
   `EvidenceSet`. Confirm every item is `UNTRUSTED`, tiers were recomputed locally rather
   than taken from the page, and undated items came back `undated` rather than dated.
6. **Confirm one shot.** Exactly one dispatch, whatever the retrieved pages say.

Step 3 has not been performed. It needs a caller, and no approved caller exists — which is
the whole of this record.

---

## 9. Status

M9-B is **ON HOLD**. Acceptance criterion #1 is **BLOCKED**: a supported mechanism exists,
it is model-mediated, and no orchestration surface has been approved that could exercise it.
The criteria covering the boundary, normalisation, bounds, one-shot dispatch and injection
resistance are unaffected and remain met — they were always properties of the Python halves.

The owner's decision is which of these M9-B should mean:

- **(a)** the Python halves plus a matched return contract, with first live retrieval
  deferred to M9-D — the reading that matches the existing plan rows; or
- **(b)** end-to-end live retrieval, which requires pulling a minimal orchestration surface
  forward out of M9-C/M9-D into M9-B.

0 commits, 0 pushes.
