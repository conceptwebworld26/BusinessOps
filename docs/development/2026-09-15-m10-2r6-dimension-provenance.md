# 2026-09-15 — M10.2-R.6: dimension provenance and source-context admissibility

**Milestone:** 10.2-R.6 — Implementation of ADR-0026
**Status on completion:** COMPLETED — the mechanism exists, is enforced where footings are
present, and is additive everywhere else. **No live research. No scout dispatch. No change
to `compatibility.compare()`. No change to ADR-0025. No commit.**
**Supersedes:** None. Follows `2026-09-15-m10-2r3-deterministic-allow-branch.md` and the
M10.2-R.4 live verification (verification-only, no record written) and the M10.2-R.5
decision (decision-only, no record written).

## 1. Prompt / task performed

Implement the architecture M10.2-R.5 selected: dimension-specific provenance, `EvidenceItem`
as the sole source-context carrier, same-document and same-operation binding, narrowly
admitted deterministic derivation, model inference prohibited for compatibility, and
`compatibility.compare()` unchanged.

## 2. Objective

M10.2-R.4 returned `unknown` for `geography`, `currency` and `methodology` and was right to.
But the run also showed the verdict rested on the operator's restraint: a caller writing
`currency="USD"` from background knowledge would have produced `compatible`, and nothing in
the serialised record would have shown it was a guess. The hole was never strictness — it
was that the architecture could not tell a stated dimension from an asserted one.

## 3. Changes made

### New

`lib/python/biq/synthesis/dimension_provenance.py` (415 lines). `DimensionProvenance` is
immutable, refuses source metadata as constructor input, and carries: dimension, value,
basis, evidence id, verbatim source excerpt, locator, applicability, derivation. `resolve()`
judges each footing against the evidence registry and returns both the seven-key view
`compare()` reads and a full audit trail of every footing, admitted or refused, with a
reason code.

Four bases; three admissible:

| Basis | Admissible | Binding required |
|---|---|---|
| `stated` | yes | evidence cited by the statement; excerpt present in its content |
| `context` | yes | same set, same operation, **same document**, excerpt present, applicability covers period **and** scope |
| `derived` | yes, `unit`/`currency` only | evidence cited; rule in the closed registry |
| `asserted` | **never** | — recorded and serialised, reads as unstated |

### Modified

- `synthesis/contract.py` — `SynthesisItem` gains `dimension_provenance`, a resolved view and
  a resolution trail; `dimensions` returns the resolved view once the item is in a set and
  the declared view before that; new `declared_dimensions` keeps the audit view; serialisation
  writes footings in **fixed seven-dimension order**; `from_dict()` rebuilds footings but
  deliberately does **not** restore the resolved view or any serialised source metadata.
- `synthesis/synthesis_set.py` — `_resolve_dimensions()` runs at `add()`, beside
  `_require_internal_footing()`, and records a conflict per contested dimension reusing
  `conflicts`' existing kind vocabulary; new `require_dimension_provenance` flag.
- `synthesis/merge.py` — `sourced_statement(dimension_provenance=…)`.
- `synthesis/__init__.py` — exports.
- `lib/schemas/synthesis.schema.json` — `dimension_provenance` (closed `basis` enum),
  `dimension_resolution`, `resolved_dimensions`.

### The design decision that mattered most

**Resolution is stored on the item as a derived field, so `compare()` needs no change.**
`compare()` reads `item.dimensions`; making that property return the already-resolved view
means the comparison engine never learns what provenance, evidence, a tier or a registry is.
A test asserts `compatibility.py` contains none of those tokens, and its md5 is unchanged at
`35a89e32f6fad71bc7c21abe9dbe4915`.

### One bug found and fixed during implementation

The first resolver checked each footing's value against the statement's declared value
*before* detecting disagreement between footings. That silenced every competing footing, so
the conflict branch §14 requires was unreachable. Reordered: bindings are judged first,
disagreement between admissible footings second, agreement with the statement last. Caught
by `FixtureE`, which failed on the first run.

## 4. Files created

| Path | Purpose |
|---|---|
| `lib/python/biq/synthesis/dimension_provenance.py` | The type and the resolution path |
| `tests/unit/test_m10_2r6_dimension_provenance.py` | 91 tests |
| `docs/decisions/ADR-0026-…md` | The decision |
| `docs/development/2026-09-15-m10-2r6-dimension-provenance.md` | This record |

## 5. Files modified

`synthesis/contract.py` · `synthesis/synthesis_set.py` · `synthesis/merge.py` ·
`synthesis/__init__.py` · `lib/schemas/synthesis.schema.json` · `architecture.md` ·
`project_plan.md` · `docs/decisions/README.md`.

**No existing test was modified, retargeted, disabled or deleted.**

## 6. Files deleted

None.

## 7. Features implemented

Dimension-level provenance and admissibility. No new analysis, no new figure, no new
recommendation, no new research capability.

## 8. Tests performed

```bash
python -m unittest tests.unit.test_m10_2r6_dimension_provenance
python tests/run_tests.py
claude plugin validate . --strict
```

## 9. Test results

```
python -m unittest tests.unit.test_m10_2r6_dimension_provenance
Ran 91 tests in 0.037s
OK

python tests/run_tests.py
Ran 3153 tests in 341.079s
OK (skipped=19)
ran 3153 | failures 0 | errors 0 | skipped 19

claude plugin validate . --strict
✔ Validation passed   (exit 0)
```

3,153 = 3,062 (M10.2-R.3 baseline) + 91 new. **No existing test changed**, which is the
evidence that the change is additive and that no prior behaviour moved.

## 10. Issues discovered

- **Same-document context collides with content-addressed evidence ids.** `evidence_id()` is
  derived from `(source, reference, retrieved_at)`, so two `BIQ-REC/1` records from one URL
  in one retrieval produce the **same** id and the registry keeps the last. Through the
  production retrieval path, therefore, same-document context is most naturally expressed as
  a `context` footing quoting a different excerpt of the **same** evidence item — which is
  supported and tested. Two genuinely distinct items sharing a reference are expressible only
  with explicit ids, as the fixtures do. Not a defect introduced here; recorded because it
  shapes how the mechanism will actually be used.
- **The residual gap is real and named.** A dimension with no footing is passed through
  unchanged. Until the research skills emit footings, the pre-R.6 behaviour stands for them.
  `require_dimension_provenance=True` closes it per set.
- **Free-text dimensions still fail on synonymy.** `"global"` and `"worldwide"` return
  `incompatible`, not a match. Refusing a synonym table is deliberate (ADR-0026); the cost is
  false incompatibility, which fails safe.

## 11. Decisions made

**ADR-0026**, recording the M10.2-R.5 decision. ADR-0025 is unmodified.

## 12. Architecture changes

`architecture.md` gains a *Dimension admissibility (ADR-0026)* subsection under the synthesis
layer, the ADR index row, and the module in the tree listing.

## 13. Project-plan updates

New `M10.2-R.5` (`COMPLETED (DECISION ONLY)`) and `M10.2-R.6` (`COMPLETED`) sections.
**M10.2-R remains `PARTIALLY VERIFIED`**; R-12 remains open.

## 14. Documentation updates

`architecture.md`, `project_plan.md`, `docs/decisions/README.md`, ADR-0026, this record.
Unrelated documentation debt — including the ADR index omissions for 0017, 0018, 0023 and
0024 — was deliberately **not** touched.

## 15. Remaining work

1. **Migrate the four research skills** to emit dimension footings, then consider making
   `require_dimension_provenance` the default.
2. **Retrieval does not yet ask for dimension-bearing text.** The scout brief was not changed
   and must not be without its own decision — it touches the agent contract.
3. **A live ALLOW remains undemonstrated.** This milestone is synthetic throughout.
4. **R-12** — open, untouched.
5. **D-12** — `architecture.md` still does not describe the seven-dimension test itself.

## 16. Git commit reference

N/A — no commit was made. No branch created, nothing staged, nothing pushed.
