# ADR-0011 — Business Context as a first-class component

**Date:** 2026-09-08
**Status:** Accepted
**Deciders:** Project owner (architecture review), Claude

## Context

The original architecture treated business characteristics as scattered configuration:
currency and fiscal year in `config/`, materiality thresholds in `config/`, and nothing at
all capturing industry, business model or what the company actually sells.

Architecture review identified the consequence. The KPI registry lists ~27 metrics, and the
original design gated each one on **data availability alone**. That is the wrong test. A
consulting firm's spreadsheet may well contain enough columns to compute inventory turnover;
the number would be meaningless. A SaaS business needs ARR, MRR, NRR and churn; a retailer
needs AOV, inventory turnover, sell-through and same-store sales; a services firm needs
utilisation, billable hours, realisation and project margin. Presenting all 27 to everyone is
noise that buries the handful that matter.

There is a second consequence. ADR-0009's Tier 0 external research needs public context —
industry, business model, geography, product category — to construct a benchmark query at
all. Without a context component there is nowhere for that to live, and no way to mark which
fields are safe to externalise.

## Problem

Where do a business's identity, characteristics, vocabulary and preferences live, and how do
they shape analysis?

## Options considered

### Option A — leave it in `config/`
- Pros: nothing new.
- Cons: config is flat key-value settings; this is a described entity with structure,
  privacy classes and validation rules. It also gives KPI relevance nowhere to live.

### Option B — infer context from the data each time
- Pros: no setup for the user.
- Cons: inferring "you look like a SaaS business" from column names is exactly the guessing
  the ambiguity protocol forbids. Getting it wrong silently changes which KPIs are presented.

### Option C — a first-class, persistent, user-confirmed Business Context component

## Decision

**Option C.** Business Context is a first-class component: a `biq-business-context` skill,
a `business_context.json` document, and a schema.

### Content

Identity and characteristics — business name, industry (with a taxonomy code), business
model, organisation size band, products/services and their categories, geographic markets.
Reporting — fiscal year start, currency, number/date format, reporting period, output
preferences. Analysis — KPI definition overrides, materiality thresholds, business
terminology glossary. Plus any other user-approved context.

Every field is optional. **Absence is handled by asking or by narrowing scope — never by
guessing.**

### Storage

Project-local at `./.businessiq/business_context.json`, gitignored, because the context
belongs with the data it describes and consultants analyse many businesses. A user-level
file at `~/.claude/businessiq/business_context.json` is supported for single-business users.
Project-local wins where both exist.

### Precedence

`command argument → project business context → user business context → shipped defaults`

Business Context replaces the generic project/user config layers for everything it covers;
`config/businessiq.defaults.json` remains the shipped floor. This resolves the overlap the
original design had between "config" and "business characteristics" by making Business
Context *the* business-specific layer.

### Privacy

Business Context is confidential and classified field by field per ADR-0009. A designated
**externalizable subset** — industry, business model, size *band*, geographic market,
product *categories* — is what Tier 0 research queries are built from. Business name is
externalizable only when the analysis is explicitly about the user's own public company (a
`/company-analysis` of oneself); otherwise it is Tier 2. Nothing else in the document is
externalizable by default.

### Validation

Schema-validated on load. Industry and business model come from a controlled vocabulary; an
unrecognised value triggers a clarifying question rather than a silent pass. Contradictions
between context and data (context says GBP, data is in USD) surface as a quality finding,
never a silent override.

### KPI relevance

The KPI registry gains an `applicable_models` field, and the engine returns a **fourth**
result bucket alongside `computed` / `unavailable` / `partial`:

- `not_applicable` — the data may support it, but the business model makes it meaningless.

This is a genuinely different statement from `unavailable` ("we lack the inputs") and users
need to be able to tell them apart. When Business Context is absent, no KPI is suppressed;
instead the output notes that relevance filtering is off and offers to set context up.

### Consumption

Every command loads Business Context at pipeline step 1. It shapes information requirements
(step 2), KPI selection (step 8), materiality thresholds (step 10), external query
construction (step 5), and output formatting (step 18).

## Reason

The decisive argument is that KPI relevance has no other correct home. Data availability
cannot answer "should this business see inventory turnover?", and inferring it silently is
the failure the ambiguity protocol exists to prevent. Making context explicit, persistent and
user-confirmed turns a guess into a stated fact the user can correct.

Promoting it also resolves two things the original design left awkward: the config/context
overlap, and Tier 0 research having no sanctioned source of public business terms.

## Consequences

**Positive** — analysis is relevant rather than exhaustive; a new business type is supported
by adding vocabulary and KPI applicability, not code; Tier 0 research gets a clean,
classified source of public terms; the config precedence chain becomes coherent.

**Negative** — first-run setup exists where previously there was none (mitigated: every
field optional, elicited conversationally, and BusinessIQ works without it at reduced
relevance). A controlled vocabulary for industry and business model must be maintained.

**Follow-up required** — `biq-business-context` skill, `business_context.schema.json` and the
controlled vocabulary land in Milestone 1 so the vertical slice can exercise them; the KPI
registry's `applicable_models` field and the `not_applicable` bucket land with the KPI engine.

## Revisit when

The controlled vocabulary proves too rigid for real businesses, or a business type needs
relevance rules that `applicable_models` cannot express.
