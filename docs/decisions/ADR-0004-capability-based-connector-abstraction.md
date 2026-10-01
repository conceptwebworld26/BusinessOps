# ADR-0004 — Capability-based connector abstraction

**Date:** 2026-09-08
**Status:** Accepted
**Deciders:** Project owner, Claude (architecture gate)

## Context

The specification lists sixteen named systems to integrate: QuickBooks, Xero, NetSuite,
Salesforce, HubSpot, Shopify, Stripe, PostgreSQL, MySQL, Snowflake, BigQuery, Databricks,
Google Sheets, Google Drive, Excel/OneDrive and Slack.

The local plugin catalogue (466 KB, three marketplaces) was searched for MCP servers for
each. Findings:

| System | Finding |
|---|---|
| HubSpot | Working server — `https://mcp.hubspot.com/anthropic`, shipped by the `marketing` plugin |
| Slack | Server exists (`https://mcp.slack.com/mcp`) — write-capable |
| QuickBooks, Xero | **Nothing found** |
| Google Sheets, Drive, Excel/OneDrive | **Nothing found** |
| Salesforce, NetSuite, Shopify, Stripe | Only developer-tooling skill packages, not business-data servers |
| Postgres, MySQL, Snowflake, BigQuery, Databricks | Vendor servers exist in the wider ecosystem; none verified here |

The specification itself says "Do not assume all connectors exist" and "Uploaded Excel/CSV
files must remain a viable standalone path".

## Problem

How should skills address data sources, given that most named connectors have no verified
MCP server and the set will change over time?

## Options considered

### Option A — Name products directly in skills
`biq-sales-intelligence` calls the QuickBooks tool by name.

- Pros: direct and simple.
- Cons: every skill breaks when a connector is absent — which is the common case today.
  Adding a connector means editing every skill. Skills become coupled to vendors.

### Option B — Capability placeholders resolved by a broker
Skills request `~~accounting`, `~~crm`, `~~commerce`, `~~warehouse`, `~~spreadsheet`,
`~~chat`. `biq-connector-broker` resolves the placeholder at runtime to whatever server is
connected, enforces read-only, and returns a *named absence* when nothing matches.

- Pros: skills are vendor-neutral and never change when connectors do; adding a connector is
  a `.mcp.json` entry plus a capability-map row; absence degrades gracefully with a specific
  message and a file-upload fallback. This is the pattern the official `marketing` plugin
  already uses (`CONNECTORS.md`), so it is proven in production.
- Cons: one indirection; capability semantics must be defined carefully.

### Option C — Ship `.mcp.json` entries for all sixteen systems anyway
- Pros: looks complete.
- Cons: would require **inventing endpoint URLs** for systems with no known server. Those
  entries would fail at connect time, producing confusing errors and eroding trust in every
  other part of the product. Rejected outright.

## Decision

**Option B.** Skills address capabilities, never products. `biq-connector-broker` performs
discovery, capability mapping, read-only enforcement and named degradation. `.mcp.json`
ships **only endpoints verified to exist**; every other category is documented in
`CONNECTORS.md` as user-configurable. Adding any server is a Connector-gate decision
requiring explicit user approval.

The uploaded Excel/CSV path is treated as **load-bearing, not a fallback** — for accounting
and spreadsheet data it is currently the *only* path.

## Reason

The connector survey turned the specification's cautionary note into a hard fact: for the
two most important categories in a business-intelligence product — accounting and
spreadsheets — no verified server exists. An architecture that assumed otherwise would be
undeliverable. Option B is the only one that stays honest about that while still being ready
the moment a server appears.

Option C is not merely suboptimal; fabricating endpoints is the connector equivalent of
fabricating a citation, and the same rule applies.

## Consequences

**Positive** — skills never change when the connector landscape does; missing connectors
produce a specific, actionable message rather than an empty result; no fabricated endpoints;
the file path is designed as a first-class citizen from day one.

**Negative** — the delivered v1 will have far fewer live integrations than the specification
implies. This is a requirement gap that needs the owner's acknowledgement, tracked as
risk R-02.

**Follow-up required** — `CONNECTORS.md` must state plainly which categories have no server
today. `/business-health` and friends must be fully usable from a spreadsheet alone.

## Revisit when

A first-party MCP server appears for accounting or spreadsheets, or the owner decides to
fund a custom local MCP server for a specific system.
