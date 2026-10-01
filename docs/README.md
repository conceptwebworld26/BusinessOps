# BusinessOps Documentation

Index of project documentation. Start here.

## Which document owns what

Each document has exactly one responsibility. If information would fit in two places, it
belongs in one and is linked from the other.

| Document | Question it answers | Updated |
|---|---|---|
| [`../CLAUDE.md`](../CLAUDE.md) | How do I *develop* this project? | When process, conventions or rules change |
| [`../architecture.md`](../architecture.md) | What is the system, and why is it this way? | Whenever an approved architectural change lands |
| [`../project_plan.md`](../project_plan.md) | What is done, in flight, blocked, or next? | Every task |
| [`../README.md`](../README.md) | How do I install and use BusinessOps? | When user-facing behaviour changes |
| `docs/` | Everything long-form, historical or per-component | Continuously |
| [`../reference/`](../reference/) | Policy documents the plugin itself reads at runtime | With the architecture |

## Directory map

| Directory | Contents | Convention |
|---|---|---|
| [`development/`](development/) | Date-wise development history — one record per milestone | `YYYY-MM-DD-<slug>.md`, **append-only** |
| [`decisions/`](decisions/) | Architecture Decision Records | `ADR-NNNN-<slug>.md` — see [the bar](decisions/README.md) |
| [`architecture/`](architecture/) | Deep dives too long for `architecture.md` | One topic per file |
| [`testing/`](testing/) | Test plan, coverage matrix, recorded results | |
| [`integrations/`](integrations/) | Per-connector setup, capabilities, limitations | One file per connector |
| [`skills/`](skills/) | Skill index, with the design-to-shipped mapping (D-13) | `README.md`; each skill's detailed reference is its own `skills/<name>/SKILL.md` |
| [`commands/`](commands/) | Command index and command reference pages | `README.md`; one page per command family, or `<command-name>.md` for a single-command family |
| [`agents/`](agents/) | Reference page per subagent | `bops-<name>.md` |
| [`examples/`](examples/) | Worked end-to-end walkthroughs on demo data | |
| [`troubleshooting/`](troubleshooting/) | Symptom → cause → fix | |
| [`releases/`](releases/) | Release notes, one page per version | `<version>.md`; [0.1.0](releases/0.1.0.md) is a release candidate until published |
| [`templates/`](templates/) | Templates for the three recurring artifacts | Do not edit ad hoc |

## Component reference

The current inventory is 18 user-facing commands, 1 internal test harness, 16 skills and 2 subagents
(verified 2026-09-27, M14-3).

- [Command Reference](commands/README.md): the command index, with reference pages for
  [internal analytics](commands/internal-analytics.md),
  [forecasting and anomalies](commands/forecasting-and-anomalies.md),
  [external research](commands/external-research.md),
  [`/benchmark-comparison`](commands/benchmark-comparison.md) and
  [synthesis and reporting](commands/synthesis-and-reporting.md).
- [Skill Reference](skills/README.md): shipped skills, designed-but-not-shipped skills, and the D-13 mapping.
- [Agent Reference](agents/README.md): [`bops-research-scout`](agents/bops-research-scout.md) and
  [`bops-analysis-verifier`](agents/bops-analysis-verifier.md).

## Templates

| Template | Used for |
|---|---|
| [`templates/task-report.md`](templates/task-report.md) | The 15-section report ending every implementation task |
| [`templates/dev-record.md`](templates/dev-record.md) | The dated development record in `development/` |
| [`templates/adr.md`](templates/adr.md) | A new architecture decision record |

## Development history

Records are append-only. A record is never edited to reflect later understanding; a newer
record supersedes it and says so. Reading `development/` in date order should let someone
unfamiliar with the project understand how BusinessOps evolved and why.

- [2026-09-08 — Milestone 0: Architecture Gate](development/2026-09-08-milestone-0-architecture-gate.md)
- [2026-09-08 — Architecture Review Corrections (Revision 2)](development/2026-09-08-architecture-review-corrections.md)
- [2026-09-08 — Milestone 1: Foundation](development/2026-09-08-foundation.md)
- [2026-09-08 — Milestone 2: Vertical Slice](development/2026-09-08-vertical-slice.md)
- [2026-09-08 — Milestone 3: Data Layer](development/2026-09-08-data-layer.md)
- [2026-09-08 — Milestone 4: Data Quality](development/2026-09-08-data-quality.md)
- [2026-09-08 — Milestone 5: KPI Engine](development/2026-09-08-kpi-engine.md)
- [2026-09-08 — Milestone 6: Internal Analytics Skills](development/2026-09-08-internal-analytics.md)
- [2026-09-09 — Milestone 7: Internal Analytics Commands](development/2026-09-09-internal-analytics-commands.md)

Records from Milestone 8 onward are not listed individually here: `development/` is the complete, date-ordered
index, and `project_plan.md` owns each milestone's status. *(Noted 2026-09-27, M14-1; D-14.)*

## Decisions

- [ADR-0001 — Claude Code plugin as the delivery platform](decisions/ADR-0001-claude-code-plugin-platform.md)
- [ADR-0002 — Deterministic stdlib-only compute engine](decisions/ADR-0002-deterministic-compute-engine.md)
- [ADR-0003 — Commands orchestrate, skills hold logic](decisions/ADR-0003-commands-orchestrate-skills-hold-logic.md)
- [ADR-0004 — Capability-based connector abstraction](decisions/ADR-0004-capability-based-connector-abstraction.md)
- [ADR-0005 — Seven-class evidence ledger](decisions/ADR-0005-seven-class-evidence-ledger.md)
- [ADR-0006 — Three subagents, not eight](decisions/ADR-0006-three-subagents-not-eight.md)
- [ADR-0007 — Two-layer testing strategy](decisions/ADR-0007-two-layer-testing-strategy.md)
- [ADR-0008 — Tiered `.xlsx` ingestion](decisions/ADR-0008-tiered-xlsx-ingestion.md)
- [ADR-0009 — Comparative intelligence and the privacy boundary](decisions/ADR-0009-comparative-intelligence-privacy-boundary.md)
- [ADR-0010 — Consequence-based approval model](decisions/ADR-0010-consequence-based-approval-model.md)
- [ADR-0011 — Business Context as a first-class component](decisions/ADR-0011-business-context-first-class.md)
- [ADR-0012 — Component placement rule](decisions/ADR-0012-component-placement-rule.md)
- [ADR-0013 — Token budget is self-imposed](decisions/ADR-0013-token-budget-is-self-imposed.md)
- [ADR-0014 — The retrieval agent ships with the first milestone that retrieves](decisions/ADR-0014-retrieval-agent-ships-with-retrieval.md)
- [ADR-0015 — Model-mediated scout dispatch](decisions/ADR-0015-model-mediated-scout-dispatch.md)
- [ADR-0016 — Declared conflicts outrank numeric agreement](decisions/ADR-0016-declared-conflicts-outrank-numeric-agreement.md)
- [ADR-0017 — The scout returns operation-bound line records, not an envelope](decisions/ADR-0017-operation-bound-line-records.md)
- [ADR-0018 — First-party company sources are tier B, by explicit registry](decisions/ADR-0018-first-party-company-source-registry.md)
- [ADR-0019 — Two research intents added for market analysis](decisions/ADR-0019-market-research-intents.md)
- [ADR-0020 — Two research intents added for competitor analysis, and two reused](decisions/ADR-0020-competitor-research-intents.md)
- [ADR-0021 — One immutable research-intent registry replaces the flat intent tables](decisions/ADR-0021-research-intent-registry.md)
- [ADR-0022 — One synthesis contract, built from existing vocabularies, that promotes nothing](decisions/ADR-0022-cross-domain-synthesis-contract.md)
- [ADR-0023 — An internal statement is defined by its provenance, not by its declared origin](decisions/ADR-0023-internal-statements-need-internal-footing.md)
- [ADR-0024 — One retrieval assembly, two closers: the `EvidenceSet` reaches synthesis as an object](decisions/ADR-0024-retrieval-to-synthesis-object-seam.md)
- [ADR-0025 — `unit` is a quantity type; scale is normalised into the value](decisions/ADR-0025-unit-is-a-quantity-type.md)
- [ADR-0026 — A dimension is admissible for compatibility only where its provenance says a source stated it](decisions/ADR-0026-dimension-provenance-and-source-context-admissibility.md)
- [ADR-0027 — Source context travels inside the evidence record; the protocol does not change](decisions/ADR-0027-external-source-context-extraction.md)
- [ADR-0028 — The research command's footing path is one seam, and it is strict by construction](decisions/ADR-0028-command-path-footing-is-strict.md)
- [ADR-0029 — The local join is a surface of its own, and it sequences only](decisions/ADR-0029-the-local-join-surface.md)
- [ADR-0030 — A SWOT point is a placement of a synthesis statement, never new text](decisions/ADR-0030-a-swot-point-is-a-placement.md)
- [ADR-0031 — The strategy recommendation contract](decisions/ADR-0031-strategy-recommendation-contract.md)
- [ADR-0032 — The Decision Support contract](decisions/ADR-0032-decision-support-contract.md)
- [ADR-0033 — The Executive Report contract](decisions/ADR-0033-executive-report-contract.md)
- [ADR-0034 — The M11 verification and finalisation contract](decisions/ADR-0034-m11-verification-and-finalisation-contract.md)
- [ADR-0035 — The M11 blind-recomputation boundary](decisions/ADR-0035-m11-blind-recomputation-boundary.md)
- [ADR-0036 — The data profiler contract](decisions/ADR-0036-biq-data-profiler-contract.md)
- [ADR-0037 — The M12 connector layer contract](decisions/ADR-0037-m12-connector-layer-contract.md)
- [ADR-0038 — Optional connectors and the user-initiated connection lifecycle](decisions/ADR-0038-optional-connector-connection-lifecycle.md)
- [ADR-0039 — The M13 test hardening and evals contract](decisions/ADR-0039-m13-test-hardening-and-evals-contract.md)
- [ADR-0040 — An owner-accepted environment-unavailable gap in the M13 coverage matrix](decisions/ADR-0040-m13-owner-accepted-environment-gap.md)
- [ADR-0041 — Deterministic, repository-owned input fixtures for the M13.2 eval cases: committed, builder-reproduced, bound to their cases, and inputs only](decisions/ADR-0041-m13-2-deterministic-repository-owned-eval-fixtures.md)
- [ADR-0042 — The engine is entered through one plugin-root-anchored, isolated launcher, located by the platform's `${CLAUDE_PLUGIN_ROOT}` substitution in command and skill bodies](decisions/ADR-0042-plugin-root-anchored-isolated-engine-entry.md)
- [ADR-0043 — Defect register status vocabulary for verified product fixes: `fixed_product`](decisions/ADR-0043-defect-status-for-verified-product-fixes.md)
- [ADR-0044 — The eval case file is written in the platform's own case format, and carries the BusinessOps semantic record beside it in the same file](decisions/ADR-0044-platform-format-eval-cases.md)
- [ADR-0045 — A BusinessOps-owned runtime resolver chooses the Python interpreter, so no command names one](decisions/ADR-0045-businessiq-owned-portable-runtime-resolution.md)
- [ADR-0046 — Under WSL, automatic interpreter resolution excludes Windows executables; the explicit override does not](decisions/ADR-0046-wsl-excludes-windows-interpreters-from-automatic-resolution.md)
- [ADR-0047 — A routing grader accepts the owning BusinessOps command route as well as the skill route](decisions/ADR-0047-routing-graders-accept-the-owning-command-route.md)
- [ADR-0048 — An eval case may declare one deterministic precondition fixture, staged at the path the case names](decisions/ADR-0048-declared-precondition-fixtures-for-eval-cases.md)
- [ADR-0049 — A run whose semantic judge votes split is `execution_unavailable`, never a pass or a fail](decisions/ADR-0049-semantic-judge-splits-are-execution-unavailable.md)
- [ADR-0050 — The disclosure gate establishes the provenance of every request fragment from the workspace's business data](decisions/ADR-0050-provenance-aware-research-boundary.md)
- [ADR-0051 — A pre-execution write-approval boundary: a plugin-wide `PreToolUse` guard, an engine execution guard, and single-use capabilities granted only from the user's prompt](decisions/ADR-0051-pre-execution-write-approval-boundary.md)
- [ADR-0052 — The local verifier MCP server is launched through the runtime resolver](decisions/ADR-0052-verifier-server-launched-through-the-runtime-resolver.md)
- [ADR-0053 — The scout's reply reaches the engine through a harness capture, never a model copy](decisions/ADR-0053-scout-reply-captured-by-the-harness.md)
- [ADR-0054 — BusinessOps product identity and the `bops` technical namespace](decisions/ADR-0054-businessops-product-identity-and-bops-namespace.md)
- [ADR-0055 — The installable package is built from an allowlist into its own plugin root](decisions/ADR-0055-distribution-package-built-from-an-allowlist.md)
- [ADR-0056 — Commands and skills name the shipped reference documents by their plugin-root path](decisions/ADR-0056-plugin-root-paths-for-shipped-reference-documents.md)
- [ADR-0057 — One public repository holds the source and the built package](decisions/ADR-0057-one-public-repository-for-source-and-package.md)
- [ADR-0058 — Prakash Meghani - Krayons Global is the current rights holder and support identity](decisions/ADR-0058-krayons-global-rights-holder-and-support-identity.md)
