# ADR-0008 — Tiered `.xlsx` ingestion with a managed dependency

**Date:** 2026-09-08
**Status:** Accepted
**Amends:** ADR-0002 (the "stdlib only, no dependencies" clause; ADR-0002's core decision —
deterministic code produces every reported figure — is unchanged)
**Deciders:** Project owner (architecture review), Claude

## Context

ADR-0002 committed to a stdlib-only engine. Architecture review challenged whether that
delivers *production-grade* Excel ingestion, correctly noting that a partial parser is worse
than none: it misreads data silently, which is this product's worst failure mode.

Everything below was verified on this machine during the review, not assumed.

**What the environment actually provides:**

| Probe | Result |
|---|---|
| Claude Code `Read` tool on `.xlsx` | **Cannot read it** — "This tool cannot read binary files." No built-in path exists. |
| `pip` | 24.3.1 present |
| PyPI reachable | Yes — resolved `openpyxl` latest = 3.1.5 |
| `venv` + `ensurepip` | Both available |
| npm registry | Reachable (`xlsx` 0.18.5) |
| System Python packages | stdlib only — no pandas, numpy, openpyxl |

**Both candidate readers were then built and run against the same realistic test workbook**
(two sheets; styled date cells; a custom GBP currency format; a built-in percent format;
formula cells with cached values; inline strings; shared strings):

| Capability | stdlib parser (written for this review) | openpyxl 3.1.5 (installed in an isolated venv) |
|---|---|---|
| Sheet detection via rels graph | ✅ `['Sales', 'Costs']` | ✅ `['Sales', 'Costs']` |
| Shared strings | ✅ | ✅ |
| Inline strings (`t="inlineStr"`) | ✅ `EMEA` | ✅ |
| Date cells via `styles.xml` numFmt | ✅ `45000` → `2023-03-15` | ✅ `2023-03-15` |
| 1900 / 1904 date systems | ✅ detected from `workbookPr` | ✅ |
| Formula cells — cached value, never evaluated | ✅ 2 cells, `15250.75` / `6100.3` | ✅ same values |
| Currency symbol from format code | ✅ `£` | ✅ `"£"#,##0.00` |
| Built-in numFmt ids (e.g. id 10 = `0.00%`) | ❌ **misclassified percent as plain number** | ✅ resolved |
| Streaming / constant memory | ✅ `iterparse` | ✅ `read_only=True` |

Values agreed everywhere both succeeded. The stdlib parser has one real defect found by
probe — it resolves only *custom* number formats, not the ~50 built-in ECMA-376 ids. That
specific gap is a bounded lookup table. What it stands for is not bounded: openpyxl carries
years of hardening against the long tail of real-world workbooks (malformed archives, odd
encodings, merged cells, huge shared-string tables, `.xlsm`, pivot caches) that a
review-week parser cannot match.

## Problem

What reads `.xlsx` in production, given that the environment offers no built-in reader,
guarantees no third-party package, and cannot guarantee network access either?

## Options considered

### Option A — stdlib parser only (ADR-0002 as originally written)
- Pros: zero install; works offline; no supply-chain surface.
- Cons: real-world robustness unproven and the failure tail is long. A parser that quietly
  misreads a date column as integers produces a confidently wrong analysis — precisely the
  outcome the product exists to prevent.

### Option B — require the user to `pip install openpyxl`
- Pros: simple to specify.
- Cons: it is exactly the "manually install an undocumented dependency" the review rules
  out. Most users hit an import error and stop.

### Option C — tell users to export CSV
- Pros: trivially reliable; CSV needs no parser beyond stdlib `csv`.
- Cons: unacceptable as the *only* path — the product promises Excel ingestion, and export
  loses sheet structure, types and formats. Retained as a floor, not a strategy.

### Option D — tiered reader with an automatic, consented, isolated bootstrap
Resolve a reader at runtime in preference order, and never guess when the chosen tier cannot
handle a construct.

## Decision

**Option D.** A `biq-xlsx-reader` resolver selects the highest available tier:

| Tier | Reader | Condition | Install |
|---|---|---|---|
| 1 | openpyxl already importable | present in the active interpreter | none |
| 2 | openpyxl in a **plugin-managed venv** at `~/.claude/businessiq/runtime/` | Python + pip + network available | **one-time, disclosed, consented** |
| 3 | **stdlib parser** | Python available, no network or install declined | none |
| 4 | **Guided CSV export** | no usable Python | none |

Rules that make this safe:

1. **The bootstrap asks once, in plain terms** — what will be installed (`openpyxl`, pinned),
   where (an isolated venv under `~/.claude/businessiq/`, never the system or project
   interpreter), and that declining drops to Tier 3. It is a write action under the
   permission model and is gated like one.
2. **The stdlib tier is complete for a documented subset, and refuses outside it.** It must
   detect constructs it does not fully support — unresolvable number formats, shared formulas,
   external references, encrypted workbooks — and **escalate or halt rather than guess**.
   Every dataset records which tier read it, and the quality report carries a `WARNING` when
   Tier 3 was used with any unresolved format.
3. **The source file is opened read-only at every tier.** Never written, never moved.
4. **Formulas are never evaluated** — the cached value is read. A formula cell with no cached
   value is a `WARNING`, not an invented number.
5. **Cross-tier equivalence is a test requirement:** the same fixture read at Tier 1 and
   Tier 3 must produce identical canonical datasets, or the fixture documents the difference.

## Reason

The probes turned this from a preference into a measurement. Option A's weakness is real and
was caught by probe within an hour — the built-in format gap — which is strong evidence that
a hand-written parser's long tail is longer than a week of work. Option B is ruled out by the
review. Option C cannot be the product.

Option D is the only one that is *simultaneously* production-grade on the common path and
functional on the degraded one. Crucially, it removes the failure mode that mattered: with
tier recorded on every dataset and a hard refusal outside the supported subset, a Tier-3
read can be *incomplete* but cannot be *silently wrong*.

The stdlib tier is not a token gesture. It was built and run during this review, handles
every hard construct except built-in format ids, and is the only thing standing between an
offline user and no product at all.

## Consequences

**Positive** — reliable Excel ingestion on the common path; graceful degradation offline;
no manual dependency step; provenance of *how a file was read* becomes part of the dataset
record, which feeds the evidence ledger.

**Negative** — a dependency and its supply chain enter the product (mitigated: single,
pinned, isolated, consented, optional). Four tiers mean four code paths and a cross-tier
equivalence test burden. `~/.claude/businessiq/runtime/` is state outside the repository that
must be documented and removable.

**Follow-up required** — Milestone 1 ships the resolver and the consent flow; Milestone 2
ships both readers, the built-in numFmt table for Tier 3, the unsupported-construct detector,
and the cross-tier equivalence tests. `README.md` documents the venv location and how to
delete it.

## Revisit when

The plugin platform provides a managed runtime or a declared-dependency mechanism, at which
point Tiers 1–2 collapse into a manifest entry.
