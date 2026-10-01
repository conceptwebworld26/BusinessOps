# ADR-0046 — Under WSL, automatic interpreter resolution excludes Windows executables; the explicit override does not

**Date:** 2026-09-23
**Status:** Accepted — 2026-09-23, by the project owner, who selected this direction in the M13-DEF-12 remediation
prompt and authorised its implementation in the same decision.

- **What acceptance approves.** One rule inside the runtime resolver's candidate search, and its tests and governance.
  Nothing else. No analytical behaviour, KPI, forecast, anomaly, research, synthesis, report, connector or business rule
  is in scope, and none was changed.
- **Implemented 2026-09-23**, in the same task: 16 lines in `lib/biq_run.sh`, 15 new tests, three mutations each caught,
  and the full regression re-run.

**Deciders:** Project owner (direction selected and implementation authorised, 2026-09-23), raised by the M13.2 final
pre-flight.
**Supersedes:** none.
**Amends:** [ADR-0045](ADR-0045-businessiq-owned-portable-runtime-resolution.md), **in part**: its *Interpreter
discovery* rule 3 only — the clause that tries the Windows suffixes `.exe`, `.com`, `.bat`, `.cmd` on every host. Under
WSL those suffixes are no longer tried during **automatic** resolution. ADR-0045's `BIQ_PYTHON` override, its
`python`-then-`python3` order, its absolute-`PATH`-element rule, its `BIQ_RUNTIME_OK` probe, its `-I` handoff, its exit
statuses and everything else remain in force. **ADR-0045's text and status line are not edited**, as the repository did
for ADR-0040, ADR-0041, ADR-0043 and ADR-0045 itself.
**Relates to:** ADR-0042 (the launcher the resolver hands off to), ADR-0045 (the resolver this amends), M13-DEF-08 (the
defect ADR-0045 closed), M13-DEF-11 (whose remediation exposed this), M13-DEF-12 (the defect this closes).

## Context

### What ADR-0045 decided, and the one case it did not foresee

ADR-0045 made `lib/biq_run.sh` the single place an interpreter is chosen, and had it try, per `PATH` directory, the bare
name first and then the Windows suffixes — so that Git Bash on Windows, where `PATH` holds Windows directories and
interpreters carry `.exe`, would resolve. On Unix the bare name always matches first, so the suffixes were expected to
cost nothing.

**WSL is the case where that reasoning fails.** WSL puts the host's Windows directories on `PATH` through interop, so a
Linux shell sees `/mnt/c/Python313/python.exe` alongside `/usr/bin/python3` — and if no bare `python` exists anywhere,
which is the Debian and Ubuntu default, the suffix search reaches the Windows interpreter first.

### What the final pre-flight observed, on 2026-09-23

Established on this host with no evaluation:

| Check | Result |
|---|---|
| `command -v python` | absent |
| `command -v python3` | `/usr/bin/python3` |
| `command -v python.exe` | `/mnt/c/Python313/python.exe` |
| `/mnt/c` entries on `PATH` | **25**, via WSL interop |
| `sh lib/biq_run.sh --where` | **exit 2**: `python.exe: can't open file 'D:\mnt\d\…\biq_run.py'` |

An `sh -x` trace showed the loop reaching `/mnt/c/Python313/` and selecting `python.exe`. That interpreter **passes** the
`BIQ_RUNTIME_OK` probe, because it genuinely is Python 3.13, and then cannot open the engine: from it,
`os.path.isfile('/mnt/d/…/lib/python/biq_run.py')` is `False`, because a Windows process cannot address a Linux path and
mangles it to `D:\mnt\d\…`. Recorded as **M13-DEF-12**.

**Why no earlier verification caught it.** Every prior check of ADR-0045 — 26 static assertions, 40 executed scenarios
and three `--where` pre-flights — ran inside a sandboxed session that stripped the `/mnt/c` entries from `PATH`, so the
only candidate the resolver could ever see was `/usr/bin/python3`. Disabling that sandbox to remediate M13-DEF-11
revealed the host's real `PATH`.

### Why the version probe cannot decide this

The probe asks "are you Python 3.9 or newer?" and `/mnt/c/Python313/python.exe` answers truthfully yes. Version is the
wrong question: the interpreter is valid, and merely inhabits a different filesystem namespace from the engine it is
asked to run. No strengthening of the version check reaches this.

### Why `BIQ_PYTHON` is not a sufficient answer

It works, and it stays. But requiring it would mean BusinessIQ does not run on a mainstream platform until the user
understands a WSL/Windows interoperability detail and configures round it. ADR-0045's whole purpose was that a user
should not have to know what their Python is called; the same reasoning applies to which kernel their Python belongs to.

## Decision

**Under WSL, the automatic candidate search does not try the Windows executable suffixes.** Everything else is unchanged.

| Path | Behaviour |
|---|---|
| **WSL, automatic** | Bare names only: `python`, then `python3`. `.exe`, `.com`, `.bat`, `.cmd` are **not** tried |
| **WSL, `BIQ_PYTHON`** | **Unchanged.** An explicit absolute path may name a Windows interpreter; the exclusion governs automatic selection, not a deliberate instruction |
| **Native Windows** | **Unchanged.** Suffixes remain eligible |
| **Other Linux, and every other host** | **Unchanged.** Suffixes remain eligible; the bare name matches first anyway |

The rule is about the **suffix**, not the directory: a bare `python3` found under `/mnt/c` is still eligible, because
nothing about its location makes it a Windows binary.

### How WSL is detected

The kernel release string is read from `/proc/sys/kernel/osrelease` with the shell's `read` built-in, and matched for
`*icrosoft*` or `*WSL*` — which covers WSL 1 (`…-Microsoft`) and WSL 2 (`…-microsoft-standard-WSL2`).

Three properties make this the right check:

- **No external command.** `read`, `[`, `case` are built-ins, so the resolver keeps ADR-0045's property of depending on
  nothing outside the shell — which is a security property, not tidiness: a resolver that needed `uname` would
  misbehave under an unusable `PATH`, and that is how the launcher path once became working-directory relative.
- **Not environment-steerable.** `WSL_DISTRO_NAME` and `WSL_INTEROP` were rejected as the signal: an environment
  variable can be set by anything, and this decision selects which interpreter runs the engine.
- **Fails safe.** If the file cannot be read, the answer is "not WSL". A native Windows shell has no procfs, so that
  default is also the correct one for the platform it describes, and no host loses behaviour it had.

## Consequences

**Good.** BusinessIQ runs on WSL with Windows Python on `PATH` — a common configuration, and this host's default — with
no user action. The failure mode is structurally impossible for automatic selection rather than merely unlikely.

**Costs, stated.** One platform test inside the resolver, and one more thing a reader must know. Two ADR-0045 tests that
asserted Windows suffix lookup against the shipped file cannot run on a WSL kernel; they are skipped there with a pointer,
and the property they covered is asserted in `integration.test_m13_def12_wsl_interpreter` against a copy whose only edit
redirects the procfs read.

**Unchanged.** ADR-0042's launcher and import boundary; ADR-0045's `BIQ_PYTHON` override, name order, absolute-element
rule, probe token, `-I` handoff, exit 78, dependency-free implementation, and refusal to mutate `PATH`, install anything
or touch the network.

**Verified live, not only in tests.** On this host the automatic resolver now selects `/usr/bin/python3` and enters the
engine, from the repository and from an external working directory, with the Windows interpreter still on `PATH` and
still passing the probe.

## Revisit when

WSL exposes Linux-addressable Windows interpreters, or a supported host appears on which the kernel release string is not
a reliable WSL signal, or `BIQ_PYTHON` stops being sufficient for the deliberate cross-platform case.
