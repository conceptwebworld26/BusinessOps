# 2026-09-14 — M9-D.3: Competitor Analysis Skill + `/competitor-analysis` command

**Milestone:** 9-D.3 — External Research Commands
**Status on completion:** `REVIEW` — deterministic work complete; fresh-session live smoke test outstanding
**Supersedes:** None

## 1. Prompt / task performed

Implement `skills/biq-competitor-analysis/SKILL.md` and `commands/competitor-analysis.md`
following the thin-command architecture M9-D.1 and M9-D.2 established. Required input
`company`; optional `competitors`, `geography`, `focus`, window and public terms; five focus
values `landscape | comparison | positioning | developments | full`. Competitor
identification must be evidence-based and must never fabricate a competitor or promote an
unsupported candidate. No rankings, no scoring, no strategic recommendations. Do not change
the scout protocol, source-tier policy, disclosure-gate policy or candidate-claim
verification policy. Write focused skill and command tests, run full regression and plugin
validation, then perform one fresh-session live smoke test of
`/competitor-analysis Microsoft --focus landscape`. No commit, no push.

## 2. Objective

Add the third of four external research capabilities without adding a second research
pipeline, and do it in a way that makes the two failure modes specific to competitor
research structurally hard rather than merely discouraged:

1. **Fabricated or over-claimed competitor identity** — treating a company as a competitor
   because a source mentioned it, because a category overlaps, or because the shortlist
   looked short.
2. **Silent escalation into decision support** — a ranking, a score, or a "strongest
   competitor" verdict, each of which is a decision wearing an observation's clothes.

## 3. Changes made

**Phase 0 — inspection.** Read the two shipped research skills and commands, the research
core (`contract`, `query`, `gate`, `handoff`, `scout`, `sources`, `evidence_set`), the
command registry, the ambiguity protocol, ADR-0016 through ADR-0019, and the M9 test suite.
Established that the whole pipeline is reusable as-is and that the only gap is query
*wording* for two of the four competitor questions. Recorded a baseline full-suite run:
**2223 tests, 0 failures, 0 errors, 19 skipped.**

**Engine — two additive intents (ADR-0020).** `LANDSCAPE` and `COMPARISON` added to
`contract.INTENTS`, with `INTENT_TERMS` entries `"competitive landscape"` and
`"competitor comparison"`, both exported from `biq.research`. `positioning` and
`developments` deliberately **reuse** the existing `POSITIONING` and `TRENDS` intents rather
than minting competitor-specific twins — `POSITIONING`'s own comment already reads "how
entities compare publicly", and `biq-company-analysis` has mapped developments onto `TRENDS`
since M9-C.3. The inline `(PROFILE, POSITIONING)` tuple in `query.build()` was extracted to
a named `SUBJECT_LEADS` constant and the two new intents added to it, so a competitor query
reads `Contoso Logistics competitive landscape`. Existing query strings are unchanged
byte-for-byte, pinned by test for both M9-D.1 and M9-D.2.

No new claim kind was added: competitor research reuses `financials`, `market_sizing` and
`positioning`, which is the whole of `sources.STALENESS_DAYS`.

**Skill.** `skills/biq-competitor-analysis/SKILL.md`. Its three headline rules are that a
company is not a competitor because it appeared, that this skill compares but never ranks,
and that two figures are not comparable until checked. Identification is a two-path,
one-standard process (user-supplied names preserved verbatim and never substituted;
discovered names extracted from evidence, normalised, deduplicated only on evidence) with an
explicit evidence-to-state table yielding exactly two states, `identified` and `observed`,
and a third row that yields **nothing at all** for a mere mention or a category overlap. The
shortlist is bounded at roughly three to five and is explicitly never padded; fewer than
three and more than five both have stated, honest handling, and the shortlist may not be
chosen by ranking. Ten observable comparison dimensions with no scoring system; a comparison
table held to missing-stays-missing, missing-is-not-weakness, no derived column and
row-order-is-not-a-ranking. A five-point comparability test that fails on unknown rather than
assuming a match. Market share calculable only under six conditions, with the absent
denominator called out as the common failure. Positioning split structurally into self-claim,
independent description and labelled interpretation, with "market leader" singled out.
Developments held to dates, with retrieval time explicitly not publication time. A dedicated
*No rankings, no scores* section that declines a ranking **even when asked directly**.

**Command.** `commands/competitor-analysis.md`, a thin orchestrator in the shape of the two
before it: validate, resolve context for public terms only, route ambiguity to the skill's
protocol, invoke the skill, present its ten sections unchanged. It contains no gate call, no
dispatch, no tiering, no evidence construction, no ranking logic and no market-share
arithmetic, each asserted by test.

**Tests.** Two new modules, 252 tests, covering the prompt's items 1–110 plus the
intent-addition regression. Contract assertions run against the documents; policy assertions
run against the **real engine** through the same `open_retrieval` / `close_retrieval` calls
the skill uses, with fixtures standing in for scout replies.

**Three existing tests retargeted, none deleted.** Five assertions failed after the command
appeared, all of them statements that `/competitor-analysis` does not exist. Each was
narrowed to `/industry-research` — the one research command still unbuilt — at unchanged
strength: each still fails on any *other* command appearing.

**Four stale cross-references corrected.** `biq-market-analysis`, `/market-analysis` (two
places) and `/company-analysis` each told the user that competitor analysis "is not built".
Routing behaviour is unchanged in all four — each still declines and names the other
capability — but the claim that the capability does not exist was corrected, because after
today it does.

## 4. Files created

| Path | What |
|---|---|
| `skills/biq-competitor-analysis/SKILL.md` | The skill. All competitor-analysis judgement |
| `commands/competitor-analysis.md` | The thin orchestrator |
| `tests/unit/test_m9d3_competitor_analysis.py` | 167 focused skill tests |
| `tests/unit/test_m9d3_competitor_analysis_command.py` | 85 focused command tests |
| `docs/decisions/ADR-0020-competitor-research-intents.md` | The intent decision ADR-0019 deferred here |
| `docs/development/2026-09-14-m9d3-competitor-analysis.md` | This record |

## 5. Files modified

| Path | Change |
|---|---|
| `lib/python/biq/research/contract.py` | `LANDSCAPE` and `COMPARISON` added to `INTENTS`, with the reuse rationale in the comment |
| `lib/python/biq/research/query.py` | Two `INTENT_TERMS` entries; `SUBJECT_LEADS` extracted and extended |
| `lib/python/biq/research/__init__.py` | Both names exported and added to `__all__` |
| `tests/unit/test_command_registry.py` | `competitor-analysis` moved from `UNBUILT_RESEARCH_COMMANDS` to `RESEARCH_COMMANDS`; `UNBUILT_COMMAND` moved on to `industry-research` |
| `tests/unit/test_m9b_scout_contract.py` | Deferred tuple narrowed to `industry-research` |
| `tests/unit/test_m9d2_market_analysis_command.py` | Absence assertion narrowed to `industry-research`, plus a positive assertion that the competitor command now exists |
| `skills/biq-market-analysis/SKILL.md` | "which is not built" → "reached by `/competitor-analysis`". Behaviour unchanged |
| `commands/market-analysis.md` | Same correction, two places. Behaviour unchanged |
| `commands/company-analysis.md` | Same correction. Behaviour unchanged |
| `architecture.md` | Intent enumeration updated; `/competitor-analysis` section added with the ranking boundary; "remaining two" → "remaining"; ADR-0020 indexed |
| `project_plan.md` | M9-D.3 rows replace the single `PLANNED` row |
| `README.md` | Command status table |
| `docs/commands/README.md` | Command documentation |
| `docs/decisions/README.md` | ADR-0020 indexed |

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | User-reachable? |
|---|---|---|
| Competitor analysis judgement and workflow | `skills/biq-competitor-analysis/SKILL.md` | Yes, by description match |
| `/competitor-analysis` slash command | `commands/competitor-analysis.md` | Yes |
| Evidence-based competitor identification, two states | The skill, *Competitor identification* | Yes |
| Bounded, never-padded shortlist | The skill, *How many* | Yes |
| Ten observable comparison dimensions, no scoring | The skill, *Comparison dimensions* | Yes |
| Five-point comparability test | The skill, *The comparability test* | Yes |
| Six-condition market-share gate | The skill, *Market share* | Yes |
| Ranking refusal, including on direct request | The skill, *No rankings, no scores* | Yes |
| `LANDSCAPE` / `COMPARISON` research intents | `biq.research.contract`, `biq.research.query` | Through the skill |

## 8. Tests performed

```
python tests/run_tests.py                                            # baseline, before changes
python tests/run_tests.py unit.test_m9d3_competitor_analysis
python tests/run_tests.py unit.test_m9d3_competitor_analysis_command
python tests/run_tests.py <each of the 25 M9 modules>
python tests/run_tests.py                                            # full regression
claude plugin validate . --strict
```

## 9. Test results

**Baseline, before any change:** `ran 2223 | failures 0 | errors 0 | skipped 19`

**Focused — skill:** `ran 167 | failures 0 | errors 0 | skipped 0` (`OK`)

**Focused — command:** `ran 85 | failures 0 | errors 0 | skipped 0` (`OK`)

**M9 regression, 25 modules:** `ran 1314 | failures 0 | errors 0 | skipped 2`
(the 2 skips are `integration.test_m9b_live_smoke`, which skips without a live fixture, as
it did before this milestone)

**Full regression:** `ran 2475 | failures 0 | errors 0 | skipped 19` (`OK (skipped=19)`)
— 2223 baseline + 252 new, no change in skip count.

**Plugin validation:** `✔ Validation passed`

Two intermediate runs failed and are recorded rather than hidden. The first, nine failures in
the new skill module, were all mistaken assertions of mine about the engine — `classify_tier`
returns a tuple not a mapping; a no-terminator reply surfaces as `unavailable` rather than
carrying `NO_TERMINATOR` as its `reason`; a tier-D-only set parses `ok` with `usable: 0`
rather than failing. Every one was fixed by correcting the test to what the engine actually
does; **no production behaviour was changed to make a test pass.** The second, five failures
across three existing modules, were the "not yet built" assertions described above.

**Live smoke test: NOT RUN.** See *Remaining work*.

## 10. Issues discovered

- **The command-thinness "launch" ban does not transfer.** `unit.test_m9d2_market_analysis_command`
  asserts the bare word `launch` is absent from the command. `/competitor-analysis` cannot
  meet that: a product launch is a development this skill reports, and "what to launch" appears
  in the sentence that refuses strategy. The new test asserts dispatch *phrasing* instead —
  `launch the`, `dispatch the scout`, `invoke the scout` and six more — which is what the
  assertion was ever guarding, and additionally asserts the command hands the single dispatch
  to the skill. No weakening: the market command's own stricter assertion is untouched.
- **`/market-analysis` still shows `REVIEW` in `project_plan.md`** pending its own
  fresh-session live smoke test. That smoke test was performed earlier on 2026-09-14 and
  passed, but the verification prompt that ran it forbade documentation changes and this
  prompt forbids modifying market-analysis, so the row was left alone. It is a documentation
  lag, not a defect, and closing it is an owner action.
- **D-11 remains open.** ADR-0017 and ADR-0018 are still missing from `docs/README.md`.
  ADR-0020 was added to `docs/decisions/README.md` and `architecture.md`, matching where
  ADR-0019 was indexed; correcting the two earlier omissions remains an unrelated change and
  was left alone.

## 11. Decisions made

[ADR-0020 — Two research intents added for competitor analysis, and two reused](../decisions/ADR-0020-competitor-research-intents.md).

It also answers the question ADR-0019 explicitly deferred to this milestone — whether a flat
intent enumeration is still the right shape at nine members. It is; the per-category table is
deferred to `/industry-research` (M9-D.4) with the condition restated.

## 12. Architecture changes

`architecture.md`: the intent enumeration now names `landscape` and `comparison` and records
that M9-D.3 reused two intents rather than adding four. A new subsection documents
`/competitor-analysis` → `biq-competitor-analysis`, its two defining rules, and — at length,
because it is the boundary most likely to be argued with — why the ranking refusal exists and
where strategy actually lives. The "remaining two research commands" sentence became one.
ADR-0020 indexed.

## 13. Project-plan updates

| Row | From | To |
|---|---|---|
| `biq-competitor-analysis` skill | (folded into a joint `PLANNED` row) | `COMPLETED` |
| `/competitor-analysis` command | (same) | `REVIEW` — live smoke outstanding |
| `/industry-research` command | (same) | `PLANNED` — M9-D.4+ |

## 14. Documentation updates

`README.md` (command status), `docs/commands/README.md` (command documentation),
`architecture.md` (above), `project_plan.md` (above), `docs/decisions/README.md` (ADR index),
ADR-0020, and this record. Four stale "not built" cross-references corrected in the two
earlier research skills and commands.

## 15. Remaining work

**The fresh-session live smoke test of `/competitor-analysis Microsoft --focus landscape`
has not been run, and cannot be run from this session.** The milestone requires a genuinely
fresh Claude Code session — not `--continue`, not `--resume` — and the session that wrote the
command is by definition not fresh. This is the same gap M9-D.2 recorded and it is an owner
action: open a new session and invoke the command once.

Until it runs, `/competitor-analysis` is **not demonstrated live** and stays at `REVIEW`.
What the live test must establish is listed in the milestone prompt; the deterministic half
of every one of those properties is already covered by the 252 focused tests, so what remains
genuinely untested is the dispatch leg — the runtime launching `biq-research-scout` and a
real reply reaching the production parser without repair.

Not in scope and not started: `/industry-research`, SWOT, strategy analysis, decision
support, any ranking framework, any competitive scoring.

## 16. Git commit reference

**No commit.** No push. Branch `main`, working tree dirty by design. The milestone prompt
forbade both.
