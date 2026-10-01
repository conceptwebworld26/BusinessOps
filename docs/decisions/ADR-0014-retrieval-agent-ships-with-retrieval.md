# ADR-0014 — The retrieval agent ships with the first milestone that retrieves

**Date:** 2026-09-10
**Status:** Accepted
**Relates to:** [ADR-0006](ADR-0006-three-subagents-not-eight.md) (three subagents),
[ADR-0009](ADR-0009-comparative-intelligence-privacy-boundary.md) (the disclosure boundary).
Neither is superseded or amended; this decision fixes *when* a control they both rely on is
delivered.
**Deciders:** Project owner, Claude (Milestone 9 architecture review)

## Context

Milestone 9 is the first milestone in which information may leave the machine. The
Milestone 9 architecture review traced the disclosure boundary and found that the roadmap
delivered its two enforcement mechanisms in different milestones.

The first is the **disclosure gate**: query construction runs the ADR-0009 tier checks
before any tool call. That lands in M9.

The second is **capability separation**: `biq-research-scout`, the agent that performs
retrieval, is granted web tools and **no file access**, so it cannot read the dataset even
if instructed to. That was scheduled for M11 — which itself depends on M9.

So as sequenced, M9 would have performed external retrieval with only one of its two
controls present, and the missing one is the control the repository leans on hardest:

- ADR-0006 (Consequences): "the internal/external boundary is enforced by capability, not
  by instruction".
- ADR-0009 (Enforcement): "The structural backstop from ADR-0006 … **is what makes this
  safe in practice**"; (Consequences) "the agent tool-split makes Tier 3 **structurally
  unreachable** rather than merely forbidden".
- `architecture.md` §10: "The tool split above is what makes the Tier-3 privacy boundary
  **structural rather than advisory**."
- `README.md`, already shipped to users: "**Structural, not just promised:** the agent that
  performs web research has no file-system access and cannot read your data even if
  instructed to."

ADR-0006 introduced the property almost in passing — "a useful side effect" of a decision
made for context isolation and fan-out. ADR-0009 then built its safety argument on it. That
drift is how the sequencing gap survived review until now.

## Problem

Is capability separation a **precondition** of external retrieval, or a later hardening
step that M9 can ship without?

## Options considered

### A. Leave the scout in M11; add a compensating control in M9
Retrieval runs in the main thread, with the disclosure gate as the sole sanctioned path.

- Pros: cheapest; no roadmap change; M9 ships sooner.
- Cons: **it cannot restore the property.** The main thread holds file access and web
  access simultaneously. A compensating control is code or instruction *inside* a context
  that retains both capabilities, so whatever it forbids, that context remains *able* to
  read a file and call a web tool. This does not produce a weaker version of the guarantee;
  it produces a different kind — advisory — while four documents assert the structural kind
  and one of them is a published user-facing promise. It would also make the gate a single
  point of failure at exactly the moment it is least proven, being newly written.

### B. Move all three M11 agents into M9
- Pros: preserves the property; empties M11.
- Cons: `biq-data-profiler` and `biq-analysis-verifier` have nothing to do with retrieval.
  The verifier's consumers (`/executive-report`, `/decision-support`) do not exist until
  M10. Moving them buys no safety and inflates M9 — the milestone that least needs extra
  surface.

### C. Resequence M9 / M10 / M11
- Pros: preserves the property.
- Cons: the largest schedule change available. M11 currently depends on M9, so the
  dependency would have to be inverted or split anyway — which is option D with more
  disruption.

### D. Move only `biq-research-scout` into M9
- Pros: preserves the property at the smallest possible cost — one agent definition, one
  tool grant, one manifest entry, roughly 80 always-on tokens. The scout is the only M11
  component M9's security argument depends on. M11 keeps the other two, and its dependency
  *narrows*: neither remaining agent depends on M9, which also dissolves the current
  M9↔M11 circularity.
- Cons: M11 becomes a smaller milestone and must be explained as such.

## Decision

**Option D.** `biq-research-scout` ships with Milestone 9. `biq-data-profiler` and
`biq-analysis-verifier` remain in Milestone 11.

The general rule this expresses, which is the durable part:

> **The retrieval agent ships with the first milestone that retrieves.** Capability
> separation is a precondition of external retrieval, not a later hardening step.

And its corollary:

> **A security test ships with the component whose property it proves**, not with a
> milestone number.

ADR-0006's follow-up assigned the scout's no-file-access test to "Milestone 10" — which, by
content, is the current M11 after the Revision-2 renumbering. That test moves with the
scout into M9 and is now `tests/unit/test_research_scout_boundary.py`. It asserts against
the *declared tool grant*, not against behaviour, because a future grant of `Read` would
silently convert a structural guarantee back into a written policy and nothing else in the
suite would notice.

## Reason

The two mechanisms fail independently, which is the entire value of having both. The gate
prevents a *correct* implementation from sending internal data. The scout prevents *any*
implementation — correct, defective, or subverted by an adversarial retrieved page — from
reading it in the first place. Shipping the gate alone would mean a single defect in the
newest, least-proven component in the system could put business data on the network.

The cost of avoiding that is one agent definition. There is no version of this trade where
deferring the control is the better engineering decision; the only real question was
whether to move one agent or several, and moving one is sufficient.

## Consequences

**Positive** — M9 retrieves with both controls present; ADR-0009's central safety claim
becomes true when the code it describes exists rather than a milestone later; the README's
published promise holds from the first retrieval; the M9↔M11 circular dependency
disappears; the security test lives with the thing it protects and will not drift again if
the roadmap is renumbered.

**Negative** — M11 is a smaller milestone than the roadmap originally described and must be
explained. M9 carries slightly more surface, and about 80 more always-on tokens
(R-09 — which ADR-0013 governs, and which is not a reason to decline a security control).

**Follow-up required** — `project_plan.md` moves the scout and its test from M11 to M9 and
records M9's real dependencies (M1, M3, M5, M6, M7). The M9 implementation must ensure no
retrieval path exists that does not go through both the gate and the scout.

## Revisit when

A second retrieval path is proposed — an MCP server that fetches external content (M12) is
the likely candidate. The rule above applies to it unchanged: whatever performs the
retrieval must not also be able to read business data.
