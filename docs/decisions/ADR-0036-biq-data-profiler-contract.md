# ADR-0036 — The data profiler contract: a deterministic, value-free assembly of what the Data Layer already knows, bound to its sources, with the subagent deferred until a model must browse

**Date:** 2026-09-17
**Status:** Accepted
**Deciders:** Project owner (M11 data-profiler brief), recorded in the M11 `biq-data-profiler` contract review (decision only)
**Relates to:** ADR-0002 (figures come from code), ADR-0006 (three subagents — **refined here, not
amended**), ADR-0008 (tiered reader), ADR-0009 (disclosure and sensitivity), ADR-0012 (placement),
ADR-0014 (the tool grant is the boundary), ADR-0022 (synthesis contract), ADR-0034 and ADR-0035
(source binding, determinism, re-entry). No accepted ADR text is edited.

## Context

What the repository says `biq-data-profiler` is, verified by reading it at `d388ccd`:

- **ADR-0006:** one of three subagents, justified by *context isolation* — "Raw scan output is enormous and
  worthless once summarised" — granted file access and no web tools.
- **`architecture.md` §10:** "Scan/profile files, sheets, schemas, connector catalogues", invoked for "large or
  multi-sheet data, multi-source reconciliation". **§17:** for >100k rows "the engine streams and aggregates —
  only aggregates reach model context; `biq-data-profiler` isolates the scan". **§9 / `reference/analysis-
  framework.md` step 4:** "Inspect data → ingestion / data-profiler", which must produce "a dataset and profile,
  with the reader tier recorded".
- **ADR-0014, `project_plan.md`:** it remains in Milestone 11. Nothing further defines it; no module, schema,
  skill, command or agent exists.

What the Data Layer and its neighbours already compute — each in one home:

| Fact | Home | Notes |
|---|---|---|
| Encryption, macros, external links, shared formulas, hidden and very-hidden sheets, sheet names, date system | `ingest/workbook.inspect()` → `WorkbookFacts` | Read from the package; **no cell is read** |
| Rows, columns, headers, sheet, sheets detected, reader tier, reader warnings | `ingest/readers.read()` → `Dataset` | **One sheet per `Dataset`**; all rows materialised |
| Per-column kind, kind counts, currencies, missing/ambiguous counts, mixed types, day-first | `normalize.profile_column()` → `ColumnProfile` | Kind and ambiguity from the **first 1,000 values**; missing counted over the whole column |
| Processing mode, rows examined, completeness | `ingest/canonical.build()` | Mode chosen by a 100,000-row threshold; true chunked streaming deferred at M3 |
| Sensitivity class and reasons (`public` … `never`) | `privacy/sensitivity.classify_field()` | Name and content evidence; first 200 values |
| Business role, status (`auto`/`confirm_required`/`unmapped`), confidence, evidence | `mapping/semantic.infer()` | |
| Quality findings, severities, grade, halt, completeness per check | `quality/checks.run()` — 13 families | Messages and evidence may carry values |
| KPI availability, declared inputs, minimum periods, applicable models | `kpi/engine`, `kpi/catalog` | Decided inside each calculator, together with the value |
| Command required roles | `commands/registry` (declared); `commands/runner.run()` (enforced inline) | |
| Labels, k-anonymity floor (5), banding | `analytics/presentation`, `privacy/aggregation` | |
| Source SHA-256, content-addressed identity, stale refusal | `commands/runner.source_sha256()`, ADR-0034/0035 patterns | |

So a profile of *files* needs no model to read raw data: the engine already turns bytes into bounded
structure, and nothing but that structure ever reaches a model. What is missing is one bound, deterministic,
privacy-safe **assembly** of those facts across every sheet and file a user supplies, a few exact structural
counts nobody computes yet (non-null, distinct, date coverage, key uniqueness, cross-source key overlap), and
a statement of what a named analysis could and could not do with the data — without a second quality engine,
KPI engine, privacy engine or reader.

## Problem

Define the data profiler precisely enough to implement: what it produces and never produces, its inputs,
output, fact semantics, provenance, privacy, source binding, identity, failure states, its relationship to
M3, M4, M5, synthesis and Business Context, and whether a subagent is justified — without duplicating any
existing rule or weakening any existing boundary.

## Options considered

### Option A — The ADR-0006 subagent scans files with `Read`/`Bash` and summarises them

**Rejected.** Raw rows would enter a model context, which `architecture.md` §17 forbids ("only aggregates reach
model context"); the model would author the facts a profile exists to state; a shell or file-read grant is not
a boundary (ADR-0014, ADR-0035).

### Option B — A subagent holding a fixed local MCP operation that pages through a deterministic profile

Structurally safe, like the verifier. **Rejected.** Isolation is only worth a subagent when bulky material must
be read by a model; a deterministic profile is already bounded and renders in bounded views, so the main thread
never absorbs bulk. It would add a second MCP server, a Connector-gate decision and an agent to maintain, to
isolate nothing.

### Option C — A subagent with no tools that explains a profile passed in its prompt

**Rejected.** The main thread composes the prompt, so nothing is isolated; explanation is not context
isolation, fan-out or independent verification, so it fails ADR-0006's own test.

### Option D — A deterministic profiler assembling the existing engines; the subagent deferred to the case ADR-0006 still describes

A Python engine builds a closed, content-addressed, source-bound `DataProfileResult` from the Data Layer's own
reads and the existing engines' own outputs, emitting counts, rates, kinds, classes and references — never a
business value. The already-architected `biq-data-ingestion` skill, whose §4 output is `profile.json`, is the
model's entry point. The `biq-data-profiler` subagent is not built now; it
remains allocated for model-mediated exploration of sources Python cannot reach. **Chosen.**

## Decision

**The data profiler is deterministic engine code. It assembles, for one request over one or more local files,
what the Data Layer already establishes, adds a closed set of exact structural counts, references — never
re-grades — quality and KPI applicability, and emits no cell value except ISO currency codes and date bounds of
non-restricted date columns. Its result is closed, content-addressed and bound to the SHA-256 of every source;
a stale result refuses to serialise. It is diagnostic metadata about data, never evidence, and never enters
synthesis. No model computes, edits or authors any profile fact. The `biq-data-profiler` subagent is deferred:
for files, the engine already provides the isolation ADR-0006 asked for.**

It is not a reader, a quality engine, a KPI engine, an analytics, forecasting or anomaly engine, a privacy
classifier, a semantic mapper, a synthesis, recommendation or decision engine, or a streaming redesign.

### 1. The subagent (refining ADR-0006)

- ADR-0006's justification for `biq-data-profiler` was that raw scan output is enormous. Since the Milestone 2 slice and the
  Milestone 3 Data Layer the scan is engine work whose raw output never enters any model context, and a profile is bounded. For local
  files, ADR-0006's three-justification test is not met, so **no subagent is built for file profiling**.
- The name `biq-data-profiler` and its ADR-0006 grant principle (data access, no web) stay reserved for the case
  that still meets the test: **model-mediated exploration of a source only reachable through model tools and
  too large for the main context** — connector catalogues (`architecture.md` §10) arrive with the M12 connector
  layer. Building it then needs its own contract; its tool grant must follow ADR-0014/ADR-0035 (declared,
  structural, no shell or raw-row read).
- ADR-0006 is not edited; this refinement is recorded in the decisions index, as ADR-0031's refinement of
  ADR-0022 was.

### 2. What it does, and does not

| Does | Does not |
|---|---|
| Read each supplied file only through `workbook.inspect()` and `readers.read()` | Open a file any other way, follow an external link, run a macro, evaluate a formula, bypass encryption |
| Profile every **visible** sheet of a workbook, and a hidden sheet only when the request names it | Read hidden sheets by default |
| Reuse `canonical.build()`, `sensitivity`, `mapping.infer()` verbatim for kind, currency, class and role | Re-infer, re-classify or re-map |
| Compute the closed set of structural counts in §5 over every row read | Sample rows, approximate, sketch or extrapolate |
| Run `quality.checks.run()` and **reference** its findings | Grade, threshold, re-severity or summarise quality |
| Report KPI and command applicability **as M5 and the command registry decide it** | Compute a KPI value, a trend, a total, an average, a min/max of a figure, a ranking |
| Propose key candidates and cross-source key-overlap rates for a user to confirm | Choose a join, reconcile data, merge datasets |
| Emit structure: names, counts, rates, kinds, classes, statuses, references | Emit a cell value, a sample, a top-N list, a customer or product name |

### 3. Input contract

A closed request, refused whole on any unknown field or invalid value:

| Field | Required | Rule |
|---|---|---|
| `sources` | **yes** | 1–20 local file paths, each an existing regular file with extension `.csv`, `.tsv`, `.txt`, `.xlsx` or `.xlsm` (the reader's own set). No URL, scheme, directory, glob, stdin or duplicate path. Order is presentation order |
| `sheets` | no | Per source, sheet names to profile; may name a hidden sheet. Absent → every visible sheet. A named sheet that does not exist refuses the request |
| `objective` | no | `{command_id}` from `commands/registry` and/or `kpi_ids` from the KPI catalogue — closed ids only, never free text |
| `presentation` | no | `local` (default) or `shareable` (`analytics/presentation`) |

Beside the request: the `ResolvedConfig` and resolved Business Context the pipeline already resolves (§12).
**Never accepted:** statistics, counts, kinds, sensitivity classes, roles, quality grades, applicability,
confidence, trust, a `DataProfileResult` or its dict, a serialised dataset, connector handles (M12).

One request produces one profile covering every supplied source and every profiled sheet. Each sheet is one
dataset; nothing is concatenated or joined.

### 4. Output — `DataProfileResult`

Built only by `data_profile.build()`; closed schema `lib/schemas/profile.schema.json` — the `profile` schema
`architecture.md` §13 already lists, so no new artifact name is introduced.

| Field | Shape |
|---|---|
| `schema_version` | `"1.0.0"` |
| `analysis` | const `"data_profile"` |
| `profile_id` | `^dpr-[0-9a-f]{12}$` (§8) |
| `status` | `complete` \| `complete_with_limitations` \| `partial` \| `unavailable` (§10) |
| `presentation` | `local` \| `shareable` |
| `config_digest` | `sha256:` of the canonical resolved configuration, computed as `commands/runner` computes a run's `config_digest` |
| `limits` | `{max_sources, distinct_cap, kind_sample, sensitivity_sample}` — the engine constants in force |
| `request` | the closed request as accepted |
| `context_used` | `{business_model, currency}` from Business Context, labelled as context, or `null` |
| `sources[]` | `{source_ref, source_name, source_type, size_bytes, source_sha256, status, reason_code, workbook}` — `workbook` is the `WorkbookFacts` record (sheet names, visibility, encrypted, macro-enabled, external-link **count**, shared-formula count, date system) for workbooks, else `null`; the absolute path appears only in `local` presentation |
| `datasets[]` | per profiled sheet: `{dataset_ref, source_ref, sheet, reader_tier, status, reason_code, row_count, column_count, processing_mode, rows_examined, complete, duplicate_headers, columns[], key_candidates[], quality, applicability}` |
| `columns[]` | `{column_ref, position, original_name, normalized_name, facts}` — `facts` per §5 |
| `relationships[]` | cross-dataset key candidates: `{left, right, overlap_rate, basis: "calculated", status: "candidate"}` — never a confirmed join |
| `limitations[]` | `{code, subject_ref, reason}` in discovery order (§10) |
| `trust_statement`, `use_statement` | fixed text: facts describe structure; they are not evidence and decide nothing |

**No** confidence, trust grade, severity, score, rank, timestamp, sample value, top values, min/max of a
non-date column, mean, total, or model-written field.

### 5. Fact semantics — every fact carries its basis

Each fact is `{value, basis, operation, examined}`: `operation` names the one function that produced it;
`examined` is the number of values it rests on.

| Basis | Meaning | Facts |
|---|---|---|
| `observed` | Read as-is from the package or reader | sheet names and visibility, encrypted, macro-enabled, external-link count, shared-formula count, date system, headers, row and column counts, reader tier, reader `IngestWarning` codes |
| `calculated` | Exact, deterministic, over every row read | `non_null_count`, `empty_count`, `distinct_count` (exact; `null` above `distinct_cap` with limitation `distinct_count_capped` and `distinct_at_least`), `uniqueness_rate` (distinct / non-null), `duplicate_headers`, `date_coverage` `{first, last, period_count}` for date-kind columns not classed `restricted`/`never` (periods via `kpi.primitives.periods()`), key-candidate status (non-null = rows and uniqueness = 1, or a named M3 `order_id`/`customer`/`product` role), cross-dataset `overlap_rate` (Jaccard of exact distinct sets, both under the cap, same kind) |
| `inferred` | Produced by an existing M3 rule, carried with that rule's own evidence and sample size | `kind`, `kind_counts`, `mixed_types`, `ambiguous_count` (sample), `currencies`, `day_first` (`normalize.profile_column`, 1,000); `sensitivity` class and reasons (`classify_field`, 200); `role` with `status` and `confidence` (`mapping.infer`) |

A `confirm_required` role is shown as exactly that — never as the role. There is no `heuristic` or
`model_generated` basis: nothing in a profile comes from a model.

### 6. Privacy

- **No cell value leaves the engine** except ISO currency codes and `date_coverage` bounds of non-restricted
  date columns. No samples, distinct values, top values, names, emails, phone numbers, addresses, identifiers or
  numeric statistics of figures.
- A column classed `never` or `restricted` reports its name, kind, class and counts only — no date bounds, no
  key overlap.
- In `shareable` presentation, counts below the k-anonymity floor are banded with `privacy.aggregation.
  band_count()`, absolute paths are omitted, and column names of `never`-classed columns are replaced with
  their position; `local` shows names and exact counts to the data's owner.
- Sensitivity comes only from M3. A profile is local output: it is never part of any external query, and the
  disclosure gate (ADR-0009) governs anything that would leave.

### 7. Relationships to existing layers — reference, never re-decide

- **M3 (Data Layer)** is the only way data is read and the only source of kind, currency, sensitivity and role.
  The profiler adds exact counts over the rows M3 materialised and records M3's processing mode verbatim. True
  chunked streaming stays the M3 deferral it already is; the profiler neither implements nor relabels it.
- **M4 (Data Quality)** is authoritative. Per dataset the profiler runs `quality.checks.run()` exactly as the
  pipeline does and references each finding by `{check_id, family, code, severity, affected, fields,
  completeness}` plus the report `grade` and `halted` — **never** its message, evidence, threshold or observed
  value, which may carry data. The profiler never counts a duplicate, an outlier, a negative or an invalid value
  as a quality observation and never thresholds its own counts. M4 does not call the profiler: no cycle.
- **M5 (KPIs)** is authoritative for applicability, and in M5 availability is decided inside each calculator
  (`kpi/engine._calculate_one`: applicability → currency safety → the calculator's own input contract). There is
  no precondition-only entry point, and the profiler does not create one or re-implement any calculator's input
  rule. For the requested `kpi_ids`, or the requested command's `kpi_focus`, the profiler calls
  `kpi.engine.calculate()` exactly as the pipeline does and keeps **only the status bucket** (`available`,
  `partial`, `unavailable`, `not_applicable`, `insufficient_data` — `kpi.contract.BUCKETS`) plus the definition's
  declared `inputs` and `minimum_periods`. The value, currency and reason text are discarded before the result
  is built — they are figures or may carry them. No objective → no KPI applicability section.
- **M7 (commands)** is authoritative for what a command needs. For a requested `command_id` the profiler reports
  the registry's declared `required_roles`, each with its mapping status from `mapping.infer()` (`auto`,
  `confirm_required`, absent). It does **not** predict the command's outcome: that also depends on the quality
  gate, KPIs and engines, and is decided only by running the command. The profiler never changes what a command
  or KPI does.
- **M8, M9, M10, M11-verification:** no relationship. Forecast, anomaly, research, synthesis, Strategy, SWOT,
  Decision Support and Executive Report do not consume a profile.
- **Layering.** `data_profile.py` is a top-level composition module beside `pipeline.py`, which already composes
  reading, quality and KPIs the same way. It imports downward only (ingest, normalize, privacy, mapping, quality,
  kpi, the command registry's declarations); nothing in those layers imports it, so no lower layer depends on a
  profile.

### 8. Identity, binding and staleness

- **Source binding:** each source's SHA-256 over its complete bytes is captured immediately before its first
  read and again after its last; a difference marks that source `unavailable` with `changed_during_profile` and
  none of its datasets is profiled.
- **`profile_id`** = `dpr-` + 12 hex over the canonical JSON of `{schema_version, limits, request, presentation,
  config_digest, context_used, [(source_name, source_sha256, sheets profiled, reader tier)]}`. Same bytes, request
  and configuration → the same id and a byte-identical result. Refs are content-addressed the same way:
  `src-` over `(source_name, source_sha256)`, `dst-` over `(source_ref, sheet, reader_tier)`, `col-` over
  `(dataset_ref, position, original_name)`.
- **Staleness:** the result holds each source path and digest; `as_dict()` and `to_json()` re-hash every source
  and **refuse** if any differs (or has become unreadable), as the M11 run registry refuses a changed source
  (`SOURCE_CHANGED`). There is
  no setter and no constructor outside `build()`.
- **Determinism:** sources in request order, sheets in workbook order, columns in source order, candidates and
  relationships in that order; no timestamp; no row sampling; M3's inference samples are first-N.

### 9. Large data and Excel

- Every count is exact over the rows M3's reader materialised; there is no sampling and no approximate
  statistic. A distinct set above `distinct_cap` (100,000) is not held: `distinct_count` is `null`, the limitation
  says so, and that column takes part in no overlap. More than 20 sources refuses the request rather than
  truncating it.
- If the reader cannot read a source (memory, format, tier), that source is `unavailable`; the reader's error is
  mapped to one closed reason code (§10) and its message, which may name data, is not carried. Nothing is estimated.
- Workbooks: `workbook.inspect()` runs before any cell read. Encrypted → source `unavailable` (`encrypted`), no
  bypass. Macro-enabled → observed, never executed. External links → counted, never followed. Formulas are never
  evaluated; values are the reader's cached values. A construct the resolved tier refuses rather than guesses
  (`architecture.md` §5 rule 2 — e.g. shared formulas or external references at Tier 3) makes that source
  `unavailable` (`reader_refused`) with the existing CSV-export guidance code. Hidden sheets are listed; profiled
  only when named.
- Tier 4 means no usable Python, so no profile can be built at all; the skill says so and gives the existing CSV
  guidance. It never substitutes a model reading of the file.

### 10. Status, limitations and failure

| Situation | Outcome |
|---|---|
| Request invalid: no or >20 sources, URL, directory, missing file, unsupported extension, duplicate, unknown field, unknown objective id, named sheet absent, caller-supplied fact | **Refused**; no result |
| Every source and sheet profiled, no limitation | `complete` |
| Profiled, but a limitation applies (`sampled_inference`, `distinct_count_capped`, `hidden_sheet_not_profiled`, `macro_enabled_not_executed`, `external_links_not_followed`, `degraded_reader_tier`, `mixed_types`, `no_rows`, `no_date_column`, `inconsistent_headers_across_sheets`) | `complete_with_limitations` |
| Some source or sheet `unavailable` (`encrypted`, `unreadable`, `malformed`, `unsupported_encoding`, `empty_file`, `no_columns`, `reader_refused`, `changed_during_profile`) | `partial` |
| Nothing profiled | `unavailable` — the result still lists every source with its reason |
| Source changes after profiling | Serialisation refused (stale) |

`inferred` facts always add `sampled_inference` when a column exceeded the rule's sample. No missing statistic is
filled; an unavailable fact is `null` with its limitation.

### 11. Synthesis, evidence and re-entry

A profile is **diagnostic metadata about the data, not evidence about the business**. It needs no evidence class
and gets none; no translator accepts it; no Layer-3 capability consumes it. `SynthesisSet.register_claims()` refuses
a `DataProfileResult`, its dict, any record with `analysis: data_profile`, and any record carrying a profile-only
field (`profile_id`, `source_ref`, `dataset_ref`, `column_ref`, `key_candidates`, `relationships`,
`applicability`). Internal facts keep reaching synthesis only through the existing engine-footed
translators. There is no profile → synthesis → recommendation path.

### 12. Business Context

Business Context affects the profile only where an existing engine already uses it: M5's `applicable_models`,
M4's currency check. The profile shows `context_used` labelled as context. It never infers a business model,
currency or subject from the data, and never states a context value as a data fact.

### 13. Model boundary

No model reads raw rows for a profile, computes or edits a profile fact, supplies a count, class, role, grade or
status, marks a key candidate confirmed, or presents a profile as evidence or as a verdict on whether the data is
"good". A model may choose to request a profile, present `data_profile.render()` output, and explain limitations
already listed. A join key becomes confirmed only by the user, outside the profile (`architecture.md` §17).

### 14. Tools and invocation

- The skill runs the engine exactly as the analysis commands do: one Bash invocation of Python over
  `lib/python`, printing `data_profile.render()` of the result. No new command, no MCP server, no agent, no web
  tool; the Connector gate is not engaged.
- Skill frontmatter cannot restrict tools (ADR-0001), so the skill's instruction not to open a source file with
  `Read` or a shell is advisory. **The privacy guarantee is therefore the output contract, not a tool grant:**
  the engine emits no value (§6), and a structural test holds that the rendered and serialised profile of a
  canary dataset contains none of its cell values beyond §6's two exceptions.
- The engine does no network I/O (CLAUDE.md §4). A profile is never an argument to research, the disclosure gate
  or any export.

## Reason

Option D is the only option that keeps every existing home authoritative (ADR-0012), keeps raw data out of every
model context (§17, ADR-0009), and satisfies ADR-0006's own test instead of building an agent that the engine has
made unnecessary. Binding and identity reuse the verification milestone's proven patterns, so a profile can be
stale but never silently wrong. Emitting counts, rates, kinds and references rather than values keeps profiling on
the structural side of the line analytics owns.

## Consequences

**Positive.** One user-facing answer to "what is in these files, and what can BusinessIQ do with them", with no
new reader, classifier, quality rule or KPI rule, no raw data in any model context, and exact figures only.

**Negative.** No min/max/mean of figures and no sample values, which some users expect of a profiler — those are
analytics. Distinct counts stop at the cap. Profiling very large files costs what reading them costs, because
chunked streaming remains the M3 deferral. The ADR-0006 subagent is not built in M11; architecture tables that
name it describe a deferred component until a model-mediated source exists.

**Follow-up required — the profiler implementation milestone.** `lib/python/biq/data_profile.py` (`build`,
`DataProfileResult`, `render`, `DataProfileError`); `lib/schemas/profile.schema.json`;
`skills/biq-data-ingestion/SKILL.md` for local files only (connector resolution stays M12) as the model's entry
point, so the skill count stays 20; the `register_claims()` refusal extended; focused tests for every row of §10, fact
basis, privacy (no value emitted, banding, `never` columns), determinism and identity, staleness, workbook
constructs at every tier, M4/M5 reference-not-recompute, and re-entry; documentation. **Not part of it:** an agent,
an MCP server, a command, connector sources, chunked streaming, approximate statistics.

## Revisit when

- A model-mediated source too large for the main context exists (connector catalogues, M12) — build the subagent
  under its own contract.
- Chunked streaming lands in the Data Layer — counts may then be computed in a pass without materialisation.
- Users need value statistics of figures — that is an analytics decision, not a profile change.
