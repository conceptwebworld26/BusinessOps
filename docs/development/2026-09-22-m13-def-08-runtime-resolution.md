# 2026-09-22 — M13-DEF-08: a BusinessIQ-owned runtime resolver, so no command names an interpreter

**Milestone:** M13-DEF-08 remediation (outside M13's scope, ADR-0039 I-13 / §G.2), serving M13.2
**Status on completion:** **M13-DEF-08 `fixed_product`** (ADR-0043), under accepted **ADR-0045**;
M13.2 `IN PROGRESS`; M13-DEF-05 `open`; M13-DEF-06, M13-DEF-07, M13-DEF-09 `fixed_infrastructure`
**Supersedes:** None. It follows `2026-09-22-m13-2-eval-harness-remediation.md`, which recorded
M13-DEF-08 and the owner decision this task carries out.

## 1. Prompt / task performed

The owner's M13-DEF-08 remediation prompt. It records the selected architectural direction —
**Option C, a BusinessIQ-owned portable interpreter resolution** — and authorises its
implementation: one resolver that is the only place a Python executable is chosen, the shipped
bodies migrated to it, cross-platform tests, the M13-DEF-04 security contract preserved, an ADR,
and governance updates. Explicitly forbidden: `claude plugin eval`, any paid evaluation, network
access, package installation, a downloaded Python, a fake interpreter, a global `PATH` or
shell-profile change, an evaluator-only workaround, weakened sandboxing, and any change to
analytical behaviour. No commit, no push, no staging.

**No paid evaluation was run.** `claude plugin eval` was not invoked.

## 2. Objective

Make BusinessIQ reach its engine on a supported host without the host having to call Python
`python`, and without any command or skill knowing what Python is called.

## 3. Changes made

### 3.1 What the inspection established, including one correction to the brief

| Question | Answer |
|---|---|
| How do commands invoke Python? | `python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py" -c "…"`, in two forms: plain, and a `$(cat <<'PY'` heredoc |
| How many sites? | **10 engine commands and 16 engine skills, 34 blocks** — not the 14 the prompt states. `grep -rl 'python -I' commands/` matches 10; the looser count of 14 includes 4 files that only mention `lib/python/biq/...` paths in prose. ADR-0042 and `project_plan.md` both record "10 commands and 16 skills", so 26 files is the real scope |
| What does ADR-0042 guarantee? | Plugin-root-anchored location by `${CLAUDE_PLUGIN_ROOT}` substitution; isolated mode; engine directory first on `sys.path` and the working directory nowhere; `biq` verified to come from the plugin; no working-directory dependence; centralised path logic; fail loudly with exit 2 and no fallback |
| Which parts are security-sensitive? | The isolation check before any import, the `sys.path` rebuild, the `biq` origin check, the manifest check, and the refusal to fall back. All are inside `biq_run.py` and none of them depends on which interpreter runs it |
| What must stay unchanged? | Every one of those, plus the working directory, argument forwarding, exit status and stream behaviour |
| Can the launcher become the resolution boundary? | **No.** Choosing the interpreter is what must happen *before* Python runs, so a Python file cannot do it. The resolution boundary has to sit outside `biq_run.py` and hand off to it |

**A second finding, about why this escaped the tests.**
`integration.test_m13_def04_engine_entry` builds its subprocess as
`[sys.executable, "-I", <launcher>, "-c", code]`. It never executes the literal token `python`, so
all 21 of its tests passed on a host with no `python` at all. The suite proved the import boundary
thoroughly and the *invocation* not at all. That gap is why the defect reached a paid evaluation
run before anyone saw it, and it is the reason the new suite drives the real shell script.

### 3.2 The design, and why it is a shell script

The command bodies are already POSIX-shell blocks — that is how the model runs them — so the shell
is the one layer already guaranteed to be present. Putting resolution there adds no dependency; it
**removes** one. The old form needed a shell *and* an executable called `python`. The new form
needs only the shell that was already needed.

`lib/biq_run.sh`, POSIX only (checked with `sh -n` and `dash -n`), 4 header constants and three
short sections:

1. **Locate the launcher** from `${0%/*}` plus the built-ins `cd`/`pwd`, never from the
   environment. `biq_launcher="$biq_lib/python/biq_run.py"`, and a missing one is an error.
2. **Choose a candidate:** `BIQ_PYTHON` if set, else `python`, then `python3`, scanned over `PATH`.
3. **Hand off:** `exec "$candidate" -I "$biq_launcher" "$@"`.

`exec` replaces the shell, so the engine's exit status, stdout, stderr and working directory are
its own and nothing is wrapped or buffered.

### 3.3 Two decisions that are the substance of the security argument

**The `PATH` scan is hand-rolled, and only absolute elements count.** `command -v python` would
return `./python` when `PATH` contains `.` or an empty element, which is the realistic way a file
in the user's working directory becomes the interpreter. The resolver splits `PATH` itself and
skips any element that is not absolute (`/…`, or a drive-letter path for Git Bash). An absolute
element is trusted even when it happens to *be* the working directory, because a project-local
virtual environment is legitimate and must keep working — the rule is about relative elements, not
about a directory's identity, and both halves are asserted.

**A candidate must emit a token, not merely exit 0.** The probe is
`"$1" -I -c '…sys.stdout.write("BIQ_RUNTIME_OK" if sys.version_info[:2] >= (3, 9) else "unsupported")'`
and the output must equal the token. A status-only check accepts anything runnable that exits 0 —
including a stub that ignores its arguments — and then hands it the engine. Requiring the token
means the candidate actually evaluated the version expression, so it is a Python meeting the
contract and not just a file that runs. The probe uses `-I`, so no `PYTHON*` variable, user site
directory or working directory can change the answer.

The consequence is that a selected interpreter runs twice: once probed, once `exec`ed. That is the
contract, and `test_a_selected_interpreter_is_probed_before_it_is_used` pins it.

### 3.4 A bug found while testing, which is the whole argument for using no external command

The first draft located itself with `$(dirname -- "$0")`. Run with `PATH=/nonexistent`, `dirname`
could not be found, the substitution came back empty, and the launcher path became
`$PWD/python/biq_run.py` — **working-directory relative**, which is precisely the class of defect
M13-DEF-04 closed, reintroduced through the back door. A hostile `python/biq_run.py` in the user's
directory would have been the launcher.

It was replaced with parameter expansion and built-ins. The `sed` in the failure message went the
same way. **The resolver now needs no external command at all**, which is a security property
rather than tidiness, and both a static test (`test_it_needs_no_external_command`) and a
behavioural one (`test_an_unusable_path_still_finds_the_launcher`, which plants that hostile file)
hold it. Restoring `dirname` fails 3 static and 38 behavioural tests.

### 3.5 Migration

All **34** blocks in **26** files changed from

```bash
python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py" -c "
```

to

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh" -c "
```

and the heredoc form correspondingly. **Nothing else in any block changed**: every line of engine
code is byte-for-byte what it was. The 9 delegating commands were inspected and left alone — they
carry no engine block, and a test asserts they name neither `biq_run.py` nor `biq_run.sh`.

### 3.6 Governance

**ADR-0045**, accepted and implemented the same day. It **amends ADR-0042 in part** — the written
form of the invocation, and the `--allow-tools` pattern that form implies — and nothing else.
ADR-0042's launcher, import boundary, isolation requirement, `${CLAUDE_PLUGIN_ROOT}` mechanism,
working-directory semantics and failure behaviour are unchanged and in force. **ADR-0042's text and
status line were not edited**, following the precedent of ADR-0040, ADR-0041 and ADR-0043.

## 4. Files created

| File | Purpose |
|---|---|
| `lib/biq_run.sh` | The runtime resolver: the one place an interpreter is chosen |
| `tests/unit/test_m13_def08_runtime_resolver.py` | Static guard, 26 assertions |
| `tests/integration/test_m13_def08_runtime_resolution.py` | Behavioural suite, 40 executed scenarios |
| `docs/decisions/ADR-0045-businessiq-owned-portable-runtime-resolution.md` | The decision |
| `docs/development/2026-09-22-m13-def-08-runtime-resolution.md` | This record |

## 5. Files modified

| File | Change |
|---|---|
| 10 `commands/*.md`, 16 `skills/*/SKILL.md` | 34 blocks moved to the boundary line. No engine code changed |
| `lib/python/biq_run.py` | Docstring and `USAGE` describe the boundary and the resolver's exit 78. **No logic changed** |
| `tests/unit/test_m13_def04_static_guard.py` | Boundary line updated; the retired form now forbidden; new assertions that no shipped line names an interpreter and that the boundary path appears only on the boundary line |
| `tests/integration/test_m13_def04_engine_entry.py` | Parses the new opener and maps it to the launcher it hands off to. **Its 21 tests and their subject are unchanged** |
| `docs/decisions/README.md` | ADR-0045 row; the amended/refined line records 0042 amended in part by 0045 |
| `docs/testing/defects.md` | M13-DEF-08 → `fixed_product` with its ADR-0043 status basis and its stated limits |
| `docs/testing/eval-suite.md` | The `engine-python` pre-flight: what the grant maps to now, that the replacement is an owner decision, and the new interpreter check `sh lib/biq_run.sh --where` |
| `project_plan.md` | M13-DEF-08 resolved; the interpreter task `COMPLETED`; a new `BLOCKED` row for the grant decision; a header bullet |

## 6. Files deleted

None.

## 7. Features implemented

| Feature | Location | User-reachable? |
|---|---|---|
| Portable interpreter resolution | `lib/biq_run.sh` | **Yes** — every command and skill on any host offering Python 3.9+ as `python` or `python3` |
| Explicit interpreter override | `BIQ_PYTHON` | **Yes** — absolute path, validated, announced, never a fallback |
| Windows suffix lookup | `lib/biq_run.sh` | Yes on Windows shells; **simulated in tests only**, never executed on Windows |
| Actionable "no interpreter" failure | `lib/biq_run.sh`, exit 78 | Yes |

## 8. Tests performed

```
python3 tests/run_tests.py unit.test_m13_def08_runtime_resolver
python3 tests/run_tests.py integration.test_m13_def08_runtime_resolution
python3 tests/run_tests.py unit.test_m13_def04_static_guard
python3 tests/run_tests.py integration.test_m13_def04_engine_entry
python3 tests/run_tests.py unit.test_m13_eval_cases
python3 tests/run_tests.py unit.test_m13_eval_results
python3 tests/run_tests.py unit.test_m13_coverage_matrix
python3 tests/run_tests.py
claude plugin validate . --strict
sh -n lib/biq_run.sh ; dash -n lib/biq_run.sh
```

Plus a four-mutation check of the resolver, each mutation applied to a copy-backed file and then
restored, with the file confirmed byte-identical to the original afterwards.

`claude plugin eval` was **not** run. No model was invoked, no network reached, no MCP tool called,
no authentication performed, nothing published, nothing installed.

## 9. Test results

| Command | Result |
|---|---|
| `unit.test_m13_def08_runtime_resolver` | **Ran 26 — OK** (new) |
| `integration.test_m13_def08_runtime_resolution` | **Ran 40 — OK** (new) |
| `unit.test_m13_def04_static_guard` | **Ran 16 — OK** (was 14; 2 added) |
| `integration.test_m13_def04_engine_entry` | **Ran 21 — OK**, unchanged in substance |
| `sh -n` / `dash -n` on the resolver | clean under both shells |
| Full regression | recorded in §9 of the final task report |

**Mutation check** — each mutation caught:

| Mutation | Failing tests |
|---|---|
| Drop the absolute-`PATH`-element guard | **3** behavioural |
| Accept the probe on exit status alone | **4** behavioural |
| Drop `-I` from the handoff | **29** behavioural |
| Restore the external `dirname` | **3** static + **38** behavioural |

The third is the important one: without `-I` nearly the whole isolation contract collapses, which
is the right shape for a guard on ADR-0042's central property.

**Proof on the host that found the defect:** `sh lib/biq_run.sh --where` reports the plugin's
engine, `"plugin": "businessiq"`, `"isolated": true`, `"python": "3.14.4"` — on a machine with no
`python` at all.

## 10. Issues discovered

1. **The prompt's "14 commands" is 10 commands and 16 skills, 34 blocks.** Migrating only the
   commands would have left 16 skills unable to enter the engine. Recorded in §3.1.
2. **The M13-DEF-04 suite could not have caught this**, because it invokes `sys.executable` rather
   than the literal token the bodies name. The new suite drives the real script.
3. **An external `dirname` made the launcher path working-directory relative** under a broken
   `PATH`. Found by a test, fixed, and now guarded twice (§3.4).
4. **The eval `--allow-tools` grant is not settled.** The first token is now `sh`, so
   `Bash(python:*)` cannot match. **An owner decision**, recorded in ADR-0045 *Follow-up required*
   and in `project_plan.md` as `BLOCKED`. Not decided here.
5. **`README.md` and `CLAUDE.md` still document `python tests/run_tests.py`**, which does not work
   on this host. The runner is developer-facing and outside this boundary; left to the owner.
6. **Windows and macOS were not executed.** Windows lookup is covered by deterministic simulated
   tests only, and no claim beyond that is made.

## 11. Decisions made

[ADR-0045](../decisions/ADR-0045-businessiq-owned-portable-runtime-resolution.md) — accepted
2026-09-22, amending ADR-0042 in part. ADR-0042 was not edited.

## 12. Architecture changes

`architecture.md` was not modified. The engine-entry *form* changed and its layering, contracts,
extension points and approval rules did not; the entry is recorded in ADR-0042 and now ADR-0045,
which is where the repository keeps it.

## 13. Project-plan updates

- M13-DEF-08: `open` → **`fixed_product`**, resolved 2026-09-22, uncommitted.
- M13.2 task "Engine interpreter on the evaluation machine": `BLOCKED` → **`COMPLETED`**.
- New M13.2 task "Eval `--allow-tools` grant for the new boundary": **`BLOCKED` — owner decision**.
- M13.2 stays `IN PROGRESS`. **No case class changed and no evidence moved**: the pilot case is
  still `automated_fail`, because a class records what a run did, not what has since been fixed.

## 14. Documentation updates

`docs/decisions/ADR-0045-…`, `docs/decisions/README.md`, `docs/testing/defects.md`,
`docs/testing/eval-suite.md`, `project_plan.md`, and this record.

## 15. Remaining work

1. **The owner states the eval `--allow-tools` grant.** Nothing else blocks the next evaluation.
2. Then the M13.2 pilot at `--runs 3` with `--scaffold` and `--keep-temp`, which is also the first
   conforming §E.1 measurement and yields the trace ADR-0044 stage 3 needs.
3. Windows and macOS runtime verification, if the owner wants it claimed rather than simulated.
4. The `python tests/run_tests.py` documentation decision.
5. Extend eval input staging to the remaining 37 `requires_business_file` cases (M13-DEF-07).

## 16. Git commit reference

**No commit, no push, no staging.** Nothing reset, cleaned, reverted or stashed; all pre-existing
uncommitted M13.2 work intact. Branch `main`, base
`21ee21b21213ad80273650f056ef2f318023742c`.
