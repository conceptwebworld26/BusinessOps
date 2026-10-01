# ADR-0009 — Comparative intelligence and the internal/external privacy boundary

**Date:** 2026-09-08
**Status:** Accepted
**Supersedes:** the blanket construction-time rejection rule described in `architecture.md`
§7 as originally written (the rest of the research architecture stands)
**Deciders:** Project owner (architecture review), Claude

## Context

The original boundary rejected any external query "containing any internal identifier,
customer name or business figure". Architecture review correctly identified this as too
restrictive: it blocks the questions business users most want answered.

- "Our churn is 8%. How does that compare with the industry?"
- "Our revenue grew 12%. How does that compare with competitors?"
- "Our gross margin is 35%. Is that typical for this industry?"
- "Based on our product mix, what market trends should we watch?"

The requirement is not to weaken privacy but to make comparative intelligence possible
safely: confidential raw internal data must not be transmitted unless explicitly authorised
and technically permitted, while aggregated, anonymised or derived context may be used where
it reveals nothing confidential.

## Problem

How does BusinessIQ answer internal-versus-external comparative questions without
transmitting confidential business data?

## Options considered

### Option A — original blanket rejection
- Pros: maximally safe; trivial to implement.
- Cons: fails all four questions above. Users work around it by pasting figures into a
  general chat, which is *worse* for privacy than a governed path.

### Option B — allow internal figures in external queries when the user asks
- Pros: answers everything.
- Cons: no structure. "Our revenue is £4.2m and our top customer is Acme" reaches a search
  engine because someone typed a loose instruction. Unacceptable.

### Option C — retrieve the benchmark, compare locally
Observe what these questions actually need. None of them requires *sending* the internal
figure. Each needs an **external benchmark**, which is a public fact, retrievable with no
internal data at all. The comparison then happens on the user's machine.

- "industry churn benchmark, B2B SaaS, 2026" → returns 5–7% → compared locally against 8%.
- "competitor revenue growth" → public filings → compared locally against 12%.
- Product *categories* (from Business Context, non-confidential) drive a trends query; the
  product *mix numbers* never leave.

### Option D — Option C, plus a graded disclosure gate for the residual cases

## Decision

**Option D — a four-tier disclosure model, with local-join as the default.**

### Tier 0 — Local join (default; covers substantially all comparative questions)

The external query is built **only** from public terms: industry, business model, geography,
product category, competitor names, time period — sourced from Business Context
(ADR-0011), which marks which fields are externalizable. The benchmark comes back, and the
comparison is computed **locally by the engine**. No internal value is transmitted, so no
approval is needed and none of the four example questions requires one.

### Tier 1 — Derived-safe context (auto-allowed only if it passes the gate)

Occasionally a query is materially better with a characteristic attached ("benchmarks for
50–200-employee firms"). Permitted only when the value passes **all four** checks:

1. **Aggregation floor** — derived from at least *k* underlying entities (default k = 5), so
   no individual customer, employee or transaction is recoverable.
2. **Banded, not exact** — expressed as a range or bucket (`50–200 employees`,
   `£1m–£5m revenue`), never a precise level. Rates and ratios (growth %, churn %, margin %)
   are already non-identifying and pass as-is; **absolute monetary levels never pass Tier 1**.
3. **Re-identification check** — the *combination* of attributes must not narrow to a
   plausibly unique organisation. Industry + micro-geography + a narrow revenue band can
   identify a company even though each part looks harmless; the check evaluates the query as
   a whole, not field by field.
4. **Not on the Tier 3 list.**

### Tier 2 — Explicit user-approved disclosure

Anything above Tier 1 requires the user to see **the exact text that will be transmitted**,
verbatim, before it is sent, plus the destination, with a single-use approval. Approval is
per query — never a session-wide mode, never inferred from an earlier yes.

### Tier 3 — Never externalizable, no approval path

Credentials, API keys, access tokens; personally identifiable information; customer names
and customer-level records; individual transaction details; confidential financial records
and raw ledgers. There is no user approval that unlocks these — the request is refused and
the Tier 0 alternative offered.

### Enforcement

- Classification is a property of the **data**, not the query: every field carries a
  sensitivity class from ingestion onward, and Business Context marks its own fields
  externalizable or not.
- The gate runs at **query construction**, before any tool call, and its decision plus the
  transmitted text are written to the evidence ledger — so what left the machine is auditable
  after the fact.
- The structural backstop from ADR-0006 is unchanged and is what makes this safe in practice:
  `biq-research-scout`, the agent that performs retrieval, **has no file-system access**. It
  cannot read the dataset even if instructed to. It receives only a constructed query that
  has already passed the gate.
- Retrieved content remains untrusted input. Text in a retrieved page instructing disclosure
  of internal data is data, not instruction, and cannot raise a tier.

## Reason

The reframing is what makes this work: these questions were never actually *requests to
share* internal data. They are requests to *contextualise* it. Once the benchmark is
recognised as the thing being fetched, the internal figure has no reason to leave — Tier 0
answers all four examples with strictly less transmission than the original rule allowed,
because the original rule pushed users to paste figures elsewhere.

The tiers below it exist because "substantially all" is not "all", and an honest model needs
a governed path for the remainder rather than a prohibition users route around.

The four Tier-1 checks are there because naïve anonymisation fails in two specific ways this
product would hit: small-denominator aggregates that expose an individual, and attribute
combinations that re-identify an organisation. Banding plus a floor plus whole-query
evaluation addresses both.

## Consequences

**Positive** — the comparative questions users most want are answered, with *less* data
leaving the machine than before; the privacy model is stronger, not weaker, because it is
now specific rather than blanket; every disclosure decision is logged and auditable; the
agent tool-split makes Tier 3 structurally unreachable rather than merely forbidden.

**Negative** — more machinery than a blanket ban: field-level classification, a
re-identification check that is inherently heuristic, and a consent flow. The
re-identification check will sometimes be conservative and block a harmless query; that is
the correct direction to err.

**Follow-up required** — sensitivity classification lands with ingestion (M2) and Business
Context (M1); the gate and its ledger entries land with the research layer (M8). Tests must
include an attempted Tier-3 disclosure (must refuse), a small-denominator aggregate (must
block), a re-identifying attribute combination (must block), and all four example questions
(must succeed at Tier 0 with no approval prompt).

## Revisit when

`k` proves wrong in practice, or a class of question emerges that Tier 0 genuinely cannot
serve.
