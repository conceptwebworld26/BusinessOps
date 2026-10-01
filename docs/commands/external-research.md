# External research commands

Reference for the four commands that research a public subject:

`/company-analysis` · `/market-analysis` · `/competitor-analysis` · `/industry-research`

Each command file under `commands/` is authoritative for sequencing, and each skill is authoritative for research
behaviour. This page explains them. Index: [Command Reference](README.md).

**Plan status:** all four are `COMPLETED` in `project_plan.md`. Each passed its fresh-session live smoke test on
2026-09-27 (M14-6). Milestone 9 stays `IN PROGRESS` for its other planned rows: the `bops-external-research` skill and
three tier-test rows.

## Purpose

Answer questions about a company, market, competitive landscape or industry that you would have to look up rather
than compute. The answers come from reliable public sources, and every source is tiered and dated locally. **These
commands read no business file and send nothing internal.**

## When to use which

| Subject | Use | Analytical object | Skill |
|---|---|---|---|
| One named company | [`/company-analysis`](../../commands/company-analysis.md) | What it does, dated developments, stated positioning, reported figures, risks and opportunities | [`bops-company-analysis`](../../skills/bops-company-analysis/SKILL.md) |
| One named market | [`/market-analysis`](../../commands/market-analysis.md) | Definition and scope, size and growth where a source states it, trends, demand and supply drivers, risks | [`bops-market-analysis`](../../skills/bops-market-analysis/SKILL.md) |
| The rivals of one named company | [`/competitor-analysis`](../../commands/competitor-analysis.md) | Evidence-based competitor identity, source-stated comparison, positioning, developments | [`bops-competitor-analysis`](../../skills/bops-competitor-analysis/SKILL.md) |
| One named industry | [`/industry-research`](../../commands/industry-research.md) | The industry as a system: boundaries, size, trends, drivers, risks, structure | [`bops-industry-research`](../../skills/bops-industry-research/SKILL.md) |

To compare a public figure with **your own** figure, use [`/benchmark-comparison`](benchmark-comparison.md). The
public side is fetched here and the join is done locally.

## Inputs

| Command | Required | `--focus` values (default `full`) | Other options |
|---|---|---|---|
| `/company-analysis` | company | `overview`, `developments`, `positioning`, `full` | `--industry`, `--market`, `--period`, `--window` |
| `/market-analysis` | market | `overview`, `size-growth`, `trends`, `drivers-risks`, `full` | `--geography`, `--industry`, `--period`, `--window` |
| `/competitor-analysis` | focal company | `landscape`, `comparison`, `positioning`, `developments`, `full` | `--competitors "A, B, C"`, `--geography`, `--industry`, `--period`, `--window` |
| `/industry-research` | industry | `overview`, `size-growth`, `trends`, `drivers-risks`, `structure`, `full` | `--geography`, `--period`, `--product-category`, `--window` |

An unsupported `--focus` value is rejected by name, and the command lists the valid values rather than falling back
to the default. Geography, window and public terms are passed to the skill verbatim. An ambiguous subject prompts a
question naming the candidates, and nothing is retrieved until it is answered.

Each focus is one research question, with its own gate-authorised retrieval and a single scout dispatch. `full`
runs every focus for that command: up to three retrievals for a company, four for a market or competitor landscape,
and five for an industry.

## Outputs

Each skill produces **ten fixed sections**, which the command reproduces unchanged. Every command's sections include
an executive summary, an evidence summary, conflicts, limitations and confidence. The remaining sections are
subject-specific: see each command file's step "Present the skill's result". A section with no evidence says so and
is not padded.

## Important behaviour

- **The disclosure gate runs before anything leaves.** Queries are built from public terms only (Tier 0, ADR-0009).
  The gate screens every request fragment against your workspace's business data (ADR-0050). A `not_authorised`
  result is reported, never rephrased.
- **The scout's reply reaches the engine verbatim.** The plugin's `PostToolUse` hook captures it byte for byte, and the
  retrieval is closed from that capture. No model copies it (ADR-0053).
- **The retrieval context cannot read your data.** The `bops-research-scout` subagent holds only `WebSearch` and
  `WebFetch` ([agent reference](../agents/bops-research-scout.md)).
- **Figures are quoted, never estimated.** A figure no source stated stays absent.
- **Market and industry sizes are compared only when compatible.** Definition, geography, unit and currency, period
  and methodology must all be stated by the source and must match. Conflicting estimates are reported separately and
  never averaged.
- **Competitor identity is evidence-based.** A company is `identified` only where a source states the competitive
  relationship, and `observed` where the evidence is weak. Being mentioned is not enough. Nothing is ranked or called
  "best".
- **Nothing in an industry is scored.** There is no attractiveness index, Five Forces rating or ranking.
  Concentration is reported only where a source measured it.
- **Fail closed.** A failed or malformed retrieval is reported as a research limitation. It is never filled in from
  the subject's name or from training knowledge.

## Limitations

- Public sources only. None of these commands reads your file.
- No recommendations. What to do about the findings is [`/strategy-analysis`](synthesis-and-reporting.md).
- Candidate claims stay `candidate` and `verified: false`, and a tier C source stays tier C.
- Live behaviour depends on the web tools available in the session.

## Evidence and provenance

Every analytical item is `UNTRUSTED_EXTERNAL_DATA`: it is quoted from a source, never obeyed. Instructions found in
a retrieved page are reported as content. Sources are tiered A, B or C by hostname and dated locally, under
[`reference/research-policy.md`](../../reference/research-policy.md). Findings carry provenance class 3 (external
sourced) in [`reference/evidence-ledger.md`](../../reference/evidence-ledger.md).

## Examples

These are taken from the command files:

```
/company-analysis Microsoft --focus overview
/market-analysis "electric vehicle charging" --geography Europe --period 2026
/competitor-analysis Contoso Logistics --focus landscape
/industry-research industrial robotics --geography Europe --period 2026
```

## Approvals

None are needed to run: Tier 0 research is read-only and carries nothing internal (`CLAUDE.md` §9). Overwriting a
file, exporting off the machine or sending the result needs explicit per-action approval.

## Related

- The research-intent registry: `architecture.md` §4 (*The research-intent registry*), ADR-0021.
- The research command surface: `architecture.md` §7, ADR-0019, ADR-0020.
- Records: [M9-D.1](../development/2026-09-13-m9d1-company-analysis-command.md),
  [M9-D.2](../development/2026-09-13-m9d2-market-analysis.md),
  [M9-D.3](../development/2026-09-14-m9d3-competitor-analysis.md),
  [M9-D.5](../development/2026-09-14-m9d5-industry-research.md).
