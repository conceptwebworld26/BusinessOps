# 2026-09-15 — M10.2-R.3: the internal↔external ALLOW branch, on a deterministic fixture

**Milestone:** 10.2-R.3 — Deterministic internal↔external ALLOW-branch verification
**Status on completion:** COMPLETED — ALLOW reached through the production path on a
synthetic fixture. **No live research. No scout. No production change.**
**Supersedes:** None. Follows `2026-09-15-m10-2r2-canonical-unit-semantics.md`.

## 1. Prompt / task performed

Exercise the seven-dimension compatibility ALLOW branch across the internal/external
boundary using a truthful deterministic fixture, and prove the branch is not overly
permissive. Verification only: no live research, no scout dispatch, no change to
`compatibility.compare()`, no R-12 change, no commit. None of those were done.

## 2. Objective

Every previous cross-domain exercise of the seven-dimension test **rejected**. Rejection
alone proves nothing: a function that always returned `INCOMPATIBLE` would have passed all
of them. This milestone had to show the other half — that a genuinely comparable pair
reaches `COMPATIBLE` through the real engine, with nothing forced.

## 3. Changes made

**Verification only. No production file was touched.** One new test module,
`tests/unit/test_m10_2r3_allow_branch.py`, 51 tests.

### The fixture, and what it is not

> **The evidence is synthetic and is not a real external source.** `Synthetic Logistics Ltd`
> is not a company. `synthetic-source.example.invalid` is a reserved host that can never
> resolve. The figures are invented for this test. **Nothing in this milestone is a
> real-world observation, and nothing in it reached a network.**

The pair is truthful in the sense that matters: the external statement describes *the same
metric, of the same entity, over the same period, on the same basis* as the internal
calculation — a filed-account restatement of a company's own revenue. That is the one shape
where an internal↔external monetary comparison is legitimate, and it is deliberately **not**
revenue against a market size, which must never compare.

Internal: `AnalysisSet` → `from_analysis_set()` → `CALCULATION`, GBP 12,500,000, footed on a
registered dataset. External: an `EvidenceItem` on the reserved host → `register_external()`
→ `sourced_statement(source_unit="GBP million", observed=Decimal("12.5"))`, canonicalised at
construction to `Decimal("12500000")`, `unit=currency`, `currency=GBP`.

**Ephemeral only.** No persistent Business Context, no `.businessiq/`, no
`businessiq-output/`, no production data. The fixture lives in the test module.

### The result

```
status      : compatible      matched 7 | mismatched 0 | unknown 0
converted   : False           NEVER_CONVERTS: True
may_combine : True
```

Nothing was manually set: `compare()` was called on the two constructed items and its own
record returned, carrying its own seven keys and its own `REASON[COMPATIBLE]` string.

### What the milestone found about compatibility and value equality

`compatibility.compare()` **never reads a value** — there is no `observed` in the module. So
a pair compatible on all seven dimensions while stating materially different numbers comes
back `COMPATIBLE`, and `compare_values()` returns early, recording **no conflict and no
limitation**.

This is the architecture separating *may these be related* from *do they agree*, and it is
documented here rather than treated as a defect. But it is worth the owner's attention:
**a value disagreement between an internal figure and a comparable external one is a finding
this architecture currently has nowhere to put.** The conflict layer fires only when the
pair is *not* comparable — which is the opposite of when a numeric disagreement is most
meaningful. Pinned by four tests so a future milestone changes it deliberately.

## 4. Files created

| Path | Purpose |
|---|---|
| `tests/unit/test_m10_2r3_allow_branch.py` | 51 tests: ALLOW, normalisation, provenance, negative controls, conflict boundary, support, serialisation, security |
| `docs/development/2026-09-15-m10-2r3-deterministic-allow-branch.md` | This record |

## 5. Files modified

- `project_plan.md` — M10.2-R.3 section.

**No production file, schema, command, skill, agent or existing test was modified.**

## 6. Files deleted

None. No test removed, disabled or weakened.

## 7. Features implemented

**None.** This milestone adds no capability. It verifies work already accepted in ADR-0025
and implemented in M10.2-R.2.

## 8. Tests performed

```bash
python -m unittest tests.unit.test_m10_2r3_allow_branch
python tests/run_tests.py
claude plugin validate . --strict
```

## 9. Test results

```
python -m unittest tests.unit.test_m10_2r3_allow_branch
Ran 51 tests in 0.021s
OK

python tests/run_tests.py
Ran 3062 tests in 404.321s
OK (skipped=19)
ran 3062 | failures 0 | errors 0 | skipped 19

claude plugin validate . --strict
✔ Validation passed   (exit 0)
```

3,062 = 3,011 (M10.2-R.2 baseline) + 51 new. **No existing test changed**, which is the
evidence that no production behaviour moved.

Three of my own assertions were wrong on first run and were corrected rather than the
production code: a directly-constructed `EvidenceItem` carries no pipeline `notes` (its
`trust` is what marks it untrusted); the word *quantity* appears in `compatibility.py`'s own
prose, so the no-import assertion had to be written precisely; and the local tiering note is
added by the retrieval pipeline, so the test now re-derives the tier through
`sources.classify_tier()` instead.

## 10. Issues discovered

- **No value-disagreement finding exists for a comparable pair** (§ 3). Documented, pinned,
  not changed.
- **The fixture's evidence is constructed directly**, as the existing synthesis fixtures do,
  so it does not exercise the retrieval pipeline's note-writing and local re-tiering. The
  tier is still verified: `register_external()` re-derives it and refuses anything stronger,
  demonstrated by the tier-A forgery probe. But this fixture does not stand in for a
  pipeline-built set.
- **ALLOW does not raise support.** The external statement stays `partially_supported` at
  tier C with `MEDIUM` confidence, and the internal stays `supported`/`HIGH`. Comparability
  and grading are independent, and a compatible pair is not a verified one.

## 11. Decisions made

None. No ADR. ADR-0025 is unmodified and no new architectural decision was required.

## 12. Architecture changes

None. `compatibility.py` is byte-identical to its M10.1 form (122 lines, md5
`35a89e32f6fad71bc7c21abe9dbe4915`, unchanged before and after this milestone).

## 13. Project-plan updates

New M10.2-R.3 section, `COMPLETED`. **M10.2-R remains `PARTIALLY VERIFIED`** — this
milestone is deterministic and synthetic, and says nothing about live runtime behaviour.
R-12 remains open.

## 14. Documentation updates

`project_plan.md` and this record. `architecture.md` needed no change: nothing architectural
moved.

## 15. Remaining work

1. **Live runtime evidence for M10.2-R.** A deterministic ALLOW is not a live ALLOW; the
   live leg still depends on a clean first-delivery scout retrieval.
2. **R-12** — open, untouched.
3. **D-12** — `architecture.md` still does not describe the seven-dimension test.
4. Owner decision on whether a value-disagreement finding should exist for comparable pairs.

## 16. Git commit reference

N/A — no commit was made. No branch created, nothing staged, nothing pushed.
