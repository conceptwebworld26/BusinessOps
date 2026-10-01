---
name: bops-swot
description: Use when asked for a SWOT — strengths, weaknesses, opportunities and threats — over the user's own business data and the public research around it. Reads a genuine strict synthesis set built by the existing analysis and research paths and places statements already in it into four quadrants, each point tagged data-supported, externally-sourced or analytical-inference and traced to the statements it rests on. Adds no evidence of its own, never pads an empty quadrant, carries conflicts, limitations and confidence through unchanged, and issues no recommendation, ranking, score or priority. Trigger phrases include "SWOT", "strengths and weaknesses", "opportunities and threats", "where do we stand", "situation analysis".
---

# SWOT

Read the synthesis set and place what it already says into four quadrants. That is the whole
skill: **a SWOT point is a statement the set already holds, placed.** It has no text of its
own, so it cannot carry a claim nobody grounded, and it cannot carry advice.

## The three rules that matter most

**1. No point without a statement.** Every point names one `synthesis_id` in the set. A point
you would like to make that is not already a statement is either a reading of statements that
are — author it with `synthesis.interpretation()` first, naming what it rests on — or it is not
a point. There is no free-text field to put it in, by design.

**2. The tag is read, never chosen.** The statement's kind decides it:

| Statement kind | Domain | Tag |
|---|---|---|
| `FACT`, `CALCULATION` | internal | `data-supported` |
| `SOURCED` | external | `externally-sourced` |
| `INTERPRETATION` with supports in the set | either | `analytical-inference` |

`ASSUMPTION` has no tag and is never a point. A placement whose tag disagrees with the kind is
refused, not corrected — an interpretation is never presented as a fact, and a source's
wording is never presented as our data.

**3. This skill stops at description.** Strengths, weaknesses, opportunities and threats are
readings of evidence. What to *do* about any of them is a recommendation — provenance class 7,
requiring evidence, rationale, expected benefit, risks, dependencies and confidence — and that
is `bops-strategy-recommendations`. Say so and offer the SWOT instead.

## What this skill does and does not do

| Does | Does not |
|---|---|
| Read a genuine strict `SynthesisSet` | Reread the file, rerun the KPI engine or any analysis |
| Place existing statements into quadrants | Write a point that is not a statement in the set |
| Author readings through `synthesis.interpretation()` | Author a reading that names no supporting statements |
| Carry each statement's support, confidence, conflicts, materiality, limitations and caveats | Upgrade, soften, re-grade or drop any of them |
| Show an explicit empty state for an empty quadrant | Pad a quadrant so it looks complete |
| Keep points in the order the analysis produced them | Rank, score, weight, prioritise or pick a winner |
| Consume research the existing research skills retrieved | Search, fetch, dispatch the scout, or build evidence |

**No recommendations, in any form.** No action plan, no next steps, no "should", no prioritised
list, no investment view, no "key opportunity to pursue". **No ranking or scoring.** No
opportunity attractiveness score, no threat severity rating, no quadrant weighting, no
"biggest strength", no winner or loser — declined even when asked directly, for the reason
`bops-competitor-analysis` declines a ranking: a score is a decision presented as an
observation.

## Input contract

**Required: a genuine strict synthesis set.** The `SynthesisSet` object a synthesis pass
produced, built with `require_dimension_provenance=True`, holding at least one statement. A
serialised set, a dict, a subclass, a look-alike or a non-strict set is refused by
`swot.build()`, because each would carry support and confidence as data nothing graded.

The set is built by paths that already exist, and this skill reuses them unchanged:

| Side | Path | Owns |
|---|---|---|
| Internal | `commands.run(<analysis command>, source=…)` → `commands.internal_statements()` → `from_analysis_set()` / `from_kpi_result()` | The figures, materiality, caveats (ADR-0023) |
| External | the research skill's own gate-authorised retrieval → `research.close_retrieval_object()` → `synthesis.footed_statement()` for a figure, `register_external()` + `sourced_statement()` for a qualitative reading of a source | Tiering, freshness, footing, conflicts (ADR-0024, ADR-0028) |
| Readings | `synthesis.interpretation(…, supports=[…])` | Traceable supports; advisory wording refused |

Translate each internal analysis under **its own origin** — `ORIGIN_SALES` for sales,
`ORIGIN_CUSTOMER` for customer and so on — so two domains stating the same sentence remain two
statements. A statement id that identifies more than one item is refused as ambiguous.

**Business Context frames; it is never evidence.** Its business name, model and currency may
set the set's `subject`, `business_model` and `currency`, which head the SWOT. None of it is a
statement and none of it can be placed. Its public industry and geography may sharpen a
research question exactly as the research skills already allow; nothing classified above
`public` reaches a query (the disclosure tiers in `${CLAUDE_PLUGIN_ROOT}/reference/research-policy.md`).

## The flow

`reply_text` is the scout's reply exactly as the harness captured it (ADR-0053), read with
`R.handback_reply('<operation>')`. Never copy, write or retype it yourself, and never trim or extract it. The rule,
and why, is *Close from the harness's verbatim capture* in `skills/bops-market-analysis/SKILL.md`.

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "$(cat <<'PY'
from bops import commands as C
from bops import research as R
from bops import synthesis as S
from bops import swot

synthesis = S.SynthesisSet(subject="<business name>", business_model="<model>",
                           currency="<ISO code>", require_dimension_provenance=True)

# Internal half — the user's own file, read here, never transmitted.
run = C.run("business-health", source="<their file>")
for domain, origin in (("sales", S.ORIGIN_SALES), ("customer", S.ORIGIN_CUSTOMER),
                       ("product", S.ORIGIN_PRODUCT), ("financial", S.ORIGIN_FINANCIAL)):
    if domain in run.analysis_keys:
        C.internal_statements(synthesis, run, origin, "<local dataset id>", domains=[domain])

# External half — the reply the research skill's own dispatch returned, closed locally.
reply_text = R.handback_reply("<operation>")   # the harness's verbatim capture, never a copy
retrieval = R.close_retrieval_object(reply_text, "<public subject>", R.MARKET,
                                     intent=R.TRENDS, public_terms={...},
                                     operation="<the research skill's operation>")
evidence = S.evidence_from_retrieval(retrieval)
S.register_external(synthesis, evidence, S.ORIGIN_MARKET)
S.sourced_statement(synthesis, S.ORIGIN_MARKET, "<what the source said>",
                    evidence_ids=[evidence.items[0].id])

# A reading, only where one is warranted, naming what it rests on.
S.interpretation(synthesis, S.ORIGIN_MARKET, "<the reading>", supports=["sy-…", "sy-…"])

# Look before placing: every statement, its tag, and the quadrants it may sit in.
for entry in swot.candidates(synthesis):
    ...

result = swot.build(synthesis, [
    {"quadrant": swot.STRENGTHS, "tag": swot.DATA_SUPPORTED, "synthesis_id": "sy-…"},
    {"quadrant": swot.THREATS, "tag": swot.EXTERNALLY_SOURCED, "synthesis_id": "sy-…"},
])
print(swot.render(result))
PY
)"
```

Synthesis ids are content-addressed, so a first pass that prints `swot.candidates()` gives ids
that a second pass over the same inputs reproduces exactly.

## Placing a statement

**Which quadrant is your judgement; whether it is grounded is the engine's.**

| Quadrant | Describes | May hold |
|---|---|---|
| Strengths | Favourable internal capabilities or results the evidence shows | `data-supported`; `analytical-inference` resting on at least one internal statement |
| Weaknesses | Unfavourable internal limitations or results the evidence shows | the same |
| Opportunities | External conditions or developments that may create favourable possibilities | `externally-sourced`; `analytical-inference` resting on at least one external statement |
| Threats | External conditions or developments that may create adverse exposure | the same |

An inference may rest on internal, external or mixed statements; what it may not do is sit on
a side none of its evidence is on. `swot.candidates()` lists, for each statement, the quadrants
it may occupy.

**Favourable or unfavourable is a reading, so read carefully.** A movement is not a strength
because it is large; a sourced trend is not an opportunity because it is growth. Where the
direction genuinely depends on something the set does not say, leave the statement unplaced
rather than guessing a quadrant. **One statement is one point**: placing it twice — in two
quadrants or twice in one — is refused.

**Material statements are not re-judged.** Materiality came from the configured policy
upstream and travels on the point unchanged. A material statement you leave unplaced is listed
under `material_not_placed`, so the omission is visible; say why it was left out.

**Prefer aggregates.** Where a finding names a customer or salesperson, its caveat already says
the result is for local use and must be pseudonymised before it is shared. That caveat travels
on the point; do not strip it, and prefer an aggregate statement where one says the same thing.

## Uncertainty, conflicts and limitations

Carried, never resolved. `swot.build()` copies them from the set; do not summarise them away.

- **Confidence** is the synthesis layer's `HIGH` / `MEDIUM` / `LOW` with its named reason codes —
  per point, and for the set as a whole. Do not restate it in stronger or weaker words.
- **`partially_supported`** statements may be placed and keep their lowered confidence.
  **`unsupported`** and **`insufficient_evidence`** statements are refused as points.
- **Conflicts** appear on every point they touch (`conflict_refs`) and in full in the result.
  Two sources that disagree are both reported; neither is chosen, averaged or preferred by tier.
- **Unresolved dimensions** on a footed figure are shown with their reason codes. An
  `incompatible` or `unknown` comparison stays exactly that, with its limitation.
- **Limitations** — unavailable KPIs, incomparable values, unresolved conflicts, data-quality
  warnings — are all carried, at the same prominence as the quadrants.

## Empty quadrants

**An empty quadrant says so.** It carries *"No supported point identified."* and nothing else.
No research was requested, the research returned nothing citable, or nothing in the evidence
reads as favourable or adverse — each is a complete answer. Never borrow a statement from the
other side, soften a threshold or write a generic point to fill the space.

## Human review

The result states that quadrant placement is an analytical judgement requiring human review
and that BusinessOps checked only its grounding. Keep that statement. Present the SWOT as a
structured reading of evidence for a person to assess, not as a conclusion.

## Output

`swot.render(result)` formats the result once: heading, confidence, limitations, conflicts,
then the four quadrants in fixed order — each point with its tag, statement, id, kind, domain,
support, confidence, the provenance chain it rests on (with source, tier and date for external
evidence), the statements an inference reads, confidence reasons, contested conflicts,
unresolved dimensions and caveats — then any material statements not placed, then the
human-review note.

Add nothing after it: no summary, no key takeaways, no recommendations, no next steps, no
ranking. The JSON form is `swot.to_json(result)`, validated by `lib/schemas/swot.schema.json`.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No synthesis set, or it is serialised, a look-alike, non-strict or empty | Refused. Build the set through the existing paths first |
| Statement id not in the set, or ambiguous | Refused. Never guess which statement was meant |
| Tag disagrees with the statement's kind | Refused, never relabelled |
| Internal statement in Opportunities/Threats, or external in Strengths/Weaknesses | Refused |
| Interpretation with no supports, forged supports, a later or circular support, or an assumption behind it | Refused |
| Statement graded `unsupported` or `insufficient_evidence` | Refused as a point |
| Placement carrying text, a score, rank, priority or recommendation | Refused — a placement has three fields |
| Retrieval refused, failed or returned nothing citable | Opportunities and Threats stay empty and say so; nothing internal is sent as a fallback |
| Asked which point matters most, or to score the quadrants | Decline; present the SWOT unranked |
| Asked what to do about a weakness or threat | Decline; name `bops-strategy-recommendations` |

**Fail closed.** Every refusal produces less output, never invented output.

Related policy: `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md` (classes and confidence),
`${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md`, `${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md`,
`${CLAUDE_PLUGIN_ROOT}/reference/research-policy.md`, `${CLAUDE_PLUGIN_ROOT}/reference/ambiguity-protocol.md`, the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`, ADR-0022 (the synthesis contract), ADR-0023 (internal footing), ADR-0028 (strict
footing path), ADR-0029 (the local join), ADR-0030 (SWOT reads the synthesis set).
