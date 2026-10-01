# 2026-09-13 — M9-D.1: the `/company-analysis` command

**Milestone:** M9-D.1 — `/company-analysis`
**Status on completion:** `REVIEW` — deterministic work complete, fresh-session live smoke
test outstanding (section 15)
**Supersedes:** None

---

## 1. Prompt / task performed

Expose the existing Company Analysis capability as `/company-analysis`: a thin
command/orchestrator over the `biq-company-analysis` skill, with focused tests, updated
documentation, plugin validation, and one fresh-session live smoke test. Explicitly not to
implement the other three research commands, duplicate any analysis logic, change the scout
protocol, source-tier policy, disclosure policy or claim policy, or commit.

## 2. Objective

M9-C.16 live-tested the **skill**. There was no command. The whole of this milestone is the
UX layer that makes the capability reachable by name — and the discipline that it stay a UX
layer, since the obvious failure mode is a command that slowly reimplements the skill.

## 3. Changes made

### Phase 0 — inspection, which decided the design

Reading the repository first settled the one real question: **how a research command
registers.** BusinessIQ has two command surfaces, not one.

- `biq.commands.registry` declares the nine **analytics** commands. Each spec carries
  `required_roles` (dataset mapping roles), an analytical `domain`, a `kpi_focus`, an
  `engine` from `("analytics", "forecast", "anomaly")`, and `sections` that must exist in
  `sections.RENDERERS`. `commands.run()` ingests a file and drives that pipeline.
- `commands/*.md` is the **plugin** surface, auto-discovered (architecture.md §2).
  `/retrieval-slice` already exists there with **no** registry spec, because it runs no
  dataset pipeline.

A public-source research command reads no file. Every field of a `CommandSpec` would have to
be invented for it, `sections` would need a second renderer duplicating the skill's ten
sections in Python, and `commands.run()` would be driving a dataset pipeline for a command
with no dataset. So `/company-analysis` follows the existing precedent: **markdown
orchestrator, no registry spec.** This is applying the repository's established dual-surface
pattern, not a new one — which is why **no ADR was written**. Stop conditions 1–3 were
checked against this and none applies: the skill's interface needed no change at all.

### Phase 1 — the command

`commands/company-analysis.md`. Frontmatter: `description` and `argument-hint` only. Four
steps: resolve Business Context → resolve the company name → invoke the skill → present the
result. Twelve failure conditions. The input table mirrors the skill's contract exactly —
`company` required, the same four focus values, `--window` and public terms passed through
verbatim.

Three things it deliberately says about itself, each asserted by test:

- **"The command performs none of those steps itself."** It does not search, fetch, tier a
  source, build evidence, propose a claim, verify one, or write a finding.
- **"Nothing here may upgrade a result."** Candidate stays candidate, unsupported stays
  unsupported, tier C stays tier C, an absent figure stays absent. If the command's prose is
  more confident than the skill's, the command is wrong.
- **Fail closed** — every failure path produces *less* output, never invented output, and a
  failed retrieval is never filled in from the company name or from training knowledge.

**No production Python changed. The skill was not modified** — no compatibility adjustment
proved necessary, so none was made.

### Business Context, and the one security point worth stating

Context is optional here and has exactly one role: supplying **public** disambiguating terms
(industry, market) when the user gave none. Context fields carry privacy classifications, and
nothing above `public` may reach a query. The command says so, and the disclosure gate
enforces it independently at `open_retrieval` — the command's instruction is the courtesy,
the gate is the control.

## 4. Files created

| Path | What |
|---|---|
| `commands/company-analysis.md` | The command |
| `tests/unit/test_m9d1_company_analysis_command.py` | 50 focused tests |
| `docs/development/2026-09-13-m9d1-company-analysis-command.md` | This record |

## 5. Files modified

| Path | Change |
|---|---|
| `tests/unit/test_command_registry.py` | Retargeted 2 tests, added 2 (35 → 37) |
| `tests/unit/test_m9b_scout_contract.py` | Retargeted 1 test (62, unchanged count) |
| `commands/retrieval-slice.md` | One sentence: the four research commands are no longer all unbuilt |
| `architecture.md` | New §7 subsection, *The research command surface* |
| `docs/commands/README.md` | Command row, the no-registry-spec note, stale count 7 → 10 |
| `README.md` | M9-D section; removed research/forecasting from "not built yet" |
| `project_plan.md` | Header phase line; M9-D row split into D.1 `REVIEW` and D.2+ `PLANNED` |

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | User-reachable? |
|---|---|---|
| `/company-analysis` | `commands/company-analysis.md` | Yes, after a session restart — **not yet live-verified** |

## 8. Tests performed

```
python tests/run_tests.py unit.test_m9d1_company_analysis_command
python tests/run_tests.py unit.test_command_registry
python tests/run_tests.py unit.test_m9b_scout_contract
python tests/run_tests.py                     # full regression
claude plugin validate . --strict
```

Plus a **mutation check** on the section-order assertions: the command's section list was
temporarily reordered (`overview` before `executive summary`), both order tests failed as
they should, and the file was restored and re-verified. The assertions are not vacuous.

## 9. Test results

```
$ python tests/run_tests.py
Ran 2033 tests in 114.186s
OK (skipped=19)
ran 2033 | failures 0 | errors 0 | skipped 19

$ claude plugin validate . --strict
✔ Validation passed
```

Focused: `unit.test_m9d1_company_analysis_command` **50** OK.

All twenty M9 modules pass: `test_m9d1_company_analysis_command` 50 ·
`test_m9c17_first_party_registry` 45 · `test_m9c6_tier_boundary` 42 ·
`test_m9c15_production_protocol` 61 · `test_m9c9_shape_experiment` 22 ·
`test_m9c14_zero_record_and_full_path` 54 · `test_m9c1_bare_envelope_contract` 42 ·
`test_m9b_scout_contract` 62 · `test_m9c7_return_contract_boundary` 16 ·
`test_m9c3_company_analysis` 60 · `test_m9c8_handoff_provenance` 11 ·
`test_m9c4_conflict_transport` 53 · `test_m9_governance` 46 · `test_m9a_adversarial` 34 ·
`test_m9a_gate_forgery` 43 · `test_m9a_invariants` 57 · `test_m9a_research_core` 65 ·
`test_m9b_candidate_claims` 36 · `test_m9b_scout_security` 57 ·
`test_m9c2_advisory_guard_wording` 12.

Count: 1981 (M9-C.17) + 50 new + 2 added to the registry module = 2033.

### The three tests that had to move, and why none was weakened

| Test | Was | Now |
|---|---|---|
| `test_no_analytics_command_is_undeclared` | Undeclared markdown surfaces == `{retrieval-slice}` | Undeclared == harness ∪ research. Still fails on **any other** undeclared surface, which is the property worth having |
| `test_every_markdown_orchestrator_is_declared` | `EXPECTED + HARNESS` | `EXPECTED + HARNESS + RESEARCH` |
| `test_it_is_not_one_of_the_four_deferred_research_commands` | All four research commands absent | Renamed `..._is_not_one_of_the_research_commands`: asserts the **harness's own name** is not a research command, plus the three still deferred. No longer weakens as later M9-D milestones ship |

`RESEARCH_COMMANDS` was added as a **separate** constant rather than folding
`company-analysis` into `HARNESS_COMMANDS` — a shipped user-facing command must not hide
behind a constant meaning "integration scaffolding".

**Added to replace the lost coverage:** `test_the_unbuilt_research_commands_still_do_not_exist`
(the three siblings are absent from disk *and* from the registry) and
`test_a_research_command_is_not_a_runnable_analytics_command` (`spec_for` None,
`require` raises — so the command cannot quietly acquire a dataset pipeline).

No security assertion was touched. Nothing was deleted.

## 10. Issues discovered

1. **`docs/commands/README.md` said "seven thin orchestrators" while listing nine.** Stale
   since M8. Corrected to ten in passing, since it introduces the table this milestone edits.
2. **`README.md` listed forecasting and anomaly detection as "not built yet".** Stale since
   M8 — both shipped. Corrected as part of the same sentence this milestone had to change.
   Flagged rather than silently absorbed: the rest of the README still presents Milestone 7
   as "this release" and **remains stale**. A full README refresh is its own task and was
   deliberately not performed here.
3. **`architecture.md` says `commands/ 17 thin orchestrators`** against 11 actual files. That
   is the planned final inventory, not a current count, and was left alone.

## 11. Decisions made

**No ADR.** Registering a research command as a markdown orchestrator with no registry spec
applies the pattern `/retrieval-slice` already established; it is not a new architectural
decision. The prompt's instruction was explicit that an ADR should not be created merely for
a command, and nothing here met the bar in `docs/decisions/README.md`.

## 12. Architecture changes

`architecture.md` §7 gains *The research command surface*: the skill and the command are one
capability reached two ways; the command holds none of the pipeline; research commands carry
no `biq.commands.registry` entry, with the reason; the other three are not built.

## 13. Project-plan updates

- Header phase line: 9-D.1 now `REVIEW`, live smoke test named as outstanding.
- `/company-analysis` split from the four-command row into its own `REVIEW` row.
- `/market-analysis` · `/competitor-analysis` · `/industry-research` remain `PLANNED` (M9-D.2+).

## 14. Documentation updates

`architecture.md`, `docs/commands/README.md`, `README.md`, `project_plan.md`,
`commands/retrieval-slice.md`, and this record.

## 15. Remaining work

**The fresh-session live smoke test — the one completion criterion not met.**

The milestone requires one live `/company-analysis Microsoft --focus overview` in a
**genuinely fresh** Claude Code session, explicitly discounting any same-session run because
the session that created the command did not have it registered at start. That restart is an
owner action: a session cannot restart itself, so this could not be performed here, and no
same-session substitute was attempted or reported as one.

Everything the live test depends on is in place and verified deterministically: the command
exists with valid frontmatter, plugin validation passes, the skill is unmodified, and the
`BIQ-REC/1` / `BIQ-END/1` path passes all 20 M9 modules. What the live run still has to
establish is registration and wiring, which no offline test can:

1. a fresh session lists `/company-analysis`;
2. it accepts `Microsoft`, `focus: overview`;
3. it invokes `biq-company-analysis` rather than researching on its own;
4. the gate issues the brief; exactly **one** dispatch; no retry;
5. the raw reply reaches `parse_reply()` with **no manual repair, extraction or trimming**;
6. tiers are recomputed locally; no claim is marked verified; limitations and confidence survive;
7. no business file is read and no internal term reaches the query.

Record, when it runs: command input, discovery, dispatch count, evidence count, tiers seen,
candidate-claim count, verified-claim count (**must be 0**), confidence, limitations, and
whether any manual repair occurred (**must be NO**).

Two known properties worth expecting rather than being surprised by: Microsoft's own domain
now classifies **tier B** under the M9-C.17 registry, so support may read `supported` where
M9-C.16 saw `unsupported`; and the ADR-0018 open question — first-party sources are tiered as
*sources*, not as *source-claim pairs* — is unaffected by this milestone and still open.

## 16. Git commit reference

N/A — no commit, no push, as instructed. Branch `main`, all changes uncommitted.
