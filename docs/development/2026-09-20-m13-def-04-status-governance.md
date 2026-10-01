# M13-DEF-04 Status Governance Reconciliation

**Date:** 2026-09-20
**Scope:** governance, documentation and validator only. There is no product change.
**Status on completion:** ADR-0043 **Accepted**. M13-DEF-04's register status is **`fixed_product`**. M13.2 remains IN
PROGRESS, and its manual observations are READY / PLANNED. Nothing committed, nothing pushed, nothing staged.
**Supersedes:** in `2026-09-20-m13-def-04-implementation.md`, only the statement that the §G.1 `status` field stays
`open` (§8 and §10 there). That record is otherwise unchanged and not edited.

## Starting State

- **Git.** `HEAD` = `origin/main` = `21ee21b21213ad80273650f056ef2f318023742c`, on branch `main`, with nothing staged.
  The working tree carried the uncommitted M13.2, M13-DEF-04 design, acceptance and implementation work: 53 status
  lines at the start, all preserved.
- **Implementation verified.** M13-DEF-04's remediation, accepted ADR-0042, was implemented on 2026-09-20:
  - T-A to T-K passed;
  - the full regression passed: 4,872 tests, 0 failures, 0 errors, 29 skipped.
- **The register still used `open`** for M13-DEF-04's §G.1 `status` field. The resolution was recorded only in prose,
  the register-state table and the project plan.

## Problem

ADR-0039 §G.1's closed `status` vocabulary was `open`, `fixed_infrastructure` and `withdrawn`. Its closing sentence
reads: "A product defect stays `open` through M13".

`tests/unit/test_m13_coverage_matrix.py` enforced this in two places:

- `DEFECT_CLOSED["status"]`;
- `test_a_product_defect_stays_open_through_m13`, which allows only `open` or `withdrawn` for product defects.

None of the three values fits a product defect fixed and verified outside M13:

- `fixed_infrastructure` would misclassify a product and runtime defect;
- `withdrawn` asserts a misread source, which is untrue here, and ADR-0039 forbids using it to accept product
  behaviour;
- `open` contradicts the implementation evidence, the project plan and the record's own disposition.

## Decision

**Add exactly one status: `fixed_product`.** The name follows the register's own convention, alongside
`fixed_infrastructure`, and keeps the product and infrastructure distinction. No generic `resolved` value was added.

**It may be used only when all of these hold:**

- the defect is product-class;
- it was fixed in a milestone outside M13, under its own prompt;
- the fix follows an accepted decision;
- the fix was verified by deterministic tests that ran and by a full regression with 0 failures and 0 errors;
- no known implementation defect remains;
- the record carries a `**Status basis (ADR-0043).**` paragraph naming the accepted ADR and the verification record.

**It never means:** designed, accepted, deferred, owner-accepted, partially fixed, or infrastructure-only.

**Unchanged:**

- the meanings of the existing statuses;
- the `blocks_m13_completion` rule (`yes` only for an open infrastructure defect);
- the M13 boundary: I-1, I-13 and §G.2, under which no product defect is fixed within M13.

## ADR

**[ADR-0043](../decisions/ADR-0043-defect-status-for-verified-product-fixes.md)**, "Defect register status vocabulary
for verified product fixes: `fixed_product`", is **Accepted**, 2026-09-20.

- **The number.** The previous highest was 0042, and no `ADR-0043*` file existed in the tree or in history.
- **What it amends.** ADR-0039 §G.1, in part: the `status` vocabulary and its closing sentence only. ADR-0039's text
  and status line are unedited, as for ADR-0040 and ADR-0041.
- **Where it is indexed:** in `docs/decisions/README.md`, with a row and an amendment note, and in `architecture.md`
  §19.

## Validator

`tests/unit/test_m13_coverage_matrix.py`:

- **Vocabulary.** `DEFECT_CLOSED["status"]` gains `fixed_product`.
- **New definitions:**
  - `CLASS_STATUSES`: product → `open`, `withdrawn`, `fixed_product`; infrastructure → `open`, `withdrawn`,
    `fixed_infrastructure`;
  - `defect_blocks()`, `status_basis()`, `adr_is_accepted()` and `status_problems()`.
- **Tightened, not weakened.** `fixed_infrastructure` is now enforced as infrastructure-only, as ADR-0039 §G.1 already
  said. A `fixed_product` basis must cite an **accepted** ADR other than 0039 and 0043, plus an existing
  `docs/development/` record.
- **Amended test.** `test_a_product_defect_stays_open_through_m13` now allows `fixed_product` alongside `open` and
  `withdrawn`, and still forbids `fixed_infrastructure` for a product defect. No assertion was removed.
- **New test in `DefectRegisterIsComplete`.** `test_every_status_pairs_with_its_class_and_a_product_fix_states_its_basis`
  checks the real register.
- **New class `StatusVocabularySemantics`**, with 6 tests on synthetic records:
  - the new status is accepted with its basis;
  - the five existing class and status pairs are still accepted;
  - invalid statuses are rejected: `fixed`, `resolved`, `closed`, `done`, `FIXED_PRODUCT`, `fixed-product`,
    `fixed_product ` with a trailing space, the empty string and `None`;
  - each fix status is bound to its class;
  - five basis defects are rejected: no paragraph, no ADR, only ADR-0039 and ADR-0043, a non-existent ADR, and a
    missing record;
  - the blocking rule gives `no` for a product fix.
- **Checked on the real record, in memory:**
  - M13-DEF-04 as written has no problems;
  - without its basis paragraph → rejected;
  - relabelled as infrastructure → rejected;
  - with the cited ADR swapped for an unaccepted one → rejected.

## M13-DEF-04

`docs/testing/defects.md`:

- **The `status` field** changed from `open` to **`fixed_product`**, and the register-state table row now reads
  `fixed_product` (ADR-0043).
- **A `**Status basis (ADR-0043).**` paragraph was added.** It distinguishes **discovered during M13** (M13.2 WD-1,
  2026-09-19) from **fixed after M13 under ADR-0042** (2026-09-20), and cites the verification record.
- **The "why the status field still reads `open`" bullet** was replaced with a dated statement of the change.
- **`blocks_m13_completion` stays `no`.**
- **Nothing removed.** The original description, root cause, security finding, reproducer, test evidence and
  remediation text are all kept. The register introduction now lists the amended vocabulary.

## M13.2

**M13.2 remains IN PROGRESS.** This change does not complete it. The manual observations are **READY / PLANNED**, as a
separate, owner-controlled step. No eval was run, and no manual observation was performed. `docs/testing/manual/`
does not exist.

## Open Items

- **G-3:** OPEN (the eval sandbox).
- **V-4:** OPEN (the minimum Claude CLI version).
- **Unix-like runtime verification:** OPEN.

## Other documentation

- `project_plan.md`: two statements that the field "still reads `open`" now read `fixed_product` (ADR-0043).
- `docs/testing/README.md`: the defects row names the amended vocabulary.
- `docs/testing/manual-observation-pack.md`:
  - the historical WD-1 sentence is annotated with the current status;
  - the *Current state* block gains the register status and "READY / PLANNED".
- `docs/testing/eval-suite.md` needed no change; it has no contradictory status language.

## No Product Changes

This task changed governance, documentation and one validator test module only. Nothing changed under:

- `lib/`, `commands/`, `skills/`, `agents/`, `reference/`, `config/`, `.claude-plugin/` or `.mcp.json`;
- `evals/`;
- ADR-0039, ADR-0040, ADR-0041 or ADR-0042;
- any test other than `tests/unit/test_m13_coverage_matrix.py`.
