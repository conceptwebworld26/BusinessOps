# BusinessOps Privacy Policy

**Provider:** Prakash Meghani - Krayons Global
**Contact:** krayonsglobal@gmail.com
**Applies to:** BusinessOps 0.1.0 · last updated 2026-10-01

BusinessOps is a plugin that runs inside Anthropic's Claude applications. This policy describes what the
BusinessOps software itself does with data. It was written from the plugin's source code, which you can
inspect.

## Summary

- BusinessOps has **no telemetry, analytics or tracking**, and no server of its own. The Licensor receives
  no data from your use of it.
- Your files are **read and analysed on your own computer** by BusinessOps' local engine. The engine never
  modifies your original files and makes no network connections of its own.
- **Claude processes your conversation.** Analysis results that BusinessOps returns into your conversation,
  and anything else in that conversation, are processed by Anthropic under your agreement with Anthropic.
- **Web research uses Claude's own web tools**, with queries built from public terms, such as an industry,
  market, company name or period, not from your business data.
- **One optional download**: with your explicit consent, BusinessOps can download the `openpyxl` library
  from the Python Package Index (PyPI).

## 1. Data BusinessOps reads

- **Files you point it at**: spreadsheets and exports (`.xlsx`, `.xlsm`, `.csv`, `.tsv`). They are read,
  never modified; any cleaning happens on a working copy in memory or in BusinessOps' local state.
- **Business Context**, if you create it: `./.businessops/business_context.json` in your project or
  `~/.claude/businessops/business_context.json`. It holds the optional description of your business that
  you write yourself.
- **Configuration**: the defaults shipped with the plugin, and any settings you add.

## 2. Local processing

Figures, KPIs, forecasts and anomaly scans are computed by BusinessOps' Python engine on your computer.
BusinessOps is designed to return computed results, such as figures, tables and aggregates, into your
conversation rather than raw rows. Anything that is returned into the conversation is then processed by
Claude (see section 4).

## 3. Data BusinessOps stores, and where

All of it stays on your computer. BusinessOps sends none of it anywhere.

| Location | What | How long |
|---|---|---|
| `./businessops-output/` | Reports and exports, written only when you ask for a file | Until you delete them |
| `./.businessops/verification/` | Verification requests (the source file's path, a SHA-256 hash of its contents and the run's arguments) and verification records (salted digests only, no values) | Until you delete them |
| `./.businessops/connectors/operations/` | Connector discovery records. No connector ships in this version, so none are written | — |
| `~/.claude/businessops/guard/` | Write-approval records: the session identifier, the tool, the working directory, a hash of the tool input, and the file paths an operation would change. Also session markers | Pending requests are deleted after 30 minutes, granted approvals after 10 minutes, and used approvals 24 hours after they expire |
| `~/.claude/businessops/guard/handback/` | The text that the research agent returned from public web sources, kept so the engine reads it exactly | Until you delete it |
| `~/.claude/businessops/runtime/` | The optional `openpyxl` installation (section 5) | Until you delete it |

BusinessOps keeps no separate log file. The record of what a research query disclosed is part of the
analysis output shown to you.

## 4. Data that leaves your computer

- **To Anthropic, through Claude.** BusinessOps runs inside Claude. Your prompts, the analysis results
  BusinessOps returns into the conversation, and anything else in that conversation are processed by
  Anthropic under your agreement with Anthropic and Anthropic's privacy policy. BusinessOps does not
  control that processing.
- **Web research.** The research commands (company, market, competitor and industry research, benchmark
  comparison, and the synthesis commands that use them) use Claude's WebSearch and WebFetch tools. A
  disclosure gate builds each query from public terms before it is sent. Customer names, individual
  records, credentials and raw ledgers are refused outright, and anything beyond derived, banded and
  aggregated context is shown to you verbatim for approval first. Web pages are fetched by Claude's tools,
  not by BusinessOps.
- **Optional download from PyPI.** To read `.xlsx` files when no suitable reader is available, BusinessOps
  can, **only after asking you and receiving your consent**, create a private Python environment and
  install `openpyxl` from the Python Package Index. That download is an ordinary package request to PyPI;
  no business data is sent.
- **Nothing else.** BusinessOps has no connector to any business system in this version, and sends no data
  to the Licensor or to any other third party.

## 5. Third parties

BusinessOps itself shares no data with third parties. Anthropic (through Claude), the websites Claude's
web tools reach, and PyPI (only if you consent to the optional download) have their own terms and privacy
policies.

## 6. Your choices

- Uninstalling the plugin stops all BusinessOps processing.
- You can delete `./businessops-output/`, `./.businessops/` and `~/.claude/businessops/` at any time.
- You can decline the optional `openpyxl` download; BusinessOps then uses its built-in reader or asks for
  a CSV export.
- Do not include personal data in files you analyse unless you need to.

## 7. Children

BusinessOps is a business tool and is not intended for people under 18.

## 8. Changes and contact

This policy may change with new versions of BusinessOps; the version included with a release applies to
that release. Questions or concerns about privacy: krayonsglobal@gmail.com
