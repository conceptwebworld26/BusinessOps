# 2026-09-08 — Milestone 4: Data Quality

**Milestone:** 4 — Data Quality (full)
**Status on completion:** `REVIEW` — awaiting Milestone 4 review
**Supersedes:** None. Follows
[2026-09-08-data-layer.md](2026-09-08-data-layer.md).

## 1. Prompt / task performed

Milestone 3 approved. Complete the production data-quality layer on top of the M3 canonical
dataset: all thirteen approved check families with a uniform contract, a validated
`quality_report.schema.json`, the INFO/WARNING/CRITICAL severity model, the quality gate,
configurable thresholds with provenance, privacy-safe reporting, processing-mode awareness,
one deliberately broken fixture per family, and adversarial tests — without regressing the
M2 vertical slice or M3 normalization. No Milestone 5 work.

## 2. Where the thirteen families came from

`architecture.md` says the quality skill runs "13 check families" but does not enumerate
them. The enumeration is the approved product specification's validation list, and it is
exactly thirteen items. That is the taxonomy implemented:

| # | Identifier | # | Identifier |
|---|---|---|---|
| 1 | `missing_values` | 8 | `inconsistent_customers` |
| 2 | `duplicate_records` | 9 | `inconsistent_products` |
| 3 | `invalid_dates` | 10 | `currency_consistency` |
| 4 | `invalid_numbers` | 11 | `outliers` |
| 5 | `negative_values` | 12 | `broken_formulas` |
| 6 | `missing_periods` | 13 | `incomplete_dataset` |
| 7 | `duplicate_transactions` | | |

**A discrepancy identified and resolved.** M2 and M3 had grouped checks into five *labels*
(`structure`, `missing`, `duplicates`, `validity`, `currency`) that did not map one-to-one
onto the approved thirteen. Those groupings covered roughly eight of the thirteen concerns
and left three genuinely unimplemented (`missing_periods`, `outliers`, `broken_formulas` as
a family). Following the approved architecture rather than the incidental implementation,
M4 restructured the five groupings into the thirteen named families, preserving every
existing behaviour. The legacy grouping label is retained on each finding as `family` for
report continuity; `check_id` is the authoritative machine-readable identifier.

## 3. The check contract

Every family declares a `CheckSpec` — identity and policy, separate from execution:

    check_id · title · purpose · detects · severity_policy · can_halt · thresholds

and returns a `CheckResult` carrying its findings, its completeness, and — if it could not
run — the reason. Each `Finding` carries: `check_id`, `code`, `severity`, `message`,
`fields`, `evidence`, `threshold` (with the configuration layer that supplied it),
`observed`, `remediation`, `halts` and `completeness`.

A family that cannot run (no product column, for instance) reports itself as `not_run` with
a reason rather than silently contributing nothing.

Registration is the extension point: adding a family is `register(spec, function)`, not
surgery on a dispatcher.

## 4. Severity model

Findings carry `INFO` / `WARNING` / `CRITICAL`; the report carries `PASS` / `WARNING` /
`CRITICAL`, the highest finding severity present (INFO-only being a `PASS`).

- **INFO** — real but immaterial. A single blank optional field; a few refunds.
- **WARNING** — analysis continues, and the finding travels with every downstream figure as
  a global ledger caveat. It is never dropped during summarisation.
- **CRITICAL** — continuing would mislead, so the pipeline halts and no KPIs are produced.

**Severity is not applied because a value looks unusual.** Six of the thirteen families can
never halt, and two — `outliers` and `negative_values` — are deliberately incapable of
CRITICAL, because an unusual business value is not a data defect.

## 5. Quality gate

Unchanged in shape, completed in substance: clean data passes; warning-level data passes
with warnings preserved on every claim; `CRITICAL` halts at `halted_at="quality_gate"` with
zero KPIs produced and a rendered output that says so rather than showing a scorecard. The
gate exposes structured findings and the full source provenance.

## 6. Thresholds

Ten configurable thresholds, all under `quality.*`, resolved through the standard precedence
chain. Every finding records the key, the effective value, the configuration layer that
supplied it, and — separately — the observed value:

```
max_missing_pct 5.0 · duplicate_tolerance 0 · max_duplicate_pct 5.0
max_invalid_pct 10.0 · negative_tolerance_pct 5.0 · max_period_gap_pct 20.0
min_periods 2 · outlier_ratio 1000.0 · outlier_min_sample 30 · halt_on CRITICAL
```

Defaults are deliberately conservative rather than finding-hungry. Tested both ways: relaxing
`max_missing_pct` to 99 turns a CRITICAL into an INFO and the run proceeds; tightening
`min_periods` to 24 creates a finding on data that otherwise passes.

## 7. Outliers are data integrity, not anomaly detection

`outliers` looks for values whose *magnitude* suggests a data-entry error — more than 1000×
the column median, the signature of a misplaced decimal point or a unit mismatch. It does
not look for months where revenue was unusually good, never reaches CRITICAL, and never uses
the word fraud. A test asserts that last point directly. Business anomaly intelligence is a
later milestone and a different thing.

## 8. Privacy

Quality reporting is a plausible privacy leak — findings naturally want to quote the values
that triggered them. Reports therefore consume the M3 field sensitivity classification: any
field classified above `derived_safe` contributes **no literal values**, only counts,
percentages, types and a redaction marker.

Verified: a dataset of email addresses and customer-name variants produces the finding, names
the *column*, and contains none of the addresses or customer names. A column of API keys
produces a report with no key in it. M3's conservative classification is read, never
weakened.

## 9. Processing mode

A sampled or streamed pass never claims to be exhaustive. `Context.completeness` derives
from `canonical.complete`; every finding carries it; the report carries it; a caveat is
added; and `incomplete_dataset` raises an explicit `partial_processing` finding naming how
many rows of how many were examined.

## 10. Quality report schema

`lib/schemas/quality_report.schema.json` — overall grade, halt state, completeness,
processing mode, rows and columns examined, source identity, per-family results (including
families that found nothing or could not run), and every finding with its evidence,
threshold, remediation and halt flag.

The schema defines `finding` once and `$ref`s it from two places. That required adding local
`$ref` support to the stdlib validator — **and the `unsupported_keywords` guard built in M1
caught the omission before it could silently stop enforcing anything**, which is precisely
what that guard exists for. Remote refs are rejected, since resolving one would mean a
network fetch during validation.

Reports are deterministic: findings are sorted by (severity, check id, code), and the same
input produces byte-identical JSON.

## 11. Files created

```
lib/python/biq/quality/contract.py
lib/python/biq/quality/families.py
lib/python/biq/quality/report.py
lib/schemas/quality_report.schema.json
tests/fixtures/build_quality_fixtures.py
tests/integration/test_quality_m4.py
tests/integration/test_quality_adversarial.py
docs/development/2026-09-08-data-quality.md   (this file)
```

## 12. Files modified

| File | Change |
|---|---|
| `quality/checks.py` | Rewritten as the stable facade; `run()` keeps its signature |
| `quality/__init__.py` | Export the contract, specs and report types |
| `jsonschema_mini.py` | Local `$ref` / `definitions` support |
| `config/businessiq.defaults.json` | Ten `quality.*` thresholds |
| `tests/unit/test_engine_m2.py` | Family assertion updated to the 13-family taxonomy |
| `tests/integration/test_data_layer.py` | One M3 finding code renamed by the restructure |
| `tests/integration/test_performance.py` | Quality baseline; printing moved to `atexit` |
| `project_plan.md`, `README.md`, docs indexes | Status |

**No ADR body modified. No architectural decision changed.**

## 13. Test results

**478 tests, 0 failures, 0 errors** (17 skipped on the system interpreter: Tier 1 and Tier 2
need openpyxl).

| Milestone | Tests |
|---|---|
| M1 baseline | 120 |
| M2 (cumulative) | 271 |
| M3 (cumulative) | 403 |
| **M4 (cumulative)** | **478** |
| M4 additions | 75 (48 quality + 27 adversarial) |

## 14. Bugs found and fixed

1. **`duplicate_transactions` escalated to CRITICAL** on repeated order ids. A four-line
   order legitimately shares one order number, so this would have halted analysis for
   ordinary businesses. The M2 regression tests caught it. The family is now incapable of
   halting; only whole-row duplicates escalate.
2. **Ambiguous values were attributed to the wrong family.** Date ambiguity surfaced as an
   "ambiguous numbers" finding, so a user looking for a date problem would not have found
   it. Ambiguity is now routed by shape, and the `invalid_dates` family reports date
   ambiguity even when the date role failed to map — which is exactly when the user most
   needs the explanation.
3. Two of my own test expectations were wrong and were corrected rather than the code:
   33% non-numeric revenue *is* CRITICAL, and the privacy test asserted a column name would
   appear in a report where no finding referenced that column.

## 15. Performance baseline

| Operation | Rows | Time | Rate |
|---|---|---|---|
| Quality, 13 families | 2,204 | 0.24s | ~9k rows/s |
| Quality, 13 families | 30,000 | 0.99s | ~30k rows/s |

Measurement, not benchmarking; thresholds in the tests are loose enough to catch only an
order-of-magnitude regression. The full pass costs roughly a second on 30k rows, which is
not a bottleneck worth optimising against today.

## 16. M2 vertical slice regression

Verified unchanged on both paths:

| | CSV | XLSX Tier 3 |
|---|---|---|
| Revenue | £3,467,850.16 | £3,467,850.16 |
| Gross margin | 34.9143% | 34.9143% |
| NRR | `not_applicable` | `not_applicable` |
| Findings | 11 | 11 |
| Margin materiality | material | material |
| Quality grade | PASS | WARNING (degraded reader — unchanged from M3) |
| Report validates | yes | yes |

## 17. Limitations and known risks

1. **`inconsistent_customers` / `inconsistent_products` detect only normalisation-level
   variants** — case, whitespace, punctuation. "Acme Ltd" versus "Acme Limited" is not
   detected. Fuzzy matching would guess, and guessing that two customers are one is exactly
   what the ambiguity protocol forbids.
2. **`outliers` uses a median-ratio rule**, not a distributional model. It is deliberately
   blunt: a high threshold catching decimal-point errors, not statistical anomalies.
3. **`missing_periods` assumes monthly granularity.** Weekly or daily businesses will see
   gaps that are not gaps. Configurable granularity is future work.
4. **Row-level evidence is not exposed** — findings report counts, percentages and column
   names, never row numbers with values. That is a deliberate privacy trade; locating a
   specific bad row is left to the user's own file.
5. **Sampled processing lowers confidence but does not re-check** — a partial pass is
   labelled, not completed.

## 18. Git commit reference

Branch `main`. **No commit made** — `CLAUDE.md` section 10 requires commits only on request.
Nothing pushed, no history rewritten.
