# 2026-09-11 — M9-C.2: advisory-language guard, documentation correction

**Milestone:** 9 — External Intelligence & Disclosure Gate (M9-C.2)
**Status on completion:** `COMPLETED`
**Supersedes:** None. Closes the second and last item deferred from M9-B, recorded in
`docs/development/2026-09-10-m9b-live-verification-closure.md` §10 item B. That record's
description of this defect was accurate and needs no correction.

---

## 1. Prompt / task performed

Implement M9-C.2 — correct the advisory-language documentation in
`commands/retrieval-slice.md` so it describes the heuristic guard the engine actually
applies rather than claiming semantic advice detection. Documentation accuracy only: do not
expand `ADVISORY_MARKERS`, do not modify `handoff.py`, research policy, EvidenceSet logic,
disclosure gates, scout or parser behaviour, or unrelated tests. Add only the minimum
documentation test needed to stop the inaccurate claim returning. Write a dated development
record, mark M9-C.2 `COMPLETED` in the plan, create no ADR unless governance requires one,
start no further M9-C work, and do not commit or push.

## 2. Objective

Make one sentence true.

The command file told the model that Python "will refuse a claim that … **reads as advice**".
Python does no such thing. It refuses a claim containing one of fifteen fixed phrases in
`handoff.ADVISORY_MARKERS`. The M9-B live verification proposed *"Logistics firms should
target a gross margin above 20% to stay competitive"* — advice by any ordinary reading — and
the engine accepted it, because no marker covers a bare "firms should".

## 3. Changes made

1. **Corrected the refusal clause.** "reads as advice" → "**contains a recognised advisory
   marker**", and added that a claim surviving every check is still `status: candidate` and
   `verified: false`, because the policy decides only whether a claim may be *proposed*.
2. **Named the mechanism.** A new paragraph states the guard is *"a heuristic guard, not a
   semantic classifier"*, that it matches a fixed phrase list, points at
   `ADVISORY_MARKERS` in `lib/python/biq/research/handoff.py`, gives three example phrases,
   says that is the whole mechanism, and states it **must not be described as comprehensive
   advice detection**.
3. **Stated the consequence for the reader.** A second paragraph: *"A statement it accepts
   is not thereby non-advisory."* It cites the live counter-example verbatim, says the
   engine accepts it, and says plainly that this is the guard working as designed rather
   than a defect to report — then returns the obligation to where it actually sits: the
   rule two paragraphs above, which is the model's to honour. Ends *"never read acceptance
   as permission."*
4. **Added `tests/unit/test_m9c2_advisory_guard_wording.py`** — 12 tests in two classes.
5. **Touched no implementation.** `handoff.py` is unchanged and `ADVISORY_MARKERS` still
   holds exactly its original fifteen phrases.

## 4. Files created

- `tests/unit/test_m9c2_advisory_guard_wording.py` — 12 tests.
- `docs/development/2026-09-11-m9c2-advisory-guard-wording.md` — this record.

## 5. Files modified

- `commands/retrieval-slice.md` — the refusal clause in step 4, plus two new paragraphs.
  Steps 1, 2, 3 and 5, the "What must never happen" table, and the frontmatter are
  **unchanged**.
- `project_plan.md` — M9-C.2 status only (§13).

## 6. Files deleted

None.

## 7. Features implemented

None, deliberately. The deliverable is an accurate instruction to a model, plus tests that
keep it accurate. **No behaviour changed anywhere.**

## 8. Tests performed

```bash
# focused
PYTHONPATH=lib/python python -m unittest tests.unit.test_m9c2_advisory_guard_wording -v

# the two contract suites that also scan commands/retrieval-slice.md
PYTHONPATH=lib/python python -m unittest tests.unit.test_m9b_scout_contract \
    tests.unit.test_m9c1_bare_envelope_contract tests.unit.test_m9c2_advisory_guard_wording

# full regression
python tests/run_tests.py
```

## 9. Test results

**Focused — 12 tests, all passing:**

```
Ran 12 tests in 0.013s
OK
```

| Class | Tests | Covers |
|---|---|---|
| `TestTheWordingIsAccurate` | 8 | "reads as advice" is gone; the refusal is described as a marker match; the guard is named a heuristic and not a classifier; it forbids calling itself comprehensive; it states acceptance proves nothing; it points at `ADVISORY_MARKERS` and `handoff.py`; **the other five policy checks are still documented**; candidate/`verified: false` still stated |
| `TestTheDocumentMatchesTheEngine` | 4 | A recognised marker is still refused (`not_a_source_claim`); the documented counter-example is still accepted; an accepted advisory statement is still `candidate` / unverified; the marker list is still a plain sequence of phrases |

**Three contract suites together — 111 tests, all passing.** This is the check that mattered:
`test_m9b_scout_contract.TestOrchestrationSurface` scans the same command file for the
dispatch instruction, the one-shot rule and the gate-authority rule, and none of that moved.

**Full regression — 1,612 tests, all passing:**

```
Ran 1612 tests in 109.654s
OK (skipped=19)
ran 1612 | failures 0 | errors 0 | skipped 19
```

Baseline 1,600 at M9-C.1; +12 is exactly this task. **Skips unchanged at 19.**

## 10. Issues discovered

None new. This task closed a known one.

Two things worth recording about the shape of the fix, because both were choices:

**The test suite couples the document to the code rather than freezing either.**
`test_the_documented_counter_example_is_still_accepted` asserts that the engine still
accepts the sentence the document cites as accepted. If someone later adds "firms should"
to `ADVISORY_MARKERS`, that test fails — and the document quoting the sentence as accepted
must be corrected in the same change. Nothing asserts the list's contents, so expanding it
stays entirely possible; what cannot happen is expanding it and leaving the document behind.
This is the same failure mode M9-C.2 exists to fix, so guarding the fix against its own
recurrence seemed worth twelve lines.

**Why an inaccurate command file is worse than an inaccurate comment.** `handoff.py` has
always been candid — *"a guard, not a proof"*, and *"no string check can decide whether a
sentence exceeds its source"*. The command file is read by a model as its instructions, and
a model told the machine will catch advice has less reason to police its own wording. The
guard's real backstop was never the phrase list; it is the rule that a statement reports
what one source said. The correction puts that obligation back in front of the reader
instead of implying it has been automated.

## 11. Decisions made

**No ADR**, determined against the bar in `docs/decisions/README.md`, which names **wording
changes** in its exclusion list explicitly. Nothing else in the bar is engaged: no contract,
invariant, boundary, topology or execution model changed; nothing became harder to undo; no
option a reviewer would expect was rejected — the option of making the guard semantic was
ruled out by the task itself and remains available to a future milestone.

## 12. Architecture changes

None. `architecture.md` not modified and requires none.

## 13. Project-plan updates

Two edits, both M9-C.2 scope:

- The deferred row *"Advisory-language documentation overstates the guard"* → `COMPLETED`,
  retitled M9-C.2, pointed at this record.
- The 9-B approval paragraph updated: both deferred items are now closed.

No other row, status or milestone touched.

## 14. Documentation updates

`commands/retrieval-slice.md` and `project_plan.md` as described. `architecture.md`,
`CLAUDE.md`, `agents/biq-research-scout.md`, `reference/research-policy.md`, every skill and
every existing development record were left alone.

## 15. Remaining work

**Both M9-B deferred items are now closed.** M9-C.1 hardened the scout return contract;
M9-C.2 corrected the advisory wording.

1. **M9-C proper** — the four research skills (`biq-company-analysis`,
   `biq-market-analysis`, `biq-competitor-analysis`, `biq-industry-research`). Not started.
2. **M9-D** — the four external commands. Not started.
3. **Not scheduled, and deliberately not proposed here:** making the advisory guard
   semantic. If it is ever wanted, it is a claim-policy change needing its own milestone and
   probably an ADR, and it would have to earn its place against the argument in §10 — the
   backstop is the model's obligation, not the string check.

## 16. Git commit reference

N/A. Branch `main`, no commit created, nothing staged, nothing pushed.

---

## Exact wording change

**Before** (`commands/retrieval-slice.md`, step 4):

> Python then applies the policy and will refuse a claim that: names no item in this set,
> rests on a tier-D source, rests on tier C alone when material, carries no publication
> date, **reads as advice**, or stands in a set with an unresolved conflict.

**After** — the clause corrected, plus two paragraphs:

> Python then applies the policy and will refuse a claim that: names no item in this set,
> rests on a tier-D source, rests on tier C alone when material, carries no publication
> date, **contains a recognised advisory marker**, or stands in a set with an unresolved
> conflict. A claim that survives every one of those checks is still `status: candidate`
> and `verified: false`. The policy decides only whether a claim may be *proposed*.
>
> **The advisory check is a heuristic guard, not a semantic classifier.** It matches a
> fixed phrase list — `ADVISORY_MARKERS` in `lib/python/biq/research/handoff.py` … That is
> the whole mechanism … and it must not be described as comprehensive advice detection.
>
> **A statement it accepts is not thereby non-advisory.** No marker matches "Logistics
> firms should target a gross margin above 20% to stay competitive", so the engine accepts
> that sentence — plainly advice, accepted, and that is the guard working exactly as
> designed rather than a defect to report … never read acceptance as permission.

**Implementation untouched.** `ADVISORY_MARKERS` still holds its original fifteen phrases —
`we should`, `you should`, `we recommend`, `i recommend`, `recommend that`, `must `,
`ought to`, `the business should`, `suggests we`, `implies we`, `therefore we`,
`this means we`, `opportunity to`, `risk to our`, `for us this` — and `handoff.py` was not
opened for editing. No NLP or LLM classification, no new markers, no new claim-policy rules,
no new evidence requirements, no new research commands, no scout or parser change.

**Final status: `M9-C.2 COMPLETED`.**
