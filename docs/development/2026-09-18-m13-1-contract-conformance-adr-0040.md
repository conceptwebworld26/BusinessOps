# 2026-09-18 — M13.1 contract conformance: ADR-0040, the owner-accepted environment-unavailable gap

**Milestone:** 13 — Test Hardening & Evals, part M13.1 (deterministic hardening) under ADR-0039, as amended by
ADR-0040
**Status on completion:** REVIEW. The ADR-0039 §L completion gate is now satisfied under ADR-0039 as amended by
ADR-0040. M13.1 awaits the owner's approval and is **not** git-checkpointed. M13.2 was not started. Nothing committed.
**Supersedes:** `docs/development/2026-09-18-m13-1-final-remediation.md`, in part:

- §11 *The contradiction*;
- the "Not met, for S2-14" row of its §L table;
- §15 item 1.

That record and every earlier record are unchanged.

## 1. Prompt / task performed

The owner's "M13.1 contract conformance remediation" prompt. It asked for three things:

- a small new ADR that resolves the ADR-0039 §L contradiction by introducing an owner-accepted,
  environment-unavailable gap category, with S2-14 as its first application;
- minimal documentation reconciliation;
- a re-evaluation of the M13.1 completion gate, with focused validation only.

The prompt prohibited:

- editing ADR-0039 in place;
- inventing a defect id for S2-14, or reclassifying it as a product or infrastructure defect;
- marking S2-14 covered, or weakening the eight skipped tests;
- installing openpyxl;
- any production change;
- M13.2 and evals;
- connectors;
- `.mcp.json`;
- committing or pushing;
- marking the milestone git-checkpointed.

## 2. Objective

Let M13.1's completion gate be evaluated truthfully. That means:

- S2-14 stays a visible, uncounted gap;
- no defect is invented;
- no evidence is upgraded;
- ADR-0039's evidence discipline is left intact.

## 3. Changes made

1. **Baseline.**
   - `HEAD` = `990e88d5f13db65b2ecdf0737c7f613b83c6034d`.
   - The working tree was the M13.1 tree left by the final remediation: 6 modified files and 16 untracked.
   - Every modified and untracked file was hashed into the scratchpad before editing.
2. **Conventions inspected.**
   - `docs/decisions/README.md`: sequential numbers, immutable once accepted, and index entries in
     `architecture.md` §19 and `docs/README.md`.
   - `docs/templates/adr.md`.
   - The ADR headers of 0002, 0008, 0023 and 0038.
   - The repository's precedent for amending an ADR that may not be edited: ADR-0022 and ADR-0004 kept their text
     and status lines, and the amendment was recorded in the new ADR, the decisions index note and §19.
3. **Next number, from the repository.** The highest existing ADR is 0039, and no `ADR-0040*` exists in the tree or
   in git history. The new ADR is therefore **0040**.
4. **ADR-0040 written.** It covers:
   - the three-way distinction;
   - five eligibility conditions;
   - the eleven-field disposition record;
   - the "never" rules;
   - the exact amended wording;
   - an explicit "everything else unchanged" list;
   - S2-14 as the first application, using recorded facts only.
5. **Documentation reconciled** (§5).
6. **The completion gate re-evaluated** (§11), and focused validation run (§9, §17).

## 4. Files created

- `docs/decisions/ADR-0040-m13-owner-accepted-environment-gap.md`
- `docs/development/2026-09-18-m13-1-contract-conformance-adr-0040.md` (this record)

## 5. Files modified (in this pass)

| File | Change |
|---|---|
| `docs/testing/coverage-matrix.md` | Header cites ADR-0040. `gap` column definition. S2-14 row notes. Gap-kinds table. S2-14 section now has the ADR-0040 §3 disposition record table. The "ADR-0039 conformance" paragraph is rewritten to the amended rule |
| `docs/testing/defects.md` | The S2-14 note cites ADR-0040: not a product defect, not a test-infrastructure defect, never an `M13-DEF-NN` id |
| `docs/testing/README.md` | The S2-14 sentence uses the exact label and cites ADR-0040 |
| `project_plan.md` | Header. Milestone summary row 13. M13 sub-milestone row. M13.1 table: the U-1 row, and the §L completion-check row, `BLOCKED` → `COMPLETED` |
| `architecture.md` | §15, one sentence after the M13 contract paragraph. §19, an ADR-0040 index row |
| `docs/decisions/README.md` | ADR-0040 index row, and the *Amended / refined* note |
| `docs/README.md` | ADR-0040 list entry |
| `tests/unit/test_m13_coverage_matrix.py` | Module docstring and the `OWNER_DECISIONS` comment only. **No executable line or assertion changed** |

## 6. Files deleted

None.

## 7. Features implemented

None. This was a governance and documentation amendment only.

## 8. Tests performed

Focused only. The full 4,749-test suite was **not** re-run: no executable test line and no production file changed.
The only test-file change is to comments. Each module was run separately, because `tests/run_tests.py` loads only its
first argument:

- the seven M13.1 modules;
- `unit.test_m12b_connector_registry`, which scans every `docs/development/` file for a Gate block;
- `unit.test_manifest`, which checks that the repository documents exist.

Strict validation, `git diff --check`, the secret scan and the scope audit followed (§17).

## 9. Test results

```
unit.test_m13_coverage_matrix              ran 26 | failures 0 | errors 0 | skipped 0
unit.test_m13_discriminability             ran 13 | failures 0 | errors 0 | skipped 0
integration.test_m13_selection_stability   ran 5 | failures 0 | errors 0 | skipped 0
integration.test_m13_large_dataset         ran 6 | failures 0 | errors 0 | skipped 2
negative.test_m13_error_handling           ran 5 | failures 0 | errors 0 | skipped 0
negative.test_m13_approval_boundaries      ran 4 | failures 0 | errors 0 | skipped 0
negative.test_m13_tier_rows                ran 6 | failures 0 | errors 0 | skipped 0
unit.test_m12b_connector_registry          ran 51 | failures 0 | errors 0 | skipped 0
unit.test_manifest                         ran 15 | failures 0 | errors 0 | skipped 0
```

The last full-suite run, from the final remediation, stands for the unchanged executable tree: 4,749 tests,
0 failures, 0 errors, 28 skipped, 414.476 s.

## 10. Issues discovered

None new.

- **Open defects:** M13-DEF-01 and M13-DEF-03, both product, `open`, not fixed, and remediation unassigned.
- **Resolved defect:** M13-DEF-02, `fixed_infrastructure`.

## 11. Decisions made

**[ADR-0040](../decisions/ADR-0040-m13-owner-accepted-environment-gap.md), Accepted 2026-09-18.** It amends ADR-0039
in part: two passages only. ADR-0039's file is unedited.

- **§B, status `gap`:**
  - As accepted: "`gap` — with the defect id (§G.1) that explains why it is still open."
  - Amended, adding: "…or, for an owner-accepted environment-unavailable gap, the complete disposition record of
    ADR-0040 §3."
- **§L, M13.1 `COMPLETED`, second condition:**
  - As accepted: "every deterministic gap either closed, or `gap` with a defect id;"
  - Amended, adding: "…or `gap` with a complete owner-accepted environment-unavailable disposition (ADR-0040 §2 and
    §3);"

The ADR's status is **Accepted**. It records acceptance in the owner's prompt, which directed this amendment and
specified its content. If the owner intended a `Proposed` → acceptance step, the status line is the one place to
change.

**M13.1 completion gate, re-evaluated under ADR-0039 as amended:**

| §L condition | Result |
|---|---|
| Matrix closed against S1–S7, every row statused | Met: 99 rows, and the validator recounts every set |
| Every deterministic gap closed, or `gap` with a defect id, or `gap` with a complete ADR-0040 disposition | **Met.** S1-17 → M13-DEF-03. S2-14 → the ADR-0040 §3 record, all eleven fields present, and all five §2 conditions hold |
| D.1 executed and recorded; D.2 and D.3 recorded | Met |
| Every defect recorded, none `blocks_m13_completion: yes` | Met. DEF-01 and DEF-03: `product`, `open`, `no`. DEF-02: `infrastructure`, `fixed_infrastructure`, `no` |
| K.1 to K.6 | Met. K.1 and K.5 rest on the 414.476-second full run, unchanged since for executable content; K.3, K.4 and K.6 re-run here (§17) |
| Plan, architecture, development record, task report | Met |
| Commit only on the owner's request | Met: nothing committed |

**What did not change:**

- S2-14 is still `gap` / `execution_unavailable`, labelled OPEN GAP — ENVIRONMENT UNAVAILABLE, and not covered.
- The totals are still 76 `covered`, 3 `covered-by-M13`, 18 `behavioural-only`, 0 `not-applicable` and 2 `gap`.
- No defect was invented, and no evidence was upgraded.
- No production behaviour changed.

M13.1 **satisfies its completion gate**. It remains `REVIEW` pending the owner's approval, and it is not
git-checkpointed.

## 12. Architecture changes

No design change:

- §15 gained one sentence noting the ADR-0040 amendment;
- §19 gained the ADR-0040 index row.

## 13. Project-plan updates

| Item | Change |
|---|---|
| §L completion check | `BLOCKED` → `COMPLETED`, satisfied under the amended ADR |
| U-1 row | Cites ADR-0040 |
| Header, summary row 13, sub-milestone row | State that the gate is satisfied, M13.1 is awaiting owner approval, and it is not checkpointed |
| M13.1 | Stays `REVIEW` |
| Unchanged | M13 `IN PROGRESS`; M13.2 `PLANNED`, not authorised; M9 `IN PROGRESS`; M12-C `BLOCKED` |

## 14. Documentation updates

As §5. Not edited:

- ADR-0039 and every other accepted ADR;
- `CLAUDE.md`;
- `README.md`;
- `CONNECTORS.md`;
- `docs/testing/measurements.md`, which holds no §L wording;
- every earlier development record.

## 15. Remaining work

1. **Owner:** approve M13.1, which would move it from `REVIEW` to `COMPLETED`, and decide whether to checkpoint it.
2. **Owner:** assign remediation milestones to M13-DEF-01 and M13-DEF-03. Both are unassigned.
3. **Owner:** closing S2-14 needs a recorded run in the ADR-0040 closure environment. That is optional, and outside
   M13.1.
4. **M13.2:** only under its own authorising prompt.
5. **Unchanged:**
   - M9's four fresh-session live smoke tests;
   - M12-C `BLOCKED`;
   - D-13 and D-14;
   - R-01, R-05, R-10, R-11 and R-12.

## 16. Git commit reference

N/A. Nothing was committed, amended, pushed, stashed or reset. Branch `main`, base `990e88d`. Not git-checkpointed.

## 17. Final validation

| Check | Result |
|---|---|
| Focused tests | §9: 131 tests across 9 modules, 0 failures, 0 errors, 2 opt-in skips |
| `claude plugin validate . --strict` | `✔ Validation passed`, exit 0 |
| `git diff --check` | Clean, exit 0 (CRLF-conversion warnings only). No untracked file has trailing whitespace |
| Secret scan | The six new or untracked files touched (1,183 lines), plus every added line in the four tracked files touched. The only hit is the public commit id in this record |
| Validator unchanged in behaviour | Reversing this pass's two comment edits reproduces the file's session-start SHA-256 (`37cc2da3…`) byte for byte, so nothing but the docstring and one comment changed |
| ADR-0001 to ADR-0038 | 38 of 38 blob hashes equal `HEAD:` |
| ADR-0039 | Unedited. Its SHA-256 still equals the session-start hash (`53fec3b3…`) |
| Protected paths | `git status --porcelain` is empty for `lib/`, `skills/`, `commands/`, `agents/`, `reference/`, `config/`, `assets/`, `.claude-plugin/`, `.mcp.json`, `tests/run_tests.py`, `.gitignore`, `CLAUDE.md` and `README.md`. `CONNECTORS.md` shows as modified by an earlier session; its hash equals the session-start snapshot |
| Files changed by this pass | Against a snapshot taken before this pass: exactly the 8 modified files in §5 and the 2 new files in §4 |

**Confirmations:**

- **No production change.** No production file or behaviour changed.
- **Defects unchanged.** No defect was invented, fixed or reclassified.
- **Evidence unchanged.** No evidence was upgraded, and no test was weakened, removed or skipped.
- **No dependency installed.** openpyxl was not installed.
- **Nothing external.** No connector, MCP tool, authentication, web access or eval was used.
- **Nothing committed.** Nothing was committed, pushed, amended, stashed or reset, and the milestone is not marked
  git-checkpointed.
