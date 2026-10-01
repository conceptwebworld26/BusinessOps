# ADR-0040 — An owner-accepted environment-unavailable gap in the M13 coverage matrix: a recorded gap, never a defect and never coverage

**Date:** 2026-09-18
**Status:** Accepted — 2026-09-18, by the project owner, in the M13.1 contract conformance remediation prompt. That
prompt directed this amendment and specified its content. Acceptance authorises no implementation, no production
change, no eval and no dependency installation.
**Deciders:** Project owner (U-1 decision (c), 2026-09-18; this amendment), raised by the M13.1 final remediation
**Supersedes:** none. **Amends:** [ADR-0039](ADR-0039-m13-test-hardening-and-evals-contract.md), in part: the `gap`
definition in §B and the second M13.1 condition in §L only (see *Amended wording*). ADR-0039's text and status line
are not edited. The amendment is recorded here, in `docs/decisions/README.md` and in `architecture.md` §19, as the
repository did for ADR-0022 and ADR-0004.
**Relates to:** ADR-0007 (two-layer testing), [ADR-0008](ADR-0008-tiered-xlsx-ingestion.md) (tiered `.xlsx`
ingestion; openpyxl only in the consented managed runtime), ADR-0010 (approval follows consequence).

## Context

ADR-0039 §B gives every coverage-matrix row exactly one status. It defines `gap` as "with the defect id (§G.1) that
explains why it is still open". §L makes M13.1 `COMPLETED` conditional on "every deterministic gap either closed, or
`gap` with a defect id". §G.1 allows two defect classes:

- `product`: BusinessIQ behaviour;
- `infrastructure`: a defect "in M13's own tests, fixtures, graders, scaffolds or static validator".

An `open` infrastructure defect is `blocks_m13_completion: yes` by rule.

M13.1 found one deterministic row that none of those outcomes describes truthfully. These facts are recorded in
`docs/testing/coverage-matrix.md` and in the M13.1 development records of 2026-09-18:

- **S2-14, cross-tier equivalence** (the same fixture at Tier 1 and Tier 3) is covered by eight existing Tier-1
  tests: 7 in `integration.test_data_layer.TestCrossTierEquivalence` and
  `integration.test_vertical_slice.TestCrossTierEquivalence.test_tier1_and_tier3_agree`.
- All eight are skipped, because the system interpreter, Python 3.13.1, cannot import openpyxl, and Tier 1 is
  openpyxl in that interpreter.
- `CLAUDE.md` §4 and ADR-0008 prohibit installing openpyxl into the system interpreter.
- The consented managed runtime is Tier 2. It is a separate process and does not make these Tier-1 tests execute.
- No test, measurement or observation shows the product failing the requirement. The tests have not run.

The only honest status is `gap`. But a product defect id would misstate the finding. An infrastructure defect id would
misstate it too: the tests are not M13's, and they are right to skip. It would also block M13 by rule. On 2026-09-18
the owner decided U-1 as (c): accept S2-14 as an open gap. The M13.1 final remediation then found that §L, as written,
cannot be met by that decision, and it stopped rather than invent a defect id or upgrade the evidence.

## Problem

Give ADR-0039 a truthful way to record a deterministic gap whose evidence cannot execute in the approved environment,
and let that gap satisfy M13's completion gate. It must not turn missing evidence into positive evidence, and it must
not hide a defect.

## Options considered

### Option A — Assign S2-14 a defect id

**Rejected.**

- `product` asserts a product failure no evidence shows.
- `infrastructure` misdescribes correct, pre-M13 tests, and it would block M13 by rule.
- Either would be a false record, made to satisfy a checklist.

### Option B — Mark S2-14 `covered` from the Tier-3 and CSV tests that do run

**Rejected.** Those tests compare Tier 3 with CSV, not with Tier 1. ADR-0039 §B forbids `covered` on a skipped test.

### Option C — Install openpyxl, or fabricate a Tier-1 environment

**Rejected.** Installing it is prohibited by `CLAUDE.md` §4 and ADR-0008. A fabricated environment would produce
evidence about nothing real.

### Option D — Leave M13.1 permanently unable to complete

**Rejected.** It makes an owner-accepted, fully disclosed gap indistinguishable, at the gate, from an undisclosed one.

### Option E — A third, narrowly defined gap disposition: owner-accepted, environment-unavailable, never a defect and never coverage

**Chosen.**

## Decision

### 1. Three distinct things, never merged

| | Product defect | Test-infrastructure defect | Owner-accepted environment-unavailable gap |
|---|---|---|---|
| What it is | BusinessIQ behaviour or shipped documentation that does not meet a stated requirement | A defect in M13's own tests, fixtures, graders, scaffolds or static validator | The row's evidence cannot execute, because the capability it needs is unavailable in the approved execution environment |
| Identifier | `M13-DEF-NN` (ADR-0039 §G.1) | `M13-DEF-NN` (ADR-0039 §G.1) | An owner-decision identifier (for S2-14, `U-1`). **Never** an `M13-DEF-NN` id |
| Recorded in | `docs/testing/defects.md` | `docs/testing/defects.md` | `docs/testing/coverage-matrix.md`: the row, plus a disposition section for that row. **Not** in the defect register |
| Matrix status | `gap` | Fixed within M13, so the row is re-assessed | `gap` |
| Effect on M13 completion | Unchanged: may stay `open` (ADR-0039 §G.2) | Unchanged: must be fixed. Open means `blocks_m13_completion: yes` | May satisfy the gate when §2 and §3 are fully met |

### 2. Eligibility — all five must hold

A matrix row may carry this disposition only if **every** one of these is true:

1. **The covering tests exist and are unchanged.** They are neither weakened, removed nor replaced. They skip only
   because a named capability is absent from the execution environment, and their skip reason says so.
2. **M13 may not provide the capability.** Obtaining it in the approved environment is prohibited by existing
   repository governance, or lies outside ADR-0039 §A.2.
3. **No evidence of a product failure.** No executed test, measurement or observation shows the product failing the
   requirement. If one does, the row is a **product defect** under ADR-0039 §G.1, and this disposition is unavailable.
4. **Not caused by M13's own infrastructure.** If it is, the row is a **test-infrastructure defect**, fixed within M13
   (ADR-0039 §G.2), and this disposition is unavailable.
5. **Explicitly accepted by the owner**, with a date. An owner decision records the gap. It is not evidence (§4).

### 3. The mandatory disposition record

Each such row carries, in `docs/testing/coverage-matrix.md`, all of:

| Field | Content |
|---|---|
| Matrix row id | e.g. `S2-14` |
| Status | `gap` |
| Evidence | `execution_unavailable` |
| Label | Exactly `OPEN GAP — ENVIRONMENT UNAVAILABLE` |
| Reason execution is unavailable | The concrete, verifiable reason: the missing capability, the skip reason, and the governance that prevents providing it |
| Owner decision | The decision identifier and the option chosen |
| Decision date | ISO date |
| Closure environment required | The environment or capability in which the covering tests would execute, and the condition under which that environment is acceptable |
| Not covered | An explicit statement that the row is not covered and is not counted as covered |
| Not a product defect | An explicit statement |
| Not a test-infrastructure defect | An explicit statement |

A row missing any field does not have this disposition. For ADR-0039 §L it is then an unexplained gap.

### 4. What the disposition can never do

- **It never counts as coverage.** The row stays `gap` in every total, summary and status line. It is never
  `covered`, `covered-by-M13`, passed, verified, equivalent or demonstrated.
- **An owner decision cannot turn unavailable evidence into positive evidence.** Acceptance records that the gap is
  known and disclosed. It says nothing about whether the product meets the requirement.
- **It cannot conceal a defect.** It is unavailable whenever §2.3 or §2.4 fails. If a later run of the covering tests
  executes and fails, the result is a product defect record (or an infrastructure one, as §G.1 decides), never a
  continued environment gap.
- **Documentation cannot close it.** The row changes status only after a recorded run of its unchanged covering tests
  in the closure environment. The row becomes `covered` if they ran and passed, and a §G.1 defect if they failed.
- **It is not a general policy.** It applies to the ADR-0039 coverage matrix and M13's completion gates only. Any later
  milestone needs its own decision.

### 5. Amended wording in ADR-0039

Only these two passages are amended. ADR-0039's file is not edited. This ADR is the amending text.

| ADR-0039 | As accepted | As amended by this ADR |
|---|---|---|
| §B, status `gap` | "`gap` — with the defect id (§G.1) that explains why it is still open." | "`gap` — with the defect id (§G.1) that explains why it is still open, **or, for an owner-accepted environment-unavailable gap, the complete disposition record of ADR-0040 §3.**" |
| §L, M13.1 `COMPLETED`, second condition | "every deterministic gap either closed, or `gap` with a defect id;" | "every deterministic gap either closed, or `gap` with a defect id, **or `gap` with a complete owner-accepted environment-unavailable disposition (ADR-0040 §2 and §3);**" |

### 6. Everything else in ADR-0039 is unchanged

In particular:

- Automated and manual evidence stay separate evidence classes (I-2, I-4, §E.6).
- Execution being unavailable is not a pass (I-3).
- A manual scenario is never an automated pass (I-4).
- Defects are recorded, never hidden, masked or silently fixed. Product defects are not fixed within M13 (I-13, §G).
- M13 changes no production behaviour to make a test, eval or measurement pass (I-1).
- §G.1's defect record, its two classes and its `blocks_m13_completion` rule are unchanged.
- §E, §F, §H, the M13.2 completion conditions, and the invariants I-1 to I-13 are unchanged.

### 7. First application — S2-14

The disposition is applied to S2-14, the case that raised it, using only facts already recorded:

| Field | S2-14 |
|---|---|
| Matrix row id | `S2-14`, cross-tier equivalence (same fixture at Tier 1 and Tier 3) |
| Status | `gap` |
| Evidence | `execution_unavailable` |
| Label | `OPEN GAP — ENVIRONMENT UNAVAILABLE` |
| Reason execution is unavailable | The system interpreter, Python 3.13.1, cannot import openpyxl, so all eight Tier-1 equivalence tests are skipped ("openpyxl absent; Tier 1 cannot be compared here"). `CLAUDE.md` §4 and ADR-0008 prohibit installing openpyxl there. The consented managed runtime is Tier 2 and does not make these Tier-1 tests execute |
| Owner decision | U-1, option (c): accept S2-14 as an open gap |
| Decision date | 2026-09-18 |
| Closure environment required | An owner-approved execution environment whose test interpreter can import openpyxl, so that Tier 1 is available, provided without installing openpyxl into the system interpreter against `CLAUDE.md` §4 and ADR-0008. The eight unchanged tests would then have to run and be recorded |
| Not covered | Not covered, and not counted as covered. No cross-tier equivalence is claimed. The Tier-3-versus-CSV test that runs is not evidence of Tier-1 equivalence |
| Not a product defect | Not a product defect. No evidence shows the product failing the requirement |
| Not a test-infrastructure defect | Not a test-infrastructure defect. The tests are pre-M13 and correct to skip |

All five §2 conditions hold for S2-14.

## Reason

The contract's purpose is that coverage is *known*, not that it is complete. ADR-0039 §L's "does not mean" list
already says completion does not mean the product is defect-free. A gap that is disclosed, reasoned, dated,
owner-accepted and still counted as a gap is known coverage. The rule that stopped M13.1 existed to stop undisclosed
or unexplained gaps. It was never meant to force a false defect record.

Each safeguard in §2 and §4 closes a specific route by which the new disposition could hide something:

- a real failure is excluded by §2.3;
- a broken M13 test is excluded by §2.4;
- a documentation upgrade is excluded by §4.

The label and the field list keep the gap visible wherever the row is read.

## Consequences

**Positive**

- S2-14 can be recorded truthfully, and M13.1's gate can be evaluated without a false defect record.
- The three categories stay distinguishable in the matrix, the register and the plan.

**Negative**

- A requirement stays unevidenced at M13's completion. Cross-tier equivalence at Tier 1 is not demonstrated in this
  environment.
- The narrow exception adds one more status explanation for reviewers to read.

**Follow-up required**

1. Reconcile the M13.1 documentation to this amendment:
   - `coverage-matrix.md` (the S2-14 disposition record);
   - the testing index and the defect register's note;
   - `project_plan.md`;
   - `architecture.md` §19;
   - the ADR indexes;
   - a new development record.

   No past record is edited.
2. Closing S2-14 needs a recorded run in the closure environment. That is an owner decision, outside M13.1.

## Revisit when

- A run of the covering tests in an owner-approved closure environment is recorded.
- A second row appears to need this disposition. §2 then has to be applied to it on its own facts.
- A milestone after M13 needs a comparable rule. It needs its own decision, because this ADR does not extend beyond
  M13.
