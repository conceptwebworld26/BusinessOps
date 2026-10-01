# ADR-0033 — The Executive Report contract: an assembly of existing artifacts over one synthesis set, authoring nothing

**Date:** 2026-09-16
**Status:** Accepted
**Deciders:** Project owner (M10.3.4 brief), recorded in M10.3.4 (contract and architecture review, decision only)
**Relates to:** ADR-0002 (figures come from code), ADR-0005 (seven classes), ADR-0010 (approval),
ADR-0012 (placement), ADR-0022 (synthesis contract), ADR-0023 (internal footing), ADR-0030 (SWOT),
ADR-0031 (recommendation contract), ADR-0032 (Decision Support). No accepted ADR is amended.

## Context

`architecture.md` §4 has listed `biq-executive-report` since Revision 1 as the Layer-3 capability that
"assembles; performs no fresh analysis", with `biq-report-composer`'s judgement merged into it and its
rendering mechanics into the engine. Nothing else defines it. What the repository did say before this
review:

- **`project_plan.md`, "M10.3.4 onward · PLANNED":** `biq-executive-report` + `/executive-report`;
  "Reads the M10.1 representation and may assemble `StrategyResult`s and `DecisionResult`s
  (ADR-0031, ADR-0032)."
- **ADR-0022:** all four M10 capabilities read one synthesis representation; "let each M10 capability
  read the upstream objects directly" was **rejected**, because it puts the comparability rule in four
  places. The executive summary is named as "the most condensed and most-forwarded artifact in the
  system, and therefore the worst place for a provenance failure to surface."
- **ADR-0031 / `architecture.md` §7:** Executive Report "may assemble recommendation records but never
  authors, edits or re-grades one".
- **ADR-0032 §14:** Executive Report may consume `DecisionResult`s, draft or final with the lifecycle
  shown; it never authors, edits, re-grades, reorders by importance or drops a part, record,
  preference, divergence, confidence, conflict, limitation or caveat; whether it requires `final`
  packages is its own milestone's decision.
- **`architecture.md` §10:** the M11 `biq-analysis-verifier` runs before `/executive-report` finalises;
  ADR-0032 §13 defines "finalise" as moving a draft to `final`.
- **ADR-0010 / `CLAUDE.md` §9:** executive reports and scorecards held in conversation or the
  scratchpad are draft generation needing no approval; a new file in `./businessiq-output/` needs none,
  path stated; overwriting, exporting and sending need explicit per-action approval.
- **`reference/output-standards.md`:** the KPI scorecard shape (metric · current · prior · change ·
  change % · materiality flag · confidence), the forecast table, the recommendation list and the
  decision package; actual vs forecast and evidence vs interpretation must be distinguishable; every
  report states its basis; a quality warning precedes the numbers.
- **`lib/python/biq/render/executive.py`:** the Milestone 2 "Business Health Snapshot", explicitly "not
  the full executive-report skill (M10)", embedded whole by `/business-health`.

Inspection of the code established what can reach a strict `SynthesisSet` today (probed read-only on
the shipped synthetic demo file):

| Artifact | Enters the set through | Probe |
|---|---|---|
| Internal findings (`AnalysisSet`) | `from_analysis_set()` / `commands.internal_statements()` | `FACT`/`CALCULATION`, engine-footed |
| KPIs (`KPIResult`) | `from_kpi_result()` | 9 statements from `/business-health`; unavailable KPIs recorded as `kpi.unavailable` limitations; materiality not assessed (`None`) |
| Anomalies (`AnomalySet`) | `internal_statements(…, ORIGIN_ANOMALY, …)` | 11 `CALCULATION` statements, `supported`, material |
| External research (`EvidenceSet`) | `register_external()` + `sourced_statement()` / `footed_statement()` | `SOURCED`, untrusted |
| Comparisons | `commands.local_join()` | ADR-0029 |
| Forecasts (`ForecastSet`) | **nothing** | `from_analysis_set` refuses the class-6 `ASSUMPTION` findings; `synthesis.assumption()` records text with provenance `unavailable`, not linked to the forecast |

The synthesis layer anticipates forecasts — `ORIGIN_FORECAST`, provenance kind `P_FORECAST`,
`register_analysis()` accepting a `ForecastSet`, reason code `forecast_instability` — but no translator
produces a forecast-footed statement, and none decides how one is graded (under current grading an
`ASSUMPTION` with a resolvable internal reference would read `supported` / `HIGH`).

SWOT's `build()` returns a plain record with no digest or object binding. `StrategyResult` and
`DecisionResult` are objects bound to the set object and its SHA-256 digest. Business Context carries
`analysis.kpi_overrides.<id>.target`, but no engine consumes it and it does not reach resolved
configuration.

## Problem

Define what Executive Report produces, from what, and under which existing rules — precisely enough to
implement and test — without a second synthesis layer, a second recommendation contract, a second
confidence or materiality system, a scoring framework, direct reads of upstream engines, or any change
to ADR-0022, ADR-0030, ADR-0031 or ADR-0032.

## Options considered

### Option A — Executive Report reads the upstream engine objects directly

`CommandResult`, `KPIResult`, `ForecastSet`, `AnomalySet`, `EvidenceSet`, plus the Layer-3 results.
Rich, and forecasts would be available today. **Rejected:** it is the alternative ADR-0022 already
rejected — a fifth reader of upstream objects, a second place provenance, comparability and
materiality are interpreted, and a report whose statements are not the statements the other three
capabilities grounded.

### Option B — Executive Report is a free-form narrative skill over whatever was produced

Readable. **Rejected:** unsupported executive prose is exactly the provenance failure ADR-0022 names,
and nothing could check it.

### Option C — Executive Report assembles one synthesis set and the Layer-3 results bound to it

Every statement shown is a statement in one genuine strict set; SWOT, Strategy and Decision Support
appear whole and only when bound to that same set; the report authors no sentence of analysis.
Forecasts are unavailable until the synthesis layer can carry them. **Chosen.**

## Decision

**Executive Report produces an `ExecutiveReportResult`: a draft, fixed-section report held beside one
genuine strict `SynthesisSet`, assembling that set's statements and the SWOT, Strategy and Decision
Support results bound to it. It authors no analysis, no recommendation and no summary prose; every
business statement it shows is a synthesis statement, a class-7 record or a decision-package part,
shown verbatim with its own provenance, confidence and materiality. Every result before M11 is a
`draft`.**

It is not a second synthesis engine, a replacement for Strategy or Decision Support, a research,
forecasting or anomaly engine, a scoring or ranking engine, or an execution system. `/business-health`
and the Milestone 2 snapshot are unchanged and separate.

### 1. Input contract

| Input | Status | Rule |
|---|---|---|
| Genuine strict `SynthesisSet` | **Required, exactly one** | `synthesis/grounding.py` identity rules: `type(...) is SynthesisSet`, `require_dimension_provenance=True`, non-empty, every item graded. Its declared `quality_grade` must not be `CRITICAL` |
| Request (framing) | **Required**, closed | Fields in §9; every one optional except the record itself; unknown fields refused |
| `StrategyResult` | Optional, at most one | The object `strategy.build()` produced; `is_bound_to(synthesis)` for this set object |
| SWOT result | Optional, at most one | The record `swot.build()` returned. Accepted only if `swot.build(synthesis, placements)` over the placements it contains reproduces it exactly (deterministic serialisation equal); otherwise refused |
| `DecisionResult` | Optional, zero or more | Objects `decision_support.build()` produced, each `is_bound_to(synthesis)`; no two identical; where a package was built with a `StrategyResult` and a `StrategyResult` is also supplied, they must be the same object |
| Resolved configuration | Optional | Read only to state which materiality thresholds applied and their layer (basis line) |
| `AnalysisSet`, `KPIResult`, `AnomalySet`, `ForecastSet`, `EvidenceSet`, `CommandResult` | **Not direct inputs** | They reach the report only as statements and registered objects of the set (ADR-0022). A serialised copy of any artifact is refused |
| Business Context | Framing only | Through the set's `subject`, `business_model`, `currency`, and the request's framing fields; never evidence |

"Optional" means *may be absent*. **An optional input that is supplied and invalid refuses the whole
report**; it is never silently omitted.

### 2. Evidence versus presentation

- **Evidence** is only what the set holds: statements resolved by id through `grounding`, with their
  kind, class, origin, domain, trust, support, confidence and reasons, materiality, conflicts, caveats,
  limitations and `chain()`. Class-7 records and decision-package parts are shown as what they are —
  owned by their issuer — never as evidence.
- **Presentation** is everything the report adds: the fixed section structure, grouping, labels, fixed
  engine-owned sentences (lifecycle note, human-decision statement, order note, empty states),
  cross-references by id, structural counts about the report itself, and locale formatting applied
  once at rendering (`reference/output-standards.md`).
- **The report writes no sentence of analysis.** No summary prose, no "what this means", no causal
  explanation, no evaluative label. There is therefore no authored text for the ADR-0031 figure rule to
  check: every figure shown is a statement's own text or field, or a record's or part's own text.
- User framing (§9) is stored verbatim with `origin: "user"` and is never evidence, never a statement,
  never transmitted.

### 3. Sections — fixed order, always present

Every section is always present. An optional section that has nothing to show carries a `status` and a
fixed reason rather than disappearing. `status` is one of `included`, `empty` (the input exists and
holds nothing — for example a `StrategyResult` whose own empty state applies), `not_supplied` (the
optional input was not given) or `not_available` (the set holds no statement of that kind).

| # | Section | Required content | May be empty? | Owns semantics? |
|---|---|---|---|---|
| 1 | `reporting_frame` | Lifecycle and verification label; the quality grade, with a `WARNING` stated **before** any figure; subject, business model, currency, as-of; the user's reporting period, audience, objective, questions and constraints as framing (not stated → "not stated"); registered datasets and external evidence sets by label; materiality thresholds applied and their layer, where configuration is supplied | Never | Presentation of the set's metadata and user framing |
| 2 | `executive_summary` | §4 | Its lists may be empty, each with a fixed statement | Selection by fixed rule only |
| 3 | `kpi_scorecard` | §5 | `not_available` when the set registered no KPI | KPI engine, through the set |
| 4 | `findings` | Every `FACT`, `CALCULATION`, `SOURCED` and supported `INTERPRETATION` statement whose origin is neither `kpi`, `anomaly` nor `forecast`, split into an **evidence** block (classes 1/3/4) and an **interpretation** block (class 5), each in set order | Yes | Synthesis |
| 5 | `anomalies` | Every statement of origin `anomaly`, in set order (§6) | `not_available` | Anomaly engine, through the set |
| 6 | `outlook` | Every `ASSUMPTION` statement of origin `forecast` whose provenance resolves to a registered forecast finding (§6) | `not_available` — **always, until a synthesis forecast translator exists** | Forecast engine, through the set |
| 7 | `swot` | The verified SWOT record whole: quadrants in fixed order, point ids, tags, statements, empty states | `not_supplied` | ADR-0030 |
| 8 | `strategy_recommendations` | The `StrategyResult` records whole, in their own order, with its empty state, human-decision statement and order note | `not_supplied` / `empty` | ADR-0031 |
| 9 | `decision_support` | Each `DecisionResult` whole — all twelve parts, lifecycle and verification label, its own synthesis digest | `not_supplied` | ADR-0032 |
| 10 | `evidence_and_uncertainty` | The set's confidence (labelled as the set's), every conflict whole, every limitation (including unavailable, not-applicable and insufficient-data KPIs and analyses), every `ASSUMPTION` not shown in `outlook`, every statement the set graded `unsupported` or `insufficient_evidence` (labelled as not supported), unresolved dimensions carried by statements | Never (its lists may be empty, each stated) | Synthesis |
| 11 | `decisions_for_the_reader` | The human-decision statement (§12); each included package's decision question with its lifecycle and preferred option or no-preference reason; the ids of recommendations awaiting a person's decision; each package's next steps by reference (package, index) — no new step | Never | Presentation of owned content |

**Prohibited sections and devices:** "what is going well" and "what needs attention" (favourable and
unfavourable placement is SWOT's, ADR-0030); a standalone "key risks" or "opportunities" section (risks
belong to the records and packages that state them, opportunities and threats to SWOT; an aggregate
would re-home, re-order and imply severity); any overall, health, attractiveness or report score; KPI
ratings, red/amber/green or traffic lights; "top priorities", "best option", "headline recommendation";
severity, likelihood or impact columns; decision matrices of numbers; an action plan with owners or
dates.

### 4. Executive summary

A fixed selection, never prose. It contains exactly:

1. **Material statements** — every statement in the set with a `material` verdict whose kind is `FACT`,
   `CALCULATION`, `SOURCED`, or `INTERPRETATION` with supports verified by `grounding`, and whose
   support is not `unsupported` or `insufficient_evidence`; verbatim, in set order, each with kind,
   class label (evidence or interpretation), origin, domain, trust, support, confidence and reasons,
   and its materiality verdict. Interpretations are labelled as interpretations. An `ASSUMPTION`
   (including a forecast) never appears here.
2. **Material but not supported** — the ids of material statements graded `unsupported` or
   `insufficient_evidence`, pointing at section 10. They are never dropped and never presented as
   findings.
3. **Materiality not assessed** — the count of statements carrying no materiality verdict, so absence
   of a verdict is visible.
4. **Recommendations** — for the `StrategyResult`, each record's id, issuer, action verbatim and derived
   confidence, in the record order. No ranking, no subset.
5. **Decisions** — for each package: its decision question, lifecycle and verification label, and its
   preferred option label with its basis, or its no-preference reason. Nothing more is taken from a
   package into the summary.
6. **Standing of the evidence** — the set's confidence and reasons, and the number of conflicts and
   limitations, pointing at section 10.
7. **Availability** — the `status` of sections 3 and 5–9.

Selection is by rule, so the summary cannot be curated: every qualifying statement appears, however
many there are, and nothing else does. "Every major conclusion traces to at least one class 1–4 entry"
(§7) holds because interpretations enter only with verified supports.

### 5. KPI scorecard

- **Rows:** one per `KPIResult` registered in the set, in the KPI catalogue's declaration order
  (`kpi/catalog.py`), never sorted by value, change or materiality.
- **Fields:** `kpi_id`; name; `status` (`available`, `partial`, `unavailable`, `not_applicable`,
  `insufficient_data`); value, unit, currency and periods as the engine computed them; for a
  value-bearing row, the `synthesis_id` of its statement with that statement's materiality verdict (or
  "not assessed"), confidence and reasons; for any other row, the engine's reason; caveats and formula
  basis.
- **Prior, change, change %:** only from the same statement's own `comparison`, `change` and
  `change_pct`. They are never joined in from another finding, never computed by the report; absent →
  "not computed".
- **Targets:** not shown. `kpi_overrides.target` is consumed by no engine and does not reach
  configuration, so a target beside a value would invite a gap nobody computed. Revisit when an engine
  computes target variance.
- **No** health score, rating, colour, good/bad label, KPI ranking or re-judged materiality.

### 6. Anomalies and outlook

**Anomalies.** Each anomaly statement is shown verbatim with the metric, period, observed value,
baseline comparison, deviation, basis, materiality verdict, confidence, caveats — including the
engine's investigation note — and limitations the statement carries; its dimension is shown by
resolving the statement's anomaly provenance to the registered finding, redacted exactly as the engine
redacted it. The report adds no cause, no attribution, and never the
words fraud, error, theft or misstatement: an anomaly is a measured deviation, not an explanation.

**Outlook.** A forecast is a class-6 estimate. The section admits only `ASSUMPTION` statements of origin
`forecast` whose provenance resolves to a forecast finding registered in the set, and shows, by
resolving that pointer rather than copying: scenario, forecast period, method, horizon, history
periods, the uncertainty band and its basis, the validation statement and the assumption register —
always as a block separate from actuals, never merged into a series with them, never with guarantee
language (the forecast engine's `FORBIDDEN_CERTAINTY` list), and never with a scenario the engine did not
produce. **No existing translator produces such a statement** (see Context), so the first
implementation shows `not_available` with the fixed reason *"No forecast statement in this synthesis
set carries forecast provenance."* Forecast text recorded through `synthesis.assumption()` has
`unavailable` provenance, is not an outlook, and appears only among assumptions in section 10. Enabling
the section needs a synthesis-layer forecast translator decided on its own terms, which must not let an
estimate grade `supported` / `HIGH` merely because its provenance resolves. Executive Report never reads
a `ForecastSet` directly.

### 7. Strategy (ADR-0031, unchanged)

The `StrategyResult`'s records are shown whole and unchanged: class 7, their `issued_by`, derived
confidence and reasons, evidence detail, rationale, expected benefit, risks, dependencies, conflicts,
limitations and caveats, in the result's own deterministic order with its own order note. The report
never rewrites, re-grades, reorders, merges, filters or drops a record, never ranks them, never turns
one into evidence, and adds no recommendation semantics of its own. A record that also appears inside
a decision package is shown in both places and cross-referenced by `recommendation_id`.

### 8. Decision Support (ADR-0032, unchanged)

Optional. Each package is shown whole: all twelve parts in contract order, its lifecycle and
verification label before its parts, its synthesis digest, guidance (records, preferred option and
basis or no-preference reason, divergences) and uncertainty (package and per-option confidence,
conflicts, limitations, unresolved dimensions, next steps). The report never re-authors, re-grades,
re-orders, reinterprets, summarises away or drops any part. Packages appear in the order the user's
request lists them, stated not to be a priority.

**Lifecycle.** Draft packages are admitted and always labelled *draft — unverified*. A future `final`
package is structurally interchangeable at the level of its parts, because the M11 verifier records its
verification beside a draft and never edits the parts (ADR-0032 §13); the report reads each package's
lifecycle from the object and shows any verification record M11 attaches exactly as carried. A report
never makes a draft package appear verified or final.

### 9. Framing and Business Context

The request is a closed record: `reporting_period`, `audience`, `objective` (each optional non-blank
text), and `questions` and `constraints` (each an optional list of non-blank text). Decision packages
are passed beside the request, and the order they are passed in is their presentation order. The
request fields are user framing: stored verbatim, `origin: "user"`,
shown in `reporting_frame`, never evidence, never inferred when absent ("not stated"), never used to
select, filter or answer anything, never transmitted. The report does not answer `questions`; it shows
what the assembled artifacts contain. There is no field recording that a decision was made or approved,
so the report cannot claim either.

### 10. Recommendation semantics

**Executive Report issues no recommendations.** `biq-executive-report` is not a class-7 issuer;
`strategy.RECOMMENDATION_ISSUERS` stays as it is; the summary only references records by id. A user who
wants guidance the report lacks is routed to `/strategy-analysis` or `/decision-support`, whose results
the report then assembles. No score, weight, rank, "best", "top", "winner", regrading, reordering or
estimated benefit exists anywhere in the report.

### 11. Confidence, materiality, conflicts, limitations

Existing mechanisms only. Each statement, record and package part carries its own derived confidence
and reasons; the set's confidence is shown and labelled as the set's. **The report computes no
confidence of its own** — no report-level `combine()`, no overall score. Materiality is each statement's
upstream verdict, never re-judged; material statements surface through the summary rule (§4); no second
threshold. Conflicts are shown whole, never settled. Limitations only accumulate: the set's, and every
included artifact's own, shown with it. Unavailable, not-applicable and insufficient-data analyses and
KPIs appear with their reasons; absent optional inputs appear as `not_supplied`; absence of evidence is
stated, never filled.

### 12. Human decision and action boundary

Unchanged (ADR-0010, `CLAUDE.md` §9). Producing a report is draft generation: read-only, no approval. The
report executes nothing, sends nothing, writes to no system, modifies no source data, makes no financial
transaction, and never claims a decision was made or an approval given. Writing it as a new file in
`./businessiq-output/` needs no approval with the path stated; overwriting a file, exporting it off the
machine or sending it to anyone needs explicit per-action approval, and the export stays labelled with
its lifecycle. The fixed statement:

> *This is a draft report for people to read and decide on. BusinessIQ assembled it from analysis
> already produced: it made no decision, recorded no approval and executes nothing. Acting on anything
> in it - a system write, a message, an export or an overwrite - needs a person's decision and explicit
> per-action approval, and financial transactions are prohibited.*

### 13. Lifecycle and the M11 boundary

- **`lifecycle`** is `draft` or `final`. **Every `ExecutiveReportResult` produced before M11 is `draft`**,
  with `verification: "unverified"`, and no code path in the implementation milestone can set `final`.
- **Draft** — assembled and unverified. **Verified** — not a lifecycle value: the act, and its record,
  of the M11 `biq-analysis-verifier` independently recomputing the report's headline figures (the
  summary's statements and the scorecard's values) against the engines, challenging its
  interpretations, confirming every binding and digest, and confirming every included artifact is shown
  whole and unaltered. **Final** — the lifecycle after a successful verification, recorded beside the
  draft; the verifier never edits a section.
- **A report is never presented as more verified than what it contains:** a `final` report may not
  include a `draft` decision package. That is a precondition M11 must enforce, not something this
  milestone implements. How the verification is recorded is M11's decision.
- **No circularity:** the implementation milestone produces drafts without waiting for M11; M11 depends
  on M10 because it verifies M10's drafts.

### 14. Binding, identity and re-entry

- **Built only by the engine's `build()`**, holding the set object, its SHA-256 digest
  (`strategy.synthesis_digest()`), and each included component: the `StrategyResult` object, the SWOT
  record's deterministic-serialisation digest, and each `DecisionResult` object with its serialisation
  digest at build time. Serialising the report refuses if the set changed, a component is no longer
  bound to it, or a component's digest no longer matches.
- **Output identity:** `report_id` is content-addressed (`rpt-` + 12 hex) over the synthesis digest, the
  component digests and the framing.
- **No re-entry:** the report adds nothing to the set, and `register_claims()` must refuse a report and
  every section or entry of one, as it refuses recommendation records and decision packages.

### 15. Deterministic ordering

Order is presentation and is stated not to be a ranking, priority or preference.

| Content | Order |
|---|---|
| Sections | §3, fixed |
| KPIs | KPI catalogue declaration order |
| Summary statements, findings, anomalies, outlook, assumptions, unsupported statements | Synthesis set order (evidence block before interpretation block in `findings`) |
| SWOT | As `swot.build()` orders it |
| Recommendations | As the `StrategyResult` orders them |
| Decision packages | The order the request supplies them; each package's internal order as ADR-0032 fixes it |
| Conflicts, limitations | The set's order (first-seen for limitations) |

### 16. Failure and empty states

**Fail closed — no report, nothing emitted:** no set, or a serialised, look-alike, non-strict, empty or
ungraded one; a set declared `CRITICAL`; a request that is not the closed record or carries any field
for confidence, support, trust, verification, lifecycle, score, weight, rank, priority, severity,
likelihood, target or anything else; blank framing text; a serialised, look-alike or unbound
`StrategyResult`; more than one `StrategyResult` or SWOT; a SWOT record that its placements do not
reproduce over this set; a serialised, look-alike or unbound `DecisionResult`; a duplicate package; a
package bound to a different `StrategyResult` object from the one supplied; any id that does not resolve
exactly once; the set or a component changing during or after assembly.

**Not failures — stated empty states:** no KPI registered; unavailable or insufficient-history KPIs; no
anomaly statements; no forecast statement (always, for now); no external research in the set; no SWOT,
`StrategyResult` or decision package supplied; a `StrategyResult` with no records; no material statement;
conflicting statements; partial sources. **A minimally valid report** is a genuine strict non-empty set
(not `CRITICAL`) and an empty request: sections 1, 2, 4 and 10 carry the set's content, and 3 and 5–9
state their status.

### 17. Output model

Closed at every level; deterministic serialisation preserving section order; implemented as
`lib/schemas/executive_report.schema.json` in the implementation milestone.

| Field | Shape |
|---|---|
| `schema_version` | `"1.0.0"` |
| `analysis` | const `"executive_report"` |
| `issued_by` | const `"biq-executive-report"` — the assembling capability, not a class-7 issuer |
| `report_id` | `^rpt-[0-9a-f]{12}$` |
| `lifecycle` | `draft` \| `final` (implementation produces `draft` only) |
| `verification` | `"unverified"` for a draft |
| `lifecycle_note`, `trust_statement`, `human_decision`, `order_note` | fixed engine-owned text |
| `subject`, `as_of`, `business_model`, `currency`, `quality_grade` | from the set, nullable |
| `synthesis_digest` | `^sha256:[0-9a-f]{64}$` |
| `sources` | `{strategy: {included, synthesis_digest, recommendation_ids} , swot: {included, digest}, decision_packages: [{digest, lifecycle, verification, synthesis_digest, decision_question}]}` |
| `section_order` | the eleven section names, in §3 order |
| `sections` | an object keyed by those names; each optional section `{status, reason, …content}`; content arrays may be empty; `reporting_frame`, `executive_summary` and `evidence_and_uncertainty` always `included` |

Mirrored definitions (statement detail, recommendation record, limitation, decision package) must be
pinned by test to `strategy.schema.json`, `swot.schema.json` and `decision_support.schema.json`, because
`jsonschema_mini` resolves only local references. No field anywhere for score, weight, rank, priority,
severity, likelihood, rating, colour, target, owner, due date or execution state.

### 18. External research

The engine and skill never retrieve, dispatch a scout or build a query. Research reaches the report only
as `SOURCED` statements already in the set, untrusted, with their source semantics (tier, date,
freshness, support). The `/executive-report` command may sequence the existing research skills to build
the set exactly as `/swot-analysis`, `/strategy-analysis` and `/decision-support` do — gate, Tier 0,
nothing internal in a query, nothing internal as a fallback — and may invoke `biq-swot`,
`biq-strategy-recommendations` and `biq-decision-support` over the same set object; the last only for a
decision question the user supplied.

## Security constraints the implementation must meet

1. Consume only a genuine strict `SynthesisSet`; resolve every statement id through `grounding`; refuse
   unknown, ambiguous and out-of-set ids.
2. Admit a `StrategyResult` or `DecisionResult` only as the bound object, and a SWOT record only when its
   placements reproduce it over this set.
3. Show recommendation records and decision-package parts as owned content, never as evidence; show
   assumptions (including forecasts) only as assumptions or outlook, never as evidence.
4. Refuse any authored confidence, support, trust, verification, lifecycle, tier, score, weight, rank,
   priority, severity, likelihood or target.
5. Preserve every statement's kind, class, origin, domain and trust; external content stays untrusted
   and is quoted with its source semantics, never obeyed.
6. Author no sentence of analysis; every figure shown is an existing statement's, record's or part's own.
7. Never let a report or any part of it re-enter synthesis (`register_claims()` refusal extended).
8. Read no file, retrieve nothing, dispatch nothing, write nothing, transmit nothing; framing stays
   local.
9. Fail closed: a refused report raises and nothing is emitted; an invalid optional input refuses the
   report rather than being dropped.

## Reason

Option C is the only one that keeps ADR-0022's single-reading rule, ADR-0031's and ADR-0032's
"assemble, never author or re-grade" wording, and the output standards simultaneously. It adds structure
and no policy: grounding, confidence, materiality, conflicts, limitations, the recommendation contract
and the decision package all keep their one home. Refusing a curated or prose summary is what makes the
most-forwarded artifact the most traceable rather than the least.

## Consequences

**Positive.** The report is checkable end to end: every business statement resolves to one statement,
record or part, and the summary is reproducible from the inputs. Nothing upstream is re-implemented.
Draft and final packages share one presentation path. M11 has a precise object to verify.

**Negative.** The summary can be long when many statements are material, because it is not curated. The
outlook section is always empty until the synthesis layer carries forecasts. There are no targets, no
ratings and no "going well / needs attention" sections, which some executive templates expect. KPI rows
show no prior-period change unless the statement itself carries one. Records inside decision packages
may appear twice (cross-referenced). Everything before M11 is a draft.

**Follow-up required.**
- Implementation milestone: `lib/python/biq/executive_report.py` (`build()`, `ExecutiveReportResult`,
  `render()`), `lib/schemas/executive_report.schema.json`, `skills/biq-executive-report/SKILL.md`,
  `commands/executive-report.md`, focused tests, registry changes moving `executive-report` to built.
- Additive, not policy: extend the `register_claims()` refusal to report records; a read-only accessor
  exposing which `StrategyResult` a `DecisionResult` is bound to; a read-only enumeration of the
  `KPIResult`s a set registered, if the set lacks one.
- Separately decided, not part of the implementation milestone unless approved: a synthesis forecast
  translator and its grading rule.

## Revisit when

- A synthesis forecast translator is approved (enables `outlook`).
- An engine computes KPI target variance (may add targets to the scorecard).
- M11 defines how verification is recorded (may add fields to `final` reports).
- A defensible, computable prioritisation policy is proposed.
- Users need an executive summary that is shorter than the material-statement rule produces.
