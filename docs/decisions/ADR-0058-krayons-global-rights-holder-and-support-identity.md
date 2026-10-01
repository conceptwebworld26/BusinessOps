# ADR-0058 — Prakash Meghani - Krayons Global is the current rights holder and support identity

**Date:** 2026-10-01
**Status:** Accepted — 2026-10-01, by the project owner. Supersedes
[ADR-0054](ADR-0054-businessops-product-identity-and-bops-namespace.md) in one respect only: the current rights
holder of the active BusinessOps product. ADR-0054's product name, plugin identifier and `bops` namespace are
unchanged, and its text is preserved as the historical record.
**Deciders:** Project owner (Prakash Meghani - Krayons Global)

## Context

ADR-0054 (2026-09-30) recorded the rights holder as **Prakash Meghani - Concept Web World**. The manifests, `LICENSE`,
`EULA.md`, `PRIVACY.md` and README carried that name, with the support contact `hello@conceptwebworld.com`.

BusinessOps is to be submitted to Anthropic's plugin directory from the paid Claude account associated with Krayons
Global. The owner decided that the current public identity of BusinessOps changes to match.

## Problem

Which owner and support identity do the current BusinessOps product documents and the distribution package present?
And what happens to the records that name the earlier identity?

## Options considered

### Option A — Keep Prakash Meghani - Concept Web World

Pros: no change. Cons: it no longer matches the owner's decision or the account the submission comes from.

### Option B — Change every occurrence everywhere

Pros: one name in the whole repository. Cons: it rewrites historical decisions, development records and captured
evidence, so they would no longer say what was true when they were written.

### Option C — Change the current identity; preserve the historical records

Pros: the shipped product and current documents name the current owner, and the history stays accurate. Cons: the
repository contains both names, and each occurrence has to be read in its context.

## Decision

Option C.

- The current rights holder, licensor, privacy-policy provider, plugin author and marketplace owner is exactly
  **Prakash Meghani - Krayons Global**.
- The current support and contact address is **krayonsglobal@gmail.com**.
- The decision applies to the current, public BusinessOps product and its distribution package:
  - `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`;
  - `LICENSE`, `EULA.md` and `PRIVACY.md`;
  - `README.md`;
  - the current-state section of `project_plan.md`;
  - the package `dist/businessops/`, generated from these by `scripts/build_distribution.py`.
- Historical ADRs (ADR-0054 to ADR-0057 included), dated development records and captured evidence are **not
  rewritten**. They keep the identity that was current when they were written.
- Unchanged:
  - the product `BusinessOps`, slug `businessops` and prefix `bops`;
  - the MCP server `bops-verifier` and tool `mcp__plugin_businessops_bops-verifier__recompute`;
  - the licence `LicenseRef-BusinessOps-Proprietary`;
  - the repository <https://github.com/conceptwebworld26/BusinessOps>;
  - the plugin path `dist/businessops`.

## Reason

The directory listing, licence, end-user agreement, privacy policy and support channel must name the party that
currently stands behind BusinessOps. The project's records are evidence of how BusinessOps was built, so they keep the
identity of their time (ADR-0054's own approach to the BusinessIQ names).

## Consequences

**Positive**
- The submitted package and current documents present one consistent owner and support contact.
- The development history stays accurate.

**Negative**
- Both identities appear in the repository. The old one remains only in historical records, none of which is shipped.
  Each occurrence is classified in
  [`2026-10-01-businessops-krayons-global-identity-migration.md`](../development/2026-10-01-businessops-krayons-global-identity-migration.md).

**Legal scope.** This change updates the repository's identity on the product owner's decision. It does not record or
claim a legal assignment or transfer of rights, and the ownership was not independently verified here. Any separate
legal assignment or transfer that may be required is outside this repository change. Only names and addresses were
replaced in `LICENSE`, `EULA.md` and `PRIVACY.md`; their legal wording is unchanged and has not been legally reviewed.
