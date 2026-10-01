# Architecture Decision Records

## The bar

Write an ADR when a decision is **significant and hard to reverse**. Concretely, when it
meets at least one of:

- It constrains future work (choosing a platform, an execution model, a data contract).
- It would be expensive to undo once code depends on it.
- It rejects an option a reasonable reviewer would have expected us to take.
- It changes a load-bearing invariant — the evidence model, the permission model, the
  internal/external boundary, or the agent topology.
- Someone six months from now would otherwise ask "why on earth is it like this?"

**Do not write an ADR for:** renaming a file, adding a KPI, adding a quality check, adding
a connector, wording changes, bug fixes, or anything the architecture already anticipates as
a registration-only extension point.

Registration-only extensions are listed in `architecture.md` (Extension Points). If a change
appears there with "Touches core? No", it needs no ADR.

## Conventions

- Filename: `ADR-NNNN-<kebab-slug>.md`, zero-padded to four digits, allocated sequentially.
- Numbers are never reused, even if an ADR is later rejected.
- ADRs are **immutable once accepted**. To change a decision, write a new ADR and set the
  old one's status to `Superseded by ADR-NNNN`. Never rewrite history.
- Every accepted ADR is listed in `architecture.md` (Major architectural decisions) and in
  `docs/README.md`.
- Template: [`../templates/adr.md`](../templates/adr.md).

## Index

| ID | Title | Date | Status |
|---|---|---|---|
| [0001](ADR-0001-claude-code-plugin-platform.md) | Claude Code plugin as the delivery platform | 2026-09-08 | Accepted |
| [0002](ADR-0002-deterministic-compute-engine.md) | Deterministic stdlib-only compute engine | 2026-09-08 | Accepted |
| [0003](ADR-0003-commands-orchestrate-skills-hold-logic.md) | Commands orchestrate, skills hold logic | 2026-09-08 | Accepted |
| [0004](ADR-0004-capability-based-connector-abstraction.md) | Capability-based connector abstraction | 2026-09-08 | Accepted — runtime-discovery and "user-configurable" clauses superseded in part by 0037 (OD-2 accepted 2026-09-17) |
| [0005](ADR-0005-seven-class-evidence-ledger.md) | Seven-class evidence ledger | 2026-09-08 | Accepted |
| [0006](ADR-0006-three-subagents-not-eight.md) | Three subagents, not eight | 2026-09-08 | Accepted |
| [0007](ADR-0007-two-layer-testing-strategy.md) | Two-layer testing strategy | 2026-09-08 | Accepted |
| [0008](ADR-0008-tiered-xlsx-ingestion.md) | Tiered `.xlsx` ingestion with a managed dependency | 2026-09-08 | Accepted |
| [0009](ADR-0009-comparative-intelligence-privacy-boundary.md) | Comparative intelligence and the privacy boundary | 2026-09-08 | Accepted |
| [0010](ADR-0010-consequence-based-approval-model.md) | Consequence-based approval model | 2026-09-08 | Accepted |
| [0011](ADR-0011-business-context-first-class.md) | Business Context as a first-class component | 2026-09-08 | Accepted |
| [0012](ADR-0012-component-placement-rule.md) | Component placement: where each rule lives | 2026-09-08 | Accepted |
| [0013](ADR-0013-token-budget-is-self-imposed.md) | Token budget is self-imposed | 2026-09-08 | Accepted |
| [0014](ADR-0014-retrieval-agent-ships-with-retrieval.md) | The retrieval agent ships with the first milestone that retrieves | 2026-09-10 | Accepted |
| [0015](ADR-0015-model-mediated-scout-dispatch.md) | Scout dispatch is model-mediated; the orchestration surface is markdown | 2026-09-10 | Accepted |
| [0016](ADR-0016-declared-conflicts-outrank-numeric-agreement.md) | Declared conflicts outrank numeric agreement | 2026-09-11 | Accepted |
| [0017](ADR-0017-operation-bound-line-records.md) | The scout returns operation-bound line records, not an envelope | 2026-09-13 | Accepted *(index entry added 2026-09-27, M14-1)* |
| [0018](ADR-0018-first-party-company-source-registry.md) | First-party company sources are tier B, by explicit registry | 2026-09-13 | Accepted *(index entry added 2026-09-27, M14-1)* |
| [0019](ADR-0019-market-research-intents.md) | Two research intents added for market analysis | 2026-09-13 | Accepted |
| [0020](ADR-0020-competitor-research-intents.md) | Two research intents added for competitor analysis, and two reused | 2026-09-14 | Accepted |
| [0021](ADR-0021-research-intent-registry.md) | One immutable research-intent registry replaces the flat intent tables | 2026-09-14 | Accepted |
| [0022](ADR-0022-cross-domain-synthesis-contract.md) | One synthesis contract, built from existing vocabularies, that promotes nothing | 2026-09-14 | Accepted |
| [0023](ADR-0023-internal-statements-need-internal-footing.md) | An internal statement is defined by its provenance, not by its declared origin | 2026-09-15 | Accepted *(index entry added 2026-09-27, M14-1)* |
| [0024](ADR-0024-retrieval-to-synthesis-object-seam.md) | One retrieval assembly, two closers: the `EvidenceSet` reaches synthesis as an object | 2026-09-15 | Accepted *(index entry added 2026-09-27, M14-1)* |
| [0025](ADR-0025-unit-is-a-quantity-type.md) | `unit` is a quantity type; scale is normalised into the value, never carried as a label | 2026-09-15 | Accepted |
| [0026](ADR-0026-dimension-provenance-and-source-context-admissibility.md) | A dimension is admissible for compatibility only where its provenance says a source stated it | 2026-09-15 | Accepted |
| [0027](ADR-0027-external-source-context-extraction.md) | Source context travels inside the evidence record; the protocol does not change | 2026-09-15 | Accepted |
| [0028](ADR-0028-command-path-footing-is-strict.md) | The research command's footing path is one seam, and it is strict by construction | 2026-09-15 | Accepted |
| [0029](ADR-0029-the-local-join-surface.md) | The local join is a surface of its own, and it sequences only | 2026-09-16 | Accepted |
| [0030](ADR-0030-a-swot-point-is-a-placement.md) | A SWOT point is a placement of a synthesis statement, never new text | 2026-09-16 | Accepted |
| [0031](ADR-0031-strategy-recommendation-contract.md) | The strategy recommendation contract: a class-7 claim resolved against a synthesis set, held beside it | 2026-09-16 | Accepted |
| [0032](ADR-0032-decision-support-contract.md) | The Decision Support contract: a twelve-part draft decision package beside the synthesis set | 2026-09-16 | Accepted |
| [0033](ADR-0033-executive-report-contract.md) | The Executive Report contract: an assembly of existing artifacts over one synthesis set, authoring nothing | 2026-09-16 | Accepted |
| [0034](ADR-0034-m11-verification-and-finalisation-contract.md) | The M11 verification and finalisation contract: deterministic integrity checks, blind recomputation, and a final lifecycle recorded beside an unedited draft | 2026-09-17 | Accepted — partially superseded by 0035 |
| [0035](ADR-0035-m11-blind-recomputation-boundary.md) | The M11 blind-recomputation boundary: an opaque request, one fixed operation, digests not values, and no shell for the verifier agent | 2026-09-17 | Accepted |
| [0036](ADR-0036-biq-data-profiler-contract.md) | The data profiler contract: a deterministic, value-free assembly of what the Data Layer already knows, bound to its sources, with the subagent deferred until a model must browse | 2026-09-17 | Accepted |
| [0037](ADR-0037-m12-connector-layer-contract.md) | The M12 connector layer contract: a registry-bound, read-only connector catalogue, discovery separated from data, and connected-system reads blocked until no model context holds a value | 2026-09-17 | Accepted — supersedes in part 0004 (runtime-discovery and "user-configurable" clauses only) |
| [0038](ADR-0038-optional-connector-connection-lifecycle.md) | Optional connectors and the user-initiated connection lifecycle: supported, connected, authorized, verified and available are five different facts | 2026-09-18 | Accepted — clarifies 0037 (supersedes and amends nothing); OD-3 resolved 2026-09-18 |
| [0039](ADR-0039-m13-test-hardening-and-evals-contract.md) | The M13 test hardening and evals contract: a closed coverage matrix, deterministic gap closure, recorded measurement, and a behavioural eval suite under an explicit execution policy | 2026-09-18 | Accepted — 2026-09-18, with owner clarifications; applies 0007 without editing it |
| [0040](ADR-0040-m13-owner-accepted-environment-gap.md) | An owner-accepted environment-unavailable gap in the M13 coverage matrix: a recorded gap, never a defect and never coverage | 2026-09-18 | Accepted — amends 0039 in part (§B `gap` definition and §L's second M13.1 condition only) |
| [0041](ADR-0041-m13-2-deterministic-repository-owned-eval-fixtures.md) | Deterministic, repository-owned input fixtures for the M13.2 eval cases: committed, builder-reproduced, bound to their cases, and inputs only | 2026-09-19 | Accepted — amends 0039 in part (§E.2's last sentence and §E.5's second assertion only); resolves G-1 only |
| [0042](ADR-0042-plugin-root-anchored-isolated-engine-entry.md) | The engine is entered through one plugin-root-anchored, isolated launcher (`python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py" -c …`), located by `${CLAUDE_PLUGIN_ROOT}` substitution in command and skill bodies | 2026-09-19 | Accepted — the remediation architecture for M13-DEF-04. **Implemented 2026-09-20** (`lib/python/biq_run.py`, 10 commands, 16 skills), verified by T-A to T-K and the full regression, and not yet committed. Amends none. G-3/V-3, V-4 and Unix-like runtime verification stay open |
| [0044](ADR-0044-platform-format-eval-cases.md) | The eval case file is written in the platform's own case format, and carries the BusinessIQ semantic record beside it in the same file | 2026-09-22 | **Accepted** — the migration architecture for M13-DEF-05, staged in three parts. **Phase 1 and Stage 3 both implemented 2026-09-22**: 64 cases dual-layered and **all 133 graders mapped** (0 pending, 0 dropped), **64 of 64 cases platform-loadable**. Stage 3 was completed from the observed trace of the owner-authorised three-run pilot, which showed a command firing under the `Skill` tool as `businessiq:<command>`. Amends none |
| [0043](ADR-0043-defect-status-for-verified-product-fixes.md) | Defect register status vocabulary for verified product fixes: adds `fixed_product` (product only; fixed and verified by a dedicated milestone outside M13) | 2026-09-20 | Accepted — amends 0039 in part (§G.1 `status` vocabulary and its closing sentence only); M13 boundary (I-1, I-13) unchanged |
| [0045](ADR-0045-businessiq-owned-portable-runtime-resolution.md) | A BusinessIQ-owned runtime resolver (`lib/biq_run.sh`) chooses the Python interpreter, so no command or skill names one: every engine block is `sh "${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh" -c …` | 2026-09-22 | **Accepted** — the remediation architecture for M13-DEF-08, and **implemented the same day** (`lib/biq_run.sh`, 26 files, 34 blocks, 66 tests). Amends 0042 in part (the written form of the invocation and the tool grant it implies only); ADR-0042's launcher, import boundary and isolation are unchanged. Follow-up: the owner re-agrees the eval `--allow-tools` grant; Windows and macOS runtime verification not performed |
| [0046](ADR-0046-wsl-excludes-windows-interpreters-from-automatic-resolution.md) | Under WSL, automatic interpreter resolution excludes the Windows executable suffixes; the explicit `BIQ_PYTHON` override does not | 2026-09-23 | **Accepted** — the remediation architecture for M13-DEF-12, and **implemented the same day** (16 lines in `lib/biq_run.sh`, 15 tests, 3 mutations each caught). Amends 0045 in part (its *Interpreter discovery* rule 3 only); native Windows and native Linux behaviour, the override, the probe and the `-I` handoff are unchanged |
| [0047](ADR-0047-routing-graders-accept-the-owning-command-route.md) | A routing grader accepts the owning BusinessIQ command route as well as the skill route, the ownership derived from the engine command registry and each command's own declaration | 2026-09-25 | **Accepted** — the remediation for M13-DEF-17, **implemented the same day**. Amends 0044 in part (the `skill_invoked` / `skill_not_invoked` mapping only) |
| [0048](ADR-0048-declared-precondition-fixtures-for-eval-cases.md) | An eval case may declare one deterministic precondition fixture, staged at the path the case names; admitted for `a20` only | 2026-09-25 | **Accepted** — the remediation for M13-DEF-19, **implemented the same day**. Amends 0041 in part (§2 format, §5 binding and §8 assertions 9-10, for a declared precondition fixture only) |
| [0049](ADR-0049-semantic-judge-splits-are-execution-unavailable.md) | A run whose semantic LLM judge votes split is `execution_unavailable` — inconclusive automated evidence, never a pass or a fail; no majority rule, no pinned judge | 2026-09-25 | **Accepted** — the remediation for M13-DEF-23, **implemented the same day**. Amends 0039 in part (§E.6's class table only); not retroactive |
| [0050](ADR-0050-provenance-aware-research-boundary.md) | The disclosure gate establishes the provenance of every request fragment from the workspace's business data: a value from a non-public column never goes at Tier 0, a `never` value never goes at all, and an unscreenable workspace refuses | 2026-09-26 | **Accepted** — the remediation for M13-DEF-13, **implemented the same day**. Applies 0009 (classification is a property of the data); amends nothing |
| [0051](ADR-0051-pre-execution-write-approval-boundary.md) | A pre-execution write-approval boundary: a plugin-wide `PreToolUse` guard scoped by engagement, a deterministic allowlist write classifier, single-use capabilities bound to the exact operation and granted only from the user's prompt, and an engine execution guard | 2026-09-26 | **Accepted** — the remediation for M13-DEF-24, **implemented the same day**. Amends 0001 in part (its "`hooks/` is deferred" sentence only) and 0035 in part (Option B's hook reasoning, for the write boundary only; the verifier keeps no shell) |
| [0052](ADR-0052-verifier-server-launched-through-the-runtime-resolver.md) | The local verifier MCP server is launched through the runtime resolver: `.mcp.json` declares `sh "${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh" --verifier`, and the launcher gains an exact `--verifier` entry | 2026-09-27 | **Accepted** — amends 0035 §3 in part (the declared command and arguments only); fixes R-13 |
| [0053](ADR-0053-scout-reply-captured-by-the-harness.md) | The scout's reply reaches the engine through a harness capture, never a model copy: a `PostToolUse` hook stores `tool_response.content` byte for byte under the guard root, and `close_retrieval()` reads it with `R.handback_reply()` | 2026-09-27 | **Accepted**; amends 0017 and `architecture.md` §10 in part (the reply's carrier only); resolves M9 criterion 5 |
| [0054](ADR-0054-businessops-product-identity-and-bops-namespace.md) | BusinessOps product identity and the `bops` technical namespace: plugin `businessops`, prefix `bops`, rights holder Prakash Meghani - Concept Web World; historical records and pinned fixtures keep the BusinessIQ names | Accepted 2026-09-30 |
| [0055](ADR-0055-distribution-package-built-from-an-allowlist.md) | The installable package is built by `scripts/build_distribution.py` from an explicit allowlist, with the plugin root at the package root; tests, evals, history and developer tooling stay in the development repository | Accepted 2026-09-30; amended by ADR-0057 |
| [0056](ADR-0056-plugin-root-paths-for-shipped-reference-documents.md) | Commands and skills name the shipped `reference/` documents by their `${CLAUDE_PLUGIN_ROOT}` path, because relative paths do not resolve in an installed plugin (live-tested); amends ADR-0042's static guard by exactly that form | Accepted 2026-09-30 |
| [0057](ADR-0057-one-public-repository-for-source-and-package.md) | One public repository, `conceptwebworld26/BusinessOps`, holds the source and the committed package `dist/businessops/` (submitted as the plugin path); no separate distribution repository | Accepted 2026-10-01 |

**Amended / refined:** ADR-0002 amended in part by 0008 · ADR-0003 refined by 0012 · ADR-0042 amended in part by 0045 (the invocation's written form and its tool grant only) · ADR-0017 amended in part by 0053 (the reply's carrier only) · ADR-0035 amended in part by 0052 (the verifier's declared command and arguments only) · ADR-0045 amended in part by 0046 (Windows suffixes under WSL only) · ADR-0044 amended in part by 0047 (the skill-routing mapping only) · ADR-0041 amended in part by 0048 (declared precondition fixtures only) · ADR-0039 amended in part by 0049 (semantic judge splits only) · ADR-0001 amended in part by 0051 (the hooks deferral only) · ADR-0035 amended in part by 0051 (Option B's hook reasoning, for the write boundary only) ·
the blanket-rejection rule from Revision 1 superseded by 0009 · the original human-review
gate superseded by 0010 · the 4,000-token ceiling corrected by 0013 · ADR-0022 §5 (where recommendations are held)
refined by 0031 · ADR-0034's recomputation interface, verifier-agent grant and finding value representation
superseded in part by 0035 · ADR-0006's allocation of `biq-data-profiler` (a file-scanning subagent) refined by
0036: file profiling is deterministic engine work and the subagent is deferred to model-mediated sources. Original ADR text is preserved in every case; only status lines gained
amendment notes — except ADR-0022, whose status line was deliberately left unannotated by
M10.3.2-A, which was instructed to edit no accepted ADR. The refinement is recorded here and in
ADR-0031. ADR-0006's status line is likewise left unannotated; its refinement is recorded here and in ADR-0036.
ADR-0004's decision that `biq-connector-broker` "performs discovery" of "whatever server is connected", and that
categories are "user-configurable", is superseded in part by 0037 (exact registry-bound identity; OD-2 accepted
2026-09-17). ADR-0004's text and status line are left unedited; the relationship is recorded here, in ADR-0037
(*Relationship to ADR-0004*) and in `architecture.md` §19. ADR-0039's `gap` definition (§B) and its second M13.1
completion condition (§L) are amended in part by 0040, which admits an owner-accepted environment-unavailable gap.
ADR-0039 is accepted and immutable, so its text and status line are left unedited; the amendment is recorded here, in
ADR-0040 and in `architecture.md` §19. ADR-0039's §E.2 input rule (last sentence) and §E.5 input-path assertion
(second assertion) are amended in part by 0041, which admits committed, builder-reproduced eval input fixtures under
`tests/fixtures/eval_inputs/`. ADR-0039's text and status line are likewise left unedited; the amendment is recorded
here, in ADR-0041 and in `architecture.md` §19. ADR-0039's §G.1 defect `status` vocabulary is amended in part by
0043, which adds `fixed_product` for a product defect fixed and verified by a dedicated milestone outside M13; the
amendment is recorded here, in ADR-0043 and in `architecture.md` §19, and ADR-0039 is again left unedited.

---

## Milestone numbers in ADRs 0001-0009 are pre-Revision-2

Several ADRs name a milestone by number. **Those numbers were written before the
Revision-2 roadmap change**, which inserted the end-to-end vertical slice as Milestone 2 and
took the count from 13 to 14. Every milestone after M1 therefore shifted up by one, and the
ADR bodies were deliberately **not** rewritten - an ADR records what was decided at the
time, and editing its text to chase a renumbering would damage the record it exists to keep.

This has now been mistaken for a genuine ADR/plan conflict twice. The mapping is recorded
here once so it is not rediscovered a third time.

| ADR | Says | Means (current numbering) | Verified by |
|---|---|---|---|
| 0002 | "Milestone 2 must ship a runtime probe" | M1 - superseded on this point by ADR-0008, which correctly says Milestone 1 | Runtime resolver shipped in M1 |
| 0005 | "`claim_ledger` and `evidence_set` schemas land in Milestone 8" | **M9** | Those schemas are M9 tasks in `project_plan.md` |
| 0006 | "Milestone 10 includes a test asserting `biq-research-scout` has no file-access tools" | **M11** as written - **relocated to M9 by ADR-0014**, which binds the test to the component rather than to a number | The plan's M11 carried that exact sentence before ADR-0014 |
| 0009 | "sensitivity classification lands with ingestion (M2) and Business Context (M1)" | ingestion -> **M3**; Business Context -> M1 | `privacy/sensitivity.py` shipped in M3 |
| 0009 | "the gate and its ledger entries land with the research layer (M8)" | **M9** | The disclosure gate is an M9 task |

**Reading rule:** in ADRs 0001-0009, a milestone number greater than 1 refers to the
milestone now numbered one higher. ADR-0008 is the exception - it was written during the
review and already uses current numbering. ADRs 0010 onward use current numbering.

**When in doubt, match by content, not by number.** Every mapping above was confirmed by
finding the same deliverable in `project_plan.md`, not by applying the offset blindly.

ADR-0014 (2026-09-10) is why the 0006 row now differs: it moves the scout and its test to
M9 and establishes that a security test ships with the component whose property it proves,
so this particular drift cannot recur.
