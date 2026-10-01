# 2026-09-08 — Milestone 2: Vertical Slice

**Milestone:** 2 — Vertical Slice (end-to-end proof on synthetic data)
**Status on completion:** `REVIEW` — awaiting Milestone 2 review
**Supersedes:** None. Follows
[2026-09-08-foundation.md](2026-09-08-foundation.md).

> This milestone was implemented across two sessions; the first hit the context limit after
> writing the implementation and the integration test but before the suite had ever run. The
> second session reconstructed state from the repository, found the suite could not execute
> at all (missing `__init__.py` in `tests/integration/`), fixed it, and completed the
> remaining work. **No M2 test result existed before the second session.**

## 1. Prompt / task performed

Milestone 1 approved; R-02 decided as **file-first v1, no custom MCP servers**. Implement the
vertical slice only: synthetic dataset → ingestion → semantic mapping → data quality → KPI
calculation → Business Context relevance → sales analysis → evidence/provenance →
executive-style output, using the real production architecture rather than a throwaway demo
path. Explicitly not Milestone 3 or later.

## 2. Objective

Prove the approved architecture works end to end on realistic synthetic data before building
the remaining 19 skills, 16 commands, 3 subagents and the connector layer.

## 3. Changes made

### Synthetic dataset

`assets/demo-data/generate_demo_data.py` builds a deterministic 24-month dataset (seed
`20260908`) for an invented wholesale/retail business, "Northwind Provisions Ltd". 2,204
transaction rows, 12 columns, 6 products, 4 regions, 5 salespeople, 24 customers. Both CSV
and XLSX describe the same rows; the workbook is written with the standard library so it
exercises exactly the constructs the Tier 3 reader must handle — shared strings, styled date
cells, a custom GBP currency format, and an inline string. Fixed zip timestamps make
regeneration byte-identical, verified by SHA-256.

Trends were planted deliberately so the analysis layer has something true to find: ~18%
annual growth, a Q4 seasonal peak, "Legacy Crates" declining to near-retirement, "Chilled
Logistics" launching in month 7 and growing fast, the North region outgrowing the others,
and — the finding that matters most — **unit costs rising from month 19 while selling prices
hold**, compressing gross margin.

**A correction worth recording.** The first version of the generator applied regional growth
to *price*, which cancelled the cost inflation: margin ended up *rising* 39.5% → 42.6%, so
the dataset did not contain the trend its own docstring claimed. Rather than reword the
docstring, the generator was fixed — regional growth now shifts order *mix*, never price —
and margin now genuinely compresses (37.26% → 34.41% half over half; 36.83% → 23.57% across
the final six months). A demo dataset that does not contain the trend it advertises is
worthless for proving the analysis layer.

### Ingestion

`biq/ingest/` provides the canonical `Dataset` (carrying source type, path, sheet, reader
tier, warnings and full provenance) and the readers. CSV handles encoding fallback,
delimiter sniffing, type coercion, ragged rows and duplicate headers. XLSX is read at Tier 1
(openpyxl, `data_only=True`) or Tier 3 (zipfile + ElementTree).

The Tier 3 gap identified during architecture review — built-in `numFmt` ids — is now
resolved via an explicit ECMA-376 id set, and any id outside the known set produces an
`unresolved_number_format` warning rather than a guess. Formulas are never evaluated: the
cached value is read, and a formula cell with no cached value yields `None` plus a warning.

### Semantic mapping

`biq/mapping/semantic.py` scores every column against every role on **both** the header name
and the column's actual contents, so a column named `Revenue` full of text does not become
revenue. Thresholds follow the ambiguity protocol exactly: ≥0.90 auto, 0.60–0.89 confirm
required, <0.60 unmapped. One column may fill only one role. Negative patterns stop
`UnitPrice` winning the revenue role.

### Data quality

Four families — structure, missing, duplicates, validity. **A severity/grade distinction was
introduced**: individual findings carry `INFO`/`WARNING`/`CRITICAL` (as the M2 prompt
requires), while the report as a whole carries the architecture's `PASS`/`WARNING`/`CRITICAL`
grade, computed as the highest finding severity (INFO-only ⇒ `PASS`). These describe
different things — one finding versus one verdict — so both vocabularies are kept. This is
an implementation detail, not an architectural change.

### KPI engine

`biq/kpi/registry.py` holds **every numeric formula in BusinessIQ**. Each KPI declares two
independent gates: `requires` (input roles) and `applicable_models` (business models).
Results land in one of four buckets, and `unavailable` versus `not_applicable` is a
distinction users need. Money is `Decimal`; rounding happens once at presentation.

### Business Context relevance

Demonstrated non-trivially. `net_revenue_retention` declares `applicable_models = ("saas",
"marketplace")`; the demo business is `retail`, so it returns `not_applicable`. Switching the
context to `saas` makes the same KPI attempt calculation — proving the classification comes
through the context→applicability architecture rather than a hard-coded result. Meanwhile
`inventory_turnover` *is* applicable to a retailer but the dataset has no inventory column,
so it returns `unavailable`. With no context at all, nothing is suppressed and the output
says relevance filtering is off.

### Materiality, evidence, analysis, output

`biq/materiality.py` implements the three outcomes including `undetermined` — reporting an
unmeasurable change as "not material" would be a quiet lie. Margin uses percentage points.
Every verdict names the threshold that fired and the config layer it came from.

`biq/evidence.py` implements the seven provenance classes with enforcement: a calculated
claim without a formula, user data without a source, or a recommendation missing any of its
six required fields all raise. Global caveats attach to past *and* future claims so a quality
warning cannot be dropped during summarisation.

`biq/analytics/` computes aggregations and candidate findings; `biq/render/executive.py`
produces the report. `biq/pipeline.py` wires steps 1–18 of the analysis framework.

### Skill and command

`skills/biq-sales-intelligence/SKILL.md` interprets computed output and never calculates.
`commands/business-health.md` is a thin orchestrator containing no formulas, no thresholds
and no policy — only sequence, gates and failure conditions.

## 4. Files created

```
assets/demo-data/generate_demo_data.py · northwind_sales.csv · northwind_sales.xlsx
assets/demo-data/business_context.json
lib/python/biq/ingest/{__init__,dataset,readers}.py
lib/python/biq/mapping/{__init__,semantic}.py
lib/python/biq/quality/{__init__,checks}.py
lib/python/biq/kpi/{__init__,registry}.py
lib/python/biq/analytics/{__init__,sales,findings}.py
lib/python/biq/render/{__init__,executive}.py
lib/python/biq/{evidence,materiality,pipeline}.py
skills/biq-sales-intelligence/SKILL.md
commands/business-health.md
tests/fixtures/{__init__,build_fixtures}.py
tests/integration/{__init__,test_vertical_slice}.py
tests/unit/{test_ingest,test_engine_m2}.py
docs/development/2026-09-08-vertical-slice.md   (this file)
```

## 5. Files modified

| File | Change |
|---|---|
| `lib/python/biq/__init__.py` | Export the M2 modules |
| `lib/python/biq/evidence.py` | **Bug fix** — see section 9 |
| `assets/demo-data/generate_demo_data.py` | Margin-compression correction (section 3) |
| `commands/business-health.md` | Added "Trying it on the demo data" |
| `project_plan.md` | M1 → `COMPLETED`, M2 → `REVIEW` with evidence |
| `docs/README.md`, `docs/development/README.md` | Index entries |

**No ADR body modified. No architectural decision changed.**

## 6. Files deleted

None. A temporary measurement probe at `~/.claude/skills/businessiq-m2-probe` was created,
measured and removed (verified). A runtime `.businessiq/` directory was created to
demonstrate context loading and then removed; it is gitignored either way.

## 7. Features implemented

Ingestion (CSV + XLSX Tier 1/Tier 3) · semantic mapping with confirm-below-threshold · the
four-family quality gate with `CRITICAL` halt · the KPI registry with four result buckets ·
Business Context relevance filtering · materiality with three outcomes · the seven-class
evidence ledger · deterministic sales analytics · executive-style rendering · one analysis
skill · one command.

## 8. Tests performed

```
python tests/run_tests.py                                   # 271 tests, system interpreter
<venv>/python.exe tests/run_tests.py                        # 271 tests, openpyxl present
python tests/run_tests.py integration.test_vertical_slice -v
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json --strict
claude plugin validate . --strict
claude plugin details businessiq-m2-probe                   # temporary, removed
python assets/demo-data/generate_demo_data.py               # + SHA-256 determinism check
git check-ignore -q .businessiq/business_context.json
```

## 9. Test results

**271 tests, 0 failures, 0 errors.** Under the system interpreter 4 are skipped (Scenario F
needs openpyxl); under an interpreter with openpyxl 3.1.5 available, **0 are skipped and all
271 pass**, so every required scenario including Tier 1 and cross-tier equivalence has
genuinely executed.

Three errors surfaced when the new unit tests first ran, and all three were investigated
rather than silenced:

1. **A real bug in `evidence.py`.** `confidence` is an explicit `__init__` parameter, so it
   never reached `**extra`; the recommendation validator looked for it there and therefore
   rejected *every* well-formed recommendation. Fixed by checking the explicit parameter.
   Found only because a unit test constructed a valid class-7 claim directly — the pipeline
   does not yet issue recommendations, so integration tests could never have caught it.
2. **Two wrong test fixtures.** A test workbook whose only data cell was empty produced no
   rows, because the reader correctly skips fully-empty rows. The code was right and the
   fixture was wrong; the fixture now has a second populated column.

Earlier in the milestone, the first session's work could not run at all:
`ImportError: Start directory is not importable: tests\integration` — a missing
`__init__.py`. Fixed in the resuming session.

## 10. Issues discovered

| Issue | Resolution |
|---|---|
| Test suite could not execute (missing `tests/integration/__init__.py`) | Fixed |
| `evidence.py` rejected every valid recommendation | Fixed |
| Demo dataset did not contain its documented margin trend | Generator corrected |
| Two unit-test fixtures asserted against correct behaviour | Fixtures corrected |
| Demo context file shipped with no documented way to use it | Command doc updated |
| **Token cost per component is running high** — see section 12 | Recorded as a watch item |

## 11. Decisions made

No ADRs. Three implementation choices inside approved scope:

1. **Finding severity vs report grade** — `INFO`/`WARNING`/`CRITICAL` for findings,
   `PASS`/`WARNING`/`CRITICAL` for the report verdict.
2. **Tier 2 is resolved but not used for reading in M2.** When a managed openpyxl runtime
   exists, reading through it needs out-of-process execution, which is M3. The reader falls
   back to Tier 3 and says so explicitly rather than claiming Tier 2.
3. **The `undetermined` materiality outcome is exercised deliberately**, so the honest
   third answer is proven rather than assumed.

## 12. Architecture changes

**None.** The measurement below is a watch item, not a change.

Always-on cost at M2 is **~271 tok for 2 components** (skill ~150, command ~120). Extrapolated
across the designed 20 skills + 17 commands that is roughly **5,000 tok**, above the
self-imposed ≤3,000 target from ADR-0013. Reference plugins average ~110 per skill and as
little as ~20 per command, so BusinessIQ's descriptions are longer than the norm. Per the M2
instruction not to prematurely optimise, nothing was changed; the standard is set with these
two components and the trend is recorded for review. ADR-0013 already prescribes the
response if it holds: merge components whose descriptions overlap, never thin a description
until it stops matching.

## 13. Project-plan updates

M1 → `COMPLETED`. M2 → `REVIEW` with a per-task evidence table. R-04 updated (built-in
number formats now resolved at Tier 3). R-09 added for the token-cost trend.

## 14. Documentation updates

This record; `project_plan.md`; `docs/README.md` and `docs/development/README.md` indexes;
`commands/business-health.md` demo section. Historical records untouched; no ADR body
modified.

## 15. Remaining work

Milestones 3–14. The slice proves the architecture; it does not implement it broadly. Next is
Milestone 3 (full data layer): complete tiered readers including out-of-process Tier 2,
shared formulas, external references, encrypted-workbook detection, streaming, full
normalisation, the `biq-semantic-mapping` skill wrapper, and field sensitivity classification.

## 16. Git commit reference

Branch `main`. **No commit made** — `CLAUDE.md` section 10 requires commits only on request.
Nothing pushed, no history rewritten. All M0/M1/M2 files remain uncommitted in the working
tree for review.
