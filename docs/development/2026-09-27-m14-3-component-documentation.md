# 2026-09-27 — M14-3: component documentation and index reconciliation

**Milestone:** 14 — Documentation & Release
**Status on completion:** REVIEW — M14-3 is implemented and uncommitted, awaiting owner review and checkpoint
**Supersedes:** None. §10 corrects one finding of `2026-09-27-m14-2-readme-redesign.md` without editing that record

## 1. Prompt / task performed

The owner prompt was "M14-3 — Component documentation and index reconciliation". It asked for six things:

1. reconcile the stale skill and command indexes;
2. create useful per-component reference documentation where it is missing;
3. resolve the documentation part of D-13 from the actual repository;
4. distinguish implemented, internal, planned and unavailable components;
5. make documentation navigation consistent;
6. record the work under `CLAUDE.md` §11.

The following were excluded:

- `README.md`, `CLAUDE.md` and `architecture.md`;
- source, tests, schemas, manifests, hooks, `.mcp.json` and configuration;
- R-13, the `forecast.min_history_periods` fix, connectors and MCP;
- tagging, publication, evaluations, commit and push.

## 2. Objective

Make the component documentation describe the repository as it is: what ships, what is internal, what was designed
but not built, and why the design and shipped counts differ. Do this without inventing components or changing any
status.

**Starting checkpoint:**

- HEAD `5c1b15d535ba06fbf1daa0ab0c6e73a912b9047d` on `main` ("M14.2: redesign product README");
- `origin/main` at `595e91047e60e2439c511a309f4b6fe1ba2be2b0`;
- remote `github.com/conceptwebworld26/BusinessIQ`;
- working tree clean.

## 3. Changes made

### 3.1 Authoritative component inventory

Built from the files on disk and cross-checked against:

- the command, skill and agent frontmatter;
- `lib/python/biq/commands/registry.py`;
- `project_plan.md` and `architecture.md` §§1, 4, 10 and 13;
- `docs/testing/measurements.md` and `docs/testing/coverage-matrix.md`.

| Kind | On disk | Classification |
|---|---|---|
| Command files | 19 | 18 `USER_FACING`, 1 `INTERNAL_TEST_HARNESS` |
| Skills | 16 | 16 `SHIPPED/IMPLEMENTED`. None is internal or test-only, and none carries `user-invocable: false` |
| Subagents | 2 built | Plus 1 allocated and not built (`biq-data-profiler`) |
| Designed skills not shipped | 5 | `DESIGNED_NOT_SHIPPED`: 4 unscheduled, 1 `PLANNED` (unscheduled) |

These match the facts the M14-2 audit reported: 18 commands, 16 skills and 2 subagents.

### 3.2 Command reconciliation

- **User-facing (18):**
  - `/business-health`, `/sales-analysis`, `/customer-analysis`, `/product-analysis`, `/profitability-analysis`,
    `/cash-flow-analysis`, `/ask-business-data`;
  - `/revenue-forecast`, `/anomaly-detection`;
  - `/company-analysis`, `/market-analysis`, `/competitor-analysis`, `/industry-research`;
  - `/benchmark-comparison`;
  - `/swot-analysis`, `/strategy-analysis`, `/decision-support`, `/executive-report`.

  The first nine (the first two groups) are the `CommandSpec` declarations in the registry. The four research
  commands are `REVIEW` in the plan, with their live smoke tests outstanding.
- **Internal test harness (1):** `/retrieval-slice`. The evidence:
  - its frontmatter says "M9-B internal retrieval vertical slice / integration harness … answers no business
    question";
  - it carries `disable-model-invocation: true`;
  - `project_plan.md` (M9-B) calls it "an integration harness … not a research capability";
  - `measurements.md` excludes it from the model-invocable set;
  - coverage-matrix row S4-15 tests its negative path.

  It is classified in the index's *Internal* section, not hidden. The index also notes that it remains
  auto-discovered and can be typed by hand.
- **Development-only, planned or unimplemented commands:** none on disk.
- **Design count.** The `architecture.md` §1 diagram says "commands/ (17)". That is the Revision 2 design count, and
  it was never enumerated (D-06). §13 already records 19 files. There is no named command to map against, so there
  is no command-level discrepancy beyond the diagram's figure.
- **`docs/commands/README.md` before M14-3:**
  - it said "ten thin orchestrators" while its tables listed 15;
  - it omitted `/competitor-analysis`, `/industry-research` and `/benchmark-comparison` from every table;
  - it said "All four research commands are now built" with no plan status.

  All of this was rewritten. Arguments come from each command's `argument-hint` frontmatter, and purposes from each
  command's description and body.

### 3.3 Skill reconciliation

- **Shipped (16):**
  - data layer: `biq-data-ingestion`;
  - internal analytics: sales, customer, product, financial, forecasting, anomaly;
  - external intelligence: company, market, competitor, industry, `biq-benchmark-comparison`;
  - synthesis: `biq-swot`, `biq-strategy-recommendations`, `biq-decision-support`, `biq-executive-report`.
- **Designed, not shipped (5):**
  - `biq-business-context`, `biq-semantic-mapping`, `biq-data-quality` and `biq-kpi-engine`, all unscheduled;
  - `biq-external-research`, `PLANNED` and unscheduled.
- **Planned:** none beyond `biq-external-research`.
- **Internal or test-only:** none.
- **`docs/skills/README.md` before M14-3:** it said "Shipped so far — six skills", listed 11 of the 16 skills (it
  omitted the four research skills and `biq-benchmark-comparison`), and had no statement of the unbuilt design. It was rewritten by layer, with a
  designed-not-shipped section and the D-13 mapping.

### 3.4 Subagent inventory

| Agent | Purpose | Status |
|---|---|---|
| `biq-research-scout` | Retrieve and triage public sources for one entity. Tools: `WebSearch` and `WebFetch` only | Built (M9-B). **It had no `docs/agents/` page, a gap the M11 record noted.** M14-3 adds `docs/agents/biq-research-scout.md` |
| `biq-analysis-verifier` | Start the blind recomputation for `--final`. Its only tool is the one `recompute` MCP tool | Built (M11), with an existing page. Its runtime depends on the `biq-verifier` server (R-13) |
| `biq-data-profiler` | Model-mediated connector-catalogue exploration | Allocated by ADR-0006, deferred by ADR-0036, not built |

`docs/agents/README.md` said "Empty until Milestone 10" and listed only the verifier. It now lists all three with
their status.

### 3.5 D-13 reconciliation

`docs/skills/README.md` § *Design-to-shipped mapping (D-13)* maps each of the 20 skills in `architecture.md` §4 to
its shipped state, and adds `biq-benchmark-comparison`, which is outside the design.

**Result: 20 designed − 5 not shipped + 1 outside the design = 16 shipped.**

For each of the five unshipped skills, the page names where its work happens today. Each engine exists and runs
inside the commands:

| Skill | Engine |
|---|---|
| `biq-business-context` | `context/loader.py`, which reads and validates but never elicits or writes |
| `biq-semantic-mapping` | `mapping/semantic.py` |
| `biq-data-quality` | `quality/` |
| `biq-kpi-engine` | `kpi/` |
| `biq-external-research` | `research/` |

The prompt's "approximately 4 items" is **five** in the repository. D-13 has always recorded five, and the mapping
uses five.

- **Resolved:** the documentation part. The mapping exists, the counts are explained, and no unimplemented skill is
  shown as available.
- **Open:** the owner decision recorded in D-13 remains: schedule each of the five skills, or retire it by ADR.
  `architecture.md` §4 was **not** amended; it remains the designed set.
- **Not debt:** the two Revision 1 merges (`biq-connector-broker` and `biq-report-composer`) are recorded as
  historical.

### 3.6 Per-component documentation

The prompt asked to avoid 18 mechanical pages. The command files are already full specifications, and the
non-duplication rule (ADR-0012) forbids restating them. So the reference pages are **one per command family**.

Each page covers:

- purpose and when to use which command;
- inputs and outputs;
- important behaviour and limitations;
- evidence and provenance;
- examples, taken from the command files or using the shipped demo file names;
- approvals and related links.

| Page | Commands |
|---|---|
| `docs/commands/internal-analytics.md` | The 7 internal-analytics commands |
| `docs/commands/forecasting-and-anomalies.md` | `/revenue-forecast`, `/anomaly-detection` |
| `docs/commands/external-research.md` | The 4 research commands |
| `docs/commands/benchmark-comparison.md` | `/benchmark-comparison` (single-command family, so the `<command-name>.md` convention applies) |
| `docs/commands/synthesis-and-reporting.md` | The 4 synthesis commands |

Other decisions:

- **Skills.** No per-skill pages were created. Each `SKILL.md` is the skill's detailed reference, and the index says
  so. The `docs/README.md` directory map now states this convention, and the family-page convention for commands.
- **Agents.** One page was added (the scout), following the existing per-agent convention.
- **Internal harness.** It is documented only in the command index's *Internal* section. There is no reference page,
  because it is not a user component.

The forecasting page states the engine's **actual** minimum-history rule (see §10).

### 3.7 Navigation and link validation

- `docs/README.md` gained a *Component reference* section, and two corrected directory-map rows.
- No link in `docs/examples/README.md` or `docs/troubleshooting/README.md` was stale or broken, so neither was
  changed.
- All relative links and in-page anchors in the 11 changed or new `docs/` files were checked by script: **237
  links, 0 broken.**
- Stale-count scan across `docs/**/*.md`, excluding the append-only `development/`:
  - no remaining "six skills", "ten commands", "seven thin", "shipped so far" or "Empty until Milestone 10";
  - the "17 commands" and "20 skills" hits in ADR-0003 and ADR-0013 are historical decision text, and were preserved;
  - the "20 skills" hit in `docs/skills/README.md` is the intended design count, stated as such.

### 3.8 Governance (`project_plan.md`)

- **New entries:** a dated M14-3 bullet, and a new M14-3 row (`REVIEW`, uncommitted).
- **The M14 table's former "Per-component reference pages · worked examples · troubleshooting guide" row:** the
  reference-page part moved into M14-3. The remaining items are kept as `PLANNED`.
- **Updated:** the current-phase line, the next gate, the M14 summary row, and D-13 (documentation part reconciled,
  owner decision open).
- **Known issue R-14 added** (§10).
- **M14-2 checkpoint:** the current-phase line and the M14 summary row now record M14-2 as checkpointed `5c1b15d`.
  That is the HEAD this work started from, and both lines had to be rewritten to add M14-3.
- **Not changed:** the M14-1 and M14-2 table rows and their dated bullets still say "uncommitted". That stale wording
  is deliberately left for a separate reconciliation, as the prompt directs.

## 4. Files created

- `docs/commands/internal-analytics.md`
- `docs/commands/forecasting-and-anomalies.md`
- `docs/commands/external-research.md`
- `docs/commands/benchmark-comparison.md`
- `docs/commands/synthesis-and-reporting.md`
- `docs/agents/biq-research-scout.md`
- `docs/development/2026-09-27-m14-3-component-documentation.md` (this record)

## 5. Files modified

- `docs/commands/README.md`
- `docs/skills/README.md`
- `docs/agents/README.md`
- `docs/README.md`
- `project_plan.md`

## 6. Files deleted

None.

## 7. Features implemented

None. This is documentation only.

## 8. Tests performed

- `git diff --check`, plus a trailing-whitespace and tab scan of the new, untracked files;
- the relative link and anchor check over every changed `docs/` file;
- the stale-count scan (§3.7);
- `claude plugin validate . --strict`;
- `python3 tests/run_tests.py` (full regression);
- one engine check of the forecast minimum history, run through `commands.run('revenue-forecast', …)` on two
  synthetic CSVs of 8 and 12 periods, written only to the session scratchpad;
- the scope audit: `git status --short`, `git diff --stat` and `git diff --name-only`.

No repository test reads `docs/skills`, `docs/commands` or `docs/agents`, so no test needed to change.

## 9. Test results

- `git diff --check`: clean. The new files have no trailing whitespace or tabs.
- Links: 237 checked, 0 broken.
- Strict validation: `✔ Validation passed` (marketplace manifest).
- Full regression: `Ran 5286 tests in 566.938s` · `OK (skipped=31)` · `ran 5286 | failures 0 | errors 0 | skipped 31`, exit 0.
- Forecast minimum-history check:
  - 8 periods: revenue and gross profit both `insufficient data`, "Revenue has 8 periods of history; 12 are required
    before a forecast is produced".
  - 12 periods: forecast `available`.

## 10. Issues discovered

- **R-14: the M14-2 finding on `forecast.min_history_periods` was wrong.**
  - M14-2 §10 recorded the setting as unread by the forecast engine. In fact `forecast/engine.py`
    `forecast_series()` reads it (default 12) and returns `insufficient_data` below it, as the check in §9 confirms.
  - The approved `README.md` says that with fewer than six periods a method is still chosen and marked unvalidated.
    Under the default configuration that path is unreachable.
  - `commands/revenue-forecast.md` ("default 12 periods") is correct.
  - **Not fixed:** `README.md` is outside M14-3, and the M14-2 record is append-only. Recorded as Known issue R-14.
    The new forecasting reference page states the real rule.
  - The out-of-scope "fix `forecast.min_history_periods`" item from M14-2 §15 therefore needs re-framing. The setting
    is live, and the defect is in `README.md`'s description of it.
- **Stale text inside command files.** These are product surface, outside M14-3, and were not changed:
  - `commands/business-health.md` *Scope* says forecasting, anomaly detection, external research and benchmarking
    "do not exist yet";
  - `commands/cash-flow-analysis.md` says forecasting "arrives in a later milestone";
  - `commands/company-analysis.md`, `market-analysis.md` and `benchmark-comparison.md` point to
    `biq-strategy-recommendations` "(Milestone 10)" as if it were future.

  The reference pages describe the current state.
- **`CLAUDE.md` §3 inconsistencies.** These need an owner decision (D-07) and were not changed:
  - it still says "(20 skills)", where 16 ship;
  - it describes `plugin.json` as having "agents listed explicitly", while `architecture.md` §2 says agents must
    **not** be listed. The manifest correctly omits the key.
- **`architecture.md` §1 diagram** shows "commands/ (17)". This is a design-time figure (§3.2) and does not prevent
  accurate documentation, so architecture was not changed or escalated.
- **`docs/development/README.md`'s table** stops at M9-B, while `docs/README.md` says the directory itself is the
  complete index. This is outside M14-3's component scope, and was left unchanged.

## 11. Decisions made

- Command reference pages are organised **by family**, and skills keep `SKILL.md` as their detailed reference. Both
  conventions are stated in `docs/README.md`.
- No ADR was created. This is a documentation-organisation choice below the ADR bar in `docs/decisions/README.md`.

## 12. Architecture changes

None. `architecture.md` is unchanged.

## 13. Project-plan updates

As §3.8:

- M14-3 `REVIEW`, uncommitted;
- the D-13 documentation part reconciled, with the owner decision open;
- R-14 added;
- the M14 current-state lines record M14-2 as checkpointed `5c1b15d`.

## 14. Documentation updates

As §§4–5. No `docs/integrations/` page applies, because no connector is admitted.

## 15. Remaining work

- **Owner decision, D-13:** schedule or retire (by ADR) `biq-business-context`, `biq-semantic-mapping`,
  `biq-data-quality`, `biq-kpi-engine` and `biq-external-research`.
- **R-14:** correct `README.md`'s forecasting statement under its own owner prompt.
- **R-13:** the verifier launcher (`.mcp.json`), under its own owner prompt.
- **Command-file stale wording** (§10): a product-surface edit that needs its own prompt.
- **Owner decision, `CLAUDE.md` §3:** the skill count and the agents-in-manifest sentence (D-07).
- **Plan cleanup:** the M14-1 and M14-2 rows' "uncommitted" wording, and the stale `docs/development/README.md`
  table.
- **Later M14 items:** worked examples, the troubleshooting guide, the packaging observation, the token-cost
  measurement (D-10), and release tagging.

**Explicitly out of scope and not performed:**

- R-13;
- any `.mcp.json`, configuration, source, test, schema, manifest or hook change;
- the `forecast.min_history_periods` setting;
- connectors and MCP;
- tagging, marketplace publication and paid evaluations;
- any `README.md`, `CLAUDE.md` or `architecture.md` change.

## 16. Git commit reference

N/A. Nothing was staged, committed, amended, tagged or pushed. HEAD remains `5c1b15d` and `origin/main` remains
`595e910`.

## 17. Final reconciliation: R-14 (added 2026-09-27, after owner review of M14-3)

Sections 1–16 are kept as first written. This section records what followed them.

1. **Discovery.** M14-3's verification (§§9–10) found R-14. The M14-2 record had called
   `forecast.min_history_periods` unused, and the approved `README.md` said that a history shorter than six periods
   still produces an unvalidated forecast.
2. **The original statement was factually incorrect.**
3. **Actual behaviour, established from the repository:**
   - `lib/python/biq/forecast/engine.py` `forecast_series()` reads `forecast.min_history_periods`;
   - the shipped default is 12 (`config/businessiq.defaults.json`);
   - a shorter history returns an insufficient-data result and produces no forecast (8-period check, §9);
   - the value can be overridden through the configuration hierarchy in `lib/python/biq/config.py` (command, project,
     user, shipped defaults).
4. **Correction.** A separate, narrowly scoped, owner-approved documentation correction replaced that one `README.md`
   sub-bullet. It was replaced with the configured-minimum rule: 12 periods by default, and no forecast below it.
   No other `README.md` text changed.
5. **Validation:**
   - `git diff -- README.md` is limited to that bullet, with one line removed and three added;
   - `git diff --check` is clean;
   - `unit.test_manifest` and `negative.test_m12b_connector_security`, the tests that read `README.md`, pass
     (93 tests, OK).
6. **No production code or configuration changed.** The forecast engine needed no change.
7. **R-14 is resolved.** It is recorded as `Closed 2026-09-27 (M14-3 follow-up)` in `project_plan.md`
   *Known issues*, the same closed wording other entries in that table use. The R-14 items in §§10 and 15
   ("not fixed", "remaining work") are superseded by this section.
8. **M14-3 remains documentation-only,** and its status is unchanged: `REVIEW`, uncommitted, awaiting owner
   checkpoint. `README.md` joins the M14-3 working-tree scope as the R-14 correction.
