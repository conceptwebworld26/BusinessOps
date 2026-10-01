# 2026-09-08 — Milestone 3: Data Layer (Full)

**Milestone:** 3 — Data Layer
**Status on completion:** `REVIEW` — awaiting Milestone 3 review
**Supersedes:** None. Follows
[2026-09-08-vertical-slice.md](2026-09-08-vertical-slice.md).

## 1. Prompt / task performed

Milestone 2 approved. Make ingestion, canonical representation, normalization, the semantic
mapping foundation and field-level sensitivity classification robust enough to support the
rest of the product: all four reader tiers, out-of-process Tier 2, formula/external-reference/
encryption/macro handling, streaming awareness, expanded cross-tier equivalence, adversarial
tests, and privacy-preserving aggregation primitives. The M2 vertical slice had to keep
working throughout. No Milestone 4 work.

## 2. Reader tiers

| Tier | Reader | State after M3 |
|---|---|---|
| 1 | openpyxl in this interpreter | `read_only=True`, `data_only=True`; hidden-sheet and merged-cell behaviour documented and warned; open failures wrapped in a clear error |
| 2 | openpyxl in the managed runtime | **New: real out-of-process reading.** A worker module (`ingest/_managed_read.py`) runs under the managed interpreter and returns JSON; dates are revived so types match the other tiers |
| 3 | stdlib parser | Built-in and custom number formats, 1900/1904, shared strings, inline strings, cached formula values, workbook/worksheet relationships, unresolved-format warnings |
| 4 | Guided CSV export | **New:** structured guidance naming the reason, the required structure, what an export loses, and that the source is untouched |

Workbook-level constructs are now established **before any cell is read**, by
`ingest/workbook.py`. Encryption and corruption therefore fail before a tier is even chosen,
rather than midway through parsing.

`_managed_read.py` is a real module rather than an embedded script string so it can be read,
linted and tested. A test parses its AST and asserts it imports no `subprocess`, `os`,
`urllib` or `socket`, and calls no `open`/`exec`/`eval` — the worker reads and nothing else.

## 3. Managed runtime

Unchanged in its guarantees, extended in reach. `resolve()` remains pure inspection and never
installs; `bootstrap()` still raises `ConsentRequiredError` unless consent is literally
`True`; `allow_bootstrap: "always"` is still deliberately unsupported, because ADR-0010 makes
approval per-action. What M3 adds is that a managed runtime, once consented to, is now
actually *used* for reading rather than falling back to Tier 3 with an apology.

## 4. Canonical dataset

`ingest/canonical.py` wraps a raw `Dataset` and adds, per field: original name, normalized
name, inferred kind, currency evidence, missing/ambiguous counts and a sensitivity class.

The derived/source distinction is explicit in the API, not just in prose:

    raw_rows()          exactly what was read
    normalized_rows()   the derived, typed representation

The source file is never opened for writing on any path, and a test asserts byte-identity
before and after reading for every fixture, including the ones that raise.

Processing mode (`full` / `streamed` / `sampled` / `aggregated`) and `rows_examined` are
recorded in provenance, and an incomplete pass adds a **global ledger caveat** so no figure
derived from a sample can be presented as if the whole dataset had been analysed.

## 5. Normalization

`biq/normalize.py` handles strings, integers, decimals, percentages, dates, datetimes,
booleans, currency values and missing markers, across common representations: thousands
separators, currency symbols and ISO codes, European and Anglo decimal conventions,
accounting parentheses for negatives, percentage signs, whitespace, and the usual missing
tokens (`n/a`, `NULL`, `-`, `#N/A`).

**The ambiguity rule is the point of this module.** `1,234.56` and `1.234,56` are decidable.
`1,234` and `1.234` are not — they differ by a factor of a thousand depending on a convention
the file never states. Those return `AMBIGUOUS`, preserve the original text, set
`confirm_required`, and produce a warning naming *both* readings. A caller with independent
evidence can pass `assume_separator`; nothing guesses on its own.

Dates work the same way: `15/01/2025` is decidable because 15 exceeds 12; `03/04/2025` is
not, and is reported rather than resolved. `infer_day_first` resolves a whole column when any
value in it decides the question, which is column-level evidence rather than a guess.

Money is `Decimal` throughout.

**A real bug this surfaced:** the M2 CSV reader coerced `"1.234"` straight to a float,
silently deciding the separator question before the normalizer could flag it. The reader now
leaves genuinely ambiguous numerics as text. Found by an M3 test, not by inspection.

## 6. Currency

Detected from symbols, ISO codes and cell number formats, and recorded per field and per
dataset. Three behaviours, all tested:

- **Mixed currencies in one dataset** → `CRITICAL`. Totals across currencies would be
  meaningless, so the pipeline halts rather than summing them.
- **Context says GBP, data says USD** → `CRITICAL` contradiction. Both facts are preserved;
  no exchange rate is applied.
- **No live FX** anywhere. Not in M3, by design.

## 7. Formulas, external references, encryption, macros

| Construct | Behaviour |
|---|---|
| Formula with a cached value | Cached value used. Never evaluated |
| Formula without a cached value | `None` + warning. **Never invented** |
| Shared formulas | Detected and counted; read from cached values like any other formula |
| External references | Detected from `xl/externalLinks/` and from `[n]Sheet!A1` formulas. The external file is **never opened or downloaded**; the cached value is used and flagged as possibly stale |
| Encrypted / password-protected | Detected by OLE magic bytes. Fails clearly and points to an unprotected copy or CSV export. **No password prompting, no cracking, no bypass** |
| Macros (`.xlsm`, `vbaProject.bin`) | Detected; workbook read for values only. **Macros are never executed** |
| Corrupt archive / malformed XML | Clear failure naming the problem |

## 8. Field-level sensitivity classification

`biq/privacy/` implements ADR-0009's requirement that classification is a property of the
data. Six classes, ordered, each mapping to the minimum disclosure tier that may carry it:

| Class | Min tier | Examples |
|---|---|---|
| `public` | 0 | region, category, period, currency |
| `derived_safe` | 1 | revenue, cost, quantity — aggregate only |
| `conditional` | 2 | own business name, in the named case |
| `internal` | 2 | product names, notes — **the default for anything unmatched** |
| `restricted` | 2 | salesperson, order id — individual people and transactions |
| `never` | — | credentials, PII, customer identity. **No approval path** |

Two signals, stricter wins: the header name, and the actual content. Content matters because
a column called `Notes` full of email addresses is precisely what a name-only classifier
leaks — and a single confirmed hit in the sample escalates, because a majority rule would let
one credential through.

The vocabulary lives in one module and is imported by `context/privacy.py`, so Business
Context fields and dataset fields cannot drift apart (ADR-0012).

**Two real bugs found here by tests:**

1. ISO dates matched the phone-number pattern, so **every date column was classified
   `never`** — which would have silently broken Tier 0 research, whose whole premise is that
   periods and dimensions are public. Content rules now skip values that parse as dates or
   plain numbers, and a phone number must carry at least nine digits.
2. `permitted_at_tier` treated the tier map as a *maximum*, so a `derived_safe` aggregate was
   accepted at Tier 0 — a query meant to carry public terms only. The map is a **minimum**
   required tier; higher tiers demand more approval.

## 9. Privacy-preserving aggregation foundation

`privacy/aggregation.py` provides the reusable primitives for ADR-0009's Tier 1 gate:
entity counting, banding for counts and amounts, rate construction, whole-query
re-identification assessment, and `assess_disclosure` applying all four checks.

**Nothing here performs external research or makes any network call.** It is the foundation
a later intelligence layer consumes.

The re-identification check evaluates the *whole* attribute set, because that is where naive
anonymisation fails: industry alone is fine, geography alone is fine, and industry plus
micro-geography plus a narrow revenue band can be one company.

## 10. Semantic mapping foundation

Strengthened, not replaced. Scoring now records four signals — header evidence, content
evidence, type agreement and negative evidence — in an `Evidence` object, so every mapping
answers *why*:

> Column 'NetRevenue' maps to 'revenue' with confidence 1.00 (auto). Evidence: header
> 'NetRevenue' is a strong name for revenue; content is number in 100% of sampled values,
> matching what revenue expects.

Rejected candidates are retained too, so `explain(role)` can say why a role went unmapped
rather than merely reporting that it did. The M2 confirm-below-threshold behaviour is
unchanged and still tested.

**The production `biq-semantic-mapping` skill was deliberately not created** — the project
plan assigns the skill wrapper to a later milestone; M3 is the engine layer only.

## 11. Cross-tier equivalence — the definition

Tier 1 and Tier 3 are **equivalent** for a workbook when:

1. the same sheet is selected,
2. column names match exactly and in order,
3. row counts match,
4. every cell's *canonical value* matches — dates as `date`, numbers as numeric, text as
   text.

Metadata is explicitly **not** required to match: the reader tier differs by definition, and
each reader legitimately emits its own warnings. Requiring byte-identical internals would
test the readers' implementation rather than the data they produce.

Corpus: rich types (dates, currency, percentages, formulas, shared + inline strings, mixed
types), multi-sheet with a hidden sheet, empty rows and missing values, duplicate headers,
the 1904 date system, an unresolved custom number format, and the full 2,204-row demo
workbook. Tier 2 is additionally compared against Tier 3 on the demo workbook.

## 12. Files created

```
lib/python/biq/normalize.py
lib/python/biq/ingest/canonical.py
lib/python/biq/ingest/workbook.py
lib/python/biq/ingest/_managed_read.py
lib/python/biq/privacy/{__init__,classes,sensitivity,aggregation}.py
tests/fixtures/build_workbooks.py
tests/integration/{test_data_layer,test_tier2_runtime,test_performance}.py
tests/unit/test_engine_m3.py
docs/development/2026-09-08-data-layer.md   (this file)
```

## 13. Files modified

| File | Change |
|---|---|
| `ingest/readers.py` | Tier 1 hardening; Tier 2 dispatch; Tier 3 workbook facts, external refs, malformed-XML failure, shared coercion helper; Tier 4 guidance; CSV ambiguity fix |
| `ingest/__init__.py` | Export canonical, workbook, managed reader |
| `ingest/workbook.py` | Missing/unreadable files now raise `ConfigError` |
| `mapping/semantic.py` | `Evidence`, `explain()`, rejected candidates |
| `mapping/__init__.py` | Export `Evidence` |
| `quality/checks.py` | Fifth family: currency and normalization ambiguity |
| `pipeline.py` | Builds the canonical view; records sensitivity and incomplete passes in the ledger; passes canonical + context to the quality gate |
| `context/privacy.py` | Imports the shared vocabulary instead of defining its own |
| `privacy/classes.py` | Tier semantics corrected to a minimum |
| `privacy/sensitivity.py` | Date/number exclusion in content rules |
| `biq/__init__.py` | Export `normalize`, `privacy` |
| `tests/unit/test_business_context.py` | 6-class assertions + a no-weakening test |
| `tests/unit/test_engine_m2.py` | Check-family assertion allows the M3 addition |
| `tests/unit/test_ingest.py` | Case-insensitive message assertion |
| `project_plan.md`, `README.md`, docs indexes | Status |

**No ADR body modified. No architectural decision changed.**

## 14. Test results

**403 tests, 0 failures, 0 errors.** 17 skipped on the system interpreter (Tier 1 and Tier 2
need openpyxl); under an interpreter with openpyxl 3.1.5 only **1** skips — a test that is
skipped *by design* when openpyxl is present, because it asserts the failure path of a worker
without it.

M2 baseline before M3: 271 tests passing. After M3: all still passing, plus 132 new.

Bugs found by these tests and fixed: the CSV separator coercion, the date/phone false
positive, the tier-map direction, and `workbook.inspect` leaking a raw `OSError`.

## 15. Performance baseline

| Operation | Rows | Time | Rate |
|---|---|---|---|
| Demo CSV | 2,204 | 0.04s | ~53k rows/s |
| Demo XLSX Tier 3 | 2,204 | 0.42s | ~5.3k rows/s |
| Canonical build (demo) | 2,204 | 0.41s | ~5.4k rows/s |
| Large CSV | 60,000 | 0.61s | ~98k rows/s |
| Canonical build (large) | 60,000 | 0.25s | ~240k rows/s |

Measurement, not benchmarking. Test thresholds are deliberately loose — they exist to catch
an order-of-magnitude regression, not to police milliseconds. Memory was not instrumented;
the readers stream rather than materialising the XML tree, and `read_only=True` at Tier 1
does the same.

## 16. Limitations

1. **Merged cells** — the value is read from the top-left cell; the rest are empty. In
   `read_only` mode openpyxl does not expose merged ranges, so a merged header can leave a
   column unnamed. Warned, not silently reconciled.
2. **Hidden sheets** are skipped unless named explicitly, and warned when read.
3. **Streaming is coarse** — mode is chosen by row count against a threshold. There is no
   true chunked pipeline yet; the honest statement is that processing mode is *recorded*
   correctly, not that very large files are optimised.
4. **Tier 2 costs a process spawn** per workbook. Acceptable for one file; it would need
   batching if many files were read in a loop.
5. **Sensitivity classification is heuristic** and errs conservative — it will sometimes
   classify a harmless column as `internal`. That is the correct direction to err.
6. **Currency conversion is out of scope**, by design. Mixed currencies halt.

## 17. Remaining work

Milestones 4–14. Next is Milestone 4 (Data Quality, full): the remaining check families,
`quality_report.schema.json`, and one broken fixture per family.

## 18. Git commit reference

Branch `main`. **No commit made** — `CLAUDE.md` section 10 requires commits only on request.
Nothing pushed, no history rewritten.
