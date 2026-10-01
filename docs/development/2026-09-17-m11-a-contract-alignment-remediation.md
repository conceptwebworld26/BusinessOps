# 2026-09-17 — M11-A: contract-alignment remediation (blind-recomputation boundary)

**Milestone:** 11-A — verification and finalisation contract (remediation within the decision-only milestone)
**Status on completion:** COMPLETED (DECISION ONLY)
**Supersedes:** `docs/development/2026-09-17-m11-a-verification-finalisation-contract.md` — only its §3
item 4 description of recomputation as running in the agent over a brief, and the §10 item *`Bash` is a
shell*, which described a limitation this remediation removes rather than accepts. That record is
otherwise current and is left intact.

## 1. Prompt / task performed

Resolve a seam in the uncommitted M11-A contract before implementation: ADR-0034 gave the
`biq-analysis-verifier` agent a source path and a `Bash` grant, and had it return recomputed values as
verbatim stdout, while findings could carry expected and observed values. Design a recomputation
interface in which no model sees the confidential source or a checked value; constrain source access and
the return channel; make the recomputation basis unambiguous; keep every other M11 decision. Decision
only: no `verification.py`, schema, agent, server, test, code, command, skill or manifest; no edit to
ADR-0031/0032/0033; no commit or push.

## 2. Baseline

HEAD `4dc65624a739eef559b42a4f1f1e9bb972176d54` = `origin/main`; working tree holding the uncommitted M11-A
changes (ADR-0034, its record, `architecture.md`, `project_plan.md`, `reference/output-standards.md`, both
ADR indexes). Last full run 4,408 tests, 0 failures, 0 errors, 19 skipped.

## 3. Changes made

1. **Re-read the governance and precedents**, not the previous report: `CLAUDE.md` (§3 agents, §7, §8, §9,
   §13 Connector gate), `architecture.md` §7 and §10, `project_plan.md` M11, ADR-0002, ADR-0006, ADR-0014,
   ADR-0015, ADR-0031, ADR-0032, ADR-0033, ADR-0034, the M11-A record, `agents/biq-research-scout.md`,
   `tests/unit/test_research_scout_boundary.py`, `commands/runner.run`, `synthesis_set.register_*`,
   `config.py` (the `.businessiq` resolver), `.gitignore`, `synthesis.schema.json`.
2. **Confirmed the seam in ADR-0034's own text** — §5.3 brief lists the source path; §12 grants `Bash`;
   §5.3/§12 return stdout "verbatim" after the command "emits recomputed fields"; §11 claims the files carry
   "never figures", which the reply contradicts; §6 redacts values in findings only partially; the
   dataset-keyed basis leaves overwrite ambiguity unresolved (`register_dataset`, `register_kpi`,
   `register_analysis` all key by id and overwrite).
3. **Established the constraint from precedent.** The scout's security is its declared tool grant
   (ADR-0014; boundary test); agent frontmatter names whole tools; nothing verified restricts `Bash` to one
   command (ADR-0001). A `Bash` grant is an arbitrary shell, so it cannot host a blind boundary.
4. **Decided ADR-0035** (Option D of four): the agent's entire grant is one plugin-local MCP operation
   taking only an opaque request id; the operation resolves a content-addressed request internally,
   refuses on source or configuration hash mismatch, and writes salted digests (never values) to a
   machine-only record; it returns only `biq.verifier.result/1`; `verify()` re-derives the request, binds
   the record and compares digests of the draft's exact strings. Findings carry references and comparison
   codes, never values. The basis becomes a content-addressed run registration, digest-bound in the set,
   with cross-run re-registration refused. Unverifiable platform facts make recomputation `BLOCKED`, never
   shell-routed.
5. **Recorded supersession** on ADR-0034's status line only (repository convention: accepted ADR text is
   immutable; status lines record supersession), and in both indexes' status columns and the
   *Amended / refined* note. ADR-0034's body is unchanged.
6. Documentation (§14).

## 4. Files created

- `docs/decisions/ADR-0035-m11-blind-recomputation-boundary.md`
- `docs/development/2026-09-17-m11-a-contract-alignment-remediation.md` (this record)

## 5. Files modified

All within the uncommitted M11-A change set:

- `docs/decisions/ADR-0034-m11-verification-and-finalisation-contract.md` — **status line only**
- `architecture.md` — §7 M11 summary (blind-recomputation boundary bullet, findings without values, model
  boundary, seams); §10 verifier row (role and tool grant); §19 decision table
- `project_plan.md` — M11-A table rows *Agent*, *Methods*, *Findings*; remediation paragraph; M11
  implementation scope
- `reference/output-standards.md` — findings show a reference and comparison code, never a figure or text
- `docs/decisions/README.md`, `docs/README.md` — ADR-0035 listed; ADR-0034 status

## 6. Files deleted

None.

## 7. Features implemented

None. Contract only. M11 remains unimplemented.

## 8. Tests performed

```
python tests/run_tests.py
claude plugin validate . --strict
git diff --check
```

## 9. Test results

Run after the documentation changes; no code or test changed, so these are regression results only.

| Run | Result |
|---|---|
| `python tests/run_tests.py` | ran 4,408, failures 0, errors 0, skipped 19 |
| `claude plugin validate . --strict` | Validation passed |
| `git diff --check` | clean |

No verifier test exists or was written.

## 10. Issues discovered

- **The M11-A contract contradicted itself** on what the recomputation channel carries (§3 above).
  Resolved by ADR-0035.
- **Cross-run re-registration will be refused** where M10 silently overwrote. No current test is known to
  depend on the overwrite, but the implementation must run the full suite against the change.
- **Platform facts are unmeasured:** a plugin stdio MCP server, its tool name, an agent restricted to that
  single tool, and strict validation of both. ADR-0035 §11 requires measuring them first and blocks
  recomputation if any fails.
- **Not fixed (pre-existing, unrelated):** the `project_plan.md` milestone summary table and its "Last
  updated" line; M11's heading text "listed explicitly in `plugin.json`", which ADR-0015 measured to be
  wrong (agents are auto-discovered).

## 11. Decisions made

[ADR-0035](../decisions/ADR-0035-m11-blind-recomputation-boundary.md), superseding ADR-0034 in part. No
change to ADR-0031, ADR-0032 or ADR-0033.

## 12. Architecture changes

`architecture.md` §7 and §10 now describe the ADR-0035 boundary. Decided, not built.

## 13. Project-plan updates

M11-A remains `COMPLETED (DECISION ONLY)` with a remediation entry; *M11 — Verification and finalisation
implementation* remains `PLANNED`, its scope updated.

## 14. Documentation updates

As §5. `CLAUDE.md` unchanged: the Connector gate already governs the new local MCP server, and
verification stays read-only with no approval. `README.md` unchanged: nothing user-reachable changed.

## 15. Remaining work

The M11 implementation milestone, starting with the ADR-0035 §11 measurements; `biq-data-profiler`.

## 16. Git commit reference

N/A — no commit made, nothing staged or pushed.
