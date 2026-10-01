# ADR-0047 — A routing grader accepts the owning BusinessIQ command route as well as the skill route

**Date:** 2026-09-25
**Status:** Accepted — 2026-09-25, by the project owner, who approved this decision ("Decision 1") in the
M13-DEF-17, M13-DEF-19 and M13-DEF-23 remediation prompt and authorised its implementation in the same decision.

- **What acceptance approves.** One mapping rule in the M13.2 evaluation case files, its validator assertions and
  its tests. Nothing else. No command, skill, agent, engine module, routing behaviour or runtime file is in scope,
  and none was changed.
- **Implemented 2026-09-25**, in the same task (`docs/development/2026-09-25-m13-2-adr-0047-0048-remediation.md`).

**Deciders:** Project owner (decision and implementation authorised, 2026-09-25), raised by M13-DEF-17.
**Supersedes:** none.
**Amends:** [ADR-0044](ADR-0044-platform-format-eval-cases.md), **in part**: its decision-table rows for
`skill_invoked` and `skill_not_invoked`, and the stage-3 sentence that the 22 such graders "keep their Phase 1
mapping — `tool: Skill` with the bare skill name as `input_match`". Every other part of ADR-0044 — the dual-layer
case file, the other mappings, `command_invoked` / `command_not_invoked`, staging and its *Revisit when* — remains in
force. **ADR-0044's text and status line are not edited**, as the repository did for ADR-0040, ADR-0041, ADR-0043,
ADR-0045 and ADR-0046.
**Relates to:** ADR-0039 §E.3 (routing cases), ADR-0044 (the case format this amends), M13-DEF-17 (the defect this
closes), `lib/python/biq/commands/registry.py` and `commands/*.md` (the declarations the mapping is derived from).

## Context

ADR-0044 mapped a semantic `skill_invoked` grader to a platform `tool_used` grader with `tool: Skill` and the bare
skill name as `input_match`, and `skill_not_invoked` to the same with `min: 0`, `max: 0`. When that was decided, no
run had shown how the platform records a skill or a command.

The M13.2 closing evaluation (2026-09-24/25) showed it. A BusinessIQ command and a BusinessIQ skill both appear as a
`Skill` tool call whose input names them: `{"skill":"businessiq:anomaly-detection"}` for the command,
`{"skill":"businessiq:biq-anomaly-detection"}` for the skill. In `r01`, `r07`, `r08`, `r10`, `r13` and `b04` the model
routed to the **command** that owns the expected skill, the command ran and, in `r01` and `b04`, the engine produced
its output — and the grader failed, "Skill called 0x", because the input did not contain `biq-<skill>`.

**Why the bare-skill mapping was insufficient.** A BusinessIQ command is a thin orchestrator for exactly one owning
skill (ADR-0003; ADR-0012's placement rule). Selecting the command *is* selecting that capability: the command's own
file states that its logic lives in that skill, and for the internal-analytics commands the engine's command registry
records the same. Requiring a separate `Skill` call for `biq-<skill>` measured an implementation detail — whether the
model also loaded the skill file — not whether BusinessIQ routed the request to the right capability. The
bare-substring match also had the opposite weakness: it looked anywhere in the input, including a command's `args`.

## Decision

**A routing grader accepts either the expected skill route or the route of a command that owns that skill, and
nothing else.**

1. **The relationship comes from the repository's own declarations, never from a hand-kept list.** A command owns a
   skill when either
   - the engine's command registry, `lib/python/biq/commands/registry.py`, gives that skill as the command's `skill`
     (the internal-analytics commands); or
   - the command's file, `commands/<command>.md`, states that its logic "lives in `skills/<skill>/SKILL.md`" (the
     research and synthesis commands).

   The two sources cover disjoint commands. Where neither names an owner (`business-health`, `ask-business-data`,
   `retrieval-slice`), the command owns no skill. A skill with no owning command (`biq-data-ingestion`) is accepted
   only on its own route.
2. **Platform mapping.** `skill_invoked` for skill *S* becomes `type: tool_used`, `tool: Skill`,
   `input_match: "skill":"businessiq:(?:S|C1|C2…)"`, where *C1…* are the commands that own *S*, sorted. The match is
   **anchored on the `Skill` input's `skill` value**, closed by its quote, with the plugin prefix required: an
   unrelated BusinessIQ command, another plugin's command, a mention in `args` or in the final message, or a
   different tool cannot satisfy it. `min`, `max` and `arm` are unchanged from each case's current grader.
3. **Symmetry.** `skill_not_invoked` for skill *S* uses the same `input_match` with `min: 0`, `max: 0`, so a competing
   component's command route counts as that component firing — which the bare-skill mapping missed.
4. **Production routing is unchanged.** Nothing forces or discourages a skill call. The evaluator measures whether
   BusinessIQ routed to the right capability.
5. **Enforced.** The static validator derives the ownership map from the two declarations and asserts that every
   `skill_invoked` and `skill_not_invoked` platform grader carries exactly the mapped `input_match`. A change to a
   command's owning skill therefore fails the validator until the cases are regenerated.

## Consequences

- The `skill_invoked` graders of `r01` to `r16`, `r20` to `r22` (intended) and `b04`, and the `skill_not_invoked`
  graders of `r20` to `r22` (competing), are re-mapped. No grader is added or removed.
- **Historical results are not re-scored.** The closing evaluation's classes stand. The affected cases need a new
  owner-authorised evaluation before any class can change.
- The command-routing near-miss cases `r17` to `r19` assert commands directly (`command_invoked`, ADR-0044 stage 3)
  and are outside this amendment.

## Revisit when

The platform records commands and skills differently from the observed `Skill`-tool input; a command comes to own more
than one skill, or a skill's ownership is declared anywhere other than the two sources above.
