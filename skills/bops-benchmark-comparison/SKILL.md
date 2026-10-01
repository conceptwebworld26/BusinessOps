---
name: bops-benchmark-comparison
description: Use when a question compares the user's own figure with a public benchmark — "is our gross margin typical", "how does our revenue compare with the industry", "are we above or below average for our sector". Computes the internal figure from the user's own file through the existing analysis commands, retrieves the public benchmark through the existing disclosure gate and research seam using public terms only, and joins the two **locally**. The internal figure never enters a query and never leaves the machine. Reports whether the two measure the same quantity, and nothing beyond that — no ranking, no score, no verdict on whether the business is doing well, and no recommendation.
---

# Benchmark Comparison

Answer one comparative question by fetching the public side and joining it to the user's own
figure **here**, on this machine. This is the local join ADR-0009 makes the default: *"is our
margin typical?"* is a question about the industry, so the query is about the industry.

## The rule that matters most

**The internal figure is never part of the question you ask.** Not in the query text, not as
a "for context" aside, not rounded, not banded, not as a range, not as "roughly". The
benchmark is retrieved by asking what is typical for a public industry, market or category —
and the comparison happens afterwards, locally, when both numbers are already here.

If you ever find yourself wanting to send the internal number to get a better benchmark, the
answer is no, and the reason is not caution: a benchmark that was chosen to sit near our
number is not a benchmark, it is a mirror.

The second rule: **this skill compares; it does not judge.** "Our margin is 34.9% and the
benchmark is 31.2%, on the same definition, period, geography, basis and currency" is the
output. "We are outperforming" is not. Whether being above or below a benchmark is good,
bad, expected or irrelevant is a judgement about the business, and it needs evidence,
rationale, risks and dependencies this skill does not have.

The third rule: **two figures are not comparable until the engine says so.** A benchmark on
a different definition, period, geography, scope, basis or currency is a different quantity.
The seven-dimension test decides, it fails on unknown rather than assuming a match, and an
`incompatible` result is a finding worth reporting — not a problem to work around.

## What this skill does and does not do

| Does | Does not |
|---|---|
| Compute the internal figure through the existing analysis commands | Recompute a KPI, or invent one the engine did not produce |
| Retrieve the benchmark through the existing gate and research seam | Build a second retrieval pipeline, or send anything internal |
| Foot the external figure through the existing strict seam | Author a second footing mechanism |
| Join the two locally, after retrieval | Transmit, band, round or hint at the internal value |
| Report what the seven-dimension test found | Average, convert, combine or rewrite either figure |
| Say plainly when the two are not comparable | Present an incomparable pair as a comparison anyway |
| Keep internal and external provenance separate | Let either side inherit the other's trust or evidence |
| Stop at description | Rank, score, grade, or say whether the business is doing well |

**No recommendations.** A recommendation is provenance class 7 and needs evidence,
rationale, expected benefit, risks, dependencies and confidence — all six. This skill stops
at description. What to *do* about a gap is `bops-strategy-recommendations`; say so and offer
the comparison instead.

**No verdicts.** "Better", "worse", "underperforming", "outperforming", "healthy",
"concerning" and "we should be worried" are judgements, not comparisons. They do not appear
in this skill's own voice, even when the gap is large and even when asked directly.

## Input contract

| Input | Required | Notes |
|---|---|---|
| `source` | **yes** | The user's spreadsheet or CSV. Read locally; never transmitted |
| `metric` | **yes** | Which internal figure to compare — `revenue`, `gross_profit`, `gross_margin`, and so on. It must be one the engine actually computed |
| `benchmark_subject` | **yes** | The **public** thing to retrieve a benchmark for — an industry, market or product category. Never the user's own company unless that company is genuinely public |
| `category` | recommended | `industry`, `market`, `competitor` or `company` — which research question the benchmark is |
| `industry`, `geographic_market`, `period`, `product_category` | optional | Public disambiguating terms. They sharpen the query and cost nothing |

**The benchmark subject is public by construction.** It names a sector, a market or a
category — the thing a published figure would be *about*. If the only way to describe what
you want a benchmark for is to describe the user's own business in enough detail to identify
it, stop and ask; that is a re-identification risk, not a query.

## The flow

Two independent halves, joined at the end. **Retrieve first, join second** — always in that
order, because the join is what makes the internal number relevant and it must not be able
to influence what was asked.

```
PUBLIC HALF   open_retrieval (GATE) → one scout dispatch → close_retrieval_object
                  → genuine EvidenceSet → strict footing

LOCAL HALF    commands.run(<analysis command>, source=…) → genuine CommandResult
                  → AnalysisSet / KPIResult

JOIN          local_join(...) → one strict SynthesisSet → compare_values()
```

`reply_text` is the scout's reply exactly as the harness captured it (ADR-0053), read with
`R.handback_reply('<operation>')`. Never copy, write or retype it yourself, and never trim or extract it. The rule,
and why, is *Close from the harness's verbatim capture* in `skills/bops-market-analysis/SKILL.md`.

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "$(cat <<'PY'
from decimal import Decimal
from bops import commands as C
from bops import research as R
from bops import synthesis as S

# 1. The public half. Public terms only; the gate sees the whole query.
reply_text = R.handback_reply("<operation>")   # the harness's verbatim capture, never a copy
retrieval = R.close_retrieval_object(reply_text, "<public benchmark subject>", R.INDUSTRY,
                                     intent=R.BENCHMARK, public_terms={...},
                                     operation="benchmark-comparison-<subject>-<date>")
benchmark = retrieval["evidence_set"].items[0]

# 2. The local half. The user's own file, read here, never transmitted.
run = C.run("profitability-analysis", source="<their file>")

# 3. The join. After retrieval, on this machine.
joined = C.local_join(
    run, retrieval, S.ORIGIN_INDUSTRY, "<the source's own sentence>", benchmark.id,
    dataset_id="<a local id for their file>", internal_metric="revenue",
    internal_dimensions={"metric_definition": "<what our figure counts>",
                         "period": "<the period our figure covers>",
                         "geography": "<the territory our figure covers>",
                         "scope": "<which slice of the business>",
                         "methodology": "<how our figure was computed>"},
    stated={ ...the six quoted dimensions the benchmark source states... },
    metric="revenue", observed=Decimal("3.47"), source_unit="USD million")

joined.comparison    # the seven-dimension record: matched, mismatched, unknown
joined.compatible    # whether the two measure the same quantity. Not a verdict
PY
)"
```

`C.local_join()` is sequencing. It calls the existing internal translators
(`from_analysis_set`, `from_kpi_result`), the existing external seam
(`footed_statement`, which calls `source_footings`), and the existing `compare_values()`. It
computes nothing, foots nothing itself, and holds no privacy rule — it cannot construct a
query, because it imports nothing that could.

**`internal_dimensions` describes our own figure, and stays here.** It tells the comparison
what our number counts, over what period, territory, slice and method — the same seven
dimensions the benchmark must match. It is never transmitted; it exists so the engine can
refuse a comparison rather than assume one.

## Choosing the internal metric

Name a metric the engine computed. `local_join` refuses a metric no finding carries, and
refuses an ambiguous one where the run produced the same metric for several periods — narrow
the run or name the period rather than comparing an arbitrary pair.

**An unavailable KPI is a limitation, not a zero.** Where the supplied file cannot support
the metric, the engine says so and the comparison does not happen. Report which field was
missing. Never substitute a related metric because it is available.

## What the engine compares

The seven dimensions, all of which must match:

| Dimension | Our side | Their side |
|---|---|---|
| `metric_definition` | what our figure counts, stated by us | what the source says its figure counts |
| `period` | the period our figure covers | the period the source states |
| `geography` | the territory our figure covers | the territory the source states |
| `currency` | the currency the engine computed in | the ISO code the source's excerpt prints |
| `unit` | the quantity type the engine produced | the quantity type ADR-0025 read from the notation |
| `scope` | which slice of our business | which slice the source measured |
| `methodology` | how our figure was computed | how the source says theirs was |

**Our side is engine-footed; their side must be source-footed.** Our figure rests on the
registered dataset it was computed from (ADR-0023) and carries no dimension provenance —
that asymmetry is deliberate: our number rests on our data, and a published number rests on
what its publisher printed. Their figure reaches the check only where a footing shows the
source stated the dimension, and a dimension no source stated stays unknown.

**A percentage metric cannot currently reach `compatible`.** `currency` is meaningless for a
margin or a growth rate, so it is unstated on both sides — and the test treats unstated as
`unknown`, never as a match. A margin comparison therefore comes back `unknown` on
`currency` today. Report that honestly: the two margins are shown side by side with the
limitation stated, and the pair is not described as comparable. Do not supply a currency to
make the unknown go away; that is the fabrication the whole mechanism exists to prevent.

## Reporting the result

Fixed section order. A section with nothing to say says so and is not padded.

| # | Section | Contains |
|---|---|---|
| 1 | The comparison | Both figures, each with its own definition, period, geography, scope, basis and source. Never a single blended number |
| 2 | Comparability | What the seven-dimension test found: which dimensions matched, which differed, which were unstated and why |
| 3 | Our figure | The internal value, the metric, the file it came from, the period, and the analysis command that produced it |
| 4 | The benchmark | The external value, quoted with its source, publication date, local tier and freshness |
| 5 | Limitations | Unstated dimensions, unavailable metrics, quality caveats, thin or dated evidence |
| 6 | Confidence | `HIGH` / `MEDIUM` / `LOW`, from the evidence, with the support assessment behind it |

**Both figures always appear separately.** There is no combined figure, no ratio, no
percentage gap presented as a finding, no midpoint and no "we are X% above". If a reader
wants the arithmetic they can do it; this skill's job is to establish whether the arithmetic
would mean anything.

**An `incompatible` or `unknown` result is a complete answer.** "Our figure and this
benchmark are not measuring the same quantity — the source sized value added and we computed
revenue" is more useful than a comparison that quietly equates them.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No file given | Ask for one. Do not retrieve, and do not describe a benchmark alone as a comparison |
| No metric given | Ask which figure to compare. Never pick one |
| Metric not computed on this file | Say which field was missing. Never substitute a related metric |
| Metric ambiguous across periods | Ask which period. Do not compare an arbitrary pair |
| Benchmark subject would identify the user's business | Stop and ask. Re-identification is a disclosure, whatever the field is called |
| Gate returns `not_authorised` | Report the refusal and any alternative it offered. Never rephrase to get a different answer, and never add internal context to get a better result |
| Retrieval failed, blocked or returned nothing citable | Report it. The internal figure stays local and **no fallback transmission of any kind occurs** |
| Benchmark states fewer than seven dimensions | Report the pair as not comparable, naming the unstated dimensions. Never supply them |
| Sources conflict | Preserve each with its definition, declare the conflict, lower confidence |
| Figures are comparable but differ | Report both with the difference stated as an observation. Never as a verdict |
| Asked whether the business is doing well | Decline; that is a judgement. Present the comparison |
| Asked what to do about the gap | Decline; name `bops-strategy-recommendations` |
| Asked to send the internal figure to get a closer benchmark | Refuse. It is a Tier-2 disclosure at best and a mirror at worst |

**Fail closed.** Every one of these produces less output, never invented output, and never a
disclosure that was not already authorised.

Related policy: `${CLAUDE_PLUGIN_ROOT}/reference/research-policy.md`, `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md`,
`${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md`, the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`, ADR-0009 (the four-tier
disclosure model), ADR-0023 (internal footing), ADR-0026 and ADR-0028 (dimension footing).
