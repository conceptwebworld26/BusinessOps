# 2026-09-19 — M13.2: manual observation execution pack (preparation only)

**Milestone:** 13 — Test Hardening & Evals, part M13.2, under ADR-0039 as amended by ADR-0040 and ADR-0041.
Preparation only.
**Status on completion:** IN PROGRESS. **Zero manual observations performed.** M13.2 is not `COMPLETED`. Nothing
committed, nothing pushed.
**Supersedes:** None. Every earlier record is unchanged.

## 1. Prompt / task performed

The owner's "M13.2 Manual Observation Execution Pack Preparation" prompt. It asked for an exact owner-execution pack
for the twelve S3 `manual_observation` scenarios, containing:

- the twelve rows;
- a per-scenario checklist (A to M);
- a canonical record template;
- evidence-capture rules;
- twelve packets, each with the exact case prompt;
- deterministic checks.

It prohibited:

- performing any observation or launching a scenario session;
- any eval, including `--help`;
- web, MCP, connector or authentication use;
- fabricated transcripts or results, and creating any `docs/testing/manual/*.md` record;
- production changes, committing and pushing.

## 2. Objective

Let the owner perform each scenario without inference, and record valid evidence that can never be mistaken for an
automated result.

## 3. Changes made

1. **State verified.**
   - `HEAD` = `origin/main` = `21ee21b21213ad80273650f056ef2f318023742c`.
   - The working tree held the uncommitted M13.2 work and the §E.1/G-2 record, as expected.
2. **Sources read:**
   - ADR-0039 §E.1, §E.6, §I and §J;
   - ADR-0040, and ADR-0041 §12;
   - `eval-suite.md`, `coverage-matrix.md` and `docs/testing/README.md`;
   - both earlier M13.2 records;
   - the project-plan M13 entries;
   - the twelve designated case files.
3. **The twelve rows** were taken from the designation table in `eval-suite.md`, S3-01 to S3-12, with no
   reconstruction:
   - b01, b02, b03, b04 and b05;
   - c01;
   - d01, d05, d06 and d07;
   - a15;
   - r20.
4. **Finding WD-1 (engine path), recorded for the owner and not acted on.**
   - **The documented import is working-directory-relative.** Every engine invocation in the shipped commands and
     skills is `sys.path.insert(0, 'lib/python')`. Only `.mcp.json` uses `${CLAUDE_PLUGIN_ROOT}`.
   - **The G-2 working directory is outside the repository.**
   - **Earlier live runs** were launched from the repository root (`2026-09-10-m9b-vertical-slice.md`).
   - **A plain Python check** in a scratchpad directory, with no session and no model, gave these results:
     - outside the repository, the documented snippet raised `ModuleNotFoundError: No module named 'biq'`;
     - at the repository root, it imported;
     - `biq` is not installed globally.
   - **What the pack does with it:**
     - states the fact without predicting model behaviour;
     - tells the owner not to intervene, and to record what happens;
     - leaves the decision to proceed under the G-2 working directory to the owner.

   It is **not** recorded as a defect. No test, eval or measurement observed product behaviour, and whether an
   installed plugin used from a user's directory is affected is a runtime question. It is **not** a G-2 void
   condition. G-2 was not changed.
5. **Pack written:** `docs/testing/manual-observation-pack.md`.
   - **Opening statements:**
     - the preparation-only status: "ZERO manual observations have been performed";
     - the G-3 sentence: "Platform verification remains open and is required before any automated/plugin evaluation
       execution";
     - WD-1.
   - **Evidence classes:** a table keeping `manual_observation` apart from `automated_pass`, `automated_fail`,
     `not_executed` and `execution_unavailable`.
   - **Checklist:** items A to M.
   - **Evidence rules:**
     - only two properties have contractual exact wording: "no reliable source found" for S3-05 and S3-07, and
       `CRITICAL` for S3-02;
     - S3-03's periods are content, not a phrase;
     - every other property is semantic;
     - the output figures each case permits are listed per row;
     - evidence the owner cannot capture is not required.
   - **Record template:** the §E.1 items, the G-2 provenance and G-2's owner confirmation, and nothing else. A
     separate observation-ID field, a time, a session identifier and a notes field were considered and left out: the
     path is the identity, and none of the others is required by the contract.
   - **Twelve packets**, generated from the case files by a scratchpad script:
     - each prompt, purpose, expected property and input comes from the case;
     - the observation guidance is phrased "Observe whether …", with no predictions.
6. **Validator added:** `tests/unit/test_m13_manual_observation_pack.py`, 15 tests.
   - **What it checks:**
     - exactly twelve packets in row order, each on its designated case, with every field present;
     - prompts byte-identical to the cases; purpose and expected property quoted from the cases;
     - inputs equal to the case inputs, existing, with the manifest hashes;
     - canonical record paths;
     - no `docs/testing/manual/` directory;
     - no predicted or claimed result;
     - the template carries only placeholders;
     - the evidence-class separation;
     - G-3 stated OPEN;
     - no prohibited flag or tool token, and reserved URLs only.
   - **Its first run** failed one check. The case's own `expected_property` text ("what failed", meaning the data
     check) matched an over-broad result pattern. The pattern was narrowed to claims about a case, scenario or
     observation, and the pack was not changed.
   - **Mutation check:** 10 deliberate corruptions on a scratch copy of the repository, each caught.
7. **Cross-references updated:**
   - `eval-suite.md`: a pointer to the pack and WD-1;
   - `docs/testing/README.md`: an index row;
   - `coverage-matrix.md`: the state paragraph only. Evidence cells and totals are unchanged;
   - `project_plan.md`: the next gate and the manual-scenarios row.

## 4. Files created

| File | Purpose |
|---|---|
| `docs/testing/manual-observation-pack.md` | The owner execution pack |
| `tests/unit/test_m13_manual_observation_pack.py` | The pack validator, 15 tests |
| `docs/development/2026-09-19-m13-2-manual-observation-pack.md` | This record |

## 5. Files modified

- `docs/testing/eval-suite.md`
- `docs/testing/README.md`
- `docs/testing/coverage-matrix.md`
- `project_plan.md`

All were already modified, uncommitted, earlier in M13.2. No case, fixture, existing test or production file changed.

## 6. Files deleted

None.

## 7. Features implemented

None.

## 8. Tests performed

- `python tests/run_tests.py -v unit.test_m13_manual_observation_pack`
- The pack-validator mutation check, on a scratchpad copy.
- `unit.test_m13_eval_cases`, `integration.test_m13_eval_input_preconditions` and `unit.test_m13_coverage_matrix`.
- `python tests/run_tests.py`, the full regression, because a test module was added.
- `git diff --check`, a whitespace scan, a secret scan and the scope audit.

**Not run:** any evaluation, any manual scenario, and any session.

## 9. Test results

Recorded in the task report of this session. They are not pre-stated here.

## 10. Issues discovered

**WD-1** (§3 item 4). It is an owner decision before any scenario is performed. No defect is recorded.

## 11. Decisions made

No ADR. The template's field set is limited to contract-required fields (§3 item 5).

## 12. Architecture changes

None.

## 13. Project-plan updates

No status transition. The manual-scenarios row stays `PLANNED`, with the pack and WD-1 noted, and the next gate names
WD-1.

## 14. Documentation updates

As §4 and §5.

## 15. Remaining work

1. The owner's WD-1 decision.
2. The twelve owner-performed scenarios and their records. When the first is added,
   `test_no_manual_observation_exists_yet` must be replaced by record assertions in the same change.
3. M13.2 closure: see `2026-09-19-m13-2-e1-outcome-g2.md` §3.8.
4. G-3, only on authorised execution.

## 16. Git commit reference

N/A. No commit and no push.
