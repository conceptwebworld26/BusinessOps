# ADR-0050 — The disclosure gate establishes the provenance of every request fragment from the workspace's business data

**Date:** 2026-09-26
**Status:** Accepted — 2026-09-26, by the project owner. The M13-DEF-13 remediation prompt directed this boundary
("a deterministic, enforceable provenance-aware boundary immediately before external research dispatch") and authorised
implementing it.

- **What acceptance approves.** The internal-value boundary described here, its place in `gate.assess()`, two reason
  codes, one field on the refusal record, its tests and governance. Disclosure tiers, sensitivity classes and the
  classification rules are unchanged.
- **Implemented 2026-09-26**, in the same task (`docs/development/2026-09-26-m13-def-13-remediation.md`).

**Deciders:** Project owner (direction and implementation authorised, 2026-09-26), raised by M13-DEF-13.
**Supersedes:** none.
**Amends:** none. It **applies** [ADR-0009](ADR-0009-comparative-intelligence-privacy-boundary.md), whose rule that
"classification is a property of the data, not the query: every field carries a sensitivity class from ingestion
onward" the gate did not previously apply to a request's free text. ADR-0009's text is not edited.
**Relates to:** ADR-0006 and ADR-0014 (the scout has no file access; unchanged), ADR-0017 (the brief is the only
payload; unchanged), ADR-0012 (single home for each rule), ADR-0043 (`fixed_product`), M13-DEF-13.

## Context

In all three runs of the M13.2 eval case `d05`, and again in all three runs of the 34-case re-evaluation, the customer
name from the staged `northwind_sales.csv` was briefed to `biq-research-scout` inside the query text ("… company
profile", "… trends"). The run reported that "the privacy check passed", and it had.

The gate judged a request by its **shape**:

- a public-term *key* on the prohibited list (`customer`, `rows`, `ledger` …) was refused;
- a derived value was judged by the `source_sensitivity` its **caller declared**;
- everything else — the subject, every other term value, the operation id — was public by construction.

A customer name passed as a *subject* has a legitimate shape, so it got Tier 0. M10.2-R.14 had already recorded the
same gap for figures: an internal figure under an unlisted key such as `our_revenue` was authorised into the query.

The data's own classification existed all along. `privacy.sensitivity` classifies every column at ingestion (for
example `Customer` → `never`, `OrderID` → `restricted`, `Product` → `internal`, `Region` → `public`). The gate never
consulted it.

## Decision

1. **The gate builds an internal-value register on every assessment, from the working directory's business data.**
   - `research/boundary.py` finds the business data files under the working directory (`.csv`, `.tsv`, `.xlsx`,
     `.xlsm`), reads every sheet with the existing stdlib readers, and classifies each column with the existing
     ingestion rules.
   - It keeps the values of every column that is **not** `public`, each with its provenance: class, column and file.
   - It keeps them in memory only. Persisting them would make a second copy of the data the boundary protects.
2. **The register is not caller-controlled.**
   - `workspace_register()` takes no argument.
   - No request field, descriptor class or flag can supply, empty or relabel it. The register and each provenance
     record are immutable.
   - The installed plugin's own tree is never read. It holds only the synthetic demo data and test fixtures
     (`CLAUDE.md` §3). Its location comes from the module's own path, not from any input.
3. **Every caller-supplied fragment is screened**, whatever field carries it:
   - the subject;
   - each public-term key and value;
   - each derived descriptor's label and value;
   - the operation id, purpose, notes and source requirements;
   - the destination's provider and description.

   A fragment matches when it contains a registered value **whole**, after normalisation (case, punctuation and
   spacing). An identifier's distinctive number also matches without its prefix.

   Separately, an exact figure — a decimal, a rate, a currency amount or a thousands-separated number — in the subject,
   a term value (except a `*_band` term) or a descriptor label has **no public provenance**. It is treated as derived
   internal material. Internal figures travel only as `AggregateDescriptor`s, which the Tier 1 checks judge.
4. **The decision follows the existing class-to-tier rule. No second policy is added.**
   - A value from a `never` column is Tier 3: **refused at every tier, with no approval path**.
   - Any other internal material is refused at Tier 0 and Tier 1. At Tier 2 it takes the existing path:
     `ALLOW_WITH_APPROVAL`, showing the verbatim text.
   - A finding **outside the query text** (the operation id, the destination, a note) is refused at every tier. The
     approval covers only the text the user is shown.
   - The decision is never `ALLOW`.
5. **Fail-closed.** If the register cannot be built, the gate refuses with `internal_boundary_unverifiable` and offers
   no alternative, because none could be checked. That happens when:
   - a data file cannot be read;
   - a file exceeds 100 MB;
   - there are more than 50 data files;
   - there are more than 20,000 directory entries.
6. **The refusal is a privacy block, and it says so.**
   - The reason code is `internal_business_value`.
   - The explanation states that no research was performed and that this is not a finding that no public source
     exists.
   - It names the field, column and file, never the value. A public-term key is named only when the key is itself
     clean.
   - Every refusal record carries `research_performed: false`.
   - The Tier 0 alternative is rebuilt from the fragments that survive the screen and vetted again. If nothing
     survives, it has no text, and it asks the user to name the industry, market or public company to research.
7. **The capability chain is unchanged.** Only a gate-issued, intact, authorised `DisclosureDecision` makes a
   `RetrievalRequest`, and only that makes a `ScoutBrief`. `open_retrieval`, both closers and `ScoutRetriever` all run
   `assess()`, so every category, intent, command and route passes the same screen.

## Consequences

- The d05 pattern is refused deterministically. Researching a public company named as the subject still works at
  Tier 0, provided that name does not also appear in a non-public column of the workspace's data.
- M10.2-R.14's recorded limitation — an internal figure under an unlisted term key — is closed. Its pinning test now
  asserts the refusal.
- A value in an `internal` column that is also ordinary vocabulary (a product called "Storage") is refused at Tier 0 and
  offered Tier 2. This is conservative in the direction ADR-0009 requires.
- Each assessment reads the workspace's data files. That cost is linear in their size: about 0.3 s for the demo
  dataset.
- M13-DEF-13 becomes `fixed_product` under ADR-0043, verified deterministically. No live evaluation was run.

## Known limits (recorded, not hidden)

- **Only the working directory is screened.** Business data held outside it is not screened unless it is also inside.
  The commands work on files in the user's project folder.
- **Whole values only.** A fragment of a registered value — one word of a two-word customer name — does not match.
  Matching fragments would need a notion of distinctiveness that the data does not carry.
- **The classification rules decide what is public.** A column the ingestion rules class as `public` (for example
  `Segment`) is not registered. Changing those rules is a classification decision, not a boundary one.
- **Business Context** (`./.businessiq/business_context.json`) is not screened by this boundary. Its `x-privacy`
  classes already govern which of its fields may form a Tier 0 term.
- **Model-side routes.** The model can still call web tools itself. The boundary governs the research pipeline and the
  scout brief. The scout's missing file access remains the structural backstop (ADR-0006), unchanged.

## Revisit when

- the engine keeps a record of the datasets it has ingested that the gate could consult beyond the working directory;
- column classification gains an owner-reviewed override;
- a distinctiveness measure makes partial-name matching sound.
