# Testing

Test plan, the coverage matrix, and recorded results. Milestone 13 (`COMPLETED`, 2026-09-26) worked under the contract in
[ADR-0039](../decisions/ADR-0039-m13-test-hardening-and-evals-contract.md). `claude plugin eval` was early-access gated
when ADR-0007 was written. The 64-case suite has since been executed under that contract, and R-01 is closed; see
`project_plan.md`, *Known issues*.

> **Lineage.** The documents here name tests, eval cases and identifiers in their current BusinessOps form (`bops`,
> `businessops`). Results and observations dated before 2026-09-30 were recorded under the BusinessIQ identifiers
> (`biq`, `businessiq`); the SHA-256 pinned result fixtures in `tests/fixtures/eval_results/` keep those original
> names byte for byte, and the tests translate a recorded routing case id to its current one.

| Document | Holds |
|---|---|
| [coverage-matrix.md](coverage-matrix.md) | The closed S1–S7 coverage matrix: 99 rows, each with its covering tests, status and evidence class (ADR-0039 §B). ADR-0007's uncommitted 24-scenario list is recorded as unavailable, not reconstructed |
| [defects.md](defects.md) | The M13 defect register (ADR-0039 §G.1, status vocabulary amended by ADR-0043). Recorded defects, **not** fixed within M13. A product defect fixed and verified afterwards by its own milestone is `fixed_product` (M13-DEF-04) |
| [eval-suite.md](eval-suite.md) | The M13.2 behavioural eval suite: dual-layer case schema `bops-eval-case/2` (ADR-0044), grader vocabulary, the 64-case inventory, the ADR-0041 input fixtures and the execution procedure. Authored and statically validated; **not executed** |
| [manual-observation-pack.md](manual-observation-pack.md) | The owner's execution pack for the twelve S3 `manual_observation` scenarios: checklist, evidence rules, record template and one packet per row. It also records pre-execution condition WD-1 (engine path), product defect **M13-DEF-04**, which was **remediated 2026-09-20** under ADR-0042. S3-01 to S3-11 are no longer blocked by it. **Preparation only; zero observations performed** |
| [measurements.md](measurements.md) | M13-MEAS-D1 (large dataset), D2 (description discriminability, R-05) and D3 (forecast selection stability, R-10), plus the regression-suite wall-clock history, which is an observation and not a §D measurement. Recorded, never a threshold |
| [evidence/](evidence/) | Captured command output preserved as evidence, one dated file per check (BusinessOps M3.1: distribution validation, MCP verification, the installed-package reference-path test; M4A: package validation and MCP verification; M4A.1: package validation; M4: distribution package validation, single-repository package validation, R18 installation-path validation). Absolute paths are redacted |

`tests/unit/test_m13_coverage_matrix.py` validates the matrix and the defect register on every run.
`tests/unit/test_m13_eval_cases.py` validates the eval cases, the committed eval input fixtures
(`tests/fixtures/eval_inputs/`, ADR-0041) and the execution procedure. `tests/integration/test_m13_eval_input_preconditions.py`
checks that each fixture establishes its precondition through the unchanged pipeline.

Row S2-14 (cross-tier equivalence) is an **OPEN GAP — ENVIRONMENT UNAVAILABLE**. The owner accepted it (U-1 (c),
2026-09-18) because the Tier-1 tests need openpyxl in the system interpreter, which must not be installed there. It is
an owner-accepted environment-unavailable gap under
[ADR-0040](../decisions/ADR-0040-m13-owner-accepted-environment-gap.md), which amends ADR-0039 §B and §L to admit it.
It is not covered and not a defect.

**Evidence classes** (ADR-0039 §E.6): `automated_pass`, `automated_fail`, `not_executed`, `execution_unavailable`,
and, separately, `manual_observation`. A manual observation, or execution that was unavailable or unauthorised, is
never reported as a pass. M13.2 has authored the suite (64 cases, 2026-09-19), and **none has been executed**,
because no execution is authorised: ADR-0039 §E.1 outcome **(c)**, recorded 2026-09-19. Every case and every
behavioural row is `not_executed`. G-2 is resolved by the manual-observation procedure in
[eval-suite.md](eval-suite.md), which is owner-performed, one fresh session per S3 row, with records in
`docs/testing/manual/`. **No manual scenario has been performed yet.** G-3 (platform mechanics) stays open until
execution time.

**Opt-in suites** (skipped unless their environment variable is set):

- `BOPS_LARGE_DATASET=1` — `integration.test_m13_large_dataset` (D1);
- `BOPS_AGENT_BOUNDARY_RUNTIME=1` — the M11 verifier runtime boundary;
- `BUSINESSOPS_LIVE_SMOKE=1` — the M9-B live scout smoke.
