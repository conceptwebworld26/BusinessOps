# 2026-09-15 — M10.2-R.2: canonical unit semantics, implemented

**Milestone:** 10.2-R.2 — Implement canonical unit semantics (ADR-0025)
**Status on completion:** COMPLETED — ADR-0025 implemented as accepted, 3,011 tests green.
**Supersedes:** None. Implements the decision recorded in
`docs/development/2026-09-15-m10-2r1-cross-domain-unit-semantics.md`; ADR-0025 is unmodified.

## 1. Prompt / task performed

Convert ADR-0025 into production code, contracts, schemas and deterministic tests.
Implementation only: no live external research, no scout dispatch, no R-12 fix, no commit.
None of those were done.

## 2. Objective

`unit` meant a quantity type internally and an unvalidated, magnitude-qualified display
label externally. Close that split so a unit names a quantity type on both sides, with the
magnitude in the value and the currency in its own field.

## 3. Changes made

### The canonical vocabulary — `lib/python/biq/kpi/contract.py`

Homed where the vocabulary already lived and where every consumer already imports from, so
no parallel contract was created. Added `PERCENTAGE_POINTS` (previously a bare literal in
three modules), `QUANTITY_TYPES`, `MONETARY_QUANTITY_TYPES`, `is_quantity_type()` and
`is_monetary()`.

    QUANTITY_TYPES = ("currency", "percent", "ratio", "count", "days", "percentage_points")

Six tokens, every one of them already emitted by production before this milestone. Nothing
was invented from a test or a comment. `percent` and `percentage_points` stay **distinct**:
20% is a rate, 20 percentage points is a change in a rate, and the analytics layer has
always kept them apart.

### The normalisation boundary — `lib/python/biq/quantity.py` (new)

`canonical_amount()` decomposes a source's published notation into a value in base units, a
quantity type and a currency code. `parse_source_unit()` reads `"USD billion"`,
`"EUR million"`, `"USD"`, `"billion"`. `SCALES` is a closed table — thousand, million,
billion, trillion, unit — with a short, deliberately incomplete alias list.

Three choices worth stating:

* **`b` and `mm` are not aliases.** `b` reads as billion in one market and as a bare token
  in another; `mm` means million in US banking and nothing elsewhere. An absent alias
  refuses; a wrong alias misstates a figure by three orders of magnitude.
* **A bare `$` establishes no currency.** At least four currencies use that symbol, so
  `"billion"` alone yields `currency=None`, which leaves the dimension unstated and
  therefore rejecting. This is the live case: the Research and Markets record in the
  M10.2-R run wrote `$226.36 billion` and never named a currency.
* **Floats are refused outright.** `canonical_amount(3.4, ...)` raises rather than drifting.

An integral result is tidied to its integral form, so `Decimal("3.4") * 10**9` serialises as
`3400000000` rather than `3400000000.0` and two paths reaching one quantity by different
scales produce identical bytes. That is notation, not rounding; a non-integral amount is
untouched.

### Enforcement — `lib/python/biq/synthesis/contract.py`

`SynthesisItem.__init__` now routes `unit` through `_quantity_type_or_refuse()`. `None`
stays legitimate and means *not stated*; anything outside the vocabulary raises
`SynthesisError` naming the vocabulary and pointing at `canonical_amount()`.

**One thing to flag for review.** ADR-0025 point 6 words this as *"an out-of-vocabulary unit
is `None`, not a token to match"*. The implementation **raises** instead of coercing to
`None`. The decision is unchanged — an unrecognised token can never satisfy the dimension
either way — but the failure mode is stricter, and it was chosen because coercion would
surface three layers later as an unexplained `unknown` while raising puts the failure in the
caller that built the statement, which is the repository's existing idiom for every other
invalid field on this class. ADR-0025 was **not** edited to match; this note is the record.

### The construction seam — `lib/python/biq/synthesis/merge.py`

`sourced_statement()` gains `source_unit` / `source_scale`. Passing either canonicalises
`observed` before the statement exists. Passing `unit` *and* `source_unit` is refused, and a
currency stated by both the notation and the caller must agree or the call is refused.

`compatibility.compare()` is **untouched**. A test asserts it imports nothing from
`quantity`, mentions no scale table and still reports `converted: False` on every outcome.

### Internal producers

`analytics/domain.py`, `analytics/financial.py` and `materiality.py` now use the vocabulary
constants instead of string literals. `kpi/engine.py`'s `MONETARY_UNITS` is the contract's
`MONETARY_QUANTITY_TYPES` rather than a second tuple of its own.

### Schemas

`synthesis.schema.json` `item.unit`, `anomaly.schema.json` `observation.unit` and
`forecast.schema.json` `unit` moved from open `["string","null"]` to the closed vocabulary
plus `null`. `kpi_results.schema.json` was already a closed five-value enum and correctly
excludes `percentage_points`, which KPI results never emit; it was left alone.

`evidence_set.schema.json` conflict-position `unit` was **deliberately left open**. A
position quotes what a source published — `"USD bn"` is the right value there — and a
position is a description of a source, not a compatibility dimension.

## 4. Files created

| Path | Purpose |
|---|---|
| `lib/python/biq/quantity.py` | Source notation → canonical quantity; the scale table |
| `tests/unit/test_m10_2r2_unit_semantics.py` | 61 tests across the seven required groups |
| `docs/development/2026-09-15-m10-2r2-canonical-unit-semantics.md` | This record |

## 5. Files modified

**Production**

| Path | Purpose |
|---|---|
| `lib/python/biq/kpi/contract.py` | The one closed vocabulary + membership predicates |
| `lib/python/biq/kpi/engine.py` | `MONETARY_UNITS` reads the contract, not a second list |
| `lib/python/biq/synthesis/contract.py` | Vocabulary enforced at `SynthesisItem` construction |
| `lib/python/biq/synthesis/merge.py` | `source_unit` / `source_scale` canonicalisation seam |
| `lib/python/biq/analytics/domain.py` | Constant instead of a `percentage_points` literal |
| `lib/python/biq/analytics/financial.py` | Same |
| `lib/python/biq/materiality.py` | Same, plus `percent` and `currency` literals |
| `lib/python/biq/__init__.py` | Export `quantity` |
| `lib/schemas/synthesis.schema.json` | `item.unit` → closed vocabulary |
| `lib/schemas/anomaly.schema.json` | `observation.unit` → closed vocabulary |
| `lib/schemas/forecast.schema.json` | `unit` → closed vocabulary |

**Tests** — retargeted, none deleted, none weakened

| Path | Purpose |
|---|---|
| `tests/fixtures/build_synthesis_fixtures.py` | Sourced statement uses `source_unit="USD bn"`; conflict positions left verbatim |
| `tests/unit/test_m10_1_synthesis_policy.py` | One `sourced_statement` retargeted to `source_unit` |
| `tests/unit/test_m10_2r_live_compatibility.py` | `AGREED` unit → `currency`; values restated in base units |
| `tests/unit/test_m10_2r_retrieval_seam.py` | One `sourced_statement` retargeted to `source_unit` |
| `tests/integration/test_m10_1_cross_domain.py` | Conflict position value `310` → `310000000000` |

**Documentation**

| Path | Purpose |
|---|---|
| `architecture.md` | *Canonical quantities* paragraph in the synthesis layer; `quantity.py` in the layout |
| `project_plan.md` | M10.2-R.2 section |

## 6. Files deleted

None. No test was removed or disabled.

## 7. Features implemented

| Feature | Location | User-reachable yet? |
|---|---|---|
| Canonical quantity vocabulary | `kpi/contract.py` | Indirectly — every figure already carries one |
| Scale canonicalisation | `quantity.py` | Not yet — M10.3 consumers will call it |
| Unit enforcement at construction | `synthesis/contract.py` | Indirectly |
| `source_unit` seam | `synthesis/merge.py` | Not yet |

No command, skill or agent changed. No skill documents the synthesis construction API yet,
so none needed updating — verified by grep, not assumed.

## 8. Tests performed

```bash
python -m unittest tests.unit.test_m10_2r2_unit_semantics
python -m unittest tests.unit.test_m10_1_synthesis_policy
python -m unittest tests.unit.test_m10_2r_live_compatibility
python -m unittest tests.unit.test_m10_2r_retrieval_seam
python -m unittest tests.integration.test_m10_1_cross_domain
python tests/run_tests.py
claude plugin validate . --strict
```

## 9. Test results

```
python -m unittest tests.unit.test_m10_2r2_unit_semantics
Ran 61 tests in 0.737s
OK

python tests/run_tests.py
Ran 3011 tests in 334.333s
OK (skipped=19)
ran 3011 | failures 0 | errors 0 | skipped 19

claude plugin validate . --strict
✔ Validation passed   (exit 0)
```

3,011 = 2,950 (M10.2-R.1 baseline) + 61 new. Every existing test still runs; the five
retargeted files changed expectations, not counts, and each change is attributable to
ADR-0025 and commented as such at the line.

Two intermediate failures were found and fixed rather than suppressed:
`test_the_sourced_path_through_the_seam_works` carried `unit="GBP bn"`, and
`test_the_cross_domain_conflict_keeps_both_positions_unaveraged` asserted the external
position value as `310` where it is now `310000000000` — the same quantity in base units,
with both positions still unaveraged, which is what that test exists to prove.

## 10. Issues discovered

- **No divergence from ADR-0025 in the decision**, but one in the failure mode: refusal by
  exception rather than coercion to `None`. Recorded in § 3 above and in the final report
  rather than by editing the ADR.
- **`kpi_results.schema.json` excludes `percentage_points`** while the shared vocabulary
  includes it. Correct today — KPI results never emit that token — but the two lists can now
  drift. Not reconciled here; it would mean widening a schema that is currently accurate.
- **No persisted artifacts required migration.** Nothing writes a synthesis set to disk,
  `synthesis.load()` has no production caller, and neither `./.businessiq/` nor
  `./businessiq-output/` carries a unit field. No migration system was invented.

## 11. Decisions made

No new ADR. This milestone implements ADR-0025 and takes no decision of its own; the three
judgement calls inside it — where the vocabulary lives, which scale aliases are safe, and
refusal-by-exception — are implementation detail recorded here.

## 12. Architecture changes

`architecture.md` gained a *Canonical quantities* paragraph in the synthesis layer section
and `quantity.py` in the repository layout. The layer's inputs, outputs, kinds, domain
constraint, provenance rules and retrieval seam are unchanged.

## 13. Project-plan updates

New M10.2-R.2 section, `COMPLETED`. M10.2-R remains `PARTIALLY VERIFIED`; R-12 remains open.

## 14. Documentation updates

`architecture.md`, `project_plan.md`, this record. ADR-0025 unmodified. No skill, command,
agent or reference page required a change.

## 15. Remaining work

1. A like-for-like internal↔external fixture and a clean live verification that reaches the
   ALLOW branch across domains. **M10.2-R stays partially verified until then.**
2. R-12 — open, untouched, and still requiring either valid protocol on first delivery or an
   approved recovery protocol defined in its own milestone.
3. D-12 — `architecture.md` still does not describe the seven-dimension test itself.
4. M10.3 consumers can now be built against stable unit semantics.

## 16. Git commit reference

N/A — no commit was made. No branch created, nothing staged, nothing pushed.
