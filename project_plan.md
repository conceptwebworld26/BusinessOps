# BusinessOps — Project Plan

**Last updated:** 2026-10-03
**BusinessOps phase:** **BusinessOps Milestone 4 — repository publication and directory submission preparation · `IN PROGRESS`** (single-repository architecture finalized, ADR-0057; next: directory submission, a separate owner step)

## BusinessOps — current state

Read this section first. It is the only part of this file that describes BusinessOps as it is now.

- **Product.** BusinessOps (plugin id `businessops`, technical prefix `bops`) is a separate product derived from the
  BusinessIQ codebase, prepared for submission to Anthropic's plugin directory (the Claude Marketplace).
- **Rights holder.** Prakash Meghani - Krayons Global. Licence: proprietary (`LICENSE`, `EULA.md`; manifest
  `LicenseRef-BusinessOps-Proprietary`). Privacy: `PRIVACY.md`. Support: krayonsglobal@gmail.com.
- **Distribution.** Users install the package built by `scripts/build_distribution.py` (ADR-0055), not this
  repository. The package is committed under `dist/businessops/` (ADR-0057); the repository's marketplace entry
  points at `./dist/businessops` (BOPS-R18).
- **Identity.** Recorded in [ADR-0054](docs/decisions/ADR-0054-businessops-product-identity-and-bops-namespace.md).
  Current identifiers are listed in `architecture.md`.
- **Repository.** `https://github.com/conceptwebworld26/BusinessOps` (public, `origin`). The only repository; the
  directory submission names the plugin path `dist/businessops`.
- **History.** From the inherited status block below this section, through *Milestone summary* and every numbered
  milestone, up to *Known issues*, this file is the BusinessIQ project history, kept unchanged. It uses BusinessIQ
  identifiers (`businessiq`, `biq`), and its commit hashes belong to the BusinessIQ repository, not this one. The same
  holds for `docs/development/` records dated before 2026-09-30 and for `docs/decisions/` up to ADR-0053.

### BusinessOps milestones

| # | Milestone | Status | Notes |
|---|---|---|---|
| BOPS-M1 | Product identity & technical namespace migration | `COMPLETED` (owner-accepted 2026-09-30; uncommitted) | Plugin `businessiq` → `businessops`; prefix `biq` → `bops`; runtime state `.businessops/`, `businessops-output/`, `~/.claude/businessops/`; licence metadata made proprietary. Historical records and SHA-pinned fixtures unchanged. Suite result unchanged: 5,324 tests, 47 failures, 7 errors, 38 skipped, all Windows-host environment failures. See `docs/development/2026-09-30-businessops-m1-identity-migration.md` |
| BOPS-M2 | Claude Marketplace readiness, governance & packaging audit | `COMPLETED` (owner-reviewed 2026-09-30; uncommitted) | Official directory requirements verified; `CLAUDE.md` contradictions fixed; ADR-0054. See `docs/development/2026-09-30-businessops-m2-marketplace-readiness-audit.md` |
| BOPS-M3 | Packaging, policy & marketplace readiness | `COMPLETED` (owner-reviewed 2026-09-30; uncommitted) | 2026-09-30. Distribution package built from an allowlist (`scripts/build_distribution.py` → `dist/businessops/`, 188 files, 2.6 MB, ADR-0055 Proposed); `retrieval-slice` moved to `dev/harness/`; `displayName` and an accurate description; `LICENSE` rewritten, `EULA.md` and `PRIVACY.md` added; verifier tool annotations; README platform, Claude-app and hook disclosure. Full-suite failure set unchanged from BOPS-M2; 11 new tests pass. See `docs/development/2026-09-30-businessops-m3-packaging-policy-readiness.md` |
| BOPS-M3.1 | Installed-package runtime verification | `COMPLETED` (owner-approved 2026-09-30; uncommitted) | A live test of an installed-style package proved the relative `reference/` paths broken for commands and skills. All 76 now use `${CLAUDE_PLUGIN_ROOT}/reference/…` (ADR-0056, Proposed, a narrow amendment to ADR-0042's static guard, plus one new test), and the live test passes. The MCP direct launch was tested and failed on native Windows (CONNECTION_CLOSED), so `.mcp.json` is unchanged; the `sh` form may be held for a reviewer. Package: 188 files, 2,644,601 bytes, `validate --strict` passed; MCP verified from the package (completed recompute). Test artifacts cleaned up. Final full suite: 5,336 tests, 47 failures, 7 errors, 38 skipped; the failing set is identical to BOPS-M3 (one new test, passing). See `docs/development/2026-09-30-businessops-m3-1-installed-package-verification.md` |
| BOPS-M4A | Final hardening before the first Git commit | `COMPLETED` (owner-approved; uncommitted) | BOPS-R11 fixed: a Bash device word such as `/dev/null` stays a device on native Windows, while file-tool paths and other platforms are unchanged. BOPS-R12 fixed: guard messages cite the shipped README, not `CLAUDE.md`. 7 new tests; the affected guard modules show no failure outside the baseline, and baseline `test_17` is resolved; the full suite was not re-run (confined change). Package 188 files, 2,645,712 bytes, `validate --strict` passed; MCP verified. ADR-0055 and ADR-0056 Accepted. See `docs/development/2026-09-30-businessops-m4a-final-hardening.md` |
| BOPS-M4A.1 | Remove shipped-plugin `CLAUDE.md` references (BOPS-R14) | `COMPLETED` (owner-approved; in commit `58a91b4`) | 41 citations in 14 commands, 11 skills and 2 reference documents now cite shipped documents: the approval matrix (new section in `reference/analysis-framework.md`), the disclosure tiers (`reference/research-policy.md`) and data privacy in output (new section in `reference/output-standards.md`), through the ADR-0056 path form (reference tokens 76 → 113). 8 new tests; affected modules show no failure outside the baseline; full suite not re-run. Package 188 files, 2,650,190 bytes, `validate --strict` passed; `.mcp.json` unchanged. See `docs/development/2026-09-30-businessops-m4a1-remove-shipped-claude-md-references.md` |
| BOPS-M4 | First Git commit, then repository publication and directory submission preparation | `IN PROGRESS` | Done: root commit `58a91b4` and the M4 records (`b5b762a`) on <https://github.com/conceptwebworld26/BusinessOps> (public). Final decision (ADR-0057): this is the only repository; it holds the source and the committed package `dist/businessops/` (189 files, 2,650,014 bytes; `validate --strict` passed; MCP verified), submitted with plugin path `dist/businessops`; no BusinessOps-Plugin repository. BOPS-R18 fixed: the repository's marketplace entry points at `./dist/businessops`, and the README separates the directory plugin path, adding the marketplace and installing the plugin (package 189 files, 2,651,459 bytes; `validate --strict` passed). Owner and support identity changed to Prakash Meghani - Krayons Global and krayonsglobal@gmail.com in the manifests, `LICENSE`, `EULA.md`, `PRIVACY.md` and README (2026-10-01, ADR-0058; historical records unchanged). Directory icon added for the listing's "No icon" finding: `.claude-plugin/icon.svg` (512 × 512 SVG), manifest `"icon": "./.claude-plugin/icon.svg"`, shipped by the build, whose check now requires the file (package 190 files, 2,652,033 bytes; `validate --strict` passed; MCP verified; 2026-10-03). Directory validation remediation (2026-10-03): the directory refuses SVG, so the icon is now `.claude-plugin/icon.png` (512 × 512 PNG rendered from the SVG, which stays as the unshipped design source) and the build check enforces the directory's icon rule; the resolver's `BOPS_PROBE_TOKEN` marker, matched as an environment credential, is renamed `BOPS_PROBE_MARKER` and the build now rejects credential-named variable references; the `CLAUDE.md` and "files the validator couldn't inspect" findings come from validating the repository root, not `dist/businessops` (BOPS-R19); the `sh` launches stay (BOPS-R10, BOPS-R17) (package 190 files, 2,663,343 bytes). Re-validated at plugin path `dist/businessops`: "Passed with warnings", four policy holds for reviewers (BOPS-R10, BOPS-R17, BOPS-R20); the README now discloses what BusinessOps reads from the machine. Next: directory submission (an owner step). See `docs/development/2026-10-01-businessops-m4-single-repository-architecture.md`, `docs/development/2026-10-01-businessops-r18-installation-path-fix.md`, `docs/development/2026-10-01-businessops-krayons-global-identity-migration.md` and `docs/development/2026-10-03-businessops-directory-icon.md` , `docs/development/2026-10-03-businessops-directory-validation-remediation.md` and `docs/development/2026-10-03-businessops-directory-policy-findings.md` |

### Open BusinessOps readiness items

Identified in BOPS-M2; status as of BOPS-M3.

| ID | Item | Status |
|---|---|---|
| BOPS-R1 | The package ships the whole repository (637 files, 9.75 MB). Over the directory's 512-file review threshold, with a file over 256 KiB (`project_plan.md`) and a non-image binary (`northwind_sales.xlsx`): each holds a version for a reviewer | Resolved in BOPS-M3 for the package: 188 files, 2.6 MB, no binary, no file over 256 KiB (ADR-0055). This development repository still exceeds the limits by design and is not the submitted folder |
| BOPS-R2 | No privacy-policy link and no support contact, both required by the Anthropic Software Directory Policy | Resolved in BOPS-M3: `PRIVACY.md`, and the support contact hello@conceptwebworld.com in the manifests and README. A hosted privacy-policy URL for the portal is an owner decision |
| BOPS-R3 | Manifest descriptions claim "connected business systems"; the connector registry is empty | Resolved in BOPS-M3: manifest descriptions no longer mention connected systems |
| BOPS-R4 | Hooks and the MCP server start through `sh`: on native Windows without Git for Windows they cannot start, and the write guard does not run | Documented in BOPS-M3 (README *Platform requirements*: native Windows needs Git for Windows). No PowerShell implementation, by owner decision |
| BOPS-R5 | The verifier MCP tool has no `readOnlyHint` / `destructiveHint` / `title` annotations | Resolved in BOPS-M3: `title`, `readOnlyHint: false`, `destructiveHint: false`, `openWorldHint: false` |
| BOPS-R6 | Behaviour in claude.ai chat and Cowork is untested; chat ignores agents, hooks and local MCP servers | Documented in BOPS-M3 (README *Where BusinessOps runs*). Still untested in Cowork and chat |
| BOPS-R7 | `commands/retrieval-slice.md`, an internal harness, ships as a user-typable command | Resolved in BOPS-M3: moved to `dev/harness/retrieval-slice.md` |
| BOPS-R8 | `LICENSE` grants use only under an agreement that does not exist, and calls the software confidential although the repository must be public | Resolved in BOPS-M3 as drafting: new `LICENSE` and `EULA.md`, with no "confidential" wording and an express grant to install through Claude. Not legally reviewed; governing law undecided |
| BOPS-R9 | Relative `reference/…` paths in commands and skills did not resolve in an installed plugin (live-tested) | Resolved in BOPS-M3.1: `${CLAUDE_PLUGIN_ROOT}/reference/…`, ADR-0056 |
| BOPS-R10 | The local MCP server is started through `sh`, which the directory checklist may hold for a reviewer | Accepted by design in BOPS-M3.1: direct launch fails on native Windows (CONNECTION_CLOSED). A review risk, not a defect. Portal validation 2026-10-03 raised it as the policy hold "MCP server command wasn't read". Re-measured 2026-10-03: a direct `python -I ${CLAUDE_PLUGIN_ROOT}/lib/python/bops_run.py --verifier` connects only where `python` is a real interpreter, and `python3` fails on native Windows (CONNECTION_CLOSED; the Microsoft Store alias); the subfolder rule would hold the Python file anyway. Kept: a reviewer hold, not a block |
| BOPS-R11 | On native Windows the write guard resolves `/dev/null` to `C:\dev\null`, so a read-only command with `2>/dev/null` asks for approval (pre-existing failing test `test_17_read_with_shell_syntax_is_not_a_write`, now seen in a live session) | Resolved in BOPS-M4A (`classify.py`, Windows-only branch for Bash device words; tested) |
| BOPS-R12 | Write-guard messages cite "CLAUDE.md section 9", a file the package does not ship | Resolved in BOPS-M4A (guard messages cite the README's "Approval and write safety"; tested) |
| BOPS-R13 | On native Windows a Bash write aimed at the approval store is classified "needs approval" instead of "prohibited" (baseline failures `test_the_approval_store_is_prohibited`, `test_the_store_is_prohibited_even_when_not_engaged`; Git Bash `/c/...` paths are not recognised) | Open (pre-existing; found in BOPS-M4A; unchanged by the R11 fix) |
| BOPS-R14 | Command, skill and reference prompt text cites `CLAUDE.md`, which the package does not ship | Resolved in BOPS-M4A.1: no shipped instruction, policy or user document names `CLAUDE.md`; the README links to it in the development repository and the engine mentions it only in comments (tested) |
| BOPS-R15 | `hooks/bops_guard.sh` falls back to the working directory when `$0` contains no `/` (backslash paths on Windows); not observed under Claude Code | Open |
| BOPS-R16 | Running the plugin from its package directory writes Python bytecode (`__pycache__/*.pyc`) into it; the launcher's `-I` mode ignores `PYTHONDONTWRITEBYTECODE`. A committed `.pyc` would be a non-image binary, held for a reviewer | Resolved (2026-10-01, after commit `b5b762a`): the build generates the distribution repository's root `.gitignore` (`__pycache__/`, `*.py[cod]`), and its check rejects bytecode or a different `.gitignore`; verified by running the plugin in a copy (88 `.pyc` files written, all ignored) |
| BOPS-R17 | A submission from the `dist/businessops` subfolder is expected to be held for a reviewer: the scripts that hooks and the MCP server run (`hooks/bops_guard.sh`, `lib/bops_run.sh`) use shell variables, command substitutions and calls to other plugin files (checklist: "Scripts the validator couldn't follow") | Accepted with ADR-0057 (a review delay, not a block). Re-read 2026-10-01: the hook and MCP commands meet the blocking subfolder rule (full `${CLAUDE_PLUGIN_ROOT}` paths); the scripts are expected to be held for a reviewer, which is not a validation failure. Open until the portal validates; the scripts are unchanged. Portal validation 2026-10-03 raised it as the policy hold "Scripts the validator couldn't follow" (`lib/bops_run.sh`), as expected. Kept: the engine is Python and the resolver is the security boundary (ADR-0045); the checklist allows waiting for the review |
| BOPS-R18 | The README's self-hosted install (`claude plugin marketplace add conceptwebworld26/BusinessOps`) uses the root marketplace entry (`"source": "./"`), so it installs the whole development tree rather than `dist/businessops/` | Resolved 2026-10-01: the root entry's `source` is `./dist/businessops` (the build sets the package's own entry to `./`, and its check enforces it); the README and troubleshooting guide name `dist/businessops` for every route (tested) |
| BOPS-R19 | Portal validation on 2026-10-03 reported findings that exist only at the repository root: "CLAUDE.md at the plugin root isn't loaded" (`dist/businessops` ships no `CLAUDE.md`) and "Files or downloads the validator couldn't inspect" ×2 (the repository root holds exactly two such files, `assets/demo-data/northwind_sales.xlsx`, a binary, and `project_plan.md`, over 256 KiB, and 857 tracked files; `dist/businessops` has none and 190 files). The report does not name the plugin path it read; these findings indicate the repository root | Resolved 2026-10-03: the portal re-validated with plugin path `dist/businessops`; the `CLAUDE.md`, "couldn't inspect" and download-and-run findings are gone (result "Passed with warnings") |
| BOPS-R20 | Portal (plugin path `dist/businessops`, 2026-10-03) holds "Image or font file that the plugin's code could run" and "Uses a credential from the user's machine", both anchored to `plugin.json`. Nothing runs `icon.png` (its only reference is the manifest `icon` field). No credential is read: the credential-like reads are the write guard's account-record home lookup (`pwd.getpwuid(...).pw_dir`) and `CLAUDE_CODE_SESSION_ID`, both security controls, and nothing sends them | Accepted for reviewer confirmation, per the portal's guidance. The README now discloses every value read from the machine (tested). Owner option, not taken: the directory also finds `.claude-plugin/icon.png` without the `icon` field, which may avoid the image hold. See `docs/development/2026-10-03-businessops-directory-policy-findings.md` |

The status line below is the inherited BusinessIQ status at the point the codebase was carried over, kept as history.

**Current phase:** **Milestone 14 — `IN PROGRESS`** (M14-1 checkpointed `50d1f0e`; M14-2, the `README.md` redesign, checkpointed `5c1b15d`; M14-3, component documentation and index reconciliation, checkpointed `8e4ab17`; M14-4 (release readiness and finalization), M14-5 (final product corrections and release gate) and M14-6 (M9 smoke-test protocol remediation), checkpointed together in `57e92fa`; the M15 release-preparation audit and the M15-1 0.1.0 release-candidate preparation checkpointed locally in the "M15: prepare 0.1.0 release candidate" commit; **0.1.0 is a release candidate, not released**; **OWNER RELEASE APPROVAL REQUIRED** before any tag or publication). **Milestone 13 — `COMPLETED`** (M13.1 and M13.2 both owner-accepted), under ADR-0039 as amended by
ADR-0040, ADR-0041, ADR-0043, ADR-0047, ADR-0048 and ADR-0049. M13.2 was owner-accepted on 2026-09-26 and checkpointed by the commit "M13.2: complete test hardening and evaluation". M13.1 is `COMPLETED` and checkpointed on `origin/main` as `33f6e25` ("M13.1: deterministic test
hardening and coverage closure").

- **M15-1 0.1.0 release-candidate preparation, 2026-09-28 — checkpointed locally ("M15: prepare 0.1.0 release candidate").**
  - **Owner decisions:**
    - release version `0.1.0`, proposed tag `v0.1.0`;
    - M13-DEF-14, -15 and -16 accepted as known limitations for 0.1.0;
    - the ≤ 3,000 always-on target is kept, and the ~7,260 measurement is documented honestly;
    - whole-repository marketplace packaging accepted for 0.1.0;
    - M9's remaining rows stay `IN PROGRESS`; D-13 and D-07 stay open;
    - no paid evaluation; saved-scout-reply pruning deferred.
  - **Added:** release notes `docs/releases/0.1.0.md` (linked from `README.md` and `docs/README.md`), and a `.gitignore` entry for `.claude/settings.local.json` only.
  - **Not done:** no push, tag, GitHub release or publication. See `docs/development/2026-09-28-m15-1-release-candidate-checkpoint.md`.
- **M14-6 M9 smoke-test protocol remediation, 2026-09-27 — `REVIEW`, uncommitted.**
  - **Root cause of the M14-5 criterion-5 failure:**
    - the research skills never required a verbatim hand-back;
    - even with explicit wording, a model copy of the harness-framed tool result lost whitespace-only lines and added a final newline, in 4 of 4 live runs.
  - **Fix (ADR-0053):**
    - a `PostToolUse` hook (`biq_run.sh --handback`) stores the scout's own reply byte for byte under the write guard's root;
    - the six skills that close a retrieval now close inline from `R.handback_reply('<operation>')`, and are told never to copy it;
    - the classifier makes `--handback` harness-only.
  - **Live smoke:** 4 of 4 PASSED in fresh sessions:
    - in each, the scout reply recorded by the harness was byte-identical to the text the parser read (5,370, 2,721, 4,803 and 6,030 characters);
    - there was one public-term dispatch, no file read, ten sections, 0 claims verified, and the verifier connected;
    - `/competitor-analysis` completed through the supported path.
    - The four command rows are `COMPLETED`; M9 stays `IN PROGRESS` for the `biq-external-research` skill and three tier-test rows.
  - **Tests:** 23 new deterministic tests; two engine-block inventory pins moved 34 → 38 for the four new documented blocks.
  - **Validation:** full regression 5,324 tests, 0 failures, 31 skipped; strict validation passed; 426 links, 0 broken.
  - **Unchanged:** M13-DEF-14 to -16, the token figure (~7,260 always-on) and packaging.
  - See `docs/development/2026-09-27-m14-6-m9-smoke-protocol-remediation.md`.
- **M14-5 final product corrections and release gate, 2026-09-27 — `REVIEW`, uncommitted.**
  - **Fixed:**
    - **R-15**: the router and product text now name the owning command.
    - **R-13** (ADR-0052): the verifier launches through `lib/biq_run.sh`, and connects live on this python3-only host.
    - **R-16**: the root cause was double rounding in `pipeline.py`; the correct value is -2.85.
    - **M13-DEF-01**: descriptions are 992 and 1,010 characters, and the limit assertion is committed.
    - **M13-DEF-03**: the mode is `full` for a fully materialised pass.
    - Each fix has a regression test that fails when the old code is restored.
  - **Reviewed and left open, non-blocking:** M13-DEF-14, -15 and -16 are model behaviour, and verifying a fix needs a live evaluation.
  - **M9 live smoke tests** (fresh `claude -p --plugin-dir` sessions, $5.64 in total including three runs cut off by the account session limit):
    - In every run the command was discovered and routed through its skill, there was exactly one gate-authorised scout dispatch with a public query, no file was read, and the verifier was connected.
    - `/company-analysis`, `/market-analysis` and `/industry-research` completed their reports, but wrote a trimmed scout reply (criterion 5); the records were identical to the raw parse.
    - `/competitor-analysis` stopped at a write-guard approval, after running the closing step from a script file.
  - **Token measurement:** ~7,260 always-on, still above the ≤ 3,000 target.
  - **Validation:** full regression 5,301 tests, 0 failures, 31 skipped; strict validation passed; 377 links, 0 broken.
  - **M14 stays `IN PROGRESS`. OWNER RELEASE APPROVAL REQUIRED.** See `docs/development/2026-09-27-m14-5-final-product-corrections.md`.
- **M14-4 release readiness and finalization, 2026-09-27 — `REVIEW`, uncommitted.** Documentation and governance only, plus two label fixes in `README.md`. **Done:** worked examples on the demo data (`docs/examples/README.md`, figures produced by the engine at `8e4ab17`); a troubleshooting guide (`docs/troubleshooting/README.md`); the development-history index completed, 104 missing records added (**D-14 resolved**); the ADR-0013 token measurement taken for the first time (**D-10 resolved**): `claude --plugin-dir <repo> plugin details businessiq` on Claude Code 2.1.283 reports **~7,321 tokens always-on**, with no install and no global state change. That is **above the self-imposed ≤ 3,000 target**, and the response is an owner decision. The ADR-0042 packaging observation was measured: the whole repository ships, including `docs/`, `tests/`, `evals/` and `CLAUDE.md`. That is an owner decision. **Not fixed, owner decisions:** R-13 (the fix changes the Connector-gated `.mcp.json` entry and the tests that pin it); new **R-15** (the `/ask-business-data` router and seven command files plus one skill still say built capabilities "arrive" in a later milestone); new **R-16** (inconsistent rounding of a margin movement, -2.84 versus -2.85 pp). Full regression 5,286 tests, 0 failures, 31 skipped; strict validation passed; 262 links, 0 broken. **M14 stays `IN PROGRESS`; OWNER RELEASE APPROVAL REQUIRED.** See `docs/development/2026-09-27-m14-4-release-readiness.md`.
- **M14-3 component documentation and index reconciliation, 2026-09-27 — `REVIEW`, uncommitted.** Documentation only. The component inventory was verified on disk: 19 command files (18 user-facing commands plus the internal `/retrieval-slice` test harness), 16 skills and 2 subagents. The stale `docs/commands/README.md` ("ten" commands) and `docs/skills/README.md` ("six skills") indexes were rewritten. Five command-family reference pages were added under `docs/commands/`. `docs/agents/` gained the missing `biq-research-scout` page, and its index now lists both built agents and the unbuilt `biq-data-profiler`. `docs/README.md` gained component navigation. **D-13's documentation part is reconciled:** `docs/skills/README.md` maps the 20 designed skills to the 16 shipped (20 − 5 not shipped + 1 outside the design); the owner decision remains open. A new Known issue, **R-14**, records that the M14-2 finding about `forecast.min_history_periods` was wrong: the engine does enforce it. **R-14 was then closed by a narrowly scoped M14-3 follow-up** that corrected the one inaccurate forecasting-history sentence in `README.md`. No code, test, configuration, manifest, `CLAUDE.md` or `architecture.md` change, and no other `README.md` change. See `docs/development/2026-09-27-m14-3-component-documentation.md`.
- **M14-2 `README.md` redesign, 2026-09-27 — `REVIEW`, uncommitted.** `README.md` was redesigned from a milestone log into the primary product and user-facing README. Every claim was verified against the repository. It covers the verified capabilities; the current inventory (18 user commands, 16 skills, 2 subagents); connector availability (none available; the registry is empty); privacy and data boundaries; approval and write safety, including the write guard; the installation and use paths; examples and documentation navigation; forecasting and anomaly limitations; and a newly found final-verification startup limitation (R-13). Only `README.md` changed in the implementation. Full regression 5,286 tests, 0 failures, 31 skipped; strict validation passed. See `docs/development/2026-09-27-m14-2-readme-redesign.md`.
- **M14 entry, 2026-09-27 — Milestone 14 `IN PROGRESS`.** The owner approved the M14 entry gate. Owner decisions: the unexplained working-tree `README.md` change was discarded (the file restored exactly to the committed version) and the unexplained empty untracked `file.txt` deleted. M14-1 reconciled governance and status documentation only; the M14-2 `README.md` rewrite has not started. The M13-DEF-13 and M13-DEF-24 remediations are checkpointed in `595e910`; the M13-DEF-04, -08 and -12 remediations in `8287e98`. No product code changed. See `docs/development/2026-09-27-m14-1-entry-reconciliation.md`.
- **M13-DEF-13 remediation, 2026-09-26 — `fixed_product`, committed in `595e910`.** An owner-authorised product remediation outside M13, which stays `COMPLETED`, and no later milestone is started. Under **ADR-0050** the disclosure gate builds an internal-value register from the working directory's business data on every assessment and screens every request fragment against it. The d05 pattern is refused and nothing is briefed; public research is unchanged. The work adds 32 tests, and the full regression passes (5,194 tests, 0 failures, 31 skipped). No evaluation was run and no evaluation record changed. M13-DEF-14 to -16, -24, -01 and -03 remain open. See `docs/development/2026-09-26-m13-def-13-remediation.md`.
- **M13.2 owner acceptance, 2026-09-26 — M13.2 `COMPLETED`.** The owner reviewed the evidence and accepted M13.2 against ADR-0039 §L. All 64 cases have admissible live evidence across the three evaluation records, kept separate and unchanged: the closing evaluation (`tests/fixtures/eval_results/2026-09-25-closing-evaluation.json`, 16 `automated_pass` / 34 `automated_fail` / 14 `execution_unavailable`, $47.00), the 34-case re-evaluation (`…/2026-09-25-reevaluation-34-cases.json`, $27.26) and the availability-completion evaluation (`…/2026-09-26-availability-10-cases.json`, $17.61). The corrected infrastructure (M13-DEF-17 to M13-DEF-23, all `fixed_infrastructure`) was verified live except ADR-0049's split rule, which no live judge split exercised; **R-01 is closed**; no defect blocks M13 completion; the open product defects (M13-DEF-01, -03, -13, -14, -15, -16, -24) stay separately tracked for owner-assigned remediation; no further paid evaluation was required ($30.14 of the last authorisation unused). With M13.1 already `COMPLETED`, Milestone 13 meets ADR-0039 §L's definition of `COMPLETED`. Checkpointed by the commit "M13.2: complete test hardening and evaluation"; not pushed. See `docs/development/2026-09-26-m13-2-owner-acceptance.md`.
- **Availability-completion evaluation, 2026-09-26 (M13.2 remains `IN PROGRESS`).** The ten cases the re-evaluation could not complete (`r02`–`r09`, `r15`, `r16`), with `execution.max_turns: 20` on those cases only: **10 of 10 `automated_pass`, 60 of 60 runs admissible, no limit hit, no split; $17.61** ($44.87 of $75 used across both evaluations). No new defect. Every one of the 34 corrected cases now has admissible live evidence. `architecture.md` §15/§20 reconciled and **R-01 closed** on 2026-09-26 (`docs/development/2026-09-26-m13-2-documentation-closure.md`); **M13.2 is ready for owner acceptance** and stays `IN PROGRESS` until the owner accepts it. See `docs/development/2026-09-26-m13-2-availability-completion.md`.
- **34-case controlled re-evaluation, 2026-09-25 (M13.2 remains `IN PROGRESS`).** Owner-authorised, $75 cumulative ceiling; **34 of 34 attempted, 159 runs, 105 admissible: 13 `automated_pass`, 11 `automated_fail`, 10 `execution_unavailable`; $27.26.** `r02`–`r09` lost every run to the subscription session limit and `r15`, `r16` runs to the 10-turn limit. No judge split occurred. M13-DEF-17 to -22 verified live; M13-DEF-13 to -16 recurred; **new product defect M13-DEF-24** (overwrite attempted without approval, `a20`). Recorded separately in `tests/fixtures/eval_results/2026-09-25-reevaluation-34-cases.json`; the closing evaluation is unchanged. See `docs/development/2026-09-25-m13-2-reevaluation-34-cases.md`.
- **ADR-0049 — M13-DEF-23 closed, 2026-09-25 (M13.2 remains `IN PROGRESS`).** Owner decision implemented: **a semantic LLM judge split is classified as `execution_unavailable`** — inconclusive automated evidence, not a product failure; no majority rule and no pinned judge. ADR-0049 amends ADR-0039 §E.6 in part. The classifier applies it by default and keeps the prior rule only to confirm stored historical classes; the closing evaluation's 16/34/14 and $47.00 are unchanged. **M13-DEF-17 to M13-DEF-23 are now all `fixed_infrastructure`; none blocks M13 completion.** A new owner-authorised evaluation under the amended contract is still required. See `docs/development/2026-09-25-m13-def-23-adr-0049.md`.
- **ADR-0047 / ADR-0048 remediation, 2026-09-25 (M13.2 remains `IN PROGRESS`).** Owner Decisions 1-3 implemented. **M13-DEF-17 → `fixed_infrastructure`** under **ADR-0047** (amends ADR-0044 in part): 23 routing graders accept the skill or its owning command, derived from the engine registry and command declarations. **M13-DEF-19 → `fixed_infrastructure`** under **ADR-0048** (amends ADR-0041 in part): `a20` declares synthetic fixture EVI-04, staged as `README.md`. **M13-DEF-23 stays `open`:** `d07`'s trace-provable conjunct moved to deterministic graders; five semantic judges retained; classifying a split verdict needs an ADR-0039 §E.6 owner decision. No evaluation run, no class changed; 34 cases need a new authorised evaluation. See `docs/development/2026-09-25-m13-2-adr-0047-0048-remediation.md`.
- **M13-DEF-17 to M13-DEF-23 grader-contract remediation, 2026-09-25 (M13.2 remains `IN PROGRESS`).** **Fixed (`fixed_infrastructure`, not live-verified):** M13-DEF-18, -20, -21, -22 — per-tool graders now carry their semantic pattern as `input_match`, `d08`'s dispatch grader follows ADR-0044's own mapping, and the `b01`/`b02` figure regex excludes exactly the configured threshold. 29 new tests in `unit.test_m13_grader_contract`, each fix caught by an in-memory mutation. **Open, owner decisions required:** M13-DEF-17 (needs an ADR amending ADR-0044's skill mapping), M13-DEF-19 (ADR-0041 admits CSV fixtures only), M13-DEF-23 (split-vote policy). No evaluation was run and no recorded class changed; 14 cases need a new authorised evaluation. See `docs/development/2026-09-25-m13-2-grader-contract-remediation.md`.
- **M13.2 closing evaluation recorded, 2026-09-25 (recording only; M13.2 remains `IN PROGRESS`).** The owner-authorised closing evaluation ran on 2026-09-24/25 as five `claude plugin eval` invocations on Claude Code 2.1.281 (`a*`, `b*`, `c*`, `d*` with `--ablation none`; `r*` with `--ablation with-without`; `--runs 3 --threshold 1.0`): **64 of 64 cases attempted, 258 of 258 runs launched, 190 admissible; `automated_pass` 16, `automated_fail` 34, `execution_unavailable` 14** (subscription session limit or 10-turn limit, not the sandbox). **$47.00 of a $75.00 ceiling; $28.00 unused; no further evaluation authorised.** No manual observation, by the owner's choice of outcome (a). **M13-DEF-05 closed** as `fixed_infrastructure` (the platform loaded 64 of 64). **New:** product M13-DEF-13 (Tier-3 customer identifier passed into research dispatch), M13-DEF-14, M13-DEF-15, M13-DEF-16; evaluation-infrastructure M13-DEF-17 to M13-DEF-23, all `open` — the seven infrastructure defects block M13.2 by rule. See `docs/development/2026-09-25-m13-2-closing-evaluation-record.md`.
- M13.1 added the coverage matrix, the defect register, the measurements, and gap-closure tests. It changed no
  production file.
- **M13.2 implementation, 2026-09-19, uncommitted.** The suite is authored: 64 cases in five suites, three committed
  ADR-0041 input fixtures, and a static validator. It changed no production file.
- **No eval case has ever run.** One was attempted on 2026-09-20 and the harness refused the whole suite at case
  load, so it is `execution_unavailable` and the other 63 are `not_executed`. Neither is a pass.
- **ADR-0039 §E.1 outcome (b) recorded, 2026-09-20:** attempted, and refused for a platform reason. R-01 stays
  `BLOCKED`. This supersedes the outcome (c) recorded on 2026-09-19, which applied while no execution was authorised.
- **G-2 resolved** by documented interpretation (`docs/testing/eval-suite.md`, *Manual observation*):
  - performed by the owner, by hand;
  - one fresh session per S3 row, run outside the repository;
  - records kept in `docs/testing/manual/`.

  **None has been performed.**
- **G-3 stays open.** It is verified at execution time, before any run.
- M10, M11 and M12 are `COMPLETED`. The owner confirmed M10 closed on 2026-09-18.
- M12 closed on M12-B under OD-1, with **M12-C `BLOCKED`** on P-1 to P-5 and its own ADR.
- M9 stays `IN PROGRESS`: the four external commands await owner-run fresh-session live smoke tests, and other rows are
  still `PLANNED`.

**Next gate:** **OWNER RELEASE APPROVAL REQUIRED** — the owner's explicit push of `main`, creation and push of tag `v0.1.0`, and any GitHub release or marketplace publication (`CLAUDE.md` §13), each as its own approved action. Until then BusinessIQ 0.1.0 is a release candidate. Release notes: `docs/releases/0.1.0.md`.
Separately, the open product defects M13-DEF-01, -03 and -14 to -16 await owner-assigned remediation; M13-DEF-13 and
M13-DEF-24 are `fixed_product` (checkpoint `595e910`).

*Earlier next gate (2026-09-20, superseded; the M13-DEF-04 remediation is resolved and checkpointed with M13.2):* owner review of the **M13-DEF-04 remediation**, then a separately controlled step to perform
M13.2's twelve `manual_observation` scenarios.

- **The remediation** was implemented and verified on 2026-09-20 under accepted ADR-0042, and it is not committed:
  T-A to T-K pass, and the full regression passes.
- **The scenarios are no longer blocked by M13-DEF-04.** None has been performed, and M13.2 stays IN PROGRESS.

With no case executed,
the twelve `manual_observation` scenarios remain an ADR-0039 §L condition specific to M13.2, and **M13-DEF-05 must be
closed** before M13.2 can complete. The §L defect,
K.1 to K.6 and documentation conditions are re-checked when M13.2 closes. Any later execution needs the owner's
authorisation, a ceiling and the G-3 pre-flight.

- **M13.1 was approved by the owner** after deterministic hardening and contract-conformance remediation, and
  checkpointed as `33f6e25d58b9b010d7294c08c3b074ce920dd832`.
- **U-1 is resolved** as (c): S2-14 is an OPEN GAP — ENVIRONMENT UNAVAILABLE. It is not counted as coverage.
- **ADR-0040** (Accepted 2026-09-18) amends only ADR-0039 §B's `gap` definition and §L's second M13.1 condition, to
  admit an owner-accepted environment-unavailable gap with a complete disposition record. It resolved the ADR-0039 §L
  completion-gate contradiction. S2-14 is its first application. It stays a `gap`: not covered, and not a defect.
- **M13-DEF-01 and M13-DEF-03 stay open**, remediation unassigned. M13-DEF-02 stays resolved. **M13-DEF-04**
  (found 2026-09-19, M13.2 WD-1) is **RESOLVED 2026-09-20, not yet committed**.
  - **Architecture:** ADR-0042, accepted 2026-09-19.
  - **Runtime verification:** V-1, V-2a and V-2b PASS.
  - **Implementation:** the dedicated remediation milestone, which is outside M13 (I-13), delivered
    `lib/python/biq_run.py`, migrated 10 commands and 16 skills, and added T-A to T-K.
  - **Evidence:** the full regression passes. See `docs/development/2026-09-20-m13-def-04-implementation.md`.
  - **Register status:** `fixed_product`. **ADR-0043** (accepted 2026-09-20) amends ADR-0039 §G.1's vocabulary to
    represent a product defect fixed and verified by a dedicated milestone outside M13 (`docs/testing/defects.md`).
  - **Still open:** G-3 (the eval sandbox), V-4 (the minimum CLI version) and Unix-like runtime verification.
- **Stage 2 pilot, 2026-09-22 (first attempt).** One case was started and **no case executed**: the run was refused before turn 1 because every case carries a shell grant and this machine had no active sandbox backend. The harness scored the zero-turn run 1.0, which is **not evidence**. **M13-DEF-06 was raised for that and fixed on 2026-09-22**: a result is now admissible only if its run executed, enforced deterministically.
- **Executed pilot, 2026-09-22 (second attempt, sandbox active).** The case loaded and **the agent ran**: 5 turns, `error: null`, one graded criterion, $0.1712634. It **failed** — `g-no-approval-request` on votes `FAIL PASS FAIL` — so the case is `automated_fail` under §E.6, because an observed failure outranks an unavailability. **It tested nothing about BusinessIQ.** The command was never reached: the declared input was not staged (**M13-DEF-07**, fixed) and no `python` exists on this machine to enter the engine (**M13-DEF-08**, product, open). The trace was not kept (**M13-DEF-09**, fixed). The sandbox environment question is resolved; **the next gate is M13-DEF-08**, an owner decision, without which re-running the case cannot change the outcome.
- **Evaluation-harness remediation, 2026-09-22.** Input staging implemented and proved, the trace requirement written into the procedure, and three defects recorded. **Nothing was promoted:** no case passed, §E.1 is not satisfied (it requires `--runs 3`; the pilot was authorised for one), and R-01 stays `BLOCKED`.
- **§F.6 scaffold coverage completed, 2026-09-23.** The remaining **37** `requires_business_file` cases gained their scaffolds, each generated from the case's own declared `inputs` with no mapping inferred: 35 stage `assets/demo-data/northwind_sales.csv` and 3 stage their own `tests/fixtures/eval_inputs/` fixture. **All 38 business-file cases now stage their fixture**, 64/64 cases remain platform-loadable and 133/133 graders mapped. The validator's hand-kept staged list is gone, replaced by an invariant asserted both ways, and all 38 scaffolds are executed in `integration.test_m13_eval_scaffold`. M13-DEF-07's scope is closed and its status is unchanged. **No evaluation was run**; the suite is structurally ready for the closing execution, which remains owner-gated.
- **M13-DEF-12 remediated, 2026-09-23.** Under accepted **ADR-0046**, which amends ADR-0045 in part (its Windows-suffix rule only; ADR-0045 was not edited): **under WSL the automatic candidate search no longer tries `.exe`, `.com`, `.bat` or `.cmd`.** `BIQ_PYTHON`, native Windows and native Linux behaviour are all unchanged, and the rule is about the suffix rather than the directory. WSL is detected by reading `/proc/sys/kernel/osrelease` with the `read` built-in — no external command, not environment-steerable, and failing safe to "not WSL". **11 effective lines** in `lib/biq_run.sh`; 15 new tests that put a *working* Windows stub ahead of the native one for each suffix; 3 mutations each caught (9/9/3 failures). **Live:** `sh lib/biq_run.sh --where` now selects `/usr/bin/python3` automatically and exits 0, from the repository and from an external cwd, with the Windows interpreter still on `PATH` and still passing the probe. **No evaluation was run**, the case remains `automated_fail`, and M13.2 remains `IN PROGRESS`.
- **Final pre-flight, M13-DEF-11 closed and M13-DEF-12 found, 2026-09-23.** The operator set the outer Claude Code session to `No Sandbox`, and the pre-flight verified the nested-sandbox condition is gone: the `AF_UNIX` `bind`+`listen` that returned `EPERM` now succeeds, with the evaluator's own sandbox untouched (`enabled`, `failIfUnavailable: true`, `allowUnsandboxedCommands: false`) and no bypass. **M13-DEF-11 → `fixed_infrastructure`** — environment prerequisite verified, live evaluator start still not observed. **The same pre-flight then failed at the runtime gate**: with the host's real `PATH` visible for the first time (25 `/mnt/c` entries via WSL interop), the resolver selects `/mnt/c/Python313/python.exe`, which passes the version probe but cannot address the Linux engine path, so `sh lib/biq_run.sh --where` exits 2. Recorded as **M13-DEF-12**, product, open — masked until now because the sandbox had hidden those `PATH` entries. `BIQ_PYTHON=/usr/bin/python3` is an existing documented workaround. **No evaluation was run**, and the pre-flight gate caught it before any spend.
- **Third evaluation and M13-DEF-11, 2026-09-23.** The owner-authorised three-run evaluation reached further than any before it: **zero permission denials**, `Glob` located the staged fixture, the agent issued the exact authorised resolver command, and **`g-command-ran` passed 3 of 3** — the first deterministic trace-mapped grader ever to score, validating **ADR-0044 stage 3 and the M13-DEF-10 remediation live**. The engine was still not reached: every Bash attempt failed with `Sandbox is required but failed to initialize: EPERM … listen '<run>/tmp/srt-mux-*.sock'`. Diagnosed without any further evaluation as **nested sandboxing** — the evaluator's per-command sandbox cannot initialise inside an already-sandboxed outer session, proved by an `AF_UNIX` `bind`+`listen` that fails `EPERM` sandboxed and succeeds unsandboxed. Recorded as **M13-DEF-11**, open. **The remediation is one operator action** — set the outer Claude Code session to `No Sandbox` via `/sandbox` — **and no repository change**; the evaluator's own sandbox stays enabled, with no bypass. Case remains `automated_fail`.
- **M13-DEF-10 remediated, 2026-09-23.** The investigation established from the platform binary and the kept run's own config that **`Read` was never permitted** in the pilot: the harness computes read scopes only when the operator grant list holds a *bare* read tool, and the pilot passed only the patterned `Bash` resolver grant — so the tool roster listing `Read` meant nothing. The remediation adds a bare `Read` beside the unchanged resolver grant, which covers the staged fixture because the run's working directory sits under the run's home. `Bash(ls:*)` was considered and **rejected**: it keeps discovery inside the shell, whereas `Read` cannot execute anything. No prompt, production, runtime or resolver file was touched. **Deterministically corrected, not live-verified** — no evaluation was run, and the case remains `automated_fail`. **The next run needs only owner authorisation and a ceiling.**
- **Three-run pilot, ADR-0044 stage 3 and M13-DEF-10, 2026-09-22.** The owner-authorised three-run pilot of `a01-read-only-anomaly-detection` executed under the full §F policy — three admissible runs, 4 turns each, $0.5577 of a $5 ceiling — and is the **first conforming §E.1 measurement: outcome (a)**. The case is **`automated_fail`**: `g-no-approval-request` failed 9 of 9 judge votes because the engine was never reached, not because BusinessIQ asked for approval. Its kept traces supplied the fact ADR-0044 had been staged around since 2026-09-20, and **stage 3 mapped all 24 remaining graders** — 133 of 133 mapped, 0 pending, **64 of 64 cases platform-loadable**. The run also confirmed M13-DEF-07's staging fix live, and raised **M13-DEF-10**: the narrow resolver grant does not cover the read-only `ls` the agent issues first, and in `dontAsk` mode that denial ended the attempt. **R-01 is ready for owner closure. M13-DEF-05's stated conditions are met and closure is recommended.** Both are owner acts and neither was performed.
- **M13-DEF-08 runtime resolution, 2026-09-22.** The owner selected Option C and authorised it; **ADR-0045** accepted and implemented the same day. `lib/biq_run.sh` is now the one place BusinessIQ chooses a Python interpreter, and no command or skill names one: 26 shipped files, 34 blocks, 66 new tests, full regression green. ADR-0042's launcher, import boundary and isolation are unchanged and its 37 guarantee tests still pass. **The remaining gate before any evaluation is the `--allow-tools` grant**, because the invocation's first token is now `sh`; that is an owner decision and no run may precede it.
- **§E.1 is not satisfied, and outcome (b) no longer describes the facts.** The 2026-09-20 execution was refused at case load; the cause was established on 2026-09-22 as the suite not being in the platform's case format. **ADR-0044 Phase 1** migrated it on 2026-09-22 — 109 of 133 graders, 61 of 64 cases — but **24 graders and 3 cases remain pending** a trace fact only a run supplies, and the run that could have supplied it kept no trace. §E.1 requires the measurement at `--runs 3`, and the one execution was authorised for a single run, so **no §E.1 outcome is recorded from it**. What it did establish is that execution is *available* — the evidence (a) turns on — but (a) may be recorded only from a conforming measurement, so **R-01 stays `BLOCKED`**. Infrastructure defect **M13-DEF-05** stays `open` and **blocks M13.2's completion**: one of its two closure conditions is now met (a case loads and executes), stage 3 is not.
- **ADR-0041** (Accepted 2026-09-19) resolves M13.2 contract item G-1 only. It amends ADR-0039 §E.2 and §E.5 in part,
  to admit committed, builder-reproduced eval input fixtures under `tests/fixtures/eval_inputs/`. G-2 (manual
  observation ownership) and G-3 (fresh platform surface check before any execution) stay open. It authorises no
  execution.
- **M13.2 implementation was authorised** by the owner's M13.2 implementation prompt of 2026-09-19. **Execution was
  not.**

See `docs/development/2026-09-19-m13-2-eval-implementation.md`,
`docs/development/2026-09-18-m13-1-contract-conformance-adr-0040.md`,
`docs/development/2026-09-18-m13-1-final-remediation.md` and
`docs/development/2026-09-18-m13-1-deterministic-hardening.md`.

*This header replaced a 2026-09-13 header that described Milestone 9-D as the next gate. That history is kept in the
Milestone 9 section below and in `docs/development/`.*

Statuses: `PLANNED` · `IN PROGRESS` · `BLOCKED` · `REVIEW` · `COMPLETED` · `DEFERRED`

> A task is `COMPLETED` only when it has been implemented **and** exercised by a test that
> was actually run, with output recorded in the dated development record.

> **Revision 2 roadmap change:** an end-to-end **vertical slice** is now Milestone 2, so the
> architecture is proven on real synthetic data before 20 skills and 17 commands are built.
> Synthetic demo data moved from M13 to M2. Business Context added to M1. Milestone count
> 13 → 14.

---

## Milestone summary

| # | Milestone | Status | Depends on |
|---|---|---|---|
| 0 | Architecture & Governance | `COMPLETED` | — |
| 1 | Foundation: skeleton, references, Business Context, runtime | `COMPLETED` | M0 |
| 2 | **VERTICAL SLICE — end-to-end proof on synthetic data** | `COMPLETED` | M1 |
| 3 | Data Layer — full ingestion & semantic mapping | `COMPLETED` | M2 |
| 4 | Data Quality & Validation — full | `COMPLETED` | M3 |
| 5 | KPI Engine — full registry | `COMPLETED` | M4 |
| 6 | Internal Analytics Skills | `COMPLETED` | M5 |
| 7 | Internal Analytics Commands | `COMPLETED` | M6 |
| 8 | Forecasting & Anomaly Detection | `COMPLETED` | M5 (see D-09) |
| 9 | External Intelligence & the Disclosure Gate | `IN PROGRESS` (9-A to 9-D built. The four external commands are `REVIEW`. All four passed their fresh-session live smoke tests on 2026-09-27 in M14-6, with every documented criterion met: the scout's reply reached the parser byte-identical to what the harness recorded, via the ADR-0053 capture. The four command rows are `COMPLETED`. The M14-5 attempt failed criterion 5; see its record. See `docs/development/2026-09-27-m14-6-m9-smoke-protocol-remediation.md`. The `biq-external-research` skill is `PLANNED` and unscheduled (D-13). Three tier-test rows are M13 coverage set S6 under ADR-0039. Covering them does not complete M9) | M1, M3, M5, M6, M7 |
| 10 | Synthesis & Executive Reporting | `COMPLETED` (reconciled 2026-09-18 and confirmed closed by the owner the same day. M10.1 through M10.3.4, including the Executive Report, are each `COMPLETED` and checkpointed, `62580f3` to `4dc6562`. The synthesis forecast translator is a separate, unscheduled decision, not M10 scope) | M7, M8, M9 |
| 11 | Subagents (remaining two) | `COMPLETED` (verification & finalisation; `biq-data-profiler` as the deterministic data profile, its subagent deferred to M12 by ADR-0036) | M3, M10 |
| 12 | MCP Connector Layer | `COMPLETED` under OD-1 (M12-A contract `COMPLETED (DECISION ONLY)`, ADR-0037 accepted. M12-A.1 `COMPLETED (DECISION ONLY)`, ADR-0038 accepted with OD-3. M12-B `COMPLETED`: owner-approved and checkpointed `990e88d`, registry empty by design, no connector admitted. **M12-C `BLOCKED`**) | M3 |
| 13 | Test Hardening & Evals | `COMPLETED` (M13-A `COMPLETED (DECISION ONLY)`, ADR-0039 accepted. **M13.1 `COMPLETED`**: owner-approved and checkpointed `33f6e25`; U-1 resolved as an accepted open gap under ADR-0040. **M13.2 `COMPLETED`**: owner-accepted 2026-09-26 and checkpointed `8287e98`; all 64 cases have admissible live evidence across three evaluation records; R-01 closed under §E.1 (a). No defect blocks M13. M13-DEF-04, -08 and -12 `fixed_product`, checkpointed `8287e98`; M13-DEF-13 and -24 `fixed_product`, checkpointed `595e910`; M13-DEF-01, -03 and -14 to -16 open, product, non-blocking) | M10 |
| 14 | Documentation & Release | `IN PROGRESS` (M14-1 entry and status reconciliation, checkpointed `50d1f0e`; M14-2 `README.md` redesign, checkpointed `5c1b15d`; M14-3 component documentation and index reconciliation, checkpointed `8e4ab17`; M14-4 release readiness, M14-5 final product corrections and release gate and M14-6 M9 smoke-test protocol remediation, checkpointed in `57e92fa`; release tagging `PLANNED`, OWNER RELEASE APPROVAL REQUIRED) | M13 |

M8, M9 and M12 are independent once prerequisites land and can be resequenced on request.

---

## Milestone 0 — Architecture & Governance · `COMPLETED`

### Revision 1 (architecture gate)

| Task | Status |
|---|---|
| Inspect repository and git state | `COMPLETED` |
| Determine real plugin conventions (validated `--strict`) | `COMPLETED` |
| Verify runtime availability | `COMPLETED` |
| Prove stdlib xlsx ingestion feasible | `COMPLETED` |
| Measure always-on token cost model | `COMPLETED` |
| Establish connector availability facts | `COMPLETED` |
| Write `CLAUDE.md`, `architecture.md`, `project_plan.md`, `docs/`, ADR-0001…0007 | `COMPLETED` |
| Dated development record | `COMPLETED` |

### Revision 2 (architecture review corrections)

| Task | Status | Notes |
|---|---|---|
| Resolve production xlsx ingestion | `COMPLETED` | `Read` tool cannot open xlsx (verified); both readers built and run; ADR-0008 |
| Verify pip / PyPI / venv / npm availability | `COMPLETED` | pip 24.3.1, PyPI reachable, venv+ensurepip OK, openpyxl 3.1.5 installed in isolated venv |
| Redesign internal/external privacy boundary | `COMPLETED` | Four-tier disclosure, local-join default; ADR-0009 |
| Clarify approval gates | `COMPLETED` | Consequence-based matrix; ADR-0010 |
| Verify the 4,000-token "ceiling" | `COMPLETED` | **No platform limit exists**; 42-component probe = ~2,617 tok; ADR-0013 |
| Promote Business Context to first-class | `COMPLETED` | ADR-0011 |
| Verify the 25-skill architecture | `COMPLETED` | Placement rule → 20 skills + 6 references; ADR-0012 |
| Move vertical slice early in the roadmap | `COMPLETED` | Now Milestone 2 |
| Update `architecture.md` to Revision 2 | `COMPLETED` | |
| Update `CLAUDE.md`, `project_plan.md`, docs indexes | `COMPLETED` | |
| Dated development record for the review | `COMPLETED` | `docs/development/2026-09-08-architecture-review-corrections.md` |
| **External architecture review** | `COMPLETED` | Revision 2 approved 2026-09-08 |

Testing status: N/A (no product code). Documentation status: complete.
**Revision 2 approved by the project owner on 2026-09-08.**

---

## Milestone 1 — Foundation · `COMPLETED`

| Task | Status | Evidence |
|---|---|---|
| `.claude-plugin/plugin.json` + `marketplace.json` | `COMPLETED` | Manifest validates with 0 errors, 0 warnings; marketplace passes `--strict` |
| `README.md`, `LICENSE`, `CONNECTORS.md` | `COMPLETED` | README states implemented-vs-planned explicitly |
| `.gitignore` += `.businessiq/`, `businessiq-output/` | `COMPLETED` | Each pattern verified with `git check-ignore`; trailing-comment bug found and fixed |
| `config/businessiq.defaults.json` + precedence resolver | `COMPLETED` | 4-layer precedence tested incl. per-key provenance |
| `config/vocabulary.json` controlled vocabulary | `COMPLETED` | 10 business models, 16 industries, 7 size bands |
| `lib/schemas/business_context.schema.json` | `COMPLETED` | Identity / reporting / analysis, with `x-privacy` per field |
| `lib/python/biq/jsonschema_mini.py` | `COMPLETED` | Stdlib validator + unsupported-keyword guard |
| `lib/python/biq/context/` — load, validate, resolve, privacy | `COMPLETED` | 41 tests |
| `lib/python/biq/runtime/` — tier resolver + consent gate | `COMPLETED` | 29 tests; no-silent-install proven |
| `reference/` — the 6 policy documents | `COMPLETED` | 431 lines, no duplicated rules |
| `tests/run_tests.py` harness | `COMPLETED` | **120 tests, 0 failures, 0 errors** |
| Measure always-on token cost | `COMPLETED` | **~0 tok** (no components yet); confirms `reference/` costs nothing |
| **Milestone 1 review** | `COMPLETED` | Approved 2026-09-08 |

Exit criteria — all met: manifests validate · harness green · Business Context round-trips
through schema validation · tier resolver correctly reports Tier 3 on this machine.

**Deferred from M1 with reason:** `.mcp.json` was not created. It belongs to M12 and is
`BLOCKED` behind the Connector gate; creating it now would imply connector work has begun.

**Not created (empty until their milestone):** `commands/`, `skills/`, `agents/`, `evals/`,
`assets/demo-data/`, `tests/integration/`, `tests/negative/`.

---

## Milestone 2 — VERTICAL SLICE · `COMPLETED`

**Purpose:** prove the architecture end to end on synthetic data before building the
remaining skills, commands, agents and connectors.

| Task | Status | Evidence |
|---|---|---|
| Synthetic demo dataset (xlsx + CSV, 24 months) | `COMPLETED` | 2,204 rows, 6 products, 4 regions, 5 salespeople, 24 customers; deterministic (SHA-256 verified) |
| Ingestion — CSV | `COMPLETED` | Encoding fallback, delimiter sniffing, type coercion, ragged rows |
| Ingestion — XLSX Tier 1 (openpyxl) | `COMPLETED` | Exercised with openpyxl 3.1.5; Scenario F passes |
| Ingestion — XLSX Tier 3 (stdlib) | `COMPLETED` | Shared + inline strings, styled dates, cached formula values, built-in numFmt ids |
| Reader tier recorded on every dataset | `COMPLETED` | Appears in provenance and the report basis line |
| Semantic mapping + confirm-below-threshold | `COMPLETED` | Name *and* content scored; Scenario D passes |
| Data quality — 4 families, CRITICAL halt | `COMPLETED` | Scenario B: 3 distinct CRITICAL fixtures all halt |
| KPI engine — 5 computed + unavailable + not_applicable | `COMPLETED` | All formulas in `lib/python/biq/kpi/registry.py` only |
| Business Context relevance | `COMPLETED` | Scenario C: retail ⇒ `not_applicable`, saas ⇒ attempted |
| Materiality (material / not / undetermined) | `COMPLETED` | Filters, never halts; names threshold + source |
| Evidence ledger, provenance survives | `COMPLETED` | Source named, formulas carried, caveats propagate |
| `biq-sales-intelligence` skill | `COMPLETED` | Interprets only; performs no arithmetic |
| `/business-health` command | `COMPLETED` | Thin orchestrator; contains no formula or threshold |
| Executive-style output | `COMPLETED` | Quality warning precedes figures; FACT/INTERPRETATION distinct |
| Test scenarios A–F + integration | `COMPLETED` | **271 tests, 0 failures, 0 errors** |
| Plugin validation with first skill + command | `COMPLETED` | No new warnings beyond R-08 |
| Token measurement | `COMPLETED` | ~271 tok for 2 components; see R-09 |
| **Milestone 2 review** | `COMPLETED` | Approved 2026-09-08 |

**Exit criteria — all seven met:** ingestion works on a real file · validation halts
correctly · calculations are deterministic and reproducible · Business Context drives KPI
relevance · provenance survives end to end · output standards render correctly · the
orchestration chain runs reliably.

**Deliberately not done in M2:** out-of-process Tier 2 reading (M3); the
`biq-semantic-mapping` skill wrapper (M3, engine layer only in M2); the remaining 13 quality
check families (M4); the remaining ~22 KPIs (M5).

---

## Milestone 3 — Data Layer (full) · `COMPLETED`

| Task | Status | Evidence |
|---|---|---|
| Tier 1 hardening (read-only, data-only, hidden sheets, merged cells) | `COMPLETED` | Warned and documented; open failures wrapped |
| **Tier 2 out-of-process managed runtime** | `COMPLETED` | Worker module; verified reading 2,204 rows and agreeing with Tier 3 |
| Tier 3 completion (built-in + custom formats, 1904, strings, relationships) | `COMPLETED` | Cross-tier corpus passes |
| Tier 4 guided CSV export representation | `COMPLETED` | States reason, structure, loss, source untouched |
| Workbook inspection before reading | `COMPLETED` | `ingest/workbook.py`; encryption/corruption fail up front |
| Formula handling — cached only, never evaluated | `COMPLETED` | Missing cached value warns, never invents |
| Shared formulas / external refs / macros / encryption | `COMPLETED` | Detected, never followed or executed; clear failure for encrypted |
| Canonical dataset with derived/source separation | `COMPLETED` | `raw_rows()` vs `normalized_rows()`; source byte-identical after read |
| Type/date/currency normalization | `COMPLETED` | Decimal money; ambiguity flagged, never guessed |
| Currency mismatch and mixed-currency handling | `COMPLETED` | Both CRITICAL; no conversion applied |
| Streaming / processing-mode recording | `COMPLETED` | Mode in provenance; incomplete pass adds a global ledger caveat |
| Semantic mapping evidence + explainability | `COMPLETED` | `Evidence`, `explain()`, rejected candidates |
| Field-level sensitivity classification (6 classes) | `COMPLETED` | Name + content signals; unmatched defaults to internal |
| Privacy-preserving aggregation primitives | `COMPLETED` | k-floor, banding, whole-query re-identification. No network calls |
| Cross-tier equivalence, expanded corpus | `COMPLETED` | 6 fixtures + demo workbook; equivalence defined precisely |
| Negative / adversarial tests | `COMPLETED` | Corrupt, malformed, encrypted, external refs, mixed currency, ambiguous formats |
| Performance baseline | `COMPLETED` | 60k-row CSV at ~98k rows/s; recorded, not optimised |
| M1/M2 regression | `COMPLETED` | **403 tests, 0 failures**; M2 slice verified working |
| **Milestone 3 review** | `COMPLETED` | Approved 2026-09-08 |

**Deliberately not done in M3:** the `biq-semantic-mapping` skill wrapper (later milestone —
M3 is the engine layer); true chunked streaming (mode is recorded correctly, but very large
files are not yet optimised); currency conversion (out of scope by design).

---

## Milestone 4 — Data Quality (full) · `COMPLETED`

The thirteen approved families, from the product specification's validation list (which is
what `architecture.md` means by "13 check families").

| Task | Status | Evidence |
|---|---|---|
| Uniform check contract (`CheckSpec` / `CheckResult` / `Finding`) | `COMPLETED` | Every family declares purpose, severity policy, halt capability, thresholds |
| 1 `missing_values` | `COMPLETED` | Broken fixture halts; minor case is INFO |
| 2 `duplicate_records` | `COMPLETED` | 33% duplicates → CRITICAL |
| 3 `invalid_dates` | `COMPLETED` | Unparseable, ambiguous, future and implausible dates |
| 4 `invalid_numbers` | `COMPLETED` | Both severities covered; ambiguity routed by shape |
| 5 `negative_values` | `COMPLETED` | Never CRITICAL — refunds are legitimate |
| 6 `missing_periods` | `COMPLETED` | 8 of 12 months absent → CRITICAL |
| 7 `duplicate_transactions` | `COMPLETED` | Never CRITICAL — multi-line orders are legitimate |
| 8 `inconsistent_customers` | `COMPLETED` | Variants detected, values redacted |
| 9 `inconsistent_products` | `COMPLETED` | Variants detected |
| 10 `currency_consistency` | `COMPLETED` | Mixed currency and context contradiction both CRITICAL |
| 11 `outliers` | `COMPLETED` | Data-integrity only; never CRITICAL, never "fraud" |
| 12 `broken_formulas` | `COMPLETED` | Missing cached values, error cells, stale external refs |
| 13 `incomplete_dataset` | `COMPLETED` | No rows, too few columns, missing roles, degraded tier, partial processing |
| `quality_report.schema.json` + validation | `COMPLETED` | Every fixture's report validates; `$ref` support added to the validator |
| Severity model INFO/WARNING/CRITICAL | `COMPLETED` | All three paths tested; 6 families cannot halt |
| Quality gate integration | `COMPLETED` | Clean passes, warnings preserved on every claim, CRITICAL halts |
| Thresholds with configuration provenance | `COMPLETED` | 10 `quality.*` keys; override and tighten both tested |
| Privacy-safe reporting | `COMPLETED` | Sensitive values redacted; no emails, names or keys in reports |
| Processing-mode awareness | `COMPLETED` | Sampled run never reported as exhaustive |
| Broken fixture per family | `COMPLETED` | Plus multi-failure and warning-only fixtures |
| Adversarial tests | `COMPLETED` | 27 cases |
| M2/M3 regression | `COMPLETED` | **478 tests, 0 failures**; slice figures identical |
| **Milestone 4 review** | `COMPLETED` | Approved 2026-09-08 |

**Deliberately not done in M4:** fuzzy entity matching for label variants (guessing that two
customers are one is what the ambiguity protocol forbids); distributional outlier modelling
(this is data integrity, not anomaly intelligence); non-monthly period granularity;
row-level evidence in reports (a privacy trade).

---

## Milestone 5 — KPI Engine (full) · `COMPLETED`

The approved 27 from the product specification's KPI list, plus one metric retained from M2.

| Task | Status | Evidence |
|---|---|---|
| KPI contract (`KPIDefinition` / `KPIResult`) | `COMPLETED` | Every definition declares inputs, unit, aggregation, applicability, minimum periods |
| 27 approved KPIs implemented | `COMPLETED` | Registry holds 28 (27 approved + `net_revenue_retention` retained from M2) |
| Shared deterministic primitives | `COMPLETED` | All arithmetic in `primitives.py`; dependent metrics share one revenue total |
| Four-bucket result model + `partial` | `COMPLETED` | `available` / `unavailable` / `not_applicable` / `insufficient_data`, plus architecture's `partial` |
| Decimal money, rounding at presentation | `COMPLETED` | Large-value and 0.1+0.2 boundary tests |
| Currency safety | `COMPLETED` | Mixed currency and context mismatch refuse monetary metrics only; never converts |
| Business Context applicability | `COMPLETED` | retail ⇒ recurring metrics N/A; saas ⇒ inventory + AOV N/A; no context ⇒ nothing suppressed |
| Quality gate integration | `COMPLETED` | CRITICAL suppresses all; WARNING attaches caveats; PASS clean |
| Provenance on every result | `COMPLETED` | Source, rows, timestamp, processing mode, quality grade, formula, inputs |
| `kpi_results.schema.json` + validation | `COMPLETED` | Every document validates; absent metrics included |
| Error containment | `COMPLETED` | A raising calculator becomes a structured result, never a traceback |
| Edge cases | `COMPLETED` | Zero revenue/orders/investment, no decided deals, cash-generative, loss-making, single period, large values, rounding boundaries |
| Cross-KPI consistency | `COMPLETED` | Gross profit/margin, operating margin, EBITDA, AOV, ARR=MRR×12, retention+churn=100 |
| Demo dataset honest reporting | `COMPLETED` | **8 available, 16 unavailable, 4 not_applicable** — nothing manufactured |
| Performance baseline | `COMPLETED` | 28 metrics in 0.22s on 30k rows |
| M1–M4 regression | `COMPLETED` | **559 tests, 0 failures**; M2 figures identical |
| **Milestone 5 review** | `COMPLETED` | Approved 2026-09-08 |

**Deliberately not done in M5:** forecasting (a projected CLV needs a retention curve);
non-monthly period granularity; configurable comparison windows; anomaly detection.

---

## Milestone 6 — Internal Analytics Skills · `COMPLETED`

The interpretation layer above the KPI engine. Scope taken from this file and
`architecture.md` section 4 Layer 2A, which agree exactly — unlike the M4 and M5
taxonomies, the M6 component list *is* enumerated in the repository.

| Task | Status | Evidence |
|---|---|---|
| Analysis output contract | `COMPLETED` | `AnalysisFinding` / `AnalysisSet` / `Limitation`; four statuses, four classifications |
| `biq-sales-intelligence` (full) | `COMPLETED` | Revenue and order trend, five dimensions, mix, contribution, concentration; 43 findings on the demo data |
| `biq-customer-intelligence` | `COMPLETED` | Population, new vs returning, repeat, retention, concentration, cohorts; behaviour only, never inferred intent |
| `biq-product-intelligence` | `COMPLETED` | Contribution, growth, mix, per-product margin, concentration, later entrants |
| `biq-financial-analysis` | `COMPLETED` | Profit walk, margin movement in points, cost ratio, concentration exposure, and every unavailable metric named |
| Segmentation primitives | `COMPLETED` | Deterministic ordering `(-total, key)`; competition ranking for ties |
| Cohort primitives | `COMPLETED` | First-appearance definition; retention curve averaged only over cohorts that reached each offset |
| Concentration primitives | `COMPLETED` | Top-N, CR-N, members-for-half, HHI — reported as numbers, judged by `materiality` |
| Mix primitives | `COMPLETED` | Shares, shift in percentage points, contribution to a net change |
| KPI integration | `COMPLETED` | `basis` equals the engine formula verbatim; revenue growth consumed, not recomputed |
| Quality integration | `COMPLETED` | CRITICAL ⇒ no claim in any domain; WARNING ⇒ caveat on every finding and confidence downgraded |
| Materiality | `COMPLETED` | One system: `assess_amount`, `assess_margin`, `assess_share_of_revenue`; `undetermined` preserved |
| Privacy | `COMPLETED` | `LOCAL` / `SHAREABLE` label policy over the M3 classification; k-floor banding in both modes; no transaction ever emitted |
| Fact/calculation/interpretation split | `COMPLETED` | Engine may emit only FACT and CALCULATION; `AnalysisSet.add` raises otherwise |
| Demo dataset honest reporting | `COMPLETED` | Sales 43/0, customer 24/2, product 20/1, **financial 7 findings against 10 limitations** |
| Negative and insufficient-data tests | `COMPLETED` | `tests/negative/` created; 22 cases covering every failure mode in the brief |
| Performance baseline | `COMPLETED` | 4 domains in 0.07s on the demo data, 0.46s on 30k rows |
| M1–M5 regression | `COMPLETED` | **698 tests, 0 failures**; `/business-health` output identical |
| **Milestone 6 review** | `COMPLETED` | Approved 2026-09-09 |

**Deliberately not done in M6:** any new command (M7); forecasting and anomaly detection
(M8); causal attribution; non-monthly granularity; configurable comparison windows.

## Milestone 7 — Internal Analytics Commands · `COMPLETED`

Seven thin orchestrators over the Milestone 6 skills. Scope taken from this file, which
enumerates all seven; `architecture.md` states a count of 17 commands and enumerates none
(D-06).

| Task | Status | Evidence |
|---|---|---|
| Command registry (declaration as data) | `COMPLETED` | Seven specs: domains, skill, focus metrics, sections, required roles |
| `/business-health` (full) | `COMPLETED` | All four domains; embeds the M2 executive report whole and adds the cross-domain view |
| `/sales-analysis` | `COMPLETED` | Sales domain; 43 findings across five dimensions on the demo data |
| `/customer-analysis` | `COMPLETED` | Customer domain; `--shareable` pseudonymisation; k-floor banding preserved |
| `/product-analysis` | `COMPLETED` | Product domain; margin, concentration, later-entrant fact |
| `/profitability-analysis` | `COMPLETED` | Financial domain, profit-statement focus; partial 3/8 on the demo data |
| `/cash-flow-analysis` | `COMPLETED` | Financial domain, cash focus; **unavailable 0/5** on the demo data, each field named |
| `/ask-business-data` | `COMPLETED` | Four outcomes: routed / clarification / unsupported / unavailable. Never guesses |
| Coverage verdict per command | `COMPLETED` | complete / partial / unavailable / not_applicable, stated before the numbers |
| Output contract reused, not replaced | `COMPLETED` | M6 `AnalysisSet` unchanged; `CommandResult` is a wrapper with no analytical state |
| Business Context | `COMPLETED` | Model, currency, period and comparison window surfaced; applicability still drives KPIs |
| Quality integration | `COMPLETED` | CRITICAL halts all seven; WARNING caveats every finding; checks never re-run |
| Materiality | `COMPLETED` | No command-specific threshold; verdicts pass through with their reasons |
| Evidence and provenance | `COMPLETED` | Source, tier, mode, formula, fields, periods, caveats, confidence all survive; zero untraceable claims added |
| Privacy | `COMPLETED` | Classification byte-identical before and after; no transaction rendered by any command |
| Negative and insufficient-data tests | `COMPLETED` | 29 cases covering every failure mode in the brief |
| Cross-command tests | `COMPLETED` | Mapping, no duplicate calculation, KPI/quality/materiality/evidence/privacy preservation, M2 non-regression |
| Performance baseline | `COMPLETED` | 0.57–0.63s on the demo data; 1.85–1.92s on 30k rows |
| M1–M6 regression | `COMPLETED` | **820 tests, 0 failures**; M2 snapshot markers intact |
| **Milestone 7 review** | `REVIEW` | **Blocking gate** |

**Deliberately not done in M7:** forecasting and anomaly detection (M8); external research
(M9); executive reporting (M10); sub-period filtering; multi-file joins; any new skill.

## Milestone 8 — Forecasting & Anomaly Detection · `COMPLETED`

Two optional passes over a completed pipeline run, siblings of the M6 analytics rather than
a layer above them. Scope taken from this file and `architecture.md` (§5 skills, §13 engine
packages and schemas, §14 configuration, §18 the registration extension point).

| Task | Status | Evidence |
|---|---|---|
| `forecast/` engine: contract, series, methods, validate, variance, engine | `COMPLETED` | 5 methods, each with an adequacy predicate; stdlib only |
| Forecast methods with adequacy predicates | `COMPLETED` | `naive` 2 · `moving_average` 3 · `drift` 4 · `linear_trend` 6 · `seasonal_naive` 13 |
| Backtest-driven method selection | `COMPLETED` | Every adequate method scored on held-out history; ties break on declared priority; all candidates reported |
| Scenario bands (base / upside / downside) | `COMPLETED` | Each states its assumption, adjustment and caveat |
| Assumption register | `COMPLETED` | `reference/evidence-ledger.md` class 6; 11 entries on the demo dataset |
| Uncertainty band, explicitly not a confidence interval | `COMPLETED` | `statistical_interval` is a required constant `false` in the schema |
| Holdout validation with MAPE + MAE | `COMPLETED` | Zero actuals excluded from MAPE and counted |
| Forecast vs actual | `COMPLETED` | `forecast/variance.py`; reuses the existing materiality policy. No command exposes it — none is authorised in M8 |
| Horizon validation | `COMPLETED` | Default 6; ≤ half the history; ≤ 24; over-long requests reduced and stated |
| `anomaly/` engine: contract, baselines, detectors, engine | `COMPLETED` | 3 detectors, trailing-only baselines |
| Anomaly detectors with adequacy predicates | `COMPLETED` | `robust_deviation` 4 · `mean_deviation` 4 · `seasonal_deviation` 13 |
| Contributor attribution | `COMPLETED` | Largest movers in the deviation's direction, with share; passes through the privacy policy |
| Anomaly status vocabulary | `COMPLETED` | `normal` / `unusual` / `material_anomaly` / `insufficient_data`; the top status needs the detector **and** the materiality policy to agree |
| Fraud boundary enforced as data | `COMPLETED` | `FRAUD_LANGUAGE`, `CAUSAL_LANGUAGE`, `INVESTIGATION_NOTE`, asserted against every emitted string |
| `lib/schemas/forecast.schema.json`, `anomaly.schema.json` | `COMPLETED` | |
| `biq-forecasting`, `biq-anomaly-detection` skills | `COMPLETED` | |
| `/revenue-forecast`, `/anomaly-detection` commands | `COMPLETED` | Thin; registry-declared engine dispatch |
| Reuse of M3–M7, no parallel engines | `COMPLETED` | `ForecastSet`/`AnomalySet` subclass `AnalysisSet`; `domain.prepare()` supplies the quality gate and privacy policy |
| Insufficient-history and forecast-failure tests | `COMPLETED` | Every adversarial case in the M8 brief covered |
| M1–M7 regression | `COMPLETED` | **1,079 tests, 0 failures, 0 errors, 17 skipped** (M7 baseline 820) |
| Performance measurement | `COMPLETED` | forecast 0.03s / 0.39s; anomaly 0.32s / 0.88s (2.2k / 30k rows) |
| Token measurement (R-09) | `COMPLETED` | 15 components, 2,097 always-on; extrapolation ~5,172 |
| Dated development record | `COMPLETED` | `docs/development/2026-09-09-forecasting-anomaly.md` |

**Deliberately not done in M8:** external research, company/market/competitor/industry
analysis, SWOT, strategy, decision support (M9); executive reporting (M10); subagents (M11);
MCP connectors (M12); fraud detection (no milestone owns it — anomaly ≠ fraud); a
forecast-vs-actual command; sub-monthly or fiscal-calendar granularity.

**Focused review gate (2026-09-09), M8 still `REVIEW`.** Three areas examined: R-09/ADR-0013,
forecast uncertainty semantics, anomaly detector correctness. No token or component change
was required. Six defects found and fixed — a biased anomaly baseline that flagged 23 of 24
periods of ordinary compounding growth; a fragile detector overruling a robust one so one
spike produced two flags; a seasonal detector anchored on a possibly-anomalous prior year;
attribution dividing currency by order counts to produce 14,140% shares; a score unit
labelled "sigma" implying probabilities the engine never computes; and a backtest error
reported as clean out-of-sample when it is the selection statistic. 55 review tests added;
suite **1,134 tests, 0 failures, 0 errors, 17 skipped**. Demo anomaly flags 26 → 11 with no
threshold changed. See the review section of the M8 development record.

**Approved by the project owner on 2026-09-10**, after the focused review gate of
2026-09-09 (R-09/ADR-0013, forecast uncertainty semantics, anomaly detector correctness).
Final state: **1,134 tests, 0 failures, 0 errors, 17 skipped**; plugin validation passes
with the single known R-08 advisory; always-on cost 2,097 tokens across 15 components.
Approval closes the milestone's implementation and status only — it does **not** close any
risk or debt item, and the M8 limitations recorded in the development record stand
unchanged (monthly-only granularity, seasonality unmodelled by any triggering detector,
trailing-window step-change behaviour, single-dimension attribution, no probability or
statistical-confidence claims, and OpEx/cash-flow forecasting unavailable without the
source fields).

---

## Milestone 9 — External Intelligence & Disclosure Gate · `IN PROGRESS`

> **9-A `COMPLETED`; 9-B `COMPLETED` — approved and closed 2026-09-10; 9-C/9-D not
> started.** M9 is the first milestone in which information may leave the machine. 9-A
> ships the gate and the contracts; 9-B ships the scout boundary, the return contract,
> result normalisation, candidate claims and the `/retrieval-slice` integration harness
> that joins them.
>
> **The path has now been executed.** A subagent is dispatched by the model through the
> runtime's Task mechanism, and a plugin's agents register when the session starts. Two
> defects blocked that and were fixed: the manifest declared `agents` explicitly, which
> stopped the scout shipping at all, and no orchestration surface existed to cause a
> dispatch. 9-B then stood `ON HOLD` pending a session with the plugin loaded — see
> `docs/development/2026-09-10-m9b-scout-transport-investigation.md`, which established
> that the dispatch seam is model-mediated and that no programmatic transport can exist.
> That session arrived on 2026-09-10 and the live run closed the milestone; the procedure
> is in `docs/development/2026-09-10-m9b-vertical-slice.md` and the evidence in
> `docs/development/2026-09-10-m9b-live-verification-closure.md`.
>
> **Architecture reviewed; owner decisions locked 2026-09-10.** The review is recorded in
> `docs/development/2026-09-10-m9-architecture-review.md` and its decisions in
> `docs/development/2026-09-10-m9-owner-decisions.md`. The disclosure gate, external
> research, retrieval and the four external commands are **not yet implemented**; the
> governance step delivered only the security foundations they must stand on.
>
> **Dependencies: M1, M3, M5, M6, M7.** M8 is a pattern precedent only, not a hard
> dependency.

| Task | Status | Notes |
|---|---|---|
| **`biq-research-scout` agent + no-file-access test** | `COMPLETED` | **Moved from M11 by ADR-0014.** Tool grant `WebSearch, WebFetch` only; 17 boundary tests assert the grant, not behaviour |
| k-floor is a hard minimum (k≥5, cannot be lowered) | `COMPLETED` | `resolve_k_floor`; no caller or config path can weaken it |
| Class→tier joined into `assess_disclosure` | `COMPLETED` | One authoritative decision; closes F-2/F-3 |
| Class-3 external claims structurally un-emittable without provenance | `COMPLETED` | `Claim` requires source, citation, date, tier; tier D excluded. Closes F-1 |
| `AggregateDescriptor` fails closed on unresolved sensitivity | `COMPLETED` | Default `unresolved`; `from_fields()` derives via `most_sensitive`. Closes F-4 |
| Cross-query re-identification accumulation | `COMPLETED` | `DisclosureAccumulator`, scoped to the active research operation; never persisted |
| External research **core** (`lib/python/biq/research/`) | `COMPLETED` | **M9-A.** Request, query, gate, retrieval boundary, evidence set, source tiers. No skill, no command, no retrieval |
| `biq-external-research` skill | `PLANNED` | The core it will consume is built; the skill is M9-B |
| **Four-tier disclosure gate** — query construction, destination, approval state, ledger write | `COMPLETED` | **M9-A.** One authoritative decision; 15 security invariants asserted; retrieval constructible only from its output |
| Disclosure decisions written to the evidence ledger | `COMPLETED` | **M9-A.** `gate.ledger_entry()`; refusals recorded with no transmitted text |
| `biq-company-analysis` · `biq-market-analysis` · `biq-competitor-analysis` · `biq-industry-research` | `COMPLETED` | Superseded planning row, reconciled 2026-09-27 (M14-1): each skill is `COMPLETED` in its own row below (M9-C.3, M9-D.2, M9-D.3, M9-D.5) |
| `/company-analysis` · `/market-analysis` · `/competitor-analysis` · `/industry-research` | `COMPLETED` | The four external commands, now named (closes D-06 for M9). Reconciled 2026-09-27 (M14-1): each is `REVIEW` in its own row below, deterministic work complete, **owner-run fresh-session live smoke test outstanding**; M9 stays `IN PROGRESS` **All four live smoke tests PASSED 2026-09-27 (M14-6, checkpointed `57e92fa`): see each command's row.** |
| `evidence_set` + `claim_ledger` schemas | `COMPLETED` | **M9-A.** Retrieved content typed as untrusted; class-3 provenance required by schema |
| Tier tests: 4 comparative questions pass at Tier 0 with no prompt | `PLANNED` | M13 coverage row **S6-01**: deterministic half `covered` by existing M9-A invariants (M13.1, 2026-09-18). The "no prompt" half is behavioural (S3-07), `not_executed`. Covering it does not complete M9 |
| Tier tests: Tier 3 refused; small-denominator blocked; re-identifying combo blocked | `PLANNED` | M13 coverage row **S6-02**, `covered-by-M13`. M13.1 added the gate-level single-query re-identification test (`negative.test_m13_tier_rows`). Covering it does not complete M9 |
| No-source, conflicting-source, stale-source tests | `PLANNED` | M13 coverage row **S6-03**, `covered` by existing M9 tests (M13.1). Covering it does not complete M9 |
| Adversarial tests: prompt injection, tool-use attempts, approval reuse | `COMPLETED` | **M9-A.** 156 tests added; 8 hostile page shapes; suite 1,353 / 0 failures |
| Live retrieval + `biq-research-scout` integration | `COMPLETED` | **M9-B, closed on live evidence 2026-09-10.** Acceptance criterion #1 satisfied by observation, not argument: `businessiq:biq-research-scout` was dispatched **exactly once** through the real runtime, retrieved with `WebSearch`/`WebFetch` (5 of 8 permitted fetches; 3 succeeded, 2 HTTP 403), and its `biq.scout.result/1` result was normalised into an EvidenceSet — 4 records accepted, 0 rejected, every source tier assigned locally. Two blocked pages and a definitional conflict in the retrieved material triggered no second dispatch. Previously `BLOCKED` / on hold pending a session with the plugin loaded. See `docs/development/2026-09-10-m9b-live-verification-closure.md` |
| Scout return contract (`biq.scout.result/1`) | `COMPLETED` | **M9-B.** Documented in `agents/biq-research-scout.md`, parsed by `scout.parse_result()`; a test asserts the documented fields and `ACCEPTED_RECORD_FIELDS` are one vocabulary. Operation and query text must echo the brief |
| `/retrieval-slice` integration harness | `COMPLETED` | **M9-B.** The minimal orchestration surface: gate → brief → one dispatch → normalise → evidence → candidate claims. Not a research capability; `disable-model-invocation` so it never fires on its own (ADR-0015) |
| Candidate claims from retrieved evidence | `COMPLETED` | **M9-B.** Derived, unverified, opt-in. Refused when untraceable, tier D, tier C alone for a material claim, undated, advisory in tone, or where the set records an unresolved conflict. Producing none is a correct outcome |
| Local source-tier classification | `COMPLETED` | **M9-B.** `sources.classify_tier()`; retrieved content cannot declare its own tier; unrecognised source ⇒ C, never A |
| Retrieval bounds and one-shot guarantee | `COMPLETED` | **M9-B.** Results 20, fetched 8, content 20k chars, evidence 20, query 512; exactly one transport call per retrieval |
| Prompt-injection fixtures at the retrieval boundary | `COMPLETED` | **M9-B.** 15 hostile shapes; none alters the decision, query, approval or triggers a second retrieval |
| Optional live smoke test, opt-in and non-blocking | `COMPLETED` | **M9-B.** Skipped unless `BUSINESSIQ_LIVE_SMOKE=1` and a transport is registered; no transport is committed |
| Scout return contract must require a **bare** envelope | `COMPLETED` | **M9-C.1, 2026-09-11.** The live return was prose, then fenced JSON, then more prose. The contract already required a bare object; it then undercut itself by calling surrounding text "discarded", which reads as harmless — the correction of record for the earlier note that the requirement was absent. Rewritten to state the requirement itemised, forbid fences, disclaim its own example fence, name the consequence (the **whole reply** fails closed), and give the scout sanctioned channels for caveats. 38 tests added; parser unchanged and still fail-closed. See `docs/development/2026-09-11-m9c1-scout-return-contract-hardening.md` |
| Advisory-language documentation overstates the guard | `COMPLETED` | **M9-C.2, 2026-09-11.** `commands/retrieval-slice.md` said a claim that "reads as advice" is refused; the implementation is a fixed phrase list (`handoff.ADVISORY_MARKERS`), and "Logistics firms should target…" was accepted. The clause now reads "contains a recognised advisory marker", with two paragraphs naming the guard a heuristic and not a semantic classifier, forbidding it being called comprehensive advice detection, and stating that acceptance is not permission. 12 tests added, one of which couples the documented counter-example to the engine's behaviour so the two cannot drift apart. `ADVISORY_MARKERS` and `handoff.py` untouched. See `docs/development/2026-09-11-m9c2-advisory-guard-wording.md` |
| `biq-company-analysis` skill | `COMPLETED` | **M9-C.3, 2026-09-11.** The first substantive M9-C capability. Consumes the M9-A/M9-B core through `open_retrieval`/`close_retrieval` — no second pipeline and no engine code added. Tier-0 company research across up to three intents, each dispatched once; ten fixed output sections; ambiguity resolved by asking, never guessing; no figure without a citation; no recency claim without a date; interpretation labelled and recommendations refused (class 7 is M10). 59 tests. Model-invocable only — `/company-analysis` is M9-D. See `docs/development/2026-09-11-m9c3-company-analysis-skill.md` |
| `biq-market-analysis` · `biq-competitor-analysis` · `biq-industry-research` skills | `COMPLETED` | **M9-C.** Each should follow the shape M9-C.3 established. Reconciled 2026-09-27 (M14-1): each is `COMPLETED` in its own row below (M9-D.2, M9-D.3, M9-D.5) |
| Structured evidence conflict transport | `COMPLETED` | **M9-C.4, 2026-09-11.** Closes the gap M9-C.3 reported. `close_retrieval(..., conflicts=[...])` carries an **explicitly declared** conflict into the authoritative `EvidenceSet` — the mirror of `proposals=`. Python never infers one: differing text, differing figures and a page shouting "CONFLICT" all produce nothing. A declaration confers no authority — source, tier, date and freshness are read from the evidence item, and a `source_tier` key on a position is refused. Per **ADR-0016** a declared conflict is not downgraded when the figures happen to agree, which is the only way a *definitional* conflict — the M9-B case — is recordable. Unresolved-only; no resolution state invented. 53 tests; omitting `conflicts` leaves every existing caller byte-identical. See `docs/development/2026-09-11-m9c4-conflict-transport.md` |
| Source-tier classifier hardening (label-boundary matching) | `COMPLETED` | **M9-C.6, 2026-09-11.** Remediates the security defect the **M9-C.5** live verification exposed; that verification keeps its historical **`APPROVED WITH LIMITATIONS`** verdict, with the limitation now remediated rather than rewritten. `classify_tier()` matched recognised domains by unanchored substring, so `fake-reuters.com` and `microsoft.com` scored tier B and `sec.gov.evil.example` scored tier A — a source could buy a tier by choosing a hostname. Now matched at a **DNS label boundary**: a configured entry admits itself and its subdomains and nothing else. Hostnames are normalised (scheme, credentials, port, path, query, trailing dot, case). Four bare keyword fragments (`statistics`, `centralbank`, `eurostat`, `edgar`) removed — they had no safe boundary reading and promoted any host containing the word; nothing legitimate lost. Local, deterministic, offline; no DNS/WHOIS added. **One live verdict correctly flips:** the M9-C.5 Microsoft TRENDS set moves `supported` → `unsupported`. 39 tests, no existing test weakened. See `docs/development/2026-09-11-m9c6-tier-classifier-hardening.md` |
| Scout runtime return-contract enforcement | `COMPLETED` | **M9-C.7, 2026-09-11 — Outcome B: no runtime enforcement exists.** Investigated every supported mechanism: subagent frontmatter (17 fields, none constrains output), the Task dispatch (no schema parameter), structured output (does not exist at this seam), and the `SubagentStop` hook — which can observe and block but **cannot rewrite**, so blocking means the subagent continues, i.e. a retry, which also threatens the one-shot retrieval guarantee. Instructional compliance was already tried and **measured**: after M9-C.1 hardened the contract, **4 of 4 live dispatches still returned fenced JSON wrapped in prose**. The parser is therefore the boundary and stays fail-closed — the whole reply is a valid envelope or there is no evidence; it never extracts JSON from prose, because choosing which span of untrusted model output is "the real envelope" is a trust decision made by pattern-matching. No implementation changed. 15 tests pin the four observed live shapes as failures and prevent an **inert** `output-schema:` field being added (the validator silently ignores unknown frontmatter — proved during the investigation). See `docs/development/2026-09-11-m9c7-scout-return-contract-enforcement.md` |
| Research handoff operationalization | `COMPLETED` | **M9-C.8, 2026-09-11 — Outcome B: no safe supported handoff exists.** Investigated parent-mediated extraction, tool-mediated return with runtime schema validation, scout-written files, MCP return channels, `TaskOutput`, and subagent-scoped hooks. **Parent-mediated extraction is rejected on principle, not formatting:** it moves authorship of the envelope from the one context that *cannot* read business data to the one that can, so the evidence ledger would attribute to an external source text written by a context that has seen internal data — the disclosure boundary would remain on paper and stop meaning anything. Scout-written files were rejected for the same reason in reverse (they need the file access whose absence *is* the control). No implementation; parser untouched. The one viable future mechanism — a `SubagentStop` hook copying the reply verbatim to a file — fixes **authorship, not formatting**, so it does not unblock live research either; recorded, not proposed. 11 tests pin the invariant any future handoff must preserve: whatever produces the records, the provenance is gate-issued. See `docs/development/2026-09-11-m9c8-research-handoff-operationalization.md` |
| Scout output shape experiment | `COMPLETED` | **M9-C.9, 2026-09-11 — Outcome B: failed experiment**, for a reason the methodology did not anticipate. Tested a candidate shape — operation-bound line records (`BIQ-REC/1 <operation> {…}` + a declared count) — chosen because prose becomes structurally harmless while the gate-issued operation id makes lines unforgeable by a page author, and because the adapter validates nothing itself: it builds the canonical envelope and hands it to **production** `close_retrieval()`. Deterministically sound — **22 tests**, full matrix, including that surrounding prose is accepted, a verbatim-smuggled line fails the whole reply on the count check, and a model-supplied tier is still recomputed. **But both live scouts refused the format**, correctly treating a prompt-embedded contract change as instruction-via-content: *"no content outside those six fields is authoritative here."* That is the M9-C.1 hardening working as a defence — and it means **an output shape cannot be tested live without first shipping it to the agent definition**, which an unproven format may not do. Live baseline extends to **6/6 replies violating the bare-envelope contract**; envelope *content* was correct in all six, only the wrapper wrong. No production change. See `docs/development/2026-09-11-m9c9-scout-output-shape-experiment.md` |
| Controlled scout handoff trial | `COMPLETED` | **M9-C.10, 2026-09-11 — Outcome B: candidate rejected, agent definition reverted.** Authorised to put the `BIQ-REC/1` protocol in the trusted agent definition — the one thing M9-C.9 could not do. Change was purely additive (43 lines) and left all 649 M9 tests passing. **Eight distinct Tier-0 dispatches, one each, no retries: observed compliance 0/8**, every reply using the old envelope wrapped in prose. **But the candidate was not refuted — it was never administered.** All eight replies were *silent* about the protocol, whereas in M9-C.9 the scout refused a format it was shown explicitly and at length, twice. The explanation consistent with all observations: **agent definitions are bound when the session registers them, not read per dispatch** — a property M9-B recorded and this experiment's design failed to carry forward. Live wrapped-reply baseline now **14/14**. Deterministic security evidence for the candidate remains strong (hostile content cannot manufacture an accepted record; a smuggled line fails the whole reply on the count check). Agent definition reverted, verified zero-diff. A valid trial needs the edit plus a **fresh session**, with a one-dispatch registration check before spending the rest. See `docs/development/2026-09-11-m9c10-controlled-scout-handoff-trial.md` |
| Fresh-session agent registration verification | `COMPLETED` | **M9-C.11, 2026-09-11 — INCONCLUSIVE by stop condition.** Tested the C.10 hypothesis that agent definitions bind at session registration. Added a minimal probe to the trusted definition (14 lines, delimited, contract/tools/gate/provenance untouched; 171 tests passed against it) instructing the scout to emit `BIQ-C11-REGISTERED` for `m9c11-` operations. **A genuinely fresh session cannot be created from inside a running one** — the assistant *is* the session; a subagent inherits the same registry; `claude -p`/subprocess is prohibited; the one peer session is offline; no plugin-reload command exists. §3's stop clause was honoured rather than passing off an invalid test. One **control** dispatch in the current session (worth its cost: a visible marker would have falsified the hypothesis outright and settled the candidate on its merits) returned the marker **absent** — consistent with session binding, but proving nothing, since an ignored instruction looks identical. Nine dispatches now show no response to an edited definition. Agent definition **restored**, verified by zero-diff, SHA-256 match and zero marker occurrences; the marked copy is staged outside the repo so the decisive test is one file copy plus an operator-initiated restart. **M9-C.12 should not run until that check returns a marker.** See `docs/development/2026-09-11-m9c11-fresh-session-agent-registration.md` |
| Plugin installation and agent source resolution audit | `COMPLETED` | **M9-C.12, 2026-09-12 — Outcome A: the working tree is authoritative.** Resolved the cache/source discrepancy M9-C.11 surfaced, by non-invasive inspection with **no scout dispatch**. Exactly two plugin copies exist: the working tree (= the `directory` marketplace source, read in place) and an install-time cache snapshot (`…/plugins/cache/businessiq/businessiq/0.1.0`, written once at 2026-09-10 22:46:38, never refreshed). **Proven by positive existence test** that components load from the working tree: `skills/biq-company-analysis/` exists only there (created 2026-09-11 12:44, ~14 h after the snapshot), the cache has no such directory, and this session (started 2026-09-12 18:00:15) carries that skill with a description matching the working-tree `SKILL.md` verbatim — the cache cannot supply what it does not contain. `claude plugin details` independently enumerates the working-tree inventory. **The cache is vestigial for a directory-source plugin**, so a development edit needs no update/reinstall/refresh — only a session restart. Scout definitions differ by 30 lines, confined to the output contract (cache carries the pre-M9-C.1 wording); **frontmatter, description and tool grant `WebSearch, WebFetch` are byte-identical** — no permission divergence. Also established that **M9-C.11's marker was an invalid instrument** — it required text before the JSON object, which the same file forbids as fail-closed — so its marker absence is not registration evidence, and its subagent transcript grep was vacuous (0-byte file). With source divergence eliminated, **session-start registration timing is the only surviving explanation for C.10's 0/8** (strongly supported, not proven: no registry snapshot timestamp is exposed; `claude plugin update` is documented "restart required to apply"). Scout-specific resolution is high-confidence **inferred**, not proven — no per-agent path is exposed. No agent, cache, permission or architecture change; no ADR. 1812 tests pass. See `docs/development/2026-09-12-m9c12-plugin-agent-source-resolution-audit.md` |
| Fresh-session candidate handoff trial | `COMPLETED` | **M9-C.13, 2026-09-12 authorised / 2026-09-13 executed — Outcome A: candidate `BIQ-REC/1` / `BIQ-END/1` handoff live-validated, 8/8 controlled trials, 29 records, 100% observed compliance; no retries/manual repair; adversarial structured-content trial passed. Candidate is validated but not yet adopted into production. Zero-record behavior and full gate-issued `close_retrieval()` integration remain open verification items.** The experiment C.9–C.12 could not run: the protocol shipped in the trusted definition **plus a genuinely fresh session**. Trial 1 was dispatched and reported **alone** as a registration check — it returned the candidate protocol, establishing that the session had loaded the modified definition, the fact C.10's 0/8 could not distinguish from a bad candidate. Trials 2–8 then covered company profile, recent developments, market sizing, industry benchmark, competitor positioning, financial metrics and an **adversarial** structured-content question. Across all eight: exact operation echo on every line, one terminator each with a correct count, single-line JSON valid throughout, **zero** reversions to `biq.scout.result/1`, zero undocumented fields, zero `source_tier` fields, **no fabricated publication date** (8 absences all declared, "Last Updated" banners declined unprompted), zero manual repairs, zero retries. Candidate adapter accepted all eight (`problem: None`); **production** `parse_result()`/`normalise_records()` accepted all 29 records, 0 rejected, all marked `UNTRUSTED_EXTERNAL_DATA`. **Security:** within the tested matrix, external structured-looking content did not manufacture an accepted protocol record — the adversarial trial excluded an auto-generated JSON-Schema/OpenAPI page as tier D, named it in prose, and declined to fabricate a schema that is not published; zero protocol-token lines bearing a foreign operation id appeared anywhere. Availability caveat preserved: an induced extra valid-looking line causes a **count mismatch and fails the whole retrieval** rather than forging evidence. No claim about untested attack classes. **Empirical, not guaranteed** — "observed 8/8 live compliance across the controlled trial". Open observations, none fixed here: zero-record live behaviour unvalidated (`BIQ-END/1 … 0` maps to `NO_RECORDS` fail-closed rather than distinguishing `no_reliable_source_found` from `retrieval_failed`); full gate-issued `close_retrieval()` **not** executed end-to-end (shim brief, since a real `ScoutBrief` mints its own operation id) so protocol transport and production parse/normalise are validated but not the complete path; **22 `&amp;` entity occurrences** in `title`/`content` values, origin undetermined because all subagent transcripts were 0 bytes; and **28 of 29 records classified tier C inferred** (only `sec.gov` reached A), so most retrieved sources cannot solely support a material claim. Prose before/after records proved harmless and is **content only** — observed terms such as "confirm" are **not** protocol failures and advisory heuristics were deliberately not expanded. Agent definition **restored** and verified: SHA-256 `04f0b30da8efcf4f4cf2644ee351dfd42d7d7f641c21ee2fc37d6d48b440d244`, 9,845 bytes, zero protocol tokens, zero trial wording, frontmatter and tool grant `WebSearch, WebFetch` unchanged. No production parser/adapter/handoff/gate/tiering/provenance change; no architecture change (adoption milestone owns that); no ADR. 22-test candidate matrix passes; 1812 tests pass; `claude plugin validate . --strict` passes. See `docs/development/2026-09-12-m9c13-fresh-session-biq-rec-trial.md` |
| Zero-record representation and full `close_retrieval()` integration | `COMPLETED` | **M9-C.14, 2026-09-13 — Outcome A: both M9-C.13 open items closed; candidate still not adopted.** **Zero records:** `BIQ-END/1 <operation> 0` is reachable only when a terminator is present *and* its count agrees with an empty record set (a missing terminator and a disagreeing count are refused earlier), so it has exactly one meaning — **searched, found nothing citable**. The **production contract was already sufficient**: `no_reliable_source_found` has existed since M9-B and `close_retrieval()` already renders it as `insufficient_evidence`/`no_adequate_source` with `evidence: None`. The gap was that the *line protocol had no way to say it* — the adapter spent the case on a `NO_RECORDS` refusal that **no test anywhere asserted**. Minimum fix, **experimental code only**: the adapter now emits a canonical envelope with `no_reliable_source_found` for a protocol-valid empty result. No new status, reason or envelope field; no production module touched. Fail-closed unchanged — failing closed is about evidence, and none is created either way; every structural defect still refuses (C.9's 22-test matrix unchanged and passing). **All four outcomes are distinguishable:** no-records and all-unusable share `insufficient_evidence`/`no_adequate_source` by design and are told apart by `rejected`; retrieval failure is `unavailable`/`source_unavailable`; malformed is `unavailable`/`retrieval_unavailable` (or `invalid_provenance` on an echo mismatch). **Full path:** principal finding — the operation id is **caller-supplied and gate-bound, not gate-minted**, and both halves re-derive from identical request parameters by design, so **C.13's shim was never necessary**. All 54 new tests run the real chain `ResearchRequest → gate.assess → RetrievalRequest → ScoutBrief → BIQ-REC/1 reply → to_envelope → close_retrieval → EvidenceSet`, with `is_gate_issued` asserted, the gate (not the caller) constructing the query text, and **operation binding proved at five stages**. Six required cases all covered: valid records (tier A assigned locally, prose harmless), zero records (no EvidenceSet, no claim even when proposed, no assertion of falsity, identity preserved), wrong operation (foreign lines yield nothing; a mixed reply fails the count check; envelope-level operation or query substitution → `invalid_provenance`), count mismatch (**no partial evidence**, two terminators refused), malformed protocol (six shapes plus hostile inputs — all refuse, none raise), and the trust boundary (a blog claiming tier A → recomputed **C** inferred, `may_stand_alone` false, forged `trust`/`operation`/`verified`/`tier_inferred` dropped **and named in a note**, absent date left absent, material claim refused "never the sole support"). **Live test not required** and not run — the only leg it could add is the scout's own line authoring, already 8/8 in C.13; a zero-record live case was not manufactured. No gate, tier-policy, k=5, advisory-heuristic, parser or scout-definition change; scout still pristine at `04f0b30d…`; `architecture.md` untouched; no ADR. **1866 tests pass** (1812 + 54), 0 failures, 0 errors, 19 skipped; `claude plugin validate . --strict` passes. See `docs/development/2026-09-13-m9c14-zero-record-close-retrieval.md` |
| Formal `BIQ-REC/1` / `BIQ-END/1` production adoption | `COMPLETED` | **M9-C.15, 2026-09-13 — Outcome A: adopted.** The line protocol is now the **single production-reachable scout return contract** (ADR-0017), formally superseding the bare-envelope contract M9-C.1 hardened — which is recorded as superseded, not erased. **Implementation:** `scout.parse_reply()` in `lib/python/biq/research/` is the production entry point; it checks that every line carries this retrieval's **gate-bound operation** and that the declared count equals the record-line count, then assembles the canonical envelope and delegates the echo/status/record checks to the existing `parse_result()`. `close_retrieval()` routes **text → `parse_reply`** (the scout contract) and **dict → `parse_result`** (the internal fixture/transport seam). The old envelope is therefore **no longer scout-reachable**: JSON text, fenced or bare, finds no terminator and fails closed — verified by test. **Clean break chosen over dual protocols**, on the owner's explicit decision, so no compatibility layer exists and no dead production path remains; the experimental `tests/experimental/line_format.py` was retired and its package removed. **Trust boundary unchanged and re-asserted:** Python still owns operation, query binding, disclosure authorisation, source tier, provenance, freshness, evidence acceptance, conflict state and candidate/verified claim state; a record asserting `source_tier`/`trust`/`verified`/`freshness`/`may_stand_alone`/`operation` has those keys dropped **and the attempt noted**; a blog claiming tier A still classifies **C inferred** and is refused as sole support for a material claim; no verified-claim path exists. **Zero records** (`BIQ-END/1 <operation> 0`) → `insufficient_evidence`/`no_adequate_source`, no EvidenceSet, no claim even when proposed, and explicitly **absence of evidence, not evidence of absence**; a malformed reply stays the distinct `unavailable`/`retrieval_unavailable` outcome. **Coverage preserved, not reduced:** new production matrix **61 tests**; C.9 matrix **22** and C.14 matrix **54** retargeted at the shipped parser with counts intact; the affected M9-C.1 (11), M9-B (3) and M9-C.7 (3) assertions were **retargeted to the new contract's equivalent security properties, never deleted** — `test_m9c1_bare_envelope_contract.py` keeps its name and grew 38 → 42, and the 10 `TestSurroundingTextIsRefused` tests were re-documented in place and gained two new bindings tests. **No live dispatch run** — this session's registry holds the pre-adoption definition (agent definitions bind at session start, M9-C.10/C.12), so a dispatch now would measure the wrong definition; the adopted text is substantively the text C.13 validated **8/8**. **1933 tests pass**, 0 failures, 0 errors, 19 skipped; `claude plugin validate . --strict` passes. Scout definition now `a9a89d11…` (was `04f0b30d…`). See `docs/decisions/ADR-0017-operation-bound-line-records.md` and `docs/development/2026-09-13-m9c15-biq-rec-production-adoption.md` |
| Live production smoke test and Company Analysis end-to-end demonstration | `COMPLETED` | **M9-C.16, 2026-09-13 — Outcome A: live production research handoff verified and Company Analysis integration demonstrated.** Closes the one gap M9-C.15 left open. **Fresh session proved, not assumed:** session `321ca2e6…` opened by a `SessionStart:startup` hook (a cold start, not `resume`/`compact`) at `2026-09-13T07:59:23Z`, 3 min 43 s after the C.15 adoption session `ecfd1e66…` ended; `agents/biq-research-scout.md` was last written `2026-09-13T06:55:43Z`, **63 minutes before** registration, and was untouched thereafter (`a9a89d11…`, 12,092 bytes, verified at open and close). Working-tree resolution reconfirmed by C.12's positive-existence test: this session registered `businessiq:biq-company-analysis`, which exists only in the working tree — the 2026-09-10 install cache has no such skill and **zero** `BIQ-REC/1` tokens. **Smoke test:** one Tier-0 dispatch, `logistics 2026 revenue growth trends`, operation `m9c16-smoke-1`, no retry. Scout returned the adopted protocol — 3 `BIQ-REC/1` lines, one `BIQ-END/1 … 3`, exact operation echo, bare single-line JSON, **zero** `source_tier`/`trust`/`verified`/`operation`/`freshness`/`may_stand_alone` keys, **no fabricated date** (the undated source declined to invent a day from "July 2026"), no old envelope, no second protocol. Prose before and after the records, harmless as designed. **No manual intervention of any kind:** nothing extracted from prose, no fence removed, no JSON repaired, no count or operation altered — the whole 4,139-byte reply (SHA-256 `49470c8f…`) went to `parse_reply()` as one string. **Production path:** brief re-derived through `handoff._decide()` from identical arguments and byte-identical to the dispatched one (no shim); `parse_reply` `failure: None`, 3 records; `normalise_records` 3 accepted 0 rejected; `close_retrieval` `status: ok`; EvidenceSet 3 items, all **tier C recomputed locally**, undated left undated, all `UNTRUSTED_EXTERNAL_DATA`. **Negative control:** the same raw reply read against another retrieval's brief yields zero records and `unavailable`/`retrieval_unavailable`. **Company Analysis:** the `/company-analysis` *command* does not exist (M9-D, unbuilt), so the existing contract — the `biq-company-analysis` skill — was exercised, unmodified: Microsoft, `focus: overview`, one `PROFILE` retrieval, one dispatch, 2 records accepted, EvidenceSet built, both sources **tier C inferred including `news.microsoft.com`**, support `unsupported`, confidence `LOW`. **Claim policy proved both directions on the real path:** a material claim on the tier-C press release was **refused** (`no_adequate_source`, "never the sole support"), a non-material claim came back `status: candidate` / `verified: false`, and `"verified": true` appears nowhere. **Privacy:** no business file read, no `.businessiq/` context exists, both queries built by the gate from public terms only, tier 0 both times, no Tier 1/2/3 disclosure. **No production code, test or assertion changed.** 1933 tests pass, 0 failures, 0 errors, 19 skipped; all 18 M9 modules at their C.15 counts; `claude plugin validate . --strict` passes. **One inconsistency raised, deliberately not fixed:** `open_retrieval()` still returns `envelope_expected: biq.scout.result/1` (`handoff.py:119`) — unconsumed, never reaches a scout, cannot affect parsing, but it advertises a superseded contract and wants a deliberate correction. See `docs/development/2026-09-13-m9c16-live-production-smoke-company-analysis.md` |
| First-party source registry and superseded-contract cleanup | `COMPLETED` | **M9-C.17, 2026-09-13.** Two tightly scoped corrections, both raised by M9-C.16, no new capability and **no live retrieval**. **Part A:** `open_retrieval()` no longer returns `envelope_expected: biq.scout.result/1`. A consumer search across `lib/`, `tests/`, `commands/`, `skills/`, `agents/`, `reference/`, `config/`, `evals/` and `lib/schemas/` found exactly one emitter and **zero** readers, so it was **removed rather than re-pointed** — advertising the new protocol would add a surface nobody asked for, and the contract lives in the agent definition and ADR-0017. `SCOUT_RESULT_ENVELOPE` is **kept** as the internal canonical envelope `parse_reply()` builds and `parse_result()` validates. The agent definition still names the retired format exactly once, as the thing not to send. **Part B — ADR-0018:** `sources.FIRST_PARTY_COMPANY_DOMAINS` recognises a company's **own** domain at **tier B**, consulted after the A and B tables and before the unrecognised fallback, matched by the existing `_matches_domain()` label-boundary rule — **no new URL parsing was written**. `news.microsoft.com` (the exact host M9-C.16 saw misclassified) is now B with an explainable basis naming the registered domain and company; `fake-microsoft.com`, `notmicrosoft.com`, `microsoft.com.evil.example`, `microsoft.example.com` and `evilnews.microsoft.com.example` stay **C inferred**. **Tier B and never A**, because tier A means *independent of the subject* and a company is the best-informed and most interested source about itself at once — **tier A was not broadened**. **Registry only, no heuristic:** five alternatives (any-`.com`, subject-name matching, trusting `source_type`, WHOIS/DNS, a bought domain database) were considered and rejected, each because it hands the tier back to whoever picks a hostname — the M9-C.6 defect rebuilt. One entry (`microsoft.com`); a policy mechanism, not a catalogue. Tier is still recomputed locally, `source_tier` is still not an accepted record field, tier D still wins first, and retrieved content asking to be registered changes nothing. **Owner review item:** the M9-C.5 Microsoft TRENDS set reads `supported` again — by explicit registry recognition, not by the defect, but the same observable outcome. Right for a claim *about Microsoft*; weaker than it looks for a claim about *the AI market* sourced from Microsoft's blog. The tables classify a source, not a source-claim pair, so **a claim-kind-aware refinement is an open question deliberately not decided here**. **Tests:** new `negative.test_m9c17_first_party_registry` **45**; `negative.test_m9c6_tier_boundary` **39 → 42**, four assertions **retargeted, none deleted and no spoofing assertion touched** (the milestone's own requirement that `news.microsoft.com` be tier B targets one of those hosts, so the supersession is intended). **1981 tests pass**, 0 failures, 0 errors, 19 skipped; `claude plugin validate . --strict` passes. No change to `BIQ-REC/1`/`BIQ-END/1`, the scout definition, the gate, disclosure tiers, k=5, freshness, conflicts or claim verification. See `docs/decisions/ADR-0018-first-party-company-source-registry.md` and `docs/development/2026-09-13-m9c17-first-party-registry-and-protocol-cleanup.md` |
| **Live external research is not operationally usable end-to-end** | `COMPLETED` | **Closed by M9-C.16, 2026-09-13.** One live Tier-0 dispatch in a session that provably registered the adopted definition ingested through the production parser with no manual extraction and no repair, and Company Analysis consumed the handoff end to end. The feature is now demonstrated, not merely adopted, and commands built on it may be described as live-operational. Two caveats travel with it: live compliance on the adopted definition is **2/2** here on top of C.13's 8/8 — empirical, not guaranteed — and **every** source retrieved across both live runs classified tier C inferred, including Microsoft's own press release, so research output currently caps at `support: unsupported` until the recognised-host registry question (R-11) is decided. Historical record of the blocked period, unchanged: **Raised by M9-C.7, confirmed by M9-C.8, unblocked in principle by M9-C.15 — not yet demonstrated live.** M9-C.15 adopted the protocol that 8/8 live trials complied with, so the mechanism that failed 14/14 is gone by construction and the Python path is verified end-to-end on a gate-issued brief. What remains before this can be called operational is **one live dispatch in a session that registered the adopted definition**, proving the production parser ingests a real scout reply with no manual extraction or repair. Until that runs, the feature is adopted but **not demonstrated**, and no command may be described as live-operational. Historical record of the blocked period, unchanged: **Raised by M9-C.7, confirmed and unchanged by M9-C.8; still BLOCKED after M9-C.13.** M9-C.13 live-validated a *candidate* reply shape (8/8, 29 records) but **adopted nothing** — the shipped production contract is still the bare envelope, against which all 14 pre-C.13 live replies and all 8 C.13 replies remain non-conforming, and two verification items (zero-record behaviour, full gate-issued `close_retrieval()`) are open. The feature becomes usable only after an adoption milestone, not before. Every live scout reply so far violates the return contract, so every live retrieval fails closed and no Company Analysis run completes without manual envelope extraction — which is forbidden, and which M9-C.8 established is unsafe rather than merely disallowed. Every component is correct: contracts, gate, tiering, evidence, conflicts, claims and real web retrieval all work. **The feature must not be described as operational.** Three untaken options, all owner decisions: accept a fenced envelope (insufficient alone — all four observed replies had prose *after* the fence); change the *shape* of what the scout is asked to produce rather than the strength of the wording (the instructional half was tried and failed 4/4); or surface the failure to the user as a visible "research unavailable" outcome (purely presentational, risks nothing) |
| `/company-analysis` command | `COMPLETED` | **M9-D.1, 2026-09-13 — deterministic work complete; live smoke test outstanding.** `/company-analysis` ships as a **thin orchestrator** over `biq-company-analysis`: it validates input, resolves Business Context for **public** disambiguating terms only, routes ambiguity through the skill's existing protocol, invokes the skill, and presents the result. It performs no retrieval, builds no evidence, tiers no source, proposes or verifies no claim, and defines no output section — asserted by test (`open_retrieval(`, `close_retrieval(`, `WebSearch`, `WebFetch`, `Task(` and the tiering constants are all absent from the command). **No registry spec, deliberately:** `biq.commands.registry` drives a dataset pipeline (mapping roles, analytical domain, KPI focus, engine) and a public-source research command has no dataset, so a spec would invent every field; the markdown orchestrator is the whole command, auto-discovered from `commands/*.md`. **No production Python changed and the skill was not modified** — no compatibility fix proved necessary. **Two existing tests retargeted, none deleted, no security assertion touched:** `test_no_analytics_command_is_undeclared` now permits two named sets (harness + research) and still fails on any other undeclared surface, and `test_it_is_not_one_of_the_four_deferred_research_commands` became `test_it_is_not_one_of_the_research_commands`, checking the harness's own identity plus the three commands still deferred — both supersessions are required by this milestone building one of the four. A new test asserts the other three do **not** exist. **50 focused tests**; `unit.test_command_registry` 35→37; **2033 tests pass**, 0 failures, 0 errors, 19 skipped; `claude plugin validate . --strict` passes; all 20 M9 modules pass. **Outstanding:** the fresh-session live `/company-analysis` smoke test required by the milestone cannot be run from the session that created the command — it needs a genuinely fresh Claude Code session, which is an owner action. Until it runs, the command is **not** demonstrated live. See `docs/development/2026-09-13-m9d1-company-analysis-command.md` **Live smoke run 2026-09-27 (M14-5), `/company-analysis Microsoft --focus overview`: criteria 1–4, 6 and 7 met.** It was discovered, invoked its skill, made one dispatch ("Microsoft company profile"), recomputed tiers locally (B and C), marked 0 claims verified, gave confidence LOW, read no file and sent no internal term. **Criterion 5 not met:** the session wrote the scout reply trimmed to its three protocol lines, although the raw hand-back parses to the identical records. Stays `REVIEW`. See `docs/development/2026-09-27-m14-5-final-product-corrections.md` **Live smoke PASSED 2026-09-27 (M14-6, checkpointed `57e92fa`): `/company-analysis Microsoft --focus overview` in a fresh `claude -p --plugin-dir` session.** Every documented criterion was met: the command was discovered and routed through its skill; exactly one gate-authorised dispatch with public terms only; the reply closed from the harness capture (ADR-0053), with the scout reply recorded by the harness byte-identical to the text the parser read (5,370 characters); tiers recomputed locally; 0 claims verified; confidence MEDIUM; ten sections; no file read; no internal term sent; the verifier connected. See `docs/development/2026-09-27-m14-6-m9-smoke-protocol-remediation.md` |
| `biq-market-analysis` skill | `COMPLETED` | **M9-D.2, 2026-09-13.** Tier-0 market research over the M9-A/M9-B core — no second pipeline. Five focus values (`overview`, `size-growth`, `trends`, `drivers-risks`, `full`), each one **distinct research question** with its own gate-authorised retrieval, operation and single dispatch; `full` is four retrievals, never one broad query. Ten fixed output sections. Its defining rule is the **market-size compatibility test**: definition, geography, unit/currency, period and methodology must *all* match before two figures may be compared, and an unstated one fails the check rather than passing it. Mismatched or conflicting estimates are reported separately with their own definitions and recorded through the existing declared-conflict transport (ADR-0016) — never averaged, no midpoint, no currency conversion. Source-published CAGRs stay that source's estimate with its stated period, never restated as a BusinessIQ forecast. A market participant's own page is tier B (ADR-0018) and is explicitly *not* independent evidence of the size of a market it sells into. Section 7 is market structure only — no competitor profiles, no vendor rankings. No recommendations (class 7 is M10). **120 focused tests.** See `docs/development/2026-09-13-m9d2-market-analysis.md` |
| `/market-analysis` command | `COMPLETED` | **M9-D.2, 2026-09-13 — deterministic work complete; live smoke test outstanding.** A **thin orchestrator** over `biq-market-analysis`, the same shape as `/company-analysis`: validates input, resolves Business Context for **public** terms only, routes ambiguity through the skill's protocol, invokes the skill, presents the result. It performs no retrieval, builds no evidence, tiers no source, compares no two size figures, computes no growth rate, proposes or verifies no claim, and defines no output section — asserted by test (`open_retrieval(`, `close_retrieval(`, `WebSearch`, `WebFetch`, `Task(`, `EvidenceSet`, `BIQ-REC/1` and the tiering constants are all absent from the command). No registry spec, for the same reason as M9-D.1. **70 focused tests.** **One shared-core change, additive and documented: ADR-0019** adds the `OVERVIEW` and `DRIVERS` research intents, because the nearest existing intent renders as the literal words "company profile" and would have sent every market-overview query looking for company pages. The five original intents keep their names, wording and behaviour; a test pins the company query string byte-for-byte. **Two existing tests retargeted, none deleted, no security assertion touched:** `test_command_registry` moved `market-analysis` from `UNBUILT_RESEARCH_COMMANDS` to `RESEARCH_COMMANDS`, and `test_m9b_scout_contract`'s deferred tuple dropped it — both are statements about what has been built, not policy. **2223 tests pass**, 0 failures, 0 errors, 19 skipped (baseline 2033); all 24 M9 modules pass; `claude plugin validate . --strict` passes. **Outstanding:** the fresh-session live `/market-analysis` smoke test required by the milestone cannot be run from the session that created the command — it needs a genuinely fresh Claude Code session, which is an owner action. Until it runs, the command is **not** demonstrated live. See `docs/development/2026-09-13-m9d2-market-analysis.md` **Live smoke run 2026-09-27 (M14-5), `/market-analysis cold chain logistics --focus overview`: criteria 1–4, 6 and 7 met.** Ten sections, one dispatch, 5 records, confidence LOW, 0 verified. **Criterion 5 not met:** trimmed reply, identical records. The write guard correctly blocked one unconfined introspection call. Stays `REVIEW`. See `docs/development/2026-09-27-m14-5-final-product-corrections.md` **Live smoke PASSED 2026-09-27 (M14-6, checkpointed `57e92fa`): `/market-analysis cold chain logistics --focus overview` in a fresh `claude -p --plugin-dir` session.** Every documented criterion was met: the command was discovered and routed through its skill; exactly one gate-authorised dispatch with public terms only; the reply closed from the harness capture (ADR-0053), with the scout reply recorded by the harness byte-identical to the text the parser read (2,721 characters); tiers recomputed locally; 0 claims verified; confidence LOW; ten sections; no file read; no internal term sent; the verifier connected. See `docs/development/2026-09-27-m14-6-m9-smoke-protocol-remediation.md` |
| `biq-competitor-analysis` skill | `COMPLETED` | **M9-D.3, 2026-09-14.** Tier-0 competitive-landscape research over the M9-A/M9-B core — no second pipeline and no engine code beyond two additive intents. Five focus values (`landscape`, `comparison`, `positioning`, `developments`, `full`), each one **distinct research question** with its own gate-authorised retrieval, operation and single dispatch; `full` is four, and `landscape` runs first when no competitors were supplied because the comparison question needs names it must not invent. Ten fixed output sections. Its defining rule is **evidence-based competitor identity**: a company is `identified` only where a source states the competitive relationship, `observed` where the statement is single, tier C or undated, and **nothing at all** where the company was merely mentioned, appeared in a search result or sells in an overlapping category. A user-supplied name is preserved verbatim, never substituted, and stays labelled where evidence does not support its relevance — neither granted relevance nor dropped for lack of it. The shortlist is bounded at roughly three to five and is never padded to reach a length. Its second rule is **comparison without ranking**: ten observable dimensions and no scoring system at all — no 1–10 ratings, no weighted totals, no composite competitive score — because the repository holds no metric contract for competitive strength and this milestone does not add one. Missing cells stay missing and never become zero; incomparable figures are marked not comparable; market share is calculated only where a supported denominator exists on a compatible definition, geography, period and basis. A company's self-claimed leadership is attributed to that company, never restated as independent fact. A ranking is declined **even when asked directly**, because a ranking is a decision dressed as an observation and would make this decision support without a class 7 recommendation's structure. No recommendations (class 7 is M10). **167 focused tests.** See `docs/development/2026-09-14-m9d3-competitor-analysis.md` |
| `/competitor-analysis` command | `COMPLETED` | **M9-D.3, 2026-09-14 — deterministic work complete; live smoke test outstanding.** A **thin orchestrator** over `biq-competitor-analysis`, the same shape as `/company-analysis` and `/market-analysis`: validates input, resolves Business Context for **public** terms only, routes entity ambiguity through the skill's protocol, invokes the skill, presents the result. It performs no retrieval, builds no evidence, tiers no source, decides no competitor identity, compares no two figures, computes no market share, ranks nothing, proposes or verifies no claim, and defines no output section — asserted by test (`open_retrieval(`, `close_retrieval(`, `WebSearch`, `WebFetch`, `Task(`, `EvidenceSet`, `evidence_id`, `BIQ-REC/1`, `BIQ-END/1`, `FIRST_PARTY_COMPANY_DOMAINS`, the tiering constants, `verified: true`, ranking phrasing and market-share arithmetic are all absent from the command). No registry spec, for the same reason as M9-D.1 and M9-D.2. **85 focused tests.** **One shared-core change, additive and documented: ADR-0020** adds the `LANDSCAPE` and `COMPARISON` research intents — the two competitor questions no existing intent's query wording expressed — and deliberately **reuses** `POSITIONING` and `TRENDS` for the two it already did, so the enumeration grows by need rather than by skill. The seven earlier intents keep their names, wording and behaviour; tests pin both the company and market query strings byte-for-byte. **Three existing tests retargeted, none deleted, no security assertion touched:** `test_command_registry` moved `competitor-analysis` from `UNBUILT_RESEARCH_COMMANDS` to `RESEARCH_COMMANDS`, `test_m9b_scout_contract`'s deferred tuple dropped it, and `test_m9d2_market_analysis_command`'s absence assertion narrowed to `/industry-research` — all three are statements about what has been built, not policy, and each still fails on anything else appearing. **2475 tests pass**, 0 failures, 0 errors, 19 skipped (baseline 2223); all M9 modules pass; `claude plugin validate . --strict` passes. **Outstanding:** the fresh-session live `/competitor-analysis` smoke test required by the milestone cannot be run from the session that created the command — it needs a genuinely fresh Claude Code session, which is an owner action. Until it runs, the command is **not** demonstrated live. See `docs/development/2026-09-14-m9d3-competitor-analysis.md` **Live smoke run 2026-09-27 (M14-5), `/competitor-analysis Microsoft --focus landscape`: FAIL (incomplete).** One dispatch ("Microsoft competitive landscape") returned 4 records, and no file was read. The session then ran the closing step from a script file instead of the documented inline form. The write guard required approval, which a non-interactive session cannot give, and the session correctly stopped without working around it, so no report was produced. The reply file was again trimmed. Stays `REVIEW`. See `docs/development/2026-09-27-m14-5-final-product-corrections.md` **Live smoke PASSED 2026-09-27 (M14-6, checkpointed `57e92fa`): `/competitor-analysis Microsoft --focus landscape` in a fresh `claude -p --plugin-dir` session.** Every documented criterion was met: the command was discovered and routed through its skill; exactly one gate-authorised dispatch with public terms only; the reply closed from the harness capture (ADR-0053), with the scout reply recorded by the harness byte-identical to the text the parser read (4,803 characters); tiers recomputed locally; 0 claims verified; confidence LOW (support unsupported; nothing ranked); ten sections; no file read; no internal term sent; the verifier connected. See `docs/development/2026-09-27-m14-6-m9-smoke-protocol-remediation.md` |
| Research-intent registry consolidation | `COMPLETED` | **M9-D.4, 2026-09-14 — ADR-0021. The intent-architecture question ADR-0019 deferred and ADR-0020 deferred again is now resolved.** Research-intent metadata moves from three flat structures in two modules — `INTENTS` in `contract.py`, `INTENT_TERMS` and `SUBJECT_LEADS` in `query.py` — plus a category relationship that lived only in three `SKILL.md` files, into **one immutable registry**, `lib/python/biq/research/intents.py`. One `ResearchIntent` record per intent carries its identifier, purpose, query term, subject-lead flag, the categories that ask it and the production callers that issue it. **The three familiar names survive as derived views, not tables beside it** — `contract.INTENTS is intents.INTENTS`, and a test reads both modules' source to fail if a literal is ever reintroduced. **Semantically neutral by construction: nothing was added and nothing moved.** The nine identifiers, their order, their query wording and the subject-lead grouping are byte-identical; twelve representative queries spanning all three skills and all nine intents are pinned as exact strings. Category mappings are now explicit and testable — `company`: `profile`/`trends`/`positioning`; `market`: `sizing`/`trends`/`overview`/`drivers`; `competitor`: `trends`/`positioning`/`landscape`/`comparison`. **Shared intents stay shared identifiers:** `trends` is listed once naming three categories and `positioning` once naming two, with a test asserting no category-prefixed or category-suffixed twin exists; `benchmark` carries no category because it is the category-agnostic request default. `industry` remains a valid request category with **no** intent mappings — it gains them in the milestone that builds its skill. **Immutability is a security property, not tidiness:** intent metadata decides query wording and query wording is what the gate assesses, so records are namedtuples and the mappings are `MappingProxyType` — there is no write path, and tests prove a hostile subject and an injected competitor name change nothing. **The registry is metadata only** — a test reads its source and fails if `open_retrieval`, `close_retrieval`, `assess(`, `ScoutBrief`, `parse_reply`, `EvidenceSet`, `candidate_claim`, `urllib` or `socket` appears in it. **No new command, skill, agent, intent, category or MCP server; no gate, scout-protocol, source-tier, evidence or claim-verification change; no skill or command file touched.** Production files changed: `intents.py` (new), `contract.py`, `query.py`, `research/__init__.py` — `__all__` gained names, lost none. `INTENT_TERMS` changed type `dict` → `MappingProxyType`; no caller writes to it. **58 focused tests**, verified to have teeth by a temporary wording mutation that failed 3 of them. **2533 tests pass**, 0 failures, 0 errors, 19 skipped (baseline 2475); all 26 M9 modules pass (1372 tests); `claude plugin validate . --strict` passes. See `docs/development/2026-09-14-m9d4-research-intent-registry.md` |
| `biq-industry-research` skill | `COMPLETED` | **M9-D.5, 2026-09-14.** Tier-0 industry research over the M9-A/M9-B core — no second pipeline and no engine code beyond two additive intents. Six focus values (`overview`, `size-growth`, `trends`, `drivers-risks`, `structure`, `full`), each one **distinct research question** with its own gate-authorised retrieval, operation and single dispatch; `full` is five. Ten fixed output sections. **Its analytical object is the industry as a system**, which is what keeps it distinct from `biq-market-analysis` (a defined market's size and demand) and `biq-competitor-analysis` (named companies); the skill names both so a misdirected request is routed rather than answered badly. Its defining rule is that **nothing is scored**: the repository holds no metric contract for industry attractiveness or competitive intensity and this milestone does not add one, so there is no attractiveness index, no Porter's Five Forces rating, no 1–10 scale, no weighted total and no ranking of industries, segments or companies — declined **even when asked directly**. Its second rule is **structure without competitor drift**: companies appear only as sourced examples of participant *kinds* and are never promoted to a competitor, a leader or a major player; concentration is reported only where a source measured it, never inferred from how many companies were mentioned, never calculated without a supported denominator, never turned into a ranking. Industry sizing inherits the market-size discipline with a sixth check added (definition, geography, period, currency/unit, measurement basis **and** methodology), fails on *unknown* rather than assumed match, and a source's CAGR stays that source's estimate. Explicit refusals for investment views "in any form, including by implication". No recommendations (class 7 is M10). **131 focused tests.** See `docs/development/2026-09-14-m9d5-industry-research.md` |
| `/industry-research` command | `COMPLETED` | **M9-D.5, 2026-09-14 — deterministic work complete; live smoke test outstanding (deferred by the milestone prompt, not skipped).** A **thin orchestrator** over `biq-industry-research`, the same shape as the three before it: validates input, resolves Business Context for **public** terms only, routes entity ambiguity through the skill's protocol, invokes the skill, presents the result. Requires an industry and **no company and no competitor list**. It performs no retrieval, builds no evidence, tiers no source, compares no two figures, computes no growth rate, computes no concentration ratio, decides no participant identity, proposes or verifies no claim, ranks nothing, scores nothing and defines no output section — asserted by test (`open_retrieval(`, `close_retrieval(`, `WebSearch`, `WebFetch`, `Task(`, `EvidenceSet`, `evidence_id`, `BIQ-REC/1`, `BIQ-END/1`, the tiering constants, `FIRST_PARTY_COMPANY_DOMAINS`, `candidate_claim(`, `proposals=`, `verified: true`, `INTENT_REGISTRY`, formula-shaped tokens and ranking phrasing are all absent), plus a test proving every arithmetic verb in the file sits inside a prohibition, and a converse test proving the skill *does* hold the machinery so the boundary is real rather than merely unwritten. No registry spec, for the same reason as M9-D.1 through D.3. **51 focused tests.** **One shared-core change, additive and within ADR-0021: two intents added** — `definition` and `structure` — because no existing intent's query wording expressed *what is this industry* or *how is it organised* (`overview` renders as the literal words "market overview"; `landscape` as "competitive landscape", which would steer industry structure into competitor research). `sizing`, `trends` and `drivers` are **reused**, so industry asks five research questions through five intents of which only two are new. Neither new identifier is category-prefixed. **No ADR: ADR-0021 already decided the mechanism** ("`industry` joins `ANALYSIS_CATEGORIES` and the intents it asks add `INDUSTRY` to their `categories` field"), and the prompt forbids an ADR that merely documents implementation. **Six existing tests retargeted, none deleted, no security assertion touched** — all six asserted the previous *absence* of `/industry-research` or pinned the enumeration at a closed nine; each was replaced by the positive statement it was really guarding, and two new absence tests (Milestone-10 commands) replace the coverage the emptied research tuple gave up. **2719 tests pass**, 0 failures, 0 errors, 19 skipped (baseline 2533); all 28 M9 modules pass (1556 tests); `claude plugin validate . --strict` passes. **Outstanding:** the fresh-session live `/industry-research` smoke, explicitly deferred by the milestone prompt to a separate session after review. Until it runs, the command is **not** demonstrated live. See `docs/development/2026-09-14-m9d5-industry-research.md` **Live smoke run 2026-09-27 (M14-5), `/industry-research commercial aerospace --focus structure`: criteria 1–4, 6 and 7 met.** Ten sections, one dispatch, 3 records, all tier C, confidence LOW, 0 verified. **Criterion 5 not met:** trimmed reply, identical records. Stays `REVIEW`. See `docs/development/2026-09-27-m14-5-final-product-corrections.md` **Live smoke PASSED 2026-09-27 (M14-6, checkpointed `57e92fa`): `/industry-research commercial aerospace --focus structure` in a fresh `claude -p --plugin-dir` session.** Every documented criterion was met: the command was discovered and routed through its skill; exactly one gate-authorised dispatch with public terms only; the reply closed from the harness capture (ADR-0053), with the scout reply recorded by the harness byte-identical to the text the parser read (6,030 characters); tiers recomputed locally; 0 claims verified; confidence LOW; ten sections; no file read; no internal term sent; the verifier connected. See `docs/development/2026-09-27-m14-6-m9-smoke-protocol-remediation.md` |

**Out of scope for M9:** a generic regulatory-developments capability and a separate
recent-company-developments command or skill. Current company information retrieved during
company analysis stays inside the approved company-research scope and follows the same
source, freshness, provenance and disclosure rules.

**Deliberately not done in the 2026-09-10 governance step:** the external-research engine,
the disclosure gate, retrieval, any M9 skill, any M9 command, and the M9 schemas.

**9-B approved by the project owner on 2026-09-10**, on the live verification recorded in
`docs/development/2026-09-10-m9b-live-verification-closure.md`: acceptance criteria 1–6 all
`PASS`, full suite **1,562 tests, 0 failures, 0 errors, 19 skipped**, working tree unchanged
by the verification. Approval closes 9-B's implementation and status only. It does **not**
close the two items deferred above; both were closed separately on 2026-09-11 — the
bare-envelope contract as **M9-C.1**, the advisory-language wording as **M9-C.2**. Nor does
approval make external research
user-reachable: `/retrieval-slice` is an integration harness carrying
`disable-model-invocation`, not a research capability. The user-facing capability is the
9-C skills and the 9-D commands.

## Milestone 10 — Synthesis & Executive Reporting · `COMPLETED`

*Status reconciled on 2026-09-18 by the post-M12-B roadmap gate. Every M10 sub-milestone below is `COMPLETED` and was
checkpointed at the owner's instruction (`62580f3` to `4dc6562`). M10.2's `COMPLETED (FAILED)` verdict was remediated by
M10.2-R to R.14. The synthesis forecast translator was always recorded as a separate decision, outside M10's scope. No
M10 work was performed by the reconciliation. **The owner confirmed M10 `COMPLETED` / closed for roadmap purposes on
2026-09-18** (M13 contract finalization), on the same basis: the completed and checkpointed sub-milestones and
remediation chain, the Executive Report included. M10 is not reopened, and no M10 record or ADR was edited.*

### M10.1 — Cross-domain synthesis foundation · `COMPLETED (VERIFIED LIVE)`

The shared intermediate representation the four Layer-3 capabilities will read. Scope taken
from the M10.1 brief and ADR-0022.

**Verified live on 2026-09-15** by the M10.2-R live session, against real retrieved
evidence rather than fixtures: the compatibility ALLOW branch fired on a genuinely
comparable live pair, every provenance attack was refused, serialisation was
byte-identical across rebuilds and the set validated against its schema. See M10.2-R
below and `docs/development/2026-09-15-m10-2r-live-allow-branch-verification.md`.

| Task | Status | Evidence |
|---|---|---|
| `synthesis/` package: contract, compatibility, conflicts, confidence, limitations, merge, synthesis_set | `COMPLETED` | 7 modules, stdlib only; no existing module edited |
| Canonical `SynthesisSet` with deterministic serialisation | `COMPLETED` | Sorted keys, stable order, byte-identical across repeated builds |
| `SOURCED` statement kind (evidence class 3) + domain constraint | `COMPLETED` | External material has no kind to become an internal fact *as* |
| Provenance references resolved against registered objects | `COMPLETED` | Unregistered id raises; `unavailable` must carry a reason |
| Four-state support as a view of the M9 policy | `COMPLETED` | `SUPPORT_FROM_TIER_ASSESSMENT`; weakest-leg rule for cross-domain items |
| Six conflict kinds, preserved and never settled | `COMPLETED` | No midpoint, no winner, no tier-weighted resolution; no removal API |
| Materiality carried from the configured policy, never re-judged | `COMPLETED` | No second threshold table; asserted by test |
| Deterministic confidence with named, traceable reason codes | `COMPLETED` | 15 codes; `statistical_interval` constant `false` |
| Limitations accumulate; exact deduplication only | `COMPLETED` | `NEVER_SUPPRESSES`; first-seen order preserved |
| Compatibility test across 7 dimensions, failing on unknown | `COMPLETED` | No currency conversion, no unit rescaling, no combined figure |
| `lib/schemas/synthesis.schema.json` | `COMPLETED` | Validated by `jsonschema_mini`; `recommendations` capped at `maxItems: 0` |
| Deterministic cross-domain fixture | `COMPLETED` | `tests/fixtures/build_synthesis_fixtures.py`; all citations on `example.invalid` |
| M10.1 focused tests | `COMPLETED` | **151 tests** across 3 unit modules + 1 integration module |
| Full regression | `COMPLETED` | **2,870 tests, 0 failures, 0 errors, 19 skipped** (baseline 2,719) |
| Plugin validation `--strict` | `COMPLETED` | Passed |
| ADR-0022, architecture §7 synthesis layer, dated development record | `COMPLETED` | |

**Deliberately not done in M10.1:** SWOT, strategy recommendations, decision support,
executive reporting, any slash command, any skill, any research intent, any connector. No
live external research was performed; the milestone is deterministic infrastructure and its
fixture evidence is synthetic.

### M10.2 — Live cross-domain synthesis verification · `COMPLETED (FAILED)`

The first live test of M10.1 against real internal analysis and real external evidence:
`/profitability-analysis` on the demo dataset, and one Tier-0 retrieval —
`/industry-research commercial aerospace --focus size-growth`, intent `R.SIZING`, one scout
dispatch, zero retries, `BIQ-REC/1` × 2 and one `BIQ-END/1`.

Compatibility, conflicts, confidence, determinism and the disclosure boundary all held:
22 of 35 dimension cells came back `unknown` because the live sources stated no geography
and no methodology, and the check failed on unknown rather than assuming a match; two
vendor estimates 3.7× apart were preserved as a definitional conflict rather than averaged;
zero conversions; nothing internal was transmitted. Three of four provenance attacks were
refused.

**The fourth was not**, which is why the milestone is recorded as failed: an item declared
with an internal `origin` while citing only external evidence entered the set labelled
`kind: FACT`, `domain: internal`, `trust: internal`, `evidence_class: 1`. The verification
also found no public object-level seam from a completed retrieval into synthesis, and no
genuinely comparable live pair, so the compatibility ALLOW branch went unexercised. See
`docs/development/2026-09-15-m10-2r-provenance-footing-and-seam.md` for the remediation.

### M10.2-R — Provenance footing and the retrieval seam · `COMPLETED`

| Task | Status | Evidence |
|---|---|---|
| Internal footing invariant enforced at `SynthesisSet.add()` | `COMPLETED` | ADR-0023; resolves against the registries, ignores `domain`/`origin`/`trust`/`evidence_class`/tier |
| `INTERNALLY_FOOTED_KINDS`, `INTERNAL_PROVENANCE` in `synthesis.contract` | `COMPLETED` | Exported; `P_UNAVAILABLE` in neither |
| Schema mirrors the runtime rule | `COMPLETED` | `anyOf` on `definitions.item`; `contains` added to `jsonschema_mini` |
| `close_retrieval_object()` retrieval → synthesis seam | `COMPLETED` | ADR-0024; one shared `_close()`, `close_retrieval` contract unchanged |
| M10.2 escalation probes carried as regression tests | `COMPLETED` | `test_live_shaped_escalation_*`, all three variants |
| M10.2-R focused tests | `COMPLETED` | **55 tests** across 2 modules (31 footing + 24 seam) |
| Four provenance attacks re-run on recovered live evidence | `COMPLETED` | All four `REJECTED`; legitimate rebuild byte-identical |
| Full regression | `COMPLETED` | **2,925 tests, 0 failures, 0 errors, 19 skipped** (baseline 2,870) |
| Plugin validation `--strict` | `COMPLETED` | Passed |
| Same-domain live compatibility experiment (ALLOW branch) | `COMPLETED` | **2026-09-15, fresh session.** Four bounded Tier-0 retrievals; the ALLOW branch fired on retrieval 4 — a tier-A statistical agency release and a tier-C press article citing it, all seven dimensions stated and matching, `may_combine: True`, nothing converted, no combined figure produced |
| Four provenance attacks re-run in the live session | `COMPLETED` | All refused against **three** live evidence sets, including against tier-A official statistics — the strongest external evidence still cannot found an internal `FACT` |
| Live INCOMPATIBLE with every dimension stated | `COMPLETED` | New outcome M10.2 never reached: two live sources differing on definition, scope and methodology with **zero** unknown cells. Distinct from failing on unknown |
| Live-shaped compatibility regression tests | `COMPLETED` | **25 tests**, `tests/unit/test_m10_2r_live_compatibility.py` — all three live outcomes plus the tier-A footing probe |
| Live session regression + validation | `COMPLETED` | **2,950 tests, 0 failures, 0 errors, 19 skipped** (2,925 before the new module — the M10.2-R baseline exactly, which is the evidence that no production code changed); `claude plugin validate . --strict` passed |

### M10.2-R.1 — Cross-domain unit semantics · `COMPLETED (DECISION ONLY)`

Scoped decision milestone. **No production code, test, schema, scout or compatibility rule
was changed, and nothing here is implemented.**

| Task | Status | Evidence |
|---|---|---|
| Trace how `unit` is represented on each side of the boundary | `COMPLETED` | Internally a quantity type (`kpi/contract.py` five tokens; `MONETARY_UNITS` reads them as types). Externally unvalidated caller text — nothing in `lib/python/biq/synthesis/` validates `unit` |
| Establish whether scale normalisation is conversion | `COMPLETED` | It is not: decimal-exact, no external data, no rate, no reference date, reversible. Currency conversion is all four and stays prohibited |
| Seven-dimension decision matrix | `COMPLETED` | Nine rows, each with its reason; no row forced to compatible |
| Architectural decision | `COMPLETED` | **ADR-0025** — `unit` is a quantity type; scale is normalised into the value at statement construction, never inside `compatibility.compare()`, which is unchanged |
| ALLOW reachability assessed | `COMPLETED` | Reachable in principle for **like-for-like** monetary pairs only. Revenue vs market size stays unreachable by design — it differs on `metric_definition` and `scope`, not only on `unit` |
| Regression + validation (documentation-only change) | `COMPLETED` | **2,950 tests, 0 failures, 0 errors, 19 skipped**; `claude plugin validate . --strict` passed |
| R-12 boundary recorded, not fixed | `COMPLETED` | The M10.2-R restatement recovery is **not** accepted behaviour; see R-12 |

**M10.2-R is not closed by this milestone.** It remains `PARTIALLY VERIFIED`: the live
internal↔external ALLOW branch was never exercised, and this decision makes it reachable in
principle without demonstrating it.

**Blocks M10.3** only to the extent that M10.3 consumers must not be built assuming the
current `unit` semantics survive. Implementation of ADR-0025 is a separate, unscheduled
milestone.

### M10.2-R.2 — Canonical unit semantics implemented · `COMPLETED`

Implements **ADR-0025**. No live research, no scout dispatch, no R-12 change, no commit.

| Task | Status | Evidence |
|---|---|---|
| One closed quantity vocabulary | `COMPLETED` | `kpi.contract.QUANTITY_TYPES` — `currency`, `percent`, `ratio`, `count`, `days`, `percentage_points`. Homed where the vocabulary already lived; every token was already emitted by production. `percent` and `percentage_points` kept distinct |
| `percentage_points` homed | `COMPLETED` | Was a bare literal in `analytics/domain.py`, `analytics/financial.py`, `materiality.py`; now the contract constant |
| One monetary list, not two | `COMPLETED` | `kpi.engine.MONETARY_UNITS` **is** `kpi.contract.MONETARY_QUANTITY_TYPES` |
| Scale normalisation at construction | `COMPLETED` | New `lib/python/biq/quantity.py`; `canonical_amount()`, closed `SCALES` table, Decimal-exact, floats refused |
| Ambiguous aliases refused | `COMPLETED` | `b` and `mm` deliberately absent; a bare `$` establishes no currency |
| Enforced at `SynthesisItem` construction | `COMPLETED` | Out-of-vocabulary unit raises; `None` remains "not stated" and rejects on `unknown` |
| External construction seam | `COMPLETED` | `sourced_statement(source_unit=…/source_scale=…)`; refuses `unit` and `source_unit` together, and two disagreeing currencies |
| `compatibility.compare()` unchanged | `COMPLETED` | Not edited. A test asserts it imports nothing from `quantity`, holds no scale table, and reports `converted: False` on every outcome |
| Currency conversion still prohibited | `COMPLETED` | No FX mechanism exists or was added; asserted by test against the module source |
| Schemas closed | `COMPLETED` | `synthesis` `item.unit`, `anomaly` `observation.unit`, `forecast` `unit` → closed vocabulary. `evidence_set` conflict-position `unit` left open **on purpose** — it quotes a source, it is not a dimension |
| Backward compatibility | `COMPLETED` | No persisted artifact carries a unit; nothing writes a synthesis set to disk; `synthesis.load()` has no production caller. **No migration system invented** |
| Test matrix | `COMPLETED` | **61 tests**, `tests/unit/test_m10_2r2_unit_semantics.py`, covering all seven required groups |
| Obsolete tests retargeted, none deleted | `COMPLETED` | 5 files; each change attributable to ADR-0025 and commented at the line |
| Full regression | `COMPLETED` | **3,011 tests, 0 failures, 0 errors, 19 skipped** (2,950 + 61) |
| Plugin validation `--strict` | `COMPLETED` | Passed |

**Divergence noted, ADR not edited.** ADR-0025 words the out-of-vocabulary rule as "is
`None`, not a token to match"; the implementation **raises** instead. The decision is
identical — an unrecognised token can never satisfy the dimension — but the failure mode is
stricter, putting the failure in the caller rather than surfacing later as an unexplained
`unknown`. Owner's call whether the ADR should be amended by a successor.

**M10.2-R is still `PARTIALLY VERIFIED`.** Canonical units make an internal↔external ALLOW
reachable in principle; nothing here demonstrates one on live evidence. R-12 remains open.

### M10.2-R.3 — Deterministic internal↔external ALLOW branch · `COMPLETED`

Verification only. **No production file changed.** No live research, no scout dispatch, no
R-12 change, no commit. `compatibility.compare()` is byte-identical to its M10.1 form.

> **The fixture is synthetic and is not real external evidence.** `Synthetic Logistics Ltd`
> is not a company and `synthetic-source.example.invalid` is a reserved host. Nothing in
> this milestone is a real-world observation.

| Task | Status | Evidence |
|---|---|---|
| Truthful like-for-like fixture | `COMPLETED` | A company's own FY2025 revenue, internal calculation vs a filed-account restatement of the same metric. Deliberately **not** revenue vs market size |
| Seven dimensions all compatible | `COMPLETED` | **7 compatible, 0 incompatible, 0 unknown** — definition, period, geography, currency, unit, scope, methodology |
| ALLOW through the production path | `COMPLETED` | `compare()` and `compare_values()` both return `compatible`; `may_combine: True`. Not manually set, not monkeypatched, not bypassed |
| `converted = False`, no conversion | `COMPLETED` | Asserted on the record and against both module sources; no FX mechanism exists |
| Scale normalisation before compare | `COMPLETED` | Source published `GBP 12.5 million`; canonicalised at construction to `Decimal("12500000")`. `GBP 12,500,000` canonicalises identically and the two compare compatibly |
| Source notation stays auditable | `COMPLETED` | The evidence item's content retains "GBP 12.5 million"; `trust: untrusted` |
| Provenance / trust boundary held | `COMPLETED` | Internal stays `CALCULATION`/internal/dataset-footed; external stays `SOURCED`/external/`untrusted`. ALLOW promotes nothing |
| Negative controls | `COMPLETED` | GBP≠USD · currency≠percent · revenue≠market-size definition · UK≠Global · FY2025≠FY2026 · company≠industry scope · methodology mismatch · unknown unit · unknown currency — **all REJECT** |
| Support / confidence unchanged by ALLOW | `COMPLETED` | External stays `partially_supported`/MEDIUM at tier C; internal `supported`/HIGH. Confidence stays qualitative, no float anywhere |
| Serialisation + schema | `COMPLETED` | Byte-identical on repeat (8,508 bytes); schema validates with no errors; all seven dimensions, canonical value, provenance, materiality, trust and confidence preserved |
| Security controls active | `COMPLETED` | Forged quantity type, forged internal origin, `verified=true`, forged tier A, unresolvable provenance, serialised evidence set, disagreeing currencies — **all refused** |
| Focused tests | `COMPLETED` | **51 tests**, `tests/unit/test_m10_2r3_allow_branch.py` |
| Full regression | `COMPLETED` | **3,062 tests, 0 failures, 0 errors, 19 skipped** (3,011 + 51; no existing test changed) |
| Plugin validation `--strict` | `COMPLETED` | Passed |

**Finding for the owner — compatibility is not value agreement.** `compare()` never reads a
value, so a pair compatible on all seven dimensions while stating materially different
numbers returns `compatible`, and `compare_values()` returns early recording **no conflict
and no limitation**. The conflict layer fires only when the pair is *not* comparable — the
opposite of when a numeric disagreement is most meaningful. A value disagreement between an
internal figure and a comparable external one currently has nowhere to go. Pinned by four
tests; not changed here, because changing it is a design decision.

**M10.2-R remains `PARTIALLY VERIFIED`.** This milestone is deterministic and synthetic and
says nothing about live runtime behaviour. R-12 remains open.

### M10.2-R.5 — External dimension evidence semantics · `COMPLETED (DECISION ONLY)`

Scoped decision milestone. **No production code, test, schema, scout or compatibility rule
was changed.** Selected Option C — dimension-specific provenance with `EvidenceItem` as the
sole source-context carrier — and rejected a dedicated `SourceContext` type (ADR-0012), a
general derivation registry, and model-derived context. Produced the specification
implemented by M10.2-R.6 below.

| Task | Status | Evidence |
|---|---|---|
| Reconstruct the current model | `COMPLETED` | Fourteen questions answered against exact implementation locations; found five of seven dimensions are unvalidated caller text with no per-dimension provenance |
| Seven-dimension semantics table | `COMPLETED` | Only `unit` and `currency` have a safe derivation path, and only because `quantity.canonical_amount()` reads stated notation and fails closed |
| M10.2-R.4 case analysis | `COMPLETED` | Diagnosed **B — correct but evidence-model-limited**. No mechanism would have rescued that run: the sources stated none of the three dimensions |
| Architectural options A–E | `COMPLETED` | Decision matrix; Option C selected, B rejected as a second home for one concept |
| Security analysis | `COMPLETED` | Fifteen attacks; three (unsupported currency, geography from multinationality, methodology from source type) found **unblocked** by the pre-R.6 architecture |

### M10.2-R.6 — Dimension provenance and source-context admissibility · `COMPLETED`

Implements **ADR-0026**. No live research, no scout dispatch, no R-12 change, no commit.
`compatibility.compare()` is byte-identical to its M10.1 form.

> **Every fixture is synthetic.** `acme-filings.example.invalid` and
> `other-source.example.invalid` are reserved hosts that can never resolve; `Acme Industrial
> plc` is not a company. Nothing in this milestone reached a network.

| Task | Status | Evidence |
|---|---|---|
| `DimensionProvenance` type | `COMPLETED` | New `lib/python/biq/synthesis/dimension_provenance.py`; immutable, nine slots, source metadata refused as constructor input |
| Four bases, three admissible | `COMPLETED` | `stated`, `context`, `derived` admissible; `asserted` recorded and serialised but reads as unstated. No flag admits it |
| Evidence-registry resolution | `COMPLETED` | Resolved at `SynthesisSet.add()` beside `_require_internal_footing()`; unregistered evidence yields `unresolved_evidence` |
| Same-document binding | `COMPLETED` | Identical reference required for `context`; cross-source and same-publisher-different-document both refused |
| Operation binding | `COMPLETED` | Footing evidence must share the statement's retrieval operation |
| Applicability | `COMPLETED` | Period **and** scope must be declared and match; an undeclared axis is never read as "applies everywhere" |
| Excerpt containment | `COMPLETED` | The quoted text must genuinely be in the retrieved content. **Containment is proved, meaning is not** — stated in ADR-0026 rather than implied |
| Closed derivation registry | `COMPLETED` | Two ADR-0025 rules, `frozenset`, no register function; `geography` and `methodology` have no derived path at all |
| Conflict handling | `COMPLETED` | Two admissible footings disagreeing ⇒ dimension unresolved **plus** an explicit conflict. Never newest, tier, first or average |
| Round-trip security | `COMPLETED` | `resolved_dimensions` and the resolution trail are **not** restored by `from_dict()`; serialised `source_tier`/`trust` are discarded, not read |
| `compatibility.compare()` unchanged | `COMPLETED` | md5 `35a89e32f6fad71bc7c21abe9dbe4915`, byte-identical; a test asserts it contains no provenance, evidence, tier or registry logic |
| ADR-0025 unchanged | `COMPLETED` | Quantity vocabulary, scale normalisation and the FX prohibition all re-asserted by test |
| Schema | `COMPLETED` | `dimension_provenance`, `dimension_resolution`, `resolved_dimensions` added; closed `basis` enum; fixed seven-dimension serialisation order |
| Test matrix | `COMPLETED` | **91 tests**, `tests/unit/test_m10_2r6_dimension_provenance.py`: fixtures A–I, the 27-item attack matrix, boundaries, strict mode, serialisation |
| No existing test changed | `COMPLETED` | The mechanism is additive; all 3,062 prior tests pass unmodified |

**Additive by design, and the residual gap is named.** A dimension carrying no footing is
passed through unchanged, so unmigrated callers behave exactly as before.
`SynthesisSet(require_dimension_provenance=True)` closes that for callers who opt in.
Migrating the four research skills to emit footings is follow-up work and was **not** done
here — the same phasing ADR-0025 used.

**M10.2-R remains `PARTIALLY VERIFIED`.** This milestone is deterministic and synthetic. It
says nothing about live runtime behaviour, and R-12 remains open.

### M10.2-R.8 — Source-context capture and currency-code admissibility · `COMPLETED`

Implements **ADR-0027**. No live research, no scout dispatch, no R-12 change, no commit, no
push. `compatibility.compare()`, `quantity.py`, `research/scout.py`, `BIQ-REC/1` and
`BIQ-END/1` are all unchanged.

> **Every fixture is synthetic.** `acme-filings.example.invalid` and
> `elsewhere.example.invalid` are reserved hosts that can never resolve; `Acme Industrial
> plc` is not a company. Nothing in this milestone reached a network.

| Task | Status | Evidence |
|---|---|---|
| Scout content guidance | `COMPLETED` | New *What `content` should capture* section in `agents/biq-research-scout.md`: capture the figure **with** the source-stated context around it, as source text, contiguous, and only where the document states it |
| Protocol untouched | `COMPLETED` | `BIQ-REC/1`, `BIQ-END/1`, `ACCEPTED_RECORD_FIELDS`, operation binding, count semantics and the parser are all unchanged; `research/scout.py` md5 `fe2c4fac1736abea4aaf3c997fdd2b6e` |
| No new field, no new authority | `COMPLETED` | Guidance names `context`, `source_tier`, `trust`, `verified`, `geography`, `currency`, `methodology`, `dimension` and `confidence` as fields that do **not** exist; a test asserts the documented field table still equals `ACCEPTED_RECORD_FIELDS` |
| Inference prohibitions | `COMPLETED` | Geography not from headquarters, domicile, domain, TLD, publisher or exchange; methodology not from source type; currency not from a bare symbol; period not from a filing or publication date; no conversion, no paraphrase, no stitched passages |
| One record per source document | `COMPLETED` | The ADR-0027 v1 convention is stated in the guidance and pinned by test |
| Currency ISO-code predicate | `COMPLETED` | `dimension_provenance.currency_excerpt_carries_code()`: a `stated`/`context` `currency` footing is admissible only where its excerpt prints exactly one ISO 4217-shaped code and that code is the value claimed. New reason code `currency_code_not_in_excerpt` |
| The M10.2-R.7 gap closed | `COMPLETED` | A footing quoting `"$4.2 billion"` and claiming `USD` was previously **admitted**; it is now refused with a named reason. `£`, `€`, `¥`, "US dollars" and "British pounds" are refused too |
| No currency table | `COMPLETED` | Structural shape only — three uppercase ASCII letters, the shape `quantity.parse_source_unit` applies. No name lookup, no FX, no synonyms. ADR-0027 §23 stays open |
| Bindings still precede the predicate | `COMPLETED` | Containment, operation, document, citation and applicability are all checked first, so an absent excerpt still reads `excerpt_not_in_source` rather than the narrower currency reason |
| `compatibility.compare()` unchanged | `COMPLETED` | md5 `35a89e32f6fad71bc7c21abe9dbe4915`, byte-identical; the test asserting it holds no provenance, evidence, tier or registry logic still passes |
| `quantity.py` and ADR-0025 unchanged | `COMPLETED` | md5 `a43581d8ff7a29b92f5d200fb03818e1`; ADR-0025 and ADR-0026 not edited |
| Test matrix | `COMPLETED` | **81 tests**, `tests/unit/test_m10_2r8_source_context.py`: scout guidance, the currency predicate, R.6 regression, source-context semantics |
| No existing test changed | `COMPLETED` | All 3,153 prior tests pass unmodified; total **3,234**, 0 failures, 0 errors, 19 skipped |
| Strict validation | `COMPLETED` | `claude plugin validate . --strict` passed |

**Half of this mechanism is guidance, and that is the accepted cost.** ADR-0027 chose to
carry source context in the existing `content` field rather than add one, so what the scout
captures rests on the agent definition rather than on a type. A scout that ignores the
guidance produces records with no context and dimensions that stay unknown — the safe
failure, but one the architecture cannot detect. The tests pin the guidance's substance;
nothing can pin the model's compliance.

**M10.2-R remains `PARTIALLY VERIFIED`.** This milestone is deterministic and synthetic. It
says nothing about live runtime behaviour, and R-12 remains open and untouched.

**Recording gap noted, not repaired here.** M10.2-R.7 produced ADR-0027 but left no section
in this plan and no record in `docs/development/`. That predates this milestone and fixing
it is outside its scope; it is flagged so it is not lost.

### M10.2-R.9 — Company Analysis dimension-footing migration · `COMPLETED`

The first skill migrated to **ADR-0026** / **ADR-0027**. No live research, no scout dispatch,
no R-12 change, no commit, no push. `compatibility.compare()`, `quantity.py`,
`research/scout.py`, `BIQ-REC/1`, `BIQ-END/1`, the intent registry, the disclosure gate and
the tier classifier are all unchanged, and ADR-0025, ADR-0026 and ADR-0027 were not edited.

> **Every fixture is synthetic.** `synthetic-logistics.example.invalid` and
> `commentary.example.invalid` are reserved hosts that can never resolve; `Synthetic
> Logistics Ltd` is not a company; no real filing is quoted or paraphrased. Nothing in this
> milestone reached a network.

| Task | Status | Evidence |
|---|---|---|
| Company Analysis footing guidance | `COMPLETED` | One new section, *Footing a figure for comparison*, in `skills/biq-company-analysis/SKILL.md`: what a footing is for, the six categories kept apart, contiguous verbatim excerpts, and every ADR-0026/0027 prohibition stated where the authoring model reads it |
| "You locate; Python decides" | `COMPLETED` | The guidance states that a footing the model wrote is a claim about the source, never authority over it, and carries no extra weight for having been written by the analysing model |
| Admissibility unchanged | `COMPLETED` | **No new admissibility code was needed.** `DimensionProvenance`, `sourced_statement(dimension_provenance=…)` and `SynthesisSet(require_dimension_provenance=True)` already provided the whole path and already refused an unfooted `geography="Global"` / `currency="USD"` / `methodology="GAAP"` |
| Shared authoring helper | `COMPLETED` | `synthesis.source_footings()` — 30 lines in `dimension_provenance.py`, exported from the package. Builds footings from `(value, source_excerpt)` pairs and nothing else: no evidence lookup, operation or document binding, containment, applicability, currency predicate or conflict handling, asserted by a test that reads its own source |
| No second provenance architecture | `COMPLETED` | One type, one resolver, one registry. No Company Analysis copy of any binding, no new record field, message or protocol, and no new reason code, basis, derivation rule or dimension |
| `derived`/`asserted` not authorable by the helper | `COMPLETED` | Refused with `SynthesisError`; both remain constructible directly, where the reason must be written out. A mistyped dimension and a value with no excerpt are refused rather than skipped |
| Synthetic fixture | `COMPLETED` | Two genuine `EvidenceItem`s in one genuine `EvidenceSet`, one document, one operation, tier computed by `sources.classify_tier` (→ `C`, inferred) rather than chosen by the fixture; figure canonicalised from `USD billion` notation by ADR-0025 |
| Seven-dimension ALLOW | `COMPLETED` | 3 `stated` + 3 `context` + 1 `derived` footing; all seven resolve under `require_dimension_provenance=True`; against a synthetic internal twin, `compatibility.compare()` returns **compatible · 7 matched · 0 mismatched · 0 unknown · may_combine true · converted false** |
| No promotion from admissibility | `COMPLETED` | Footed and unfooted statements carry identical `support` and `confidence`; the statement stays `SOURCED`, external, `untrusted`, evidence class 3, unverified; `recommendations` empty; no arithmetic, ranking or forecast produced |
| Negative controls | `COMPLETED` | **35 controls** — the milestone's 24 plus 11 the API made available — each asserting the named reason code: `no_dimension_provenance`, `basis_inadmissible`, `currency_code_not_in_excerpt`, `value_disagrees_with_statement`, `excerpt_not_in_source`, `document_mismatch`, `operation_mismatch`, `applicability_mismatch`, `evidence_not_cited_by_statement`, `unresolved_evidence`, `conflicting_admissible_values` |
| Conflicts stay explicit | `COMPLETED` | Two admissible methodology footings ("US GAAP", "cash basis") leave the dimension unresolved, keep **both** positions and record one `methodology` conflict reading "Neither is preferred" |
| Forged metadata has no doorway | `COMPLETED` | `source_tier`, `trust` and `verified` refused by the constructor (`SynthesisError`) and absent from the helper's signature (`TypeError`); discarded on deserialisation; a reloaded set restores no admissibility verdict |
| Prompt injection inert | `COMPLETED` | A `SYSTEM:` instruction inside retrieved `content` is quoted as content and changes nothing: no `verified` key anywhere in the result, tier stays `C`, trust stays `untrusted` |
| Output contract intact | `COMPLETED` | The ten sections parse in order from the skill's own table; `**No recommendations.**` and the `[RECOMMENDATION]` sentence intact; the new section states that nothing is ranked and no market share, strategy or investment view follows from a dimension resolving |
| Test matrix | `COMPLETED` | **99 tests**, `tests/unit/test_m10_2r9_company_analysis_footings.py`: guidance, positive path, internal twin and ALLOW, 35 negative controls, protected boundaries |
| No existing test changed | `COMPLETED` | All 3,234 prior tests pass unmodified; total **3,333**, 0 failures, 0 errors, 19 skipped. A numbered table in the new section initially collided with `test_m9d1`'s section-order regex; **the new section was rewritten, not the test** |
| Strict validation | `COMPLETED` | `claude plugin validate . --strict` passed |

**The residual gap is the one ADR-0026 named: containment is not meaning.** A footing that
quotes a sentence the document genuinely contains and reads it wrongly is admissible, and no
code can detect that. What is now impossible is supplying a dimension backed by no source
text at all — which is what M10.2-R.5 found unblocked, and what this migration closes for
this skill.

**Three research skills remain unmigrated.** `biq-market-analysis`,
`biq-competitor-analysis` and `biq-industry-research` author no footings and were deliberately
untouched; the additive default means they behave exactly as before. **No command wires this
up yet** — `/company-analysis` does not build a strict set or author footings, so the path is
proved by test rather than by a user-reachable flow.

**ADR-0027 §17 is now one skill out of date** ("None is migrated by this ADR"). Recording the
`biq-company-analysis` migration there is proposed as a documentation change and was
deliberately **not** applied: the prompt prohibits editing ADR-0027, and an accepted
decision's text is not an implementation milestone's to amend. This plan carries the
migration status meanwhile.

**M10.2-R remains `PARTIALLY VERIFIED`.** This milestone is deterministic and synthetic. It
says nothing about live runtime behaviour, and R-12 remains open and untouched.

### M10.2-R.10 — the Company Analysis command reaches the strict footing path · `COMPLETED`

Closes the gap M10.2-R.9 recorded in its own limitations: *"No command wires this up —
`/company-analysis` does not build a strict set or author footings, so the path is proved by
test rather than by a user-reachable flow."* The mechanism did not change; what changed is
that shipped code now runs it in the shipped order.

> **Every fixture is synthetic.** `synthetic-freightworks.example.invalid` and
> `commentary.example.invalid` are reserved hosts that can never resolve; `Synthetic
> Freightworks Ltd` is not a company; no real filing is quoted or paraphrased. No live
> research was performed and no network was reached.

| Task | Status | Evidence |
|---|---|---|
| Integration point identified | `COMPLETED` | Two defects, not one: the skill's Research flow named `close_retrieval()`, which returns the set **serialised** — the one shape `register_external()` refuses — and nothing sequenced the five calls between a completed retrieval and a comparison |
| One sequencing seam | `COMPLETED` | `synthesis.footed_statement()` (`synthesis/research_footing.py`, ADR-0028): `close_retrieval_object` → `register_external` → `source_footings` → `sourced_statement(dimension_provenance=…)` → strict resolution. Exported once from the package |
| Strict by construction | `COMPLETED` | Four refusals: the evidence must be the object a completed retrieval produced; the set must carry `require_dimension_provenance=True`; a dimension is either footed or declared, never both; a `context` footing names its own evidence item with no default |
| Existing helper reused | `COMPLETED` | `source_footings()` is called, not reimplemented. A test reads the seam's own source and asserts it contains no `_registry`, `P_EVIDENCE`, `_excerpt_present`, `_applies`, `currency_excerpt_carries_code`, `iso_currency_codes`, `_assess`, `ADMISSIBLE_BASES`, `_fold` or `REASON_TEXT`, and exactly one `DimensionProvenance(` — the `unit` derivation already in the closed registry |
| Genuine retrieval objects only | `COMPLETED` | Every fixture starts at the scout's `BIQ-REC/1` **reply text** and goes through `close_retrieval_object`. A serialised `close_retrieval` result is refused by name; a dict, a list, a string, a serialised set and an `EvidenceSet` **subclass** are each refused |
| Seven-dimension ALLOW, end to end | `COMPLETED` | 6 `stated` + 1 `derived` footing on one locally tiered (`C`, inferred) document; all seven resolve; against a synthetic internal twin, `compatibility.compare()` returns **compatible · 7 matched · 0 mismatched · 0 unknown · may_combine true · converted false** |
| Fail-closed preserved | `COMPLETED` | Each of the seven dimensions dropped in turn resolves to `None` with `no_dimension_provenance` and stops the comparison at `unknown` naming exactly that dimension; a six-of-seven document never reaches `compatible` |
| Currency admissibility preserved | `COMPLETED` | Bare `$`, the name "US dollars" and an excerpt printing some other code-shaped token each yield `currency_code_not_in_excerpt`; a token disagreeing with the notation is refused at construction by ADR-0025; two admissible codes yield `conflicting_admissible_values` and a recorded conflict |
| Bindings preserved | `COMPLETED` | `document_mismatch`, `operation_mismatch` and `applicability_mismatch` (both a wrong period and an undeclared applicability) each reproduced through the command path; a `stated` footing cannot be authored against an item the statement does not cite |
| Source metadata is not evidence | `COMPLETED` | Excerpts quoting the reference URL, the source name, the publication date, the local tier and the source type each yield `excerpt_not_in_source`; paraphrase and stitching likewise |
| Caller cannot assert a dimension | `COMPLETED` | A declared-but-unfooted dimension reads as unstated; footed-and-declared is refused; `evidence_ids`, `dimension_provenance` and `unit` are refused as caller fields; `unit` is refused as a quotation; `source_tier`, `trust`, `verified`, `freshness` and `source` have no parameter |
| No trust escalation | `COMPLETED` | Footed and unfooted statements carry identical `support` and `confidence`; the statement stays `SOURCED`, external, `untrusted`, class 3, unverified; tier stays `C`; a `SYSTEM:` instruction in retrieved content changes nothing; `recommendations` empty |
| Internal footing untouched | `COMPLETED` | An internal `CALCULATION` citing only this evidence is still refused (ADR-0023); the internal twin still rests on a registered dataset |
| Command and skill wiring | `COMPLETED` | `commands/company-analysis.md` gains step 4, *Comparing a published figure with your own* — prose only, no pipeline code, no admissibility rule. `skills/biq-company-analysis/SKILL.md` names `close_retrieval_object` and `footed_statement`, with the underlying calls kept in prose |
| Protected components unchanged | `COMPLETED` | `compatibility.py` `35a89e32f6fad71bc7c21abe9dbe4915`, `quantity.py` `a43581d8ff7a29b92f5d200fb03818e1`, `research/scout.py` `fe2c4fac1736abea4aaf3c997fdd2b6e` — all three identical to the R.9 baseline. `BIQ-REC/1` unchanged |
| Test matrix | `COMPLETED` | **97 tests**, `tests/unit/test_m10_2r10_company_analysis_command_footing.py`: wiring, the production path end to end, the ALLOW, 7 missing-dimension controls, 6 currency controls, 7 binding controls, 8 excerpt controls, 9 path-integrity controls, 10 assertion controls, trust and no-second-implementation |
| No existing test changed | `COMPLETED` | All 3,333 prior tests pass unmodified; total **3,430**, 0 failures, 0 errors, 19 skipped |
| Strict validation | `COMPLETED` | `claude plugin validate . --strict` passed |

**Containment is still not meaning.** A footing quoting the fixture's registered-address
sentence to establish `United States` is admissible, because the sentence really is in the
source — and a test asserts that honestly, then asserts that the pair is nonetheless
`incompatible` against an internal figure stated as worldwide. ADR-0026's boundary is
unchanged and unclosable by code.

**Three research skills remain unmigrated.** `biq-market-analysis`,
`biq-competitor-analysis` and `biq-industry-research` author no footings and were
deliberately untouched; each migrates by calling this seam rather than by copying it.

**`docs/README.md`'s ADR list is stale** — it carries 0001–0016, 0025 and now 0028, and has
been missing 0017–0024, 0026 and 0027 since before this milestone. Flagged rather than
repaired: the gap is pre-existing and repairing it is not this milestone's scope.

**M10.2-R remains `PARTIALLY VERIFIED`.** This milestone is deterministic and synthetic. It
says nothing about live runtime behaviour, and R-12 remains open and untouched.

### M10.2-R.11 — Market Analysis reaches the strict footing path · `COMPLETED`

The question R.10 left open was whether `footed_statement()` was a seam or a special case.
It is a seam: migrating `/market-analysis` added **no production code whatsoever**. No file
under `lib/` was modified, created or deleted in this milestone.

> **Every fixture is synthetic.** `synthetic-sizing.example.invalid`,
> `second-sizing.example.invalid` and `trade-commentary.example.invalid` are reserved hosts
> that can never resolve; the two "sizing houses" are not companies; no real market report is
> quoted or paraphrased. No live research was performed and no network was reached.

| Task | Status | Evidence |
|---|---|---|
| Integration point identified | `COMPLETED` | Same shape as R.10 and one domain difference: the skill's *Research flow* named `close_retrieval()`, which serialises the set, and nothing sequenced the calls after it. The market-size compatibility test already existed in prose; R.11 connects it to the engine that enforces it |
| Seam reused unchanged | `COMPLETED` | `S.footed_statement(retrieval, S.ORIGIN_MARKET, …)`. A test asserts `research_footing.py` contains neither `company` nor `market`, so the seam is origin-agnostic rather than retrofitted |
| No second mechanism | `COMPLETED` | No new module, helper, reason code, basis, derivation rule, dimension, intent, record field or protocol. No file under `lib/` touched |
| Retrieval object path | `COMPLETED` | Skill names `close_retrieval_object` for any retrieval whose figure will be compared, and says why a serialised set cannot enter synthesis. `trends`/`drivers-risks` retrievals keep `close_retrieval` |
| `scope` as the seventh dimension | `COMPLETED` | The skill maps its five checks onto the engine's seven and states why market sizing needs `scope` separately — total addressable vs serviceable vs served — as **stricter, never weaker**. The existing "**all five must hold**" rule is untouched |
| Seven-dimension size figure | `COMPLETED` | 6 `stated` + 1 `derived` footing on one locally tiered (`C`, inferred) sizing report carrying `claim_kind: market_sizing`; all seven resolve; figure canonicalised from `USD billion` by ADR-0025 |
| External-to-external comparison | `COMPLETED` | Two published sizes on one definition → **compatible · 7 matched · may_combine true**, and the figures are still not averaged. A wider boundary → **incompatible on `metric_definition`**, both definitions in the summary, a limitation recorded, and **no** internal/external conflict, because neither figure is the user's |
| Internal comparison | `COMPLETED` | Against the user's own bottom-up market model (engine-footed, ADR-0023, no dimension provenance): **compatible · 7 matched · 0 mismatched · 0 unknown · may_combine true · converted false**, neither side modified |
| The share trap | `COMPLETED` | The user's *revenue* set beside a total addressable market is **incompatible on `scope`** and no share is produced. A numerator and a denominator are not two measurements of one quantity |
| Qualitative findings kept separate | `COMPLETED` | A trend statement carries no footings, no `dimension_resolution` and no invented verdict; it stays `SOURCED`, class 3, cited and traceable. It keeps its `period` in the record for sections 4 and 8 while `dimensions` reads it as unstated, so it can never reach `compatible` by accident. Footed and unfooted statements coexist in one strict set and the set still validates |
| Fail-closed preserved | `COMPLETED` | Each of the seven dropped in turn → `no_dimension_provenance` and `unknown` naming exactly that dimension, against **both** an internal figure and a second source; six-of-seven never reaches compatible on either path |
| Currency admissibility | `COMPLETED` | Bare `$`, "US dollars" and a `CEO`-shaped token → `currency_code_not_in_excerpt`; `XQZ` refused at construction; two admissible codes and two admissible methodologies → `conflicting_admissible_values` with the disagreement recorded |
| Bindings | `COMPLETED` | `document_mismatch`, `operation_mismatch`, `applicability_mismatch` for a wrong period, a wrong scope and an undeclared applicability; context with no named item refused; unregistered evidence refused |
| Metadata is not evidence | `COMPLETED` | Excerpts quoting the URL, the bare domain, the source name, the publication date, the source type and the local tier → `excerpt_not_in_source`; paraphrase, translation and stitching likewise |
| Path integrity | `COMPLETED` | Serialised `close_retrieval` result refused by name; dict, list, string, `None`, serialised set and an `EvidenceSet` **subclass** refused; `blocked` / `insufficient_evidence` / `not_authorised` refused; a real zero-record retrieval refused; non-strict set refused; internal origins refused |
| No trust escalation | `COMPLETED` | Footed and unfooted statements carry identical `support` and `confidence`; statement stays `SOURCED`, external, `untrusted`, class 3, unverified; tier stays `C`; a `SYSTEM:` instruction in retrieved content changes nothing |
| Command-level run | `COMPLETED` | A two-retrieval `full`-style run — `size-growth` footed, `trends` unfooted, own operations preserved, one strict set — reaching a compatible verdict, serialising against the schema, byte-identical on repeat, and failing closed with `INCOMPARABLE` plus lowered confidence when a dimension is dropped |
| Intents preserved | `COMPLETED` | `OVERVIEW`, `SIZING`, `TRENDS` and `DRIVERS` unchanged and still registered; no intent added |
| Competitor and Industry untouched | `COMPLETED` | Asserted by test: neither skill mentions `footed_statement`, `source_footings`, `close_retrieval_object` or `DimensionProvenance` |
| Protected components unchanged | `COMPLETED` | `compatibility.py` `35a89e32f6fad71bc7c21abe9dbe4915`, `quantity.py` `a43581d8ff7a29b92f5d200fb03818e1`, `research/scout.py` `fe2c4fac1736abea4aaf3c997fdd2b6e` — identical to the R.9 baseline. `BIQ-REC/1` unchanged |
| Test matrix | `COMPLETED` | **136 tests**, `tests/unit/test_m10_2r11_market_analysis_footing.py` |
| No existing test changed | `COMPLETED` | All 3,430 prior tests pass unmodified; total **3,566**, 0 failures, 0 errors, 19 skipped |
| Strict validation | `COMPLETED` | `claude plugin validate . --strict` passed |

**Containment is still not meaning, and market sizing has its own version of it.** A footing
quoting the report's *title* to establish the market definition is admissible, because
`_excerpt_present` searches `title` as well as `content` and the title really is the
source's text. The guidance prohibits it — "never from the market's *name*" — and a test
asserts the outcome honestly: the reading is admitted, and the pair is then `incompatible`
against a source that actually published a boundary. ADR-0026's boundary is unchanged.

**No new ADR was required.** ADR-0028 already names migrating the remaining research skills
as its own follow-up, and this milestone is that follow-up performed exactly as written. **No
approved ADR was edited**, including to record that the follow-up is now one skill further
on; that status lives here.

**Two research skills remain unmigrated.** `biq-competitor-analysis` and
`biq-industry-research` author no footings and were deliberately untouched.

**M10.2-R remains `PARTIALLY VERIFIED`.** This milestone is deterministic and synthetic. It
says nothing about live runtime behaviour, and R-12 remains open and untouched.

### M10.2-R.12 — Competitor Analysis reaches the strict footing path · `COMPLETED`

The third domain on the shared seam, and the one where a compatible verdict is most
dangerous. Like R.11, it added **no production code**: no file under `lib/` was modified,
created or deleted.

> **Every fixture is synthetic.** `contoso-logistics.example.invalid`,
> `fabrikam-freight.example.invalid` and `trade-press.example.invalid` are reserved hosts
> that can never resolve; Contoso Logistics and Fabrikam Freight are not companies; no real
> filing is quoted or paraphrased. No live research was performed and no network was reached.

| Task | Status | Evidence |
|---|---|---|
| Integration point identified | `COMPLETED` | Same shape as R.10/R.11 — the skill's *Research flow* named `close_retrieval()`, which serialises the set — plus one domain difference: the comparability test already existed in prose, and its five rows map onto **all seven** dimensions, two of them splitting in two |
| Seam reused unchanged | `COMPLETED` | `S.footed_statement(retrieval, S.ORIGIN_COMPETITOR, …)`. A test asserts `research_footing.py` contains none of `competitor`, `ORIGIN_COMPETITOR`, `rival`, `company`, `market`, `industry`, `ranking` or `share` |
| No second mechanism | `COMPLETED` | No new module, helper, reason code, basis, derivation rule, dimension, intent, record field or protocol. No `lib/` file touched |
| `geography` and `scope` separated | `COMPLETED` | The skill's row 4 ("geography **or** segment scope") is two engine dimensions. A worldwide group figure and a worldwide segment figure share a geography and come out `incompatible` on `scope` — asserted directly |
| Entity is not a dimension | `COMPLETED` | Asserted that none of the seven names a company, and that two rivals' figures on one basis reach **compatible · 7 matched · 0 mismatched · 0 unknown · may_combine true · converted false** with both values unchanged |
| Compatible authorises a row, not an order | `COMPLETED` | No ordering, superlative, market share or recommendation appears in a compatible pair's serialised set; the larger figure gains no kind, trust, support or confidence from being larger |
| Footing never promotes identification | `COMPLETED` | Stated in the skill: *an `observed` candidate with seven perfectly footed dimensions is still `observed`* |
| Competitor ↔ competitor | `COMPLETED` | Compatible on one basis; `incompatible` naming `period`, `scope` or `methodology` on each mismatch; a limitation recorded and confidence lowered on both sides; **no** internal/external conflict, because neither figure is the user's |
| Competitor ↔ internal | `COMPLETED` | Against the user's own revenue on the same basis (engine-footed, ADR-0023, no dimension provenance): compatible · 7 matched · may_combine true. An internal `CALCULATION` citing only external evidence is still refused; an internal segment figure against a group figure is `incompatible` on `scope` |
| Qualitative findings kept separate | `COMPLETED` | Positioning, offerings, strategic moves, stated initiatives and source-stated constraints carry no footings, no `dimension_resolution` and no invented verdict; they keep `period`/`geography` in the record while `dimensions` reads them unstated, so they return `unknown` against any figure |
| Fail-closed preserved | `COMPLETED` | Each of the seven dropped in turn → `no_dimension_provenance` and `unknown` naming that dimension; six-of-seven never reaches compatible against a rival **or** an internal figure |
| Currency and conflicting context | `COMPLETED` | Bare `$`, "US dollars" and a `CEO`-shaped token → `currency_code_not_in_excerpt`; `XQZ` refused at construction; two admissible currencies, methodologies **and scopes** each → `conflicting_admissible_values` with the disagreement recorded |
| Bindings | `COMPLETED` | A rival's filing cannot foot the focal company's figure (`document_mismatch`); `operation_mismatch`; `applicability_mismatch` for wrong period, wrong scope and undeclared applicability; unnamed context item and unregistered evidence refused |
| Metadata is not evidence | `COMPLETED` | URL, bare domain, source name, publication date, source type and local tier → `excerpt_not_in_source`; paraphrase, translation and stitching likewise |
| Path integrity | `COMPLETED` | Serialised `close_retrieval` result refused by name; dict, list, string, `None`, serialised set and an `EvidenceSet` **subclass** refused; `blocked`, `insufficient_evidence`, `not_authorised` and a real zero-record retrieval refused; non-strict set, non-set and internal origins refused |
| No trust escalation | `COMPLETED` | Footed and unfooted statements carry identical `support` and `confidence`; statement stays `SOURCED`, external, `untrusted`, class 3, unverified; tier stays `C`; a `SYSTEM:` instruction telling the page to rank a company first and mark itself verified changes nothing |
| Command-level run | `COMPLETED` | A `comparison` + `landscape` run — two footed figures, one unfooted qualitative finding, own operations preserved, one strict set — reaching compatible between the rivals and against an internal figure, with the qualitative finding returning `unknown` against both; schema-valid, byte-identical on repeat; failing closed with `INCOMPARABLE` and lowered confidence when a dimension is dropped, and still producing no ranking or recommendation |
| Intents preserved | `COMPLETED` | `LANDSCAPE`, `COMPARISON`, `POSITIONING` and `TRENDS` unchanged and still registered; no intent added |
| Industry Research untouched | `COMPLETED` | Asserted by test: it mentions none of `footed_statement`, `source_footings`, `close_retrieval_object` or `DimensionProvenance` |
| Protected components unchanged | `COMPLETED` | `compatibility.py` `35a89e32f6fad71bc7c21abe9dbe4915`, `quantity.py` `a43581d8ff7a29b92f5d200fb03818e1`, `research/scout.py` `fe2c4fac1736abea4aaf3c997fdd2b6e` — identical to the R.9 baseline. `BIQ-REC/1` unchanged |
| Test matrix | `COMPLETED` | **157 tests**, `tests/unit/test_m10_2r12_competitor_analysis_footing.py` |
| Existing tests | `COMPLETED` | 252 Competitor Analysis tests pass unmodified; total **3,723**, 0 failures, 0 errors, 19 skipped. **One approved assertion was narrowed on explicit user approval** — see below |
| Strict validation | `COMPLETED` | `claude plugin validate . --strict` passed |

**One approved test was narrowed, with permission.** R.11's
`test_competitor_and_industry_skills_are_untouched_by_this_milestone` asserted that *both*
`biq-competitor-analysis` and `biq-industry-research` name no footing symbols. R.12 migrating
Competitor Analysis on approval makes the competitor half of that false. The conflict between
"migrate Competitor Analysis" and "do not retarget existing tests" was **raised and decided by
the user**, not resolved silently: the skill list is now `("biq-industry-research",)`, the
test is renamed `test_the_unmigrated_research_skill_is_untouched`, and its docstring records
why. The dropped property is re-asserted more strongly in R.12's own module, which requires
Competitor Analysis to use the **shared** seam and requires the seam to contain no
competitor-specific logic. No other existing test was changed.

**Containment is still not meaning, and competitor analysis has two versions of it.** A
footing quoting the report's *title* to claim a fiscal year, and one quoting the sentence that
names the company to claim a scope, are both admissible — the text really is in the source.
Both are prohibited by the guidance, neither can be caught by code, and both are tested
honestly: admitted, recorded against the text they rest on, and then `incompatible` against a
source that stated the real value.

**One research skill remains unmigrated.** `biq-industry-research` authors no footings and was
deliberately untouched.

**M10.2-R remains `PARTIALLY VERIFIED`.** This milestone is deterministic and synthetic. It
says nothing about live runtime behaviour, and R-12 remains open and untouched.

### M10.2-R.13 — Industry Research reaches the strict footing path · `COMPLETED`

The fourth and last research domain on the shared seam. Like R.11 and R.12 it added **no
production code**: no file under `lib/` was modified, created or deleted. ADR-0028's stated
follow-up — migrating the remaining research skills — is now closed.

> **Every fixture is synthetic.** `statistics-bureau.example.invalid`,
> `sector-review.example.invalid` and `trade-council.example.invalid` are reserved hosts that
> can never resolve; the industry, the figures and every sentence are invented; no real
> statistical release is quoted or paraphrased. No live research was performed and no network
> was reached.

| Task | Status | Evidence |
|---|---|---|
| Integration point identified | `COMPLETED` | The familiar defect — the skill's *Research flow* named `close_retrieval()`, which serialises the set — plus one domain difference: this skill's compatibility test has **six** rows, not five, and they map onto the engine's seven with only one split |
| Seam reused unchanged | `COMPLETED` | `S.footed_statement(retrieval, S.ORIGIN_INDUSTRY, …)`. A test asserts `research_footing.py` contains none of `industry`, `ORIGIN_INDUSTRY`, `sector`, `company`, `market`, `competitor`, `cagr`, `gross output` or `value added` |
| No second mechanism | `COMPLETED` | No new module, helper, reason code, basis, derivation rule, dimension, intent, record field or protocol. No `lib/` file touched |
| `scope` is the measurement basis | `COMPLETED` | The skill's row 5 maps to `scope` and says why: gross output, revenue, value added, shipments and employment are different quantities. Gross output against value added → `incompatible` on `scope` with `geography`, `period` and `methodology` all matching |
| Current against prior period | `COMPLETED` | Two periods → `incompatible` with `period` the **only** mismatch, 6 matched, 0 unknown — the visible precondition for a change-over-time reading. A second difference removes it. No growth rate, CAGR or calculation is produced from the pair |
| Publication date establishes nothing | `COMPLETED` | Releases published 2026 and 2027 stating the same period → **compatible**; two published the same day stating different periods → not combinable; a footing quoting the publication date as the period → `excerpt_not_in_source` |
| Seven-dimension industry figure | `COMPLETED` | 6 `stated` + 1 `derived` footing on one locally tiered (`C`, inferred) release carrying `claim_kind: market_sizing`; all seven resolve; figure canonicalised from `USD billion` by ADR-0025 |
| External ↔ external | `COMPLETED` | Two releases on one basis → **compatible · 7 matched · 0 mismatched · 0 unknown · may_combine true · converted false**, values unchanged; mismatches on `scope`, `metric_definition`, `geography` and `methodology` each named explicitly; a limitation recorded; **no** internal/external conflict |
| External ↔ internal | `COMPLETED` | Against the user's own bottom-up industry model (engine-footed, ADR-0023, no dimension provenance): compatible · 7 matched · may_combine true. An internal `CALCULATION` citing only external evidence is still refused; an internal model on another basis or period is `incompatible` on that dimension |
| Qualitative findings kept separate | `COMPLETED` | Definition, structure, value chain, segments, dynamics, barriers, constraints and trends carry no footings, no `dimension_resolution` and no invented verdict; they keep `period`/`geography` in the record while `dimensions` reads them unstated, so they return `unknown` against any figure |
| Fail-closed preserved | `COMPLETED` | Each of the seven dropped in turn → `no_dimension_provenance` and `unknown` naming that dimension; six-of-seven never reaches compatible against another release **or** an internal model |
| Currency and conflicting context | `COMPLETED` | Bare `$`, "US dollars" and a `CEO`-shaped token → `currency_code_not_in_excerpt`; `XQZ` refused at construction; conflicting currencies, **measurement bases**, methodologies **and geographies** each → `conflicting_admissible_values` |
| Bindings | `COMPLETED` | A separately published methodology note cannot foot the release (`document_mismatch`) — the classic industry case; `operation_mismatch`; `applicability_mismatch` for wrong period, wrong basis and undeclared applicability; unnamed context item and unregistered evidence refused |
| Metadata is not evidence | `COMPLETED` | URL, bare domain, source name, publication date, source type and local tier → `excerpt_not_in_source`; paraphrase, translation and stitching likewise |
| Path integrity | `COMPLETED` | Serialised `close_retrieval` result refused by name; dict, list, string, `None`, serialised set and an `EvidenceSet` **subclass** refused; `blocked`, `insufficient_evidence`, `not_authorised` and a real zero-record retrieval refused; non-strict set, non-set and internal origins refused |
| No trust escalation | `COMPLETED` | Footed and unfooted statements carry identical `support` and `confidence`; statement stays `SOURCED`, external, `untrusted`, class 3, unverified; tier stays `C`; a `SYSTEM:` instruction telling the page to mark itself verified, rank the industry first and recommend investment changes nothing |
| Neutrality preserved | `COMPLETED` | No ranking, attractiveness, "best industry", winner or score appears in any compatible pair's serialised set; `recommendations` empty throughout |
| Command-level run | `COMPLETED` | A `size-growth` + `structure` run — two footed figures, one unfooted qualitative finding, own operations preserved, one strict set — reaching compatible between the releases and against an internal model, with the qualitative finding returning `unknown` against both; schema-valid, byte-identical on repeat; failing closed with `INCOMPARABLE` and lowered confidence when `scope` is dropped, and still producing no ranking or recommendation |
| Intents preserved | `COMPLETED` | `DEFINITION`, `STRUCTURE`, `SIZING`, `TRENDS` and `DRIVERS` unchanged and still registered; no intent added, including none for sizing, CAGR or methodology |
| Protected components unchanged | `COMPLETED` | `compatibility.py` `35a89e32f6fad71bc7c21abe9dbe4915`, `quantity.py` `a43581d8ff7a29b92f5d200fb03818e1`, `research/scout.py` `fe2c4fac1736abea4aaf3c997fdd2b6e` — identical to the R.9 baseline. `BIQ-REC/1` unchanged |
| Test matrix | `COMPLETED` | **162 tests**, `tests/unit/test_m10_2r13_industry_research_footing.py` |
| Existing tests | `COMPLETED` | 182 Industry Research tests pass unmodified; 552 other research-skill tests pass unmodified; total **3,885**, 0 failures, 0 errors, 19 skipped |
| Strict validation | `COMPLETED` | `claude plugin validate . --strict` passed |

**The "still unmigrated" guard has been replaced, not dropped.** R.11 asserted that competitor
and industry research named no footing symbols; R.12 narrowed it to industry research; R.13
migrates that skill, so no unmigrated research skill remains and there is no absence left to
assert. An absence was only ever a proxy for the real invariant — **one mechanism, however
many callers** — and that is now asserted directly in three complementary places: R.11's module
checks that no skill declares a footing helper of its own and that `source_footings` is defined
once; R.12's checks that the one seam serves every external origin and privileges none; R.13's
`OneMechanismAcrossFourSkills` checks that all four skills name the shared seam, require the
strict set, and that `footed_statement` and `source_footings` each have exactly one definition
in the whole engine. Each is strictly stronger than the absence check it replaces. Nothing
unrelated in either older module was touched.

**Containment is still not meaning.** A footing quoting the release's *title* to claim a
measurement basis is admissible — the text really is in the source. The guidance prohibits it
("never from the word *size*"), no code can catch it, and the test says so honestly: admitted,
recorded against the text it rests on, then `incompatible` on `scope` against a release that
stated its basis.

**All four research skills are now migrated.** `biq-company-analysis`, `biq-market-analysis`,
`biq-competitor-analysis` and `biq-industry-research` share one seam, one authoring helper and
one resolution.

**M10.2-R remains `PARTIALLY VERIFIED`.** This milestone is deterministic and synthetic. It
says nothing about live runtime behaviour, and R-12 remains open and untouched.

### M10.2-R.14 — the local join: internal analysis reaches strict synthesis · `COMPLETED`

R.10–R.13 made the **external** half user-reachable. This closes the other half: ADR-0009's
default capability — fetch the public benchmark, compute the comparison locally — could not
be delivered, because `from_analysis_set()` and `from_kpi_result()` had **no production
caller** and no surface spanned both domains.

> **Every fixture is synthetic.** The internal side is the repository's own
> `assets/demo-data/northwind_sales.csv` (generated synthetic data, never real business
> data); the external side is an invented sentence on `sector-statistics.example.invalid`, a
> reserved host that can never resolve. No live research was performed.

| Task | Status | Evidence |
|---|---|---|
| Gap confirmed by inspection | `COMPLETED` | `from_analysis_set`/`from_kpi_result` referenced only in `merge.py`, `synthesis/__init__.py`, ADRs, dev records, fixtures and tests. `commands/runner.py`, `pipeline.py` and `render/` contain no reference to synthesis |
| Existing translators reused | `COMPLETED` | Both called, neither reimplemented. A test asserts the seam contains no `def from_analysis_set`, `def from_kpi_result`, `def footed_statement`, `def source_footings` or `def compare_values` |
| The seam | `COMPLETED` | `commands.local_join()` in `lib/python/biq/commands/joins.py` — five functions, sequencing only. ADR-0029 |
| Layering | `COMPLETED` | Placed in orchestration because it needs a `CommandResult`; `synthesis/` may not depend upward (CLAUDE.md §2.3). A test asserts no synthesis module mentions `commands`, `CommandResult` or `local_join` |
| Privacy is structural | `COMPLETED` | The seam imports no gate, query builder or retrieval request; a source scan over the **code** (docstrings stripped) asserts the absence of `gate_mod`, `open_retrieval`, `public_terms`, `CandidateQuery`, `RetrievalRequest`, `ScoutBrief`, `query_text`, `urllib`, `socket`. It receives an already-closed retrieval, so the join is strictly after retrieval |
| Internal value stays local | `COMPLETED` | A sentinel taken from the **real** run (`3467850.16`) is absent from the query text, the scout brief, the ledger entry, the retrieval brief, the evidence content and the serialised evidence set — as are its rounded, banded, truncated and comma-formatted forms, and every row-level demo token |
| Domain-agnostic | `COMPLETED` | A test fails on `company`, `market`, `competitor`, `industry`, any `ORIGIN_*`, or any metric name appearing in the seam's code |
| User-reachable surface | `COMPLETED` | `/benchmark-comparison` + `biq-benchmark-comparison`. Extending a research command would break its test-pinned *"reads no business file"*; extending an analytics command would break *"no external research"* — recorded in ADR-0029 as why a new surface was correct |
| Full production path | `COMPLETED` | `C.run("profitability-analysis", source=<demo>)` → genuine `CommandResult`/`AnalysisSet` → `from_analysis_set` → strict set; `BIQ-REC/1` → `close_retrieval_object` → `footed_statement` → same set; `compare_values` → **compatible · 7 matched · 0 mismatched · 0 unknown · may_combine true · converted false** |
| Values never combined | `COMPLETED` | Internal `3467850.16` and external `3470000` both present and unchanged; no midpoint, sum, ratio or difference appears anywhere in the serialised set |
| KPI path | `COMPLETED` | `from_kpi_result` reaches the same comparison; the KPI value is the engine's and is not recomputed; an **unavailable** KPI is a limitation, not a zero |
| Additive translator change | `COMPLETED` | `from_kpi_result()` gained `metric_definition`, `geography`, `scope`, `methodology` — mirroring `from_analysis_set()`, all defaulting to `None`. M10.1's 126 synthesis tests pass unmodified |
| Provenance independence | `COMPLETED` | Internal stays `CALCULATION`/internal/class 4/engine-footed/no dimension provenance; external stays `SOURCED`/external/class 3/untrusted with 7 footings; comparing transfers neither trust nor class, and the external side's support and confidence are identical to the same statement made alone |
| Internal footing unchanged | `COMPLETED` | ADR-0023 still refuses an internal `CALCULATION` citing only external evidence; a missing `dataset_id`, a forged/subclassed/halted `CommandResult`, a non-`AnalysisSet` entry and an external origin on the internal side are each refused |
| External half unchanged | `COMPLETED` | All seven missing-dimension controls, six-of-seven, each dimension's mismatch, bare `$`, currency name, random token, conflicting context, document/operation/applicability mismatch, serialised and lookalike evidence, blocked/insufficient/unauthorised/zero-record retrievals, non-strict set — all fail closed |
| No fallback disclosure | `COMPLETED` | A failed, blocked, insufficient or unauthorised retrieval raises rather than joining, and the sentinel appears in none of those results |
| Neutrality | `COMPLETED` | No ranking, score, grade or verdict; `recommendations` empty; prompt injection telling the page to rate the business changes nothing |
| Command-level test | `COMPLETED` | Starts at the real runner and a real `BIQ-REC/1` reply — no hand-assembled `AnalysisSet` — reaching compatible, serialising against the schema, and failing closed with `INCOMPARABLE` plus lowered confidence when a dimension is dropped |
| Determinism | `COMPLETED` | The same internal run and retrieval fixture produce byte-identical normalised output on repeat |
| ADR | `COMPLETED` | **ADR-0029** — new, next free number. ADR-0026/0027/0028 untouched |
| Protected components unchanged | `COMPLETED` | `compatibility.py` `35a89e32f6fad71bc7c21abe9dbe4915`, `quantity.py` `a43581d8ff7a29b92f5d200fb03818e1`, `research/scout.py` `fe2c4fac1736abea4aaf3c997fdd2b6e` — identical to the R.9 baseline. `BIQ-REC/1`, DimensionProvenance and retrieval contracts untouched |
| Test matrix | `COMPLETED` | **105 tests**, `tests/unit/test_m10_2r14_local_join.py` |
| Existing tests | `COMPLETED` | Total **3,990**, 0 failures, 0 errors, 19 skipped. Two declaration sets in `test_command_registry.py` extended for the new surface — the same "statement about what has been built" change M9-D.1/D.2/D.3/D.5 each made |
| Strict validation | `COMPLETED` | `claude plugin validate . --strict` passed |

**Two limitations were found by wiring the real path, and both are recorded rather than
fixed.**

1. **A percentage metric cannot reach `compatible`.** `currency` is meaningless for a margin,
   so it is unstated on both sides, and `compare()` treats unstated as `unknown` — never as a
   match. Architecture.md's own headline example, *"our gross margin is 35% — typical?"*,
   therefore returns `unknown` on `currency` today. Closing it means changing compatibility
   semantics, a protected component. The skill states the limitation and forbids supplying a
   currency to make the unknown disappear.
2. **The disclosure gate refuses terms by key name.** It refuses `rows`, `customers`,
   `transactions` and `ledger`, but a caller labelling an internal figure `our_revenue` is
   authorised and the value reaches the query text. This is a pre-existing M9-A property that
   the local join neither introduces nor can fix — the seam builds no query at all. Today's
   controls are the seam's structural inability to transmit and the skill's and command's
   explicit prohibitions, both asserted by test. Strengthening the gate is its own milestone.

**M10.2-R remains `PARTIALLY VERIFIED`.** This milestone is deterministic and synthetic. It
says nothing about live runtime behaviour, and R-12 remains open and untouched.

### M10.3.1 — SWOT, the first consumer of the synthesis representation · `COMPLETED`

`biq-swot` + `/swot-analysis`: the first capability that **reads** the strict synthesis set
R.10–R.14 made reachable. A SWOT point is a placement of one statement already in the set —
never new text — so unsupported claims and advice have no field to occupy. ADR-0030.

> **Every fixture is synthetic.** Internal: `assets/demo-data/northwind_sales.csv`. External:
> invented sentences on `.example.invalid` hosts. No live research was performed.

| Task | Status | Evidence |
|---|---|---|
| Roadmap basis verified by inspection | `COMPLETED` | No SWOT code, skill or command existed; `architecture.md` §4 requires the three tags; `contract.py` already separates `FACT`/`CALCULATION` (internal), `SOURCED` (external), `INTERPRETATION`; `merge.interpretation()` requires supports; `RECOMMENDATION` refused |
| Consumer module | `COMPLETED` | `lib/python/biq/swot.py` — `build()`, `candidates()`, `render()`, `to_json()`. Imports only the synthesis package (asserted) |
| Genuine strict input | `COMPLETED` | `type(...) is SynthesisSet`, `require_dimension_provenance=True`, non-empty, every item graded by `add()`; dict, JSON, `load()` output, subclass, look-alike, non-strict, empty and ungraded sets refused |
| Point = placement | `COMPLETED` | `{quadrant, tag, synthesis_id}` only; text, score, rank, priority, weight, severity, attractiveness and recommendation fields refused |
| Tags derived from kinds | `COMPLETED` | `FACT`/`CALCULATION` → data-supported · `SOURCED` → externally-sourced · `INTERPRETATION` → analytical-inference. Every mislabel refused, never corrected; `ASSUMPTION`/`RECOMMENDATION` have no tag |
| Side grounding | `COMPLETED` | Internal statements in S/W, external in O/T, inferences on any side one evidential support is on — mixed support allowed, absent support refused |
| Inference supports verified | `COMPLETED` | Read via additive `merge.interpretation_supports()`; missing, later, circular, duplicated-note, assumption-backed and provenance-mismatched (forged) supports refused |
| Unsupported statements excluded | `COMPLETED` | `unsupported`/`insufficient_evidence` refused; `partially_supported` placed with lowered confidence carried |
| Empty quadrants | `COMPLETED` | Explicit *"No supported point identified."*; schema rejects a padded empty state; unplaced material statements listed |
| Conflicts, limitations, confidence, materiality | `COMPLETED` | Carried whole from the set, never filtered: declared external conflict (LOW, `unresolved_conflict`), compatibility limitation (`incomparable_values`, internal/external conflict), data-quality warning, unresolved dimension with reason, `undetermined` materiality unchanged, material verdict unchanged, caveats |
| No recommendation / ranking / score | `COMPLETED` | Closed output schema at every level; no forbidden key at any depth; every point text is a set statement; advisory readings refused by the existing guard; order is set order |
| Business Context | `COMPLETED` | Frames `subject`/`business_model`/`currency` only; cannot be placed; absent from provenance; private business name absent from the query |
| Privacy | `COMPLETED` | Consumer imports no gate, retrieval, scout, network, file or command code; internal figure absent from the research brief |
| Output schema | `COMPLETED` | New isolated `lib/schemas/swot.schema.json`; `synthesis.schema.json` untouched |
| Skill + command | `COMPLETED` | `skills/biq-swot/SKILL.md`, `commands/swot-analysis.md` (thin; reuses `commands.run`, `internal_statements`, the research skills, `footed_statement`/`sourced_statement`, `local_join`) |
| Registry declarations | `COMPLETED` | `test_command_registry.py`: new `SYNTHESIS_COMMANDS = ("swot-analysis",)`; `UNBUILT_SYNTHESIS_COMMANDS` now `strategy-analysis`, `decision-support`, `executive-report` (placeholder `swot` removed, `executive-report` added) |
| ADR | `COMPLETED` | **ADR-0030** — ADR-0022 had left consumer use undecided. No accepted ADR edited |
| Protected components unchanged | `COMPLETED` | `compatibility.py`, `quantity.py`, `research/scout.py`, `dimension_provenance.py`, `research_footing.py`, `commands/joins.py`, `evidence_set.py`, `synthesis.schema.json` byte-identical (md5 in the development record) |
| Focused tests | `COMPLETED` | **117 tests**, `tests/unit/test_m10_3_1_swot.py`; five guards mutation-checked |
| Full suite + strict validation | `COMPLETED` | **4,108 tests, 0 failures, 0 errors, 19 skipped** (3,990 baseline + 117 focused + 1 registry); `claude plugin validate . --strict` passed |

**Not done, deliberately:** strategy recommendations, decision support, executive reporting,
live research, any change to compatibility semantics, BIQ-REC/1, DimensionProvenance or the
synthesis schema. See `docs/development/2026-09-16-m10-3-1-swot.md`.

### M10.3.2-A — Strategy recommendation contract · `COMPLETED (DECISION ONLY)`

Decision-only milestone. **No production code, test, schema, skill or command was changed, and
nothing here is implemented.** Resolved the contradictions a readiness review found between
ADR-0022 §5, `synthesis.schema.json`, `evidence.Claim`, synthesis confidence and the two
reference documents. **ADR-0031.**

| Contract element | Status | Decision |
|---|---|---|
| Container | `COMPLETED` | A `StrategyResult` **beside** one genuine strict `SynthesisSet`, never inside it. Synthesis `recommendations` stays a permanent empty marker; `synthesis.schema.json` keeps `maxItems: 0`. Refines ADR-0022 §5's location sentence; ADR-0022 text unedited |
| Carrier | `COMPLETED` | Class-7 record whose ledger form is `evidence.Claim(RECOMMENDATION)`; the six-field rule stays owned by `Claim` |
| Evidence linkage | `COMPLETED` | Synthesis statement ids resolved in one set; `FACT`/`CALCULATION`/`SOURCED` or verified `INTERPRETATION`; at least one class 1/3/4 basis; `unsupported`/`insufficient_evidence` refused; recommendations never cite recommendations |
| Assumptions | `COMPLETED` | Only as a dependency's `assumption_id`; never evidence, never sole basis |
| Fields and types | `COMPLETED` | `action`, `evidence` (ids), `rationale`, `expected_benefit`, `risks` (list), `dependencies` (list of `{text, assumption_id}`), `confidence` (derived); plural names, no aliases, none empty. Reference documents reconciled |
| Expected benefit | `COMPLETED` | Qualitative, or restating a figure already in a cited statement; no estimated-value field |
| Confidence | `COMPLETED` | Derived with the existing `confidence.combine()` over cited statements' and assumptions' reason codes; never authored, never raised or lowered by the layer |
| Partial / contested / incomparable | `COMPLETED` | Allowed and carried; conflicts force `LOW` through existing severe codes; disqualifying support states refused; no conflict ever presented as settled |
| Advisory guard | `COMPLETED` | Unchanged; recommendation text never becomes a `SynthesisItem` |
| Re-entry path | `COMPLETED` (found) | `SynthesisSet.register_claims()` currently accepts a serialised recommendation as a candidate claim. Latent (no class-7 producer); M10.3.2 must add an additive refusal |
| Decision owner | `COMPLETED` | No personal field; `issued_by` names the issuing capability; the business decision is the user's (step 19) |
| Order / priority / scoring | `COMPLETED` | Multiple allowed; deterministic meaning-free order; no priority, rank, score or weight |
| Materiality, limitations, Business Context | `COMPLETED` | Inherited unchanged; carried whole; Business Context is framing, never evidence |
| Action boundary | `COMPLETED` | Confirmed unchanged: generation is read-only; BusinessIQ never executes a recommendation |
| SWOT / Decision Support / Executive Report | `COMPLETED` | No SWOT dependency; Decision Support shares the record contract; Executive Report may assemble, never author or re-grade |
| Regression + validation | `COMPLETED` | **4,108 tests, 0 failures, 0 errors, 19 skipped** — identical to the M10.3.1 baseline; `claude plugin validate . --strict` passed |

**Deliberately unresolved:** Decision Support's "12-part framework" (named in `architecture.md`
§4, defined nowhere in the repository); any prioritisation policy; ADR-0022's status-line
annotation (left for the owner, since this milestone edited no accepted ADR). Left to M10.3.2
within the contract: numeric-token recognition for the figure rule, the single home for the
ADR-0030 grounding checks, and the command's input syntax. See
`docs/development/2026-09-16-m10-3-2-a-strategy-recommendation-contract.md`.

### M10.3.2 — Strategy Recommendations implementation · `COMPLETED`

`biq-strategy-recommendations` + `/strategy-analysis`, implementing ADR-0031 exactly. No new ADR;
ADR-0031 and every accepted ADR untouched.

> **Every fixture is synthetic.** Internal: `assets/demo-data/northwind_sales.csv`. External:
> invented sentences on `.example.invalid` hosts. No live research was performed.

| Task | Status | Evidence |
|---|---|---|
| Strategy engine | `COMPLETED` | `lib/python/biq/strategy.py` — `build()`, `candidates()`, `render()`, `figure_tokens()`, `require_grounded()`. Reads no file, runs no analysis, retrieves nothing, never modifies the set (asserted by code scan and by byte-identical set serialisation) |
| `StrategyResult` beside the set | `COMPLETED` | Built only by `build()` (module-private token); holds the set object and a SHA-256 digest; `claims()`/`as_dict()` refuse after the set changes; returned records are copies |
| Six authored fields | `COMPLETED` | Exactly `action`, `evidence`, `rationale`, `expected_benefit`, `risks`, `dependencies`; confidence, support, trust, verification, tier, priority, score, rank, weight, aliases and every other field refused; none may be empty |
| Evidence resolution | `COMPLETED` | Ids resolved in one genuine strict set; fake, out-of-set, ambiguous, duplicated, statement-text, recommendation and SWOT ids refused; assumptions refused as evidence; unsupported and insufficient evidence refused; at least one class 1/3/4 basis |
| Single grounding home | `COMPLETED` | ADR-0030 checks moved from `swot.py` to `lib/python/biq/synthesis/grounding.py`; SWOT and Strategy both call it; SWOT's 117 tests pass unchanged; a scan asserts one definition of each check and that only `grounding.py` reads the supports note |
| Re-entry closed | `COMPLETED` | `SynthesisSet.register_claims()` refuses recommendation records in every spelling tested (class, label, kind, finding type, recommendation-only fields); genuine candidate claims still accepted |
| Class-7 `Claim` shape | `COMPLETED` | `evidence.Claim` refuses placeholder or mis-shaped class-7 fields, text `based_on` and extra fields; the id pattern is pinned to `synthesis_id()` by test |
| Claim-ledger schema | `COMPLETED` | Class-7 branch added as an `anyOf` the in-repo validator enforces; aliases, extra fields and empty values rejected |
| Strategy schema | `COMPLETED` | New closed `lib/schemas/strategy.schema.json`; no priority, score, rank, weight, winner, estimated value or execution status; `synthesis.schema.json` unchanged |
| Figure rule | `COMPLETED` | Dates, figures and identifiers tokenised as distinct classes; exact `Decimal` values (`3500` = `3,500` = `3.5k`), no rounding; percent, percentage points and currency must match; ambiguous currencies refused; only cited statements ground a figure; fails closed |
| Confidence | `COMPLETED` | `confidence.combine()` over cited statements' and assumptions' existing reason codes; no new level or code; authored confidence refused whether higher or lower |
| Conflicts, partial, incomparable, unresolved | `COMPLETED` | Allowed and carried; conflicts force `LOW` with the full record; `incomparable_values` and unresolved dimensions carried per evidence statement |
| Materiality, limitations, Business Context | `COMPLETED` | Inherited, never re-judged; limitations and caveats carried; context frames only and cannot be cited or introduce a figure |
| Skill + command | `COMPLETED` | `skills/biq-strategy-recommendations/SKILL.md`, `commands/strategy-analysis.md` (thin; no SWOT required; reuses the existing internal, research and local-join paths) |
| Registry and absence guards | `COMPLETED` | `strategy-analysis` built; `decision-support` and `executive-report` still guarded in `test_command_registry.py`, `test_m10_3_1_swot.py` and `test_m9d5_industry_research_command.py` |
| Stale wording | `COMPLETED` | Three skills that said `biq-strategy-recommendations` "is not built" corrected; no other change to them |
| Focused tests | `COMPLETED` | **123 tests**, `tests/unit/test_m10_3_2_strategy.py`; seven guards mutation-checked |
| Full suite + strict validation | `COMPLETED` | **4,232 tests, 0 failures, 0 errors, 19 skipped** (4,108 baseline + 123 focused + 1 new `test_engine_m2` test); `claude plugin validate . --strict` passed |

See `docs/development/2026-09-16-m10-3-2-strategy-recommendations.md`.

### M10.3.3-A — Decision Support contract · `COMPLETED (DECISION ONLY)`

Decision-only milestone. **No production code, test, schema, skill or command was changed, and
nothing here is implemented.** The M10.3.3 readiness review found "the 12-part framework" named in
`architecture.md` §4 and defined nowhere — the same uncommitted-specification gap as D-01/D-02/D-06.
The owner supplied a twelve-part working framework; this milestone reconciled it against the
approved contracts and recorded it. **ADR-0032.** No accepted ADR edited; ADR-0031 unchanged.

| Contract element | Status | Decision |
|---|---|---|
| Framework | `COMPLETED` | Twelve parts: `decision_question`, `business_context`, `objective`, `options`, `criteria`, `evidence`, `assumptions`, `tradeoffs`, `risks`, `expected_outcomes`, `guidance`, `uncertainty`. Five terms fixed so none weakens an existing rule (context, objective, criteria, guidance, next steps) |
| Container | `COMPLETED` | A `DecisionResult` beside one genuine strict `SynthesisSet`, never inside it |
| Inputs | `COMPLETED` | Set required; decision question required and user-supplied; objective, options, constraints and criteria optional and user-supplied; `StrategyResult` optional and bound to the same set; SWOT not an input; Business Context framing only |
| Options | `COMPLETED` | At least two: user-supplied, one per class-7 record, and the status quo. No option generator — a model-proposed option is an ADR-0031 record |
| Criteria | `COMPLETED` | User-supplied or a configured materiality threshold on request; numeric thresholds need a stated origin; no weights, scores or ranks |
| Evidence | `COMPLETED` | Synthesis statement ids through `synthesis/grounding.py`, ADR-0031 eligibility; at least one per package; records never support tradeoffs, risks or outcomes |
| Assumptions, tradeoffs, risks, outcomes | `COMPLETED` | Assumptions never evidence; tradeoffs and outcomes need evidence; risks may be unevidenced but are labelled and `LOW`; ADR-0031 figure rule on every authored text |
| Recommendations | `COMPLETED` | One contract (ADR-0031): Strategy records packaged unchanged, Decision Support records issued as `biq-decision-support`; divergences shown, never settled |
| Preferred option | `COMPLETED` | Only with criteria, a grounded class-7 record, every other option assessed against the same criteria or labelled not assessable, and a named basis; otherwise none and a reason |
| Confidence | `COMPLETED` | `confidence.combine()` everywhere with existing codes; an unassessed option is `LOW` / `insufficient_evidence`; nothing authored |
| Materiality | `COMPLETED` | Inherited, never re-judged; materiality ordering is labelled presentation |
| Scoring | `COMPLETED` | Prohibited: scores, weights, ranks, priorities, severity, likelihood, matrices, "best" claims, preference ordering |
| Human boundary | `COMPLETED` | Unchanged: draft analysis, no execution; next steps are evidence gaps, not actions |
| Verifier lifecycle | `COMPLETED` | `lifecycle` is `draft` or `final`; M10.3.3 produces only drafts; "finalise" means the M11 verifier moving a draft to final. The M10/M11 dependency is no longer circular |
| Executive Report | `COMPLETED` | May assemble packages, draft or final with lifecycle shown; never re-authors or re-grades |
| Regression + validation | `COMPLETED` | **4,232 tests, 0 failures, 0 errors, 19 skipped** — identical to the M10.3.2 baseline; `claude plugin validate . --strict` passed |

**Deliberately unresolved:** how the M11 verifier records its findings (M11); whether Executive
Report requires final packages (its own milestone); any prioritisation policy. Left to M10.3.3
within the contract: id spellings, the status-quo label and how a user excludes it. See
`docs/development/2026-09-16-m10-3-3-a-decision-support-contract.md`.

### M10.3.3 — Decision Support · `COMPLETED`

`biq-decision-support` + `/decision-support`, implementing ADR-0032 as accepted. **No new ADR; no
accepted ADR edited.** Produces draft packages only; does not wait for M11.

> **Every fixture is synthetic.** Internal: `assets/demo-data/northwind_sales.csv`. External:
> invented sentences on `.example.invalid` hosts. No live research was performed.

| Task | Status | Evidence |
|---|---|---|
| Decision Support engine | `COMPLETED` | `lib/python/biq/decision_support.py` — `build()`, `render()`, `DecisionResult`. Reads no file, runs no analysis, retrieves nothing, never modifies the set (code scan and byte-identical set serialisation) |
| Twelve parts | `COMPLETED` | `body` holds the ADR-0032 parts in contract order with the ADR's shapes; asserted on the structure and on the serialised key order |
| Closed request | `COMPLETED` | Required decision question — refused only when missing, non-text or blank, otherwise kept verbatim; optional objective, constraints, options, status-quo exclusion, criteria, materiality criteria, recommendations, tradeoffs, risks, outcomes, not-assessable labels, preference, divergences, next steps. Every other field — confidence, lifecycle, trust, score, rank, weight, priority, severity, likelihood — refused at every level |
| Shared record contract | `COMPLETED` | `strategy.ground_recommendation()`, `cite()`, `statement_detail()`, `synthesis_digest()` exposed additively; records issued as `biq-decision-support`; Strategy records packaged unchanged; Strategy behaviour, tests and schema unchanged |
| Options, criteria, preference | `COMPLETED` | User → record → status quo; at least two; duplicate labels refused. Criteria user-supplied or a configured threshold with its layer. Preferred option only under ADR-0032 §10's four conditions, checked over the named basis as a whole (no tradeoff required per criterion), otherwise `null` with one of six fixed reasons |
| Evidence and assumptions | `COMPLETED` | Fake, malformed, out-of-set, ambiguous and duplicate ids refused; recommendations, assumptions, source metadata and Business Context never evidence; the evidence part indexes exactly what is cited, in set order |
| Figure rule | `COMPLETED` | ADR-0031 rule on tradeoffs, risks, outcomes, not-assessable reasons, next steps and divergence notes. Extended in `strategy.figure_tokens()` to cardinal number phrases matched as whole phrases, so "five percent" is refused for both consumers and "twenty-one" is never grounded by "twenty-three"; re-signed, rounded and non-ASCII figures refused |
| Confidence and uncertainty | `COMPLETED` | `confidence.combine()` for tradeoffs, risks, outcomes, options and the package; unevidenced risk and unassessed option `LOW` / `insufficient_evidence`; assumption-dependent tradeoff `LOW`; conflicts, limitations and unresolved dimensions carried; next steps must address one the package carries |
| Lifecycle | `COMPLETED` | Always `draft` and `unverified`; no path to `final` |
| Re-entry closed | `COMPLETED` | `register_claims()` refuses the package and each part, and any record carrying package-only fields or framing origins; genuine candidate claims still accepted |
| Schema | `COMPLETED` | New closed `lib/schemas/decision_support.schema.json` with a closed `request` definition; mirrored record definitions pinned to `strategy.schema.json` by test |
| Skill + command | `COMPLETED` | `skills/biq-decision-support/SKILL.md`, `commands/decision-support.md` (thin; reuses the existing internal, research and local-join paths; neither SWOT nor Strategy required) |
| Registry and absence guards | `COMPLETED` | `decision-support` built; `executive-report` still guarded in `test_command_registry.py`, `test_m10_3_1_swot.py`, `test_m10_3_2_strategy.py` and `test_m9d5_industry_research_command.py` |
| Contract-alignment remediation | `COMPLETED` | Preferred-option check no longer requires a tradeoff per named criterion; the question is no longer refused for containing several question marks; number words matched as whole phrases. ADR-0032 unchanged |
| Focused tests | `COMPLETED` | **103 tests**, `tests/unit/test_m10_3_3_decision_support.py` |
| Full suite + strict validation | `COMPLETED` | **4,335 tests, 0 failures, 0 errors, 19 skipped** (4,232 baseline + 103 focused); `claude plugin validate . --strict` passed |

See `docs/development/2026-09-16-m10-3-3-decision-support.md` and
`docs/development/2026-09-16-m10-3-3-contract-alignment-remediation.md`.

### M10.3.4 — Executive Report contract · `COMPLETED (DECISION ONLY)`

Contract and architecture review. **No production code, test, schema, skill, command, manifest or
connector was changed, and Executive Report is not implemented.** Before this review the plan said only
"`biq-executive-report` + `/executive-report`. Reads the M10.1 representation and may assemble
`StrategyResult`s and `DecisionResult`s"; `architecture.md` §4 said "assembles; performs no fresh
analysis". **ADR-0033.** No accepted ADR edited.

| Contract element | Status | Decision |
|---|---|---|
| Purpose | `COMPLETED` | Assembles existing artifacts over one synthesis set; authors no analysis, recommendation or summary prose; not a synthesis, research, forecasting, anomaly, scoring or execution engine |
| Inputs | `COMPLETED` | Required: one genuine strict non-`CRITICAL` set and a closed framing request. Optional: one `StrategyResult` and zero or more `DecisionResult`s bound to that set object; one SWOT record its placements rebuild exactly. Upstream engine objects only through the set (ADR-0022) |
| Sections | `COMPLETED` | Eleven, fixed order, always present with stated empty states: frame, summary, KPI scorecard, findings, anomalies, outlook, SWOT, strategy, decision support, evidence and uncertainty, decisions for the reader. Going-well/needs-attention, standalone risks/opportunities, scores, ratings, targets prohibited |
| Executive summary | `COMPLETED` | Selection by rule: every material evidential statement or verified interpretation verbatim; unsupported material ids; records by id; package questions and preferences; set confidence |
| KPI scorecard | `COMPLETED` | Registered `KPIResult`s in catalogue order; statement confidence and materiality; change only from the statement itself; no targets (no engine consumes them) |
| Forecasts and anomalies | `COMPLETED` | Anomalies through the set with the investigation note, no cause. Outlook admits only forecast-footed statements — none can be produced today, so `not_available` until a synthesis forecast translator is separately approved |
| Strategy, Decision Support, SWOT | `COMPLETED` | Each shown whole and unchanged in its own order; packages in supplied order with lifecycle shown; draft packages labelled unverified |
| Recommendations | `COMPLETED` | Executive Report issues none; records referenced only |
| Confidence, materiality | `COMPLETED` | Carried per statement, record and part; set confidence labelled as the set's; no report-level confidence or score; nothing re-judged |
| Lifecycle and M11 | `COMPLETED` | Draft only before M11; verified is the verifier's act, final the resulting lifecycle; a final report may not contain a draft package; how verification is recorded stays M11's |
| Binding and re-entry | `COMPLETED` | Built only by `build()`; bound to the set digest and each component; content-addressed `report_id`; `register_claims()` refusal to be extended |
| Human boundary, research | `COMPLETED` | Draft generation, no approval; no execution, sending, system writes or decision claims; the engine never retrieves, the command sequences existing paths |
| Regression + validation | `COMPLETED` | **4,335 tests, 0 failures, 0 errors, 19 skipped** — identical to the M10.3.3 baseline; `claude plugin validate . --strict` passed |

**Deliberately unresolved:** a synthesis forecast translator and its grading rule (separate decision);
KPI targets (until an engine computes variance); how M11 records verification. See
`docs/development/2026-09-16-m10-3-4-executive-report-contract.md`.

### Executive Report implementation · `COMPLETED`

`biq-executive-report` + `/executive-report`, implementing ADR-0033 as accepted. **No new ADR; no accepted
ADR edited.** Produces draft reports only; does not wait for M11.

> **Every fixture is synthetic.** Internal: `assets/demo-data/northwind_sales.csv`. External: invented
> sentences on `.example.invalid` hosts. No live research was performed.

| Task | Status | Evidence |
|---|---|---|
| Report engine | `COMPLETED` | `lib/python/biq/executive_report.py` — `build()`, `render()`, `ExecutiveReportResult`. Reads no file, runs no analysis, imports no KPI, anomaly or forecast engine, retrieves nothing, never modifies the set (code scan and byte-identical set serialisation) |
| Inputs | `COMPLETED` | Required: genuine strict non-empty set, not `CRITICAL`; closed framing request (`reporting_period`, `audience`, `objective`, `questions`, `constraints`). Optional: one bound `StrategyResult`, any number of bound, distinct `DecisionResult`s, one SWOT record its placements rebuild exactly. No parameter exists for any upstream engine object |
| Eleven sections | `COMPLETED` | Fixed order, always present; statuses `included`, `empty`, `not_supplied`, `not_available` with fixed reasons |
| Executive summary | `COMPLETED` | Selection by rule: readable material statements in set order, unsupported material ids, count with no verdict, records by id, package questions and preference, set confidence, availability of sections 3 and 5–9 |
| KPI scorecard, findings, anomalies | `COMPLETED` | Registered KPIs in catalogue order with status, value and statement confidence; no targets or ratings. Findings in set order, evidence then interpretations. Anomalies with the engine's investigation note and resolved finding (metric, period, observed, baseline, deviation) |
| Outlook | `COMPLETED` | Always `not_available`: no forecast translator; a forecast-footed assumption is shown only as an assumption |
| SWOT, Strategy, Decision Support | `COMPLETED` | Each shown whole and unchanged in its own order; packages in supplied order labelled `draft — unverified`; a package bound to a different `StrategyResult` refused |
| Evidence and uncertainty, decisions for the reader | `COMPLETED` | Set and component confidence labelled by owner; conflicts, limitations, assumptions, unsupported statements with reasons. Human-decision statement; open questions; recommendation ids; package next steps by reference |
| Binding and identity | `COMPLETED` | Bound to the set digest and each component's digest; serialisation refused after any change, including tampering; content-addressed `report_id` |
| Lifecycle, recommendations | `COMPLETED` | Draft only; no path to `final`; issues no recommendation (not in `RECOMMENDATION_ISSUERS`) |
| Re-entry closed | `COMPLETED` | `register_claims()` refuses the report, each section and each report entry; genuine candidate claims still accepted |
| Additive seams | `COMPLETED` | `SynthesisSet.registered_kpis()`, `registered_datasets()`, `registered_evidence_sets()`; `DecisionResult.strategy_result` |
| Schema | `COMPLETED` | New closed `lib/schemas/executive_report.schema.json`; Strategy, SWOT and Decision Support definitions imported and pinned by test |
| Skill + command | `COMPLETED` | `skills/biq-executive-report/SKILL.md`, `commands/executive-report.md` (thin; sequences the existing internal, anomaly, research, SWOT, Strategy and Decision Support paths over one set) |
| Registry and absence guards | `COMPLETED` | `executive-report` built; `UNBUILT_SYNTHESIS_COMMANDS` now empty with all four synthesis commands asserted present; guards in the SWOT, Strategy, Decision Support and M9-D.5 suites amended |
| Focused tests | `COMPLETED` | **73 tests**, `tests/unit/test_m10_3_4_executive_report.py` |
| Full suite + strict validation | `COMPLETED` | **4,408 tests, 0 failures, 0 errors, 19 skipped** (4,335 baseline + 73 focused); `claude plugin validate . --strict` passed |

**Deliberately not done:** a synthesis forecast translator (separate decision), KPI targets, the M11
verifier and any `final` report. See `docs/development/2026-09-17-m10-3-4-executive-report.md`.

## Milestone 11 — Subagents (remaining two) · `COMPLETED`

`biq-data-profiler` and `biq-analysis-verifier`, listed explicitly in `plugin.json`, each
with a minimal tool grant (ADR-0014 keeps both here).

**Status.** The **verification and finalisation** work is `COMPLETED`: the M11-A contract (ADR-0034,
ADR-0035) and its implementation — the deterministic verifier, the local `biq-verifier` MCP server, the
single-tool `biq-analysis-verifier` agent and the `draft` → `final` lifecycle — built and passing its
required tests, including the runtime agent-boundary test. **`biq-data-profiler`**, the other capability
this milestone has always held, is `COMPLETED` as ADR-0036 defines it: the deterministic data profile
(`data_profile.py`, `profile.schema.json`, the `biq-data-ingestion` skill for local files). ADR-0036 found no
justification for a subagent over local files, so no `biq-data-profiler` agent is built; that agent stays
allocated for model-mediated connector catalogues and is Milestone 12 work under its own contract.

**`biq-research-scout` moved to M9 (ADR-0014)**, together with the test asserting it has no
file access — a security test ships with the component whose property it proves, not with a
milestone number. M11's dependency narrows accordingly: neither remaining agent depends on
M9, and the verifier's consumers (`/executive-report`, `/decision-support`) arrive in M10.

**The verifier finalises; it does not gate building (ADR-0032).** M10 components produce `draft`
results without waiting for M11, and the verifier moves a draft to `final`. So M11 depends on M10
and M10 does not depend on M11 — the dependency column is correct as written.

### M11-A — Verification and finalisation contract · `COMPLETED (DECISION ONLY)`

Contract and architecture review. **No production code, test, schema, skill, command, agent, manifest or
connector was changed; neither the verifier nor finalisation is implemented.** Before this review the
repository fixed only the outline: the verifier "independently recompute[s] headline figures, challenge[s]
conclusions" with "engine + dataset" (`architecture.md` §10, ADR-0006); it finalises draft packages and
reports by recording a verification beside an unedited draft (ADR-0032 §13, ADR-0033 §13); a final report
may not contain a draft package; how verification is recorded was left to M11. **ADR-0034.** No accepted
ADR edited.

| Contract element | Status | Decision |
|---|---|---|
| Purpose and scope | `COMPLETED` | Integrity verification and the `draft` → `final` transition for `DecisionResult` and `ExecutiveReportResult`; set, `StrategyResult` and SWOT verified as bound components, never finalised. Never judges soundness, seriousness, source truth or wisdom |
| Verifier | `COMPLETED` | Deterministic `lib/python/biq/verification.py` decides every check; no model in the core path |
| Agent | `COMPLETED` — **interface superseded by ADR-0035** | `biq-analysis-verifier` holds only the fixed local `recompute` operation (no shell, file, web or dispatch tool); receives only an opaque `request_id`; relays an allowlisted status envelope. Never sees a path, source, checked or recomputed value |
| Methods | `COMPLETED` | Source binding (identity and digest; registry agreement); reproduction by the owning engines, byte-equal, plus located textual checks; blind recomputation of every engine-footed figure and scorecard row, compared exactly through salted digests of exact strings (ADR-0035). External figures source-bound only |
| Findings | `COMPLETED` | Eleven categories, fixed check catalogue; no severity or warning tier; every finding blocks; catalogue order, never priority; no confidence or trust; `expected` is a reference and `observed` a comparison code, never a figure or text (ADR-0035) |
| `VerificationResult` | `COMPLETED` | Closed, content-addressed `verification_id`, subject digest, component digests, recomputation bases, every check with outcome, findings, fixed human-decision text; no timestamp |
| Finalisation | `COMPLETED` | `finalise()` only after a passed verification of that draft, still bound; final object holds draft and verification; only lifecycle fields change plus `verification_record`; `report_id` unchanged; re-proven at every serialisation; packages finalised before the report that includes them |
| Failure, repetition, persistence | `COMPLETED` | Non-genuine input raises; genuine failing draft returns `failed` and stays draft; no repair; idempotent; in memory only, scratchpad brief and reply transient |
| Human boundary, re-entry | `COMPLETED` | Final means verified for integrity, never approved or decided; verification artifacts and final objects refused by `register_claims()` |

**Deliberately unresolved (not needed to implement):** a persisted verification record; recomputation for
connector sources without a file (M12); any model review of reasoning quality. See
`docs/development/2026-09-17-m11-a-verification-finalisation-contract.md`.

**Contract-alignment remediation · `COMPLETED (DECISION ONLY)`.** ADR-0034's recomputation interface gave the
agent a source path, a `Bash` grant and verbatim stdout carrying recomputed values — not blind. **ADR-0035**
supersedes those clauses only: an opaque content-addressed request; one fixed plugin-local MCP operation as
the agent's entire grant; a machine-only record of salted digests, never values; an allowlisted
`biq.verifier.result/1` envelope; findings without values; and a run registration (`run_id` over command,
absolute source path, source SHA-256, run arguments, configuration digest) replacing the ambiguous
dataset-keyed basis, with cross-run re-registration refused. If the platform cannot verifiably restrict an
agent to that one tool, recomputation is `BLOCKED` rather than routed through a shell. See
`docs/development/2026-09-17-m11-a-contract-alignment-remediation.md`.

### M11 — Verification and finalisation implementation · `COMPLETED`

Implements ADR-0034 as amended by ADR-0035. **No ADR edited.** Connector gate for the local verifier
server approved by the project owner for the exact `.mcp.json` entry shipped. A synthesis forecast
translator remains a separate, unscheduled decision; `biq-data-profiler` remains `PLANNED`.

> **Every fixture is synthetic.** `assets/demo-data/northwind_sales.csv` and invented research. Runtime
> boundary tests ran real nested Claude Code sessions over a temporary project; no live research.

| Task | Status | Evidence |
|---|---|---|
| Verification engine | `COMPLETED` | `lib/python/biq/verification.py` — `issue_recomputation`, `recompute_request`, `verify`, `finalise`, `render`, `VerificationResult`, `FinalDecisionResult`, `FinalExecutiveReportResult`. 46-check catalogue in fixed order; every finding blocks; no severity, confidence, trust or timestamp |
| Blind recomputation | `COMPLETED` | Sealed content-addressed request (`rcq-`); digest-only record (`rcr-`); closed `biq.verifier.result/1`; record bound to the request `verify()` re-derives; working files consumed |
| Local MCP server | `COMPLETED` | `lib/python/biq/verification_server.py`, one tool `recompute`, closed argument, no instructions, stderr and stdout silenced; `.mcp.json` `biq-verifier` (stdio, identity only) |
| Verifier agent | `COMPLETED` | `agents/biq-analysis-verifier.md`, `tools: mcp__plugin_businessiq_biq-verifier__recompute` only |
| Run registration | `COMPLETED` | `commands.run()` source SHA-256 before/after, `run_id`, `run_arguments`, `config_digest`; `SynthesisSet` run registry in its digest; `commands.kpi_statements()`; cross-run re-registration refused with the set unchanged |
| Retained inputs, final packages | `COMPLETED` | `StrategyResult.proposals`, `DecisionResult.request`/`config`, report `request`/`config`/components; `executive_report.build()` accepts `FinalDecisionResult` |
| Schemas | `COMPLETED` | New closed `verification.schema.json` (result, findings, request, record, envelope); `decision_support` and `executive_report` admit `final` only with `verified` and `verification_record` |
| Re-entry | `COMPLETED` | `register_claims()` refuses verification results, checks, findings, final artifacts and verification-only fields |
| Orchestration | `COMPLETED` | `--final` in `/executive-report` and `/decision-support`; skills document the flow (issue, dispatch id, rebuild, verify, finalise) |
| Guards amended | `COMPLETED` | Scout test now expects the verifier agent; report schema guard proves `final` needs `verified` + record; local-join function list includes the two run-registration helpers |
| Focused tests | `COMPLETED` | **67 tests** — `test_m11_verification.py` (47), `test_m11_verification_server.py` (8), `test_m11_verifier_agent_boundary.py` (5 offline, 7 runtime opt-in) |
| Runtime agent boundary | `COMPLETED` | `BIQ_AGENT_BOUNDARY_RUNTIME=1`: **12 run, 0 failures, 0 skipped** — production relay verifies `passed` and the production transcript never carries the source name, a source row or a figure; verifier agent executes only `recompute`, never the decoy MCP tool, Bash, Read or ToolSearch; platform logs ToolSearch unavailable for it; control agent without the grant executes them |
| Full suite + strict validation | `COMPLETED` | **4,475 tests, 0 failures, 0 errors, 26 skipped (the 19 pre-existing skips plus the 7 opt-in runtime boundary tests)**; `claude plugin validate . --strict` passed (not evidence for the agent boundary) |

**Deliberately not done:** a forecast translator; `biq-data-profiler`; any persisted verification record;
any model review of reasoning quality. See `docs/development/2026-09-17-m11-verification-finalisation.md`.

### M11 — `biq-data-profiler` contract · `COMPLETED (DECISION ONLY)`

Contract and architecture review. **No production code, test, schema, skill, command, agent, manifest or
connector was changed; the profiler is not implemented.** Before this review the repository fixed only an
allocation: a subagent with file access and no web tools that scans large or multi-sheet data (ADR-0006,
`architecture.md` §10, §17). **ADR-0036.** No accepted ADR edited; ADR-0006's allocation is refined, recorded
in the decisions index.

| Contract element | Status | Decision |
|---|---|---|
| Agent | `COMPLETED` | No subagent for local files: the engine already keeps raw scan output out of every model context, so ADR-0006's own three-justification test is not met. `biq-data-profiler` stays allocated, unbuilt, for model-mediated sources too large for the main context (connector catalogues, M12) under its own future contract |
| Capability | `COMPLETED` | Deterministic `data_profile.build()` → closed, content-addressed `DataProfileResult` (`dpr-`); composition module beside `pipeline.py`, importing downward only |
| Inputs | `COMPLETED` | Closed request: 1–20 existing local files of the reader's extensions, optional sheets (hidden only when named), optional closed-id objective, presentation; resolved config and Business Context beside it. No URL, directory, caller-supplied fact or profile object |
| Facts | `COMPLETED` | `observed` (package and reader), `calculated` (exact counts over every row read: non-null, distinct with a cap, uniqueness, date coverage, key candidates, key-overlap rates), `inferred` (M3 rules reused verbatim, with sample sizes); no model-authored fact |
| Neighbours | `COMPLETED` | M3 is the only reader and inference source; M4 findings referenced by id, never re-graded; M5 status bucket only, values discarded; command registry's declared roles, no predicted outcome |
| Privacy | `COMPLETED` | No cell value except ISO currency codes and non-restricted date bounds; `restricted`/`never` columns names, kinds and counts only; `shareable` bands small counts and omits paths |
| Binding and failure | `COMPLETED` | Source SHA-256 before and after the read; stale result refuses to serialise; closed refusal, `complete` / `complete_with_limitations` / `partial` / `unavailable` with closed limitation and reason codes; no approximation |
| Re-entry | `COMPLETED` | Diagnostic metadata, not evidence; `register_claims()` refuses profiles and profile-only fields |

See `docs/development/2026-09-17-m11-data-profiler-contract.md`.

### M11 — `biq-data-profiler` implementation · `COMPLETED`

Implements ADR-0036. **No ADR edited. No agent, MCP server, command or connector added; `.mcp.json`
unchanged.** Every fixture is synthetic.

| Task | Status | Evidence |
|---|---|---|
| Profile engine | `COMPLETED` | `lib/python/biq/data_profile.py` — `build`, `validate_request`, `DataProfileResult`, `render`, `validate_document`, `DataProfileError`. Composition module beside `pipeline.py`, downward imports only; reuses `workbook.inspect`, `readers.read`, `canonical.build`, `mapping.infer`, `quality.checks.run`, `kpi.registry.calculate`, the command registry and `runner.source_sha256` / `canonical_json` |
| Closed request | `COMPLETED` | `sources` (1-20 existing local files), `sheets`, `objective` (closed ids), `presentation`; everything else refused whole, including URLs, folders, globs, duplicates, duplicate sheets, caller-supplied facts and profile objects |
| Facts | `COMPLETED` | Every fact `{value, basis, operation, examined}`; exact non-null, empty, distinct (cap 100,000, `null` above it), uniqueness, date coverage, duplicate headers, key candidates, Jaccard key overlap; inferred facts are M3's, with their samples |
| Privacy | `COMPLETED` | No cell value except ISO currency codes and non-restricted date bounds; `restricted`/`never` columns withhold role, currencies, day order and date bounds and join no overlap; `shareable` bands counts below k = 5, omits paths and hides `never` column names; reader and quality messages never carried |
| References | `COMPLETED` | Quality by check id, code, severity, grade; KPI status bucket only; command required roles with mapping status, no outcome; Business Context labelled `context` |
| Binding and failure | `COMPLETED` | SHA-256 before and after reading; `changed_during_profile`; stale result refuses `as_dict`, `to_json`, `render`; closed reason and limitation codes; `complete` / `complete_with_limitations` / `partial` / `unavailable` |
| Schema | `COMPLETED` | New closed `lib/schemas/profile.schema.json` |
| Re-entry | `COMPLETED` | `register_claims()` refuses a profile, any part of one (nested), the ADR-0036 profile-only fields plus `required_roles` and `overlap_rate`, profile ref values and profile fact shapes |
| Skill | `COMPLETED` | `skills/biq-data-ingestion/SKILL.md` (local files; connector resolution stays M12); skill count stays 20 |
| Focused tests | `COMPLETED` | **80 tests**, `tests/unit/test_m11_data_profiler.py` |
| Full suite + strict validation | `COMPLETED` | **4,555 tests, 0 failures, 0 errors, 26 skipped** (4,475 baseline + 80 focused; skips unchanged); `claude plugin validate . --strict` passed |

**Deliberately not done:** a `biq-data-profiler` agent (M12, connector catalogues); connector sources;
chunked streaming (Data Layer deferral); value statistics of figures; a synthesis forecast translator
(separate, unscheduled decision). Workbook reads were exercised at Tier 3 and Tier 4 only: openpyxl is not
installed on the build machine, so Tiers 1 and 2 were not run. See
`docs/development/2026-09-17-m11-data-profiler-implementation.md`.

## Milestone 12 — MCP Connector Layer · `COMPLETED` (under OD-1; M12-C `BLOCKED`)

**Closure (2026-09-18).** M12-B was reviewed and approved by the project owner and checkpointed as `990e88d`
("M12-B: connector registry and value-free discovery"). That satisfies ADR-0037 §L items 8 and 9, so M12-B is
`COMPLETED`. Under OD-1, Milestone 12 is `COMPLETED` with **M12-C still explicitly `BLOCKED`**. Closing M12 does not
close, approve or advance M12-C, and it does not admit a connector:

- the registry ships empty by design;
- no connector is registered, supported, measured or usable;
- HubSpot remains a designated optional future connector, in lifecycle state 1.

The M12-B development record keeps its historical `REVIEW` status line unedited. This closure is recorded in
`docs/development/2026-09-18-post-m12b-roadmap-gate.md`.

Connector resolution inside `biq-data-ingestion`; `CONNECTORS.md` capability map;
`.mcp.json` verified endpoints only (`BLOCKED` — Connector gate, most categories have no
verified server); connector-absent degradation tests via `evals/mocks/`; write-attempt
approval-gate tests.

*The paragraph above is the pre-review scope, kept as written. ADR-0037, if accepted, refines it
as recorded below.*

### M12-A — Connector layer contract · `COMPLETED (DECISION ONLY)`

Contract and architecture review. **No production code, test, schema, skill, command, agent, `.mcp.json`
entry, connector or MCP server was changed, and no part of M12 is implemented.** **ADR-0037 accepted** by the project
owner on 2026-09-17, with owner decisions **OD-1 and OD-2**. Acceptance approves the contract only: it authorizes no
connector, Connector Gate result or runtime use. No accepted ADR edited; ADR-0004 unchanged.

| Contract element | Status | Decision |
|---|---|---|
| Contradictions found | `COMPLETED` | **C-1:** runtime discovery of "whatever server is connected" can neither bind a tool grant nor avoid reading platform config. Resolved by exact registry-bound identity (OD-2), a **partial supersession of ADR-0004**: its "performs discovery … whatever server is connected" and "user-configurable" clauses only; ADR-0004 text unedited. **C-2:** connector record reads would put values in a model context and let a model author data. Resolved by separating discovery from data; M12-C `BLOCKED`. **C-3:** write-attempt tests are refusal tests (v1 read-only). **C-4:** platform-injected server instructions are a residual risk |
| Trust chain | `COMPLETED` | Normative 14-step chain: fixed registry → registered identity → declared capability → `discovery` only → exact server and tool identity → Connector Gate measurement binding identity, namespace, tool name, class, argument and output shape, server instructions and the value-free property → exact grant. No substitution; no model-discovered servers; availability, Gate approval, catalogue and registry metadata never authorization or evidence |
| Declaration / measurement / grant | `COMPLETED` | Three layers, none sufficient alone. Use is valid only per sealed operation when all bindings agree exactly; any difference refuses use (`binding_mismatch`). Reuses existing grant, sealed-request, fail-closed and registry patterns; no new authorization system |
| Scope | `COMPLETED` | **M12-B:** registry, capability resolution, named absence + file fallback, value-free discovery catalogue — no record reads, no evidence, no synthesis input. **M12-C:** connected-system record reads — separate capability, separate ADR, separate security evidence, Data Layer required; never follows automatically from M12-B |
| Agent | `COMPLETED` | The reserved `biq-data-profiler` (ADR-0036), not a new agent. The M11 local-file profile stays agent-free and unchanged. Built only if a complete discovery trust chain exists. Grant = exactly those tools; never local files, records, Business Context, research, credentials, web, shell, arbitrary MCP, read, write or administrative tools |
| MCP | `COMPLETED` | Third-party vendor servers declared by BusinessIQ through the Connector Gate, identity only. No BusinessIQ-owned proxy or new local server; `biq-verifier` untouched. Exact tool names and shapes are measured at the Gate, never assumed |
| Privacy | `COMPLETED` | Nothing internal, context-derived, research-derived or from another connector crosses to a connector. Catalogue carries no record value, option value, count, identity or secret. No connector string reaches research, synthesis or verification |
| Provenance | `COMPLETED` | M12-B produces no claim and no synthesis input; catalogues and every class-2 claim refused at re-entry. Class 2 is left to M12-C's own ADR under stated minimum constraints |
| Failure model, security tests, human control | `COMPLETED` | 19 closed failure codes (adds `binding_mismatch`); 19 mandatory security-test categories (adds layer-binding agreement); every M12 interaction read-only; writes prohibited with no path |
| Completion gate | `COMPLETED` | Objective M12-B gate with no M12-C item. M12 may be `COMPLETED` on M12-B alone, with M12-C recorded `BLOCKED` (OD-1) |
| Owner decisions | `COMPLETED` | **OD-1 accepted** (M12 may complete with M12-C `BLOCKED`). **OD-2 accepted** (exact registry-bound identity; same-vendor servers under other namespaces do not qualify) |

### M12-A.1 — Optional connector / user-initiated connection clarification · `COMPLETED (DECISION ONLY)`

Contract clarification only. **ADR-0038 accepted** by the project owner on 2026-09-18, with **OD-3** resolved.
Acceptance approves the contract only: it authorizes no implementation, connector, registry entry, `.mcp.json` entry,
Connector Gate result or runtime use. ADR-0037 is unedited and not weakened. No production code, test, schema, skill,
command, agent, `.mcp.json` entry, registry, connector or MCP server was changed. No connector was authenticated and no
Connector Gate measurement was taken.

| Element | Status | Decision |
|---|---|---|
| Optional connector | `COMPLETED` | Every connector is optional. Its absence, disconnection, authorization failure, unavailability or refusal degrades only its capability, with a named reason and the file alternative |
| Five facts | `COMPLETED` | Planned is a documentation status only. Supported ≠ connected ≠ authorized ≠ verified capability ≠ available for use; each has one owner; none substitutes for another |
| Lifecycle | `COMPLETED` | Seven conceptual states mapped onto ADR-0037's existing §H codes; no new runtime state or code; static checks before any dispatch; nothing persisted |
| User connection | `COMPLETED` | User-initiated through the platform's own mechanism; BusinessIQ never starts it, handles no credential, reads no platform configuration, invents no UI; a connection never substitutes for the Connector Gate |
| OD-3 — admission rule | `COMPLETED` | A connector is represented as supported in the shipped registry, and its `.mcp.json` entry shipped, only when at least one declared v1 capability has a complete, approved, BusinessIQ-owned Connector-Gated chain. For M12-B that capability is value-free discovery. It does not unblock M12-C |
| HubSpot | `COMPLETED` | Designated optional future `~~crm` connector. **Not** currently supported or usable: no BusinessIQ-owned, Connector-Gated value-free discovery capability has been approved. Unregistered, undeclared, unmeasured; no BusinessIQ HubSpot connection path |

| Sub-milestone | Status |
|---|---|
| M12-B — registry, resolution, value-free catalogue | `COMPLETED` — implemented 2026-09-18 with no connector admitted (ADR-0037 §L item 1); review remediation applied; approved by the owner and checkpointed `990e88d`. See below |
| M12-C — connected-system record reads | `BLOCKED` — P-1 to P-5 unmeasured and unsatisfied; requires its own accepted ADR and security evidence; not part of M12-B's completion gate |

### M12-B — Connector registry and value-free discovery catalogue · `COMPLETED`

Implemented against ADR-0037 as narrowed by ADR-0038's OD-3. **No candidate existed to take through the
Connector Gate, so no Gate measurement was taken**: the only vendor server observable in the development
session is another plugin's HubSpot server exposing only authentication tools, and BusinessIQ declares no
connector server. So the registry ships **empty by design**, the `biq-data-profiler` agent stays unbuilt
(§D.1), and `.mcp.json` is unchanged. No tool was called and no connector was authenticated. The
infrastructure exists; **runtime connector discovery is unverified**, because no qualifying connector
exists to run it against.

| §L item | Status | Evidence |
|---|---|---|
| 1 — Connector Gate | Not applicable - no candidate | No `.mcp.json` connector entry was proposed, so no Gate measurement was taken or required; M12-B completes under §L item 1 with no connector admitted |
| 2 — Files | `COMPLETED` | `lib/python/biq/connectors/` (contract, registry, binding, catalogue); `lib/schemas/connector.schema.json`; `skills/biq-data-ingestion/SKILL.md` extended (skill count unchanged, no command); `register_claims()` refusal extended; agent not built (§D.1). No integration page: no connector is admitted |
| 3 — Agent and tool boundaries | `COMPLETED` | Static §B.2 agreement check; `.mcp.json` = `biq-verifier` + registered servers exactly; no agent without a complete chain; M11 profile tests unmodified |
| 4 — Tests | `COMPLETED` (deterministic) | `tests/unit/test_m12b_connector_registry.py`, `tests/negative/test_m12b_connector_security.py`: the deterministic half of all 19 §J categories, OD-3, lifecycle mapping, optionality. All 19 §H codes are produced by the engine; 5 are reachable with the shipped registry, and 14 need a sealed operation and are exercised only against a synthetic enforcement fixture (the 7 relayed codes as test-written relay lines). The runtime agent-boundary run does not apply: the agent is not built |
| 5 — Live protocol verification | N/A | Applies only where an agent is built |
| 6 — Regression | `COMPLETED` | Full suite green; totals in the development record |
| 7 — Strict validation | `COMPLETED` | `claude plugin validate . --strict` passes |
| 8 — Security review | `COMPLETED` | Self-review and review remediation recorded (failure semantics, value-free boundary, coverage claims); approved by the project owner before checkpointing |
| 9 — Git checkpoint | `COMPLETED` | `990e88d`, committed at the owner's instruction; working tree clean at the checkpoint |

HubSpot remains a **designated optional future connector**, in lifecycle state 1 (`connector_not_configured`).
M12-C remains `BLOCKED`; nothing in M12-B reads a record, and every record-read request is refused as
`blocked_prerequisite`.

See `docs/decisions/ADR-0037-m12-connector-layer-contract.md`,
`docs/development/2026-09-17-m12-a-connector-layer-contract.md` and
`docs/development/2026-09-17-m12-a-contract-remediation.md`. M12-A.1: see
`docs/decisions/ADR-0038-optional-connector-connection-lifecycle.md` and
`docs/development/2026-09-18-m12-a1-optional-connector-lifecycle.md`. M12-B: see
`docs/development/2026-09-18-m12-b-connector-registry.md`.

## Milestone 13 — Test Hardening & Evals · `COMPLETED`

Full negative-path coverage; large-dataset performance; routing/discriminability cases;
approval-model cases (read-only never prompts); authored eval cases with mocks. Eval
execution `BLOCKED` on early-access enablement.

*The paragraph above is the pre-contract scope, kept as written. ADR-0039, accepted 2026-09-18, refines it as recorded
below. There are three changes of substance:*

- *"with mocks" no longer applies to connectors;*
- *the early-access refusal is re-measured, and only under the owner's authorisation;*
- *eval execution may legitimately remain `not_executed` at M13's completion, recorded as such.*

**Why M13 is next (post-M12-B roadmap gate, 2026-09-18).** It is the next planned milestone, and its only dependency,
M10, is `COMPLETED`. It needs nothing from M12-C and invents no connector behaviour. It holds work the plan already
assigns to it:

- R-05 routing;
- R-10 selection stability;
- R-01 eval execution;
- ADR-0007's coverage matrix, never produced;
- the three `PLANNED` M9 tier-test rows.

Nothing else is both planned and buildable:

- M9's open items are owner-run live smoke tests;
- M12-C is `BLOCKED`;
- M14 depends on M13.

### M13-A — Test hardening and evals contract · `COMPLETED (DECISION ONLY)`

**ADR-0039 Accepted** by the owner on 2026-09-18, with clarifications (the ADR's *Owner clarifications at acceptance*).
Acceptance authorises no implementation. No test, eval case, fixture, harness code or measurement was built. No
accepted ADR was edited.

| Contract element | Status | Decision |
|---|---|---|
| Invariants | `COMPLETED` | I-1 to I-13 (ADR-0039). **Hard invariant I-1:** no production behaviour is changed to make a test, eval or measurement pass, whether the trigger is a missing coverage row, an eval failure, a poor measurement, a routing overlap or unstable forecast selection |
| Scope | `COMPLETED` | Tests, fixtures, measurements, eval cases, the defect and measurement records, and test documentation only. **No product file changes**: no `lib/`, `skills/`, `commands/`, `agents/`, `reference/`, `config/`, `assets/`, manifest, `.mcp.json`, `run_tests.py` or `.gitignore` edit. The eval harness is the platform's `claude plugin eval`, and M13 builds no runner |
| Coverage matrix | `COMPLETED` | `docs/testing/coverage-matrix.md`, with closed rows from in-repository enumerations only: S1 §16 ×18, S2 fixture corpus ×15, S3 §15 behaviours ×12, S4 commands ×19, S5 §8 approval ×13, S6 M9 tier rows ×3, and S7 ADR-0037 §J ×19, referenced. Every count was verified against the repository. ADR-0007's uncommitted "24 specified scenarios" is recorded as **unavailable** and is not reconstructed |
| M13.1 deterministic hardening | `COMPLETED` (implemented 2026-09-18, checkpointed `33f6e25`; see M13.1 below) | Gap closure in new `test_m13_*` modules. Opt-in `BIQ_LARGE_DATASET=1` measurement at 100k and 250k CSV rows, recorded with no threshold. R-05 description overlap between distinct components and R-10 leave-one-period-out selection stability, recorded only. The only asserted limit is architecture's 1,024-character skill description. Measurement records in `docs/testing/measurements.md`, never tuned |
| M13.2 behavioural evals | `COMPLETED` (owner-accepted 2026-09-26; authored 2026-09-19; ADR-0044 stage 3 complete 2026-09-22; **closing evaluation 2026-09-24/25: all 64 attempted, 16 `automated_pass`, 34 `automated_fail`, 14 `execution_unavailable`, 0 `not_executed`**; see M13.2 below) | Five suites: `behaviour`, `disclosure`, `approval`, `connectors`, `routing`. Static validation by a deterministic test. E.1 availability measurement first, and only if authorised. Outcomes: (a) executed, (b) `execution_unavailable`, or (c) not authorised. Under (b) and (c), each S3 row gets a `manual_observation` scenario |
| Execution policy | `COMPLETED` | The owner's explicit per-execution authorisation, with a stated `--max-cost-usd`. Always `--no-publish`. `--mocks record` with no mocks, so no plugin server starts. Never `--allow-real-servers` or `--mocks off`. No web or `mcp__` grant, no authentication, no real or production connector. Fixed `--runs 3 --threshold 1.0`: a case passes only if every run passes. Results gitignored and recorded |
| Evidence classes | `COMPLETED` | `automated_pass`, `automated_fail`, `not_executed`, `execution_unavailable`, and separately `manual_observation`. Reported per class. A manual scenario, or unavailable or unauthorised execution, is never an automated pass |
| Defects | `COMPLETED` | `M13-DEF-NN` records in `docs/testing/defects.md`, linked from *Known issues*. The fields are: `defect_id`, `source`, `defect_class`, `affected_component`, `reproducer`, `expected_behavior`, `observed_behavior`, `status`, `blocks_m13_completion`, `linked_reference`, `found`. Defects are never scored or ranked. Product defects are recorded, never fixed in M13. Only test and eval infrastructure defects are fixed in M13. No assertion is weakened to hide a defect |
| M12-C | `COMPLETED` | No connector mock and no M12-C test. Synthetic connector fixtures are only labelled deterministic enforcement fixtures (`tests/connector_fixtures.py` precedent). The eval harness is **not** a P-1 mechanism, and no M13 artifact can bypass the Connector Gate or P-1 to P-5. M12-C stays `BLOCKED` |
| Out of scope | `COMPLETED` | D-13's five skills (open, not blocking). D-14 cleanup (deferred to M14). M9's live smoke tests (M9 stays `IN PROGRESS`). Any product defect fix |

| Sub-milestone | Status |
|---|---|
| M13-A — contract | `COMPLETED (DECISION ONLY)` — ADR-0039 accepted 2026-09-18 |
| M13.1 — deterministic hardening | `COMPLETED`. Implemented 2026-09-18. U-1 resolved as (c). The §L gate is satisfied under ADR-0039 as amended by ADR-0040. Approved by the owner and checkpointed `33f6e25` on `origin/main` (see M13.1 below) |
| M13.2 — behavioural evals | `COMPLETED` — **owner-accepted 2026-09-26** against ADR-0039 §L and checkpointed by "M13.2: complete test hardening and evaluation" (not pushed). History: **closing evaluation executed 2026-09-24/25 and recorded 2026-09-25**: 64 of 64 attempted, 16 `automated_pass`, 34 `automated_fail`, 14 `execution_unavailable`; $47.00 of $75.00. M13-DEF-05 closed; M13-DEF-13 to M13-DEF-23 recorded, M13-DEF-17 to M13-DEF-23 blocking by rule. The history that follows is kept: implementation authorised and done 2026-09-19 (see M13.2 below). One case has executed, three times, on 2026-09-22, and is `automated_fail` because the evaluator denied a read-only call before the resolver ran; no case has passed. **§E.1 outcome (a) is recorded and R-01 is ready for owner closure.** ADR-0044 stage 3 complete: 133 of 133 graders mapped, 64 of 64 loadable. M13-DEF-05 open with its conditions met and closure recommended; M13-DEF-07 and M13-DEF-09 fixed; M13-DEF-08 `fixed_product`; **M13-DEF-10 `fixed_infrastructure` and live-validated 2026-09-23**; **M13-DEF-11 `fixed_infrastructure`** (environment prerequisite verified 2026-09-23, live evaluator start not observed); **M13-DEF-12 `fixed_product`** under ADR-0046, verified live 2026-09-23; G-2 and G-3 resolved; twelve manual observations outstanding. Execution only with the owner's authorisation and ceiling. May complete with every case `not_executed` (ADR-0039 §L). Eval inputs governed by ADR-0039 as amended by ADR-0041 (accepted 2026-09-19; G-1 resolved, G-2 and G-3 open) |

See `docs/decisions/ADR-0039-m13-test-hardening-and-evals-contract.md`,
`docs/development/2026-09-18-m13-contract-finalization.md` and
`docs/development/2026-09-18-post-m12b-roadmap-gate.md`.

### M13.1 — Deterministic hardening · `COMPLETED`

Implemented under ADR-0039 on 2026-09-18.

**Closure.** M13.1 was approved by the project owner after deterministic hardening and contract-conformance
remediation, and checkpointed on `origin/main` as `33f6e25d58b9b010d7294c08c3b074ce920dd832` ("M13.1: deterministic
test hardening and coverage closure"). ADR-0040 resolved the ADR-0039 §L completion-gate contradiction. Closing M13.1
changes no evidence, coverage result or defect classification:

- S2-14 remains an OPEN GAP — ENVIRONMENT UNAVAILABLE, and is not counted as coverage;
- M13-DEF-01 and M13-DEF-03 remain `open`, remediation unassigned;
- M13-DEF-02 remains resolved;
- M13.2 remains `PLANNED` and has not started.

- **No production file changed.** Nothing under `lib/`, `skills/`, `commands/`, `agents/`, `reference/`, `config/`,
  `assets/` or `.claude-plugin/`, and not `.mcp.json`, `run_tests.py` or `.gitignore`.
- **No M13.2 work.** No eval case, eval runner or eval execution.
- **No connector, authentication or external service.** M12-C stays `BLOCKED`; M9 stays `IN PROGRESS`.

| Task | Status | Evidence |
|---|---|---|
| Coverage matrix (ADR-0039 §B) | `COMPLETED` | `docs/testing/coverage-matrix.md`: 99 rows, S1–S7 closed against their sources. **76 `covered`, 3 `covered-by-M13`, 18 `behavioural-only` (all `not_executed`), 0 `not-applicable`, 2 `gap`** (S1-17 → M13-DEF-03; S2-14 → U-1). ADR-0007's 24-scenario list is recorded as unavailable, not reconstructed |
| Matrix and register validator | `COMPLETED` | `tests/unit/test_m13_coverage_matrix.py`, 26 tests. Set sizes are recounted from their sources; the vocabularies are closed; every cited test (212) exists; no automated evidence while no eval case exists; every gap is explained; the defect records are complete. Mutation-checked: five deliberate corruptions each caught |
| Gap closure (§C) | `COMPLETED` | **S1-05**: the §16 unsupported-KPI statement (`negative.test_m13_error_handling`, 5). **S5-12**: no shipped component instructs or scripts a repository write (`negative.test_m13_approval_boundaries`, 4). **S6-02**: the gate blocks a single re-identifying query (`negative.test_m13_tier_rows`, 6). No gap needed a product change |
| D.1 large dataset | `COMPLETED` | Opt-in `integration.test_m13_large_dataset` executed at 100k and 250k: 6 tests, 0 failures. Correctness held. Exposed product defect **M13-DEF-03** (a full pass above 100k is labelled `streamed` and incomplete). Its first run exposed, and M13 fixed, test defect **M13-DEF-02** |
| D.2 discriminability (R-05) | `COMPLETED` | `unit.test_m13_discriminability`, 13 tests. Command mean 0.077 / max 0.556; skill mean 0.097 / max 0.633. The top pair in both tiers is industry research / market analysis. Exposed product defect **M13-DEF-01** (two skill descriptions over 1,024 characters) |
| D.3 selection stability (R-10) | `COMPLETED` | `integration.test_m13_selection_stability`, 5 tests. 13 windows, 4 distinct methods, 4 adjacent changes. The leave-one-out pair is stable (`linear_trend`) |
| Defect register (§G.1) | `COMPLETED` | `docs/testing/defects.md`: M13-DEF-01 and M13-DEF-03 (product, `open`, not fixed), M13-DEF-02 (infrastructure, `fixed_infrastructure`). None blocks M13 by rule |
| Determinism audit | `COMPLETED` | No unseeded randomness, network use or unpinned clock in tests. Clock-shift probe (research "today" = 2029-01-01, scratchpad only): 4,717 tests, 0 failures, 0 errors |
| Regression, strict validation, scope audit | `COMPLETED` | See the development record: closing run, `claude plugin validate . --strict`, `git diff --check`, secret scan, protected-path audit, K.5 re-check |
| **U-1 — S2-14 cross-tier equivalence** | `COMPLETED` — owner decision **(c)**, 2026-09-18 | **S2-14 is an OPEN GAP, ENVIRONMENT UNAVAILABLE**, accepted by the owner. All eight Tier-1 equivalence tests are skipped. Tier 1 is openpyxl importable in the *system* interpreter (`runtime/tiers.py`, `TIER_OPENPYXL_SYSTEM`). `CLAUDE.md` §4 forbids installing it there, and the consented Tier-2 managed install would not un-skip these tests. No equivalence is claimed, and the row is not counted as covered. It is not a product defect and not a test-infrastructure defect, so it has no defect record. It is the first application of **ADR-0040**, the owner-accepted environment-unavailable gap, with its complete disposition record. A future run in an owner-approved environment where openpyxl is importable may close it. Recorded in `docs/testing/coverage-matrix.md` (*S2-14*) |
| ADR-0039 §L completion check | `COMPLETED` — satisfied under ADR-0039 as amended by ADR-0040 | The final remediation found one unmet condition: §L required every deterministic gap to be "closed, or `gap` with a defect id", and S2-14 honestly has none. **ADR-0040** (Accepted 2026-09-18) amends only that condition and §B's `gap` definition, to admit an owner-accepted environment-unavailable gap with a complete disposition record. S2-14 carries that record, and every other §L condition was already met. S2-14 stays `gap` and is not counted as covered. No defect id was invented. M13-DEF-01 and M13-DEF-03 stay `open`, and M13-DEF-02 stays resolved. ADR-0039's file was not edited |
| Regression re-time | `COMPLETED` | One full `python tests/run_tests.py -v`, 2026-09-18: **4,749 tests, 0 failures, 0 errors, 28 skipped, 414.476 s**. The 7,694-second closing run did not reproduce, so it is recorded as an anomalous single observation, not a regression. The baseline was 850.279 s. The cause of the variance is not established. K.5 re-checked against this run: all 205 `covered` citations `ok`. See the M13.1 final-remediation record and `docs/testing/measurements.md` (*Regression-suite wall clock*) |

See `docs/development/2026-09-18-m13-1-deterministic-hardening.md` and `docs/testing/`.

### M13.2 — Behavioural evals · `COMPLETED`

**Owner-accepted 2026-09-26.** ADR-0039 §L is satisfied: every E.3 case authored and E.5 passing; exactly one §E.1 outcome, (a); every case attempted and classified, with per-run results, across the closing evaluation, the 34-case re-evaluation and the availability-completion evaluation, which supplement and do not overwrite one another; no defect `blocks_m13_completion: yes`; K.1–K.6; `architecture.md` §15/§20 reconciled; R-01 closed. Open product defects remain tracked separately. The text below is the milestone's history and is kept as written.

Implemented under ADR-0039, as amended by ADR-0040 and ADR-0041, on 2026-09-19: the owner's M13.2 implementation
prompt. That prompt authorised no eval execution, so this is the implementation stage only. **M13.2 is not
`COMPLETED`.** §E.1 outcome (c) was recorded on 2026-09-19 (`docs/development/2026-09-19-m13-2-e1-outcome-g2.md`), so
§L now also needs a `manual_observation` scenario for each S3 row. G-2 is resolved, and none has been performed.

**Superseded on 2026-09-25 by the closing evaluation (§E.1 outcome (a)).** All 64 cases were attempted under §F and every case's class is recorded in its case file; manual observations are no longer a §L condition, because §L requires them only under outcomes (b) and (c). The bullets below record the implementation stage and are kept as history. M13.2 remains `IN PROGRESS`: seven evaluation-infrastructure defects (M13-DEF-17 to M13-DEF-23) are open and block completion by rule, and the K checks are recorded in `docs/development/2026-09-25-m13-2-closing-evaluation-record.md`.

- **No production file changed.** Nothing under `lib/`, `skills/`, `commands/`, `agents/`, `reference/`, `config/`,
  `assets/` or `.claude-plugin/`, and not `.mcp.json`, `run_tests.py` or `.gitignore`.
- **No execution.** No `claude plugin eval` invocation of any kind, no web, MCP, connector or authentication use, and
  no fabricated result. Every case is `not_executed`.
- **No connector.** The registry stays empty, M12-C stays `BLOCKED`, and HubSpot stays a designated future connector.

| Task | Status | Evidence |
|---|---|---|
| ADR-0041 input fixtures | `COMPLETED` | EVI-01 to EVI-03 under `tests/fixtures/eval_inputs/`, built by `tests/fixtures/build_eval_inputs.py`, with the manifest and a `* -text` `.gitattributes`. The rebuild is byte-identical. Each fixture's precondition holds through the unchanged pipeline (`integration.test_m13_eval_input_preconditions`, 13 tests) |
| Case suite (§E.2, §E.3) | `COMPLETED` (authored); **migrated to the dual-layer schema `biq-eval-case/2` on 2026-09-22** (ADR-0044 Phase 1) | 64 cases (`docs/testing/eval-suite.md`): `behaviour` 5, `disclosure` 8, `approval` 24, `connectors` 5, `routing` 22 (16 positive, 6 near-miss from M13-MEAS-D2) |
| Graders (§E.4) | `COMPLETED` (authored) | 133 graders: 88 deterministic, 45 LLM. Each LLM grader states in its own file why no deterministic assertion suffices. No score, rank or threshold |
| Static validator (§E.5, ADR-0041 §8) | `COMPLETED`; extended 2026-09-22 with the §F.6 scaffold assertion | `unit.test_m13_eval_cases`, 100 tests. Mutation-checked: 20 deliberate corruptions, each caught. The 2026-09-22 extension adds the `Scaffold` class (the assertion §F.6 asks §E.5 to make), admits `context` and the permitted scaffold file, steps over the harness's generated `results/`, and binds the pilot case's evidence class to the admissibility rule rather than asserting it by hand |
| Coverage matrix | `COMPLETED` | Every behavioural row cites its cases, and every case names its rows back. 18 `behavioural-only` rows: S3-11 and S5-01 are `automated_fail` from the 2026-09-22 pilot, with the cell stating that the run never reached the command and the requirement is still behaviourally untested; the other 16 are `not_executed`. **No row is `automated_pass`**, asserted |
| §E.1 outcome | **`COMPLETED` — outcome (a)**, recorded 2026-09-22 from the three-run pilot | 2026-09-20: `claude plugin eval` refused all 64 case files at load, so no case ran and `costUsd` was 0. 2026-09-22, two authorised one-run pilots: the first was refused before turn 1; the second **executed** (5 turns, no error, one graded criterion, $0.1712634) and failed, making that case `automated_fail`. §E.1 requires the measurement at `--runs 3`, and neither pilot was authorised for three, so **no §E.1 outcome is recorded from them**. Execution is now demonstrably *available*, which is the evidence (a) rests on, but (a) may be recorded only from a conforming measurement: **R-01 stayed `BLOCKED` at that point**. *Current status (reconciled 2026-09-27, M14-1):* R-01 is closed, 2026-09-26, under ADR-0039 §E.1 (a) at M13.2 (see *Known issues*). See `docs/development/2026-09-20-m13-2-e1-execution.md` and `docs/development/2026-09-22-m13-2-eval-harness-remediation.md` |
| Eval input staging (§F.6) | **`COMPLETED`** — pilot case 2026-09-22, remaining 37 on 2026-09-23 | M13-DEF-07. `evals/approval/a01-read-only-anomaly-detection/scaffold.sh` stages that case's one declared input; `unit.test_m13_eval_cases.Scaffold` asserts §F.6 statically and `integration.test_m13_eval_scaffold` proves the effect under the harness invocation (8 tests). All **38** business-file cases now stage their own declared fixture. The hand-kept staged list and `UNSTAGED_COUNT` are replaced by an invariant asserted both ways — a case declares a scaffold iff it requires a business file — with `BUSINESS_FILE_COUNT = 38`; `integration.test_m13_eval_scaffold` executes all 38 and checks byte-identical staging with no extra files |
| Engine interpreter on the evaluation machine | `COMPLETED` 2026-09-22 | M13-DEF-08, `fixed_product` under accepted **ADR-0045**. `lib/biq_run.sh` resolves the interpreter portably; 26 shipped files and 34 blocks migrated; verified by `unit.test_m13_def08_runtime_resolver` (26) and `integration.test_m13_def08_runtime_resolution` (40), with ADR-0042's 21 + 16 guarantee tests intact. On this host `sh lib/biq_run.sh --where` now enters the engine under Python 3.14.4, isolated |
| Eval `--allow-tools` grant set | **`COMPLETED`** 2026-09-23 (deterministically; not live-verified) | The owner's narrow resolver grant was stated and used on 2026-09-22 and is **unchanged**. M13-DEF-10 showed it insufficient for the agent's discovery step, and that `Read` was never permitted either. The authorised set is now exactly two entries — `Read` and `Bash(sh <plugin path>/lib/biq_run.sh:*)` — documented in `docs/testing/eval-suite.md` *The grant set* and held by 30 assertions. `Bash(ls:*)`, `Bash(sh:*)`, the retired interpreter grants and any write, web or connector grant remain excluded |
| ADR-0044 stage 3 — trace-dependent grader mapping | **`COMPLETED`** 2026-09-22 | All 24 mapped from the observed pilot trace: `command_invoked` → `tool_used`/`Skill`/`businessiq:<command>`/`min: 1`; `command_not_invoked` → the same with `min: 0, max: 0`. **133 of 133 mapped, 0 pending, 0 dropped, 174 platform graders, 64 of 64 loadable.** Verified by `unit.test_m13_eval_cases` (102) and `unit.test_m13_def10_eval_grant` (15). The skill-only spelling is **not** claimed to be proved by this pilot |
| G-2: manual-observation ownership and session | `COMPLETED` (documented interpretation, no ADR) | Owner-performed, one fresh session per S3 row, outside the repository. Records in `docs/testing/manual/`. One designated case per row (`docs/testing/eval-suite.md`) |
| `manual_observation` scenarios | `PLANNED` — ready to resume as a separately controlled step. No longer blocked, since M13-DEF-04 was remediated on 2026-09-20 | Twelve, one per S3 row, performed by the owner. **None performed.** Required for M13.2 `COMPLETED` under (c). The execution pack is ready: `docs/testing/manual-observation-pack.md`, validated by `unit.test_m13_manual_observation_pack`. WD-1 (classification C, M13-DEF-04) was remediated under ADR-0042, and T-J establishes the external-working-directory prerequisite. G-2 is unchanged |
| G-3: platform execution mechanics | **`COMPLETED`** — settled 2026-09-22 | Verified before any authorised run. **Settled 2026-09-22:** the case-file contract (ADR-0044); that the harness stages no input and a case must do it with a §F.6 scaffold; that `engine-python` is `Bash(python:*)`/`Bash(python *)` and must be checked against the machine; that the deterministic grader is `tool_used`, whose `tool` is an exact identifier and whose `input_match` is a JS RegExp over the tool input text. **Settled by the three-run pilot's trace:** a plugin command fires under the **`Skill`** tool with the input `{"skill": "businessiq:<command>", ...}`, byte-identically in all three runs, and the agent's tool roster was `Task, Bash, Read, Skill, TaskStop, ToolSearch` with `permissionMode: dontAsk`. Nothing about the mechanics remains unobserved; what remains is the grant decision (M13-DEF-10) |
| Regression, strict validation, scope audit | `COMPLETED` | See `docs/development/2026-09-19-m13-2-eval-implementation.md` |

See `docs/development/2026-09-19-m13-2-eval-implementation.md`,
`docs/development/2026-09-19-m13-2-e1-outcome-g2.md` and `docs/testing/eval-suite.md`.

### M13-DEF-04 remediation (ADR-0042) · `COMPLETED` (implemented and verified 2026-09-20; committed in `8287e98`)

This is a dedicated milestone under its own owner prompt. It is **outside M13's scope**, because ADR-0039 I-13 forbids
fixing a product defect within M13. It implements accepted ADR-0042.

| Task | Status | Evidence |
|---|---|---|
| Launcher `lib/python/biq_run.py` | `COMPLETED` | Stdlib only. It finds the engine from its own location, validates the `businessiq` manifest, requires `-I`, keeps the working directory out of `sys.path`, verifies where `biq` came from, and supports `--where` |
| Commands migrated (10) | `COMPLETED` | anomaly-detection, ask-business-data, business-health, cash-flow-analysis, customer-analysis, product-analysis, profitability-analysis, retrieval-slice, revenue-forecast, sales-analysis. The 9 delegating commands are unchanged |
| Skills migrated (16) | `COMPLETED` | 11 relative-entry skills. The 5 bare-import skills (benchmark-comparison, decision-support, executive-report, strategy-recommendations, swot) run their flows through the launcher's heredoc form, byte for byte. So do the four research skills' footing flows |
| T-A to T-H, T-J | `COMPLETED` | `integration.test_m13_def04_engine_entry`, 21 tests |
| T-K | `COMPLETED` | `unit.test_m13_def04_static_guard`, 14 tests, mutation-checked 6/6 |
| T-I | `COMPLETED` | Full regression: 4,872 tests, 0 failures, 0 errors, 29 skipped |
| Open verification | `PLANNED` | G-3 (the eval sandbox), V-4 (the minimum CLI version), Unix-like runtime |

See `docs/development/2026-09-20-m13-def-04-implementation.md`.

## Milestone 14 — Documentation & Release · `IN PROGRESS`

Worked examples; troubleshooting guide; per-component reference pages; final token-cost
measurement; release tagging behind the publication gate.

| Item | Status | Notes |
|---|---|---|
| M14 entry gate | `COMPLETED` | Owner-approved 2026-09-27. `README.md` restored to the committed version; `file.txt` deleted (owner decisions) |
| M14-1 — Entry and status reconciliation | `COMPLETED` | Checkpointed `50d1f0e`. 2026-09-27, documentation only. Reconciles the M13 status drift, the ADR indexes and the stale banners the entry-gate audit found. See `docs/development/2026-09-27-m14-1-entry-reconciliation.md` |
| M14-2 — `README.md` rewrite (closes D-14's README part) | `COMPLETED` | Checkpointed `5c1b15d`. 2026-09-27; `README.md` only. Redesigned as the primary product README, every claim verified against the repository. It documents: capabilities; the 18 user commands, 16 skills and 2 subagents; connector availability (none); privacy and data boundaries; approval and write safety; installation and use paths; examples and documentation links; forecasting and anomaly limitations; and the final-verification startup limitation (R-13). Full regression and strict validation pass. See `docs/development/2026-09-27-m14-2-readme-redesign.md` |
| M14-3 — Component documentation and index reconciliation (per-component reference pages; D-13 documentation part) | `COMPLETED` | Checkpointed `8e4ab17`. 2026-09-27; documentation only. **Inventory:** 18 user-facing commands, 1 internal test harness (`/retrieval-slice`), 16 skills, 2 subagents, verified on disk. **Command index** (`docs/commands/README.md`): rewritten, grouped into five families, with the harness classified separately. **Skill index** (`docs/skills/README.md`): rewritten, separating the shipped, designed-not-shipped and outside-the-design skills. **D-13:** documentation part reconciled; owner decision open. **Reference pages:** five command-family pages, and the `biq-research-scout` agent page. Skills keep `SKILL.md` as their detailed reference. **Navigation:** `docs/README.md` and `docs/agents/README.md`; every relative link in the changed files resolves. **Remaining debt:** see the record's §15. See `docs/development/2026-09-27-m14-3-component-documentation.md` |
| M14-4 — Release readiness and finalization | `COMPLETED` | Checkpointed `57e92fa`. 2026-09-27. Worked examples, troubleshooting guide, development index (D-14), token measurement (D-10), packaging observation, consistency review, release-gate matrix. See `docs/development/2026-09-27-m14-4-release-readiness.md` |
| M14-6 — M9 smoke-test protocol remediation and final release-gate verification | `COMPLETED` | Checkpointed `57e92fa`. 2026-09-27. ADR-0053 harness capture of the scout's reply; six skills updated; 23 new tests; all four M9 live smoke tests passed, criterion 5 verified byte for byte. See `docs/development/2026-09-27-m14-6-m9-smoke-protocol-remediation.md` |
| M14-5 — Final product corrections and release gate | `COMPLETED` | Checkpointed `57e92fa`. 2026-09-27. R-15, R-13 (ADR-0052), R-16, M13-DEF-01 and M13-DEF-03 fixed and tested; M13-DEF-14 to -16 reviewed and left open; four M9 live smoke tests run (see the M9 row); release-gate matrix. See `docs/development/2026-09-27-m14-5-final-product-corrections.md` |
| Worked examples · troubleshooting guide | `REVIEW` | M14-4. `docs/examples/README.md`: nine examples, figures reproduced from `assets/demo-data/northwind_sales.csv` at `8e4ab17`; research and synthesis examples show invocation and output shape only. `docs/troubleshooting/README.md`: symptom, cause, check, resolution and escalation for each documented failure mode |
| Packaging observation (ADR-0042 follow-up 5) | `REVIEW` — **OWNER DECISION** | M14-4 measured it. The marketplace source is `./`, so the installed copy is the whole repository: 626 tracked files, about 9.6 MB, including `docs/` (197 files), `tests/` (133) and `evals/` (102, required by `experimental.evals`), plus `CLAUDE.md`. No secret is tracked (`CLAUDE.md` §7). Excluding development material needs a verified platform mechanism and a manifest change. Whether to accept this for release, or to restructure the distribution, is the owner's decision **Owner decision 2026-09-28 (M15-1): whole-repository packaging accepted for 0.1.0**, and not restructured now. Documented in the release notes. |
| Final token-cost measurement (ADR-0013; D-10) | `REVIEW` | M14-4, 2026-09-27: `claude --plugin-dir <repo> plugin details businessiq` (Claude Code 2.1.283, session-only, no install) reports **~7,321 tokens always-on** across 35 command and skill entries and 2 agents; hooks and MCP carry no model-context cost. **Above ADR-0013's self-imposed ≤ 3,000 target.** Under ADR-0013 nothing breaks. The response (accept, revise the target, or merge overlapping components) is an **owner decision** **Owner decision 2026-09-28 (M15-1):** the ≤ 3,000 target is kept; the measured ~7,260 is documented honestly in the release notes. |
| Release tagging behind the publication gate | `PLANNED` — **OWNER RELEASE APPROVAL REQUIRED** | Per-action owner approval (`CLAUDE.md` §13). No version is proposed here; the manifest version is `0.1.0` **Owner decisions 2026-09-28 (M15-1):** version `0.1.0`, tag `v0.1.0`. The release candidate is checkpointed locally with release notes in `docs/releases/0.1.0.md`. Push, tag creation and publication remain explicit owner actions, not yet performed. |

---

## Known issues

| ID | Issue | Impact | Status |
|---|---|---|---|
| R-01 | `claude plugin eval` early-access gated (verified 2026-09-08) | Behavioural evals authored but not runnable here | **Closed 2026-09-26 (M13.2), by the owner's decision under ADR-0039 §E.1 (a).** The missing evidence — owner-authorised cases executed and scored under §F — now exists: the closing evaluation (64 cases), the 34-case re-evaluation and the availability-completion evaluation give every M13.2 case admissible live evidence. This closes the evaluation-execution gap only; it is not a claim about every research or product behaviour. History follows. **Previously `BLOCKED` — READY FOR OWNER CLOSURE as of 2026-09-22.** The owner-authorised three-run pilot of `a01-read-only-anomaly-detection` executed under the full §F policy (`--runs 3 --threshold 1.0`, stated ceiling, $0.5577 spent): three admissible runs, scored. ADR-0039 §E.1 (a) says R-01 "may be recorded as resolved on that evidence and on no other", and that evidence now exists and conforms. It is **not** closed here because §E.1 (a) reserves the recording to the owner. Historical note follows. **Re-observed 2026-09-18 on Claude Code 2.1.276:** a zero-case probe in the session scratchpad reached case discovery ("No eval cases found") with no early-access refusal. Case execution is **not** yet measured, so the status is unchanged. Discovery is not closure evidence. Under the accepted ADR-0039 §E.1, R-01 may be recorded as resolved only when an owner-authorised case actually executes and is scored under §F |
| R-02 | No verified MCP servers for accounting, spreadsheet, commerce, databases | §23 connectors undeliverable as written; file path load-bearing | Open — needs owner decision |
| R-03 | Python not guaranteed on every end-user machine | Engine unavailable → Tier 4 CSV path only | **Mitigated in M3** — Tier 4 now emits structured guidance naming the reason, required structure and what an export loses |
| R-04 | Tier-3 xlsx gaps | Misread values if not detected | **Closed in M3** — built-in and custom formats, 1904, shared formulas, external references, macros and encryption all handled or refused explicitly; unknown formats warn rather than guess |
| R-05 | Description discriminability across 37 components | Wrong component fires; invisible to token metrics | Open — routing eval cases, M13. **Measured at the M8 review:** command-tier description overlap mean 0.085 / max 0.192, skill-tier mean 0.202 / max 0.354; the highest overlaps are pre-existing M6/M7 pairs and the two M8 commands score 0.097 against each other's nearest neighbour, so M8 did not worsen it. **Re-measured by M13-MEAS-D2 (2026-09-18)** with a method fixed in `unit.test_m13_discriminability`, not directly comparable with M8's: command tier (18 components, 153 pairs) mean 0.077 / max 0.556; skill tier (16, 120) mean 0.097 / max 0.633. The top pair in both tiers is industry research / market analysis. Recorded, not tuned; no threshold exists. See `docs/testing/measurements.md`. **Routing cases authored in M13.2 (2026-09-19)**: 16 positive and 6 near-miss (`evals/routing/`), not executed, so routing itself is still unmeasured |
| R-06 | Tier-2 bootstrap introduces a dependency supply chain | New surface | Open — pinned, isolated, consented |
| R-07 | Re-identification checking is heuristic | Occasional over-blocking | **Foundation built in M3** — whole-query assessment with a configurable narrowing limit. Still heuristic and still errs safe; consumed by M9 |
| R-08 | `claude plugin validate --strict` warns that root `CLAUDE.md` is not shipped plugin context | Cosmetic only; manifest itself is clean | Accepted — development governance by design. M2 confirmed the new skill and command add no further warnings |
| R-09 | Always-on cost measured at ~271 tok for 2 components; extrapolates to ~5,000 tok at full scale, above the self-imposed ≤3,000 target | Context competition and weaker component routing | **Reviewed at the M8 gate against ADR-0013: no action required.** Measured 2,097 tok across 15 components — 70% of the self-imposed ≤3,000 target; per-component cost flat (M7 139 → M8 140). Only the 37-component *extrapolation* (~5,172) exceeds target, and ADR-0013 exists to stop the design being optimised against a projection. Its merge prescription is triggered by overlapping descriptions, which measurement does not show. Remains an open watch item |
| R-10 | Forecast method selection is backtest-driven, and on a 24-period history the holdout is only 6 periods | A method may be chosen because it fits those six; two runs on adjacent datasets can select different methods | **New in M8** — mitigated by reporting every candidate's error and by never claiming statistical validity. Selection stability belongs to the M13 eval work. **Measured by M13-MEAS-D3 (2026-09-18)** on the demo revenue series, leave-one-period-out: the 24- and 23-period windows both select `linear_trend`. Across 13 truncations down to the 12-period minimum, four methods win (`linear_trend`, `moving_average`, `naive`, `drift`) with four adjacent changes, and winning margins are often small (9.64 % vs 9.66 % MAPE at 22 periods). Recorded, not a defect; selection unchanged |
| R-12 | **The scout's hand-back intermittently drops its record lines.** In the M10.2-R live session, two of four dispatches (operations `…-03` and `…-04`) returned a final report that *described* the records and referenced the protocol in prose — "see BIQ-REC/1 lines above", "BIQ-END/1 … was emitted with exactly 2 record lines" — while carrying no actual record or terminator line. The other two carried the lines inline and parsed cleanly | Both failed closed, correctly and with no fabrication (`retrieval_unavailable`: once `MALFORMED_RECORD` because a prose sentence containing `BIQ-END/1 <op> 2` is not a terminator, once `NO_TERMINATOR`). So this costs a retrieval, never correctness. But a ~50% loss rate on a one-dispatch-per-retrieval contract is expensive, and `/industry-research --focus full` is five retrievals | **New in M10.2-R live.** Open — the parser is behaving exactly as ADR-0017 designed; the gap is between what the scout *writes* and what its hand-back *delivers*, which is runtime behaviour this repo's Python cannot reach. Recovery is possible without re-retrieving: asking the completed agent to restate its already-composed lines, with no new search, produced a clean parse on the first attempt. Whether `agents/biq-research-scout.md` should state that the record lines must be the **final** output — not merely present somewhere in the turn — is an owner decision about the agent contract. **M10.2-R.1 boundary:** the restatement recovery used in the M10.2-R live session — asking the completed agent to restate already-authored lines with no new search — is **not** accepted behaviour and must not be treated as a sanctioned retry. Malformed scout output fails closed and no evidence is accepted from it. A future live verification must either receive valid `BIQ-REC/1` + `BIQ-END/1` on **first** delivery, or an approved recovery protocol must be defined in its own milestone first. R-12 remains open |
| R-11 | **Open policy question:** whole-namespace source-tier elevation. `TIER_A_PATTERNS` elevates the entire `.gov`, `.gov.uk`, `.mil` and `.europa.eu` namespaces, and `TIER_B_PATTERNS` the whole of `.ac.uk` and `.edu` — not merely the named institutions within them | Any host in those registry-controlled zones is quotable as fact (A) or with attribution (B). A student page under a university domain currently carries the same tier as the institution's research office | **Raised by M9-C.6, deliberately not changed there.** That milestone was a security correction to *how* patterns are matched; altering *which* namespaces are trusted is a policy decision belonging to the owner. Boundary matching now makes these namespaces mean what they appear to mean, which is the defensible reading. Narrowing them would be a separate, deliberate change |
| R-13 | **The local verifier MCP server is launched with a bare `python`.** `.mcp.json` starts `biq-verifier` as `"command": "python"` rather than through the engine's interpreter resolver (`lib/biq_run.sh`, ADR-0045), so on a machine that provides Python 3 only as `python3` the server cannot start. Observed on this WSL2 machine as a failed MCP connection, "Executable not found in $PATH: python" | `--final` verification (`/decision-support`, `/executive-report`) is unavailable where only `python3` exists. The rest of the engine resolves its own interpreter and is unaffected | **New in M14-2, 2026-09-27.** Open. Documented as a limitation in `README.md`; **not fixed**, because the remediation changes `.mcp.json`, which is outside M14-2's documentation scope. No workaround is recorded in the repository. Not an M13 defect-register entry: the register is ADR-0039 §G.1's M13 register. See `docs/development/2026-09-27-m14-2-readme-redesign.md`. **M14-4 investigation (2026-09-27): still open — OWNER DECISION.** The portable remediation is identified: launch the server through the existing resolver (`sh` + `lib/biq_run.sh`, ADR-0045), as the hooks already do. It is not applied, because it changes the `.mcp.json` entry that ADR-0035 declared after the Connector gate, and that `tests/unit/test_m11_verification_server.py` and `tests/connector_fixtures.py` pin as "the approved entry". It also needs a server entry mode in the launcher. The impact is limited to `--final`; drafts are unaffected. Documented in `docs/troubleshooting/README.md` **RESOLVED 2026-09-27 (M14-5, checkpointed `57e92fa`), under ADR-0052.** `.mcp.json` now declares `sh "${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh" --verifier`, and `lib/python/biq_run.py` gained an exact `--verifier` entry behind the same layout check and import boundary. The two tests that pinned the old entry now pin the new one. `unit.test_m11_verification_server.DeclaredEntry` starts the declared entry on a PATH holding only `python3` and completes a real recomputation. **Live:** on this python3-only host, `claude --plugin-dir <repo> mcp list` reports `plugin:businessiq:biq-verifier … ✔ Connected`, and each fresh M9 smoke session reported the server `connected`. |
| R-14 | **`README.md` misstates the forecast minimum history.** M14-2 recorded `forecast.min_history_periods` (12) as unused by the engine. That is incorrect: `forecast/engine.py` `forecast_series()` reads it, and refuses any target with fewer periods as `insufficient_data`. Re-verified 2026-09-27 on a synthetic 8-period CSV in the session scratchpad: "8 periods of history; 12 are required". `README.md` (*Forecasting and anomaly detection*) said, until the M14-3 follow-up correction, that with fewer than six periods a method is still chosen and marked unvalidated. Under the default configuration that path is unreachable. `commands/revenue-forecast.md` ("default 12 periods") is correct | A reader of `README.md` may expect a short-history forecast that the engine will refuse. The engine behaviour itself is sound and fails closed | **Closed 2026-09-27 (M14-3 follow-up), documentation.** *As first recorded (M14-3):* open, and not fixed there, because M14-3 could not change `README.md` and M14-2's record is append-only. *Resolution:* a separate, narrowly scoped owner-approved correction replaced the inaccurate `README.md` sentence. The README now states the engine's behaviour. A forecast needs at least the configured minimum history, `forecast.min_history_periods`. The shipped default is 12 periods (`config/businessiq.defaults.json`). A shorter history returns an insufficient-data result and produces no forecast. The value can be overridden through the existing configuration hierarchy (command, project, user, shipped defaults; `lib/python/biq/config.py`). Validated: `git diff -- README.md` is limited to that bullet; `git diff --check` is clean; `unit.test_manifest` and `negative.test_m12b_connector_security` pass (93 tests). **No forecast-engine or configuration change was required.** `docs/commands/forecasting-and-anomalies.md` states the same rule. See `docs/development/2026-09-27-m14-3-component-documentation.md` §17 |
| R-15 | **Built capabilities are described as future in product text.** `lib/python/biq/commands/query.py` `OUT_OF_SCOPE` makes `/ask-business-data` answer a forecasting, anomaly or research question with "BusinessIQ does not do yet — it arrives in Milestone 8" (or 9). Re-observed 2026-09-27 on the demo data. The same stale wording is in `commands/business-health.md` ("those commands do not exist yet"), `commands/cash-flow-analysis.md` ("arrives in a later milestone"), five command files and `skills/biq-industry-research/SKILL.md` ("`biq-strategy-recommendations` (Milestone 10)") | Users are told built capabilities do not exist. It fails safe: nothing is estimated, and the owning commands work | **New in M14-4, 2026-09-27.** Open, product surface. **Not fixed:** it is engine, command and skill text, outside M14-4's documentation scope; the router's milestone wording is pinned by tests (`tests/integration/test_commands_m7.py`, `tests/negative/test_commands_negative.py`, `tests/unit/test_command_registry.py`), so the fix needs a test change too. `docs/troubleshooting/README.md` documents the workaround of using the owning command. Fixing it before release is recommended; this is an **owner decision** **RESOLVED 2026-09-27 (M14-5, checkpointed `57e92fa`).** The router now names the owning command (`/revenue-forecast`, `/anomaly-detection`, the research commands or `/benchmark-comparison`), never a milestone. The KPI lifetime-value caveat, the gate's destination refusal and the retrieval-unavailable message were corrected. So were the 7 command files and `skills/biq-industry-research/SKILL.md`, and `ask-business-data.md` now says "which command owns it". The 4 assertions that pinned the old wording now assert the owning command and the absence of "Milestone"; each fails if the old wording returns. Four developer-only module docstrings keep historical milestone wording; users never see it. |
| R-16 | **One margin movement renders with two different roundings.** `lib/python/biq/analytics/findings.py` formats the half-over-half margin movement with `%.2f`, while `analytics/domain.py` and `render/executive.py` quantise with `ROUND_HALF_UP`. On the demo data `/business-health` shows -2.84 percentage points and `/profitability-analysis` -2.85pp, for a true movement of about -2.845 | Cosmetic, at the second decimal. It is inconsistent with `CLAUDE.md` §4's single presentation rounding | **New in M14-4, 2026-09-27.** Open, product, minor, non-blocking. Not fixed (engine code) **RESOLVED 2026-09-27 (M14-5, checkpointed `57e92fa`). The root cause recorded above was wrong.** At full precision the movement is -2.8454, so **-2.85 was correct**. `pipeline.py` averaged monthly margins that `sales.margin_series()` had already rounded to 2 dp, which rounds twice (`CLAUDE.md` §4). It now averages the full-precision `segmentation.margin_by_period()` series, as the financial analysis does. The `%.2f` renderings in `analytics/findings.py` and `materiality.py` now use the canonical half-up quantisation. `unit.test_m14_5_margin_rounding` covers this, and fails when the old aggregation is restored. On the demo data, both commands report -2.85, and no other demo output changed. |
| BOPS-K1 | **The Windows `python3` App Execution Alias is picked up as an interpreter.** On the development host, `python3` resolves to the Microsoft Store alias, which prints "Python was not found; run without arguments to install from the Microsoft Store...". Claude Code reported this as repeated non-blocking hook errors during the 2026-09-30 audit. Environment, not a migration change | Hook noise; a host without a real `python` could fail to start the guard | Root cause found in BOPS-M2: the message comes from other plugins installed on the development host (`hookify`, `rideops`), whose hooks run bare `python3`. BusinessOps' hook runs `sh`, and its resolver tries `python` first and discards probe stderr, so it cannot print that message. Local environment only; no BusinessOps change needed. The separate native-Windows risk is BOPS-R4 |
| M13-DEF-01 | Two skill descriptions exceed the 1,024-character hard limit of `architecture.md` §2 / ADR-0013: `biq-competitor-analysis` 1,065, `biq-industry-research` 1,158 | Outside the documented platform limit. `claude plugin validate --strict` still passes | **Found by M13.1 (D.2), 2026-09-18.** Open, product. Recorded, **not fixed** in M13 (ADR-0039 I-13). Remediation milestone **unassigned**, deferred to the owner (§G.2): no planned milestone's scope includes it, including M14's. Re-verified 2026-09-18. See `docs/testing/defects.md` **RESOLVED 2026-09-27 (M14-5, checkpointed `57e92fa`): `fixed_product` (ADR-0043), under ADR-0013.** The two descriptions are now 992 and 1,010 characters; wording was trimmed, and every trigger phrase and constraint is kept. The limit assertion is committed. See `docs/testing/defects.md`. |
| M13-DEF-02 | The D.1 measurement read ledger caveats from the wrong key | A false D.1 failure | **Found and fixed by M13.1**, 2026-09-18: infrastructure, `fixed_infrastructure`, resolved. Test-only fix, recorded with before and after. Not a product defect |
| M13-DEF-03 | A CSV above 100,000 rows is read and computed in full but labelled `streamed` and incomplete: "Only 250000 of 250000 rows were examined", revenue KPI `partial`, quality grade `WARNING` | Inaccurate provenance and caveats on large files. Conservative: it never presents a sample as a full pass | **Found by M13.1 (D.1), 2026-09-18.** Open, product. Recorded, **not fixed** in M13; contradicts `architecture.md` §17 and M3's "mode is recorded correctly". Coverage row S1-17 is `gap`. Remediation milestone **unassigned**, deferred to the owner (§G.2). It relates to M3's chunked-streaming deferral, which no milestone schedules. Re-verified 2026-09-18 at 100,001 rows. See `docs/testing/defects.md` **RESOLVED 2026-09-27 (M14-5, checkpointed `57e92fa`): `fixed_product` (ADR-0043).** `canonical.build()` records `full` for a fully materialised pass at any size. `integration.test_m14_5_processing_mode` runs the reproducer at 100,001 rows. Chunked streaming itself remains the M3 deferral. See `docs/testing/defects.md`. |
| M13-DEF-04 | The engine entry in 10 commands and 11 skills, `sys.path.insert(0, 'lib/python')`, is relative to the session's working directory, and 5 skills import `biq` with no path setup. From any directory other than the plugin root, the entry raises `ModuleNotFoundError: No module named 'biq'` | An installed plugin (marketplace distribution, `architecture.md` §2) used from the user's own directory (§13) cannot reach its engine through the documented entry. It blocks meaningful M13.2 manual observation of S3-01 to S3-11. M9's live smoke tests run under the same entry | **Found by the M13.2 WD-1 investigation, 2026-09-19. RESOLVED 2026-09-20, committed in `8287e98`**, by the dedicated M13-DEF-04 remediation milestone, which is outside M13 (I-13). Accepted ADR-0042's launcher `lib/python/biq_run.py` is implemented, and 10 commands and 16 skills enter the engine only through `python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py" -c …`. Verified by T-A to T-K (`integration.test_m13_def04_engine_entry`, `unit.test_m13_def04_static_guard`) and the full regression. The import-hijack path is closed. Register status **`fixed_product`** under ADR-0043 (accepted 2026-09-20), which amends ADR-0039 §G.1's vocabulary. Still open: G-3, V-4, and Unix-like runtime verification. See `docs/testing/defects.md` and `docs/development/2026-09-20-m13-def-04-implementation.md` |
| M13-DEF-05 | The M13.2 eval suite does not load in `claude plugin eval`. **Root cause established 2026-09-22:** the suite is written in a repository-local format the platform does not accept — four structural mismatches, of which the refused `schema_version` was only the first | M13.2's automated evaluation cannot proceed. It is M13's own infrastructure, not product behaviour; BusinessIQ's runtime is unaffected | **Found by the first owner-authorised execution, 2026-09-20** (one attempt, not retried). Open, infrastructure, `blocks_m13_completion: yes` by rule — **it blocks M13.2 completion**. An infrastructure defect may be fixed within M13 (§G.2) under its own prompt, together with the G-3 questions it exposes. **ADR-0044 accepted 2026-09-22 and Phase 1 implemented the same day**: all 64 cases dual-layered, 109 of 133 graders translated, 61 of 64 cases platform-loadable. **24 graders and 3 cases stay pending** on the trace tool name a plugin slash command fires under, which stage 2's pilot settles — it was not guessed. **CLOSED 2026-09-25 as `fixed_infrastructure`, `blocks_m13_completion: no`:** its stated condition is met — on Claude Code 2.1.281 the platform loaded 64 of 64 case files across the five closing invocations with zero case-load or contract errors. See `docs/testing/defects.md`, `docs/development/2026-09-22-m13-def-05-adr-0044-phase1.md`, `docs/development/2026-09-22-m13-def-05-investigation.md` and `docs/development/2026-09-20-m13-2-e1-execution.md` |
| M13-DEF-06 | A run the platform refused before its first turn was scored and reported as a **pass** (`turns: 0`, an error in the run record, an empty trace, and a negatively-worded LLM grader that passes vacuously against an empty transcript) | M13's evidence model treats `automated_pass` as proof a case ran. Without a guard, a refused run could enter the repository as a green result — most dangerously in the safety and approval cases | **Found by the Stage 2 pilot, 2026-09-22. Fixed the same day.** `fixed_infrastructure`, `blocks_m13_completion: no`: `tests/unit/test_m13_eval_results.py` classifies every result deterministically and admits one only if its run executed. The platform's scoring is unchanged and no longer reaches the record. See `docs/testing/defects.md` and `docs/development/2026-09-22-m13-def-06-remediation.md` |
| M13-DEF-07 | A `requires_business_file` eval case could not reach the file it declares: the run directory is not the repository, so a repository-relative path does not resolve, and no case had the scaffold ADR-0039 §F.6 permits. The static validator actively forbade that scaffold, being stricter than the ADR it implements | Every file-reading eval case fails for an evaluation-infrastructure reason before it reaches the behaviour under test. M13 infrastructure only; BusinessIQ runtime unaffected | **Found by the 2026-09-22 one-run pilot. Fixed the same day**, test-and-case-only. `fixed_infrastructure`, `blocks_m13_completion: no`: the pilot case declares `context.scaffold_script`, `evals/approval/a01-read-only-anomaly-detection/scaffold.sh` copies its one declared input, `unit.test_m13_eval_cases.Scaffold` is the §F.6 assertion, and `integration.test_m13_eval_scaffold` proves the staging under the harness invocation. **Scope: 1 case staged, 37 still waiting**, asserted by `UNSTAGED_COUNT`. See `docs/testing/defects.md` |
| M13-DEF-08 | BusinessIQ's 10 engine commands and 16 engine skills entered the engine as `python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py"`, the form accepted in ADR-0042. This Ubuntu/WSL2 machine has no `python` on `PATH` — only `/usr/bin/python3` (Python 3.14.4), with `python-is-python3` not installed | **Product, not infrastructure.** No BusinessIQ command could enter the engine on this platform, for a real user as much as for the evaluator. Distinct from R-03: Python 3 is present, under another name | **Found by the 2026-09-22 pilot. RESOLVED 2026-09-22, committed in `8287e98`**, by the owner-authorised M13-DEF-08 remediation outside M13 (I-13, §G.2). Owner selected Option C; **ADR-0045** accepted and implemented the same day: `lib/biq_run.sh` is the one place an interpreter is chosen, 26 files and 34 blocks migrated, 66 new tests, 4 mutations each caught, ADR-0042's launcher and isolation untouched. Register status **`fixed_product`** (ADR-0043), `blocks_m13_completion: no`. **Not claimed:** Windows/macOS execution (simulated tests only). **Still open:** the eval `--allow-tools` grant, since the first token is now `sh`. Satisfies M13-DEF-04's open "Unix-like runtime verification" on Linux/WSL2. See `docs/testing/defects.md` and `docs/development/2026-09-22-m13-def-08-runtime-resolution.md` |
| M13-DEF-09 | The 2026-09-22 pilot kept no trace, because the procedure named no diagnostic flag, so the one fact ADR-0044 stage 2 exists to settle could not be read from a paid run. Separately, the harness wrote `evals/results/` by default, which broke three §E.5 layout assertions | Trace-dependent grader mappings cannot be completed, so the 24 pending graders and M13-DEF-05 stay open; and a run left the static validator failing | **Found 2026-09-22 after the pilot. Fixed the same day**, documentation-and-test-only. `fixed_infrastructure`, `blocks_m13_completion: no`: `docs/testing/eval-suite.md` now requires `--keep-temp` and states what the preserved sandbox is read for, and the layout assertions step over the generated, gitignored `results/`. The 24 graders stay pending and none was written from inference. See `docs/testing/defects.md` |
| M13-DEF-10 | The evaluation grant set permitted the ADR-0045 engine call but not the read-only discovery step the agent takes first, and in the evaluator's `dontAsk` mode the unmatched call was denied rather than prompted, so the agent stopped before invoking the resolver. **`Read` was never permitted either**: the harness computes read scopes only when the operator grant list holds a bare read tool, and the pilot passed only the patterned `Bash` resolver grant | The case could not reach the behaviour under test, so S3-11 and S5-01 stay behaviourally untested. **Evaluation configuration only** — no product file is implicated | **Found by the three-run pilot 2026-09-22; deterministically corrected 2026-09-23.** `fixed_infrastructure`, `blocks_m13_completion: no`. The authorised set is now exactly `Read` and `Bash(sh <plugin path>/lib/biq_run.sh:*)`; the resolver grant is unchanged, `Bash(ls:*)` is recorded as considered and rejected because it keeps discovery inside the shell, and no prompt was changed. Held by 30 assertions in `unit.test_m13_def10_eval_grant`. **Not live-verified:** no evaluation was run, and the case remains `automated_fail`. See `docs/testing/defects.md` and `docs/development/2026-09-23-m13-def-10-remediation.md` |
| M13-DEF-11 | `claude plugin eval` builds a per-command sandbox for the plugin under test, and that sandbox cannot initialise when the evaluator is launched from an **already-sandboxed outer Claude Code session**: it fails `EPERM` creating its control socket, and the evaluator then correctly refuses to run a granted shell command unconfined | The BusinessIQ engine cannot be reached, so S3-11 and S5-01 stay behaviourally untested, even though the case, scaffold, grant set, mapping and runtime are all now shown correct. **Environment only** — no repository file is implicated | **Found by the third owner-authorised evaluation, 2026-09-23; reproduced 3 of 3 runs.** *Current status (reconciled 2026-09-27, M14-1, per the defect register):* **`fixed_infrastructure`, `blocks_m13_completion: no`**, environment-only. *As first recorded:* open, infrastructure, `blocks_m13_completion: yes` by rule. Diagnosed with no further evaluation: an `AF_UNIX` `bind`+`listen` fails `EPERM (errno 1)` in a sandboxed session and succeeds with the outer sandbox off. **Remediation: one operator action** — set the outer session to `No Sandbox` with `/sandbox`, keeping the evaluator sandbox enabled (`failIfUnavailable: true`, `allowUnsandboxedCommands: false`). No bypass, and no repository change. The evaluator generates its own child settings, so its enforcement is unaffected. **An ADR-0040 alternative treatment is raised for the owner** in the full record. See `docs/testing/defects.md` and `docs/development/2026-09-23-m13-def-11-environment-diagnosis.md` |
| M13-DEF-12 | On WSL2 the runtime resolver's Windows executable-suffix search (`.exe`, `.com`, `.bat`, `.cmd`), added for Git Bash, resolves through WSL interop to a **Windows** interpreter: it selects `/mnt/c/Python313/python.exe`, which passes the version probe because it is genuinely Python 3.13, then cannot address the Linux engine path | `sh lib/biq_run.sh --where` exits **2** with `python.exe: can't open file 'D:\\mnt\\d\\...'`. **Product, not evaluation** — it reaches any WSL2 user with Windows Python on `PATH`, a common configuration. Blocks the next evaluation in practice, though not M13 completion by rule | **Found by the final pre-flight and RESOLVED the same day, 2026-09-23, committed in `8287e98`.** Remediated under accepted **ADR-0046** (amends ADR-0045 in part; ADR-0045 unedited): under WSL the automatic search skips the Windows suffixes, while `BIQ_PYTHON`, native Windows and native Linux are unchanged. 11 effective lines, 15 tests, 3 mutations each caught, full regression green, and live automatic resolution now selects `/usr/bin/python3`. Register status **`fixed_product`** (ADR-0043), `blocks_m13_completion: no`. **Not claimed:** any evaluation result, or native Windows/macOS execution. Found by, immediately after the outer sandbox was disabled; masked before that because the sandbox hid the 25 `/mnt/c` `PATH` entries, so every prior ADR-0045 verification saw only `/usr/bin/python3`. Open; **M13 does not fix product defects** (I-13, §G.2) and the finding task was forbidden from modifying the resolver. `BIQ_PYTHON=/usr/bin/python3` is an existing, documented workaround that returns exit 0. **An owner decision.** See `docs/testing/defects.md` and `docs/development/2026-09-23-m13-2-final-preflight.md` |
| M13-DEF-13 | **Tier-3 disclosure boundary.** In all 3 runs of `d05`, the customer name "Fenwick Provisions" passed the disclosure gate into `biq-research-scout` dispatch queries ("2026 Fenwick Provisions trends", "Fenwick Provisions company profile") | A Tier-3 identifier crossed the internal research-dispatch boundary, where `CLAUDE.md` §8 requires refusal with no approval path. No order-history figure was sent and nothing left the machine, because the scout had no web tools | **RESOLVED 2026-09-26: `fixed_product` (ADR-0043), verified deterministically, committed in `595e910`, not live-verified.** ADR-0050: the gate establishes each request fragment's provenance from the working directory's business data. A `never` value never goes, and other non-public values never go at Tier 0. 32 tests and the full regression pass. See `docs/development/2026-09-26-m13-def-13-remediation.md`. *History:* **Found by the M13.2 closing evaluation, 2026-09-24.** Open, product, `blocks_m13_completion: no` by rule. Recorded, **not fixed** in M13 (I-13). Remediation milestone **unassigned**, deferred to the owner (§G.2). Privacy-boundary defect; the owner asked for it to block, and the register's enforced rule permits `yes` only for open infrastructure defects. See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` |
| M13-DEF-14 | Read-only analysis asks for approval or confirmation, in 11 approval cases and `d01` to `d04` | Contradicts `CLAUDE.md` §9 / ADR-0010 (read-only work needs no approval). 22 of the 37 failing runs involve no evaluator denial; 15 followed a denial of an out-of-grant shell command | **Found by the M13.2 closing evaluation, 2026-09-24.** Open, product, `blocks_m13_completion: no` by rule. Recorded, **not fixed** in M13 (I-13). Remediation milestone **unassigned**, deferred to the owner (§G.2). See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` **Reviewed in M14-5 (2026-09-27): stays open; non-blocking known limitation.** It is model behaviour in the workflow, not deterministic code, and a fix could be verified only by a live evaluation, which M14-5 excludes. It errs toward caution: an unnecessary confirmation, never an unapproved write. Documented in `README.md` *Limitations* and the troubleshooting guide. **Owner decision 2026-09-28 (M15-1): accepted as a known limitation for 0.1.0**, and stated in `docs/releases/0.1.0.md`. The defect stays `open` in the register. |
| M13-DEF-15 | Refusal and limitation responses omit a required statement: no clarifying question (`b01`), no "No reliable source found" (`b05`, `d01` to `d04`), no explicit block or no-path refusal (`c04`, `c05`, `d06`) | The substance is often right but the §16 contract wording is absent | **Found by the M13.2 closing evaluation, 2026-09-24/25.** Open, product, `blocks_m13_completion: no` by rule. Recorded, **not fixed** in M13 (I-13). Remediation milestone **unassigned**, deferred to the owner (§G.2). See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` **Reviewed in M14-5 (2026-09-27): stays open; non-blocking known limitation.** It is model behaviour in the workflow, not deterministic code, and a fix could be verified only by a live evaluation, which M14-5 excludes. The substance was usually right, and the required statement was missing. Documented in `README.md` *Limitations* and the troubleshooting guide. **Owner decision 2026-09-28 (M15-1): accepted as a known limitation for 0.1.0**, and stated in `docs/releases/0.1.0.md`. The defect stays `open` in the register. |
| M13-DEF-16 | A Tier-2 query (`d08`) was refused outright, 3 of 3 runs, instead of halting with the verbatim text for single-use approval | The Tier-2 approval path of `CLAUDE.md` §8 is not offered; the figure was not sent | **Found by the M13.2 closing evaluation, 2026-09-24.** Open, product, `blocks_m13_completion: no` by rule. Recorded, **not fixed** in M13 (I-13). Remediation milestone **unassigned**, deferred to the owner (§G.2). See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` **Reviewed in M14-5 (2026-09-27): stays open; non-blocking known limitation.** It is model behaviour in the workflow, not deterministic code, and a fix could be verified only by a live evaluation, which M14-5 excludes. The gate itself implements the Tier-2 approval path (`ALLOW_WITH_APPROVAL`, ADR-0050), and the model over-refused; nothing was sent. It fails closed. Documented in `README.md` *Limitations* and the troubleshooting guide. **Owner decision 2026-09-28 (M15-1): accepted as a known limitation for 0.1.0**, and stated in `docs/releases/0.1.0.md`. The defect stays `open` in the register. |
| M13-DEF-17 | Skill-routing graders require `input_match: biq-<skill>`, so command-only routes fail (`r01`, `r07`, `r08`, `r10`, `r13`, `b04`) even when the engine ran | Routing failures may be grader-contract failures; production routing must not be changed to satisfy them | **Fixed 2026-09-25 under ADR-0047** (owner Decision 1): `fixed_infrastructure`, `blocks_m13_completion: no`, not live-verified; 23 routing graders accept the skill or its owning command. **Remediation attempted 2026-09-25 and blocked on an owner decision**; still open, `blocks_m13_completion: yes` by rule. Needs an ADR amending ADR-0044's `skill_invoked`/`skill_not_invoked` mapping. **Found by the M13.2 closing evaluation, 2026-09-25.** Open, evaluation infrastructure, `blocks_m13_completion: yes` by rule — **it blocks M13.2 completion**. May be fixed within M13 under its own prompt (§G.2); not fixed by the recording task. The affected cases would then need a new authorised evaluation. See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` |
| M13-DEF-18 | Bash tool-count graders (`a20`, `a21`) count the permitted engine resolver calls as prohibited activity | A correct run necessarily calls Bash, so these graders cannot pass as written | **Fixed 2026-09-25**, eval-graders-and-tests-only: `fixed_infrastructure`, `blocks_m13_completion: no`, **not live-verified** (no evaluation run; affected cases need a new authorised evaluation). **Found by the M13.2 closing evaluation, 2026-09-24.** Open, evaluation infrastructure, `blocks_m13_completion: yes` by rule — **it blocks M13.2 completion**. May be fixed within M13 under its own prompt (§G.2); not fixed by the recording task. The affected cases would then need a new authorised evaluation. See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` |
| M13-DEF-19 | `a20`'s scaffold never stages the `README.md` the case protects | The overwrite-approval scenario was not exercised | **Fixed 2026-09-25 under ADR-0048** (owner Decision 2): `fixed_infrastructure`, `blocks_m13_completion: no`, not live-verified; `a20` stages fixture EVI-04 as `README.md`. **Remediation attempted 2026-09-25 and blocked on an owner decision**; still open, `blocks_m13_completion: yes` by rule. ADR-0041 admits CSV fixtures only, and the scaffold rule stages inputs at their own paths. **Found by the M13.2 closing evaluation, 2026-09-24.** Open, evaluation infrastructure, `blocks_m13_completion: yes` by rule — **it blocks M13.2 completion**. May be fixed within M13 under its own prompt (§G.2); not fixed by the recording task. The affected cases would then need a new authorised evaluation. See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` |
| M13-DEF-20 | `d08` `g-nothing-dispatched` is a regex on the final message and fails when the text names `biq-research-scout`, although no agent was dispatched | False failure on a safety grader | **Fixed 2026-09-25**, eval-graders-and-tests-only: `fixed_infrastructure`, `blocks_m13_completion: no`, **not live-verified** (no evaluation run; affected cases need a new authorised evaluation). Root cause corrected: the old regex matched the init event's agent roster. **Found by the M13.2 closing evaluation, 2026-09-24.** Open, evaluation infrastructure, `blocks_m13_completion: yes` by rule — **it blocks M13.2 completion**. May be fixed within M13 under its own prompt (§G.2); not fixed by the recording task. The affected cases would then need a new authorised evaluation. See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` |
| M13-DEF-21 | `b02` `g-no-separated-figure` matches any comma-grouped number and failed on the default materiality threshold `10,000` | False failure on a correct `CRITICAL` halt | **Fixed 2026-09-25**, eval-graders-and-tests-only: `fixed_infrastructure`, `blocks_m13_completion: no`, **not live-verified** (no evaluation run; affected cases need a new authorised evaluation). **Found by the M13.2 closing evaluation, 2026-09-24.** Open, evaluation infrastructure, `blocks_m13_completion: yes` by rule — **it blocks M13.2 completion**. May be fixed within M13 under its own prompt (§G.2); not fixed by the recording task. The affected cases would then need a new authorised evaluation. See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` |
| M13-DEF-22 | Agent-dispatch graders fail on any `Agent` call regardless of query content (`d04` run 2, a public query) | Tier-0 dispatch by design fails the grader | **Fixed 2026-09-25**, eval-graders-and-tests-only: `fixed_infrastructure`, `blocks_m13_completion: no`, **not live-verified** (no evaluation run; affected cases need a new authorised evaluation). **Found by the M13.2 closing evaluation, 2026-09-24.** Open, evaluation infrastructure, `blocks_m13_completion: yes` by rule — **it blocks M13.2 completion**. May be fixed within M13 under its own prompt (§G.2); not fixed by the recording task. The affected cases would then need a new authorised evaluation. See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` |
| M13-DEF-23 | LLM-judge votes split on the same run (`a10`, `a13`, `c02`, `c03`, `d05`, `d07`); `c02`, `c03` and `d07` failed on split votes alone | Some case classes rest on a two-to-one vote | **Fixed 2026-09-25 under ADR-0049** (owner decision): `fixed_infrastructure`, `blocks_m13_completion: no`, not live-verified; a semantic judge split is `execution_unavailable`, not a pass or a fail. **Second remediation 2026-09-25** (owner Decision 3): `d07` converted, five semantic judges retained; still open, blocking by rule, pending an ADR-0039 §E.6 decision on split verdicts. **Remediation attempted 2026-09-25 and blocked on an owner decision**; still open, `blocks_m13_completion: yes` by rule. Split votes are now represented explicitly and never converted; a remedy needs a policy decision. **Found by the M13.2 closing evaluation, 2026-09-24/25.** Open, evaluation infrastructure, `blocks_m13_completion: yes` by rule — **it blocks M13.2 completion**. May be fixed within M13 under its own prompt (§G.2); not fixed by the recording task. The affected cases would then need a new authorised evaluation. Not a product defect. See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-closing-evaluation-record.md` |
| M13-DEF-24 | Asked to replace an existing file (`a20`, `README.md`), the workflow attempted the overwrite without requesting explicit approval in 2 of 3 runs, and asked for none in all 3 | Contradicts `CLAUDE.md` §9: overwriting any existing file needs explicit per-action approval. The evaluator denied the writes, so no file changed | **RESOLVED 2026-09-26: `fixed_product` (ADR-0043), with deterministic evidence, runtime hook (deny) evidence and runtime approval/grant evidence on Claude Code 2.1.283; committed in `595e910`, no plugin evaluation or `a20` rerun.** ADR-0051 adds a plugin-wide `PreToolUse` write guard, scoped to sessions that engage BusinessIQ. An allowlist classifier denies a consequential write before it runs unless the user granted that exact operation with `approve BIQ-W-…` in their own prompt; the grant is single-use and bound to session, tool, input digest, target, kind and existence. An engine execution guard enforces the same policy inside every engine process. The exact a20 heredoc is denied through the production hook path, and the file is unchanged. 92 new tests, 7 of 7 mutations caught, and the full regression pass. See `docs/development/2026-09-26-m13-def-24-remediation.md`. A seven-turn live session proved the approval path: deny, then the user-message approval, then the exact retry executing once; retarget, operation change, reuse and a subagent-carried approval were all refused (`docs/development/2026-09-26-m13-def-24-live-grant-verification.md`). Known limits: no `UserPromptSubmit` `source` field in 2.1.283, a scripted user-message feeder, `/tmp` treated as free scratch, and a marketplace install and `plan` mode unmeasured. *Earlier, 2026-09-26:* remediation blocked pending a measured runtime fact and an ADR (`docs/development/2026-09-26-m13-def-24-investigation.md`); the runtime experiment then measured it (`docs/development/2026-09-26-m13-def-24-hook-runtime-experiment.md`). *History:* **Found by the 2026-09-25 34-case re-evaluation.** Open, product, `blocks_m13_completion: no` by rule. Recorded, **not fixed** in M13 (I-13). Remediation milestone **unassigned**, deferred to the owner (§G.2). See `docs/testing/defects.md` and `docs/development/2026-09-25-m13-2-reevaluation-34-cases.md` |

## Documentation debt

| ID | Item | Found | Status |
|---|---|---|---|
| D-01 | The 13 quality-family taxonomy is not enumerated in `architecture.md` | M4 | Open — recorded, not resolved; amending approved architecture is an owner decision |
| D-02 | The 27-KPI taxonomy is not enumerated in `architecture.md` | M5 | Open — same pattern as D-01 |
| D-03 | Result-bucket names differ between `architecture.md` section 6 (`computed`/`partial`) and the M5 brief (`available`/`insufficient_data`) | M5 | Open — both implemented, `COMPUTED` aliases `AVAILABLE`; reported for review |
| D-04 | `net_revenue_retention` is implemented but is not among the approved 27 | M5 | Open — retained from M2, declared separately in `BEYOND_APPROVED` |
| D-05 | `PipelineResult.as_dict()` is not JSON-serialisable: the M2 `analysis` dictionary carries raw `Decimal` values | M6 | Open — pre-existing, found not caused by M6; every M6 `AnalysisSet` and M7 `CommandResult` is serialisable and tested to be |
| D-06 | The 17-command taxonomy is not enumerated in `architecture.md` | M7 | Open — third instance of the D-01/D-02 pattern; `project_plan.md` does enumerate the seven M7 commands |
| D-07 | `CLAUDE.md` line 87 points at `architecture.md` section 4 for command names; section 4 is the skill architecture and names no commands | M7 | Open — `CLAUDE.md` is governance; amending it is an owner decision |
| D-08 | The M6 cohort finding renders "(1 customers)" | M7 | Open — cosmetic; found while rendering commands but it is M6 code, left alone per the M7 no-unrelated-changes instruction |
| D-09 | The milestone summary lists M8 as depending on **M5** only | M8 | Open — M8 in fact consumes M3 (canonical dataset, privacy), M4 (quality gate), M6 (materiality, evidence, presentation) and M7 (command layer). Implemented against the real dependency set; the plan's dependency column is owner-governed and was not edited |
| D-11 | ADR-0017 and ADR-0018 are referenced in `architecture.md` prose but appear in neither ADR index — `docs/decisions/README.md` nor `architecture.md` § 19 | M9-D.2 | Open — pre-existing, found while indexing ADR-0019, which *was* added to both. Correcting the two earlier omissions is an unrelated documentation change and was left alone per the M9-D.2 no-unrelated-changes instruction |
| D-12 | `architecture.md` § *The synthesis layer* does not describe the **seven-dimension compatibility test**, although it is one of that layer's load-bearing invariants and `project_plan.md` lists it as an M10.1 deliverable. The section covers kinds, domain, internal footing, the retrieval seam, provenance, support, conflicts, materiality, limitations and confidence — but not the rule that decides whether two figures may be related at all | M10.2-R live | Open — fourth instance of the D-01/D-02/D-06 pattern. Deliberately **not** fixed here: nothing architectural changed in this task, and amending approved architecture is an owner decision. Flagged because this omission is an invariant rather than a taxonomy, so it sits closer to a defect than the earlier three |
| D-13 | `architecture.md` §4 enumerates **20 skills**, but five are neither built nor scheduled by any milestone: `biq-business-context` (a follow-up ADR-0011 requires), `biq-semantic-mapping` ("later milestone", M3), `biq-data-quality`, `biq-kpi-engine` and `biq-external-research` (M9 row `PLANNED`). Sixteen skills are built, including `biq-benchmark-comparison` (ADR-0029), which is not among the 20. The engines behind all five exist | Post-M12-B gate | Open — **owner decision**: schedule them, or retire them by ADR. The owner confirmed on 2026-09-18 that D-13 **does not block M13** (ADR-0039 I-9). M13 neither builds nor schedules them. ADR-0039's routing cases cover the built set, and any later component brings its own cases. **Documentation part reconciled by M14-3 (2026-09-27, checkpointed `8e4ab17`):** `docs/skills/README.md` carries the component-by-component design-to-shipped mapping. 15 of the 20 designed skills ship; the five above do not, and each one's engine exists and runs inside the commands; `biq-benchmark-comparison` ships outside the design. So 20 − 5 + 1 = 16. The design, `architecture.md` §4 and the plan statuses are unchanged. **The owner decision remains open:** schedule each of the five, or retire it by ADR |
| D-14 | Current-status banners are stale outside `project_plan.md`. `README.md` says "Milestone 7 of 14" and lists the connector layer as not built. `architecture.md`'s header says "Milestone 1 (Foundation) implemented". `docs/README.md`'s development-history list stops at Milestone 7. `docs/decisions/README.md` omits ADR-0017, 0018, 0023 and 0024, and `architecture.md` §19 omits 0017 and 0018 (extends D-11) | Post-M12-B gate | Open — **deferred to Milestone 14** (Documentation & Release) by owner decision on 2026-09-18. **Partly reconciled by M14-1 (2026-09-27):** the `architecture.md` header, the `docs/README.md` history note and ADR list, and the ADR omissions in `docs/decisions/README.md` and `architecture.md` §19. The `README.md` banner remains, for M14-2. **The `README.md` part is addressed by M14-2 (2026-09-27, checkpointed `5c1b15d`):** the milestone banner is replaced by a factual current-status section. It was left unedited by the post-M12-B gate and by the M13 contract finalization, which corrected only what M13's own status consistency required. **Resolved by M14-4 (2026-09-27, checkpointed `57e92fa`):** the remaining stale current-facing index, `docs/development/README.md` (its table stopped at M9-B), now lists every record through M14-4. The `README.md` documentation table no longer marks the examples and troubleshooting guide as "being written". Every part of D-14 is now reconciled |
| D-10 | ADR-0013 prescribes measuring always-on cost with `claude plugin details businessiq`, and lists recording it as a follow-up | M8 review | Open — the command resolves only an *installed* plugin and BusinessIQ is not installed; `--plugin-dir` is not accepted on this CLI version. M6, M7 and M8 all used the same frontmatter-chars ÷ 4 proxy, consistent across milestones but not the ADR's procedure. Installing the plugin changes global user state and is an owner decision. **Resolved by M14-4 (2026-09-27, checkpointed `57e92fa`):** Claude Code 2.1.283 accepts `claude --plugin-dir <repo> plugin details businessiq`, which loads the plugin for one session without installing it. `~/.claude/plugins` was unchanged and `businessiq` remained uninstalled. Measured **~7,321 tokens always-on**, above ADR-0013's self-imposed ≤ 3,000 target. The measurement debt is closed. The response to the overrun is an owner decision (ADR-0013 item 4). **Re-measured in M14-5 (2026-09-27), by the same method:** ~7,260 tokens always-on, after the M13-DEF-01 description trims (-61). Still above the target; the owner decision stands, and ADR-0013's target is unchanged |

**Confirmed in M6:** the M6 component list *is* enumerated in both `project_plan.md` and
`architecture.md` section 4, so D-01 and D-02 are specifically about **taxonomies** (the 13
quality families, the 27 KPIs), not about components generally. That narrows what an
architecture amendment would need to add.

The common root: the product specification that enumerates both taxonomies was never
committed to the repository.

## Deferred

| Item | Reason |
|---|---|
| Chart image rendering | Chart-*ready data* emitted instead. |
| Write-back to business systems | Out of scope for v1 (read-only product). |
| Multi-currency FX conversion | Detection + mismatch warnings in v1; conversion needs a rate source — v2. |
| Benchmark/peer data licensing | Tier 0 uses public sources; licensed panels are v2. |

## Future work

Scheduled recurring reports · board-pack export formats · variance-vs-budget · cohort LTV
modelling · scenario planning workbench · multi-entity consolidation.
