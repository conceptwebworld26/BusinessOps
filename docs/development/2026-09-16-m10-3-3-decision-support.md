# 2026-09-16 — M10.3.3: Decision Support

**Milestone:** 10.3.3 — `biq-decision-support` + `/decision-support`
**Status on completion:** COMPLETED
**Supersedes:** None

## 1. Prompt / task performed

Implement ADR-0032 as accepted: a deterministic Decision Support engine producing a draft,
twelve-part `DecisionResult` beside one genuine strict `SynthesisSet`, optionally packaging a
`StrategyResult` bound to the same set; a strict, closed input contract; fail-closed validation;
the ADR-0031 record contract, figure rule and `confidence.combine()` reused rather than copied; a
closed schema; the skill and a thin command; focused tests; registry and absence guards moved. No
commit, no push, no Executive Report, no M11 verifier, no live research, no MCP change, no change to
ADR-0032 or any accepted ADR.

## 2. Baseline

| Fact | Value |
|---|---|
| HEAD | `60aeca355577f6e9804089a621dc86d24c93ca0a` — *M10.3.3-A: Decision Support contract* |
| Branch | `main`, clean tree at start |
| Last full run | 4,232 tests, 0 failures, 0 errors, 19 skipped |

## 3. Changes made

In this order:

1. **Additive seams in `strategy.py`.** `DECISION_SUPPORT_ISSUER`, `RECOMMENDATION_ISSUERS`,
   `synthesis_digest()`, `cite()`, `statement_detail()` and `ground_recommendation(…, issued_by=…)`.
   The record builder `_recommendation()` now takes `issued_by`, restricted to the two issuers;
   `strategy.build()` still passes Strategy's own. `cite()` is the evidence-citation loop that was
   already inside `_recommendation()`, lifted out so records, tradeoffs, risks and outcomes use one
   rule.
2. **Number words in the figure rule.** `figure_tokens()` now reads cardinal number words
   (`NUMBER_WORDS`: zero, two–twenty, the tens, hundred, thousand, million, billion, trillion, dozen,
   and plurals) not already part of a figure as `("number_word", word)`; `require_grounded()` refuses
   one no cited statement prints as the same word. `one` is excluded (a pronoun far more often than a
   quantity); fractions and multipliers stay qualitative. This applies to Strategy as well — see §10.
   The Strategy test that allow-lists `.add(` calls gained `number_words`.
3. **Re-entry.** `SynthesisSet.register_claims()` now also refuses a record with
   `analysis: decision_support`, any decision-package-only field (`decision_question`, `lifecycle`,
   `option_id`, `criterion_id`, `tradeoff_id`, `risk_id`, `outcome_id`, `preferred_option`,
   `preference_basis`, `no_preference_reason`, `divergences`, `next_steps`, `option_ids`,
   `criterion_ids`, `assumption_ids`, `recommendation_ids`, `referenced_by`, `addresses`), or a
   framing origin (`user`, `status_quo`). SWOT, Strategy and synthesis-security tests re-run clean.
4. **Engine** `lib/python/biq/decision_support.py`: `build()`, `DecisionResult`, `render()`.
5. **Schema** `lib/schemas/decision_support.schema.json`, generated from Strategy's definitions so
   the mirrored `recommendation`, `evidence_detail`, `limitation`, `synthesis_id`, `text`, `level` and
   `confidence_assessment` start identical; a test pins them.
6. **Command and skill**, then the four absence guards, then the focused tests, then documentation.

## 4. Files created

- `lib/python/biq/decision_support.py`
- `lib/schemas/decision_support.schema.json`
- `skills/biq-decision-support/SKILL.md`
- `commands/decision-support.md`
- `tests/unit/test_m10_3_3_decision_support.py`
- `docs/development/2026-09-16-m10-3-3-decision-support.md` (this record)

## 5. Files modified

- `lib/python/biq/strategy.py` — additive seams; number-word figure tokens
- `lib/python/biq/synthesis/synthesis_set.py` — re-entry refusal covers decision packages
- `tests/unit/test_m10_3_2_strategy.py` — `.add(` allow-list; absence guard now Executive Report only
- `tests/unit/test_m10_3_1_swot.py`, `tests/unit/test_m9d5_industry_research_command.py`,
  `tests/unit/test_command_registry.py` — `decision-support` moved from unbuilt to built
- `architecture.md` — §4 status, §7 consumers, figure-rule classes, contract "built" with enforcement
  notes, §13 tree
- `project_plan.md` — M10.3.3 `COMPLETED`
- `README.md`, `docs/commands/README.md`, `docs/skills/README.md` — inventory
- `commands/strategy-analysis.md`, `commands/swot-analysis.md` — stale "not built" scope lines only

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | User-reachable |
|---|---|---|
| Draft twelve-part decision package | `decision_support.build()` / `render()` | Yes, via `/decision-support` |
| Shared class-7 record builder with issuer | `strategy.ground_recommendation()` | Internal seam |
| Number-word figure rule | `strategy.figure_tokens()` / `require_grounded()` | Yes, through both consumers |
| Decision-package re-entry refusal | `SynthesisSet.register_claims()` | Internal guard |

**Request contract** (closed; `decision_question` required): `objective`, `constraints`, `options`,
`include_status_quo`, `criteria`, `materiality_criteria`, `recommendations`, `tradeoffs`, `risks`,
`expected_outcomes`, `not_assessable`, `preferred_option`, `preference_criteria`, `divergences`,
`next_steps`. Options are referred to by label and criteria by text; ids are content-addressed
(`opt-`, `crit-`, `trd-`, `rsk-`, `out-` + 12 hex).

**The twelve parts** appear under `body` in ADR-0032 order with ADR-0032's shapes; metadata
(schema version, analysis, issuer, lifecycle, verification, lifecycle note, subject, as-of, business
model, currency, quality grade, synthesis digest, whether a Strategy result is bound, trust
statement, human-decision statement, order note, material not cited, set conflicts, set
limitations, set confidence) sits beside it.

## 8. Tests performed

```
python -m unittest unit.test_m10_3_3_decision_support          (from tests/)
python -m unittest unit.test_m10_1_synthesis_security unit.test_m10_3_1_swot unit.test_m10_3_2_strategy
python tests/run_tests.py unit.test_command_registry
python tests/run_tests.py unit.test_m9d5_industry_research_command
python tests/run_tests.py
claude plugin validate . --strict
git diff --check
```

## 9. Test results

- Focused: **93 tests, OK.**
- Synthesis security 33 OK; SWOT 117 OK; Strategy 123 OK; command registry 40 OK; M9-D.5 command 51 OK.
- Full suite: **ran 4325 | failures 0 | errors 0 | skipped 19** (4,232 + 93).
- `claude plugin validate . --strict`: **Validation passed.**
- `git diff --check`: clean (only the repository's usual LF→CRLF working-copy notices).

## 10. Issues discovered

- **Brief summary vs ADR shapes.** The brief's shorthand described `preference_basis` as text,
  `next_steps[].addresses` as text, and per-record `reasons`. ADR-0032 §2 fixes
  `preference_basis: {recommendation_id, criterion_ids}`, `addresses: {kind, ref}` and
  `confidence_reasons`. The accepted ADR was implemented; nothing in it was changed. Not a
  contradiction in the contract, so no stop was required.
- **Outcomes carry no criteria.** ADR-0032 §10 speaks of "tradeoffs or outcomes" relating record
  evidence to criteria, but §2 gives `expected_outcomes` no `criterion_ids`. The engine checks the
  preferred-option conditions through tradeoffs, the only part that can name a criterion, and
  requires a tradeoff per named criterion (the stricter reading). Recorded here, not a new decision.
- **Next steps cite nothing.** ADR-0032 §6 applies the figure rule to next steps against "a statement
  that part cites". A next step's figures are grounded only by the statements behind what it
  addresses (the conflict's items, or the statement with the unresolved dimension); a limitation
  grounds none.
- **Question ambiguity is structural.** The engine refuses a question with no words or more than one
  question mark; semantic ambiguity remains the skill's to resolve by asking.
- **Number words reach Strategy.** The rule was added in the shared figure rule, as the brief
  required it for Decision Support and ADR-0032 requires "the same implementation". A Strategy
  recommendation writing "five percent" where no cited statement prints "five" is now refused. All
  123 Strategy tests pass unchanged apart from the allow-list line.
- **Uncertainty limitations include the set's.** The uncertainty part merges the cited statements'
  limitations, the set's own (for example `synthesis.unresolved_conflict`) and not-assessable labels,
  so a next step can address a set-level limitation.
- **Fixture reuse.** The focused tests import `test_m10_3_2_strategy` for its fixtures instead of
  copying them; a change there affects both suites.

## 11. Decisions made

None beyond ADR-0032. Implementation choices it left open: status-quo label *Make no change*;
exclusion via `include_status_quo: false`; the id spellings above; configuration criteria rendered as
`Materiality threshold <key>: <value>` with `source` `materiality.<key> (<layer> layer)`; fixed
no-preference reason texts (`NO_PREFERENCE_*`).

## 12. Architecture changes

`architecture.md` §4 and §7 now describe Decision Support as built, with the enforcement notes
above; §7's figure rule lists number words; §13 lists the module and schema. No change in substance
to any decided contract.

## 13. Project-plan updates

M10.3.3 — Decision Support: `PLANNED` → `COMPLETED`. M10.3.4 onward (Executive Report) unchanged.

## 14. Documentation updates

`architecture.md`, `project_plan.md`, `README.md`, `docs/commands/README.md`,
`docs/skills/README.md`, two command scope lines, this record. `reference/output-standards.md`
already defined the decision-package shape the renderer follows and was not changed. `CLAUDE.md`
unchanged (no governance change). No ADR created or edited.

## 15. Remaining work

- M10.3.4 onward: Executive Report.
- M11: the analysis verifier, which alone moves a draft package to `final`.
- The design counts (17 commands, 20 skills) in `README.md`, `CLAUDE.md` and `architecture.md` are
  targets, not inventory, and were left as they are.

## 16. Git commit reference

N/A — no commit made, nothing pushed.
