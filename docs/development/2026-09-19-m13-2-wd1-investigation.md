# 2026-09-19 — M13.2 WD-1 investigation: the engine entry is working-directory-relative (M13-DEF-04)

**Milestone:** 13 — Test Hardening & Evals, part M13.2, under ADR-0039 as amended by ADR-0040 and ADR-0041.
Investigation and contract-compatibility only.
**Status on completion:** IN PROGRESS. The classification is **C, a product/packaging defect**. M13-DEF-04 is recorded
`open` and not fixed. G-2 is unchanged. **Zero manual observations performed.** Nothing committed, nothing pushed.
**Supersedes:** in `2026-09-19-m13-2-manual-observation-pack.md`, only the "not recorded as a defect" statement and
item 1 of §15 (the owner's WD-1 decision). That record is otherwise unchanged and not edited.

## 1. Prompt / task performed

The owner's "M13.2 WD-1 Execution-Environment Investigation" prompt. It asked me to:

- trace how the plugin locates its engine;
- decide from evidence whether G-2's external working directory is compatible with the product, choosing one of
  four categories: A no blocker, B environment adjustment, C product/packaging defect, or D contract conflict;
- check the security and evidence boundary of any adjustment;
- record the result.

It prohibited:

- observations, sessions and evals of any kind;
- web, MCP and authentication use;
- production changes and invented runtime mechanisms;
- committing and pushing.

## 2. Objective

Establish whether a manual observation can be both executable and faithful to G-2's boundary, and classify WD-1
honestly.

## 3. Changes made

### 3.1 What G-2's external working directory protects

`eval-suite.md` (*Manual observation*) gives the reasons for it:

- running inside the repository "would load the development `CLAUDE.md`, the case files and their graders into the
  observed session";
- the working directory holds only the case's named inputs (ADR-0041 §5; §F.6, copy only);
- the scenario "stands in for" an eval case, whose model sees no grader.

The protected property is an uncontaminated, user-faithful session.

### 3.2 How the engine is reached (trace)

| Question | Finding | Evidence |
|---|---|---|
| A. Plugin root | The directory the plugin is loaded from. For the owner's installed copy, that is `~/.claude/plugins/cache/businessiq/businessiq/0.1.0` (user scope, commit `8d52b0e`); under `--plugin-dir`, the given path | `~/.claude/plugins/installed_plugins.json` (read locally); the M9-B record |
| B. Does the loader make the repository available independently of the working directory? | For the engine, **no verified mechanism**. `${CLAUDE_PLUGIN_ROOT}` is verified only in `.mcp.json` launch arguments. A development session with BusinessIQ installed has **no** `CLAUDE_PLUGIN*` variable in its Bash environment. The Bash tool's working directory is the session's working directory, and this session's shell reset to it after each `cd` | M11 record, probe A; `env` in this session; this session's tool output |
| C. Does command or skill execution assume the working directory is the repository? | **Yes.** The only entry is `sys.path.insert(0, 'lib/python')` | 23 occurrences, one form |
| D. Which files | 10 commands and 11 skills carry the entry. 5 skills import `biq` with no path setup, and fail even from the repository root. 8 model-invocable commands reach the engine only through skills | `grep`; the M13-DEF-04 record |
| E. Kind of path | **Production/runtime**: the command wrappers and skill scripts the model runs. Not test-only. The engine's internal paths are `__file__`-anchored and safe | `lib/python/biq/*` |
| F. Universal or selective | **Universal.** All 19 commands and all 16 skills reach the engine only through a working-directory-relative path. Only `biq-verifier` (MCP) is plugin-root-safe | as above |

### 3.3 Reproduction (verbatim, 2026-09-19, Python 3.13.1)

```
$ ls -A  (empty dir outside the plugin root)
$ python -c "import sys; sys.path.insert(0, 'lib/python'); from biq import commands"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import sys; sys.path.insert(0, 'lib/python'); from biq import commands
                                                  ^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'biq'
exit 1
--- from the plugin root:
imported
exit 0
```

`python -c "from biq import config"`, run from the repository root with no path setup (the five bare-import skills),
also raises `ModuleNotFoundError`. `biq` is not installed in the interpreter.

### 3.4 Candidate environments (security and evidence check)

| Candidate | Engine reachable | Development `CLAUDE.md` injected | `evals/` graders exposed | Faithful to a user | Verdict |
|---|---|---|---|---|---|
| G-2 as written (outside working directory; plugin from the repository or installed) | **No** | No | No | Yes | Faithful, but not executable for engine-dependent properties |
| Working directory = repository root | Yes | **Yes**: this development session carries it as "project instructions" | **Yes**: readable in the working tree | No | Rejected |
| Owner-set `PYTHONPATH`, or a copy or link of `lib/python` in the working directory | Yes | No | No | **No**: not a repository-defined or platform-defined mechanism, and it changes the execution environment | Rejected |
| `${CLAUDE_PLUGIN_ROOT}` in command or skill bodies | Unverified | n/a | n/a | n/a | Rejected: unverified, and a product change (I-1, I-13) |

**Constant across every candidate:** no real business data, credential, web tool or MCP tool is introduced.

**Conclusion:** no environment is both executable and faithful.

### 3.5 Classification: C

**Why C.** The contract places the installed plugin and the working directory in different places:

- the distribution is a marketplace install (`architecture.md` §2; ADR-0001);
- runtime state lives in the user's working directory, "outside the repo" (`architecture.md` §13);
- the file path must stay "fully functional standalone, forever" (`CLAUDE.md` §2, principle 8).

The shipped entry reaches the engine only when the two coincide. Nothing legitimate bridges them (§3.4).

**Why not the others:**

- **A:** the setup is correct, and the failure is the product's.
- **B:** no legitimate adjustment exists.
- **D:** G-2's working directory is the one the architecture describes, so G-2 and the contract agree. The conflict is
  between the product and its own architecture.

**Recorded as M13-DEF-04** in `docs/testing/defects.md`. The record has every §G.1 field:

- `source`: `test` (deterministic check);
- `defect_class`: `product`;
- `status`: `open`;
- `blocks_m13_completion`: `no`, by rule.

**What was not done:**

- The requirement check was **not committed** as a failing test, following ADR-0039 §G and the M13-DEF-01 precedent.
- No production file changed, and no workaround was added.
- **Honest limit:** no session was run, so whether a model locates the engine another way is not observed. The
  defect is in the documented entry, which is what the product instructs the model to execute.

### 3.6 Effect on the manual observations

- **S3-01 to S3-11: blocked for meaningful observation while M13-DEF-04 is open.** Each depends on engine output: the
  quality gate, mapping, forecast, anomaly scan, disclosure gate or connector registry. The named connector absence,
  for example, is produced by `registry.resolve('~~crm')` in `biq-data-ingestion`, behind the same entry.
- **S3-12: not blocked at the property observed.** Its routing property is decided at skill selection, before any
  engine call.
- **What the pack says.** Scenarios performed now would record what a session does under the defect, not the behaviour
  their cases target. The pack says so. How M13.2 proceeds is the owner's decision: perform and record as they stand,
  or defer until a later milestone remediates M13-DEF-04.

### 3.7 Documentation

- `defects.md`: the M13-DEF-04 record and register row.
- `manual-observation-pack.md`: the WD-1 investigation result.
- `eval-suite.md`, `docs/testing/README.md` and `coverage-matrix.md`: the state paragraph only. No row, status,
  evidence or total changed.
- `architecture.md` §20: item 11, within ADR-0039 §A.2, following the M13-DEF-03 precedent in item 10.
- `project_plan.md`:
  - the header, the next gate and the M13 row;
  - the manual-scenarios row moves from `PLANNED` to `BLOCKED`;
  - a *Known issues* row for M13-DEF-04.

### 3.8 Test

`unit.test_m13_manual_observation_pack` gains one test. While M13-DEF-04 is open, the pack must:

- cite it;
- state classification C;
- state that G-2 is unchanged;
- state that S3-01 to S3-11 are blocked.

The record's reproducer must carry the entry. When a later milestone fixes the defect, this test must change with the
record.

## 4. Files created

| File | Purpose |
|---|---|
| `docs/development/2026-09-19-m13-2-wd1-investigation.md` | This record |

## 5. Files modified

- `docs/testing/defects.md`
- `docs/testing/manual-observation-pack.md`
- `docs/testing/eval-suite.md`
- `docs/testing/README.md`
- `docs/testing/coverage-matrix.md`
- `architecture.md` (§20 only)
- `project_plan.md`
- `tests/unit/test_m13_manual_observation_pack.py` (one test and a docstring line)

No `commands/`, `skills/`, `lib/`, `agents/`, `reference/`, `config/`, `.claude-plugin/` or `.mcp.json` file changed.
No case or fixture changed.

## 6. Files deleted

None.

## 7. Features implemented

None.

## 8. Tests performed

- The reproducer (§3.3).
- `unit.test_m13_manual_observation_pack`, `unit.test_m13_eval_cases`, `unit.test_m13_coverage_matrix` (it validates
  the defect register), `integration.test_m13_eval_input_preconditions` and `unit.test_manifest`.
- `claude plugin validate . --strict`.
- The full regression, because a test module changed.
- `git diff --check`, a whitespace scan, a secret scan and the scope audit.

**Not run:** any eval, any manual scenario, and any session.

## 9. Test results

Recorded in the task report of this session.

## 10. Issues discovered

**M13-DEF-04** (§3.5). **Related:** M9's pending fresh-session live smoke tests run under the same entry. That is
noted in the record, and M9 is not changed.

## 11. Decisions made

- The classification, C, made from evidence.
- No ADR: G-2 and the contract are unchanged.

## 12. Architecture changes

`architecture.md` §20 item 11 records the limitation. No design change.

## 13. Project-plan updates

- The `manual_observation` scenarios move from `PLANNED` to **`BLOCKED`**, on M13-DEF-04.
- A *Known issues* row is added for M13-DEF-04.
- M13.2 stays `IN PROGRESS`.

## 14. Documentation updates

As §5.

## 15. Remaining work

1. **The owner's decision:** how M13.2 proceeds given M13-DEF-04.
2. **M13-DEF-04's remediation milestone:** unassigned, and outside M13 (I-13). A fix needs a verified plugin-root
   mechanism for command and skill bodies, which no repository evidence establishes today.
3. **G-3:** OPEN, only on authorised execution.

## 16. Git commit reference

N/A. No commit and no push.
