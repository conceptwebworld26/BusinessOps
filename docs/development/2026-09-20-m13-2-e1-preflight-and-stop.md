# 2026-09-20 — M13.2 §E.1 first execution: G-3 pre-flight done, execution stopped at the §F.1 ceiling

**Milestone:** 13 — Test Hardening & Evals, part M13.2 (behavioural evals), under ADR-0039 as amended by ADR-0040,
ADR-0041 and ADR-0043.
**Status on completion:** **No eval was executed. Zero attempts.** §E.1's recorded outcome stays **(c)**, with the
reason "no owner authorisation / ceiling" — now specifically the missing ceiling. M13.2 stays IN PROGRESS. G-3 stays
OPEN, partially informed by the pre-flight below. Nothing committed, nothing pushed, nothing staged.
**Supersedes:** nothing. Every earlier record stands.

## 1. What this task asked, and what happened

The owner's "M13.2 First Controlled Evaluation Execution" prompt authorised **one** case to run against the owner's
existing Claude allowance, and prohibited any separate paid charge, any second attempt and any workaround.

The G-3 pre-flight was performed, as ADR-0041 §12 and `docs/testing/eval-suite.md` require immediately before any
run. It found the harness present and usable. **Execution was then stopped, before any case ran**, because ADR-0039
§F.1's second precondition is unmet.

## 2. The blocker: §F.1's cost ceiling

ADR-0039 §F.1, verbatim:

> **Explicitly authorised by the owner, per execution.** It runs only when the project owner explicitly authorises
> that execution, in the implementation prompt or in writing for that run, **and** states a `--max-cost-usd` ceiling.
> The ceiling is passed on the command line. Without both, the suite is authored and statically validated only, and
> every case is `not_executed` (§E.1 c).

- **Authorisation:** given, for the owner's existing allowance.
- **Ceiling:** **not stated.** The prompt says "Do not invent a cost number", and ADR-0039 forbids inventing one
  anyway: the ceiling is the owner's, and it is passed on the command line.

§E.1 (c) covers this exact case: "**(c) Execution is not authorised,** or no ceiling is stated."

This is a **contract precondition**, not a platform failure, so it is not `execution_unavailable`, which §E.1 (b)
reserves for an attempted execution the platform refused. No case was attempted, so nothing is recorded as attempted.

**What unblocks it:** one number from the owner, for example "authorised, `--max-cost-usd 5`". The pre-flight below
must then be re-read immediately before the run, as G-3 requires.

## 3. G-3 pre-flight (read-only, 2026-09-20, Claude Code 2.1.278)

`claude plugin eval --help` was read. Nothing was executed. Facts, as the help states them:

| Item | Finding |
|---|---|
| Harness | Present. "Run eval cases (`<eval dir>/**/case.yaml` or `prompt.md + graders/*.md`…) against a plugin and report scored results" |
| Case discovery | `<eval dir>/**/case.yaml`; the eval dir is `evals/` unless `--eval-dir` or the manifest says otherwise. BusinessIQ's manifest already declares `experimental.evals` = `evals` |
| Selecting one case | `--case <glob>` filters cases by name. `--tag` also exists |
| Cost | "Each run is a full claude child on your own credential", so it draws on the **owner's existing Claude allowance**. No separate billing mechanism appears in the surface |
| `--max-cost-usd` | Exists, and is **optional at the tool level**: "Optional hard cost ceiling; abort and report partial results if hit (exit 2)". ADR-0039 §F.1 makes it **mandatory for BusinessIQ**, which is the binding rule here |
| `--runs` | "Override per-case runs (default: `case.runs ?? 3`)". §F.7 fixes `--runs 3` |
| `--threshold` | "Exit 1 if any case score is below this threshold (default: 1.0)". §F.7 fixes `--threshold 1.0` |
| `--no-publish` | "Keep the HTML report local only; skip publishing it to claude.ai". §F.2 requires it, because publishing is an export (ADR-0010) |
| `--publish-report` | Present, and "already the default when your account supports it" — which is why §F.2's `--no-publish` is mandatory |
| `--mocks` | `record` is the default: "a plugin server with no mock is NOT started". §F.3 requires `record`, with no `evals/mocks/` |
| `--allow-real-servers` | Present, and **prohibited** by §F.3 |
| `--allow-tools` | "Operator grant for gated tools (Bash, Write, Edit, WebFetch, mcp__*). Supports `Tool(pattern:*)` syntax". §F.5 limits the grant to the engine's `python` invocations; §F.4 forbids web and `mcp__` grants |
| `--scaffold` | Off by default, and `--no-scaffold` exists. BusinessIQ has no scaffold script |
| `--ablation` | `none | with-without`; under `with-without`, "graders marked with-only, incl. `tool_used: Skill`, are a plugin-fired indicator rather than part of the score". §F.8 sets `with-without` for `routing` and `none` elsewhere |
| `--judge-model` | Default `haiku`, matching §E.4's "platform default unless the implementation prompt names one" |
| `--trust-plugin` | Asserts trust and skips the first-run prompt. §I permits it for this repository's own plugin, on the owner's authorisation |
| Results | `evals/results/…`, which `.gitignore` already excludes (§F.9) |

**Still unverified, so G-3 stays OPEN:**

- whether the harness parses BusinessIQ's repository-local case schema `biq-eval-case/1`, and how it maps its check
  vocabulary. The help documents `case.yaml` and `prompt.md + graders/*.md` but not the schema's fields;
- what the `engine-python` grant maps to concretely under `--allow-tools`;
- how a named input reaches the case sandbox;
- the sandbox's behaviour.

Only a real run can settle those, and a run needs the ceiling.

## 4. The case that would have run

Selected by the repository's deterministic ordering, `sorted(glob("evals/*/*/case.yaml"))`, which the §E.5 validator
uses:

| Item | Value |
|---|---|
| Path | `evals/approval/a01-read-only-anomaly-detection/case.yaml` |
| Suite | `approval` |
| Case id | `a01-read-only-anomaly-detection` |
| Purpose | The read-only command `anomaly-detection` runs with no approval request (ADR-0039 §E.3; `architecture.md` §8) |
| Input | `assets/demo-data/northwind_sales.csv`, the committed synthetic demo dataset. No ADR-0041 fixture |
| Graders | One deterministic (`command_invoked: anomaly-detection`) and one LLM (no approval requested) |
| Expected property | "Runs the command and presents its result without asking for approval." |
| Ablation | `none` (§F.8: only `routing` uses `with-without`) |
| Evidence class | `not_executed`, unchanged |

It needs no credential, no authentication, no MCP server, no web access and no real business or customer data.

## 5. What was not done

- **No eval case was executed**, and no case was attempted, so there was no retry.
- **No E.1 execution record** was created, because nothing executed.
- **No `manual_observation`** was created, and the twelve S3 scenarios were not performed.
- **No repository state changed** beyond this record: no product file, command, skill, agent, eval case, grader,
  threshold, fixture or configuration.
- **No external service, MCP tool, authentication or web access** was used.

## 6. Status

- **M13.2:** IN PROGRESS. 0 of 64 cases executed.
- **§E.1 outcome:** (c), unchanged, now attributable specifically to the missing ceiling.
- **G-3:** OPEN, with the pre-flight facts of §3 recorded.
- **V-4:** OPEN. Only CLI 2.1.278 is seen.
- **Unix-like runtime verification:** OPEN.
- **M13-DEF-04:** `fixed_product`, unaffected by this task.
