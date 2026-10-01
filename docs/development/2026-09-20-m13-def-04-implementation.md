# 2026-09-20 — M13-DEF-04 remediation: the ADR-0042 engine launcher (implementation)

**Milestone:** the dedicated M13-DEF-04 remediation milestone, under the owner's own prompt. It is **outside M13's
scope**: ADR-0039 I-13 forbids fixing a product defect within M13, and assigns the fix to "a future milestone under
its own prompt". It implements accepted ADR-0042.
**Status on completion:** COMPLETED as an implementation, verified. **M13-DEF-04 RESOLVED**, not yet committed.
M13.2 remains IN PROGRESS, with its manual observations ready to resume as a separate step. G-3, V-4 and Unix-like
runtime verification remain OPEN.
**Supersedes:** in `2026-09-19-m13-def-04-adr-0042-acceptance.md`, only "implementation not performed" and the
M13-DEF-04 "OPEN" disposition. Every earlier record is otherwise unchanged and not edited.

## 1. Starting state

- **Git.** `HEAD` = `origin/main` = `21ee21b21213ad80273650f056ef2f318023742c`, on branch `main`, with nothing staged.
- **Pre-existing uncommitted work, preserved.** The M13.2 and M13-DEF-04 documentation and eval work:
  - modified: `architecture.md`, `docs/decisions/README.md`, `docs/testing/README.md`,
    `docs/testing/coverage-matrix.md`, `docs/testing/defects.md`, `project_plan.md`;
  - untracked: ADR-0042, seven `docs/development/2026-09-19-*` records, `docs/testing/eval-suite.md`,
    `docs/testing/manual-observation-pack.md`, `evals/`, `tests/fixtures/build_eval_inputs.py`,
    `tests/fixtures/eval_inputs/`, and three test modules.
- **Governing state.** ADR-0042 was Accepted on 2026-09-19, and V-1, V-2a and V-2b had passed at runtime.

## 2. Scope

The scope was the runtime and import boundary only:

- one launcher;
- the entry line of every engine-reaching command and skill;
- the tests ADR-0042 names (T-A to T-K);
- documentation reconciliation.

Nothing else changed:

- analytics, KPI, forecast, anomaly, disclosure, connector, evidence or eval policy;
- engine modules under `lib/python/biq/`;
- `.mcp.json`, the verifier server, agents, reference, config;
- ADR-0039, ADR-0040 and ADR-0041;
- the 9 delegating commands.

## 3. Launcher design (`lib/python/biq_run.py`)

The launcher is stdlib only, imports `sys`, `builtins`, `json` and `os`, and is 121 lines long. In order, it:

1. **Checks isolation first.** Before anything else is imported, `sys.flags.isolated` must be set, or it exits with
   status 2 and says to use `python -I`. Under `-I`:
   - `PYTHON*` variables are ignored;
   - user site-packages are disabled;
   - neither the working directory nor the script directory is on `sys.path`.
2. **Locates itself.** `ENGINE = dirname(realpath(__file__))` and `ROOT = ENGINE/../..`. It never uses the working
   directory to find the plugin, and it contains no fixed path.
3. **Validates the layout.** `ENGINE` must end in `lib/python`, `ENGINE/biq/__init__.py` must exist, and
   `ROOT/.claude-plugin/plugin.json` must parse and name `businessiq`.
4. **Rebuilds the import path.** It refuses if `biq` is already imported. It then rebuilds `sys.path` as `[ENGINE]`
   plus the interpreter's own entries, minus `''`, `'.'` and anything that resolves to the working directory. It
   uses `os.getcwd()` only to exclude that directory.
5. **Verifies the engine.** It imports `biq` and checks that `realpath(biq.__file__)` is `ENGINE/biq/__init__.py`.
   Otherwise it exits with status 2.
6. **Runs the code.** `-c CODE [ARG…]` executes `CODE` in a fresh `__main__` namespace, with `sys.argv` shaped as
   Python's own `-c` shapes it. `--where` prints sorted JSON: `biq_module`, `engine`, `isolated`, `plugin`,
   `plugin_root`, `python`. Any other argument form exits with status 2 and a usage message.
7. **Adds no side effects.** It never changes the working directory, sets no environment variable and writes no file.
   An exception in `CODE` propagates as it would under `python -c`, exiting with status 1.

## 4. Commands migrated (10)

- anomaly-detection
- ask-business-data
- business-health
- cash-flow-analysis
- customer-analysis
- product-analysis
- profitability-analysis
- retrieval-slice (2 blocks)
- revenue-forecast
- sales-analysis

**The change** to each block:

- the opener `python -c "` became `python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py" -c "`;
- the line `import sys; sys.path.insert(0, 'lib/python')` was removed, or reduced to `import json` where `json` was
  used. `sys` was used nowhere else in those blocks.

No other line changed.

**Not changed:** the 9 delegating commands (benchmark-comparison, company-analysis, competitor-analysis,
decision-support, executive-report, industry-research, market-analysis, strategy-analysis, swot-analysis). None
carries an engine block; they reach the engine through their skills.

## 5. Skills migrated (16)

- **Relative-entry bash blocks (11 skills), the same two-line change as §4:** biq-anomaly-detection,
  biq-company-analysis, biq-competitor-analysis, biq-customer-intelligence, biq-data-ingestion (2 blocks),
  biq-financial-analysis, biq-forecasting, biq-industry-research, biq-market-analysis, biq-product-intelligence,
  biq-sales-intelligence.
- **The five bare-import skills:** biq-benchmark-comparison, biq-decision-support (2 flows), biq-executive-report
  (2 flows), biq-strategy-recommendations, biq-swot. Their ```python flow blocks are now bash launcher blocks in the
  launcher's quoted-heredoc form:

  ```
  python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py" -c "$(cat <<'PY'
  <flow, byte for byte unchanged>
  PY
  )"
  ```

  The heredoc passes the flow's text verbatim as the `-c` argument, which ADR-0042 fixes as the launcher's only code
  interface. It needs no quote escaping (the flows carry up to 164 double quotes), and adds no launcher mode.
- **Found during migration:** four research skills (company-analysis, competitor-analysis, industry-research,
  market-analysis) also had bare `from biq import …` ```python footing flows. Those flows were not in the design
  inventory's bare-import list. They were migrated the same way, so no command or skill imports `biq` outside the
  launcher.

**Observation, not changed.** The flows are templates the model adapts. They contain placeholders such as `reply_text`
and `"sy-…"`, and one, in biq-benchmark-comparison, holds pre-existing non-Python pseudo-code
(`stated={ ...the six quoted dimensions... }`). The migration preserved them exactly, so the static guard checks form
and boundary, not that the code compiles.

**No prose** in any command, skill, reference or agent described the old mechanism, so none needed changing.

## 6. Security boundary

| Threat | Result | Test |
|---|---|---|
| `biq.py` in the working directory | not imported | T-F sentinel absent; `biq` origin is the plugin |
| `biq/` in the working directory | not imported | T-F |
| `lib/python/biq/` in the working directory | not imported. **Control:** the old entry did import it | T-F `test_the_fixture_is_live_under_the_old_entry` |
| `json.py`, `decimal.py` in the working directory | not imported; both origins are outside the working directory | T-F |
| Hostile `PYTHONPATH` holding `biq/` and `json.py` | ignored. **Control:** without isolation it was imported | T-G |
| Run without `-I` | refused, exit 2, before any import; sentinel absent | T-G |
| Malformed arguments | refused, exit 2 | T-G |
| A copy whose manifest is not `businessiq` | refused, exit 2; the code did not run | T-C |
| Imported package origin | verified by the launcher; asserted in T-A, T-C, T-F, T-G and T-J | — |

## 7. Tests

| Id | Test | Result |
|---|---|---|
| T-A | `ExternalWorkingDirectory` (3): the `/sales-analysis` block runs from a temporary working directory outside the repository; the engine comes from the plugin; `input.csv` resolves in the working directory, which the launcher leaves unchanged; the old entry fails there (control) | PASS |
| T-B | `RepositoryRoot` (2): runs from the repository root; `--where` reports the repository | PASS |
| T-C | `CacheLikeCopy` (3): a copy of the shipped layout at `…/plugin cache/businessiq/0.1.0` (a path with a space). `--where` reports the copy and not the repository; `/business-health` runs from an external working directory on the copy's engine; a non-`businessiq` manifest is refused. **A local packaging test, not marketplace equivalence** | PASS |
| T-D | `BareImportSkills` (1): for each of the five skills and each launcher block, the imports run through the launcher from an external working directory, and every loaded `biq` module lies in the plugin's engine. The same imports without the launcher fail with `No module named 'biq'` | PASS |
| T-E | `RepresentativeCommands` (2): sales-analysis, revenue-forecast, anomaly-detection and business-health run from an external working directory on a 24-period synthetic CSV, with their headings present and no halt; the data-ingestion skill's connector-resolution block runs | PASS |
| T-F | `WorkingDirectoryShadowing` (2) | PASS |
| T-G | `EnvironmentAndIsolation` (4) | PASS |
| T-H | `WorkingDirectoryIndependence` (2): identical input in two directories gives byte-identical output and identical `--where`; a different input in a third directory gives different output with identical `--where`. This separates import resolution from input resolution | PASS |
| T-J | `M132ExternalWorkingDirectoryPrerequisite` (2): every engine block (at least 34) uses the substituted launcher; a command and a skill block run from a cache-like copy at a path with a space, from an external working directory holding planted modules, and the engine comes from the copy with nothing planted imported | PASS |
| T-K | `unit.test_m13_def04_static_guard` (14): no old entry and no `sys.path` manipulation; every engine block opens with the launcher; no `biq` import outside one; the five skills covered; the delegating commands carry no engine block; no working-directory or environment lookup; the root appears only on the launcher line; one launcher, stdlib only; isolation checked before any other import; no fixed path. **Mutation-checked** on a scratch copy: 6 of 6 corruptions caught | PASS |
| T-I | Full regression, `python tests/run_tests.py` | **4,872 tests, 0 failures, 0 errors, 29 skipped, 253.2 s**: the previous 4,837, plus 21 integration and 14 static tests. The skip count is unchanged |

**How the tests run.** They emulate the platform's verified body substitution (`${CLAUDE_PLUGIN_ROOT}` → the plugin
path with `/`) and bash's argument passing on the **real command and skill text**. They then run the launcher as a
subprocess, with no shell, from temporary directories. No Claude session, eval, web or MCP is involved.

**One harness fix, found during development.** The first run decoded child output as UTF-8, but on Windows a piped
child writes cp1252. That is a test defect, fixed. Checked:

- Claude Code's shell sets no `PYTHON*` variable here;
- the stdout encoding is cp1252 both with and without `-I`.

So `-I` changes no output encoding in this environment.

`unit.test_m13_manual_observation_pack`'s WD-1 test was **updated** to the remediated state, as its docstring
required ("must change with the record").

## 8. Remaining limitations

- **G-3: OPEN.** The eval sandbox was not tested.
- **V-4: OPEN.** Only CLI 2.1.278 is verified.
- **Unix-like runtime: OPEN.** The body substitution was verified on Windows only. The launcher's tests ran on
  Windows.
- **Encoding.** Under `-I`, a user's `PYTHONIOENCODING` or `PYTHONUTF8` is ignored. None is set in the observed Claude
  Code shell.
- **Reader tiers.** A user-site openpyxl is no longer Tier 1 (ADR-0042, *Compatibility*).
- **Model reads a file instead of invoking it.** If the model opens a skill file directly, the root is not
  substituted. The path then becomes `/lib/python/biq_run.py` and the run fails loudly.
- **Register vocabulary.** The §G.1 `status` field of M13-DEF-04 remains `open`. ADR-0039's closed vocabulary (`open`,
  `fixed_infrastructure`, `withdrawn`) has no state for a product defect fixed outside M13, and the validator
  enforces it. The resolution is recorded in the register-state table, the record's disposition and
  `project_plan.md`. Changing the field needs an owner decision amending ADR-0039.
- **M9.** M9's pending live smoke tests no longer depend on the repository root for the engine. M9 itself is
  unchanged.

## 9. M13-DEF-04 and M13.2

- **M13-DEF-04: RESOLVED**, remediated and verified, not yet committed.
- **M13.2: IN PROGRESS.** The S3 manual observations are **ready to resume** as a separate, owner-controlled step.
  T-J establishes readiness only.
- **No eval and no manual observation was executed.** No `docs/testing/manual/` record exists.

## 10. Files changed by this milestone

| Kind | Files |
|---|---|
| Production | `lib/python/biq_run.py` (new) |
| Commands (10) | anomaly-detection, ask-business-data, business-health, cash-flow-analysis, customer-analysis, product-analysis, profitability-analysis, retrieval-slice, revenue-forecast, sales-analysis |
| Skills (16) | the 11 relative-entry skills and the 5 bare-import skills listed in §5 |
| Tests | `tests/integration/test_m13_def04_engine_entry.py` (new), `tests/unit/test_m13_def04_static_guard.py` (new), `tests/unit/test_m13_manual_observation_pack.py` (WD-1 test updated) |
| Documentation | `architecture.md` (§2 *Engine entry* row, §19 row, §20 item 11), `project_plan.md`, `docs/decisions/README.md` (0042 row), `docs/testing/defects.md`, `docs/testing/manual-observation-pack.md`, `docs/testing/eval-suite.md`, `docs/testing/README.md`, `docs/testing/coverage-matrix.md`, and this record |

**Unchanged:** ADR-0042's own text (its Status line stays as accepted), and ADR-0039, ADR-0040 and ADR-0041.

## 11. Git

**No commit and no push.** Nothing is staged.
