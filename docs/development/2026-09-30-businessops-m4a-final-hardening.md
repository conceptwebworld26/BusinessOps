# 2026-09-30 — BusinessOps Milestone 4A: final hardening before the first Git commit

**Milestone:** BOPS-M4A — Final hardening before the first Git commit
**Status on completion:** REVIEW
**Supersedes:** None

## 1. Prompt / task performed

Make exactly the two hardening fixes the M3.1 review identified, BOPS-R11 and BOPS-R12. Then rebuild and validate
the package, verify MCP from the package, and run a final security check. No architecture, distribution,
reference-path, `.mcp.json`, PowerShell, connector or skill-visibility change. No commit, push, remote or
submission.

## 2. BOPS-R11 — `2>/dev/null` read as a Windows file write

**Cause.** `writeguard/policy.py` `Policy.resolve()` passes an absolute path through `os.path.realpath()`. On native
Windows, `realpath('/dev/null')` is `C:\dev\null` (drive-qualified), which `Policy.is_device()` does not recognise, so
a Bash redirect to `/dev/null` became "create new file" and needed approval. On macOS, Linux and WSL `realpath` keeps
`/dev/null`.

**Why the fix is not in `Policy.resolve()`.** Shell words and file-tool paths share `_Context.resolve()`. In a
**Bash** command on Windows, Git Bash maps `/dev/null` to the null device. The **Write** tool given
`file_path: "/dev/null"` on Windows would really create `C:\dev\null`. A global exception would have let that write
through.

**Fix** (`lib/python/bops/writeguard/classify.py`):

- `_WINDOWS = os.name == "nt"`, a module seam for tests;
- `_Context.shell`, set only while a Bash command line is classified;
- in `_Context.resolve()`, for a literal shell word on Windows that `Policy.is_device()` already admits (`/dev/null`,
  `/dev/stdout`, `/dev/stderr`, `/dev/tty`, `/dev/fd/N`, `/proc/self/fd/N`), the device name is kept instead of the
  `realpath()` result.

Nothing else changes. Off Windows the branch is never taken. File tools are never affected. No path is added to any
allowlist, and the device list is the existing one.

## 3. BOPS-R12 — guard messages cited `CLAUDE.md`

The three user-visible guard strings cited "CLAUDE.md section 9", which the package does not ship:

- the block message in `writeguard/hook.py` `approval_response()`;
- the reasons "original source data is immutable" and "changing an existing file needs explicit approval" in
  `writeguard/policy.py`.

They now cite `(see the BusinessOps README, "Approval and write safety")`, a section of the shipped `README.md` that
describes exactly these rules. Developer docstrings and comments in `lib/` still mention `CLAUDE.md`, but they are
never shown to a user.

## 4. Tests

New, in `tests/unit/test_m13_def24_write_classifier.py`:

- `WindowsShellDevices` (5 tests), with `classify._WINDOWS` switched so both platforms are exercised on any host:
  - device redirects are free on Windows;
  - genuine writes (`notes.txt`, `README.md`, `/dev/nullx`, `/dev/null/x`, `dev/null`, `C:/dev/null`) still need
    approval;
  - a `/dev/null` path given to Write, Edit or MultiEdit still needs approval;
  - every non-device security decision is identical with the branch on and off, and source-data immutability holds
    even beside a device (`tee /dev/null data.csv`);
  - off Windows the result is exactly `realpath()`'s.
- `GuardMessages` (2 tests): the rendered block and deny messages, and every non-docstring string in every
  `writeguard` module, name no developer document. The block message cites the README section.

Affected modules, run with the project runner (`python tests/run_tests.py <module>`):
`integration.test_m13_def24_write_boundary`, `negative.test_m13_approval_boundaries`,
`unit.test_distribution_build`, `unit.test_m13_def24_hook_decision`, `unit.test_m13_def24_write_classifier`,
`unit.test_m14_6_verbatim_handback`, `unit.test_m13_def04_static_guard`, `unit.test_m13_def08_runtime_resolver`.

- There are no failures outside the known Windows baseline set.
- One baseline failure is **resolved**: `RequiredCases.test_17_read_with_shell_syntax_is_not_a_write`
  (`cat file.txt > /dev/null`).

The full suite was not run. The change is confined to one Windows-only branch for Bash device words and two message
strings, and every module that imports or exercises the guard was run.

When the same modules were run from `tests/` rather than the repository root,
`test_the_guard_fails_closed_when_it_cannot_start` failed. That comes from where the tests were run, not from the
fix: on Windows, `bops_guard.sh` derives its root from `$0`. A backslash path contains no `/`, so the wrapper falls
back to the working directory, and from `tests/` that makes the repository the "broken" plugin's root. Under the
project runner the test passes. Claude Code passes `/`-separated paths on Windows, as the M3.1 live hook sessions
show.

## 5. Package, validation and MCP

Evidence: [`docs/testing/evidence/2026-09-30-m4a-package-validation.txt`](../testing/evidence/2026-09-30-m4a-package-validation.txt).

- The package is 188 files and 2,645,712 bytes (+1,111 bytes, the guard changes).
- `claude plugin validate dist/businessops --strict` and the `plugin.json` strict check both passed.
- It has 76 `${CLAUDE_PLUGIN_ROOT}/reference/` tokens with no missing targets, and 0 relative mentions. `.mcp.json` is
  byte-identical to the repository copy.
- It contains no developer, history, test or eval file, no binary, no symlink, no file over 256 KiB and no personal
  path.
- MCP, run from the package in its production `sh` form: `claude mcp list` reported Connected. `initialize`,
  `tools/list` (with annotations) and `tools/call` all worked.

## 6. Security check (shipped package)

- No credentials, keys, tokens, connection strings or credentials in URLs.
- Emails: `hello@conceptwebworld.com`, plus `reuters.com@evil.example` in a code comment about URL spoofing.
- External hosts are documentation or identifiers, never contacted by code: GitHub links to the development
  repository, JSON Schema `$id`s, OpenXML namespaces, `anthropic.com` (manifest `$schema`), `claude.com` (README
  source), `git-scm.com` (Windows requirement), `ons.gov.uk` (an example in the scout's reply format), and
  `mcp.slack.com` / `mcp.hubspot.com` (vendor servers described in `CONNECTORS.md`, not used).
- Guard messages: no `CLAUDE.md`. The README links to `CLAUDE.md` in the development repository ("How this project
  is developed"). Commands, skills and reference prompt text still cite `CLAUDE.md` (BOPS-R14).

## 7. Decisions

ADR-0055 and ADR-0056 are marked Accepted, as the owner confirmed in the M4A prompt. No new ADR: both fixes are
narrow corrections within ADR-0051's existing write-boundary design.

## 8. Findings recorded for later

- **BOPS-R13.** On native Windows, a Bash write aimed at the approval store is classified "needs approval" instead
  of "prohibited". This is the baseline failures `Zones.test_the_approval_store_is_prohibited` and
  `Outside.test_the_store_is_prohibited_even_when_not_engaged`: the path handling misses the store, including through
  `/c/Users/...` Git Bash paths. Pre-existing and not changed by R11, which a test now proves.
- **BOPS-R14.** Command, skill and reference prompt text cites `CLAUDE.md`, which is not shipped.
- **BOPS-R15.** `hooks/bops_guard.sh` falls back to `.` when `$0` has no `/`. Not observed under Claude Code.

## 9. Git commit reference

N/A — no commit, no push, no remote.
