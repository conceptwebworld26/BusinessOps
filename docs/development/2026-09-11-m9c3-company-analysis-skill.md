# 2026-09-11 — M9-C.3: `biq-company-analysis` skill

**Milestone:** 9 — External Intelligence & Disclosure Gate (M9-C.3)
**Status on completion:** `COMPLETED`
**Supersedes:** None.

---

## 1. Prompt / task performed

Implement M9-C.3 — the `biq-company-analysis` external-research skill, the first substantive
M9-C capability. Use the approved M9-A/M9-B infrastructure and the model-mediated
`biq-research-scout` seam; build no second research pipeline; respect disclosure, source-tier,
evidence and candidate-claim policy; fail safely on ambiguity and thin evidence; make recent
developments date-aware; surface conflicts rather than resolving them; fabricate nothing.
Comprehensive deterministic tests, focused then full. Inspect the existing contracts first and
**stop and report** if one is insufficient rather than changing architecture. No ADR unless
genuinely required. Dated development record, project-plan status for M9-C.3 only. Build none
of the other three skills, no commands, no SWOT, strategy, decision support or reporting. No
commit, no push.

## 2. Objective

Give BusinessIQ its first working external-research capability: an evidence-backed analysis of
one named company, assembled entirely from public sources through the existing gate, with every
figure quoted from a citation and every source tiered and dated locally.

## 3. Changes made

### Contract inspection, before writing anything

Six checks against the shipped engine rather than against documentation:

| Question | Answer |
|---|---|
| Does the request contract support company research? | Yes — `R.COMPANY` category; `PROFILE`, `TRENDS`, `POSITIONING` intents |
| Does a company query pass the gate at Tier 0? | **Yes.** All three intents returned `authorised`, tier 0, e.g. `Maersk logistics 2026 company profile` |
| Is the company name a permitted public term? | Yes — the query builder places the subject first for `PROFILE`/`POSITIONING` |
| Can the engine detect an ambiguous company? | **No** — it refuses only an *empty* subject. Ambiguity is model judgement and belongs in the skill |
| Are tier A/B sources recognised by identity? | Yes — `sec.gov`, `.gov`, `ons.gov.uk` → A; `reuters.com`, `ft.com`, `bloomberg.com` → B; unrecognised → C |
| Can a conflict be recorded through the handoff API? | **No.** See §10 |

Five of six were sufficient. The sixth is a genuine gap, reported rather than patched.

### The skill

`skills/biq-company-analysis/SKILL.md`, following the house pattern of the six internal
analysis skills — frontmatter with trigger phrases, the rule that matters most, a does/does-not
table, inputs, method, output, failure conditions, related policy.

Design decisions worth recording:

1. **Two rules lead, because they are the two ways this skill could do damage.** *"A financial
   figure appears only if a source stated it"* — not scaled from headcount, not inferred from a
   funding round. And *"'recent' requires a date"* — an `undated` item cannot support a recency
   claim, because you cannot show when it happened.
2. **Ambiguity is resolved before the request is built.** The engine cannot tell that "Apple"
   might be three different entities and will happily research the wrong one. The skill asks,
   naming its candidates. A well-cited report on the wrong company is worse than a question.
3. **A `full` analysis is up to three retrievals, one per intent, each dispatched once.** This
   needed stating explicitly, because it sits next to a rule it superficially resembles:
   re-running the gate to get a *better answer to the same question* is forbidden; asking three
   *different* questions, each once, is not. Within one retrieval, one dispatch.
4. **No recommendations.** A recommendation is provenance class 7 and needs all six parts. This
   skill stops at class 5 interpretation and names `biq-strategy-recommendations` (M10) as the
   owner. Risks and opportunities are interpretation, labelled as such, each tracing to a cited
   item.
5. **The conflicts limitation is written into the skill itself**, not just this record —
   including the instruction not to read an empty `conflicts` array as agreement.

No engine code was added. The skill consumes `open_retrieval` / `close_retrieval` and reads the
dictionaries they return.

### The tests

`tests/unit/test_m9c3_company_analysis.py` — 59 tests in five classes, covering the skill
document and the pipeline behaviour it depends on.

## 4. Files created

- `skills/biq-company-analysis/SKILL.md`
- `tests/unit/test_m9c3_company_analysis.py` — 59 tests
- `docs/development/2026-09-11-m9c3-company-analysis-skill.md` — this record

## 5. Files modified

- `project_plan.md` — M9-C.3 status only (§13).

No `lib/`, no `agents/`, no `commands/`, no `reference/`, no `architecture.md`, no other skill.

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | User-reachable? |
|---|---|---|
| `biq-company-analysis` skill | `skills/biq-company-analysis/SKILL.md` | **Not yet.** Model-invocable only — no `user-invocable`, and no slash command. `/company-analysis` is M9-D |

## 8. Tests performed

```bash
PYTHONPATH=lib/python python -m unittest tests.unit.test_m9c3_company_analysis
python tests/run_tests.py
claude plugin validate .claude-plugin/plugin.json --strict
```

## 9. Test results

**Focused — 59 tests, all passing:**

```
Ran 59 tests in 0.021s
OK
```

| Class | Tests | Covers |
|---|---|---|
| `TestSkillContract` | 19 | Location and naming; only supported frontmatter (ADR-0001); **not** a slash command; trigger phrases; no invented figures; date required for "recent"; ask when ambiguous; no recommendations; no second pipeline; names the real entry points, the scout and the gate; all ten output sections; the provenance labels; one dispatch per retrieval; the conflicts limitation; owning policy documents; the internal-data boundary |
| `TestHappyPaths` | 8 | Identifiable company; citation retained; dated development is `current`; multiple sources kept; mixed tiers tiered individually (A/B/C); tier A supports a material claim; a candidate claim is produced; the claim keeps source, citation, date, tier and evidence id |
| `TestSafetyAndPolicy` | 12 | Tier 0; the brief is six fields with no internal term in any of them; the company name **does** reach the query as a public term; a scout-supplied tier is ignored; tier-C-only is `unsupported` and the material claim is refused; tier D is present but not usable and supports nothing; no claim can be `verified`; every item untrusted; content withheld from instruction context; an injected instruction changes no tier, no decision, no trust |
| `TestResearchQuality` | 12 | Empty and whitespace company refused with **no dispatchable brief**; no citable source and retrieval failure are structured outcomes; out-of-window evidence labelled `dated`, not dropped; missing date never inferred; the 365-day boundary tested either side; partial retrieval keeps what is citable and records the rest; rejection carried into notes; duplicates do not read as corroboration; conflicting figures both survive; `conflicts` is empty on this path |
| `TestOutputQuality` | 8 | Ingestion adds no figure; an absent metric stays absent; no citation is manufactured; `summary` carries what the skill reads first; support degrades when the authoritative source is removed; an inferred tier says so; every item carries the untrusted banner; an advisory statement is refused here too |

**Full regression — 1,671 tests, all passing:**

```
Ran 1671 tests in 112.325s
OK (skipped=19)
ran 1671 | failures 0 | errors 0 | skipped 19
```

Baseline 1,612 at M9-C.2; +59 is exactly this task. **Skips unchanged at 19.**

**Plugin validation:** the single known **R-08** advisory (root `CLAUDE.md` is not shipped
plugin context), unchanged and already accepted in the plan's Known issues. The new skill
introduces **no new warning**.

### Five failures during development, all fixed before completion

Recorded because the fixes changed the deliverable, not just the tests:

- Three were wrong assertions of mine (matching across a line break; expecting a refusal to omit
  a `brief` key when it returns `brief: None`).
- **Two were a real defect in the skill.** I had written that out-of-window items are labelled
  `stale`. The engine's `freshness` vocabulary is `current` / `dated` / `undated`; `stale`
  appears only as a *set-level summary counter*. A skill telling the model to look for a value
  the engine never emits would have failed silently at the worst moment. The skill now names all
  three values and notes the summary's differing word.

## 10. Issues discovered

**A contract gap, reported rather than patched, as the brief required.**

`close_retrieval` takes no conflict argument and returns `evidence.as_dict()` — a plain
dictionary. `EvidenceSet.record_conflict()` therefore cannot be reached from this path, and
`evidence["conflicts"]` is **always `[]`** here, no matter how sharply the sources disagree.
This is the same fact the M9-B live run surfaced: the scout described a real definitional
conflict in prose and the engine's conflict count was nonetheless `0`.

Three ways to close it, none taken here:

| Option | Assessment |
|---|---|
| Add a `conflicts=` parameter to `close_retrieval`, mirroring `proposals=` | Smallest and most consistent with the existing shape. Needs an owner decision — it changes a shipped API |
| Have the skill build an `EvidenceSet` directly to call `record_conflict()` | **Rejected.** That is a second pipeline, which the brief forbids and which would duplicate ingestion |
| Detect conflicts automatically during ingestion | **Rejected for now.** Automatic conflict resolution is explicitly out of scope, and detection without resolution still needs a definition of "materially disagrees" per claim kind |

**What the skill does in the meantime** is honest rather than silent: section 8 of the output is
written by the model from the evidence, the limitation is stated inside the skill, and the skill
instructs that an empty `conflicts` array must not be read as agreement.
`test_the_conflicts_array_is_empty_on_this_path` pins the current behaviour so that a future fix
must update the skill's limitation section in the same change.

**Recommended as M9-C.4**, ahead of the remaining three research skills, since all four will
inherit this same gap.

## 11. Decisions made

**No ADR.** Assessed against `docs/decisions/README.md`. Adding a skill is a
registration-only extension — `architecture.md` already names `biq-company-analysis` as one of
the four Layer-2B skills consuming the shared research core, so the architecture anticipated
this component and no decision was taken that constrains future work, moves an invariant or
rejects an expected option. The five design decisions in §3 are local to the skill and recorded
here.

**A decision that would need an ADR was deliberately not taken:** changing `close_retrieval`'s
signature to carry conflicts (§10). That is an owner call on a shipped API.

## 12. Architecture changes

None. `architecture.md` describes this skill's existence and its dependence on the shared
research core; both are now true rather than planned. No amendment required.

## 13. Project-plan updates

M9-C.3 scope only: the `biq-company-analysis` row moved from `PLANNED` to `COMPLETED`, and a new
`DEFERRED` row records the conflicts gap as M9-C.4. The three sibling skills and all four
commands remain `PLANNED`, untouched.

## 14. Documentation updates

This record, the skill itself, and the plan row. No reference page, architecture section or
existing record was modified.

## 15. Remaining work

1. **M9-C.4 — the conflicts gap** (§10). Recommended next, because the remaining three skills
   inherit it.
2. **The three sibling skills** — `biq-market-analysis`, `biq-competitor-analysis`,
   `biq-industry-research`. Not started. Each should follow this skill's shape.
3. **M9-D** — the four external commands, including `/company-analysis`, which is what finally
   makes this capability user-reachable.
4. **Optional, non-blocking:** a live `/retrieval-slice` run against a real company to see this
   skill's flow end to end. Not required for M9-C.3, whose tests are deterministic by design.

## 16. Git commit reference

N/A. Branch `main`, no commit created, nothing staged, nothing pushed.

---

## Company Analysis contract

**Input:** `company` (required, must be unambiguous — ask if not), `focus`
(`overview` / `developments` / `positioning` / `full`, default `full`), `window` (optional),
and optional public disambiguating terms `industry`, `geographic_market`, `period`.

**Flow:** objective → information requirements → public terms only → `open_retrieval` (gate,
Tier 0) → one `biq-research-scout` dispatch with the brief verbatim → `close_retrieval` →
normalised records → `EvidenceSet` → local tiering, freshness, support → candidate claims
(optional) → synthesis → structured analysis. Up to three retrievals for a `full` analysis, one
per intent, each dispatched exactly once.

**Output:** ten fixed sections — executive summary · company overview · recent developments ·
positioning · business indicators · risks and opportunities · evidence summary · conflicts ·
limitations · confidence. A section with no evidence says so and is not padded.

**Boundary:** no internal business data, no file or repository access, no customer names, no
transactions, no credentials. The brief is six fields and can carry none of these. Retrieved
content stays `UNTRUSTED_EXTERNAL_DATA` throughout.

**Final status: `M9-C.3 COMPLETED`.**
