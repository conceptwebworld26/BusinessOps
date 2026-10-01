# /benchmark-comparison

Reference for `/benchmark-comparison`. The authoritative specification is
[`commands/benchmark-comparison.md`](../../commands/benchmark-comparison.md), and the analytical behaviour lives in
[`bops-benchmark-comparison`](../../skills/bops-benchmark-comparison/SKILL.md). Index: [Command Reference](README.md).

## Purpose

Answer "is our figure typical?" The command computes one figure from your own file, retrieves a public benchmark
for a public subject, and sets the two side by side **on this machine**. Your figure is never part of the query and
never leaves the machine. This is the local join surface of ADR-0029.

## When to use it

- "Is our gross margin typical for cold chain logistics?"
- "How does our revenue compare with the industry?"

For public research on its own, use the [external research](external-research.md) commands. For your own data on
its own, use the [internal analytics](internal-analytics.md) commands.

## Inputs

| Input | Required | Notes |
|---|---|---|
| file | yes | Read locally. With no file there is no comparison, and a benchmark is never presented alone |
| `--metric` | yes | Which internal figure to compare. Never picked for you |
| `--benchmark` | yes | The **public** subject: an industry, market or category |
| `--category` | no | `industry`, `market`, `competitor` or `company` |
| `--industry`, `--geography`, `--period` | no | Public disambiguating terms |

If describing the benchmark subject would identify your business, the command stops and asks before anything is
retrieved.

## Outputs

The skill produces six fixed sections: the comparison, comparability, our figure, the benchmark, limitations and
confidence. **Both figures always appear separately.** There is no blended figure, midpoint, ratio or gap presented
as a finding.

## Important behaviour

- **The public half runs first, and the two halves stay independent.** The internal figure never informs the query:
  not in full, rounded, banded, as a range or as context.
- **The seven-dimension test.** Two figures are comparable only when all seven dimensions match: `metric_definition`,
  `period`, `geography`, `currency`, `unit`, `scope` and `methodology`. Our side is footed by the engine, and the
  benchmark's side must be stated by its source. A dimension the source did not state is *unknown*, and an unknown
  dimension makes the pair not comparable. It is never filled in.
- **No fallback disclosure.** If the gate refuses, or retrieval fails or returns nothing citable, the run reports
  that and stops. Nothing internal is ever sent instead.
- **No verdict, score or ranking.** Being above or below a benchmark is reported as an observation, never as good or
  bad.

## Limitations

- One internal figure against one public benchmark per run.
- The metric must be computable from the file. A missing field is named, and no related metric is substituted.
- What to do about a difference is [`/strategy-analysis`](synthesis-and-reporting.md).

## Evidence and provenance

The internal figure stays a `[CALCULATION]` on your own data. The benchmark stays `[FACT/SOURCED]`: external,
untrusted, unverified, and tiered under [`reference/research-policy.md`](../../reference/research-policy.md).
Neither side inherits the other's provenance because the two were compared.

## Examples

These are taken from the command file:

```
/benchmark-comparison sales.xlsx --metric revenue --benchmark "cold chain logistics"
/benchmark-comparison sales.csv --metric gross_profit --benchmark "specialty retail" --period 2025
```

## Approvals

None are needed to run. The benchmark query is Tier 0 and the join is local, so nothing crosses the boundary
(`CLAUDE.md` §9, ADR-0009). Overwriting a file, exporting off the machine or sending the result needs explicit
per-action approval.

## Related

- ADR-0029 (the local join surface) and [its record](../development/2026-09-16-m10-2r14-local-join.md).
- ADR-0025 (units) and ADR-0026 (dimension provenance).
- [Synthesis and reporting](synthesis-and-reporting.md): a strict synthesis set built here can be reused by the
  synthesis commands in the same pass.
