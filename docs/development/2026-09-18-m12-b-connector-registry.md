# 2026-09-18 — M12-B connector registry and value-free discovery catalogue

**Milestone:** 12 — MCP Connector Layer: M12-B implementation
**Status on completion:** REVIEW — implemented and tested with **no connector admitted** (ADR-0037 §L item 1);
uncommitted, awaiting owner review. M12-C stays `BLOCKED`.
**Supersedes:** None. Follows `2026-09-18-m12-a1-optional-connector-lifecycle.md`, which is left unedited.

## 1. Prompt / task performed

Implement only the buildable M12-B scope of ADR-0037, as narrowed by ADR-0038's OD-3:

- a fixed, registry-bound connector catalogue;
- exact capability lookup and named absence;
- a value-free metadata catalogue;
- exact identity binding between registry, Connector Gate and grant;
- deterministic, fail-closed behaviour.

The prompt ruled out every one of these:

- record reads, writes, authentication and administrative operations;
- evidence, synthesis and analysis;
- a new command or skill;
- a `.mcp.json` or HubSpot entry;
- a fake Gate record;
- a commit or a push.

Measure the actual tool surface before deciding admission, and take the §L item 1 path if no gateable
capability exists.

## 2. Objective

Deliver ADR-0037 §L's M12-B items so that:

- the registry, resolution, named absence, binding checks and catalogue engine exist and are proven;
- nothing is admitted without a complete, approved, BusinessIQ-owned discovery chain;
- file-based BusinessIQ is untouched.

## 3. Changes made

1. **Baseline.** `HEAD` = `origin/main` = `0425af28c305919ddb4114e20f73412957be6648` after `git fetch origin`; working
   tree clean. Full suite on the clean tree: **4,555 tests, 0 failures, 0 errors, 26 skipped**, identical to the
   recorded baseline.
2. **Read:**
   - `CLAUDE.md`, `project_plan.md` (M11–M12) and `CONNECTORS.md`;
   - `architecture.md` §4, §10–§13 and §16–§19;
   - ADR-0004, ADR-0037 and ADR-0038 in full;
   - the decisions and docs indexes, and the M12-A.1 record;
   - the precedents: `research/intents.py` (immutable registry), `verification.py` (sealed request),
     `research/scout.py` (line protocol), `data_profile.py` (result shape, build token) and
     `synthesis_set.register_claims()` (re-entry refusal);
   - the three tests that pin `.mcp.json` and the agent set.
3. **Connector Gate measurement** (§9, below): no admissible capability. The §L item 1 path was taken.
4. **Engine.** New package `lib/python/biq/connectors/`, one concern per module:
   - `contract.py` — closed vocabularies:
     - the six placeholders, with `~~chat` ineligible;
     - the four interaction classes, of which only `discovery` is permitted;
     - the 19 §H codes, each with one sentence of its own;
     - result statuses, entry kinds and data types;
     - the authority-key and §C.6 prohibited-key lists;
     - the value-shape screen.
   - `registry.py` — the fixed registry:
     - built from source-declared `_DECLARATIONS`, deep-frozen, with read-only proxies;
     - structurally validated at build;
     - exact lookup and resolution (`not_configured` / `configured` / `ambiguous`);
     - **`_DECLARATIONS = ()`**.
   - `binding.py` — the Connector Gate record form: exactly one fenced `biq-connector-gate` JSON block, in a
     dated `docs/development/` record, with a closed field set. Also:
     - readers for `.mcp.json`, the `biq-data-profiler` grant and the Gate records, anchored to the plugin
       root and never to the working directory or the environment;
     - `chain_mismatches()`, the §B.2 agreement check, which names each disagreeing binding;
     - `admission_findings()`, which applies OD-3 and the §D.1 build rule to the shipped repository.
   - `catalogue.py`:
     - the ADR-0038 §5 evaluation order;
     - the sealed, consumed-once brief;
     - the fail-closed `BIQ-CAT/1` / `BIQ-CAT-END/1` parser;
     - the immutable `CatalogueResult`, with schema validation and rendering.
5. **Schema.** `lib/schemas/connector.schema.json`: the closed result, with definitions for resolution, brief,
   declaration, Gate record, entry and the 19-code enum. It uses only keywords `jsonschema_mini` enforces.
6. **Synthesis re-entry (ADR-0037 §I).** `SynthesisSet.register_claims()` now refuses:
   - a connector catalogue, and every part of one;
   - a resolution or a brief;
   - connector-only fields and catalogue or operation ids;
   - every class-2 claim, recognised by `class`, `provenance_class`, `evidence_class` or `class_name`.

   Detection is by shape, so synthesis imports nothing from `biq.connectors`. A genuine candidate claim is still
   accepted.
7. **Skill.** `skills/biq-data-ingestion/SKILL.md` gained a *Connected systems* section:
   - resolve through the registry only;
   - present the named absence and the file alternative;
   - never enumerate session servers or tools;
   - never start or suggest a sign-in, and never ask for a credential;
   - never claim a connection;
   - no record reads or writes;
   - a catalogue is not evidence.

   One sentence was added to the description so connector questions route here. The skill count is unchanged
   and no command was added.
8. **Tests.** A synthetic fixture module (`tests/connector_fixtures.py`) and two suites (§8).
9. **Documentation** (§14).

### Implementation contract items fixed here (ADR-0037 leaves these to implementation)

| Item | Decision |
|---|---|
| Module placement | `lib/python/biq/connectors/{contract,registry,binding,catalogue}.py`, following `research/intents.py` |
| Gate record form | One fenced JSON block whose language tag is `biq-connector-gate`, per dated development record. It has 17 closed fields: identity, transport, namespace, tool name, class and reasons, object types, arguments, output fields, verbatim server instructions (or `null`), the value-free proof (`demonstrated`, `synthetic_data`, `method`), `measured_on`, `platform_version` and `owner_acceptance` |
| Brief storage | `./.businessiq/connectors/operations/<op>.json`, inside the existing gitignored runtime state. It is written exclusively, claimed by rename and deleted on close, whatever the outcome |
| Operation id | `cop-` followed by 24 hex characters (96 bits) from `secrets` |
| Line protocol | Records: `BIQ-CAT/1 <op> {json}`. Terminator: `BIQ-CAT-END/1 <op> <connector_id> <tool_name> <outcome> <count>`. `<outcome>` is `completed` or one of the 7 relayable codes. Neither token prefixes the research tokens, and neither parser reads the other's lines (tested) |
| Argument sources | `object_type` (one call per scoped object type), `page_size` (fixed integer 1–1000) and `cursor` (named for the agent, supplied only from the same tool in the same operation) |
| Entry allowlist | object: `kind, object, label`. property: adds `property, data_type, required`. relationship: `kind, object, related_object, label`. A declaration's allowlist is a subset of this |
| Identifier | `^[A-Za-z][A-Za-z0-9_.-]{0,63}$`. A bare id, a number, an email or a URL cannot pass |
| Value-shape screen | Matches emails, URLs, runs of 6 or more digits, ISO dates, currency and decimal amounts, JWTs, prefixed API keys, bearer strings, long hex, and long mixed-case alphanumeric runs. A matching identifier drops its entry; a matching label is dropped; a matching key name is recorded as `<unnamed>`. Each is noted as `privacy_restricted` |
| `timeout` | Closing with `reply=None` (no reply delivered), or a relayed `timeout` |
| Write / administrative request | `request_invalid`, with the fixed sentence "BusinessIQ has no write or administrative connector interaction…". No §H code describes an interaction that has no path, and the sentence differs from the forged-request message that shares the code |
| Scope outside the declaration, or more calls than `max_calls` | `capability_unsupported`, ADR-0038 state 2 ("scope lies outside the admitted capability") |
| Result identity | `cat-` followed by 12 hex characters, over connector, placeholder, requested object types and normalised entries. It excludes the operation and time, and is `null` when no entry exists |

None of these adds a failure code, an interaction class, a lifecycle state, an authority or a security boundary.
Each is inside the latitude ADR-0037 marks "implementation contract item".

## 4. Files created

- `lib/python/biq/connectors/__init__.py`
- `lib/python/biq/connectors/contract.py`
- `lib/python/biq/connectors/registry.py`
- `lib/python/biq/connectors/binding.py`
- `lib/python/biq/connectors/catalogue.py`
- `lib/schemas/connector.schema.json`
- `tests/connector_fixtures.py`
- `tests/unit/test_m12b_connector_registry.py`
- `tests/negative/test_m12b_connector_security.py`
- `docs/development/2026-09-18-m12-b-connector-registry.md`

## 5. Files modified

- `lib/python/biq/synthesis/synthesis_set.py` — the `register_claims()` connector and class-2 refusal
- `skills/biq-data-ingestion/SKILL.md` — the connector section and one description sentence
- `CONNECTORS.md`, `architecture.md` (§4, §10, §11, §13, §16, §18), `project_plan.md`,
  `docs/integrations/README.md`

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | User-reachable? |
|---|---|---|
| Capability resolution and named absence for all six placeholders | `connectors.registry.resolve()` / `resolve_all()` via `biq-data-ingestion` | Yes. Every placeholder is `not_configured`, with the file alternative |
| Discovery request evaluation and sealing | `connectors.catalogue.request_discovery()` | Yes. It always ends in a named refusal, because nothing is registered |
| Reply parsing and catalogue building | `connectors.catalogue.close_discovery()` | No. No brief can be sealed with an empty registry, so it is exercised only against the synthetic fixture |
| Admission and binding checks | `connectors.binding` | Static suite |
| Synthesis refusal of connector material and class 2 | `synthesis_set.register_claims()` | Yes |

## 8. Tests performed

```
git fetch origin; git rev-parse HEAD; git rev-parse main origin/main; git status --short --branch
python tests/run_tests.py                                    # baseline, clean tree
python tests/run_tests.py unit.test_m12b_connector_registry
python tests/run_tests.py negative.test_m12b_connector_security
python tests/run_tests.py                                    # final
claude plugin validate . --strict
git diff --check
```

Also run:

- a secret-pattern scan of every added diff line and every untracked file;
- a Python line-ending check;
- a scope audit (§9).

**The synthetic fixture.** `tests/connector_fixtures.py` builds an in-memory connector:

- id `synthetic-crm`, server `biq-synthetic-crm`, URL under the reserved `.invalid` domain;
- a "Gate record" that is a Python dict under a 2099 path that does not exist;
- every reason and method field says `SYNTHETIC FIXTURE - not a measurement`.

It is patched in only for the duration of a test. It is not, and is never presented as, a Connector Gate
measurement.

**Coverage against the prompt's A–I and ADR-0037 §J** (115 new tests):

| Area | Where |
|---|---|
| A. Registry | Shipped registry empty; exact identity with near misses (case, whitespace, prefix, suffix); unknown placeholder; duplicate ids, servers, tools and capabilities; every malformed field; `~~chat` ineligible; read, write and administrative undeclarable; identity-only transport; dated Gate path; closed arguments and outputs; immutability (J-18) |
| B. OD-3 | Complete synthetic chain admits; missing Gate record, grant or `.mcp.json` entry does not. Documentation and the vendor endpoint admit nothing. HubSpot ids are refused. Another plugin's server and namespace fail; an authentication-only tool fails. A stray server or agent fails admission. The shipped repository has no findings |
| C. Value-free | Entries, types, required flags and relationships kept. Canary values, options, picklists, samples, counts, record ids, owners, emails, tokens, amounts, dates and URLs never reach the JSON or the render, and are noted by name. Value-shaped identifiers drop their entry; value-shaped key names are `<unnamed>`; labels are bounded and stripped of control characters; out-of-scope entries are dropped; undeclared fields are dropped |
| D. Exact binding (J-19) | Each single disagreement names its binding: connector, placeholder, server identity, transport, namespace, tool name, class, argument shape, output shape, value-free property, missing Gate record, grant (absent, empty, extra, duplicate, same-vendor), missing server, `headers`/`env`. No prefix, case, whitespace or alias matching. A mismatch seals nothing. A layer change between seal and close is refused; a tampered brief is a `sealed_operation` mismatch |
| E. 19 codes | Each code produced by its situation, schema-valid, with its status. Relayed codes never build a catalogue. A relayed failure carrying records is malformed. Zero records is `insufficient_data`. Messages are distinct |
| F. Optionality | The profile and `/sales-analysis` output on the demo file (minus wall-clock stamps) are byte-identical with no connector, a registered one, one relayed as not authorized or unavailable, and one unverified. No file-workflow module imports the connector layer. No connector-named skill, command or agent exists |
| G. Security | Model-declared connected, authorized, verified or available refused in requests and terminators, and dropped from records. No public function takes a tool, server, registry or arguments. No mutating or dispatching function exists. An AST scan finds no environment, credential-store or network access. No runtime markdown names an authentication tool, another plugin's tools, or server enumeration |
| H. Determinism | Any record order and duplicate lines give identical bytes and id; the id excludes operation and time; it changes with scope or entries; operation ids are random and distinct; schema keywords are all enforced |
| J-6 / J-9 / J-14 | Connector modules import no research, command, profile, reader or synthesis code. The disclosure gate accepts no connector object. Catalogue lines fail the scout parser, and research tokens fail the catalogue parser. Every catalogue part, resolution, brief, connector field and class-2 claim is refused at re-entry; a genuine claim is accepted |
| Lifecycle (ADR-0038 §4, §12.1) | States 1–7 map to their codes. No relay reaches a statically refused state. Nothing about a connection persists. No sentence affirms a connection, authorization, verification or availability, or names a screen, URL or vendor |

**Runtime §J halves** (J-3, J-5 and J-8 runtime, and the §E.10 transcript canary) **were not run**. They test the
connector agent, which is not built under §D.1. The static suite pins its absence.

## 9. Test results

### Connector Gate measurement

Inspection only. No tool was called.

- **BusinessIQ `.mcp.json`:** exactly `biq-verifier` (stdio). No connector server is declared.
- **Session tool surface** (deferred tool list, and `ToolSearch "+hubspot"`, which loads schemas only):
  - HubSpot: exactly `mcp__plugin_marketing_hubspot__authenticate` and
    `mcp__plugin_marketing_hubspot__complete_authentication`. The server is `plugin:marketing:hubspot` over
    http, **another plugin's** server. Its own description says its "real tools" appear only after OAuth.
  - Other business-system servers (atlassian, bigquery, hex, amplitude, klaviyo, supermetrics, similarweb,
    ahrefs, canva, figma, notion, slack) expose only `authenticate` / `complete_authentication`, and all
    belong to other plugins.
  - `mcp__plugin_businessiq_biq-verifier__recompute` is BusinessIQ's own verifier, not a connector. It failed to
    connect in this session.
- **Result:** no candidate satisfies ADR-0037 §B.1. The prompt's stop conditions 2 (only another plugin's
  server), 4 (only authentication tools) and 5 (a BusinessIQ server declaration would have to be invented) hold.
  Per ADR-0037 §L item 1 and the prompt, M12-B was completed with an empty registry. No Gate record, no
  `.mcp.json` entry and no agent were created. HubSpot was not authenticated.

### Suites

Baseline (clean tree, before any change):

```
Ran 4555 tests in 753.654s
OK (skipped=26)
ran 4555 | failures 0 | errors 0 | skipped 26
```

Focused suites (final):

```
unit.test_m12b_connector_registry       ran 50 | failures 0 | errors 0 | skipped 0
negative.test_m12b_connector_security   ran 65 | failures 0 | errors 0 | skipped 0
```

The first runs of the focused suites failed, 1 + 17 and 6 + 1. Everything was fixed before the final run:

- `thaw()` did not recurse into plain lists, which broke the argument-shape comparison;
- one tool-name test value was in fact a legal name;
- two tests misused the fixture's `grant=None` default;
- the mutating-verb scan matched the constant `AMBIGUOUS_CONNECTOR`;
- the command result carries `started_at` and `calculated_at` wall-clock stamps, so the optionality comparison
  now excludes them;
- a skill-count assertion assumed 20, but 16 skill directories exist; it was replaced by the real invariant,
  "no connector-named skill, command or agent";
- the source scan read docstrings, so it is now an AST scan of code only.

Two engine defects were found and fixed:

- `object_types` items, dropped-key notes and limitations **were not refused at synthesis re-entry**; now they
  are;
- the long base64-run secret screen dropped a legitimate 43-character snake_case identifier. It now flags only
  mixed-case, digit-bearing runs, and payment-key prefixes are matched explicitly.

Final full suite: see §17.

- **`claude plugin validate . --strict`:** `✔ Validation passed`.
- **`git diff --check`:** exit 0. Every changed and new file is LF-only with no trailing whitespace, matching
  `HEAD`. Git prints only `core.autocrlf` notices.
- **Secret scan** (added diff lines plus untracked files):
  - 0 AWS, Slack, `sk-`, HubSpot PAT, full-JWT, private-key, bearer or connection-string values.
  - Emails and URLs found are on reserved domains (`example.com`, `.invalid`), the public HubSpot endpoint
    already in the repository, and schema ids.
  - Two assignment hits and two token-shaped strings are synthetic test canaries. Two strings copied real
    providers' documented example formats (`AKIA…EXAMPLE`, `ghp_…`) and were replaced by obviously synthetic
    shapes.
- **Immutability:** ADR-0004, ADR-0037, ADR-0038, `CLAUDE.md` and `.mcp.json` are unchanged (§17).

## 10. Issues discovered

- **No admissible connector exists** (§9). This is expected, and it does not block M12-B.
- **Pre-existing tests left untouched.** `test_m11_verification_server`, `test_m11_data_profiler` and
  `test_research_scout_boundary` pin `.mcp.json` = `biq-verifier` and the agent set. ADR-0037 says they are
  retargeted when a connector is admitted. With an empty registry they are exactly right, so they were not
  modified. The new registry-derived tests assert the general rule beside them
  (`.mcp.json` = `biq-verifier` + registered servers; agent ⇔ complete chain).
- **Conservative value screen.** It will drop some genuine metadata: an identifier embedding a run of 6 or more
  digits, such as a vendor property named after a pipeline-stage id, or a label containing a date. That is the
  fail-closed direction. It becomes relevant only when a real connector is gated, and should be measured at that
  Gate.
- **Residual risks restated from ADR-0037.**
  - A value hidden inside an allowed free-text label cannot always be detected by shape; it is local-only and
    non-evidential.
  - The main thread's control over another plugin's tools is advisory.
  - Platform-injected server instructions (C-4) are outside BusinessIQ's control. They are observed this session
    for other plugins' servers, never used.
- `docs/README.md`'s development-history list stops at M7 (pre-existing), so this record is not added there,
  consistent with the recent records.
- D-11 is unchanged and unrelated.

## 11. Decisions made

No ADR. Every choice in §3's table is an ADR-0037 "implementation contract item" or follows directly from its
text, and none is hard to reverse. The one judgement call is that a write or administrative request is refused as
`request_invalid` with a distinct fixed sentence. That keeps the §H set closed at 19, as the prompt requires.
The owner may prefer an ADR note on it.

## 12. Architecture changes

`architecture.md`:

- §4: the ingestion row names the registry and the empty-registry named absence;
- §10: the agent is still unbuilt after M12-B, under §D.1;
- §11: the M12-B implementation table and the empty registry;
- §13: `connectors/` and the `connector` schema;
- §16: the MCP-unavailable row names the 19 codes;
- §18: the connector extension row names the Gate block and `admission_findings()`.

No accepted ADR was edited.

## 13. Project-plan updates

- Milestone 12: `PLANNED` → `IN PROGRESS`.
- M12-B: `PLANNED` → `REVIEW`, with a new subsection mapping each §L item to its status.
- M12-C: `BLOCKED`, unchanged.

## 14. Documentation updates

- `CONNECTORS.md`: the status note says M12-B is implemented and the registry is empty; the named-absence row
  matches the runtime text; the admission rule is enforced by the static suite.
- `architecture.md` and `project_plan.md`: as §12 and §13.
- `docs/integrations/README.md`: the stale "Empty until Milestone 11" line is replaced. There are no integration
  pages because no connector is admitted.
- `docs/decisions/README.md` and `docs/README.md` were inspected and not changed, because there is no new ADR.

## 15. Remaining work

- Owner review of this implementation, then a separate Git checkpoint on instruction.
- A future Connector Gate for a BusinessIQ-declared server with a demonstrably value-free discovery tool, on a
  vendor sandbox with synthetic data. Only that admits a connector, builds the agent, and brings the §L item 5 live
  run and the runtime §J halves into scope.
- M12-C stays `BLOCKED` on P-1 to P-5 and its own ADR.

## 16. Git commit reference

N/A. Nothing committed or pushed. The change set is left uncommitted in the working tree for review.

## 17. Final validation

Run on the finished tree after every code, test and documentation edit except this section, which adds prose
only.

```
Ran 4670 tests in 231.073s
OK (skipped=26)
ran 4670 | failures 0 | errors 0 | skipped 26
```

- **Totals:** 4,555 baseline + 115 new = 4,670. 0 failures, 0 errors. The skip count is unchanged at 26, and no
  new test skips. An intermediate full run (before the final test-string, private-rename and documentation edits)
  gave the same 4,670 / 0 / 0 / 26.
- **`claude plugin validate . --strict`:** exit 0, `✔ Validation passed`. As in M11, this is not evidence for any
  agent or MCP boundary.
- **`git diff --check`:** exit 0.
- **Immutability** (`git rev-parse HEAD:<f>` against `git hash-object <f>`): byte-identical for:
  - ADR-0004 (`e51c0ed`), ADR-0037 (`42f3f28`) and ADR-0038 (`b8805c9`);
  - `CLAUDE.md` (`5b48ca0`), `.mcp.json` (`d68bc36`) and `.claude-plugin/plugin.json` (`7e1a476`);
  - the M12-A.1 development record (`114e4af`).
- **Scope:**
  - Modified: `CONNECTORS.md`, `architecture.md`, `docs/integrations/README.md`, `synthesis_set.py`,
    `project_plan.md` and `skills/biq-data-ingestion/SKILL.md`. Everything else in the change set is new.
  - No change under `agents/`, `commands/`, `reference/`, `config/`, `evals/`, `assets/` or `.claude-plugin/`, or
    to any existing test.
  - No `.businessiq/` directory was left in the repository by the tests.
- **No tool was called, no connector was authenticated, nothing was committed or pushed.**

## 18. Review remediation — failure semantics, value-free boundary, coverage accuracy (2026-09-18)

**Status after this pass:** `REVIEW — SECURITY/ARCHITECTURE REVIEW`. Owner approval pending; not committed. Sections
1–17 above are the first implementation pass, kept as history. Where this section corrects them, this section
governs.

Scope: a review against ADR-0037, ADR-0038, the M12-B scope and the actual code and tests, correcting only genuine
issues in three areas: failure semantics, the value-free boundary, and claims about what is proven. No accepted ADR
needed to change, and none was edited. No connector, agent, Gate record, `.mcp.json` entry or authentication was
added or performed.

### 18.1 Baseline

`HEAD` = `0425af28c305919ddb4114e20f73412957be6648`, with the M12-B change set uncommitted. Full suite before any
remediation edit: `Ran 4670 tests … OK (skipped=26)` — 4,670 / 0 / 0 / 26, identical to §17.

### 18.2 Failure semantics — conclusion: `request_invalid` for write and administrative is correct

This applies the existing §H semantics. It is not a new failure category.

| Operation requested | Code | Why this code, and not another of the 19 |
|---|---|---|
| Record read (`read`) | `blocked_prerequisite` | §H names exactly this situation: "any record-read request while M12-C is `BLOCKED`". ADR-0038 state 7 maps record reads here |
| Write (`write`) | `request_invalid` | ADR-0038 state 7 separates write and administrative ("refusal with no approval offered") from record reads. `blocked_prerequisite` would imply a prerequisite could unblock a write, and none can (ADR-0037 §G, §K). `capability_unsupported` presupposes a registered connector. The request asks for something outside what an M12-B request may ask for, which is §H's `request_invalid`, "refused whole before any dispatch" |
| Administrative (`administrative`) | `request_invalid` | As for write. Authentication is the user's, through the platform (ADR-0038 §6) |
| Unknown or unsupported operation class (`delete`, `execute`, `export`, `authenticate`, …) | `request_invalid` | A non-closed value (§H), refused at shape validation before evaluation, so no lifecycle state is reached (ADR-0038 §4) |

**One change was made.** Before this pass, a write or administrative refusal was distinguishable from a forged
request only by its prose. The interaction class is now carried as the limitation subject
(`{"code": "request_invalid", "subject": "write"}`), and a record read carries `"read"`. This gives a
machine-readable distinction within the existing closed code set. The subject is always one of the four closed class
names, never caller text. An unknown class carries no subject.

**Order is unchanged and correct.** Shape validation runs first (ADR-0038 §4: `request_invalid` refuses a malformed
request before evaluation). The interaction class is decided next, before any connector identity (ADR-0038 §5), so a
`read` naming `hubspot` is `blocked_prerequisite`.

**No dispatcher.** There is no function that takes a tool name, server, namespace or free arguments. A brief's tool
and arguments derive only from the registry declaration. The four operation classes admit exactly one executable
path (`discovery`), and that path exists only on a complete chain. Tests assert all of this.

### 18.3 The 19 codes — claim versus actual coverage

The first report said every code was "produced by its real situation in a test". **That overstated.** It is
corrected here. Every code below is defined in `contract.py`, in the schema enum and in `MESSAGES`, and every code
is required by ADR-0037 §H.

| Code | Reachable with the shipped (empty) registry | Tested | Kind of evidence |
|---|---|---|---|
| `connector_not_configured` | **Yes** | Yes | Deterministic, shipped registry |
| `request_invalid` | **Yes** | Yes | Deterministic, shipped registry and synthetic |
| `privacy_restricted` | **Yes** (request side) | Yes | Request side: deterministic, shipped and synthetic. Reply side: synthetic only |
| `blocked_prerequisite` | **Yes** | Yes | Deterministic, shipped registry |
| `operation_unknown` | **Yes** | Yes | Deterministic, shipped (nothing is ever sealed) and synthetic replay |
| `ambiguous_connector` | No — needs two registered connectors | Yes | Synthetic fixture only |
| `capability_unsupported` | No — needs a registered connector | Yes | Synthetic fixture only |
| `binding_mismatch` | No — needs a registered connector | Yes | Deterministic layer checks over synthetic layers |
| `malformed_response` | No — needs a sealed operation | Yes | Synthetic fixture only (parser is deterministic) |
| `metadata_conflict` | No | Yes | Synthetic fixture only |
| `external_content_unavailable` | No | Yes | Synthetic fixture only |
| `insufficient_data` | No | Yes | Synthetic fixture only |
| `timeout` | No | Yes | Synthetic (`reply=None`, and a test-written relay line). **Runtime-unverified** |
| `connector_unavailable` | No | Yes | Test-written relay line only. **Runtime-unverified** |
| `connector_not_authorized` | No | Yes | Test-written relay line only. **Runtime-unverified** |
| `authentication_failure` | No | Yes | Test-written relay line only. **Runtime-unverified** |
| `authorization_failure` | No | Yes | Test-written relay line only. **Runtime-unverified** |
| `tool_failure` | No | Yes | Test-written relay line only. **Runtime-unverified** |
| `stale_metadata` | No | Yes | Test-written relay line only. **Runtime-unverified** |

Summary:

- **Implemented:** 19 of 19.
- **Deterministically produced by the engine:** 19 of 19.
- **Reachable in the shipped state:** 5.
- **Synthetic-only:** 14.
- **Runtime-verified:** 0.

The 7 relayed codes are **future and runtime coverage**. What the connector agent would actually relay, and whether a
real vendor's failures map onto them, can only be observed once a connector is admitted and the agent is built.
No fake agent, connector or runtime evidence was created to fill this gap.

A new test (`ShippedReachability`) pins the shipped state. Over every placeholder and operation class, plus forged,
unregistered and value-requesting requests, and closes with any operation, exactly those 5 codes occur, and no brief
is ever sealed.

### 18.4 Value-free boundary — conclusion: structural boundary confirmed; the screen is defence in depth

The primary boundary is, in order:

1. the exact registered capability;
2. an owner-approved Connector Gate record demonstrating value-free output;
3. exact identity binding across the registry, Gate record, `.mcp.json` and grant, checked at seal **and** re-checked
   at close;
4. the declaration's closed output allowlist;
5. the closed data-type vocabulary and the JSON-boolean `required`;
6. the closed result schema;
7. fail-closed structural validation.

The value-shape screen runs only after all of that has admitted the operation. It is a heuristic second line.

Confirmed by reading the code and tests:

- **An unapproved response is never trusted because it looks clean.** No brief exists without a complete chain, so a
  well-formed, screen-clean reply for an unsealed operation is `operation_unknown`. A chain broken between seal and
  close is `binding_mismatch`. A Gate record without a demonstrated value-free property is `binding_mismatch`. New
  tests cover each case.
- **No arbitrary field enters.** Keys outside the declaration's allowlist are dropped and noted by name. The entry
  shape is fixed at eight keys. A new test shows a vendor type name carrying text maps to `unknown`, and that extra
  `value` and `count` keys never surface.
- **No permissive fallback.** Raw `data_type` text never passes. It is either mapped or `unknown`.
- **No vendor error text.** Relay outcomes are single tokens. Prose around the lines is ignored, and every message is
  fixed text.
- **No credentials or tokens** can cross, by allowlist first and screen second.
- **No counts or aggregates.** Reply-side counts are dropped keys. The terminator's count is protocol-only and never
  enters the result. `conflicts[].variants` counts metadata variants, never records.

**Corrected wording.** The comment above the screen in `contract.py` now states that the screen is defence in depth,
not the boundary; that it cannot recognise every value (a plain name in a free-text label passes it — ADR-0037's
stated residual risk, now pinned by a test); and that it has not been measured against any real vendor response. The
screen itself is unchanged: nothing was weakened, and no identifier format was broadened.

### 18.5 Catalogue protocol review — two gaps closed

Each of these was confirmed by an existing test:

- malformed response;
- wrong connector echo and wrong tool echo;
- a tampered sealed brief;
- replay;
- declared-count mismatch;
- missing or duplicated terminator;
- extra fields not trusted;
- no record values or vendor error text surviving.

Two structural ambiguities were being silently repaired, contrary to ADR-0017's "nothing is repaired". Both are
fixed in `catalogue.py`:

1. **A repeated key inside one record line** (`{"object": "contacts", "object": "users"}`) was resolved to the
   last value by `json.loads`. Record lines are now parsed with a duplicate-key hook, and `NaN` / `Infinity` are
   refused. Either makes the line a `malformed_response`.
2. **A repeated entry** (the same line twice, or two lines identical after normalisation) was silently collapsed.
   It is now a `malformed_response`.

**Differing variants of one identifier** are still kept and flagged as `metadata_conflict` with status
`complete_with_limitations`. That is the accepted ADR-0037 §H behaviour, not a defect, and a test pins it.

The first pass's determinism test asserted the collapse. It was corrected to assert order-invariance only, and a
separate test asserts that a repeated record is refused.

### 18.6 What is proven now, and what is not

| Proven now, by deterministic tests | Not proven now |
|---|---|
| Registry exactness and immutability | Any real vendor discovery response |
| Empty-registry behaviour: 5 reachable codes, nothing sealed | Real HubSpot discovery |
| The static OD-3 admission rule and the §D.1 build rule | A real BusinessIQ HubSpot connection (none can exist) |
| Exact identity and layer-binding checks | A real Connector Gate measurement for any business-system connector — **none was taken**. §9's "Connector Gate measurement" was an inspection of the session's tool surface, which found no candidate to measure |
| Evaluation order and operation-class mapping | Real connector-agent behaviour: grant enforcement, relay, first-delivery parse (ADR-0037 §J runtime halves, §L item 5) |
| Fail-closed parsing and deterministic results | That the 7 relayed codes match anything a real agent or vendor emits |
| Value-free enforcement **against a synthetic enforcement fixture** | That the value-shape screen's thresholds suit any real vendor's metadata |
| No dispatcher, no authentication, no write, no administration path | M12-C record reads — `BLOCKED` |
| Synthesis refusal of connector material and class 2; file-workflow independence | |

### 18.7 Documentation corrected

| File | Correction |
|---|---|
| `lib/python/biq/connectors/registry.py` | The docstring no longer says "the M12-B Connector Gate found…": no candidate existed, and no Gate measurement was taken |
| `lib/python/biq/connectors/contract.py` | The screen is labelled defence in depth, with its limits (§18.4) |
| `CONNECTORS.md` | The status note: in security and architecture review; empty by design; no Gate measurement; what is proven; no real discovery has run |
| `architecture.md` §11 | The `contract.py` and `registry.py` rows. Three paragraphs are added: operation-class semantics, the structural value-free boundary, and what is and is not proven |
| `project_plan.md` | M12-B status `REVIEW — SECURITY/ARCHITECTURE REVIEW`. §L item 1 is "not applicable - no candidate" (it previously read `COMPLETED`). §L item 4 states the 5 / 14 / 0 coverage split. §L item 8 records this pass. The prose states that runtime discovery is unverified |
| `tests/connector_fixtures.py` | Labelled "Synthetic enforcement fixture only - non-production" |
| `test_m12b_connector_registry.py` | The failure-model test is renamed `…produced_deterministically_by_the_engine`, with a docstring stating which codes are shipped-state, synthetic and relay-written |

### 18.8 Status confirmations

- **No connector is admitted.** `_DECLARATIONS = ()`. The empty registry is intentional.
- **HubSpot remains a designated optional future connector**, in lifecycle state 1. It is not registered, declared,
  measured, connected or usable.
- **M12-C remains `BLOCKED`** on P-1 to P-5 and its own ADR. Every record-read request is `blocked_prerequisite`.
- ADR-0004, ADR-0037, ADR-0038, `CLAUDE.md` and `.mcp.json` are unchanged.

### 18.9 Validation (this pass)

Run on the finished tree after every edit in this pass except this subsection, which adds prose only.

```
unit.test_m12b_connector_registry       ran 51 | failures 0 | errors 0 | skipped 0
negative.test_m12b_connector_security   ran 78 | failures 0 | errors 0 | skipped 0
Ran 4684 tests in 246.034s
OK (skipped=26)
ran 4684 | failures 0 | errors 0 | skipped 26
```

- **Totals:** 4,670 before this pass + 14 new tests = 4,684. 0 failures, 0 errors. Skips unchanged at 26.
- **The 14 new tests:**
  - 13 in the security suite: operation-class semantics (4), shipped-state reachability (2), structural ambiguity
    (4) and screen-is-not-the-boundary (3);
  - 1 in the unit suite: a repeated record is refused.
  - One unit test was corrected in place (determinism: order only) and one was renamed (the failure model).
- **`claude plugin validate . --strict`:** exit 0, `✔ Validation passed`.
- **`git diff --check`:** exit 0. Every changed file is LF-only.
- **Secret scan** (added diff lines plus untracked files):
  - 0 AWS, GitHub, Slack, `sk-`, HubSpot PAT, full-JWT, private-key, bearer or connection-string values.
  - The only hits are the known synthetic test canaries: two assignment-shaped canaries, and emails on the reserved
    `example.com` and `.invalid` domains.
- **Immutability:** ADR-0004, ADR-0037, ADR-0038, `CLAUDE.md`, `.mcp.json` and `.claude-plugin/plugin.json` are
  byte-identical to `HEAD`.
- **Scope:**
  - `agents/` still holds only `biq-analysis-verifier` and `biq-research-scout`.
  - No `.businessiq/` directory was left in the repository.
  - Code changes in this pass are confined to `connectors/catalogue.py`, plus comments and docstrings in
    `contract.py` and `registry.py`.
- **Nothing was committed, pushed or amended.** No tool was called and no connector was authenticated.
