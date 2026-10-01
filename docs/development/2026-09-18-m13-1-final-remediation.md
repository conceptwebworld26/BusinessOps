# 2026-09-18 — M13.1 final remediation: U-1 resolved, defect disposition verified, regression re-timed

**Milestone:** 13 — Test Hardening & Evals, part M13.1 (deterministic hardening) under ADR-0039 (Accepted)
**Status on completion:** REVIEW. U-1 is resolved. The ADR-0039 §L completion check found one conformance point that
only the owner can resolve (§11), so M13.1 is **not** marked `COMPLETED`. M13.2 was not started. Nothing committed.
**Supersedes:** `docs/development/2026-09-18-m13-1-deterministic-hardening.md`, in part:

- §10 *Open owner decision* (U-1): now resolved as (c);
- §15 item 1: U-1 decided; item 2: the dispositions are recorded, remediation is unassigned;
- §17's unexplained wall time: re-timed here.

That record is otherwise unchanged and was not edited.

## 1. Prompt / task performed

The owner's "M13.1 final remediation" prompt, run in a fresh session. It asked for five things, and only these:

- record the owner's U-1 decision, (c) accept S2-14 as an open gap, and show S2-14 as
  `OPEN GAP — ENVIRONMENT UNAVAILABLE`;
- verify that M13-DEF-01 and M13-DEF-03 stay recorded as open product defects, unfixed, with a future disposition
  taken from the real `project_plan.md`, never invented;
- verify that M13-DEF-02 stays a resolved infrastructure defect;
- re-time the full regression suite exactly once;
- check M13.1 against ADR-0039 §L, and stop and report rather than edit ADR-0039 if it does not permit completion.

The prompt excluded:

- M13.2, eval execution and `claude plugin eval`;
- any production change, and any fix of M13-DEF-01 or M13-DEF-03;
- installing openpyxl, or fabricating a Tier-1 environment;
- connectors, authentication and `.mcp.json`;
- M12-C;
- editing an accepted ADR;
- committing, pushing or amending.

## 2. Objective

Leave M13.1 in a state a reviewer can approve or reject on its merits:

- the one open decision recorded;
- the defect register verified;
- the anomalous runtime either reproduced or shown to be a single observation;
- conformance to ADR-0039 stated exactly.

## 3. Changes made

1. **Baseline.** `git status --short --branch` showed exactly the M13.1 working tree: 6 modified files and 15
   untracked. After `git fetch origin`, `HEAD` = `origin/main` = `990e88d5f13db65b2ecdf0737c7f613b83c6034d`. Every
   modified and untracked file was hashed into the scratchpad before any edit. Nothing was discarded, stashed or
   reset.
2. **Reading.** `CLAUDE.md`, ADR-0039 in full, the M13 parts of `project_plan.md` and `architecture.md`, the matrix, the
   register, the measurements, the M13.1 record, the matrix validator, `runtime/tiers.py`, `ingest/canonical.py` and
   ADR-0008.
3. **Environment facts for U-1, re-verified.** The system interpreter is Python 3.13.1, and `import openpyxl` fails
   with `ModuleNotFoundError: No module named 'openpyxl'`. `tests/integration/test_data_layer.py` gates its Tier-1
   comparisons on `skipUnless(openpyxl_available(), "openpyxl absent; Tier 1 cannot be compared here")`.
4. **U-1 recorded** (§11). The S2-14 row, the column definitions, a gap-kinds table and a new *S2-14* section were
   added to `coverage-matrix.md`.
5. **Defects re-verified.**
   - **M13-DEF-01:** the recorded reproducer was re-run, and printed
     `{'biq-competitor-analysis': 1065, 'biq-industry-research': 1158}`.
   - **M13-DEF-03:** it was reproduced independently at the threshold, by a scratchpad script outside the
     repository. That is not a D.1 re-run, and the D.1 measurement was not re-parameterised (see §9).
   - **Register:** a state table and per-record *Disposition* lines were added to `defects.md`, outside the §G.1 field
     tables. No field, status or class changed.
6. **Validator comment.** In `tests/unit/test_m13_coverage_matrix.py`, the docstring and the `OWNER_DECISIONS` comment
   now say that U-1 is resolved. **No assertion changed.**
7. **A documentation bug introduced and fixed in this pass.** The first version of the gap-kinds table began its rows
   `| S1-17 |` and `| S2-14 |`, which the validator's row pattern reads as matrix rows. The focused run failed with 2
   `IndexError` errors in `setUpClass`. The ids were back-quoted, and the validator was not loosened. The focused
   tests then passed.
8. **Focused tests**, then **one** full timed run (§9).
9. **ADR-0039 §L completion check** (§11).
10. **Documentation:**
    - `project_plan.md`;
    - `measurements.md`, whose new section is an observation, not a §D measurement;
    - `docs/testing/README.md`;
    - this record.
11. **Validation and scope audit** (§17).

## 4. Files created

- `docs/development/2026-09-18-m13-1-final-remediation.md` (this record)

## 5. Files modified (in this pass)

All six were already uncommitted M13.1 files. None is a production file.

- `docs/testing/coverage-matrix.md`:
  - `gap` column definition;
  - S2-14 row;
  - gap-kinds table;
  - evidence summary;
  - new *S2-14* section.
- `docs/testing/defects.md`: register-state table, and three *Disposition* paragraphs, plus a *Why the metadata is
  inconsistent* paragraph for DEF-03.
- `docs/testing/measurements.md`: new section, *Regression-suite wall clock*.
- `docs/testing/README.md`: the index row for `measurements.md`, and one sentence on S2-14.
- `project_plan.md`:
  - header;
  - milestone summary row 13;
  - M13 sub-milestone row;
  - M13.1 table: the U-1 row resolved, and two new rows, the §L completion check and the regression re-time;
  - Known issues rows for M13-DEF-01, 02 and 03.
- `tests/unit/test_m13_coverage_matrix.py`: comments and docstring only.

## 6. Files deleted

None. Scratchpad only, outside the repository:

- the pre-edit hash list;
- the DEF-03 threshold script, whose temporary CSVs were deleted after the run;
- the full-run log and timing file;
- this record's draft.

## 7. Features implemented

None. This pass changed documentation, plus comments in one test module.

## 8. Tests performed

- The seven M13.1 modules, one at a time. `tests/run_tests.py` loads only the first name it is given, so each was a
  separate run: `python tests/run_tests.py <module>`.
- `python tests/run_tests.py unit.test_m13_coverage_matrix`, re-run after the gap-kinds fix.
- **One** full run, `python tests/run_tests.py -v`, the same invocation as the M13.1 closing run. It was wrapped in
  `date` stamps for wall clock and logged to the scratchpad.
- The DEF-01 reproducer (§3.5).
- The DEF-03 threshold reproduction (§3.5).
- `claude plugin validate . --strict`, `git diff --check`, the secret scan, and the protected-path and ADR hash audit
  (§17).

**Not executed:**

- any `claude plugin eval`;
- the opt-in `BIQ_LARGE_DATASET`, `BIQ_AGENT_BOUNDARY_RUNTIME` and `BUSINESSIQ_LIVE_SMOKE` suites;
- any Tier-1 test (U-1).

## 9. Test results

**Focused M13.1 modules** (after the gap-kinds fix):

```
unit.test_m13_coverage_matrix              ran 26 | failures 0 | errors 0 | skipped 0
unit.test_m13_discriminability             ran 13 | failures 0 | errors 0 | skipped 0
integration.test_m13_selection_stability   ran 5 | failures 0 | errors 0 | skipped 0
integration.test_m13_large_dataset         ran 6 | failures 0 | errors 0 | skipped 2
negative.test_m13_error_handling           ran 5 | failures 0 | errors 0 | skipped 0
negative.test_m13_approval_boundaries      ran 4 | failures 0 | errors 0 | skipped 0
negative.test_m13_tier_rows                ran 6 | failures 0 | errors 0 | skipped 0
```

That is 65 tests, 0 failures, 0 errors and 2 skips. The skips are D1's opt-in tests, with `BIQ_LARGE_DATASET` unset.
Before the fix, `unit.test_m13_coverage_matrix` gave `ran 7 | failures 0 | errors 2 | skipped 0` (§3.7).

**DEF-03 threshold reproduction** (scratchpad `def03_check.py`, synthetic
`fixtures.build_m13_large_fixtures.large_csv`):

```
100000 full complete= True examined= 100000 rows= 100000 revenue= available caveats= [] src_unchanged= True
100001 streamed complete= False examined= 100001 rows= 100001 revenue= partial caveats= ['Only 100001 of 100001 rows were examined (streamed processing); figures describe the examined portion.'] src_unchanged= True
```

**Full suite, second timing run:** `python tests/run_tests.py -v`, once, on the tree after the documentation and comment edits
and before this record existed:

```
START 2026-09-18T23:07:26+05:30
Ran 4749 tests in 414.476s
OK (skipped=28)
ran 4749 | failures 0 | errors 0 | skipped 28
EXIT 0
END 2026-09-18T23:14:21+05:30
```

- **Tests:** 4,749, the same count as the M13.1 closing run. This pass added no test.
- **Skips:** 28, unchanged. There are 26 baseline skips:
  - 7 in `test_data_layer.TestCrossTierEquivalence` and 1 in `test_vertical_slice.TestCrossTierEquivalence`
    (openpyxl absent);
  - 3 in `test_vertical_slice.TestScenarioFTier1Xlsx` (openpyxl absent);
  - 6 in `test_tier2_runtime.TestTier2OutOfProcess` (no managed runtime);
  - 2 in `test_m9b_live_smoke` (opt-in);
  - 7 in `test_m11_verifier_agent_boundary` (opt-in).

  The other 2 are D1's opt-in skips.
- **Failures and errors:** 0 and 0.
- **Wall clock:** 414.476 s by unittest, and 415 s between the `date` stamps.
- **Host at the start:** Windows 11, the *Balanced* power scheme, about 1.0 GB of 16 GB RAM free, and 14 % CPU load.
  The only other Python process was the idle `biq-verifier` server.
- **K.5, re-checked against this run** (scratchpad `k5_recheck.py`, which parses the verbose log):
  - 4,749 outcomes parsed;
  - all 205 citations in `covered` and `covered-by-M13` rows are `ok`;
  - S1-17's four citations are `ok`, because its gap is a product defect, not a skip;
  - S2-14's three citations are `skipped`, as the matrix states.

## 10. Issues discovered

- **The ADR-0039 §L conformance point for S2-14** (§11). This is the one open item.
- **Runtime:** the 7,694-second closing run did **not** reproduce: the re-time took 414.476 s for the same 4,749 tests. It is recorded as an anomalous single observation, not a regression, with no defect and no assigned cause (`measurements.md`, *Regression-suite wall clock*). Wall clock on this machine varies widely: 850 s, then 7,694 s, then 414 s. ADR-0039 defines no runtime threshold, so none is applied.
- **Nothing new in the product.** M13-DEF-01 and M13-DEF-03 reproduce exactly as recorded. No new defect id was
  assigned.

## 11. Decisions made

**U-1, owner decision (c), 2026-09-18: accept S2-14 as an open gap.** It is recorded as
`OPEN GAP — ENVIRONMENT UNAVAILABLE`:

- **Status and evidence:** status `gap`, evidence `execution_unavailable`, citing U-1.
- **Not a pass:** the row is not counted as covered, passed, runtime-verified or equivalent.
- **No defect record:** it is an environment and coverage gap, not evidence of a product defect.
- **Nothing added to cover it:** no test was weakened or replaced, no synthetic stand-in was added, and openpyxl was
  not installed.
- **How it could close:** a future run in an owner-approved environment could close it.

**ADR-0039 §L completion check.** Each condition, checked against the tree:

| §L condition for M13.1 `COMPLETED` | Result |
|---|---|
| Matrix closed against S1–S7, every row present and statused | **Met.** 99 rows; the validator recounts every set from its source |
| Every deterministic gap either closed, or `gap` with a defect id | **Not met, for S2-14.** S1-17 is `gap` with M13-DEF-03, as required. S2-14 is `gap` with **no** defect id |
| D.1 executed once and recorded | Met: M13-MEAS-D1 |
| D.2 and D.3 recorded under D.4 | Met: M13-MEAS-D2 and D3 |
| Every defect recorded under §G.1, none `blocks_m13_completion: yes` | Met. DEF-01 and DEF-03 are `product`, `open`, `no`. DEF-02 is `infrastructure`, `fixed_infrastructure`, `no` |
| K.1 — suite 0 failures, 0 errors; skip changes explained | Met. The re-time gave 4,749 tests, 0 failures, 0 errors. The 28 skips are the 26 baseline skips plus D1's 2 opt-in skips, all explained |
| K.2 — no existing test module edited except by retargeting | Met. No pre-M13 module is modified. The only edited test file is M13.1's own validator, in comments |
| K.3 — strict validation | Met (§17) |
| K.4 — diff check and secret scan | Met (§17) |
| K.5 — every `covered` row's tests ran unskipped in the closing run | Met, re-checked against the re-time: 205 of 205 `covered` citations `ok` |
| K.6 — scope audit | Met (§17) |
| Plan, architecture, dev record, task report | Met. `architecture.md` needed no change: no architectural fact changed |
| Commit only on the owner's request | Met: nothing committed |

**The contradiction.** ADR-0039 §B defines `gap` as "with the defect id (§G.1) that explains why it is still open".
§L requires "every deterministic gap either closed, or `gap` with a defect id". S2-14 cannot honestly carry a defect
id, for three reasons:

- §G.1's `defect_class` is closed to `product` and `infrastructure`;
- `product` would misstate the owner's finding;
- `infrastructure` is limited to "M13's own tests, fixtures, graders, scaffolds or static validator". The skipped
  tests are pre-M13 modules and are correct to skip. An `open` infrastructure record would also make
  `blocks_m13_completion: yes` by rule.

§G.2's permission to complete with open defects covers **product** defects only. ADR-0039 therefore does not permit
M13.1 `COMPLETED` with S2-14 as an open, defect-free gap. Owner decision (c) settles how the row is recorded. It does
not change the ADR's completion text.

As the prompt required, I **stopped at this point and did not edit ADR-0039**. No new ADR was drafted and no status was
invented. M13.1 stays `REVIEW`. Resolving this is an owner decision. For example, an accepted decision that amends
ADR-0039 §B and §L to admit an owner-accepted environment gap would resolve it, recorded as a new ADR because
ADR-0039 is immutable. This record makes no recommendation between routes.

**Defect dispositions.**

- M13-DEF-01 and M13-DEF-03: remediation **unassigned**, deferred to the owner (§G.2).
  - `project_plan.md`'s only planned milestone after M13 is M14, Documentation & Release: worked examples, a
    troubleshooting guide, per-component reference pages, a token-cost measurement and release tagging. Its scope
    includes neither fix.
  - DEF-03 relates to M3's unscheduled chunked-streaming deferral.
  - No milestone was invented.
- M13-DEF-02: resolved, `fixed_infrastructure`, not reopened.

No ADR was created.

## 12. Architecture changes

None. `architecture.md` was not edited in this pass. §20 item 10 already describes M13-DEF-03 accurately.

## 13. Project-plan updates

| Item | Change |
|---|---|
| M13.1 | Stays `REVIEW`. Not `COMPLETED`, because of the §L point in §11 |
| U-1 | `BLOCKED` (owner decision) → `COMPLETED`: decision (c) recorded |
| ADR-0039 §L completion check | New row, `BLOCKED`, awaiting the owner's decision |
| Regression re-time | New row, `COMPLETED` |
| Known issues | M13-DEF-01 and M13-DEF-03 now read "remediation unassigned"; M13-DEF-02 reads "resolved" |
| Unchanged | M13 `IN PROGRESS`; M13.2 `PLANNED`, not authorised; M9 `IN PROGRESS`; M12-C `BLOCKED`; R-01 `BLOCKED` |

## 14. Documentation updates

As §5. Not updated, deliberately:

- ADR-0039 and every other accepted ADR;
- `CLAUDE.md`;
- `architecture.md`;
- `README.md`;
- `CONNECTORS.md`;
- `docs/README.md`;
- `docs/decisions/README.md`;
- every earlier development record, including the M13.1 record this one partly supersedes.

## 15. Remaining work

1. **Owner:** resolve the ADR-0039 §L conformance point for S2-14 (§11). M13.1 cannot be marked `COMPLETED` under
   the ADR as written until then.
2. **Owner:** assign remediation milestones to M13-DEF-01 and M13-DEF-03, whenever the owner chooses. Both are
   unassigned.
3. **Owner:** O-3 and O-4 from the M13.1 record are unchanged.
4. **Owner:** optionally, watch the suite's wall clock on later runs. No action is required, and no threshold exists.
5. **M13.2:** only under its own authorising prompt, and only after M13.1 is `COMPLETED`.
6. **Unchanged:**
   - M9's four fresh-session live smoke tests;
   - M12-C `BLOCKED`;
   - D-13 and D-14;
   - R-01, R-05, R-10, R-11 and R-12.

## 16. Git commit reference

N/A. Nothing was committed, amended, pushed, stashed or reset. Branch `main`, base `990e88d`.

## 17. Final validation

| Check | Result |
|---|---|
| Focused M13.1 modules | 65 tests, 0 failures, 0 errors, 2 opt-in skips (§9) |
| Full suite (the single re-time) | 4,749 tests, 0 failures, 0 errors, 28 skipped, 414.476 s (§9) |
| `claude plugin validate . --strict` | `✔ Validation passed`, exit 0 |
| `git diff --check` | Clean, exit 0 (CRLF-conversion warnings only). Untracked files: no trailing whitespace |
| Secret scan | See below |
| ADR-0001 to ADR-0038 | 38 of 38 blob hashes equal `HEAD:` |
| ADR-0039 | Untracked since acceptance, so it has no `HEAD:` blob. Its SHA-256 equals the hash taken at the start of this session (`53fec3b3…`) |
| `CLAUDE.md`, `.mcp.json` | Unchanged against `HEAD` |
| Protected paths | `git status --porcelain` is empty for `lib/`, `skills/`, `commands/`, `agents/`, `reference/`, `config/`, `assets/`, `.claude-plugin/`, `.mcp.json`, `tests/run_tests.py`, `.gitignore`, `CLAUDE.md` and `README.md`. `CONNECTORS.md` and `docs/decisions/README.md` show as modified, but their hashes equal the session-start snapshot, so the earlier contract-finalization session changed them, not this pass |
| Files changed by this pass | The session-start snapshot shows exactly six changed files: `docs/testing/coverage-matrix.md`, `defects.md`, `measurements.md`, `README.md`, `project_plan.md` and `tests/unit/test_m13_coverage_matrix.py`. This record is the one new file. No other file changed |
| Pre-M13 test modules | None modified |

**Secret scan:** the full content of the seven files this pass touched, 3,201 lines, was scanned for:

- AWS, GitHub, Slack, `sk-` and HubSpot-shaped tokens;
- JWTs, bearer strings and private keys;
- key, secret, password and token assignments;
- credentialed and database URLs;
- 40-plus-hex strings, email addresses and URLs.

There were two hits, and neither is a secret:

- the public commit id `990e88d5…` in this record;
- a pre-existing, committed `project_plan.md` line (M9-C.13). It is unchanged by this pass, and it holds a published
  SHA-256 of an agent file.

No URL, email address or credential was added.

**Confirmations:**

- **No production change.** No file under `lib/`, `skills/`, `commands/`, `agents/`, `reference/`, `config/` or
  `assets/` was changed, and neither were `.claude-plugin/`, `.mcp.json`, `tests/run_tests.py` or `.gitignore`.
- **Defects not fixed.** M13-DEF-01 and M13-DEF-03 were left unfixed. Neither their tests nor their expectations
  changed.
- **Nothing external.** No connector, MCP tool, authentication, web access or external service was used by this pass.
  The session's plugin had started the `biq-verifier` server process, which sat idle and was never called. The only
  network operation was `git fetch origin`.
- **No M13.2 work.** No eval was authored or executed, no `claude plugin eval` was run, and every behavioural row is
  still `not_executed`.
- **Status unchanged.** M9 stays `IN PROGRESS`, and M12-C stays `BLOCKED`.
- **Nothing committed.** Nothing was committed, amended, pushed, stashed or reset.
