# bops-analysis-verifier

**Definition:** [`agents/bops-analysis-verifier.md`](../../agents/bops-analysis-verifier.md) ·
**Contract:** ADR-0034, ADR-0035 · **Built:** M11

## Responsibility

Start the blind recomputation of one sealed verification request and hand back its status. It receives
only an opaque request id (`rcq-` + 16 hex), calls the one `recompute` operation once, and returns the
closed `bops.verifier.result/1` envelope unchanged. It decides nothing: `verification.verify()` compares
every figure and decides every outcome.

## Tool grant

`mcp__plugin_businessops_bops-verifier__recompute` - and nothing else. No file, shell, web, ToolSearch,
other MCP or dispatch tool. The grant is the boundary (ADR-0014, ADR-0035), so it is asserted by
`tests/unit/test_m11_verifier_agent_boundary.py`: statically on every run, and at runtime (opt-in,
`BOPS_AGENT_BOUNDARY_RUNTIME=1`) in real nested sessions with a control agent that holds no grant.
`claude plugin validate --strict` does not check it.

## Invoked when

`/executive-report --final` or `/decision-support --final`, once per request id that
`verification.issue_recomputation()` returned. Never for analysis, research or presentation.

## Justification (ADR-0006)

Independent verification. The recomputing process never receives the figures it checks, and the agent
context cannot read data at all; independence is structural, not a model's judgement.
