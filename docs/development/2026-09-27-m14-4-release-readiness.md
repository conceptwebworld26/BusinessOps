# 2026-09-27 — M14-4: release readiness and finalization

**Milestone:** 14 — Documentation & Release
**Status on completion:** REVIEW — M14-4 is implemented and uncommitted, awaiting owner review. M14 stays `IN PROGRESS`, and **OWNER RELEASE APPROVAL REQUIRED**
**Supersedes:** None

## 1. Prompt / task performed

The owner prompt was "M14-4 — Release Readiness and Finalization". It asked for eight things:

1. worked examples;
2. a troubleshooting guide;
3. final indexes and status;
4. release-relevant documentation fixes where safe;
5. the final token-cost measurement;
6. documented release limitations and owner decisions;
7. a release-gate report;
8. a readiness recommendation.

Also required: investigate R-13, D-10, D-14 and ADR-0042 follow-up 5.

Excluded: commit, amend, tag, push and publication; new product capability; invented versions; paid evaluations.

## 2. Objective and starting checkpoint

Leave BusinessIQ documented, measured and assessed for a release decision, without making that decision.

**Starting checkpoint:**

- HEAD `8e4ab17a8405a01542d71fb1731b4b42003dbe5d` ("M14.3: reconcile component documentation"), on `main`;
- `origin/main` at `595e91047e60e2439c511a309f4b6fe1ba2be2b0`;
- working tree clean, no stash.

## 3. Remaining M14 scope, as found

| Item | Status found | Classification | Result |
|---|---|---|---|
| Worked examples | `PLANNED` | IMPLEMENT NOW | Done (§5) |
| Troubleshooting guide | `PLANNED` | IMPLEMENT NOW | Done (§6) |
| D-14 stale status and indexes | Partly reconciled | IMPLEMENT NOW | Resolved (§9) |
| D-10 token measurement | Blocked on installing | IMPLEMENT NOW, once the session-only route was found | Measured (§8) |
| ADR-0042 follow-up 5 (packaging) | `PLANNED` | OWNER DECISION | Measured and documented (§10) |
| R-13 verifier launcher | Open | OWNER DECISION | Investigated; remediation identified, not applied (§7) |
| Documentation consistency | — | IMPLEMENT NOW, current-facing text only | Done (§11); product-surface findings R-15 and R-16 recorded |
| D-07 (`CLAUDE.md` §3) | Open | OWNER DECISION | Unchanged |
| D-13 (five designed skills) | Documentation reconciled | OWNER DECISION | Unchanged |
| M9 live smoke tests (4 research commands `REVIEW`) | Outstanding | OWNER DECISION (owner-run) | Unchanged |
| Open M13 product defects (M13-DEF-01, -03, -14, -15, -16) | Open | OWNER DECISION (remediation unassigned) | Unchanged |
| Release tagging | `PLANNED` | OWNER RELEASE APPROVAL REQUIRED | Not performed |

## 4. Work completed

**Files created:**

- `docs/development/2026-09-27-m14-4-release-readiness.md` (this record).

**Files rewritten** (each was a stub):

- `docs/examples/README.md`;
- `docs/troubleshooting/README.md`.

**Files modified:**

- `docs/development/README.md` (index completed);
- `docs/testing/README.md` (stale "early-access gated" sentence);
- `docs/architecture/README.md` (stale "Empty until Milestone 2");
- `README.md` (two documentation-table labels, "being written");
- `project_plan.md`.

No source, test, configuration, schema, manifest, hook, `.mcp.json`, command, skill, agent, reference, `CLAUDE.md`
or `architecture.md` file changed.

## 5. Worked examples

`docs/examples/README.md` holds nine examples:

1. business health;
2. a routed single question;
3. sales, product, customer and profitability depth;
4. cash-flow unavailability;
5. forecasting;
6. anomaly detection;
7. public research;
8. benchmark comparison;
9. the synthesis chain: SWOT, strategy, decision support and executive report.

It also has a provenance legend and a reproduction recipe.

**Where the numbers come from.** Every figure was produced by the engine on 2026-09-27 at `8e4ab17`. Each run used
`sh lib/biq_run.sh -c "commands.run(...)"` on `assets/demo-data/northwind_sales.csv`, with the demo Business Context.
The runs were made from a directory in the session scratchpad, so nothing was written to the repository. Examples:

- revenue £3,467,850.16 and gross margin 34.91%;
- the revenue forecast chose linear trend, with 10.94% MAPE and a base of GBP 1,491,165.59;
- 11 of 108 periods flagged as anomalies.

**No values shown for live examples.** The research and synthesis examples show the invocation and the output shape
only, because their output depends on live sources. No connector example exists, because none is available.

## 6. Troubleshooting guide

`docs/troubleshooting/README.md` gives symptom, cause, check, supported resolution and escalation for each of these:

- installing and loading, including name collisions and `/retrieval-slice`;
- the interpreter resolver, exit 78, `BIQ_PYTHON` and WSL (ADR-0045 and ADR-0046);
- the fail-closed write guard;
- file input and the Excel tiers;
- the `CRITICAL` quality halt and unconfirmed mappings;
- KPIs that are unavailable or not applicable;
- the R-15 and R-16 symptoms;
- forecasting: minimum history, unavailable targets, horizon cap, and the report outlook;
- anomalies: baseline minimum, sensitivity, and the fraud boundary;
- research: nothing citable, `not_authorised`, ambiguity, and the defects on record;
- connectors;
- approvals: the approval code flow and operations that are refused outright;
- Business Context;
- `--final` and R-13;
- developer validation, single-module tests, and M13-DEF-11.

Where the repository documents no workaround (R-13, R-16), the guide says so.

## 7. R-13: investigation and result

**Result: open, owner decision. Not fixed.**

- **Confirmed.** `.mcp.json` launches `biq-verifier` as `"command": "python"`, and this session's MCP connection
  failed with "Executable not found in $PATH: python". The engine (`lib/biq_run.sh`) and the hooks
  (`hooks/biq_guard.sh`) already resolve `python`, then `python3`, portably.
- **Portable remediation identified.** Declare the server as `sh` with `${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh`, using
  a launcher entry mode for the verifier. That is the pattern the hooks use, and it has no absolute path and no
  environment-specific assumption.
- **Why it was not applied.** It is not a documentation or packaging change. Three things stand in the way:
  1. the entry was declared under ADR-0035 after the Connector gate (`CLAUDE.md` §13);
  2. it is pinned byte-for-byte as "the approved entry" by
     `tests/unit/test_m11_verification_server.py::test_mcp_json_declares_exactly_the_approved_entry` and by
     `tests/connector_fixtures.py` `VERIFIER_ENTRY`, which the connector-security tests use;
  3. `lib/python/biq_run.py` has no server entry mode, so source code would change too.

  Changing all three amends an approved contract and its tests. That exceeds this prompt's scope-control rule, so the
  change is left for an owner decision, with this design.
- **Release impact.** `--final` is unavailable on systems that provide Python 3 only as `python3`. It fails closed:
  drafts remain usable and are labelled unverified. Everything else is unaffected. This is documented in `README.md`
  *Limitations*, and now in the troubleshooting guide.

## 8. D-10: token measurement

**Result: measured; the measurement debt is closed. The budget overrun is an owner decision.**

- **Method.** `claude --plugin-dir /mnt/d/Prakash/Claude/Plugins/BusinessIQ/BusinessIQ plugin details businessiq`,
  on Claude Code 2.1.283. This is the ADR-0013 procedure (`claude plugin details businessiq`) with the plugin loaded
  for one session. Two checks came first:
  - `claude plugin details businessiq` alone reports "not found": the plugin is not installed;
  - `claude plugin details businessiq --plugin-dir …` is rejected ("unknown option").
- **No global state changed.** `ls ~/.claude/plugins` was identical before and after, and `claude plugin list` shows
  `businessiq` still not installed.
- **Measured values (2026-09-27):**
  - Always-on: **~7,321 tokens**.
  - Inventory: 35 command and skill entries (the 19 command files and 16 skills), 2 agents, 3 hook events
    ("harness-only — no model context cost"), 1 MCP server ("tool schemas resolved at runtime; not counted").
  - Largest always-on entries: `biq-industry-research` ~370, `biq-competitor-analysis` ~340, `biq-data-ingestion`
    ~310, `biq-market-analysis` ~310.
  - Largest on-invoke entries: `biq-competitor-analysis` ~15.4k, `biq-industry-research` ~15.3k,
    `biq-market-analysis` ~10.7k.
  - The tool counts `/retrieval-slice` (~130 always-on) although it carries `disable-model-invocation: true`. That is
    recorded as reported.
- **Limitations.**
  - The tool labels its counts as estimates.
  - On-invoke cost is per firing, so it is not a session total.
  - Evaluation spend (for example, $47.00 for the closing evaluation) is a different quantity, and is not used here.
- **Against ADR-0013.** The self-imposed target is ≤ 3,000 tokens always-on, so this measurement is about 2.4 times the
  target. ADR-0013 records that nothing breaks. The response ("merge components whose descriptions overlap — never …
  truncate") is an owner decision. Related open defect: M13-DEF-01 (two descriptions over 1,024 characters).

## 9. D-14 reconciliation

- **The development index.** `docs/development/README.md`'s table stopped at M9-B. The 104 missing records were
  added, one row per record in the table's existing `Date | Milestone | Record` convention. Each record's milestone
  text is taken from its own first heading. The rows cover M9-B to M14-4, including this record. No record was edited.
- **README labels.** `README.md`'s documentation table no longer says the examples and troubleshooting guide are
  "being written".
- **Result.** With M14-1's and M14-2's parts, every part of D-14 is reconciled. `project_plan.md` records D-14 as
  resolved by M14-4.

## 10. ADR-0042 packaging follow-up 5

**Result: measured and documented; owner decision.**

- **Why everything ships.** `marketplace.json` sets `"source": "./"`, so an install copies the repository: 626
  tracked files, about 9.6 MB.
- **Development material in the installed copy:**
  - `docs/`: 197 files, about 2.9 MB;
  - `tests/`: 133 files, about 3.2 MB;
  - `evals/`: 102 files, about 0.26 MB. These are needed, because the manifest's `experimental.evals` points at
    `evals`;
  - `CLAUDE.md`, `project_plan.md` and `architecture.md`.
- **No secret is tracked** (`CLAUDE.md` §7, `.gitignore`), and none of this material enters the model's context
  (ADR-0042).
- **Why nothing was changed.** Excluding development material needs a verified platform mechanism and a manifest or
  distribution change. Neither is established in the repository, and the prompt forbids inventing package metadata.
- **The owner decision.** Accept this for release, or restructure the distribution.

## 11. Documentation consistency review

Current-facing documents were scanned: `README.md`, `CONNECTORS.md`, every `docs/*/README.md`, `docs/commands/*` and
`docs/agents/*`. Historical ADRs and dated records were excluded, and left as written.

**Corrected:**

- the two `README.md` labels;
- `docs/testing/README.md`, which still described `claude plugin eval` as early-access gated (R-01 is closed);
- `docs/architecture/README.md` ("Empty until Milestone 2");
- the development index (§9).

**Found in product surface, not documentation, and recorded without being fixed:**

- **R-15.** The `/ask-business-data` router tells users forecasting, anomalies and research "arrive" in Milestone 8
  or 9. This was re-observed live on the demo data. The wording is pinned by three test modules.
  - Seven command files and `skills/biq-industry-research/SKILL.md` carry similar wording ("do not exist yet", "a
    later milestone", "(Milestone 10)").
  - Fixing it changes engine, command, skill and test files.
- **R-16.** The same margin movement renders as -2.84 pp in `/business-health` and -2.85 pp in
  `/profitability-analysis`. `analytics/findings.py` uses `%.2f`, while the other paths quantise with
  `ROUND_HALF_UP`.

**Unchanged, by prompt:**

- `CLAUDE.md` §3 ("20 skills", agents "listed explicitly"; D-07);
- the M14-1 and M14-2 historical "uncommitted" wording.

## 12. Validation results

- `git diff --check`: clean. New or rewritten files: no trailing whitespace or tabs.
- Links: 262 relative links and anchors in the 9 changed or new files checked, **0 broken**. The development index
  lists every dated record, with none unlisted and none dangling.
- `claude plugin validate . --strict`: `✔ Validation passed`.
- Governance and README-reading tests: `unit.test_command_registry`, `unit.test_m13_coverage_matrix`,
  `unit.test_manifest` and `negative.test_m12b_connector_security`. Result: `Ran 166 tests`, `OK (skipped=1)`.
- Full regression, `python3 tests/run_tests.py`: `Ran 5286 tests in 591.016s`, `OK (skipped=31)`,
  `ran 5286 | failures 0 | errors 0 | skipped 31`, exit 0.
- No paid evaluation, MCP or connector was run. The token measurement loads the plugin for one session and invokes
  no model.

## 13. Release-gate matrix

| Gate | Status | Evidence | Limitation | Release impact |
|---|---|---|---|---|
| A. Product functionality | PARTIAL | 18 user commands, 16 skills and 2 agents ship (M14-3); full regression passes | R-15 text; research commands `REVIEW` | Owner decision on R-15 and the M9 smoke tests |
| B. Internal analytics | PASS | Nine registry commands; demo runs in `docs/examples/`; regression | M13-DEF-03 (large-CSV labelling); R-16 | Non-blocking |
| C. Forecasting | PASS | Backtested forecast on demo data; minimum-history refusal verified (R-14 closed) | Forecasts not carried into reports | Non-blocking |
| D. Anomaly detection | PASS | 11 of 108 periods flagged on demo data, with the fraud boundary | Describes, never explains | Non-blocking |
| E. External research | PARTIAL | Four commands deterministically complete; disclosure gate hardened (ADR-0050) | Owner-run live smoke tests outstanding (M9 `IN PROGRESS`); M13-DEF-15 and -16 open | OWNER DECISION |
| F. Cross-domain synthesis | PASS | ADR-0022 set; M10 `COMPLETED` | None known | Non-blocking |
| G. SWOT / strategy | PASS | M10.3.1 and M10.3.2 `COMPLETED` | No ranking, by design | Non-blocking |
| H. Decision support | PARTIAL | M10.3.3 `COMPLETED`; drafts work | `--final` unavailable where only `python3` exists (R-13) | OWNER DECISION (R-13) |
| I. Executive reporting | PARTIAL | M10.3.4 `COMPLETED`; drafts work | R-13 for `--final`; outlook has no forecast | OWNER DECISION (R-13) |
| J. Privacy and security | PASS | Tier model, ADR-0050 gate, scout tool grant; M13-DEF-13 `fixed_product` | Tier 2 refused rather than shown (M13-DEF-16) | Non-blocking (fails closed) |
| K. Write safety | PASS | ADR-0051 guard; M13-DEF-24 `fixed_product`; live grant verification | Prompt-origin limitation (`README.md`) | Non-blocking |
| L. Connector state | PASS | Empty registry by design (ADR-0037 OD-1); documented everywhere | No connected systems; M12-C `BLOCKED` | Non-blocking: shipped state is truthful |
| M. Documentation | PASS | M14-1 to M14-4; indexes complete; links resolve | `CLAUDE.md` §3 (D-07); product-text R-15 | Non-blocking for documentation |
| N. Worked examples | PASS | `docs/examples/README.md`, figures reproduced | Live examples carry no values | Non-blocking |
| O. Troubleshooting | PASS | `docs/troubleshooting/README.md` | R-13 and R-16 have no workaround | Non-blocking |
| P. Testing and regression | PASS | Full regression: 5,286 tests, 0 failures, 0 errors, 31 skipped; strict validation passed | — | Non-blocking |
| Q. Evaluation status | PASS | M13.2 owner-accepted; all 64 cases have admissible live evidence; R-01 closed | Product defects M13-DEF-01, -03, -14, -15 and -16 open | OWNER DECISION (remediation unassigned) |
| R. Token/cost measurement | OWNER DECISION | Measured: ~7,321 tokens always-on (§8) | Above the self-imposed ≤ 3,000 target | OWNER DECISION (ADR-0013 response) |
| S. Packaging | OWNER DECISION | Whole repository ships (§10) | Development material in the installed copy | OWNER DECISION |
| T. Release and tagging readiness | OWNER DECISION | No tag exists; manifest version `0.1.0`; publication gate (`CLAUDE.md` §13) | Owner decisions A, E, H, I, Q, R and S open | **OWNER RELEASE APPROVAL REQUIRED** |

**Recommendation.** The repository is technically ready for the owner to review a release checkpoint. The regression,
validation, documentation and examples are complete, and every known limitation is documented truthfully. It is
**not** recommended to tag a public release until the owner has decided three things:

- R-15, because users are told built capabilities do not exist;
- R-13, because `--final` is unavailable on `python3`-only systems;
- the outstanding M9 live smoke tests.

The token overrun and the packaging choice are owner decisions, but neither blocks correctness. No version is proposed.

## 14. Remaining owner decisions

1. **OWNER RELEASE APPROVAL REQUIRED.** Any tag, push, GitHub release or marketplace publication.
2. **R-13.** Approve amending the ADR-0035 `.mcp.json` entry, and its pinning tests, to launch through `lib/biq_run.sh`
   (§7).
3. **R-15.** Approve a product-surface fix to the router, the 7 command files, 1 skill and 3 test modules.
4. **R-16.** Whether to fix the rounding inconsistency (minor).
5. **ADR-0013.** The response to ~7,321 against the ≤ 3,000 always-on target.
6. **ADR-0042 follow-up 5.** Accept whole-repository packaging, or restructure the distribution.
7. **M9.** Run the four owner-run fresh-session live smoke tests.
8. **Open M13 product defects** M13-DEF-01, -03, -14, -15 and -16: assign remediation or accept for release.
9. **D-13.** Schedule or retire, by ADR, the five designed-not-shipped skills.
10. **D-07.** The `CLAUDE.md` §3 command pointer, skill count and agents-in-manifest sentence.

## 15. Remaining release blockers

**No technical blocker was found:**

- the regression passes;
- strict validation passes;
- no known defect makes the product produce a wrong figure or cross a privacy boundary.

**Every remaining item is an owner decision.** R-13, R-15 and the M9 smoke tests are the ones recommended to settle
before a public tag (§13).

## 16. Tag, push and publication

- **No release tag was created.**
- **Nothing was committed, amended, staged, pushed or published.**
- HEAD remains `8e4ab17`, and `origin/main` remains `595e910`.

## 17. Git commit reference

N/A.
