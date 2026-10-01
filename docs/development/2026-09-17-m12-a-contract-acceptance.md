# 2026-09-17 — M12-A connector layer contract accepted

**Milestone:** 12 — MCP Connector Layer: M12-A contract acceptance and Git checkpoint
**Status on completion:** COMPLETED (DECISION ONLY) — ADR-0037 `Accepted`; M12-B `PLANNED` (not started); M12-C `BLOCKED`
**Supersedes:** None. Follows `2026-09-17-m12-a-connector-layer-contract.md` and
`2026-09-17-m12-a-contract-remediation.md`. Both are left unedited: their `Proposed` and `REVIEW` statements were
accurate when written.

## 1. Prompt / task performed

The owner approved ADR-0037 and confirmed OD-1 and OD-2 as final:

- **OD-1:** M12 may be `COMPLETED` on a fully implemented and verified M12-B. M12-C is a separate future capability,
  needing P-1 to P-5, separate architectural approval, separate security evidence and its own ADR, and it does not
  block M12-B.
- **OD-2:** exact registered identity — connector, server, transport, namespace and fully qualified tool — with no
  aliases, prefixes, patterns, case folding, vendor matching or inferred identity.

The task:

1. Record acceptance under the existing ADR conventions, without changing the decision's substance or ADR-0004.
2. Reconcile only the documentation that must reflect acceptance.
3. Validate.
4. Commit exactly once as `M12-A: connector layer contract`, push fast-forward, and verify.

No M12-B work and no Connector Gate measurement.

## 2. Objective

Make ADR-0037 the accepted contract without authorizing any implementation, connector or runtime use, and checkpoint
the reviewed M12-A work.

## 3. Changes made

1. **Verified:**
   - HEAD and `origin/main` (after `git fetch`) are both `ad6588c387634005d61033a117b4fa3586dc42bf`.
   - ADR-0004's working-tree blob `e51c0ede14a524060f7d1fa6db523b5acd28c93d` equals `HEAD:` — byte-identical.
2. **ADR-0037 acceptance**, status-bearing lines only:
   - The *Status* line reads `Accepted — 2026-09-17`, and states that acceptance approves the contract only and
     authorizes no connector, Connector Gate result or runtime use.
   - *Deciders* adds acceptance.
   - The decomposition row for M12-A, §L's M12-A line, the supersession sentence in *Relationship to ADR-0004*, and
     follow-up item 1 now record acceptance.
   - No rule, binding, boundary, code, test category or prohibition changed. OD-2's enumerated identity fields
     (connector, server, transport, namespace, tool) and its no-alias, prefix, pattern, case-folding,
     vendor-matching or inference rule were already stated in §B.1 and §B.4.
3. **Reconciliation:**
   - `architecture.md`: §10 cell, §11 contract heading and §19 row now say accepted.
   - `CONNECTORS.md`: status note says accepted, and that no connector is usable until implemented and Gate-passed.
     The Slack row "gated behind explicit approval" was changed to "not eligible in Milestone 12". It directly
     contradicted ADR-0037 §E.2 by implying Slack is usable with approval.
   - `docs/decisions/README.md`: 0037 row reads `Accepted — supersedes in part 0004`.
   - `docs/README.md`: the "(proposed)" marker is removed.
   - `project_plan.md`: summary row 12; M12-A → `COMPLETED (DECISION ONLY)` with contract rows `COMPLETED`; M12-B row
     states it is not started and that acceptance authorizes no implementation; M12-C stays `BLOCKED`.
   - Milestone 12 itself stays `PLANNED`; nothing implies M12-B exists.
4. **Not changed:**
   - ADR-0004, including its status line;
   - `.mcp.json`, `agents/`, `commands/`, `skills/`, `lib/`, `tests/`, `.claude-plugin/`, `config/`;
   - previously noted stale documentation unrelated to M12-A (`docs/integrations/README.md`, the M11 heading and
     the "Last updated" line in `project_plan.md`).

## 4. Files created

- `docs/development/2026-09-17-m12-a-contract-acceptance.md`

## 5. Files modified

- `docs/decisions/ADR-0037-m12-connector-layer-contract.md`
- `architecture.md`
- `CONNECTORS.md`
- `project_plan.md`
- `docs/decisions/README.md`
- `docs/README.md`

These files carry the whole reviewed M12-A change set; none was in the repository at `ad6588c` in its current form.

## 6. Files deleted

None.

## 7. Features implemented

None. Decision only. No connector is usable.

## 8. Tests performed

```
git fetch origin; git rev-parse HEAD origin/main
git hash-object docs/decisions/ADR-0004-…md; git rev-parse HEAD:docs/decisions/ADR-0004-…md
python tests/run_tests.py
claude plugin validate . --strict
git diff --check
```

Also run: a scripted documentation-consistency check and a secret-pattern scan of the changed files. Both results are
recorded in the task report and in §9 below.

## 9. Test results

```
Ran 4555 tests in 295.013s
OK (skipped=26)
ran 4555 | failures 0 | errors 0 | skipped 26
```

```
Validating marketplace manifest: …\.claude-plugin\marketplace.json
✔ Validation passed
```

Identical to the expected baseline (4,555 / 0 / 0 / 26).

## 10. Issues discovered

None new. The residual risks in ADR-0037 *Consequences* stand.

## 11. Decisions made

[ADR-0037](../decisions/ADR-0037-m12-connector-layer-contract.md) **Accepted**, 2026-09-17, with OD-1 and OD-2. It
supersedes in part ADR-0004's runtime-discovery and "user-configurable" clauses. ADR-0004 is unedited.

## 12. Architecture changes

ADR-0037 is now the accepted connector-layer contract. No component was built.

## 13. Project-plan updates

- M12-A: `REVIEW (DECISION ONLY)` → `COMPLETED (DECISION ONLY)`.
- M12-B: `PLANNED`, not started.
- M12-C: `BLOCKED`.
- Milestone 12: `PLANNED`.

## 14. Documentation updates

As §5.

## 15. Remaining work

M12-B, as its own implementation task, starting with the Connector Gate. M12-C stays `BLOCKED` pending P-1 to P-5,
separate approval, separate security evidence and its own ADR.

## 16. Git commit reference

Branch `main`, one commit `M12-A: connector layer contract` on top of `ad6588c`, pushed fast-forward to `origin/main`.
The resulting SHA is reported in the task report, since a record cannot contain the hash of the commit that contains
it.
