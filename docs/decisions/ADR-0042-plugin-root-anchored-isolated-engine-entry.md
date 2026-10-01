# ADR-0042 — The engine is entered through one plugin-root-anchored, isolated launcher, located by the platform's `${CLAUDE_PLUGIN_ROOT}` substitution in command and skill bodies

**Date:** 2026-09-19
**Status:** Accepted — 2026-09-19, by the project owner, as drafted.

- **Basis.** V-1 and V-2 were verified at runtime (V-1, V-2a and V-2b PASS) in
  `docs/development/2026-09-19-m13-def-04-runtime-verification.md`. The body below keeps its pre-verification wording
  of them.
- **What acceptance approves.** The architecture for a later implementation, and nothing else. **Not implemented:**
  the launcher does not exist. M13-DEF-04 remains open, and M13.2 is not unblocked by this ADR.
- **Still open:** G-3 (and so V-3), V-4, and runtime verification on Unix-like systems.
**Deciders:** Project owner, on review. Drafted in the M13-DEF-04 remediation design prompt (design only).
**Supersedes:** none. **Amends:** none on acceptance except as *Follow-up required* states. No accepted ADR is edited.
**Relates to:**

- ADR-0001 (verified platform conventions);
- ADR-0002 (a deterministic engine that is stdlib only);
- ADR-0008 (reader tiers; no dependency outside the consented runtime);
- ADR-0012 (component placement);
- ADR-0035 (the `biq-verifier` boundary, unchanged);
- ADR-0039, ADR-0040 and ADR-0041 (M13; G-2 and G-3).

## Context

### The defect

**M13-DEF-04** (`docs/testing/defects.md`) is open. Every route from a command or skill into the engine depends on the
session's working directory:

- **10 commands and 11 skills** begin their engine call with `sys.path.insert(0, 'lib/python')`, a path resolved
  against the working directory;
- **5 skills** (`biq-benchmark-comparison`, `biq-decision-support`, `biq-executive-report`,
  `biq-strategy-recommendations` and `biq-swot`) write `from biq import …` with no path setup at all. They fail even
  from the repository root;
- **the other 9 model-invocable commands** reach the engine only through those skills.

From any directory other than the plugin root, the entry raises `ModuleNotFoundError: No module named 'biq'`.

The accepted architecture puts the installed plugin and the user's working directory in different places:

- the distribution is a marketplace install (`architecture.md` §2; ADR-0001), and the owner's installed copy lives in
  the platform plugin cache;
- runtime state lives in the user's working directory (`architecture.md` §13).

M13.2's G-2 working directory, which is outside the repository, is therefore the faithful user environment. M13.2's
manual observations S3-01 to S3-11 are blocked on this defect.

### The entry is also an import-hijack path

Measured locally on 2026-09-19 (Python 3.13.1), with no session and no model:

| Invocation | Effect in a working directory the user controls |
|---|---|
| `python -c "import sys; sys.path.insert(0, 'lib/python'); import biq"` | A `lib/python/biq/` in the working directory **is executed** ("HIJACKED: lib/python/biq resolved from the user cwd") |
| `python -c "…; import json"` | `sys.path[0]` is `''`, the working directory. A `json.py` there **shadows the standard library** |
| `python -I -c "…"` | `sys.path[0]` is the standard-library zip. The working directory is not on `sys.path` |
| `python <dir>/probe.py` | `sys.path[0]` is the script's own directory. The working directory is not on `sys.path` |
| `python -I <dir>/probe.py` | Neither the script's directory nor the working directory is on `sys.path` |

### Where the platform provides the plugin root

Established by static inspection of the installed Claude Code CLI, 2.1.278 (`~/.local/bin/claude.exe`), by
searching its embedded code for `CLAUDE_PLUGIN_ROOT`, and by observing this development session.

| Layer | `${CLAUDE_PLUGIN_ROOT}` | Evidence |
|---|---|---|
| MCP server launch configuration (`.mcp.json` `command` / `args` / `env`) | **Substituted as text**, and also set as the server process's environment variable | The CLI builds `{CLAUDE_PLUGIN_ROOT: <plugin path>, …}` for stdio servers. The M11 probe A observed it at runtime |
| Hooks (`hooks/hooks.json`, and skill hooks) | Substituted, and exported to the hook process's environment | The CLI's hook runner sets `CLAUDE_PLUGIN_ROOT` in the hook environment |
| **Plugin command bodies** (`commands/*.md`) | **Substituted as text before the model sees the prompt** | The plugin command builder's `getPromptForCommand` applies `n9(text, {path: <plugin path>})`. `n9` replaces `/\$\{CLAUDE_PLUGIN_ROOT\}/g` with the plugin path, converting `\` to `/`. Commands load through `Man(w.commandsPath, …, w.path, {isSkillMode:false})` |
| **Plugin skill bodies** (`skills/<name>/SKILL.md`) | **Substituted as text**, by the same builder with `isSkillMode:true` | Skills load through `Oan(h.skillsPath, …, h.path, …)`. In skill mode the text is also prefixed "Base directory for this skill: <dir>", and `${CLAUDE_SKILL_DIR}` is substituted |
| **The Bash tool's shell environment** | **Not set** | A development session with BusinessIQ installed shows no `CLAUDE_PLUGIN*` variable in `env`. The Bash working directory is the session's working directory |
| A file the model reads with `Read` (for example a `reference/*.md`) | **Not substituted** | Substitution belongs to the command and skill prompt builder only |

Notes on the substitution:

- Only the exact brace form `${CLAUDE_PLUGIN_ROOT}` is replaced in bodies. `$CLAUDE_PLUGIN_ROOT` is not.
- This is **configuration-time text substitution into the prompt**, not a shell or process variable. A body that
  contains `${CLAUDE_PLUGIN_ROOT}` reaches the model already carrying the absolute plugin path.

**Verification status.** The two body rows are **statically verified on 2.1.278** and **not yet observed at runtime**
(V-1 below). `architecture.md` §2's platform facts were verified on 2.1.263.

## Problem

How must a command or skill reach the engine so that it:

- works from any working directory, and from both a source checkout and an installed copy;
- cannot be redirected to another `biq`, or to a shadowed standard library, by the working directory or the
  environment;
- keeps the path logic in one place;
- changes no product behaviour beyond the entry itself?

## Constraints

1. **No working-directory dependence.** No `cd` into the plugin, no `PYTHONPATH`, no copy or link of plugin files
   into the user's directory, and no dependence on the current directory.
2. **Development material stays out of the observed context.** Development `CLAUDE.md`, `evals/`, graders and
   `docs/` are never brought into the user's working context.
3. **Architecture unchanged.**
   - Stdlib only (ADR-0002, `CLAUDE.md` §4). No installed package, and no new dependency.
   - File-first v1. No new MCP server for imports. `biq-verifier` unchanged.
   - No change to connectors, M12 policy, M13 eval policy or disclosure behaviour.
4. **Distribution.** It works for a source checkout (`--plugin-dir`) and for a marketplace-installed copy, on Windows
   and Unix-like systems, with no hard-coded path.
5. **Centralised.** The path logic lives in one file, and each command or skill carries no path logic of its own.
6. **Fail loudly** (`CLAUDE.md` §2 principle 5): an unresolved root is an error, never a fallback.

## Options considered

### Option A — Plugin-root-anchored isolated launcher, located by body substitution (chosen)

One new file, `lib/python/biq_run.py`, resolves the engine from its own `__file__`. Every command and skill enters the
engine as:

```bash
python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py" -c "
from biq import commands
…
"
```

The platform replaces `${CLAUDE_PLUGIN_ROOT}` in the body with the absolute plugin path before the model sees it.

- **Pros:**
  - It uses the only plugin-root mechanism the platform provides for command and skill bodies.
  - The path logic lives in one stdlib file.
  - It works from any working directory and in any installed copy.
  - `-I` and script invocation keep the working directory and `PYTHONPATH` off `sys.path`, which closes the
    hijack paths.
  - Snippet bodies stay the same apart from their first line.
- **Cons:**
  - Every engine-reaching command and skill still needs its invocation line edited once. The platform offers no way
    to locate the root other than text in the body.
  - It depends on a platform substitution that is statically verified but not yet runtime-observed (V-1).

### Option B — Replace `'lib/python'` with `'${CLAUDE_PLUGIN_ROOT}/lib/python'` inside each snippet

- **Pros:** the smallest textual edit.
- **Cons, and rejected because:**
  - The path logic is duplicated in 21 or more places.
  - The path is embedded inside Python source, where an apostrophe in a home-directory path breaks the string
    literal.
  - `python -c` still puts the working directory on `sys.path`, so a `json.py` or `decimal.py` there can still
    shadow the standard library.
  - It leaves nothing to validate that the engine imported is the plugin's own.

### Option C — Read `CLAUDE_PLUGIN_ROOT` from the process environment (`os.environ`, or `$CLAUDE_PLUGIN_ROOT` in Bash)

**Rejected.** It is not set in the Bash tool's environment (observed). It is exported only to hooks, MCP servers and
monitors.

### Option D — Install `biq` as a Python package (`pyproject.toml` / `pip install`)

**Rejected:**

- It installs into a system, user or project interpreter, which `CLAUDE.md` §4 and ADR-0008 forbid for anything
  outside the consented runtime.
- It adds an installation prerequisite.
- The installed package would drift from the plugin copy that is actually loaded.
- A user-site install is itself a shadowing surface.
- The repository has no packaging metadata today, and none is needed.

### Option E — A SessionStart hook that exports the plugin root into the session environment (`CLAUDE_ENV_FILE`)

**Rejected:**

- It adds a new component type, and `architecture.md` §2 records hooks as deferred with "no need identified".
- It runs code at every session start.
- It writes a global environment value.
- It still needs the launcher.
- Its runtime behaviour is unverified here.

### Option F — Derive the root from the skill's "Base directory for this skill" header or `${CLAUDE_SKILL_DIR}`

**Rejected.** It applies to skills only, and commands get no header. It would need per-skill relative arithmetic
(`../../lib/python`), which duplicates path logic.

### Option G — Run sessions from the repository root, or with `PYTHONPATH`, or with a copy or link of `lib/python`

**Rejected.** Each breaks constraint 1 or 2, and the repository-root variant loads the development `CLAUDE.md` as
project instructions.

### Option H — An MCP server that exposes the engine

**Rejected.** A new production MCP server for imports is out of scope by constraint 3, and it would change the tool
surface and the permissions.

## Decision

On acceptance, the engine has **exactly one entry**: `lib/python/biq_run.py`, run as
`python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py" -c "<code>"`.

1. **Location.** `biq_run.py` sits beside the `biq` package, so `os.path.dirname(os.path.realpath(__file__))` is
   exactly the directory that must be on `sys.path`.
2. **Resolution and validation.** It resolves `LIB` from its own `__file__` and `ROOT` as `LIB/../..`. It then
   validates, failing with a non-zero exit and a plain stderr message if either check fails:
   - that `LIB/biq/__init__.py` exists;
   - that `ROOT/.claude-plugin/plugin.json` parses and names `businessiq`.
3. **Isolation is required.** It refuses to run unless `sys.flags.isolated` is set, which is what `-I` sets, and
   says to use `-I`. `-I` ignores `PYTHON*` environment variables and the user site-packages, and it keeps both the
   working directory and the script's directory off `sys.path`.
4. **Path hygiene, in defence in depth.**
   - It removes `''`, `'.'` and any entry that resolves to the working directory.
   - It refuses if `biq` is already imported.
   - It inserts `LIB` at position 0.
   - It imports `biq` and verifies that `realpath(biq.__file__)` lies under `LIB`. Otherwise it fails.
5. **Execution.** It accepts exactly `-c CODE`, mirroring Python's own flag, and executes `CODE` in a fresh `__main__`
   namespace. It also accepts `--where`, which prints a JSON object:
   `{"plugin_root", "engine", "biq_module", "isolated", "python"}`. That serves the acceptance tests and the owner's
   pre-flight.
6. **What it adds.** No behaviour of its own: no network, no file write, no output beyond what `CODE` prints, plus
   stderr diagnostics.
7. **Every engine-reaching command and skill** uses that invocation line and carries no other path logic. A static
   test enforces this:
   - the old `sys.path.insert(0, 'lib/python')` entry must be absent;
   - any `from biq` or `import biq` must appear only inside a launcher-invoked block;
   - the launcher line must be byte-identical everywhere.
8. **The five bare-import skills** keep their flows unchanged. Their executable blocks are expressed as launcher
   invocations, so the `from biq import …` lines run inside the launcher.
9. **Quoting.** The path is double-quoted in the shell and never embedded in Python source. `n9` has already turned
   backslashes into `/`, and Windows filenames cannot contain `"`.
10. **An unsubstituted root fails loudly.** If a body reaches the shell with the literal `${CLAUDE_PLUGIN_ROOT}`, for
    example because the model read the file instead of invoking the skill, the variable is empty in the Bash
    environment. The path becomes `/lib/python/biq_run.py`, which does not exist, and Python fails with "can't open
    file". There is no silent fallback.

### Runtime model

```
Claude Code loads plugin command/skill  ──►  ${CLAUDE_PLUGIN_ROOT} → absolute plugin path, substituted in the body text
model runs the body's Bash block       ──►  python -I "<plugin>/lib/python/biq_run.py" -c "<code>"
biq_run.py                             ──►  LIB from __file__; validate ROOT; require -I; clean sys.path; import biq; verify biq.__file__ ⊂ LIB
<code>                                 ──►  unchanged engine calls (commands.run, research, synthesis …)
```

- **Source checkout** (`claude --plugin-dir <repo>`): the plugin path is the checkout, so the checkout's engine runs.
- **Installed copy:** the plugin path is the cache copy, so the cache copy's engine runs. No path is hard-coded.
- **External working directory:** the working directory never enters `sys.path`. Relative input paths in `CODE`,
  such as the user's CSV, still resolve against the working directory, because the process's working directory is
  unchanged.

## Security considerations

- **Import hijack, closed.**
  - A `biq.py`, a `biq/` or a `lib/python/biq/` in the working directory cannot be imported. `-I` and script
    invocation keep the working directory off `sys.path`, the launcher strips it anyway, and it verifies where
    `biq.__file__` came from.
  - A `json.py` or other stdlib-named module in the working directory cannot shadow the standard library. It is not
    on `sys.path`.
  - `usercustomize` and the user site-packages are disabled by `-I` (`-s`). `sitecustomize` loads only from the
    interpreter's own site-packages, never from the working directory.
  - `PYTHONPATH`, `PYTHONSTARTUP` and `PYTHONHOME` are ignored under `-I` (`-E`).
- **Residual risk.** An unsubstituted root resolves to the system path `/lib/python/biq_run.py`. Exploiting that needs
  write access to a system directory, which is outside the threat model. It is recorded here.
- **Development-file exposure.**
  - Nothing new enters the model's context. The project `CLAUDE.md` is loaded from the working directory, not the
    plugin root (`architecture.md` §2 validator note).
  - The absolute plugin path does become visible in the command text. Skill invocations already expose it through
    the platform's "Base directory for this skill" header.
  - The installed copy does contain development material (`CLAUDE.md`, `evals/`, `tests/`, `docs/`). That is a
    packaging observation for M14, **not** introduced by this decision, and recorded as follow-up.
- **Boundaries unchanged.** No change to file access, privacy classification, the disclosure gate, MCP permissions,
  connector permissions or the approval model. No new code-execution capability: the launcher executes exactly the
  snippet the model already runs today with `python -c`.
- **Personal data.** The absolute path can contain the OS user name. Records written from transcripts (for example
  M13.2 manual observations) replace the home directory with `~`.

## Packaging and distribution

| Environment | Behaviour |
|---|---|
| Local Git checkout / `--plugin-dir` | The root is the checkout. Works from any working directory |
| Installed / marketplace copy | The root is the platform-cache copy (for example `~/.claude/plugins/cache/businessiq/businessiq/<version>`), as the platform supplies it. Nothing is hard-coded |
| Windows | `n9` normalises the path to `/`, and Python accepts `/`. The Bash tool on Windows is Git Bash; double quotes carry spaces. A PowerShell invocation of these bash blocks is an existing, unchanged limitation |
| Unix-like | Standard. A path containing `"`, `$` or a backtick fails closed |

- **No new prerequisite.** `python` 3.9+ was already required (R-03), and `-I` exists since 3.4.
- **No packaging metadata**, and no installation step.

## Compatibility

- **User-visible behaviour.** It is unchanged apart from now working outside the plugin root.
- **Reader tiers.**
  - Tier 1, openpyxl in the running interpreter, no longer sees a **user-site** openpyxl, because `-I` implies `-s`.
    Such a file then reads at Tier 2 (the consented runtime) or Tier 3 (stdlib).
  - Cross-tier equivalence is the existing contract (§5, S2-14), so this is a detection change, not a result change.
  - This is recorded, not hidden.
- **Unchanged:** `biq-verifier` and `.mcp.json`, the agents, engine modules (their internal paths are already
  `__file__`-anchored) and `tests/run_tests.py`.
- **Existing tests.** No existing test pins the old entry text. The only reference is the M13 pack validator's
  M13-DEF-04 check, which changes with the defect record at fix time.

## Test and acceptance requirements (for the implementing milestone)

| Id | Kind | Requirement |
|---|---|---|
| T-A | implementation | From a temporary working directory outside the repository, run `python -I <root>/lib/python/biq_run.py -c "from biq import commands; …"` on a copied synthetic CSV. It imports, runs one command, and produces output |
| T-B | implementation | From the repository root: the same result (regression) |
| T-C | packaging | Build a cache-like copy of the shipped layout (all shipped paths, no `.git`) in a temporary directory, and run T-A against **that** copy's launcher. It must import that copy's `biq`, per `--where`. This is not claimed as marketplace equivalence |
| T-D | implementation | For each of the five bare-import skills, their flows' import lines run under the launcher, and a static check shows every `from biq` is launcher-wrapped |
| T-E | implementation | A sample of relative-entry commands (sales, forecast, anomaly, business-health) runs from an external working directory |
| T-F | security | The external working directory contains a hostile `biq.py`, `biq/__init__.py`, `lib/python/biq/__init__.py`, `json.py` and `decimal.py`. None is imported; `--where` reports the plugin's `biq`; and a sentinel file those modules would write is absent |
| T-G | security | With `PYTHONPATH` pointing at a hostile `biq`, and with `-I` omitted: the first is ignored, and the second is refused with the `-I` message |
| T-H | implementation | The same command and input give byte-identical rendered output from two different working directories |
| T-I | regression | The full `python tests/run_tests.py`: 0 failures, 0 errors |
| T-J | M13.2 acceptance | A static test proves that every engine-reaching command and skill uses the launcher line, and none uses the old entry. The G-2 condition, "external working directory; engine reachable", holds by T-A and T-C. **Plus** a runtime V-1 probe recorded before any manual observation resumes |
| T-K | static | The launcher line is byte-identical in every file. The launcher imports only the stdlib, opens no network and writes no file |

## Unresolved platform facts (to verify before implementation)

- **V-1.** At runtime, on the CLI in use, a plugin **command** body and a plugin **skill** body containing
  `${CLAUDE_PLUGIN_ROOT}` reach the model with the absolute plugin path. This is statically established on 2.1.278.
  It needs one owner-run probe with a throwaway scratch plugin in a fresh session, and it must include one skill
  invoked by the model, not only by slash.
- **V-2.** The substitution holds for both invocation routes: user slash invocation, and model invocation of a
  command or skill.
- **V-3.** Inside the eval harness sandbox (G-3), whether the plugin root is substituted, and to what. This is a G-3
  item, and is not decided here.
- **V-4.** The minimum CLI version providing body substitution is unknown. The implementing milestone records the
  version it verified, as `architecture.md` §2 does.

## Consequences

**Positive**

- M13-DEF-04's cause is removed at its root, for every command and skill, by one file and one line convention.
- The import-hijack and stdlib-shadowing paths in the current entry close.
- A source checkout and an installed copy behave identically.
- M13.2's G-2 observations and M9's user-representative smoke runs become possible.

**Negative**

- 10 commands and 16 skills are edited once. The platform offers no body-free way to locate the root.
- The entry depends on a platform text substitution, statically verified and runtime-unverified (V-1).
- User-site openpyxl is no longer Tier 1.

**Follow-up required**

1. Owner review, and acceptance or amendment of this ADR.
2. The V-1 and V-2 runtime probes, owner-run.
3. An implementation milestone under its own prompt, which is not M13 (ADR-0039 I-1 and I-13 forbid product fixes in
   M13).
4. On acceptance: index it in `docs/decisions/README.md` and `architecture.md` §19. Add the entry rule to
   `architecture.md` §2 or §3, and remove §20 item 11 once fixed.
5. M14: the packaging observation that development material ships in the installed copy.

## Relationship to M13-DEF-04

This ADR is the **design** for M13-DEF-04's remediation. The defect stays `open`, and this ADR fixes nothing. The
defect's record gains a cross-reference only.

## Relationship to M13.2 G-2 and G-3

- **G-2 is unchanged.** Its external working directory is correct.
- **M13.2 stays blocked** for S3-01 to S3-11 until:
  - this design is implemented in its own milestone;
  - T-A to T-K pass;
  - V-1 and V-2 are recorded.
- **G-3 stays OPEN.** V-3 is a G-3 item.

## Implementation deferred

Nothing in this ADR has been implemented. No file under `lib/`, `commands/`, `skills/`, `tests/` or `evals/` was
changed by the investigation that drafted it.

## Revisit when

- The platform documents or changes plugin-root substitution for command and skill bodies, or exports the plugin
  root to the Bash environment.
- V-1 contradicts the static reading.
- The engine becomes an installed package by a separate decision.
- Python's isolated-mode semantics change.
