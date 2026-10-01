# 2026-09-23 — Final pre-flight: M13-DEF-11 closed, M13-DEF-12 found before any spend

**Milestone:** M13 — test hardening and evals (M13.2)
**Status on completion:** M13.2 `IN PROGRESS`; **M13-DEF-11 `fixed_infrastructure`** (environment prerequisite verified,
live evaluator start not observed); **M13-DEF-12 raised, product, `open`**; M13-DEF-05 `open`, ready for owner closure;
M13-DEF-06, 07, 09, 10 `fixed_infrastructure`; M13-DEF-08 `fixed_product`; ADR-0044 stage 3 complete and live-validated;
§E.1 outcome (a); R-01 ready for owner closure
**Supersedes:** None. It follows `2026-09-23-m13-def-11-environment-diagnosis.md`.

## 1. Prompt / task performed

The owner's final non-paid pre-flight, after manually setting the outer Claude Code session to `No Sandbox`. Verify the
environment is prepared for the next authorised evaluation. No `claude plugin eval`, no case, no credits, no LLM
evaluator, no web retrieval, no MCP, no authentication, no bypass, no broad grants, no production, resolver or
eval-semantics change, no installation, no commit, push or staging.

**No evaluation was run.** `claude plugin eval` was not invoked and no credit was spent.

## 2. Result

**NOT READY.** The environment condition this pre-flight was meant to confirm is genuinely fixed — and the same
pre-flight then failed at the next gate, on a defect the previous environment had been hiding.

## 3. M13-DEF-11: verified fixed

The operator set the outer session to `No Sandbox`. The exact operation whose failure defined the defect was retested:

| | Before | After |
|---|---|---|
| user namespace | `user:[4026532354]` (non-initial) | `user:[4026531837]` (initial) |
| uid_map | `1000 1000 1` | `0 0 4294967295` |
| Seccomp | mode 2, 1 filter | mode **0**, 0 filters |
| `AF_UNIX` `bind`+`listen` | **EPERM (errno 1)** | **OK** |

Done in a temporary directory, socket and directory removed afterwards, repository untouched. The evaluator's own
sandbox is unchanged — `enabled: true`, `failIfUnavailable: true`, `allowUnsandboxedCommands: false`, from the preserved
child configs of all three runs of the 2026-09-23 evaluation. No bypass was used.

**Two claims, one made.** **Verified:** the environment prerequisite. **Not verified:** that the evaluator's sandbox
*initialises* — that needs the next authorised run. `fixed_infrastructure` records the first, not the second.

## 4. M13-DEF-12: the defect the sandbox was hiding

`sh lib/biq_run.sh --where`, which had passed three times before, now fails:

```
python.exe: can't open file 'D:\mnt\d\Prakash\Claude\Plugins\BusinessIQ\BusinessIQ\lib\python\biq_run.py':
  [Errno 2] No such file or directory
exit=2
```

**The chain, each step observed:**

1. With the outer sandbox off, `PATH` carries **25** `/mnt/c` entries via WSL interop, including `/mnt/c/Python313/`.
2. `command -v python` → absent. `command -v python3` → `/usr/bin/python3`. `command -v python.exe` →
   `/mnt/c/Python313/python.exe`.
3. The resolver's candidate loop tries the bare name first, then `.exe`, `.com`, `.bat`, `.cmd` per `PATH` directory. An
   `sh -x` trace shows it reaching `/mnt/c/...` and selecting `python.exe` — because `python` is absent everywhere, and
   `/mnt/c/Python313/` precedes nothing that would supply it.
4. **The probe passes.** `/mnt/c/Python313/python.exe -I -c '…'` prints `BIQ_RUNTIME_OK`: it is genuinely Python 3.13.
5. The handoff fails. From that interpreter `os.path.isfile('/mnt/d/…/lib/python/biq_run.py')` is `False` — a Windows
   process cannot address a Linux path, and mangles it to `D:\mnt\d\…`.
6. `BIQ_PYTHON=/usr/bin/python3 sh lib/biq_run.sh --where` → exit 0, `"isolated": true`, `"python": "3.14.4"`. The
   resolver's documented escape hatch is unaffected.

**Why every prior verification missed it.** The outer sandbox stripped the `/mnt/c` `PATH` entries, so the only candidate
the resolver could ever see was `/usr/bin/python3`. ADR-0045's 26 static assertions, 40 executed scenarios and three
`--where` pre-flights all ran under that sandbox. Removing it to fix M13-DEF-11 revealed the host's real `PATH` and this
defect with it. **The resolver was never wrong about `python3`; it is wrong about `.exe`.**

**Why the probe cannot catch it.** It asks "are you Python 3.9+?", and the answer is truthfully yes. Version is the wrong
question: the interpreter is valid and simply inhabits a different filesystem namespace from the engine it is asked to
run. Catching it needs a check the probe does not make — for instance, that the candidate can see the launcher.

**Product, not evaluation.** It reaches any WSL2 user with Windows Python on `PATH`, which is a common configuration and
is this host's default. No eval case, grant, scaffold or mapping is involved.

**Not fixed here**, and this is a stop condition: `lib/biq_run.sh` is production code, ADR-0045 fixes the invocation
form, and this task forbade modifying the resolver. ADR-0039 I-13 and §G.2 reserve product defects to the owner.

## 5. The pre-flight gate did its job

The §F pre-flight requires `sh lib/biq_run.sh --where` to exit 0 before a run is authorised. It failed, and stopped the
evaluation **before any spend**. A run launched without it would have cost roughly $0.6 to discover the same thing from a
transcript. That gate was added on 2026-09-22 for exactly this class of failure.

## 6. Files created

| File | Purpose |
|---|---|
| `docs/development/2026-09-23-m13-2-final-preflight.md` | This record |

## 7. Files modified

| File | Change |
|---|---|
| `docs/testing/defects.md` | M13-DEF-11 → `fixed_infrastructure` with the before/after and the two-claim distinction; **M13-DEF-12** added (product, open); register row and state header |
| `docs/testing/eval-suite.md` | "What blocks the next run" → M13-DEF-12; pre-flight 1a marked satisfied; the interpreter pre-flight records the failure and that the gate caught it |
| `project_plan.md` | Header bullet; **M13-DEF-12** known-issue row; M13.2 detail row |

**No production, runtime, resolver, engine, command, skill, agent, connector, MCP, manifest, test-logic or eval-case file
was modified.**

## 8. A note on the working-tree count

`git status --short` reports **135** entries, where the sandboxed session reported 146. The difference is **11 phantom
paths** the sandbox's filesystem view projected into the repository — `.bash_profile`, `.bashrc`, `.gitconfig`,
`.gitmodules`, `.idea`, `.profile`, `.ripgreprc`, `.vscode`, `.zprofile`, `.zshrc` and `.claude` — ten of which do not
exist here at all. **Nothing was lost:** every file created across this milestone's work was verified present, HEAD is
unchanged, nothing is staged, and `git stash list` is empty. 135 is the true unsandboxed count.

## 9. Tests

No source change, so the full suite was not run. The modules that read the documents this task edited:

| Module | Result |
|---|---|
| `unit.test_m13_coverage_matrix` | **Ran 33 — OK (skipped=1)** |
| `unit.test_m13_eval_cases` | **Ran 102 — OK** |
| `unit.test_m13_def10_eval_grant` | **Ran 30 — OK** |

One of these caught a real error while writing this up: the defect register's parser reads any `` | `word` | … | `` line
as a field, so the before/after comparison table inside M13-DEF-11 was being absorbed as bogus fields named `uid_map` and
`Seccomp`. The table was rewritten; the parser was not weakened.

**No test asserts the environment itself**, and none was manufactured.

## 10. Remaining work

1. **The owner decides M13-DEF-12**: amend the resolver (its own prompt and an ADR amendment — for example, rejecting a
   candidate that cannot see the launcher, or not applying Windows suffixes when the host is WSL), or accept
   `BIQ_PYTHON` as the documented answer on such hosts.
2. Then the authorised three-run evaluation, whose pre-flight must show `--where` at exit 0.
3. The owner closes **R-01**, and **M13-DEF-05** if the 1-of-64 loader residual is acceptable.
4. The twelve `manual_observation` scenarios; staging for the remaining 37 `requires_business_file` cases.

## 11. Git commit reference

**No commit, no push, no staging.** Nothing reset, cleaned, reverted or stashed; all pre-existing uncommitted M13.2 work
intact. Branch `main`, base `21ee21b21213ad80273650f056ef2f318023742c`.
