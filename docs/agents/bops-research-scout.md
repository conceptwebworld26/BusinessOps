# bops-research-scout

**Definition:** [`agents/bops-research-scout.md`](../../agents/bops-research-scout.md) ·
**Contract:** ADR-0014, ADR-0015, ADR-0017 · **Built:** M9-B

## Responsibility

Retrieve and triage public sources for **one** named entity (a company, market, competitor or industry) and return
cited findings. It receives only the scout brief: one JSON object whose `query_text` has already passed the
disclosure gate. It returns operation-bound line records (`BOPS-REC/1 … BOPS-END/1`, ADR-0017). These are parsed by
`bops.research.scout.parse_reply()` and ingested by `close_retrieval()` or `close_retrieval_object()` (`lib/python/bops/research/handoff.py`). It does not construct or extend the query,
and it decides nothing about tiering, freshness or claims. Those happen locally, in the engine and the research
skills.

## Tool grant

`WebSearch` and `WebFetch`, and nothing else. There is no `Read`, `Bash`, `Glob`, `Grep` or any file or repository
access. The grant is the security control: the context that retrieves cannot read business data. The disclosure
gate decides what may be asked, and the grant decides what can possibly be read (ADR-0006, ADR-0009, ADR-0014). The
grant is asserted by `tests/unit/test_research_scout_boundary.py` and `tests/negative/test_m9b_scout_security.py`.

## Invoked when

Once per gate-authorised retrieval, dispatched by the orchestrating model as `businessops:bops-research-scout`
(ADR-0015). This happens for `/company-analysis`, `/market-analysis`, `/competitor-analysis`, `/industry-research`,
`/benchmark-comparison`, and the research half of the synthesis commands. The reply reaches the engine verbatim
through the plugin's `PostToolUse` hook, which stores the scout's own text byte for byte under the write guard's root.
The session closes the retrieval with `R.handback_reply('<operation>')` and never copies the reply itself (ADR-0053).

## Justification (ADR-0006)

Context isolation. Retrieval needs web access, and web access must never share a context with file access. Keeping
the scout's tools separate from the main thread makes the internal/external boundary structural rather than
advisory.
