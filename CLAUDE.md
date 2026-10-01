# CLAUDE.md — BusinessOps

Persistent development instructions for Claude when working in this repository.

This file governs **how the project is built**. It deliberately contains no business
analysis logic — that lives in `skills/`. See [Document ownership](#document-ownership)
before adding anything here.

---

## 1. Project purpose

BusinessOps is a **Claude Code plugin** that turns internal business data and reliable
external business intelligence into insights, analytics, forecasts, strategic analysis,
recommendations and decision-ready reports.

It is a structured decision-support system, not a general-purpose chatbot. Every output
must be traceable to evidence, must separate fact from interpretation, and must state its
own confidence and limitations.

Canonical technical description: `architecture.md` (currently Revision 2).
Canonical roadmap and status: `project_plan.md`.

---

## 2. Architecture principles

1. **Determinism over inference for numbers.** Financial and KPI figures are computed by
   code in `lib/python/bops/`, never by model arithmetic. If a number appears in an output,
   a script produced it. See ADR-0002 (amended by ADR-0008).
2. **Single source of logic.** Every business rule has exactly one home, chosen by the
   placement test in section 3. A formula lives in the engine; a policy in one reference
   document; a workflow in one skill; sequencing in one command. Never paraphrase a rule
   that is already homed elsewhere — link to it. See ADR-0012.
3. **Layered, not tangled.** Context/Policy → Data → Analytics → Intelligence → Synthesis →
   Orchestration. A layer may depend on layers below it, never above.
4. **Provenance is mandatory.** Every claim carries one of the seven provenance classes
   defined in `reference/evidence-ledger.md`. Unattributed claims are defects.
5. **Fail loudly.** When data is insufficient, ambiguous, or of failing quality, stop the
   workflow and say so. Never degrade silently into a plausible-looking wrong answer.
6. **Approval follows consequence, not activity.** Read-only analysis runs on request with
   no approval. Actions that leave the machine or cannot be undone require explicit
   per-action approval. See section 9 and ADR-0010.
7. **Source data is immutable.** Never modify, repair, overwrite or "clean" a user's
   original file or record. Normalisation happens in a derived working copy.
8. **Graceful degradation.** No connector is assumed present. The uploaded Excel/CSV path
   must remain fully functional standalone, forever.
9. **Additive extension.** New KPIs, connectors, commands and skills are added by
   registration, not by editing core engine code. See `architecture.md`, Extension Points.

---

## 3. Repository conventions

```
.claude-plugin/plugin.json       Plugin manifest (auto-discovery; agents must NOT be listed, ADR-0015)
.claude-plugin/marketplace.json  Marketplace entry so the repo installs directly from GitHub
.mcp.json                        MCP server declarations
commands/                        User-facing slash commands (thin orchestrators)
skills/<name>/SKILL.md           Judgement + workflow (16 skills)
reference/                       Policy documents, 0 always-on, read on instruction (6)
agents/<name>.md                 Subagents (context isolation / fan-out / verification only)
hooks/hooks.json                 The plugin-wide write guard (ADR-0051); no logic, enters the engine
lib/python/bops/                 Deterministic compute engine (Python 3.9+, stdlib only)
lib/schemas/                     JSON Schemas for every artifact passed between layers
config/                          Default configuration; user config resolved at runtime
assets/demo-data/                Synthetic demo dataset only — never real data
tests/                           Deterministic fixture test harness
evals/                           Plugin eval suite (behavioural tests)
docs/                            Long-form documentation and project history
dev/harness/                     Developer-only harnesses, never shipped (e.g. retrieval-slice)
scripts/build_distribution.py    Builds the installable package into dist/ (gitignored), ADR-0055
LICENSE · EULA.md · PRIVACY.md   Proprietary licence, end-user terms, privacy policy (all shipped)
```

Runtime state lives **outside** the repository and is never committed:
`./.businessops/business_context.json` (gitignored) · `./businessops-output/` (generated
reports) · `~/.claude/businessops/runtime/` (the consented reader venv, ADR-0008) · `~/.claude/businessops/guard/`
(write-approval store, ADR-0051).

**Where a rule belongs** (ADR-0012) — apply this test before writing anything:

| Question | Home |
|---|---|
| Deterministic computation, no judgement? | `lib/python/bops/` |
| A definition, policy or table nobody invokes directly? | `reference/` |
| Needs model judgement, and a user might ask for it in words? | `skills/<name>/SKILL.md` |
| Purely sequencing: what runs, in what order, with which gates? | `commands/<name>.md` |

Agents hold **no** unique business logic. A rule found only inside an agent is a bug. The same
holds for hooks: `hooks/` only routes an event into `lib/python/bops/writeguard/`, where the write
policy lives (ADR-0051).

**Naming**

- Skills: `bops-<domain>-<function>`, lowercase, hyphenated (e.g. `bops-data-quality`).
- Commands: the plain user-facing name from `architecture.md` section 4
  (e.g. `sales-analysis.md`), no `bops-` prefix.
- Agents: `bops-<role>` (e.g. `bops-research-scout`).
- Python modules: `snake_case`; one concern per module.
- Dates in filenames and documents: ISO `YYYY-MM-DD`, always.

**Frontmatter** — only fields verified to be supported (see ADR-0001):

- Skills: `name`, `description`, optional `argument-hint`, `user-invocable`.
- Commands: `description`, optional `argument-hint`, `allowed-tools`,
  `disable-model-invocation`, `hide-from-slash-command-tool`.
- Agents: `name`, `description`, `tools`, `model`, `color`.

Do not invent frontmatter fields. Validate with `claude plugin validate . --strict`.

---

## 4. Coding conventions

- **Python 3.9+.** The engine is stdlib-first: every code path must have a stdlib fallback
  producing identical results. The one managed dependency is the Tier-2 xlsx reader
  (openpyxl), installed only into `~/.claude/businessops/runtime/` after explicit user
  consent, never into the system or project interpreter (ADR-0008). Never add a dependency
  without an ADR.
- Scripts are **pure and testable**: read inputs from argv/stdin, write JSON to stdout,
  diagnostics to stderr, non-zero exit on failure. No interactive prompts.
- Every script emits machine-readable JSON conforming to a schema in `lib/schemas/`.
- Money uses `decimal.Decimal`, never binary float, in any path that produces a reported
  figure. Rounding is applied once, at presentation.
- No network calls from `lib/python/bops/`. External retrieval belongs to the research layer.
- Comment density and idiom should match the surrounding module.

---

## 5. Development workflow

This project runs on an **external review loop**:

```
User prompt -> Claude performs ONLY that task -> docs updated -> tests run
-> dated development record written -> structured TASK REPORT -> external review
-> next approved prompt
```

Rules:

- **Do only the current prompt.** Approval of milestone N is not approval of N+1.
- Before starting, read `project_plan.md` and the most recent file in `docs/development/`.
- Use TodoWrite for any task with more than three steps.
- If the prompt conflicts with `architecture.md`, stop and raise it. Do not silently deviate.

---

## 6. Testing requirements

- No feature is marked `COMPLETED` in `project_plan.md` until it has been implemented **and**
  exercised by a test that was actually executed.
- Every engine module needs deterministic fixture tests in `tests/`.
- Every failure mode listed in `architecture.md` (Error Handling) needs a negative-path test.
- Run `python tests/run_tests.py` and paste real output into the task report.
- **Never claim a test passed without running it.** Never claim a feature works without
  verifying it. If a test was not run, the report says so.

---

## 7. Security requirements

- No credentials, API keys, tokens, connection strings or real customer data in this repo —
  not in code, fixtures, docs, examples, eval cases or commit messages.
- Authentication is delegated entirely to MCP servers and their OAuth flows. BusinessOps
  never stores, reads, logs or transmits a secret.
- `.mcp.json` contains only server identity (type/url/command). Never embed a token.
- Treat `.env*` as sensitive; it is gitignored and must stay that way.
- Redact secrets from anything written to `docs/` or emitted in a report.

---

## 8. Data privacy requirements

All business data is confidential. What may leave the machine is governed by the four-tier
disclosure model (ADR-0009); nothing else is permitted.

| Tier | What | Approval |
|---|---|---|
| **0** | Query built **only** from public terms (industry, business model, geography, product category, competitor names, period). The benchmark comes back and the comparison is computed **locally**. | None — this is the default and covers substantially all comparative questions |
| **1** | Derived-safe context: aggregated over ≥ 5 entities, **banded not exact**, passes a whole-query re-identification check. Rates and ratios pass; absolute monetary levels never do. | None if all four checks pass |
| **2** | Anything more — the user sees the **verbatim text to be sent** and approves **per query**. Never a session-wide mode. | Explicit, per query |
| **3** | Credentials, tokens, PII, customer names, customer-level records, individual transactions, raw ledgers. | **Refused — no approval path** |

- **Answer comparative questions by fetching the benchmark, not by sending the figure.**
  "Is our 35% margin typical?" is a query about the industry, not about us.
- The gate runs at query construction, before any tool call, and logs what was sent.
- Prefer aggregates. Row-level or named-individual data only when the analysis genuinely
  requires it, and never in a shareable artifact without asking.
- Derived working files go under the session scratchpad or `./businessops-output/`, never
  into the user's source data.

---

## 9. Permission model — approval follows consequence

Approval is graded by **consequence**, not by activity (ADR-0010). Gating ordinary analysis
would produce approval fatigue, which is how a genuinely consequential prompt gets waved
through.

**No approval needed — just do it:**

- Any read-only analysis: KPI, sales, customer, product, profitability, cash-flow,
  forecasting, anomaly detection, company/market/competitor/industry research, SWOT,
  strategy, decision support
- Tier 0/1 external research (section 8)
- Draft reports held in conversation or the session scratchpad
- Writing a **new** file into `./businessops-output/` — state the path

**Explicit, per-action approval required — state exactly what changes and where:**

- Overwriting **any** existing file
- Tier 2 external research — show the verbatim text first
- Exporting anything off the machine (cloud, shared workspace, any URL)
- Writes to CRM, accounting, commerce or databases — name system, record, change
- Sending a message, email or chat post; publishing anything — show recipients and content
- Installing the Tier-2 reader dependency (once, disclosed)
- `git commit` (on request only)

**Prohibited outright — no approval unlocks these:**

- Modifying original source data
- Any financial transaction
- Tier 3 disclosure (section 8)
- `git push` without an explicit instruction; force-push; rewriting history; deleting branches

Approval is **per action and non-transferable** — approving one export does not approve the
next. There is no session-wide "yes to everything".

---

## 10. Git expectations

- Commit only when the user asks. Never push unless explicitly instructed.
- One logical change per commit; documentation updated in the same commit as the code it
  describes.
- Message format `<type>(<scope>): <summary>` where type is one of
  `feat|fix|docs|test|refactor|chore`, e.g. `feat(kpi-engine): add DSO and DPO calculators`.
- `main` carries governance and documentation. Implementation milestones use
  `milestone/<n>-<slug>` branches when the user asks for a branch.
- Never rewrite history. Never run destructive git operations.
- Every commit message ends with the attribution block the session specifies.

---

## 11. Documentation requirements

After every meaningful implementation task, in this order:

1. Update `architecture.md` if anything architectural changed.
2. Update `project_plan.md` statuses (`PLANNED / IN PROGRESS / BLOCKED / REVIEW /
   COMPLETED / DEFERRED`).
3. Write a **new** dated record at `docs/development/YYYY-MM-DD-<slug>.md` from
   `docs/templates/dev-record.md`. Never edit or overwrite a past record; correct it by
   writing a newer one that supersedes it.
4. Add an ADR under `docs/decisions/` for any significant or hard-to-reverse decision
   (see `docs/decisions/README.md` for the bar). Trivial changes get no ADR.
5. Update the relevant reference page under `docs/skills|commands|agents|integrations/`.
6. Emit the TASK REPORT (section 12).

**Architecture must never change silently.** If the code no longer matches
`architecture.md`, one of the two is a bug — fix it in the same task.

### Document ownership

| Document | Owns | Never contains |
|---|---|---|
| `CLAUDE.md` | How to *develop* this project | Business logic, KPI formulas, prose docs |
| `architecture.md` | What the system *is*, and why | Status, dates, roadmap |
| `project_plan.md` | What is *done / next*, status | Design rationale, technical detail |
| `README.md` | What users install and run | Development process |
| `docs/` | Long-form, historical, per-component detail | Anything duplicated from the above |
| `skills/*/SKILL.md` | Judgement and workflow | Formulas, policy tables, governance |
| `reference/*.md` | Policy and definitions | Workflow, computation, status |
| `lib/python/bops/` | Computation | Prose, policy, judgement |

If information would appear in two of these, it belongs in exactly one and is linked from
the other.

---

## 12. Required task report

End every meaningful implementation task with exactly this structure. Use `N/A` where a
section does not apply. Template: `docs/templates/task-report.md`.

```
TASK REPORT
 1. Objective               9. Test Results
 2. Work Completed         10. Issues / Risks
 3. Files Created          11. Documentation Updated
 4. Files Modified         12. Project Plan Updated
 5. Files Deleted          13. Git Status / Commit
 6. Features Implemented   14. Remaining Work
 7. Architecture Changes   15. Recommended Next Step
 8. Tests Performed
```

Accuracy rules: report what happened, not what was intended. If a step was skipped, say so.
If a test failed, show the output. If scope was reduced, name what was left out and why.

---

## 13. Approval gates

Work stops and waits for explicit user approval at each of these points:

| Gate | Trigger |
|---|---|
| Architecture gate | Before any implementation begins |
| Milestone gate | Before starting each milestone in `project_plan.md` |
| Connector gate | Before adding any MCP server to `.mcp.json` |
| Disclosure gate | Before a Tier 2 external query (section 8) |
| Write-action gate | Before any explicit-approval action in section 9 |
| Publication gate | Before any commit, push, tag or release |

At a gate, present the decision and stop. Do not proceed on assumed approval.
