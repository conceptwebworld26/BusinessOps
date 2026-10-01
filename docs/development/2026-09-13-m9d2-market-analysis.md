# 2026-09-13 — M9-D.2: Market Analysis skill and `/market-analysis` command

**Milestone:** 9-D.2 — External research commands, the second of four
**Status on completion:** `REVIEW` — deterministic work complete; fresh-session live smoke test outstanding
**Supersedes:** None

## 1. Prompt / task performed

Implement the next research capability, `/market-analysis`, following the architectural
pattern M9-D.1 established: a thin command over a skill that owns all analytical behaviour
and consumes the existing research pipeline. Explicitly out of scope: competitor analysis,
industry research, any change to company analysis, any redesign of the research pipeline,
any change to the `BIQ-REC/1` / `BIQ-END/1` protocol, source-tier policy, disclosure-gate
policy or candidate-claim verification policy. No commit, no push.

## 2. Objective

Ship market research that is safe in the one way market research is uniquely unsafe: two
honest, high-quality sources routinely size the same market three-fold apart because they
drew the boundary in different places. A system that averages those, or picks one, or prints
a range implying they measure one quantity, produces a confident number that is wrong and
carries no signal that it is wrong. The milestone's real deliverable is that the system
refuses to do that, and says why.

## 3. Changes made

**Phase 0 — inspection.** Read the research core end to end before writing anything.
Findings that shaped the work:

- The `market_sizing` claim kind and its 730-day staleness window already existed in
  `sources.py`. No new claim kind was needed.
- The declared-conflict transport (ADR-0016) already carries `definition`, `scope`, `unit`
  and `value` per position, refuses a `source_tier` key, and keeps a declared conflict a
  conflict even when the figures agree numerically. That is precisely the market-size
  definitional-mismatch case; it needed no extension at all.
- The first-party registry (ADR-0018) already keeps a company's own domain at tier B with a
  "not independent" note, which is the mechanism for saying that a participant's own market
  estimate is not independent evidence of market size.
- `contract.INTENTS` had no intent expressing *what a market is* or *what moves it*, and
  nothing in the engine or the test suite enumerated `INTENTS` exhaustively.
- Three existing tests asserted `/market-analysis` does not exist. One of them —
  `test_commands_negative.test_an_unknown_command_is_refused_by_name` — tests
  `commands.run()`, which still raises `KeyError` because research commands carry no registry
  spec; it needed no change and was left alone. Two were statements about what had been
  built and were retargeted the way M9-D.1 retargeted its equivalents.

**The one shared-core change (ADR-0019).** `overview` and `drivers-risks` had no intent to
map onto. The nearest, `PROFILE`, is rendered by the deterministic query builder as the
literal words **"company profile"** — so `/market-analysis cold chain logistics --focus
overview` would have dispatched `cold chain logistics company profile` and retrieved company
pages for a market question, succeeding silently and reading fine. Two constants were added
to `contract.INTENTS` and two entries to `query.INTENT_TERMS`, plus exports. Strictly
additive: the five original intents keep their names, positions, wording and behaviour, and
a test pins `Northwind Logistics logistics company profile` as a literal string so any drift
in company research fails here rather than in production.

**The skill.** `skills/biq-market-analysis/SKILL.md`. Three rules lead it: a size figure
appears only if a source stated it and appears with that source's definition; two figures are
not comparable until checked; a forecast belongs to whoever made it. The
**market-size compatibility test** is the centre — definition, geography, unit/currency,
period and methodology must *all* match, and an unstated one **fails the check on unknown,
not on assumed match**. Five focus values, each one distinct research question with its own
gate-authorised retrieval, operation and single dispatch; `full` is four retrievals and the
skill forbids merging questions to save a dispatch. Ten fixed output sections, section 7
scoped to market structure with competitor profiling explicitly refused.

**The command.** `commands/market-analysis.md`, the same shape as `/company-analysis` so the
two read side by side. It sequences and nothing else, and says so; it additionally declares
"No arithmetic here" because the thing a market command would most plausibly drift into is
relating two numbers the skill reported separately.

**Tests.** Two new modules following the M9-C.3 / M9-D.1 conventions: contract assertions
against the collapsed markdown, and policy assertions against the real
`open_retrieval`/`close_retrieval` path with fixtures standing in for the scout reply. No
network access.

**Four test assumptions I got wrong and corrected against real behaviour**, rather than
adjusting production to match the tests:

1. Tier D is **not** absent from the evidence set. It is carried, marked `usable: false`
   with an `excluded_reason`, and counted under `excluded`. The skill's wording was corrected
   to say that accurately, and the tests now assert the real shape.
2. A tier-D-only reply returns `status: ok` with `usable: 0` and `support: unsupported` — not
   a failed retrieval. Tested as such, plus a test that such a set supports no claim.
3. `assert "average" not in json.dumps(conflict)` failed because the engine's own statement
   reads "neither is averaged away nor silently preferred". Replaced with structural
   assertions: two positions, no `mean`/`average`/`midpoint`/`consensus`/`combined` key, and
   the spread computed from the two values.
4. The section-order test spliced two numbered tables together, because the compatibility
   test is also a numbered table. Scoped to the Output section.

A fifth correction was mechanical: the repository is checked out CRLF, and reading the skill
in binary mode made every `^---\n` regex fail. The test reads in text mode, with a comment
saying why.

## 4. Files created

| File | What |
|---|---|
| `skills/biq-market-analysis/SKILL.md` | The Market Analysis skill — all analytical behaviour |
| `commands/market-analysis.md` | The thin `/market-analysis` orchestrator |
| `tests/unit/test_m9d2_market_analysis.py` | 120 skill + pipeline tests |
| `tests/unit/test_m9d2_market_analysis_command.py` | 70 command-contract + policy tests |
| `docs/decisions/ADR-0019-market-research-intents.md` | The two added intents, and why |
| `docs/development/2026-09-13-m9d2-market-analysis.md` | This record |

## 5. Files modified

| File | Change |
|---|---|
| `lib/python/biq/research/contract.py` | Added `OVERVIEW` and `DRIVERS` to `INTENTS` (ADR-0019). Additive only |
| `lib/python/biq/research/query.py` | Two `INTENT_TERMS` entries for the new intents |
| `lib/python/biq/research/__init__.py` | Exported both names |
| `tests/unit/test_command_registry.py` | `market-analysis` moved from `UNBUILT_RESEARCH_COMMANDS` to `RESEARCH_COMMANDS`; docstring updated |
| `tests/unit/test_m9b_scout_contract.py` | `market-analysis` removed from the still-deferred tuple; docstring records why |
| `architecture.md` | `/market-analysis` in the research command surface; the intent enumeration in Layer 2B; unbuilt list now two; ADR-0019 in § 19 |
| `project_plan.md` | M9-D.2 rows; D-11 recorded |
| `README.md` | `/market-analysis` in the M9-D table, with usage and the sizing rule |
| `docs/commands/README.md` | `/market-analysis` row and description |
| `docs/decisions/README.md` | ADR-0019 indexed |

## 6. Files deleted

None. No test was deleted, weakened or disabled.

## 7. Features implemented

| Feature | Location | User-reachable? |
|---|---|---|
| Market Analysis skill | `skills/biq-market-analysis/SKILL.md` | Yes — model-invocable |
| `/market-analysis` command | `commands/market-analysis.md` | Yes — pending fresh-session registration |
| Market-size compatibility test | The skill | Yes, through both |
| `OVERVIEW` / `DRIVERS` intents | `lib/python/biq/research/` | Indirectly, through the skill |

## 8. Tests performed

```
python tests/run_tests.py unit.test_m9d2_market_analysis
python tests/run_tests.py unit.test_m9d2_market_analysis_command
python tests/run_tests.py <each of the 24 M9 modules>
python tests/run_tests.py
claude plugin validate . --strict
```

## 9. Test results

Real output, all run on 2026-09-13.

```
unit.test_m9d2_market_analysis           ran 120 | failures 0 | errors 0 | skipped 0
unit.test_m9d2_market_analysis_command   ran  70 | failures 0 | errors 0 | skipped 0
full suite                               ran 2223 | failures 0 | errors 0 | skipped 19
```

Baseline before this milestone was `ran 2033 | failures 0 | errors 0 | skipped 19`; the
delta is exactly the 190 tests added. All 24 M9 modules pass individually, including
`unit.test_m9c3_company_analysis` (60) and `unit.test_m9d1_company_analysis_command` (50),
both unchanged. `unit.test_command_registry` and `unit.test_m9b_scout_contract` pass at
their amended assertions.

`claude plugin validate . --strict` → `✔ Validation passed`.

**Not run:** the fresh-session live `/market-analysis` smoke test. See § 15.

## 10. Issues discovered

- **D-11 (new, open).** ADR-0017 and ADR-0018 are referenced in `architecture.md` prose but
  appear in neither ADR index. Found while indexing ADR-0019, which was added to both.
  Correcting the two earlier omissions is unrelated to this milestone and was left alone.
- **Observation, not filed.** `skills/biq-company-analysis/SKILL.md` says "Tier D never
  reaches you — it is excluded at ingestion." A tier D item does reach the set, marked
  unusable with an exclusion reason. The consequence is identical (it supports nothing), so
  the instruction is safe, but the wording is imprecise. The new skill states it accurately.
  Company analysis was out of scope and was not edited.

## 11. Decisions made

[ADR-0019 — Two research intents added for market analysis](../decisions/ADR-0019-market-research-intents.md).
No other decision was required: every other mechanism the milestone needed already existed.

## 12. Architecture changes

`architecture.md` § 4 (Layer 2B) now records the intent enumeration and its closure; § 7
(The research command surface) describes `/market-analysis`, its focus-to-retrieval mapping
and the market-size compatibility test, and the unbuilt list drops to two; § 19 indexes
ADR-0019. No layer, boundary or contract moved.

## 13. Project-plan updates

- `biq-market-analysis` skill: `PLANNED` → `COMPLETED`
- `/market-analysis` command: `PLANNED` → `REVIEW` (live smoke outstanding)
- The remaining research commands row narrowed to `/competitor-analysis` ·
  `/industry-research`, `PLANNED`
- D-11 recorded

## 14. Documentation updates

`architecture.md`, `project_plan.md`, `README.md`, `docs/commands/README.md`,
`docs/decisions/README.md`, ADR-0019, this record. `docs/skills/README.md` was **not**
updated: it indexes the six internal analytics skills only and has never listed a research
skill, including `biq-company-analysis`. Extending its scope is a separate change.

## 15. Remaining work

**The fresh-session live `/market-analysis` smoke test.** The milestone requires one
invocation of `/market-analysis cold chain logistics --focus overview` in a genuinely fresh
Claude Code session — not `--continue`, not `--resume`, and not the session that created the
command. That session is an owner action and cannot be started from inside this one, so the
test was not run and no result for it is claimed. Until it runs, `/market-analysis` is
implemented and deterministically tested but **not demonstrated live**.

Expected, for whoever runs it: exactly one dispatch (a single `PROFILE`-equivalent
`OVERVIEW` retrieval), zero retries, `BIQ-REC/1` records and one `BIQ-END/1` terminator, the
raw reply to `parse_reply()` with no repair, tiers recomputed locally, no claim verified,
and all ten sections present. Market-size evidence being thin or absent under an `overview`
focus is an acceptable outcome provided the output says so.

## 16. Git commit reference

N/A. No commit was created and nothing was pushed, as instructed. Working tree carries the
changes listed in §§ 4–5.
