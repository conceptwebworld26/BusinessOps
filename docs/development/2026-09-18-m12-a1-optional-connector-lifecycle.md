# 2026-09-18 — M12-A.1 optional connector / user-initiated connection contract

**Milestone:** 12 — MCP Connector Layer: M12-A.1 contract clarification
**Status on completion:** COMPLETED (DECISION ONLY) — ADR-0038 `Accepted` 2026-09-18 with OD-3 resolved (final
remediation, §17); M12-A stays `COMPLETED (DECISION ONLY)`; M12-B `PLANNED` (not started); M12-C `BLOCKED`. The first
pass ended at `REVIEW (DECISION ONLY)` with ADR-0038 `Proposed`; §1–§16 describe that pass, amended where noted
**Supersedes:** None. Follows `2026-09-17-m12-a-contract-acceptance.md`, which is left unedited.

## 1. Prompt / task performed

The owner clarified a product requirement: **HubSpot must be an optional BusinessIQ connector.** BusinessIQ must remain
fully usable without it. A user who wants it must have a proper, explicit, user-initiated way to connect it through the
platform's supported mechanism. BusinessIQ must not assume HubSpot is connected because a HubSpot MCP server exists in
a session.

The task: write a **new** ADR, status `Proposed`, defining the optional-connector model and user-initiated connection
lifecycle without editing, weakening or replacing ADR-0037. Update `CONNECTORS.md`, `architecture.md`, `project_plan.md`
and the ADR indexes only as needed. Validate. No implementation, no Connector Gate measurement, no authentication, no
`.mcp.json` change, no commit and no push.

## 2. Objective

Make *supported*, *connected*, *authorized*, *verified capability* and *available for use* five distinct, individually
owned facts. Define a closed lifecycle over ADR-0037's existing vocabulary. Answer whether a "proper way to connect" can
be specified without specifying platform UI.

## 3. Changes made

1. **Verified state.** `git fetch origin`; `HEAD` = `origin/main` =
   `09cb52bd490ea3a175801bcb1a89319855256517` (`M12-A: connector layer contract`); working tree clean.
2. **Read:**
   - `CLAUDE.md`, `architecture.md` §11/§12/§16–§20, the `project_plan.md` M12 section, `CONNECTORS.md`;
   - ADR-0037 in full and ADR-0004 in full;
   - ADR-0014, ADR-0017, ADR-0018 and ADR-0035 (headers and decisions);
   - the ADR index, `docs/README.md`, `docs/integrations/README.md`, `.mcp.json`, the latest development records, and
     the repository's secret-keyword tests.
3. **Numbering.** The highest ADR is 0037, so the new ADR is **0038**.
4. **Conflict analysis against ADR-0037.** No conflict. Two readings of the brief would have conflicted, and the ADR
   resolves both from ADR-0037's own text:
   - "HubSpot is supported" read as a present fact. Under ADR-0037 *supported* means *registered*, and no registry
     exists. The ADR therefore states HubSpot as **designated**, in lifecycle state 1 today.
   - "A proper way to connect HubSpot" read as connecting any HubSpot server. ADR-0037 §B.4 admits only BusinessIQ's
     own declared entry, which does not exist until M12-B ships one through the Gate. The ADR says so plainly: there is
     no BusinessIQ HubSpot connection path yet.
5. **Wrote ADR-0038** (`Proposed`). Contents:
   - the optional-connector definition;
   - the five facts, each with who decides it and how BusinessIQ learns it;
   - the non-implication invariant;
   - a seven-state conceptual lifecycle mapped onto ADR-0037's §H codes, adding no runtime state or code, with all 19
     §H codes accounted for;
   - an evaluation order that puts static checks before any dispatch;
   - the user-initiated connection boundary;
   - HubSpot's designation and current status;
   - user messages per state, and the file fallback;
   - privacy, and the 17 security invariants mapped to where each is held;
   - the relationship to ADR-0037;
   - four M12-B obligations, carried through ADR-0037's existing §L items and §J categories;
   - one open owner decision, **OD-3**.
6. **Updated documentation:** `CONNECTORS.md`, `architecture.md` §11 and §19, `project_plan.md` (summary row 12, a new
   M12-A.1 subsection, a note on the M12-B row), `docs/decisions/README.md` and `docs/README.md`.
7. **Validated:** the full suite, strict validation, `git diff --check`, a scripted consistency check and a
   secret-pattern scan (§8–§9).

### Observation recorded, not measured

The brief reports a recent M12-B Connector Gate examination finding that third-party business-system servers are
exposed only through authentication tools, with no qualifying value-free discovery capability. **No record of that
examination exists in the repository.** ADR-0038 cites it as owner-reported, not as a Gate measurement.

This session's tool list contains `mcp__plugin_marketing_hubspot__authenticate` and
`mcp__plugin_marketing_hubspot__complete_authentication` and no other HubSpot tool. That is consistent with the report.
It is another plugin's server, which does not qualify under ADR-0037 §B.1 item 9. **No tool was called.**

## 4. Files created

- `docs/decisions/ADR-0038-optional-connector-connection-lifecycle.md`
- `docs/development/2026-09-18-m12-a1-optional-connector-lifecycle.md`

## 5. Files modified

- `CONNECTORS.md`
- `architecture.md`
- `project_plan.md`
- `docs/decisions/README.md`
- `docs/README.md`

## 6. Files deleted

None.

## 7. Features implemented

None. Decision only. No connector is registered, declared, measured, connected or usable.

## 8. Tests performed

```
git fetch origin; git rev-parse HEAD; git rev-parse origin/main; git log -1 --oneline
python tests/run_tests.py
claude plugin validate . --strict
git diff --check
```

Also run:

- **Consistency check** (scripted, in the session scratchpad; the repository has no documentation-consistency test).
  It covers:
  - ADR-0038's references to ADR-0037 sections and §J categories;
  - coverage of all §H codes;
  - no lifecycle name colliding with a §H code;
  - ADR-0038's internal section references;
  - relative links in every changed file;
  - index presence in all four places;
  - forbidden present-tense claims about HubSpot.
- **Secret-pattern scan** of every added line and the new ADR, for token-shaped values: AWS, GitHub, Slack,
  `sk-`-style keys, HubSpot private-app tokens, JWTs, bearer strings, private keys, key/secret/password/token
  assignments, long hex strings, emails, URLs and connection strings. The repository's own secret tests
  (`test_manifest`, `test_config`) are keyword tests over JSON config. They are part of the full suite, and they would
  flag prose that says "no tokens", so the documentation scan checks values instead.
- **Immutability** of ADR-0004 and ADR-0037: working-tree blob hashes compared with `HEAD:`.

## 9. Test results

Final run, on the finished tree:

```
Ran 4555 tests in 248.859s
OK (skipped=26)
ran 4555 | failures 0 | errors 0 | skipped 26
```

An earlier run overlapped the documentation edits and gave the same result (4,555 / 0 / 0 / 26, 715.302s). Both are
identical to the expected baseline.

```
Validating marketplace manifest: …\.claude-plugin\marketplace.json
✔ Validation passed
```

- **`git diff --check`:** exit 0, no whitespace errors. It printed only `core.autocrlf` notices. Line endings are
  unchanged: HEAD and the working copy are both LF.
- **Consistency check:** passes on review. The script reported three kinds of flag, and each is a false positive:
  - five ADR-0037 references (§A.1, §E.2, §E.3, §E.6, §E.9) that the script expected as headings — they exist as bold
    paragraph labels;
  - one `§16`, which refers to `architecture.md` §16;
  - three "HubSpot is connected/registered" matches, which are negations or quoted anti-patterns, not claims.

  All 19 §H codes are accounted for. No lifecycle name collides with a §H code. The §J references (13, 15, 16, 19)
  exist. Internal references resolve. No links are broken. ADR-0038 is present in all four indexes.
- **Secret-pattern scan:** 0 hits in every value class. The only URL found is `https://mcp.hubspot.com/anthropic`,
  the public endpoint already recorded in ADR-0004 and `CONNECTORS.md`.
- **Immutability:** ADR-0004 (`e51c0ed…`), ADR-0037 (`42f3f28…`), `CLAUDE.md` and `.mcp.json` are byte-identical to
  `HEAD`.

## 10. Issues discovered

- **No repository record** of the owner-reported M12-B Connector Gate examination (§3).
- **No BusinessIQ HubSpot connection path exists yet.** This is not a defect. It follows from ADR-0037 §B.4, because
  BusinessIQ has declared no HubSpot server entry. It is stated in ADR-0038 *Consequences* and `CONNECTORS.md`.
- **OD-3** was open at the end of the first pass. It decides whether a connector with no complete discovery chain may
  still be registered and have its `.mcp.json` entry shipped. Recommended: no. Resolved in §17.
- **`docs/integrations/README.md` is stale** ("Empty until Milestone 11"). Noted before, in the M12-A acceptance record,
  and left alone. No integration page is created here; that is M12-B work.
- Pre-existing D-11 (ADR-0017 and ADR-0018 missing from the indexes) is unchanged. It is unrelated to this task.

## 11. Decisions made

[ADR-0038](../decisions/ADR-0038-optional-connector-connection-lifecycle.md). The first pass left it `Proposed`, with OD-3
awaiting the owner. It is now **Accepted** with OD-3 resolved (§17). It clarifies ADR-0037 and supersedes and amends
nothing.

## 12. Architecture changes

`architecture.md` §11 records:

- the planned status;
- the five facts;
- the lifecycle;
- the OD-3 admission rule;
- HubSpot's designated, not-supported status, as ADR-0038 (accepted).

§19 lists 0038 as `Accepted`. No component was built.

## 13. Project-plan updates

- New **M12-A.1**: `REVIEW (DECISION ONLY)` in the first pass, then `COMPLETED (DECISION ONLY)` on acceptance (§17).
- M12-A: `COMPLETED (DECISION ONLY)`, unchanged.
- M12-B: `PLANNED`, not started. The OD-3 admission rule and the ADR-0038 §12 obligations apply.
- M12-C: `BLOCKED`, unchanged.
- Milestone 12: `PLANNED`.

## 14. Documentation updates

As §5.

## 15. Remaining work

- ~~Owner review of ADR-0038 and a decision on OD-3~~ — done, §17.
- M12-B, as its own implementation task, starting with the Connector Gate.
- M12-C stays `BLOCKED`.

## 16. Git commit reference

N/A. Nothing committed or pushed; the change set is left uncommitted for review.

## 17. Final remediation — OD-3 resolved and ADR-0038 accepted (2026-09-18)

### Owner decision (OD-3)

- A connector may be described in documentation as **planned, designated or future** without being a currently
  supported connector.
- **Admission rule.** A connector must not be represented as a currently supported or usable connector in the shipped
  registry, and its `.mcp.json` entry is not shipped, unless at least one declared capability in its declared v1 scope
  has a complete, approved, BusinessIQ-owned Connector-Gated chain.
- **Not qualifying:**
  - documentation naming the connector;
  - designation as a future connector;
  - a vendor MCP endpoint;
  - another plugin's server;
  - the user being able to authenticate to some vendor server;
  - a same-vendor connector elsewhere.

  Another plugin's server, tool or namespace can never satisfy BusinessIQ's declaration.
- **For M12-B, the admission capability is value-free discovery.** Its chain needs every one of:
  - a BusinessIQ-declared server identity;
  - the exact server and transport identity;
  - the exact namespace;
  - the exact fully qualified tool identity;
  - a Connector Gate measurement;
  - an approved value-free output proof;
  - a matching agent grant;
  - a matching sealed-operation binding.
- The rule does not require every future connector to expose discovery permanently. It governs the declared v1 scope.
- It does **not** unblock M12-C, which stays `BLOCKED` on P-1 to P-5 and its own ADR.
- Optionality, the user-initiated authentication boundary (no credential ever received, stored, logged or transmitted)
  and the Connector Gate are unchanged. A connection never substitutes for Gate approval.

### HubSpot

HubSpot is a designated optional future connector. It is **not** a currently supported or usable BusinessIQ connector,
because no BusinessIQ-owned, Connector-Gated value-free discovery capability has been approved. No HubSpot connector
exists in BusinessIQ, and BusinessIQ has no HubSpot connection path. The `marketing` plugin's HubSpot server does not
qualify. Core file functionality is independent of HubSpot.

### Contradiction check

OD-3 narrows what ADR-0037 permits: §D.1 allows a registered connector with no complete chain, but does not require
one. It weakens nothing. ADR-0037's `capability_unsupported`, `stale_metadata` and `binding_mismatch` still apply to a
scope no chain covers, to post-admission staleness and to defects. §L item 1 still lets M12-B complete with no
connector admitted. **No change to ADR-0037 or ADR-0004 was needed, and none was made.**

### ADR-0038 changes

- Status → `Accepted — 2026-09-18`, and *Deciders* records OD-3 and acceptance.
- The Decision paragraph: "none implies another" became "none substitutes for another". Under OD-3, support is
  admitted only on a verified capability, so the exact statement is a one-way admission dependency. Support still
  never implies that the capability requested now is verified or still current.
- *Planned* is defined as a documentation-only status.
- The §2 Supported row and the §3 invariant table now carry the admission rule.
- The §4 state 1 row names planned connectors. The state 2 row is narrowed to an uncovered scope, staleness or a
  defect. Transition rule 1 requires OD-3.
- §7 opens with the one-sentence HubSpot status and gains a "currently supported?" row.
- §8 states that the HubSpot messages for states 2–7 apply only after admission.
- §11 records that OD-3 narrows ADR-0037.
- §12 gains obligation 5: static enforcement of the admission rule, under §L item 4 and §J-19, with no new test
  category.
- *Owner decision required* becomes *Owner decision — OD-3, resolved*.
- *Consequences*, *Follow-up* and *Revisit when* are reconciled.

### Other documentation reconciled

- `CONNECTORS.md`: the status note says accepted; the planned status and the admission-qualified Supported row are
  added; the HubSpot paragraph uses the owner's wording; *Adding a connector* states the admission rule.
- `architecture.md` §11 and §19.
- `project_plan.md`: summary row 12; M12-A.1 → `COMPLETED (DECISION ONLY)` with its rows `COMPLETED`; the M12-B row.
- `docs/decisions/README.md` and `docs/README.md`: accepted.

### Not done

No implementation, registry, schema, agent, command, skill, `.mcp.json` change, MCP server, authentication, call to an
authentication tool, Connector Gate measurement, commit or push.

### Validation (final remediation)

See §18.

## 18. Final remediation — validation results

Run on the finished tree after every final-remediation edit except this section. This section adds prose only.

```
Ran 4555 tests in 225.250s
OK (skipped=26)
ran 4555 | failures 0 | errors 0 | skipped 26
```

This is identical to the baseline: 4,555 / 0 / 0 / 26.

```
Validating marketplace manifest: …\.claude-plugin\marketplace.json
✔ Validation passed
```

- **`git diff --check`:** exit 0. The new files have no trailing whitespace and no CR.
- **Consistency script** (same as §9):
  - all 19 §H codes are accounted for, and no lifecycle name collides with a §H code;
  - the §J references (13, 15, 16, 19) exist;
  - no links are broken, and ADR-0038 appears in all four indexes;
  - the flags are the known false positives from §9, plus `Status:** Accepted`, which is now intended.
- **Wording scans:**
  - No current document calls ADR-0038 proposed or OD-3 open. The only such lines are first-pass history in this
    record, labelled as such.
  - Every "HubSpot is supported/connected/registered" match is a negation or a quoted anti-pattern.
- **Secret-pattern scan** of the added diff lines plus both new files (71,058 characters): 0 hits in every value class.
  The only URL is `https://mcp.hubspot.com/anthropic`, the public endpoint in ADR-0004. The only 40-hex string is
  commit `09cb52b…`.
- **Immutability:** ADR-0004, ADR-0037, `CLAUDE.md` and `.mcp.json` are byte-identical to `HEAD`.
- **Scope:**
  - No change under `.mcp.json`, `agents/`, `commands/`, `skills/`, `lib/`, `tests/`, `.claude-plugin/`, `config/`,
    `CLAUDE.md`, `evals/`, `assets/` or `reference/`.
  - The diff touches only `architecture.md` §11 and §19, `project_plan.md` row 12 and the M12 section, the two index
    lines, `CONNECTORS.md`, and the two new files.
- **No authentication tool was called, and no connector was authenticated.** No commit, no push.
