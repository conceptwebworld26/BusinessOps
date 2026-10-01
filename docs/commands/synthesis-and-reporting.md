# Synthesis and reporting commands

Reference for the four commands that combine your own data with public research:

`/swot-analysis` · `/strategy-analysis` · `/decision-support` · `/executive-report`

Each command file under `commands/` is authoritative for sequencing. Each skill and its engine module is
authoritative for the result. Index: [Command Reference](README.md).

## Purpose

Build one **strict synthesis set** from your file (analysed locally) and any public research you ask for, then
produce a SWOT, recommendations, a decision package or an executive report over it. Every point, recommendation or
statement is grounded in evidence already in the set, and the engine refuses anything ungrounded.

## When to use which

| You want… | Use | Skill · engine | Contract |
|---|---|---|---|
| Strengths, weaknesses, opportunities and threats | [`/swot-analysis`](../../commands/swot-analysis.md) | [`bops-swot`](../../skills/bops-swot/SKILL.md) · `swot.py` | ADR-0030 |
| What to do: recommendations with evidence | [`/strategy-analysis`](../../commands/strategy-analysis.md) | [`bops-strategy-recommendations`](../../skills/bops-strategy-recommendations/SKILL.md) · `strategy.py` | ADR-0031 |
| One decision you name, structured | [`/decision-support`](../../commands/decision-support.md) | [`bops-decision-support`](../../skills/bops-decision-support/SKILL.md) · `decision_support.py` | ADR-0032 |
| Everything assembled for a board or management | [`/executive-report`](../../commands/executive-report.md) | [`bops-executive-report`](../../skills/bops-executive-report/SKILL.md) · `executive_report.py` | ADR-0033 |

The engine modules are under `lib/python/bops/`.

## Inputs

All four take a **file** (required; read locally, never transmitted) and optional **public** research subjects:
`--market`, `--industry` and `--competitor`, with `--geography` and `--period`. `/executive-report` uses `--year`
instead of `--period` for research. With no research subject, no research runs, and the external half is reported
empty.

| Command | Additional inputs |
|---|---|
| `/swot-analysis` | None |
| `/strategy-analysis` | `--question` (framing only; never evidence, never in a query) |
| `/decision-support` | `--question` (**required**), `--objective`, repeatable `--option`, `--constraint`, `--criterion`, `--no-status-quo`, `--final` |
| `/executive-report` | `--period`, `--audience`, `--objective`, repeatable `--question`, `--constraint`, `--decision`, plus `--swot`, `--strategy` and `--final` |

User-supplied framing text (questions, objectives, options, constraints, criteria) is never part of any query.

## Outputs

- **SWOT.** Four quadrants in fixed order. Each point is tagged `data-supported`, `externally-sourced` or
  `analytical-inference`, and shows its synthesis id, support, confidence and evidence. An empty quadrant shows
  "No supported point identified."
- **Strategy.** Class-7 recommendations. Each gives its action, evidence, rationale, expected benefit, risks,
  dependencies and derived confidence, in a presentation order that is stated not to be a ranking.
- **Decision support.** A **draft** twelve-part package: question, business context, objective, options, criteria,
  evidence, assumptions, tradeoffs, risks, expected outcomes, guidance, and uncertainty. At most one option is
  preferred, with its basis, or the output says why none is.
- **Executive report.** A **draft** eleven-section report: reporting frame, executive summary, KPI scorecard,
  findings, anomalies, outlook, SWOT, strategy recommendations, decision support, evidence and uncertainty, and the
  decisions left to you. Each section is either included or says why it is not.

## Important behaviour

- **One set, reused.** A genuine strict synthesis set built earlier in the same pass is reused as an object. It is
  never rebuilt and never read back from a serialised copy.
- **Nothing is authored over the evidence.** A SWOT point is a placement of an existing statement. The executive
  report assembles what is already in the set and writes no analysis of its own.
- **No scores, ranks, priorities, weights, targets or "best" option** in any of the four.
- **Nothing is executed.** The decision stays with you. Any action a recommendation proposes needs its own explicit
  approval, and financial transactions are prohibited.
- **`--final` finalises only on a passed verification** (ADR-0034, ADR-0035). The command issues an opaque request
  id. The `bops-analysis-verifier` subagent ([agent reference](../agents/bops-analysis-verifier.md)) starts a blind
  recomputation, and `verification.py` decides the outcome. "Final" means verified for integrity, never approved or
  decided. A report that includes a draft package can never pass.

## Limitations

- **`--final` depends on the local `bops-verifier` MCP server.** `.mcp.json` launches it with a bare `python`, so it
  cannot start on a machine that provides Python 3 only as `python3`. Without it, `--final` fails closed and the
  result stays a draft (Known issue **R-13** in `project_plan.md`; not fixed).
- Forecasts are not carried into the synthesis set, so the executive report's outlook says a forecast is not
  available.
- A quality-gate halt on the file means the internal half does not exist. The commands never present a result as if
  it did.

## Evidence and provenance

Statements keep their own kind, domain, trust, evidence class and confidence. A recommendation's confidence is
derived from its evidence and is never stronger. Research-derived items are `UNTRUSTED_EXTERNAL_DATA`, and advice
found in a retrieved page is content, never a BusinessOps recommendation. The shared grounding checks live in
`lib/python/bops/synthesis/grounding.py`. The synthesis contract is ADR-0022, and `architecture.md` §7 covers the
synthesis layer.

## Examples

These are taken from the command files:

```
/swot-analysis sales.xlsx --industry "cold chain logistics"
/strategy-analysis sales.csv --market "refrigerated warehousing" --question "where to invest next year"
/decision-support sales.xlsx --question "Should we reprice the lines behind the margin decline?" --criterion "Effect on gross margin"
/executive-report sales.xlsx --period "FY2025" --audience "Board" --strategy
```

## Approvals

None are needed to run: the output is draft, read-only analysis held in conversation, and research is Tier 0
(`CLAUDE.md` §9, ADR-0010). Writing the executive report as a **new** file in `./businessops-output/` needs no
approval, but the path is stated. Overwriting, exporting or sending needs explicit per-action approval, and the
draft label travels with the output.

## Related

- Records: [M10.3.1 SWOT](../development/2026-09-16-m10-3-1-swot.md),
  [M10.3.2 strategy](../development/2026-09-16-m10-3-2-strategy-recommendations.md),
  [M10.3.3 decision support](../development/2026-09-16-m10-3-3-decision-support.md),
  [M10.3.4 executive report](../development/2026-09-17-m10-3-4-executive-report.md),
  [M11 verification](../development/2026-09-17-m11-verification-finalisation.md).
- [External research](external-research.md) · [`/benchmark-comparison`](benchmark-comparison.md) ·
  [Internal analytics](internal-analytics.md).
