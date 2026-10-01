# ADR-0037 — The M12 connector layer contract: a registry-bound, read-only connector catalogue, discovery separated from data, and connected-system reads blocked until no model context holds a value

**Date:** 2026-09-17
**Status:** Accepted — 2026-09-17, by the project owner, with OD-1 and OD-2. Acceptance approves the contract only: nothing in
it is implemented, and it authorizes no connector, Connector Gate result or runtime use (M12-B implementation and the
Connector Gate are still required; M12-C remains `BLOCKED`).
**Deciders:** Project owner (M12 architecture and contract-definition brief; OD-1 and OD-2; acceptance), recorded in the M12-A review and remediation (decision only)
**Supersedes, in part:** [ADR-0004](ADR-0004-capability-based-connector-abstraction.md) — only the two clauses listed in
*Relationship to ADR-0004*. Every other ADR-0004 decision stands. ADR-0004's text, including its status line, is not
edited; the relationship is recorded in the decisions index, as for ADR-0006 and ADR-0022.
**Relates to:** ADR-0001 (verified platform facts only), ADR-0002 (figures from code), ADR-0005 (class 2), ADR-0006 and
ADR-0036 (the reserved `biq-data-profiler` agent), ADR-0009 (disclosure), ADR-0010 (approval), ADR-0011 (Business
Context), ADR-0012 (placement; the broker merged into ingestion), ADR-0014 (the tool grant is the boundary), ADR-0015
(model-mediated dispatch), ADR-0017 (operation-bound records; no model authorship of source data), ADR-0018 (a registry,
never a heuristic), ADR-0022/0023 (synthesis provenance), ADR-0034/0035 (verification; sealed requests; digests not
values).

## Context

### What the repository already says M12 is

Verified by reading the repository at `ad6588c`:

| Source | Statement |
|---|---|
| `project_plan.md` M12 | "Connector resolution inside `biq-data-ingestion`; `CONNECTORS.md` capability map; `.mcp.json` verified endpoints only (`BLOCKED` — Connector gate …); connector-absent degradation tests via `evals/mocks/`; write-attempt approval-gate tests." Depends on M3 |
| `architecture.md` §4 | `biq-data-ingestion`: "Resolve the source (file **or** connector capability), read it via the tiered reader …" `biq-connector-broker` merged into it (ADR-0012) |
| `architecture.md` §10, ADR-0036 §1 | `biq-data-profiler` is deferred and reserved for "model-mediated exploration of a source only reachable through model tools and too large for the main context — connector catalogues"; grant "data access through a declared structural grant, **no web**, no shell or raw-row read" |
| `architecture.md` §11, ADR-0004 | Skills address capabilities (`~~crm`, `~~accounting`, `~~commerce`, `~~warehouse`, `~~spreadsheet`, `~~chat`), never products. "Source resolution … discovers live servers, maps capability to tools, enforces read-only, and degrades by returning a named absence plus the file fallback." Only verified endpoints ship; adding one is the Connector gate |
| `CONNECTORS.md` | HubSpot (`~~crm`) and Slack (`~~chat`, write-capable) endpoints verified to exist on 2026-09-08; accounting, spreadsheet, commerce and warehouse have no verified server. Reads "called freely within a workflow"; writes explicitly approved; "BusinessIQ is a read-only product in v1" |
| `architecture.md` §16 | "MCP unavailable — Name the connector, what could not be retrieved, offer the file path" |
| `reference/evidence-ledger.md`, `evidence.py` | Class 2 "Connected-system data — pulled from an MCP-connected system; system name, pull timestamp". `CONNECTED_DATA = 2` exists; nothing produces it |
| `research/contract.py` `Destination` | "An MCP-connected source is Milestone 12 and would need its own entry plus its own review" |
| ADR-0014 *Revisit* | "an MCP server that fetches external content (M12) … whatever performs the retrieval must not also be able to read business data" |
| ADR-0035 *Revisit* | "Connector sources (M12) need recomputation without a local file to hash" |
| `project_plan.md` *Deferred* | "Write-back to business systems — out of scope for v1 (read-only product)" |

No module, schema, skill section, agent, test or `.mcp.json` entry for connectors exists. `.mcp.json` holds only
`biq-verifier`, and three tests pin that (`test_m11_verification_server`, `test_m11_data_profiler`,
`test_research_scout_boundary` for the agent set).

### What later decisions established, which the M12 text predates

The M12 lines above were written at Revision 2 (2026-09-08). Since then the repository has measured or decided:

1. **Python can neither see nor call an MCP tool.** Tools are called by the model (ADR-0015). The only MCP tool
   BusinessIQ has shipped is one whose server it wrote (ADR-0035).
2. **The tool grant is the boundary, and it is a list of exact tool names** (ADR-0014, ADR-0035 §9, measured in M11:
   an agent whose `tools` names one MCP tool executes only that tool and has no `ToolSearch`). A grant cannot name
   "whatever server is connected". The only tool-name form the repository has measured is that of its own stdio
   server: `mcp__plugin_businessiq_biq-verifier__recompute`.
3. **No model authors source data.** A reply is ingested verbatim and never transcribed or repaired, because
   authorship decides provenance (ADR-0017, M9-C.8).
4. **No raw value enters a model context** on the paths BusinessIQ controls: the engine emits aggregates (§17), the
   profile emits no cell value (ADR-0036 §6), verification relays digests, never values (ADR-0035 §10).
5. **Figures come from code** (ADR-0002).
6. **BusinessIQ never reads, stores or transmits a secret** (`CLAUDE.md` §7).

Two observations from this session are also relevant, and are recorded as observations, not measurements of a
BusinessIQ component:

- The session's tool list contains `mcp__plugin_marketing_hubspot__authenticate`: a HubSpot server already
  reachable under **another plugin's** namespace. Under ADR-0004's wording it would "answer `~~crm`".
- The session's system context contains a section of "MCP Server Instructions" supplied by connected servers. Text
  authored by an external server is therefore placed by the platform into the main context before any BusinessIQ
  component runs.

### The contradictions this review found

**C-1 — Runtime discovery of "whatever server is connected" cannot be made structural or secret-free.**
`architecture.md` §11, ADR-0004 and `CONNECTORS.md` describe resolution to any connected server of a capability. But:

1. Python cannot observe the session's servers except by reading platform configuration files, which can hold server
   headers and tokens (`CLAUDE.md` §7 forbids reading them).
2. The model can observe them, but a model's report that a server exists is model-controlled.
3. A grant must name exact tool names. A server in an unknown namespace — such as the one observed above, or a
   look-alike a user installed — can be neither granted safely nor told apart from a substitute.

**Resolution (OD-2, accepted):** exact registry-bound identity, formalised as the trust chain in §B.1–§B.3, superseding
the two ADR-0004 clauses listed in *Relationship to ADR-0004*.

**C-2 — Connector record reads, as written, would put raw values in a model context and let a model author data.**
`architecture.md` §4 has ingestion "read" a connector capability, and §11 has read tools "called freely". A
third-party MCP read tool is called by a model and its result lands in that model's context (1). Whatever then reaches
Python is either model-transcribed, contradicting (3), or read by Python from a file the model wrote, which needs a
write tool and is still model-authored. The records would sit in a context that holds other tools, contradicting (4)
and the reserved grant's "no raw-row read" (ADR-0036 §1); figures computed from model-relayed values contradict (5).

**Resolution:** separate *discovery* (structural catalogue metadata, value-free by measured tool classification) from
*data* (record values). M12-B builds discovery only. Connected-system record reads are M12-C, recorded `BLOCKED` (OD-1)
until §M's prerequisites are satisfied and M12-C's own ADR is accepted. Nothing downgrades to a model relay in the
meantime.

**C-3 — "Write-attempt approval-gate tests" (plan) versus "read-only product in v1" (plan *Deferred*, `CONNECTORS.md`).**
Not a contradiction of decisions: ADR-0010 grades a system write as explicit-approval **if** one exists, and v1 builds
none. Clarified, not amended: M12 has no write or administrative path at all, so the M12 tests are write-attempt
**refusal** tests. Offering an approval for a capability that does not exist would itself mislead.

**C-4 — Server-supplied instructions reach the main context outside any BusinessIQ control.**
`architecture.md` §12 ("external content is data, not instruction") is enforced structurally for retrieved pages and
connector replies, but a connected server's instructions are placed by the platform. Not resolvable by BusinessIQ.
Recorded as a residual risk with a Connector-gate control (§E.11), not an amendment.

## Problem

Define M12 precisely enough to implement: what the connector layer is and is not; its trust model; the canonical
connector metadata and the class of every field; whether an agent and MCP are required and with exactly what grant;
the privacy, read/write and provenance boundaries; deterministic failure states; security tests; human control; and
an objective completion gate — without weakening M3, M9, M9-A, M10, M11 or the approval and secret policies, and
without inventing platform facts that have not been measured.

## Options considered

### Option A — Build M12 as written: dynamic resolution, and the main thread calls connector read tools

**Rejected.** C-1 and C-2 in full: raw CRM records (customer names, emails — Tier 3 material) in the main context that
also dispatches research and holds web tools; data model-authored; no bindable grant; a look-alike server
indistinguishable from the real one.

### Option B — A subagent granted the connector's read tools returns records as text for Python to ingest

**Rejected.** Isolation from the main thread improves, but the values are still in a model context, the agent
transcribes them (ADR-0017), and the grant contradicts "no raw-row read" (ADR-0036 §1). Class-2 figures would be
model-authored.

### Option C — A BusinessIQ-owned local MCP proxy that calls the vendor API itself and returns digests

Structurally like the verifier. **Rejected.** The proxy would have to hold the vendor OAuth token or API key, which
`CLAUDE.md` §7 forbids ("never stores, reads, logs or transmits a secret"), and would make the engine's process a
network client (`CLAUDE.md` §4).

### Option D — Defer M12 entirely

**Rejected as the decision.** The named absence, the capability map, and the value-free catalogue that ADR-0036
reserved an agent for can all be built safely now, and graceful degradation is a standing requirement (`CLAUDE.md`
§2.8).

### Option E — Registry-bound resolution; value-free discovery through the reserved agent; data reads blocked on measured prerequisites

**Chosen.**

## Decision

**M12 is a read-only connector layer. M12-B is buildable: a deterministic, immutable connector registry; capability
resolution with named absence; and a value-free connector catalogue explored through the reserved `biq-data-profiler`
agent. Only a tool that is registered, measured through the Connector Gate and granted — all three agreeing exactly on
identity and capability — may be used, and only for value-free discovery. Its reply is parsed fail-closed by Python.
M12-C, connected-system record reads, is a separate capability recorded `BLOCKED` until prerequisites P-1 to P-5 are
satisfied and its own ADR is accepted. It never follows automatically from M12-B. Connector metadata, availability and
catalogue entries are never evidence and never authorization. No write or administrative connector interaction exists
in M12. BusinessIQ holds no credential and adds no MCP server of its own.**

| Part | Scope | Status under this contract |
|---|---|---|
| **M12-A** | This contract | Accepted 2026-09-17 (with OD-1 and OD-2) |
| **M12-B** | Registry, capability resolution, named absence and file fallback, the value-free catalogue, the agent (only if §D.1's build rule is met), documentation, tests | `PLANNED`; any `.mcp.json` entry passes the Connector Gate first |
| **M12-C** | Connected-system record reads producing class-2 datasets | **`BLOCKED`** on §M (P-1 to P-5) **and** a separate accepted ADR |

#### The M12-B / M12-C boundary — normative

| | M12-B | M12-C |
|---|---|---|
| What it does | Catalogue / discovery **only** | Actual connected-system **record reads** |
| Data | Value-free, structural metadata only | Business record values |
| Tools | Only tools measured as `discovery` (§G) | `read` tools — **none grantable** under this contract |
| Record reads | **None** | Its entire purpose |
| Evidence | **None**; never a claim of any class | Class 2 only on the conditions §I sets as a minimum |
| Synthesis input | **None**; refused at re-entry | Only through the Data Layer and engines, on those conditions |
| Data Layer | Not involved: no rows exist | **Required**: M3 reading, sensitivity classes, M4 quality gate, engines |
| Approval | This ADR | **Its own ADR**, after P-1 to P-5 are measured and recorded |
| Security evidence | §J and the §L gate | **Separate** security evidence and tests, defined by its own ADR |
| Status | `PLANNED` | **`BLOCKED`** |

**No part of M12-C is in the M12-B completion gate, and completing M12-B is not evidence for, approval of, or progress
toward M12-C.** Every statement this contract makes about M12-C (§F, §I, §K, §M) is a **minimum constraint** that its
future ADR must meet. None is an approval, a design, or a promise that M12-C will be built.

### A. Purpose

**A.1 Exact capability (M12-B).** For each capability placeholder, BusinessIQ states deterministically whether a
connector is registered, and names the absence and the file-export alternative when not. For a connector whose trust
chain (§B.1) is complete and which the user has authenticated, it produces a bounded, value-free catalogue of what the
connected system structurally holds: object types, their properties, property data types, required flags, and
relationships between object types.

**A.2 User value.** "Which of my business systems can BusinessIQ use here, and what do they hold?" is answered without
putting business records in a model context. "Why can't BusinessIQ read my accounting system?" is answered with a
named absence and the exact file path that works instead, which remains the load-bearing path for accounting and
spreadsheets (ADR-0004, unchanged).

**A.3 Non-goals.** No record reads (M12-C). No write, create, update, delete, send, post, subscribe, share, export or
administrative connector interaction. No authentication initiated by BusinessIQ. No credential storage, reading,
logging or transmission. No BusinessIQ-owned MCP server, proxy or HTTP client. No adoption of any server or tool
outside the registry. No record values, samples, option values, counts or user identities in any catalogue. No KPI,
analysis, ranking, score, recommendation or evidence from a catalogue. No `~~chat` connector (write-capable
communication), and no connector that retrieves public web content (a retrieval path under ADR-0014; research stays
M9's). No change to the scout, the disclosure gate, synthesis, verification or the local-file profile. No new command
and no new skill: the skill count stays 20 and `biq-data-ingestion` is the entry point (§4, ADR-0036).

### B. Trust model

| Component | Trust | Controls |
|---|---|---|
| Deterministic Python (`lib/python/biq/`) | **Trusted for authority**: registry, classification lookup, binding checks, resolution, argument validation, sealing, parsing, failure mapping, re-entry refusal | No network, no MCP client, no secret read, no read of platform or user configuration |
| Connector registry (repository) | **Authoritative declaration**, changed only by a reviewed commit after the Connector Gate | Immutable at runtime; no configuration, Business Context, argument or model path widens it |
| `.mcp.json` (repository) | Authoritative **server identity declaration** only (`type`, `url` or `command`/`args`); no `headers`, token or environment secret | Connector Gate |
| Connector Gate record | Authoritative **measurement** of what one declared server and tool demonstrably provide, approved by the owner | Dated development record; re-measured on any change of a bound field |
| Platform (Claude Code) | Trusted to enforce agent tool grants **only as measured**, to run OAuth, and to hold tokens | Measured, never assumed (ADR-0001) |
| Main-thread model | **Untrusted for authority.** Sequences, presents, asks. Holds business-derived aggregates and web dispatch capability | Must never call a connector tool or look for connectors; advisory, with a sequencing test (as ADR-0035 accepts for `recompute`) |
| `biq-data-profiler` agent model | **Untrusted.** Calls granted discovery tools and relays catalogue records | Grant; sealed brief; fail-closed parser |
| Third-party MCP server (vendor) | **External system of record.** Its outputs are confidential to the user **and** untrusted as instruction; its tool descriptions and server instructions are external content | Connector Gate; grant; allowlist parser |
| Connected system's stored content (labels, notes, descriptions) | Authored by arbitrary people inside or outside the business — **untrusted content** | Data, never instruction |
| User | Authority for business decisions, connector choice among registered connectors, authentication, approvals | ADR-0010 |

**Model boundary:** no model decides a registry entry, a tool classification, a binding, a resolution status, an
authorization, a connector identity, an evidence class or a failure mapping. **User boundary:** only the user
authenticates a connector (through the platform), chooses among registered connectors for one capability, and
approves consequential actions under ADR-0010. No user, configuration or model input can add a connector, a server, a
tool, a capability or an interaction class at runtime.

**Two axes, never merged.** Connector output is **internal and confidential** on the privacy axis and **untrusted** on
the instruction axis. It never becomes public (Tier 0) because it arrived from outside the engine, and it never
becomes trusted because it is the user's.

#### B.1 The M12-B trust chain — normative

Terms. A **capability placeholder** is ADR-0004's `~~crm`, `~~accounting` and so on. A **declared capability** is one
registry declaration binding **one** tool of **one** registered connector to **one** interaction class (§G). All
comparisons below are **exact**: byte equality of identifiers. There is no prefix, pattern, wildcard, alias,
case-folding, display-name or "same vendor" matching anywhere in the chain.

1. **BusinessIQ maintains a fixed connector registry** in the repository. It is immutable at runtime.
2. **The registry contains only explicitly registered connector identities.** A `connector_id` not present in it does
   not exist for BusinessIQ.
3. **Each registered connector explicitly declares its capability placeholder and its declared capabilities.** Nothing
   is inferred from a vendor, a server name, a tool description or a catalogue.
4. **Only a declared capability whose interaction class is `discovery` can be considered for M12-B.** `read`, `write`
   and `administrative` declarations are never usable under this contract.
5. **A discovery capability names the exact MCP server identity and the exact tool identity** (§B.4).
6. **The tool is unusable until it has been measured and verified through the Connector Gate** and the owner has
   approved that record.
7. **The Connector Gate record binds, for that one declared capability:**
   - connector identity;
   - server identity and the tool namespace the platform derives for it;
   - the exact fully qualified tool name;
   - tool classification, with the reasons;
   - argument shape;
   - output shape;
   - the server's instructions, verbatim;
   - the **value-free discovery property**, demonstrated by measurement on synthetic data (§G).
8. **The agent may use only the exact tool or tools whose grant matches both the registry and the Connector Gate
   record.** Nothing else is granted, and a tool absent from either is never granted.
9. **Substitution is refused.** A same-vendor server under a different namespace, a different server identity, or an
   unregistered tool **must not** be substituted for a registered one, even when it offers the same tools, the same
   vendor name or the same catalogue.
10. **A model never discovers MCP servers and promotes them into BusinessIQ connectors.** No BusinessIQ skill, command
    or agent enumerates the session's servers or tools to find connectors. No code path accepts a model-reported
    server, tool or connector as a registry candidate. The registry changes only by a reviewed commit after the
    Connector Gate.
11. **Connector availability never implies authorization.** A reachable server, a listed tool, a successful call and a
    `completed` relay each authorize nothing.
12. **Authorization is never inferred from catalogue metadata.** No entry, label, object type, property or relationship
    grants, extends or evidences any permission.
13. **A connector response is never evidence** merely because it came through a registered, gated and granted
    connector. Passing the chain proves where a response came from, never that it is true or admissible (§I).
14. **Registry metadata is never an authorization token.** No registry entry, Gate record reference, resolution
    status, brief, reply or catalogue is presented, accepted, serialised, cached or persisted as proof of permission.

**If any link is missing or any binding differs, use is refused.** The refusal is fail-closed, whole and silent of
values (`binding_mismatch` or `request_invalid`, §H). Nothing is retried with changes, degraded to a partial grant, or
repaired to make the layers agree.

#### B.2 Declaration, measurement and runtime grant

Three layers, each necessary and none sufficient:

| Layer | What it is | Where it lives | What it establishes | What it does **not** establish |
|---|---|---|---|---|
| **A. Registry declaration** | What BusinessIQ expects and supports | The repository registry, plus BusinessIQ's own `.mcp.json` server identity | That BusinessIQ intends to support this connector, server, tool and interaction class | That the tool exists, behaves as declared, is value-free, or may be called |
| **B. Connector Gate measurement** | What the actual configured server and tool demonstrably provide | A dated development record, approved by the owner, holding every §B.1 item 7 binding in a form the static tests compare exactly (the form is an implementation contract item) | That on a stated date and platform version, this exact server and tool behaved as recorded | That BusinessIQ supports it, or that the agent may call it |
| **C. Runtime grant** | What the agent can actually call | The `tools` field of `agents/biq-data-profiler.md`, and per operation the sealed brief naming one tool | What the platform will let the agent execute, as measured | That the tool is registered, measured, discovery-class or value-free |

**Normative rules:**

- **Registry declaration alone does not authorize runtime use.** An unmeasured declaration is never granted.
- **A measured capability alone does not authorize runtime use** if it is not registered. A Gate record for an
  unregistered tool is never granted.
- **A grant alone authorizes nothing**; a grant naming a tool outside A or B is a defect, and the build is refused.
- **Runtime use is valid only for one sealed operation, and only when every binding agrees exactly across A, B and C:**
  - connector identity;
  - capability placeholder;
  - server identity and namespace;
  - exact tool name;
  - interaction class `discovery`;
  - argument shape;
  - output shape.
- **If any binding differs, runtime use is refused.** Refusal applies at every point that can check it:
  - the static test suite (a mismatching build is not shippable);
  - the engine when sealing a brief, reading only BusinessIQ's own repository files, never platform or user
    configuration;
  - the engine when parsing a reply;
  - the platform's grant enforcement, as measured.

This is **not a new authorization system.** It reuses the existing structures: the grant-is-the-boundary rule
(ADR-0014, ADR-0035), the sealed, consumed-once request (ADR-0035), the fail-closed operation-bound reply (ADR-0017),
and the reviewed-registry-over-heuristic rule (ADR-0018). "Valid runtime use" is a condition recomputed per operation,
never an object, flag or token.

#### B.3 What authorization is, and is not

- **Vendor authorization** — whether the user's account may read the system — belongs to the user and the vendor. It
  is held by the platform's OAuth and is never represented, stored, inferred, asserted or requested by BusinessIQ. A
  relayed `connector_not_authorized` or `authorization_failure` reports its absence and grants nothing.
- **BusinessIQ permission** is only the §B.2 agreement for one sealed operation, restricted to discovery.
- **Connector Gate approval is not runtime authorization**, and it never authorizes a `read`, `write` or
  `administrative` interaction.
- **No request, reply, catalogue or registry field can express authorization.** An `authorized`, `approved`, `granted`,
  `scope`, `trust` or `verified` key is refused in a request and dropped and noted in a reply (§E.9, §J).

#### B.4 Identity bindings

- **Registry identity.** `connector_id` is an exact string in the registry. Exactly one capability placeholder from the
  closed ADR-0004 vocabulary is declared per connector. A request naming an absent id, a near-miss id, or an id with
  another capability is refused.
- **Server identity.** The exact `.mcp.json` server key BusinessIQ ships, together with its declared transport identity
  (`type` with `url`, or `command` with `args`), must be byte-identical in the registry declaration, in `.mcp.json` and
  in the Connector Gate record. The tool namespace the platform derives for that server entry is **measured at the
  Gate, never constructed from a pattern**. The repository's only measured form is its own stdio server's. A server of
  the same vendor declared by another plugin, by the user, or under any other key, URL or command is a different
  identity and never qualifies.
- **Tool identity.** The exact fully qualified tool name, as the platform exposed it for that server entry at the
  Gate, must be byte-identical in the registry declaration, the Gate record, the agent grant, the sealed brief and the
  reply echo. A tool name is meaningful only under its registered server identity.
- **Change.** Any change to a bound field — server identity, namespace, tool name, classification, argument shape,
  output shape, server instructions or the value-free property — makes the capability unusable until a new Connector
  Gate record is approved and the three layers agree again. A relayed `stale_metadata` has the same effect.

### C. Connector catalogue model

Field names in this section are **implementation contract items**. The required content, classification and
prohibitions are normative.

#### C.1 Registry declaration — one per supported connector, repository-held

| Content | Meaning | Classification |
|---|---|---|
| Connector identity | Stable, exact id | authoritative configuration |
| Capability placeholder | Exactly one from the closed ADR-0004 vocabulary | capability metadata (authoritative) |
| Display name | Vendor product name, for named absence | authoritative configuration |
| Server identity | The exact `.mcp.json` key and transport identity BusinessIQ declares (§B.4) | authoritative configuration |
| Endpoint verification | Reference to the Connector Gate development record | authoritative configuration |
| Declared capabilities | Per tool: exact fully qualified name **as measured**, interaction class (§G), closed argument shape, closed output-field allowlist, Gate record reference | capability metadata (authoritative); the argument shape is also authorization metadata (policy) |
| Permitted interactions | In M12-B: exactly `discovery`. `read` can be added only by M12-C's own ADR | authorization metadata (policy) |
| File-fallback guidance | The file-export alternative named in absences | authoritative configuration |

The declaration contains no enabled flag, authorization, scope, token, header, priority or trust. Vendor authorization
is §B.3's; BusinessIQ's permission is §B.2's.

#### C.2 Capability resolution — per request, deterministic, local

| Content | Meaning | Classification |
|---|---|---|
| Requested capability placeholder | Closed vocabulary | user-provided configuration (validated) |
| Resolution status | `not_configured` \| `configured` \| `ambiguous` | capability metadata, derived from the registry **only** |
| Connectors | Registry ids in registry order | capability metadata |
| Absence | Fixed named-absence text and file-fallback guidance when `not_configured` | authoritative configuration |

`configured` means *registered and declared*. It asserts nothing about measurement, grant, reachability,
authentication or authorization.

#### C.3 Session observation — per operation

| Content | Meaning | Classification |
|---|---|---|
| Observed outcome | `completed` or a failure code of §H | **availability metadata — model-relayed, untrusted.** Can only reduce what is shown, never grant anything |
| Connector choice | Which registered connector the user chose when `ambiguous` | user-provided configuration (per request, not persisted) |
| Scope | Object-type ids requested, from the declaration's closed list | user-provided configuration (validated) |

#### C.4 Catalogue entry — per record in a reply

| Content | Meaning | Classification |
|---|---|---|
| Entry kind | `object` \| `property` \| `relationship` | external/untrusted content (shape-validated) |
| Object, property and related-object identifiers | As the system reports them; pattern- and length-validated | external/untrusted content; internal-confidential |
| Label | The system's display label, length-bounded, control characters removed | external/untrusted content; internal-confidential; local presentation only |
| Data type | Mapped by Python to a closed vocabulary; unknown → `unknown` | external/untrusted content (normalised) |
| Required flag | As reported | external/untrusted content |
| Basis | `relayed` (model-transcribed from a discovery tool) | authoritative (set by Python, never by the reply) |

#### C.5 Catalogue result — built only by the engine

The result carries: connector identity, capability placeholder, status and reason code, entries, conflicts,
limitations, notes of dropped keys (names only, never values), and fixed trust and use statements. Its identity is
content-addressed over the connector identity, the capability placeholder, the scope and the normalised entries, and
**excludes** the operation and any time. The fixed statements say: *connector-reported structure, relayed by a model,
unverified; not evidence; authorizes nothing.* The closed schema is an implementation contract item.

#### C.6 In no field, anywhere

| Class | Examples |
|---|---|
| **evidence** | No declaration, Gate record, resolution, observation or catalogue field is evidence of any class |
| **authorization** | No field is, contains, or can be presented as permission (§B.3) |
| **analysis** | No mapping of properties to business roles, no applicability verdict, no score or rank |
| **prohibited** | Record values; sample values; picklist or enumerated option values; record, row or object counts; owner, user or team identities; emails; tokens, keys, authorization headers, OAuth URLs or codes; vendor error message text; `source_tier`, `trust`, `verified`, `authorized`, `approved`, `granted`, `scope` (as authority), `confidence`, `priority`, `score`, `rank`, `recommendation` |

**Connector metadata never becomes evidence by existing.** It is diagnostic metadata about a system, like a profile
(ADR-0036 §11), and is refused at synthesis re-entry (§I).

### D. Agent boundary

#### D.1 The reserved agent, and its two distinct responsibilities

**The M12 agent is `biq-data-profiler`, the name ADR-0006 allocated and ADR-0036 reserved. No second profiling,
connector or catalogue agent is created; topology stays at three agents.**

The name covers two responsibilities that share nothing but the name:

| | M11 local-file profiling (built, ADR-0036) | M12 connector-catalogue discovery (this contract) |
|---|---|---|
| Performed by | The deterministic engine `data_profile.py`, reached through the `biq-data-ingestion` skill. **No agent and no model reads a file** | The `biq-data-profiler` agent calls granted discovery tools; the engine seals, parses and builds the result |
| Input | 1–20 local files | One sealed brief |
| Output | `DataProfileResult` | Catalogue result (§C.5) |
| Privacy guarantee | No cell value except ISO currency codes and non-restricted date bounds (ADR-0036 §6) | Value-free by measured tool classification and parser allowlist (§C.6, §G) |

**The M12 responsibility does not weaken the M11 guarantees:**

- The agent never profiles, opens, receives or references a local file, a dataset or a `DataProfileResult`.
- The profile engine never accepts a connector source; ADR-0036 §3 already refuses connector handles, and that
  refusal stands.
- Neither artifact embeds, references or feeds the other.
- ADR-0036 §6's privacy rules, source binding and non-evidence status are unchanged and are not relaxed for, or by
  analogy with, catalogues.
- Local-file profiling stays agent-free.

**Why the agent is justified for M12.** Resolution and named absence are local and deterministic, and need no agent.
Catalogue exploration passes ADR-0006's test on the grounds ADR-0036 reserved:

- **Context isolation:** raw discovery output of a large schema must not accumulate in the main thread.
- **Structural separation:** the context calling a connector must hold no web, file, shell or dispatch tool, and the
  main thread holds them all.

**Build rule.** `agents/biq-data-profiler.md` is created in M12-B only if at least one declared capability has a
complete §B.1 trust chain with interaction class `discovery`. An agent with an empty grant is never built, because an
absent `tools` field inherits every tool. Otherwise the agent stays deferred and every connector's catalogue status is
`capability_unsupported`.

#### D.2 Responsibility, inputs, outputs

- **Responsibility.** For one sealed brief: call the one named discovery tool, at most the brief's bounded number of
  times, with exactly the sealed arguments. The only addition allowed is a continuation cursor the same tool returned
  in this operation, where the declaration allows one. Then return catalogue records in the line protocol. It holds
  no logic (`CLAUDE.md` §3).
- **Input — the brief**, closed: an operation id, the connector identity, the exact tool name, the closed arguments,
  and bounds on calls and entries. The exact fields, protocol string and limits are **implementation contract items**.
- **Output — operation-bound record lines** on ADR-0017's proven shape, with **tokens distinct from `BIQ-REC/1` and
  `BIQ-END/1`**, so a research reply can never parse as a catalogue reply or the reverse. The exact tokens are an
  implementation contract item.
  - Every line carries this operation.
  - The declared count equals the number of record lines.
  - Prose around the lines is harmless content.
  - Any defect fails the whole reply, with no partial catalogue.

#### D.3 Permissions

**The agent must never receive:**
- raw business records, or raw local file contents;
- a dataset or a profile;
- Business Context;
- research content, evidence or synthesis material;
- the conversation;
- credentials, tokens or authentication material;
- arbitrary filesystem, web, shell or MCP access;
- any `read`, `write` or `administrative` tool.

**Only the exact measured value-free discovery tool or tools whose §B.2 bindings agree may ever be granted.**

| Question | Answer |
|---|---|
| Allowed tools | Exactly the declared `discovery` tools whose registry declaration, Gate record and grant agree (§B.2), by exact fully qualified name |
| Prohibited tools | `read`, `write` and `administrative` connector tools, including authentication tools; every tool of any other server, key or namespace, including same-vendor servers; `Bash`, `PowerShell`, `Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Glob`, `Grep`, `LS`, `WebSearch`, `WebFetch`, `Task`, `Agent`, `ToolSearch`, `ListMcpResourcesTool`, `ReadMcpResourceTool`, `Skill`, `SendMessage`, `mcp__plugin_businessiq_biq-verifier__recompute` |
| May use MCP? | Only the granted discovery tools |
| Filesystem access? | None |
| Read business data? | No — no files, no datasets, no record-returning tool |
| Execute commands? | No |
| External writes? | No — no mutating tool is grantable |
| Call research? | No — no web and no dispatch; no connector content reaches the gate (§F) |
| Produce evidence? | No |
| Enter synthesis? | No |

#### D.4 Binding tests

- **Static:** the agent's `tools`, the registry's declared `discovery` tools, the Connector Gate records and BusinessIQ's
  `.mcp.json` connector entries agree exactly on every §B.2 binding. Any disagreement fails the suite.
- **Runtime, opt-in** (the M11 pattern): instructed to use another tool, the agent executes none. The tools tried
  include a decoy server's tool, a same-vendor server's tool under another namespace, a `read` tool of the same server,
  an authentication tool, `ToolSearch` and a shell.

### E. MCP boundary

**E.1 Is MCP required?** **Yes, only as the transport of third-party connectors**, declared in BusinessIQ's own
`.mcp.json` through the Connector Gate. **M12 adds no BusinessIQ MCP server**, no proxy and no second operation on
`biq-verifier` (Option C). The `biq-verifier` entry and its tests are untouched.

**E.2 Server role.** A vendor's own server for its system of record, declared with identity only.

- `~~crm` HubSpot: the repository records its endpoint as verified to exist on 2026-09-08. It must be **re-verified
  and measured at the Gate**.
- `~~chat` Slack: **ineligible in M12**.
- No other category has a verified server, and none may be invented.

**E.3 Tool names and arguments.** Exact tool names, input schemas and output shapes of any candidate server are **not
known to this repository**. They are Connector Gate measurements, taken on a vendor sandbox or developer account
holding only synthetic data, and never guessed. The contract fixes the ceiling on arguments, which are closed per
declared capability and drawn only from:

- object-type ids from the declaration's closed list for that connector;
- fixed paging sizes from the declaration;
- an opaque continuation cursor the same tool returned earlier **in the same operation**.

**E.4 Return envelope.** The vendor's raw output is not a BusinessIQ envelope and never reaches Python. BusinessIQ's
envelope is the agent's record lines (§D.2), parsed against the sealed brief.

**E.5 Allowed and prohibited information.** Allowed toward the server: §E.3 only. Allowed back into BusinessIQ: §C.4
content only. Prohibited in both directions: §C.6 and §F.

**E.6 Authentication and credentials.**

- OAuth is run by the platform when the user starts it.
- The agent holds no authentication tool, and no BusinessIQ markdown instructs one.
- BusinessIQ observes only the relayed failure code `connector_not_authorized`.
- No BusinessIQ `.mcp.json` entry may carry `headers`, environment secrets or a token (static test).
- No module reads platform configuration, credential stores, `~/.claude*`, `.env*` or a keychain (source-scan test).
- No vendor error text is carried anywhere, because it can contain URLs, codes or tokens.

**E.7 Failure behaviour.** §H. Fail closed, no partial catalogue, no retry with changed arguments, no substitution by
another connector, web research or a cached catalogue.

**E.8 Tool identity binding and anti-substitution.** §B.1–§B.4. The brief names one tool; a reply echoing another tool,
connector or operation fails closed.

**E.9 Anti-forgery.**

- The operation id carries at least 64 bits from a cryptographic generator. A content-addressed id would be predictable
  to anyone who can write a label in the connected system, so an author of stored content cannot pre-write a matching
  line.
- The brief is **sealed and consumed once**, following ADR-0035's request pattern: a reply for an unknown or
  already-consumed operation is refused (replay). Its storage location is an implementation contract item within the
  existing gitignored runtime state; no new store is introduced.
- A record carrying an authority or identity key (`source_tier`, `trust`, `verified`, `authorized`, `approved`,
  `granted`, `operation`, `basis`, connector or capability identity) has it dropped, and the attempt is noted by key
  name (ADR-0017).
- No request or reply field can express authorization.

**E.10 Transcript leakage.** The agent's context and transcript hold the raw discovery output. This is why the
`discovery` classification requires measured value-free output (§G). The main context holds only the rendered
catalogue. No transcript holds a secret, because none passes through BusinessIQ. A runtime test asserts the main
transcript contains no canary record value from the sandbox fixture.

**E.11 Server instructions (C-4).** The Connector Gate records each candidate server's published instructions
verbatim. A server whose instructions direct tool use, data handling or disclosure is not admitted. BusinessIQ cannot
suppress platform-injected instructions, and says so.

### F. Privacy — what may cross each boundary

| From → to | May cross | Must never cross |
|---|---|---|
| Raw internal business data (files, datasets, KPI and analysis values) → connector arguments | **Nothing** | Every value, identifier, name, figure, period derived from data |
| Business Context → connector arguments | **Nothing** (no field is needed) | Business name, industry, any context field |
| Research content, evidence, synthesis → connector arguments | **Nothing** | Everything |
| Another connector's output → connector arguments | **Nothing** | Identifiers, labels, cursors from another connector or operation |
| Registry declaration → connector arguments | Closed object-type ids, fixed page sizes | — |
| Same tool, same operation → connector arguments | Its own opaque continuation cursor | — |
| Connector discovery output → agent context | What the measured `discovery` tool returns (value-free by classification) | Anything from a `read` tool |
| Agent reply → Python | §C.4 content on protocol lines | §C.6 prohibited fields (dropped, noted by name) |
| Catalogue → main model and user | Rendered catalogue, local presentation | Record values, counts, option values, identities, secrets |
| Catalogue, connector metadata, availability → research gate / scout | **Nothing** — the gate's inputs stay Business Context's externalizable subset (ADR-0009, ADR-0011) | Every connector-derived string |
| Catalogue, connector metadata, availability → synthesis, evidence, verification | **Nothing** (§I) | Everything |
| Catalogue → off-machine export | Only under ADR-0010 explicit approval | Automatic export of any kind |
| Connected-system record values → **anything**, under this contract | **Nothing** — M12-C is `BLOCKED` | Everything |

**Minimum constraints on any future M12-C ADR (not approvals):**

- Record values would reach deterministic Python only as a machine-captured verbatim payload, digest-bound, through M3,
  M4 and the engines.
- No model context would ever hold a value, and a model-relayed value is never admissible.
- Only aggregates would reach a model, as for files (§17), with M3 sensitivity classes and k-floor banding.
- Read arguments would carry no identifier from another source.

A connector's output that is itself Tier 3 material (customer names, individual transactions) stays Tier 3 under
ADR-0009 wherever it is, with no approval path off the machine.

### G. Read/write boundary

| Class | Definition (criteria for measurement and review) | M12 |
|---|---|---|
| `discovery` | Non-mutating; returns only schema-level structure; **demonstrated by Gate measurement on synthetic data** to return no record value, sample, option value, count, user/owner identity or email; no side effect a user would recognise | **Grantable in M12-B** only through the complete §B.1 chain |
| `read` | Non-mutating; returns record-level values, samples, option values, counts or identities | **Not grantable.** M12-C, `BLOCKED` |
| `write` | Creates, updates, deletes, sends, posts, subscribes, shares, exports or triggers anything | **Prohibited in M12; no path exists.** A future write capability needs its own ADR and ADR-0010 explicit per-action approval, and remains out of v1 scope |
| `administrative` | Authentication, authorization, installation, configuration, user or permission management | **Prohibited** for BusinessIQ components; authentication is the user's, through the platform |

- A property that cannot be demonstrated counts as absent: a tool whose value-free output is not shown by measurement
  is `read`.
- A tool whose classification is uncertain takes the more consequential class; a tool combining classes takes the
  most consequential.
- A declaration is never reclassified to fit a measurement.
- Vendor-side access logging and rate-limit consumption are not business side effects under ADR-0010. They are
  recorded in the connector's integration page.

### H. Failure model — closed codes, deterministic mapping

| Code | Situation | Outcome |
|---|---|---|
| `connector_not_configured` | No registry entry for the capability placeholder | Named absence + file-export guidance; that capability only degrades (§16) |
| `ambiguous_connector` | More than one registered connector for the capability and no user choice | Ask the user; never choose by order, vendor, recency or availability |
| `capability_unsupported` | Registered connector has no complete discovery trust chain for the requested scope, or the agent is not built (§D.1) | Named, with the file path |
| `binding_mismatch` | Registry declaration, Gate record, `.mcp.json` and grant disagree on any §B.2 binding, or a required layer is missing | Use refused before any dispatch; nothing repaired |
| `connector_unavailable` | Server not connected or tool not reachable in this session (relayed) | Named; no retry with changes; no substitute |
| `connector_not_authorized` | Registered and reachable, but the user has not authenticated it (relayed) | Tell the user to authenticate through the platform; BusinessIQ never starts it |
| `authentication_failure` | Authentication attempted and rejected (relayed) | Named; no message text carried |
| `authorization_failure` | Server refused the call for scope or permission (relayed) | Named; BusinessIQ never requests broader access |
| `timeout` | No reply within the bound | Named |
| `tool_failure` | Platform or tool error without a mappable code | Named; no message text |
| `malformed_response` | Protocol defect: wrong operation, count mismatch, missing or duplicate terminator, malformed line, wrong tool or connector echo | Whole reply refused; no partial catalogue (ADR-0017) |
| `operation_unknown` | Reply for an unsealed, consumed or foreign operation (replay) | Refused |
| `stale_metadata` | Relayed reply shows a registered tool missing, renamed, or changed in argument or output shape against the Gate record | Capability unusable until re-measured and re-approved; never auto-adopted |
| `metadata_conflict` | Within one reply, one identifier with differing attributes | Every variant kept and flagged, none chosen (ADR-0016's rule); status `complete_with_limitations` |
| `external_content_unavailable` | A requested object type is reported absent or inaccessible | That scope item `unavailable`; others proceed |
| `privacy_restricted` | A requested scope or a reply field falls under §C.6 | Refused or dropped and noted by key name |
| `insufficient_data` | Valid reply with no entries for the scope | Absence of catalogue entries, never evidence the object has none |
| `request_invalid` | Unknown field, non-closed value, caller-supplied authority, unregistered or forged connector, server or tool identity, capability outside the vocabulary | Refused whole before any dispatch |
| `blocked_prerequisite` | Any record-read request while M12-C is `BLOCKED` | Refused with the file-export alternative |

Relayed codes are untrusted and can only reduce what is shown. Result statuses follow ADR-0036's shape:
`complete` · `complete_with_limitations` · `partial` · `unavailable`.

### I. Provenance

| Connector-derived item | Observation | Sourced evidence (3) | Calculation (4) | Interpretation (5) | Assumption (6) | Recommendation (7) |
|---|---|---|---|---|---|---|
| Registry declaration, Gate record, resolution, availability, authorization state | No | No | No | No | No | No |
| Catalogue entry (M12-B) | Diagnostic metadata only, never a claim | No | No | No | No | No |
| Any response, **because** it passed the §B.1 chain | No | No | No | No | No | No |
| Model-relayed record value, ever | No | No | No | No | No | No |

**M12-B produces no claim of any class and no synthesis input.** `SynthesisSet.register_claims()` is extended in M12-B
to refuse:

- a catalogue result, and any part of one;
- any record identifying itself as a connector catalogue;
- connector-only fields (the exact field list follows the implementation's names);
- **every class-2 (connected-system) claim**, because no M12-B path can produce a legitimate one.

**Minimum constraints on any future M12-C ADR before connector-derived information may reach synthesis (not
approvals):**

1. It was machine-captured verbatim by a mechanism that ADR accepts after §M, never model-relayed.
2. The payload is bound by SHA-256 and carried by a run registration in the ADR-0035 §2 pattern.
3. It was read through M3 (sensitivity classes), graded by M4 (quality gate), and computed by the engines.
4. The internal statements were registered through the existing translators and satisfy internal footing (ADR-0023).
5. The class-2 presentation carries the system name and a pull timestamp that no model supplied.
6. Re-pulling from a live system is never recomputation. Verification of a class-2 figure would run over the captured,
   hashed payload only (the ADR-0035 *Revisit* question).

No catalogue ever appears in a verifiable artifact.

### J. Security test contract

Mandatory in M12-B, deterministic unless marked *runtime* (opt-in, M11 pattern, run and reported before completion):

| # | Category | Must prove |
|---|---|---|
| 1 | Forged connector capability | A capability outside the closed vocabulary, or a reply line declaring a capability, tool or interaction class, is refused or dropped and noted |
| 2 | Forged authorization | A request or reply carrying `authorized`, `approved`, `granted`, `scope`, `trust`, `verified` is refused whole (request) or has the key dropped and noted (reply); no API accepts authorization; no registry, Gate or resolution object is accepted as permission |
| 3 | Unauthorized tool use | Static: grant = declared `discovery` tools = Gate-measured tools, exactly. *Runtime:* instructed to call a `read`, `write` or authentication tool, a decoy server's tool, `ToolSearch` or a shell, the agent executes none |
| 4 | Wrong MCP tool | A reply echoing a tool other than the sealed brief's fails closed |
| 5 | Extra MCP tool | `.mcp.json` servers = `biq-verifier` + registered connector servers exactly; grant has no extra name; *runtime* decoy tool never executed |
| 6 | Raw business-data leakage | Rendered and serialised catalogue of a canary fixture (with record values, option values, counts, emails) contains none of them; no connector module imports the gate, query builder, retrieval request, scout, `commands.run`, the profile engine or any reader; the gate accepts no connector object; *runtime* main transcript holds no canary value |
| 7 | Secret leakage | No token-shaped string in registry, `.mcp.json`, fixtures, docs; BusinessIQ `.mcp.json` entries carry no `headers`/`env`; source scan finds no read of `~/.claude*`, `.env*`, credential stores; failure outputs carry no message text; secret-named reply keys dropped, value never echoed |
| 8 | Prompt injection | Labels and descriptions carrying instructions are data: parsed as content, change no status, scope, tool or count; *runtime* injected instruction in a sandbox label causes no additional tool call |
| 9 | Connector response injection | Protocol-looking text inside a label creates no record; a smuggled extra line fails the count; research tokens never parse as catalogue and the reverse |
| 10 | Malformed connector response | Every structural defect in §H `malformed_response` fails closed with no partial catalogue |
| 11 | Stale connector metadata | A relayed tool or shape differing from the Gate record yields `stale_metadata` and the capability is unusable; a reply for a consumed operation yields `operation_unknown` |
| 12 | Cross-connector confusion | A reply for connector A under B's operation is refused; two registered connectors for one capability yield `ambiguous_connector` with no auto-choice; no catalogue mixes connectors |
| 13 | Write / side-effect attempt | The registry refuses a `write` or `administrative` declaration in any grant or brief; a write request yields a refusal with no approval offered; source scan finds no mutating code path |
| 14 | Synthesis re-entry bypass | `register_claims()` refuses a catalogue, each part, connector-only fields and every class-2 claim; genuine candidate claims still accepted |
| 15 | Model-created authorization | A relayed `completed`, a `configured` resolution or a Gate record reference never becomes authorization; no status value means authorized; a model-supplied authorization field is refused |
| 16 | Model-created connector identity | A connector id, server identity or tool name absent from the registry is refused at request and reply; a new identity in a reply is dropped and noted; a `.mcp.json` server not in the registry fails the consistency test; no BusinessIQ markdown instructs enumerating session servers or tools |
| 17 | Protocol matrix (ADR-0017 lessons) | Operation binding, count check, single dispatch, no retry, no repair, zero-record = `insufficient_data` ≠ `malformed_response` |
| 18 | Registry immutability | Registry records and mappings are read-only; no configuration key, Business Context field, argument or model output adds a connector, server, tool, capability or interaction class |
| 19 | Layer-binding agreement (§B.2) | Declaration without a Gate record, a Gate record without a declaration, a grant without both, and each single-field disagreement (connector, placeholder, server identity, namespace, tool name, class, argument shape, output shape) yield `binding_mismatch` and no dispatch; a same-vendor server under another key or namespace never satisfies a registered identity |

Existing tests pinning `.mcp.json` and the agent set are **retargeted, never deleted**, and every security assertion in
them is kept. No M12-C test belongs to this contract.

### K. Human control

| Operation | Class |
|---|---|
| Viewing capability resolution, the registry and named absences (local, no network) | **Automatic, read-only** |
| A catalogue discovery call through a complete §B.1 chain to a user-authenticated connector with closed arguments (nothing internal transmitted) | **Automatic, read-only** (ADR-0010 read-only analysis) |
| Choosing among registered connectors for one capability | **User-confirmed** (a clarification, per request, not persisted) |
| Authenticating a connector | **User-initiated** through the platform; BusinessIQ never starts it |
| Writing a new catalogue rendering into `./businessiq-output/` | None; path stated (ADR-0010) |
| Overwriting a file; exporting a catalogue off the machine | **Explicit, per action** (ADR-0010) |
| Adding or changing a `.mcp.json` connector entry, registry declaration, Gate record or agent grant | **Connector Gate** (development-time, owner) |
| Connected-system record reads | **Not available** — M12-C `BLOCKED`; its approval class is for its own ADR |
| Any write or administrative connector interaction; any connector argument carrying internal, context, research or other-connector content; any connector content into research; reading or storing a credential; adopting an unregistered or substituted server or tool; a model-relayed value as data; financial transactions | **Prohibited** — no approval unlocks these in M12 |

**Must be read-only:** every M12 connector interaction. **Must never produce an external side effect:** resolution,
catalogue, binding checks, failure handling and tests.

### L. Completion gate

**M12-A (this contract):** met — ADR-0037, OD-1 and OD-2 accepted by the owner on 2026-09-17.

**M12-B `COMPLETED` requires every item. No item refers to M12-C.**

1. **Connector Gate passed** for each `.mcp.json` connector entry added. Its approved development record holds every
   §B.1 item 7 binding, on synthetic data. If no declared capability completes the chain, M12-B still completes with
   the registry, resolution, named absence, binding checks and catalogue engine, and with the agent deferred under
   §D.1.
2. **Files:**
   - the connector registry, resolution, binding checks and catalogue engine under `lib/python/biq/` (module names are
     an implementation item; engine placement follows the precedent of `research/intents.py`);
   - a closed schema under `lib/schemas/`;
   - `agents/biq-data-profiler.md` only under §D.1;
   - `skills/biq-data-ingestion/SKILL.md` extended for connector resolution and catalogue (skill count stays 20; no
     new command);
   - the `register_claims()` refusal extended;
   - `CONNECTORS.md`, `architecture.md` §4/§10/§11/§16/§18 and the connector's integration page updated;
   - `project_plan.md`, a dated development record and the task report.
3. **Agent/tool boundaries:** §B.2 agreement, the §D.3 grant and must-not-receive list, §E.6 no-secret configuration.
   The M11 local-file profile is unchanged (its tests pass unmodified, apart from the scope guards retargeted under
   item 6).
4. **Tests:** focused deterministic tests for every §H code, §B rule, §C content rule, §F row and §I refusal; all
   nineteen §J categories; the runtime agent-boundary run executed and reported with 0 failures, or the agent not
   built under §D.1.
5. **Live protocol verification:** where an agent is built, one fresh-session dispatch against a sandbox account with
   synthetic data. The first delivery parses with no manual extraction, repair or retry (the M9-C.10–C.16 lessons).
   Until that has run, the catalogue path is `REVIEW`, not `COMPLETED`.
6. **Regression:** `python tests/run_tests.py` — 0 failures, 0 errors; any skip-count change explained; retargeted
   tests listed with the assertion each preserves.
7. **Strict validation:** `claude plugin validate . --strict` passes. Recorded as **not** evidence for the agent or MCP
   boundary (M11 measurement).
8. **Security review:** no unresolved critical or high finding; residual risks (§Consequences) restated in the record.
9. **Git checkpoint:** a commit only on the owner's request after review, one logical change, documentation in the
   same commit; never pushed without instruction; working tree clean at the checkpoint.

**M12-C:** recorded **`BLOCKED`** (OD-1). It is unblocked only when P-1 to P-5 (§M) are measured and satisfied, **and**
its own ADR is accepted with its own security evidence and Data Layer design. Until then it has no implementation
milestone.

**Milestone 12 `COMPLETED` (OD-1, accepted):** M12-B `COMPLETED` and verified, with M12-C still explicitly recorded
`BLOCKED`. Marking M12 `COMPLETED` does not close, approve or advance M12-C.

### M. M12-C prerequisites — platform facts to measure, and the rule if they fail

Measured on the installed Claude Code, never assumed (ADR-0001). The repository's only prior investigation of runtime
interception mechanisms is M9-C.7 and M9-C.8, which examined subagent-level hooks for a different purpose. **No
candidate mechanism for M12-C is proposed or presumed here.**

- **P-1** A supported mechanism exists by which a verified `read` tool's output reaches deterministic Python
  **verbatim**, authored by no model.
- **P-2** The same mechanism keeps the values out of **every** model context, including the calling agent's. What any
  persisted transcript retains is measured.
- **P-3** A call's arguments can be bound to a sealed pull request and refused **before transmission** when they
  differ.
- **P-4** Capture and refusal apply only to BusinessIQ-sealed operations, and never observe, record or alter the user's
  other tool use.
- **P-5** An agent grant naming a third-party server's tool restricts the agent exactly as measured for the stdio
  `biq-verifier` tool.

**While any of P-1 to P-5 is unverified, M12-C stays `BLOCKED`.** It is not replaced by a model relay, a main-thread
call, a `Bash` or `Write` grant, a Python HTTP client, or a BusinessIQ proxy holding credentials, without a new ADR.
Satisfying P-1 to P-5 does not itself unblock M12-C: its own ADR must still be accepted. The file-export path serves
every connector capability meanwhile.

## Relationship to ADR-0004

ADR-0004 was inspected directly. Its decision reads: "**Option B.** Skills address capabilities, never products.
`biq-connector-broker` performs discovery, capability mapping, read-only enforcement and named degradation. `.mcp.json`
ships **only endpoints verified to exist**; every other category is documented in `CONNECTORS.md` as user-configurable.
Adding any server is a Connector-gate decision requiring explicit user approval." Option B, which the decision adopts,
says the broker "resolves the placeholder at runtime to whatever server is connected".

**This is a partial supersession, not an independent decision and not a refinement that merely adds detail.** Two of
ADR-0004's clauses no longer hold under OD-2:

| ADR-0004 clause | Superseded by |
|---|---|
| The broker "performs discovery", as adopted from Option B: "resolves the placeholder at runtime to whatever server is connected" | §B.1–§B.4. A placeholder resolves only to exact, registered connector identities whose trust chain is complete. No connected server is discovered or adopted |
| "every other category is documented in `CONNECTORS.md` as user-configurable" | §B.1 items 2, 9 and 10. A server the user configures outside the registry is not usable by BusinessIQ, whatever its vendor; a category with no registered connector is a named absence |

One piece of **rationale**, not decision text, is also no longer accurate. Option B's pro "adding a connector is a
`.mcp.json` entry plus a capability-map row" now needs a registry declaration, an approved Connector Gate record and the
matching grant. `architecture.md` §11 and §18 record the current extension cost.

**Unchanged and still governing:**
- skills address capabilities, never products;
- capability mapping, read-only enforcement and named degradation;
- `.mcp.json` ships only endpoints verified to exist, and no endpoint is ever invented;
- adding any server is a Connector-gate decision requiring explicit approval;
- the uploaded file path is load-bearing, not a fallback;
- ADR-0012's placement of the broker inside `biq-data-ingestion`.

**ADR-0004 remains historically immutable.** Its text and status line are not edited. The partial supersession is
recorded in `docs/decisions/README.md` and `architecture.md` §19, as ADR-0036's refinement of ADR-0006 and ADR-0031's
refinement of ADR-0022 were. OD-2's substance was accepted on 2026-09-17, and current architecture and connector
documentation already state it. The supersession is formal as of this ADR's acceptance on 2026-09-17.

## Architectural compatibility

| Accepted contract | Held by |
|---|---|
| M3 Data Layer privacy | M12-B reads no rows; M12-C (blocked) must pass through M3 |
| M9 external research boundary (ADR-0009/0014/0015/0017) | Agent has no web or dispatch; scout gains no connector tool; no connector string reaches the gate; web-retrieving connectors excluded; operation-bound, fail-closed protocol reused with distinct tokens |
| M9-A capability security | Closed vocabularies; immutable registry; exact identity bindings; authority keys dropped and noted; no caller-supplied authority; fail closed |
| M10 synthesis provenance (ADR-0022/0023/0031) | Catalogue non-evidential and refused at re-entry; every class-2 claim refused in M12-B |
| M11 verification (ADR-0034/0035) | No catalogue in verifiable artifacts; `biq-verifier` untouched; sealed-request pattern reused, not changed |
| M11 profiler (ADR-0036) | The reserved agent is used for its reserved purpose; local-file profiling stays agent-free and its guarantees unchanged; "no web, no shell, no raw-row read" held |
| Human approval (ADR-0010) | All M12 interactions read-only; consequential actions unchanged; no write path |
| No-secret policy (`CLAUDE.md` §7) | Platform OAuth only; identity-only `.mcp.json`; no config or credential reads; no error text |
| External-content trust (`architecture.md` §12) | Connector output untrusted for instruction while confidential for privacy; C-4 residual stated |

Contradictions found and handled: C-1 (partial supersession of ADR-0004, OD-2), C-2 (discovery/data separation; M12-C
`BLOCKED`, OD-1), C-3 (clarification only), C-4 (residual risk). No accepted ADR is edited.

## Owner decisions — accepted 2026-09-17

- **OD-1 — accepted.** M12 may be marked `COMPLETED` when M12-B is fully implemented and verified, even though M12-C
  remains `BLOCKED`. M12-C stays explicitly recorded `BLOCKED` until P-1 to P-5 are satisfied and its own ADR is
  accepted.
- **OD-2 — accepted.** M12 uses exact registry-bound connector and server identity. A same-vendor server under another
  namespace does not qualify. Exact identity, declared capability and measured tool binding are required (§B).

## Reason

Option E is the only option that keeps every accepted boundary intact while still delivering the part of M12 that can
be delivered. The disclosure, verification and profiler milestones all converged on one principle: authority is
structural (a declared grant, a sealed request, a fail-closed parser), and values never pass through a model. Applied
to connectors, that principle separates what a model may relay (value-free structure, labelled unverified and
non-evidential) from what it may never touch (records), and blocks the second until the platform can prove it. Binding
connectors to BusinessIQ-declared, measured and granted identities is the connector equivalent of ADR-0018's registry
over heuristics: an entry exists because a person verified it, which is what makes it safe. Requiring declaration,
measurement and grant to agree means no single layer — a hopeful declaration, a stray measurement or an over-broad
grant — can make a tool usable on its own.

## Consequences

**Positive.**
- Named absence and a capability map for every placeholder, with no network and no secret.
- A catalogue that answers "what does my CRM hold" without a record in any model context.
- A grant bound to exact, measured identities that no look-alike can satisfy.
- No connector string can reach research, synthesis or verification.
- Class 2 stays unproduced rather than model-authored.
- M12-C has an explicit, testable unblock condition that is separate from M12-B.

**Negative.**
- M12 may complete without connected-system record reads, which the specification implied (extends R-02).
- Users who connected a vendor server through another plugin must also authenticate BusinessIQ's own declared entry.
- The catalogue may be empty for a connector whose vendor exposes no demonstrably value-free discovery tool.
- Every change on the vendor's side to a bound field disables that capability until it is re-measured.
- Model-relayed labels are unverified, and a value hidden inside an allowed free-text label cannot be detected by
  shape. It is local-only and non-evidential, but it is a residual risk.
- The main thread could still call a connector tool directly if another plugin exposes one. BusinessIQ's control
  there is advisory (instructions plus a sequencing test), as ADR-0035 accepted for `recompute`.
- Platform-injected server instructions (C-4) are outside BusinessIQ's control.
- Three existing guard tests must be retargeted.

**Follow-up required.**
1. Owner acceptance of this ADR — done, 2026-09-17.
2. M12-B per §L, starting with Connector Gate measurement of candidate servers.
3. M12-C stays `BLOCKED`; measuring P-1 to P-5 and writing its ADR is separate work that nothing here schedules.

## Revisit when

- The platform offers a verified way for plugin Python to receive an MCP tool result without a model context (M12-C).
- A vendor publishes a first-party server for accounting or spreadsheets (ADR-0004's own revisit condition).
- A write-back capability is proposed. That needs its own ADR and ADR-0010's explicit approval, and is outside v1.
- A connector is proposed that retrieves public web content (ADR-0014 applies to it unchanged).
- Agent grants can be verified to restrict tool **arguments**, not only tool names.
