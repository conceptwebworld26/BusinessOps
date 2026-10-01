# 2026-09-16 — M10.3.2: Strategy Recommendations

**Milestone:** 10.3.2 — `biq-strategy-recommendations` + `/strategy-analysis`
**Status on completion:** COMPLETED
**Supersedes:** None

## 1. Prompt / task performed

Implement ADR-0031 exactly: a deterministic strategy engine producing class-7 recommendations in
a `StrategyResult` beside one genuine strict `SynthesisSet`; evidence resolved against real
synthesis statement ids; derived confidence; fail-closed figure grounding; one shared home for
the ADR-0030 grounding checks; the `register_claims()` re-entry path closed; class-7 claim-ledger
validation; a closed strategy schema; the skill and a thin command; extensive deterministic
tests. No commit, no push, no M10.3.3, no Decision Support or Executive Report, no live research,
no change to ADR-0031 or any accepted ADR.

## 2. Baseline

| Fact | Value |
|---|---|
| HEAD | `d41cb8f286086871babb4052a6ffbfbde536a738` — *M10.3.2-A: strategy recommendation contract* |
| Branch | `main`, equal to `origin/main` after a read-only fetch, clean tree |
| Last full run | 4,108 tests, 0 failures, 0 errors, 19 skipped |

## 3. What inspection established before coding

- `swot.py` held the ADR-0030 grounding checks privately (`_graded`, `_one`, `_rests_on`,
  `genuine_synthesis`). ADR-0031 requires one home, and SWOT's 117 tests pin its refusal phrases.
- `SynthesisSet.register_claims()` stored any record not marked verified — including a serialised
  recommendation — as a citable candidate claim (probed in M10.3.2-A).
- `evidence.Claim` class 7 checked truthiness only; `test_engine_m2` pinned `evidence="e"` as valid.
- `jsonschema_mini` does **not** implement `allOf`/`if`/`then`; the claim-ledger schema's existing
  conditionals are therefore unenforced by the in-repo validator, while `anyOf` is enforced.
- `biq.quantity.scale_factor()` already owns the closed scale vocabulary (`k`, `m`, `mn`, `bn`,
  `tn`, their words and plurals; ambiguous `b`/`mm` absent).
- Three shipped skills said `biq-strategy-recommendations` "is not built"; three existing tests
  asserted `strategy-analysis` does not exist; `test_m8_review` rejects an unquoted `": "` in
  frontmatter.

## 4. Changes made

1. **`lib/python/biq/synthesis/grounding.py` (new).** `genuine_set`, `graded`, `index`, `one`,
   `interpretation_supports`, `interpretation_domains`, `evidence_domains`, `GroundingError`,
   `EVIDENTIAL_KINDS`, `READABLE_KINDS`, `DISQUALIFYING_SUPPORT`. Consumer-neutral messages that keep
   every phrase SWOT's tests pin. Knows neither consumer.
2. **`lib/python/biq/swot.py`.** Private grounding helpers removed; calls `grounding` and reports its
   refusals as `SwotError`. Only the tag rule remains SWOT's. 117/117 unchanged.
3. **`lib/python/biq/synthesis/synthesis_set.py`.** Additive `_is_recommendation()` refusal in
   `register_claims()`: class/provenance_class/evidence_class `7`; label, kind, finding_type or
   class_name `RECOMMENDATION`; any of `recommendation_id`, `issued_by`, `action`, `rationale`,
   `expected_benefit`, `risks`, `dependencies`. No existing acceptance changed.
4. **`lib/python/biq/evidence.py`.** Class-7 shape check (`_recommendation_shape`): non-empty action;
   evidence a non-empty list of distinct `sy-[0-9a-f]{12}` ids; non-empty rationale and expected
   benefit; risks a non-empty list of non-empty text; dependencies a non-empty list of exactly
   `{text, assumption_id}`; confidence a level; `based_on` either absent or exactly the evidence
   ids; no other field. `RECOMMENDATION_FIELDS` unchanged. No synthesis import (layering).
5. **`lib/python/biq/strategy.py` (new).** The engine — §6.
6. **`lib/schemas/claim_ledger.schema.json`.** Class-7 `anyOf` branch (enforced) plus description.
7. **`lib/schemas/strategy.schema.json` (new).** Closed `StrategyResult`.
8. **`skills/biq-strategy-recommendations/SKILL.md`, `commands/strategy-analysis.md` (new).**
9. **Tests.** New `tests/unit/test_m10_3_2_strategy.py` (123). Amended, as milestone outcomes:
   `test_command_registry.py` (strategy built; unbuilt now decision-support, executive-report;
   `UNBUILT_COMMAND` → `decision-support`), `test_m10_3_1_swot.py` and
   `test_m9d5_industry_research_command.py` (strategy removed from absence lists, the other two kept),
   `test_engine_m2.py` (the placeholder-accepting class-7 test retargeted to the canonical shape, and a
   new test pinning that placeholders are refused).
10. **Wording.** "is not built" removed from the Strategy reference in `biq-competitor-analysis`,
    `biq-industry-research` and `biq-swot` skills.
11. **Docs.** §10 below.

## 5. `StrategyResult`

Constructed only by `build()` (module-private token). Holds the set **object** (never a serialised
copy) and `synthesis_digest` = SHA-256 of `synthesis.to_json()` at build time. `is_bound_to(set)` is
true only for that object, unchanged; `claims()` and `as_dict()` refuse otherwise. `recommendations`
returns deep copies. Serialised fields: `schema_version`, `analysis`, `issued_by`, framing (`subject`,
`as_of`, `business_model`, `currency`, `quality_grade`), `synthesis_digest`, `trust_statement`,
`human_decision`, `order_note`, `recommendations`, `empty_state`, `material_not_cited`, set
`conflicts` and `limitations` whole, set `confidence`.

Each recommendation: `recommendation_id` (`rec-` + SHA-256 of action and sorted evidence),
`issued_by`, `provenance_class` 7, `label`, the six authored fields (dependencies normalised to
`{text, assumption_id}`), derived `confidence`, `confidence_reasons`, `support` (weakest), `rests_on`,
`material`, `evidence_detail` (kind, class, origin, domain, trust, statement, support, confidence and
reasons, materiality, conflict refs, unresolved dimensions, chain, verified supports), `assumptions`,
`conflicts` (full records), `limitations`, `caveats`.

## 6. Engine rules as implemented

- **Evidence:** each id through `grounding.one` then `grounding.evidence_domains`; an `ASSUMPTION`
  refused with its own message; basis requires class 1/3/4 or a verified interpretation.
- **Assumptions:** `assumption_id` must resolve to exactly one graded `ASSUMPTION`.
- **Figures:** `figure_tokens()` — dates (`YYYY-MM-DD`, `YYYY-MM`, years 1900–2099 unless a currency
  precedes or a scale/percent follows), figures (code before/after, `£`→GBP, `€`→EUR, `$`/`¥` literal,
  sign, grouped or plain digits, decimal, `quantity` scale words, `%`/`percent`/`pp`/`percentage
  point(s)`; exact normalised `Decimal`), identifiers (any other digit-bearing word, including a
  malformed grouping); non-ASCII numerals refused. `require_grounded()` — figure: same kind, same
  value, same currency if stated, and refused when an unmarked figure matches two currencies; date:
  same date, or a year grounded by a cited date in that year; identifier: same word or a cited id.
  Checked on action, rationale, expected benefit and each risk against cited evidence; dependency
  text may also quote its own cited assumption.
- **Confidence:** `confidence.combine([confidence.assess(reasons) for cited + assumptions])`.
- **Order:** `(earliest cited position, recommendation_id)`; duplicate ids refused.
- **Build is atomic:** the first refusal raises; the set digest is compared before and after.

## 7. Files created

- `lib/python/biq/strategy.py`
- `lib/python/biq/synthesis/grounding.py`
- `lib/schemas/strategy.schema.json`
- `skills/biq-strategy-recommendations/SKILL.md`
- `commands/strategy-analysis.md`
- `tests/unit/test_m10_3_2_strategy.py`
- `docs/development/2026-09-16-m10-3-2-strategy-recommendations.md`

## 8. Files modified

`lib/python/biq/evidence.py`, `lib/python/biq/swot.py`, `lib/python/biq/synthesis/synthesis_set.py`,
`lib/schemas/claim_ledger.schema.json`, `skills/biq-competitor-analysis/SKILL.md`,
`skills/biq-industry-research/SKILL.md`, `skills/biq-swot/SKILL.md`,
`tests/unit/test_command_registry.py`, `tests/unit/test_engine_m2.py`,
`tests/unit/test_m10_3_1_swot.py`, `tests/unit/test_m9d5_industry_research_command.py`,
`architecture.md`, `project_plan.md`, `README.md`, `docs/commands/README.md`,
`docs/skills/README.md`.

## 9. Files deleted

None.

## 10. Documentation governance

| File | Decision | Reason |
|---|---|---|
| `architecture.md` | UPDATED | §4 row built; research surface no longer says "not built"; consumers line; §7 *How the contract is enforced*; §13 structure |
| `project_plan.md` | UPDATED | M10.3.2 `COMPLETED` section; M10.3.2-A kept `COMPLETED (DECISION ONLY)`; M10.3.3 onward still `PLANNED` |
| `README.md` | UPDATED | `/strategy-analysis` inventory row and paragraph; "Not built yet" no longer lists strategy |
| `docs/commands/README.md`, `docs/skills/README.md` | UPDATED | Strategy rows added; pre-existing gaps left |
| This record | CREATED | — |
| `CLAUDE.md` | NOT REQUIRED | Development governance unchanged; §9 already classes strategy as read-only |
| `docs/decisions/README.md`, `docs/README.md` | NOT REQUIRED | No new ADR |
| `reference/evidence-ledger.md`, `reference/output-standards.md` | NOT REQUIRED | M10.3.2-A already stated the contract "enforced by the strategy engine from M10.3.2", which is now true |
| ADR-0031 and all accepted ADRs | NOT REQUIRED | Immutable; implementation follows ADR-0031 without a new decision |
| `docs/development/README.md` | DEFERRED | Stale since M9-B; unrelated cleanup |

## 11. Tests performed

```
python tests/run_tests.py unit.test_m10_3_2_strategy
python tests/run_tests.py <regression modules listed in §12>
python tests/run_tests.py
claude plugin validate . --strict
```

Mutation check: seven guards disabled in turn (authored extra fields, expected-benefit figure rule,
assumption confidence, build token, set binding, shared grounding, `register_claims` refusal); each
produced failures (4, 2, 2, 1, 1, 6, 1); files restored and re-verified at 123/0/0.

Focused matrix (123): single (6), multiple (4), mixed (3), interpretation (3), assumption (3),
confidence (6), conflict (3), partial/incomparable/unresolved (4), materiality (4), Business Context
(3), expected benefit (3), command-level (8), fail-closed (24), class-7 claim shape (6), figure tokens
(7), figure grounding (10), traceability (4), single grounding home (4), anti-re-entry (7), output (7),
skill and command (4).

## 12. Test results

| Run | Result |
|---|---|
| `unit.test_m10_3_2_strategy` (focused) | `ran 123 \| failures 0 \| errors 0 \| skipped 0` |
| `unit.test_m10_3_1_swot` (SWOT, now on shared grounding) | `ran 117 \| failures 0 \| errors 0 \| skipped 0` |
| M10.1 synthesis / policy / security / cross-domain | 36 / 57 / 33 / 25 — 0 failures, 0 errors |
| M10.2-R footing / retrieval seam | 31 / 24 — 0 failures, 0 errors |
| R.6 / R.8 / R.9 / R.10 | 91 / 81 / 99 / 97 — 0 failures, 0 errors |
| R.11 / R.12 / R.13 / R.14 | 136 / 157 / 162 / 105 — 0 failures, 0 errors |
| `test_engine_m2` / `test_command_registry` / `test_manifest` / `test_m9_governance` | 64 / 40 / 15 / 46 — 0 failures, 0 errors |
| `test_m9d5_industry_research_command` / `test_m8_review` | 51 / 55 — 0 failures, 0 errors |
| **Full suite** | **`ran 4232 \| failures 0 \| errors 0 \| skipped 19`** — 4,108 baseline + 123 focused + 1 new `test_engine_m2` test |
| `claude plugin validate . --strict` | `✔ Validation passed` (exit 0) |

No existing test was deleted or weakened. Four existing test files were amended as milestone
outcomes (§4 item 9); every absence guard for Decision Support and Executive Report is intact.

## 13. Protected components

Unchanged against HEAD (`git diff --quiet`): `synthesis/compatibility.py`, `quantity.py`, all of
`research/` (including `scout.py` and `BIQ-REC/1`), `synthesis/dimension_provenance.py`,
`synthesis/research_footing.py`, all of `commands/` in the engine (including `joins.py`),
`synthesis/contract.py`, `synthesis/merge.py`, `lib/schemas/synthesis.schema.json`, `docs/decisions/`,
`reference/`, `agents/`, `.claude-plugin/`, `config/`, `CLAUDE.md`.

## 14. Remaining limitations

1. **Wording is not checked for meaning.** The engine proves evidence, confidence and figures; it
   cannot prove a rationale does not treat an incomparable pair as comparable, or that an action is
   wise. That is model judgement under human review, and the result says so.
2. **The figure rule is deliberately literal.** No rounding tolerance, no sign-insensitive matching
   (`declined 5.54%` does not match `-5.54%`), no number words (`half`, `double` are not read), and a
   bare year 1900–2099 is always a date. Legitimate prose will sometimes be refused.
3. **`m` is read as million** (the `biq.quantity` alias). `5m` meaning metres is refused unless the
   evidence prints the same five million.
4. **Identity is by state.** Any later change to the set (a new statement, a regraded conflict)
   invalidates an existing `StrategyResult`; recommendations must be rebuilt.
5. **The claim-ledger `allOf` conditionals for classes 1, 3 and 4 remain unenforced by the in-repo
   validator** (pre-existing); the new class-7 branch uses `anyOf`, which is enforced.
6. **Model-mediated command.** Objects do not persist across tool calls; the skill runs a candidates
   pass and a build pass over content-addressed ids.
7. **Nothing verified live.** Deterministic and synthetic; R-12 untouched.

## 15. Live research

**None.**

## 16. Git commit reference

**N/A — no commit, no push.** HEAD unchanged at `d41cb8f286086871babb4052a6ffbfbde536a738`.
