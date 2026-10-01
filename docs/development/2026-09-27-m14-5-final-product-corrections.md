# 2026-09-27 — M14-5: final product corrections and release gate

**Milestone:** 14 — Documentation & Release
**Status on completion:** REVIEW — implemented and uncommitted, awaiting owner review. M14 stays `IN PROGRESS`. **OWNER RELEASE APPROVAL REQUIRED**
**Supersedes:** In part, `2026-09-27-m14-4-release-readiness.md`:

- §7: R-13 is now fixed;
- §11: R-15 and R-16 are now fixed, and its R-16 root cause was wrong (see §5 below);
- §§13 to 15: the gate status.

That record is not edited.

## 1. Prompt / task performed

The owner prompt was "M14-5 — Final Product Corrections and Release Gate". It asked for these steps:

1. resolve R-15, R-13 and R-16;
2. review and disposition M13-DEF-01, -03, -14, -15 and -16, fixing only what is release-relevant and safely fixable;
3. perform the four M9 live smoke tests by the documented procedure;
4. re-run validation;
5. re-measure token cost only by a free, local method;
6. preserve the packaging finding;
7. report a release gate without making the release decision.

Excluded: commit, amend, tag, push and publication; paid evaluations; new capability; D-07; D-13.

## 2. Starting checkpoint

- HEAD `8e4ab17a8405a01542d71fb1731b4b42003dbe5d` (M14-3), on `main`.
- `origin/main` at `595e910`.
- The M14-4 working tree (8 files) was present and preserved. A backup diff was taken in the session scratchpad
  before any change.

## 3. R-15: stale product-facing messaging — RESOLVED

**Root cause.** Refusal and scope text written before M8 to M10 existed was never updated when those milestones
shipped.

**How occurrences were classified.** Every occurrence was searched for:

- current user-facing text was corrected;
- historical ADRs and dated records were left as written;
- four developer-only module docstrings keep historical milestone wording, because users never see them.

**Files fixed:**

- `lib/python/biq/commands/query.py`: the `/ask-business-data` router now names the owning command
  (`/revenue-forecast`, `/anomaly-detection`, or the research commands and `/benchmark-comparison`), with no
  milestone.
- `lib/python/biq/kpi/catalog.py`: the lifetime-value caveat.
- `lib/python/biq/research/gate.py`: the destination refusal.
- `lib/python/biq/research/retrieval.py`: the retrieval-unavailable message.
- `commands/business-health.md` and `commands/cash-flow-analysis.md`.
- `commands/ask-business-data.md`: "which command owns it".
- `commands/company-analysis.md`, `market-analysis.md`, `competitor-analysis.md`, `industry-research.md` and
  `benchmark-comparison.md`, plus `skills/biq-industry-research/SKILL.md`: "(Milestone 10)" became
  "(`/strategy-analysis`)".

**Tests changed.** Four assertions pinned the obsolete wording: two in `unit.test_command_registry`, one in
`negative.test_commands_negative` and one in `integration.test_commands_m7`. Each now asserts the owning command
**and** that no "Milestone" appears, so each is stricter than before.

**Verification:**

- 78 modules touching commands, skills, the catalogue, the gate and retrieval: 4,299 tests, OK.
- Restoring the old router wording makes `unit.test_command_registry` fail.

## 4. R-13: verifier launcher — FIXED (ADR-0052)

**Root cause.** `.mcp.json` declared the server as `"command": "python"`. It predates ADR-0045, which moved every
other engine entry to the resolver.

**Change:**

- `.mcp.json` now declares `{"type": "stdio", "command": "sh", "args": ["${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh",
  "--verifier"]}`.
- `lib/python/biq_run.py` gained an exact `--verifier` mode. It runs the same layout check and import boundary as the
  other modes, then calls `biq.verification_server.main()`. It takes no argument and runs no caller code.
- The two pins were updated: `unit.test_m11_verification_server::test_mcp_json_declares_exactly_the_approved_entry`
  and `tests/connector_fixtures.py::VERIFIER_ENTRY`.
- ADR-0052 was written and indexed in all three ADR indexes.
- `architecture.md` §2 was updated.

**New tests.** `DeclaredEntry` runs 4 tests on the server started exactly as declared, on a `PATH` holding only a
`python3`:
- it initialises and lists one tool;
- it completes a real recomputation;
- extra arguments are refused as usage;
- the `PATH` holds no `python`.

**Validation:**

- Verifier, connector-security, registry, agent-boundary, profiler and runtime-resolver modules: 274 tests, OK.
- **Live:** on this host (no `python`; `/usr/bin/python3` only), `claude --plugin-dir <repo> mcp list`, run outside
  the repository, reports `plugin:businessiq:biq-verifier: sh …/lib/biq_run.sh --verifier - ✔ Connected`.
- Every fresh M9 smoke session's init event reported `plugin:businessiq:biq-verifier` as `connected`.
- The "before" evidence is this session's own start-up: `biq-verifier (ENOENT): "Executable not found in $PATH:
  python"`.

**Remaining limitations:**

- It needs `sh`, which is already a prerequisite.
- Run inside the repository, `claude mcp list` also reads `.mcp.json` as a project file, where
  `${CLAUDE_PLUGIN_ROOT}` is unset. That entry always fails there, and it is not the plugin's server. This is
  documented in the troubleshooting guide.

## 5. R-16: margin-movement rounding — FIXED

**Root cause. M14-4 had it backwards.** At full precision the demo movement is **-2.8454**, which rounds half up to
**-2.85**, the value `/profitability-analysis` showed.

- `pipeline.py` averaged the monthly margins returned by `sales.margin_series()`, which are **already rounded to
  2 dp**. That gives -2.8433, shown as -2.84.
- Rounding before aggregating breaks `CLAUDE.md` §4.

**Fix:**

- `pipeline.py` now averages the full-precision `segmentation.margin_by_period()` series through
  `segmentation.series_halves()`, the same path `analytics/financial.py` uses.
- The `%.2f` renderings of this movement in `analytics/findings.py` and `materiality.py` now use the canonical
  `Decimal.quantize(…, ROUND_HALF_UP)` that `analytics.domain` uses.

**Tests.** `unit.test_m14_5_margin_rounding` has 6 tests:

- the pipeline halves equal the full-precision halves, and differ from the twice-rounded ones;
- both commands print -2.85 on the demo data;
- the half-up tie case (-2.125 becomes -2.13, where `%.2f` gives -2.12).

Restoring the old aggregation fails 3 of them.

**Demo verification.** All eight demo command outputs were re-rendered and diffed against M14-4. Exactly one line
changed: `/business-health`'s movement, now -2.85. The worked examples were updated.

## 6. M13 defect dispositions

| Defect | What it is | Reproducible? | Release impact | Disposition |
|---|---|---|---|---|
| M13-DEF-01 | Two skill descriptions over the 1,024-character hard limit (1,065 and 1,158) | Yes (reproducer printed both) | Release-relevant: violates the project's documented hard limit (ADR-0013); the tail holds the trigger phrases | **Fixed, `fixed_product` (ADR-0043), under ADR-0013.** Wording trimmed to 992 and 1,010 characters; every trigger phrase and every test-pinned refusal phrase kept; the limit assertion committed; highest skill-pair overlap fell 0.633 → 0.551 |
| M13-DEF-03 | A complete pass over 100,000 rows labelled `streamed`, incomplete and `partial` | Yes | Release-relevant: large-file users are told complete figures are partial | **Fixed, `fixed_product`.** `canonical.build()` records `full` unless a caller that really streamed says so. `integration.test_m14_5_processing_mode` runs the reproducer at 100,001 rows and fails under the old rule. Below the ADR bar. ADR-0036 §7 is unaffected; its Context table described the old rule as it then stood, so the concern raised mid-task that it conflicted was withdrawn |
| M13-DEF-14 | Read-only analysis asks for approval | Not re-run (a live evaluation is required) | Non-blocking: errs toward caution | **Open, known limitation.** Model behaviour; a fix is unverifiable without a paid evaluation |
| M13-DEF-15 | Required statements omitted (clarifying question, "No reliable source found") | Not re-run | Non-blocking: substance usually right | **Open, known limitation** |
| M13-DEF-16 | A Tier-2 query refused outright rather than shown for approval | Not re-run | Non-blocking: fails closed; the gate implements the approval path (ADR-0050), and the model over-refuses | **Open, known limitation** |

The regression initially failed on M13-DEF-01's first trim. It had merged the pinned phrases "scores nothing" and
"ranks nothing", which `unit.test_m9d5_industry_research` asserts. The phrases were restored verbatim, and length was
recovered elsewhere. The test was not changed.

## 7. M9 live smoke tests

**Procedure.** `docs/development/2026-09-13-m9d1-company-analysis-command.md` §15 requires a genuinely fresh Claude
Code session with the plugin registered at start. Each test was run as `claude -p --plugin-dir <repo>
--no-session-persistence --output-format stream-json --verbose --max-budget-usd 5` from an empty scratchpad
directory, which holds no business data. The grant was the engine resolver, Read, Write, Agent, Task, Skill,
WebSearch and WebFetch.

The inputs come from each command's record (market M9-D.2 §15, competitor M9-D.3). The industry record names no
input, so the command file's own single-retrieval example was used.

**First attempt, not counted.** The first attempts of market, competitor and industry ran in parallel and were all
cut off by the **account session limit** ("You've hit your session limit", `terminal_reason: api_error`). They were
re-run one at a time.

| Command and input | Launched and registered | Retrieval | Evidence and attribution | Output contract | Result |
|---|---|---|---|---|---|
| `/company-analysis Microsoft --focus overview` | Yes; skill invoked; verifier connected | 1 dispatch: "Microsoft company profile"; 5 fetches | 2 records, tiers B and C recomputed locally, both undated; 0 verified; conflicts and limitations stated | 10 sections, confidence LOW, no figure estimated | **FAIL on criterion 5 only** |
| `/market-analysis cold chain logistics --focus overview` | Yes | 1 dispatch; 7 fetches | 5 records; 0 verified | 10 sections, confidence LOW | **FAIL on criterion 5 only** |
| `/competitor-analysis Microsoft --focus landscape` | Yes | 1 dispatch: "Microsoft competitive landscape"; 4 records | Not assembled | **Not produced** | **FAIL (incomplete)** |
| `/industry-research commercial aerospace --focus structure` | Yes | 1 dispatch; 6 fetches | 3 records, all tier C; 0 verified | 10 sections, confidence LOW with the tier-C reason | **FAIL on criterion 5 only** |

**What passed in every run:**

- discovery and skill routing;
- exactly one gate-authorised dispatch, with a public query only;
- no file read anywhere;
- no internal term in any query.

**Criterion 5, "no manual repair, extraction or trimming".** It was not met in any completed run.

- The platform delivers the scout's reply wrapped as "[Subagent hand-back] …", with every line indented. The scout
  also added prose around its records.
- Each session wrote only the de-indented protocol lines to the reply file.
- Checked offline with `biq.research.scout.parse_reply()`: the **raw hand-back parses verbatim** to the identical
  records (2, 5 and 3), so there is no correctness impact.
- The likely cause is the research skills' wording, "Feed the scout's **reply text** to `close_retrieval`", which
  never says *verbatim*, whereas `architecture.md` §10 does.

**The competitor failure.** After retrieval, the session wrote the closing call into a script file and ran it with
`exec(open(...))`, not the documented inline form. The write guard (ADR-0051) cannot confine that, so it asked for
approval, which a non-interactive session cannot give. The session correctly refused to work around the guard and
stopped. Interactively, the user could approve the call; the troubleshooting guide now describes this.

**Write-guard observations.** In the market run, an unconfined `import inspect` call was blocked. That is correct
behaviour, and the session carried on without it.

**Cost.** $5.64 across all seven sessions, including the three that were cut off.

## 8. Token and cost status (D-10)

The M14-4 method was re-run: `claude --plugin-dir <repo> plugin details businessiq`, with no install.

- Always-on is **~7,260 tokens**, down from ~7,321; the change comes from the M13-DEF-01 trims.
- It is still above ADR-0013's self-imposed ≤ 3,000 target.

D-10 is a resolved measurement with an over-target result. The response is an owner decision, and the target is
unchanged.

## 9. Packaging

This is unchanged from the M14-4 finding:

- the marketplace source is `./`, so the whole repository ships: about 626 tracked files, about 9.6 MB, including
  `docs/`, `tests/` and `evals/`;
- no tracked secret was found.

This task adds four files. Whether to accept this packaging or restructure it is an owner decision.

## 10. Files changed by M14-5

**Product:**

- `.mcp.json`;
- `lib/python/biq_run.py`;
- `lib/python/biq/commands/query.py`, `kpi/catalog.py`, `research/gate.py`, `research/retrieval.py`;
- `lib/python/biq/pipeline.py`, `analytics/findings.py`, `materiality.py`, `ingest/canonical.py`;
- the 7 command files named in §3;
- `skills/biq-industry-research/SKILL.md` and `skills/biq-competitor-analysis/SKILL.md`.

**Tests:**

- modified: `tests/connector_fixtures.py`, `unit/test_m11_verification_server.py`, `unit/test_command_registry.py`,
  `negative/test_commands_negative.py`, `integration/test_commands_m7.py`, `unit/test_m13_discriminability.py`;
- new: `unit/test_m14_5_margin_rounding.py`, `integration/test_m14_5_processing_mode.py`.

**Documentation and governance:**

- new: ADR-0052 and this record;
- modified: `architecture.md` (§2 MCP row, §19 index, §20 item 10), `README.md` (*Limitations*), `project_plan.md`,
  `docs/testing/defects.md`, `docs/decisions/README.md`, `docs/README.md`, `docs/development/README.md`,
  `docs/examples/README.md`, `docs/troubleshooting/README.md`.

`CLAUDE.md` was not changed.

## 11. Validation

- Full regression (final tree): `Ran 5301 tests in 638.307s`, `OK (skipped=31)`, `ran 5301 | failures 0 | errors 0 | skipped 31`, exit 0. The governance modules were re-run after the last documentation edits: 217 tests, OK.
- The first full run failed 1 test (§6), and it was corrected.
- Targeted runs are listed in §§3 to 6.
- The register validator (`unit.test_m13_coverage_matrix`): 33 tests, OK.
- `claude plugin validate . --strict`: passed. Links: 377 across 24 changed Markdown files, 0 broken. `git diff --check`: clean.

## 12. Release-gate matrix

| Gate | Status | Evidence | Limitation | Release impact |
|---|---|---|---|---|
| A. Product functionality | PARTIAL | 18 commands, 16 skills, 2 agents; stale messaging fixed (R-15); regression | Research commands still `REVIEW` (G. below) | OWNER DECISION |
| B. Internal analytics | PASS | Demo outputs reproduced; R-16 and M13-DEF-03 fixed | — | Non-blocking |
| C. Forecasting | PASS | Minimum-history refusal verified (R-14 closed) | Forecasts not in reports | Non-blocking |
| D. Anomaly detection | PASS | Demo scan; fraud boundary | Describes, never explains | Non-blocking |
| E. External research | PARTIAL | Live: 4 of 4 dispatched correctly, public queries only, no file read; 3 of 4 produced the full report | Criterion 5 unmet (trimmed reply, identical records); competitor stopped at a guard approval | OWNER DECISION |
| F. Cross-domain synthesis | PASS | M10 `COMPLETED` | — | Non-blocking |
| G. SWOT / strategy | PASS | M10.3.1 and M10.3.2 | No ranking, by design | Non-blocking |
| H. Decision support | PASS | Drafts work; `--final` verifier now connects (R-13 fixed) | — | Non-blocking |
| I. Executive reporting | PASS | As H.; outlook states that no forecast is available | Forecasts not carried in | Non-blocking |
| J. Privacy and security | PASS | ADR-0009 and ADR-0050 gate; scout grant; no internal term in any live query | M13-DEF-16 (over-refusal, fails closed) | Non-blocking |
| K. Write safety | PASS | ADR-0051 guard blocked unconfined engine calls live and was not circumvented | Can halt a non-interactive run | Non-blocking |
| L. Connector state | PASS | Empty registry, truthfully documented | M12-C `BLOCKED` | Non-blocking |
| M. Documentation | PASS | Indexes complete; links resolve | D-07 (`CLAUDE.md` §3) | Non-blocking |
| N. Worked examples | PASS | Re-verified after fixes | Live examples carry no values | Non-blocking |
| O. Troubleshooting | PASS | Updated for R-13, R-15, R-16 and the guard pause | — | Non-blocking |
| P. Testing and regression | PASS | Full regression: 5,301 tests, 0 failures, 0 errors, 31 skipped | — | Non-blocking |
| Q. Evaluation status | PASS | M13.2 owner-accepted | M13-DEF-14 to -16 open (model behaviour) | OWNER DECISION |
| R. Token/cost measurement | OWNER DECISION | ~7,260 always-on (§8) | Above ≤ 3,000 | OWNER DECISION |
| S. Packaging | OWNER DECISION | Whole repository ships (§9) | Development material installed | OWNER DECISION |
| T. Release and tagging | OWNER DECISION | No tag; version `0.1.0` | Decisions A, E, Q, R and S | **OWNER RELEASE APPROVAL REQUIRED** |

## 13. Remaining owner decisions

1. **OWNER RELEASE APPROVAL REQUIRED:** any tag, push, release or publication.
2. **M9 criterion 5.** Either accept the trimmed-reply behaviour (records identical, parser tolerates the raw text),
   or approve a wording fix to the research skills ("write the reply exactly as received") followed by fresh live
   re-runs. Also decide whether `/competitor-analysis` leaves `REVIEW` after its guard-halted run, or needs a
   re-run.
3. **M13-DEF-14, -15 and -16:** accept as known limitations for release, or schedule a remediation verified by a
   live evaluation.
4. **ADR-0013:** the response to ~7,260 against ≤ 3,000.
5. **Packaging:** accept whole-repository packaging, or restructure it.
6. **D-13 and D-07:** unchanged.

## 14. Remaining release blockers

No unresolved **technical** blocker was found:

- no known defect produces a wrong figure, crosses a privacy boundary or writes without approval;
- the verifier now starts on `python3`-only hosts.

The open items are owner decisions.

## 15. Tag, push and publication

- No commit, amend, stage, tag, push or publication.
- HEAD remains `8e4ab17`, and `origin/main` remains `595e910`.

## 16. Git commit reference

N/A.
