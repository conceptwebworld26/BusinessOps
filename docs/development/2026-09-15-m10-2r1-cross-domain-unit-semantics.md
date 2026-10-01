# 2026-09-15 — M10.2-R.1: cross-domain unit semantics, decided not implemented

**Milestone:** 10.2-R.1 — Cross-domain unit semantics decision
**Status on completion:** COMPLETED (DECISION ONLY) — ADR-0025 accepted, nothing implemented.
**Supersedes:** None. Follows
`docs/development/2026-09-15-m10-2r-live-allow-branch-verification.md` and the M10.2-R final
live verification, both of which stand intact.

## 1. Prompt / task performed

A scoped decision milestone: determine the correct semantic treatment of monetary units
across the internal/external boundary before M10.3 begins. Explicitly forbidden — changing
production code, tests, schemas, the scout, compatibility rules; adding a conversion; running
live external research; running `/industry-research` or `/profitability-analysis`; committing
or pushing. None of those were done.

## 2. Objective

The M10.2-R final live verification observed that internal monetary findings carry
`unit: "currency"` while external market-size evidence carries `unit: "USD billion"`, and
concluded that strict textual equality may make monetary internal↔external comparison
structurally unreachable. This milestone had to decide whether that is a defect, what the
canonical representation should be, and whether reconciling the two would amount to a
prohibited conversion.

## 3. Changes made

Documentation only. No production module, test, schema, command, skill, agent or
configuration file was touched.

### What the trace established

`unit` means two different things depending on which side of the boundary wrote it:

* **Internal — a semantic quantity type.** `lib/python/biq/kpi/contract.py` defines
  `CURRENCY`, `PERCENT`, `RATIO`, `COUNT`, `DAYS`; `lib/python/biq/kpi/engine.py` reads them
  as types (`MONETARY_UNITS = ("currency",)` gates currency safety and currency attachment).
  Magnitude lives in the `Decimal`, the currency code in a separate field, formatting in
  `render.executive.money()`.
* **External — unvalidated caller text.** Nothing in `lib/python/biq/synthesis/` validates
  `unit`. A skill writes whatever the source wrote.
* **`compatibility.compare()`** tests by exact equality after `_normalise()` case-folds and
  collapses whitespace. `NEVER_CONVERTS = True`.
* **The internal vocabulary is not closed either.** `analytics.contract.Finding.unit` has no
  vocabulary constant, and `percentage_points` is a bare literal in `analytics/domain.py`,
  `analytics/financial.py` and `materiality.py` — a sixth token absent from the KPI list.
  Surveyed empirically across four commands on the demo dataset: `currency`, `percent`,
  `count`, `percentage_points`.
* **No FX mechanism exists.** `kpi/engine.py` refuses monetary metrics outright on mixed
  currencies; there is no rate table, no conversion function, nothing.

### The decision

**ADR-0025.** `unit` denotes a quantity type and nothing else, drawn from one closed
vocabulary shared by both domains. Scale is a property of the value, normalised into it at
statement construction — in the skill that reads the source, **never** inside
`compatibility.compare()`, which this ADR leaves entirely unchanged. Currency conversion
stays prohibited with no approval path. An out-of-vocabulary unit is `None`, not a token that
can match another unrecognised token.

### The two arguments that decided it

**Scale normalisation is not conversion.** `USD 3.4 billion` and `USD 3,400,000,000` are the
same quantity in different notation: decimal-exact, no external data, no rate, no reference
date, reversible. `GBP 3.4 billion` and `USD 3.4 billion` are different quantities, and
relating them needs a rate BusinessIQ does not hold, which varies with time, forces an
unmade judgement (spot, average or closing) and is lossy. Permitting the first while
prohibiting the second is a line, not a softening.

**A magnitude-qualified unit token is unsafe, not merely untidy.** If both sides carry
`unit: "USD billion"`, strict equality passes and nothing then checks that each side's value
is actually in billions. A statement holding `3400000000` under a label saying *billion*
would compare as compatible with one holding `282.8` — a comparison certified wrong by 10⁹.
Strict equality is only safe when the token carries no magnitude, which is an argument *from*
strictness rather than against it.

### What the decision does not fix

Unit was never the whole obstacle. In the live run, internal revenue against external market
size failed on `metric_definition`, `period`, `geography`, `currency`, `unit` and `scope`
together; fixing `unit` moves that pair from six failures to five. A company's revenue is not
a market's size and must never become comparable to one. The legitimate internal↔external
monetary comparison is like-for-like, and the M10.2-R conclusion was right about the
mechanism but aimed at the wrong target pairing.

## 4. Files created

- `docs/decisions/ADR-0025-unit-is-a-quantity-type.md`
- `docs/development/2026-09-15-m10-2r1-cross-domain-unit-semantics.md` (this record)

## 5. Files modified

- `docs/decisions/README.md` — ADR-0025 index row.
- `architecture.md` — ADR-0025 row in *Major architectural decisions*. No other change; the
  architecture itself did not change, because nothing was implemented.
- `docs/README.md` — ADR-0025 link.
- `project_plan.md` — new M10.2-R.1 section `COMPLETED (DECISION ONLY)`; R-12 extended with
  the recovery boundary.

## 6. Files deleted

None.

## 7. Features implemented

**None, deliberately.** This milestone decides; it does not build. No behaviour changed and
no user-reachable capability was added or altered.

## 8. Tests performed

```bash
python tests/run_tests.py
claude plugin validate . --strict
```

Run because documentation changed, to establish that it changed nothing else. No test was
added, removed or modified.

## 9. Test results

```
Ran 2950 tests in 130.281s
OK (skipped=19)
ran 2950 | failures 0 | errors 0 | skipped 19

claude plugin validate . --strict
✔ Validation passed   (exit 0)
```

2,950 is the M10.2-R baseline exactly, which is the evidence that no production or test file
was touched.

## 10. Issues discovered

- **The internal unit vocabulary is not centrally defined.** `kpi/contract.py` holds five
  constants for `KPIDefinition.unit`; `analytics.contract.Finding.unit` holds none, and
  `percentage_points` exists only as a repeated string literal. Any implementation of
  ADR-0025 has to reconcile this first. Recorded in the ADR's follow-up.
- **ADR index drift (pre-existing, not fixed here).** `docs/decisions/README.md` omits
  ADR-0017, 0018, 0023 and 0024; `architecture.md` omits 0017 and 0018; `docs/README.md`
  stops at 0016. ADR-0025 was added to all three, but the existing gaps were left alone —
  closing them is unrelated to this milestone and belongs to whoever owns that debt.

## 11. Decisions made

ADR-0025, accepted. It **refines** ADR-0022's `DIMENSIONS` contract by fixing the meaning of
one dimension; it does not supersede it, and ADR-0022 is unmodified.

## 12. Architecture changes

None. `architecture.md` gained one index row and nothing else. The compatibility test,
the seven dimensions and the no-conversion rule are all exactly as they were.

## 13. Project-plan updates

- New M10.2-R.1 section, `COMPLETED (DECISION ONLY)`, stating explicitly that M10.2-R is
  **not** closed by it.
- R-12 extended with the M10.2-R.1 boundary: the restatement recovery is not accepted
  behaviour, malformed scout output fails closed, and a future live verification needs valid
  protocol on first delivery or an approved recovery protocol defined in its own milestone.

## 14. Documentation updates

ADR-0025, this record, three ADR indexes, `project_plan.md`. No skill, command, agent or
reference page required a change, because no behaviour changed.

## 15. Remaining work

1. An implementation milestone for ADR-0025: home the unit vocabulary in one module, validate
   `unit` at `SynthesisItem` construction, revise the four research skills to normalise scale
   at statement construction, reconcile `percentage_points`.
2. A like-for-like internal↔external fixture, then a live verification that can actually
   reach the ALLOW branch across domains.
3. R-12 remains open and is now bounded rather than resolved.
4. D-12 remains open — `architecture.md` still does not describe the seven-dimension test.

## 16. Git commit reference

N/A — no commit was made. No branch created, nothing staged, nothing pushed.
