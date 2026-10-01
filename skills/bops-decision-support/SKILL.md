---
name: bops-decision-support
description: Use when the user faces a specific decision — "should we reprice or cut costs", "help me decide between these options", "what are the tradeoffs of expanding", "build a decision package for this choice". Structures one user-supplied decision question into ADR-0032's twelve-part draft package over a genuine strict synthesis set built from the user's own data and public research. Options, criteria, objective and constraints come from the user; every tradeoff, risk and outcome cites synthesis statement ids; recommendations are class-7 records; confidence is derived, never chosen. Quotes figures only from cited evidence, prefers at most one option and only when criteria and a grounded recommendation support it, and never scores, ranks or executes anything — the decision stays with the user.
---

# Decision Support

Lay out one decision so a person can make it: what is being decided, the options, what matters,
what the evidence says about each option, what could go wrong, and what is still unknown. The
package is a **draft** until the analysis verifier finalises it, and it never makes the decision
(ADR-0032).

## The rules that matter most

**1. The user frames; the evidence supports.** The decision question, objective, constraints,
options and criteria are the user's words, stored verbatim with `origin: "user"`. They are never
evidence, never inferred, never rewritten, and never leave the machine. If there is no question,
or it is unclear what single decision is being made, **ask** — do not build a package around a
guess. The engine checks only that a question is present and non-blank; judging its meaning is
yours.

**2. Every claim about an option cites real statements.** A tradeoff and an expected outcome cite
at least one synthesis statement id from **one** genuine strict synthesis set; a risk may cite none,
and then it is labelled unevidenced and derives `LOW`. The engine resolves each id; an unknown,
ambiguous, duplicated or out-of-set id, an assumption, a recommendation id, a SWOT point, a source
URL or a Business Context field is refused.

**3. Nothing is authored that should be derived.** Confidence, support, trust, verification and
lifecycle are derived by the engine. There is no field for a score, weight, rank, priority,
severity or likelihood, and supplying one is refused.

**4. Figures are quoted, never produced.** Any number in a tradeoff, risk, outcome, next step or
divergence note must be printed by a statement that part cites (or, for a tradeoff, a criterion it
references) — same kind, same value, same sign, same currency, written as printed. No rounding, no
number words the evidence does not print as the same phrase ("five percent"), no numerals in other
scripts, no new figure, gap, ratio, projection, uplift, saving or return. If a figure cannot be quoted, describe the effect qualitatively.

**5. BusinessOps structures; the user decides.** Nothing here is executed. Acting on a decision — a
system write, a message, an export, an overwrite — needs the user's decision and explicit
per-action approval, and financial transactions are prohibited (the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`, ADR-0010).

## What this skill does and does not do

| Does | Does not |
|---|---|
| Read a genuine strict `SynthesisSet` | Reread the file, rerun analysis, retrieve, dispatch the scout |
| Record the user's question, objective, constraints, options and criteria | Infer any of them from data or Business Context |
| Package a bound `StrategyResult`'s records unchanged | Edit, re-grade, merge or drop a Strategy record |
| Issue class-7 records under ADR-0031 as `bops-decision-support` | Invent an option with no record behind it |
| Relate options to criteria through evidenced tradeoffs | Score, weight or rank options against criteria |
| Prefer one option when ADR-0032's conditions all hold | Name a best option, a winner or an order of preference |
| Carry every conflict, limitation and unresolved dimension | Settle a conflict or drop a limitation |
| Name next steps as evidence gaps | Assign owners, dates or actions |
| Hand a draft to the user | Mark it final, execute, schedule, send or write anything |

## Input contract

**Required: a genuine strict synthesis set** — the `SynthesisSet` object a synthesis pass produced,
with `require_dimension_provenance=True`. It is built by the paths that already exist, exactly as
for `bops-swot` and `bops-strategy-recommendations`; if one was built in the same pass, reuse its set
object rather than building a second:

| Side | Path |
|---|---|
| Internal | `commands.run(<analysis command>, source=…)` → `commands.internal_statements()` per domain, each under its own origin |
| External | the research skill's own gate-authorised retrieval → `research.close_retrieval_object()` → `synthesis.footed_statement()` / `register_external()` + `sourced_statement()` |
| Comparison | `commands.local_join()` where one internal figure meets one benchmark |
| Readings | `synthesis.interpretation(…, supports=[…])` |
| Assumptions | `synthesis.assumption(…)` — only for something a tradeoff or record genuinely depends on |

**Required: a decision question from the user.** **Optional:** objective, constraints, options,
criteria, and a `StrategyResult` that `strategy.build()` produced over **this same set object** — a
serialised result, a look-alike, or one built over a different or since-changed set is refused.

**Business Context frames; it is never evidence.** Its name, model and currency reach the package
through the set's `subject`, `business_model` and `currency`. It has no objective, constraint or
criterion field and supplies none. It cannot be cited and cannot introduce a figure.

## The flow

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "$(cat <<'PY'
from bops import config
from bops import decision_support
from bops import strategy
from bops import synthesis as S

synthesis = S.SynthesisSet(subject="<business name>", business_model="<model>",
                           currency="<ISO code>", require_dimension_provenance=True)
# ... internal statements, research statements, readings — the existing paths above ...

# Look before writing: every statement and the role it may play.
for entry in strategy.candidates(synthesis):
    ...   # role is "evidence", "assumption" or "ineligible" (with the reason)

result = decision_support.build(synthesis, {
    "decision_question": "<the user's question, verbatim>",
    "objective": "<the user's objective, verbatim>",              # optional
    "constraints": ["<the user's constraint>"],                     # optional
    "options": ["<the user's option label>"],                       # optional
    "include_status_quo": True,                                     # default
    "criteria": ["<the user's criterion>"],                         # optional
    "materiality_criteria": ["percentage"],                         # only when the user asks
    "recommendations": [{                                           # ADR-0031 proposals
        "action": "…", "evidence": ["sy-…"], "rationale": "…",
        "expected_benefit": "…", "risks": ["…"],
        "dependencies": [{"text": "The cited evidence remains current and correctly scoped."}]}],
    "tradeoffs": [{"options": ["<label>", "<label>"], "criteria": ["<criterion text>"],
                   "text": "…", "evidence": ["sy-…"], "assumptions": ["sy-…"]}],
    "risks": [{"option": "<label>", "text": "…", "evidence": ["sy-…"]}],
    "expected_outcomes": [{"option": "<label>", "text": "…", "evidence": ["sy-…"]}],
    "not_assessable": [{"option": "<label>", "reason": "…"}],
    "preferred_option": "<label>",                                  # optional
    "preference_criteria": ["<criterion text>"],
    "divergences": [{"recommendations": ["rec-…", "rec-…"], "note": "…"}],
    "next_steps": [{"text": "…", "addresses": {"kind": "limitation", "ref": "<code>"}}],
}, strategy_result=None, config=config.resolve())
print(decision_support.render(result))
PY
)"
```

Options are referred to by label and criteria by text; the engine assigns the ids. A recommendation
option's label is its record's `action`; the status quo's label is `decision_support.STATUS_QUO_LABEL`
(*Make no change*). `config` is needed only for `materiality_criteria`. `decision_support.build()` is
authoritative: if it refuses, report the refusal and fix the request against the evidence or leave
the part out. It never returns a partial package.

## Writing the parts

**Options.** The user's options, then one per recommendation record (Strategy's first, then any
issued here), then the status quo unless the user excluded it. At least two are needed; otherwise
ask what the alternatives are. An option you think is missing is not added as a label — author it
as an ADR-0031 recommendation with its own evidence, and it becomes an option through that record.

**Criteria.** Only what the user said matters, or a configured materiality threshold the user asked
for (it is recorded with its configuration layer). No weights. With no criteria there is never a
preferred option.

**Tradeoffs.** What choosing one option gives up or gains relative to another, against named
criteria where they apply, citing the statements that show it. Name any registered assumption the
reading depends on in `assumptions`; it is disclosed, never evidence, and it makes the tradeoff
`LOW`.

**Risks.** What could go wrong with one option. Cite evidence where it exists. An unevidenced risk
is allowed as a caution, derives `LOW` with `insufficient_evidence`, and may state no figure.

**Expected outcomes.** What one option is expected to produce, citing at least one statement.
Qualitative by default; a figure only by quoting a cited statement.

**Not assessable.** Where the evidence says nothing about an option, say so with a reason instead of
writing a thin tradeoff. It is recorded as a limitation. An option cannot be both assessed and not
assessable.

**Divergences.** Where a record issued here points a different way from a packaged Strategy record,
name both record ids and a note that quotes only what the records state. Neither record wins.

**Next steps.** Evidence gaps only, each addressing a limitation code, conflict id or unresolved
dimension (`<synthesis id>:<dimension>`) the package carries. No owner, date or instruction.

## The preferred option

State one only when **all** of these hold, and let the engine check them:

1. at least one criterion exists;
2. the option comes from a recommendation record in guidance, and at least one tradeoff about that
   option names one of the basis criteria and cites a statement the record itself cites — the
   criteria those tradeoffs name are the ones the preference rests on;
3. every other option appears in at least one tradeoff naming one of those same criteria, or is
   labelled not assessable;
4. `preference_criteria` names the criteria it is preferred against.

A tradeoff is not needed for every named criterion, and one comparative tradeoff can assess several
options at once. Expected outcomes name no criteria, so they cannot satisfy 2 or 3.

Otherwise `preferred_option` is `null` and `no_preference_reason` says which condition failed. The
preference carries its record's derived confidence, so a contested basis makes it `LOW`. At most one
option is preferred; the rest are **not** ordered. Never call an option best, top or first — **even
when asked directly**.

## Confidence

**Derived, never chosen.** Each tradeoff, risk and outcome combines the reason codes of what it
cites (and, for a tradeoff, its assumptions); nothing cited → `LOW`, `insufficient_evidence`. Each
option combines every tradeoff, risk, outcome and record that references it, so an option nothing
assesses is `LOW`. The package combines the options and the records. Present each level and its
reasons exactly as derived.

## Conflicts, uncertainty and limitations

- **Conflicts** touching any cited statement are carried in full; neither side is chosen, averaged
  or preferred by tier.
- **Partially supported, incomparable, unresolved-dimension and `LOW` evidence** may be cited; its
  reasons and unresolved dimensions travel into the uncertainty part.
- **Limitations and caveats** are never dropped.
- **Materiality** is inherited, never re-judged. Material statements the package does not cite are
  listed.

## Finalisation (M11)

A package becomes `final` only through `verification.py` (ADR-0034, ADR-0035), and only when asked for.
This skill decides nothing about it:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "$(cat <<'PY'
from bops import verification

request_id = verification.issue_recomputation(package)   # an opaque id, or None
# ... the command dispatches businessops:bops-analysis-verifier with ONLY request_id and keeps its
# reply verbatim; the draft is then rebuilt with exactly the same inputs in a new process ...
result = verification.verify(package, reply)                # every check deterministic
if result.passed:
    final = verification.finalise(package, result)          # lifecycle fields change, nothing else
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

## Output

`decision_support.render(result)` formats the package once: the lifecycle label (`draft — unverified`,
or `final — verified` for a finalised package), the
human-decision statement, the order note, then the twelve parts in order. The JSON form is
`result.to_json()`, validated by `lib/schemas/decision_support.schema.json`; the class-7 ledger
form of records issued here is `result.claims()`. The package is held beside the set and never
re-enters it.

Add nothing after it: no summary ranking, no "best option", no action plan with dates, no execution
step, and no claim that the package is final unless `verification.finalise()` produced it.

## Failure conditions

| Condition | Behaviour |
|---|---|
| No synthesis set, or serialised, look-alike, non-strict or empty | Refused. Build the set through the existing paths first |
| No decision question, or a blank one | Refused. Ask the user |
| A question whose decision is unclear | Ask the user before building; the engine does not judge meaning |
| Fewer than two options, or two options with the same label | Refused. Ask the user |
| `StrategyResult` serialised, look-alike, or bound to a different or changed set | Refused |
| Evidence id unknown, ambiguous, duplicated, out of set, an assumption or a recommendation | Refused |
| A tradeoff or outcome with no evidence; a package citing nothing at all | Refused |
| Any field outside the request contract (confidence, lifecycle, trust, score, weight, rank, priority…) | Refused |
| A figure, date or number word the cited statements do not print; a rounded or re-signed figure | Refused |
| A next step addressing something the package does not carry | Refused |
| The set changed after the package was built | Refused; build again |
| Asked for the best option, a score or a ranking | Decline; present the package as built |
| Asked to finalise the package or carry out the decision | Only the verifier finalises, through the flow above and only when verification passes; the user decides, and any action needs its own explicit approval |

**Fail closed.** Every refusal produces no package, never a partial or invented one.

Related policy: `${CLAUDE_PLUGIN_ROOT}/reference/evidence-ledger.md` (class 7), `${CLAUDE_PLUGIN_ROOT}/reference/output-standards.md`
(decision package), `${CLAUDE_PLUGIN_ROOT}/reference/materiality-policy.md`, `${CLAUDE_PLUGIN_ROOT}/reference/research-policy.md`,
`${CLAUDE_PLUGIN_ROOT}/reference/ambiguity-protocol.md`, the approval matrix in `${CLAUDE_PLUGIN_ROOT}/reference/analysis-framework.md`, ADR-0010, ADR-0022, ADR-0030,
ADR-0031, ADR-0032.
