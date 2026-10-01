# Reference — Analysis Framework

**Owns:** the canonical 19-step pipeline every BusinessOps workflow follows, and the approval
matrix (*Approval follows consequence*).
**Consulted by:** every command, as an explicit numbered step.
**Does not own:** materiality thresholds ([materiality-policy](materiality-policy.md)),
provenance ([evidence-ledger](evidence-ledger.md)), formatting
([output-standards](output-standards.md)), refusal behaviour
([ambiguity-protocol](ambiguity-protocol.md)), research rules
([research-policy](research-policy.md)).

---

## The pipeline

```
 1  Identify objective + load Business Context
 2  Determine information requirements
 3  Split internal vs external requirements
 4  Inspect data                    → ingestion / data-profiler
 5  Retrieve external information   → DISCLOSURE GATE
 6  Validate                        → QUALITY GATE
 7  Normalize                       → derived copy; source untouched
 8  Calculate                       → engine; relevance from Business Context
 9  Compare                         → period / segment / benchmark
10  Identify material changes       → materiality filters
11  Investigate
12  Separate facts from interpretation
13  Generate insights
14  Evaluate risks and opportunities
15  Generate recommendations
16  Identify assumptions and uncertainty
17  Assign confidence
18  Generate output
19  Human decision
```

A command that skips a step must say **which and why** in its output.

## The two gates that halt

| Gate | Step | Halts when |
|---|---|---|
| **Disclosure** | 5 | A query needs Tier 2 (await approval) or Tier 3 (refuse) — see [research-policy](research-policy.md) |
| **Quality** | 6 | Data quality is `CRITICAL` — continuing would mislead |

Materiality (step 10) **filters** what is reported; it never halts.

## Step 19 is not a gate

"Human decision" states the product's purpose: BusinessOps produces decision-*ready*
analysis for a person to act on. It does **not** gate execution. Read-only analysis runs on
request without approval. The approval gate attaches to a consequential *action*, if one is
later requested — see *Approval follows consequence* below and ADR-0010.

## Approval follows consequence

Approval is graded by **consequence**, not by activity (ADR-0010). Gating ordinary analysis
produces approval fatigue, which is how a genuinely consequential prompt gets waved through.

| Consequence | Examples | Approval |
|---|---|---|
| **Read-only, or a new local file** | Any read-only analysis (KPI, sales, customer, product, profitability, cash flow, forecasting, anomaly detection, research, SWOT, strategy, decision support); research at disclosure Tiers 0 and 1 ([research-policy](research-policy.md)); drafts held in the conversation or the session scratchpad; writing a **new** file under `./businessops-output/`, stating the path | None |
| **Leaves the machine or cannot be undone** | Overwriting or deleting **any** existing file; Tier 2 research, after showing the verbatim text; exporting anything off the machine; writing to a CRM, accounting, commerce or database system; sending a message, email or chat post, or publishing; installing the optional reader dependency (once, disclosed); committing to a version-control repository | Explicit, **per action**: state exactly what changes and where |
| **Prohibited** | Modifying the user's original source data; any financial transaction; Tier 3 disclosure; pushing to a remote repository without an explicit instruction, force-pushing, rewriting history or deleting branches | Refused; no approval unlocks it |

Approval is per action and non-transferable: approving one export does not approve the next,
and there is no session-wide "yes to everything". The write guard enforces the filesystem part
of this matrix before a tool call runs (README, *Approval and write safety*).

## What each step must produce

| Step | Must produce |
|---|---|
| 1 | A stated objective and the resolved Business Context (including what is missing) |
| 2–3 | An explicit list of what is needed, split internal vs external |
| 4 | A dataset and profile, with the **reader tier recorded** |
| 5 | An evidence set with source, date and tier per item — or a stated absence |
| 6 | A graded quality report; `CRITICAL` stops the workflow here |
| 7 | A derived working copy. **The source file is never modified** |
| 8 | Results in four buckets: computed / partial / unavailable / not_applicable |
| 9–11 | Comparisons and the investigation of anything material |
| 12 | Every claim assigned a provenance class 1–7 |
| 13–15 | Insights, risks, opportunities, recommendations — each with its evidence |
| 16–17 | A registered assumption list and an explicit confidence level |
| 18 | Output conforming to [output-standards](output-standards.md) |

## Applying it honestly

- If a step cannot run, say so and say why. Do not silently skip it.
- If the objective is ambiguous, stop at step 1 and ask — see
  [ambiguity-protocol](ambiguity-protocol.md).
- If required data is absent, name the field. Never substitute an estimate for a
  measurement.
