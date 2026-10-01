# Skill Reference

The index of BusinessOps's skills: what ships, what was designed but is not shipped, and why the two counts
differ. The skill logic itself lives in `skills/<name>/SKILL.md`, and **that file is each skill's detailed
reference**. This page explains and indexes, and does not repeat it. For the user-facing workflow around
each skill, see the command family pages linked in the last column and the [command reference](../commands/README.md).

*Inventory verified against `skills/` on 2026-09-27 (M14-3).* Status for each skill is owned by
[`project_plan.md`](../../project_plan.md); this page reports it.

## At a glance

| | Count | Where it is defined |
|---|---|---|
| Skills shipped in `skills/` | **16** | This page, *Shipped skills* |
| Skills in the `architecture.md` §4 design | 20 | [`architecture.md` §4](../../architecture.md) |
| Designed skills that ship | 15 | |
| Designed skills not shipped | **5** | This page, *Designed, not shipped* |
| Shipped skills outside the §4 design | 1 (`bops-benchmark-comparison`) | ADR-0029 |

**20 designed − 5 not shipped + 1 outside the design = 16 shipped.** The full mapping is in
[Design-to-shipped mapping (D-13)](#design-to-shipped-mapping-d-13).

No skill is internal or test-only. Every shipped skill can be invoked by the model on the user's request, and
none carries `user-invocable: false`.

## Shipped skills

Every shipped skill is `COMPLETED` in `project_plan.md`. None performs arithmetic: every figure a skill
presents was computed by `lib/python/bops/`.

### Data layer

| Skill | Answers | Does not cover | Command reference |
|---|---|---|---|
| [`bops-data-ingestion`](../../skills/bops-data-ingestion/SKILL.md) | What 1–20 local files contain: sheets, columns, exact non-null, empty and distinct counts, date coverage, key candidates and key overlap, the Data Quality grade, and whether a named command or KPI has what it needs | Cell values; KPI values, totals or averages; ranking; joining; evidence; connector sources | No command. Invoked by request, for example "what is in this file?" |

`bops-data-ingestion` (M11) presents a `DataProfileResult` from `lib/python/bops/data_profile.py`. That module reads
only through the Data Layer and refuses to serialise once a source changes. See ADR-0036 and
[the implementation record](../development/2026-09-17-m11-data-profiler-implementation.md).

### Internal analytics

| Skill | Answers | Does not cover | Command reference |
|---|---|---|---|
| [`bops-sales-intelligence`](../../skills/bops-sales-intelligence/SKILL.md) | Revenue and order trend; which region, salesperson, line or period moved; mix shift; what drove the net change; revenue concentration | Per-product margin; customer behaviour; the profit statement | [Internal analytics](../commands/internal-analytics.md) |
| [`bops-customer-intelligence`](../../skills/bops-customer-intelligence/SKILL.md) | How many customers; new versus returning; retention and churn; concentration; acquisition cohorts | Products; margins; anything about intent or motivation | [Internal analytics](../commands/internal-analytics.md) |
| [`bops-product-intelligence`](../../skills/bops-product-intelligence/SKILL.md) | Product and category contribution, growth, mix, per-product margin, concentration, first appearance | Customers; regions; whole-business profitability | [Internal analytics](../commands/internal-analytics.md) |
| [`bops-financial-analysis`](../../skills/bops-financial-analysis/SKILL.md) | Profit and margin as far as the data goes; margin movement in points; cost ratio; cash and balance-sheet metrics; what is unavailable and why | Ranking products or customers; any transaction or accounting action | [Internal analytics](../commands/internal-analytics.md) |
| [`bops-forecasting`](../../skills/bops-forecasting/SKILL.md) | A computed forecast: the backtested method, base/upside/downside scenarios, the assumption register, the uncertainty band and what could not be forecast | Choosing a method, doing arithmetic, attaching a probability, or forecasting from external data | [Forecasting and anomalies](../commands/forecasting-and-anomalies.md) |
| [`bops-anomaly-detection`](../../skills/bops-anomaly-detection/SKILL.md) | Which periods deviated from their own baseline, by how much, against which baseline, and which parts of the data sit underneath | Explaining a cause, ranking by score alone, or calling any anomaly fraud | [Forecasting and anomalies](../commands/forecasting-and-anomalies.md) |

The first four consume an `AnalysisSet` from `lib/python/bops/analytics/`. `bops-forecasting` consumes a
`ForecastSet` and `bops-anomaly-detection` an `AnomalySet`. Both are `AnalysisSet` subclasses, so the same
materiality, evidence and presentation rules apply. See [the Milestone 6 record](../development/2026-09-08-internal-analytics.md)
and [the Milestone 8 record](../development/2026-09-09-forecasting-anomaly.md).

### External intelligence

| Skill | Answers | Does not cover | Command reference |
|---|---|---|---|
| [`bops-company-analysis`](../../skills/bops-company-analysis/SKILL.md) | What one named company does, its dated recent developments, stated positioning, publicly reported figures quoted from their sources, and the risks and opportunities the evidence carries | Your own data; estimates of figures no source stated; recommendations | [External research](../commands/external-research.md) |
| [`bops-market-analysis`](../../skills/bops-market-analysis/SKILL.md) | One named market: definition and scope, size and growth where a source states a figure, trends, drivers, risks and constraints | Averaged or midpoint sizings; competitor profiles; recommendations | [External research](../commands/external-research.md) |
| [`bops-competitor-analysis`](../../skills/bops-competitor-analysis/SKILL.md) | The competitive landscape around one named company: evidence-based competitor identity, source-stated comparison, positioning, developments, strengths and constraints | Ranking, scoring or naming a "best"; market share without a supported denominator; recommendations | [External research](../commands/external-research.md) |
| [`bops-industry-research`](../../skills/bops-industry-research/SKILL.md) | One named industry as a system: definition and boundaries, size and growth where a source states a figure, trends, drivers, risks and publicly observable structure | Attractiveness scores, Five Forces ratings or any ranking; inferred concentration; strategy | [External research](../commands/external-research.md) |
| [`bops-benchmark-comparison`](../../skills/bops-benchmark-comparison/SKILL.md) | One figure from your own file set beside a public benchmark, joined locally, with a seven-dimension comparability check | Sending your figure anywhere; blended figures, gaps or verdicts; scores or rankings | [`/benchmark-comparison`](../commands/benchmark-comparison.md) |

All five retrieve through the disclosure gate and the `bops-research-scout` subagent. The shared research core they
parameterise is engine code in `lib/python/bops/research/`, not a skill (see `bops-external-research` below).
`bops-benchmark-comparison` is the local join surface of ADR-0029, and it adds no analysis or research of its own.

### Synthesis

| Skill | Answers | Does not cover | Command reference |
|---|---|---|---|
| [`bops-swot`](../../skills/bops-swot/SKILL.md) | A four-quadrant SWOT placed from statements already in a strict synthesis set, each tagged data-supported, externally-sourced or analytical-inference | Writing new evidence; recommendations; ranking, scoring or prioritising points | [Synthesis and reporting](../commands/synthesis-and-reporting.md) |
| [`bops-strategy-recommendations`](../../skills/bops-strategy-recommendations/SKILL.md) | Class-7 recommendations whose evidence is synthesis statement ids, with derived confidence and figures quoted only from that evidence | Ranking, scoring or prioritising; estimating a figure; executing an action | [Synthesis and reporting](../commands/synthesis-and-reporting.md) |
| [`bops-decision-support`](../../skills/bops-decision-support/SKILL.md) | A draft twelve-part decision package for one user-supplied decision, with evidenced tradeoffs, risks and outcomes, derived confidence and at most one grounded preferred option | Scoring, weighting or ranking options; inferring framing; executing a decision; finalising without a passed verification | [Synthesis and reporting](../commands/synthesis-and-reporting.md) |
| [`bops-executive-report`](../../skills/bops-executive-report/SKILL.md) | A draft eleven-section report assembled from a strict synthesis set and the SWOT, strategy and decision results bound to it, every statement verbatim with its own evidence and confidence | Authoring analysis or summary prose; recommendations; scores, ratings, targets or rankings; forecasts; finalising without a passed verification | [Synthesis and reporting](../commands/synthesis-and-reporting.md) |

All four consume a `SynthesisSet`. The grounding checks they share have one home,
`lib/python/bops/synthesis/grounding.py`. Their contracts are ADR-0030 (SWOT), ADR-0031 (strategy), ADR-0032
(decision support) and ADR-0033 (executive report).

## Designed, not shipped

These five skills are part of the `architecture.md` §4 design. **None of them ships.** None is scheduled by any
milestone, and none may be presented as available. In each case the deterministic engine behind the skill
**does** exist and runs inside the commands. What is missing is the model-facing skill wrapper that §4 describes.

| Designed skill (§4 layer) | What §4 assigns it | Where that work happens today | Plan status |
|---|---|---|---|
| `bops-business-context` (L0) | Elicit, validate, persist and apply the business's identity and preferences | The engine **reads and validates** context (`lib/python/bops/context/loader.py`), and every data command resolves it as its first step. No skill or command elicits or writes it: the user supplies `./.businessops/business_context.json` themselves (for example by copying the demo sample, as `/business-health` shows) | Not scheduled. ADR-0011 records the skill as a required follow-up |
| `bops-semantic-mapping` (L1) | Map columns to business roles, confidence-scored, and ask below threshold | `lib/python/bops/mapping/semantic.py`, run inside every data command. Unconfirmed mappings are surfaced through `semantic_map.clarification_request()` | Not scheduled. M3 deferred the wrapper to "a later milestone" |
| `bops-data-quality` (L1) | The validation gate: 13 check families, and `CRITICAL` halts | `lib/python/bops/quality/`, run inside every data command. A `CRITICAL` grade halts the run. `bops-data-ingestion` reports the grade | Not scheduled |
| `bops-kpi-engine` (L2A) | Around 27 KPIs, each with a status | `lib/python/bops/kpi/`, run inside every data command. The analytics skills present its results | Not scheduled |
| `bops-external-research` (L2B) | The shared research core: query construction, the disclosure gate, citation capture | `lib/python/bops/research/` (gate, query, intents, retrieval, evidence sets), used directly by the four research skills and `bops-benchmark-comparison` | `PLANNED`, unscheduled (M9 row) |

Two further Revision 1 skills, `bops-connector-broker` and `bops-report-composer`, were **merged** into shipped
skills and the engine before Revision 2 (`architecture.md` §4, *Merged from Revision 1*). They are not counted
as designed skills and are not debt.

## Design-to-shipped mapping (D-13)

This is the component-by-component reconciliation that project-plan debt item **D-13** calls for. It changes
no design and no status. It records how the §4 design and the `skills/` directory correspond.

| §4 layer | Designed skill | Shipped? | Notes |
|---|---|---|---|
| L0 Context | `bops-business-context` | **No** | Engine exists (`context/`) |
| L1 Data | `bops-data-ingestion` | Yes | Built M11 (ADR-0036) as the data profiler. Connector resolution returns a named absence, because the connector registry ships empty |
| L1 Data | `bops-semantic-mapping` | **No** | Engine exists (`mapping/`) |
| L1 Data | `bops-data-quality` | **No** | Engine exists (`quality/`) |
| L2A Analytics | `bops-kpi-engine` | **No** | Engine exists (`kpi/`) |
| L2A Analytics | `bops-sales-intelligence` | Yes | M6 |
| L2A Analytics | `bops-customer-intelligence` | Yes | M6 |
| L2A Analytics | `bops-product-intelligence` | Yes | M6 |
| L2A Analytics | `bops-financial-analysis` | Yes | M6 |
| L2A Analytics | `bops-forecasting` | Yes | M8 |
| L2A Analytics | `bops-anomaly-detection` | Yes | M8 |
| L2B Intelligence | `bops-external-research` | **No** | Engine exists (`research/`). Plan row `PLANNED` |
| L2B Intelligence | `bops-company-analysis` | Yes | M9-C.3 |
| L2B Intelligence | `bops-market-analysis` | Yes | M9-D.2 |
| L2B Intelligence | `bops-competitor-analysis` | Yes | M9-D.3 |
| L2B Intelligence | `bops-industry-research` | Yes | M9-D.5 |
| L3 Synthesis | `bops-swot` | Yes | M10.3.1 |
| L3 Synthesis | `bops-strategy-recommendations` | Yes | M10.3.2 |
| L3 Synthesis | `bops-decision-support` | Yes | M10.3.3 |
| L3 Synthesis | `bops-executive-report` | Yes | M10.3.4 |
| *(not in §4)* | `bops-benchmark-comparison` | Yes | The local join surface (ADR-0029), built in M10.2-R.14 |

**Why the counts differ.** The design has 20 skills and 15 of them ship. The five that do not ship are all
wrappers over engine code that does exist and does run. One shipped skill, `bops-benchmark-comparison`, was added
by ADR-0029 after the design was written.

**What remains open.** Whether each of the five is scheduled for a later milestone or retired from the design by
an ADR is an **owner decision**, recorded as D-13 in `project_plan.md`. This page does not make that decision,
and it does not amend `architecture.md` §4.
