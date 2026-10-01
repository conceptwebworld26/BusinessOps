# ADR-0049 — A run whose semantic judge votes split is `execution_unavailable`, never a pass or a fail

**Date:** 2026-09-25
**Status:** Accepted — 2026-09-25, by the project owner, who made this decision in the M13-DEF-23 remediation prompt
and authorised its implementation in the same decision.

- **What acceptance approves.** One classification rule in ADR-0039 §E.6, its implementation in the M13-DEF-06
  classifier (`tests/unit/test_m13_eval_results.py`), its tests and governance. Nothing else. No product file, grader,
  case, fixture or historical result is in scope, and none was changed.
- **Implemented 2026-09-25**, in the same task (`docs/development/2026-09-25-m13-def-23-adr-0049.md`).

**Deciders:** Project owner (decision and implementation authorised, 2026-09-25), raised by M13-DEF-23.
**Supersedes:** none.
**Amends:** [ADR-0039](ADR-0039-m13-test-hardening-and-evals-contract.md), **in part**: §E.6's class table, by adding one
case to `execution_unavailable` and excluding it from `automated_pass` and `automated_fail`. Every other part of
§E.6 — the closed vocabulary, `not_executed`, `manual_observation`, "an observed failure takes precedence", and the
M13-DEF-06 admissibility rule — remains in force. **ADR-0039's text and status line are not edited**, as the repository
did for ADR-0040, ADR-0041, ADR-0043, ADR-0045 and ADR-0046.
**Relates to:** ADR-0039 §E.6, ADR-0044 (which carries LLM criteria verbatim), ADR-0047 and ADR-0048 (the other
M13.2 closing remediations), M13-DEF-06 (the admissibility rule), M13-DEF-23 (the defect this closes).

## Context

A semantic LLM grader is judged by the platform with several votes, and the platform records one verdict per grader:
the majority. ADR-0039 §E.6 then treats a scored failing run as an observed failure. So a two-to-one split became a
pass or a fail on the vote count alone. The M13.2 closing evaluation recorded six split runs, and `c02`, `c03` and
`d07` were `automated_fail` on split votes alone (M13-DEF-23).

A split is not a finding about BusinessIQ. It shows that the automated measurement did not settle the question. Counting
the majority would be a majority-vote rule; pinning a judge model would hide the disagreement rather than resolve it.
The owner rejected both. Deterministic restructuring, done on 2026-09-25, removed what the trace can prove from the
judges (`d07`). The remaining split judges are genuinely semantic.

## Decision

1. **A semantic LLM grader may produce conflicting judge votes.** A *split* is a scored semantic grader whose recorded
   votes include both a pass and a fail.
2. **A split is not sufficient evidence for `automated_pass`, nor for `automated_fail`.**
3. **A run whose only unfavourable evidence is a split is `execution_unavailable` for that run**: inconclusive automated
   evidence. The case class then follows §E.6 as before — a case with such a run and no established failing run is
   `execution_unavailable`.
4. **It is not a product failure.** It means the automated evaluation did not establish a deterministic verdict.
5. **No majority-vote policy is introduced, and no judge model is pinned.**
6. **Established evidence still decides.** A run in which a deterministic grader failed, or a semantic grader failed
   with unanimous votes, is an observed failure even if another grader split, and "an observed failure takes precedence"
   still applies across a case's runs. Deterministic evidence remains preferred wherever it exists.
7. **Only a genuine split changes.** Unanimous semantic verdicts, deterministic verdicts, and every inadmissible run —
   an execution error, no turn, no verdict, a turn limit, a subscription session limit, a sandbox refusal, a skipped
   grader, an unavailable evaluator — are classified exactly as before. They are never read as a split.
8. **The M13-DEF-06 admissibility rule is unchanged.** The split rule is applied to admissible runs only.
9. **No retroactive re-scoring.** Results recorded before this ADR keep their classes. The classifier keeps the prior
   rule, named explicitly, solely to confirm those stored classes, and every future evaluation is classified under
   this rule.

## Consequences

- The closing evaluation's 16 `automated_pass`, 34 `automated_fail` and 14 `execution_unavailable` stand as recorded.
- A future evaluation will record a genuine split as `execution_unavailable`, with the split named in the reason.
- M13-DEF-23 is closed as `fixed_infrastructure`.

## Revisit when

The platform exposes per-grader uncertainty or unresolved verdicts itself; an owner wants split runs re-judged rather
than recorded as unavailable; or a deterministic replacement exists for a grader that still splits.
