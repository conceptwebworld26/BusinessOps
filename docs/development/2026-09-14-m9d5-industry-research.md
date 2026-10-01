# 2026-09-14 — M9-D.5 Industry Research Skill and `/industry-research` command

**Milestone:** M9-D.5 — industry research
**Status on completion:** COMPLETED (skill) / REVIEW (command — live smoke deferred by the prompt)
**Supersedes:** None

## 1. Prompt / task performed

Implement `skills/biq-industry-research/SKILL.md`, `commands/industry-research.md`, and the
minimum industry intent mappings in the existing canonical registry. Reuse existing intents
wherever the semantics are genuinely identical; add a new canonical intent only where they
are materially different. Do not create a second registry or a second research pipeline, do
not change the scout protocol, disclosure policy, source-tier policy, evidence semantics or
claim verification, and do not change company, market or competitor behaviour. No live web
research in this session.

Explicitly out of scope and not done: SWOT, strategy analysis, decision support,
executive-report changes, MCP servers, commits, pushes, live smoke.

## 2. Objective

Give BusinessIQ a fourth research capability whose analytical object is the **industry as a
system** — distinct from a market and from a set of named competitors — without growing a
parallel architecture to hold it.

## 3. Changes made

**Baseline first.** `python tests/run_tests.py` before any edit: **2533 tests, 0 failures, 0
errors, 19 skipped** — identical to the baseline the prompt stated, so nothing needed
explaining before implementation.

**Then the intent decision, which is the only genuinely open question in the milestone.**
Industry research has five research questions. The prompt's rule is reuse where the question
is the same, add only where it is materially different, and the repository already has a
precedent for how to judge that: ADR-0019 added `OVERVIEW` rather than reusing `PROFILE`
because `PROFILE` renders as the literal words *company profile*, which would have sent a
market question looking for company pages. **The query wording is the retrieval**, so that
is the test I applied to each of the five.

| Question | Decision | Why |
|---|---|---|
| size and growth | **reuse `SIZING`** | Same question; `market size` is the phrase industry-size sources use. Purpose text widened to "market or industry"; `query_term` untouched |
| what is changing | **reuse `TRENDS`** | Already object-agnostic — `trends` — and already shared by three categories |
| what moves and constrains it | **reuse `DRIVERS`** | Same question; `market drivers and constraints` retrieves industry drivers unchanged |
| what is this industry | **new `DEFINITION`** | `OVERVIEW` renders as *market overview*, which steers an industry-definition question at market-research reports rather than classifications, trade bodies and industry associations |
| how is it organised | **new `STRUCTURE`** | Nearest existing intent is `LANDSCAPE`, rendering as *competitive landscape* — which would steer industry structure straight into competitor research, the one thing this skill must not become |

So: **five research questions, five intents, two of them new.** The enumeration goes from
nine to eleven.

**Naming mattered here.** `industry_overview` and `industry_structure` would have been
category-prefixed twins of the kind ADR-0020 rejected and a test forbids. `DEFINITION` and
`STRUCTURE` name the *question* rather than the category asking it, so either can be reused
by a later category without a rename — which is the same property that let `SIZING` and
`DRIVERS` be reused here.

**The registry change is one file.** `intents.py` gained two records, `INDUSTRY` joined
`ANALYSIS_CATEGORIES`, and `SIZING`, `TRENDS` and `DRIVERS` gained `INDUSTRY` in their
`categories` field. `contract.py`, `query.py` and `research/__init__.py` only re-export the
two new identifiers; no literal was added to any of them, and `INTENTS`, `INTENT_TERMS` and
`SUBJECT_LEADS` remain derived views. `SUBJECT_LEADS` did not change at all — both new
intents trail the subject, matching the market intents they sit beside.

**Then the skill and the command**, written to the shape of `biq-market-analysis` and
`/market-analysis` so a reviewer can read them side by side, with the two industry-specific
disciplines added: nothing is scored, and structure must not drift into competitor analysis.

## 4. Files created

- `skills/biq-industry-research/SKILL.md`
- `commands/industry-research.md`
- `tests/unit/test_m9d5_industry_research.py` — 131 tests
- `tests/unit/test_m9d5_industry_research_command.py` — 51 tests
- `docs/development/2026-09-14-m9d5-industry-research.md` — this record

## 5. Files modified

**Production:**

- `lib/python/biq/research/intents.py` — two records added; `INDUSTRY` added to
  `ANALYSIS_CATEGORIES` and to three existing records' `categories`; two `purpose` strings
  widened to say "market or industry"
- `lib/python/biq/research/contract.py` — re-exports `DEFINITION` and `STRUCTURE`
- `lib/python/biq/research/__init__.py` — same, plus `__all__` entries

**Tests (all six retargets are the previous *absence* of `/industry-research`, or a closed
count the milestone is sanctioned to grow):**

- `tests/unit/test_command_registry.py`
- `tests/unit/test_m9b_scout_contract.py`
- `tests/unit/test_m9d2_market_analysis_command.py`
- `tests/unit/test_m9d3_competitor_analysis_command.py`
- `tests/unit/test_m9d3_competitor_analysis.py`
- `tests/unit/test_m9d4_research_intent_registry.py`

**Documentation:** `README.md`, `docs/commands/README.md`, `architecture.md`,
`project_plan.md`, and a one-clause factual correction in the Scope section of
`commands/company-analysis.md`, `commands/market-analysis.md` and
`commands/competitor-analysis.md` — see *Issues discovered*.

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | User-reachable? |
|---|---|---|
| Industry research skill, six focus values, ten sections | `skills/biq-industry-research/SKILL.md` | Yes — model-invocable |
| `/industry-research` thin command | `commands/industry-research.md` | Yes — slash command |
| `DEFINITION` and `STRUCTURE` intents | `lib/python/biq/research/intents.py` | Indirectly, via the skill |
| Industry category mappings | same | Indirectly |

## 8. Tests performed

```
python tests/run_tests.py                                          # baseline, before edits
python tests/run_tests.py unit.test_m9d5_industry_research
python tests/run_tests.py unit.test_m9d5_industry_research_command
python tests/run_tests.py unit.test_m9d4_research_intent_registry
<mutation: one query_term + injected machinery in the command, re-run, revert>
<M9 subset: all 28 test_m9*.py modules across unit/integration/negative>
python tests/run_tests.py                                          # full regression
claude plugin validate . --strict
```

## 9. Test results

**Baseline, before any change:**

```
Ran 2533 tests in 110.770s
OK (skipped=19)
ran 2533 | failures 0 | errors 0 | skipped 19
```

**Focused suites:**

```
unit.test_m9d5_industry_research:          ran 131 | failures 0 | errors 0 | skipped 0
unit.test_m9d5_industry_research_command:  ran  51 | failures 0 | errors 0 | skipped 0
```

**Teeth check.** Green tests over new documents prove nothing unless they can fail, so two
mutations were applied at once — `STRUCTURE`'s query term changed to
`competitor research industry structure`, and a line reading *"Use WebSearch to fetch sources
and compute the concentration ratio = top4 / total"* appended to the command:

```
unit.test_m9d5_industry_research:          ran 131 | failures 1
unit.test_m9d5_industry_research_command:  ran  51 | failures 4
unit.test_m9d4_research_intent_registry:   ran  60 | failures 2
```

Seven independent assertions caught them — the pinned query string, the category-label leak
check, the thinness token list, the formula-token list and the retrieval-tool check among
them. Both mutations were reverted and all three suites re-ran clean.

**M9 subset — all 28 `test_m9*` modules:**

```
Ran 1556 tests in 0.387s
OK (skipped=2)
ran 1556 | failures 0 | errors 0 | skipped 2
```

**Full regression:**

```
ran 2719 | failures 0 | errors 0 | skipped 19
```

2719 = 2533 baseline + 182 new + 4 added while retargeting (two positive assertions replacing
the emptied research tuple, and two splits in the M9-D.4 file).

**Plugin validation:**

```
Validating marketplace manifest: .claude-plugin\marketplace.json
✔ Validation passed
```

## 10. Issues discovered

**One test of mine was asserting a guarantee the system does not make.** My first draft of
"no private context field can enter a query" passed `public_terms={"revenue": …}` and
expected a refusal. The gate allowed it: `revenue` is not in `contract.PROHIBITED_KEYS`,
which is matched on the key and deliberately covers shapes like `customer`, `api_key`,
`transactions`, `ledger` and `rows`. This is **existing gate behaviour, identical for
company, market and competitor research**, and the milestone forbids changing disclosure
policy — so the test was wrong, not the engine. It now asserts what is actually guaranteed
(every prohibited key is refused and its value never echoes back, and a row collection is
refused whatever it is called) and its docstring records that the prohibited-key set is one
of three layers: this skill also reads no business file, so it holds no internal figure to
send, and its input contract admits only public terms. **Flagged rather than silently
adjusted**, because "the gate refuses a key called `revenue`" is a reasonable thing for a
future reader to assume and it is not true.

**One vacuous assertion avoided.** `ScoutBrief` refuses anything that is not a
`RetrievalRequest` carrying a gate authorisation, so my first parser test errored rather than
passing. The fix builds the brief the way production does — and the refusal became its own
test (`test_46c`), since "no path reaches the scout without the gate" is worth asserting
directly.

**A stale sentence in three shipped command files.** `/company-analysis`,
`/market-analysis` and `/competitor-analysis` each ended their Scope section with
"`/industry-research` — the last of which is not built", and `docs/commands/README.md` said
the same. Building it makes all four statements false. I corrected the clause in each — a
factual correction to prose, changing no behaviour, no input, no output and no rule — and
flag it here because the prompt ring-fenced those files. No test pinned the phrase.

**No stop condition was triggered.** Specifically: two new intents is the minimum, not more;
three existing intents were safely reused; no existing query string moved; company, market
and competitor behaviour is unchanged; no second registry; no disclosure, scout, evidence or
claim change; no scoring methodology was needed because nothing is scored; concentration is
constrained by requiring a sourced denominator; private data cannot cross the boundary;
external content stays untrusted; and full regression passed without weakening coverage.

**Pre-existing, not touched:** D-11 (ADR-0017 and ADR-0018 missing from both ADR indexes)
remains open.

## 11. Decisions made

**No ADR was created, deliberately.** ADR-0021 already decided both the mechanism and the
test this milestone applied:

> When that skill is built, `industry` joins `ANALYSIS_CATEGORIES` and the intents it asks
> add `INDUSTRY` to their `categories` field. If it needs a question no existing intent
> expresses, that intent is added as one new record — which is now a single edit in a single
> file, which was the point.

That is exactly what happened, twice. The reuse-versus-add test is ADR-0019's and ADR-0020's,
applied unchanged. Nothing here is a new architectural decision, and the prompt says not to
create an ADR merely to document implementation, so the intent reasoning lives beside the
records in `intents.py` and in section 3 above.

ADR-0019, ADR-0020 and ADR-0021 were not modified.

## 12. Architecture changes

`architecture.md`:

- **Layer 2B** — the category/intent table's `industry` row changed from "none —
  `/industry-research` is not built" to its five intents; the shared-intent sentence updated
  (`trends` now names four categories; `positioning`, `sizing` and `drivers` each name two);
  the intent-enumeration paragraph records the M9-D.5 additions and that the enumeration
  stands at eleven.
- **The research command surface** — "The remaining research command … is not built" replaced
  by the `/industry-research` section: its six focus values, the industry-as-a-system
  distinction from market and competitor analysis, the no-scoring rule and the
  structure-without-competitor-drift rule, and the sixth compatibility check industry sizing
  adds. Ends "All four research commands are now built."

`reference/research-policy.md` was **not** changed: it describes disclosure tiers, source
tiers, recency and conflicts, none of which moved.

## 13. Project-plan updates

- **Added:** `biq-industry-research` skill — `COMPLETED`.
- **Added:** `/industry-research` command — `REVIEW`, with the outstanding live smoke named
  as deferred by the prompt rather than skipped.
- **Removed:** the `/industry-research` `PLANNED` row it replaces.
- **Unchanged, deliberately:** every M9-D.1 to M9-D.4 row. Industry research, SWOT, strategy
  and decision support are marked complete nowhere except the industry rows above; SWOT,
  strategy and decision support remain unbuilt, and a new test asserts their command surfaces
  do not exist.

## 14. Documentation updates

`README.md`, `docs/commands/README.md`, `architecture.md`, `project_plan.md`, the Scope
clause in three sibling command files, and this record.

## 15. Remaining work

**The fresh-session live smoke**, explicitly deferred by the milestone prompt to a separate
session after review. Until it runs, `/industry-research` is not demonstrated live and its
plan row stays `REVIEW` — the same position `/company-analysis`, `/market-analysis` and
`/competitor-analysis` each occupied after their implementation milestones.

**Deferred by design:**

- **`full` is five retrievals and five dispatches.** That is the most of any research skill.
  The cost is stated in the skill rather than optimised away, because merging two questions
  into one broad query returns sources that do neither well.
- **No industry benchmark join.** Comparing an industry against the user's own figures
  fetches the public side and joins locally; the skill says so and never sends the internal
  figure. The local-join capability itself is not this milestone's.
- **`biq-strategy-recommendations` remains unbuilt** (Milestone 10). Every strategy,
  entry, pricing and investment question this skill declines names it as the destination.

**Confirmation of no behaviour change to what already shipped.** Four independent lines of
evidence: the pre-existing suite passed with only the six sanctioned retargets, all of which
asserted an absence this milestone removes or a count it is sanctioned to grow; eight
existing query strings spanning all three earlier skills are pinned byte-for-byte in the new
suite and unchanged; `SUBJECT_LEADS` and all nine existing query terms are unchanged; and the
mutation run showed the suites can fail on exactly these properties.

## 16. Git commit reference

**N/A — no commit.** The prompt forbade committing and pushing. Working tree on `main`,
uncommitted. Files created and modified as listed in sections 4 and 5; no other file in the
repository was touched.
