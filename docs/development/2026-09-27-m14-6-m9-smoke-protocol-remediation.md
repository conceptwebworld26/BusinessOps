# 2026-09-27 — M14-6: M9 smoke-test protocol remediation and final release-gate verification

**Milestone:** 14 — Documentation & Release
**Status on completion:** REVIEW — implemented and uncommitted, awaiting owner review. M14 stays `IN PROGRESS`. **OWNER RELEASE APPROVAL REQUIRED**
**Supersedes:** In part, `2026-09-27-m14-5-final-product-corrections.md` §7 (the M9 smoke results) and §§12–13 (gate E and
owner decision 2). That record is not edited.

## 1. Prompt / task performed

"M14-6 — M9 Smoke-Test Protocol Remediation and Final Release-Gate Verification."

- **Resolve the criterion-5 failure.** The scout's reply must reach the parser verbatim: no trimming, de-indenting,
  stripping, extraction, normalisation, rewriting, reconstruction or cleanup. The prompt allows the minimum
  implementation change if wording alone cannot achieve that.
- **Re-run the four M9 live smoke tests** in fresh sessions, and compare the texts, not the parsed records.
- **Keep unchanged:** M13-DEF-14 to -16, the token figure and packaging.
- **Excluded:** commit, tag, push and publication.

## 2. Starting state

- HEAD `8e4ab17`, with the uncommitted M14-4 and M14-5 working tree (42 changed or untracked paths), preserved.
- `origin/main` at `595e910`.
- No stash.

## 3. Root cause

1. **Instructions.** The four research skills said only "Feed the scout's **reply text** to `R.close_retrieval(...)`".
   The verbatim rule existed only in `architecture.md` §10 and the internal `/retrieval-slice` harness.
2. **The carrier.**
   - The session never receives the raw reply. The harness renders a subagent's report inside a frame: a preamble
     line, every line indented by two spaces "so a frame-like line at column zero inside it would be forged", and an
     `agentId` / `<usage>` footer.
   - Removing the frame and de-indenting reproduces the raw reply exactly (verified: 4,308 of 4,308 characters on the
     M14-5 market trace).
   - In M14-5 the sessions wrote only the de-indented protocol lines, which is extraction.
3. **Wording alone is not enough (measured).**
   - The first M14-6 fix told the six skills to write the `Agent` tool result "exactly as you received it".
   - All four fresh runs then copied the whole framed result: frame, indentation, prose and footer.
   - Every non-whitespace character matched, but each run wrote every whitespace-only line as an empty line and added a
     final newline (differences of 1, 3, 3 and 7 characters).
   - A model regenerating text through the Write tool is not a verbatim channel.
   - Those traces are kept in the scratchpad as `m146a/`.
4. **The parser was never at fault.** `close_retrieval()` hands its payload straight to `parse_reply()`, which splits it
   into lines and strips each one as part of parsing. `_unfence()` applies only to the legacy JSON-envelope path.

## 4. The fix (ADR-0053)

**Measuring what a hook receives.** A probe plugin, kept in the scratchpad only, showed what a `PostToolUse` hook
receives for an `Agent` call:

- `tool_response.content` holds the subagent's **own** reply, unframed;
- `tool_input.prompt` holds the brief, and with it the `operation`.

**Changes:**

- `hooks/hooks.json`: `PostToolUse`, matcher `Agent|Task`, command `sh "${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh" --handback`.
- `lib/python/biq_run.py`: an exact `--handback` mode, behind the layout check and import boundary. It runs no caller
  code and takes no argument.
- `lib/python/biq/research/handback.py` (new):
  - `capture()` stores the text blocks of `tool_response.content` for a scout dispatch whose brief names a safe
    operation id, as UTF-8 with `newline=""`, through a temporary file and an atomic rename, under
    `~/.claude/businessiq/guard/handback/`;
  - `reply()` reads the capture back unchanged, or raises `HandbackError`;
  - `main()` always exits 0.
- `lib/python/biq/research/__init__.py` exports `handback_reply` and `HandbackError`.
- `lib/python/biq/writeguard/classify.py`: `--handback` joins `--guard` as a harness-only entry, prohibited from any
  tool call. The store sits inside the guard root, which is already prohibited.
- **The six skills that close a retrieval:**
  - `biq-company-analysis`, `biq-market-analysis`, `biq-competitor-analysis` and `biq-industry-research` close inline
    with `R.close_retrieval(R.handback_reply('<operation>'), …)`. They are told never to copy, write or retype the
    reply, and to report a failed retrieval if no capture exists.
  - `biq-benchmark-comparison` and `biq-swot` take `reply_text` from `R.handback_reply()`.
- **Docs:** ADR-0053 (new, indexed in all three ADR indexes); `architecture.md` §2 and §10; the
  `biq-research-scout` reference page; `docs/commands/external-research.md`; the troubleshooting guide (a new entry for
  a missing capture).

**Why this is the minimal safe change.** The line protocol, parser, gate, tiering and the scout's `WebSearch`/`WebFetch`-
only grant are all untouched. Giving the scout file access was rejected, because it would break the privacy boundary.
The capture is a transport, and it decides nothing.

## 5. Tests

`tests/unit/test_m14_6_verbatim_handback.py` has 23 tests:

- **The capture is byte-exact.** The fixture has prose, an indented line, whitespace-only lines, a CRLF and a
  whitespace-only last line. The tests also cover joining multiple blocks, a later dispatch replacing an earlier one,
  and the store sitting under the guard root.
- **Only scout dispatches are captured.** Other events, tools and agents, non-brief prompts, and unsafe operation ids
  (`../../escape`, `a/b`, empty, dot-leading, over-long, non-string) are all ignored; a missing capture raises; the entry
  never raises.
- **The engine boundary.** `close_retrieval` passes `parse_reply` **the same object**, and a trimmed copy is a different
  text even when it parses to the same records.
- **The hook path.** The declaration is exact, `biq_run.sh --handback` writes the captured bytes from stdin, and an extra
  argument is refused.
- **Forgery.** Invoking `--handback` through `sh`, a pipe or `python -I` is **prohibited**, and so is writing into the
  store. The documented inline close is **free**.
- **The skills.** The six closing skills are discovered by content; each reads the capture and never a copy
  (`reply.txt`, `exec(open(`).

**Mutation checks.** Each was restored immediately afterwards:

- removing `--handback` from the classifier fails 3 tests;
- a capture that strips fails 4;
- the old company-skill wording fails 2.

**Pins moved.** `unit.test_m13_def24_write_classifier` and `unit.test_m13_def08_runtime_resolver` pin the number of
shipped engine blocks. Both moved 34 → 38, for the four documented inline closes, each of which passes the confinement
check. File counts are unchanged.

**Store hygiene.** The launcher test writes to the account's real guard store (the launcher resolves home from the
account database by design). It removes its file, and removes the directory if it created it. One empty leftover
directory from an earlier run was removed.

## 6. M9 live smoke tests

**Procedure.** As M9-D.1 §15 specifies. Each test ran as `claude -p --plugin-dir <repo> --no-session-persistence
--output-format stream-json --verbose --max-budget-usd 5`, in an empty scratchpad directory, one at a time. The grant
was the engine resolver, Read, Write, Agent, Task, Skill, WebSearch and WebFetch.

**Attempts that do not count:**

- the wording-only runs (`m146a/`), which failed criterion 5 as described in §3;
- one sequence cut off by the account session limit in its first turns (`m146b-aborted/`).

**Final runs:**

| Command and input | Result | Dispatches (public query) | Reply A → B | Close | Records | Verified | Confidence | Sections |
|---|---|---|---|---|---|---|---|---|
| `/company-analysis Microsoft --focus overview` | **PASS** | 1 ("Microsoft technology 2026 company profile") | 5,370 → 5,370, identical | `handback_reply`, inline | 4 | 0 | MEDIUM | 10 |
| `/market-analysis cold chain logistics --focus overview` | **PASS** | 1 ("cold chain logistics market overview") | 2,721 → 2,721, identical | `handback_reply`, inline (twice: the documented re-close with `conflicts=`) | 2 | 0 | LOW | 10 |
| `/competitor-analysis Microsoft --focus landscape` | **PASS** | 1 ("Microsoft competitive landscape") | 4,803 → 4,803, identical | `handback_reply`, inline | 3 | 0 | LOW, `support: unsupported`, nothing ranked | 10 |
| `/industry-research commercial aerospace --focus structure` | **PASS** | 1 ("commercial aerospace industry structure and value chain") | 6,030 → 6,030, identical | `handback_reply`, inline | 3 | 0 | LOW | 10 |

**What passed in every run:**

- the command was discovered, and its skill was invoked;
- the verifier was `connected`;
- no `Read`, `Glob` or `Grep` was used anywhere, and no internal term was sent;
- the session wrote the reply to no file, and typed it into no command.

**Criterion 5.**

- **A** is the scout's reply as the harness recorded it in the session trace (`tool_use_result.content`, the same text
  the hook receives).
- **B** is the capture file that `R.handback_reply()` read for the parser, compared with `newline=""`.
- They are byte-identical in all four runs.

**The competitor run.** It completed through the supported path. The M14-5 guard stop came from the session improvising
an `exec(open(script))` close. That was a skill-documentation gap, not a read-only command attempting a write. The
skill now shows the exact inline form.

**Observations:**

- In the market run the session attempted a `grep` over the plugin's own source code. The smoke grant denied it, so it
  never ran.
- M14-5 and M14-6 smoke sessions cost **$12.53** in total. The final four cost $3.27.

## 7. M13-DEF-14, -15 and -16

These are unchanged: open, known model-behaviour limitations. No paid evaluation was run, and no deterministic evidence
changed.

## 8. Token cost and packaging

- **Token cost:** unchanged at **~7,260 tokens always-on** (M14-5 measurement), above the ≤ 3,000 target. This task added
  skill *body* text, which is on-invoke cost, not always-on. The target is unchanged, and the response is an owner
  decision.
- **Packaging:** the finding is unchanged (whole repository, about 626 tracked files and 9.6 MB before this task, no
  tracked secrets). This task adds 4 files. No exclusion mechanism was introduced.

## 9. Files changed by M14-6

**Product:**

- `hooks/hooks.json`;
- `lib/python/biq_run.py`;
- `lib/python/biq/research/handback.py` (new);
- `lib/python/biq/research/__init__.py`;
- `lib/python/biq/writeguard/classify.py`;
- 6 skills: the four research skills, `biq-benchmark-comparison` and `biq-swot`.

**Tests:**

- new: `tests/unit/test_m14_6_verbatim_handback.py`;
- modified: `tests/unit/test_m13_def24_write_classifier.py`, `tests/unit/test_m13_def08_runtime_resolver.py`.

**Docs:**

- ADR-0053 (new) and this record (new);
- `architecture.md`, `docs/decisions/README.md`, `docs/README.md`, `docs/development/README.md`;
- `docs/agents/biq-research-scout.md`, `docs/commands/README.md`, `docs/commands/external-research.md`;
- `docs/examples/README.md`, `docs/troubleshooting/README.md`;
- `README.md` (one status-table row);
- `project_plan.md`.

`CLAUDE.md`, `.mcp.json`, configuration, schemas, manifests, evals and historical ADRs were not changed by this task.

## 10. Validation

- **Targeted suites** (guard, launcher, verifier, research and the manifest, 38 modules): 1,792 tests. The first run
  surfaced the block-count pin; after the §5 update, both pinning modules pass.
- **Full regression** (`python3 tests/run_tests.py`), final tree: `Ran 5324 tests in 682.431s`, `OK (skipped=31)`,
  `ran 5324 | failures 0 | errors 0 | skipped 31`, exit 0.
- **Strict validation** (`claude plugin validate . --strict`): passed.
- **Links:** 426 across 33 changed Markdown files, 0 broken.
- **`git diff --check`:** clean.
- **Working-tree audit:** 49 modified and 9 new paths, all within M14-4 to M14-6. No generated or scratchpad file, no
  historical ADR changed, and no secret.

## 11. Release-gate matrix

| Gate | Status | Evidence | Limitation | Release impact |
|---|---|---|---|---|
| A. Product functionality | PASS | 18 commands, 16 skills and 2 agents; R-13, R-15 and R-16 fixed (M14-5); M9 commands live-verified | — | Non-blocking |
| B. Internal analytics | PASS | Demo outputs reproduced (M14-5) | — | Non-blocking |
| C. Forecasting | PASS | Minimum-history refusal verified | Forecasts not in reports | Non-blocking |
| D. Anomaly detection | PASS | Demo scan; fraud boundary | Describes, never explains | Non-blocking |
| E. External research | PASS | 4 of 4 live smoke tests passed, criterion 5 byte-exact (§6) | Research quality is bounded by public sources | Non-blocking |
| F. Cross-domain synthesis | PASS | M10 `COMPLETED` | — | Non-blocking |
| G. SWOT / strategy | PASS | M10.3.1 and M10.3.2 | No ranking, by design | Non-blocking |
| H. Decision support | PASS | Drafts work; the verifier connects (ADR-0052) | — | Non-blocking |
| I. Executive reporting | PASS | As H.; the outlook states that no forecast is available | — | Non-blocking |
| J. Privacy and security | PASS | Public-term-only queries live; scout grant unchanged; captures unforgeable from the session | M13-DEF-16 (over-refusal, fails closed) | Non-blocking |
| K. Write safety | PASS | ADR-0051 guard; `--handback` harness-only | Can halt a non-interactive run on unconfined code | Non-blocking |
| L. Connector state | PASS | Empty registry, truthfully documented | M12-C `BLOCKED` | Non-blocking |
| M. Documentation | PASS | Indexes and links updated; no stale smoke claims | D-07 (`CLAUDE.md` §3) | Non-blocking |
| N. Worked examples | PASS | Re-verified (M14-5) | Live examples carry no values | Non-blocking |
| O. Troubleshooting | PASS | Updated for ADR-0052 and ADR-0053 | — | Non-blocking |
| P. Testing and regression | PASS | Full regression: 5,324 tests, 0 failures, 0 errors, 31 skipped; strict validation passed | — | Non-blocking |
| Q. Evaluation status | OWNER DECISION | M13.2 accepted; M13-DEF-14 to -16 open (model behaviour) | Unverifiable without a paid evaluation | OWNER DECISION |
| R. Token/cost measurement | OWNER DECISION | ~7,260 always-on | Above ≤ 3,000 | OWNER DECISION |
| S. Packaging | OWNER DECISION | Whole repository ships | Development material installed | OWNER DECISION |
| T. Release and tagging | OWNER DECISION | No tag; version `0.1.0` | Q, R and S open | **OWNER RELEASE APPROVAL REQUIRED** |

## 12. Remaining owner decisions

1. **OWNER RELEASE APPROVAL REQUIRED:** any tag, push, release or publication, and the checkpoint commits for M14-4 to
   M14-6.
2. M13-DEF-14, -15 and -16: accept as known limitations, or schedule a remediation verified by a live evaluation.
3. The response to ~7,260 against the ≤ 3,000 always-on target.
4. Packaging: accept the whole-repository install, or restructure it.
5. A retention rule for old reply captures (ADR-0053 follow-up; optional).
6. D-13 and D-07: unchanged.

M9 as a milestone stays `IN PROGRESS` for rows outside M14's scope: the `biq-external-research` skill and three
tier-test rows.

## 13. Tag, push and publication

- No commit, amend, stage, tag, push or publication.
- HEAD remains `8e4ab17`, and `origin/main` remains `595e910`.

## 14. Git commit reference

N/A.
