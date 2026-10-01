# 2026-09-11 — M9-C.4: structured evidence conflict transport

**Milestone:** 9 — External Intelligence & Disclosure Gate (M9-C.4)
**Status on completion:** `COMPLETED`
**Supersedes:** None. Closes the gap reported in
`docs/development/2026-09-11-m9c3-company-analysis-skill.md` §10.

---

## 1. Prompt / task performed

Implement M9-C.4 — a clean, explicit transport so a research skill can pass an observed
conflict into the existing `EvidenceSet` without a second pipeline and without Python
inferring conflicts. Inspect the existing contracts first and stop if they cannot safely
support it. Evaluate a `conflicts=` input analogous to `proposals=`, without assuming it is
right. Validate structurally; reject malformed and unknown references; preserve local tier
authority, untrusted content, fail-closed behaviour and the disclosure gate. Add no
resolution mechanism if the model has none. Assess whether an ADR is required rather than
creating one automatically. Comprehensive deterministic tests, no live retrieval, dated
record, plan update for M9-C.4 only. No commit, no push.

## 2. Objective

Make an already-observed conflict representable in the authoritative evidence set. Not
automatic detection — the opposite: an explicit, validated, typed declaration.

## 3. Changes made

### Inspection first

Reading `sources.assess_conflict()` decided the design, and it turned on one property that
documentation does not state:

| Property of the existing model | Consequence for this task |
|---|---|
| Compares caller-supplied `SourcePosition` objects; never reads retrieved text | Good — the no-inference rule is already structural |
| Decides `CONFLICTS` vs `AGREES` from a **numeric spread** against a 20% threshold | **Decisive.** See below |
| Returns `AGREES` when positions are not numerically comparable | A definitional conflict would be recorded as agreement |
| Three states — `AGREES`, `CONFLICTS`, `SINGLE`. No *resolved* state | No resolution mechanism added, per the brief |
| `close_retrieval` returns `evidence.as_dict()`; the object never escapes | Confirms the gap: `record_conflict()` was unreachable, not missing |

The decisive finding: **the numeric test cannot see the conflict that motivated the work.**
The M9-B live conflict was definitional — the scout's own words were *"sources disagree
sharply because they define 'gross margin' differently … this is a definitional conflict,
not a factual one."* Two sources measuring incompatible things can report nearly identical
figures, and `assess_conflict` would file that as `AGREES`.

So a transport that simply forwarded positions to the existing assessment would have
recorded **agreement** for the exact case the milestone exists to fix. That is what made
this an architectural decision rather than a parameter addition, and it is why ADR-0016
exists.

### Implementation — three small changes, each in the module that owns the concept

1. **`sources.assess_conflict(..., declared=False, reason=None)`** — a declared conflict
   returns status `CONFLICTS` whatever the spread, carries `declared: true`, keeps the
   numeric verdict under `numeric_assessment`, sets `confidence_effect: "lowered"`, and
   takes a caller-supplied reason or falls back to the existing `_likely_reason()`. Default
   `False` leaves M9-A behaviour byte-identical. Extracted `_spread_pct()` so both paths
   compute the spread the same way.
2. **`EvidenceSet.record_conflict(..., declared=False, reason=None)`** — pass-through. The
   pre-M9-C.4 signature behaves exactly as before.
3. **`handoff.close_retrieval(..., conflicts=None)`** plus `_structured_conflicts()` — the
   validated transport, the mirror of `_candidate_claims`. Refusals are returned in a new
   `conflicts_not_recorded` key, as results rather than errors.

**Ordering matters and is deliberate:** conflicts are recorded *before* claims, because an
unresolved conflict is one of the conditions that refuses a claim. Recording them afterwards
would let a claim stand that the same call then contradicts.

### Validation rules, and why each exists

| Rule | Refusal | Why |
|---|---|---|
| Must be a record | `malformed_conflict` | — |
| Must name a subject | `no_subject` | A conflict about nothing cannot be read later |
| `positions` must be a list | `malformed_positions` | — |
| At least two positions | `insufficient_positions` | One source cannot disagree with itself |
| Two positions must name **different** items | `single_source` | Same reason, after id resolution |
| Each position a record naming a known `evidence_id` | `invalid_position` | An unknown id would create evidence that was never retrieved |
| Each position carries a non-empty scalar value | `invalid_position` | Containers and blanks are not "what the source said" |
| Position fields limited to `evidence_id`, `value`, `unit`, `definition`, `scope` | `invalid_position` | **The security rule.** `source_tier` is not accepted; a position that could name its own tier would let a caller promote a content farm by asserting `"A"` |

Source, tier, date and freshness are read from the evidence item the position names. The
caller says *which item* and *what that item said*; everything conferring authority is
looked up locally.

### Company Analysis — minimal change only

`skills/biq-company-analysis/SKILL.md`: method step 7 now says to declare the conflict, and
the `## Known limitation` section — which is no longer true — was replaced by
`## Declaring a conflict`, showing the shape and stating that an empty array means *nothing
was declared*, never that sources agree. No redesign; the ten output sections, input
contract, failure conditions and every other rule are untouched.

Two M9-C.3 tests were updated because their wording described the old limitation as current
fact. Neither assertion was weakened: `test_the_conflicts_array_is_empty_on_this_path` became
`..._until_one_is_declared` with the no-inference meaning made explicit, and the limitation
test became `test_it_says_an_empty_conflicts_array_is_not_agreement` plus a new test that the
skill tells the model how to declare one.

## 4. Files created

- `tests/unit/test_m9c4_conflict_transport.py` — 53 tests
- `docs/decisions/ADR-0016-declared-conflicts-outrank-numeric-agreement.md`
- `docs/development/2026-09-11-m9c4-conflict-transport.md` — this record

## 5. Files modified

| File | Change |
|---|---|
| `lib/python/biq/research/sources.py` | `declared`/`reason` on `assess_conflict`; `_declared_conflict()`; `_spread_pct()` extracted |
| `lib/python/biq/research/evidence_set.py` | `declared`/`reason` on `record_conflict` |
| `lib/python/biq/research/handoff.py` | `conflicts=` input, `_structured_conflicts()`, `_position()`, `_refuse_conflict()`, `_clean_text()`, `conflicts_not_recorded` in the result |
| `skills/biq-company-analysis/SKILL.md` | Step 7; limitation section replaced |
| `tests/unit/test_m9c3_company_analysis.py` | Two tests re-pointed at the new behaviour |
| `architecture.md` | Conflict paragraph in *Source tiering, recency, conflicts*; ADR table |
| `docs/decisions/README.md`, `docs/README.md` | ADR index |
| `project_plan.md` | M9-C.4 status |

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | User-reachable? |
|---|---|---|
| Declared-conflict transport | `handoff.close_retrieval(conflicts=...)` | Not directly — consumed by research skills |
| Declared-conflict semantics | `sources.assess_conflict(declared=True)` | No |
| Conflict declaration in Company Analysis | `skills/biq-company-analysis/SKILL.md` | Model-invocable only; `/company-analysis` is M9-D |

## 8. Tests performed

```bash
PYTHONPATH=lib/python python -m unittest tests.unit.test_m9c4_conflict_transport
PYTHONPATH=lib/python python -m unittest tests.unit.test_m9a_research_core \
    tests.unit.test_m9b_candidate_claims tests.unit.test_m9b_scout_contract \
    tests.unit.test_m9c1_bare_envelope_contract tests.unit.test_m9c2_advisory_guard_wording \
    tests.unit.test_m9c3_company_analysis tests.negative.test_m9b_scout_security
python tests/run_tests.py
claude plugin validate .claude-plugin/plugin.json --strict
```

## 9. Test results

**Focused — 53 tests, all passing:**

```
Ran 53 tests in 0.028s
OK
```

| Class | Tests | Covers |
|---|---|---|
| `TestValidTransport` | 13 | One and multiple conflicts reach the set; subject, unit, definition and reason preserved; derived reason when none given; confidence lowered; summary counts it; **a declared conflict is not downgraded when the figures agree**; non-numeric positions transportable; unresolved stays unresolved; neither source preferred |
| `TestExistingBehaviourUnchanged` | 6 | Omitted, `None` and `[]` all behave as before; `record_conflict` without `declared` still lets the numbers decide; `assess_conflict` still finds a numeric conflict unaided and carries no `declared` flag |
| `TestInvalidTransport` | 16 | Not a record; no/blank subject; positions not a list; zero and one position; same item twice; position not a record; missing, non-string and unknown `evidence_id`; missing value; container value; undocumented field; one bad conflict does not block a good one; nothing raises |
| `TestNoInference` | 6 | Differing text produces nothing; wildly different figures produce nothing; a page shouting "CONFLICT" produces nothing; a `conflicts` key on a record is dropped; an envelope-level `conflicts` key is ignored; only an explicit declaration records one |
| `TestSecurity` | 8 | A position may not supply `source_tier`; tier, source and date all come from the evidence item; a refused request yields no set to attach one to; disclosure tier unchanged; content stays untrusted; instruction-safe view still withholds content |
| `TestClaimsUnderConflict` | 4 | A claim stands with no conflict; a declared conflict refuses it in the same call; a **refused** conflict does not block a claim; claims stay unverified |

**Prior M9 suites — 328 tests, all passing, unchanged.** `test_m9a_research_core`,
`test_m9b_candidate_claims`, `test_m9b_scout_contract`, `test_m9c1_bare_envelope_contract`,
`test_m9c2_advisory_guard_wording`, `test_m9c3_company_analysis`,
`test_m9b_scout_security`. No existing assertion was weakened to accommodate this change;
the only edits were the two M9-C.3 tests whose *wording* described the closed gap.

**Full regression — 1,725 tests, all passing:**

```
Ran 1725 tests in 445.159s
OK (skipped=19)
ran 1725 | failures 0 | errors 0 | skipped 19
```

Baseline 1,671 at M9-C.3; +54 is this task (53 new, +1 net from the M9-C.3 edit).
**Skips unchanged at 19.**

**Plugin validation:** the known **R-08** advisory only, unchanged.

## 10. Issues discovered

**Pre-existing ADR index drift, corrected.** The convention in `docs/decisions/README.md`
is that every accepted ADR appears in that index, in `docs/README.md` and in
`architecture.md`. **ADR-0015 was in none of the first two, ADR-0014 in neither the
architecture table nor `docs/README.md`.** Both were added alongside 0016 — indexing 0016
correctly while leaving a hole immediately above it would have made the index worse. This
was not caused by M9-C.4 and is recorded here rather than silently fixed.

**No resolution state exists, and none was added.** The model supports `AGREES`,
`CONFLICTS` and `SINGLE`. Per the brief, unresolved-only behaviour is preserved: a conflict
cannot be marked resolved, and preferring one source does not erase the record.
`test_an_unresolved_conflict_stays_unresolved` asserts no resolution key appears.

**A consequence worth knowing.** Declaring a conflict refuses candidate claims in the same
call. That is the existing policy working as written, not a new restriction — but a skill
that declares a conflict and expects a claim will find none, and the reason is in
`claims_not_produced` as `unresolved_conflict`.

## 11. Decisions made

**ADR-0016 — Declared conflicts outrank numeric agreement.** Written because the governance
bar is genuinely met, not because the API changed: the decision establishes that a declared
conflict sets the status regardless of the numeric spread, which changes how the evidence
model resolves a disagreement between the model's observation and the engine's arithmetic.
That is a load-bearing invariant, it constrains the three remaining research skills, and it
is exactly the kind of thing someone would later ask "why on earth is it like this?" about.

Three options were weighed. Option A — let the numeric assessment decide — was rejected on
its own motivating example. Option C — infer conflicts from content — was rejected outright
as the inference the deterministic engine must not perform. Option B was chosen.

## 12. Architecture changes

`architecture.md` gained a paragraph in *Source tiering, recency, conflicts* stating that a
conflict enters the set only by explicit declaration, that the engine never infers one, that
a declaration confers no authority, and that only unresolved conflicts are representable.
The ADR table gained 0014 and 0016.

## 13. Project-plan updates

M9-C.4 scope only: the `DEFERRED` row becomes `COMPLETED` with the record and ADR cited. The
three sibling skills and the four commands remain `PLANNED`, untouched.

## 14. Documentation updates

ADR-0016, the architecture paragraph and ADR table, both ADR indexes, the Company Analysis
skill's conflict sections, this record, and the plan row. No other skill, command, reference
page or development record was modified.

## 15. Remaining work

1. **M9-C.5 — live Company Analysis verification.** Deliberately not performed here. It is
   the first end-to-end exercise of this transport, and the M9-B definitional conflict is the
   obvious scenario to replay against the real thing.
2. **The three sibling skills** — market, competitor, industry. Each should use `conflicts=`
   from the start rather than inheriting a documented gap.
3. **M9-D** — the four external commands.

## 16. Git commit reference

N/A. Branch `main`, no commit created, nothing staged, nothing pushed.

---

## The contract now shipped

```python
close_retrieval(payload, subject, category, conflicts=[{
    "subject": "gross margin definition",              # required
    "reason":  "Different definitions, not different facts.",   # optional
    "positions": [                                     # >= 2, distinct evidence items
        {"evidence_id": "ev-…", "value": 92.19, "unit": "%",
         "definition": "revenue minus COGS", "scope": "listed carriers"},
        {"evidence_id": "ev-…", "value": 12.5, "unit": "%",
         "definition": "sell rate minus buy rate"},
    ],
}], ...)
```

Accepted position fields: `evidence_id`, `value`, `unit`, `definition`, `scope` — and
nothing else. Refusals return in `conflicts_not_recorded`. Omitting `conflicts` leaves every
existing caller byte-identical.

**Final status: `M9-C.4 COMPLETED`.**
