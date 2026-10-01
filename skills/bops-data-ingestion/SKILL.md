---
name: bops-data-ingestion
description: Use when asked what is in one or more local spreadsheets or CSV files before analysing them — which sheets and columns exist, how complete each column is, how many distinct values it holds, what date range it covers, which columns look like keys, how far keys overlap between files, and whether a named command or KPI has the columns it needs. Runs the deterministic data profile over 1-20 local .csv, .tsv, .txt, .xlsx or .xlsm files through the Data Layer and presents its structural facts. Shows no cell values, computes no KPI value, total or average, ranks nothing, joins nothing and produces no evidence or recommendation. Also answers whether BusinessOps can use a connected business system such as a CRM or accounting package — in this version always a named absence with the file-export alternative. Trigger phrases include "profile this file", "what's in this spreadsheet", "which columns do I have", "is this data ready", "check these files before analysis".
argument-hint: "[paths to 1-20 local .xlsx or .csv files]"
---

# Data ingestion — local-file profile

Profile local files with the engine and present what it returns. That is the whole skill:
**every fact comes from `lib/python/bops/data_profile.py`, and you add none.** The profile is
the answer to "what is in these files, and what could BusinessOps do with them" — never an
answer about the business.

Contract: ADR-0036. Connector sources are never profiled; a request for a connected system is
handled by the connector section below (ADR-0037, ADR-0038).

## The rules that matter most

**1. The engine is the only reader.** Never open a source file with `Read`, a shell command, a
spreadsheet tool or anything else — not to "check a column", not to show an example row. The
Data Layer reads it; the profile carries no raw rows, so nothing you could need is missing.

**2. No values.** The profile emits no cell value except ISO currency codes and the first and
last dates of date columns not classed `restricted` or `never`. Do not add example values,
top values, names, identifiers or figures from anywhere else, and do not guess what a column
contains beyond its kind and class.

**3. Facts keep their basis.** `observed` came from the file or the reader. `calculated` is an
exact count over every row read. `inferred` is a Data Layer rule (kind, currency, sensitivity,
role) run over the first values of the column, with the sample stated in `examined`. Never
present an `inferred` fact as observed, never upgrade `confirm_required` to a role, and never
restate a count as an estimate or an estimate as a count.

**4. A profile is not evidence and not a verdict.** Do not register it, or any part of it, in
a synthesis set (it is refused). Do not call the data "good" or "bad", score it, rank columns
or files, or recommend what to do. Quality appears as Data Quality's own grade and check ids.

**5. Candidates are for the user to confirm.** A key candidate or a key overlap is a structural
proposal. Never describe it as a join, a relationship between records, or a confirmed key.

## Steps

**1. Collect the paths.** One to twenty local files the user named. Do not search folders or
expand globs — ask the user to name each file. Hidden sheets are profiled only when the user
names them.

**2. Run the profile.**

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops import data_profile
result = data_profile.build({'sources': ['<path>']})
print(data_profile.render(result))
"
```

Optional request fields, and nothing else:

| Field | Meaning |
|---|---|
| `sheets` | `{'<path exactly as in sources>': ['Sheet name', ...]}` — named sheets only; a hidden sheet is read only when named here |
| `objective` | `{'command_id': 'sales-analysis'}` and/or `{'kpi_ids': ['gross_margin']}` — closed ids only |
| `presentation` | `'local'` (default) or `'shareable'`, which bands small counts, omits paths and replaces the names of `never`-classed columns with their position |

Never pass counts, kinds, classes, roles, grades, confidence or a previous profile — the
request is refused.

**3. Present the rendered profile.** Lead with the status and any unavailable source and its
reason code, then per dataset: rows, columns, reader tier, each column's kind, class and counts,
date coverage where shown, key candidates, the Data Quality grade and, if an objective was
given, the command's required roles with their mapping status and each KPI's status.

**4. State the limitations as prominently as the facts.** Every entry in `limitations` is
shown. `sampled_inference` means kind, class and role came from the first values of each
column while the counts are exact.

## Output meaning

| Entry | Say | Never say |
|---|---|---|
| KPI `available` | the KPI engine could compute it from these columns | its value, or that it is healthy |
| command role `confirm_required` | the column needs the user's confirmation before that command relies on it | that the command will succeed |
| `distinct_count` null with `distinct_count_capped` | more distinct values than the cap; not counted | an approximate number |
| key overlap rate | the share of distinct key values two columns have in common | that the files join, or on what |

## Failure conditions

| Condition | Behaviour |
|---|---|
| Request refused (`DataProfileError`) | Report the reason as given; fix the request with the user. Nothing is profiled |
| Status `partial` | Some sources or sheets are unavailable; name each with its reason code. The rest is valid |
| Status `unavailable` | Nothing could be profiled; show each source's reason code |
| `reader_refused`, `malformed` or `encrypted` workbook | Show the CSV export guidance the render includes. Never try another way to open the file |
| No Python available (reader Tier 4) | No profile can be built. Give the CSV export guidance and stop — never read the file yourself instead |
| Serialisation refused as stale | A source changed after profiling. Build the profile again |

## Connected systems — resolution and named absence

When the user asks whether BusinessOps can read a business system — a CRM, an accounting
package, a store, a warehouse, a spreadsheet service — resolve the capability. Do not look
for connectors: never list, search for or inspect the session's MCP servers or tools. A
connector exists for BusinessOps only if its registry declares it.

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "
from bops.connectors import registry, catalogue
print(catalogue.render_resolution(registry.resolve('~~crm')))
"
```

The capability is one of `~~accounting`, `~~crm`, `~~commerce`, `~~warehouse`,
`~~spreadsheet`, `~~chat`. **No connector is registered in this version**, so every
capability resolves to a named absence. Present its text and its file alternative exactly:
export the data to CSV or Excel and profile or analyse the file as above. The file path is
complete on its own and never waits for a connector.

A value-free catalogue (`catalogue.request_discovery(...)`) exists only for a connector whose
registry declaration, Connector Gate record and agent grant agree exactly. None does, so it
returns a named refusal; present its `message` and `file_fallback` and stop.

Rules that hold whatever the user says:

- **Never start or suggest a sign-in, and never ask for a credential.** Connecting a system is
  the user's own act, through their Claude platform, for the server BusinessOps declares — and
  BusinessOps declares none today. Never call an authentication tool, never ask for or accept an
  API key, token, password or authorization link, and never put one in a command.
- **A server connected elsewhere is not a BusinessOps connector.** A vendor server provided by
  another plugin, or one the user added, is never used — not even when it names the same
  vendor.
- **Never say a connector is connected, authorized, verified or available.** State only what
  the result says: a named absence, a named refusal, or one completed operation.
- **No record reads, no writes.** Reading records from a connected system is blocked
  (Milestone 12-C), and no write or administrative connector action exists. Offer the file
  path instead.
- **A catalogue is not evidence.** Never register it, or anything from it, in a synthesis set
  (it is refused), and never compute, rank or recommend from it.

## What this skill does not do

Compute KPIs, totals, averages, minima or maxima of figures, trends, forecasts or anomalies;
rank or score; join, merge or reconcile datasets; research anything externally; send the
profile anywhere; modify any source file; create evidence, recommendations or decisions. For
analysis, run the relevant command after profiling.
