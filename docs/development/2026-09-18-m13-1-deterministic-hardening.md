# 2026-09-18 — M13.1: deterministic hardening

**Milestone:** 13 — Test Hardening & Evals, part M13.1 (deterministic hardening) under ADR-0039 (Accepted)
**Status on completion:** REVIEW. Implemented and validated, with one owner decision open (**U-1**). M13.2 not
started and not authorised. Nothing committed.
**Supersedes:** None.

## 1. Prompt / task performed

An owner-authorised M13.1 implementation prompt. It covered:

- reconciling repository state;
- running the baseline;
- implementing M13.1 only:
  - the coverage matrix over S1–S7;
  - deterministic hardening;
  - D1, D2 and D3 without invented thresholds;
- recording defects rather than fixing product code;
- validating, auditing scope, and documenting.

The prompt excluded:

- M13.2 and any eval execution or runner;
- production changes;
- connectors, MCP, authentication, web and external services;
- D-13 and D-14;
- marking M9 complete;
- commit, push, stash or reset.

## 2. Objective

Make coverage checkable against ADR-0039's closed sets, close the deterministic gaps that need no product change,
execute and record the three measurements, and record every defect found, all within the scope of ADR-0039 §A.2.

## 3. Changes made

1. **Repository reconciliation.**
   - `git status --short --branch`: 5 modified documents and 3 untracked documents. That is exactly the state M13
     contract finalization left: the same files, with modification times from that session.
   - `HEAD` = `origin/main` = `990e88d5f13db65b2ecdf0737c7f613b83c6034d` after `git fetch origin`.
   - No unexpected change. Nothing was discarded, stashed or reset.
2. **Baseline** (§9): 4,684 tests, 0 failures, 0 errors, 26 skipped. The 26 skips are listed in §10.
3. **Coverage mapping.**
   - Every test in the suite was indexed by parsing, not importing: 4,684 ids, equal to the suite count.
   - Each S1–S7 row was mapped to existing tests after reading the relevant engine code and test classes.
   - Rows were never mapped by name alone where the behaviour was in doubt. Examples:
     - §16 "offer trend description" was traced to `skills/biq-forecasting/SKILL.md:99`;
     - the write-approval row was traced to ADR-0037 §G/§K;
     - the gate's re-identification path was traced in `research/gate.py`.
4. **Gap closure.** Three deterministic gaps were closed with new tests. None needed a product change:
   - **S1-05**: the §16 sentence;
   - **S5-12**: no component writes the repository;
   - **S6-02**: the gate-level single-query re-identification block.
5. **Measurements.** D2 and D3 were written and run.
   - D2 exposed **M13-DEF-01**, a product defect.
   - D1 was written and run with `BIQ_LARGE_DATASET=1`. Its first run failed on 250k. Diagnosis found **my test** read
     the ledger's caveats from the wrong key: **M13-DEF-02**, an infrastructure defect, fixed. The corrected module
     was re-run, and that run is the record.
   - The corrected run then showed **M13-DEF-03**, a product defect, recorded and not fixed.
6. **Determinism audit** (§8).
7. **Matrix validator.** It was written, then mutation-checked against five deliberate corruptions in scratchpad
   copies of the matrix. Each was caught.
8. **Documentation** (§14).
9. **Validation and scope audit** (§17).

## 4. Files created

**Tests** (new modules only, as ADR-0039 §C.1 requires):

| File | Tests | Role |
|---|---|---|
| `tests/fixtures/build_m13_large_fixtures.py` | — | Deterministic synthetic large-CSV generator; integer-pence money; `Synthetic …` labels |
| `tests/integration/test_m13_large_dataset.py` | 6 (2 opt-in) | D1 measurement (opt-in `BIQ_LARGE_DATASET=1`) plus 4 always-on generator-determinism tests |
| `tests/unit/test_m13_discriminability.py` | 13 | D2 measurement, non-empty descriptions, instrument self-tests |
| `tests/integration/test_m13_selection_stability.py` | 5 | D3 measurement, determinism |
| `tests/negative/test_m13_error_handling.py` | 5 | S1-05 gap closure |
| `tests/negative/test_m13_approval_boundaries.py` | 4 | S5-12 gap closure |
| `tests/negative/test_m13_tier_rows.py` | 6 | S6-02 gap closure |
| `tests/unit/test_m13_coverage_matrix.py` | 26 | Matrix and defect-register validator |

That is **65 new tests**, 2 of which are opt-in skips by default.

**Documentation:**

- `docs/testing/coverage-matrix.md`
- `docs/testing/defects.md`
- `docs/testing/measurements.md`
- `docs/development/2026-09-18-m13-1-deterministic-hardening.md` (this record)

## 5. Files modified

- `docs/testing/README.md` — index of the three M13 documents, the evidence classes, and the opt-in suites.
- `project_plan.md`:
  - header;
  - summary row 13 → `IN PROGRESS`;
  - notes on the three M9 tier rows, whose statuses stay `PLANNED`;
  - M13-A contract row and sub-milestone table;
  - a new M13.1 section;
  - Known issues: M13-DEF-01/02/03 rows, plus the R-05 and R-10 measurement notes.
- `architecture.md`:
  - §15, a pointer to the M13 artifacts;
  - §20, item 7 (D2 measured) and item 9 (D3), and a new item 10 (M13-DEF-03).

No existing test module was edited or retargeted.

## 6. Files deleted

None in the repository. The following scratchpad files were created and remain outside the repository:

- the clock-shift probe script and its output;
- the D1 run outputs;
- the matrix mutation copy, which was deleted after use;
- the table extracts.

The D1 fixtures were generated in temporary directories and deleted by the tests.

## 7. Features implemented

None user-facing. M13.1 adds test, fixture, measurement and validation infrastructure only.

## 8. Tests performed

- `python tests/run_tests.py -v` — baseline, before any change.
- Focused runs of every new module:
  - `unit.test_m13_discriminability`
  - `integration.test_m13_selection_stability`
  - `negative.test_m13_error_handling`
  - `negative.test_m13_approval_boundaries`
  - `negative.test_m13_tier_rows`
  - `unit.test_m13_coverage_matrix`
  - `integration.test_m13_large_dataset` (default, opt-in skipped)
- `BIQ_LARGE_DATASET=1 python tests/run_tests.py -v integration.test_m13_large_dataset`: run 1 (M13-DEF-02), then
  run 2, which is the record.
- **Clock-shift determinism probe** (scratchpad `clockshift_probe.py`; not committed, and no repository file
  touched). It ran the whole suite with the research layer's implicit `today()` (`research/sources.py`,
  `research/scout.py`) shifted to 2029-01-01, keeping `isinstance` semantics.
- **Static determinism audit** of `tests/` and `assets/demo-data/generate_demo_data.py`:
  - random use: the only generator is `random.Random(SEED)`;
  - wall-clock use: one read, `test_engine_m2.py:193`, which builds a date three years in the future, so its outcome
    is clock-independent;
  - network use: none; the only matches are negative assertions.
- **Matrix validator mutation check** (scratchpad): five corruptions of a copy of the matrix — a bad test id, a bad
  status, an `automated_pass` claim, an unexplained gap and a dropped row. Each was caught.
- The closing full suite, verbose; strict validation; `git diff --check`; secret scan; scope audit; the K.5 re-check
  (§17).

**Not executed:**

- any `claude plugin eval` invocation (M13.2 not authorised; `not_executed`);
- the opt-in `BIQ_AGENT_BOUNDARY_RUNTIME` and `BUSINESSIQ_LIVE_SMOKE` suites (outside M13.1).

## 9. Test results

**Baseline** (tree = `990e88d` plus the uncommitted M13 contract-finalization documents):

```
Ran 4684 tests in 850.279s
OK (skipped=26)
ran 4684 | failures 0 | errors 0 | skipped 26
```

**Clock-shift probe** (tree with the first five new modules):

```
CLOCKSHIFT 2029-01-01 ran 4717 | failures 0 | errors 0 | skipped 28
```

No test depends on the research layer's implicit current date.

**D1**, run 1 — M13-DEF-02, a test defect, since fixed:

```
FAIL: test_250k_csv_rows ... AssertionError: False is not true : an incomplete pass carries no caveat naming its processing mode
ran 6 | failures 1 | errors 0 | skipped 0
```

**D1**, run 2 — the recorded M13-MEAS-D1:

```
ran 6 | failures 0 | errors 0 | skipped 0
```

The per-size figures are in `docs/testing/measurements.md`.

**Closing run:** §17.

## 10. Issues discovered

**Product defects, recorded and not fixed** (`docs/testing/defects.md`):

- **M13-DEF-01**: `biq-competitor-analysis` (1,065) and `biq-industry-research` (1,158) skill descriptions exceed the
  1,024-character hard limit of `architecture.md` §2 / ADR-0013. The D.2 length assertion was therefore not
  committed (ADR-0039 §G), and every length is recorded instead.
- **M13-DEF-03**: at 250,000 CSV rows, every row is read and revenue is exact. Yet the pass is labelled `streamed` /
  incomplete: "Only 250000 of 250000 rows were examined", revenue KPI `partial`, quality grade `WARNING`. This
  contradicts §17 and M3's "mode is recorded correctly". It is conservative, never overstating completeness.

**Test-infrastructure defect, fixed in M13:**

- **M13-DEF-02**: the D.1 module read `ledger.as_dict().get("global_caveats")`, which is always empty.
  - Before: `caveats = result.ledger.as_dict().get("global_caveats", [])`.
  - After: `caveats = result.ledger.summary()["global_caveats"]`.

**Open owner decision:**

- **U-1 — S2-14 cross-tier equivalence cannot be `covered`.**
  - All 8 Tier-1 equivalence tests are skipped: 7 in `test_data_layer.TestCrossTierEquivalence` and 1
    `test_vertical_slice.TestCrossTierEquivalence.test_tier1_and_tier3_agree`.
  - Tier 1 is openpyxl in the *system* interpreter. `CLAUDE.md` §4 forbids installing it there, and the consented
    Tier-2 managed install would not un-skip them.
  - ADR-0039 §B forbids `covered` on a skipped test. `gap` needs a §G.1 defect id, and §G.1's classes (`product`,
    `infrastructure`) fit neither case. A misclassified defect would also either mislabel the product or block M13
    by rule.
  - So the row is `gap` / `execution_unavailable`, citing U-1. The validator admits exactly this one exception, by
    name (`OWNER_DECISIONS`).
  - Options:
    - (a) the owner runs the closing check under an interpreter that already provides openpyxl;
    - (b) clarify ADR-0039 with a status for environment-skipped deterministic rows;
    - (c) accept an open gap.
  - **This is raised, not resolved.** ADR-0039 was not edited.

**Baseline skips (26), unchanged:**

| Skips | Where | Reason |
|---|---|---|
| 7 | `test_data_layer.TestCrossTierEquivalence` | openpyxl absent |
| 1 | `test_vertical_slice.TestCrossTierEquivalence` | openpyxl absent |
| 3 | `test_vertical_slice.TestScenarioFTier1Xlsx` | openpyxl absent |
| 6 | `test_tier2_runtime.TestTier2OutOfProcess` | no managed runtime |
| 2 | `test_m9b_live_smoke` | opt-in `BUSINESSIQ_LIVE_SMOKE` |
| 7 | `test_m11_verifier_agent_boundary.RuntimeBoundary` | opt-in `BIQ_AGENT_BOUNDARY_RUNTIME` |

**Observations, not defects:**

- **O-1** — R-05: industry research / market analysis is the highest-overlap pair in both tiers (0.556 commands,
  0.633 skills).
- **O-2** — R-10: four methods win across 13 truncations, but the literal leave-one-out pair is stable.
- **O-3** — `architecture.md` §16's write row ("request approval naming system, record, change") and §8's "System
  writes: Explicit" predate ADR-0037 §G/§K, under which v1 has no write path and refuses outright. The matrix records
  the refined requirement. Aligning §16/§8 is architecture wording (M14 / D-14 territory), not M13.1's.
- **O-4** — `kpi.engine.calculate` silently skips an unknown KPI id (`if definition is None: continue`), although its
  docstring says "never a silent omission". No accepted architecture specifies unknown-id handling, so under §G.1 this
  is **not** recordable as a defect. It is left for the owner.

## 11. Decisions made

None of substance. No ADR was created, and ADR-0039 was not edited: U-1 is raised as an owner decision instead.
Implementation choices within the contract:

- **D3 windows** remove trailing periods one at a time down to the configured minimum. The literal leave-one-out pair
  (24 vs 23 periods) is reported separately.
- **D2 command tier** excludes `retrieval-slice` (`disable-model-invocation: true`) and lists it.
- **D2 method.** M8 recorded no tokenisation, so it is fixed in the module and labelled not directly comparable.
- **D1 revenue check.** D1 additionally asserts that the engine's revenue equals an independently computed exact
  total. This is a correctness property, not a threshold.
- **S1-17** is `gap` (M13-DEF-03), not `covered`. Its cited tests pass, but the scope warning is inaccurate above
  100,000 rows.

## 12. Architecture changes

None to the design. `architecture.md` §15 gained a pointer to the M13 artifacts. §20 gained two things: the
measured facts (items 7 and 9) and item 10, which states that large CSVs are materialised, not streamed, and that the
recorded mode is wrong above 100k (M13-DEF-03).

## 13. Project-plan updates

- **M13:** `PLANNED` → `IN PROGRESS`.
- **M13.1:** `PLANNED` → `REVIEW`.
- **M13.2:** `PLANNED`, not authorised.
- **M9:** stays `IN PROGRESS`. Its three tier rows stay `PLANNED`, now with S6 evidence notes.
- **M12-C:** `BLOCKED`, unchanged.
- **R-01:** unchanged, `BLOCKED`. No eval executed.
- **R-05 and R-10:** measurement notes added; both still open.
- **Known issues:** M13-DEF-01, 02 and 03 added.

## 14. Documentation updates

As §4 and §5. Not updated, deliberately:

- `README.md` (D-14);
- `docs/README.md`: history list (D-14); the prompt excludes D-14 cleanup;
- `CONNECTORS.md`: no connector change;
- ADR-0039 and every accepted ADR;
- `CLAUDE.md`;
- every historical development record.

## 15. Remaining work

1. **Owner:** review M13.1. Decide **U-1**.
2. **Owner:** choose the remediation milestones for M13-DEF-01 and M13-DEF-03. These are product fixes, outside M13.
3. **Owner:** consider O-3 and O-4.
4. **M13.2** under its own authorising prompt. It states whether execution is authorised, and the `--max-cost-usd`.
5. Unchanged:
   - M9's four live smoke tests;
   - M12-C `BLOCKED`;
   - D-13 and D-14;
   - R-01, R-05, R-10, R-11 and R-12.

## 16. Git commit reference

N/A — nothing committed, amended, pushed, stashed or reset. Branch `main`, base `990e88d`.

## 17. Final validation (closing run)

**Full suite, verbose (`python tests/run_tests.py -v`), on the finished tree:**

```
Ran 4749 tests in 7694.008s
OK (skipped=28)
ran 4749 | failures 0 | errors 0 | skipped 28
```

- **Tests:** 4,749 = 4,684 baseline + 65 added by M13.1.
- **Skips:** 28 = the 26 baseline skips (§10, unchanged) + 2 D1 opt-in skips
  (`LargeDatasetMeasurement`, `BIQ_LARGE_DATASET` unset).
- **Failures and errors:** 0 and 0. No existing test was edited, and none regressed.
- **Wall time: 7,694 s against the baseline's 850 s, cause not established.** The seven new modules take about 2.1 s
  together when timed in isolation (coverage matrix 0.4 s, discriminability 0.1 s, selection stability 0.7 s, large
  dataset default 0.2 s, error handling 0.2 s, approval boundaries 0.4 s, tier rows 0.1 s), so they do not account
  for it. Host load or sleep during the run is possible but was not verified. The owner may want to re-time a run.

**K.5 matrix re-check against this run** (scratchpad `k5_recheck.py`, which parses the verbose log):

- 4,749 outcomes parsed;
- all **205** test citations in `covered` / `covered-by-M13` rows are `ok`; none is skipped or missing;
- the only skipped citations belong to the `gap` row S2-14 (U-1), as expected.

**Other checks:**

| Check | Result |
|---|---|
| `claude plugin validate . --strict` (Claude Code 2.1.276) | `✔ Validation passed`, exit 0 |
| `git diff --check` | Clean, exit 0 (CRLF-conversion warnings only). Untracked files: 0 lines with trailing whitespace |
| Secret scan | Every added tracked line and every untracked file, 3,780 lines, checked for AWS, GitHub, Slack, `sk-` and HubSpot tokens, JWTs, bearer strings, private keys, key/secret/password/token assignments, credentialed URLs, connection strings, 40+-hex strings, email addresses and URLs. **Only hit:** the public commit id `990e88d5…` in the development records. No URL and no email address |
| Scope audit (ADR-0039 K.6) | `git status --porcelain` is empty for `lib/`, `skills/`, `commands/`, `agents/`, `reference/`, `config/`, `assets/`, `.claude-plugin/`, `.mcp.json`, `tests/run_tests.py`, `.gitignore`, `CLAUDE.md` and `README.md`. ADR-0001–0038: 38 of 38 blob hashes equal `HEAD:`. ADR-0039 is unmodified since acceptance (mtime 18:47, before this session). No existing test module is modified; every M13.1 test file is new |
| Prior-session files | `CONNECTORS.md`, `docs/README.md`, `docs/decisions/README.md` and both earlier 2026-09-18 records carry modification times from before this session. M13.1 did not write them |

**Confirmations:**

- No production code or behaviour was changed.
- No connector, MCP tool, authentication, web access or external service was used.
- The only network operation was `git fetch origin`.
- **M13.2 behavioural evals were not authored or executed.** No `claude plugin eval` invocation was made, and every
  behavioural row is `not_executed`.
- M12-C stays `BLOCKED`. M9 stays `IN PROGRESS`. No connector was admitted, and HubSpot was not admitted.
- Nothing was committed, amended, pushed, stashed or reset.
