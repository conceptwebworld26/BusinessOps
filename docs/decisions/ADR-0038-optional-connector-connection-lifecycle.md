# ADR-0038 — Optional connectors and the user-initiated connection lifecycle: supported, connected, authorized, verified and available are five different facts

**Date:** 2026-09-18
**Status:** Accepted — 2026-09-18, by the project owner, with OD-3 resolved (see *Owner decision — OD-3*). Acceptance
approves the contract only. It authorizes no implementation, no connector, no registry entry, no `.mcp.json` entry, no
Connector Gate result and no runtime use.
**Deciders:** Project owner (M12-A.1 brief: "HubSpot must be an optional BusinessIQ connector"; OD-3; acceptance),
recorded in the M12-A.1 clarification and its final remediation (decision only)
**Supersedes:** none. **Amends:** none. ADR-0037 is not edited, weakened or replaced (see *Relationship to ADR-0037*).
**Relates to:** [ADR-0037](ADR-0037-m12-connector-layer-contract.md) (the connector layer contract this ADR clarifies),
[ADR-0004](ADR-0004-capability-based-connector-abstraction.md) (capabilities, named absence, the file path is
load-bearing), ADR-0001 (verified platform facts only), ADR-0009 (disclosure tiers), ADR-0010 (approval follows
consequence), ADR-0014 (the tool grant is the boundary), ADR-0017 (no model authors source data), ADR-0018 (a registry,
never a heuristic), ADR-0035 (sealed, consumed-once requests), ADR-0036 (the reserved `biq-data-profiler` agent).

## Context

### What the accepted contract already fixes

ADR-0037 (accepted 2026-09-17, with OD-1 and OD-2) fixes the connector trust chain. Verified by reading the repository
at `09cb52b`:

| ADR-0037 | Statement |
|---|---|
| §B.1, §B.4 | A connector is usable only through its **exact registered identity**: a registry declaration, the exact server entry BusinessIQ ships in its own `.mcp.json`, and the exact tool name measured for that entry. A same-vendor server under another key or namespace never qualifies |
| §B.2 | Three layers must agree exactly: **registry declaration** (what BusinessIQ supports), **Connector Gate measurement** (what the server and tool demonstrably provide), **runtime grant** (what the agent can call). No single layer authorizes use |
| §B.3 | Vendor authorization belongs to the user and the vendor, is held by the platform's OAuth, and is never represented, stored, inferred, asserted or requested by BusinessIQ |
| §E.6, §K | OAuth is run by the platform **when the user starts it**. The agent holds no authentication tool, and no BusinessIQ markdown instructs one. BusinessIQ observes only the relayed failure code `connector_not_authorized` |
| §H | Closed failure codes, including `connector_not_configured`, `capability_unsupported`, `binding_mismatch`, `connector_unavailable`, `connector_not_authorized`, `authentication_failure`, `authorization_failure`, `stale_metadata`, `blocked_prerequisite` |
| §C.2 | `configured` means *registered and declared*, and asserts nothing about measurement, grant, reachability, authentication or authorization |
| *Consequences* | "Users who connected a vendor server through another plugin must also authenticate BusinessIQ's own declared entry" |

The repository today holds **no connector registry, no connector `.mcp.json` entry, no Connector Gate record and no
connector agent**. `.mcp.json` declares only `biq-verifier`. M12-B is `PLANNED` and not started; M12-C is `BLOCKED`.

### The product requirement

The owner has stated the requirement this ADR records:

- **HubSpot must be an optional BusinessIQ connector.** BusinessIQ must remain fully usable without it.
- A user who wants HubSpot must have a **proper, explicit, user-initiated** way to connect it, through the platform's
  supported connection mechanism.
- BusinessIQ must **not** assume HubSpot is connected merely because a HubSpot MCP server exists in a Claude session.

### What ADR-0037 leaves implicit

ADR-0037 speaks of a connector "which the user has authenticated" (§A.1) and a "user-authenticated connector" (§K), and
it maps an unauthenticated connector to `connector_not_authorized` (§H). It does not:

- define what an **optional** connector is, or state that its absence, disconnection or failure must leave core
  BusinessIQ intact;
- separate *supported*, *connected*, *authorized*, *verified* and *available* as distinct facts, with who decides each;
- define the **lifecycle** of a connector from the user's point of view, or what BusinessIQ tells the user at each
  stage;
- say what the "proper way to connect" is, or who owns it.

Those gaps invite exactly the conflation the owner's requirement forbids: "HubSpot is supported, therefore connected",
or "HubSpot is connected, therefore usable".

### Observations — not measurements

- **Owner-reported.** The M12-A.1 brief reports that a recent M12-B Connector Gate examination found the current
  Claude session exposes third-party business-system servers only through authentication tools, and no qualifying
  value-free discovery capability. **That examination is not recorded in the repository** (no development record, no
  Gate record). It is cited here as the owner's report and is not treated as a Connector Gate measurement.
- **This session.** The tool list available while this ADR was written contains
  `mcp__plugin_marketing_hubspot__authenticate` and `mcp__plugin_marketing_hubspot__complete_authentication`, and no
  other HubSpot tool. This is consistent with the owner's report. It is an observation of **another plugin's**
  server, which does not qualify as BusinessIQ's connector under ADR-0037 §B.1 item 9, and it measures nothing about a
  server BusinessIQ would declare. No tool was called.

### The architectural question

*Can "a proper way to connect HubSpot" be specified at the BusinessIQ contract level without specifying a particular
Claude platform UI?* **Yes.** BusinessIQ owns the lifecycle and the security requirements around a connection. The
platform owns the connection mechanism itself. BusinessIQ can require that a supported connection path exists, that
the user initiates it, that it passes through the platform and never through BusinessIQ, and that BusinessIQ
describes it only from what the Connector Gate observed. It cannot, and must not, define the platform's screens,
commands, URLs, OAuth endpoints or APIs (ADR-0001: verified platform facts only). None is recorded in this repository,
so none is named here.

## Problem

Define the optional-connector model and the user-initiated connection lifecycle precisely enough that M12-B can
implement it and that no state — in code, documentation or a user-facing message — can treat one of *supported*,
*connected*, *authorized*, *verified* or *available* as implying another, without weakening ADR-0037 or inventing
platform facts.

## Options considered

### Option A — A connected server is an enabled connector

If the user has connected HubSpot in the platform, BusinessIQ uses it.

**Rejected.** It is ADR-0004's superseded "whatever server is connected" under another name. It contradicts ADR-0037
§B.1 items 9–11 (no substitution, no model-discovered servers, availability never implies authorization). It would
admit the `marketing` plugin's HubSpot server observed above.

### Option B — BusinessIQ manages the connection

BusinessIQ starts OAuth, asks the user for an API key or token, or holds a token in a local proxy.

**Rejected.** `CLAUDE.md` §7: BusinessIQ never stores, reads, logs or transmits a secret. ADR-0037 rejected the
credential-holding proxy (Option C) and forbids BusinessIQ from starting authentication (§E.6, §K).

### Option C — BusinessIQ detects connection by inspecting platform configuration

Python reads the platform's MCP configuration or credential store to learn what is connected.

**Rejected.** ADR-0037 §B.1 item 10 and §E.6: no module reads platform configuration, credential stores, `~/.claude*`,
`.env*` or a keychain, and nothing enumerates the session's servers to find connectors. Such files can hold tokens.

### Option D — A lifecycle contract around a platform-owned connection

BusinessIQ defines what an optional connector is, five distinct facts, a closed lifecycle mapped onto ADR-0037's
existing codes, and the user messages at each stage. The platform provides the connection mechanism. ADR-0037's trust
chain is unchanged and still decides use.

**Chosen.**

## Decision

**A BusinessIQ connector is optional. Being supported, being connected, being authorized, having a verified capability
and being available for use are five separate facts, decided by different parties, and none substitutes for another. A
connector named in documentation as planned is none of them. A connector is admitted as supported only when its declared
v1 capability scope has at least one complete, approved, BusinessIQ-owned Connector-Gated capability chain (OD-3). The
user connects a supported connector only through the platform's own mechanism, which BusinessIQ neither starts,
performs, observes directly nor stores anything from. A connection grants BusinessIQ nothing: every use still requires
ADR-0037's exact registered identity, Connector Gate measurement and matching grant, for one sealed operation,
restricted to value-free discovery in M12-B. HubSpot is a designated optional future connector. It is not a currently
supported or usable BusinessIQ connector. The file path serves every capability whatever the connector's state.**

### 1. Optional connector

An **optional connector** is a connector whose absence, disconnection, unavailability, refusal or failure:

- degrades **only** the one capability it serves (ADR-0004; `architecture.md` §16), with a named reason and the file
  alternative;
- never fails, blocks, delays or changes any workflow that does not request that capability;
- never changes a figure, finding, evidence set, synthesis result or verification outcome produced from files.

**Every BusinessIQ connector is optional.** No command, skill, engine module, test or default configuration may require
a connector to be registered, declared, connected, authorized or available. The uploaded Excel/CSV path remains fully
functional standalone (`CLAUDE.md` §2.8), and for accounting and spreadsheets it remains the only path (ADR-0004).

### 2. The five facts

A **planned** (or designated, future) connector is one that documentation names as intended. It is a documentation
status only: it is not a registry entry, not one of the five facts, and it establishes none of them. BusinessIQ's
runtime never sees it (§8, state 1).

| Fact | Definition | Decided by | Where it is held | How BusinessIQ learns it | Never implies |
|---|---|---|---|---|---|
| **Supported** | BusinessIQ has a registry declaration for the connector (ADR-0037 §B.2 layer A; §C.2 `configured`), admitted under OD-3's rule: at least one declared capability had a complete, approved chain when it was admitted | The owner, by a reviewed commit after the Connector Gate | The repository registry | Deterministic registry lookup by Python | Connected, authorized, available; that the capability requested now is verified, or that the admitted one is still current |
| **Verified capability** | For one declared `discovery` capability, an owner-approved Connector Gate record and the agent grant agree exactly with the declaration on every §B.2 binding | The owner, at the Connector Gate | The repository: registry, Gate record, agent grant | Deterministic binding checks and static tests (ADR-0037 §B.2, §D.4) | Connected, authorized, available; anything about the user's account |
| **Connected** | The user has completed the platform's authentication for **BusinessIQ's own declared server entry** | The user, through the platform | The platform. Never in BusinessIQ, never in the repository, never in `.businessiq/` | Only indirectly: a relayed outcome other than `connector_not_authorized` / `connector_unavailable`. Untrusted; can only reduce what is shown | Supported, verified, authorized, available |
| **Authorized** | Two things, never merged (ADR-0037 §B.3). **Vendor authorization:** the user's account may make this call. **BusinessIQ permission:** the §B.2 agreement for one sealed discovery operation | Vendor authorization: user and vendor. BusinessIQ permission: recomputed by Python per operation | Vendor authorization: the platform and vendor. BusinessIQ permission: nowhere — it is a condition, never an object | Vendor authorization: only its absence, as relayed `authorization_failure`. BusinessIQ permission: computed | Each other; available; evidence |
| **Available for use** | For **one** sealed operation: supported, verified, in-scope interaction class (`discovery` only in M12-B), and the relayed outcome `completed` with a reply that parses fail-closed | Python, over the static facts plus an untrusted relay that can only reduce | Nowhere. Recomputed per operation; never persisted, cached or carried to another operation or session | Per operation | Any later operation; evidence; authorization for anything else |

"Verified capability" is a **documentation and lifecycle term** for a Gate-measured tool binding. It verifies the
binding, never any output. It is **never** a field, key, flag or status value in a request, reply, catalogue, registry
or result. ADR-0037 §B.3 and §E.9 still refuse or drop a `verified`, `authorized`, `approved`, `granted`, `scope` or
`trust` key wherever it appears.

### 3. The non-implication invariant

```
SUPPORTED  ≠  CONNECTED  ≠  AUTHORIZED  ≠  VERIFIED CAPABILITY  ≠  AVAILABLE FOR USE
```

No fact substitutes for another, and no state transition may skip a distinction. There is exactly one dependency
between them, and it runs one way at admission time only: a connector is **admitted** as supported only on a verified
capability (OD-3). Support never implies that the capability requested now is verified or still current, and nothing
implies support. In particular:

| Situation | What it does **not** establish |
|---|---|
| Documentation names a connector as planned or designated | That it is supported, connected, verified, authorized or available. It does not exist for BusinessIQ's runtime |
| The user connected a HubSpot server — BusinessIQ's own, another plugin's or their own | That BusinessIQ supports it, that any capability is verified, or that anything is available. A server other than BusinessIQ's declared entry never counts as *connected* for BusinessIQ |
| BusinessIQ supports a connector | That any user has connected it, that the capability requested now is verified, or that the capability it was admitted on is still current (`stale_metadata`) |
| A capability is Gate-verified | That this user connected it or that this user's account authorizes the call. The Gate measures on a vendor sandbox with synthetic data (ADR-0037 §E.3), not on the user's account |
| The vendor accepted one call | That the next call is permitted, or that any other tool, object type or interaction is |
| One operation was available | That any other operation is. Nothing is carried forward |
| Any of the above | Evidence, a claim of any class, a synthesis input, or authorization for a `read`, `write` or `administrative` interaction |

### 4. The lifecycle — a closed conceptual state model

The states below are **lifecycle names for documentation and user messaging**. They add no runtime code, status,
enum, field or schema. At runtime BusinessIQ reports only ADR-0037's §H codes and result statuses; the table maps each
state onto them.

| # | Lifecycle state | Holds when | Decided by | Reported as (ADR-0037, unchanged) | Use |
|---|---|---|---|---|---|
| 1 | `not_supported` | No registry declaration for the requested capability placeholder. This includes every planned or designated connector | Python, from the registry | `connector_not_configured` | None. Named absence and the file alternative |
| 2 | `supported_not_verified` | Supported, but no complete, agreeing chain covers the **requested** scope. Under OD-3 this arises only when the scope lies outside the admitted capability, when bound metadata went stale after admission, or when a binding disagreement is detected (a defect, refused fail-closed) | Python and the static tests | `capability_unsupported`, `stale_metadata`, `binding_mismatch` | None. Nothing is dispatched, so the connection is never consulted. File alternative |
| 3 | `supported_not_connected` | States 1–2 do not hold, and the relayed outcome says the user has not authenticated BusinessIQ's declared entry | The platform, relayed; untrusted | `connector_not_authorized` | None. The user is told the connector is supported but not connected, that connecting is theirs to do through the platform, and the file alternative |
| 4 | `connector_unavailable` | States 1–2 do not hold, and the relayed outcome says the server or tool is not reachable in this session | The platform, relayed; untrusted | `connector_unavailable`, `timeout`, `tool_failure` | None. Named; no retry with changes; no substitute; file alternative |
| 5 | `connected_not_authorized` | States 1–2 do not hold, the user authenticated, and the vendor rejected authentication or refused the call for scope or permission | The vendor, relayed; untrusted | `authentication_failure`, `authorization_failure` | None. Named without message text; BusinessIQ never requests broader access; file alternative |
| 6 | `verified_capability_available` | States 1–2 do not hold, and for one sealed discovery operation the relayed outcome is `completed` and the reply parses fail-closed | Python, over the static chain plus the relay | Result status `complete`, `complete_with_limitations` or `partial` (ADR-0036 shape) | That one operation only: a value-free catalogue, labelled unverified, not evidence (ADR-0037 §C.5, §I) |
| 7 | `blocked` | A request for a record read, write or administrative interaction, **in any state including 6** | Python | `blocked_prerequisite` (record reads, M12-C) or refusal with no approval offered (write, administrative; ADR-0037 §G, §J-13) | None. File alternative |

The remaining eight §H codes are not lifecycle states. They are request- or operation-level outcomes, and each still
maps into the table:

- `request_invalid` refuses a malformed or forged request before evaluation, so no state is reached.
- `ambiguous_connector` asks the user to choose among registered connectors before evaluation continues.
- `malformed_response` and `operation_unknown` fail that one operation closed with no catalogue. It is not available,
  and it is not state 6.
- `metadata_conflict`, `external_content_unavailable`, `privacy_restricted` and `insufficient_data` qualify a state-6
  result.

Deliberately **not** states:

- **`connected_not_verified`** is a real situation — the user connected something while BusinessIQ has no verified
  capability — but BusinessIQ reports it as state 1 or 2. Because static checks run before any dispatch (§5), the
  connection is never observed or consulted, and it could not change the outcome. Making it a state would require
  BusinessIQ to learn about connections it has no use for.
- **`connection_available` / `connection_pending`** are not added. Whether the platform offers a connection, or has one
  in progress, is platform state that BusinessIQ cannot observe structurally without reading platform configuration
  (Option C, rejected). An in-progress connection is, to BusinessIQ, state 3.
- **`capability_unavailable`** (the brief's term) is ADR-0037's existing `capability_unsupported` (state 2). No new code
  is created.

**Naming note.** ADR-0037's code `connector_not_authorized` means "registered and reachable, but the user has not
authenticated it" — that is, *not connected* (state 3). Vendor refusal of a call is `authorization_failure` (state 5).
The codes are not renamed. This ADR fixes their meaning in the lifecycle so that neither is read as BusinessIQ
permission.

**Transition rules.**

1. Only a **reviewed commit after an approved Connector Gate** moves a connector out of state 1, and only when OD-3's
   admission rule is met. Only such a commit moves a capability out of state 2. Nothing at runtime does — no user
   input, configuration, Business Context field, model output, relay, connection, or documentation naming the connector
   as planned.
2. Only **the user, through the platform,** moves a connector out of state 3. BusinessIQ never does.
3. The state is **recomputed from scratch per operation**. Nothing — state, relay, connection observation, catalogue or
   permission — is persisted, cached or carried to another operation or session (ADR-0037 §B.2: valid use is "a
   condition recomputed per operation, never an object, flag or token").
4. Relayed information is untrusted and can move an evaluation **only toward a less capable state**. A relay can never
   move it toward state 6 on its own, and never out of state 1, 2 or 7.
5. State 7 is independent of every other state. A record read is `blocked` even when discovery is available.
6. A vendor-side change to any bound field returns the capability to state 2 (`stale_metadata`) until it is re-measured
   and re-approved (ADR-0037 §B.4).

### 5. Evaluation order

For each request, BusinessIQ evaluates in this order and stops at the first state that holds:

1. **Interaction class** — a record-read, write or administrative request is state 7, before anything else.
2. **Supported** — registry lookup (state 1).
3. **Verified capability** — static binding agreement (state 2).
4. **Only then**, a sealed discovery operation may be dispatched, and its relayed outcome decides state 3, 4, 5 or 6.

Static facts are decided by Python from the repository alone. Session facts are learned only by relay, only after
the static facts already permit the operation, and only to reduce it. **BusinessIQ never probes for a connection:** it
learns that a connector is not connected only from the outcome of an operation it was already permitted to dispatch.

### 6. The user-initiated connection boundary

**BusinessIQ defines** the lifecycle, the requirements on a connection and the security rules around it. **The platform
provides** the connection mechanism. These are fixed:

- **The connection is the user's act, through the platform.** The authority for vendor access is the user's consent,
  given to the vendor through the platform's authentication. It is never a BusinessIQ action.
- **BusinessIQ never starts it.** No BusinessIQ skill, command or agent calls, instructs or suggests calling a platform
  authentication tool (ADR-0037 §E.6). The connector agent's grant never includes one (ADR-0037 §D.3).
- **BusinessIQ never takes part in it.** BusinessIQ does not obtain, request, prompt for, accept, receive, read, store,
  log, cache, forward or transmit credentials, API keys, tokens, OAuth codes, authorization URLs or secrets. It never
  asks the user to paste any of them into BusinessIQ, a command argument, a file or Business Context.
- **BusinessIQ sends nothing to connect.** No Business Context, business data, research content or connector metadata
  is involved in, or sent for, authentication.
- **BusinessIQ does not observe it directly.** It does not read platform configuration, credential stores or session
  server lists to learn whether a connection exists (Option C, rejected). §5 is the only way it learns anything.
- **BusinessIQ never declares it.** No BusinessIQ component, and no model, may state that a connector *is* connected.
  The furthest BusinessIQ says is that a permitted operation completed, or that one failed with a named code.
- **What counts as connected.** Only the user's authentication of **BusinessIQ's own declared server entry** (ADR-0037
  §B.4). Connecting the same vendor through another plugin, or through a server the user added, does not count and does
  not make any BusinessIQ capability available.
- **A supported connection path must exist before a connector is offered as supported.** BusinessIQ describes that path
  only from what the Connector Gate observed on the installed platform version (§12). It never invents a screen, button,
  command, URL, OAuth endpoint or platform API. Where the platform's connection interface is outside BusinessIQ's
  control, the documentation says so.
- **Outside BusinessIQ's control.** What the platform shows for a declared but unauthenticated server, and whether a user
  can ask the assistant to start the platform's authentication outside any BusinessIQ workflow, are platform behaviour.
  BusinessIQ neither relies on nor instructs either. In every case the authority is the user's consent at the vendor,
  and the result still grants BusinessIQ nothing (§3).

**Disconnection and revocation** are equally the user's and the platform's. A disconnected or revoked connector
returns to state 3 or 5 at its next operation. Nothing BusinessIQ holds needs clearing, because it holds nothing.

### 7. HubSpot

**Status in one sentence.** HubSpot is a designated optional future connector for BusinessIQ (`~~crm`). It is **not** a
currently supported or usable BusinessIQ connector in this repository, because no BusinessIQ-owned, Connector-Gated,
value-free discovery capability has yet been approved. No HubSpot connector exists in BusinessIQ, and BusinessIQ has no
HubSpot connection path. The `marketing` plugin's HubSpot server does not qualify (§6; ADR-0037 §B.1 item 9).

**Designation.** If HubSpot is admitted under OD-3, then as a BusinessIQ connector it will be:

- **optional** — §1 applies in full; no core function requires it;
- **user-connected** — only through the platform, only to BusinessIQ's own declared entry (§6);
- **identity-bound** — to exactly the connector id, `.mcp.json` server key and transport identity, platform-derived
  namespace and fully qualified tool names that the registry declares and the Connector Gate measures (ADR-0037 §B.4);
- **Gate-bound** — no HubSpot capability is usable until its Connector Gate record is approved and the three layers
  agree (ADR-0037 §B.1–§B.2);
- **read-only in v1**, and in M12-B **value-free discovery only** — no record reads (M12-C, `BLOCKED`), no writes, no
  administrative actions (ADR-0037 §G);
- **not an authorization bypass** — a HubSpot connection authorizes nothing in BusinessIQ (§3);
- **not a reason to expose HubSpot MCP tools** — only the exact Gate-measured `discovery` tools may ever be granted, to
  the connector agent only. No other HubSpot tool, under any namespace, is granted, called or instructed by BusinessIQ.

**Current status — stated, not claimed:**

| Question | Answer at `09cb52b` |
|---|---|
| A currently supported BusinessIQ connector? | **No.** Planned and designated only |
| Registered in a BusinessIQ connector registry? | **No.** No registry exists (M12-B, not started) |
| Declared in BusinessIQ's `.mcp.json`? | **No.** `.mcp.json` declares only `biq-verifier` |
| Connector Gate measured or approved? | **No.** No Gate record exists |
| Any HubSpot tool name, argument shape or output shape known to the repository? | **No.** These are Gate measurements (ADR-0037 §E.3) |
| A value-free discovery capability demonstrated? | **No.** Not measured |
| Connected? | **Not known to BusinessIQ and not claimed.** A connection to another plugin's HubSpot server would not count (§6) |
| Usable by BusinessIQ? | **No** |
| Lifecycle state for `~~crm` today | **State 1** (`connector_not_configured`): no `~~crm` connector is registered |
| Endpoint | `https://mcp.hubspot.com/anthropic`, recorded as verified to exist on 2026-09-08 (ADR-0004). Must be re-verified and measured at the Gate (ADR-0037 §E.2) |

A future BusinessIQ HubSpot connector becomes *supported* in the §2 sense only after its BusinessIQ-owned declaration
exists and at least one value-free discovery capability has a complete, approved Connector-Gated chain (OD-3). If the
Gate finds none, HubSpot stays designated and in state 1.

### 8. User experience

The wording is an implementation item for M12-B (the registry's fixed absence text and file-fallback guidance, ADR-0037
§C.1–§C.2). The substance is normative. The HubSpot messages for states 2–7 apply only after HubSpot is admitted under
OD-3. Until then, only state 1 can occur:

| State | BusinessIQ says, in substance | Always also |
|---|---|---|
| 1 — before HubSpot is registered | No CRM connector is available in this version of BusinessIQ. Runtime text comes from the registry only, so an unregistered vendor is not named at runtime; `CONNECTORS.md` documents HubSpot's designation | The file-export alternative |
| 2 | HubSpot is an optional connector BusinessIQ supports, but the capability you asked for is not available in this version | The file-export alternative |
| 3 | HubSpot is an optional supported connector, but it is **not connected**. Connecting it is your choice and happens through your Claude platform's own connection mechanism for the HubSpot server BusinessIQ declares; BusinessIQ does not start the sign-in or handle any credential | The file-export alternative |
| 4 | HubSpot could not be reached in this session | The file-export alternative |
| 5 | HubSpot did not accept the request for this account. BusinessIQ does not request broader access | The file-export alternative |
| 6 | The value-free catalogue, with its fixed trust statement: connector-reported structure, relayed by a model, unverified; not evidence; authorizes nothing | — |
| 7 | Reading HubSpot records (or writing to HubSpot) is not available in BusinessIQ | The file-export alternative |

Messages must keep the states distinguishable. No message says or implies that a connector is connected, authorized,
verified or usable beyond what its state establishes. No message names a platform screen, button, command, URL or
endpoint unless a Connector Gate record observed it.

**File-export fallback.** In every state except 6, and alongside 6 for anything beyond discovery, BusinessIQ offers the
file path: export the CRM data to CSV or Excel and supply the file, and the same analysis runs through
`biq-data-ingestion` (M3 reading, M4 quality gate, the engines). The file path never waits for, depends on, or is
changed by a connector.

### 9. Privacy

The optional-connection model **does not weaken** the privacy boundary (ADR-0009; ADR-0037 §F). At every lifecycle state:

- no raw business record crosses the connector boundary in either direction;
- no Business Context is sent to connect, authenticate or discover;
- no research content, evidence or synthesis material is sent;
- no credential is handled by BusinessIQ (§6);
- no connector output, connector metadata, connection status or lifecycle state becomes evidence, a claim of any class
  or a synthesis input (ADR-0037 §C.6, §I);
- no connector metadata or connection status becomes authorization (ADR-0037 §B.1 items 11–14).

**M12-B specifically** permits value-free discovery only: no business record reads, no counts, no picklist or option
values, no record samples, no user or owner identities, no raw business values (ADR-0037 §C.6, §G).

**M12-C** — connected-system record reads — remains the future capability and remains **`BLOCKED`** on ADR-0037 §M
(P-1 to P-5) and its own accepted ADR. A user's connection does not unblock it, advance it, or count as any of P-1 to
P-5.

### 10. Security invariants

| # | Invariant | Held by |
|---|---|---|
| 1 | User connection is not BusinessIQ authorization | §2, §3; ADR-0037 §B.3 |
| 2 | Authentication does not bypass registry binding | §4 rule 1, §5; ADR-0037 §B.1 items 1–3 |
| 3 | Authentication does not bypass Connector Gate measurement | §4 rule 1, §5; ADR-0037 §B.1 items 6–7 |
| 4 | A model cannot initiate or manufacture authorization | §6; ADR-0037 §B.3, §E.6, §J-15 |
| 5 | A model cannot declare a connector connected | §2, §6 |
| 6 | A model cannot manufacture connector identity | ADR-0037 §B.4, §J-16 |
| 7 | A model cannot manufacture tool identity | ADR-0037 §B.4, §J-16 |
| 8 | A model cannot select arbitrary same-vendor servers | §6; ADR-0037 §B.1 item 9, §J-19 |
| 9 | BusinessIQ does not inspect platform configuration to discover connected servers | §4 (not-a-state notes), §6; ADR-0037 §B.1 item 10, §E.6 |
| 10 | BusinessIQ does not store vendor credentials or tokens | §6; `CLAUDE.md` §7; ADR-0037 §E.6 |
| 11 | Connector instructions remain untrusted | ADR-0037 §B, §E.11 (C-4 residual) |
| 12 | Connector output remains untrusted | ADR-0037 §B, §C.4 |
| 13 | No write or administrative connector capability is introduced | §7; ADR-0037 §G |
| 14 | No connection status becomes evidence | §9; ADR-0037 §I |
| 15 | No connection metadata enters synthesis as evidence | §9; ADR-0037 §I (`register_claims()` refusal) |
| 16 | A disconnected optional connector does not break core BusinessIQ | §1 |
| 17 | File-based ingestion remains a supported fallback | §1, §8; ADR-0004 |

Invariants 5, 16 and 17 are newly stated here. The rest restate ADR-0037 in lifecycle terms and change none of its rules.

### 11. Relationship to ADR-0037

- **ADR-0037 remains accepted and immutable.** Its text and status line are not edited.
- **This ADR does not weaken or replace ADR-0037.** It removes no rule, relaxes no binding, adds no interaction class,
  failure code, test category, field, state or authority.
- **It clarifies the lifecycle** around an optional connector, before and alongside the registry-bound capability model:
  what a connection is, who owns it, and what BusinessIQ says at each stage.
- **Exact connector, server and tool identity** (ADR-0037 §B.1, §B.4) remains mandatory.
- **Connector Gate requirements** (ADR-0037 §B.1 item 7, §B.2, §L item 1) remain mandatory.
- **M12-B remains value-free discovery only.**
- **M12-C remains `BLOCKED`.**
- **User authentication does not itself grant runtime capability.** It is one precondition, observed only by relay,
  never sufficient and never recorded.

- **OD-3 narrows ADR-0037 and weakens nothing.** ADR-0037 permits a registered connector with no complete discovery
  chain (§D.1), but does not require one. OD-3 forbids shipping such a connector. ADR-0037's `capability_unsupported`,
  `stale_metadata` and `binding_mismatch` remain in force for a scope no chain covers, for post-admission staleness and
  for defects. ADR-0037 §L item 1 still lets M12-B complete with the registry, resolution, named absence and binding
  checks, and with the agent deferred, when no connector is admitted.

**Conflict check.** Each §2–§10 statement and the OD-3 resolution were compared with ADR-0037 §A–§M and
*Consequences*. No conflict was found. Two points could read as tension and are resolved by ADR-0037's own text:

- *"HubSpot is supported"* would contradict ADR-0037 if read as a present fact, because *supported* means registered
  (§B.2 layer A) and nothing is registered. This ADR therefore states HubSpot as **designated**, in state 1 today (§7).
- *"The user must have a proper way to connect"* would contradict ADR-0037 §B.4 if it meant connecting any HubSpot
  server. It means connecting BusinessIQ's own declared entry, which does not exist until M12-B ships one through the
  Gate. Until then, no BusinessIQ HubSpot connection path exists, and the file path is the way (§7, §8).

### 12. Obligations on M12-B

These add to ADR-0037 §L only through its existing items and §J categories. No new test category and no new completion
item is created:

1. **Optional-connector tests** (§L item 4, §J-15/§J-16). Deterministic tests show that every lifecycle state maps to
   its §4 code, and that no state's user-facing text claims a connection, authorization or verification it does not
   establish. They also show that the file-based commands behave identically with a connector unregistered,
   registered and unverified, or relayed as not authorized or unavailable.
2. **No authentication instruction** (§J-16 source scan). No BusinessIQ markdown instructs, suggests or names a platform
   authentication tool. This already follows from ADR-0037 §E.6. M12-B asserts it by test.
3. **The connection path is documented from observation** (§L item 2, the integration page). The connector's
   integration page describes how the user connects BusinessIQ's declared entry only as recorded in the Connector Gate
   development record for the installed platform version. Anything the Gate did not observe is stated as
   outside BusinessIQ's knowledge.
4. **Optionality of a declared entry is observed at the Gate** (§L item 1). If a connector `.mcp.json` entry is
   proposed, the Gate record states what the platform exposes for it before the user authenticates, and confirms that a
   declared but unauthenticated or unreachable entry leaves the existing commands working.
5. **The admission rule is enforced statically** (§L item 4, §J-19). Every connector in the shipped registry has at
   least one declared capability whose complete chain agrees across registry, Connector Gate record, `.mcp.json` and
   grant. A registry or `.mcp.json` connector entry without one fails the suite.

## Owner decision — OD-3, resolved 2026-09-18

**Question.** When may a connector be registered, have its `.mcp.json` entry shipped, and be represented as supported?
ADR-0037 permits a registered connector with no complete discovery chain (§D.1). For an optional, user-connected
connector, that would offer a connection path — and ask the user to grant vendor access to BusinessIQ's server entry —
leading to no usable capability.

**Decision (the owner).** The proposed option (a) is adopted. Option (b) — registering and shipping a connector once
its server identity is Gate-measured, even with no usable capability — is rejected.

1. **Planned is not supported.** A connector may be described in documentation as planned, designated or future
   without being a currently supported connector.
2. **Admission rule.** A connector **must not** be represented as a currently supported or usable connector in the
   shipped BusinessIQ connector registry — and its `.mcp.json` entry is not shipped — unless at least one declared
   capability within its declared v1 capability scope has a complete, approved, BusinessIQ-owned Connector-Gated chain.
3. **What does not make a connector supported.** None of these:
   - being named in documentation;
   - being designated as a future connector;
   - a vendor providing an MCP endpoint;
   - another Claude plugin exposing a vendor server;
   - the user being able to authenticate to some vendor server;
   - a same-vendor connector existing elsewhere.

   Another plugin's server, tool or namespace can never satisfy BusinessIQ's connector declaration (ADR-0037 §B.1 item
   9, §B.4).
4. **The admission capability for M12-B is value-free discovery.** The chain requires every one of:
   - a BusinessIQ-declared server identity;
   - the exact server and transport identity;
   - the exact platform-derived namespace;
   - the exact fully qualified tool identity;
   - a Connector Gate measurement;
   - an approved value-free output proof on synthetic data;
   - a matching agent grant;
   - a matching sealed-operation binding.

   These are ADR-0037 §B.1 items 5–8, §B.2 and §G, unchanged.
5. **Scope of the rule.** This is an admission rule for a connector's declared v1 supported capability scope. It does
   **not** require that every future connector permanently expose discovery. A future ADR that approves another
   interaction class would define admission against that capability's own approved chain.
6. **M12-C is not unblocked.** Admitting a connector under this rule does not authorize connected-system record
   reads. M12-C stays `BLOCKED` on ADR-0037 §M (P-1 to P-5) and needs its own accepted ADR.
7. **Unchanged.** Optionality (§1): absence, disconnection, authorization failure, unavailability or refusal affects
   only that connector's capability and never breaks file-based BusinessIQ. The user boundary (§6): the user
   initiates authentication through the platform, and BusinessIQ never receives, stores, logs or transmits credentials,
   tokens, API keys or OAuth codes. The Connector Gate: connection or authentication never substitutes for capability
   verification or Gate approval.

**Consequence for HubSpot.** HubSpot stays a designated optional future connector, in state 1. It is not a supported
connector in the shipped registry and is not usable. The `marketing` plugin's HubSpot server does not qualify. A future
BusinessIQ HubSpot connector becomes supported only after its BusinessIQ-owned declaration and a complete, approved
Connector-Gated discovery chain exist. If the Gate confirms the owner's report that no qualifying discovery capability
is exposed, HubSpot remains designated and unregistered at the end of M12-B. M12-B still completes under ADR-0037 §L
item 1 and §D.1.

## Reason

The owner's requirement and ADR-0037 agree on substance: HubSpot is optional, the user connects it, and a connection
never widens what BusinessIQ may do. What was missing was vocabulary. Without the five facts as separate definitions, a
message, a document or a future implementation can quietly let "connected" stand for "usable", the failure ADR-0037's
chain exists to prevent. Option D names each fact, gives each a single owner, and maps the lifecycle onto codes that
already exist. It also answers the architectural question honestly: BusinessIQ can require a proper connection path
without inventing the platform's interface, because it can require that the path be the platform's and be described
only from observation. It rejects every option that would require BusinessIQ to hold a secret, read platform
configuration, or treat a server it did not declare as its own.

## Consequences

**Positive.**
- Optionality is a stated, testable invariant: no connector state can break file-based BusinessIQ.
- "Supported", "connected", "authorized", "verified" and "available" have one definition each, and no two are
  interchangeable in code, documentation or messages.
- The user gets distinct, accurate messages for "not supported", "not verified", "not connected", "unreachable" and
  "refused", each with the file alternative.
- No new runtime state, code, field or authority is introduced. The lifecycle is carried entirely by ADR-0037's
  vocabulary.
- The connection mechanism is left to the platform, with no invented interface.
- Under OD-3, "supported" always means that something works. No user is asked to grant vendor access to a BusinessIQ
  server entry that leads to no usable capability.

**Negative.**
- Until a BusinessIQ HubSpot connector is admitted under OD-3, **there is no BusinessIQ HubSpot connection path**. A
  user who has connected HubSpot through another plugin gains nothing in BusinessIQ, which may surprise them. This
  extends ADR-0037's stated negative.
- If the Gate finds no value-free discovery tool, then under OD-3 HubSpot stays unregistered, and "optional HubSpot
  connector" remains a designation, not a working feature, in v1.
- BusinessIQ cannot tell a user *whether* they are connected, only whether a permitted operation succeeded. This is
  deliberate (§5) but less convenient.
- Platform behaviour for a declared but unauthenticated server — including authentication tools the platform may expose
  in the session — is outside BusinessIQ's control. BusinessIQ's control over the main thread there is advisory, as
  ADR-0037 accepted.

**Follow-up required.**
1. Owner acceptance of this ADR, with OD-3 resolved — done, 2026-09-18.
2. M12-B, as its own implementation task, applies §12 and OD-3 alongside ADR-0037 §L.
3. M12-C stays `BLOCKED`. Nothing here schedules it.

## Revisit when

- The platform documents a verified, secret-free way for a plugin to learn whether one of its own declared servers is
  authenticated without reading configuration. §5 might then observe connection before dispatch.
- The platform offers a verified per-plugin opt-in for declaring a server, which would change what §12 item 4 must
  observe.
- The Connector Gate result for HubSpot is recorded, which decides whether HubSpot is admitted under OD-3.
- An ADR proposes a supported interaction class other than `discovery`. OD-3's admission capability would then need
  restating for it.
- M12-C's ADR is proposed. Record reads would need their own connection and consent analysis.
