# M13-DEF-04 ADR-0042 Acceptance

**Date:** 2026-09-19
**Milestone:** 13 — Test Hardening & Evals, context M13.2. Governance and documentation only.
**Status on completion:** ADR-0042 **Accepted**. **M13-DEF-04 remains OPEN.** M13.2 remains IN PROGRESS/BLOCKED.
Nothing committed, nothing pushed.
**Supersedes:** in `2026-09-19-m13-def-04-remediation-design.md` and `2026-09-19-m13-def-04-runtime-verification.md`,
only the statement that ADR-0042 is Proposed. Both records are otherwise unchanged and not edited.

## Scope

This step is ADR-0042's governance acceptance only, following the owner's "Accept ADR-0042" prompt. It covers:

- the status change;
- reconciling the ADR index, `architecture.md` (§19 and §20), `project_plan.md` and the defect register;
- this record.

Nothing was implemented, run or executed. No runtime experiment was repeated.

## Runtime Evidence

The evidence is `docs/development/2026-09-19-m13-def-04-runtime-verification.md`: a throwaway plugin loaded with
`--plugin-dir` in fresh, isolated headless sessions on Claude Code 2.1.278 under Windows. That record was read and
confirmed to document the following.

| Item | Result | What the record shows |
|---|---|---|
| **V-1** | **PASS** | The runtime delivered the command body with `${CLAUDE_PLUGIN_ROOT}` replaced by the absolute path of the plugin actually loaded (`/`-separated, matching the `--plugin-dir` argument), before the model saw it |
| **V-2a** | **PASS** | The same substitution on the explicit user slash-command route |
| **V-2b** | **PASS** | From a plain question, the model chose the skill itself. The delivered skill body carried the substituted plugin root, distinct from the platform's "Base directory for this skill" header and independent of the model's reply |
| **G-3** | **OPEN** | The eval harness and its sandbox were not used |
| M13 evals / manual observations | none | The record states that neither occurred |

## Remaining Open Items

| Item | Status |
|---|---|
| **G-3** | OPEN. The eval sandbox's plugin loading and root substitution (ADR-0042 V-3) are unverified |
| **V-4** | OPEN. The minimum CLI version providing body substitution is unknown; only 2.1.278 is verified. No minimum is claimed |
| **Unix-like runtime verification** | OPEN. Only Windows was verified at runtime. No cross-platform or marketplace-wide runtime compatibility is claimed |
| **Implementation** | NOT STARTED. It belongs to a dedicated M13-DEF-04 implementation and acceptance milestone under its own owner prompt: `lib/python/biq_run.py`, the launcher line in the 10 commands and 16 skills, and tests T-A to T-K |
| **M13.2 acceptance and manual observations** | BLOCKED on the implementation and on T-A to T-K, including T-J. G-2 is unchanged |

## Decision

**ADR-0042 is Accepted**, 2026-09-19, by the project owner, as drafted. The approved architecture is unchanged:

```bash
python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py" -c "<engine code>"
```

It is the single canonical engine entry. The launcher:

- resolves its own location from `__file__`;
- validates the plugin root (`biq/` and `.claude-plugin/plugin.json` naming `businessiq`);
- requires Python's isolated mode;
- keeps the working directory and the environment out of import resolution;
- verifies that the imported `biq` is its own;
- runs the snippet.

**The only change to ADR-0042's file** is its **Status** line. It now reads Accepted, cites the runtime evidence,
states that acceptance approves the architecture only, and names the items still open. The decision, constraints,
alternatives, security analysis, test requirements and open items are unchanged. The body's pre-verification wording
of V-1 and V-2 is kept, and the Status line records that they have since been verified.

## Implementation Status

No implementation was performed. None of the following was created or changed:

- `lib/python/biq_run.py`;
- any command or skill launcher line, import statement or packaging metadata;
- any test, including T-A to T-K and the shadowing, installed-copy and external-working-directory tests.

## M13-DEF-04

**Still OPEN.** Its remediation architecture is approved. The portability failure and the import-hijack path both
remain in the shipped entry. Every §G.1 field is unchanged, including `status: open` and `blocks_m13_completion: no`.

## M13.2

**Still IN PROGRESS/BLOCKED.** S3-01 to S3-11 cannot be observed meaningfully until the launcher is implemented and
T-A to T-K pass. No eval and no manual observation was performed.

## Documentation Reconciled

| File | Change |
|---|---|
| `docs/decisions/ADR-0042-plugin-root-anchored-isolated-engine-entry.md` | Status line only: Proposed → Accepted, with the evidence reference and the open items |
| `docs/decisions/README.md` | Index row for 0042. It amends no ADR, so there is no amendment note |
| `architecture.md` | §19: an index row for 0042, "not implemented". §20 item 11: the import-hijack aspect, ADR-0042 as the approved remediation, and "the launcher does not exist yet". The defect is not removed |
| `project_plan.md` | The next gate, now the dedicated M13-DEF-04 implementation and acceptance milestone; the M13-DEF-04 header bullet; the *Known issues* row. No milestone was added to the roadmap table |
| `docs/testing/defects.md` | The register row's remediation cell, and an "architecture accepted" paragraph. No §G.1 field changed |
| This record | Created |

**Not changed, being outside this step's allowed scope:**

- **`docs/testing/manual-observation-pack.md`** still says "see Proposed ADR-0042" in one table cell. That wording is
  now stale. It is left for the implementation milestone, which updates the pack's WD-1 section anyway.
- **The two earlier M13-DEF-04 records** say "Proposed". This record supersedes them on that point.

## Validation

The commands and results are in the task report of this session:

- `git diff --check`;
- a whitespace scan, a secret scan and a personal-data scan of the changed documentation;
- `claude plugin validate . --strict`;
- `unit.test_m13_coverage_matrix` (defect register), `unit.test_m13_manual_observation_pack`,
  `unit.test_m13_eval_cases` and `unit.test_m12b_connector_registry` (which scans `docs/development/`);
- a scope audit showing no change under `lib/`, `commands/`, `skills/`, `tests/`, `evals/`, `agents/`, `reference/`,
  `config/`, `.mcp.json`, `.claude-plugin/` or ADR-0039/0040/0041.

**Not run:** the full regression, because no code or test changed. No eval, no manual observation, no Claude session
and no web, MCP or authentication tool was used.

## Git

No `git add`, no commit and no push. All changes are left unstaged.
