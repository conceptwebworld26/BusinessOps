---
name: bops-strategy-recommendations
description: Use when asked what to do — "what should we do about the margin decline", "recommend next steps", "strategy options", "how should we respond to the competitor", "what actions follow from this analysis". Proposes class-7 recommendations grounded in a genuine strict synthesis set built from the user's own data and public research. Every recommendation states its action, cites synthesis statement ids as evidence, and gives rationale, expected benefit, risks and dependencies, with confidence derived from the evidence rather than chosen. Quotes figures only from cited evidence, carries conflicts and limitations through, and never ranks, scores, prioritises or executes anything — the decision stays with the user.
---

# Strategy Recommendations

Propose actions the evidence supports, and nothing the evidence does not. This is the one
BusinessOps capability that may issue a **provenance class 7** statement — a proposed action — so
it is also the one held most tightly to its evidence (ADR-0031).

## The rules that matter most

**1. Every recommendation cites real statements.** `evidence` is a list of synthesis statement
ids from **one** genuine strict synthesis set. The engine resolves each id; an id the set does
not hold, a SWOT point, an evidence item, a candidate claim or another recommendation is
refused. A recommendation you cannot ground in statements the set already holds is not issued.

**2. You author six fields and derive nothing.** `action`, `evidence`, `rationale`,
`expected_benefit`, `risks`, `dependencies` — exactly these, none empty, no aliases. Confidence,
support, materiality, conflicts and limitations are derived by the engine. There is no field for
confidence, priority, rank, score or weight, and supplying one is refused.

**3. Figures are quoted, never produced.** Any number in the action, rationale, expected benefit
or risks must be printed by a cited statement — same kind, same value, same currency. Write it as
the statement prints it. No new figure, gap, ratio, share, projection, uplift or estimated
benefit. If a figure cannot be quoted, describe the effect qualitatively.

**4. BusinessOps recommends; the user decides.** Nothing here is executed. Carrying an action out —
a system write, a message, an export, an overwrite — needs the user's decision and explicit
per-action approval, and financial transactions are prohibited (the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`, ADR-0010).

## What this skill does and does not do

| Does | Does not |
|---|---|
| Read a genuine strict `SynthesisSet` | Reread the file, rerun analysis, retrieve, dispatch the scout |
| Propose actions the cited statements support | Propose an action no statement supports |
| Cite statements by synthesis id | Cite prose, a source name, Business Context or another recommendation |
| Name registered assumptions as dependencies | Treat an assumption as evidence |
| Quote figures the evidence prints | Produce, round, combine or estimate a figure |
| Carry every conflict, limitation and caveat | Settle a conflict or drop a limitation |
| Present recommendations in deterministic order | Rank, score, weight or prioritise them |
| Hand a draft to the user | Execute, schedule, send or write anything |

## Input contract

**Required: a genuine strict synthesis set** — the `SynthesisSet` object a synthesis pass
produced, with `require_dimension_provenance=True`, holding at least one statement. A serialised
set, a subclass, a look-alike, a non-strict or an empty set is refused. The set is built by paths
that already exist, exactly as for `bops-swot` — this skill does not require a SWOT, and if one was
built in the same pass, reuse its set object rather than building a second:

| Side | Path |
|---|---|
| Internal | `commands.run(<analysis command>, source=…)` → `commands.internal_statements()` per domain, each under its own origin |
| External | the research skill's own gate-authorised retrieval → `research.close_retrieval_object()` → `synthesis.footed_statement()` / `register_external()` + `sourced_statement()` |
| Comparison | `commands.local_join()` where one internal figure meets one benchmark |
| Readings | `synthesis.interpretation(…, supports=[…])` |
| Assumptions | `synthesis.assumption(…)` — only for something the action genuinely depends on |

**Business Context frames; it is never evidence.** Its name, model and currency may set the set's
`subject`, `business_model` and `currency`, and it may inform which actions are relevant. It cannot
be cited, cannot satisfy the evidence minimum and cannot introduce a figure. Its private fields
never leave the machine.

## The flow

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "$(cat <<'PY'
from bops import commands as C
from bops import strategy
from bops import synthesis as S

synthesis = S.SynthesisSet(subject="<business name>", business_model="<model>",
                           currency="<ISO code>", require_dimension_provenance=True)
# ... internal statements, research statements, readings — the existing paths above ...

# Look before proposing: every statement and the role it may play.
for entry in strategy.candidates(synthesis):
    ...   # role is "evidence", "assumption" or "ineligible" (with the reason)

result = strategy.build(synthesis, [{
    "action": "<the proposed action>",
    "evidence": ["sy-…", "sy-…"],
    "rationale": "<why the cited statements lead to the action>",
    "expected_benefit": "<qualitative, or a figure a cited statement prints>",
    "risks": ["<what could make this wrong or harmful>"],
    "dependencies": [{"text": "<what must hold>", "assumption_id": "sy-…"},
                     {"text": "The cited evidence remains current and correctly scoped."}],
}])
print(strategy.render(result))
PY
)"
```

Synthesis ids are content-addressed, so a candidates pass and a build pass over the same inputs
see the same ids. `strategy.build()` is authoritative: if it refuses a proposal, report the refusal
and either fix the proposal against the evidence or leave that recommendation out.

## Writing a recommendation

**Evidence.** Cite the statements the action actually rests on — at least one fact, calculation
or sourced statement, or an interpretation whose verified chain reaches one. Several statements
and a mix of internal and external evidence are fine; each keeps its own origin, domain and trust.
Statements the set graded `unsupported` or `insufficient_evidence` cannot be cited.

**Rationale.** Explain how the cited statements lead to the action. Do not treat an incomparable
pair as comparable, and do not present a contested position as settled.

**Expected benefit.** Qualitative by default. A figure is allowed only by restating one a cited
statement prints, keeping its meaning, period and attribution.

**Risks.** At least one real risk: what could make the action wrong, costly or harmful, including
the evidence's own weaknesses (a single tier-C source, an unresolved conflict).

**Dependencies.** At least one. Every action depends on its evidence staying current and
correctly scoped; say so where nothing else applies. Where the action depends on something
assumed, register it with `synthesis.assumption()` and name it as `assumption_id` — it is disclosed,
never counted as evidence, and it makes the recommendation `LOW`.

## Confidence

**Derived, never chosen.** The engine combines the reason codes the set already derived for every
cited statement and every named assumption, and takes the weakest level with all reasons pooled.
So an unresolved conflict, an assumption, unavailable provenance or a data-quality warning makes a
recommendation `LOW`; one ordinary reason such as tier-C-only support makes it `MEDIUM`; `HIGH`
needs every cited statement to be `HIGH`. Uncertainty about the action itself belongs in `risks`,
not in a confidence you would like it to have. Present the level and its reasons exactly as
derived.

## Conflicts, uncertainty and limitations

- **Conflicts** are carried in full on every recommendation that cites a contested statement, and
  in full on the result. Neither side is chosen, averaged or preferred by tier.
- **Partially supported, incomparable, unresolved-dimension and `LOW` evidence** may be cited;
  its reasons, unresolved dimensions and limitations travel with the recommendation.
- **Limitations and caveats** — including a pseudonymisation caveat on customer or salesperson
  findings — are never dropped.
- **Materiality** is inherited, never re-judged: a recommendation is marked material when any cited
  statement is material. Material statements no recommendation cites are listed.

## Several recommendations

Several are allowed; the same action on the same evidence twice is refused. They are presented in
deterministic order — by the position of each one's earliest cited statement in the set — and that
order is **not** a ranking. Never call one the top, first, best or most important recommendation,
never number them as priorities, and never score, weight or rank them — **even when asked
directly**. The repository has no prioritisation policy, and a priority is a decision the user
makes.

## When nothing can be recommended

If no proposal can be grounded, `strategy.build(synthesis, [])` returns the explicit empty state
*"No supported recommendation identified."* Say what evidence was missing. Never write a generic
recommendation to fill the space.

## Output

`strategy.render(result)` formats the result once: heading, the human-decision statement, the
set's confidence, limitations and conflicts, then each recommendation — action, confidence and
reasons, support, the evidence with its provenance chain, rationale, expected benefit, risks,
dependencies with their assumptions, conflicts, limitations and caveats — then any material
statements not cited. The JSON form is `result.to_json()`, validated by
`lib/schemas/strategy.schema.json`; each recommendation's class-7 ledger form is
`result.claims()`.

Add nothing after it: no summary ranking, no "top priorities", no action plan with dates, no
execution step.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No synthesis set, or serialised, look-alike, non-strict or empty | Refused. Build the set through the existing paths first |
| Evidence id unknown, ambiguous, duplicated, or not a synthesis statement | Refused |
| Evidence is an assumption, or rests only on unsupported or insufficient statements | Refused |
| Interpretation with missing, later, circular, forged or assumption-backed supports | Refused |
| A field empty, missing, aliased, or an extra field (confidence, priority, score…) | Refused |
| A figure, date or number-bearing word the cited statements do not print | Refused |
| `assumption_id` that is not a registered assumption in the set | Refused |
| The set changed after the recommendations were built | Refused; build again |
| Asked which recommendation matters most, or to rank or score them | Decline; present them unranked |
| Asked to carry out a recommendation | Decline to execute; the user decides, and any action needs its own explicit approval |

**Fail closed.** Every refusal produces less output, never invented output.

Related policy: `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md` (class 7), `${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md`
(recommendation list), `${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md`, `${CLAUDE_PLUGIN_ROOT}/reference/research-policy.md`,
`${CLAUDE_PLUGIN_ROOT}/reference/ambiguity-protocol.md`, the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`, ADR-0022, ADR-0023, ADR-0030,
ADR-0031.
