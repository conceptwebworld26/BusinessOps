# 2026-09-17 — M12-A contract remediation: trust chain, layer separation, ADR-0004 relationship

**Milestone:** 12 — MCP Connector Layer: M12-A contract remediation (decision only)
**Status on completion:** REVIEW (DECISION ONLY) — ADR-0037 still `Proposed`; OD-1 and OD-2 accepted; M12-B `PLANNED`; M12-C `BLOCKED`
**Supersedes:** None. Follows `2026-09-17-m12-a-connector-layer-contract.md`, which is left unedited: its statements
that OD-1 and OD-2 were open, and that ADR-0037 "refines" ADR-0004, were accurate when written and are corrected here.

## 1. Prompt / task performed

Continue the M12-A review in the same session, with HEAD `ad6588c` and no commit or push. Record the owner's acceptance
of **OD-1** (M12 may complete on M12-B with M12-C recorded `BLOCKED` until P-1 to P-5 are satisfied and its own ADR is
accepted) and **OD-2** (exact registry-bound identity; same-vendor servers under another namespace do not qualify).
Then perform seven remediations of ADR-0037:

1. an explicit normative trust chain;
2. separation of registry declaration, Connector Gate measurement and runtime grant;
3. a direct verification of the ADR-0004 relationship;
4. `CONNECTORS.md` updated for OD-2;
5. an unmistakable M12-B/M12-C boundary;
6. the `biq-data-profiler` agent role;
7. no over-design.

No implementation, agent, `.mcp.json`, server, connector, command, skill, production code or test change.

## 2. Objective

Close the remaining architectural ambiguity so ADR-0037 can be considered for acceptance.

## 3. Changes made

1. **State verified:** `git rev-parse HEAD origin/main` → both `ad6588c387634005d61033a117b4fa3586dc42bf`. Working
   tree held only the uncommitted M12-A documentation.
2. **ADR-0004 inspected directly.** Its Decision reads "`biq-connector-broker` performs discovery, capability mapping,
   read-only enforcement and named degradation … every other category is documented in `CONNECTORS.md` as
   user-configurable". Option B, which it adopts, "resolves the placeholder at runtime to whatever server is
   connected". OD-2 makes both clauses untrue, so the relationship is a **partial supersession**, as ADR-0035 is of
   ADR-0034 — not a refinement that adds detail, and not an independent decision. The earlier wording "refines" was
   imprecise and is corrected. Unchanged: capabilities not products, verified endpoints only, the Connector gate, named
   degradation, read-only enforcement, the load-bearing file path, ADR-0012's placement. ADR-0004 is not edited
   (status line included); the relationship is recorded in the decisions index, `architecture.md` §19 and ADR-0037,
   following the ADR-0006 and ADR-0022 precedent.
3. **ADR-0037 rewritten in place** (a proposed, uncommitted ADR, so editing is permitted):
   - **New §B.1** — the 14-step normative trust chain, with exact-match semantics throughout.
   - **New §B.2** — declaration, measurement and grant as three layers, none sufficient alone. Use is valid only per
     sealed operation when every binding agrees; any difference refuses it. Explicitly no new authorization system:
     it reuses ADR-0014/0035 grants, ADR-0035 sealed requests, ADR-0017 fail-closed replies and the ADR-0018
     registry rule.
   - **New §B.3** — what authorization is and is not.
   - **New §B.4** — registry, server and tool identity bindings, and re-measurement on change.
   - A normative M12-B/M12-C boundary table after the Decision. M12-C recorded `BLOCKED`. Every M12-C statement
     relabelled as a minimum constraint on its future ADR, not an approval.
   - **§D.1** distinguishes the M11 local-file profile (the deterministic engine; no agent) from the M12 catalogue
     responsibility, and states that the M11 guarantees are not weakened. **§D.3** gains the must-not-receive list.
   - `binding_mismatch` added (19 failure codes). Security category 19, layer-binding agreement, added (19
     categories). §I now refuses every class-2 claim in M12-B.
   - §K's M12-C row no longer pre-decides an approval class. §L's M12-B gate holds no M12-C item, and M12 completion
     follows OD-1. *Owner decisions* are recorded as accepted.
   - A *Relationship to ADR-0004* section added.
4. **Over-design removed** (remediation 7):
   - the assumed `mcp__plugin_businessiq_<server_key>__<tool>` naming pattern for third-party servers — now "measured
     at the Gate, never constructed"; the only measured form is `biq-verifier`'s;
   - the speculative `PostToolUse`/`PreToolUse`/output-replacement candidates in §M — the repository holds no
     evidence for them, and §M now proposes no mechanism;
   - the named `./.businessiq/connectors/` store — now the existing runtime-state area, location an implementation
     item;
   - registry, brief and result field names — now implementation contract items, with content and classification
     normative;
   - stale cross-references "§4.1" and "§5.6" corrected to §D.1 and §E.11.
5. **`CONNECTORS.md`** (OD-2 only):
   - the opening "whatever accounting MCP server you have connected answers" replaced;
   - an *Exact registered identity* section added (registered identity; same vendor is not same identity;
     unregistered servers and tools unusable; Connector Gate required; no write, administrative or record-read
     authorization);
   - a note that HubSpot and Slack are endpoint-verified but neither registered nor Gate-measured;
   - *Adding a connector* now lists the four agreeing layers;
   - the permission rows for read, write and `~~chat` aligned to v1's read-only, discovery-only reality.
6. **`architecture.md`**, removing language contradicting OD-2 and the partial supersession:
   - §4 ingestion cell;
   - §8 least-privilege sentence ("refuses mutating connector tools without a gate" → no mutating tool exposed in v1);
   - §10 agent cell;
   - §11 resolution sentence, Slack row, extensibility sentence, the three-layer identity rule, and the M12-B/M12-C
     summary;
   - §17 multiple-connectors row;
   - §18 connector extension row;
   - §19 rows for 0004 and 0037.
7. **`project_plan.md`:** summary row 12; M12-A subsection re-tabled with the trust chain, layer separation, accepted
   decisions, M12-B `PLANNED` and M12-C `BLOCKED`.
8. **`docs/decisions/README.md`:** 0004 and 0037 index rows; the amended/refined paragraph records the partial
   supersession.

## 4. Files created

- `docs/development/2026-09-17-m12-a-contract-remediation.md`

## 5. Files modified (all uncommitted)

- `docs/decisions/ADR-0037-m12-connector-layer-contract.md` (proposed; created earlier this session)
- `CONNECTORS.md`
- `architecture.md`
- `project_plan.md`
- `docs/decisions/README.md`

`docs/README.md` carries the earlier ADR-0037 list entry and needed no further change.

## 6. Files deleted

None.

## 7. Features implemented

None. Decision only.

## 8. Tests performed

```
git rev-parse HEAD origin/main
python tests/run_tests.py
claude plugin validate . --strict
git diff --check   (plus a whitespace check of the untracked documentation files)
```

No documentation or ADR consistency test exists in the repository. Consistency was checked by script:

- ADR-0037's section references all resolve to existing headings;
- §H holds 19 codes, §J 19 categories and §B.1 14 steps, matching `project_plan.md`;
- no stale term (`§4.1`, `§5.6`, `four-way`, `eighteen`, hook names, the invented store path or naming pattern)
  remains.

## 9. Test results

```
Ran 4555 tests in 209.817s
OK (skipped=26)
ran 4555 | failures 0 | errors 0 | skipped 26
```

```
Validating marketplace manifest: …\.claude-plugin\marketplace.json
✔ Validation passed
```

Identical to the M11 baseline. Strict validation is not evidence for any agent or MCP boundary, and none changed.
`git diff --check` results are in the task report.

## 10. Issues discovered

- The first M12-A record's "refines ADR-0004" was imprecise (partial supersession); corrected here rather than by
  editing that record.
- Remaining residual risks are unchanged and stated in ADR-0037 *Consequences*.

## 11. Decisions made

OD-1 and OD-2 accepted by the owner, 2026-09-17, recorded in ADR-0037. ADR-0037 remains `Proposed`.

## 12. Architecture changes

Current architecture text now states OD-2's identity rule and M12-C's `BLOCKED` status, and records the partial
supersession of ADR-0004. No component was built.

## 13. Project-plan updates

- M12: `PLANNED`.
- M12-A: `REVIEW (DECISION ONLY)`.
- M12-B: `PLANNED`.
- M12-C: `PLANNED` → `BLOCKED` (OD-1).
- Owner-decisions row: `COMPLETED`.

## 14. Documentation updates

As §5.

## 15. Remaining work

Owner acceptance of ADR-0037. Then M12-B per §L, beginning with Connector Gate measurement. M12-C stays `BLOCKED`.

## 16. Git commit reference

N/A — nothing committed or pushed. Branch `main`, HEAD `ad6588c`.
