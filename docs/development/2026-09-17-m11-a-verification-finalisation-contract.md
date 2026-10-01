# 2026-09-17 — M11-A: Verification and finalisation contract

**Milestone:** 11-A — verification and finalisation contract review (decision only)
**Status on completion:** COMPLETED (DECISION ONLY)
**Supersedes:** None

## 1. Prompt / task performed

Make M11 precise enough to implement without reopening architecture: define the verifier's purpose,
scope, inputs, binding model, headline-figure verification, section/content/provenance checks, lifecycle,
`VerificationResult`, finding categories and blocking, finalisation and `report_id`, persistence, the
human-approval boundary, fail-closed rules, re-entry, the `biq-analysis-verifier` role and the model
boundary. Record one ADR if needed. No implementation, no ADR-0031/0032/0033 edit, no forecast
translator, no live research, no commit or push.

## 2. Objective

Decide what makes a report or package `final`, and how that is proven, consistently with ADR-0006,
ADR-0031, ADR-0032 and ADR-0033.

## 3. Changes made

1. **Read the repository as source of truth** at `4dc6562` (clean, equal to `origin/main`): `CLAUDE.md`,
   `architecture.md` (§7 contracts, §10 subagents, §19 decisions), `project_plan.md` (M10.3.3-A to M11),
   ADR-0006, ADR-0014, ADR-0031, ADR-0032, ADR-0033, the decision index, `reference/output-standards.md`,
   and the Strategy, Decision Support, Executive Report, synthesis-set and command-translation code.
2. **Established what M11 already was.** ADR-0006: an independent-verification subagent. `architecture.md`
   §10: recompute headline figures, challenge conclusions, "engine + dataset", before `/executive-report`
   and `/decision-support` finalise. ADR-0032 §13 / ADR-0033 §13: verification recorded beside an unedited
   draft moves it to `final`; verified is not a lifecycle value; a final report may not contain a draft
   package; the recording mechanism is M11's.
3. **Found five code facts the contract must handle** (ADR-0034 Context): binding is to live objects, so
   integrity checks run in-process; the set digest covers statement figures but **not** the registered
   `KPIResult` and finding objects the scorecard and anomaly blocks read; **no source file is
   fingerprinted**, and dataset registration keyed by id loses the command id when two commands share a
   dataset; results retain outputs but not the validated inputs needed to reproduce them; the report's
   own content has no digest of its own.
4. **Decided ADR-0034** (Option D of four): deterministic in-process verification plus blind
   recomputation in the verifier agent; finalisation as a new object holding the unedited draft.
5. Documentation (§14).

## 4. Files created

- `docs/decisions/ADR-0034-m11-verification-and-finalisation-contract.md`
- `docs/development/2026-09-17-m11-a-verification-finalisation-contract.md` (this record)

## 5. Files modified

- `architecture.md` — §7 M11 contract summary; §10 verifier row; §19 decision table
- `project_plan.md` — Milestone 11 `PLANNED` → `IN PROGRESS`; M11-A `COMPLETED (DECISION ONLY)`; M11
  implementation `PLANNED`
- `reference/output-standards.md` — presentation of verification results and final artifacts
- `docs/decisions/README.md`, `docs/README.md` — ADR-0034 listed

## 6. Files deleted

None.

## 7. Features implemented

None. Contract only.

## 8. Tests performed

```
python tests/run_tests.py
claude plugin validate . --strict
git diff --check
```

## 9. Test results

Run after the documentation changes; no code or test changed, so these are regression results only.

| Run | Result |
|---|---|
| `python tests/run_tests.py` | ran 4,408, failures 0, errors 0, skipped 19 (unchanged from `4dc6562`) |
| `claude plugin validate . --strict` | Validation passed |
| `git diff --check` | clean |

No verifier test exists or was written: M11 is not implemented.

## 10. Issues discovered

- **Registry values sit outside the set digest.** A registered `KPIResult` or finding changed in memory
  after a report was built is not detected by M10 binding. ADR-0034 closes it for finalisation with
  `synthesis.registry_agreement` and recomputation; drafts are unchanged.
- **No recomputation basis exists today.** No file hash anywhere; `register_dataset()` keys by dataset id,
  so the last command registered for an id overwrites the earlier one (seen in the M10.3.4 command-level
  test, where business-health and anomaly-detection share one id). ADR-0034 requires a per-registration
  basis with the source's SHA-256 as an additive seam.
- **`Bash` is a shell.** The verifier agent's "no web" is a declared grant, not a sandbox; the blind brief
  is the exposure control. Recorded as a negative consequence in ADR-0034.
- **Not fixed (pre-existing, unrelated):** the `project_plan.md` milestone summary table still reads
  "10.1 done" for M10 and `PLANNED` for M11, and the plan's "Last updated" line is 2026-09-13.

## 11. Decisions made

[ADR-0034](../decisions/ADR-0034-m11-verification-and-finalisation-contract.md). No accepted ADR edited.

## 12. Architecture changes

`architecture.md` records the decided (unbuilt) M11 contract in §7 and the verifier's concrete role and
tool grant in §10. No existing contract changed.

## 13. Project-plan updates

Milestone 11 `PLANNED` → `IN PROGRESS`; new *M11-A* `COMPLETED (DECISION ONLY)`; new *M11 — Verification
and finalisation implementation* `PLANNED`. Executive Report implementation stays `COMPLETED`;
`biq-data-profiler` stays `PLANNED`; the forecast translator stays a separate decision.

## 14. Documentation updates

As §5. `CLAUDE.md` unchanged (no governance change: verification is read-only and needs no approval under
the existing §9). `README.md` unchanged (nothing user-reachable changed).

## 15. Remaining work

The M11 implementation milestone as listed in ADR-0034 *Follow-up required*; `biq-data-profiler`.

## 16. Git commit reference

N/A — no commit made, nothing staged or pushed.
