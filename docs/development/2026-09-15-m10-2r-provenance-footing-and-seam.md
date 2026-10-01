# 2026-09-15 — M10.2-R: internal provenance footing, and the retrieval → synthesis seam

**Milestone:** 10.2-R — Cross-domain synthesis remediation + live retest
**Status on completion:** BLOCKED — remediation complete and deterministically verified;
the live same-domain retest could not run without a fresh-session attestation.
**Supersedes:** None. Remediates the defect reported by M10.2.

## 1. Prompt / task performed

Remediate the three findings from the M10.2 live verification: (1) the blocker — a caller
can construct a `SynthesisItem` declared as an internal `FACT` or `CALCULATION` while
attaching only external evidence provenance; (2) no clean public object-level seam from a
completed retrieval into the synthesis layer; (3) the compatibility ALLOW branch was never
exercised because no genuinely comparable live pair existed. Tightly scoped: no SWOT, no
strategy, no decision support, no executive reporting, no new commands, intents or
connectors. No commit, no push.

## 2. Objective

Close the provenance escalation in production code, give retrieval a supported way to hand
its `EvidenceSet` to synthesis, and re-run every M10.2 negative check against the recovered
live evidence to confirm the fix holds on real data rather than only on fixtures.

## 3. Changes made

**The defect.** M10.1's guarantee that *"external source wording never becomes an internal
fact — there is no kind for it to become"* was enforced by checking the statement kind
against a domain **derived from the origin the caller declared**. A caller naming
`ORIGIN_FINANCIAL` while citing one `P_EVIDENCE` reference passed every check. The
resulting item serialised as `kind: FACT`, `domain: internal`, `trust: internal`,
`evidence_class: 1` — indistinguishable downstream from a figure the engine computed from
the user's own spreadsheet — while its entire chain was one tier-C commercial research
house. Support (`partially_supported`) and confidence (`LOW`) did fire, so the item was
visibly weak; but weak and mislabelled-about-origin are different failures, and only the
second defeats the property the layer exists to hold.

**The fix** reads the chain instead of the label. `SynthesisSet.add()` now calls
`_require_internal_footing()` after the existing unresolved-reference check: an internal
`FACT` or `CALCULATION` must carry at least one reference that *resolves against this set's
registries* to an internal source. `domain`, `origin`, `trust`, `evidence_class`,
caller-supplied confidence and the tier on the cited object are all deliberately not
consulted — every one is caller- or payload-influenced. The check lives on the set rather
than the item because resolution needs the registries, which an item does not have.

Three shapes are now refused that were accepted before: non-material internal `FACT` on
external-only provenance, the material variant, and internal `CALCULATION` on external-only
provenance. `P_CLAIM` counts as external footing, and `P_UNAVAILABLE` as no footing at all.
Mixed provenance with at least one internal reference is accepted — that is the stated rule,
not a new permission.

**The schema** gained an `anyOf` on `definitions.item` expressing the same constraint for
records that never met the object model. This needed `contains` in `jsonschema_mini`;
`items` would have demanded that *every* reference be internal, which is a different and
wrong rule. The runtime stays authoritative — a schema validates output, and the point is
to refuse the object at construction.

**The seam.** `register_external()` accepts only an `EvidenceSet` object (correctly — a
dict would carry `source_tier` as data), but `close_retrieval()` returns `as_dict()` and
`EvidenceSet` has no `from_dict`. Both decisions are right and together left no public
path, so the M10.2 harness drove `ScoutRetriever` by hand — a second assembly of the same
pipeline. `close_retrieval_object()` now returns the set under `evidence_set`; both public
closers delegate to one private `_close()`. `close_retrieval()`'s contract is unchanged, and
the object result deliberately carries no `evidence` key so no caller reaches for one that
is sometimes a record and sometimes a live object.

**Verification** re-ran the four M10.2 provenance attacks against the *recovered* live
EvidenceSet from the earlier retrieval — replayed through the production parser from the
stored raw reply, with `as_of` pinned to the true retrieval date. No new retrieval, no new
scout dispatch, no network. The M10.2 synthesis rebuilt through the new seam is
byte-identical to the original 67,878-byte serialisation, which is the evidence that the
fix changed nothing for legitimate content.

## 4. Files created

- `docs/decisions/ADR-0023-internal-statements-need-internal-footing.md`
- `docs/decisions/ADR-0024-retrieval-to-synthesis-object-seam.md`
- `tests/unit/test_m10_2r_provenance_footing.py`
- `tests/unit/test_m10_2r_retrieval_seam.py`
- `docs/development/2026-09-15-m10-2r-provenance-footing-and-seam.md` (this record)

## 5. Files modified

- `lib/python/biq/synthesis/contract.py` — `INTERNAL_PROVENANCE`, `INTERNALLY_FOOTED_KINDS`
- `lib/python/biq/synthesis/synthesis_set.py` — `_require_internal_footing()`, called from `add()`
- `lib/python/biq/synthesis/__init__.py` — exports for the two new constants
- `lib/python/biq/research/handoff.py` — `close_retrieval_object()`, shared `_close()`
- `lib/python/biq/research/__init__.py` — export for `close_retrieval_object`
- `lib/python/biq/jsonschema_mini.py` — `contains` keyword
- `lib/schemas/synthesis.schema.json` — internal-footing `anyOf` on `definitions.item`
- `architecture.md` — synthesis-layer internal footing; the retrieval seam; ADR index
- `project_plan.md` — M10.2 recorded as `COMPLETED (FAILED)`; M10.2-R added

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | User-reachable yet? |
|---|---|---|
| Internal provenance footing invariant | `synthesis/synthesis_set.py` | Indirectly — governs every synthesis build |
| `INTERNALLY_FOOTED_KINDS` / `INTERNAL_PROVENANCE` | `synthesis/contract.py` | Exported API |
| Schema-level mirror of the invariant | `lib/schemas/synthesis.schema.json` | On validation |
| `contains` keyword | `jsonschema_mini.py` | Available to every schema |
| `close_retrieval_object()` | `research/handoff.py` | Exported API; no command uses it yet |

## 8. Tests performed

```bash
python -m unittest tests.unit.test_m10_2r_provenance_footing -v
python -m unittest tests.unit.test_m10_2r_retrieval_seam
python tests/run_tests.py
claude plugin validate . --strict
```

Plus a scratchpad harness re-running the four M10.2 provenance attacks, the five
seven-dimension comparisons, and the serialisation checks against the recovered live
EvidenceSet. That harness lives outside the repository.

## 9. Test results

```
test_m10_2r_provenance_footing:  Ran 31 tests — OK
test_m10_2r_retrieval_seam:      Ran 24 tests — OK

Full regression:
Ran 2925 tests in 204.194s
OK (skipped=19)
ran 2925 | failures 0 | errors 0 | skipped 19

claude plugin validate . --strict
✔ Validation passed   (exit 0)
```

Baseline before this task was 2,870 / 0 / 0 / 19; the 55 new tests account for the whole
difference and no existing test changed.

Post-fix attacks on the recovered live evidence — all four `REJECTED`: unknown provenance
id; forged tier A on a locally-C source; `verified: true` on a candidate claim; and all
four escalation variants (external-origin `FACT`, non-material internal `FACT`, material
internal `FACT`, internal `CALCULATION`). Reserved `RECOMMENDATION` and caller-supplied
derived fields also refused.

## 10. Issues discovered

- **The live same-domain compatibility experiment did not run.** It requires external
  retrieval, and the prompt gates the live portion on a fresh-session attestation that was
  not supplied. The compatibility ALLOW branch therefore remains unexercised on live data,
  exactly as it was after M10.2. Recorded as `BLOCKED` in `project_plan.md`.
- **Evidence ids are not stable across days.** `normalise_records` sets
  `retrieved_at = as_of or date.today()`, and the id is content-addressed over it, so
  replaying a stored reply on a later date silently re-dates the evidence and changes every
  id. Recovering the M10.2 set required pinning `as_of` to the true retrieval date. Worth
  considering whether a stored reply should carry its retrieval date alongside it; not
  changed here, as it is outside this milestone's scope.
- Nine of fifteen confidence reason codes remain unexercised by live data — the live
  sources were dated, current, tier C and non-participant, and the dataset graded PASS.

## 11. Decisions made

- **ADR-0023** — an internal statement is defined by its provenance, not by its declared
  origin. Amends ADR-0022, whose domain constraint was necessary but not sufficient.
- **ADR-0024** — one retrieval assembly, two closers; the `EvidenceSet` reaches synthesis
  as an object.

## 12. Architecture changes

`architecture.md` § *The synthesis layer* gained an **Internal footing** paragraph under the
domain-constraint table and a **retrieval seam** paragraph under Inputs. ADR index extended
with 0023 and 0024.

## 13. Project-plan updates

- M10.2 — added as `COMPLETED (FAILED)` with its findings recorded.
- M10.2-R — added as `IN PROGRESS`; every remediation task `COMPLETED`, the live
  same-domain experiment `BLOCKED`.
- The former "M10.2 onward" heading is now "M10.3 onward".

## 14. Documentation updates

`architecture.md`, `project_plan.md`, ADR-0023, ADR-0024, this record.

## 15. Remaining work

1. Run the same-domain live compatibility experiment once a fresh-session attestation is
   given, to exercise the ALLOW branch on real evidence.
2. Re-run the four provenance attacks in that live session for completeness.
3. On both passing, flip M10.2-R to `COMPLETED` and M10.1 to verified-live.

## 16. Git commit reference

N/A — no commit was made. No branch created, nothing staged, nothing pushed.
