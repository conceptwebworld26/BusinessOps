# 2026-09-19 — M13-DEF-04 remediation design investigation (design only)

**Milestone:** 13 — Test Hardening & Evals, context M13.2. This record designs a product-defect remediation whose
implementation belongs to a later milestone (ADR-0039 I-13).
**Status on completion:** REVIEW. The design is complete, and ADR-0042 is **Proposed**. **M13-DEF-04 remains OPEN.**
Implementation is deferred. M13.2 remains IN PROGRESS, and its manual observations remain BLOCKED.
**Supersedes:** None. Every earlier record is unchanged.

## 1. Prompt / task performed

The owner's "M13-DEF-04 Remediation Design Investigation — design only" prompt. It asked me to:

- confirm the defect and inventory the execution surface;
- establish from evidence where `${CLAUDE_PLUGIN_ROOT}` applies;
- evaluate the resolution mechanisms and choose one centralised architecture;
- analyse security and packaging;
- design the tests, assess the M9 impact, and draft one Proposed ADR if one is warranted.

It prohibited:

- implementation;
- edits to production files, commands, skills, tests or evals;
- workarounds (copy, link, `PYTHONPATH`, running from the repository root);
- eval and manual-observation execution;
- web, MCP and authentication use;
- committing and pushing.

## 2. Repository state

| Item | Observed |
|---|---|
| Branch | `main`, tracking `origin/main` |
| `HEAD` | `21ee21b21213ad80273650f056ef2f318023742c` ("M13.2: accept deterministic eval fixture contract") |
| Working tree | Dirty, with the uncommitted M13.2 work of 2026-09-19. It was left untouched, and nothing was reset, stashed or amended |

## 3. Defect reproduction (deterministic, no session, no model; Python 3.13.1)

| Where | Command | Result |
|---|---|---|
| Empty directory outside the repository | `python -c "import sys; sys.path.insert(0, 'lib/python'); from biq import commands"` | `ModuleNotFoundError: No module named 'biq'`, exit 1 (WD-1 record) |
| Repository root | same | imports, exit 0 |
| Repository root, no path setup (the five bare-import skills) | `python -c "from biq import config"` | `ModuleNotFoundError: No module named 'biq'` |
| A working directory containing `lib/python/biq/__init__.py` (hostile) | the current entry, `import biq` | **the hostile package ran**: "HIJACKED: lib/python/biq resolved from the user cwd" |
| A working directory containing `json.py` | `python -c "… import json"` | **the hostile `json.py` ran** (`sys.path[0] == ''`) |
| Same directory | `python -I -c "…"` | `sys.path[0]` is the stdlib zip, and the stdlib `json` is imported |
| Same directory | `python <dir>/probe.py`, and with `-I` | the working directory is not on `sys.path`. Without `-I`, `sys.path[0]` is the script's directory; with `-I`, it is neither |

The hostile probes ran in a scratchpad directory, which was deleted afterwards.

## 4. Execution-surface inventory

| Group | Members | Engine entry |
|---|---|---|
| Commands with the relative entry (10) | anomaly-detection, ask-business-data, business-health, cash-flow-analysis, customer-analysis, product-analysis, profitability-analysis, retrieval-slice, revenue-forecast, sales-analysis | `sys.path.insert(0, 'lib/python')`, the only form in use (23 occurrences) |
| Skills with the relative entry (11) | biq-anomaly-detection, biq-company-analysis, biq-competitor-analysis, biq-customer-intelligence, biq-data-ingestion, biq-financial-analysis, biq-forecasting, biq-industry-research, biq-market-analysis, biq-product-intelligence, biq-sales-intelligence | same |
| Bare-import skills (5) | biq-benchmark-comparison, biq-decision-support, biq-executive-report, biq-strategy-recommendations, biq-swot | `from biq import …` in fenced `python` flow blocks, with no path setup (§5) |
| Commands reaching the engine only through skills (9) | benchmark-comparison, company-analysis, competitor-analysis, decision-support, executive-report, industry-research, market-analysis, strategy-analysis, swot-analysis | none of their own. They invoke the skills. `decision-support`, `executive-report`, `strategy-analysis` and `swot-analysis` mention `lib/python/…` only as prose. There are 9: 18 model-invocable commands minus the 9 model-invocable ones carrying the entry (`retrieval-slice`, the tenth carrier, is not model-invocable). **Correction:** the WD-1 record and the defect register said "8"; the register and the pack are corrected here, and the past WD-1 record is superseded on this count only |
| Plugin-root-safe | `.mcp.json` → `biq-verifier` (`${CLAUDE_PLUGIN_ROOT}/lib/python/biq/verification_server.py`) | MCP launch substitution |
| Engine internals | `config.py`, `context/loader.py`, `kpi/engine.py`, `quality/report.py`, `verification.py`, `connectors/binding.py`, `connectors/catalogue.py`, `data_profile.py`, `ingest/readers.py` | `__file__`-anchored: safe once `biq` is imported |
| Agents | `biq-research-scout`, `biq-analysis-verifier` | no engine import |
| Existing entrypoint or packaging | none | no `pyproject.toml`, `setup.py`, `setup.cfg`, console script or launcher exists. The engine is a **source tree imported from the plugin root**, not an installed package |

## 5. The five bare-import skills

Each has one or more fenced `python` blocks that document the flow. The blocks begin `from biq import …` and never set
a path:

| Skill | Blocks |
|---|---|
| `biq-benchmark-comparison` | line 87 |
| `biq-decision-support` | lines 81 and 201 |
| `biq-executive-report` | lines 78 and 157 |
| `biq-strategy-recommendations` | line 69 |
| `biq-swot` | line 82 |

They depend on `biq` already being importable. The model can only make it importable by borrowing the relative entry
from another component, which works only from the repository root. They are API flows, not complete invocations.

## 6. Platform and runtime evidence

**Method.** Static byte search of the installed Claude Code CLI binary, `~/.local/bin/claude.exe`, version 2.1.278,
for `CLAUDE_PLUGIN_ROOT`, `Base directory for this skill` and `CLAUDE_SKILL_DIR`. This is read-only: nothing was
executed and no state was altered. The fragments below are quoted from the embedded code. Its identifiers are minified
and specific to this build.

| Layer | Finding | Quoted fragment |
|---|---|---|
| Plugin command and skill prompt builder | `${CLAUDE_PLUGIN_ROOT}` in the **body text** is replaced with the plugin path | `async getPromptForCommand(sr,Bn){let wn=y.isSkillMode?\`Base directory for this skill: ${cE(n.filePath)}…${M}\`:M;if(wn=Bfe(wn,sr,!0,Oe,pw),wn=n9(wn,{path:g,source:r}),…if(y.isSkillMode)wn=wn.replace(/\$\{CLAUDE_SKILL_DIR\}/g,he);` |
| The substitution function | Exact brace form only. Backslashes become `/` | `function n9(e,r){let n=(s)=>s.replace(/\\/g,"/"),i=e.replace(/\$\{CLAUDE_PLUGIN_ROOT\}/g,()=>n(r.path));…` |
| Command loading | `g` is the plugin path | `Man(w.commandsPath,w.name,w.source,w.manifest,w.path,{isSkillMode:!1},M)` |
| Skill loading | The same builder, skill mode | `Oan(h.skillsPath,h.name,h.source,h.manifest,h.path,y)` → `dX(…,g,!0,{isSkillMode:!0,…})` |
| MCP stdio servers | Substituted in `command`/`args`, and set as env | `let ve={CLAUDE_PLUGIN_ROOT:n.path,CLAUDE_PLUGIN_DATA:hye(n.source),...Ee.env\|\|{}}` |
| Hooks and monitors | Substituted and exported to the hook process | `if(B){if(Fn.CLAUDE_PLUGIN_ROOT=yt(B),…` ("…${CLAUDE_PLUGIN_ROOT}, ${CLAUDE_PLUGIN_DATA}, ${CLAUDE_PROJECT_DIR}… are substituted. Runs in the session cwd… prefix with `cd "${CLAUDE_PLUGIN_ROOT}" && ` if the script needs its own directory.") |
| The Bash tool environment | **Not set.** `env` in this development session, which has BusinessIQ installed at user scope, shows no `CLAUDE_PLUGIN*` variable. Bash runs in the session's working directory, and the shell reset to it after each `cd` in this session | observation |

**Verified:**

- body substitution exists for plugin commands and skills (statically, 2.1.278);
- it is text substitution, not a shell variable;
- MCP and hooks receive it both as substitution and as an environment variable;
- Bash does not have it;
- the Python isolation facts in §3.

**Unverified:**

- runtime observation of body substitution (V-1), and both invocation routes (V-2);
- behaviour inside the eval sandbox (V-3, a G-3 item);
- the minimum CLI version (V-4).

**Installed-copy structure.** The owner's user-scope install, recorded in `~/.claude/plugins/installed_plugins.json`,
is at `~/.claude/plugins/cache/businessiq/businessiq/0.1.0` (commit `8d52b0e`). It contains the whole repository tree,
including `CLAUDE.md`, `docs/`, `tests/` and `lib/python/biq/`.

## 7. Findings

1. **Root cause.** The engine entry resolves against the working directory. That covers the explicit relative
   entry, the bare imports that rely on it, and `python -c` putting the working directory on `sys.path`.
2. **Two faults share that one cause:**
   - a portability failure: the engine cannot be imported from outside the plugin root;
   - a security failure: import hijack and stdlib shadowing from the working directory.

   One defect covers both, because the cause and the remedy are the same. No new defect id is needed.
3. **The platform gives command and skill bodies exactly one plugin-root mechanism:** `${CLAUDE_PLUGIN_ROOT}` body
   substitution. No environment variable exists in the model's shell.

## 8. Architecture decision

**Proposed [ADR-0042](../decisions/ADR-0042-plugin-root-anchored-isolated-engine-entry.md).** Every engine-reaching
command and skill enters through one launcher:

```bash
python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py" -c "<unchanged engine code>"
```

- **What the launcher does.** `lib/python/biq_run.py` is new, stdlib only, and sits beside the `biq` package. It:
  1. resolves its directory from `__file__`;
  2. validates `biq/` and `.claude-plugin/plugin.json` (`name: businessiq`);
  3. requires `sys.flags.isolated`;
  4. strips the working directory from `sys.path` and inserts itself;
  5. imports `biq` and verifies that `biq.__file__` lies under its own directory;
  6. executes the code.
- **`--where`** prints the resolved facts as JSON, for tests and the owner's pre-flight.
- **What the platform supplies.** The absolute root, through text substitution in the body. The shell never sees a
  variable.
- **Where the path logic lives.** Only in `biq_run.py`. The per-file edit is one identical line, enforced by a static
  test.

## 9. Rejected approaches

These are summarised here; the reasons are in full in ADR-0042.

| Approach | Why rejected |
|---|---|
| (B) A root substituted inside each snippet | Duplicated path logic, a quoting hazard, and it keeps `python -c`'s working-directory shadowing |
| (C) The root from the process environment | Not set in Bash |
| (D) An installed package | Forbidden by `CLAUDE.md` §4 and ADR-0008, needs an install step, and risks version drift |
| (E) A SessionStart hook exporting the root | Adds a new component, runs at every start, and is unverified |
| (F) The skill base-directory header, or `${CLAUDE_SKILL_DIR}` | Skills only, and relative arithmetic |
| (G) Repository root, `PYTHONPATH`, or a copy or link | Breaks G-2's boundary, and not a user's environment |
| (H) An MCP server for imports | Out of scope, and it changes permissions |

## 10. Security analysis

| Concern | After ADR-0042 |
|---|---|
| `biq.py`, `biq/` or `lib/python/biq/` in the working directory | Not importable. The working directory is off `sys.path` (`-I`, script invocation, explicit strip), and the origin of `biq.__file__` is verified |
| `json.py` or another stdlib name in the working directory | Not importable. The working directory is off `sys.path` |
| `PYTHONPATH`, `PYTHONSTARTUP` | Ignored (`-I` implies `-E`) |
| `usercustomize`, user site-packages | Disabled (`-I` implies `-s`). `sitecustomize` loads only from the interpreter's own site-packages |
| An unsubstituted root | Fails loudly with "can't open file `/lib/python/biq_run.py`". Exploiting it needs system-directory write access, which is outside the threat model |
| Development files | No new context injection. The project `CLAUDE.md` loads from the working directory, not the plugin root. The absolute plugin path becomes visible, as the platform's skill base-directory header already makes it. The installed copy ships `CLAUDE.md`, `evals/` and `docs/`: a pre-existing packaging observation, referred to M14 |
| Privacy, disclosure, MCP, connector and approval boundaries | Unchanged |
| New code-execution capability | None. The launcher runs the snippet the model already runs |
| Personal data | Paths can contain the OS user name. Records replace the home directory with `~` |

## 11. Packaging analysis

- **Source checkout:** the root is the checkout.
- **Installed or marketplace copy:** the root is the copy the platform supplies, with nothing hard-coded.
- **Windows:** `n9` normalises to `/`, and Git Bash double-quoting carries spaces. `"` is impossible in Windows
  filenames.
- **Unix-like:** a path containing `"`, `$` or a backtick fails closed.
- **No new prerequisite:** Python 3.9+ is required already, and `-I` has existed since 3.4.
- **Behaviour change:** a user-site openpyxl is no longer Tier 1; Tier 2 or Tier 3 reads the file instead, with
  equivalence being the existing contract.

## 12. Test plan (for the implementing milestone)

ADR-0042 T-A to T-K. By kind:

- **Implementation:**
  - T-A: an external working directory with a copied synthetic CSV;
  - T-B: the repository root;
  - T-D: the five bare-import skills;
  - T-E: a command sample (sales, forecast, anomaly, business-health);
  - T-H: byte-identical output across working directories.
- **Packaging:** T-C, a cache-like copy of the shipped layout in a temporary directory. Its `--where` must report
  that copy. It is not claimed as marketplace equivalence.
- **Security:**
  - T-F: hostile `biq.py`, `biq/`, `lib/python/biq/`, `json.py` and `decimal.py`, checked by sentinel files;
  - T-G: `PYTHONPATH` set to a hostile `biq`, and `-I` omitted, which must be refused.
- **Regression:** T-I, the full suite.
- **Static:** T-K, one byte-identical launcher line everywhere, no old entry, and a stdlib-only launcher.
- **M13.2 acceptance:** T-J, the static launcher-line proof plus T-A and T-C, **and** the V-1 and V-2 runtime
  probes, recorded before any manual observation resumes.

## 13. M9 impact

- **What is affected.** The four M9-D commands await owner-run fresh-session live smoke tests: `/company-analysis`,
  `/market-analysis`, `/competitor-analysis` and `/industry-research`. Their skills carry the relative entry, which
  is used for the disclosure gate and the retrieval seam. Their criteria (for example the M9-D.1 record, "The
  fresh-session live smoke test") specify no working directory.
- **When it blocks them.** Run from the repository root, as every earlier live run was, DEF-04 does not block them.
  Run from a user-representative directory, it does.
- **After remediation.** ADR-0042 removes that prerequisite.
- **Separate, unrelated prerequisites:**
  - a fresh-session registration, which is an owner action;
  - live web retrieval by `biq-research-scout`, which is M9's own requirement;
  - the open ADR-0018 source-claim question noted in the M9-D.1 record.
- **Defects.** M13-DEF-04 remains the single defect for this cause. M9's documentation needs a note only after
  remediation, saying that smoke runs may use a user working directory. M9 is not changed here.

## 14. Implementation plan (later milestone; not performed)

1. Owner acceptance of ADR-0042, or an amendment.
2. The V-1 and V-2 runtime probes, owner-run: a scratch plugin via `--plugin-dir` in a fresh session. Record the
   substituted text for one command and for one model-invoked skill.
3. Add `lib/python/biq_run.py` with its unit tests: T-K, T-F, T-G and `--where`.
4. Replace the entry line in the 10 commands and 11 skills. Convert the five bare-import skills' executable blocks to
   launcher invocations. Leave the 9 delegating commands' bodies alone, since they contain no entry.
5. Add the static launcher-line test (T-J/T-K), then T-A to T-E and T-H, plus the full regression (T-I).
6. Documentation:
   - `architecture.md`: the §2/§3 entry rule, and remove §20 item 11;
   - `docs/testing/defects.md`: M13-DEF-04, as the remediation milestone's own prompt determines;
   - the manual-observation pack's WD-1 section and the related pack-validator test;
   - the ADR indexes;
   - the M9 note.
7. Then, and only then: the M13.2 acceptance evidence (T-J with V-1), before the owner resumes manual observations.

**Files that must not change** in that milestone: `.mcp.json`, `lib/python/biq/verification_server.py`, engine
modules other than the new launcher, `agents/`, `reference/`, `config/`, `evals/`, ADR-0039/0040/0041,
`tests/run_tests.py` and `.gitignore`.

## 15. Unresolved verification items

- **V-1:** runtime body substitution for commands and skills.
- **V-2:** both invocation routes.
- **V-3:** the eval sandbox (G-3).
- **V-4:** the minimum CLI version.

None is assumed.

## 16. Files

**Created:**

- `docs/decisions/ADR-0042-plugin-root-anchored-isolated-engine-entry.md` (**Proposed**)
- this record

**Modified:**

- `docs/testing/defects.md`: a cross-reference paragraph under M13-DEF-04. Every field and the `open` status are
  unchanged.
- `project_plan.md`: the header bullet, and the M13-DEF-04 *Known issues* row, as status notes.

No production, command, skill, test, eval, schema or configuration file changed.

## 17. Explicit statements

- **No implementation was performed.**
- **No eval and no manual observation was performed.** No web, MCP or authentication tool was used.
- **M13-DEF-04 remains OPEN.**
- **M13.2 remains IN PROGRESS, with manual observations BLOCKED.**
- **No commit and no push.**
