# 2026-10-01 — BusinessOps M4: BOPS-R18 installation-path fix

**Milestone:** BOPS-M4 — First Git commit, then repository publication and directory submission preparation
(step: resolve BOPS-R18)
**Status on completion:** REVIEW
**Supersedes:** None. It resolves the BOPS-R18 follow-up recorded in
[ADR-0057](../decisions/ADR-0057-one-public-repository-for-source-and-package.md) and
[`2026-10-01-businessops-m4-single-repository-architecture.md`](2026-10-01-businessops-m4-single-repository-architecture.md).

## 1. Prompt / task performed

Make the installation documentation match the single-repository architecture. The installable plugin is
`dist/businessops/`, not the repository root. The task covered the README, the package README, the four manifests and
the build. It also asked for a classification of repository references, a review of BOPS-R17 without changing its
scripts, and a check of the current Anthropic plugin-path requirement.

## 2. Problem (BOPS-R18)

The README told users to run:

```bash
claude plugin marketplace add conceptwebworld26/BusinessOps
claude plugin install businessops@businessops
```

The repository-root `.claude-plugin/marketplace.json` listed the plugin with `"source": "./"`, which is the repository
root. The commands were valid, but they installed the whole development tree: tests, evals, docs, scripts, `dev/`,
`CLAUDE.md` and a second copy of the package under `dist/`. They did not install the validated package. The README's
clone route, `claude --plugin-dir .`, also loaded the repository root.

## 3. Official behaviour relied on (code.claude.com and claude.com, read 2026-10-01)

- **Marketplace reference, *Plugin sources*.**
  - A relative-path source is "A directory inside the marketplace, resolved from the marketplace root. Must start
    with `./`".
  - The marketplace root is "the directory that contains `.claude-plugin/`".
  - "Use a relative path for a plugin in a subdirectory of the marketplace repository itself."
  - Relative paths resolve for `github` and `git` marketplace sources, because Claude Code has the marketplace's
    files.
- **Plugin loading reference, *In-place and copied plugins*.** A marketplace plugin is copied into
  `cache/<marketplace>/<plugin>/<version>/`, and "Files outside the plugin directory aren't copied". With a GitHub
  marketplace, the repository is cloned to `marketplaces/<name>/`, but only the plugin directory becomes the
  installed plugin and `${CLAUDE_PLUGIN_ROOT}`.
- **Plugin commands reference.**
  - `claude plugin marketplace add <source>`: `owner/repo` gives a `github` source.
  - `claude plugin install <plugin>`, where `<plugin>` is `name` or `name@marketplace`.
  - `claude --plugin-dir <path>` loads a plugin directory for one session.
  - `claude plugin validate <path>` validates `.claude-plugin/marketplace.json` when a directory has one. Otherwise
    it validates `plugin.json`.
- **Submit your plugin (claude.com).**
  - The Source step has a "**Plugin path (optional)**: the folder that holds `.claude-plugin/plugin.json`, if the
    plugin isn't at the repository root".
  - "The repository doesn't have to be dedicated to the plugin. If the plugin is one folder in a larger repository,
    give that folder as the plugin path when you submit; the directory reads and scans only that folder."
  - The repository can stay private while validating and submitting, and must be public before the listing goes
    live.
- **Pre-submission checklist.** "The plugin folder is the folder that contains `.claude-plugin/plugin.json` … It
  can be the repository root or a subfolder. People who install the plugin get only the plugin folder."

**Conclusion.** `dist/businessops` is the plugin path for the directory submission. Its own marketplace catalogue
does not need to point at the repository root. A relative-path entry `./dist/businessops` in the repository's
catalogue is the documented way to make the existing two commands install only the package. No new command syntax
was needed.

## 4. Fix

- **`.claude-plugin/marketplace.json` (repository root).** The entry's `source` changes from `./` to
  `./dist/businessops`. The marketplace name stays `businessops` and the plugin name stays `businessops`, so the
  install id `businessops@businessops` does not change.
- **`scripts/build_distribution.py`.**
  - A new transformation sets the packaged `marketplace.json` entry's `source` to `./`, because inside the package
    the plugin is the package root and `./dist/businessops` would not exist.
  - The build check now rejects a package whose entry is not `./`.
  - The packaged `marketplace.json` is byte-identical to the one committed in `73fb29e`.
- **`README.md`, *Quick start*.** The section now separates three things:
  - where the plugin is: the repository holds source, tests, evaluations and records on purpose, and the
    installable plugin is `dist/businessops/`, built by the builder;
  - Anthropic's directory: the submission's plugin path is `dist/businessops`, and the directory reads only that
    folder. Once listed, no command is needed;
  - the two routes that use commands:
    - adding the marketplace (`claude plugin marketplace add conceptwebworld26/BusinessOps`), whose catalogue entry
      points at `./dist/businessops`;
    - installing the plugin from it (`claude plugin install businessops@businessops`);
  - the clone route, which is now `claude --plugin-dir dist/businessops`.

  The development commands now include the build and say exactly what each `validate` run checks.
- **`dist/businessops/README.md`.** Regenerated by the builder, not edited by hand, so it carries the same text.
  This is the only file in the package that changed.
- **`docs/troubleshooting/README.md`.** The clone route and the escalation check name `dist/businessops`.
- **`architecture.md`.** The distribution row records the repository entry's `./dist/businessops` and the
  package's `./`.
- **Tests.**
  - `tests/unit/test_manifest.py`: the root entry's source is `./dist/businessops`, and that folder holds
    `.claude-plugin/plugin.json`. `claude plugin validate` does not check that a relative source exists: a copy
    pointing at `./dist/missing` passed.
  - `tests/unit/test_distribution_build.py` (16 tests): the packaged catalogue equals the source except for
    `source`, and the build check rejects a package entry that is not `./`.

The repository architecture is unchanged:
- one public repository, `https://github.com/conceptwebworld26/BusinessOps`;
- the committed package `dist/businessops/`;
- every test, eval, document, ADR, script, `architecture.md`, `project_plan.md` and `CLAUDE.md` is kept.

`hooks/bops_guard.sh` and `lib/bops_run.sh` are unchanged. No ADR: this applies ADR-0057's documented follow-up and
reverses easily.

## 5. Reference classification (`conceptwebworld26/BusinessOps`)

Classes: A = repository, source or review reference; B = plugin installation reference; C = historical or
development record; D = incorrect root-install instruction.

| Where | Class |
|---|---|
| Both `plugin.json` `homepage` and `repository`, both `marketplace.json` `homepage` (source and package) | A |
| The 15 `lib/schemas/*.schema.json` `$id` values (source and package) | A |
| `architecture.md` (distribution row, manifest example), `docs/decisions/README.md`, `docs/troubleshooting/README.md` support link, `project_plan.md` repository line and BOPS-M4 row | A |
| `scripts/build_distribution.py` (`REPOSITORY_URL`, docstring), `tests/unit/test_distribution_build.py`, `tests/unit/test_shipped_claude_md_references.py` | A |
| README and package README links to unshipped documents (rewritten by the builder) | A |
| README and package README: `marketplace add`, `git clone`, repository link in *Where the plugin is* | B (after this fix) |
| ADR-0057, the earlier M4 records, the M1 record, the single-repository evidence file, the BOPS-R18 row's former wording | C |
| README and package README `claude plugin marketplace add conceptwebworld26/BusinessOps` **before** this fix (root entry `./`) | D, fixed |

`BusinessOps-Plugin` appears only in ADR-0057, the single-repository record and the BOPS-M4 plan row, each stating that
no such repository exists. There are no active references, and none in the package.

## 6. Package validation

Evidence: [`docs/testing/evidence/2026-10-01-r18-installation-path-validation.txt`](../testing/evidence/2026-10-01-r18-installation-path-validation.txt).

- **Build.** 189 files, 2,651,459 bytes, `"problems": []`. Only `README.md` differs from the committed package.
- **`claude plugin validate --strict`** passed for `dist/businessops` (its marketplace manifest), for
  `dist/businessops/.claude-plugin/plugin.json`, and for `.` (the repository catalogue).
- **Content checks.**
  - None of: files over 256 KiB, binaries, symlinks, bytecode, secrets, personal paths, BusinessIQ or
    BusinessOps-Plugin mentions.
  - `CLAUDE.md` is not shipped. It is named only in engine comments and in one README link to the repository.
- **Tests.** 13 package-related modules show no failure outside the known native-Windows baseline in
  `unit.test_m13_def24_write_classifier`: 6 failures and 1 error, the BOPS-M3 set minus `test_17`.
  `test_the_committed_package_is_exactly_a_fresh_build` passes. The full suite was not run: the change is confined
  to manifests, the builder, documentation and their tests.
- **MCP.** Run on a throwaway copy.
  - `mcp list`: Connected.
  - `initialize` and `tools/list` (with annotations) worked.
  - A malformed id returned `request_id_invalid`.
  - An unknown tool returned `invalid params`.
- **Not run locally:** `claude plugin marketplace add`, because it writes user-level settings. The live GitHub
  install route is covered by the task report, not by this record.

## 7. BOPS-R17 status (unchanged, open)

The pre-submission checklist was re-read on 2026-10-01. Two rules apply to scripts that hooks and MCP servers run.

**Rule that blocks.** "In the command of a hook or an MCP server, write each path in full from `${CLAUDE_PLUGIN_ROOT}`,
with no other variable, command substitution, wildcard, or inline program". This blocks when the plugin folder is a
subfolder of the repository.

- BusinessOps' five commands comply.
- This is not expected to be a validation failure.

**Rules that hold for a reviewer.** Both report the finding **Scripts the validator couldn't follow**.

- The checklist says: "When the plugin folder is a subfolder of the repository, also keep shell variables other than
  `${CLAUDE_PLUGIN_ROOT}`, command substitutions, and calls to other files in the plugin out of those scripts."
- *Choices a reviewer always checks* says that in a subfolder, a hook or server that "runs a shell script that itself
  runs another file" is held.
- `hooks/bops_guard.sh` and `lib/bops_run.sh` use other variables and command substitutions, and they run Python
  files. So a **reviewer hold is expected. That is a review-risk condition, not a portal validation failure.**
- The `sh`-launched MCP server is a separate hold (BOPS-R10).

The checklist's alternatives are:
- a plugin at the root of its own repository, which the owner declined in ADR-0057;
- logic kept in plain shell scripts.

Neither is adopted without portal evidence. R17 stays open for the actual portal validation.

## 8. Git

One commit, "M4: fix distribution plugin installation path", on top of `73fb29e`, pushed to `origin` without force.
See the task report for the hash and the verification.
