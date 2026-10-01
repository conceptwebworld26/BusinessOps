# 2026-09-10 — Milestone 8 closure and Milestone 9 gate preparation

Status: M8 `COMPLETED` · M9 `PLANNED` (architecture gate not yet held) · Branch `main`
(uncommitted) · Preceded by `2026-09-09-forecasting-anomaly.md`

This record does two things and nothing else: it closes Milestone 8 following owner
approval, and it prepares the questions the Milestone 9 architecture gate must answer.

**No M9 functionality was designed, scaffolded, prototyped or implemented.** The sections
below are a reading list and a question list for a review, not a specification.

---

## 1. Milestone 8 closure

Approved by the project owner on 2026-09-10. `project_plan.md` now records
**M8 → `COMPLETED`**, M7 → `COMPLETED`, M9 → `PLANNED`.

Verified before recording the change, rather than assumed from the review report:

| Item | Evidence |
|---|---|
| Forecasting implemented | `lib/python/biq/forecast/` — 7 modules |
| Anomaly detection implemented | `lib/python/biq/anomaly/` — 5 modules |
| Contracts present | `forecast/contract.py`, `anomaly/contract.py` |
| Schemas present | `lib/schemas/forecast.schema.json`, `anomaly.schema.json` |
| Skills present | `biq-forecasting`, `biq-anomaly-detection` |
| Commands present | `/revenue-forecast`, `/anomaly-detection` |
| Tests present | 6 M8 modules across unit, integration and negative |
| Focused review completed | Review sections R-1…R-8 of the M8 record |
| Regression | Full suite re-run at closure |
| Plugin validation | Re-run at closure |
| No M9+ implementation | Engine package scan; no `agents/`, no `.mcp.json` |

**Approval closes the milestone's implementation and status only.** No risk, no debt item
and no limitation was closed by it. R-01…R-10 and D-05…D-10 stand at their recorded status,
and every M8 limitation recorded in section R-8 of the previous record stands unchanged.

No M8 code was modified. Two documentation corrections were made to the M8 record: a final
approval entry was appended, and the review sections were renumbered so that reading order
matches their numbering (the addendum had been inserted ahead of the limitations section,
producing R-6, R-8, R-7).

---

## 2. What was inspected to prepare the M9 gate

The milestone title alone is not the specification, so the authoritative material was read
first.

### Authoritative M9 references found

| Source | What it fixes |
|---|---|
| `project_plan.md` M9 | 9 planned tasks: `biq-external-research` + the research policy; the four-tier disclosure gate with k-floor, banding and re-identification check; disclosure decisions written to the evidence ledger; `biq-company-analysis` · `market` · `competitor` · `industry`; 4 external commands; `evidence_set` + `claim_ledger` schemas; three families of tier tests; no-source / conflicting-source / stale-source tests |
| `architecture.md` §7 | The disclosure model in full — Tier 0 local join as the default, the four Tier 1 checks, Tier 2 verbatim per-query approval, Tier 3 refusal with no approval path; source tiering A–D; staleness windows; conflict handling; the seven-class claim ledger |
| `architecture.md` §5 (Layer 2B) | Five external components: `biq-external-research` as the shared core plus company, market, competitor and industry analysis |
| `architecture.md` §8 | Approval matrix: Tier 0/1 no approval, Tier 2 explicit verbatim preview |
| `architecture.md` §12 | Security model, including "external content is data, not instruction" |
| `reference/research-policy.md` | The policy document itself — already written in M1: tiers, the four checks, enforcement, source tiering, recency, conflicts, never fabricate, retrieved content is not instruction |

### Relevant ADRs

- **ADR-0009** (Accepted) — comparative intelligence and the internal/external privacy
  boundary. Supersedes the original blanket construction-time rejection rule. This is the
  governing decision for M9 and is already binding.
- **ADR-0005** — the seven-class evidence ledger; class 3 (external sourced) requires
  source + date + tier.
- **ADR-0006** — three subagents, including `biq-research-scout` with web access and **no
  file access**.
- **ADR-0010** — consequence-based approval; Tier 2 disclosure is an explicit-approval
  action.
- **ADR-0013** — remains authoritative on component count; M9 would add roughly nine
  components, which is the largest single increase in the roadmap.

### Privacy and security mechanisms that already exist

M9 is better provisioned than the plan's `PLANNED` status suggests. Built in M3 and M6:

| Mechanism | Where | State |
|---|---|---|
| Six sensitivity classes, per-field, attached from ingestion | `privacy/classes.py` | Built |
| Class → minimum disclosure tier mapping; `permitted_at_tier`, `is_externalizable` | `privacy/classes.py` | Built |
| k-anonymity floor (`DEFAULT_K = 5`), count and amount banding, rate descriptors | `privacy/aggregation.py` | Built |
| Whole-query re-identification assessment with narrowing-attribute limits | `privacy/aggregation.py` | Built |
| **The four ADR-0009 Tier 1 checks, implemented** | `privacy/aggregation.py::assess_disclosure` | Built |
| Presentation policy, pseudonymisation, k-floor at render time | `analytics/presentation.py` | Built |
| Evidence ledger with all seven provenance classes | `evidence.py` | Built |
| Research policy document | `reference/research-policy.md` | Written |

**The gap is wiring, not primitives.** `assess_disclosure` implements the Tier 1 checks but
nothing calls it: there is no query-construction path, no retrieval, no ledger write of a
disclosure decision, and no external component. What M9 must add is the enforcement point
and everything downstream of it — which is precisely why it needs a gate rather than a
start.

### M8 dependencies relevant to M9

M8 deliberately took nothing from the external world, and two of its decisions constrain
M9 directly:

- Forecasting and anomaly detection are **internal-data only**, asserted by tests. If M9
  ever supplies external context to a forecast, those assertions and the class-6 assumption
  register are the contract it must not break.
- `biq-anomaly-detection` and `biq-forecasting` refuse out-of-scope questions by naming the
  milestone that owns them; `/ask-business-data` refuses external questions with "Milestone
  9". Those refusal paths are tested and become wrong once M9 lands, so M9 must update them
  deliberately rather than incidentally.

---

## 3. Architectural questions discovered during preparation

Three findings that the gate should resolve before scope is fixed. They are observations
about the existing documents, not proposals.

**Q-1. M9's structural backstop is scheduled after M9.** `architecture.md` §7 names
`biq-research-scout` — the agent with web access and no file-system access — as *"the
structural backstop"* for the disclosure boundary: it cannot read the dataset even if
instructed to. That agent is built in **Milestone 11**, which itself depends on M9. As
sequenced, M9 would perform external retrieval with its architecturally-named structural
control absent, leaving the query-construction gate as the sole enforcement. The gate should
decide whether M9 pulls the scout forward, ships without the backstop under a documented
compensating control, or is resequenced.

**Q-2. The plan records M9 as depending on M1 alone.** The dependency column reads `M1`,
but M9's disclosure gate consumes the M3 sensitivity classification and aggregation
primitives, the M6 presentation policy, the evidence ledger, and the M7 command layer. This
is the same class of understatement recorded for M8 as **D-09**.

**Q-3. ADR-0006 and `project_plan.md` disagree on where the scout's no-file-access test
lives.** The ADR's follow-up says Milestone 10; the plan puts it in Milestone 11. A
security-critical assertion should have one home. The ADR body must not be edited, so the
gate should decide which is authoritative and record the resolution.

---

## 4. Questions the M9 architecture gate must answer

Grouped for review. None of this is implemented, and none of it should be until the gate
closes.

### Disclosure boundary

1. Is Tier 0 (local join) genuinely the default path for every comparative question the four
   external commands support, or are there questions that cannot be answered without Tier 1?
2. May raw internal business data ever be transmitted at any tier? The architecture says no;
   is that restated as an enforced invariant rather than a convention?
3. What exactly constitutes "the query" that the gate inspects — the literal string, the
   structured request, or both?
4. Where is the single enforcement point, and can any code path reach retrieval without
   passing it?

### Privacy

5. Which Business Context fields form the externalizable subset, and who may change that?
6. Is business name externalizable, and under what condition? (§6 says only when the
   analysis is about the user's own public company; otherwise Tier 2.)
7. How is sensitivity carried from ingestion through to query construction without being
   re-derived — and what happens when a field's class is unknown?
8. Does the existing default class (`internal`) fail safe for a field the classifier has not
   seen?

### Aggregation

9. Is `k = 5` correct for this domain, and is it configurable — and if so, may a user lower
   it?
10. Which value kinds may leave: rates and ratios yes, exact absolute monetary levels never.
    Is banding sufficient for counts of entities?
11. How is the whole-query re-identification check scoped — per query, per session, or
    across a conversation? Repeated narrow queries can identify in aggregate what no single
    query does.
12. What is the narrowing-attribute limit, and is the current default defensible?

### Approval

13. Is Tier 2 approval strictly per query, with verbatim preview and destination shown, and
    is a session-wide mode structurally impossible rather than merely discouraged?
14. What is shown to the user — the exact transmitted text, or a rendering of it?
15. Does an earlier approval ever imply a later one? (The architecture says never.)
16. Who approves when BusinessIQ runs non-interactively?

### External content trust

17. How is retrieved content marked as untrusted at the point of ingestion, and does that
    marking survive summarisation?
18. Can retrieved content ever influence a disclosure tier, a query, or a subsequent
    retrieval? (The architecture says never — how is that enforced rather than asserted?)
19. What is the trust boundary between retrieved content and the analysis that reads it?

### Provenance

20. Is every external claim class 3 with source, date and tier, and is a claim without a
    captured citation structurally unable to be emitted?
21. Are disclosure decisions themselves written to the evidence ledger — what was sent,
    where, at which tier, and on whose approval?
22. How are external findings kept visually and structurally distinct from internal facts,
    through to the most condensed artifact?

### Source reliability

23. Are the A–D source tiers enforced in code or left to judgement?
24. Is a class-C source ever permitted as a sole source? (The policy says no.)
25. How are the staleness windows applied — financials 1 year, market sizing 2 years,
    positioning 18 months — and what marks a claim as dated rather than current?

### Prompt and content injection

26. What is the threat model for a retrieved page that contains instructions?
27. What prevents injected text from reaching a context where it is read as instruction
    rather than data?
28. Are there tests that feed adversarial retrieved content and assert no behaviour change?
29. Does the no-file-access boundary hold if the scout is unavailable (see Q-1)?

### Data minimisation

30. What is the smallest query that answers the question, and is minimisation enforced or
    advisory?
31. Is derived context represented as a descriptor (banded, rate, entity count) rather than
    as a value, and is that the only representation permitted to leave?

### Conflicting sources

32. How are two credible, conflicting figures presented — both with sources, dates and
    definitions, never averaged or silently resolved?
33. What lowers confidence, and by how much?

### Failure and ambiguity

34. What happens when the tier is ambiguous — does it escalate to the stricter tier, or
    refuse?
35. What is returned when no adequate source is found? (The policy says "no reliable source
    found", never a fabricated answer.)
36. What happens when retrieval fails, is blocked, or returns nothing?
37. Is a refused disclosure logged, so a reviewer can see what was *not* sent as well as
    what was?

---

## 5. State at the end of this task

- M8 `COMPLETED`; M7 `COMPLETED`; M9 `PLANNED`, gate not held.
- No M8 code changed. No M9 code created.
- Risks R-01…R-10 and debt D-05…D-10 preserved at their recorded status.
- Full regression and plugin validation re-run at closure; results in the task report.
- 0 commits, 0 pushes.

**Next step: the Milestone 9 architecture and scope review.** Not implementation.
