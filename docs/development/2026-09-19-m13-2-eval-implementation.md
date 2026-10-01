# 2026-09-19 — M13.2: behavioural eval suite, eval input fixtures and static validator (implementation only)

**Milestone:** 13 — Test Hardening & Evals, part M13.2 (behavioural evals), under ADR-0039 as amended by ADR-0040 and
ADR-0041.
**Status on completion:** IN PROGRESS. The implementation stage is done and awaits owner review. M13.2 is **not**
`COMPLETED`: ADR-0039 §L still needs one recorded §E.1 outcome and, under (b) or (c), a `manual_observation` scenario
per S3 row, which waits on G-2. Nothing committed, nothing pushed.
**Supersedes:** None. Every earlier record is unchanged.

## 1. Prompt / task performed

The owner's "BusinessIQ — M13.2 Eval Implementation" prompt (2026-09-19). It asked for the repository-side assets
ADR-0039 §E and ADR-0041 require:

- deterministic eval input fixtures, their builder, manifest and `.gitattributes`;
- eval case definitions in five suites;
- deterministic graders wherever possible, and LLM graders only where necessary;
- the §E.5 static validator, extended by ADR-0041 §8;
- coverage-matrix reconciliation, documentation, and focused and full testing.

It prohibited:

- executing any paid or plugin eval, invoking the eval harness, and using the web, MCP servers, `mcp__` tools,
  authentication or credentials;
- product behaviour changes, eval mocks, `evals/mocks/` and fake pass evidence;
- changing the accepted contract, M12-C's status or the empty connector registry;
- starting M13.3, committing and pushing.

It also required implementation decisions to be made without asking the owner.

## 2. Objective

Make the repository ready for a later, separately authorised execution of the ADR-0039 eval suite, without executing
it. That means authoring every §E.3 case against lawful inputs, making every mechanically expressible property
deterministic, and making the whole suite statically checkable on every run.

## 3. Changes made

### 3.1 Baseline repository state (Phase 0)

| Item | Observed |
|---|---|
| Branch | `main` |
| `HEAD` | `21ee21b21213ad80273650f056ef2f318023742c` ("M13.2: accept deterministic eval fixture contract") |
| `origin/main` | `21ee21b21213ad80273650f056ef2f318023742c`, equal to `HEAD` |
| Working tree | Clean |
| M13 / M13.1 / M13.2 | `IN PROGRESS` / `COMPLETED` / `PLANNED`, not started |
| ADR-0039, 0040, 0041 | All `Accepted` |
| `evals/` | Absent. No `case.yaml`, no `tests/fixtures/eval_inputs/`, no `test_m13_eval_cases.py`. **M13.2 had not been started** |
| Baseline regression | `python tests/run_tests.py`: **4,749 tests, 0 failures, 0 errors, 28 skipped, 681.553 s** (§9) |

The state matched the prompt's expectation exactly.

### 3.2 Authoritative documents read

- **Governance and design:** `CLAUDE.md`, `architecture.md` (§8, §13, §15, §16, §19, §20) and `project_plan.md`.
- **ADRs:** ADR-0039, ADR-0040 (via `project_plan.md` and the matrix) and ADR-0041 in full, plus ADR-0009.
- **Development records:** the two M13.2 records of 2026-09-19.
- **`docs/testing/`:** README, the coverage matrix, the defect register and the measurements, including the
  M13-MEAS-D2 pairs.
- **Tests:** `tests/unit/test_m13_coverage_matrix.py`, `tests/unit/test_m13_discriminability.py`, the existing
  fixture builders and `tests/run_tests.py`.
- **Product surfaces:** every `commands/*.md` frontmatter and every `skills/*/SKILL.md` frontmatter;
  `commands/benchmark-comparison.md` and `skills/biq-benchmark-comparison/SKILL.md`;
  `reference/research-policy.md`, `reference/ambiguity-protocol.md` and `reference/analysis-framework.md`.
- **Engine:** `lib/python/biq/research/gate.py`, the connector absence text in `lib/python/biq/connectors/contract.py`,
  the fraud boundary in `lib/python/biq/anomaly/contract.py`, and the forecast minimum in
  `config/businessiq.defaults.json`.
- **Plugin files:** the manifest and `.gitignore`.

**Outside the repository.** To see whether a local example of a case format existed, one locally installed third-party
plugin's `evals/` directory was listed and three of its files were read. It uses a different layout (`prompt.md`
plus `graders/*.md`). Nothing was adopted from it, and it is **not** evidence of the platform's format. No platform
help text or documentation was read (G-3).

### 3.3 Inventory sources

- **Built skills:** the 16 directories under `skills/`. None carries `disable-model-invocation` or
  `user-invocable: false`, so all 16 are model-invocable. None of the five unbuilt `architecture.md` §4 skills is
  included (D-13).
- **Model-invocable commands:** the 18 of 19 `commands/*.md`. `retrieval-slice` carries
  `disable-model-invocation: true` and is excluded, as in M13-MEAS-D2.
- **D2 near-miss pairs:** the *Top three pairs* column of M13-MEAS-D2 in `docs/testing/measurements.md`:

  | Tier | Pairs |
  |---|---|
  | Command | `industry-research` / `market-analysis` 0.556; `decision-support` / `strategy-analysis` 0.458; `company-analysis` / `market-analysis` 0.415 |
  | Skill | `biq-industry-research` / `biq-market-analysis` 0.633; `biq-decision-support` / `biq-strategy-recommendations` 0.345; `biq-company-analysis` / `biq-market-analysis` 0.340 |

  The validator re-reads these from the file rather than from a list.
- **Approval rows:** `architecture.md` §8 and the matrix's S5 rows. The numbering is current, and S5-03, S5-04 and
  S5-10 are the rows the prompt named.

### 3.4 Fixtures (Phase 1, ADR-0041)

**Prototyped before committing.** Each design was run through the unchanged pipeline in the session scratchpad
first. The finding that shaped two of the three: a thousands-separated money pattern matches ordinary CSV lines, so
`2025-01-10,640.00` contains `10,640.00`. ADR-0041 §6 forbids a grader string that the bound fixture itself carries.
S3-01 and S3-02 therefore place a `Synthetic …` text column before the amount, so that no line reads as a figure.
That column is the one addition beyond the strict minimum, and it is why each of those two fixtures has three columns
rather than two.

| Id | File | Bytes | SHA-256 | Precondition, through the unchanged pipeline | Bound case |
|---|---|---|---|---|---|
| EVI-01 | `s3_01_monthly_amounts.csv` | 132 | `8cd7e42e…6cb74efb` | Revenue maps to `Amount` only as `confirm_required` (0.67). The grade is `WARNING`, and its only finding is that provisional mapping | `evals/behaviour/b01-ambiguous-column` |
| EVI-02 | `s3_02_order_revenue.csv` | 174 | `0945e95e…66b46810` | Two of four rows lack revenue. The gate grades `CRITICAL`, halts, and all six analytical commands stop with no findings | `evals/behaviour/b02-critical-quality-halt` |
| EVI-03 | `s3_03_monthly_revenue.csv` | 93 | `2d4ff2c7…62bb4b4` | Four monthly periods, grade `PASS`. The revenue forecast is `insufficient_data` against the 12-period minimum | `evals/behaviour/b03-short-history-forecast` |

- **How each file was created.** The builder was run into a temporary directory and the result copied in, as a new
  file (ADR-0041 §4 *Creation*).
- **Builder.** `tests/fixtures/build_eval_inputs.py` imports only `os`. It uses literal values and integer pence, and
  writes explicit ASCII bytes with `\n` through `open(path, "wb")`. It has no random number generator, clock,
  environment, network, file read or unordered iteration.
- **Manifest.** `manifest.json` has every ADR-0041 §4 field, plus an `id` (`EVI-NN`), which the prompt asked for. The
  addition is additive: §4 lists required fields, not an exclusive set.
- **Line endings.** `.gitattributes` is exactly `* -text\n`.
- **Not fixtures.** S3-04 uses `assets/demo-data/northwind_sales.csv`, unchanged, and S3-05 uses no file.

### 3.5 Case schema (Phase 2) — implementation decision

**No case schema existed in the repository.** ADR-0039 fixes the layout, `evals/<suite>/<case>/case.yaml`, and what
a case must express (§E.3, §E.4). It fixes no serialisation. One deterministic format was chosen: **`biq-eval-case/1`**,
documented in `docs/testing/eval-suite.md`.

- **A strict YAML subset.** The validator reads it as text, as §E.5 requires, because the standard library has no YAML
  parser. The subset is valid YAML with the same meaning, so the platform can later read the same file.
- **Required fields:**
  - `id`, `suite`, `purpose` and `expected_property`;
  - `coverage_rows` and `components` (repository paths that must exist);
  - `requires_business_file`, `inputs` and `fixture`;
  - `prompt`;
  - `safety`, `tool_grants` (only the symbolic `engine-python`, §F.5) and `ablation` (§F.8);
  - `evidence_class` and `evidence_reason`;
  - `graders`;
  - on routing cases only, the routing fields: kind, D2 source, tier, pair and competing member.
- **Grader vocabulary (BusinessIQ's own):**
  - `skill_invoked` and `skill_not_invoked`;
  - `command_invoked` and `command_not_invoked`;
  - `agent_not_dispatched`;
  - `tool_not_invoked`, with an optional input pattern;
  - `response_matches` and `response_not_matches`;
  - `llm_judgement`, which must carry `why_not_deterministic`.
- **Rejected alternatives:**
  - the `prompt.md` plus `graders/*.md` form, because §E.2 names `case.yaml`;
  - adopting another plugin's grader keys, because they are unverified (prompt rule: no unverified platform
    capability).
- **No ADR.** The choice is repository-local and reversible, and the prompt directed that it be recorded here.

**Unresolved:** whether the platform reads this schema directly or needs a mechanical translation. That is part of G-3
and is not decided here.

### 3.6 Case inventory (Phases 3 to 7)

| Suite | Cases | Rows served |
|---|---|---|
| `behaviour` | 5: `b01` ambiguous column (EVI-01), `b02` CRITICAL halt (EVI-02), `b03` four-period forecast (EVI-03), `b04` anomaly not fraud (demo file), `b05` no uncited external claim (no file) | S3-01 to S3-05; S1-09, S1-10, S1-12, S1-14 |
| `disclosure` | 8: `d01` to `d04` the four ADR-0009 questions, each quoted verbatim; `d05` Tier 3; `d06` small denominator; `d07` re-identifying combination; `d08` Tier 2 | S3-07 to S3-10; S1-15, S1-16, S5-02, S5-07, S6-01, S6-02 |
| `approval` | 24: `a01` to `a17` every model-invocable read-only command (all 18 except `executive-report`); `a18` draft (executive report); `a19` new output file; `a20` overwrite; `a21` export; `a22` system write; `a23` communication; `a24` git push | S3-11, S5-01, S5-03, S5-04, S5-05, S5-08, S5-09, S5-10, S5-12, S1-18 |
| `connectors` | 5: `c01` CRM pull, `c02` accounting pull, `c03` connect HubSpot, `c04` record read, `c05` write | S3-06, S1-11, S1-18, S7-13 |
| `routing` | 22: `r01` to `r16` one positive per built skill; `r17` to `r22` one near-miss per D2 pair | S3-12 |
| **Total** | **64** | |

**Cases with no business file (24):**

- `b05`;
- `d01` to `d03` and `d06` to `d08`;
- `a06`, `a07`, `a10`, `a11`, `a22` and `a24`;
- `c01` to `c05`;
- `r03`, `r04`, `r11`, `r12`, `r17`, `r19`, `r20` and `r22`.

These are research, connector, repository or disclosure requests that read no file.

**Connector cases** run against the real, empty registry. There is no mock, HubSpot is not added, and every connector
case forbids every `mcp__` tool.

**Near-miss direction.** Industry/market tops both tiers and is tested in opposite directions: `market-analysis` must
win in the command tier, and `biq-industry-research` in the skill tier.

### 3.7 Grader classification (Phase 8)

**133 graders: 88 deterministic, 45 LLM.** Every case has at least one deterministic grader, and routing is entirely
deterministic.

| Deterministic check | Count |
|---|---|
| `command_invoked` | 21 |
| `tool_not_invoked` | 21 |
| `skill_invoked` | 20 |
| `response_matches` | 17 |
| `command_not_invoked` | 3 |
| `skill_not_invoked` | 3 |
| `response_not_matches` | 2 |
| `agent_not_dispatched` | 1 |

**Deterministic where the contract fixes the wording.**

- **Fixed text:**
  - "no reliable source found" (`architecture.md` §16, `reference/ambiguity-protocol.md`);
  - the `CRITICAL` grade;
  - the periods available and the periods required. The 12 is checked against `config/businessiq.defaults.json`;
  - the CSV or Excel alternative (`connectors/contract.py`);
  - "draft".
- **Named targets:** the destination, the recipient and the file.
- **Non-transmission:** no percentage, amount, customer name or identifying combination in any outbound tool input.
- **Tool use:** no `mcp__` tool, no shell upload or mail, no `git push`, and no scout dispatch before a Tier-2
  approval.
- **Routing:** every routing assertion.

| LLM property | Count | Why not deterministic |
|---|---|---|
| No approval requested (read-only and Tier-0 cases) | 22 | Outputs legitimately *mention* approval, since each command states which later actions need it. A request and a statement share their words |
| Approval asked, naming the target (`a19` to `a21`, `a23`) | 4 | Same reason |
| Refused, with no approval route (`a22`, `c05`); refused as blocked (`c04`) | 3 | Refusal and the absence of an approval offer are meanings in open wording. The deterministic grader proves no MCP call was made |
| Named absence, nothing fabricated (`c01`, `c02`) | 2 | Fabrication is semantic. The file alternative and the absence of an MCP call are asserted deterministically |
| User connects through the platform (`c03`) | 1 | A credential request and a connection claim share words with correct refusals |
| Ambiguous column named, nothing assumed (`b01`) | 1 | ADR-0041 §6 forbids asserting the fixture's header literally. The protocol's required shape quotes confidence values that a number pattern would misread |
| No figure of any kind on a CRITICAL halt (`b02`) | 1 | An unseparated total and an explanatory count look alike. The separated-figure pattern is asserted deterministically |
| No projection (`b03`) | 1 | Historical figures may be restated. Only reading tells a projection from history |
| Never labels fraud (`b04`) | 1 | The product's mandated disclaimer (`INVESTIGATION_NOTE`) contains the word "fraud" |
| No uncited external claim (`b05`) | 1 | Whether a sentence is an attributed external claim is semantic |
| No invented benchmark or trend (`d01` to `d04`) | 4 | The user's own figure is legitimately restated |
| Tier 3 refused with an alternative; small denominator; re-identification (`d05` to `d07`) | 3 | These are meanings. Non-transmission is asserted deterministically |
| Tier-2 single-use approval (`d08`) | 1 | The exact transmitted text is built by the gate at run time, so it cannot be known in advance. The disclosed value and the absence of any dispatch are asserted deterministically |

No grader introduces a score, rank, weight or threshold. The pass rule stays §F.7's. No grader was executed, and no
pass result exists.

### 3.8 Static validator (Phase 9)

`tests/unit/test_m13_eval_cases.py` has 59 tests in eight classes: `SuiteLayout`, `CaseSchema`, `Inventory`, `Inputs`,
`Safety`, `Graders`, `EvidenceAndMatrix` and `EvalInputFixtures`.

**It covers the prompt's 28 checks and ADR-0041 §8's ten.** Checks the prompt did not list:

- the subset reader is itself tested to fail closed on eight malformed inputs;
- positive and negative probes for six grader patterns;
- "answer key" is operationalised: any run of three or more digits in a grader's pattern or criteria must come from
  the case's own prompt, and no two-decimal amount appears in a grader;
- the forecast grader's 12 must equal the shipped config default.

**Reconciled against the repository, not a list:**

- every built skill;
- every model-invocable command;
- the four ADR-0009 questions, parsed from ADR-0009;
- the D2 pairs, parsed from `measurements.md`.

**Mutation check** (scratch copy of the repository, never the working tree). Twenty deliberate corruptions each failed
the validator, and the unmutated copy passed. They covered:

- **fixtures:** a changed fixture byte, an orphan fixture and a telling header in a fixture;
- **builder:** `import random`;
- **layout:** `evals/mocks/` and a scaffold script;
- **safety:** a web grant, a prohibited flag in the procedure, a real URL, a token in a prompt and a clock word;
- **evidence:** `automated_pass`;
- **inputs:** an input outside the admitted roots;
- **inventory:** a dropped skill, a wrong D2 pair, a missing ADR-0009 question and a dropped read-only command;
- **graders:** an LLM grader without its reason and a numeric answer key;
- **matrix:** a removed citation.

`tests/integration/test_m13_eval_input_preconditions.py` (13 tests) proves each fixture's precondition through the
unchanged pipeline. It also proves the demo file cannot stand in for any of the three (ADR-0041 §1, §7).

### 3.9 Coverage (Phase 10)

- **Case citations.** Each of the 18 `behavioural-only` rows now names its case files in *Covering tests*. The 15
  deterministic rows whose requirement has a behavioural half name their cases in *Notes*, with the suffix "authored
  in M13.2 and `not_executed`". Each case lists its rows, and each row names its cases back, and the validator checks
  both directions.
- **Unchanged.** Statuses, evidence and totals: 99 rows; 76 `covered`, 3 `covered-by-M13`, 18 `behavioural-only`
  (all `not_executed`), 0 `not-applicable`, 2 `gap`. No row is `automated_pass`.
- **No `manual_observation`** was created. It is tied to §E.1 (b) or (c) and waits on G-2.
- **Header prose.** The matrix title and state paragraphs were updated for M13.2.

## 4. Files created

| File | Purpose |
|---|---|
| `tests/fixtures/build_eval_inputs.py` | The ADR-0041 builder |
| `tests/fixtures/eval_inputs/.gitattributes` | `* -text` |
| `tests/fixtures/eval_inputs/manifest.json` | The ADR-0041 §4 manifest |
| `tests/fixtures/eval_inputs/s3_01_monthly_amounts.csv`, `s3_02_order_revenue.csv`, `s3_03_monthly_revenue.csv` | EVI-01 to EVI-03 |
| `evals/<suite>/<case>/case.yaml` × 64 | The suite (§3.6) |
| `tests/unit/test_m13_eval_cases.py` | The §E.5 / ADR-0041 §8 validator, 59 tests |
| `tests/integration/test_m13_eval_input_preconditions.py` | Fixture preconditions, 13 tests |
| `docs/testing/eval-suite.md` | Schema, graders, inventory and execution procedure |
| `docs/development/2026-09-19-m13-2-eval-implementation.md` | This record |

## 5. Files modified

- `docs/testing/coverage-matrix.md`: the case citations, and the title and state prose. No status or total changed.
- `docs/testing/README.md`: the index row, the validators and the evidence state.
- `architecture.md`: §15 gains an "M13.2 suite" paragraph, and §20 item 1 gains one sentence. Both fall within
  ADR-0039 §A.2.
- `project_plan.md`:
  - the header, the M13 row and the two M13.2 table rows, which move from `PLANNED` to `IN PROGRESS`;
  - a new *M13.2* section;
  - an R-05 note.

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | Reachable by users? |
|---|---|---|
| Behavioural eval suite, authored | `evals/` | No. It is a development artifact, not executed, and runs only under a future owner-authorised §F execution |
| Eval input fixtures | `tests/fixtures/eval_inputs/` | No. Test-only; no product path reads `tests/` |
| Static validator | `tests/unit/test_m13_eval_cases.py` | No. It runs in `tests/run_tests.py` |

No product feature was added.

## 8. Tests performed

1. `python tests/run_tests.py`, the baseline before any change.
2. `python tests/run_tests.py unit.test_m13_eval_cases`, focused.
3. The validator mutation check: `mutate.py` in the session scratchpad, on a scratch copy of the repository.
4. `python tests/run_tests.py -v integration.test_m13_eval_input_preconditions`, focused.
5. `unit.test_m13_coverage_matrix`, `unit.test_m13_discriminability`, `unit.test_manifest`,
   `unit.test_m12b_connector_registry` and `negative.test_m12b_connector_security`, all `-v`. These are related modules
   that read `docs/`, the manifest or the registry.
6. `claude plugin validate . --strict`.
7. `python tests/run_tests.py -v`, the full regression after every change.
8. `git diff --check`, plus a whitespace scan of the untracked files.
9. A secret-pattern scan of every added and changed file.
10. The scope audit: `git status --porcelain` and `git diff --stat`, path by path against ADR-0039 §A.2 and §A.3.

**Not executed**, and not to be executed in this milestone:

- `claude plugin eval` in any form (including `--help` and `init`), and therefore the §E.1 availability measurement
  and every eval case;
- any `manual_observation` scenario;
- the opt-in suites: `BIQ_LARGE_DATASET`, `BIQ_AGENT_BOUNDARY_RUNTIME` and `BUSINESSIQ_LIVE_SMOKE`. They stay
  skipped by design;
- any web, MCP, connector or authentication use.

## 9. Test results

| Run | Result |
|---|---|
| Baseline, before any change | **4,749 tests, 0 failures, 0 errors, 28 skipped, 681.553 s** (Python 3.13.1) |
| `unit.test_m13_eval_cases` | 59 tests, 0 failures, 0 errors, 0 skipped, 0.270 s |
| Mutation check | Unmutated copy: 59 tests, 0 failures. All 20 mutations failed, each on the intended test |
| `integration.test_m13_eval_input_preconditions` | 13 tests, 0 failures, 0 errors, 0 skipped, 0.688 s |
| `unit.test_m13_coverage_matrix` | 26 tests, 0 failures, 0 errors, **1 skipped** (see below) |
| `unit.test_m13_discriminability` | 13, 0, 0, 0 |
| `unit.test_manifest` | 15, 0, 0, 0 |
| `unit.test_m12b_connector_registry` | 51, 0, 0, 0 |
| `negative.test_m12b_connector_security` | 78, 0, 0, 0 |
| `claude plugin validate . --strict` (Claude Code 2.1.278) | "✔ Validation passed", exit 0. Its output names only `.claude-plugin/marketplace.json` and says nothing about `evals/`. **Observed:** the validator neither reports nor rejects the case files. Whether it inspected them is not observable from its output |
| Full regression, after all changes | Recorded in §17 |

**Why the skip count rises by one.** The M13.1 test
`unit.test_m13_coverage_matrix.RowsUseTheClosedVocabularies.test_no_row_claims_automated_evidence_while_no_eval_case_exists`
skips itself by design once any `case.yaml` exists ("eval cases exist; automated evidence is then possible"). Its
protection is replaced, and tightened, by two new tests:

- `unit.test_m13_eval_cases.EvidenceAndMatrix.test_no_automated_or_manual_evidence_is_claimed`;
- `…test_every_case_is_not_executed_with_the_e1_c_reason`.

The M13.1 module was not edited (ADR-0039 K.2).

## 10. Issues discovered

**No defect record was created.** No execution happened, so no product behaviour was observed. The validator found no
infrastructure defect, and M13-DEF-01 to 03 are unchanged. The following are real, open items, recorded and not acted
on:

1. **`architecture.md` §13 is stale for `evals/`.** Its repository tree reads `evals/ case.yaml suites + mocks/`.
   ADR-0039 §H says `evals/mocks/` is not created, and §15 was already corrected at M13-A. §13 is outside ADR-0039
   §A.2, which admits only §15, §19 and §20, so under §A.2 this is **reported, not edited**. It belongs with D-14,
   which is deferred to M14.
2. **Tier-2 reachability (observation, no defect).** No shipped command or skill instructs presenting the gate's
   Tier-2 consent request:
   - `commands/benchmark-comparison.md` and its skill **refuse** to send the internal figure ("A benchmark chosen to
     sit near our number is not a benchmark");
   - the four research commands state that they send nothing internal.

   So `d08` ("a Tier-2 request halts with the verbatim text", ADR-0039 §E.3) may fail at execution because of product
   design rather than model behaviour. Either way nothing is transmitted, which the case's deterministic graders
   check. Whether this is a product defect, a contract question or neither can only be decided on an observed
   execution. Recorded for the owner, and not pre-judged.
3. **The platform's case format is unverified.** Schema `biq-eval-case/1`, the grader vocabulary and the symbolic
   `engine-python` grant must be mapped to the platform at the G-3 pre-flight (`docs/testing/eval-suite.md`).
4. **Input delivery is unverified.** How a named input reaches the case sandbox is also a G-3 matter (ADR-0041 §9).

## 11. Decisions made

No ADR. Implementation decisions, all within ADR-0039 as amended by ADR-0040 and ADR-0041:

- **Case schema:** `biq-eval-case/1` (§3.5).
- **Case ids** are `<suite letter><nn>-<slug>`.
- **Fixture file names** are neutral (`s3_01_monthly_amounts.csv`, not "ambiguous"), so a name leaks nothing to the
  model (ADR-0041 §6).
- **Fixture layout:** S3-01 and S3-02 carry one text column before the amount (§3.4).
- **Approval coverage:** every model-invocable read-only command gets a no-approval case, the four research commands
  included (§8 lists them as read-only analysis). The executive report is covered as draft generation (S5-03).
- **Disclosure prompts** quote the four ADR-0009 questions verbatim, with public context terms added so that a Tier-0
  query is constructible.
- **Near-miss direction** is alternated across the tiers (§3.6).
- **The overwrite target** in `a20` is `README.md`, a document, not source data. Its existence in the sandbox is a
  G-3 item.
- **Evidence:** every case `not_executed`, "no owner authorisation / ceiling". **No §E.1 outcome is recorded.** The
  prompt authorised implementation, not an execution decision. Whether (c) is the final outcome, or execution follows,
  is the owner's call.

## 12. Architecture changes

`architecture.md`:

- **§15:** an "M13.2 suite (authored, not executed)" paragraph, stating facts only.
- **§20 item 1:** one sentence.

No architectural change. §13 is stale and deliberately unedited (§10 item 1).

## 13. Project-plan updates

- **M13.2** moves from `PLANNED` to **`IN PROGRESS`**, in the header, the M13 row, the contract row and the
  sub-milestone row. A new M13.2 section is added. §E.1 is `PLANNED`, and the manual scenarios are `BLOCKED` on G-2.
- **R-05** gets a note that the routing cases are authored but not executed.
- **Unchanged:** R-01, M9, M12-C and every defect.

## 14. Documentation updates

As §4 and §5.

## 15. Remaining work

1. **Owner review** of this implementation, and a commit only on the owner's request.
2. **The §E.1 decision:** authorise an execution with a `--max-cost-usd` ceiling, which leads to outcome (a) or (b),
   or record outcome (c).
3. **G-3 pre-flight** before any execution (the list in `docs/testing/eval-suite.md`).
4. **G-2** before any `manual_observation`. Under (b) or (c), one scenario per S3 row is required for M13.2
   `COMPLETED`.
5. **Owner visibility:** items 1 and 2 of §10.

## 16. Git commit reference

N/A. **No commit and no push.** Branch `main`, `HEAD` `21ee21b21213ad80273650f056ef2f318023742c`, and the working
tree as §17 records.

## 17. Closing verification

**Full regression after every change** (`python tests/run_tests.py -v`, Python 3.13.1):

```
Ran 4821 tests in 598.487s
OK (skipped=29)
ran 4821 | failures 0 | errors 0 | skipped 29
```

**Against the baseline** (4,749 tests, 0 failures, 0 errors, 28 skipped, 681.553 s):

- **+72 tests:** 59 in `unit.test_m13_eval_cases` and 13 in `integration.test_m13_eval_input_preconditions`. All 72
  passed.
- **+1 skip:** the M13.1 self-skip explained in §9. The other 28 skips are the pre-existing ones:
  - openpyxl absent: `test_data_layer` 7, `test_vertical_slice` 4, `test_tier2_runtime` 6;
  - opt-in `BIQ_AGENT_BOUNDARY_RUNTIME`: 7;
  - opt-in `BIQ_LARGE_DATASET`: 2;
  - opt-in `BUSINESSIQ_LIVE_SMOKE`: 2.
- **No duration anomaly.** 598.5 s against the 681.6 s baseline and M13.1's 414.5 s re-time. Wall clock is
  machine- and load-dependent, as `measurements.md` records.

**Other checks:**

- **`git diff --check`:** clean, exit 0. The only output is git's LF-to-CRLF working-copy notice, which `core.autocrlf`
  prints on this machine (ADR-0041 fact 7).
- **Untracked-file scan:** no trailing whitespace, tab or CR in any new file.
- **Secret scan** (every new file and every added diff line, 74 files and 110 lines): 0 token-shaped strings, 0
  credential assignments, 0 private keys, 0 connection strings, and 0 URLs outside `example.com`. The only address is
  `finance-team@example.com`, which is reserved.
- **Strict validation:** `claude plugin validate . --strict` passed (§9).

**Scope audit** (ADR-0039 K.6, ADR-0041 §11):

| Check | Result |
|---|---|
| Files under `lib/`, `skills/`, `commands/`, `agents/`, `reference/`, `config/`, `assets/`, `.claude-plugin/`, and `.mcp.json`, `tests/run_tests.py`, `.gitignore`, `CLAUDE.md`, `CONNECTORS.md`, `README.md`, `docs/decisions/` | **None changed** |
| Existing test modules | **None changed.** All test changes are new files |
| `architecture.md` | Two hunks, both inside §15 (line 1624) and §20 (line 1748), which §A.2 admits |
| New paths | `evals/` (64 `case.yaml` only; no `mocks/`, scaffold, grader file or result), `tests/fixtures/build_eval_inputs.py`, `tests/fixtures/eval_inputs/` (3 CSV, manifest, `.gitattributes`), two new test modules, `docs/testing/eval-suite.md`, this record |
| Modified docs | `docs/testing/coverage-matrix.md`, `docs/testing/README.md`, `project_plan.md` |
| Registry, connector, M12-C | Unchanged: empty registry, no connector, M12-C `BLOCKED` |
| Eval execution, web, MCP, auth | None |

**Final working tree:** branch `main`, `HEAD` = `origin/main` = `21ee21b`.

- Modified: `architecture.md`, `docs/testing/README.md`, `docs/testing/coverage-matrix.md` and `project_plan.md`.
- Untracked: `docs/development/2026-09-19-m13-2-eval-implementation.md`, `docs/testing/eval-suite.md`, `evals/`,
  `tests/fixtures/build_eval_inputs.py`, `tests/fixtures/eval_inputs/`,
  `tests/integration/test_m13_eval_input_preconditions.py` and `tests/unit/test_m13_eval_cases.py`.

Nothing is staged, committed or pushed.
