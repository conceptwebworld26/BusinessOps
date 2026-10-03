# 2026-10-03 — BusinessOps M4: Claude Directory validation remediation

**Milestone:** BOPS-M4 — First Git commit, then repository publication and directory submission preparation
(step: respond to the developer portal's validation report)
**Status on completion:** REVIEW
**Supersedes:** [`2026-10-03-businessops-directory-icon.md`](2026-10-03-businessops-directory-icon.md) in one respect
only: that record's SVG listing icon is replaced by a PNG, because the directory refuses SVG. The rest of it stands.

## 1. Prompt / task performed

The portal's **Validate** run, after commit `8a14802`, reported eight findings. The task was to fix every genuine
and safely fixable finding without removing functionality or weakening security, to keep `bops-verifier` a local
stdio server, and to audit the working tree before one commit to `origin/main`.

| # | Finding | Result | Count |
|---|---|---|---|
| 1 | Uses a credential from the user's machine | Policy hold | 2 |
| 2 | Files or downloads the validator couldn't inspect | Policy hold | 2 |
| 3 | Scripts the validator couldn't follow (`lib/bops_run.sh`) | Policy hold | — |
| 4 | MCP server command wasn't read (`.mcp.json`, `mcpServers.bops-verifier.args`) | Policy hold | — |
| 5 | No icon (SVG and WebP not accepted) | Warning | — |
| 6 | CLAUDE.md at the plugin root isn't loaded | Warning | — |
| 7 | Contains a download-and-run command | Warning | 42 |
| 8 | Local MCP server: not on claude.ai | Note | — |

The report gives counts but, as relayed, not the file list behind each count. Each finding below is mapped to files
by reading the rule that raises it in the [plugin pre-submission checklist](https://claude.com/docs/plugins/pre-submission-checklist)
(read 2026-10-03) and searching the repository for what that rule matches.

## 2. Which folder the portal validated

Two findings exist only at the repository root, not in the plugin path `dist/businessops`:

- **Finding 6.** `dist/businessops` ships no `CLAUDE.md` (the build forbids it). The repository root has one.
- **Finding 2.** The checklist holds a non-image file over 256 KiB, a binary other than a complete image or font,
  and a plugin over 512 files. Measured on the tracked files:

  | Scope | Files | Binary (not image) | Over 256 KiB |
  |---|---|---|---|
  | Repository root | 857 | `assets/demo-data/northwind_sales.xlsx` | `project_plan.md` (346,624 bytes) |
  | `dist/businessops` | 190 | none | none |

  Exactly two files at the root match, which is the reported count.

The validation therefore appears to have read the repository root. The submission's **Plugin path** must be
`dist/businessops` (ADR-0057). That is an owner step in the portal, recorded as BOPS-R19. No repository change is
made for findings 2 and 6. Deleting the development material that triggers them would destroy project history and
tests, and it would still not make the root a correct plugin.

## 3. Changes made

### 3.1 Icon (finding 5)

- The directory accepts "a square PNG or JPEG … 512 to 2048 px on each side, under 2 MB. SVG and WebP are not
  accepted." The SVG listing icon from `8a14802` therefore cannot be used.
- `.claude-plugin/icon.png` is the same design rendered from `.claude-plugin/icon.svg`:
  - rendered by Chromium (Playwright) at exactly 512 × 512 CSS px with a transparent background; no repository
    dependency;
  - 512 × 512, 8-bit RGBA, non-interlaced, 11,885 bytes;
  - SHA-256 `530aba6bd93f77cec0d5d9ff81f5712281f08e73dab97bd9b9563bb2be36d1d8`;
  - sampled pixels exactly `#0F172A` (tile), `#14B8A6` (bars) and `#F8FAFC` (B), with transparent corners.
- The manifest now reads `"icon": "./.claude-plugin/icon.png"`. `marketplace.json` is unchanged, because the
  directory-listing fields belong only in `plugin.json`.
- The SVG stays in the source repository as the design source. It is no longer shipped, since nothing in the package
  refers to it.
- `scripts/build_distribution.py` ships the PNG. The package check now fails when the manifest `icon` is not all of:
  - a `./` path inside the package;
  - a `.png`, `.jpg` or `.jpeg` file present in the package;
  - readable as PNG or JPEG;
  - square, 512 to 2048 px;
  - under 2 MB.

### 3.2 Credential (finding 1)

The rule: "Don't read a credential that is already set in the user's environment, such as `$GITHUB_TOKEN` … even in
a README example."

- BusinessOps reads no credential: authentication is delegated to MCP servers (CLAUDE.md §7).
- A search of the package for credential-named variable references found exactly two, matching the reported count:
  - `lib/bops_run.sh:71`, `"$BOPS_PROBE_TOKEN"`;
  - `lib/bops_run.sh:72`, `"$BOPS_PROBE_TOKEN"`.
- `BOPS_PROBE_TOKEN` is not a credential. It is a script-local constant, `BOPS_RUNTIME_OK`, that a candidate Python
  interpreter must print to prove it evaluated the version check (ADR-0045). It is never read from the environment
  and never sent anywhere.
- **False positive, made unambiguous.** The variable is renamed `BOPS_PROBE_MARKER`, and the two adjacent comments
  say "marker". Behaviour is unchanged. The two tests that assert the line now assert the new name.
- No `userConfig` entry is added, because no user credential exists to ask for.
- The build now fails on any shipped reference to a credential-named variable (`$…TOKEN`, `…SECRET`, `…PASSWORD`,
  `…API_KEY`, `…CREDENTIAL`). `${user_config.KEY}`, the recommended form, does not match.

### 3.3 Scripts the validator couldn't follow (finding 3): kept, by design

- The rule: in a plugin that is a subfolder of its repository, a hook or MCP server that runs a non-shell file, or a
  shell script that runs another file, is held for a reviewer.
- The checklist's two ways out are a plugin at the root of its own repository, or logic written entirely in shell.
  - The owner declined a separate repository (ADR-0057); this task also forbids one.
  - The engine is Python by design (ADR-0002), so it cannot be rewritten in shell.
- `lib/bops_run.sh` is the interpreter resolver (ADR-0045, ADR-0046). It:
  - accepts only absolute `PATH` elements;
  - requires the probe marker;
  - keeps `-I` isolation;
  - fails closed;
  - contains no download, package install, `npx`, `uvx` or `PATH` export.
- Every hook and MCP command already names its script in full from `${CLAUDE_PLUGIN_ROOT}`, which satisfies the
  blocking rule.
- The directory's own guidance allows "leaving the scripts as they are and waiting for the review". No change; recorded
  under BOPS-R17.

### 3.4 MCP server command wasn't read (finding 4): kept, measured

- The rule asks for a local server started by "running a file in the plugin with plain arguments … not through a
  shell". `bops-verifier` is started with `sh ${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh --verifier`.
- Its real entry point is `lib/python/bops_run.py --verifier`, which is Python and already bundled. A direct launch
  has to name one interpreter.
- Measured on this machine (Windows 11, Claude Code 2.1.286), on scratch copies of the package, with
  `claude --plugin-dir <copy> mcp list`:

| `.mcp.json` command | Result |
|---|---|
| `sh ${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh --verifier` (current) | ✔ Connected |
| `python -I ${CLAUDE_PLUGIN_ROOT}/lib/python/bops_run.py --verifier` | ✔ Connected |
| `python3 -I ${CLAUDE_PLUGIN_ROOT}/lib/python/bops_run.py --verifier` | ✘ Failed to connect — CONNECTION_CLOSED |

- On this machine `python3` is the Microsoft Store alias ("Python was not found"). On macOS and on Debian or Ubuntu
  without `python-is-python3`, there is no `python` at all.
- Either fixed name therefore breaks the verifier on one major platform, and the verifier gates final reports
  (ADR-0034).
- Under the subfolder rule above, a direct launch of the Python file would be held anyway, as "Scripts the validator
  couldn't follow".
- **Kept** (BOPS-R10): the change would cost function for no change in review outcome. The server stays local stdio.

### 3.5 CLAUDE.md (finding 6)

- `CLAUDE.md` is development governance only: build process, conventions, testing and the review loop. It holds no
  runtime behaviour. The runtime rules it summarises already live in shipped `reference/`, `skills/` and
  `commands/` files, and `tests/unit/test_shipped_claude_md_references.py` keeps shipped files from depending on it
  (BOPS-R14).
- The package does not ship it. The warning appears only when the repository root is validated (section 2).
- Not copied into the plugin; no change.

### 3.6 Download-and-run (finding 7): 42 audited, none changed

- The shipped package has exactly 42 lines of the form `… -c …`, an inline program, matching the reported count.
- No shipped file contains `curl`, `wget`, `npx`, `uvx`, `pipx run`, `uv run`, `pip install` or a pipe into a
  shell.
- The only network install in the product is the Tier-2 `openpyxl` reader (ADR-0008), which is:
  - consented per install;
  - pinned (`OPENPYXL_PIN`);
  - placed in a managed venv outside the plugin;
  - never started by a hook or the MCP server.
- Classes: A unsafe download-and-execute; B runtime that can be made safer; C documentation or comment; D
  development-only; E false positive; F necessary architecture.

| # | Location (package) | Class | What it is |
|---|---|---|---|
| 1 | `commands/anomaly-detection.md:36` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 2 | `commands/ask-business-data.md:28` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 3 | `commands/business-health.md:44` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 4 | `commands/cash-flow-analysis.md:37` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 5 | `commands/customer-analysis.md:32` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 6 | `commands/product-analysis.md:30` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 7 | `commands/profitability-analysis.md:31` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 8 | `commands/revenue-forecast.md:35` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 9 | `commands/sales-analysis.md:32` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 10 | `lib/bops_run.sh:5` | C | Comment describing the engine call |
| 11 | `lib/bops_run.sh:9` | C | Comment describing the engine call |
| 12 | `lib/bops_run.sh:70` | F | Interpreter version probe (`-I -c` with a fixed version check); downloads nothing |
| 13 | `lib/python/bops/writeguard/classify.py:311` | E | Write-guard message string naming a pattern it blocks |
| 14 | `lib/python/bops_run.py:5` | C | Docstring describing the engine call |
| 15 | `lib/python/bops_run.py:10` | C | Docstring describing the engine call |
| 16 | `skills/bops-anomaly-detection/SKILL.md:43` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 17 | `skills/bops-benchmark-comparison/SKILL.md:92` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 18 | `skills/bops-company-analysis/SKILL.md:73` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 19 | `skills/bops-company-analysis/SKILL.md:99` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 20 | `skills/bops-company-analysis/SKILL.md:276` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 21 | `skills/bops-competitor-analysis/SKILL.md:193` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 22 | `skills/bops-competitor-analysis/SKILL.md:216` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 23 | `skills/bops-competitor-analysis/SKILL.md:533` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 24 | `skills/bops-customer-intelligence/SKILL.md:29` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 25 | `skills/bops-data-ingestion/SKILL.md:50` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 26 | `skills/bops-data-ingestion/SKILL.md:105` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 27 | `skills/bops-decision-support/SKILL.md:82` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 28 | `skills/bops-decision-support/SKILL.md:205` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 29 | `skills/bops-executive-report/SKILL.md:79` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 30 | `skills/bops-executive-report/SKILL.md:161` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 31 | `skills/bops-financial-analysis/SKILL.md:48` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 32 | `skills/bops-forecasting/SKILL.md:29` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 33 | `skills/bops-industry-research/SKILL.md:175` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 34 | `skills/bops-industry-research/SKILL.md:197` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 35 | `skills/bops-industry-research/SKILL.md:395` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 36 | `skills/bops-market-analysis/SKILL.md:112` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 37 | `skills/bops-market-analysis/SKILL.md:134` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 38 | `skills/bops-market-analysis/SKILL.md:309` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 39 | `skills/bops-product-intelligence/SKILL.md:42` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 40 | `skills/bops-sales-intelligence/SKILL.md:31` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 41 | `skills/bops-strategy-recommendations/SKILL.md:70` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |
| 42 | `skills/bops-swot/SKILL.md:87` | F | Engine call: runs code shipped in the plugin via the resolver; downloads nothing |

**Totals:** F 37, C 4, E 1; A 0, B 0, D 0.

- The 36 engine calls are the documented entry form (ADR-0042, ADR-0045). Each runs `lib/python/bops_run.py`, which
  ships inside the plugin, with a fixed program that imports the shipped engine. That is already what the
  directory's guidance asks for: "ship the script inside the plugin and run that file".
- Replacing the inline programs with dozens of new script files would rewrite the engine-entry architecture to quiet
  a warning, and nothing would be safer. None was changed. The warning is expected to remain.

### 3.7 Local MCP server (finding 8)

- `bops-verifier` remains a local stdio server; no remote endpoint was created.
- The README's *Where BusinessOps works* table already states that claude.ai chat loads no local servers, and what
  that means for analysis (BOPS-R6). No change.

## 4. Files created

- `.claude-plugin/icon.png`
- `dist/businessops/.claude-plugin/icon.png` (built)
- `docs/development/2026-10-03-businessops-directory-validation-remediation.md`

## 5. Files modified

- `.claude-plugin/plugin.json`, `dist/businessops/.claude-plugin/plugin.json` (built): `icon` names the PNG
- `lib/bops_run.sh`, `dist/businessops/lib/bops_run.sh` (built): `BOPS_PROBE_TOKEN` renamed `BOPS_PROBE_MARKER`
- `scripts/build_distribution.py`: ships the PNG, not the SVG; directory icon rule; credential-variable check
- `tests/unit/test_distribution_build.py`: PNG icon, unshipped SVG, icon-rule negatives, credential-variable check;
  the `.gitignore`-dependency test reads bytes, because the package now holds a binary image
- `tests/unit/test_m13_def08_runtime_resolver.py`, `tests/integration/test_m13_def12_wsl_interpreter.py`: new marker name
- `tests/unit/test_shipped_claude_md_references.py`: the `.claude-plugin/` scan reads bytes, for the same reason. On
  the first full run after the change it raised a `UnicodeDecodeError` on `icon.png`, which this fixes.
- `architecture.md`, `project_plan.md`, `docs/development/README.md`

## 6. Files deleted

- `dist/businessops/.claude-plugin/icon.svg`: no longer shipped. The source SVG is kept.

## 7. Features implemented

- Directory-accepted listing icon, enforced by the build.
- Build guard against shipped credential-named variable references.

## 8. Tests performed

```
python scripts/build_distribution.py
claude plugin validate . --strict
claude plugin validate dist/businessops --strict
claude plugin validate dist/businessops/.claude-plugin/plugin.json --strict
claude plugin validate .claude-plugin/plugin.json --strict
python tests/run_tests.py
claude --plugin-dir <scratch copy of dist/businessops> mcp list
JSON-RPC over stdio to sh <copy>/lib/bops_run.sh --verifier: initialize, tools/list, recompute, unknown tool
```

## 9. Test results

- **Build.**
  - 190 files, 2,663,343 bytes, `"problems": []`.
  - Against `8a14802` the package:
    - gains `.claude-plugin/icon.png`;
    - loses `.claude-plugin/icon.svg`;
    - changes only `.claude-plugin/plugin.json` (`icon`) and `lib/bops_run.sh` (marker rename).
  - The packaged PNG is byte-identical to the source PNG: 512 × 512, 11,885 bytes.
- **`validate --strict`.**
  - Passed for `.`, `dist/businessops` and `dist/businessops/.claude-plugin/plugin.json`.
  - `.claude-plugin/plugin.json` reports only the known `CLAUDE.md` advisory (architecture.md §2), unchanged. It is
    the same text as portal finding 6, consistent with section 2.
- **Full suite** (`python tests/run_tests.py`):

  | Run | Tests | Failures | Errors | Skipped | Failing ids vs baseline |
  |---|---|---|---|---|---|
  | Baseline `8a14802` | 5361 | 46 | 7 | 38 | — |
  | First run after the change | 5362 | 46 | 8 | 38 | One new error: the `UnicodeDecodeError` above, fixed |
  | Final | 5362 | 46 | 7 | 38 | Identical |

  - The count is +1 because three SVG-icon tests were replaced by four tests: PNG icon, unshipped SVG, icon-rule
    negatives, credential variables.
  - The 53 remaining failures and errors are the known native-Windows baseline (resolver, WSL, write-guard and
    handback launch tests). They predate this work.
  - All 20 `test_distribution_build` tests pass, including the fresh-build equality test.
- **MCP** (scratch copy of the package):
  - `mcp list`: `plugin:businessops:bops-verifier … ✔ Connected`.
  - `initialize`: `bops-verifier` 1.0.0.
  - `tools/list`: `recompute` (`request_id`), with unchanged annotations.
  - `recompute` with an unknown id: `status: failed`, `error_code: request_not_found`.
  - `recompute` with `../../etc/passwd`: `request_id_invalid`.
  - Unknown tool: `-32602 invalid params`.
- **Package content.**
  - No `Concept Web World` text. Both manifests name `Prakash Meghani - Krayons Global` and
    `krayonsglobal@gmail.com`.
  - Version 0.1.0.
  - No bytecode, editor or OS files, no SVG, no hard-coded secret.
  - The only binary is the PNG icon.

## 10. Untracked-file audit

At the start, `git status --short --untracked-files=all` was empty: `main` was clean at `8a14802`, equal to
`origin/main`, so no earlier work was left uncommitted.

| Path | Class | Action |
|---|---|---|
| `.claude/settings.local.json`, `.claude/.cc-writes` | E — local machine state, ignored | Excluded |
| `evals/results/` | H — eval run output, ignored by convention | Excluded |
| `.playwright-mcp/` | G — temporary render output from this task | Deleted before commit |

## 11. Issues discovered

- BOPS-R19: the portal validation appears to have read the repository root. Re-validate with plugin path
  `dist/businessops`.
- `claude plugin validate` checks neither the icon's existence nor its format. The build covers both.

## 12. Next step

Re-run **Validate** in the portal with **Plugin path** `dist/businessops`. The expected remaining items are:
- the policy holds "Scripts the validator couldn't follow" and "MCP server command wasn't read" (by design, BOPS-R10,
  BOPS-R17);
- the download-and-run warning (section 3.6);
- the local-server note.
