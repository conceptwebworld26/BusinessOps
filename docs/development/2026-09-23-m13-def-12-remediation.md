# 2026-09-23 — M13-DEF-12: under WSL, the automatic resolver stops choosing Windows Python

**Milestone:** M13-DEF-12 remediation (outside M13's scope, ADR-0039 I-13 / §G.2), serving M13.2
**Status on completion:** **M13-DEF-12 `fixed_product`** under accepted **ADR-0046**; M13.2 `IN PROGRESS`;
M13-DEF-05 `open`, ready for owner closure; M13-DEF-06, 07, 09, 10, 11 `fixed_infrastructure`; M13-DEF-08
`fixed_product`; ADR-0044 stage 3 complete and live-validated; §E.1 outcome (a); R-01 ready for owner closure
**Supersedes:** None. It follows `2026-09-23-m13-2-final-preflight.md`, which found the defect.

## 1. Prompt / task performed

The owner's M13-DEF-12 remediation prompt, with the decision already made: on WSL, Windows executable Python candidates
must not be selected by the automatic resolver. Non-paid — no `claude plugin eval`, no case, no credits, no MCP, no web
retrieval, no authentication, no bypass, no broad grants, no package installation, no eval-semantics, fixture or grader
change, no commit, push or staging. ADR-0045 is immutable and was not to be edited.

**No evaluation was run.** `claude plugin eval` was not invoked and no credit was spent.

## 2. Root cause

WSL puts the host's Windows directories on `PATH` through interop. With no bare `python` anywhere — the Debian and Ubuntu
default — ADR-0045's per-directory suffix search reached `/mnt/c/Python313/python.exe` before `/usr/bin/python3`. That
interpreter **passes** the `BIQ_RUNTIME_OK` probe, because it genuinely is Python 3.13, and then cannot open the engine: a
Windows process cannot address a Linux path and reads `/mnt/d/…` as `D:\mnt\d\…`. `sh lib/biq_run.sh --where` exited 2.

**The probe cannot decide this.** It asks "are you Python 3.9 or newer?", and the answer is truthfully yes. Version is the
wrong question: the interpreter is valid and simply inhabits a different filesystem namespace from the engine it is asked
to run.

**Why it was invisible for a day.** Every prior verification of ADR-0045 — 26 static assertions, 40 executed scenarios,
three `--where` pre-flights — ran inside a sandboxed session that stripped the 25 `/mnt/c` entries from `PATH`, so the only
candidate the resolver could ever see was `/usr/bin/python3`. Disabling that sandbox to remediate M13-DEF-11 revealed the
host's real `PATH`.

## 3. Implementation

**11 effective lines in `lib/biq_run.sh`**, plus one header comment. Nothing else in production was touched.

```sh
biq_is_wsl=no
if [ -r /proc/sys/kernel/osrelease ]; then
    biq_osrelease=''
    read -r biq_osrelease < /proc/sys/kernel/osrelease || biq_osrelease=''
    case $biq_osrelease in
        *icrosoft*|*WSL*) biq_is_wsl=yes ;;
    esac
fi
if [ "$biq_is_wsl" = yes ]; then
    biq_suffixes='-'
fi
```

| Path | Behaviour |
|---|---|
| WSL, automatic | bare `python`, then `python3`. The Windows suffixes are **not** tried |
| WSL, `BIQ_PYTHON` | **unchanged** — an explicit absolute path may still name a Windows interpreter |
| Native Windows | **unchanged** — suffixes eligible |
| Other Linux | **unchanged** — suffixes eligible, bare name matches first anyway |

The rule is about the **suffix**, not the directory: a bare `python3` under `/mnt/c` stays eligible, because nothing about
where a file sits makes it a Windows binary.

**Detection, and why it is this and not something else.** The kernel release string is read from
`/proc/sys/kernel/osrelease` with the `read` built-in and matched for `*icrosoft*` or `*WSL*`, which covers WSL 1
(`…-Microsoft`) and WSL 2 (`…-microsoft-standard-WSL2`).

- **No external command.** `read`, `[` and `case` are built-ins, so the resolver keeps ADR-0045's dependency-free
  property. That is a security property, not tidiness: a resolver needing `uname` misbehaves under an unusable `PATH`, and
  that is precisely how the launcher path once became working-directory relative during the M13-DEF-08 work.
- **Not environment-steerable.** `WSL_DISTRO_NAME` and `WSL_INTEROP` were rejected as the signal. An environment variable
  can be set by anything, and this decision chooses which interpreter runs the engine.
- **Fails safe.** An unreadable file means "not WSL". A native Windows shell has no procfs, so that default is also the
  correct answer for the platform it describes, and no host loses behaviour it had.

Everything ADR-0045 established is untouched: `BIQ_PYTHON` semantics, the `python`-then-`python3` order, the
absolute-`PATH`-element rule, the `BIQ_RUNTIME_OK` probe, the `-I` handoff, exit 78, and the refusals to mutate `PATH`,
install anything or touch the network.

## 4. ADR

**ADR-0046** created and accepted, amending **ADR-0045 in part** — its *Interpreter discovery* rule 3 only. **ADR-0045 was
not edited**, per the repository's immutable-ADR convention and the precedent of ADR-0040, ADR-0041, ADR-0043 and
ADR-0045 itself. The number was taken from the repository (0045 was the highest). `docs/decisions/README.md` carries its
row and records the amendment.

## 5. Tests

`tests/integration/test_m13_def12_wsl_interpreter.py`, **15 tests**. The regression reproduces the exact failure mode
rather than a weakened version: a **working** Windows-suffixed stub is placed **ahead** of a native `python3` on `PATH`,
for each of the four suffixes, and the resolver must still select the native one. Because the stubs are functional, a
resolver that lost the exclusion would *succeed* while selecting the wrong interpreter — so the assertion is on **which**
interpreter ran, recorded by each stub logging its own name.

| Scenario | Test |
|---|---|
| WSL + `python3` available → native selected | `test_the_exact_regression_windows_python_first_native_still_chosen` |
| WSL + `.exe`/`.com`/`.bat`/`.cmd` first → native selected | `test_every_windows_suffix_is_skipped_in_favour_of_the_native_name` |
| WSL + only Windows candidates → refused, none executed | `test_with_only_windows_candidates_it_refuses_rather_than_choose_one` |
| WSL + bare name in a Windows directory → still eligible | `test_a_bare_native_name_in_a_windows_directory_is_still_eligible` |
| `BIQ_PYTHON` naming a `.exe` → still honoured | `test_the_explicit_override_may_still_name_a_windows_suffixed_interpreter` |
| Invalid `BIQ_PYTHON` → fails, no fallback | `test_an_invalid_override_still_fails_without_falling_back` |
| Relative and empty `PATH` elements → still rejected | `test_relative_and_empty_path_elements_are_still_rejected` |
| `-I` and `BIQ_RUNTIME_OK` → intact | `test_isolated_mode_and_the_probe_token_are_untouched` |
| **Native Linux** → suffixes still eligible | `test_native_linux_keeps_the_windows_suffixes_eligible` |
| **Native Windows** (no procfs) → suffixes still eligible | `test_native_windows_with_no_procfs_keeps_them_eligible` |
| A WSL marker on the same copy → excludes | `test_a_wsl_marker_excludes_them_even_on_this_copy` |
| Unreadable marker → fails safe | `test_an_unreadable_marker_fails_safe_rather_than_erroring` |
| The exclusion is present and the default list intact | `TheExclusionIsLoadBearing` (3 tests) |

**How the non-WSL platforms are reached.** This host is a WSL kernel, so native Linux and native Windows cannot be
produced against the shipped file. Those cases run a copy whose **only** edit redirects the procfs path the detection
reads at a fixture; the copy is rebuilt from the shipped file on every run, so a change to the real logic is reflected
there too. Nothing about the selection logic is mocked, and the WSL cases run the shipped file unmodified.

**Mutation cover** — each caught:

| Mutation | Failing tests |
|---|---|
| Remove the WSL exclusion | **9** |
| Invert the detection (never WSL) | **9** |
| Default to WSL when procfs is unreadable | **3** |

The file was restored and confirmed byte-identical after each.

**Two existing ADR-0045 tests moved rather than being deleted.** `test_windows_style_lookup_finds_an_exe_suffix` and
`test_windows_style_lookup_covers_the_other_documented_suffixes` asserted Windows suffix lookup against the shipped file,
which a WSL kernel can no longer express. They are skipped on WSL with a pointer to the new module, which asserts the same
property against the redirected copy, and a third test was added in their place asserting the WSL inverse so that class
still asserts something on this host. **No test was weakened to obtain green.**

## 6. Live verification

With the Windows interpreter still on `PATH` and still passing the probe (`/mnt/c/Python313/python.exe` →
`BIQ_RUNTIME_OK`), so the exclusion is demonstrably the only thing keeping it out:

| Check | Result |
|---|---|
| `sh lib/biq_run.sh --where`, **no `BIQ_PYTHON`** | **exit 0**, `"isolated": true`, `"python": "3.14.4"`, engine and plugin root this repository |
| Interpreter automatically selected | **`/usr/bin/python3`** (`sh -x`: `biq_is_wsl=yes`, `biq_suffixes=-`, `biq_found=/usr/bin/python3`, `exec /usr/bin/python3 -I …`) |
| External working directory, real engine call | **exit 0** — `anomaly-detection` returned `Status: ok · 11 finding(s), 11 of them material` |
| `BIQ_PYTHON=/usr/bin/python3 sh lib/biq_run.sh --where` | **exit 0**, override announced on stderr as before |

## 7. Files created

| File | Purpose |
|---|---|
| `docs/decisions/ADR-0046-wsl-excludes-windows-interpreters-from-automatic-resolution.md` | The decision |
| `tests/integration/test_m13_def12_wsl_interpreter.py` | 15 tests |
| `docs/development/2026-09-23-m13-def-12-remediation.md` | This record |

## 8. Files modified

| File | Change |
|---|---|
| `lib/biq_run.sh` | The WSL detection and the suffix exclusion — **11 effective lines** — plus one header comment. No other logic changed |
| `tests/integration/test_m13_def08_runtime_resolution.py` | A `host_is_wsl()` predicate; the two Windows-lookup tests skipped on WSL with a pointer; one test added asserting the WSL inverse |
| `docs/decisions/README.md` | The ADR-0046 row and the amendment note |
| `docs/testing/defects.md` | M13-DEF-12 → `fixed_product` with the rule, the detection rationale, the verification and the ADR-0043 status basis |
| `docs/testing/eval-suite.md` | "What blocks the next run" and the interpreter pre-flight updated |
| `project_plan.md` | Header bullet; M13-DEF-12 known-issue row; M13.2 detail row |

No eval case, scaffold, fixture, grader, skill, command, agent, manifest, connector or MCP file was modified.

## 9. Security and scope

Preserved: `-I` on both handoffs; the exact `BIQ_RUNTIME_OK` probe; the absolute-`PATH`-element requirement; rejection of
relative and empty elements; executable validation; exit 78; no external command; no `PATH` mutation; no package
installation; no network; no download. No grant was broadened, no evaluator setting touched, no bypass used. No
user-specific or Windows-specific path was hardcoded — `/mnt/c/Python313` appears only in test fixtures and prose, never in
production code — and normal WSL operation does **not** require `BIQ_PYTHON`.

## 10. Remaining work

1. The authorised three-run evaluation, whose pre-flight must show `--where` at exit 0 — it now does.
2. The owner closes **R-01**, and **M13-DEF-05** if the 1-of-64 loader residual is acceptable.
3. The twelve `manual_observation` scenarios; staging for the remaining 37 `requires_business_file` cases.
4. Native Windows and macOS runtime verification, if the owner wants those claimed rather than simulated.

## 11. Git commit reference

**No commit, no push, no staging.** Nothing reset, cleaned, reverted or stashed; all pre-existing uncommitted M13.2 work
intact. Branch `main`, base `21ee21b21213ad80273650f056ef2f318023742c`.
