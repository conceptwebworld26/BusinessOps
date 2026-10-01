# 2026-09-16 — M10.3.4: Executive Report contract (decision only)

**Milestone:** 10.3.4 — contract and architecture review for `biq-executive-report` + `/executive-report`
**Status on completion:** COMPLETED (DECISION ONLY)
**Supersedes:** None

## 1. Prompt / task performed

Define an implementation-ready Executive Report contract without implementing it: purpose, canonical
inputs, relationships to Synthesis, Strategy, Decision Support and SWOT, section structure, executive
summary, KPI scorecard, forecasts and anomalies, risks and opportunities, recommendation semantics,
lifecycle and the M11 boundary, confidence and materiality, human-decision boundary, provenance and
security, output model, ordering, empty states, framing and external research. One new ADR if
consistent with accepted contracts; stop and report if an accepted ADR is contradicted. No code, tests,
schemas, skills, commands, manifests, MCP or connectors; no live research; no commit or push.

## 2. Baseline

| Fact | Value |
|---|---|
| HEAD | `a251e57210c2642f470a50be352c3cc37e8b8e01` — *M10.3.3: Decision Support*; equal to `origin/main` after a read-only fetch; clean tree |
| Last full run | 4,335 tests, 0 failures, 0 errors, 19 skipped |
| Next free ADR | 0033 |

## 3. What the repository said about M10.3.4 before review

- `project_plan.md`, *M10.3.4 onward · PLANNED*: "`biq-executive-report` + `/executive-report`. Reads the
  M10.1 representation and may assemble `StrategyResult`s and `DecisionResult`s (ADR-0031, ADR-0032)."
- `architecture.md` §4: "`biq-executive-report` (assembles; performs no fresh analysis)"; `biq-report-composer`
  merged into it (judgement) and the engine (rendering).
- ADR-0022: the four M10 capabilities read one synthesis representation; direct reads of upstream objects
  rejected.
- ADR-0031 / §7: may assemble recommendation records, never author, edit or re-grade one.
- ADR-0032 §14: may consume packages draft or final with lifecycle shown; never re-authors, re-grades,
  reorders by importance or drops content; whether it requires `final` left to its own milestone.
- `architecture.md` §10 and ADR-0032 §13: the M11 verifier finalises, meaning draft → final.
- ADR-0010 / `CLAUDE.md` §9: executive reports and scorecards are draft generation.
- `reference/output-standards.md`: KPI scorecard, forecast table, recommendation list and decision package
  shapes; basis and quality-warning rules.
- `lib/python/biq/render/executive.py`: the Milestone 2 snapshot, "not the full executive-report skill (M10)".

No section structure, input contract, summary rule, lifecycle rule or output model existed.

## 4. What inspection established (read-only probes on the synthetic demo file)

| Question | Finding |
|---|---|
| KPIs into the set | `from_kpi_result()`: 9 statements from `/business-health`; unavailable KPIs become `kpi.unavailable` limitations; KPI statements carry no materiality verdict unless a caller passes one |
| Anomalies into the set | `internal_statements(run, ORIGIN_ANOMALY)` on `/anomaly-detection`: 11 `CALCULATION` statements, `supported`, `HIGH`, material |
| Forecasts into the set | `/revenue-forecast` → refused: "the analytics engine emitted 'ASSUMPTION', which the synthesis layer does not accept as an internal statement". `ORIGIN_FORECAST`, `P_FORECAST` and `forecast_instability` exist, but no translator produces a forecast-footed statement, and an `ASSUMPTION` with a resolvable internal reference would currently grade `supported` / `HIGH` |
| SWOT result | `swot.build()` returns a plain record with no digest or binding; points carry `quadrant`, `tag`, `synthesis_id`, `point_id`, so placements are recoverable and the record reproducible |
| Strategy / Decision Support | Objects bound to the set object and digest; `DecisionResult` holds its `StrategyResult` privately |
| KPI targets | `business_context.analysis.kpi_overrides.<id>.target` exists in the schema; no engine reads it and it does not reach resolved configuration |
| KPI order | `kpi/catalog.py` `CATALOGUE` declaration order |
| Favourable / unfavourable framing | Only SWOT owns it (ADR-0030); synthesis statements carry no direction |

## 5. Decisions (ADR-0033)

1. **Purpose.** An `ExecutiveReportResult`: a draft, fixed-section assembly beside one genuine strict set.
   It authors no analysis, recommendation or summary prose.
2. **Inputs.** Required: the set (not `CRITICAL`) and a closed framing request (`reporting_period`,
   `audience`, `objective`, `questions`, `constraints`). Optional: one bound `StrategyResult`; zero or more
   bound `DecisionResult`s; one SWOT record its placements rebuild exactly. `AnalysisSet`, `KPIResult`,
   `AnomalySet`, `ForecastSet`, `EvidenceSet`, `CommandResult` only through the set. An invalid optional
   input refuses the report.
3. **Eleven sections, fixed order, always present:** `reporting_frame`, `executive_summary`,
   `kpi_scorecard`, `findings`, `anomalies`, `outlook`, `swot`, `strategy_recommendations`,
   `decision_support`, `evidence_and_uncertainty`, `decisions_for_the_reader`; statuses `included`,
   `empty`, `not_supplied`, `not_available`.
4. **The brief's candidate list, reconciled:**

   | Candidate | Outcome | Why |
   |---|---|---|
   | Executive Summary | Required (§4 rule) | Selection by rule, never prose |
   | Business Context / Reporting Frame | Required | Basis and quality warning first (output standards) |
   | KPI Scorecard | Conditional | KPI engine through the set |
   | What Is Going Well | **Prohibited** | Favourable placement is SWOT's |
   | What Needs Attention | **Prohibited** | Unfavourable placement is SWOT's |
   | Key Risks | **Prohibited as a standalone section** | Risks are owned by records, packages and SWOT threats; an aggregate re-homes, reorders and implies severity |
   | Opportunities | **Prohibited as a standalone section** | SWOT opportunities own them |
   | Material Anomalies | Conditional, as `anomalies` (all anomaly statements, materiality shown) | Filtering by verdict would hide non-material flags; material ones also reach the summary |
   | Forecast / Outlook | Conditional, `not_available` until forecasts can enter synthesis | ADR-0022; no translator today |
   | Strategic Recommendations | Conditional | ADR-0031, whole |
   | Decision Support | Conditional | ADR-0032, whole |
   | Evidence / Confidence / Limitations | Required | Carried whole |
   | Next Steps / Human Decisions Required | Required, as `decisions_for_the_reader` | Human-decision statement; next steps only by reference to packages |
   | Findings (added) | Conditional | Evidential statements and interpretations not shown elsewhere |

5. **Recommendations:** Executive Report issues none.
6. **Lifecycle:** draft only before M11; draft packages admitted and labelled; a final report may not
   contain a draft package; verification recording is M11's.
7. **No report-level confidence or score; materiality never re-judged.**
8. **Binding:** built only by `build()`, bound to the set digest and each component; content-addressed
   `report_id`; no re-entry.
9. **Research:** the engine never retrieves; the command sequences existing paths.

## 6. Contradiction check

No accepted ADR is contradicted. ADR-0022, ADR-0030, ADR-0031 and ADR-0032 are unchanged and were not
edited. The forecast gap is a missing translator, not a contradiction: ADR-0022 anticipates forecast
provenance without mandating a translator, and ADR-0033 declines to invent one or to read `ForecastSet`
directly.

## 7. Files created

- `docs/decisions/ADR-0033-executive-report-contract.md`
- `docs/development/2026-09-16-m10-3-4-executive-report-contract.md` (this record)

## 8. Files modified

- `architecture.md` — §4 status; §7 consumers line and new *executive-report contract* section; §10
  verifier row; decisions table
- `project_plan.md` — *M10.3.4 onward* replaced by *M10.3.4 — Executive Report contract* (`COMPLETED
  (DECISION ONLY)`) and *Executive Report implementation* (`PLANNED`)
- `reference/output-standards.md` — *Executive report* shape
- `docs/decisions/README.md`, `docs/README.md` — ADR-0033 listed

## 9. Files deliberately unchanged

All production code, tests, schemas, skills, commands, agents, manifests, `.mcp.json`, every accepted
ADR, `CLAUDE.md` (no governance change), `README.md` ("Not built yet — executive reporting" remains
true), `docs/commands/README.md` and `docs/skills/README.md` (nothing new is built).

## 10. Tests performed

```
python tests/run_tests.py
claude plugin validate . --strict
git diff --check
```

## 11. Test results

- `ran 4335 | failures 0 | errors 0 | skipped 19` — identical to the M10.3.3 baseline.
- `claude plugin validate . --strict`: Validation passed.
- `git diff --check`: clean (the repository's usual LF→CRLF working-copy notices only).

## 12. Issues discovered

- **Forecasts cannot enter synthesis** (§4). Recorded as a follow-up needing its own decision, including
  how an estimate is graded.
- **KPI targets are declared but unconsumed.** Not shown until an engine computes variance.
- **Pre-existing documentation debt, not changed here:** `docs/decisions/README.md` does not list
  ADR-0017, ADR-0018, ADR-0023 or ADR-0024, and `docs/README.md` omits several ADRs; the `project_plan.md`
  milestone table row for Milestone 10 still reads "IN PROGRESS (10.1 done)".

## 13. Architecture changes

Decision recorded in `architecture.md` §4, §7, §10 and the decisions table. No built behaviour changed.

## 14. Remaining work

Executive Report implementation (ADR-0033 follow-up list); separately, a synthesis forecast translator
decision; M11 verifier.

## 15. Git commit reference

N/A — no commit made, nothing pushed.
