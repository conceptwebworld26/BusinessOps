# 2026-09-26 — M13-DEF-13 remediation: the provenance-aware research boundary

**Milestone:** Product remediation outside M13 (ADR-0039 I-13, §G.2). Milestone 13 stays `COMPLETED`; no later milestone is started.
**Status on completion:** REVIEW — M13-DEF-13 `fixed_product` (ADR-0043), verified deterministically; not committed
**Supersedes:** None. Every earlier record stays as written.

## 1. Prompt / task performed

The owner asked for remediation of M13-DEF-13 only. In `d05`, a customer name from the staged demo dataset reached a
`biq-research-scout` dispatch. The brief:

- investigate before implementing;
- treat `d05` as evidence against the product, not the evaluator;
- build a deterministic, provenance-aware, fail-closed boundary before research dispatch, reusing the existing
  disclosure architecture and adding no caller-controlled public flag;
- keep legitimate public research working;
- test the listed bypasses;
- record the change in an ADR, the defect register and the plan.

Excluded: live, paid, MCP or web evaluation; changes to historical results; commit or push; M14.

## 2. Objective

Make it impossible for the research pipeline to brief the scout with a value that came from the user's business data,
unless an existing disclosure policy explicitly permits it.

## 3. Changes made

1. **Investigation.** Read the gate, request contract, query builder, handoff, retrieval and scout modules, the
   privacy classes and field classifier, ADR-0009, the company-analysis skill, the scout agent, the `d05` case and the
   M13-DEF-13 record.
   - **Root cause.** `gate.assess()` judged a request by its **shape**:
     - it refused prohibited term *keys*;
     - it trusted a descriptor's caller-declared `source_sensitivity`;
     - it treated the subject, every other term value and the operation id as public by construction.
   - A customer name passed as the subject therefore got Tier 0. The ingestion-time column classification, which
     classes `Customer` as `never`, was never consulted at the gate.
   - M10.2-R.14 had pinned the same gap for figures (`our_revenue`).
2. **`lib/python/biq/research/boundary.py` (new).**
   - **The register.** An `InternalValueRegister` is built from the working directory's `.csv`, `.tsv`, `.xlsx` and
     `.xlsm` files, reading every sheet with the existing stdlib readers and classifying columns with
     `privacy.classify_dataset`. It holds the values of non-`public` columns, each with its provenance (class, column,
     file). It lives in memory only and is immutable.
   - **Not caller-controlled.** `workspace_register()` takes no argument. The plugin's own tree (synthetic assets and
     fixtures) is never read.
   - **Fail-closed.** An unreadable file, a file over 100 MB, more than 50 data files, or more than 20,000 entries
     raises `BoundaryUnverifiable`.
   - **Screening.** `screen()` checks every caller-supplied fragment for whole normalised registered values and for
     distinctive numbers. It also checks the subject, term values and descriptor labels for exact figures that have no
     public provenance. Findings are value-free.
3. **`gate.py`.** `assess()` builds the register first; if it cannot, it refuses with `internal_boundary_unverifiable`.
   It then screens every request after structural validation. The decision follows the existing class-to-tier rule:
   - `never` → refused at every tier;
   - other internal material in the query text → refused below Tier 2, and `ALLOW_WITH_APPROVAL` at Tier 2;
   - internal material outside the query text → refused at every tier.

   Every Tier 0 alternative is now rebuilt from the surviving fragments and vetted again, so none can repeat the value.
4. **`contract.py`.** Two reason codes: `internal_business_value` and `internal_boundary_unverifiable`.
5. **`handoff.py`.** Every refusal record carries `research_performed: false`.
6. **Tests.**
   - New: `tests/unit/test_m13_def13_research_boundary.py`, 32 tests.
   - Updated: the M10.2-R.14 pinning test (`test_m10_2r14_local_join.py`), which asserted that the gap existed. It now
     asserts the gap is closed, and its two control assertions are kept.
7. **Governance.** ADR-0050; the ADR index; `architecture.md` §7 (enforcement), §19 (ADR row) and §20 (item 12);
   `reference/research-policy.md` (Enforcement); the defect register; `project_plan.md`; this record.

## 4. Files created

- `lib/python/biq/research/boundary.py`
- `tests/unit/test_m13_def13_research_boundary.py`
- `docs/decisions/ADR-0050-provenance-aware-research-boundary.md`
- `docs/development/2026-09-26-m13-def-13-remediation.md` (this record)

## 5. Files modified

- `lib/python/biq/research/gate.py`
- `lib/python/biq/research/contract.py`
- `lib/python/biq/research/handoff.py`
- `tests/unit/test_m10_2r14_local_join.py` (one test)
- `architecture.md`, `reference/research-policy.md`, `docs/decisions/README.md`, `docs/testing/defects.md`,
  `project_plan.md`

## 6. Files deleted

None.

## 7. Features implemented

The provenance-aware research boundary (ADR-0050).

## 8. Tests performed

- the focused test module;
- the research, disclosure, scout, privacy and M9 to M11 boundary modules, run together;
- `python3 tests/run_tests.py -v`;
- `claude plugin validate . --strict`;
- `git diff --check`;
- the secret scan;
- a byte-identity check of the five evaluation fixtures;
- a scope audit.

## 9. Test results

Recorded in the task report. At the time of writing: the focused module passes 32 of 32. The full regression passes
5,194 tests with 0 failures and 31 skipped, which is the M13.2 baseline of 5,162 plus the 32 new tests.

## 10. Issues discovered

- **The M10.2-R.14 pinned gap is closed.** An internal figure under an unlisted term key is now refused.
- **Classification limit.** `Segment` columns are classed `public` by the existing ingestion rule, so their values are
  not registered. This is recorded as a limitation and not changed here, because it is a classification decision.
- **Partial-value matching** and **data outside the working directory** are not covered. Both are recorded in ADR-0050
  and `architecture.md` §20 item 12.

## 11. Decisions made

ADR-0050, directed and authorised by the owner in the prompt.

## 12. Architecture changes

The disclosure gate now establishes provenance from the workspace's business data (`architecture.md` §7). The tiers,
sensitivity classes and classification rules are unchanged. So are the capability chain (decision → retrieval request
→ brief) and the scout's tool grant.

## 13. Project-plan updates

M13-DEF-13 → `fixed_product`, in the known-issues row and in a status bullet. Milestone 13 stays `COMPLETED`.

## 14. Documentation updates

As listed in §5. No historical record, evaluation fixture, case file or earlier ADR was edited.

## 15. Remaining work

- **Live confirmation of `d05`.** It requires a new owner-authorised evaluation, and none was run.
- **Open product defects:** M13-DEF-14, -15, -16 and -24, plus M13-DEF-01 and -03.
- **ADR-0050's known limits.**

## 16. Git commit reference

N/A. Nothing staged, committed or pushed. Branch `main`, HEAD `8287e98f483d82d70502e959388ab0b0708f1e1f`.
