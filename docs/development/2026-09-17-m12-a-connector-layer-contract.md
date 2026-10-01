# 2026-09-17 — M12-A connector layer contract / architecture review

**Milestone:** 12 — MCP Connector Layer: M12-A contract and architecture definition
**Status on completion:** REVIEW (DECISION ONLY) — ADR-0037 `Proposed`; Milestone 12 implementation stays `PLANNED`
**Supersedes:** None

## 1. Prompt / task performed

A fresh Claude Code session was asked to perform **only** an M12 architecture and contract-definition review. It was to
re-read the governance and architecture documents and verify the checkpoint (`ad6588c`, clean, equal to `origin/main`).
It was then to determine from repository evidence what the connector-catalogue capability should be, and to define
its purpose, trust model, catalogue metadata model, agent and MCP boundaries, privacy, read/write boundary, failure
model, provenance, security-test contract, human control and completion gate. Contradictions were to be documented,
not silently resolved. Forbidden: implementing M12; creating the agent or an MCP server; changing `.mcp.json`; adding
connectors, commands or skills; changing production Python, schemas or tests; committing or pushing.

## 2. Objective

Settle what M12 is before any implementation, keeping every accepted boundary (M3, M9, M9-A, M10, M11 verification,
M11 profiler, approval, no-secret, external-content trust) intact. Name the future Connector gate precisely.

## 3. Changes made

1. **Restart verification.** `git status` clean on `main`; `git log -n 5` headed by `ad6588c M11: biq-data-profiler
   implementation`; `git rev-parse HEAD` and `git rev-parse origin/main` both
   `ad6588c387634005d61033a117b4fa3586dc42bf`; `main...origin/main` with no divergence. No discrepancy; work proceeded.
2. **Governance and architecture read:**
   - `CLAUDE.md`; `architecture.md` in full; `project_plan.md` (milestone summary, M1, M9, M10.3.4, M11, M12–M14,
     known issues, debt, deferred); `README.md` references; `CONNECTORS.md`; `.mcp.json`;
     `.claude-plugin/plugin.json`.
   - ADR index and ADR-0004, 0005, 0006, 0009, 0010, 0014, 0015, 0035, 0036 in full, with 0034's M12 references.
   - `agents/biq-research-scout.md`, `agents/biq-analysis-verifier.md`, `reference/evidence-ledger.md`,
     `reference/research-policy.md`, `skills/biq-data-ingestion/SKILL.md`, `docs/integrations/README.md`, and the ADR
     and development-record templates.
   - Connector-relevant code and tests: `evidence.CONNECTED_DATA`, `research/contract.Destination`,
     `tests/unit/test_m11_verification_server.py`, `test_m11_verifier_agent_boundary.py`, the scope tests in
     `test_m11_data_profiler.py`.
   - A repository-wide search for `M12`, "connector catalogue" and `biq-connector`.
3. **Existing M12 intent recovered** (ADR-0037 *Context* table): connector resolution inside `biq-data-ingestion`; a
   capability map; verified endpoints only behind the Connector gate; named absence with the file fallback; read-only
   v1; degradation and write-attempt tests. Also the reserved `biq-data-profiler` agent for model-mediated connector
   catalogues (ADR-0036), and class 2 "connected-system data", which exists in `evidence.py` and is produced by nothing.
4. **Contradictions found**, each checked against the later decisions it conflicts with:
   - **C-1:** "discovers live servers" / "whatever server you have connected answers" versus ADR-0015 (Python cannot
     see or call MCP tools), ADR-0014/0035 (the grant is a list of exact tool names) and `CLAUDE.md` §7 (discovering
     servers from Python would mean reading platform config that can hold secrets).
   - **C-2:** connector reads "called freely" feeding the tiered reader, versus ADR-0002, ADR-0017, ADR-0035 §10,
     ADR-0036 §1/§6 and §17. A third-party MCP read result lands in a model context, and anything Python then
     receives is model-authored.
   - **C-3:** "write-attempt approval-gate tests" versus v1 read-only (clarification, not a contradiction of
     decisions).
   - **C-4:** connected servers' instructions are injected by the platform into the main context (observed in this
     session's system context), outside BusinessIQ's control.
5. **Five options** assessed (ADR-0037): build as written; an agent with read tools relaying records; a BusinessIQ
   proxy holding vendor tokens; defer M12; registry-bound resolution plus value-free discovery with reads blocked on
   measured prerequisites. The fifth was chosen, being the only one that keeps every accepted boundary.
6. **ADR-0037 written as `Proposed`**, not `Accepted`, because the brief leaves the work uncommitted for owner review
   and two genuine owner decisions remain (OD-1, OD-2). While drafting:
   - The prerequisites section was renamed from "12" to "M" so it is not confused with `architecture.md` §12.
   - A failure row that carried two code names was collapsed to one closed code, `connector_not_authorized`.
   - The operation id was required to carry at least 64 random bits instead of being content-addressed. A
     content-addressed id over static connector, tool and argument values is predictable to anyone who can write a
     label in the connected system, which would defeat ADR-0017's "a page author cannot pre-write a matching line"
     property.
7. **Status and index updates**: decisions index, docs index, `architecture.md` (§10 cell, §11 paragraph, §19 row —
   all marked proposed; §11's existing text and `CONNECTORS.md` deliberately left unchanged until acceptance),
   `project_plan.md` (summary row and an M12-A subsection; M12-B and M12-C `PLANNED`).
8. **Validation** run (§8–§9).

## 4. Files created

- `docs/decisions/ADR-0037-m12-connector-layer-contract.md`
- `docs/development/2026-09-17-m12-a-connector-layer-contract.md`

## 5. Files modified

- `architecture.md` — §10 `biq-data-profiler` tools cell (pointer to proposed ADR-0037); §11 a "Proposed M12 contract"
  paragraph; §19 ADR-0037 row marked **Proposed**.
- `project_plan.md` — milestone summary row 12; M12 section: pre-review scope kept verbatim, M12-A subsection added.
- `docs/decisions/README.md` — index row 0037 (Proposed).
- `docs/README.md` — ADR list entry 0037 (proposed).

## 6. Files deleted

None.

## 7. Features implemented

None. Decision only. No M12 component is user-reachable.

## 8. Tests performed

```
python tests/run_tests.py
claude plugin validate . --strict
```

No M12 test was written: nothing is implemented, and the brief forbids manufacturing tests for unimplemented behaviour.
The repository has no automated ADR-index or documentation-consistency test (searched `tests/` for references to
`docs/decisions`); index consistency was checked by reading the three indexes after editing.

## 9. Test results

```
Ran 4555 tests in 217.807s
OK (skipped=26)
ran 4555 | failures 0 | errors 0 | skipped 26
```

Identical to the M11 profiler-implementation baseline (4,555 / 0 / 0 / 26). The 26 skips are unchanged: 19
pre-existing, plus 7 opt-in runtime agent-boundary tests.

```
Validating marketplace manifest: …\.claude-plugin\marketplace.json
✔ Validation passed
```

Strict validation is not evidence for any agent or MCP boundary (M11 measurement), and none was changed.

## 10. Issues discovered

- **C-1 to C-4** as in §3.4 and ADR-0037. Nothing resolved silently; each has a proposed handling in the ADR.
- **OD-1, OD-2**: owner decisions (ADR-0037 *Owner decisions required*).
- **Observation, not investigated (outside scope):** this session reported the plugin's `biq-verifier` MCP server as
  failed to connect (`CONNECTION_CLOSED`). No verification was attempted and no M11 file was touched; it is recorded
  so the next verification-dependent task checks the server's launch in its own session.
- **Observation:** a HubSpot server is present in this session under the `marketing` plugin's namespace
  (`mcp__plugin_marketing_hubspot__authenticate`). This is the concrete case C-1 addresses.
- **Stale documentation noticed, deliberately not edited:** `docs/integrations/README.md` says "Empty until Milestone
  11". `project_plan.md`'s M11 section opens with "listed explicitly in `plugin.json`", which ADR-0015 superseded.
  `project_plan.md`'s "Last updated" header reads 2026-09-13. All are unrelated to deciding M12's contract.

## 11. Decisions made

[ADR-0037](../decisions/ADR-0037-m12-connector-layer-contract.md) — **Proposed**. In summary:

- M12-B builds a registry, capability resolution, named absence and a value-free catalogue through the reserved
  `biq-data-profiler` agent, holding only measured discovery tools.
- M12-C, connected-system reads, is specified and blocked on P-1–P-5.
- No write or administrative path exists; no BusinessIQ MCP server is added; no credential is handled.
- Connector metadata is never evidence or authorization.

**Future Connector gate** (not requested here): each proposed `.mcp.json` entry, identity only. The gate's record holds
the re-verified endpoint; the measured plugin-namespaced tool list with input and output shapes on a synthetic sandbox
account; the read/write classification of every tool; and the server's instructions verbatim. `~~chat` is ineligible
in M12.

## 12. Architecture changes

None accepted. `architecture.md` now references the proposed ADR in §10, §11 and §19; the architecture text it would
refine (§4, §11, `CONNECTORS.md`) is unchanged pending acceptance.

## 13. Project-plan updates

- Milestone 12: `PLANNED`, annotated with the M12-A contract in `REVIEW`.
- M12-A: new, `REVIEW (DECISION ONLY)`.
- M12-B, M12-C: new, `PLANNED`.
- Nothing marked `COMPLETED`.

## 14. Documentation updates

As §5. No `docs/agents`, `docs/integrations`, `CONNECTORS.md`, `README.md` or skill change: none applies before
acceptance.

## 15. Remaining work

1. Owner review and acceptance of ADR-0037, with OD-1 and OD-2 answered.
2. M12-B per ADR-0037 §L, starting with Connector-gate measurement of candidate servers.
3. M12-C prerequisite measurement (§M) and its own ADR, or a recorded `BLOCKED`.

## 16. Git commit reference

N/A — nothing committed or pushed, per the brief. Branch `main`, HEAD `ad6588c`, changes uncommitted for review.
