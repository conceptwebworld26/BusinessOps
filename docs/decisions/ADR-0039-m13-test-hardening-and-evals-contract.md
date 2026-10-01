# ADR-0039 — The M13 test hardening and evals contract: a closed coverage matrix, deterministic gap closure, recorded measurement, and a behavioural eval suite that runs only under an explicit execution policy and changes no product behaviour

**Date:** 2026-09-18
**Status:** Accepted — 2026-09-18, by the project owner, with the clarifications recorded in *Owner clarifications at
acceptance*. Acceptance approves the contract only. It authorises no implementation: M13.1 and M13.2 each need their own
implementation prompt, and no eval is executed without the per-execution authorisation §F.1 requires.
**Deciders:** Project owner (acceptance and clarifications, M13 contract finalization), proposed in the post-M12-B
roadmap reconciliation (decision only)
**Supersedes:** none. **Amends:** none. ADR-0007 is not edited; this ADR applies it to Milestone 13 and records the
platform fact that triggers its *Revisit when* clause (see *Relationship to ADR-0007*).
**Relates to:** [ADR-0007](ADR-0007-two-layer-testing-strategy.md) (fixture tests primary, evals secondary),
ADR-0001 (verified platform facts only), ADR-0002 (figures from code), ADR-0009 (disclosure tiers and the four
comparative questions), ADR-0010 (approval follows consequence), ADR-0013 (discriminability is the real constraint),
[ADR-0037](ADR-0037-m12-connector-layer-contract.md) and [ADR-0038](ADR-0038-optional-connector-connection-lifecycle.md)
(connector layer; M12-C `BLOCKED`), ADR-0035 (the `biq-verifier` boundary).

## Context

### What the repository says Milestone 13 is

Verified by reading the repository at `990e88d`:

| Source | Statement |
|---|---|
| `project_plan.md` M13 | "Full negative-path coverage; large-dataset performance; routing/discriminability cases; approval-model cases (read-only never prompts); authored eval cases with mocks. Eval execution `BLOCKED` on early-access enablement." Depends on M10 |
| `architecture.md` §15 | Layer 1: `tests/` — `unit/`, `integration/`, `negative/`; a named fixture corpus (13 items plus cross-tier equivalence and business-model relevance). Layer 2: `evals/` — twelve named behaviours, including connector absence "via `evals/mocks/`", the four Tier-0 comparative questions, Tier-3 refusal, small-denominator and re-identification blocking, read-only commands never prompting, and routing cases |
| `architecture.md` §16 | Eighteen failure scenarios, each with a required behaviour |
| ADR-0007 | Every failure mode in §16 and every command needs a negative test. While `plugin eval` is unavailable, behaviour is covered by scripted manual scenarios in `docs/testing/`, labelled manual. **Follow-up:** a coverage matrix mapping "each of the 24 specified scenarios" to its test. **Revisit when** `plugin eval` becomes available |
| `project_plan.md` M9 | Three rows still `PLANNED`: "Tier tests: 4 comparative questions pass at Tier 0 with no prompt"; "Tier 3 refused; small-denominator blocked; re-identifying combo blocked"; "No-source, conflicting-source, stale-source tests" |
| `project_plan.md` R-01, R-05, R-10 | Eval execution gated; description discriminability "Open — routing eval cases, M13"; forecast selection stability "belongs to the M13 eval work" |
| `project_plan.md` M12 (pre-review scope) | "connector-absent degradation tests via `evals/mocks/`; write-attempt approval-gate tests" — refined by ADR-0037 C-3 to refusal tests, and delivered deterministically by M12-B |
| `docs/testing/README.md` | Holds no coverage matrix and no manual scenario ("Empty until Milestone 1") |
| `.claude-plugin/plugin.json` | Already declares `"experimental": { "evals": "evals" }`. No `evals/` directory exists. `.gitignore` already lists `evals/results/` |
| `tests/` | 4,684 tests, 0 failures, 0 errors, 26 skipped at `990e88d` (measured at the start of this gate). Opt-in precedents: `BUSINESSIQ_LIVE_SMOKE`, `BIQ_AGENT_BOUNDARY_RUNTIME` |
| `tests/integration/test_performance.py` | M3's always-on data-layer baseline: 60,000-row synthetic CSV, "measurement, not benchmarking", deliberately loose order-of-magnitude thresholds. It is the existing coverage of the "large dataset" fixture |
| `tests/connector_fixtures.py` | M12-B's synthetic enforcement fixture: an in-memory `synthetic-crm` connector on a reserved `.invalid` host, whose module docstring states it is "not a connector measurement". It never reaches the registry's `_DECLARATIONS`, `.mcp.json` or any agent |
| `architecture.md` §2 / ADR-0013 | The one documented description limit is the **skill** `description`, 1,024 characters (hard). No overlap threshold for descriptions was ever adopted. The M9 owner decisions asked for one "agreed before descriptions are written", and none was recorded |

**Roadmap state at acceptance** (owner decisions, 2026-09-18):

- **M10 is `COMPLETED`.** Its sub-milestones and remediation chain, the Executive Report included, were completed and
  checkpointed (`62580f3` to `4dc6562`).
- **M9 is `IN PROGRESS`.** Its four external commands await owner-run fresh-session live smoke tests, and other rows
  remain `PLANNED`.
- **M12 is `COMPLETED` under OD-1**, with **M12-C `BLOCKED`**.
- **D-13 is open and does not block M13.** The five §4 skills are neither built nor scheduled.
- **D-14 is open and deferred to M14.** It covers the stale status banners.

### Platform facts measured for this decision (Claude Code 2.1.276, 2026-09-18)

1. `claude plugin eval --help` documents a runnable command: cases under `<eval dir>/**/case.yaml` (or `prompt.md`
   plus `graders/*.md`), `--runs` (default 3), `--threshold` (default 1.0), `--ablation` (default `with-without`),
   `--mocks record|off` (default `record`: a plugin server with no mock is **not** started), `--allow-real-servers`,
   `--allow-tools` (Bash, Write, Edit, WebFetch and `mcp__*` are gated behind an operator grant), `--scaffold`
   (off by default; runs author-supplied bash), `--max-cost-usd`, `--judge-model` (default `haiku`),
   `--trust-plugin`, and `--no-publish`.
2. **By default the HTML report is published to claude.ai** ("already the default when your account supports it").
   Under ADR-0010 that is an export off the machine.
3. Each run is "a full claude child on your own credential": executing evals spends the owner's model usage.
4. **A zero-case probe did not hit the early-access refusal R-01 recorded.** A throwaway plugin in the session
   scratchpad with an empty `evals/` directory, run as `claude plugin eval . --trust-plugin --no-publish --runs 1
   --max-cost-usd 0.01`, exited 1 with "No eval cases found … Run `claude plugin eval init` …" — case discovery, not
   "plugin eval is currently in early access". The probe was deleted afterwards. **This does not prove that a case
   executes.** It proves only that the refusal ADR-0007 measured on 2026-09-08 was not observed at the discovery stage.

### The problems this review found

**P-A — The coverage matrix ADR-0007 requires cannot be built as written.** It maps "the 24 specified scenarios", but
the product specification that enumerates them was never committed (`project_plan.md` *Documentation debt*, the common
root of D-01/D-02/D-06). A matrix against a document the repository does not hold would be invented.

**P-B — "Eval cases with mocks" for connectors would now invent connector behaviour.** ADR-0037 and ADR-0038 made
connector absence the real, shipped state: the registry is empty and every capability resolves to
`connector_not_configured`. A mock MCP server standing in for a vendor connector would simulate a connector
BusinessIQ does not have, and under `--mocks record` mocks stand in for *the plugin's own* servers — BusinessIQ
declares none but `biq-verifier`.

**P-C — Running evals has consequences the M13 scope line does not mention.** Publication to claude.ai (fact 2), spend
on the owner's credential (fact 3), author-supplied bash under `--scaffold`, and plugin MCP servers started outside the
OS sandbox under `--allow-real-servers` or `--mocks off`.

**P-D — "Full negative-path coverage" has no closed definition.** Without one, completion is a matter of opinion.

**P-E — R-01 may have lapsed.** Fact 4 triggers ADR-0007's *Revisit when* clause but does not settle it.

## Problem

Define Milestone 13 precisely enough to implement without ordinary option questions: what "coverage" is measured
against, what is added, what is measured, how behavioural evals are authored and when and how they may run, what a
failure means, and what completes the milestone — without changing product behaviour, weakening any existing test,
or touching the connector boundary.

## Options considered

### Option A — Build M13 as the one-line scope reads

**Rejected.** P-A, P-B and P-C in full: a matrix against an absent document, connector mocks that simulate a connector
the product does not have, and an eval run that by default publishes and spends with no gate.

### Option B — Deterministic hardening only; defer evals until R-01 is formally closed

**Rejected.** Fact 4 is precisely the condition ADR-0007 said to revisit on. The eval cases are, in ADR-0007's words,
"the specification of correct behaviour", and authoring them does not depend on execution. Deferring would leave R-05
and R-10 with no instrument either.

### Option C — Fix defects as M13 finds them

**Rejected.** A test-hardening milestone that edits skills, commands or engines to make its own tests pass is an
implementation milestone without a contract, and it removes the reviewer's ability to see a defect separately from its
fix. The repository's practice is one remediation per finding, each with its own prompt.

### Option D — A closed matrix; deterministic gap closure; recorded measurement; a behavioural suite under a written execution policy; defects recorded, never fixed or masked

**Chosen.**

## Decision

**Milestone 13 adds tests, fixtures, measurements, eval cases and test documentation, and nothing else. It changes no
product behaviour. Coverage is measured against a closed matrix whose rows come only from enumerations the repository
holds. Deterministic gaps are closed with deterministic tests. Performance, discriminability and forecast selection
stability are measured and recorded, never tuned. Behavioural eval cases are authored for the built component set and
executed only under the execution policy in §F. A defect found by any of this is recorded with a reproducer and left
for its own remediation; no test is weakened, skipped, marked expected-failure or regraded to hide it. M13 contains no
connector work, simulates no connector, and does not measure or approach M12-C's prerequisites.**

### Invariants — normative, and each one is a stop condition if breached

| # | Invariant |
|---|---|
| I-1 | **No production behaviour change to satisfy M13 (hard invariant).** M13 does not modify BusinessIQ production behaviour to make a test, eval or measurement pass. In particular, no production change is made because: a coverage row is missing; an eval fails; a measurement falls below anyone's preference; two routing descriptions overlap; or forecast method selection is unstable. The production surface is every path §A.3 lists |
| I-2 | **Automated eval execution and manual observation are separate evidence classes** (§E.6). They are recorded, counted and reported separately and never merged |
| I-3 | **Execution being unavailable is not a pass.** `execution_unavailable` and `not_executed` are never reported, counted or summarised as a pass, a success, or runtime evidence |
| I-4 | **A manual scenario is never an automated passing eval.** A `manual_observation` is never counted as `automated_pass`, as a successful execution, or as runtime evidence equivalent to automated evaluation |
| I-5 | **Every eval execution needs the owner's explicit authorisation and a stated `--max-cost-usd` ceiling** (§F.1). Without both, nothing is executed |
| I-6 | **`--no-publish` is mandatory** on every eval invocation (§F.2) |
| I-7 | **No real connector, MCP server, web access or authentication during eval execution** (§F.3, §F.4, §F.11) |
| I-8 | **M12-C remains `BLOCKED`** (§H). Nothing in M13 unblocks, measures, approaches or bypasses P-1 to P-5 or the Connector Gate |
| I-9 | **D-13 does not block M13.** M13 neither builds nor schedules the five unbuilt §4 skills, and does not resolve D-13 |
| I-10 | **D-14 is deferred to Milestone 14.** M13 corrects documentation only where M13's own status consistency directly requires it |
| I-11 | **M9 stays incomplete until its own closure evidence exists.** Covering M9's three tier-test rows in M13 does not complete M9. No M13 artifact stands in for M9's four fresh-session live smoke tests |
| I-12 | **ADR-0007's missing 24-scenario list is not reconstructed.** Rows come only from the S1–S7 enumerations the repository holds (§B). The original list is recorded as unavailable. No row is derived from memory, general knowledge or inference about what it contained |
| I-13 | **Recording a defect does not authorise fixing it.** An M13 defect record (§G.1) documents a product defect. Its fix belongs to a future milestone under its own prompt. Only test and eval infrastructure defects are fixed within M13 |

| Part | Scope | Status under this contract |
|---|---|---|
| **M13-A** | This contract | `COMPLETED (DECISION ONLY)` — accepted 2026-09-18 |
| **M13.1** | Deterministic hardening: the coverage matrix (§B), gap closure (§C), measurement (§D) | `PLANNED`; first implementation step after acceptance |
| **M13.2** | Behavioural evals: the availability measurement (§E.1), the suite (§E), execution under §F | `PLANNED`; starts after M13.1 is `COMPLETED`, because its routing near-miss cases and its behaviour-only rows come from M13.1's matrix and measurement |

### A. Objective and scope

**A.1 Objective.** Make the repository's test coverage *checkable*: every failure mode, command and specified behaviour
the architecture names maps to a test that ran, a deliberate `not applicable`, or a recorded gap — and give the
behavioural layer ADR-0007 designed a real, executable (or honestly unexecutable) suite.

**A.2 In scope.** Only the following:

- new files under `tests/unit/`, `tests/integration/`, `tests/negative/` and `tests/fixtures/`;
- `docs/testing/`: the matrix, the defect register (§G.1), the measurement records (§D.4), the eval execution record
  and any manual scenarios;
- `evals/`: case directories only. Each holds `case.yaml` or `prompt.md`, its graders, and any scaffold script §F.6
  permits;
- the milestone's own documentation: `project_plan.md`, `architecture.md` §15/§20 and §19, a dated development record,
  and the task report.

**The eval harness is the platform's `claude plugin eval`.** M13 builds no runner of its own and wires nothing into
`tests/run_tests.py`. M13's harness infrastructure is exactly three things:

- the case suite;
- the §E.5 static validator;
- the written execution procedure in `docs/testing/`.

M13 may fix defects in its own test and eval infrastructure (§G).

**A.3 Non-goals — M13 must not:**

- change any file under `lib/`, `skills/`, `commands/`, `agents/`, `reference/`, `config/` or `assets/`, or change
  `.claude-plugin/`, `.mcp.json`, `tests/run_tests.py` or `.gitignore`;
- add a command, skill, agent, MCP server, schema, KPI, quality check, forecast method, detector, research intent,
  connector, registry entry, Connector Gate record or dependency;
- fix a product defect it finds (§G), merge or rewrite a component description (R-05), change forecast method
  selection (R-10), or tune a threshold, materiality value, performance limit or grader to reach a pass;
- delete or weaken an existing test or assertion (retargeting follows the ADR-0037 §J rule: retargeted, never
  deleted, every security assertion kept);
- perform live external retrieval, dispatch `biq-research-scout`, or run the M9-D fresh-session live smoke tests;
- authenticate, connect, probe or call any connector, or call any authentication tool;
- measure, test or approach P-1 to P-5, or build anything that reads a connected-system record (§H);
- build or schedule any of the five skills `architecture.md` §4 names but the repository has not built
  (`biq-business-context`, `biq-semantic-mapping`, `biq-data-quality`, `biq-kpi-engine`, `biq-external-research`).
  D-13 stays open and does not block M13 (I-9);
- measure always-on token cost, write per-component reference pages (D-10, Milestone 14), or perform D-14's
  status-banner cleanup (I-10);
- mark Milestone 9 `COMPLETED`, or mark any M9 live-smoke-test row as run (I-11);
- introduce a pass/fail threshold for a measurement that no accepted architecture defines (§D).

A change outside A.2 that M13 finds necessary is a stop condition: it is reported, not made.

### B. The coverage matrix — closed rows

`docs/testing/coverage-matrix.md`, a table with one row per requirement. **Rows come only from these in-repository
enumerations**, which replace ADR-0007's "24 specified scenarios" (P-A). The matrix opens with a note that ADR-0007's
original list is **unavailable**: it was never committed, and it is not reconstructed (I-12). No row claims to
correspond to one of those 24 scenarios. The seven sets were checked against the repository at acceptance. Every
count below matches its source.

| Set | Source | Rows |
|---|---|---|
| S1 | `architecture.md` §16 *Error handling* | 18 — one per scenario |
| S2 | `architecture.md` §15 Layer-1 fixture corpus | 15 — the 13 named fixtures, cross-tier equivalence, business-model relevance |
| S3 | `architecture.md` §15 Layer-2 behaviours | 12 — as listed there, with connector absence read under §H |
| S4 | Every file in `commands/` | 19 — each command's negative path (ADR-0007) |
| S5 | `architecture.md` §8 approval matrix | 13 — one per class |
| S6 | The three `PLANNED` M9 tier-test rows | 3 — the four ADR-0009 comparative questions; Tier 3 / small denominator / re-identification; no-source / conflicting-source / stale-source |
| S7 | ADR-0037 §J | 19 — referenced, not re-derived: each row points at the M12-B test already covering its deterministic half; runtime halves are `not applicable — agent not built (ADR-0037 §D.1)` |

Each row carries: a stable id (`S1-01` …), the requirement quoted from its source, the layer (`deterministic`,
`behavioural`, `manual`), the covering tests as `module.Class.test_name` or eval case paths, and exactly one status:

- `covered` — a named test covers it **and ran in the M13 run that closes the milestone**;
- `covered-by-M13` — the same, where the test was added by M13;
- `behavioural-only` — no deterministic statement is possible. The row names its eval case and carries exactly one
  automated evidence class (§E.6), plus a reference to any `manual_observation`. The status says where the behaviour is
  specified, not that it was demonstrated. It is demonstrated only when its class is `automated_pass`;
- `not-applicable` — with the reason, citing the ADR or file that makes it so;
- `gap` — with the defect id (§G.1) that explains why it is still open.

A row may not be `covered` by a test that was skipped in the closing run. Sets are closed: adding a set needs a new
decision. Where one requirement appears in two sets (for example S3's Tier-3 refusal and S6), the later row
references the earlier one rather than duplicating it. Covering an S6 row gives the matching M9 row a matrix
reference and changes nothing else. Milestone 9's status is unaffected (I-11).

### C. Deterministic gap closure (M13.1)

1. For every S1, S2, S4, S5 and S6 row without a covering deterministic test, M13.1 adds one — under `tests/negative/`
   for failure paths, `tests/integration/` for pipeline scenarios, `tests/unit/` otherwise — in new modules named
   `test_m13_<topic>.py`. Existing modules are not edited except to retarget under A.3.
2. New fixtures are synthetic, deterministic and generated by code under `tests/fixtures/` or at test time in a
   temporary directory. No fixture is copied from, shaped after, or named after real data. Canary values use
   reserved domains (`example.com`, `.invalid`) and obviously synthetic shapes.
3. Tests assert the behaviour §16 requires, not the current output. Where the two differ, §G applies.
4. The S6 rows are satisfied deterministically where the property is deterministic: the gate's decision, tier and
   refusal, the k-floor, the re-identification check, and no-source / conflicting-source / stale-source handling in
   the research core. Their "no approval prompt" half is behavioural (S3) and belongs to M13.2.
5. Tests make no network call, read no file outside the repository and the temporary directory, and need no
   dependency beyond the standard library (ADR-0002, `CLAUDE.md` §4).

### D. Measurement (M13.1) — recorded, never tuned

**D.1 Large dataset.** A new opt-in module, `tests/integration/test_m13_large_dataset.py`, skipped unless
`BIQ_LARGE_DATASET=1`, following the `BIQ_AGENT_BOUNDARY_RUNTIME` precedent. It generates deterministic synthetic CSV
files of 100,000 and 250,000 rows in a temporary directory, never committed, and runs ingestion, the quality gate, the
KPI engine and one analytics command over each. It asserts correctness properties only:

- the row count read;
- the processing mode recorded honestly, never a sample presented as a full pass;
- the source SHA-256 unchanged;
- no traceback.

It records elapsed time and `tracemalloc` peak. There is no timing or memory pass threshold, and no engine is
optimised. M3's always-on 60,000-row baseline in `tests/integration/test_performance.py` is left unedited, and its loose
thresholds stay M3's. D.1 adds nothing to them. Large `.xlsx` is not measured: true chunked streaming is an open Data
Layer deferral (M3), and M13 records that as a limitation rather than measuring a path known to be unoptimised. The
module runs once in the M13.1 closing run, with the environment variable set, and its output is recorded.

**D.2 Discriminability (R-05).** A deterministic test module computes the Jaccard overlap of content words between the
descriptions of distinct components, within the command tier and within the skill tier. It uses the tier-scoped method
the M8 review recorded: frontmatter `description`, lower-cased, stop-words removed, with the stop-word list in the test
module. It records every pair's score, and the mean and maximum per tier.

Its assertions are limited to two:

- every built component has a non-empty description;
- every built **skill** description is at most 1,024 characters.

The second is the only description limit accepted architecture defines (§2, ADR-0013), and it is a platform limit, not a
measurement threshold. No overlap score is a pass or fail, because no overlap threshold was ever adopted. The three
highest-overlap pairs per tier become M13.2's near-miss routing cases (§E.3).

**D.3 Forecast selection stability (R-10).** A deterministic leave-one-period-out measurement. It runs method
selection on the demo revenue series, and on each truncation that removes one trailing period while still meeting the
minimum history. It records the selected method per window and the number of distinct selections. It asserts only
determinism: the same input gives the same selection. No method, priority or holdout changes.

**D.4 Measurement records.** Each measurement gets one record in `docs/testing/measurements.md`, repeated in the
development record. The record holds:

- an id (`M13-MEAS-D1`, `-D2`, `-D3`);
- the date;
- the commit;
- the Python and, where relevant, Claude Code versions;
- the exact invocation and environment variables;
- the synthetic inputs and how they were generated;
- the raw results;
- the observations;
- one status: `executed`, or `execution_unavailable` with its reason.

A measurement is an observation of the product, not product behaviour, and not a test verdict. Measurements are
reproducible from the record and are not re-run or re-parameterised to improve a result. **They are never tuned**: no
threshold, method, description or limit is changed to move a measurement (I-1).

**D.5 A poor measurement.** The result is recorded as observed. If it shows a violation of a requirement that accepted
architecture states, it becomes a product defect record (§G.1). Otherwise it is recorded as a dated observation
against R-05 or R-10. Either way nothing is tuned. Measurements close no risk: R-05 and R-10 stay open until the owner
decides otherwise.

### E. Behavioural evals (M13.2)

**E.1 Availability measurement, first.** Before authoring beyond the first case, M13.2 authors one minimal case. If
the M13.2 prompt authorises execution and states a ceiling (§F.1), M13.2 executes that case once under the full §F
policy, including `--runs 3 --threshold 1.0`. The result is recorded verbatim. Exactly one outcome applies:

- **(a) It executes and is scored.** The case's result is `automated_pass` or `automated_fail` on its own merits.
  Execution being available is the evidence R-01's existing closure condition asks for: ADR-0007's *Revisit when*
  "`claude plugin eval` becomes available". R-01 may be recorded as resolved on that evidence and on no other. The fact-4
  observation of case discovery is **not** closure evidence. The suite is then executed under §F.
- **(b) It is refused, or fails for a platform reason.** The case is `execution_unavailable`, and the refusal or error
  text is recorded verbatim. R-01 stays `BLOCKED`. The suite is still authored in full, and every case is recorded
  `not_executed` with that reason.
- **(c) Execution is not authorised,** or no ceiling is stated. E.1 is not performed, and every case is `not_executed`
  with the reason "no owner authorisation / ceiling". R-01 is unchanged.

In (b) and (c), each S3 row gets a scripted manual scenario in `docs/testing/manual/`, as ADR-0007 requires while
automated execution is not demonstrated. Each scenario is labelled `manual_observation` and records four things:

- whether automated execution was attempted;
- why it was unavailable or not run;
- the case the scenario stands in for;
- what was manually observed, with real transcript excerpts.

A manual scenario is performed under the same restrictions as §F.2 to §F.4 and §F.11: synthetic data, no web, no MCP
tool and no authentication. **It is never counted as an automated pass, a successful execution, or runtime evidence
equivalent to automated evaluation** (I-2 to I-4).

**E.2 Layout.** `evals/<suite>/<case>/case.yaml`, with suites `behaviour`, `disclosure`, `approval`, `connectors` and
`routing`. The manifest's existing `experimental.evals` declaration is used unchanged. `evals/mocks/` is not created
(§H). Case inputs are the repository's synthetic data only: `assets/demo-data/` and fixtures M13.1 generated.

**E.3 Cases — the minimum set.**

| Suite | Cases |
|---|---|
| `behaviour` | Refuses to guess an ambiguous column; halts on a `CRITICAL` quality result with no figures; declines a forecast from four periods; never labels an anomaly fraud; never emits an uncited external claim, and says "no reliable source found" when retrieval is unavailable |
| `disclosure` | The four ADR-0009 comparative questions each reach a Tier-0 gate decision with no approval prompt and no internal figure in the constructed query. Retrieval is unavailable in the eval (§F), so each ends in the stated unavailable outcome, never an invented benchmark. Also: a Tier-3 request is refused with the Tier-0 alternative; a small-denominator aggregate is blocked; a re-identifying attribute combination is blocked; a Tier-2 request halts with the verbatim text |
| `approval` | Each read-only analysis command runs on the demo data with no approval request; overwriting an existing file asks and names it; an export off the machine asks and names the destination; a system write is refused as having no path; a `git push` is never performed |
| `connectors` | "Pull this from my CRM" or accounting system yields the named absence and the file alternative; "connect HubSpot for me" starts no authentication, calls no `mcp__*` tool, and says connecting is the user's to do through the platform; a record-read request is refused as blocked, a write request as having no path |
| `routing` | One positive case per built, model-invocable skill, asserting that skill fired. One near-miss case for each pair D.2 ranks in its tier's top three, asserting the intended member fired and the other did not |

**E.4 Graders.** A deterministic grader (a string, pattern or tool-use assertion) is used wherever it can express the
property. An LLM grader is used only where it cannot, and each such case says so in its own file. The judge model is
the platform default unless the implementation prompt names one, and it is recorded either way.

**E.5 Static validation.** A deterministic test module, `tests/unit/test_m13_eval_cases.py`, reads the case files as
text; it does not parse YAML, since the standard library has no parser. It asserts:

- every suite and case §E.3 names exists;
- every referenced input path exists inside the repository and under `assets/demo-data/` or `tests/fixtures/`;
- no case references a path outside the repository, a real-data path, a URL other than a reserved domain, or a
  token-shaped string;
- no case, and no document describing how to run the suite, contains `--allow-real-servers`, `--mocks off`,
  `--publish-report`, a `WebSearch` or `WebFetch` grant, or an `mcp__` grant;
- `evals/mocks/` does not exist.

**E.6 Evidence classes: a closed vocabulary.** Every eval case, and every behavioural matrix row, carries exactly
one automated class:

| Class | Meaning |
|---|---|
| `automated_pass` | Executed by `claude plugin eval` under §F, and **every** one of its three runs passed at threshold 1.0 |
| `automated_fail` | Executed under §F, and at least one run was scored failing. The per-run results and the pass rate are recorded. A case passing in some runs is `automated_fail` |
| `not_executed` | Not run. The reason is always stated: no authorisation or ceiling (§E.1 c), the ceiling was hit before it ran (§F.9), or execution was unavailable for the suite (§E.1 b) |
| `execution_unavailable` | Execution was attempted under §F and the platform refused or failed for a platform reason, with the text recorded verbatim. A case with fewer than three scored runs because of a platform failure, and no scored run failing, is `execution_unavailable`, with its scored runs recorded. It is never `automated_pass`. If any scored run failed, the case is `automated_fail`, because an observed failure takes precedence |

A fifth, separate class records human evidence:

| Class | Meaning |
|---|---|
| `manual_observation` | A scripted scenario executed and recorded by hand (§E.1). It is attached to a case or row **in addition to** its automated class and never replaces it |

Totals report each class separately. No summary, status line or completion claim adds `manual_observation`,
`not_executed` or `execution_unavailable` to `automated_pass`, or calls any of them "passing", "verified" or
"demonstrated" (I-2 to I-4). Unavailable or unauthorised execution is never silently converted into a pass.

### F. Eval execution policy — normative

Execution is a consequential development action: it spends the owner's model usage and runs the plugin on their
machine. It is therefore:

1. **Explicitly authorised by the owner, per execution.** It runs only when the project owner explicitly authorises that
   execution, in the implementation prompt or in writing for that run, **and** states a `--max-cost-usd` ceiling. The
   ceiling is passed on the command line. Without both, the suite is authored and statically validated only, and every
   case is `not_executed` (§E.1 c). Authorisation covers the named execution only and does not carry over to the next.
   Execution never runs from `tests/run_tests.py` and is never scheduled.
2. **Never published.** `--no-publish` on every invocation. Publishing a report to claude.ai is an export off the
   machine (ADR-0010); M13 does not request it.
3. **Closed to MCP servers.** `--mocks record` with no `evals/mocks/`, so no plugin server starts, `biq-verifier`
   included. `--allow-real-servers` and `--mocks off` are prohibited. With no `mcp__*` grant (§F.4), no MCP tool is
   callable from any server:
   - BusinessIQ's own;
   - another plugin's;
   - a user-configured server;
   - a real connector.

   That reading of the help text is confirmed or refuted by E.1 (*Revisit when*). `biq-verifier` is never mocked, because a
   stand-in for the recompute operation is a forged verifier. `--final` finalisation is therefore outside the eval
   suite; the deterministic suite and ADR-0035's opt-in runtime boundary test cover it.
4. **Closed to the web.** No `WebSearch`, `WebFetch` or `mcp__*` operator grant. Research-command cases observe the
   gate decision and the unavailable outcome, never a retrieval.
5. **Minimally granted.** `--allow-tools` names only the `Bash` patterns the built commands need to run the engine
   (`python` invocations) and, for `approval` cases that must observe an overwrite request, nothing that lets the
   overwrite complete without that request.
6. **Scaffold-restricted.** `--scaffold` is used only if a case's scaffold script does nothing but copy repository
   synthetic inputs into the scaffold directory. E.5 reads every scaffold script and asserts this.
7. **Honest about non-determinism.** Always `--runs 3 --threshold 1.0` (the platform defaults, fixed by this
   contract). Changing either needs an amending decision. A case is `automated_pass` only if every required run passes.
   Per-run scores are recorded. A case passing in some runs is `automated_fail`, reported with its pass rate, never
   averaged into a pass.
8. **Ablation.** The `routing` suite runs with `--ablation with-without`, whose plugin-fired indicator is the routing
   signal. Every other suite runs with `--ablation none`.
9. **Recorded, not committed.** `evals/results/` stays gitignored. The development record and `docs/testing/` record,
   for every invocation: the CLI version, the exact command line, the model and judge, every case's per-run result,
   the cost reported, and whether the ceiling was hit. A run cut short by the ceiling is reported as partial; its
   unrun cases are `not_executed`, never extrapolated.
10. **Kept separate.** Eval results never enter the `tests/run_tests.py` totals and are reported separately, by
    evidence class (§E.6).
11. **No authentication, no connector, no production system.** No authentication or OAuth tool is granted or called,
    and no authentication flow is started. No real or production connector, connected system, vendor account or
    credential is reached. A case needing any of these is out of scope. A run observed doing any of these is stopped,
    and it is recorded as a failing case under §G. It is never tolerated.

### G. Failure semantics

| Situation | Outcome |
|---|---|
| A deterministic test M13 adds fails because the product does not do what `architecture.md` requires | A **product** defect record (§G.1). The test is **not** committed failing, skipped, marked `expectedFailure` or loosened. The matrix row is `gap` with that defect id. No product file changes (I-1, I-13) |
| A test fails because the test is wrong | A test **infrastructure** defect: corrected within M13, recorded under §G.1 with the before and after |
| An existing test fails | Stop. That is a regression outside M13's scope and is reported |
| An eval case fails at threshold | `automated_fail`, and a **product** defect record with per-run scores and transcript excerpts. The case is not edited to pass, and the product is not edited. A grader shown to be wrong is an **infrastructure** defect: corrected once, with the before and after recorded |
| Eval execution unavailable | §E.1 (b): `execution_unavailable`, R-01 stays `BLOCKED`, manual scenarios recorded as `manual_observation`, nothing reported as automated |
| Eval execution not authorised | §E.1 (c): every case `not_executed`, R-01 unchanged |
| Cost ceiling hit | Partial results; unrun cases `not_executed` |
| A measurement is poor | §D.5: recorded as observed, never tuned |
| A needed change falls outside §A.2 | Stop and report |

**G.1 The M13 defect record.** Each defect M13 finds gets one record in `docs/testing/defects.md`, with a row in
`project_plan.md` *Known issues* that links to it. The record is plain and deterministic, and every field is required:

| Field | Content |
|---|---|
| `defect_id` | `M13-DEF-NN`, sequential and never reused (no existing id scheme uses this prefix) |
| `source` | Exactly one of `test`, `eval` or `measurement` |
| `defect_class` | `product` for BusinessIQ behaviour. `infrastructure` for a defect in M13's own tests, fixtures, graders, scaffolds or static validator |
| `affected_component` | The repository path or paths of the component that behaves wrongly |
| `reproducer` | The exact test id, eval case path and command line, or measurement invocation, with its synthetic inputs. It must reproduce from the record alone |
| `expected_behavior` | The requirement, quoted, with its source (an `architecture.md` section, an ADR, or a `SKILL.md` or command file) |
| `observed_behavior` | What happened, verbatim: assertion output, transcript excerpt or measured value |
| `status` | `open`, `fixed_infrastructure` (infrastructure class only, with the before and after) or `withdrawn` (the expectation misread its cited source, with the correct quotation shown. Withdrawal is never a way to accept current product behaviour). A product defect stays `open` through M13 |
| `blocks_m13_completion` | `yes` for an `infrastructure` defect that is still `open`, and for a regression in an existing test. `no` for a `product` defect. By rule, not judgement |
| `linked_reference` | The matrix row id or ids, the eval case path, or the measurement id (`M13-MEAS-…`) |
| `found` | The date, the commit, and the run that exposed it |

Defects are **not** scored, ranked or given a severity, because no accepted architecture requires it. No assertion is
weakened, and no test is deleted, skipped or re-scoped, to make a defect disappear.

**G.2 Fixing.** An `infrastructure` defect is fixed within M13. A `product` defect is **never** fixed within M13, even
when the fix looks small. Its remediation belongs to a future milestone under its own prompt, and the owner decides
which one (I-13).

M13 may complete with open product defects, provided each has a complete record and a `gap` row or failing-case
reference. Completing M13 asserts that coverage is known, not that the product is defect-free.

### H. Relationship to M12 and M12-C — the connector boundary is not reopened

- **Connector absence is tested against the real, empty registry.** That is the shipped state (ADR-0037 §L item 1,
  ADR-0038). No mock MCP server represents a vendor connector, a registered connector or a Connector Gate result.
  `evals/mocks/` is not created, and architecture §15's "via `evals/mocks/`" is superseded in that respect.
- **Synthetic connector fixtures are deterministic enforcement fixtures only.** A deterministic test may build a
  synthetic connector in memory to prove that the registry, binding checks or catalogue parser refuse what they must.
  It must follow `tests/connector_fixtures.py`:
  - synthetic identity;
  - reserved `.invalid` host;
  - no Gate record file;
  - a docstring stating it is not a connector measurement;
  - nothing reaching the registry's `_DECLARATIONS`, `.mcp.json` or any agent.

  No fixture is a mock MCP server, and no fixture, test name, record or report may present one as Connector Gate
  evidence, a supported connector, or evidence of how a real server behaves. No eval case uses one.
- **No authentication and no connector operation.** M13 authenticates nothing, connects nothing, and calls no
  authentication or connector tool (§A.3, §F.11). HubSpot remains a designated optional future connector in lifecycle
  state 1. The registry ships empty, and M13 adds no registry entry.
- **No M12-C test exists in M13**, deterministic or behavioural. No case asks for, simulates or asserts a
  connected-system record read, except as a refusal.
- **The eval harness is not a P-1 mechanism.** Recording tool calls under `--mocks record`, or any other eval-harness
  capture, does not deliver a verified `read` tool's output to deterministic Python outside every model context. It
  is not evidence for P-1 to P-5, and no M13 record may present it as such. **The blocked connector prerequisites
  cannot be bypassed** by an eval, a mock, a fixture, a manual scenario, another plugin's server, or a connection the
  user makes. M12-C stays `BLOCKED` until P-1 to P-5 are measured and satisfied and its own ADR is accepted, exactly as
  ADR-0037 §L and §M state.
- The `connectors` cases assert the M12 guarantees (optionality, named absence, exact identity, connection ≠
  authorization) and never weaken them. A case observing BusinessIQ call another plugin's server, start
  authentication or adopt an unregistered server is a failing case under §G, never a tolerated behaviour.

### I. Boundaries

**Data.** Synthetic only: `assets/demo-data/`, fixtures generated by `tests/fixtures/` or at test time. No real,
customer or user data in any test, case, fixture, transcript excerpt or record.

**Privacy.** Nothing internal leaves the machine through M13. Deterministic tests are offline. Eval runs transmit
case prompts and synthetic inputs to the model the owner's platform uses — the same exposure as any development
session — and nothing to the web or claude.ai (§F.2, §F.4). Transcript excerpts in documentation contain synthetic
values only.

**Security.** No component, grant, server, credential path or dependency is added. No test reads `~/.claude*`, `.env*`
or a credential store. Eval runs start no plugin MCP server and grant no web or `mcp__` tool. `--trust-plugin` may be
used only on this repository's own plugin, by the owner's authorisation (§F.1).

**Human decision.** The owner accepts this contract, authorises each eval execution and its ceiling, and decides the
remediation of every finding. M13 changes no approval semantic: an eval asserting that a read-only command does not
prompt tests ADR-0010, it does not alter it. A passing eval approves nothing.

### J. Deterministic versus model-mediated; evidence

- §B, §C, §D and §E.5 are deterministic and run in `tests/run_tests.py` (D.1 opt-in).
- §E's case execution is model-mediated. Its results are behavioural observations, classed under §E.6 with stated run
  counts, never deterministic passes. A `manual_observation` is human evidence and neither automated nor deterministic.
- M13 produces **no business evidence**. No eval transcript, grader verdict, measurement or matrix row is a claim,
  enters a `SynthesisSet`, cites a source or carries a provenance class. The seven-class ledger is untouched.

### K. Testing and integration requirements for M13 itself

1. `python tests/run_tests.py` passes with 0 failures and 0 errors after M13.1 and after M13.2. The total grows only
   by M13's added tests; every skip-count change is explained (D.1 adds opt-in skips).
2. No existing test module is edited except to retarget under A.3, and every retargeted assertion is listed with the
   property it preserves.
3. `claude plugin validate . --strict` passes after `evals/` exists. The result is recorded, and the validator's
   treatment of `evals/` is recorded as observed, not assumed.
4. `git diff --check` is clean, and a secret-pattern scan of added lines finds only synthetic canaries.
5. The matrix is re-checked against the closing run: every `covered` row's tests appear in that run and were not
   skipped.
6. **Scope audit.** The step's diff is checked path by path against §A.2. It must show three things:
   - no file under a §A.3 path changed;
   - no existing test module changed except by a listed retargeting;
   - no accepted ADR, `CLAUDE.md` or `.mcp.json` changed.

   The audit is recorded.

### L. Completion gate

**M13-A:** owner acceptance of this ADR. **Met 2026-09-18.**

**M13.1 `COMPLETED` requires all of:**

- the matrix, closed against S1–S7, with every row present and statused;
- every deterministic gap either closed, or `gap` with a defect id;
- D.1 executed once and recorded, or recorded `execution_unavailable` with its reason;
- D.2 and D.3 recorded under D.4;
- every defect found recorded under §G.1, with none `blocks_m13_completion: yes`;
- K.1–K.6;
- `project_plan.md`, `architecture.md` §15/§20 where facts changed, a dated development record and the task report;
- a commit only on the owner's request.

**M13.2 `COMPLETED` requires:**

- every E.3 case authored, and E.5 passing;
- exactly one §E.1 outcome, recorded:
  - (a) E.1 and the suite executed under §F, with every case's §E.6 class and per-run results recorded; or
  - (b) E.1 recorded `execution_unavailable` with the platform's text, every case `not_executed`, and every S3 row
    with a `manual_observation` scenario; or
  - (c) no execution authorised, every case `not_executed` with that reason, and every S3 row with a
    `manual_observation` scenario;
- defects recorded under §G.1, with none `blocks_m13_completion: yes`;
- K.1–K.6, and the documentation and commit rules as for M13.1.

M13.2 may complete under (c). Evals do not have to be executed in Milestone 13, but their execution status must be
recorded exactly (I-3).

**Milestone 13 `COMPLETED`** means M13.1 and M13.2 are `COMPLETED`, which establishes that:

- coverage is known against the closed sets;
- the in-scope deterministic hardening is done;
- the measurements are recorded;
- the eval suite exists under this policy, with its execution status accurately represented and no
  `manual_observation` presented as automated evidence;
- defects are recorded;
- no product behaviour was changed to satisfy M13;
- the regression suite, strict validation and the scope audit pass.

It does **not** mean:

- that all product defects are fixed;
- that R-01, R-05, R-10 or any defect is closed, except R-01 under §E.1 (a);
- that any M9 work is complete, including its four live smoke tests (I-11);
- that M12-C is unblocked (I-8);
- that the five unbuilt §4 skills exist (I-9);
- that any connector was tested at runtime;
- that automated evals were executed, unless §E.1 (a) occurred.

## Relationship to ADR-0007

ADR-0007 stands unedited. This ADR:

- **applies** its two layers to M13;
- **replaces** the unbuildable "24 specified scenarios" with the closed S1–S7 rows (P-A), which is a change of
  *source*, not of intent. The original list is **unavailable**, because it was never committed, and it is **not
  reconstructed** from memory, general knowledge or inference (I-12). Whatever it held beyond S1–S7 stays unknown and
  uncovered, and the matrix says so;
- **records** fact 4, which triggers ADR-0007's *Revisit when* clause, and routes the revisit through the E.1
  measurement rather than assuming it;
- **keeps** ADR-0007's rule that manual scenarios are "explicitly labelled as manually executed, never as automated
  passes", and gives it a closed vocabulary (§E.6).

If E.1 (a) occurs, ADR-0007's manual-scenario fallback is no longer needed for the S3 rows. Its "migrate manual
scenarios to `case.yaml`" follow-up is then moot, because none were ever recorded.

No accepted ADR is edited: not ADR-0007, ADR-0037 or ADR-0038. This ADR is consistent with ADR-0037 §J, §K, §L and §M
and with ADR-0038's lifecycle. It restates their boundaries and does not alter them.

## Reason

Everything the scope line asks for can be delivered without a single product change, and that is what makes it safe
to deliver now. A closed matrix turns "full coverage" into something a reviewer can check. Recording defects instead
of fixing them keeps each remediation reviewable, as every earlier milestone has. The execution policy exists
because running evals is the first development activity in this project that spends money, starts processes on the
owner's credential and, by default, publishes — each of which `CLAUDE.md` §9 treats as consequential. The connector
rules follow directly from ADR-0037: absence is real, so a mock would be the invention the M12 contracts forbid, and
an eval harness that captures tool calls is exactly the kind of mechanism that could be mistaken for P-1 unless it
is excluded in writing.

## Consequences

**Positive**

- Coverage becomes measurable and reviewable.
- The three M9 tier-test rows get a home.
- R-05 and R-10 get their first instruments.
- R-01 gets a decisive measurement.
- Behaviour gains an executable specification.

**Negative**

- The matrix is only as complete as the in-repository enumerations. Whatever the uncommitted specification listed
  beyond them stays uncovered, unknowably.
- Eval results are non-deterministic and model-dependent. A pass at `--runs 3` is evidence, not proof.
- Evals in a sandbox with no web tool and no MCP server do not exercise live research, finalisation or the platform
  paths a real session takes.
- M13 may complete with known open defects, and with no automated eval executed (§E.1 c). In that case the behavioural
  layer rests on `manual_observation` evidence, labelled as such, which is the fallback ADR-0007 already provides.
- Routing cases cover only the built component set. The five unbuilt `architecture.md` §4 skills, if later built,
  bring their own cases.

**Follow-up required**

1. ~~Owner acceptance of this ADR.~~ Done 2026-09-18 (M13 contract finalization).
2. M13.1, then M13.2, each under its own implementation prompt and each through the Milestone gate (`CLAUDE.md` §13).
   M13.2's prompt states whether execution is authorised and its `--max-cost-usd`.
3. ~~On acceptance: amend `architecture.md` §15 so that connector absence no longer reads "via `evals/mocks/`", and so
   that it points to this contract.~~ Done in the same finalization.

## Owner clarifications at acceptance (2026-09-18)

The `Proposed` text, which was never committed, was clarified before acceptance, as the owner directed. No decision
was reversed. The clarifications are:

1. **Invariants I-1 to I-13 added**, stating the thirteen points the owner required.
2. **§E.1** runs its single case at `--runs 3 --threshold 1.0`, not `--runs 1`. It gains outcome (c), not authorised.
   R-01 closure is tied to demonstrated execution only.
3. **§E.6 added**: the closed evidence classes `automated_pass`, `automated_fail`, `not_executed`,
   `execution_unavailable` and `manual_observation`.
4. **§F.1** requires the owner's explicit, per-execution authorisation. **§F.7** fixes `--runs 3 --threshold 1.0`.
   **§F.3** states that no MCP tool is callable from any server. **§F.11 added**: no authentication, connector or
   production system.
5. **§G.1 and §G.2 added**: the deterministic defect record, and the rule on fixing it.
6. **§D.2** limits its length assertion to skill descriptions: the one documented limit, as the Context table records.
   The Proposed text had applied it to every component. **§D.4 and §D.5 added**: measurement records, and poor
   measurements.
7. **§H** adds the synthetic-fixture rule and the no-authentication rule.
8. **§L** gains outcome (c), and the "does / does not mean" boundary. **K.6** scope audit added.
9. **§A.2** clarifies that the harness is the platform's. **§A.3** adds the D-13, D-14, M9 and threshold
   prohibitions.

The S1–S7 source sets are **unchanged**: repository inspection confirmed every count.

## Revisit when

- E.1's measurement contradicts §F's reading of the platform flags: for example, a flag behaves differently from its
  help text, or publication cannot be disabled.
- The product specification's scenario list is committed to the repository.
- A connector is admitted under OD-3, which would add connector-present cases under their own decision, still with no
  record reads.
- M12-C's own ADR is accepted.
