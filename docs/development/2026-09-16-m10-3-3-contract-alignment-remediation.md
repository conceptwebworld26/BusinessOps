# 2026-09-16 — M10.3.3: Decision Support contract-alignment remediation

**Milestone:** 10.3.3 — `biq-decision-support` + `/decision-support` (remediation within the milestone)
**Status on completion:** COMPLETED
**Supersedes:** `docs/development/2026-09-16-m10-3-3-decision-support.md` — only §9 (test counts),
the *Outcomes carry no criteria*, *Question ambiguity is structural* and *Number words reach
Strategy* items of §10, and the §7 note on number words. That record is otherwise current and is
left intact.

## 1. Prompt / task performed

Re-check the uncommitted M10.3.3 implementation against accepted ADR-0032 and remove behaviour
stricter than the contract: (1) the preferred-option check, (2) decision-question ambiguity
handling; (3) re-verify the shared Strategy figure-rule change; (4) re-check the ADR-0032
invariants; rerun focused, Strategy and full suites, strict validation and `git diff --check`. No
commit, push, new milestone, Executive Report, M11 work, ADR change or new ADR.

## 2. Baseline

HEAD `60aeca355577f6e9804089a621dc86d24c93ca0a`, working tree holding the uncommitted M10.3.3
implementation; last full run 4,325 tests, 0 failures, 0 errors, 19 skipped.

## 3. Changes made

### 3.1 Preferred option (`decision_support._preference`)

**Before.** For **each** criterion named in `preference_criteria`, some tradeoff had to include the
preferred option, name that criterion and cite a statement its record cites; and every other option
had to appear in a tradeoff naming **each** named criterion (or be labelled not assessable). A basis
of two criteria therefore failed unless both were individually covered.

**After.** ADR-0032 §10's four conditions, checked over the named basis as a whole:

1. the package states at least one criterion — else `NO_PREFERENCE_CRITERIA`;
2. `preference_criteria` names the basis — else `NO_PREFERENCE_BASIS` (unknown names still refused);
3. the option comes from a class-7 record in guidance — else `NO_PREFERENCE_RECORD` — and at least
   one tradeoff about the option names a basis criterion and cites a statement that record cites —
   else `NO_PREFERENCE_UNRELATED`. The basis criteria those tradeoffs name are what the preference
   rests on;
4. every other option is labelled not assessable, or appears in at least one tradeoff naming one of
   those criteria — else `NO_PREFERENCE_UNASSESSED`. An option assessed only against a different
   criterion does not count, so options stay comparable on the same criteria.

`preference_basis` still names the record and **all** criteria the user named. Nothing is scored,
weighted, ranked or combined; no new field, reason code or evaluation semantics. The two reason
texts that said "every named criterion" now say "the named criteria" / "the criteria the preference
rests on". Expected outcomes still cannot satisfy conditions 3 or 4: ADR-0032 §2 gives them no
`criterion_ids`, so an outcome cannot say which criterion it is against — a property of the
contract's shapes, satisfiable through tradeoffs, not a contradiction.

### 3.2 Decision question (`decision_support._question`)

**Before.** Refused when missing, non-text, blank, containing no letters, or containing more than
one `?`.

**After.** Refused only when missing, non-text or blank (whitespace only). Anything else is stored
exactly as written — a multi-sentence question with several question marks included. The engine
makes no claim to detect ambiguity; the skill and command ask the user when the decision is unclear.

### 3.3 Shared Strategy figure rule — verified, one defect fixed

**Consistency with the prior contract.** ADR-0031 rule 9 requires every numeric figure in authored
text to appear in cited statement text and the check to fail closed, and leaves "exact
numeric-token recognition" to implementation. M10.3.2 recorded, as a *limitation*, that number words
were not read — so "five percent" passed unchecked. Reading cardinal words as figures closes that
fail-open gap; it narrows nothing ADR-0031 permits. `half`, `double` and standalone `one` stay
unread, as before. The only other Strategy changes are additive (`cite`, `statement_detail`,
`ground_recommendation`, `synthesis_digest`, issuer constants); `cite()` is the lifted evidence loop,
unchanged in behaviour.

**Defect found and fixed.** The rule matched number words one at a time against the set of words in
the evidence, so "twenty-one" was grounded by "twenty-three", "five" by "twenty-five", "one hundred"
by "two hundred", and "two thousand" by "two stores and a thousand pallets" — each probed and
accepted. `figure_tokens()` now emits one `("number_word", phrase)` per run of cardinal words
(spaces or hyphens between them; an `and` after a scale word dropped; `one` included inside a run
but never alone), and `require_grounded()` requires the same phrase. `Twenty-five` and
`twenty five` still match each other. All four probes are now refused and pinned by test.

### 3.4 Invariants re-checked (all held; each is asserted by a focused or Strategy test)

Recommendation outside `SynthesisItem`; `SynthesisSet.recommendations` empty; one genuine strict set
required; `StrategyResult` bound to the same set object; evidence through `grounding`;
FACT/CALCULATION/SOURCED/grounded INTERPRETATION only; assumptions and recommendation records never
evidence; evidence in set order; duplicate, fake, out-of-set and ambiguous ids refused; no authored
confidence, lifecycle, trust or verification; no score, weight, rank, priority, severity or
likelihood field; exact figure grounding; unevidenced risk `LOW`; assumption-dependent tradeoff
`LOW`; unassessed option `LOW`; materiality inherited; lifecycle always `draft`, no path to `final`;
no side effects; no re-entry; no Executive Report or M11 code.

## 4. Files created

- `docs/development/2026-09-16-m10-3-3-contract-alignment-remediation.md` (this record)

## 5. Files modified

- `lib/python/biq/decision_support.py` — `_question`, `_preference`, two reason texts
- `lib/python/biq/strategy.py` — number words tokenised and matched as phrases
- `tests/unit/test_m10_3_3_decision_support.py` — see §8
- `architecture.md`, `project_plan.md`, `skills/biq-decision-support/SKILL.md`,
  `commands/decision-support.md` — wording for the changed behaviour

## 6. Files deleted

None.

## 7. Features implemented

No new feature. Behaviour aligned to ADR-0032; figure-rule defect fixed.

## 8. Tests performed

Focused tests changed: the question refusal test now covers missing, blank, whitespace and non-string
input only; new tests accept a multi-sentence question with several `?` verbatim and assert the
engine holds no punctuation rule. New preferred-option tests: a preference with two named criteria
and no tradeoff for the second (succeeds, basis names both, no score/weight/rank/matrix key); one
comparative tradeoff assessing every option (succeeds); and null results for no criteria, no
qualifying recommendation (user option; record evidence uncited), another option assessed only on a
different criterion or on none (null; succeeds once labelled not assessable), missing basis (empty
and absent), and tradeoffs naming only a non-basis criterion. Number-word tests now expect phrases
and pin the four misgrounding cases. A scratch mutation check patched the pre-remediation
`_preference` and `_question` back in: the three new must-succeed/accept tests failed under the old
rules and passed under the new.

```
python tests/run_tests.py unit.test_m10_3_3_decision_support
python tests/run_tests.py unit.test_m10_3_2_strategy
python tests/run_tests.py
claude plugin validate . --strict
git diff --check
```

## 9. Test results

Recorded in the task report for this remediation, from runs made after the last change.

## 10. Issues discovered

The number-phrase misgrounding in §3.3, fixed. No contradiction in ADR-0032.

## 11. Decisions made

None; no ADR created or edited.

## 12. Architecture changes

`architecture.md` §7 wording only: the question check, the preferred-option check and number
phrases now describe the behaviour above.

## 13. Project-plan updates

M10.3.3 stays `COMPLETED`; a remediation row added and test counts updated.

## 14. Documentation updates

`architecture.md`, `project_plan.md`, the skill and the command. `reference/output-standards.md`
not required: it says the preferred option appears "only with its named basis", which is unchanged.

## 15. Remaining work

None for M10.3.3. Next: M10.3.4 onward (Executive Report), on instruction.

## 16. Git commit reference

N/A — no commit made, nothing pushed.
