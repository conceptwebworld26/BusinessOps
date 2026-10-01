---
name: bops-executive-report
description: Use when asked for an executive report, board pack, management summary or "put it all together" view of the business — "write up an executive report", "summarise everything for the board", "give me the management report". Assembles a draft report under ADR-0033 from a genuine strict synthesis set and, where supplied, the SWOT, strategy and decision-support results built over that same set. The report has eleven fixed sections, authors no analysis, issues no recommendation, computes no confidence or score, shows every statement verbatim with its evidence, confidence and limitations, and leaves every decision to the reader.
---

# Executive Report

Put what BusinessOps has already established in front of a decision-maker, in one fixed shape, without
adding a word of analysis. The report is a **draft** until the analysis verifier finalises it
(ADR-0033).

## The rules that matter most

**1. The report assembles; it never authors.** Every business statement it shows is a statement in the
synthesis set, a class-7 record in a `StrategyResult`, or a part of a `DecisionResult` — verbatim, with
its own provenance, confidence and materiality. There is no summary prose to write. If something the
reader needs is not in those artifacts, the answer is to run the capability that produces it, not to
write it into the report.

**2. One set, and everything bound to it.** The report reads one genuine strict `SynthesisSet`. A
strategy result, SWOT or decision package is accepted only if it was built over that very set object,
and the engine checks it. KPI, anomaly, forecast, evidence and command objects are never passed to the
report: they reach it only as statements the existing translators put into the set.

**3. Nothing is authored that should be derived — or that does not exist.** No confidence, trust,
verification or lifecycle; no score, weight, rank, priority, severity, likelihood, rating, colour or
target. The framing request has no field for any of them, and supplying one is refused.

**4. The reader decides.** Nothing here is executed, sent, approved or decided. Acting on the report — a
system write, a message, an export or an overwrite — needs a person's decision and explicit per-action
approval, and financial transactions are prohibited (the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`, ADR-0010).

## What this skill does and does not do

| Does | Does not |
|---|---|
| Read one genuine strict `SynthesisSet` | Reread the file, rerun analysis, retrieve, dispatch the scout |
| Record the user's period, audience, objective, questions and constraints as framing | Infer framing, or use it to select or answer anything |
| Assemble a bound `StrategyResult`, SWOT and decision packages whole | Edit, re-grade, reorder, merge or drop a record, point or part |
| Select the executive summary by the engine's rule | Write, shorten or curate a summary |
| Show KPI rows, findings and anomalies as the set holds them | Add targets, ratings, causes or "good/bad" labels |
| State why an empty section is empty | Hide a section or fill it |
| Hand a draft to the reader | Mark it final, execute, schedule, send or write anything |

## Input contract

**Required: a genuine strict synthesis set** — the `SynthesisSet` object a synthesis pass produced, with
`require_dimension_provenance=True`, holding at least one statement, and not declared `CRITICAL`
quality. Build it through the paths that already exist; if one was built in this pass, reuse the object:

| Side | Path |
|---|---|
| Internal findings | `commands.run(<analysis command>, source=…)` → `commands.internal_statements()` per domain |
| KPIs | `commands.kpi_statements(set, run, dataset_id)` — every `KPIResult` of the run in catalogue order, bound to the run so the scorecard can be recomputed; an unavailable KPI is recorded as a limitation, never estimated. A KPI registered any other way has no recomputation basis, and the report cannot be finalised |
| Anomalies | `commands.run("anomaly-detection", source=…)` → `commands.internal_statements(set, run, synthesis.ORIGIN_ANOMALY, dataset_id)` |
| External | the research skill's gate-authorised retrieval → `research.close_retrieval_object()` → `synthesis.footed_statement()` / `register_external()` + `sourced_statement()` |
| Comparison | `commands.local_join()` |
| Readings, assumptions | `synthesis.interpretation(…, supports=[…])`, `synthesis.assumption(…)` |

**Forecasts have no path into the set.** `from_analysis_set` refuses the forecast engine's class-6
estimates, and no forecast translator is approved. So the report's outlook is `not_available`. Do not
write forecast figures into the set as text to get around this.

**Required: a framing request** — a record with any of `reporting_period`, `audience`, `objective`
(non-blank text) and `questions`, `constraints` (lists of non-blank text). `{}` is valid. Nothing else is
accepted.

**Optional, each built over the same set object:** one `StrategyResult` (`strategy.build()`), one SWOT
record (`swot.build()`), and any number of `DecisionResult`s (`decision_support.build()`) in the order
the user asked the questions. A package built with a strategy result must use the same `StrategyResult`
you pass to the report. An optional input that is invalid refuses the whole report; it is never dropped.

**Business Context frames; it is never evidence.** Its name, model and currency reach the report through
the set. It supplies no framing field and cannot be cited.

## The flow

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "$(cat <<'PY'
from bops import config
from bops import executive_report
from bops import synthesis as S

synthesis = S.SynthesisSet(subject="<business name>", business_model="<model>",
                           currency="<ISO code>", require_dimension_provenance=True)
# ... internal statements, KPIs, anomalies, research statements, readings — the paths above ...
# ... optionally: swot_record, strategy_result, [decision_result, ...] over this same object ...

report = executive_report.build(
    synthesis,
    {"reporting_period": "<the user's words>", "audience": "<the user's words>",
     "objective": "<the user's words>", "questions": ["<the user's words>"],
     "constraints": ["<the user's words>"]},          # every field optional; {} is valid
    strategy_result=strategy_result,                  # optional
    swot=swot_record,                                 # optional
    decision_results=[decision_result],               # optional, in the user's order
    config=config.resolve())                          # optional: states the thresholds applied
print(executive_report.render(report))
PY
)"
```

`executive_report.build()` is authoritative. If it refuses, report the refusal and fix the input — never
present a partly assembled report.

## The eleven sections

Always all eleven, in this order. A section with nothing to show carries a status and a fixed reason:
`empty` (the input exists and holds nothing), `not_supplied` (an optional input was not given) or
`not_available` (the set holds nothing of that kind).

| # | Section | What it shows | Possible statuses |
|---|---|---|---|
| 1 | `reporting_frame` | Draft label; data-quality warning before any figure; subject, model, currency, as-of; the user's framing; datasets and research registered; thresholds applied and their layer | `included` |
| 2 | `executive_summary` | Every material statement that can be read as evidence or verified interpretation, verbatim, in set order; ids of material statements not supported; how many statements have no materiality verdict; strategy records by id and action; each package's question, lifecycle and preference or no-preference reason; the set's confidence; the status of sections 3 and 5–9 | `included` |
| 3 | `kpi_scorecard` | One row per registered KPI, in catalogue order: status, value, the statement's confidence and materiality, prior and change only if the statement carries them, reasons for unavailable KPIs | `included`, `not_available` |
| 4 | `findings` | Other evidential statements, then interpretations, in set order | `included`, `empty` |
| 5 | `anomalies` | Anomaly statements with the engine's investigation note and the finding they resolve to — its metric, period, observed value, baseline and deviation as the engine computed them | `included`, `empty`, `not_available` |
| 6 | `outlook` | Nothing until a forecast translator is approved | `not_available` |
| 7 | `swot` | The SWOT whole | `included`, `empty`, `not_supplied` |
| 8 | `strategy_recommendations` | The strategy result whole, in its own order | `included`, `empty`, `not_supplied` |
| 9 | `decision_support` | Each package whole, labelled `draft — unverified` | `included`, `not_supplied` |
| 10 | `evidence_and_uncertainty` | The set's confidence, each component's own confidence labelled with its owner, conflicts, limitations, assumptions, statements not supported with the reason, unresolved dimensions | `included` |
| 11 | `decisions_for_the_reader` | The human-decision statement; open decision questions; recommendation ids awaiting a decision; package next steps by reference | `included` |

**Not in the report, even when asked:** "what is going well" or "what needs attention" (a SWOT is the
place for favourable and unfavourable points), a standalone risks or opportunities list, an overall or
health score, KPI ratings, colours or targets, "top", "best" or "key" picks, severity or likelihood, an
action plan with owners or dates.

## Provenance, confidence and materiality

- **Evidence** is only what the set can ground: facts, calculations, sourced statements and
  interpretations whose supports verify. **Framing, Business Context, assumptions, recommendation
  records and decision-package parts are never evidence**, and the report never shows them as such.
- **Each confidence belongs to its owner.** Statements, records and packages keep their own; the set's
  confidence is labelled as the set's. The report has no confidence of its own.
- **Materiality is inherited.** The summary rule uses each statement's upstream verdict; nothing is
  re-judged, and statements with no verdict are counted, not guessed.
- **Conflicts and limitations are carried whole**; unavailable KPIs and statements the evidence does not
  support are shown with their reasons. Absence is stated, never filled.
- **Anomalies are measured deviations**, not explanations: no cause, and never fraud, error or theft.

## Order

Sections are fixed; KPIs follow the catalogue; statements follow the set; SWOT points, records and
package parts keep their own results' order; packages appear in the order supplied. The report says so,
and none of it is a ranking — **even when asked** which item matters most.

## Lifecycle

`executive_report.build()` produces a `draft`, `unverified` report and has no path to `final`. A decision
package is shown with the lifecycle it carries.

## Finalisation (M11)

A report becomes `final` only through `verification.py` (ADR-0034, ADR-0035), and only when asked for.
This skill decides nothing about it:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "$(cat <<'PY'
from bops import verification

request_id = verification.issue_recomputation(report)   # an opaque id, or None
# ... the command dispatches businessops:bops-analysis-verifier with ONLY request_id and keeps its
# reply verbatim; the draft is then rebuilt with exactly the same inputs in a new process ...
result = verification.verify(report, reply)                # every check deterministic
if result.passed:
    final = verification.finalise(report, result)          # lifecycle fields change, nothing else
print(verification.render(result))
PY
)"
```

- **Only a passed verification finalises**, and every finding blocks. A failed verification leaves the
  draft exactly as it was; nothing is repaired, retried with changes, or described as a warning.
- **Figures are recomputed blind.** The agent receives only the request id and holds one tool; it never
  sees the data, a path or a figure, and `verify()` alone compares.
- **Final means verified for integrity** - never that anything was approved, chosen, decided or
  authorised.
- **A final report may not contain a draft package.** Finalise each package first, then build the report over the final packages; issue every request before any agent is dispatched. `report_id` is unchanged by finalisation.

## Output

`executive_report.render(report)` formats the report once. The JSON form is `report.to_json()`, validated
by `lib/schemas/executive_report.schema.json`. The report is bound to the set and to every result it
assembles: if any of them changes, serialising it is refused and it must be built again. It never
re-enters the synthesis set.

Add nothing after it: no closing summary, no "key takeaways", no ranking, no action plan, no claim that
the report is final or that anything was decided.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No synthesis set, or serialised, look-alike, non-strict, empty or `CRITICAL` | Refused. Build the set through the existing paths first |
| A framing field that is unknown, blank, duplicated, or carries confidence, trust, lifecycle, score, target or the like | Refused |
| A strategy result, SWOT or decision package that is serialised, a look-alike, built over another set, or since changed | Refused |
| Two strategy results or two SWOTs; the same decision package twice; a package built with a different strategy result | Refused |
| A SWOT whose placements do not rebuild it exactly | Refused |
| A statement id that is unknown or identifies more than one statement | Refused |
| The set or an assembled result changed after the report was built | Serialising is refused; build again |
| Asked for a score, rating, target, ranking or "top" items | Decline; present the report as built |
| Asked to finalise the report | Only through the finalisation flow above, and only when verification passes |
| Asked to send, export or act on the report | Decline without explicit per-action approval |

**Fail closed.** Every refusal produces no report, never a partial or invented one.

Related policy: `${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md` (executive report), `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md`,
`${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md`, `${CLAUDE_PLUGIN_ROOT}/reference/research-policy.md`, the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`,
ADR-0010, ADR-0022, ADR-0030, ADR-0031, ADR-0032, ADR-0033.
