# 2026-09-08 — Architecture Review Corrections (Revision 2)

**Milestone:** 0 — Architecture & Governance
**Status on completion:** `REVIEW` — awaiting approval of the corrected architecture
**Supersedes:** None. This record **follows** and does not replace
[2026-09-08-milestone-0-architecture-gate.md](2026-09-08-milestone-0-architecture-gate.md),
which stands as the record of Revision 1.

## 1. Prompt / task performed

External review of the Revision 1 BUSINESSIQ ARCHITECTURE REPORT returned seven corrections
with instructions to preserve the overall architecture and not redesign it: (1) resolve
production `.xlsx` ingestion; (2) correct the internal/external research boundary, which was
too restrictive for comparative questions; (3) clarify approval gates so read-only analysis
does not require approval; (4) verify whether the 4,000-token figure is a real platform
constraint; (5) promote Business Context to a first-class component; (6) move an early
end-to-end vertical slice into the roadmap; (7) verify — not automatically reduce — the
25-skill architecture. Still an architecture-review task: no implementation, no deployment,
no account connections.

## 2. Objective

Apply the seven corrections with evidence rather than assertion, keeping the layered design
intact, and record every decision as an ADR without overwriting Revision 1's history.

## 3. Changes made

### Correction 1 — Excel ingestion (ADR-0008)

Verified rather than assumed. The Claude Code `Read` tool **cannot open `.xlsx`** ("This tool
cannot read binary files"), so no built-in path exists and a parser is mandatory. Checked
what the environment can bootstrap: pip 24.3.1 present, PyPI reachable (resolved openpyxl
3.1.5), `venv` and `ensurepip` available, npm registry reachable.

Built a realistic test workbook with stdlib (two sheets, styled date cells, custom GBP
currency format, built-in percent format, formula cells with cached values, inline strings,
shared strings), then **built and ran both candidate readers against it**: a full stdlib
parser written for this review, and openpyxl 3.1.5 installed into an isolated scratchpad
venv. They agreed on every value both could read. The stdlib parser handled sheets via the
rels graph, shared and inline strings, date cells resolved from `styles.xml`, 1900/1904 date
systems, cached formula values, currency symbol extraction, and streaming via `iterparse` —
but **misclassified a percent cell** because it resolves only custom number formats, not the
~50 built-in ECMA-376 ids.

Decision: a **four-tier reader** — (1) openpyxl if already importable, (2) openpyxl in a
plugin-managed venv at `~/.claude/businessiq/runtime/` after one-time disclosed consent,
(3) the stdlib parser, complete for a documented subset and required to **escalate or halt
rather than guess** outside it, (4) guided CSV export. Every dataset records its tier; a
Tier-3 read with unresolved formats raises a quality `WARNING`; cross-tier equivalence is a
test requirement. This amends ADR-0002's "stdlib only" clause; ADR-0002's core decision
(deterministic code, not model arithmetic, produces reported figures) is unchanged.

### Correction 2 — Privacy boundary (ADR-0009)

Reframed the problem. The four example questions ("our churn is 8%, how does that compare?")
are not requests to *share* internal data — they are requests to *contextualise* it. What
needs fetching is the **public benchmark**, which requires no internal data at all.

New four-tier model: **Tier 0 local join** (query built only from public terms, comparison
computed locally — covers all four examples with **zero** transmission and no approval
prompt); **Tier 1 derived-safe context** gated on four checks (k≥5 aggregation floor; banded
not exact, so rates pass but absolute monetary levels never do; a whole-query
re-identification check; not on the Tier 3 list); **Tier 2** explicit per-query approval with
verbatim preview; **Tier 3** never externalizable with no approval path. The gate runs at
query construction and logs what was sent to the evidence ledger. The ADR-0006 tool split
(`biq-research-scout` has no file access) is the structural backstop.

Net effect: the model is both more capable and stricter than Revision 1's blanket rejection,
which pushed users toward pasting figures elsewhere.

### Correction 3 — Approval gates (ADR-0010)

The Revision 1 pipeline ended with "19 Human review ── GATE", which read as gating every
analysis. Replaced with a consequence-graded matrix on two axes (does the effect leave the
machine; how reversible). Read-only analysis, Tier 0/1 research, drafts, and new files in
`./businessiq-output/` need **no approval**. Overwrites, Tier 2 queries, off-machine exports,
system writes, communication, publication and the dependency bootstrap need **explicit
per-action approval**. Source-data modification, financial transactions and Tier 3 disclosure
are **prohibited outright**. Step 19 renamed "Human decision" and is explicitly not an
execution gate; the pipeline now has **two** halting gates (disclosure, quality) rather than
three.

### Correction 4 — Runtime constraints (ADR-0013)

**The 4,000-token ceiling was mine, not the platform's.** It was neither measured nor
documented, and it was presented with more authority than it had earned. Corrected.

Verified from official Anthropic skill guidance held locally: hard limits are `name` ≤ 64
chars and `description` ≤ 1024 chars; "under 500 lines" for a SKILL.md body is a *guideline*.
Progressive disclosure confirmed both officially ("At startup, only the metadata (name and
description) from all Skills is pre-loaded") and by measurement. Commands and agents also
contribute descriptions always-on; reference files and scripts cost zero until read; MCP tool
schemas are not counted.

Built a **full-scale probe** (17 commands + 25 skills + 3 agents), installed and measured it:
**~2,617 tok always-on for 42 components**, `validate --strict` passed, **no cap, warning or
error**. No aggregate limit is enforced or documented. Replaced the false ceiling with a
self-imposed ≤3,000 target and redirected optimisation onto the constraint measurement
actually revealed: **description discriminability** across many same-domain components.

### Correction 5 — Business Context (ADR-0011)

Promoted to a first-class component: a `biq-business-context` skill, a
`business_context.json` document, a schema and a controlled vocabulary. Stored project-local
at `./.businessiq/` (gitignored), user-level supported. Precedence: command argument →
project context → user context → shipped defaults, with Business Context *replacing* the
generic config layers it covers.

Its most important function is **KPI relevance**. The KPI registry gains `applicable_models`
and the engine returns a fourth bucket, `not_applicable` — meaningfully different from
`unavailable`. A consulting firm's data may support inventory turnover; the number is
meaningless. Without context nothing is suppressed; the output says relevance filtering is
off. Its externalizable subset (industry, business model, size band, geography, product
categories) is also what feeds Tier 0 research queries, resolving where those public terms
come from.

### Correction 6 — Vertical slice

Moved to **Milestone 2**, immediately after Foundation. Synthetic demo data moved from M13
to M2. The slice runs synthetic dataset → ingestion → semantic mapping → data quality →
5 KPIs (including one `not_applicable`) → one analysis skill → executive-style output, via
one command, with the evidence ledger carried end to end and both a passing and a
deliberately-broken-data test. Exit criteria are the seven things it must prove; failure
triggers architecture revision before Milestone 3. Milestone count 13 → 14.

### Correction 7 — Skill architecture verified (ADR-0012)

Verified rather than reduced, using a placement test: deterministic computation → engine;
definition/policy nobody invokes → reference document; needs judgement and plausibly asked
for in words → skill; pure sequencing → command. Agents hold no unique logic.

Applying it moved seven components without losing a single business rule. The five Layer-0
"foundation skills" were never invocable by name and contain no workflow — they are policy,
so they became **reference documents** costing zero always-on and read by explicit command
step, which is more reliable than hoping a skill auto-fires. `biq-connector-broker` merged
into `biq-data-ingestion` (source resolution is only used when loading data);
`biq-report-composer` split into judgement (`biq-executive-report`) and engine rendering.
`biq-business-context` added. Result: **20 skills + 6 reference documents + engine modules**,
17 commands and 3 agents unchanged.

## 4. Files created

```
docs/decisions/ADR-0008-tiered-xlsx-ingestion.md
docs/decisions/ADR-0009-comparative-intelligence-privacy-boundary.md
docs/decisions/ADR-0010-consequence-based-approval-model.md
docs/decisions/ADR-0011-business-context-first-class.md
docs/decisions/ADR-0012-component-placement-rule.md
docs/decisions/ADR-0013-token-budget-is-self-imposed.md
docs/development/2026-09-08-architecture-review-corrections.md   (this file)
```

## 5. Files modified

| File | Change |
|---|---|
| `architecture.md` | Rewritten as Revision 2 (v0.2.0) with a changelog header. New/changed: §2 runtime constraints, §3 component placement, §4 twenty skills, §5 tiered reader, §6 Business Context, §7 disclosure tiers, §8 approval matrix, §9 two gates, §13 repo structure, §14 config, §15 tests, §16 errors, §18 extension points, §19 ADR table, §20 limitations |
| `project_plan.md` | Vertical slice as M2; demo data moved from M13; Business Context and runtime resolver into M1; 13 → 14 milestones; Revision 2 task table; risks R-06, R-07 added |
| `CLAUDE.md` | §1 revision pointer; §2 principles 1–4 and 6; §3 placement test + runtime state + `reference/`; §4 dependency policy; §8 rewritten with the disclosure tiers; §9 rewritten as the consequence matrix; §11 ownership table; §13 disclosure gate added |
| `docs/README.md` | ADR list, development history, ownership row for `reference/` |
| `docs/decisions/README.md` | ADR index 0008–0013 + amended/refined note |
| `docs/development/README.md` | Index row for this record |
| `docs/decisions/ADR-0002-*.md` | **Status line only** — amendment note pointing to ADR-0008. Body untouched |
| `docs/decisions/ADR-0003-*.md` | **Status line only** — refinement note pointing to ADR-0012. Body untouched |
| `docs/decisions/ADR-0006-*.md` | **Status line only** — confirmed unchanged by review |

## 6. Files deleted

None in the repository. Outside it: the `scaleprobe` measurement plugin was copied into
`~/.claude/skills/` to obtain a `plugin details` reading and **removed immediately
afterwards** (verified: only the user's pre-existing skills remain). Probe artifacts
(`realistic.xlsx`, `stdlib_xlsx.py`, `make_realistic_xlsx.py`, `cmp_openpyxl.py`, `.biqvenv`,
`scaleprobe/`) remain in the session scratchpad, outside the repository.

## 7. Features implemented

None. Architecture review only — no plugin components, no engine code, nothing activated.

The stdlib xlsx parser and the openpyxl comparison written during this review are
**throwaway verification probes in the scratchpad**, not product code. They exist to answer
the review's question with evidence; the production reader is Milestone 2/3 work.

## 8. Tests performed

No product tests — there is no product code. Verification probes executed:

```
Read tool on realistic.xlsx                          # -> cannot read binary
python -m pip --version                              # 24.3.1
urllib -> https://pypi.org/pypi/openpyxl/json        # reachability
python -c "import venv, ensurepip"                   # availability
npm view xlsx version                                # registry reachability
python make_realistic_xlsx.py                        # build the fixture
python stdlib_xlsx.py realistic.xlsx                 # stdlib reader
python -m venv .biqvenv && pip install openpyxl      # bootstrap path
.biqvenv/Scripts/python.exe cmp_openpyxl.py          # openpyxl reader, same file
claude plugin validate <scaleprobe> --strict         # 42-component manifest
claude plugin details scaleprobe                     # always-on measurement
grep official skill guidance for documented limits
```

## 9. Test results

| Probe | Result |
|---|---|
| `Read` on `.xlsx` | ✅ Confirmed **cannot read binary files** — a parser is mandatory |
| pip / PyPI / venv / npm | ✅ pip 24.3.1 · openpyxl 3.1.5 resolvable · venv+ensurepip OK · npm OK |
| stdlib reader | ✅ sheets `['Sales','Costs']` · dates `45000→2023-03-15`, `45031→2023-04-15` · currency `£` · 2 formula cells read as cached `15250.75`/`6100.3` · inline string `EMEA` · 1900 system.<br>❌ **percent cell misclassified as number** — built-in numFmt ids unresolved |
| openpyxl 3.1.5 in venv | ✅ identical values; additionally resolved built-in format `0.00%` and exposed `=D2*E2` |
| 42-component `validate --strict` | ✅ Validation passed — **no cap or warning** |
| `plugin details scaleprobe` | ✅ **~2,617 tok always-on**, 42 components |
| Official guidance | ✅ hard limits 64 / 1024 chars; 500-line body is a guideline; **no aggregate ceiling documented** |

**No BusinessIQ test suite exists yet.** Nothing above is a product test.

## 10. Issues discovered

| ID | Issue |
|---|---|
| R-04 (updated) | Tier-3 built-in numFmt ids unresolved — **found by probe, would have silently misread percent and date columns**. Now a named M3 task with a refuse-don't-guess requirement |
| R-05 (reframed) | Was "token budget"; now **description discriminability** across 37 same-domain components — the real constraint, invisible to token metrics |
| R-06 (new) | Tier-2 bootstrap introduces a dependency supply chain. Pinned, isolated, consented, optional |
| R-07 (new) | Re-identification checking is inherently heuristic; will sometimes over-block. Errs safe by design |

Also corrected: the 4,000-token ceiling asserted in Revision 1 did not exist.

## 11. Decisions made

ADR-0008 through ADR-0013. ADR-0002, ADR-0003 and ADR-0006 gained status annotations only;
their bodies are preserved verbatim per the immutability rule.

## 12. Architecture changes

`architecture.md` advanced to Revision 2 (v0.2.0) — see §5 above for the section list. The
five-layer structure, 17 commands, 3 subagents, capability-based connectors, seven-class
evidence ledger and two-layer testing strategy are all unchanged.

## 13. Project-plan updates

Vertical slice inserted as Milestone 2 with seven exit criteria; synthetic demo data moved
M13 → M2; Business Context and the runtime tier resolver added to M1; `reference/` added to
M1; disclosure-gate tasks and tier tests added to M9; cross-tier equivalence added to M3;
routing and approval-model cases added to M13; milestones renumbered 13 → 14; Revision 2 task
table added to M0; risks R-06 and R-07 registered, R-04 and R-05 updated.

## 14. Documentation updates

`architecture.md`, `project_plan.md`, `CLAUDE.md`, `docs/README.md`,
`docs/decisions/README.md`, `docs/development/README.md`, six new ADRs, three ADR status
annotations, and this record. Revision 1's development record is untouched.

## 15. Remaining work

Everything after the gate. Next, subject to approval: **Milestone 1 — Foundation**
(manifest + marketplace, README/LICENSE/CONNECTORS, gitignore additions, config defaults and
resolver, the six `reference/` documents, `biq-business-context` with schema and vocabulary,
the runtime tier resolver and consent flow, `tests/run_tests.py`, and the first always-on
token measurement), followed immediately by **Milestone 2 — Vertical Slice**.

## 16. Git commit reference

Branch `main`. No commit made — `CLAUDE.md` §10 requires commits only on request. Nothing
pushed. Working tree carries the Revision 1 files plus this revision's changes, all
uncommitted.
