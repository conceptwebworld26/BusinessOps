# Agent Reference

One page per subagent (`bops-<name>.md`), covering its responsibility, tool grant, invocation conditions, and its
justification under the three-justification test (ADR-0006). The definition itself is `agents/<name>.md`.

*Inventory verified against `agents/` on 2026-09-27 (M14-3).* ADR-0006 allocates three subagents. **Two are
built**, and neither is invoked directly by the user: each is dispatched by a command or skill.

| Agent | Status | Page | Tool grant | Dispatched by |
|---|---|---|---|---|
| `bops-research-scout` | Built (M9-B, ADR-0014) | [bops-research-scout.md](bops-research-scout.md) | `WebSearch`, `WebFetch` only | Every external retrieval, one dispatch per gate-authorised retrieval |
| `bops-analysis-verifier` | Built (M11) | [bops-analysis-verifier.md](bops-analysis-verifier.md) | `mcp__plugin_businessops_bops-verifier__recompute` only | `/decision-support --final`, `/executive-report --final` |
| `bops-data-profiler` | **Allocated, not built.** Deferred by ADR-0036, and built only on a complete Connector-Gated discovery chain (ADR-0037 §D.1) | None | None | None. Local-file profiling is the deterministic `DataProfileResult`, presented by `bops-data-ingestion` |

`architecture.md` §10 is the design source for all three.
