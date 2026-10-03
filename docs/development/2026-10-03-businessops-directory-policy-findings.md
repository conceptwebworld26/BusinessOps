# 2026-10-03 — BusinessOps M4: Claude Directory policy findings (plugin path `dist/businessops`)

**Milestone:** BOPS-M4 — First Git commit, then repository publication and directory submission preparation
(step: final remediation pass on the portal report for the correct plugin path)
**Status on completion:** REVIEW
**Supersedes:** [`2026-10-03-businessops-directory-validation-remediation.md`](2026-10-03-businessops-directory-validation-remediation.md)
on one point. Its section 3.2 treated `$BOPS_PROBE_TOKEN` as the cause of "Uses a credential from the user's machine".
The rename to `BOPS_PROBE_MARKER` (commit `1663d38`) did not clear the hold, so that diagnosis was not confirmed.
Section 2 below replaces it. The rest of that record stands. Its BOPS-R19 diagnosis, that the earlier report read the
repository root, is confirmed: with plugin path `dist/businessops`, the `CLAUDE.md`, "couldn't inspect" and
download-and-run findings are gone.

## 1. The report (plugin path `dist/businessops`, branch `main`, at `1663d38`): "Passed with warnings"

| # | Finding | Result | Location given |
|---|---|---|---|
| 1 | Image or font file that the plugin's code could run | Policy hold | `.claude-plugin/plugin.json` |
| 2 | Uses a credential from the user's machine | Policy hold | `.claude-plugin/plugin.json` |
| 3 | Scripts the validator couldn't follow | Policy hold | `lib/bops_run.sh` |
| 4 | MCP server command wasn't read | Policy hold | `.mcp.json`, `mcpServers.bops-verifier.args` |
| 5 | Field from another tool's manifest (`icon`): "No action needed" | Note | `plugin.json` / `icon` |
| 6 | Local MCP server: not on claude.ai | Note | `.mcp.json` |
| 7 | Images and fonts passed without a code check (`icon.png`) | Note | `plugin.json` |

The report names no line for findings 1 and 2. Below, each is mapped to code by an exhaustive search of the package.

## 2. Credential (finding 2): no credential is read; disclosed for the reviewer

Searched in the package:
- environment reads: `os.environ`, `getenv`, shell `$NAME`;
- credential stores: keyring, keychain, `.netrc`, `.npmrc`, `.pypirc`, `.aws`, `.ssh`, `.config/`;
- names containing `TOKEN`, `SECRET`, `PASSWORD`, `PASSWD`, `API_KEY`, `ACCESS_KEY`, `PRIVATE_KEY` or `AUTH`;
- `Authorization` headers and `pwd`.

Classes: A credential, B machine credential discovery, C probe marker, D documentation, E false positive, F required
configuration.

| Construct | Reads | Class | Why it stays |
|---|---|---|---|
| `writeguard/policy.py:90` `pwd.getpwuid(os.getuid()).pw_dir` | The home folder, from the OS account record. Python's `pwd` module reads the "password database", but only the home-directory field is taken, and no password data exists there | E | Security control (ADR-0051). `$HOME` can be set by a command line. Taking the home from the environment would let a command point the engine at an approval store it controls and approve its own write. Removing it weakens the guard |
| `writeguard/export.py:74` `CLAUDE_CODE_SESSION_ID` | Claude Code's session identifier | E/F | Binds each single-use write approval to the session it was granted in (ADR-0051). Stored only in the approval store (PRIVACY.md); never sent |
| `lib/bops_run.sh` `BOPS_PYTHON`, `PATH` | An optional interpreter path; the search path | F | Interpreter resolution (ADR-0045) |
| `verification.py:286`, `writeguard/engine.py:230` `BOPS_VERIFICATION_DIR`; `writeguard/hook.py:258` `BOPS_GUARD_ROOT` | Optional folder overrides | F | Configuration |
| `lib/bops_run.sh` `BOPS_PROBE_MARKER` | A script-local constant, not the environment | C | Already renamed in `1663d38` |
| Redaction patterns (`connectors/contract.py`, `privacy/sensitivity.py`, `research/contract.py`) | Nothing; they detect credentials in order to refuse them | E | Security controls |

- **Nothing in the package reads a credential, and nothing sends one.** The engine opens no network connection
  (CLAUDE.md §4; the engine's audit hook blocks network events, `writeguard/engine.py:55`).
- The one download is the consented `openpyxl` install (section 5), which sends none of these values.
- The portal's guidance for this case: "If they are unrelated, you can leave them as they are and a reviewer confirms
  it, or remove every part that reads a credential". Removal would disable the write guard's protections, so this is
  left for the reviewer.
- **Change:** the README's *Privacy and data boundaries* now lists exactly what BusinessOps reads from the machine and
  states that none of it is sent. The checklist's security-scan advice is to "describe in the README everything the
  plugin runs, sends, or fetches".
- **Tests:** two tests keep the list honest.
  - `test_the_readme_discloses_every_environment_value_the_shipped_code_reads` collects every environment value read by
    shipped Python and shell code. It asserts the set is exactly `BOPS_VERIFICATION_DIR`, `BOPS_GUARD_ROOT`,
    `CLAUDE_CODE_SESSION_ID`, `BOPS_PYTHON` and `PATH`, and that the README names each.
  - `test_the_account_lookup_reads_only_the_home_directory` pins the single `pwd` use to `.pw_dir`.
- **Expected portal result:** the hold remains for a reviewer to confirm. That is not proven until the portal runs.

## 3. Image or font file that the plugin's code could run (finding 1): data only; retained

- The only reference to `icon.png` anywhere in the package is `plugin.json`'s `"icon": "./.claude-plugin/icon.png"`,
  the field the directory reads for the listing (finding 5: "No action needed").
- No command, skill, agent, hook, script, Python module or MCP code names, opens, executes, downloads or replaces it.
  The build script, which copies it, does not ship.
- The checklist holds an image that is referred to "from commands, hooks, or scripts, or [with its path] in backticks
  or a code block". The manifest reference is the evident trigger, since the report anchors the hold to `plugin.json`.
- Finding 7 confirms the file is a well-formed image.
- **Not genuinely executable; retained.** The portal's guidance: "If nothing runs the file, leave it as is and the
  plugin stays held for review."
- One documented alternative exists. The directory also finds an icon at `.claude-plugin/icon.png` with no manifest
  field ("Add a square PNG … at .claude-plugin/icon.png, **or** set icon in plugin.json"). Dropping the field might
  avoid the reference. It was not done, because this task requires keeping the `icon` field. It is recorded for the
  owner as BOPS-R20.

## 4. Scripts the validator couldn't follow (finding 3): retained

Execution chain:

| Started by | Command |
|---|---|
| Hooks (`hooks/hooks.json`) | `sh "${CLAUDE_PLUGIN_ROOT}/hooks/bops_guard.sh" <event>`, which runs `sh "<root>/lib/bops_run.sh" --guard <event>`; also `sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" --handback` |
| MCP (`.mcp.json`) | `sh ${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh --verifier` |
| Commands and skills | `sh "${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh" -c "<program>"` |

`lib/bops_run.sh` then:
- finds a Python 3.9+ interpreter from absolute `PATH` elements or `BOPS_PYTHON`, requiring the probe marker;
- runs `exec <python> -I <plugin root>/lib/python/bops_run.py <args>`, a file shipped inside the plugin.

It has no `npx`, `uvx`, package install, download or `PATH` export, and runs nothing outside the plugin.

Why it stays:
- The checklist: "the validator follows only plain shell scripts … [a hook or server that] runs a shell script that
  itself runs another file, that file is held. To avoid the hold, keep the plugin at the root of its own repository,
  or keep the logic a hook or server runs in shell scripts". The report repeats it: "A file that script runs in turn
  isn't followed and always goes to a reviewer."
- The engine is Python (ADR-0002) and the plugin is a subfolder of its repository (ADR-0057; this task forbids a second
  repository). So any chain ends in a Python file and is held. The options considered:
  - **A** (one wrapper with a literal path): already the structure, and still held.
  - **B** (bundled runtime): no bundled Python exists, and adding one would be a large binary, itself held.
  - **C** (platform-aware launcher): this is what `bops_run.sh` is.
  - **D** (packaged artifact): see section 5.
- The checklist accepts this outcome: "Leaving the scripts as they are and waiting for the review is also fine"
  (BOPS-R17).

## 5. MCP server command wasn't read (finding 4): retained

The server:

| | |
|---|---|
| Command | `sh` |
| Arguments | `${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh`, `--verifier` |
| Server | `bops-verifier`, Python standard library only, entry `lib/python/bops_run.py --verifier` (module `bops.verification_server`), shipped in the package |

Alternatives investigated:
1. **Direct interpreter launch.** Measured in the previous pass on this machine: `python -I …/bops_run.py --verifier`
   connects; `python3 …` fails with CONNECTION_CLOSED, because the Microsoft Store alias stands in for `python3`.
   macOS and Debian or Ubuntu have no `python`. Any fixed name breaks one major platform. The Python file would still
   be held under section 4's rule.
2. **`.mcpb` / `.dxt` bundle.** The checklist row: "Declare each MCP server with `command` and `args` or with `url`,
   not a `.mcpb` or `.dxt` bundle — Held for a reviewer. Blocks for a bundle fetched from a URL. — **Bundled MCP
   server not inspected**". A bundle is also a zip archive, which is a non-image binary and so another hold. A Python
   bundle still names a host interpreter.
   - Result: no packaged artifact clears the hold. It would add holds and keep the platform problem.
3. **Remote server.** Out of scope by instruction, and against the architecture: verification is local and reads local
   files.

**Decision:** keep `sh ${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh --verifier` (BOPS-R10).

## 6. Download and execution audit (package)

| Occurrence | Class | Notes |
|---|---|---|
| `runtime/tiers.py:266` `[python, "-m", "pip", "install", "--disable-pip-version-check", "openpyxl==3.1.5"]` | Runtime, consented | ADR-0008 Tier 2. One pinned version into `~/.claude/businessops/runtime/`, only after the user's consent, never from a hook or the MCP server. The engine guard allows exactly this argv (`writeguard/engine.py:131`) |
| `runtime/tiers.py:143` `pip --version` | Runtime probe | Checks that Tier 2 is possible; installs nothing |
| `writeguard/classify.py:198`, `:557` (`install`) | Security control | Classifies the Unix `install` copy command as a write |
| `writeguard/engine.py:55` (`socket.connect`, `urllib.Request`, …) | Security control | Network events the engine refuses |
| "download" in `PRIVACY.md` (5), `README.md` (2), `bops_run.sh`, `tiers.py`, `ingest/*.py`, `data_profile.py` (1 each) | Documentation or comment | Disclosure of the optional reader download, and "no download" statements |

The package contains no `curl`, `wget`, `Invoke-WebRequest`, `npx`, `uvx`, `pipx`, `npm install`, pipe into a shell,
`urlopen` or socket use. There is no unsafe download-and-execute.

## 7. Notes retained (findings 5, 6, 7)

- **`icon` field:** the directory reads it, and the report says "No action needed".
- **Local MCP server:** `bops-verifier` stays local stdio, and the README's *Where BusinessOps runs* table already
  says claude.ai loads no local servers.
- **Image passed without a code check:** an asset classification, confirming `icon.png` is a well-formed image.

## 8. Files

- **Created:** this record.
- **Modified:**
  - `README.md` and `dist/businessops/README.md` (built): the machine-reads disclosure;
  - `tests/unit/test_distribution_build.py`: two tests;
  - `project_plan.md`, `docs/development/README.md`.
- **Deleted:** none.

No runtime code changed, so the engine, write guard, MCP server, hooks, commands and skills are unchanged.

## 9. Tests and validation

- **Build.** `python scripts/build_distribution.py`: 190 files, 2,664,383 bytes, `"problems": []`. Only
  `README.md` changed in the package.
- **`claude plugin validate --strict`.**
  - Passed for `.`, `dist/businessops` and `dist/businessops/.claude-plugin/plugin.json`.
  - `.claude-plugin/plugin.json` (development root) reports only the known `CLAUDE.md` advisory, unchanged.
- **Full suite** (`python tests/run_tests.py`):

  | Run | Tests | Failures | Errors | Skipped |
  |---|---|---|---|---|
  | Baseline (`1663d38`) | 5362 | 46 | 7 | 38 |
  | This change | 5364 | 46 | 7 | 38 |

  - The two extra tests are the new ones, and both pass.
  - The failing and erroring test ids are identical to the baseline: the known native-Windows resolver, WSL,
    write-guard and handback launch tests.
  - All 22 `test_distribution_build` tests pass, including the fresh-build equality test.
- **MCP** (scratch copy of the package):
  - `mcp list`: `plugin:businessops:bops-verifier … ✔ Connected`.
  - `initialize`: `bops-verifier` 1.0.0.
  - `tools/list`: `recompute`, with unchanged annotations.
  - `recompute` with an unknown id: `request_not_found`; with `../../etc/passwd`: `request_id_invalid`.
  - Unknown tool: `-32602 invalid params`.
- **Package.**
  - Icon `./.claude-plugin/icon.png`: valid PNG, 512 × 512, 11,885 bytes.
  - Author `Prakash Meghani - Krayons Global`, `krayonsglobal@gmail.com`, version 0.1.0.
  - No `Concept Web World` text, no bytecode or OS files, no secrets.

## 10. Self-audit

| Finding | Source | Change | Why | Expected result |
|---|---|---|---|---|
| Image could run | `plugin.json` `icon` reference to `icon.png` | None | Data only; nothing runs it; the field is required here | Held for a reviewer |
| Credential | Most likely `pwd.getpwuid` (account record) and/or `CLAUDE_CODE_SESSION_ID`; neither is a credential | README disclosure plus tests | Removing them weakens the write guard; the guidance allows reviewer confirmation | Held; reviewer confirms |
| Scripts couldn't follow | `lib/bops_run.sh` runs a Python file | None | The engine is Python; subfolder plugin | Held (accepted, BOPS-R17) |
| MCP command | `sh …/bops_run.sh --verifier` | None | Direct launch breaks a platform; `.mcpb` is itself held | Held (accepted, BOPS-R10) |
| `icon` field note | `plugin.json` | None | "No action needed" | Note |
| Local MCP note | `.mcp.json` | None | Local verification by design | Note |
| Image passed unread note | `icon.png` | None | Asset classification | Note |
