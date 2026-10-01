# 2026-09-18 — Post-M12-B roadmap reconciliation and next-milestone contract gate

**Milestone:** Roadmap gate after Milestone 12 (M12 closure under OD-1) and M13-A (the Milestone 13 contract)
**Status on completion:** REVIEW (DECISION ONLY). ADR-0039 is `Proposed`. M12 is `COMPLETED` under OD-1, with M12-C
`BLOCKED`. M13 stays `PLANNED`. Nothing is committed.
**Supersedes:** None. `2026-09-18-m12-b-connector-registry.md` keeps its historical `REVIEW` status line unedited;
this record supplies the later approval and closure.

## 1. Prompt / task performed

An architecture and roadmap gate after the M12-B checkpoint, run in a fresh session. The prompt asked for:

- baseline verification;
- reconciliation of documentation that still described the checkpointed and approved M12-B as awaiting review;
- M12-C kept `BLOCKED`;
- one next buildable milestone, determined from the repository's accepted architecture and actual state;
- a contract ADR only if that milestone needs a new decision;
- validation.

The prompt ruled out:

- implementation, tests, commands, skills and agents;
- `.mcp.json` changes;
- edits to accepted ADRs or historical records;
- authentication and Connector Gate measurement;
- a commit or push.

## 2. Objective

Leave the repository in a clean, reviewable architectural state:

- current-status documents agree with what was approved and checkpointed;
- the next buildable milestone is identified on evidence;
- that milestone has a contract specific enough to write its implementation prompt without ordinary option questions.

## 3. Changes made

1. **Baseline.**
   - `git status --short --branch`: `## main...origin/main`, clean.
   - After `git fetch origin`, `HEAD` = `origin/main` = `990e88d5f13db65b2ecdf0737c7f613b83c6034d`.
   - Full suite: **4,684 tests, 0 failures, 0 errors, 26 skipped**, identical to the last known result.
2. **Reading.** Read in full:
   - `CLAUDE.md`, `CONNECTORS.md`, `docs/README.md`, `docs/decisions/README.md`, `docs/integrations/README.md`,
     `docs/testing/README.md`;
   - ADR-0007;
   - ADR-0037's decision, §J, §K, §L, §M and *Relationship to ADR-0004*;
   - ADR-0038's header and context;
   - the relevant ADR-0009 sections.

   Read by section:
   - `architecture.md` §1–§4 and §8–§20;
   - `project_plan.md`: summary, M9, M10 (headings and the Executive Report rows), M11, M12, M13, M14, *Known issues*,
     *Documentation debt*;
   - `README.md` (status paragraphs);
   - the M12-B development record's status lines and verification method.

   Inspected:
   - the repository tree;
   - `.mcp.json`, `plugin.json` and `.gitignore`;
   - the `skills/`, `commands/` and `agents/` inventories;
   - the test layout;
   - `git log`.
3. **Status cross-check** (§10 lists what disagreed).
4. **One platform measurement** relevant to M13 (§8): `claude plugin eval` availability on the installed CLI.
5. **Next-milestone determination** (§11) and **ADR-0039** written as `Proposed`.
6. **Documentation reconciliation** (§14).
7. **Validation** (§8, §9).

## 4. Files created

- `docs/decisions/ADR-0039-m13-test-hardening-and-evals-contract.md`
- `docs/development/2026-09-18-post-m12b-roadmap-gate.md` (this record)

## 5. Files modified

- `project_plan.md`:
  - header: current phase and next gate;
  - summary rows M9, M10, M12, M13;
  - M10 heading plus a reconciliation note;
  - M12 heading plus a closure paragraph;
  - M12-B sub-milestone row, heading and §L items 8 and 9;
  - the M13 section, adding M13-A with contract and sub-milestone tables;
  - R-01 re-observation;
  - new debt rows D-13 and D-14.
- `CONNECTORS.md` — the status paragraph: M12-B reviewed, approved and checkpointed; M12 complete under OD-1; M12-C
  blocked.
- `architecture.md`:
  - §15: R-01 re-observation, plus a pointer paragraph for the proposed M13 contract;
  - §19: ADR-0039 row, **Proposed**;
  - §20 item 1: R-01 re-observation.
- `docs/decisions/README.md` — index row 0039 (**Proposed**).
- `docs/README.md` — ADR list entry 0039 (proposed).

## 6. Files deleted

None in the repository. The throwaway eval probe directory in the session scratchpad (§8) was deleted after use.

## 7. Features implemented

None. This is a decision-only gate.

## 8. Tests performed

- `git status --short --branch`
- `git fetch origin`
- `git rev-parse HEAD origin/main`
- `python tests/run_tests.py` — at baseline, and again on the finished tree.
- **Platform measurement (not a test of BusinessIQ).**
  - Ran `claude --version` and `claude plugin eval --help`.
  - Then ran a zero-case probe: a throwaway plugin in the session scratchpad with only `.claude-plugin/plugin.json` and
    an empty `evals/`, run as `claude plugin eval . --trust-plugin --no-publish --runs 1 --max-cost-usd 0.01`.
  - The probe was never run against this repository, ran no case, called no model, published nothing, and was deleted.
- `claude plugin validate . --strict`
- `git diff --check`
- **Secret-pattern scan** of every added line in the diff and of the two new files, for token-shaped values:
  - AWS, GitHub, Slack, `sk-`-style keys, HubSpot private-app tokens;
  - JWTs, bearer strings, private keys;
  - key, secret, password and token assignments;
  - long hex strings, emails, URLs and connection strings.
- **Immutability checks:**
  - every accepted ADR (0001–0038): working-tree blob hash compared with `HEAD:`;
  - `.mcp.json`, `CLAUDE.md`, the M12-B development record, `lib/`, `skills/`, `commands/`, `agents/`, `tests/`,
    `reference/`, `config/`, `assets/`, `.claude-plugin/` and `.gitignore`: no diff.

## 9. Test results

**Baseline** (at `990e88d`, before any change):

```
Ran 4684 tests in 278.889s
OK (skipped=26)
ran 4684 | failures 0 | errors 0 | skipped 26
```

**Finished tree:** recorded in §17.

**Eval probe** (Claude Code **2.1.276**):

```
No eval cases found under …\scratchpad\evalprobe.
Cases are expected in a evals/ directory under …\scratchpad\evalprobe (the default), each case a directory
containing case.yaml or prompt.md.
Run `claude plugin eval init` for a guided interview, or `claude plugin eval init --bare <name>` to scaffold a blank case.
EXIT=1
```

What this shows, and what it does not:

- ADR-0007 recorded that on 2026-09-08 both `claude plugin eval` and `claude plugin eval init` exited with "plugin
  eval is currently in early access".
- On 2.1.276 that refusal did **not** appear at case discovery.
- This does **not** show that a case executes. R-01 is therefore annotated, not closed.
- ADR-0039 §E.1 makes executing one case the first step of M13.2.

`--help` also established three facts that ADR-0039 §F is built on:

- the report is **published to claude.ai by default**;
- each run is a full child session on the owner's credential;
- under the default `--mocks record`, a plugin MCP server with no mock is not started.

## 10. Issues discovered

**Status disagreements (current-status documents versus accepted decisions and the checkpoint):**

| Where | Said | Fact | Handled |
|---|---|---|---|
| `project_plan.md` M12 summary row, M12 heading, M12-B row and heading, §L items 8 and 9 | M12-B `REVIEW — SECURITY/ARCHITECTURE REVIEW`, "uncommitted, awaiting owner approval"; M12 `IN PROGRESS` | M12-B was approved and checkpointed as `990e88d` (prompt; `git log`). Under ADR-0037 §L and OD-1, M12 is `COMPLETED` with M12-C `BLOCKED` | Reconciled |
| `CONNECTORS.md` status paragraph | M12-B "under security and architecture review" | As above | Reconciled |
| `project_plan.md` header | "Current phase: Milestone 9 … Next gate: Milestone 9-D", dated 2026-09-13 | M9-D, M10, M11 and M12 have all happened since | Replaced |
| `project_plan.md` M10 summary row and heading | `IN PROGRESS (10.1 done)` | M10.1 through M10.3.4 are all `COMPLETED` in their own rows and were each checkpointed (`62580f3` to `4dc6562`) | Reconciled to `COMPLETED`, with the basis stated. **Owner to confirm** (§15) |
| `project_plan.md` M9 summary row | `IN PROGRESS (9-A, 9-B done)` | 9-C and 9-D are built. The four external commands are `REVIEW`, pending owner-run fresh-session smokes. One skill row and three tier-test rows are `PLANNED` | Row corrected; M9 stays `IN PROGRESS` |
| `M12-B development record`, line 4 | `REVIEW … awaiting owner review` | Historical, true when written | **Not edited** (append-only); this record supersedes it for status |

**Findings recorded, not fixed:**

- **D-13** (owner decision). `architecture.md` §4 enumerates 20 skills. Five were never built or scheduled:
  `biq-business-context`, `biq-semantic-mapping`, `biq-data-quality`, `biq-kpi-engine` and `biq-external-research`.
  `biq-benchmark-comparison` (ADR-0029) is built but is not among the 20.
- **D-14** (Milestone 14). Stale current-status banners:
  - `README.md` says "Milestone 7 of 14" and lists the connector layer as not built;
  - `architecture.md`'s header says "Milestone 1 implemented";
  - `docs/README.md`'s history list stops at Milestone 7;
  - the ADR indexes miss 0017, 0018, 0023 and 0024 (extends D-11).

  These are left alone. A gate scoped to M12-B's review status that rewrote the README would exceed its brief.
- **R-01** re-observed (§9).
- **ADR-0007's coverage matrix was never produced.** The "24 specified scenarios" it maps come from the uncommitted
  product specification. ADR-0039 §B replaces the source with in-repository enumerations.

## 11. Decisions made

### The next buildable milestone: Milestone 13 — Test Hardening & Evals

Checked against the prompt's eight criteria:

1. **Planned.** It is the next milestone in `project_plan.md`, with a written scope. Several open items are already
   assigned to it:
   - R-05 routing ("routing eval cases, M13");
   - R-10 ("belongs to the M13 eval work");
   - R-01 eval execution;
   - ADR-0007's coverage-matrix follow-up;
   - the three `PLANNED` M9 tier-test rows, which are the behaviours architecture §15 assigns to Layer 2.
2. **Not completed.** No `evals/` directory, no coverage matrix, no M13 test module and no manual scenario exist.
3. **Needs nothing from M12-C.** Connector absence is the real, shipped state, and ADR-0039 §H forbids simulating
   anything else.
4. **Prerequisites met.** Its only dependency, M10, is `COMPLETED` (§10). Eval execution depends on a platform fact
   that can now be measured (§9).
5. **Clear purpose.** Make coverage checkable, and give ADR-0007's behavioural layer a real suite.
6. **Duplicates nothing.** Existing tests are per-milestone. No cross-cutting matrix, eval suite or large-dataset
   measurement exists.
7. **Invents no connector behaviour.**
8. **Reviewable.** It splits into M13.1 (deterministic) and M13.2 (behavioural).

**Why nothing else qualifies:**

- M9's open items are owner-run live smoke tests, not buildable work.
- M12-C is `BLOCKED`.
- M14 depends on M13.
- The five unbuilt §4 skills (D-13) are not scheduled by any milestone. Scheduling them would invent a roadmap item,
  which is an owner decision.

### Whether M13 needs a new contract: yes — ADR-0039, `Proposed`

M13 had only a one-line scope, and building it as written would:

- map coverage against a document the repository does not hold (P-A);
- mock a connector the product does not have (P-B);
- run evals that publish to claude.ai and spend on the owner's credential with no gate (P-C);
- leave "full coverage" undefined (P-D).

ADR-0039 decides the following:

| Area | Decision |
|---|---|
| Scope | Tests, fixtures, measurements, eval cases and test docs only. No product file changes |
| Coverage matrix | Closed sets S1–S7 |
| Deterministic gap closure | In new `test_m13_*` modules |
| Measurement | Opt-in `BIQ_LARGE_DATASET=1` (100k and 250k CSV rows, recorded only). R-05 Jaccard overlap and R-10 leave-one-out selection stability, recorded only |
| Evals | E.1 availability first. Five suites, with a minimum case set. Deterministic graders preferred. Static validation as a stdlib text test |
| Execution policy | Authorised per execution with a cost ceiling. `--no-publish`. `--mocks record` with no mocks. No real servers, web or `mcp__` grants. `--runs 3 --threshold 1.0`. Results gitignored |
| Failure semantics | Defects recorded with ids and reproducers, never fixed or masked |
| M12-C | No connector mock, no M12-C test, the eval harness is not a P-1 mechanism, and no bypass of P-1 to P-5 |
| Completion gates | M13.1, M13.2 and M13 |

**Accepted ADRs edited:** none. ADR-0039 applies ADR-0007 and does not amend it.

## 12. Architecture changes

None decided; ADR-0039 is only proposed. `architecture.md` gained:

- a dated re-observation of a platform fact (§15, §20);
- a pointer to the proposed contract (§15);
- the §19 row, marked Proposed.

The §15 text that ADR-0039 would amend ("via `evals/mocks/`") is deliberately unchanged until acceptance, as the
M12-A precedent did.

## 13. Project-plan updates

- **M10:** `IN PROGRESS` → `COMPLETED` (reconciliation).
- **M12:** `IN PROGRESS` → `COMPLETED` under OD-1.
- **M12-B:** `REVIEW — SECURITY/ARCHITECTURE REVIEW` → `COMPLETED`, with §L items 8 and 9 → `COMPLETED`.
- **M12-C:** unchanged, `BLOCKED`.
- **M13:** stays `PLANNED`, with M13-A `REVIEW (DECISION ONLY)`, and M13.1 and M13.2 `PLANNED`.
- **M9:** stays `IN PROGRESS`; its row is corrected.
- **Known issues and debt:** R-01 annotated; D-13 and D-14 added.

## 14. Documentation updates

As §5.

Not updated, deliberately:

- `README.md` (D-14);
- `docs/testing/README.md` (M13.1 creates the matrix);
- `docs/integrations/README.md` (already accurate: no connector admitted);
- `skills/biq-data-ingestion/SKILL.md` (no review wording);
- `CLAUDE.md`.

## 15. Remaining work

1. **Owner:** accept, amend or reject ADR-0039 (the Milestone gate, `CLAUDE.md` §13).
2. **Owner:** confirm the M10 `COMPLETED` reconciliation. It rests on every sub-milestone row and checkpoint, not on
   a recorded milestone-level approval.
3. **Owner:** D-13 — schedule or retire the five unbuilt §4 skills.
4. After acceptance: **M13.1** under its own implementation prompt; then **M13.2**, whose prompt states whether eval
   execution is authorised and its `--max-cost-usd`.
5. Unchanged and outside this gate:
   - M9's four fresh-session live smoke tests (owner-run);
   - M12-C (`BLOCKED` on P-1 to P-5 and its own ADR);
   - R-05, R-10, R-11 and R-12.

## 16. Git commit reference

N/A — nothing committed or pushed, as instructed. Branch `main`, base `990e88d`.

## 17. Final validation (finished tree)

- **Full suite:** `ran 4684 | failures 0 | errors 0 | skipped 26` — identical to baseline.
- **`claude plugin validate . --strict`:** passed.
- **`git diff --check`:** clean.
- **Secret scan:** no token-shaped values in added lines or new files.
- **Immutability:** ADR-0001 to ADR-0038, `.mcp.json`, `CLAUDE.md`, the M12-B record and every implementation
  directory are unchanged.

The exact output is in the task report for this gate.
