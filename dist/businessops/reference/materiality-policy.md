# Reference — Materiality Policy

**Owns:** what counts as a material change, and how thresholds resolve.
**Consulted by:** every comparison and every skill that ranks or filters findings.
**Does not own:** threshold arithmetic (the engine, `lib/python/bops/`), or where
configuration comes from (`config.py` precedence).

---

## Thresholds

Five configurable thresholds, resolved through the precedence chain
**command argument → project business context → user business context → shipped defaults**:

| Threshold | Default | Applies to |
|---|---|---|
| `absolute_amount` | 10,000 | Movement in the reporting currency |
| `percentage` | 5.0% | Relative change period over period |
| `kpi_deviation` | 10.0% | A KPI against its prior period |
| `revenue_percentage` | 1.0% | An item's share of total revenue |
| `margin_percentage_points` | 2.0pp | Margin movement, in points not percent |

**Never hard-code a threshold** where configuration exists. If a user has set a value, it
wins — including when it seems too loose or too tight.

## How a change is judged

A change is material if it crosses **any** applicable threshold. Absolute and relative are
tested together, because either alone misleads:

- Relative alone: a 40% rise on a £200 line is noise.
- Absolute alone: a £12,000 move is trivial for a £40m business and existential for a
  £300k one.

Where Business Context supplies a size band or revenue scale, prefer the revenue-relative
test for ranking.

## Margins are points, not percents

A margin moving 35% → 32% is **3 percentage points**, not "a 8.6% decline". Report
percentage points and label them `pp`. Conflating the two is a reporting error.

## Materiality filters, it does not halt

Step 10 of the [analysis framework](analysis-framework.md) filters what is *reported*. It
never stops a workflow — that is the quality gate's job.

## Immaterial does not mean invisible

An immaterial item is excluded from headline findings, not deleted. If a user asks about
it, report it. If many immaterial items share a direction, that pattern is itself
potentially material and should be surfaced as an aggregate.

## Say which threshold fired

When something is reported as material, state the threshold that made it so and where that
threshold came from (`project context` or `shipped default`). A user must be able to
re-run with a different threshold and understand why the answer changed.
