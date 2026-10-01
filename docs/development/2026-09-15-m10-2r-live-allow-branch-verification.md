# 2026-09-15 — M10.2-R live: the compatibility ALLOW branch, on real evidence

**Milestone:** 10.2-R — Provenance footing and the retrieval seam
**Status on completion:** COMPLETED — the live same-domain experiment ran, the ALLOW
branch fired, and every provenance attack was refused against live evidence.
**Supersedes:** None. Completes the work left `BLOCKED` by
`docs/development/2026-09-15-m10-2r-provenance-footing-and-seam.md`, which stands intact.

## 1. Prompt / task performed

The owner supplied the fresh-session attestation M10.2-R required, which unblocked the
three remaining items from that record's § 15: run the same-domain live compatibility
experiment to exercise the ALLOW branch on real evidence; re-run the four provenance
attacks in the live session; and on both passing, flip M10.2-R to `COMPLETED` and M10.1 to
verified-live. No new capability, no new command, skill, intent or connector. No commit.

## 2. Objective

M10.1 built a seven-dimension compatibility test whose ALLOW branch had only ever been
exercised by fixtures. M10.2 tried and failed to reach it on live data — every live pair
failed on *unknown*, because the sources stated no geography and no methodology. The
question this task had to answer is narrow and empirical: **does the ALLOW branch fire on
real retrieved evidence when the evidence genuinely warrants it, and does everything that
must refuse still refuse?**

## 3. Changes made

### The experiment

Four bounded Tier-0 retrievals, each through the gate, each one dispatch, each closed
through the `close_retrieval_object()` seam ADR-0024 added — which is the first production
use of that seam on live data, rather than the hand-driven `ScoutRetriever` assembly M10.2
had to resort to.

| # | Operation | Query as transmitted | Outcome |
|---|---|---|---|
| 1 | `m10-2r-live-compat-01` | `semiconductors 2024 market size` | 2 records, both tier C, both `dated` |
| 2 | `m10-2r-live-compat-02` | `retail e-commerce United States 2024 US retail e-commerce sales market size` | 2 records, both tier C, both `current` |
| 3 | `m10-2r-live-compat-03` | `United States full year 2024 Census Bureau quarterly retail e-commerce sales fourth quarter 2024 market size` | **Transport failure** — no records |
| 4 | `m10-2r-live-compat-04` | same as 3, fresh operation | 2 records, tier **A** + tier C |

Every gate decision was `ALLOW` at tier 0, and every `transmitted_text` was built only from
public terms. Nothing internal left the machine at any point; there was no internal dataset
in this session to leak.

**Why four and not one.** The experiment's stated purpose is to reach a branch that only
fires when two sources genuinely measure the same quantity, so finding such a pair is the
experiment rather than a way of gaming it. Retrievals 1 and 2 were honest attempts that
found real, non-comparable pairs. Retrieval 3 failed at the transport layer and 4 is its
re-run. **No dimension was ever inferred to force a match**; every dimension below is
taken from the source's own wording, and where a source stated nothing the dimension was
left `None` and the check failed on unknown, as designed.

### Outcome A — INCOMPATIBLE with unknowns (retrieval 1)

Two sources on 2024 worldwide semiconductor revenue: a press article citing SIA
(USD 627.6bn) and one citing preliminary Gartner data (USD 626bn). Four of seven
dimensions matched; `metric_definition` differed (*chip sales* vs *industry revenue*),
`scope` was unstated on both sides and `methodology` on one. Status `incompatible`.

This is the M10.2 shape, and worth recording for one reason: the scout's own prose called
the two figures "close and consistent (~$626-628B)" and invited treating them as
corroborating. Two figures 0.25% apart are exactly the case where a human or a model
combines them without thinking. The engine refused.

### Outcome B — INCOMPATIBLE with every dimension stated (retrieval 2)

US retail e-commerce, full-year 2024: one source reporting USD 1.19tn on the Census
Bureau's basis, one reporting USD 1.170tn on Digital Commerce 360's own retail base. All
seven dimensions stated, **zero unknown cells**, three mismatches — `metric_definition`,
`scope` and `methodology`.

This is a genuinely new outcome. Every M10.2 refusal was "the sources did not say"; this
is "the sources said, and they measured different things". The two are different findings
and the reported record keeps them apart. `compare_values` recorded one `INCOMPARABLE`
limitation and marked both statements `incomparable_values` — the first live exercise of
that reason code — and recorded **no** conflict, correctly, because a same-domain pair is
not an internal/external disagreement.

### Outcome C — the ALLOW branch (retrieval 4)

Two sources reporting **the same compilation**: the US Census Bureau's Quarterly Retail
E-Commerce Sales release for Q4 2024, not seasonally adjusted, and a press article
explicitly citing it. Both state USD 352.9bn and 17.9% of total retail on the NSA basis.

```
status      : compatible
matched     : metric_definition, period, geography, currency, unit, scope, methodology
mismatched  : []
unknown     : []
may_combine : True
converted   : False          (NEVER_CONVERTS = True)
```

`compare_values` on this path recorded **no limitation**, **no conflict**, added no
confidence reason to either statement, and produced **no combined figure** — no ratio, no
difference, no share, no midpoint. Comparability is established as a precondition and
nothing is computed in passing, which is exactly what the module's docstring promises.

Two further properties held on this live set: serialising the built set twice produced
**byte-identical** output (10,179 bytes), and the serialisation validated against
`lib/schemas/synthesis.schema.json` with no errors and a permanently empty
`recommendations` array.

The pair also separated two things that could have been conflated. The tier-A statistical
agency release graded `supported`; the tier-C press article citing the very same figure
graded `partially_supported`. **Compatibility is about the quantity, grading is about the
source, and the two are independent** — the statements are comparable *and* unequally
supported, simultaneously.

The Census record carried no publication date the scout could confirm from the PDF, and
returned without one rather than with an assumed one. That produced `undated` freshness and
the `undated_external_evidence` confidence reason — a second previously-unexercised code.

### The provenance attacks, re-run live

Run against **three** live evidence sets (retrievals 1, 2 and 4), not one. Every probe
refused, every time:

| Probe | Result |
|---|---|
| Unknown provenance id | `REJECTED` — cites material the set was never given |
| Forged tier A on a locally-tiered source | `REJECTED` — tier derived from source identity, never accepted |
| Candidate claim carrying `verified: true` | `REJECTED` — no verification path exists to have produced it |
| External origin declared as `FACT` | `REJECTED` at construction |
| Non-material internal `FACT` on external footing | `REJECTED` — ADR-0023 |
| Material internal `FACT` on external footing | `REJECTED` — materiality buys no exemption |
| Internal `CALCULATION` on external footing | `REJECTED` |
| Internal `FACT` footed on a candidate claim | `REJECTED` — `P_CLAIM` is external footing |
| Reserved `RECOMMENDATION` kind | `REJECTED` |
| Caller-supplied `trust` / `support` / `confidence` | `REJECTED` — conclusions are not inputs |

**The sharpest result is the tier-A variant.** Every previous footing test cites tier-C
commercial research, which leaves open the reading that ADR-0023 is really about source
quality. It is not. An official statistic carries the highest tier the model assigns and
still cannot found an internal `FACT` or `CALCULATION`, because footing is about *whose
data it is*, not how good it is. That distinction was not demonstrable before this session
because no tier-A live source had ever been retrieved.

### Regression tests carried from the live session

`tests/unit/test_m10_2r_live_compatibility.py`, 25 tests, following the pattern M10.2-R
established with `test_live_shaped_escalation_*`: all three live outcomes are pinned as
fixtures so the branch that fired cannot silently stop firing, plus the tier-A footing
probe. Fixtures only — no network, reserved hosts, and the existing `ons.gov.uk` tier-A
fixture convention already used by the M10.1 test modules.

## 4. Files created

- `tests/unit/test_m10_2r_live_compatibility.py`
- `docs/development/2026-09-15-m10-2r-live-allow-branch-verification.md` (this record)

## 5. Files modified

- `project_plan.md` — M10.2-R `IN PROGRESS` → `COMPLETED`; its `BLOCKED` row → `COMPLETED`
  plus four new evidence rows; M10.1 → `COMPLETED (VERIFIED LIVE)`; new known issue R-12;
  new documentation debt D-12.

## 6. Files deleted

None.

## 7. Features implemented

None. This task is verification. No production module, schema, command, skill, agent or
configuration file was touched, and the regression count before the new test module was
identical to the M10.2-R baseline, which is the evidence for that claim.

| Feature | Location | User-reachable yet? |
|---|---|---|
| Live-shaped compatibility regression tests | `tests/unit/test_m10_2r_live_compatibility.py` | No — test-only |

## 8. Tests performed

```bash
python tests/run_tests.py
python -m unittest tests.unit.test_m10_2r_live_compatibility
claude plugin validate . --strict
```

Plus the live harness in the session scratchpad, outside the repository: four
`open_retrieval` / dispatch / `close_retrieval_object` cycles, three compatibility
comparisons, the attack batteries against three live evidence sets, schema validation of
the ALLOW set and a byte-identical rebuild check.

## 9. Test results

```
python tests/run_tests.py                       (before the new module)
Ran 2925 tests in 315.881s
OK (skipped=19)
ran 2925 | failures 0 | errors 0 | skipped 19

python -m unittest tests.unit.test_m10_2r_live_compatibility
Ran 25 tests in 0.011s
OK

python tests/run_tests.py                       (with the new module)
Ran 2950 tests in 119.280s
OK (skipped=19)
ran 2950 | failures 0 | errors 0 | skipped 19

claude plugin validate . --strict
✔ Validation passed   (exit 0)
```

The first run was taken **before** the new test module was written and matches the
M10.2-R baseline of 2,925 exactly, which is how this record can claim no production code
changed. The second was run after it, and 2,950 is an observed total rather than
arithmetic: the 25 new tests account for the whole difference and no existing test
changed. Both runs were clean; the wall-clock difference between them is machine load,
not a behavioural change.

Live results, in the session:

```
retrieval 1  incompatible   4/7 matched, 1 mismatch, 2 unknown
retrieval 2  incompatible   4/7 matched, 3 mismatch, 0 unknown
retrieval 3  unavailable    retrieval_unavailable / MALFORMED_RECORD
retrieval 4  COMPATIBLE     7/7 matched, 0 mismatch, 0 unknown, may_combine True
             converted False; limitations 0; conflicts 0; no combined figure
             byte-identical rebuild (10,179 bytes); schema errors: none
attacks      refused 10 of 10 (set 1), 7 of 7 (set 2), 7 of 7 (set 4)
```

## 10. Issues discovered

- **R-12 — the scout's hand-back intermittently drops its record lines.** Two of four
  dispatches returned a final report describing the records and referencing the protocol
  in prose while carrying no record or terminator line. Both failed closed with nothing
  fabricated, so correctness never depended on catching it; the cost is a wasted
  retrieval, and at roughly half of dispatches that is expensive for a contract that
  permits one dispatch per retrieval. Recorded in `project_plan.md`. Recovery without
  re-retrieving worked first time: asking the completed agent to restate its
  already-composed lines, explicitly forbidding any new search, produced a clean parse.
- **D-12 — `architecture.md` does not describe the seven-dimension compatibility test**,
  though it is a load-bearing invariant of the layer it documents. Deliberately not fixed
  here, because nothing architectural changed in this task and amending approved
  architecture is an owner decision. Flagged as sitting closer to a defect than the
  earlier D-01/D-02/D-06 omissions, which are taxonomies rather than invariants.
- **Reaching ALLOW on live data needed a deliberately chosen subject.** Two honest
  attempts at ordinary market-size questions both produced non-comparable pairs, and that
  is not a defect in either the check or the sources: independent research houses really
  do measure different things. The branch is reachable when two sources report one
  compilation, which in practice means an official statistic and the coverage of it.
  Whether a check this strict is the right default for a user-facing capability is a
  design question for M10.3's consumers, not something to settle here.
- Seven of fifteen confidence reason codes remain unexercised by live data.
  `incomparable_values` and `undated_external_evidence` were exercised for the first time
  in this session; `tier_c_only_support` again.

## 11. Decisions made

No ADR. This task made no significant or hard-to-reverse decision: it ran an experiment
already specified by M10.2-R, recorded what happened, and added regression tests. R-12 and
D-12 are open issues for the owner, not decisions taken.

## 12. Architecture changes

None. `architecture.md` is unchanged and correct as written; see D-12 for what it omits.

## 13. Project-plan updates

- M10.1 — `COMPLETED` → `COMPLETED (VERIFIED LIVE)`, with the basis stated.
- M10.2-R — `IN PROGRESS` → `COMPLETED`.
- M10.2-R's `BLOCKED` row → `COMPLETED`; four further evidence rows added.
- R-12 added to Known issues; D-12 added to Documentation debt.

## 14. Documentation updates

`project_plan.md` and this record. No other document required a change.

## 15. Remaining work

1. Decide R-12: whether `agents/biq-research-scout.md` should require the record lines to
   be the **final** output of the turn rather than merely present in it.
2. Decide D-12: whether `architecture.md` § *The synthesis layer* gains a compatibility
   paragraph.
3. M10.3 — the four Layer-3 capabilities, which read this now-live-verified representation.

## 16. Git commit reference

N/A — no commit was made. No branch created, nothing staged, nothing pushed.
