# ADR-0043 — Defect register status vocabulary for verified product fixes: `fixed_product`

**Date:** 2026-09-20
**Status:** Accepted — 2026-09-20, by the project owner, in the M13-DEF-04 governance reconciliation prompt.
**Deciders:** Project owner.
**Supersedes:** none. **Amends:** [ADR-0039](ADR-0039-m13-test-hardening-and-evals-contract.md) §G.1, in part: the
`status` field's closed vocabulary and its closing sentence (see *Amended wording*). ADR-0039's text and status line
are not edited, as for ADR-0040 and ADR-0041.
**Relates to:** ADR-0039 (I-1, I-13, §G, §L); [ADR-0042](ADR-0042-plugin-root-anchored-isolated-engine-entry.md)
(M13-DEF-04's remediation architecture); ADR-0040 and ADR-0041, which are unchanged.

## Context

ADR-0039 §G.1 defines the M13 defect record and a closed `status` vocabulary:

> `status` | `open`, `fixed_infrastructure` (infrastructure class only, with the before and after) or `withdrawn`
> (the expectation misread its cited source, with the correct quotation shown. Withdrawal is never a way to accept
> current product behaviour). A product defect stays `open` through M13

ADR-0039 §G.2 and I-13 add that a product defect is never fixed **within** M13. Its remediation belongs to "a future
milestone under its own prompt".

`tests/unit/test_m13_coverage_matrix.py` enforces this in two places:

- `DEFECT_CLOSED["status"]` is `("open", "fixed_infrastructure", "withdrawn")`;
- `test_a_product_defect_stays_open_through_m13` requires a product defect to be `open` or `withdrawn`.

M13-DEF-04 (product; the engine entry depended on the working directory) was found by M13.2 on 2026-09-19 and then
remediated by exactly such a future milestone, outside M13, on 2026-09-20. That milestone:

- implemented accepted ADR-0042;
- passed T-A to T-K, including the security tests and T-J;
- passed the full regression: 4,872 tests, 0 failures, 0 errors, 29 skipped;

as recorded in `docs/development/2026-09-20-m13-def-04-implementation.md`.

## Problem

The register cannot represent a product defect that a dedicated post-M13 milestone has fixed and verified:

- **`open`** now contradicts the implementation evidence, the project plan and the defect's own disposition;
- **`fixed_infrastructure`** would misclassify a product and runtime defect as a defect in M13's own test
  infrastructure;
- **`withdrawn`** means the expectation misread its source, which is untrue here, and ADR-0039 forbids using it to
  accept product behaviour.

## Decision

**Add exactly one status to ADR-0039 §G.1's closed vocabulary: `fixed_product`.**

The name follows the register's existing convention, which already has `fixed_infrastructure`. The product and
infrastructure distinction is kept explicit, so no generic `resolved` value is introduced.

### Semantics

`fixed_product` may be used **only** when all of the following hold:

1. `defect_class` is `product`;
2. the remediation was **implemented** in a milestone **outside M13**, under its own owner prompt (ADR-0039 I-13,
   §G.2);
3. the remediation follows an **accepted** decision or design where one governs it. For M13-DEF-04 that is ADR-0042;
4. the remediation was **verified**:
   - by deterministic tests that were actually run and passed;
   - by the full regression, with 0 failures and 0 errors;
   - and no known implementation defect remains;
5. the record states the basis in a `**Status basis (ADR-0043).**` paragraph, naming the accepted ADR and the dated
   development record that holds the verification evidence.

`fixed_product` does **not** mean any of the following, and none of them qualifies:

- designed;
- architecture accepted;
- deferred;
- owner-accepted;
- partially fixed;
- infrastructure-only.

### Existing statuses

Their meanings are unchanged:

- **`open`:** a recorded defect with no verified fix.
- **`fixed_infrastructure`:** infrastructure class only, fixed within M13, with the before and after.
- **`withdrawn`:** the expectation misread its cited source, with the correct quotation shown. It is never a way to
  accept product behaviour.

### Class and status pairing (enforced)

| `defect_class` | Allowed `status` |
|---|---|
| `product` | `open`, `withdrawn`, `fixed_product` |
| `infrastructure` | `open`, `withdrawn`, `fixed_infrastructure` |

### `blocks_m13_completion` is unchanged

The rule stays as it is: `yes` only for an `infrastructure` defect that is `open`. A `fixed_product` record is
therefore `no`, as every product record already is. M13's completion governance is not retroactively changed.

### Amended wording in ADR-0039

| ADR-0039 | As accepted | As amended by this ADR |
|---|---|---|
| §G.1, `status` row | "`open`, `fixed_infrastructure` (infrastructure class only, with the before and after) or `withdrawn` (…). A product defect stays `open` through M13" | "`open`, `fixed_infrastructure` (infrastructure class only, with the before and after), **`fixed_product` (product class only; fixed and verified by a dedicated milestone outside M13 under its own prompt, under ADR-0043's semantics)** or `withdrawn` (…). A product defect stays `open` through M13 **unless and until such a milestone fixes and verifies it**" |

Everything else in ADR-0039 is unchanged, as is everything in ADR-0040, ADR-0041 and ADR-0042.

## The M13 boundary is unchanged

This ADR does **not** alter:

- ADR-0039 **I-1**: no production change is made to satisfy M13;
- **I-13 and §G.2**: a product defect is never fixed within M13.

`fixed_product` records a fix made **after and outside** M13, by its own milestone. It gives no M13 step a way to fix
a product defect, or to mark one fixed.

## M13-DEF-04

M13-DEF-04 qualifies, on the recorded evidence:

- ADR-0042 was accepted on 2026-09-19;
- the implementation was completed on 2026-09-20: `lib/python/biq_run.py`, 10 commands and 16 skills;
- T-A to T-K passed, including T-F and T-G (security) and T-J (the external-working-directory prerequisite);
- the full regression passed: 4,872 tests, 0 failures, 0 errors, 29 skipped;
- no known implementation defect remains.

Its record keeps its discovery in M13 and states that the fix came after M13, under ADR-0042.

## M13.2

This ADR does **not** complete M13.2. Its manual observations remain a separate, owner-controlled step, and none has
been performed. G-2 is unchanged.

## Open items

These stay independent and **OPEN**:

- G-3, the eval sandbox;
- V-4, the minimum Claude CLI version;
- runtime verification on Unix-like systems.

## Consequences

**Positive**

- The register can state the truth about a product defect that has been verified as fixed.
- The product and infrastructure distinction survives.
- The M13 boundary is untouched.

**Negative**

- A fourth status value must be understood alongside the other three.
- The validator gains pairing and evidence checks, which future records must satisfy.

**Follow-up required**

- Index this ADR in `docs/decisions/README.md`, with an amendment note, and in `architecture.md` §19.
- Update the validator's vocabulary, pairing and evidence checks.
- Reconcile M13-DEF-04's `status`.

All three are done in the same change as this ADR.

## Revisit when

- A defect needs a state this vocabulary cannot express.
- M13's defect register is superseded by a general, post-M13 defect process.
