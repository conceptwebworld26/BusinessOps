# 2026-09-19 — M13.2 G-1 contract remediation: ADR-0041, deterministic repository-owned eval input fixtures

**Milestone:** 13 — Test Hardening & Evals, part M13.2 (behavioural evals) under ADR-0039, as amended by ADR-0040.
Contract remediation only.
**Status on completion:** REVIEW. ADR-0041 is `Proposed` and awaits the owner's acceptance. M13.2 stays `PLANNED` and
has not started. Nothing committed, nothing pushed.
**Supersedes:** None. Every earlier record is unchanged.

## 1. Prompt / task performed

The owner's "M13.2 G-1 contract remediation / ADR-0041" prompt. It followed the M13.2 contract review, which raised
three items:

- **G-1:** the `behaviour` eval cases have no repository-valid input fixtures under ADR-0039's input rules;
- **G-2:** ownership and session of manual observations are unspecified, which matters only under §E.1 outcome (b)
  or (c);
- **G-3:** the platform's tool-grant and help surface must be re-read immediately before any eval execution.

The prompt asked for G-1 only: a narrow amendment to ADR-0039, in a new ADR, defining how eval input fixtures may be
created and stored.

It prohibited:

- resolving G-2 or G-3;
- authorising or executing any eval, including `claude plugin eval`;
- creating fixtures, eval case directories, `case.yaml` files, graders, a runner or the static eval test;
- editing ADR-0039;
- changing M13.2's `PLANNED` status, M13's status, the M13.1 records, the matrix totals, the defect register or eval
  results;
- web, MCP, connector or authentication use;
- running the full test suite unless a changed executable test required it;
- committing or pushing.

## 2. Objective

Make M13.2 implementable by giving its eval cases a lawful source of inputs, without weakening the file-first
architecture, admitting arbitrary or runtime-generated data, or touching the execution policy.

## 3. Changes made

1. **Starting state verified.**
   - `HEAD` = `origin/main` = `75ced037b238b5a49f2b8a8246c9d2c4635c8a78` ("M13: mark milestone in progress").
   - The working tree was clean.
2. **Authoritative material read:**
   - `CLAUDE.md` and `project_plan.md`;
   - ADR-0039 and ADR-0040;
   - `docs/testing/` (README, coverage matrix, defects, measurements);
   - the four M13 records of 2026-09-18;
   - the eight builders in `tests/fixtures/`;
   - `assets/demo-data/` and its generator;
   - `architecture.md` §15 and §19;
   - `docs/decisions/README.md` and the ADR and development-record templates.
3. **Next ADR number, from the repository.** The highest ADR is 0040. No `ADR-0041*` file exists in the tree or in
   any branch's history, and no file refers to "0041". The new ADR is therefore **0041**.
4. **G-1 verified from repository evidence** (§10). All five findings the prompt listed held. One was refined: the
   gap covers three of the five `behaviour` cases, not all five.
5. **ADR-0041 written**, status `Proposed` (§11).
6. **Validation** (§8, §9).

## 4. Files created

| File | Purpose |
|---|---|
| `docs/decisions/ADR-0041-m13-2-deterministic-repository-owned-eval-fixtures.md` | The G-1 amendment to ADR-0039, `Proposed` |
| `docs/development/2026-09-19-m13-2-g1-contract-remediation-adr-0041.md` | This record |

## 5. Files modified

None.

The ADR indexes (`docs/decisions/README.md`, `architecture.md` §19) were deliberately **not** updated. The
repository requires every **accepted** ADR to be listed (`docs/decisions/README.md`, *Conventions*), and ADR-0041 is
`Proposed`. The precedent is ADR-0039, whose `Proposed` text was not recorded anywhere before acceptance. Indexing
follows acceptance (ADR-0041 *Follow-up* 2).

## 6. Files deleted

None.

## 7. Features implemented

None. This is a contract amendment. No fixture, builder, manifest, eval case, grader, runner or test was created.

## 8. Tests performed

- `git diff --check`.
- A trailing-whitespace and tab scan of both new files. `git diff --check` does not see untracked files.
- `claude plugin validate . --strict`.
- Focused documentation tests, chosen because they read `docs/`:
  - `unit.test_m12b_connector_registry.…test_no_gate_record_block_exists_in_the_repository` scans every file in
    `docs/development/`, so it reads this record;
  - `unit.test_m13_coverage_matrix` validates the matrix and register this task was required not to change.

The full suite was not run, because no executable test changed. No eval, `claude plugin eval` or `plugin eval --help`
was run.

## 9. Test results

See §17 for the verbatim output.

- `git diff --check`: clean (exit 0). No tracked file changed.
- Whitespace scan of the new files: no trailing whitespace, and no tabs.
- `claude plugin validate . --strict`: "✔ Validation passed", exit 0, on Claude Code **2.1.278**.
- Focused tests: see §17.

**Observation for G-3, recorded and not acted on.** The installed CLI is 2.1.278. ADR-0039's platform facts were
measured on 2.1.276. This supports G-3's premise that the platform's current surface must be re-read before any
execution. It resolves nothing, and no help text was inspected.

## 10. Issues discovered

**G-1 is confirmed, with one refinement.**

| Finding | Evidence |
|---|---|
| 1. ADR-0039 restricts eval inputs | §E.2: "`assets/demo-data/` and fixtures M13.1 generated". §E.5: paths "under `assets/demo-data/` or `tests/fixtures/`" |
| 2. The cases need inputs that no acceptable committed file provides | Holds for **S3-01** (ambiguous column), **S3-02** (`CRITICAL` halt) and **S3-03** (four periods). The demo CSV runs `anomaly-detection` with status `ok` (`integration.test_anomaly_m8.…test_the_demo_dataset_scans`), so it maps unambiguously and is not `CRITICAL`. It has 24 monthly periods, above the default 12-period minimum (`lib/python/biq/forecast/engine.py`). M13 may not change `assets/` (§A.3). **Refinement:** S3-04 is satisfied by the demo file, which that same test shows yields flagged anomalies. S3-05 reads no business file |
| 3. The builders are not valid inputs | `git ls-files tests/fixtures` lists `__init__.py` and eight `build_*.py` modules, and no data file. Every builder writes into a caller-supplied directory, and their docstrings say "Built at test time" or "never committed". The M13.1 record says "The D1 fixtures were generated in temporary directories and deleted by the tests" |
| 4. Runtime generation is not a lawful workaround | §F.6: a scaffold does "nothing but copy repository synthetic inputs". §F.5: Bash only for the engine's `python` invocations. §E.5: the input path must exist in the repository |
| 5. The gap is the contract's, not the product's | The engine behaviour is deterministically tested with builder output: `build_fixtures.ambiguous_mapping` (S1-14), `build_fixtures.critical_*` (S3-02 support) and `build_forecast_fixtures.short` (S1-09) |

**A further fact the contract had to address.** The repository has no `.gitattributes`, and `core.autocrlf` is
`true` here. `git ls-files --eol` shows `assets/demo-data/northwind_sales.csv` as `i/lf w/crlf`. A committed CSV's
working-tree bytes therefore vary by checkout. ADR-0041 §3 pins line endings for the fixture directory only, with a
nested `.gitattributes`. The demo file is not affected and not changed.

No product or infrastructure defect was found. The defect register is unchanged.

## 11. Decisions made

[ADR-0041](../decisions/ADR-0041-m13-2-deterministic-repository-owned-eval-fixtures.md) — **Proposed**, 2026-09-19.

**What it adds (§§1–9, 13):**

- **§1 Location.** Committed eval inputs live under `tests/fixtures/eval_inputs/`, a subdirectory of the location
  ADR-0039 already approves. A fixture is admissible only where `assets/demo-data/` cannot establish the precondition.
- **§2 Synthetic boundary.** CSV only, ASCII, `Synthetic …` identifiers, and reserved domains only.
- **§3 Determinism.** Byte-identical output, and literal values with integer or `Decimal` arithmetic. No random
  number generator (seeded or not), clock, environment, network or file read. Explicit encoding and `\n`. A nested
  `.gitattributes` marks the directory `-text`.
- **§4 Provenance.**
  - The builder is `tests/fixtures/build_eval_inputs.py`.
  - The manifest is `tests/fixtures/eval_inputs/manifest.json`, with ten required fields and no timestamp.
  - A later change to a committed fixture needs overwrite approval and a record of the old and new `sha256`.
- **§5 Case binding.** Explicit paths, bound both ways between cases and manifest, with no orphans. The manifest,
  builder and `.gitattributes` are never inputs.
- **§6 Input semantics.** A fixture never carries an answer, verdict, precomputed result or grader string.
- **§7 Size.** Minimal, at most 16 KiB per file. The M13.1 large-dataset generator is not an eval-input builder.
- **§8 Static validation.** Ten assertions added to the §E.5 validator, including byte-identical rebuild. They are not
  implemented here.
- **§9 Execution.** The committed file is consumed, and nothing is generated at execution. Delivery is governed by
  §F.6, unchanged.
- **§13 Production.** No production impact.

**What it amends (§10), on acceptance.** Only two passages of ADR-0039:

- **§E.2's last sentence:** the input sources become `assets/demo-data/` and `tests/fixtures/eval_inputs/` under
  ADR-0041, and each case names its inputs.
- **§E.5's second assertion:** the path rule narrows from `tests/fixtures/` to `tests/fixtures/eval_inputs/`, and the
  §8 assertions are added.

ADR-0039's file and status line are not edited.

**What it leaves unchanged (§11).** Everything else in ADR-0039, and ADR-0040 in full. In particular:

- **Suites:** the five suites and the §E.3 case set.
- **Graders:** deterministic wherever possible, and an LLM grader only where one cannot express the property.
- **The §E.1 first-case gate**, and every §F clause:
  - the owner's per-execution authorisation;
  - an explicit `--max-cost-usd`;
  - `--no-publish`;
  - `--runs 3 --threshold 1.0`;
  - no real servers, mocks, web or `mcp__` grants;
  - no authentication or connector.
- **Data:** no real data.
- **Evidence:** the §E.6 vocabulary.
- **Rules:** I-1 to I-13, §G, and §H.
- **§L, word for word.** Its "E.5 passing" now includes the new assertions through the amended §E.5, which is the
  only way the gate is touched.

**What it does not resolve (§12).** G-2 and G-3 stay open. No execution is authorised.

## 12. Architecture changes

None to `architecture.md`. ADR-0041 is `Proposed`. On acceptance, §19 gains its row. §15 needs no change, because it
names no input location.

## 13. Project-plan updates

None, as the prompt required:

- M13 stays `IN PROGRESS`;
- M13.2 stays `PLANNED`, not started and not authorised;
- matrix totals, the defect register and *Known issues* are unchanged.

## 14. Documentation updates

This record and ADR-0041 only.

## 15. Remaining work

1. **Owner review and acceptance of ADR-0041**, with any changes the owner directs.
2. **On acceptance:**
   - index ADR-0041 in `docs/decisions/README.md` (index row and amendment note);
   - index it in `architecture.md` §19;
   - a commit, only on the owner's request.
3. **M13.2 implementation**, under its own prompt through the Milestone gate. That prompt states whether execution is
   authorised, and its `--max-cost-usd`.
4. **G-2** must be resolved before any `manual_observation` scenario is executed or relied upon.
5. **G-3**, a fresh reading of the platform's help and grant surface, must be done immediately before any eval
   execution.

## 16. Git commit reference

N/A. Nothing committed and nothing pushed. Branch `main`, `HEAD` `75ced037b238b5a49f2b8a8246c9d2c4635c8a78`, and two
untracked files (§4).

## 17. Validation output (verbatim)

```
$ git status --short          # before any change: no output (clean)
$ git rev-parse HEAD
75ced037b238b5a49f2b8a8246c9d2c4635c8a78
$ git rev-parse origin/main
75ced037b238b5a49f2b8a8246c9d2c4635c8a78
$ git log -1 --oneline
75ced03 M13: mark milestone in progress

$ git diff --check
(no output, exit 0)

$ claude --version
2.1.278 (Claude Code)
$ claude plugin validate . --strict
Validating marketplace manifest: D:\Prakash\Claude\Plugins\BusinessIQ\BusinessIQ\.claude-plugin\marketplace.json

✔ Validation passed
(exit 0)

$ cd tests && python --version
Python 3.13.1
$ python -m unittest -v unit.test_m12b_connector_registry.ShippedAdmission.test_no_gate_record_block_exists_in_the_repository
Ran 1 test in 0.006s
OK
$ python -m unittest unit.test_m13_coverage_matrix
Ran 26 tests in 0.314s
OK

$ git status --short          # after
?? docs/decisions/ADR-0041-m13-2-deterministic-repository-owned-eval-fixtures.md
?? docs/development/2026-09-19-m13-2-g1-contract-remediation-adr-0041.md
```
