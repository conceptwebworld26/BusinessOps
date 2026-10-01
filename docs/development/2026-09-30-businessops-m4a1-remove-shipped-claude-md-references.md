# 2026-09-30 — BusinessOps Milestone 4A.1: remove shipped-plugin `CLAUDE.md` references

**Milestone:** BOPS-M4A.1 — Remove shipped-plugin `CLAUDE.md` references (BOPS-R14)
**Status on completion:** REVIEW
**Supersedes:** None
**Note on the date:** the file name follows the name given in the milestone prompt. The work was done on 2026-10-01
(local time), the date on its evidence file.

## 1. Prompt / task performed

Fix BOPS-R14 before the first Git commit. Commands, skills and reference documents cited `CLAUDE.md`, which the
installable package deliberately does not ship (ADR-0055). No production file may require `CLAUDE.md`. Every rule
must keep a shipped source of truth, and historical records are not to be changed. No change to `.mcp.json`, the MCP
implementation, the reference-path solution, BOPS-R11, R13 or R15. No commit, push, remote or submission.

## 2. Findings

`CLAUDE.md` mentions in the built package (`dist/businessops/`), traced to their sources:

| Class | Where | Count | Treatment |
|---|---|---|---|
| A. Production | 14 commands, 11 skills, 2 reference documents | 41 citations | Fixed |
| B. Development-only | `README.md`: one documentation-table row, which the build rewrites to a link into the development repository | 1 | Kept |
| B. Development-only | `lib/`: docstrings and comments in 13 engine modules; an AST check found no emitted string | 13 files | Kept |
| C. Historical | `docs/development/`, `docs/decisions/` (not shipped) | — | Unchanged |

None of the class A citations literally said "read CLAUDE.md". They were provenance parentheticals ("(`CLAUDE.md`
section 9)"), "Related policy" footers, and two "see" pointers in reference documents, for example "see the approval
matrix in `CLAUDE.md` section 9". They cited two rules:

- **Section 9, approval follows consequence.** No shipped reference document held the matrix. The README's
  "Approval and write safety" summarises it, but a command or skill can read only `reference/` by path (ADR-0056).
- **Section 8, data privacy.** The disclosure tiers are already defined in `reference/research-policy.md`. The
  output-privacy rule ("prefer aggregates … never in a shareable artifact without asking") existed only in
  `CLAUDE.md`.

## 3. Changes

**Shipped homes for the two rules** (product policy, not a copy of `CLAUDE.md`):

- `reference/analysis-framework.md`: a new section, *Approval follows consequence*, with the approval matrix (none /
  explicit per action / prohibited) and the per-action rule. Its "Owns" line names it, and the "Step 19" pointer now
  points to it. Git operations are described in words ("committing to a version-control repository", "pushing to a
  remote repository …"). The security test `test_no_shipped_markdown_instructs_a_repository_write` forbids literal
  git subcommands in shipped markdown, and was not changed.
- `reference/output-standards.md`: a new section, *Data privacy in output*: prefer aggregates; row-level or
  named-individual data only when required and never in a shareable artifact without asking; shareable output
  pseudonymises identifying contributors; derived files go only to the scratchpad or `./businessops-output/`.
- `reference/research-policy.md`: "approval mechanics" now points to `analysis-framework.md`.

**Citations.** All 39 command and skill citations now name a shipped document through the ADR-0056 path form,
`` `${CLAUDE_PLUGIN_ROOT}/reference/<file>.md` ``:

- section 9 → "the approval matrix in `…/analysis-framework.md`";
- section 8 (disclosure) → "the disclosure tiers in `…/research-policy.md`";
- "sections 8 and 9" in a "Related policy" footer that already lists `research-policy.md` → the approval-matrix
  token only;
- the two anomaly-detection footers that cited section 8 for output privacy → their existing `output-standards.md`
  entry, marked "(including *Data privacy in output*)".

37 of these were applied by a rule-based script and checked one by one in a dry run. 2 were edited by hand. The
reference tokens went from 76 to 113, all resolving.

`CLAUDE.md` itself is unchanged. It stays the development governance document; the shipped `reference/` documents
are now the product's runtime home for these two rules.

## 4. Tests

New: `tests/unit/test_shipped_claude_md_references.py`, 8 tests, all passing. It builds the package and checks:

- `CLAUDE.md` is not shipped;
- no instruction, policy or user document names it;
- no command, skill or agent tells Claude to read it;
- the three cited sections exist in the shipped reference documents;
- the README mentions it only as a link into the development repository;
- the engine mentions it only in comments and docstrings;
- `CLAUDE.md` keeps sections 8 and 9;
- historical records (ADR-0010, the 2026-09-08 foundation record) keep their original citations.

Affected modules, run with the project runner: the 61 modules that read command, skill, agent or reference text,
plus the guard and distribution modules. The only new failure was the repository-write test noted above, fixed by
rewording. A re-run of the 44 modules that read reference documents found no failure outside the known baseline.
The full suite was not run: the change is to Markdown prompt and policy text plus one new test module, and every
module that reads that text was run.

## 5. Package and validation

Evidence: [`docs/testing/evidence/2026-10-01-m4a1-package-validation.txt`](../testing/evidence/2026-10-01-m4a1-package-validation.txt).

- The package is 188 files and 2,650,190 bytes. `claude plugin validate dist/businessops --strict` and the
  `plugin.json` strict check both passed.
- It contains no developer, history, test or eval file, no binary, no symlink, no file over 256 KiB and no personal
  path.
- 113 reference tokens with no missing target, and 0 relative mentions.
- `.mcp.json` is byte-identical to the repository copy and was last modified on 2026-09-30. MCP reports Connected.

## 6. Decisions

No ADR. The change gives two existing rules a shipped home and repoints citations within ADR-0056's existing
mechanism. It is neither hard to reverse nor a new architectural choice.

## 7. Remaining

BOPS-R13 and BOPS-R15 remain deferred. No commit, push, remote or submission.
