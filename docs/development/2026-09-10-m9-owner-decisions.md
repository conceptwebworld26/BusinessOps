# 2026-09-10 — Milestone 9 owner decisions, security sequencing and governance lock

Status: M8 `COMPLETED` · M9 `PLANNED`, foundations locked, **implementation not started** ·
Branch `main` (uncommitted) · Preceded by `2026-09-10-m9-architecture-review.md`

This step locked the owner decisions from the M9 architecture review into the repository and
closed the four enforcement gaps that review found by executing the code. **No external
research, disclosure gate, retrieval, skill, command or schema was implemented.**

---

## 1. Decisions locked

| # | Decision | Where it now lives |
|---|---|---|
| Q-1 | `biq-research-scout` moves from M11 into M9. Only the scout moves | ADR-0014; `agents/biq-research-scout.md`; `project_plan.md` M9/M11 |
| Q-2 | M9 depends on M1, M3, M5, M6, M7; M8 is a soft precedent | `project_plan.md` milestone summary + M9 section |
| Q-3 | The no-file-access test ships with the scout, not with a milestone number | ADR-0014; `tests/unit/test_research_scout_boundary.py` |
| — | Re-identification accumulates across the active research operation | `privacy/aggregation.py::DisclosureAccumulator` |
| — | k ≥ 5 is a hard minimum; no caller or configuration may lower it | `privacy/aggregation.py::resolve_k_floor` |
| F-2/F-3 | Class→tier joined into `assess_disclosure`; one authoritative decision | `privacy/aggregation.py::assess_disclosure` |
| F-1 | Class-3 claims are structurally un-emittable without provenance | `evidence.py::Claim` |
| F-4 | Aggregate sensitivity is explicit or derived, never assumed | `privacy/aggregation.py::AggregateDescriptor` |
| — | The four external commands are named | `project_plan.md` M9 |
| — | Regulatory developments and recent-company-developments are out of scope | `project_plan.md` M9 |

Every one of these tightens the boundary. None loosens it.

---

## 2. Cross-query re-identification — the model

ADR-0009 requires the re-identification check to evaluate a query **as a whole**, because
industry + micro-geography + a narrow revenue band can identify a company even when each
part looks harmless. The owner decision extends the same reasoning one level up: three
queries carrying two narrowing attributes each have disclosed six, and a reader — or an
attacker — sees them together.

**What is accumulated.** Only the *names* of narrowing attributes that were actually
disclosed, filtered to `NARROWING_ATTRIBUTES`, plus a count of permitted disclosures. No
values, no query text, no results, no identifiers, no business data. `as_dict()` returns
exactly three keys: `operation`, `attributes`, `disclosures`.

**How it is represented.** A `DisclosureAccumulator` holding a set of attribute names.
Read back sorted, always, so decisions and their stated reasons are byte-identical across
runs.

**When it starts.** One accumulator per research operation, created by the caller when the
operation begins. Absent one, `assess_disclosure` behaves exactly as before — accumulation
is opt-in per operation, so no existing call site changes meaning.

**When it resets.** At `reset()`, or when the operation ends and the object is discarded. It
is **in-memory only**: nothing writes it to disk, and it is deliberately not a durable
profile carried across unrelated conversations. That constraint is asserted by a test that
checks the record contains nothing but attribute names.

**How queries are evaluated.** `assess_disclosure` judges
`accumulated.attributes ∪ query_attributes` rather than the query alone. A refused query
records nothing — it disclosed nothing, so counting it would tighten the gate on the basis
of information that never left the machine.

**Worked example, asserted as a test:**

| Query | Attributes | Verdict | Accumulated after |
|---|---|---|---|
| A | `industry` | permitted | `industry` |
| B | `region` | permitted | `industry, region` |
| C | `size_band` | permitted | `industry, region, size_band` |
| D | `product_category` | **refused** | unchanged |

Query D passes in isolation and is refused in sequence, which is precisely the requirement.
The refusal states why: *"Judged against the 3 attribute(s) already disclosed in this
research operation, not this query alone."*

---

## 3. One authoritative disclosure decision

`assess_disclosure` previously applied the four Tier-1 checks and then returned `tier = 1`
for anything that passed — without asking whether the data's *class* permits Tier 1 at all.
A `restricted` aggregate, which `TIER_FOR_CLASS` says requires Tier 2, came back
`permitted=True, tier=1`. Meanwhile `permitted_at_tier` existed, was tested, and was called
by nothing in the library.

The two halves are now joined inside `assess_disclosure`, in this order:

1. sensitivity resolved at all? (else refuse — F-4)
2. externalizable at any tier? (else refuse — Tier 3)
3. **class permitted at the tier being asked about?** (else refuse — F-2/F-3)
4. aggregation floor, with the hard k minimum applied
5. banded, not exact
6. whole-query re-identification, including accumulated state

and the returned tier follows the data's class — `0` for `public`, `1` for `derived_safe` —
never the mere fact that the checks passed.

Verified: `public`→tier 0; `derived_safe`→tier 1; `internal`, `conditional` and `restricted`
→ refused with `class_not_permitted_at_tier`; `never` → refused before any other check. A
test asserts the decision can never contradict `permitted_at_tier`.

**There is no second disclosure decision.** The M9 gate will orchestrate inputs to this
function — query text, destination, approval state — but must not re-implement the policy.

---

## 4. k-floor

`DEFAULT_K = 5` and `MINIMUM_K = 5`. `resolve_k_floor()` returns the larger of the request
and the minimum, so a floor may be raised and never lowered; non-numeric and negative
requests fall back to 5. A configurable floor that can be configured downward is not a
floor.

Asserted: k=5 passes when everything else passes; k=4 is refused; every attempt to lower the
floor via the `k_floor` argument still refuses a 4-entity aggregate; an unknown entity count
is refused.

---

## 5. Class-3 provenance

An external claim now requires `source`, `citation`, `source_date` and `source_tier`, and
the tier must be A, B or C — tier D (unattributable, AI-generated, content farms) is
excluded outright, because an excluded source is not a weak citation but no citation at all.

`Claim("Industry churn benchmark is 5–7%.", EXTERNAL_SOURCED)` now raises `LedgerError`.
`reference/research-policy.md` said "a citation never captured cannot be emitted"; that was
prose until this rule existed. Making the object unconstructible is what turns the sentence
into a guarantee — there is no path by which an uncited external figure reaches a report,
because it cannot be built.

Classes 1, 4 and 7 are unchanged, and a test asserts it. The seven-class model is untouched;
this is one more rule inside it, not a parallel evidence system.

---

## 6. Aggregate sensitivity

`AggregateDescriptor.source_sensitivity` defaulted to `derived_safe` — more permissive than
the project-wide default of `internal`, so a caller who forgot to classify an aggregate got
one that passed the Tier-3 check. The default is now `UNRESOLVED`, which no tier admits.

`AggregateDescriptor.from_fields(..., field_classes)` derives sensitivity with the existing
`most_sensitive()`, so a derived statistic is exactly as sensitive as the most sensitive
field behind it, and an empty classification resolves to `internal` rather than to anything
convenient. The shipped helpers (`rate_descriptor`, `banded_amount_descriptor`) already
classified explicitly and are unchanged.

---

## 7. Research scout — security contract

`agents/biq-research-scout.md`, tool grant **`WebSearch, WebFetch` and nothing else**.

The scout may perform external research and receives only a query that has already passed
the disclosure gate. It has no file-system, repository, business-data or secrets access, no
arbitrary tools, and no ability to spawn another agent. It cannot invoke tools from
retrieved content, cannot raise or modify a disclosure tier, and cannot reach raw internal
business data — not by policy, but because the tools that would let it do so are not
granted.

Retrieved content is **data, not instruction**. Text inside a retrieved page instructing the
scout to reveal data, call a tool, run a second search, change the query, ignore its rules
or alter its output format is content to be reported on, never an instruction to follow.

`tests/unit/test_research_scout_boundary.py` (17 tests) asserts the *declared tool grant*
rather than behaviour, because a future grant of `Read` would silently convert a structural
guarantee back into a written policy and nothing else in the suite would notice.

**No retrieval was implemented.** The agent definition establishes the capability boundary;
the thing that uses it is M9 implementation.

---

## 8. Scope boundaries held

M9 includes company, market, competitor and industry research, reached by
`/company-analysis`, `/market-analysis`, `/competitor-analysis` and `/industry-research`,
mapping to the four `biq-*-analysis` skills.

A generic **regulatory-developments** capability is **not** in scope and was not added. A
separate **recent-company-developments** command or skill is **not** in scope and was not
added; current company information retrieved during company analysis stays inside the
approved company-research scope under the same source, freshness, provenance and disclosure
rules. SWOT, strategy, decision support and executive reporting remain M10.

---

## 9. R-09

No component was merged and no description shortened. The scout adds one always-on
component (~80 tokens by ADR-0006's measurement). ADR-0013 remains authoritative: exceeding
the self-imposed target breaks nothing, and the response to overlap is a merge justified by
**measured description overlap**, never by a token count.

The architecture review's concern stands and is carried forward to M9 implementation: the
four external analysis skills share one shape — research an external subject and report —
differing only in subject, with `biq-external-research` overlapping all four by
construction. Measure with the tier-scoped Jaccard method used in the M8 review, with a
threshold agreed before descriptions are written.

---

## 10. State

Foundations locked; M9 implementation not started. Full suite green. 0 commits, 0 pushes.
