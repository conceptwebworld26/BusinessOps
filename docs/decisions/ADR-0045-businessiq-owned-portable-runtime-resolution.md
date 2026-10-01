# ADR-0045 — A BusinessIQ-owned runtime resolver chooses the Python interpreter, so no command names one

**Date:** 2026-09-22
**Status:** Accepted — 2026-09-22, by the project owner, who selected this direction (Option C,
"BusinessIQ-owned portable interpreter resolution") in the M13-DEF-08 remediation prompt and
authorised its implementation in the same decision.

- **What acceptance approves.** The runtime-invocation boundary and its tests and governance, and
  nothing else. No analytical behaviour, KPI, forecast, anomaly, research, synthesis, report,
  connector or business rule is in scope, and none was changed.
- **Implemented 2026-09-22**, in the same task: `lib/biq_run.sh`, 26 shipped files migrated
  (10 commands, 16 skills, 34 blocks), 66 new tests, and the full regression re-run.

**Deciders:** Project owner (direction selected and implementation authorised, 2026-09-22), raised
by the M13.2 evaluation pilot of 2026-09-22.
**Supersedes:** none.
**Amends:** [ADR-0042](ADR-0042-plugin-root-anchored-isolated-engine-entry.md), **in part**: the
*written form of the invocation* only — the line a command or skill body carries, and the
`--allow-tools` pattern that line implies. ADR-0042's launcher, its import boundary, its isolation
requirement, its `${CLAUDE_PLUGIN_ROOT}` location mechanism, its working-directory semantics and
its failure behaviour are unchanged and remain in force. ADR-0042's text and status line are not
edited, as the repository did for ADR-0040, ADR-0041 and ADR-0043.
**Relates to:** ADR-0042 (the launcher this hands off to), ADR-0002 (figures come from code),
ADR-0007 (two-layer testing), ADR-0039 §F.5 (the eval tool grant), M13-DEF-04 (the defect ADR-0042
closed), M13-DEF-08 (the defect this closes).

## Context

### What ADR-0042 fixed, and the one thing it left fixed in place

ADR-0042 replaced a working-directory-relative engine entry with one launcher located by the
platform's `${CLAUDE_PLUGIN_ROOT}` substitution. Its *Requirements* 4 asks that the entry work
"for a source checkout (`--plugin-dir`) and for a marketplace-installed copy, on Windows and
Unix-like systems, **with no hard-coded path**". The chosen form was:

```bash
python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py" -c "<code>"
```

The *path* is not hard-coded. The **interpreter name** is. That distinction is the whole of this
ADR.

### What the 2026-09-22 evaluation pilot observed

The M13.2 Stage-2 pilot executed on Ubuntu under WSL2. The agent took 5 turns and never entered
the engine. On that machine, established without running any evaluation:

| Check | Result |
|---|---|
| `command -v python` | prints nothing |
| `command -v python3` | `/usr/bin/python3` |
| `python3 -V` | `Python 3.14.4` |
| `dpkg-query -l python-is-python3` | no package |
| `grep -rl python3 commands/` | 0 files |

Debian and Ubuntu ship Python 3 as `python3` only; PEP 394 does not require a `python`. So on a
mainstream, supported, entirely ordinary host, **no BusinessIQ command could reach its engine** —
all 10 engine commands and all 16 engine skills, and the `python tests/run_tests.py` invocation
`README.md` documents. This was recorded as **M13-DEF-08**, a `product` defect, because it reaches
a real user of the plugin and not only the evaluator.

### Why the obvious repairs were wrong

- **Change the eval grant to `Bash(python3:*)`.** Repairs the evaluator and leaves every user on
  such a host broken. The grant was never wrong: it named exactly what the commands asked for.
- **Install `python-is-python3`.** Changes the machine to suit the software, once per machine,
  forever, and says nothing about the next host.
- **A shim named `python` on `PATH`, or a `PATH` edit in the eval case.** Makes the evaluation
  green while the product stays broken — repairing the messenger into silence. It also breaks
  ADR-0039 §F.6 (a scaffold may only copy inputs) and the eval validator's no-absolute-path rule.
- **`python3` in the 26 bodies instead.** Trades one hard-coded name for another. Windows commonly
  has `python` and no `python3`, so this moves the defect rather than removing it.
- **A fallback chain inside each body.** Puts interpreter detection in 26 places, against
  ADR-0042's *Requirements* 5 (centralised: "each command or skill carries no path logic of its
  own").

### The constraint that decides the shape

**Choosing the interpreter is what has to happen before Python runs, so it cannot happen in
Python.** `lib/python/biq_run.py` cannot resolve its own interpreter; something outside it must.
The command bodies are already POSIX-shell blocks — that is how the model runs them — so the shell
is the one layer already guaranteed to be present. Resolution belongs there, once.

This is not a new dependency. It removes one: the old form required a shell **and** an executable
called `python`; the new form requires only the shell that was already required.

## Decision

**One BusinessIQ-owned resolver, `lib/biq_run.sh`, is the only place an interpreter is chosen.**
Every command and skill reaches the engine as:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/lib/biq_run.sh" -c "<code>"
```

and the resolver hands off to ADR-0042's launcher unchanged:

```sh
exec <interpreter> -I "<plugin root>/lib/python/biq_run.py" -c "<code>"
```

### Interpreter discovery

1. **`BIQ_PYTHON`**, if set and non-empty, is the *only* candidate. It must be an absolute path,
   it is validated like any other candidate, its use is announced on stderr, and it **never falls
   back** to `PATH`. An override that could be silent, or that quietly failed over, would be a way
   to redirect execution rather than a way to choose.
2. Otherwise **`python`, then `python3`**, searched over `PATH`. `python` is first so that
   ADR-0042's contract continues to hold wherever it already held. A `python` that is Python 2
   fails the version check and the search continues, so an old host does not stop at it.
3. On each `PATH` directory the **bare name is tried first**, then `.exe`, `.com`, `.bat`, `.cmd`,
   so Windows executable lookup works under Git Bash and Unix pays nothing for it.
4. `py`, the Windows launcher, is deliberately **not** a candidate: it takes a version-selector
   argument and so would need a different invocation shape. `BIQ_PYTHON` covers it.

**`PATH` is scanned by the resolver itself, not by `command -v`, and only absolute elements are
considered.** An empty, `.` or otherwise relative element is skipped. This is the guard that stops
a file called `python` in the working directory from becoming the interpreter when `PATH` contains
`.` — which `command -v` would happily return.

### The version contract, and how a candidate is checked

A candidate must be a regular executable file, and must then print an exact token when asked, in
isolated mode, whether it satisfies **Python 3.9+** (`CLAUDE.md` §4):

```sh
"$1" -I -c '…sys.stdout.write("BIQ_RUNTIME_OK" if sys.version_info[:2] >= (3, 9) else "unsupported")'
```

**A token, not an exit status.** Something runnable that exits 0 for anything it is given —
broken, or hostile — passes a status-only check and is then handed the engine. Requiring the token
means the candidate actually evaluated the expression, so it is a Python that meets the contract
and not merely a file that runs. The probe uses `-I`, so no `PYTHON*` variable, user site directory
or working directory can influence the answer.

A selected interpreter is therefore invoked twice: once to probe, once by `exec`. That is the
contract, and it is asserted.

### What it must not do

No network access, no download, no package installation, no `PATH` export, no shell-profile
change, no `cd` outside the subshell that locates the launcher, no file written other than stderr,
and no interpreter of its own. It selects an interpreter that already exists, or it fails.

### Failure behaviour

Exit status **78** (`EX_CONFIG`) means "no usable interpreter". ADR-0042's launcher keeps **2** for
its own failures, so the two domains stay distinguishable in a transcript. The message names the
version required, the names looked for, and `BIQ_PYTHON` as the way out. It **never prints `PATH`,
`HOME` or any other environment value**: a configuration error must not become a disclosure.

### It needs no external command

The resolver's directory comes from `${0%/*}` and shell built-ins `cd`/`pwd`, not from `dirname`.
This is a security property, not tidiness. With an external `dirname` and an unusable `PATH`, the
command substitution comes back empty and the launcher path silently becomes
**working-directory-relative** — reintroducing exactly the class of defect M13-DEF-04 closed. The
resolver uses no external command at all, and a test asserts that.

### The eval tool grant follows the boundary

The first token of the invocation is now `sh`, so ADR-0039 §F.5's concrete grant changes. The
symbol `engine-python` in the case files is unchanged; what it maps to is not. **This ADR does not
choose the new grant** — see *Follow-up required*.

## Consequences

**Good.** BusinessIQ runs on a host that offers Python 3 under either name, with no user action
and no knowledge of which name their OS uses. The interpreter decision exists in exactly one file.
The plugin requires strictly less of a host than before.

**Costs, stated.** One extra process per engine call (the probe, a few tens of milliseconds). One
more file in the entry path. The eval grant must be re-agreed. A host with no Python at all still
fails — correctly, and now with a message that says what to install.

**Unchanged.** Everything ADR-0042 established: the launcher, the import boundary, isolated mode,
`${CLAUDE_PLUGIN_ROOT}` location, working-directory semantics, argument forwarding, exit status,
and the refusal to fall back. All 21 of its verification tests pass unmodified in substance.

## Follow-up required

1. **The owner re-agrees the eval `--allow-tools` grant.** `Bash(python:*)` and `Bash(python *)`
   cannot match the new first token. Two options, and the narrow one is recommended:
   - **Narrow (recommended):** a grant scoped to the resolver itself, e.g.
     `Bash(sh <plugin path>/lib/biq_run.sh:*)`. It authorises this boundary and nothing else. It
     names an absolute path, so it is written on the command line by the operator, never in a case
     file.
   - **Broad:** `Bash(sh:*)`, which authorises **any** `sh` invocation and is materially wider
     than the grant it replaces. Recorded as available and not recommended.
2. **`README.md` and `CLAUDE.md` still document `python tests/run_tests.py`.** The test runner is
   developer-facing and outside this ADR's boundary, but on this host that line does not work. It
   is left to the owner as a separate documentation decision.
3. **Runtime verification on Windows and macOS.** Windows executable lookup is covered by
   deterministic simulated tests only. No Windows or macOS execution has been performed, and none
   is claimed. ADR-0042's "Unix-like runtime verification" item is now satisfied on Linux/WSL2 by
   the M13-DEF-08 suite.
