# ADR-0013 — The token budget is self-imposed, and the real constraint is discriminability

**Date:** 2026-09-08
**Status:** Accepted
**Corrects:** `architecture.md` §2 as originally written, which presented a
"budget ceiling: 4,000 tokens always-on" in a way that implied a platform limit
**Deciders:** Project owner (architecture review), Claude

## Context

The original architecture asserted a 4,000-token always-on ceiling and described enforcing
the design against it. Architecture review asked whether that figure is an actual platform
constraint or an observed measurement, and instructed that the architecture must not be
optimised against an assumed limit.

**It was neither observed nor documented. I chose the number.** It was a reasonable-sounding
round figure above the ~3.4k estimate, presented with more authority than it had earned.
That is the error being corrected here.

## What was verified during review

**Documented hard limits** (official Anthropic skill-authoring guidance, read locally):

| Limit | Value | Nature |
|---|---|---|
| Skill `name` | 64 characters | Hard |
| Skill `description` | 1024 characters | Hard |
| SKILL.md body | under 500 lines | **Guideline** — "for optimal performance" |

**Loading behaviour** — confirmed by official guidance *and* by measurement:

> "At startup, only the metadata (name and description) from all Skills is pre-loaded.
> Agents read SKILL.md only when the Skill becomes relevant."

| Component | Always-on | On-invoke | Evidence |
|---|---|---|---|
| Skill | name + description only | full body | `marketing`: ~110 tok vs ~1.5k–6.7k |
| Command | description only | full body | `code-review`: ~20 tok vs ~2.5k |
| Agent | name + description only | full prompt | `feature-dev`: ~60–80 tok vs ~570–850 |
| MCP server | **nothing** | tool schemas at runtime | `marketing` reports 13 servers "not counted" |

So skills, commands and agents all contribute continuously — but only their descriptions.
Bodies are progressively disclosed. Reference files and scripts cost **zero** until read.

**Is there an aggregate ceiling?** A probe plugin was built at full BusinessIQ scale —
17 commands + 25 skills + 3 agents — installed, and measured:

```
Component inventory:  Skills (42)
Projected token cost: Always-on: ~2,617 tok added to every session
claude plugin validate . --strict  ->  ✔ Validation passed
```

**No cap, no warning, no error at 42 components.** No aggregate limit is enforced by the
validator or the runtime, and none is documented.

## Problem

If there is no hard limit, what actually constrains component count — and what should the
architecture optimise against?

## Decision

1. **Remove the claim of a platform ceiling.** There is none. `architecture.md` states the
   real documented limits (64 / 1024 characters, 500-line guideline) and cites the measured
   figure.
2. **Keep a budget, labelled honestly as self-imposed.** Target **≤ 3,000 tokens always-on**,
   measured with `claude plugin details businessiq` at the end of each milestone and recorded
   in the task report. Measured baseline at full scale: ~2,617 tok for 42 components; the
   revised 37-component shape (ADR-0012) projects below that.
3. **Optimise for the real constraint, which is not tokens.** With 20 skills and 17 commands
   in one domain, the binding problem is **description discriminability**: 37 similar
   descriptions competing to match a request. The failure mode is the model picking
   `biq-sales-intelligence` when the user needed `biq-customer-intelligence` — a quality
   failure that no token count reveals. Descriptions must therefore be written to be mutually
   exclusive, naming the distinguishing trigger, not merely to be short.
4. **What happens if the budget is exceeded:** nothing breaks. The cost is gradual context
   competition and worsening discriminability. The response is to merge components whose
   descriptions overlap — never to truncate descriptions, since a description too thin to
   match is worse than one costing 110 tokens.

## Reason

Designing against an invented limit is a real hazard: it would have justified merging or
thinning components for no benefit, degrading the product to satisfy a number nobody set.
Measurement showed the design fits comfortably in reality, so the correct move is to state
the facts, keep a deliberately conservative self-imposed target for discipline, and redirect
optimisation effort onto discriminability — which measurement showed is the thing that
actually degrades at this component count.

## Consequences

**Positive** — no false constraint distorting design decisions; a documented, reproducible
measurement procedure; optimisation effort aimed at a failure mode that matters.

**Negative** — discriminability is harder to measure than tokens. It needs behavioural
tests ("given this request, which component fires?"), which currently depend on the
early-access eval harness (R-01) and must otherwise be checked manually.

**Follow-up required** — record `claude plugin details businessiq` output in every milestone
report; add routing cases to the eval suite asserting the right component fires for
representative requests; review descriptions for mutual exclusivity whenever a skill is added.

## Revisit when

Anthropic documents an aggregate always-on limit, or measured routing accuracy degrades as
components are added.
