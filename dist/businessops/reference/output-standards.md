# Reference — Output Standards

**Owns:** presentation conventions and the shapes BusinessOps outputs take.
**Consulted by:** every command that produces user-facing output.
**Does not own:** provenance marking ([evidence-ledger](evidence-ledger.md)), what counts
as material ([materiality-policy](materiality-policy.md)), rendering mechanics (the
engine).

---

## Locale

All four resolve through the precedence chain; never hard-code them.

| Setting | Default | Notes |
|---|---|---|
| `currency` | `USD` | ISO 4217. Always show the code or symbol — a bare number is ambiguous |
| `number_format` | `1,234.56` | Also supports `1.234,56`, `1 234,56`, `1234.56` |
| `date_format` | `YYYY-MM-DD` | ISO by default |
| `fiscal_year_start` | `01-01` | Period labels follow the fiscal year, not the calendar |

**Never mix currencies in one total.** Where a dataset contains several, report per
currency and raise a quality finding. BusinessOps does not convert in v1 — conversion needs
a dated rate source it does not have.

## Numeric presentation

- Round **once**, at presentation. Internal arithmetic keeps full precision (`Decimal` for
  money).
- Money: 2 decimal places unless the user configures otherwise.
- Percentages: 1 decimal place. Margin *movements* in **percentage points** (`pp`).
- Large numbers: thousands separators always; abbreviate (`£1.2m`) only in summaries, never
  in tables meant for checking.
- Negatives: a leading minus, not parentheses, unless the user's format specifies otherwise.
- Show the same figure identically everywhere it appears in one report.

## Required labelling

Every output must make these unmistakable:

| Must be distinguishable | How |
|---|---|
| Actual vs forecast | Separate blocks or an explicit column. **Never one undifferentiated series** |
| Evidence vs interpretation | Classes 1–4 visually distinct from 5–7 |
| Complete vs partial periods | Partial periods flagged; never compared as if complete |
| Computed vs unavailable vs not-applicable | Three distinct states, never one blank |

## Standard shapes

- **KPI scorecard** — metric · current · prior · change · change % · materiality flag ·
  confidence.
- **Ranked table** — sorted by the dimension being argued, with a stated total and, where
  relevant, the share of that total.
- **Trend summary** — direction, magnitude, duration, and whether it is material.
- **Forecast table** — actuals block, then base / upside / downside, then the assumption
  register.
- **Chart-ready data** — structured rows a consumer can plot. BusinessOps emits the data,
  not the image.
- **Recommendation list** — action · evidence · rationale · expected benefit · risks ·
  dependencies · confidence, plus the confidence reasons, conflicts and limitations carried from
  the evidence. Field names and rules are the evidence ledger's (class 7, ADR-0031). Order is
  presentation, never a ranking: no priority, rank or score column.
- **Decision package** (ADR-0032) — twelve parts in fixed order: decision question · business
  context · objective · options · criteria · evidence · assumptions · tradeoffs · risks · expected
  outcomes · guidance · uncertainty. The lifecycle (`draft` or `final`) is shown before the parts, and
  a draft is always labelled unverified. User-supplied framing — question, objective, options,
  constraints, criteria — is labelled as the user's and never presented as evidence. Every
  tradeoff, risk and outcome shows its option, its cited evidence and its derived confidence; an
  unevidenced risk and an unassessed option say so. Guidance shows class-7 records in the
  recommendation-list shape, the preferred option only with its named basis (otherwise the stated
  reason there is none), and any divergence between records. Uncertainty shows package and
  per-option confidence, conflicts, limitations and next steps that name the gap each addresses.
  No score, weight, rank, priority, severity, likelihood or preference-ordered column; option
  order is presentation.
- **Executive report** (ADR-0033) — eleven sections in fixed order: reporting frame · executive
  summary · KPI scorecard · findings · anomalies · outlook · SWOT · strategy recommendations · decision
  support · evidence and uncertainty · decisions for the reader. The lifecycle and the data-quality
  grade come first, before any figure. Every section is shown; one with nothing to show says why
  (`empty`, `not_supplied`, `not_available`) rather than disappearing. The summary is a fixed
  selection of existing statements, records and package questions, never prose. Evidence (classes
  1/3/4) and interpretation (class 5) stay in separate blocks; forecasts stay apart from actuals. SWOT,
  recommendations and decision packages appear whole in their own shapes above. No overall or health
  score, KPI rating or colour, target, "top" or "best", severity, likelihood or action plan; order is
  presentation.
- **Verification result and final artifacts** (ADR-0034) — a verification result shows the subject
  (report id or package digest), `passed` or `failed`, every check run with its outcome, and every finding
  with its check, component, location, the reference it checked and a comparison code (`differs`,
  `absent`, `mismatched` …), in check-catalogue order — never sorted by importance, and with no severity,
  confidence or trust grade. **A finding never shows a figure or statement text** (ADR-0035); the reader
  finds the value in the draft it refers to. A **final** report or package
  shows `final — verified` and its `verification_id` before any figure, with the fixed final note that
  final means verified for integrity, not approved, decided or authorised. Its content is otherwise
  exactly the draft's. A failed verification is shown beside the draft, which stays labelled `draft —
  unverified`; nothing is ever presented as final without a passed verification.

## Every report states its basis

At minimum: reporting period · currency · data source **and reader tier** · data-quality
grade · which thresholds applied and where they came from · what was excluded and why.

## Data-quality warnings are not footnotes

If quality is `WARNING`, say so **before** the numbers, not after them. A reader must know
the caveat before forming a view, not once they already have one.

## Data privacy in output

All business data is confidential. What may leave the machine is governed by the disclosure
tiers ([research-policy](research-policy.md)); this section governs what an output shows.

- **Prefer aggregates.** Row-level or named-individual data appears only when the analysis
  genuinely requires it, and **never in a shareable artifact without asking**.
- A shareable output pseudonymises identifying contributors such as customers, and keeps to
  the aggregation floor the engine applies.
- Derived working files go under the session scratchpad or `./businessops-output/`, never into
  the user's source data.
