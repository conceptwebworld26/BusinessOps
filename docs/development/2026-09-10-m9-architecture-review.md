# 2026-09-10 — Milestone 9 architecture & scope review

Status: review only · M8 `COMPLETED` · M9 `PLANNED`, gate **not** closed · Branch `main`
(uncommitted) · Preceded by `2026-09-10-m8-closure-m9-gate-preparation.md`

**No M9 functionality was implemented, scaffolded or prototyped.** This document records
what the repository actually says, what it actually does, and what the owner must decide
before M9 implementation begins. Every finding below was verified against the repository,
not carried over from a previous report.

---

## 1. Authoritative M9 scope

Sources, in order of authority: `architecture.md` (what the system *is*) → the ADRs
(why) → `project_plan.md` (what is done/next) → `reference/` (policy).

### In M9

| Capability | Authority |
|---|---|
| `biq-external-research` — shared core: query construction, the disclosure gate, citation capture | `architecture.md` §5 Layer 2B; `project_plan.md` M9 |
| Four-tier disclosure gate with k-floor, banding, re-identification check | ADR-0009; `architecture.md` §7; plan M9 |
| Disclosure decisions written to the evidence ledger | ADR-0009 Enforcement; plan M9 |
| `biq-company-analysis`, `biq-market-analysis`, `biq-competitor-analysis`, `biq-industry-research` | `architecture.md` §5 Layer 2B; plan M9 |
| 4 external commands | plan M9 (**names not enumerated anywhere** — see Discrepancy 4) |
| `evidence_set` + `claim_ledger` schemas | plan M9; ADR-0005 follow-up |
| Source tiering A–D, staleness windows, conflict handling | `architecture.md` §7; `reference/research-policy.md` |
| Tier tests, no-source / conflicting-source / stale-source tests | plan M9; ADR-0009 follow-up |

### Not in M9

SWOT, strategy, decision support, executive reporting (M10 — `architecture.md` §5 Layer 3);
subagents including `biq-research-scout` (M11 — unless Q-1 moves it); MCP connectors (M12);
routing evals (M13). "Regulatory/business developments" and "recent company developments"
appear in **no** authoritative source and are **not** M9 scope; they would fold into
`biq-company-analysis` only if the owner says so.

### Already built and to be reused

`privacy/classes.py` (six classes, class→tier map), `privacy/aggregation.py` (k-floor,
banding, rate descriptors, re-identification, `assess_disclosure`),
`context/privacy.py` (Business Context externalization, schema-driven), `evidence.py`
(seven classes, ledger), `analytics/presentation.py` (pseudonymisation, k-floor at render),
`commands/` (registry, runner, sections), `runtime/tiers.py` (the consent pattern).

### Discrepancies found — not resolved here

1. **ADR milestone numbers predate the Revision-2 renumbering.** ADR-0005 says the claim
   and evidence schemas "land in Milestone 8"; ADR-0009 says the gate lands "with the
   research layer (M8)"; ADR-0006 says the scout test is in "Milestone 10". The plan places
   these in M9, M9 and M11. Matching by *content* rather than number shows a consistent
   off-by-one after M1, which is exactly what inserting the vertical slice as M2 (13 → 14
   milestones) produces. **These are stale numbers, not disagreements.** ADR bodies must not
   be edited; the mapping should be recorded once, authoritatively.
2. **ADR-0006 and ADR-0009 weight the scout differently.** ADR-0006 calls the tool split "a
   useful *side effect*"; ADR-0009 calls it "what makes this safe in practice" and claims it
   makes Tier 3 "structurally unreachable". `architecture.md` §7 calls it "the structural
   backstop". ADR-0009 is later and governs. See Q-1.
3. **`project_plan.md` records M9 as depending on M1 alone.** See Q-2.
4. **The four external command names are enumerated nowhere.** `architecture.md` states a
   count of 17 commands and names none (open debt **D-06**); the plan says "4 external
   commands" without names. M9 cannot be accepted against a specification that does not name
   its deliverables.

---

## 2. Q-1 — research-scout sequencing

### What the scout actually protects

`biq-research-scout` is granted **web tools and no file access** (`architecture.md` §10).
The protection is not that it behaves well; it is that the context performing retrieval
*cannot read the dataset at all*. ADR-0006: "Internal business data therefore cannot reach a
research query by accident — the agent that runs the query has no way to read it."

### Is it mandatory or defence-in-depth?

The repository answers this three times, and the answer strengthens over time:

- ADR-0006 (Consequences): "the internal/external boundary is enforced by capability, not by
  instruction".
- ADR-0009 (Enforcement): "The structural backstop from ADR-0006 is unchanged and **is what
  makes this safe in practice**"; (Consequences) "the agent tool-split makes Tier 3
  **structurally unreachable** rather than merely forbidden".
- `architecture.md` §10: "The tool split above is what makes the Tier-3 privacy boundary
  **structural rather than advisory**."
- `README.md` §Security, shipped to users: "**Structural, not just promised:** the agent that
  performs web research has no file-system access and cannot read your data even if
  instructed to."

So the scout is not decoration. It is one of **two** enforcement mechanisms, and it is the
one that survives a failure of the other. The query-construction gate prevents a *correct*
implementation from sending internal data; the scout prevents *any* implementation, correct
or not, from reading it in the first place.

### Can M9 operate without it?

Mechanically yes — retrieval would run in the main thread using the host's web tools. But
the main thread holds file access and web access **simultaneously**. In that configuration:

- the boundary reverts from structural to advisory, contradicting three architecture
  statements;
- ADR-0009's claim that Tier 3 is "structurally unreachable" becomes false;
- the README's security promise to users becomes false.

A compensating control cannot restore the property. Capability separation is a statement
about what a context *can* do; no code or instruction inside a context that holds both
capabilities can re-create it. A gate can be the only *sanctioned* path to retrieval, but
nothing structural stops the sanctioned path being bypassed, because the same context can
read a file and call a web tool directly.

### Where is disclosure enforced today?

Nowhere. `assess_disclosure` exists and is correct for what it does, but **nothing calls
it** (verified: no caller in `lib/`), there is no query-construction path, no destination
concept, no approval object, and no ledger write of a disclosure decision.

### Alternatives

| Option | Preserves structural boundary | Cost |
|---|---|---|
| **A. Pull `biq-research-scout` forward into M9** | Yes | One agent (~80 tokens always-on), its tool grant, and the no-file-access test move from M11 to M9. M11 keeps the other two agents. |
| **B. M9 compensating control** (gate as sole sanctioned retrieval path, main-thread retrieval) | **No** — advisory only | Cheapest to build; makes three architecture statements and one README promise false until M11 |
| **C. Resequence M9 after M11** | Yes | Largest schedule change; M11 currently depends on M9, so the dependency would have to be inverted or split |
| **D. Split M11** — scout into M9, profiler and verifier stay | Yes | Same as A, expressed as a plan edit rather than a scope edit |

A and D are the same technical outcome; they differ only in how the plan records it.

**Recommendation is in the final report.** This is an owner decision.

### Dependency impact of moving the scout

`project_plan.md` M11 depends on "M3, M9". Moving the scout into M9 leaves M11 with
`biq-data-profiler` (needs M3) and `biq-analysis-verifier` (needs the engine and M10's
consumers). Neither of the two remaining agents depends on M9, so M11's dependency would
narrow, not widen. No M10 dependency changes: M10 consumes M7/M8/M9 outputs, not agents.

### Governance

Moving a milestone's contents is a project-plan decision. But ADR-0006's decision text
enumerates three agents *and their milestone*, and ADR-0009 rests its safety argument on the
scout existing when retrieval does. A new ADR recording "the scout ships with the first
milestone that retrieves" is the cleaner instrument, because it captures the *rule* rather
than a one-off schedule edit. Proposed in section 8 below.

---

## 3. Q-2 — M9 dependency understatement

**Stated:** `project_plan.md` milestone summary, row 9 — depends on **M1**.

**Actual**, verified by tracing what M9's deliverables consume:

| Foundation | What M9 needs from it | Hard? |
|---|---|---|
| M1 | Business Context, `x-privacy` schema annotations, config precedence, runtime consent pattern | Hard |
| M3 | Six sensitivity classes, class→tier map, k-floor, banding, rate descriptors, re-identification, `assess_disclosure`, dataset field classification | **Hard — security-critical** |
| M5 | KPI results are the internal side of every comparative question | Hard |
| M6 | Evidence ledger integration, materiality, presentation policy, `AnalysisSet` contract | Hard |
| M7 | Command registry, runner, section renderer — the four external commands are M7-pattern commands | Hard |
| M8 | Precedent only: the `ForecastSet`/`AnomalySet` subclass pattern for a new result type; M8's "Milestone 9" refusal strings must be updated when M9 lands | Soft |
| M11 | `biq-research-scout` — see Q-1 | **Security-critical, unresolved** |

**Missing from the plan:** M3, M5, M6, M7 (and, pending Q-1, M11).

This is the third instance of the same pattern (D-09 recorded it for M8, D-01/D-02/D-06 for
enumeration gaps). Recommendation: correct the dependency column before M9 implementation,
because the M9 gate's whole purpose is to establish what must be true first — and a
dependency row that omits the security foundation is actively misleading.

Not corrected here: `project_plan.md` is authoritative and the review task directs that
recommended changes be recorded rather than applied.

---

## 4. Q-3 — scout test sequencing

**ADR-0006, Follow-up required:** "Milestone 10 includes a test asserting
`biq-research-scout` has no file-access tools."

**`project_plan.md` M11:** "`biq-data-profiler` · `biq-research-scout` ·
`biq-analysis-verifier`, listed explicitly in `plugin.json`, each with a minimal tool grant,
**plus the test asserting `biq-research-scout` has no file access**."

**Is it a real discrepancy?** No. Both refer to the same milestone under different numbering.
Inserting the vertical slice as M2 shifted every later milestone by one, so ADR-0006's
"Milestone 10" is the current M11 — and the plan's M11 contains that exact test, word for
word. The same off-by-one explains ADR-0005's "Milestone 8" (schemas → current M9) and
ADR-0009's "M8" (gate → current M9) and "(M2)" for ingestion-time classification (→ current
M3).

**But the substantive question survives the numbering.** Whichever number it carries, the
test currently sits in the milestone *after* the one that first retrieves externally. A test
asserting that the retrieval agent cannot read files belongs in the milestone that first
retrieves. If Q-1 resolves by moving the scout to M9, this test must move with it — it is
the test that proves the control exists.

**Recommendation:** treat Q-3 as resolved (stale numbering, no conflict), and bind the test's
location to the scout's location rather than to a fixed milestone number.

---

## 5. Disclosure boundary — traced, with enforcement points

```
internal data → sensitivity classification → user request → query construction
   → DISCLOSURE DECISION → retrieval → external content → claim ledger → presentation
```

| Stage | Enforcement today | Gap for M9 |
|---|---|---|
| Sensitivity classification | **Built.** `privacy/sensitivity.py` classifies dataset fields; `context/privacy.py` reads `x-privacy` from the Business Context schema. Unannotated ⇒ `internal` (fail-safe). Derived values inherit via `most_sensitive`. | None |
| Query construction | **Absent.** No module builds a query. | Build it; it is the only place the gate can run |
| Disclosure decision | **Partial.** `assess_disclosure` implements the four Tier-1 checks for **one aggregate**. No whole-query gate, no destination, no approval state, no ledger write. | See findings F-1…F-4 |
| Retrieval | **Absent.** Depends on Q-1 | — |
| External content | Policy only (`reference/research-policy.md`); no code | Trust boundary must be technical |
| Claim ledger | **Built but unenforced for class 3.** See F-1 | Enforce |
| Presentation | **Built.** Class 5–7 render distinctly from 1–4; `SOURCED` label exists for class 3 | None |

### Findings verified by execution

**F-1 — an external claim with no source, no date and no tier is accepted.** The `Claim`
constructor enforces provenance for class 1 (`source`), class 4 (`formula`) and class 7 (all
six fields) but has **no rule for class 3**. Verified: a bare
`Claim("Industry churn benchmark is 5–7%.", EXTERNAL_SOURCED)` constructs successfully.
`reference/research-policy.md` says "Citations are captured at retrieval… A citation never
captured cannot be emitted" — that guarantee is currently prose, not code. M9 must add the
class-3 rule (source + publication/access date + source tier) to the existing validator; this
is an extension of the existing system, not a parallel one.

**F-2 — `assess_disclosure` grants Tier 1 without consulting the class→tier map.** It ends
with `tier = 1 if permitted else None`, special-casing only `PUBLIC` down to 0. It never
calls `permitted_at_tier`. Verified: a descriptor whose `source_sensitivity` is `restricted`
— which `TIER_FOR_CLASS` says requires **Tier 2** — returns `permitted=True, tier=1`. The
function's docstring scopes it to "the four Tier-1 checks", so this is best read as a
**composition gap**: the class→tier rule and the four checks are two halves of one decision
and nothing currently joins them. The risk is concrete — a naive M9 caller that treats
`assessment.tier` as authorization will under-classify internal and restricted material.

**F-3 — `permitted_at_tier` and `required_tier` are dead code in the library.** Verified by
search: called only from `tests/unit/test_engine_m3.py`. The rule exists, is tested, and is
wired to nothing.

**F-4 — `AggregateDescriptor.source_sensitivity` defaults to `derived_safe`.** The
project-wide default is `internal` (`classes.DEFAULT_CLASS`), chosen because "defaulting open
would make every new column a potential leak". The descriptor's constructor default is more
permissive than that, so a caller who omits sensitivity gets a value that passes the Tier-3
check. M9's gate should require sensitivity to be supplied and derive it with
`most_sensitive()` over the source columns rather than accept a default.

**F-5 — the re-identification check is stateless per query.** `assess_reidentification`
evaluates one attribute set. Nothing accumulates attributes across queries in a session, so
three separate queries each carrying two narrowing attributes pass individually while jointly
narrowing further than one blocked query would. ADR-0009 anticipates whole-*query* evaluation
and does not address the sequence. This is a genuine open question for the gate, not a defect
in M3.

---

## 6. Disclosure gate — required shape

A **disclosure request** is not a string. The gate must inspect, as one object: the proposed
query text verbatim; every descriptor it embeds with that descriptor's derived sensitivity,
value kind and entity count; the full attribute set for the re-identification check; the
destination/provider; the purpose; and the approval state.

The decision model already exists implicitly in ADR-0009 and should not be reinvented — four
tiers producing three outcomes:

| Outcome | When |
|---|---|
| `ALLOW` | Tier 0 (public terms only) or Tier 1 (all four checks pass **and** every field's class permits Tier 1) |
| `ALLOW_WITH_APPROVAL` | Tier 2 — verbatim text and destination shown, single-use |
| `REFUSE` | Tier 3 material, or ambiguity that cannot be resolved downward |

Required properties: exactly one enforcement point; no retrieval path that does not traverse
it; the decision *and the transmitted text* written to the ledger, including refusals; and
ambiguity resolving to the **stricter** tier, never the looser one. The existing
`ConsentRequiredError` / `consent_request()` pattern in `runtime/tiers.py` is the precedent
for Tier 2 — refuse by default, raise a typed error carrying the full disclosure, proceed
only on explicit grant — and reusing its shape avoids a second approval system.

---

## 7. Components, acceptance criteria, tests, R-09

These are recorded in the task report accompanying this record rather than duplicated here:
the nine proposed components with their security roles; 40 numbered acceptance criteria; the
24-case adversarial test plan; and the R-09 projection (M9 is the first milestone at which
the **measured** always-on cost crosses the self-imposed 3,000-token target — projected
~3,393 across 24 components, 113% of target, at an unchanged ~141 tokens per component).

Two points belong in the permanent record:

- Per ADR-0013, exceeding the budget "breaks nothing"; the prescribed response is to merge
  components whose **descriptions overlap**, never to truncate. So the M9 gate should decide
  *in advance* what evidence would justify a merge, and the deciding evidence is
  discriminability, not the token count.
- The four M9 analysis skills are the highest routing-overlap risk in the architecture:
  company / market / competitor / industry analysis share a single shape — research an
  external subject and report — differing only in subject, with `biq-external-research`
  overlapping all four by construction. The M8 review's method (Jaccard overlap of
  description content words, measured within each competing tier) should be run during M9
  implementation with a threshold agreed beforehand.

---

## 8. Governance recommendations — proposed, not applied

**Proposed new ADR — "The retrieval agent ships with the first milestone that retrieves."**
*Problem:* ADR-0009 rests its safety argument on a structural control delivered in a later
milestone than the one that first performs retrieval. *Decision required:* whether
capability separation is a precondition of external retrieval or a later hardening step.
*Alternatives:* pull the scout forward; compensating control; resequence. *Consequences:*
binds the scout and its no-file-access test to retrieval rather than to a milestone number,
so the question cannot recur if the roadmap is renumbered again.

**Project-plan corrections (owner approval required):** M9 dependencies M1 → M1, M3, M5, M6,
M7 (+M11 pending Q-1); enumerate the four external command names (closes D-06 for M9);
record the ADR↔plan milestone-number mapping once.

**`architecture.md`:** no change required. Every M9 statement it makes is internally
consistent; the gaps are in implementation, not specification.

**ADR bodies:** unchanged, as required.

---

## 9. State

M8 `COMPLETED`; M9 `PLANNED`, gate open. No implementation, no scaffolding, no dependency
installed. One file created: this one. 0 commits, 0 pushes.
