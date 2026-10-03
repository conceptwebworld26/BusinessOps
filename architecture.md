# BusinessOps — Technical Architecture

**Status:** Revision 2 — **approved**. Implementation status is owned by `project_plan.md` (Milestone 14 in progress as of 2026-09-27)
**Version:** 0.2.0
**Last updated:** 2026-09-27

> **Revision 2 changelog** (corrections from the architecture review of Revision 1):
> tiered `.xlsx` ingestion with a managed dependency (ADR-0008) · comparative-intelligence
> privacy boundary replacing the blanket rejection rule (ADR-0009) · consequence-based
> approval model (ADR-0010) · Business Context promoted to a first-class component
> (ADR-0011) · component placement rule — 25 skills become 20 skills + 6 reference documents
> (ADR-0012) · the "4,000-token ceiling" corrected to a self-imposed target, since no
> platform limit exists (ADR-0013) · vertical-slice proof moved to Milestone 2.
> Revision 1 is preserved in git history and in the ADRs it produced.

This is the living source of truth for the BusinessOps technical architecture. It describes
what the system *is* and *why*. Status and roadmap live in `project_plan.md`; development
process lives in `CLAUDE.md`.

> **Lineage.** BusinessOps is derived from the BusinessIQ codebase and is developed as a
> separate product. On 2026-09-30 (BusinessOps Milestone 1) its identifiers were migrated:
> plugin `businessiq` → `businessops`, technical prefix `biq` → `bops`, runtime state
> `.businessiq/` → `.businessops/`, `businessiq-output/` → `businessops-output/` and
> `~/.claude/businessiq/` → `~/.claude/businessops/`. This document names every identifier in
> its current form. Measurements and observations dated before 2026-09-30 were made on the same
> design under the BusinessIQ identifiers, and the records cited for them (`docs/development/`,
> `docs/decisions/`) keep those original names. Commit hashes and "git history" referred to here
> belong to the BusinessIQ repository and are not part of this repository's history.

> **Implementation status.** Milestone 1 (Foundation) is built and tested: manifests,
> configuration precedence, Business Context, reader-tier resolution, the six `reference/`
> documents and the test harness. Everything else in this document is designed but not yet
> built — see `project_plan.md` for what exists today.

---

## 1. System overview

BusinessOps is a Claude Code plugin that converts **internal business data** and **external
business intelligence** into decision-ready analysis.

```
                        ┌───────────────────────────────────────┐
                        │  User (owner / CEO / CFO / analyst)   │
                        └───────────────┬───────────────────────┘
                                        │ /command or natural language
                        ┌───────────────▼───────────────────────┐
                        │  L4  ORCHESTRATION — commands/ (17)   │
                        │  sequence + gates only, no logic      │
                        └───────────────┬───────────────────────┘
      ┌─────────────────────────────────┼─────────────────────────────────┐
┌─────▼──────────────┐   ┌──────────────▼─────────────┐   ┌───────────────▼──────────┐
│ L3 SYNTHESIS (4)   │   │ L2A ANALYTICS (7)          │   │ L2B INTELLIGENCE (5)     │
│ swot · strategy ·  │◄──┤ kpi · sales · customer ·   │   │ external-research core · │
│ decision-support · │   │ product · financial ·      │   │ company · market ·       │
│ executive-report   │   │ forecasting · anomaly      │   │ competitor · industry    │
└─────┬──────────────┘   └──────────────┬─────────────┘   └───────────────┬──────────┘
      │                  ┌──────────────▼─────────────┐                   │
      │                  │ L1 DATA (3)                │                   │
      │                  │ ingestion (incl. connector │                   │
      │                  │ resolution) · semantic-map │                   │
      │                  │ · data-quality             │                   │
      │                  └──────────────┬─────────────┘                   │
      └─────────────────────────────────┼─────────────────────────────────┘
                  ┌─────────────────────▼──────────────────────┐
                  │ L0 CONTEXT + POLICY                        │
                  │ skill:      bops-business-context           │
                  │ reference/  (0 always-on, read on demand)  │
                  │   analysis-framework · evidence-ledger ·   │
                  │   materiality-policy · output-standards ·  │
                  │   ambiguity-protocol · research-policy     │
                  └─────────────────────┬──────────────────────┘
                  ┌─────────────────────▼──────────────────────┐
                  │ COMPUTE ENGINE  lib/python/bops/            │
                  │ deterministic · no network · tiered readers│
                  └────────────────────────────────────────────┘
```

**The dependency rule:** a layer may call downward, never upward. Commands call skills;
skills call the engine and read references; the engine calls nothing.

### Two information domains

| | Internal | External |
|---|---|---|
| Source | User files, MCP-connected business systems | Public web, published research |
| Trust | Authoritative for this business | Variable — tiered and dated |
| Confidentiality | Confidential | Public |
| Provenance classes | 1, 2 | 3 |
| May enter a research query | Only per the disclosure tiers in §7 | n/a |

Comparative questions ("is our margin typical?") are answered by **retrieving the public
benchmark and comparing locally**, so the internal figure does not leave the machine. §7
gives the full model.

---

## 2. Plugin architecture

Verified against Claude Code 2.1.263 (ADR-0001; probe evidence in
`docs/development/2026-09-08-milestone-0-architecture-gate.md`).

| Component | Mechanism | Discovery |
|---|---|---|
| Manifest | `.claude-plugin/plugin.json` | required |
| Distribution | `.claude-plugin/marketplace.json`; the installable package is built by `scripts/build_distribution.py` | The repository loads as a plugin for development (`--plugin-dir .`). Users install the package built from an allowlist into `dist/businessops/`, with its plugin root at the package root and no tests, evals, history or developer tooling (ADR-0055). One public repository, <https://github.com/conceptwebworld26/BusinessOps>, holds both the source and the committed package; a directory submission names the plugin path `dist/businessops` (ADR-0057). The repository's marketplace entry points at `./dist/businessops`, so adding the repository as a marketplace installs only the package; the build sets the package's own entry to `./` (BOPS-R18). The build generates the package's `.gitignore` (Python bytecode only, BOPS-R16) |
| Commands | `commands/*.md` | auto-discovered |
| Skills | `skills/<name>/SKILL.md` | auto-discovered |
| Agents | `agents/*.md` | auto-discovered — **must not** be listed in `plugin.json` |
| MCP | `.mcp.json` | auto-discovered. One local stdio server, `bops-verifier`, declared as `sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" --verifier` so it starts through the same interpreter resolver as the engine (ADR-0035, amended by ADR-0052) |
| Hooks | `hooks/hooks.json` | auto-discovered. One plugin-wide write guard: `PreToolUse`, `UserPromptSubmit` and `UserPromptExpansion` run `hooks/bops_guard.sh`, which enters the engine as `bops_run.py --guard <event>` (ADR-0051; runtime-measured on 2.1.283). A `PostToolUse` hook on `Agent`/`Task` runs `bops_run.sh --handback` to capture the research scout's reply verbatim (ADR-0053); both entries are harness-only, and a tool call may invoke neither |
| Evals | `evals/**/case.yaml` | `experimental.evals` in the manifest |
| Engine entry | `lib/python/bops_run.py`, run as `python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/bops_run.py" -c …` | not a platform concept. The platform substitutes `${CLAUDE_PLUGIN_ROOT}` in command and skill bodies (ADR-0042; runtime-verified on 2.1.278) |
| Reference docs | `reference/*.md` | not a platform concept — plain files read on demand |

```jsonc
{
  "$schema": "https://anthropic.com/claude-code/plugin.schema.json",
  "name": "businessops",
  "version": "0.1.0",
  "description": "...",
  "author": { "name": "...", "email": "..." },
  "homepage": "https://github.com/conceptwebworld26/BusinessOps",
  "repository": "https://github.com/conceptwebworld26/BusinessOps",
  "license": "LicenseRef-BusinessOps-Proprietary",
  "keywords": ["business-intelligence", "analytics", "forecasting", "fp-and-a"],
  "icon": "./.claude-plugin/icon.png",
  "experimental": { "evals": "evals" }
}
```

`icon` is a directory-listing field: Anthropic's directory reads it, Claude Code does not. The directory
accepts only a square PNG or JPEG of 512 to 2048 px under 2 MB, not SVG or WebP, so `icon` names
`.claude-plugin/icon.png`, a 512 × 512 PNG rendered from the design source `.claude-plugin/icon.svg`, which
is not shipped. `claude plugin validate` checks neither the file nor its format, so the build's package
check enforces the directory's rule.

Every component key is omitted so the conventional directories auto-discover — `agents`
included, and that one is not a style preference. Measured at Milestone 9-B: with
`"agents": ["./agents/bops-research-scout.md"]` present, `claude plugin details businessops`
reported **Agents (0)**; with the key removed, the same command reported
**Agents (1) bops-research-scout**. The manifest validated either way, so declaring agents
silently stopped the retrieval agent shipping at all. A manifest test now asserts the key's
absence and records the measurement (ADR-0015).

**Validator advisory — known and accepted (found in Milestone 1).** `claude plugin validate`
emits one warning: *"CLAUDE.md at the plugin root is not loaded as project context."* The
manifest itself validates with **zero errors and zero warnings**; the advisory concerns
`CLAUDE.md` only. It is correct and expected — this repository is both the plugin *and* its
development project, and `CLAUDE.md` is development governance (section 13 ownership table)
that is deliberately **not** shipped as plugin context. `CLAUDE.md` is retained, so
`--strict` against `plugin.json` exits non-zero on this advisory alone.
`claude plugin validate .` resolves to the marketplace manifest and passes `--strict`
cleanly. This is a documentation-placement advisory, not an architectural conflict.

### Runtime constraints — what is real (ADR-0013)

**Documented hard limits:**

| Limit | Value |
|---|---|
| Skill `name` | 64 characters |
| Skill `description` | 1024 characters |

**Documented guideline:** SKILL.md body under 500 lines "for optimal performance".

**Loading behaviour** — official guidance and measurement agree: at startup only `name` and
`description` are pre-loaded for skills, commands and agents. Bodies load on invocation.
Reference files and scripts cost **zero** until read. MCP tool schemas resolve at runtime and
are not counted.

| Component | Always-on | On-invoke | Measured on |
|---|---|---|---|
| Skill | name + description | full body | `marketing`: ~110 vs 1.5k–6.7k |
| Command | description | full body | `code-review`: ~20 vs ~2.5k |
| Agent | name + description | full prompt | `feature-dev`: ~60–80 vs 570–850 |
| Reference doc | 0 | file size when read | — |

**There is no aggregate always-on ceiling.** A full-scale probe (17 commands + 25 skills +
3 agents = 42 components) measured **~2,617 tok always-on** and passed
`claude plugin validate --strict` with no cap, warning or error. The 4,000-token "ceiling"
in Revision 1 was not a platform limit; it was my own invention and is withdrawn.

**Self-imposed target: ≤ 3,000 tokens always-on**, measured with
`claude plugin details businessops` each milestone and recorded in the task report. Exceeding
it breaks nothing — the cost is gradual context competition.

**Measured at Milestone 1: ~0 tokens always-on** (0 commands, 0 skills, 0 agents — none are
built yet). This also confirms empirically that the six `reference/` documents contribute
**nothing** at startup, which is the entire basis of the ADR-0012 placement decision.

**The real constraint is description discriminability.** With 37 components in one domain,
the binding problem is 37 similar descriptions competing to match a request; the failure is
the wrong component firing, which no token count reveals. Descriptions are therefore written
to be mutually exclusive and to name the distinguishing trigger. If the budget is exceeded,
merge components whose descriptions overlap — never thin a description, because one too
vague to match is worse than one costing 110 tokens.

---

## 3. Component placement — where each rule lives (ADR-0012)

Applied to every business rule:

| Question | Home |
|---|---|
| Deterministic computation, no judgement? | **Engine** — `lib/python/bops/` |
| A definition, policy or table nobody invokes directly? | **Reference** — `reference/` |
| Needs model judgement, and a user might ask for it in words? | **Skill** — `skills/<n>/SKILL.md` |
| Purely sequencing: what runs, in what order, with which gates? | **Command** — `commands/<n>.md` |

**Agents hold no unique business logic.** They load the same skills and references as the
main thread; their only distinctive property is isolation, fan-out or verification. A rule
found only inside an agent is a bug.

**The non-duplication rule.** A formula lives in the engine and nowhere else — skills describe
when and why it applies, never restating it. A policy lives in one reference document —
skills and commands link, never paraphrase. A workflow lives in one skill — commands sequence
skills, never inlining their steps. Review rejects any change that restates a rule already
homed elsewhere.

### Reference documents (6) — 0 always-on, read on instruction

| File | Owns |
|---|---|
| `reference/analysis-framework.md` | The 19-step pipeline (§9) |
| `reference/evidence-ledger.md` | Seven provenance classes, confidence rules (§7) |
| `reference/materiality-policy.md` | What counts as a material change |
| `reference/output-standards.md` | Currency/number/date conventions, output shapes |
| `reference/ambiguity-protocol.md` | Never-guess rules, insufficient-data phrasings |
| `reference/research-policy.md` | Source tiering, staleness windows, conflict handling |

These were Revision 1's five "Layer-0 foundation skills" plus the policy tables extracted
from `bops-external-research`. They are never invoked by name and contain no workflow, so as
skills they paid an always-on cost for a trigger that would never fire. Commands read them by
explicit numbered step — more reliable than hoping a skill auto-fires, and cheaper.

---

## 4. Skill architecture — 20 skills

Full inputs/outputs per skill are elaborated in `docs/skills/` as each is built.

### Layer 0 — Context (1)

| Skill | Purpose | In → Out | Depends on |
|---|---|---|---|
| `bops-business-context` | Elicit, validate, persist and apply the business's identity, characteristics, vocabulary and preferences. Drives **KPI relevance**, not just formatting. See §6. | conversation / `business_context.json` → validated context | ambiguity reference |

### Layer 1 — Data (3)

| Skill | Purpose | In → Out | Depends on |
|---|---|---|---|
| `bops-data-ingestion` | Resolve the source (file **or** connector capability — registered identities only, §11, through `connectors.registry`; the shipped registry is empty, so a capability resolves to a named absence plus the file path; connector record reads are M12-C, `BLOCKED`), read it via the tiered reader (§5), detect sheets/headers/types/dates/currency, normalise into the canonical dataset. **Never mutates source.** Records which reader tier was used. | path or capability → `dataset.json` + `profile.json` | engine |
| `bops-semantic-mapping` | Map columns to business roles — date, revenue, cost, quantity, customer, product, region, channel, salesperson — confidence-scored; below threshold it asks, never guesses. | profile → `semantic_map.json` | ambiguity reference |
| `bops-data-quality` | The validation gate. 13 check families graded `PASS`/`WARNING`/`CRITICAL`; `CRITICAL` halts. Grades the ingestion tier too — a Tier-3 read with unresolved formats is a `WARNING`. | dataset + map → `quality_report.json` | engine, materiality reference |

### Layer 2A — Internal analytics (7)

`bops-kpi-engine` (~27 KPIs; returns `computed` / `unavailable` / `partial` / `not_applicable`
— see §6), `bops-sales-intelligence`, `bops-customer-intelligence` (behaviour only, never
inferred intent), `bops-product-intelligence`, `bops-financial-analysis`, `bops-forecasting`
(refuses below minimum history; actuals never merged with forecast), `bops-anomaly-detection`
(never classifies anything as fraud).

### Layer 2B — External intelligence (5)

`bops-external-research` is the shared core — query construction, the **disclosure gate**
(§7), citation capture — used by `bops-company-analysis`, `bops-market-analysis`,
`bops-competitor-analysis` and `bops-industry-research`. Its policy tables live in
`reference/research-policy.md`.

A research request names a **category** and an **intent**, and the shared core is agnostic to
both so that each skill parameterises it rather than building its own request type. The intent
enumeration is closed and validated: `benchmark`, `profile`, `sizing`, `trends`, `positioning`,
and — added additively by M9-D.2 for market research (ADR-0019) — `overview` and `drivers`,
then by M9-D.3 for competitor research (ADR-0020) — `landscape` and `comparison`. An intent
outside the enumeration is refused by `ResearchRequest.validate()` before the gate sees it.
M9-D.3 added only the two questions no existing intent expressed and reused `positioning` and
`trends` for the two it already did, and M9-D.5 added `definition` and `structure` for
industry research on the same test while reusing `sizing`, `trends` and `drivers` — so the
enumeration grows by need rather than by skill, and stands at eleven.

#### The research-intent registry

**`lib/python/bops/research/intents.py` is the single source of truth for research-intent
metadata** (M9-D.4, ADR-0021). Until M9-D.4 that metadata was three flat structures in two
modules — the `INTENTS` tuple in `contract.py`, and `INTENT_TERMS` and `SUBJECT_LEADS` in
`query.py` — while the relationship between a category and the intents it asks was written
down nowhere and recoverable only by reading three skill files. Adding an intent meant
editing three structures and hoping none was missed.

The registry holds **one record per intent** (`ResearchIntent`, a namedtuple): the
identifier, its purpose, the words that express it inside the query text, whether the query
leads with the subject, the categories that ask it, and the production skills or commands
that issue it. `INTENTS`, `INTENT_TERMS` and `SUBJECT_LEADS` still exist under their
existing names and hold exactly what they always held — they are now **views derived from
the registry**, re-exported by `contract.py` and `query.py`, so they cannot drift from it or
from each other. There is no second table anywhere.

| Category | Intents | Skill |
|---|---|---|
| `company` | `profile`, `trends`, `positioning` | `bops-company-analysis` |
| `market` | `sizing`, `trends`, `overview`, `drivers` | `bops-market-analysis` |
| `competitor` | `trends`, `positioning`, `landscape`, `comparison` | `bops-competitor-analysis` |
| `industry` | `definition`, `sizing`, `trends`, `drivers`, `structure` | `bops-industry-research` |

**Shared intents are one identifier, not a twin per category.** `trends` is listed once and
names four categories; `positioning`, `sizing` and `drivers` are each listed once and name
two. A category-specific
duplicate would give one question two names, which is what a closed enumeration exists to
prevent. `benchmark` carries no category at all: it is the default intent of every
`ResearchRequest` and is category-agnostic by design, so naming an owner for it would state
something the code does not do.

**The registry is metadata and nothing else.** It performs no retrieval, calls no gate,
dispatches no scout, parses no evidence, creates no claim and synthesises nothing — each of
those has a home already, and a table that began calling them would be a framework rather
than a description. It is also immutable: the records are namedtuples and the mappings are
read-only proxies. That is a security property rather than tidiness, because intent metadata
decides query wording and query wording is what the disclosure gate assesses — a table a
caller could edit at runtime would be a table a user-supplied company name could edit at
runtime. Nothing in it is ever built from user input.

### Layer 3 — Synthesis (4)

`bops-swot` (every point tagged data-supported / externally-sourced / analytical-inference;
**built in M10.3.1** with `/swot-analysis` — see *The first consumer* in §7 and ADR-0030),
`bops-strategy-recommendations` (each recommendation carries evidence, rationale, expected
benefit, risks, dependencies and confidence — all six or it is not issued; contract decided in
ADR-0031, built in M10.3.2 with `/strategy-analysis`),
`bops-decision-support` (the 12-part framework, defined in ADR-0032; built in M10.3.3 with
`/decision-support`),
`bops-executive-report` (assembles; performs
no fresh analysis; contract decided in ADR-0033, built with `/executive-report`).

### Merged from Revision 1

`bops-connector-broker` → into `bops-data-ingestion` (source resolution is only used when
loading business data; its capability map became a reference table).
`bops-report-composer` → judgement into `bops-executive-report`, rendering mechanics into the
engine ("assembly primitives" was not a judgement boundary).

---

## 5. Data ingestion — the tiered reader (ADR-0008)

Verified: the Claude Code `Read` tool **cannot read `.xlsx`** ("cannot read binary files"),
so a parser is required. Both candidates were built and run against the same realistic
workbook during review; they agreed on every value both could read.

`bops-xlsx-reader` resolves the highest available tier:

| Tier | Reader | Condition | Install |
|---|---|---|---|
| 1 | openpyxl already importable | present in the interpreter | none |
| 2 | openpyxl in a plugin-managed venv at `~/.claude/businessops/runtime/` | Python + pip + network | one-time, disclosed, consented |
| 3 | stdlib parser (`zipfile` + `ElementTree`) | Python available, offline or install declined | none |
| 4 | Guided CSV export | no usable Python | none |

Rules that make this safe:

1. **Bootstrap asks once**, naming the package (pinned), the isolated location, and that
   declining drops to Tier 3. It is a write action and is gated like one (§8).
2. **Tier 3 is complete for a documented subset and refuses outside it** — unresolvable
   number formats, shared formulas, external references and encrypted workbooks **escalate
   or halt rather than guess**. Every dataset records its tier; a Tier-3 read with any
   unresolved format raises a quality `WARNING`.
3. **Source opened read-only at every tier.** Never written, never moved.
4. **Formulas are never evaluated** — the cached value is read. A formula cell with no cached
   value is a `WARNING`, not an invented number.
5. **Cross-tier equivalence is tested**: the same fixture at Tier 1 and Tier 3 must produce
   identical canonical datasets, or the fixture documents the difference.

Verified Tier-3 capability: sheet detection via the rels graph, shared strings, inline
strings, date cells resolved from `styles.xml`, 1900/1904 date systems, cached formula
values, currency symbol extraction, streaming via `iterparse`. Known gap, scheduled for
Milestone 2: built-in numFmt ids (a bounded ECMA-376 lookup table).

CSV and delimited files are read by the engine at all tiers with encoding and delimiter
detection.

**The data profile (M11, ADR-0036).** Built. `profile.json` — the output
`bops-data-ingestion` names in §4 — is a closed, content-addressed `DataProfileResult` built by deterministic
engine code (`data_profile.py`, a composition module beside `pipeline.py`) over one or more local files:

- It reads only through `workbook.inspect()` and the tiered reader, profiles every visible sheet (a hidden
  sheet only when named), and **reuses** M3's kind, currency, sensitivity and role inference verbatim.
- It adds only exact structural counts over every row read — non-null, empty, distinct (capped, never
  estimated), uniqueness, date coverage, key candidates and cross-dataset key-overlap rates — each labelled
  `observed`, `calculated` or `inferred` with the operation and the number of values it rests on.
- Quality is **referenced** from M4 by check id, severity and grade, never re-graded; KPI applicability is the
  status bucket M5's own calculation returns, with values discarded; command needs are the registry's declared
  roles and their mapping status, never a predicted outcome.
- It emits **no cell value** except ISO currency codes and date bounds of non-restricted date columns.
- It is bound to each source's SHA-256 (captured before and after the read) and refuses to serialise once a
  source changes.
- It is diagnostic metadata, not evidence: `register_claims()` refuses it, so no profile reaches synthesis,
  recommendation or a decision.

---

## 6. Business Context (ADR-0011)

A first-class component, not configuration.

**Content** — identity and characteristics (business name, industry with taxonomy code,
business model, size band, products/services and categories, geographic markets); reporting
(fiscal year start, currency, number/date format, reporting period, output preferences);
analysis (KPI definition overrides, materiality thresholds, terminology glossary). Every
field optional; absence is handled by asking or narrowing scope, **never by guessing**.

**Storage** — `./.businessops/business_context.json`, gitignored, because context belongs with
the data it describes and consultants analyse many businesses. `~/.claude/businessops/` is
supported for single-business users. Project-local wins.

**Precedence** — `command argument → project business context → user business context →
shipped defaults`. Business Context *is* the business-specific configuration layer;
`config/businessops.defaults.json` is the shipped floor.

**Privacy** — confidential, classified field by field. A designated **externalizable subset**
— industry, business model, size *band*, geographic market, product *categories* — is what
Tier 0 research queries are built from (§7). Business name is externalizable only when the
analysis is explicitly about the user's own public company; otherwise Tier 2.

**Validation** — schema-validated on load; industry and business model from a controlled
vocabulary, with unrecognised values triggering a question. A contradiction between context
and data (context says GBP, data is USD) is a quality finding, never a silent override.

**User override** — any field overridable per command; changes confirmed and recorded.

**KPI relevance** — the registry gains `applicable_models`, and the engine returns a fourth
bucket:

| Bucket | Meaning |
|---|---|
| `computed` | Inputs present, model-relevant |
| `partial` | Computed on incomplete periods, flagged |
| `unavailable` | **Inputs missing** — the specific field is named |
| `not_applicable` | **Inputs may exist, but the business model makes it meaningless** |

A SaaS business sees ARR, MRR, NRR, churn; a retailer sees AOV, inventory turnover,
sell-through, same-store sales; a services firm sees utilisation, billable hours,
realisation, project margin. Without Business Context nothing is suppressed — the output
notes that relevance filtering is off and offers to set it up.

**Consumption** — loaded at pipeline step 1; shapes information requirements (2), external
query construction (5), KPI selection (8), materiality (10) and output formatting (18).

---

## 7. External research, privacy boundary and evidence

### The disclosure model (ADR-0009)

Confidential raw internal data must not be transmitted unless explicitly authorised.
Aggregated, anonymised or derived context may be used where it reveals nothing confidential.

**Tier 0 — Local join (default; covers substantially all comparative questions).** The query
is built **only** from public terms — industry, business model, geography, product category,
competitor names, period — drawn from Business Context's externalizable subset. The benchmark
returns, and the engine computes the comparison **locally**. No internal value is transmitted
and no approval is required.

| Question | Query sent | Internal data sent |
|---|---|---|
| "Our churn is 8%. How does that compare?" | `B2B SaaS churn rate benchmark 2026` | none |
| "Our revenue grew 12% vs competitors?" | `<competitor> revenue growth FY25` | none |
| "Our gross margin is 35% — typical?" | `<industry> gross margin benchmark` | none |
| "Given our product mix, what trends?" | `<product categories> market trends 2026` | none |

**Tier 1 — Derived-safe context** (auto-allowed only if it passes **all four** checks):
aggregation floor of at least *k* = 5 underlying entities; **banded, not exact** (rates and
ratios pass as-is, absolute monetary levels never pass); a whole-query re-identification
check, because industry + micro-geography + a narrow revenue band can identify a company even
when each part looks harmless; and not on the Tier 3 list.

**Tier 2 — Explicit user-approved disclosure.** The user sees the **exact text to be
transmitted**, verbatim, plus the destination, and approves **per query**. Never a
session-wide mode, never inferred from an earlier yes.

**Tier 3 — Never externalizable, no approval path.** Credentials, API keys, access tokens;
PII; customer names and customer-level records; individual transaction details; confidential
financial records and raw ledgers. The request is refused and the Tier 0 alternative offered.

**Enforcement.** Sensitivity class is a property of the *data*, attached from ingestion
onward. The gate runs at query construction, before any tool call, and writes its decision
plus the transmitted text to the evidence ledger, so what left the machine is auditable.
**Provenance is established by the gate, not asserted by the caller (ADR-0050).** On every
assessment the gate reads the business data files in the working directory, classifies their
columns with the ingestion rules, and screens every fragment of the request against the values of
the non-`public` columns: the subject, each term, each descriptor's label and value, the operation
id and the other metadata. It also refuses any exact figure in a Tier 0 term. A `never` value is
refused at every tier. Other internal material is refused below Tier 2 and offered the Tier 2 path
when it is in the query text; when it is outside the query text, it is refused at every tier. A
workspace that cannot be screened refuses (`internal_boundary_unverifiable`). The refusal says
that no research ran, and it names field, column and file, never the value.
The structural backstop: `bops-research-scout`, the agent that performs retrieval, **has no
file-system access** — it cannot read the dataset even if instructed to. Retrieved content is
untrusted input and can never raise a tier.

### Source tiering, recency, conflicts

| Tier | Examples | Use |
|---|---|---|
| A | Filings, official statistics, central banks, registries | Quotable as fact with attribution |
| B | Industry research houses, major business press, trade bodies, registered first-party company sources | Quotable with attribution and date |
| C | Vendor marketing, blogs, aggregators, undated pages | Corroboration only — never sole source |
| D | Unattributable, AI-generated, content farms | Excluded |

Tiers are recognised from the hostname alone, matched at a **DNS label boundary** — a
configured domain admits itself and its subdomains, never a host that merely contains it.
`fake-reuters.com` and `reuters.com.evil.example` are tier C. Anything else would let a
source choose its own tier by choosing a hostname, which is the control local classification
exists to provide. Classification is local, deterministic and offline; no DNS or certificate
check is performed.

Three tables are consulted in order — authoritative (A), established secondary (B), then the
**first-party company registry** (B, ADR-0018) — and an unrecognised host falls to C. The
first-party registry is an explicit map of a company's own domains, so
`news.microsoft.com` is tier B while `fake-microsoft.com` and `microsoft.com.evil.example`
are tier C. It is **B and never A**: tier A means independent of the subject, and a company
is the best-informed and most interested source about itself at the same time. There is no
heuristic anywhere that infers first-party status from a hostname, a subject name or a
record's own claims — an entry exists because a person added it, which is the property that
makes it safe.

Every item carries a publication date. Staleness windows: financials 1 year, market sizing
2 years, positioning 18 months; beyond them a claim is labelled dated, not current.
Conflicts are never averaged or silently resolved — both figures are shown with sources,
dates and definitions, the likely reason for divergence stated, and confidence lowered.

A conflict enters the evidence set **only by explicit declaration**, through the
`conflicts=` input to the retrieval-close path. The engine never infers one from differing
text: comparing prose to decide meaning is judgement, and the deterministic layer does not
perform it. A declared conflict is recorded as a conflict whatever the numeric spread —
sources can disagree about what a figure *means* while reporting similar numbers — with the
numeric verdict retained alongside. Source, tier, date and freshness for each position are
read from the evidence item it names, never supplied by the declarer, so a declaration
confers no authority. Only unresolved conflicts are representable; there is no resolution
state (ADR-0016).

Citations are captured at retrieval time and carried as data. A citation never captured
cannot be emitted; with no adequate source the answer is "no reliable source found".

**Where the scout trust boundary sits.** The runtime enforces the scout's *tool grant* and
nothing about its *reply*: a subagent returns unstructured text, and no frontmatter field,
dispatch parameter or output schema exists to constrain that (investigated in M9-C.7). The
return contract is therefore enforced in Python by `scout.parse_reply()`, which reads the
adopted production contract (ADR-0017):

```text
BOPS-REC/1 <operation> {one-line JSON record}
BOPS-END/1 <operation> <count>
```

**A line is a record only if it carries this retrieval's gate-bound operation id, and the
declared count must equal the number of such lines.** Those two checks replace the span
selection the parser refuses to perform: no judgement is made about which part of an untrusted
reply is "the real payload", because identity is carried by each line. The operation is minted
per retrieval and bound by the gate, so a page author — writing before the retrieval existed —
cannot author a matching line; and a line copied verbatim out of a page inflates the count the
scout committed to, which fails the whole reply. Prose around the record lines is ordinary
content: it cannot break the reply and cannot become evidence.

Everything fails closed and salvages nothing: a wrong operation, a count that disagrees, a
missing or duplicate terminator, a malformed record, or a reply in any other shape yields no
evidence at all rather than a partial set. Instructional compliance is not enforcement, and is
not treated as a control — which is precisely why the contract was shaped to what the model
reliably produces after fourteen consecutive live replies violated a shape it did not.

`bops.scout.result/1` remains as the **internal** canonical structure that `parse_reply`
assembles and `parse_result` validates; it is not a wire contract and a scout cannot send one.

**The trust split is the architecture.** What the scout controls is content; what Python
controls is authority:

| Scout-controlled (content) | Python-controlled (authority) |
|---|---|
| `source`, `reference` | operation identity, bound by the gate |
| `title`, `content` | query binding — the approved text, re-derived |
| `publication_date`, **only when the source states one** | disclosure authorisation and tier |
| `source_type`, `claim_kind` as reported | **source tier**, recomputed from source identity |
| which records it returns at all | provenance, evidence ids, trust marking |
| prose: process notes, conflicts, blocked fetches | freshness and staleness windows |
| | evidence acceptance and bounds |
| | conflict state |
| | candidate vs verified claim state |

A record arriving with `source_tier`, `trust`, `verified`, `freshness`, `may_stand_alone` or
`operation` set has those keys **dropped**, and the attempt is recorded in a note so a forgery
is visible rather than merely ineffective. A page that could name its own tier would name A.
There is no verified claim state to reach: `CANDIDATE` is the only claim status.

**A zero-record retrieval is absence of evidence, never evidence of absence.**
`BOPS-END/1 <operation> 0` with no record lines means the scout searched and found nothing
citable — a valid and often correct research answer. It yields `insufficient_evidence` /
`no_adequate_source` with **no `EvidenceSet` built**, no placeholder item, and no claim even
when one is proposed. It must never be read as establishing that the proposition researched is
false. A retrieval failure uses the same empty shape, with the reason in the scout's prose.
A *malformed* reply is a different outcome — `unavailable` / `retrieval_unavailable` — because
an empty result is an answer and a broken reply is a defect.

**Authorship of the records is part of the boundary, not an implementation detail.** The reply
contributes records; everything describing the retrieval — subject, disclosure tier,
destination, query text, operation, bounds — is re-derived from the gate-issued request, and
evidence ids, source tiers and trust markings are computed locally. Whatever produces the
records, the provenance is BusinessOps's. This is why the reply may not be transcribed or
repaired by the parent model (investigated in M9-C.8): the scout cannot read business data and
the parent can, so moving authorship to the parent would have the evidence ledger attribute to
an external source text written by the one context that has seen internal data. The disclosure
boundary would remain on paper and stop meaning anything.

**What none of this makes true.** A reliable transport is not a truthful source. Retrieved
content stays `UNTRUSTED_EXTERNAL_DATA` and may be wrong, stale, conflicting, incomplete or
low-quality; tiering, freshness, conflict recording and candidate-claim policy are what handle
that, and they run after every retrieval regardless of how cleanly it parsed.

### The research command surface

The research capability is reached two ways, and they are the same capability. A model
recognising a research question invokes the **skill**; a user typing the **command** gets
there explicitly. Both run the identical pipeline, because the command holds none of it.

`/company-analysis` (M9-D.1) is a thin orchestrator over `bops-company-analysis`. It validates
input, resolves Business Context for **public** disambiguating terms only, routes ambiguity
through the skill's existing protocol, invokes the skill, and presents what comes back. It
performs no retrieval, builds no evidence, tiers no source, proposes and verifies no claim,
and defines no output section — all of which are the skill's, and through it the engine's.

`/market-analysis` (M9-D.2) is the same shape over `bops-market-analysis`, and deliberately so:
the two commands are readable side by side because neither holds anything but sequencing. Its
five focus values — `overview`, `size-growth`, `trends`, `drivers-risks`, `full` — each name
**one distinct research question**, and each question is its own gate-authorised retrieval with
its own operation and its own single dispatch; `full` is four retrievals, not one broad query.
The skill owns the rule that makes market research different from company research: **two
market-size figures are not comparable until definition, geography, unit/currency, period and
methodology have all been checked**, and an unstated one fails the check rather than passing
it. Mismatches are recorded through the existing declared-conflict transport (ADR-0016), whose
per-position `definition` and `scope` fields exist for exactly this; nothing is averaged, no
midpoint is taken, no currency is converted. A source's forecast or CAGR stays that source's
estimate with its stated period — never restated as a BusinessOps forecast, which is
`bops-forecasting`'s output from the user's own data. Section 7 of its output describes market
*structure* only; competitor profiling is `/competitor-analysis`.

**`/competitor-analysis` → `bops-competitor-analysis`** (M9-D.3) is the third, and the same
shape again: a thin orchestrator over a skill that owns all the judgement. It takes one focal
company, an optional user-supplied competitor list and one of five focus values —
`landscape`, `comparison`, `positioning`, `developments`, `full` — each a distinct
gate-authorised retrieval with a single dispatch, `full` being four. Where no competitors
were supplied, `landscape` runs first, because the comparison question needs names and
inventing them is the failure this skill exists to prevent.

Two rules make competitor research different from the two before it. The first is
**evidence-based identity**: a company is a competitor only where a source states the
relationship. A tier A or B source that states it yields `identified`; a single, tier C or
undated statement yields `observed`, which is reported as an observation and never promoted;
a mere mention, a search hit or an overlapping product category yields nothing at all. A
user-supplied name is preserved verbatim, never substituted, and stays labelled where the
evidence does not support its relevance — it is neither granted relevance nor dropped for
lack of it. The shortlist is bounded at roughly three to five and is never padded to reach
a length. The second is **comparison without ranking**: the skill defines ten observable
dimensions and no scoring system at all — no 1–10 ratings, no weighted totals, no composite
competitive score — because the repository holds no metric contract for competitive strength
and M9-D.3 does not add one. Missing cells stay missing and never become zero; incomparable
figures are marked not comparable rather than related; market share is calculated only where
a supported denominator exists on a compatible definition, geography, period and basis, and
otherwise reported as unsupported. A company's claim about itself — leadership above all — is
attributed to that company and never restated as independent fact.

**The ranking boundary is deliberate.** A ranking is a decision presented as an observation,
and producing one would make competitor analysis into decision support without the evidence,
rationale, expected benefit, risk, dependency and confidence structure a class 7
recommendation requires. The skill therefore declines a ranking **even when asked directly**,
and presents the underlying comparison instead. Strategy — which competitor to copy, acquire,
avoid or price against — is `bops-strategy-recommendations` (Milestone 10).

**Research commands carry no entry in `bops.commands.registry`**, unlike the nine analytics
commands. That registry drives a dataset pipeline: it declares mapping roles, an analytical
domain, a KPI focus and an engine, and `commands.run()` ingests a file. A public-source
research command has no file, so a spec would have to invent every field in it. The markdown
orchestrator is the whole command, discovered from `commands/*.md` like any other (§2), and
a test asserts the absence so the two surfaces cannot quietly merge.

**`/industry-research` → `bops-industry-research`** (M9-D.5) is the fourth and last of the
research commands, the same thin shape again. It takes one industry — no company, and no
competitor list — and one of six focus values: `overview`, `size-growth`, `trends`,
`drivers-risks`, `structure`, `full`. Each is a distinct gate-authorised retrieval with its
own operation and single dispatch; `full` is five.

**Its analytical object is the industry as a system**, and that is what keeps three
overlapping skills apart. `bops-market-analysis` asks how large a defined market is and what
the demand looks like; `bops-competitor-analysis` asks who competes and how named companies
compare; `bops-industry-research` asks what the industry is, how it is organised, what moves
it and what constrains it. They draw on overlapping evidence and answer different questions,
and each names the other two so a misdirected request is routed rather than answered badly.

Two rules make industry research different. The first is that **nothing is scored.** There is
no metric contract in this repository for industry attractiveness or competitive intensity and
M9-D.5 does not add one, so there is no attractiveness index, no Porter's Five Forces rating,
no 1–10 scale, no weighted total and no ranking of industries, segments or companies —
declined **even when asked directly**, for the reason the competitor-ranking boundary exists:
a score is a decision presented as an observation. The framework's vocabulary may be quoted
where a source used it, attributed to that source. The second is **structure without
competitor drift**: companies appear only as sourced examples of participant *kinds*, and a
company named as an example is never promoted to a competitor, a leader or a major player.
Concentration is reported only where a source measured it, with that source's definition,
geography, period, denominator and methodology; it is never inferred from how many companies
happened to be mentioned, never calculated without a supported denominator, and never turned
into a ranking. Industry size and growth inherit the market-sizing discipline with a sixth
check added — definition, geography, period, currency/unit, measurement basis **and**
methodology — and a source's CAGR stays that source's estimate.

All four research commands are now built.

### The synthesis layer (ADR-0022)

`lib/python/bops/synthesis/` is the shared intermediate representation between the two
information domains and Layer 3. It is where internal analysis and external evidence sit in
one object for the first time, which is also the only place promotion could occur — so
every guarantee it makes is structural rather than procedural.

**Inputs.** `AnalysisSet` and its subclasses (`ForecastSet`, `AnomalySet`), `KPIResult`,
`EvidenceSet`, candidate claims, `Limitation`, `MaterialityVerdict`, and the resolved
config. Typed objects only: a serialised evidence set is refused, because it would carry
`source_tier` as data and a tier is derived from a source's identity, never accepted.

**The retrieval seam (ADR-0024).** Because the evidence set must arrive as an object,
`research.close_retrieval_object()` returns it as one — under `evidence_set`, with no
`evidence` key — while `close_retrieval()` keeps returning the serialised form unchanged.
Both delegate to one private `_close()`, so there is a single retrieval assembly and no
second pipeline. The production flow is
`completed retrieval → EvidenceSet object → synthesis.register_external()`.

**Output.** `SynthesisSet`, serialised to `lib/schemas/synthesis.schema.json` with sorted
keys and stable ordering, so the same inputs always produce the same bytes.

**Canonical quantities (ADR-0025).** A statement's `unit` names a **quantity type** and
nothing else, drawn from one closed vocabulary in `kpi.contract` — `currency`, `percent`,
`ratio`, `count`, `days`, `percentage_points`. The magnitude lives in the `Decimal` value in
base units, the currency code in its own field, and display formatting in `render`. A
magnitude-qualified label such as `"USD billion"` is refused at `SynthesisItem` construction
and by the schema, because `compare()` tests this dimension by exact equality and two
statements sharing a `"USD billion"` label would match while holding values a billion apart.
`bops.quantity` decomposes a source's published notation into that canonical form **at
statement construction** — `synthesis.sourced_statement(source_unit=…)` is the seam — and
never inside `compatibility.compare()`, which converts nothing and is unchanged by the rule.
Rescaling a magnitude the source already stated is not conversion; a currency conversion
needs a rate this codebase does not hold, and remains prohibited with no approval path.

**Dimension admissibility (ADR-0026).** A dimension value alone does not establish
anything; a **footing** does. `synthesis.dimension_provenance.DimensionProvenance` records,
per dimension, the value, the basis it rests on, the evidence item it cites, the verbatim
source excerpt, the locator, and the period and scope the footing governs. Four bases exist
and three are admissible:

| Basis | Means | Admissible |
|---|---|---|
| `stated` | the dimension is in the statement's own cited evidence | yes |
| `context` | it is elsewhere in the **same source document**, cited as evidence | yes |
| `derived` | a closed, fail-closed rule read it from text the source printed | yes, for `unit` and `currency` only |
| `asserted` | somebody said so | **never** — recorded for audit, reads as unstated |

`SynthesisSet.add()` resolves the footings against the evidence registry — the same place
`_require_internal_footing()` runs, and for the same reason: resolution needs the
registries. A footing is admitted only if its evidence is registered, shares the statement's
retrieval operation, is the same document for `context`, quotes text genuinely present in
the retrieved content, and declares applicability to the statement's period and scope. What
survives populates `SynthesisItem.dimensions`, which is what `compatibility.compare()`
reads; what does not reads as `None` and fails the comparison on `unknown`.
`declared_dimensions` keeps the unresolved view for audit.

**Containment is proved; meaning is not.** The excerpt check establishes that the quoted
text really is in the source, not that it *means* the value. That boundary is stated rather
than implied. **No rule may derive `geography` or `methodology`**, source type may never
establish methodology, company identity may never establish geography, and cross-source
context is prohibited. **A `stated` or `context` footing for `currency` is
admissible only where its excerpt prints the ISO 4217 code it claims** (ADR-0027): a bare
`$`, `£`, `€` or `¥`, a currency *name*, and an excerpt naming two currencies each
establish nothing, which is ADR-0025's rule held at the admissibility layer as well as at
canonicalisation. Conflicting admissible footings leave the dimension unresolved and
record a conflict — never a winner by recency, tier or order. Admissibility confers no
trust, verification, support or confidence: external evidence stays `SOURCED` and untrusted.
The mechanism is **additive** — a dimension with no footing is passed through unchanged, so
unmigrated callers are unaffected; `SynthesisSet(require_dimension_provenance=True)` closes
that gap for callers who opt in.

**Footings are authored through one shared helper.** `synthesis.source_footings()` builds one
`stated` or `context` footing per dimension from `(value, source_excerpt)` pairs against one
cited evidence item, so the research skills share a single authoring convention rather than
one each (ADR-0027 §17). It is deliberately powerless: it constructs `DimensionProvenance`
objects and performs no evidence lookup, operation or document binding, containment,
applicability or currency check. All of those stay in resolution, and a footing the helper
built is judged exactly like one written by hand. `derived` and `asserted` are not authorable
through it - the first reads notation rather than a quote, and the second establishes nothing.

**One seam carries a research command from a completed retrieval to a footed statement
(ADR-0028).** `synthesis.footed_statement()` sequences what already exists — the evidence
object from `close_retrieval_object()`, `register_external()`, `source_footings()`, the one
`derived` `unit` footing ADR-0025 canonicalisation permits, and
`sourced_statement(dimension_provenance=…)` — onto a set built with
`require_dimension_provenance=True`. It is **strict by construction**: the evidence must be
the object a completed retrieval produced, the set may not be a loose one, a dimension is
either footed or declared and never both, and a `context` footing names its own evidence
item rather than defaulting to the statement's. Like the authoring helper it calls, it
decides nothing — no evidence lookup, no operation or document binding, no containment,
applicability or currency check — so a footing it built is judged by `resolve()` exactly as
one written by hand. ADR-0026's additive default is unchanged for every other caller;
`sourced_statement()` still passes an unfooted dimension through. `/company-analysis` is the
first command to reach the strict path through this seam, and the remaining three research
skills migrate by calling it rather than by copying it.

**The seam carries a second research domain with no engine change (M10.2-R.11).**
`/market-analysis` reaches the same strict path by calling `footed_statement()` with
`ORIGIN_MARKET`, and that migration added no production code at all: the seam is
origin-agnostic, `compatibility.compare()` reads seven dimensions without knowing which
domain produced them, and neither side of a comparison has to be internal. Market sizing
exercises two things Company Analysis does not. Its characteristic comparison is
**external-to-external** — whether two *published* sizes measure one quantity — which the
same call answers, recording a limitation rather than a cross-domain conflict because
neither figure is the user's. And it is where `scope` earns its place as the seventh
dimension: a total addressable market and a served market can share a definition, a
geography, a period, a currency and a method and still be different quantities, so the
skill's five-check table folds `scope` inside "definition" while the engine asks it
separately — stricter, never weaker. The same asymmetry makes a market *share* correctly
`incompatible` on `scope`: a numerator and a denominator are not two measurements of one
thing.

**A third domain, and the one where the entity is deliberately absent (M10.2-R.12).**
`/competitor-analysis` reaches the same strict path with `ORIGIN_COMPETITOR`, again with no
production code. Its characteristic comparison is one rival's figure against another's, and
`compatibility.compare()` has **no company dimension** — correctly, because the whole purpose
is to put different companies' figures beside one another. Which company a figure belongs to
lives in the statement, its cited evidence and its row label, never in the comparability
check. That makes the boundary explicit rather than implied: **a compatible verdict
authorises a row, not an order.** It establishes that two figures measure the same quantity
on the same basis; it produces no ranking, no superlative, no market share (a compatible pair
of revenue figures is two numerators and no denominator), and it never promotes an `observed`
competitor to an `identified` one — relevance is decided on evidence of the *relationship*
and is untouched by a dimension resolving. Competitor Analysis also gives `scope` its sharpest
reading: consolidated group versus named segment, so a worldwide group figure and a worldwide
segment figure share a `geography` and remain different quantities. And because two companies'
filings are always two documents, ADR-0026's cross-document prohibition is not an edge case
here but the normal shape of the data.

**The fourth domain completes the set, and gives `scope` its clearest reading (M10.2-R.13).**
`/industry-research` reaches the same strict path with `ORIGIN_INDUSTRY`, again with no
production code, so all four research commands now share one seam and ADR-0028's follow-up is
closed. Industry sizing is where the seventh dimension was already written down: this skill's
six-check table maps onto the engine's seven almost one to one — six rows, one split — and its
*measurement basis* row **is** `scope`. Gross output, revenue, value added, shipments and
employment are different quantities, and two honest releases can size one industry in one year
and differ by a factor of two purely because they measured different ones; the engine returns
`incompatible` on `scope` while `geography`, `period` and `methodology` all match.

Industry Research also fixes the semantics of a comparison the other three rarely make:
**current period against prior.** Two figures for two periods are `incompatible`, correctly —
they do not measure the same quantity. What makes a change-over-time reading defensible is not
a compatible verdict but `incompatible` with `period` as the **only** mismatched dimension,
six matched and none unknown. That precondition is visible in the result and is what gets
reported; no growth rate follows from the pair. A publication date establishes nothing in
either direction: two releases published a year apart that state the same period are
comparable, and two published on one day that state different periods are not.

**The local join makes the internal half reachable (M10.2-R.14, ADR-0029).** R.10–R.13
delivered the external half; `from_analysis_set()` and `from_kpi_result()` were still called
by nothing outside the test suite, so ADR-0009's default capability — fetch the public
benchmark and compute the comparison locally — had no user-reachable surface.
`/benchmark-comparison` and `bops-benchmark-comparison` are that surface, and
`commands.local_join()` is its engine seam: `commands.run()` → the M10.1 translators for our
figure, `close_retrieval_object()` → `footed_statement()` for theirs, one strict
`SynthesisSet`, then `compare_values()`. The seam **sequences only** — it computes no figure,
authors no footing, resolves no dimension and holds no privacy rule.

**It lives in the orchestration layer, and the privacy guarantee is structural.** A local
join needs a `CommandResult`, which the command layer owns, and `synthesis/` may not depend
upward (§2.3) — so the seam sits in `commands/` and the synthesis package still knows nothing
about commands. It imports no gate, no query builder and no retrieval request, so it
*cannot* construct or alter an outbound query; it receives a retrieval that has already
closed, which puts the join strictly after retrieval and leaves the internal figure nowhere
to go. Provenance stays independent in both directions: our figure remains an internal
`CALCULATION`, evidence class 4, engine-footed on the registered dataset (ADR-0023) with no
dimension provenance, and theirs remains `SOURCED`, class 3, untrusted, with seven footings.
A `compatible` verdict permits the two to be reported side by side and authorises no
arithmetic, no ranking and no verdict. `from_kpi_result()` gained the four dimension
parameters `from_analysis_set()` already had — additive, all defaulting to `None`.

**Footing is required of quantitative claims, not of research.** A market report is mostly
qualitative — trends, drivers, constraints, structure — and those statements carry no
footings and get no compatibility verdict; they remain cited, dated, tiered
`SOURCED` evidence through `sourced_statement()` unchanged. Only a figure that could be set
beside another figure takes the strict path, because that is the only situation in which an
unstated dimension becomes a false match. Both kinds share one strict set: a qualitative
statement may still declare a period and geography for the report, which `as_dict()` keeps,
while `dimensions` reads them as unstated — the correct outcome for a statement nobody is
comparing.

**Source context travels in the evidence record that already exists (ADR-0027).** A footing
needs dimension-bearing source text to quote, and that text arrives in the `BOPS-REC/1`
`content` field — no new field, no new record type, no second protocol and no scout-supplied
dimension, tier or trust. The scout is asked, in `agents/bops-research-scout.md`, to capture the
passage stating a figure together with the source-stated context around it, and to supply
nothing the document does not state. Python remains the authority: the scout retrieves, the
model quotes, and admissibility is decided here.

**Statement kinds and the domain constraint.** Four kinds are imported from
`analytics.contract`; one — `SOURCED`, evidence class 3 — is added for *a named public
source said this*. Kinds are then constrained by domain:

| Domain | Permitted kinds |
|---|---|
| internal | `FACT` · `CALCULATION` · `INTERPRETATION` · `ASSUMPTION` |
| external | `SOURCED` · `INTERPRETATION` · `ASSUMPTION` |

There is no kind for external material to become an internal fact *as*. `RECOMMENDATION`
is reserved and refused everywhere; the serialised result carries a permanently empty
`recommendations` array so downstream consumers find the shape without finding advice.

**Internal footing (ADR-0023).** The table above is necessary and not sufficient, because
it is evaluated against the origin the *caller declared*. So a second, independent check
runs at `add()` time: a `FACT` or `CALCULATION` in the internal domain must carry at least
one provenance reference that **resolves against this set's registries** to an internal
source — dataset, calculation, KPI, finding, forecast or anomaly. `domain`, `origin`,
`trust`, `evidence_class`, caller-supplied confidence and the tier on the cited object are
all deliberately not consulted; every one is caller- or payload-influenced. The rule is *at
least one* internal reference, not *only* internal ones. `lib/schemas/synthesis.schema.json`
mirrors the constraint for records that never met the object model, but the runtime is
authoritative — a schema validates output, and this must refuse the object at construction.

**The asymmetry between the domains is deliberate.** Internal findings become statements
automatically — the engine produced them from the user's data and they already carry their
basis and materiality. Registering an `EvidenceSet` creates **no** statements: it makes
items citable and conflicts visible, and turning "this source says X" into a statement is a
reading, which comes from a skill through `sourced_statement()` naming the evidence it
rests on.

**Provenance.** Every statement carries at least one reference, resolved against the
objects the set was actually given; an unregistered id raises. Where provenance genuinely
does not exist it is `unavailable` *with a reason*, which grades the statement
`insufficient_evidence`. `chain()` and `provenance_index()` answer "where did this come
from" from data.

**Support** is a four-state view of the M9 policy, not a second one —
`supported` / `partially_supported` / `unsupported` / `insufficient_evidence`, mapped from
`sources.assess_support()` with the fourth state added for *nothing was linked, so we could
not check*. A statement citing both domains takes the **weaker** of its two legs.

**Conflicts** are preserved, classified (definitional, numeric, scope, temporal,
methodology, internal/external) and never settled: no midpoint, no winner, no tier-weighted
resolution. They are lifted automatically from every registered evidence set and there is
no API that removes one.

**Materiality** is carried across from the configured policy, never re-judged.
**Limitations** only accumulate; the sole reduction is exact deduplication.
**Confidence** is qualitative and derived from named reason codes — one ordinary reason is
`MEDIUM`, two or one severe reason is `LOW` — and is never a probability.

**Consumers:** `bops-swot`, `bops-strategy-recommendations`, `bops-decision-support`,
`bops-executive-report`. M10.1 is the foundation they read. `bops-swot` (M10.3.1),
`bops-strategy-recommendations` (M10.3.2), `bops-decision-support` (M10.3.3) and
`bops-executive-report` (contract M10.3.4, ADR-0033) are all built.

**The first consumer: a SWOT point is a placement, never new text (M10.3.1, ADR-0030).**
`lib/python/bops/swot.py` reads a genuine strict `SynthesisSet` — `type(...) is`, built with
`require_dimension_provenance=True`, non-empty, every item graded by `add()` — and nothing
else: no file, no KPI engine, no retrieval, no command. A point is a placement of **one
statement already in the set** into one quadrant, `{quadrant, tag, synthesis_id}` and no
other field, so there is nowhere for unsupported text, a score, a rank or a recommendation to
go. Its text, kind, support, confidence, conflicts, materiality, limitations, caveats and
provenance chain are the statement's own. The tag is **derived from the kind** and a
disagreeing claim is refused, never relabelled:

| Kind | Tag | Quadrant side |
|---|---|---|
| internal `FACT` · `CALCULATION` | `data-supported` | Strengths · Weaknesses |
| external `SOURCED` | `externally-sourced` | Opportunities · Threats |
| `INTERPRETATION` | `analytical-inference` | any side at least one evidential support is on |

A reading not already in the set is authored first through `merge.interpretation()`, which
requires supports and refuses advisory wording. The consumer reads those supports back through
`merge.interpretation_supports()` — an additive reader beside the writer, the note's prefix
spelled once — and refuses an inference whose supports are missing, later than the reading,
circular, rest on an `ASSUMPTION`, or fail to account for exactly the provenance the reading
carries. Statements graded `unsupported` or `insufficient_evidence` are not points. Conflicts,
limitations and the set's confidence are carried whole, never filtered to the placed points; an
empty quadrant carries an explicit empty state; unplaced material statements are listed; point
order is set order and is stated not to be a ranking. **Which quadrant** is the model's reading
in `bops-swot` and requires human review; **whether it is grounded** is decided here. The output
has its own closed schema, `lib/schemas/swot.schema.json`; `synthesis.schema.json` is unchanged.
`/swot-analysis` sequences the existing internal analysis, the existing research skills and the
local join into one strict set and hands it to the skill — it retrieves, computes and discloses
nothing itself.

**The recommendation contract: beside the set, never inside it (M10.3.2-A, ADR-0031).**
Decided in M10.3.2-A, built in M10.3.2. A strategy recommendation is a **class-7 record** whose ledger form is
`evidence.Claim(provenance_class=RECOMMENDATION)`, held in a `StrategyResult` that **references**
one genuine strict `SynthesisSet` and never writes to it. The synthesis `recommendations` array
therefore stays a permanent empty marker and `synthesis.schema.json` keeps `maxItems: 0`; this
refines ADR-0022 §5's sentence that downstream milestones would fill that array, while keeping
its substance — recommendations are unproducible by the synthesis layer and issued through
`evidence.Claim` with all six fields.

| Rule | Contract |
|---|---|
| Authored fields | exactly `action`, `evidence` (synthesis statement ids), `rationale`, `expected_benefit`, `risks` (list), `dependencies` (list of `{text, assumption_id}`); no aliases, none empty |
| Evidence | resolves in one genuine strict set; `FACT`/`CALCULATION`/`SOURCED`, or `INTERPRETATION` with ADR-0030-verified supports; at least one class 1/3/4 basis; `unsupported`/`insufficient_evidence` refused |
| Assumptions | only as a dependency's `assumption_id`, never evidence; recommendations never cite recommendations |
| Confidence | derived, never authored: `confidence.combine()` over the cited statements' and assumptions' own reason codes — weakest level, reasons pooled. Conflicts, assumptions and unavailable provenance make it `LOW` |
| Figures | quoted from cited statements only; no new figure, gap, ratio, projection or estimated benefit (ADR-0002, ADR-0029) |
| Carried | per-evidence kind, domain, trust, class, support, materiality (never re-judged), conflicts, unresolved dimensions, limitations, caveats; set conflicts and limitations whole |
| Order | multiple allowed; deterministic by earliest cited statement, stated not to be a ranking; no priority, rank, score or weight |
| Owner | no personal field: `issued_by` names the issuing capability; the business decision is the user's (step 19) |

The advisory guard is untouched, because recommendation text never becomes a `SynthesisItem`.
Strategy consumes the set directly and has no SWOT dependency; Decision Support shares this
record contract; Executive Report may assemble recommendation records but never authors, edits
or re-grades one. BusinessOps never executes a recommendation (§8).

**How the contract is enforced (M10.3.2).** `lib/python/bops/strategy.py` is the engine and the
only producer. `build(synthesis, proposals)` accepts exactly the six authored fields and returns a
`StrategyResult` that only `build()` can construct (a module-private token), holding the set
**object** and a SHA-256 digest of its serialisation; `claims()` and `as_dict()` refuse once the
set has changed, so a result cannot lend its confidence to evidence it no longer describes.
Four pieces make the rules structural rather than advisory:

- **One home for grounding.** The ADR-0030 checks — genuine strict set, every item graded, one
  statement per id, evidence kinds, disqualifying support, and interpretation supports that exist,
  precede, are not circular, reach evidence and account for the provenance carried — moved out of
  `swot.py` into `synthesis/grounding.py`, which knows neither consumer. SWOT and Strategy both
  call it and report its refusals as their own errors; SWOT's behaviour is unchanged.
- **No re-entry.** `SynthesisSet.register_claims()` refuses any record that is, or is dressed as, a
  recommendation — class 7, a `RECOMMENDATION` label, kind or finding type, or any field only a
  recommendation carries. Genuine candidate claims are unaffected.
- **Class-7 shape in the ledger.** `evidence.Claim` refuses a class-7 claim whose evidence is not a
  list of distinct synthesis statement ids, whose risks or dependencies are not non-empty lists of
  the canonical shape, whose confidence is not a level, whose `based_on` is anything but its
  evidence ids, or which carries any other field. Resolution against the set stays the engine's,
  because `evidence.py` sits below synthesis. `claim_ledger.schema.json` enforces the same shape
  through an `anyOf` the in-repo validator applies.
- **Figures quoted, never produced.** `figure_tokens()` reads dates, figures (grouping, scale words
  from `bops.quantity`, percent, percentage points, currency code or symbol, sign — exact `Decimal`,
  no rounding), number-bearing identifiers and — since M10.3.3 — cardinal number phrases
  (`twenty-five` = `twenty five`, matched only as a whole phrase) as distinct classes;
  `require_grounded()`
  refuses any the cited statements do not print, including an unmarked figure that matches cited
  figures in two currencies.

The output is `lib/schemas/strategy.schema.json`, closed at every level; `synthesis.schema.json` is
unchanged and the set's `recommendations` array stays empty.

**The decision-support contract: a twelve-part draft package beside the set (M10.3.3-A,
ADR-0032).** Built in M10.3.3 (`lib/python/bops/decision_support.py`). `bops-decision-support`
produces a `DecisionResult` beside one
genuine strict `SynthesisSet`, structuring a **user-supplied decision question** into twelve parts:

| # | Part | Contract in brief |
|---|---|---|
| 1 | `decision_question` | Required, user-supplied, framing — never inferred, never evidence |
| 2 | `business_context` | Framing only (`subject`, `business_model`, `currency`); constraints are user-supplied |
| 3 | `objective` | User-supplied or recorded as not stated — never inferred |
| 4 | `options` | At least two: user-supplied, one per class-7 record in guidance, and the status quo. No option generator — a model-proposed option is an ADR-0031 record |
| 5 | `criteria` | User-supplied, or a configured materiality threshold the user asks for; no weights, scores or ranks |
| 6 | `evidence` | Index of every synthesis statement the package cites, resolved through `synthesis/grounding.py`; at least one |
| 7 | `assumptions` | Registered `ASSUMPTION` statements named by records or tradeoffs; never evidence; each makes its referrer `LOW` |
| 8 | `tradeoffs` | Records: options, optional criteria, text, at least one evidence id, derived confidence |
| 9 | `risks` | Per-option records; evidence optional, unevidenced risks labelled and `LOW`; no likelihood or severity |
| 10 | `expected_outcomes` | Per-option records, at least one evidence id, figures quoted only |
| 11 | `guidance` | ADR-0031 class-7 records (Strategy's packaged unchanged, Decision Support's issued as `bops-decision-support`), at most one preferred option under a strict grounding rule, and visible `divergences` |
| 12 | `uncertainty` | Derived package and per-option confidence, conflicts, limitations, unresolved dimensions, and next steps that are evidence gaps, never actions |

Everything is inherited rather than invented: one recommendation contract (ADR-0031), the ADR-0031
figure rule on every authored text, `confidence.combine()` for every derived level (an unassessed
option is `LOW` with `insufficient_evidence`), materiality never re-judged, Business Context never
evidence. **A preferred option** exists only when criteria exist, the option has a class-7 record
whose evidence the package relates to those criteria, every other option is assessed against the
same criteria or labelled not assessable, and the basis is named; otherwise none is stated and the
reason is. Nothing is scored, weighted or ranked, and option order is presentation. `StrategyResult`
is optional and must be bound to the same set; SWOT is not an input; Strategy records are never
edited, and a disagreement is shown, not settled. **Every result before M11 is a `draft`**; "finalise"
(§10) means the M11 verifier moving a draft to `final`. Executive Report may assemble packages and
never re-authors them.

How M10.3.3 enforces it, without a second copy of any rule:

- **Shared record builder.** `strategy.ground_recommendation()` is the one home of the ADR-0031
  record rules and takes `issued_by` from `strategy.RECOMMENDATION_ISSUERS`; Strategy's own
  behaviour and schema constant are unchanged. `strategy.cite()` is the one evidence-citation rule
  (one statement, never an assumption, readable through `grounding`) for records, tradeoffs, risks
  and outcomes alike, and `strategy.require_grounded()` is the one figure rule.
- **Closed request.** `decision_support.build(synthesis, request, strategy_result=None, config=None)`
  accepts a fixed set of request fields; options are referred to by label and criteria by text, and
  the engine assigns content-addressed ids (`opt-`, `crit-`, `trd-`, `rsk-`, `out-`). The status quo
  is labelled *Make no change* and excluded with `include_status_quo: false`. The question is
  checked structurally only — missing, non-text or blank is refused, anything else is kept exactly
  as written; whether it is ambiguous is judged by the skill and command, which ask the user. A
  configured threshold
  becomes a criterion only from a `ResolvedConfig`, with its key and layer as `source`.
- **Preferred option.** The §10 conditions are checked over the named basis as a whole, with no
  tradeoff required per criterion: at least one criterion exists; the option has a class-7 record,
  and at least one tradeoff about the option names a basis criterion and cites a statement that
  record cites (those criteria are what the preference rests on); every other option appears in a
  tradeoff naming one of those criteria or is labelled not assessable; and `preference_criteria`
  names the basis. Only tradeoffs can carry this, because §2 gives expected outcomes no criteria.
  Failure yields one of six fixed reasons.
- **Draft only.** `DecisionResult` is built only by `build()`, binds the set object and its digest
  (and any `StrategyResult`'s binding), refuses to serialise once either changes, and has no path to
  `final`. `lib/schemas/decision_support.schema.json` is closed at every level; its mirrored record
  definitions are pinned to `strategy.schema.json` by test.
- **No re-entry.** `register_claims()` refuses a package and every part of one — package-only fields,
  `analysis: decision_support`, and the user and status-quo framing origins.

**The executive-report contract: an assembly over one set, authoring nothing (M10.3.4, ADR-0033).**
Built (`lib/python/bops/executive_report.py`). `bops-executive-report` produces an
`ExecutiveReportResult` beside one genuine
strict `SynthesisSet` (not `CRITICAL`), assembling that set's statements and, optionally, one
`StrategyResult` and zero or more `DecisionResult`s bound to the same set object, and one SWOT record
accepted only when its placements rebuild it exactly over that set. `AnalysisSet`, `KPIResult`,
`AnomalySet`, `ForecastSet`, `EvidenceSet` and `CommandResult` are **not** direct inputs: they reach the
report only through the set, as ADR-0022 requires. The report authors no sentence of analysis, no
recommendation and no summary prose; every business statement it shows is a synthesis statement, a
class-7 record or a decision-package part, verbatim, with its own confidence and materiality.

| # | Section | Contract in brief |
|---|---|---|
| 1 | `reporting_frame` | Lifecycle label; quality warning before any figure; set metadata; user framing (period, audience, objective, questions, constraints) — never evidence; thresholds applied and their layer |
| 2 | `executive_summary` | A rule, not prose: every material evidential statement or verified interpretation, verbatim, in set order; ids of material statements not supported; count with no materiality verdict; Strategy records by id and action; each package's question, lifecycle and preference or no-preference reason; the set's confidence |
| 3 | `kpi_scorecard` | One row per registered `KPIResult` in catalogue order; status, value, statement confidence and materiality; prior/change only from the statement itself; no targets, ratings or colours |
| 4 | `findings` | Other evidential statements (classes 1/3/4), then interpretations (class 5), set order |
| 5 | `anomalies` | Anomaly statements with the investigation note; no cause, never "fraud" |
| 6 | `outlook` | Forecast statements with resolvable forecast provenance only — **always `not_available` until a synthesis forecast translator is separately approved** |
| 7 | `swot` | The verified SWOT whole (ADR-0030) |
| 8 | `strategy_recommendations` | The `StrategyResult` whole, unchanged, in its own order (ADR-0031) |
| 9 | `decision_support` | Each package whole, all twelve parts, lifecycle shown (ADR-0032) |
| 10 | `evidence_and_uncertainty` | Set confidence, conflicts, limitations, assumptions, statements not supported |
| 11 | `decisions_for_the_reader` | Human-decision statement; open decision questions; recommendation ids awaiting a decision; package next steps by reference |

Every section is always present; an optional one with nothing to show states `empty`, `not_supplied`
or `not_available`. **Prohibited:** "going well / needs attention" (SWOT owns placement), standalone
risks or opportunities sections, any overall or health score, KPI ratings, targets, "top" or "best",
severity, likelihood, action plans. **Executive Report issues no recommendations** and computes no
confidence of its own. It is built only by `build()`, bound to the set's digest and each component's
binding or digest, has a content-addressed `report_id`, never re-enters synthesis, and never retrieves:
the command may sequence the existing research and Layer-3 skills over one set object, as the other
synthesis commands do. **Every report before M11 is a `draft`**; the verifier recomputes headline
figures and confirms bindings and wholeness, and a `final` report may not contain a draft package.

How the implementation enforces it, without a second copy of any rule:

- **One reading of the set.** Every statement is classified once, in set order, through
  `synthesis/grounding.py`: `evidence_domains()` decides whether it may be shown as evidence, and
  `strategy.statement_detail()` produces the same per-statement detail Strategy and Decision Support
  carry. Assumptions, and statements grounding refuses (with its reason), go to
  `evidence_and_uncertainty`; none is dropped. An id the set holds twice refuses the report.
- **Read-only registry views.** `SynthesisSet.registered_kpis()`, `registered_datasets()` and
  `registered_evidence_sets()` were added so the scorecard and frame read what the set registered
  without touching its private registries; `DecisionResult.strategy_result` exposes the result a
  package was built with so the report can require the same object. All additive.
- **Binding.** `build()` records the set digest, the `StrategyResult` and each `DecisionResult` with the
  SHA-256 of its serialisation, and the SWOT record with the digest its placements reproduce;
  `as_dict()` and `to_json()` re-check every one and refuse on any change, including tampering with a
  component's private state.
- **Closed schema.** `lib/schemas/executive_report.schema.json` imports the Strategy, SWOT and Decision
  Support schemas under `strategy_`, `swot_` and `decision_` prefixes, pinned to their sources by test;
  report `lifecycle` is `const "draft"` until M11 defines `final`, and `outlook` is `const
  "not_available"`.
- **No re-entry.** `register_claims()` refuses a report, every section, and every entry carrying a
  report-only field (`report_id`, `section_order`, `statement_detail`, `synthesis_id`, `kpi_id`,
  `point_id`, `lifecycle_label` and the section names), and `analysis: executive_report`.
- **No bypass.** `build()` has no parameter for a KPI, anomaly, forecast, evidence or command object; the
  module imports none of those engines.

**The verification and finalisation contract: integrity, not endorsement (M11, ADR-0034, ADR-0035).** Built
(`lib/python/bops/verification.py`, `verification_server.py`, `agents/bops-analysis-verifier.md`). The verifier
is the deterministic module `lib/python/bops/verification.py`; the
`bops-analysis-verifier` agent (§10) is only the isolated context for blind recomputation. It verifies and
finalises **draft `DecisionResult`s and draft `ExecutiveReportResult`s**; the set, `StrategyResult` and
SWOT are verified as bound components and have no lifecycle. It never judges whether a recommendation is
sound, a risk serious, a source true or a decision wise.

- **Three methods, never substituted:** *source binding* (identity **and** digest for the set and every
  component; ids resolved through `grounding`; registered `KPIResult`s and findings agreeing with their
  statements, which the set digest does not cover); *reproduction and textual equality* (each artifact
  rebuilt by its owning engine from the inputs it retained must equal the draft's `to_json()` byte for
  byte, plus located section, content, provenance, boundary and schema checks); *blind recomputation*
  (every engine-footed figure the artifact shows, and every scorecard row, recomputed from the
  fingerprinted source and compared exactly). External figures are source-bound only.
- **The blind-recomputation boundary (ADR-0035, superseding ADR-0034's interface).** The deterministic
  layer writes a closed, content-addressed request to `./.businessops/verification/`; the verifier agent
  receives only its `request_id` and holds only one tool, a plugin-local MCP operation `recompute`, which
  resolves the request internally, refuses on a source or configuration hash mismatch, reruns the command,
  and writes a machine-only record of **salted SHA-256 digests** of the recomputed values — never the
  values — returning only the allowlisted `bops.verifier.result/1` envelope. `verify()` re-derives the
  request, binds the record to it and compares digests of the draft's exact strings. The basis is a
  **run registration** (`run_id` over command, absolute source path, source SHA-256, run arguments and
  configuration digest), digest-bound in the set; re-registering a KPI or analysis from a different run is
  refused. If the platform cannot verifiably grant an agent only that tool, recomputation is `BLOCKED`,
  never re-routed through a shell.
- **Findings** carry a fixed `check_id`, category, method, component, location, an `expected` reference
  and an `observed` comparison code — **never a figure or statement text**; there is no severity or
  warning tier, **every finding blocks**, and order is catalogue order, never priority. Verification
  carries no confidence or trust and upgrades nothing.
- **Lifecycle:** `draft` → `verify()` → `VerificationResult` (`passed` | `failed`) → `finalise()` → a
  final object holding the unedited draft and the verification. Only the lifecycle fields change and a
  `verification_record` is added; everything else, including `report_id`, is byte-identical and
  re-proven at every serialisation. A failed verification leaves the draft as it was; there is no repair.
  Repeated verification is idempotent (no timestamp). A final report may not contain a draft package, so
  packages are finalised first.
- **No model decides or sees.** No model passes, fails, edits, suppresses or finalises anything; no model
  on the verification path receives the source, a path, a checked value or a recomputed value.
- **Final is not approval.** Fixed text says so; human decisions, approvals and actions follow §8 and
  ADR-0010 unchanged. Verification state lives in memory only; verification artifacts never re-enter
  synthesis.
- **How the implementation enforces it, without a second copy of any rule:**
  - *Run registration.* `commands.run()` hashes the source before and after the run (a change makes the
    run `unavailable`) and records `run_id`, `source_sha256`, `run_arguments` and `config_digest`;
    `commands.internal_statements()` and the new `commands.kpi_statements()` register the run in the set
    and bind every KPI and finding to it, refusing a cross-run re-registration before anything is
    registered. The run registry is part of `SynthesisSet.as_dict()`, so it is digest-bound.
  - *Retained inputs.* `StrategyResult.proposals`, `DecisionResult.request`/`config` and the report's
    `request`, `config` and component views let each owning engine rebuild its result; `verify()` requires
    byte equality.
  - *One catalogue.* 46 checks in fixed order across the 11 categories; every applicable check runs; a
    finding is `{check_id, category, method, component, location, expected reference, observed code,
    fixed message}`; order is catalogue, section, component position, location.
  - *The boundary.* `issue_recomputation()` seals a content-addressed request under
    `./.businessops/verification/`; the `recompute` operation (`recompute_request()`, served by
    `verification_server.py` over stdio) returns only `bops.verifier.result/1` and writes salted digests;
    `verify()` binds the record to the request it re-derives and removes both. The server silences stderr
    and stdout at start, publishes no instructions, and imports no network library.
  - *Process boundary.* Results bind live objects, so the orchestration issues the request, dispatches the
    agent with the id, and rebuilds the draft deterministically in a new process before `verify()`; a
    rebuilt draft that differs cannot match the request. A relay wrapped in one code fence is unwrapped;
    any other text is `malformed`.
  - *Final objects.* `FinalDecisionResult` and `FinalExecutiveReportResult` hold the unedited draft and its
    `VerificationResult`, re-check every binding and the draft digest at every serialisation, and change
    only the lifecycle fields plus `verification_record`; `executive_report.build()` accepts a final
    package. Schemas admit `final` only with `verified` and a `verification_record` (closed `oneOf`).
  - *Measured platform facts* (M11-A gate, re-measured by `tests/unit/test_m11_verifier_agent_boundary.py`):
    the plugin's stdio server connects; the tool is `mcp__plugin_businessops_bops-verifier__recompute`; an agent
    whose `tools` names only that tool has no ToolSearch and executes no other tool, while an agent without
    the field does; the server resolves `./.businessops/` from the session's project directory. `claude
    plugin validate --strict` does not check agents or `.mcp.json` and is not evidence for this boundary.

### The claim ledger — seven provenance classes

| # | Class | Presentation |
|---|---|---|
| 1 | User-provided data | fact + source file + reader tier |
| 2 | Connected-system data | fact + system + pull time |
| 3 | External sourced | source + date + tier |
| 4 | Calculated metric | formula + inputs |
| 5 | Analytical interpretation | explicitly framed as interpretation |
| 6 | Estimate / assumption | flagged, assumption registered |
| 7 | Recommendation | evidence + rationale + benefit + risk + dependencies + confidence (ADR-0031) |

Classes 5–7 render visually distinct from 1–4. Every major conclusion traces to at least one
class 1–4 entry. Confidence (`HIGH`/`MEDIUM`/`LOW`) is stated, never implied by tone. The
list is closed at seven; adding one requires an ADR.

---

## 8. Permission & approval model (ADR-0010)

Approval is a function of **consequence**, not of activity. Two axes: does the effect leave
the machine, and how reversible is it?

| Class | Examples | Approval |
|---|---|---|
| **Read-only analysis** | KPI, sales, customer, product, profitability, cash-flow, forecasting, anomaly, company/market/competitor/industry research, SWOT, strategy, decision support | **None** |
| **External research, Tier 0/1** | Benchmark and public-entity queries | **None** |
| **Draft generation** | Reports, scorecards, decision packages in conversation or scratchpad | **None** |
| **New local file** in the output directory | `./businessops-output/report-2026-09-08.md` | **None**, path always stated |
| **Overwrite an existing file** | Replacing a prior output or any user file | **Explicit** — names the file |
| **Modify original source data** | Editing the user's spreadsheet or ledger | **Prohibited** |
| **External research, Tier 2** | Query carrying user-specified internal context | **Explicit** — verbatim preview |
| **Export off-machine** | Cloud drive, shared workspace, anything with a URL | **Explicit** — destination + audience |
| **System writes** | CRM, accounting, commerce, database mutation | **Explicit** — system, record, change |
| **Communication / publication** | Message, email, chat post, publish | **Explicit** — recipients + content |
| **Financial transactions** | Any payment or transfer | **Prohibited** |
| **Repository** | `git commit` on request; `git push` | Commit on request; **never push** unless instructed |
| **Dependency install** | The Tier-2 openpyxl bootstrap | **Explicit**, once, disclosed |

Approval is **per action and non-transferable**. There is no session-wide "yes to
everything".

**"Human decision" is not a gate on execution.** Read-only analysis runs on request.
Gating analysis would produce approval fatigue, which is how a genuinely consequential
prompt gets waved through. The gate attaches to the consequential action, if and when one is
requested.

Least privilege is enforced at three levels: source resolution exposes no mutating connector
tool — v1 has no write path (ADR-0037 §G); command frontmatter constrains `allowed-tools`; agent frontmatter
grants each subagent only what its role needs — `bops-research-scout` gets web tools and no
file access; a future `bops-data-profiler` (ADR-0036: deferred to model-mediated sources) no web tools.

### Enforcement of filesystem-write approvals (ADR-0051)

The table above is enforced for filesystem writes by two layers that share one policy
(`lib/python/bops/writeguard/policy.py`) and one approval store (`~/.claude/businessops/guard/`).

- **Layer 1, before execution:** the plugin-wide `PreToolUse` hook (`hooks/hooks.json`). It stops a `Bash`, `Write`,
  `Edit`, `MultiEdit`, `NotebookEdit` or `PowerShell` call, in a session that has engaged BusinessOps, if the call's
  classified operations need approval and hold no matching capability. It also stops any prohibited operation. The
  answer is `permissionDecision: "deny"`, never `allow`.
- **Layer 2, during execution:** the audit hook `bops_run.py` installs before any engine code runs
  (`writeguard/engine.py`). It stops any write, process start or network connection by the engine outside its own
  state: `~/.claude/businessops/runtime/`, `./.businessops/`, and new files in `./businessops-output/`. The engine's one
  user-file write path is `writeguard.export.write_text`, which asks first.

- **Scope.** The runtime does not attribute a tool call to a plugin, so a session is governed from the moment it
  *engages* BusinessOps: a BusinessOps `Skill` call or slash command, a BusinessOps subagent, or an engine-launcher call.
  It stays governed for the rest of the session. Before engagement, only the approval store and the guard entry are
  protected.
- **Classification.** It is an allowlist. A shell command is read-only only if every simple command is a listed
  read-only program with read-only arguments and every redirection goes to a stream or a device. Anything unparsed,
  unknown or unresolved needs approval (`UNKNOWN != SAFE`).
- **Decisions.**
  - *Free:* a new file under `./businessops-output/`; scratchpad and temporary files.
  - *Prohibited:* the approval store; the plugin while engaged; existing source-data files; force-push, history rewrite
    and branch deletion.
  - *Approval:* everything else.
- **Approval.** The denial names each operation and target and gives a code. Only the user's own prompt,
  `approve BOPS-W-XXXXXXXX`, grants it, for the same session. The capability is bound to the session, the tool, the
  canonical cwd, the digest of the exact input, and each operation's kind, canonical target, sources and existence. It
  is single-use, expires 10 minutes after the grant, and is redeemed only by an identical call.
- **Fail-closed.** An unreadable input, an internal error, a missing session id, or a guard that cannot start blocks
  the call.

---

## 9. Data flow

The canonical pipeline, defined once in `reference/analysis-framework.md`. Every command
runs it; skipping a step requires saying which and why.

```
 1  Identify objective + load Business Context
 2  Determine information requirements
 3  Split internal vs external requirements
 4  Inspect data                    ← ingestion (tiered reader) / data-profiler
 5  Retrieve external information   ← DISCLOSURE GATE: Tier 0/1 auto · Tier 2 approval · Tier 3 refuse
 6  Validate                        ← QUALITY GATE: CRITICAL halts
 7  Normalize                       ← derived copy; source untouched
 8  Calculate                       ← engine; KPI relevance from Business Context
 9  Compare                         ← period / segment / benchmark
10  Identify material changes       ← materiality filters (does not halt)
11  Investigate
12  Separate facts from interpretation
13  Generate insights
14  Evaluate risks and opportunities
15  Generate recommendations
16  Identify assumptions and uncertainty
17  Assign confidence
18  Generate output
19  Human decision                  ← the analysis is FOR a person; not a gate on execution
```

**Two gates halt a workflow:** the disclosure gate (5, Tier 2/3) and the quality gate (6,
`CRITICAL`). Materiality (10) filters. The consequential-action gate (§8) sits *after* the
pipeline, triggered only by a request to do something with the output.

### Worked example — `/revenue-forecast sales_2024.xlsx --horizon 6m`

```
1   context    → SaaS, GBP, FY starts 01-01, materiality 5% / £10k
4   ingest     → Tier 1 (openpyxl present); 18 monthly periods; tier recorded
4b  map        → date=OrderDate, revenue=NetAmount (0.94, auto)
                 customer=CustName (0.61) → CONFIRM WITH USER, not guessed
6   quality    → WARNING: 2 duplicate invoices, 1 negative amount → surfaced, not halted
7   normalize  → derived working copy; sales_2024.xlsx untouched
8   kpi        → monthly series, growth, seasonality; ARR/MRR relevant (SaaS),
                 inventory turnover → not_applicable
10  materiality→ configured 5% / £10k applied
8b  forecast   → 18 periods ≥ 12 minimum → base/upside/downside + assumptions
16  assumptions→ seasonality persists; no concentration change; 2 duplicates excluded
17  confidence → MEDIUM (18 periods, WARNING-grade quality)
18  output     → actuals and forecast visually distinct; no approval needed
19  decision   → user's. Nothing written, exported or sent.
```

---

## 10. Subagent architecture

Three subagents allocated (ADR-0006); two built. Justified only by **context
isolation**, **parallel fan-out** or **independent verification**. ADR-0036 applied that test to
`bops-data-profiler`: profiling local files is deterministic engine work whose raw output never reaches a model
(§5), so no subagent is built for it; the agent stays allocated, unbuilt, for model-mediated exploration of
sources only reachable through model tools and too large for the main context (connector catalogues, M12).

| Agent | Responsibility | Invoked when | Tools |
|---|---|---|---|
| `bops-data-profiler` | **Deferred (ADR-0036); still unbuilt after M12-B**, because ADR-0037 §D.1 builds it only on a complete Connector-Gated discovery chain and none exists. Explore connector catalogues and schemas reachable only through model tools. Local files, sheets and multi-source key overlap are profiled by the deterministic `DataProfileResult` (§5), not by this agent | a model-mediated source too large for the main context (M12) | its own contract when built (ADR-0037, accepted; not yet built — only exact, registered, Gate-measured, value-free discovery tools; never a local file, record, Business Context, research, credential, web, shell or write tool; local-file profiling stays agent-free); data access through a declared structural grant (ADR-0014, ADR-0035), **no web**, no shell or raw-row read |
| `bops-research-scout` | Retrieve and triage sources for one entity | any external command, one per entity | web, **no file access** |
| `bops-analysis-verifier` | Independently recompute headline figures, challenge conclusions — concretely (ADR-0034, ADR-0035): the zero-access context that invokes the one fixed `recompute` operation with an **opaque request id** and relays its allowlisted status envelope. It never receives a path, a source, a claimed value or a recomputed value. Pass, fail and finalisation are decided by `verification.py`, never by the agent's model | before `/executive-report` and `/decision-support` finalise — i.e. move a draft result to final; M10 components produce drafts without waiting for it (ADR-0032); a final report may not contain a draft package (ADR-0033) | the single local MCP tool `recompute` and nothing else — no shell, file, web or dispatch tool; the engine and dataset are reached only inside that operation (ADR-0035) |

Rejected: Data Analyst, Finance Analyst, Sales Analyst, Forecasting, Market Research,
Competitive Intelligence, Strategy Analyst, Executive Analyst — all reasoning-dense and
context-dependent, so they are skills. The tool split above is what makes the Tier-3 privacy
boundary structural rather than advisory.

**How a subagent is invoked.** By the orchestrating model, through the runtime's Task
mechanism, as `businessops:<agent>`. There is no programmatic dispatch API that plugin Python
may call, and that is the control rather than a gap: because Python can reach neither a web
tool nor a subagent, the component holding file access and the component holding web access
are separated by the runtime instead of by discipline. The consequence for the engine is
that external retrieval has two Python halves — build the brief, ingest the reply — joined
by an orchestration surface written in markdown that the model reads. That markdown is
executable instruction and is tested as such (ADR-0015). What crosses back between the halves
is the line protocol of ADR-0017, passed verbatim, because extracting or repairing it would move
authorship to the one context that can read business data. Since ADR-0053, no model carries it: the
plugin's `PostToolUse` hook stores the scout's reply (`tool_response.content`) byte for byte under the
write guard's root, and the orchestration surface closes the retrieval with
`close_retrieval(R.handback_reply('<operation>'), …)`. A model copy is never used; measured on live
runs, even an instructed copy lost whitespace (M14-6).

---

## 11. MCP architecture

Skills address **capabilities**, never products: `~~accounting`, `~~crm`, `~~commerce`,
`~~warehouse`, `~~spreadsheet`, `~~chat`. Source resolution inside `bops-data-ingestion`
resolves a capability **only to exact, registered connector identities**. It never discovers
connected servers and adopts them. It maps capability to tools, enforces read-only, and **degrades by
returning a named absence** plus the file fallback. (Owner decision OD-2, accepted 2026-09-17;
this supersedes in part ADR-0004's "performs discovery … whatever server is connected" and
"user-configurable" clauses — see ADR-0037 *Relationship to ADR-0004*.)

| Category | Candidates | Verified server? |
|---|---|---|
| CRM | HubSpot | ✅ `https://mcp.hubspot.com/anthropic` |
| Chat | Slack | ✅ `https://mcp.slack.com/mcp` (write-capable; not eligible in M12) |
| Accounting | QuickBooks, Xero, NetSuite | ❌ none found |
| Spreadsheet | Google Sheets/Drive, Excel/OneDrive | ❌ none found |
| CRM | Salesforce | ❌ developer tooling only |
| Commerce | Shopify, Stripe | ❌ developer tooling only |
| Warehouse | Postgres, MySQL, Snowflake, BigQuery, Databricks | ❌ none verified here |

`.mcp.json` ships **only verified endpoints**; inventing a URL is prohibited. Adding a server
is a Connector-gate decision. Because accounting and spreadsheet categories have no server,
**the file path is load-bearing, not a fallback** — which is why §5's tiered reader matters
so much. "Verified server?" records that an endpoint exists; no connector is registered or
Connector-Gate measured today, so none is usable yet. Extensibility: a new connector is a
registry declaration, one BusinessOps `.mcp.json` entry, an approved Connector Gate record, the
matching tool grant and one capability-map row, with no skill changes.

**Connector identity (OD-2, accepted 2026-09-17).** A connector tool is usable only when three
layers agree exactly on connector identity, capability, server identity and namespace, tool
name, interaction class and argument and output shape:

- the **registry declaration** (what BusinessOps supports);
- the **Connector Gate measurement** (what that exact server and tool demonstrably provide);
- the **runtime grant** (what the agent can call).

No single layer authorizes use, and any disagreement refuses it. A same-vendor server under another
key or namespace never qualifies. Availability, Gate approval and registry metadata are never
authorization or evidence.

**M12 contract — ADR-0037 (accepted 2026-09-17). M12-B implemented 2026-09-18; no connector is
admitted, so none is usable.**

- **M12-B:** value-free discovery only, through the reserved `bops-data-profiler` agent holding only
  measured discovery tools. No record reads, no evidence, no synthesis input.
- **M12-C:** connected-system record reads, recorded **`BLOCKED`** (OD-1, accepted) until platform
  prerequisites P-1–P-5 are met and its own ADR is accepted. It never follows automatically from
  M12-B.
- No write or administrative connector interaction exists.

**Optional connectors and the connection lifecycle — ADR-0038 (accepted 2026-09-18, with OD-3; nothing
implemented).** Every connector is optional: its absence, disconnection, authorization failure,
unavailability or refusal degrades only its own capability, with a named reason and the file
alternative, and never changes a file-based result. A **planned** (designated, future) connector is a
documentation status only and gives BusinessOps no connector. Five facts are kept distinct, and none
substitutes for another:

| Fact | Decided by | How BusinessOps knows it |
|---|---|---|
| **Supported** — registry declaration, admitted only under OD-3 | Owner, after the Connector Gate | Registry lookup (Python) |
| **Verified capability** — Gate record and grant agree with the declaration (§B.2) | Owner, at the Connector Gate | Static binding checks |
| **Connected** — the user authenticated BusinessOps's own declared server entry | User, through the platform | Only by relayed outcome; untrusted; can only reduce |
| **Authorized** — vendor authorization (user and vendor) and BusinessOps permission (per sealed operation), never merged | Vendor; Python per operation | Relayed `authorization_failure`; computed |
| **Available for use** — all of the above for one operation, which completed | Python, per operation | Recomputed; never persisted |

The lifecycle states are documentation vocabulary mapped onto ADR-0037's existing §H codes; no runtime
state or code is added. Static facts are evaluated before any dispatch, so BusinessOps never probes for
a connection. The user connects through the platform's own mechanism, which BusinessOps never starts,
never observes by reading configuration, and never describes beyond what the Connector Gate observed.
BusinessOps handles no credential. A connection never substitutes for Connector Gate approval.

**Admission rule (OD-3).** A connector is represented as supported in the shipped registry, and its
`.mcp.json` entry is shipped, only when at least one declared capability in its v1 scope has a complete,
approved, BusinessOps-owned Connector-Gated chain. In M12-B that capability is value-free discovery.
Documentation naming a connector, a vendor endpoint, another plugin's server, or a same-vendor connector
elsewhere does not qualify. Admission does not unblock M12-C.

HubSpot is a **designated optional future connector**. It is not a currently supported or usable
BusinessOps connector, because no BusinessOps-owned, Connector-Gated value-free discovery capability has
been approved. It is not registered, declared, measured or connected, and BusinessOps has no HubSpot
connection path.

**M12-B implementation (2026-09-18) — `lib/python/bops/connectors/`, `lib/schemas/connector.schema.json`.**

| Module | Holds |
|---|---|
| `contract.py` | The closed vocabularies: placeholders, interaction classes, the 19 §H codes, result statuses, one fixed sentence per code, and the value-shape screen - **defence in depth only** |
| `registry.py` | The fixed, deep-frozen registry (`_DECLARATIONS`) and resolution. **Shipped empty by design**: no BusinessOps-owned value-free discovery capability existed to take through the Connector Gate, so no Gate measurement was taken and OD-3 admits nothing (ADR-0037 §L item 1) |
| `binding.py` | The Connector Gate record form — one fenced `bops-connector-gate` JSON block in a dated development record — and the §B.2 agreement check across registry, Gate record, `.mcp.json` and the agent grant, reading only BusinessOps's own repository files |
| `catalogue.py` | ADR-0038 §5 evaluation order; a sealed, consumed-once brief under `./.businessops/connectors/operations/` with a 96-bit random operation id; the fail-closed `BOPS-CAT/1` / `BOPS-CAT-END/1` reply parser; the value-free `CatalogueResult` |

**Operation classes.** A record read is `blocked_prerequisite`, the one §H code whose situation it is.
A write or administrative request is `request_invalid`: it lies outside what an M12-B request may ask
for, and no prerequisite can unblock it, so `blocked_prerequisite` would mislead. The interaction class
is carried as the limitation subject and the message states that no write path exists, so the refusal
is never mistaken for a forged request. Any other operation value is `request_invalid` at shape
validation. No function takes a tool name, server or free arguments, so there is no dispatcher.

**The value-free boundary** is structural: a reply is read only for an operation sealed on a complete,
Gate-approved chain and re-checked at close; keys pass only through the declaration's closed allowlist;
data types only through a closed vocabulary; the result through the closed schema; any structural
defect - including a repeated key or a repeated entry - refuses the whole reply. The value-shape screen
is a second, heuristic line: it cannot recognise every value (a plain name in a free-text label passes
it), which is ADR-0037's stated residual risk.

**What is proven, and what is not.** Registry exactness, the empty-registry behaviour, the static
admission rule, identity binding, the evaluation order and the fail-closed parser are proven by
deterministic tests; catalogue building and the relayed codes only against a synthetic enforcement
fixture. No real vendor discovery response, HubSpot connection, Connector Gate measurement or connector
agent run exists, because no connector is admitted. `SynthesisSet.register_claims()`
refuses every catalogue, part of one, resolution, brief and class-2 claim. Nothing in the file workflow
imports the package. The `bops-data-profiler` agent stays unbuilt (§D.1), and `.mcp.json` is unchanged.

---

## 12. Security model

- **Secrets:** BusinessOps holds none. Authentication is delegated to MCP servers and their
  OAuth flows. `.mcp.json` carries server identity only.
- **Business data:** stays on the machine except as §7's tiers permit; every disclosure is
  logged to the evidence ledger.
- **Boundary enforcement:** structural via agent tool allocation, plus the query-construction
  gate, plus the write guard (§8, ADR-0051): a pre-execution hook on the model's file-writing tools and an execution
  guard inside every engine process.
- **PII:** aggregate by default; Tier 3 material never leaves under any approval.
- **Derived artifacts:** session scratchpad or the designated output directory; never
  committed.
- **Managed runtime:** `~/.claude/businessops/runtime/` holds only the consented venv;
  documented and removable.
- **Repo hygiene:** `.gitignore` covers `.env*` and `.businessops/`; fixtures and demo data
  synthetic; pre-commit secret scan proposed for Milestone 1.
- **External content is data, not instruction.** Retrieved pages may be adversarial;
  instructions found in them are never followed and can never raise a disclosure tier.

---

## 13. Repository structure

```
BusinessOps/
├── .claude-plugin/plugin.json · marketplace.json · icon.png (icon.svg: its design source, not shipped)
├── .mcp.json                     Verified endpoints only; the local bops-verifier stdio server (M11)
├── .gitignore                    + .businessops/ and businessops-output/
├── CLAUDE.md · README.md · architecture.md · project_plan.md · CONNECTORS.md · LICENSE
├── commands/                     19 thin orchestrators (shipped, 2026-09-27)
├── skills/bops-*/SKILL.md         16 skills shipped — judgement and workflow (§4 describes the 20-skill design)
├── reference/                    6 policy documents — 0 always-on
├── agents/                       2 subagents shipped (bops-research-scout, bops-analysis-verifier); bops-data-profiler deferred (ADR-0036)
├── hooks/                        hooks.json · bops_guard.sh — the plugin-wide write guard (ADR-0051)
├── lib/
│   ├── python/bops/
│   │   ├── ingest/               tiered xlsx readers · csv · normalisation
│   │   ├── runtime/              tier resolver + consented bootstrap
│   │   ├── quality/ kpi/ analytics/ forecast/ anomaly/ materiality/ format/ render/
│   │   ├── research/               disclosure gate · scout seam · evidence sets
│   │   ├── synthesis/              cross-domain synthesis foundation (M10.1);
│   │   │                           dimension_provenance.py = admissibility (ADR-0026);
│   │   │                           grounding.py = consumer grounding checks (ADR-0031)
│   │   ├── quantity.py             source notation → canonical quantity (ADR-0025)
│   │   ├── swot.py                 SWOT consumer of the synthesis set (ADR-0030)
│   │   ├── strategy.py             class-7 recommendations beside the set (ADR-0031)
│   │   ├── decision_support.py     draft twelve-part decision package beside the set (ADR-0032)
│   │   ├── executive_report.py     draft eleven-section report assembled over the set (ADR-0033)
│   │   ├── verification.py         M11 verification and finalisation (ADR-0034, ADR-0035)
│   │   ├── verification_server.py  the one-tool `recompute` MCP server (stdio, ADR-0035)
│   │   ├── data_profile.py         deterministic local-file data profile (ADR-0036)
│   │   ├── connectors/             M12-B registry (shipped empty) · binding · value-free catalogue (ADR-0037)
│   │   ├── writeguard/             write boundary (ADR-0051): shell · pyscan · classify · policy ·
│   │   │                           capability · hook · engine · export
│   └── schemas/                  dataset · profile · semantic_map · quality_report ·
│                                 business_context · kpi_results · forecast · anomaly ·
│                                 evidence_set · claim_ledger · synthesis · swot · strategy ·
│                                 decision_support · executive_report · verification · connector ·
│                                 write_approval
├── config/businessops.defaults.json
├── assets/demo-data/             Synthetic — arrives in Milestone 2
├── tests/                        run_tests.py · fixtures/ · unit/ integration/ negative/
├── evals/                        case.yaml suites + mocks/
└── docs/                         README · development/ · decisions/ · architecture/ ·
                                  testing/ · integrations/ · skills/ · commands/ ·
                                  agents/ · examples/ · troubleshooting/ · templates/
```

Runtime state outside the repo: `./.businessops/business_context.json` (gitignored),
`./businessops-output/` (generated reports), `~/.claude/businessops/runtime/` (consented venv),
`~/.claude/businessops/guard/` (session engagement markers and write approvals, ADR-0051).

---

## 14. Configuration model

Precedence: **command argument → project business context → user business context → shipped
defaults**. Business Context (§6) is the business-specific layer;
`config/businessops.defaults.json` is the shipped floor.

```jsonc
{
  "locale":      { "currency": "USD", "number_format": "1,234.56",
                   "date_format": "YYYY-MM-DD", "fiscal_year_start": "01-01" },
  "materiality": { "absolute_amount": 10000, "percentage": 5.0, "kpi_deviation": 10.0,
                   "revenue_percentage": 1.0, "margin_percentage_points": 2.0 },
  "quality":     { "halt_on": "CRITICAL", "max_missing_pct": 5.0, "duplicate_tolerance": 0 },
  "forecast":    { "min_history_periods": 12, "default_horizon_periods": 6,
                   "scenarios": ["base","upside","downside"] },
  "anomaly":     { "sensitivity": "medium", "min_baseline_periods": 6 },
  "research":    { "staleness_days": { "financials": 365, "market_sizing": 730,
                                       "positioning": 545 },
                   "min_tier_for_material_claim": "B",
                   "disclosure": { "k_anonymity_floor": 5, "default_tier": 0 } },
  "runtime":     { "xlsx_reader": "auto", "allow_bootstrap": "ask" },
  "output":      { "directory": "./businessops-output" }
}
```

No secrets in configuration, ever.

---

## 15. Testing architecture

Two layers split by failure mode (ADR-0007).

**Layer 1 — deterministic fixture tests (`tests/`, primary).** Stdlib `unittest`, run by
`python tests/run_tests.py`. Fast, free, offline. Carries the correctness burden: `unit/`
(engine modules), `integration/` (ingestion → quality → KPI → analytics), `negative/` (every
failure mode in §16, each failing loudly and correctly).

Fixture corpus: clean xlsx, clean CSV, missing values, duplicates, invalid dates, invalid
numbers, missing revenue, missing costs, currency mismatch, outliers, insufficient history,
unsupported KPI, large dataset — plus, new in Revision 2, **cross-tier equivalence** (same
fixture at Tier 1 and Tier 3) and **business-model relevance** (`not_applicable` correctness
per business model).

**Layer 2 — behavioural evals (`evals/`, secondary).** Cases asserting what the model *does*:
refuses to guess an ambiguous column; halts on `CRITICAL`; declines a forecast with 4
periods; never labels an anomaly as fraud; never emits an uncited external claim; degrades
when a connector is absent (tested against the real, empty connector registry; no `evals/mocks/`, and no mock stands in
for a connector — ADR-0039 §H). New in Revision 2: the four Tier-0
comparative questions **succeed with no approval prompt**; a Tier-3 disclosure attempt is
**refused**; a small-denominator aggregate and a re-identifying attribute combination are
**blocked**; read-only commands **never prompt**; and **routing cases** asserting the right
component fires (the discriminability constraint from §2).

**Limitation:** `claude plugin eval` is early-access gated and not enabled here — verified.
Cases are authored and version-controlled but cannot be executed on this machine; until then
behavioural guarantees are covered by scripted manual scenarios recorded in `docs/testing/`,
explicitly labelled as manual. No test is reported as passing that was not run.
*Re-observed 2026-09-18 (Claude Code 2.1.276).* A zero-case probe reached case discovery with no early-access
refusal. **Resolved 2026-09-26:** cases now execute under `claude plugin eval` (Claude Code 2.1.281), and every
M13.2 case has admissible live evidence (below), so this limitation no longer holds and R-01 is closed. The earlier
text is kept as history.

**M13 contract — ADR-0039 (Accepted).** Milestone 13, whose status lives in `project_plan.md`:

- measures coverage against a closed matrix of in-repository enumerations (S1–S7). ADR-0007's uncommitted
  24-scenario list is recorded as unavailable and is not reconstructed;
- closes deterministic gaps with new tests;
- records large-dataset, discriminability and selection-stability measurements, with no invented threshold and no
  tuning.

It authors the Layer-2 suite and executes it only under ADR-0039 §F:

- the owner's explicit per-execution authorisation, with a `--max-cost-usd` ceiling;
- always `--no-publish`;
- `--runs 3 --threshold 1.0`;
- no plugin MCP server, no web tool, no `mcp__` grant, no authentication and no connector.

Eval evidence uses a closed vocabulary: `automated_pass`, `automated_fail`, `not_executed`, `execution_unavailable`
and `manual_observation`. A manual observation or unavailable execution is never an automated pass. M13 changes no
production behaviour to satisfy a test, eval or measurement. It records defects with ids and reproducers rather than
fixing them. It simulates no connector and does not affect M12-C, which stays `BLOCKED`. Its artifacts are in
`docs/testing/`: the coverage matrix, the defect register and the measurements. A deterministic validator,
`tests/unit/test_m13_coverage_matrix.py`, checks the matrix and the register. ADR-0040 amends ADR-0039 §B and §L
in part to admit an owner-accepted environment-unavailable gap. It is a `gap` with a complete disposition record, and
never a defect or coverage.

**M13.2 suite (authored and executed).** `evals/` holds the Layer-2 suite: 64 cases in the five ADR-0039 §E.3 suites
(`behaviour`, `disclosure`, `approval`, `connectors`, `routing`), one `case.yaml` each, in the **dual-layer** schema
`bops-eval-case/2` (ADR-0044, `docs/testing/eval-suite.md`): one file carrying the platform's keys (`schema_version`, `name`,
`execution`, `graders`) and the BusinessOps semantic keys (`bops_graders`, `coverage_rows`, `evidence_class` and the rest),
which the platform's loader strips. There is no `evals/mocks/` and no runner; business-file cases stage their inputs
with a copy-only scaffold (ADR-0039 §F.6).

- **Inputs.** Cases read `assets/demo-data/` unchanged, or one of three committed, builder-reproduced fixtures under
  `tests/fixtures/eval_inputs/` (ADR-0041), each bound to one `behaviour` case. `a20` also stages one declared
  precondition fixture as `README.md` (ADR-0048).
- **Static validation.** `tests/unit/test_m13_eval_cases.py` validates the cases, the fixtures and the execution
  procedure on every run (ADR-0039 §E.5, ADR-0041 §8).
- **Execution status.** Executed under §F with owner authorisation and cost ceilings, and recorded in three separate
  result records, each kept as written:
  - the **closing evaluation** (2026-09-24/25, `tests/fixtures/eval_results/2026-09-25-closing-evaluation.json`): all
    64 cases, 16 `automated_pass`, 34 `automated_fail`, 14 `execution_unavailable`, $47.00 — the original record, and
    the classes the case files carry;
  - the **34-case re-evaluation** (2026-09-25, `…/2026-09-25-reevaluation-34-cases.json`): the cases whose graders,
    routing or staging were corrected afterwards, under the amended contract;
  - the **availability-completion evaluation** (2026-09-26, `…/2026-09-26-availability-10-cases.json`): the ten routing
    cases the re-evaluation lost to platform session and turn limits, all `automated_pass`.

  The later records supplement the closing evaluation; they do not overwrite it. Together they give every case
  admissible live evidence.
- **Contract.** ADR-0044 (the dual-layer case format the platform loads), ADR-0045 and ADR-0046 (the engine's runtime
  resolver the evaluator reaches), ADR-0047 (a routing grader accepts the skill's owning command), ADR-0048 (a declared
  precondition fixture) and ADR-0049 (a semantic LLM-judge split is `execution_unavailable`, never a pass or a fail).
  **No live judge split has occurred**, so ADR-0049's rule is verified deterministically only.
- **Defects** found by the evaluations are in `docs/testing/defects.md`; every infrastructure defect is fixed, and the
  product defects are recorded for owner-assigned remediation.

---

## 16. Error handling

| Scenario | Behaviour |
|---|---|
| Missing data | Name the field; state which metrics are unavailable; continue with the rest |
| Corrupt file | Halt; report what failed to parse and where |
| Inconsistent data | Quality finding with examples, graded; **no auto-repair** |
| Missing required field | Halt that metric only; name it; offer to proceed without |
| Unsupported KPI | "Insufficient data to calculate this metric reliably" + the inputs needed |
| KPI irrelevant to the business model | `not_applicable`, distinct from unavailable, with the reason |
| Reader tier degraded | State the tier; `WARNING` if formats were unresolved |
| Unsupported xlsx construct at Tier 3 | Escalate or halt — **never guess a value** |
| Insufficient history | Periods available vs required; refuse the forecast |
| Forecast impossible | Explain why; offer trend description instead |
| MCP unavailable | Name the connector, what could not be retrieved, offer the file path. Every connector outcome is one of ADR-0037's 19 §H codes with a fixed sentence and the file-export alternative; no connector is registered today, so every capability is `connector_not_configured` |
| External source unavailable | "No reliable source found" — never substitute a plausible one |
| Conflicting sources | Both, with sources and dates; explain divergence; lower confidence |
| Ambiguous question or column | Ask specifically; never guess |
| Disclosure gate — Tier 2 | Halt; show verbatim text; await approval |
| Disclosure gate — Tier 3 | Refuse; offer the Tier 0 alternative |
| Large dataset | Aggregate in the engine, sample for display, warn about scope |
| Write attempted without approval | Stop; request approval naming system, record, change. A filesystem write is denied before it runs by the write guard, which names each operation and target and states that nothing was written (§8, ADR-0051) |

---

## 17. Scalability

| Dimension | Approach |
|---|---|
| Small (<10k rows) | Straight through the engine; full detail |
| Large (>100k rows) | Engine streams and aggregates — **only aggregates reach model context**; the deterministic data profile (§5, ADR-0036) reports structure without values, so no scan output reaches a model |
| Warehouse-scale | Push aggregation to the source; never pull a full table |
| Multiple sources | Ingested independently, reconciled on a **user-confirmed** join key |
| Multiple connectors | Resolved per capability among registered identities only; more than one asks the user, never auto-selected; missing ones degrade individually |
| More skills/commands | Additive; constrained by discriminability, not tokens (§2) |
| More agents | Three-justification test + an ADR |

The binding constraint is **model context, not compute** — hence bulk data is summarised by
the engine or isolated in an agent before reaching the main thread.

---

## 18. Extension points

| To add | How | ADR? |
|---|---|---|
| A KPI | Registry entry: input contract + `applicable_models` + calculator | No |
| A quality check | Check-family registry entry | No |
| A forecast method / anomaly detector | Register with its adequacy predicate | No |
| A connector | Registry declaration in `connectors/registry.py` + `.mcp.json` entry + approved Connector Gate record (one `bops-connector-gate` block in a dated development record) + matching `bops-data-profiler` grant + capability-map row, all agreeing exactly (ADR-0037 §B); `binding.admission_findings()` must be empty (OD-3) | No |
| A business model / industry | Controlled-vocabulary entry + KPI applicability | No |
| An analysis domain | New Layer-2 skill + optional command | No |
| An output format | New renderer in the engine | No |
| A reader tier | Register in the tier resolver + equivalence tests | No |
| A subagent | Three-justification test | **Yes** |
| A provenance class | The ledger is closed at seven | **Yes** |
| A disclosure tier | The tiers are closed at four | **Yes** |

---

## 19. Architectural decisions

| ADR | Decision | Status |
|---|---|---|
| [0001](docs/decisions/ADR-0001-claude-code-plugin-platform.md) | Claude Code plugin, verified conventions only | Accepted |
| [0002](docs/decisions/ADR-0002-deterministic-compute-engine.md) | Deterministic engine; no model arithmetic | Accepted — amended by 0008 |
| [0003](docs/decisions/ADR-0003-commands-orchestrate-skills-hold-logic.md) | Commands orchestrate, skills hold logic | Accepted — refined by 0012 |
| [0004](docs/decisions/ADR-0004-capability-based-connector-abstraction.md) | Capability-based connectors; no invented endpoints | Accepted — its runtime-discovery and "user-configurable" clauses superseded in part by 0037 (OD-2 accepted; ADR text unedited) |
| [0005](docs/decisions/ADR-0005-seven-class-evidence-ledger.md) | Seven-class evidence ledger | Accepted |
| [0006](docs/decisions/ADR-0006-three-subagents-not-eight.md) | Three subagents, not eight | Accepted |
| [0007](docs/decisions/ADR-0007-two-layer-testing-strategy.md) | Fixture tests primary, evals secondary | Accepted |
| [0008](docs/decisions/ADR-0008-tiered-xlsx-ingestion.md) | Tiered xlsx ingestion with a managed dependency | Accepted |
| [0009](docs/decisions/ADR-0009-comparative-intelligence-privacy-boundary.md) | Four-tier disclosure model; local-join default | Accepted |
| [0010](docs/decisions/ADR-0010-consequence-based-approval-model.md) | Consequence-based approval | Accepted |
| [0011](docs/decisions/ADR-0011-business-context-first-class.md) | Business Context as a first-class component | Accepted |
| [0012](docs/decisions/ADR-0012-component-placement-rule.md) | Component placement rule | Accepted |
| [0013](docs/decisions/ADR-0013-token-budget-is-self-imposed.md) | Token budget is self-imposed; discriminability is the real constraint | Accepted |
| [0014](docs/decisions/ADR-0014-retrieval-agent-ships-with-retrieval.md) | The retrieval agent ships with the first milestone that retrieves | Accepted |
| [0015](docs/decisions/ADR-0015-model-mediated-scout-dispatch.md) | Scout dispatch is model-mediated; the orchestration surface is markdown | Accepted |
| [0016](docs/decisions/ADR-0016-declared-conflicts-outrank-numeric-agreement.md) | Declared conflicts outrank numeric agreement | Accepted |
| [0017](docs/decisions/ADR-0017-operation-bound-line-records.md) | The scout returns operation-bound line records, not an envelope | Accepted |
| [0018](docs/decisions/ADR-0018-first-party-company-source-registry.md) | First-party company sources are tier B, by explicit registry | Accepted |
| [0019](docs/decisions/ADR-0019-market-research-intents.md) | Two research intents added for market analysis | Accepted |
| [0020](docs/decisions/ADR-0020-competitor-research-intents.md) | Two research intents added for competitor analysis, and two reused | Accepted |
| [0021](docs/decisions/ADR-0021-research-intent-registry.md) | One immutable research-intent registry replaces the flat intent tables | Accepted |
| [0022](docs/decisions/ADR-0022-cross-domain-synthesis-contract.md) | One synthesis contract, built from existing vocabularies, that promotes nothing | Accepted |
| [0023](docs/decisions/ADR-0023-internal-statements-need-internal-footing.md) | An internal statement is defined by its provenance, not by its declared origin | Accepted |
| [0024](docs/decisions/ADR-0024-retrieval-to-synthesis-object-seam.md) | One retrieval assembly, two closers: the `EvidenceSet` reaches synthesis as an object | Accepted |
| [0025](docs/decisions/ADR-0025-unit-is-a-quantity-type.md) | `unit` is a quantity type; scale is normalised into the value, never carried as a label | Accepted |
| [0026](docs/decisions/ADR-0026-dimension-provenance-and-source-context-admissibility.md) | A dimension is admissible for compatibility only where its provenance says a source stated it | Accepted |
| [0027](docs/decisions/ADR-0027-external-source-context-extraction.md) | Source context travels inside the evidence record; the protocol does not change | Accepted |
| [0028](docs/decisions/ADR-0028-command-path-footing-is-strict.md) | The research command's footing path is one seam, and it is strict by construction | Accepted |
| [0029](docs/decisions/ADR-0029-the-local-join-surface.md) | The local join is a surface of its own, and it sequences only | Accepted |
| [0030](docs/decisions/ADR-0030-a-swot-point-is-a-placement.md) | A SWOT point is a placement of a synthesis statement, never new text | Accepted |
| [0031](docs/decisions/ADR-0031-strategy-recommendation-contract.md) | The strategy recommendation contract: a class-7 claim resolved against a synthesis set, held beside it | Accepted — refines 0022 §5 |
| [0032](docs/decisions/ADR-0032-decision-support-contract.md) | The Decision Support contract: a twelve-part draft decision package beside the synthesis set | Accepted |
| [0033](docs/decisions/ADR-0033-executive-report-contract.md) | The Executive Report contract: an assembly of existing artifacts over one synthesis set, authoring nothing | Accepted |
| [0034](docs/decisions/ADR-0034-m11-verification-and-finalisation-contract.md) | The M11 verification and finalisation contract: deterministic integrity checks, blind recomputation, and a final lifecycle recorded beside an unedited draft | Accepted — partially superseded by 0035 |
| [0035](docs/decisions/ADR-0035-m11-blind-recomputation-boundary.md) | The M11 blind-recomputation boundary: an opaque request, one fixed operation, digests not values, and no shell for the verifier agent | Accepted — supersedes 0034 in part |
| [0036](docs/decisions/ADR-0036-biq-data-profiler-contract.md) | The data profiler contract: a deterministic, value-free assembly of what the Data Layer already knows, bound to its sources, with the subagent deferred until a model must browse | Accepted — refines 0006 (profiler allocation) |
| [0037](docs/decisions/ADR-0037-m12-connector-layer-contract.md) | The M12 connector layer contract: registry-bound, read-only connector catalogue; discovery separated from data; connected-system reads blocked on measured prerequisites | Accepted — supersedes in part 0004 (its runtime-discovery and "user-configurable" clauses only) |
| [0038](docs/decisions/ADR-0038-optional-connector-connection-lifecycle.md) | Optional connectors and the user-initiated connection lifecycle: supported, connected, authorized, verified and available are five different facts | Accepted — clarifies 0037 (supersedes and amends nothing); OD-3 resolved: connector admission requires a complete, approved capability chain |
| [0039](docs/decisions/ADR-0039-m13-test-hardening-and-evals-contract.md) | The M13 test hardening and evals contract: a closed coverage matrix, deterministic gap closure, recorded measurement, and a behavioural eval suite under an explicit execution policy that changes no product behaviour | Accepted — applies 0007 (its 24-scenario source replaced by closed in-repository sets; 0007 unedited), edits nothing |
| [0040](docs/decisions/ADR-0040-m13-owner-accepted-environment-gap.md) | An owner-accepted environment-unavailable gap in the M13 coverage matrix: a recorded gap, never a defect and never coverage | Accepted — amends 0039 in part (§B `gap` definition and §L's second M13.1 condition only; 0039 unedited) |
| [0041](docs/decisions/ADR-0041-m13-2-deterministic-repository-owned-eval-fixtures.md) | Deterministic, repository-owned input fixtures for the M13.2 eval cases: committed, builder-reproduced, bound to their cases, and inputs only | Accepted — amends 0039 in part (§E.2's last sentence and §E.5's second assertion only; 0039 unedited); resolves G-1 only |
| [0042](docs/decisions/ADR-0042-plugin-root-anchored-isolated-engine-entry.md) | The engine is entered through one plugin-root-anchored, isolated launcher, located by `${CLAUDE_PLUGIN_ROOT}` substitution in command and skill bodies | Accepted 2026-09-19 — the remediation architecture for M13-DEF-04. **Implemented 2026-09-20** (see §2, *Engine entry*); open verification items are in §20 item 11 |
| [0044](docs/decisions/ADR-0044-platform-format-eval-cases.md) | The eval case file is written in the platform's own case format and carries the BusinessOps semantic record beside it | Accepted 2026-09-22 — the migration architecture for M13-DEF-05. **Phase 1 implemented 2026-09-22**; stages 2 and 3 need a pilot trace, and M13-DEF-05 stays open |
| [0045](docs/decisions/ADR-0045-businessiq-owned-portable-runtime-resolution.md) | A BusinessOps-owned runtime resolver chooses the Python interpreter, so no command names one | Accepted 2026-09-22 — the remediation for M13-DEF-08; amends 0042 in part |
| [0046](docs/decisions/ADR-0046-wsl-excludes-windows-interpreters-from-automatic-resolution.md) | Under WSL, automatic interpreter resolution excludes Windows executables; the explicit override does not | Accepted 2026-09-23 — the remediation for M13-DEF-12; amends 0045 in part |
| [0047](docs/decisions/ADR-0047-routing-graders-accept-the-owning-command-route.md) | A routing grader accepts the owning BusinessOps command route as well as the skill route | Accepted 2026-09-25 — the remediation for M13-DEF-17; amends 0044 in part |
| [0048](docs/decisions/ADR-0048-declared-precondition-fixtures-for-eval-cases.md) | An eval case may declare one deterministic precondition fixture, staged at the path the case names | Accepted 2026-09-25 — the remediation for M13-DEF-19; amends 0041 in part |
| [0049](docs/decisions/ADR-0049-semantic-judge-splits-are-execution-unavailable.md) | A run whose semantic judge votes split is `execution_unavailable`, never a pass or a fail | Accepted 2026-09-25 — the remediation for M13-DEF-23; amends 0039 in part |
| [0050](docs/decisions/ADR-0050-provenance-aware-research-boundary.md) | The disclosure gate establishes each request fragment's provenance from the workspace's business data; non-public values never go at Tier 0, `never` values never go, and an unscreenable workspace refuses | Accepted 2026-09-26 — the remediation for M13-DEF-13; applies 0009 |
| [0051](docs/decisions/ADR-0051-pre-execution-write-approval-boundary.md) | A pre-execution write-approval boundary: a plugin-wide `PreToolUse` guard scoped by engagement, an allowlist write classifier, single-use capabilities granted only from the user's prompt, and an engine execution guard | Accepted 2026-09-26 — the remediation for M13-DEF-24; amends 0001 in part (hooks deferral) and 0035 in part (Option B's hook reasoning, write boundary only) |
| [0052](docs/decisions/ADR-0052-verifier-server-launched-through-the-runtime-resolver.md) | The local verifier MCP server is launched through the runtime resolver (`sh lib/bops_run.sh --verifier`) | Accepted 2026-09-27 — amends 0035 §3 in part (the declared command and arguments only); fixes R-13 |
| [0053](docs/decisions/ADR-0053-scout-reply-captured-by-the-harness.md) | The scout's reply reaches the engine through a harness capture, never a model copy | Accepted 2026-09-27; amends 0017 and §10 in part (the reply's carrier only) |
| [0054](docs/decisions/ADR-0054-businessops-product-identity-and-bops-namespace.md) | BusinessOps product identity and the `bops` technical namespace; history is not rewritten | Accepted 2026-09-30 |
| [0055](docs/decisions/ADR-0055-distribution-package-built-from-an-allowlist.md) | The installable package is built from an allowlist into its own plugin root; the development repository stays complete | Accepted 2026-09-30; amended by ADR-0057 |
| [0056](docs/decisions/ADR-0056-plugin-root-paths-for-shipped-reference-documents.md) | Commands and skills name `reference/` documents by `${CLAUDE_PLUGIN_ROOT}` path; amends ADR-0042's static-guard rule by that one form | Accepted 2026-09-30 |
| [0057](docs/decisions/ADR-0057-one-public-repository-for-source-and-package.md) | One public repository holds the source and the committed package (`dist/businessops`, submitted as the plugin path); no separate distribution repository | Accepted 2026-10-01 |
| [0058](docs/decisions/ADR-0058-krayons-global-rights-holder-and-support-identity.md) | The current rights holder and support identity: Prakash Meghani - Krayons Global, krayonsglobal@gmail.com; historical records keep the identity of their time | Accepted 2026-10-01; supersedes ADR-0054 in part |
| [0043](docs/decisions/ADR-0043-defect-status-for-verified-product-fixes.md) | Defect register status vocabulary for verified product fixes: `fixed_product` | Accepted 2026-09-20 — amends 0039 in part (§G.1 `status` vocabulary only; 0039 unedited). M13-DEF-04 is its first application |

---

## 20. Known limitations and assumptions

1. **Behavioural evaluation runs only on owner authorisation.** `claude plugin eval` was early-access gated here when
   BusinessOps began (R-01). **R-01 is closed (2026-09-26):** under ADR-0039 §E.1 (a) the M13.2 suite executed and was
   scored, and every case has admissible live evidence (§15). What remains is operational, not a gap: each execution
   needs the owner's authorisation and a cost ceiling, runs share the subscription's session limits, and some cases
   need a larger turn budget (`execution.max_turns`).
2. **No verified MCP servers** for accounting, spreadsheet, commerce or databases; only
   HubSpot and Slack. The file path is load-bearing (R-02).
3. **Python is assumed available.** Verified here (3.13.1, stdlib only). Not guaranteed
   everywhere; the Tier-4 CSV path and the runtime probe cover its absence (R-03).
4. **Tier-3 xlsx gaps** — built-in numFmt ids not yet resolved (found by probe); shared
   formulas, external references and encrypted workbooks must be detected and refused
   rather than guessed (R-04).
5. **Dependency supply chain** — Tier 2 introduces openpyxl. Pinned, isolated, consented,
   optional, but it is a new surface (R-06).
6. **Re-identification checking is heuristic.** It will sometimes be conservative and block a
   harmless query; that is the correct direction to err (R-07).
7. **Description discriminability** across 37 components is the real scaling constraint, and
   is hard to measure without the eval harness (R-05). Description overlap was measured deterministically on
   2026-09-18 (M13-MEAS-D2, `docs/testing/measurements.md`) and recorded with no threshold. Routing itself is now
   exercised live by the M13.2 routing cases (§15); no discriminability threshold is set.
8. **External research quality** is bounded by what is publicly published. Some markets have
   no reliable sizing; BusinessOps says so rather than estimating.
9. **Forecasting is not a guarantee.** Methods are transparent and assumption-registered;
   accuracy is bounded by history and volatility. Selection moves between methods as trailing periods are removed
   (M13-MEAS-D3, R-10).
10. **Large CSV files are fully materialised, not streamed.** §17's "engine streams" is not yet true: chunked streaming
    is an M3 deferral. The recorded processing mode says so honestly: a pass that read every row is `full` and
    complete at any size. Before M14-5 it was inferred from the row count, and above 100,000 rows a complete pass was
    labelled `streamed` and incomplete (defect M13-DEF-03, fixed in M14-5).
11. **The engine entry depends on a platform text substitution.**
    - **The entry.** Every command and skill enters the engine through `lib/python/bops_run.py` (ADR-0042; §2, *Engine
      entry*). The launcher finds the engine from its own location, requires `python -I`, keeps the working directory
      and `PYTHON*` variables out of imports, and verifies where `bops` came from.
    - **What it replaced.** The launcher replaced the working-directory-relative `sys.path.insert(0, 'lib/python')`
      entry. That entry could not import the engine from a user's directory, and it was an import-hijack path: defect
      M13-DEF-04, remediated 2026-09-20.
    - **The dependency.** The launcher is located through `${CLAUDE_PLUGIN_ROOT}` substitution in command and skill
      bodies. That substitution has been verified at runtime on Claude Code 2.1.278, on Windows, only.
    - **Still unverified:**
      - the minimum CLI version (V-4);
      - Unix-like systems;
      - the eval sandbox (G-3).
    - **Encoding.** Under `-I`, a user's `PYTHONIOENCODING` or `PYTHONUTF8` no longer affects the engine's output
      encoding. None is set in the observed Claude Code shell, where the stdout encoding is the same with or without
      `-I`.
    - **Reader tiers.** A user-site openpyxl is no longer Tier 1 (ADR-0042, *Compatibility*).
12. **The research boundary screens the working directory's data, whole values only (ADR-0050).**
    - Business data kept outside the working directory is not screened.
    - One word of a multi-word internal value does not match; the whole value does.
    - Columns the ingestion rules class as `public` (for example `Segment`) are not registered.
    - The model can still reach web tools directly. The pipeline and the scout brief are governed, and the scout's
      missing file access remains the structural backstop.
13. **The write guard is runtime-measured on 2.1.283, and scoped by engagement (ADR-0051).**
    - Claude Code 2.1.283 was measured to honour a plugin-wide `PreToolUse` `deny` before `Bash`, `Write` and `Edit`
      run, in five permission modes.
    - A live session proved the approval path: a user-message `approve <code>` granted through `UserPromptSubmit`,
      the exact retry executed once, and a retarget, an operation change and reuse were refused. It used a scripted
      stream-json feeder, not a person typing (`docs/development/2026-09-26-m13-def-24-live-grant-verification.md`).
    - These were not measured: `plan` mode, a marketplace-installed plugin, subagents, and `claude plugin eval`.
    - Files under the system temporary directory (`/tmp`) are free scratch, and so lie outside the approval boundary.
    - A write made before BusinessOps is engaged in a session is not governed.
    - 2.1.283 does not report a prompt's `source`, so a prompt injected by a route other than the denied tools could
      carry an approval phrase.
    - Approving an `execute` operation approves arbitrary code run as the user.
    - Every matched tool call, in every session with BusinessOps installed, starts a shell and Python. This took 1.6–2.6
      s per call, measured on WSL2 with the plugin on `/mnt/d`.
