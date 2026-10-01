# Connectors

BusinessOps addresses **capabilities**, never products. A skill asks for `~~accounting`, and
the capability resolves **only to a connector BusinessOps has registered** — never to whatever
server happens to be connected. Skills still name no vendor, so adding a connector never
requires changing a skill.

> **Status:** the connector layer is Milestone 12. Its contract is ADR-0037, accepted by the project
> owner on 2026-09-17, together with the identity rule below. The optional-connector and user-connection
> lifecycle below is ADR-0038 (M12-A.1), accepted on 2026-09-18 with OD-3. **Milestone 12-B — the
> connector registry, capability resolution, named absence and the value-free catalogue engine — is
> implemented, reviewed and approved by the project owner (checkpoint `990e88d`, 2026-09-18), and its registry is empty
> by design.** Milestone 12 is complete on M12-B alone (ADR-0037 OD-1); **connected-system record reads (Milestone
> 12-C) remain blocked** and are not part of that completion. No
> BusinessOps-owned, value-free discovery capability existed to take through the Connector Gate, so no
> Gate measurement was taken and **no connector is registered, supported or usable today**; every
> capability resolves to a named absence with the file alternative. What is proven is the machinery -
> registry exactness, admission, identity binding and fail-closed parsing - by deterministic tests,
> most against a synthetic fixture. **No real connector discovery has run**, and none can until a
> connector is admitted. This page records the verified landscape the architecture was designed
> against, so expectations are accurate from the start.

## Every connector is optional

BusinessOps never needs a connector. A connector that is missing, not connected, unreachable or refused degrades only
the one capability it serves, names the reason, and offers the file-export alternative. Every other workflow runs
unchanged, and a spreadsheet or CSV alone gives you the full internal-analysis capability.

A **planned** (designated, future) connector is one this page names as intended. Planned is not supported: it gives
BusinessOps no connector at all. Beyond that, five separate facts decide whether BusinessOps can use a connector, and
none substitutes for another:

| Fact | Means | Who decides |
|---|---|---|
| **Supported** | BusinessOps has registered the connector, which it does only once at least one of its capabilities has passed the Connector Gate in full | BusinessOps, after the Connector Gate |
| **Connected** | You have signed in to BusinessOps's own declared server for it, through your Claude platform | You, through the platform |
| **Authorized** | Your vendor account permits the call; separately, BusinessOps's exact-identity checks pass for that one operation | The vendor; BusinessOps's checks, per operation |
| **Verified capability** | The exact tool has been measured and approved at the Connector Gate | BusinessOps, at the Connector Gate |
| **Available for use** | All of the above hold for one operation, and it succeeded | Recomputed every time; never remembered |

- **Not connected ≠ unsupported.** A supported connector you have not connected is reported as *not connected*.
- **Connected ≠ verified.** Signing in does not make any tool usable. Only Gate-measured, registered tools are.
- **Connected ≠ authorized for arbitrary tools.** A connection lets BusinessOps call no tool beyond its exact registered,
  Gate-measured discovery tools.
- **Connecting is your choice, and it happens in the platform.** BusinessOps never starts the sign-in and never asks for,
  sees or stores a password, API key or token. BusinessOps does not control the platform's connection screens, so this
  page does not describe them. A connector's integration page will describe the connection step only once the
  Connector Gate has observed it.
- **Only BusinessOps's own declared server counts.** Connecting the same vendor through another plugin, or through a
  server you added yourself, does not make it available to BusinessOps.

## Exact registered identity

- BusinessOps uses a connector only through its **exact registered identity**: a registered
  connector, the exact server entry BusinessOps itself declares in `.mcp.json`, and the exact
  tool names measured for that entry.
- **Same vendor is not same identity.** A HubSpot (or any other) server you connected yourself,
  or one another plugin provides, does not stand in for BusinessOps's registered entry, even if
  it offers the same tools.
- **Unregistered servers and tools are not usable by BusinessOps.** BusinessOps never discovers
  connected servers and adopts them.
- A server/tool binding is usable only after it passes the **Connector Gate**: measured, with
  the result approved and recorded, and matching both the registry and the tool grant exactly.
  If any of these disagree, BusinessOps refuses to use it.
- Connector Gate approval covers value-free **discovery** of what a system holds structurally.
  It does **not** authorize reading business records (blocked, Milestone 12-C), writes or
  administrative actions.
- Being connected, available or approved is never evidence and never authorization.

---

## The honest picture

During the architecture phase the full local plugin catalogue was searched for MCP servers
for every system in the product specification. Most do not have one.

| Category | Placeholder | Verified server available | Notes |
|---|---|---|---|
| CRM | `~~crm` | ✅ **HubSpot** — `https://mcp.hubspot.com/anthropic` | Shipped by Anthropic's `marketing` plugin |
| Chat | `~~chat` | ✅ **Slack** — `https://mcp.slack.com/mcp` | Write-capable; not eligible in Milestone 12 |
| Accounting | `~~accounting` | ❌ **None found** | QuickBooks, Xero: nothing. NetSuite: developer tooling only, not a data server |
| Spreadsheet | `~~spreadsheet` | ❌ **None found** | Google Sheets, Google Drive, Excel/OneDrive |
| CRM | `~~crm` | ❌ Salesforce | Developer tooling packages only |
| Commerce | `~~commerce` | ❌ Shopify, Stripe | Developer tooling packages only |
| Warehouse / DB | `~~warehouse` | ❌ Not verified here | Postgres, MySQL, Snowflake, BigQuery, Databricks — vendor servers exist in the wider ecosystem but none were verified in this environment |

"Verified server available" means the endpoint was found to exist during the architecture
phase. **Neither HubSpot nor Slack is registered or Connector-Gate measured**, so neither is
usable by BusinessOps yet. `~~chat` (Slack) is not eligible in Milestone 12.

**HubSpot is a designated optional future connector for BusinessOps** (`~~crm`, ADR-0038). It is **not** a
currently supported or usable BusinessOps connector in this repository, because no BusinessOps-owned, Connector-Gated
value-free discovery capability has yet been approved. It is not registered, not declared in BusinessOps's
`.mcp.json` and not Connector-Gate measured, and no HubSpot tool is known to BusinessOps. So there is no BusinessOps
HubSpot connector and no BusinessOps HubSpot connection to make. A HubSpot server you connected through another plugin
is not used by BusinessOps. If a BusinessOps HubSpot connector is admitted in future, it will be:

- connected only by you, through the platform;
- bound to its exact registered identity;
- usable only through Connector-Gate measured tools;
- limited to value-free **discovery** of what your CRM holds structurally, with no reading of records (Milestone 12-C,
  blocked) and no writes or administrative actions in v1.

Until then, export CRM data to CSV or Excel.

**We will not invent endpoint URLs.** Shipping a plausible-looking address for a server that
does not exist produces confusing connect-time failures and destroys trust in everything
else the product says. A category with no verified server is documented as having none.

## What this means in practice

**The file path is load-bearing, not a fallback.** For accounting and spreadsheet data —
the two most important sources in a business-intelligence product — uploading a file is
currently the *only* path. BusinessOps is designed so that a spreadsheet alone gives you the
full internal-analysis capability, permanently, with no connector configured.

See [README](README.md#data-sources-and-connectors) for the four-tier Excel reader.

## Adding a connector

When a server exists for a capability you need, it becomes usable by BusinessOps only when all
of these agree exactly:

1. A `.mcp.json` entry that BusinessOps ships — identity only (`type`, `url` or `command`).
   **Never a token.**
2. A registry entry declaring the connector, its capability and each tool's exact name and
   class.
3. An approved **Connector Gate** record measuring that exact server and tool.
4. The matching tool grant.

**Admission rule (ADR-0038, OD-3).** A connector is registered, its `.mcp.json` entry is shipped, and it is described
as supported only when at least one of its declared capabilities has this complete, approved chain. In Milestone 12
that capability is value-free discovery. Being named on this page, having a vendor endpoint, being exposed by another
plugin, or being something you can sign in to elsewhere does not make a connector supported.

Then add a row to the capability map above. No skill changes. The static test suite refuses a
registry, `.mcp.json` entry or agent grant that does not meet this rule. Adding a server to the shipped
`.mcp.json` is an approval gate in this project's workflow, because it is a claim that the
endpoint is real and verified.

## Permissions

| Operation | Behaviour |
|---|---|
| Discovery tools (value-free structure, Connector-Gate measured, registered, granted) | Called within a workflow, no approval |
| Record-read tools | **Not used** — connected-system record reads are blocked (Milestone 12-C) |
| Write and administrative tools | **Not used — no write or administrative path exists in v1.** Any future write capability needs its own decision and explicit per-action approval naming the system, the record and the change |
| `~~chat` | Write-class by definition — not a usable connector in Milestone 12 |
| Exports of BusinessOps output | Always gated — explicit per-action approval |
| Accounting/CRM record mutation | Never automatic, under any instruction |
| Financial transactions | Prohibited outright |

BusinessOps is a read-only product in v1. Write-back to business systems is deliberately out
of scope.

## Authentication

BusinessOps **stores no credentials of any kind** — no API keys, tokens or connection
strings, in the repository, in configuration, in logs or in reports. Authentication is
delegated entirely to each MCP server and its own OAuth flow, run by the platform when **you**
start it. BusinessOps never starts it, never asks you to paste a credential, sends nothing to
authenticate, and does not read platform configuration to find out what is connected.

## When a connector is missing, not connected or unavailable

BusinessOps degrades by **naming the reason**, never by silently returning nothing. Each reason is reported
distinctly:

| Situation | BusinessOps says, in substance |
|---|---|
| No connector registered for the capability — **every capability today** | No accounting connector is available in this version of BusinessOps |
| Registered, but the capability is not verified | The connector is supported, but this capability is not available in this version |
| Supported, but you have not connected it | The connector is an optional supported connector, but it is not connected; connecting is yours to do through the platform |
| Connected, but unreachable in this session | The connector could not be reached |
| Connected, but your account refused the request | The connector did not accept the request; BusinessOps does not ask for broader access |

Every one of these ends the same way: export the data to Excel or CSV and supply the file, and the same analysis
will run. A missing or disconnected connector degrades that capability only — it never fails the whole workflow.
