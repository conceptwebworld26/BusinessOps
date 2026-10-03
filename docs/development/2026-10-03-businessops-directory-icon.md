# 2026-10-03 — BusinessOps M4: directory icon

**Milestone:** BOPS-M4 — First Git commit, then repository publication and directory submission preparation
(step: add the icon the Claude Directory listing reported missing)
**Status on completion:** REVIEW
**Supersedes:** None.

## 1. Prompt / task performed

The Anthropic Claude Directory reported "No icon": it looked for `icon` in `plugin.json` and for a file such as
`.claude-plugin/icon.png` or `.svg`, or `assets/icon.png` or `.svg`. The task was to add a professional, original
BusinessOps icon in the authoritative source, reference it from the manifest, rebuild `dist/businessops`, and validate.
Name, slug, MCP server, identity, support email, version and functionality were not to change.

## 2. Objective

The packaged plugin at `dist/businessops` carries both a valid `icon` field in `.claude-plugin/plugin.json` and the
image file at the path that field names. A future build cannot drop either.

## 3. Changes made

1. **Source of truth.** `dist/businessops/` is built by `scripts/build_distribution.py` from an explicit allowlist
   (ADR-0055), so the icon was added to the source repository and the package was rebuilt, not edited.
2. **Official rule** (code.claude.com, *Plugin manifest reference*, *Directory listing fields*, read 2026-10-03):
   - `icon` is read by Anthropic's directory, not by Claude Code.
   - It is set only in `plugin.json`. In a marketplace entry, `claude plugin validate` reports it as an unknown field.
   - It is "the path of an image file inside the plugin, such as `./logo.png`".
   - `validate` accepts it without a warning from v2.1.281. This machine runs 2.1.286.
3. **Icon.** `.claude-plugin/icon.svg`: a navy (`#0F172A`) rounded square, two teal (`#14B8A6`) ascending bars, and
   a light (`#F8FAFC`) geometric "B" whose stem is the tallest bar. Business identity plus an analytics/growth chart.
   - Flat fills, no text, no gradient, filter, font, script, image, link or external reference.
   - 580 bytes, `viewBox="0 0 512 512"`.
   - Rendered at 256, 64, 32 and 16 px on light and dark backgrounds before adoption; legible at 32 px.
   - Original geometry; no third-party mark.
4. **Manifest.** `.claude-plugin/plugin.json` gains `"icon": "./.claude-plugin/icon.svg"` after `keywords`. No other
   field changed. `marketplace.json` is unchanged, as the rule above requires.
5. **Build.** `scripts/build_distribution.py`:
   - ships `.claude-plugin/icon.svg` (`SHIPPED_FILES`);
   - its package check now fails when the manifest `icon` is not a `./` path to an image file inside the package.
     `claude plugin validate --strict` does not check this: a scratch copy naming `./.claude-plugin/missing.svg`
     passed it.
6. **Tests.** `tests/unit/test_distribution_build.py`, three new:
   - the packaged `icon` is `./.claude-plugin/icon.svg` and that file is shipped;
   - the icon parses as SVG with a 512 × 512 viewBox and no script, image, foreignObject, style, animation, `use`,
     link, `href`, `url(`, URL, entity or event handler;
   - the build check rejects a package whose icon file is missing.
7. **Documentation.** `architecture.md` manifest example and repository structure; `project_plan.md` BOPS-M4 row; the
   development index.

No ADR: an asset and one manifest field, easily reversed. Version stays 0.1.0.

## 4. Files created

- `.claude-plugin/icon.svg`
- `dist/businessops/.claude-plugin/icon.svg` (built)
- `docs/development/2026-10-03-businessops-directory-icon.md`

## 5. Files modified

- `.claude-plugin/plugin.json`
- `dist/businessops/.claude-plugin/plugin.json` (built)
- `scripts/build_distribution.py`
- `tests/unit/test_distribution_build.py`
- `architecture.md`, `project_plan.md`, `docs/development/README.md`

## 6. Files deleted

None.

## 7. Features implemented

Directory listing icon — `.claude-plugin/icon.svg`, manifest `icon` — reaches the directory through the packaged
`plugin.json` at plugin path `dist/businessops`.

## 8. Tests performed

```
python scripts/build_distribution.py
claude plugin validate . --strict
claude plugin validate dist/businessops --strict
claude plugin validate dist/businessops/.claude-plugin/plugin.json --strict
claude plugin validate .claude-plugin/plugin.json --strict
python tests/run_tests.py            (before and after the change)
claude --plugin-dir <scratch copy of dist/businessops> mcp list
JSON-RPC over stdio to sh <copy>/lib/bops_run.sh --verifier: initialize, tools/list, unknown tool
```

## 9. Test results

- **Build.** 190 files (189 before, plus the icon), 2,652,033 bytes, `"problems": []`. Against the committed
  package, only `.claude-plugin/plugin.json` changed (the `icon` line) and `.claude-plugin/icon.svg` was added. The
  source and packaged icons are byte-identical.
- **`validate --strict`.** Passed for `.`, `dist/businessops` and `dist/businessops/.claude-plugin/plugin.json`.
  `.claude-plugin/plugin.json` reports the one known, accepted `CLAUDE.md` advisory (architecture.md §2), exactly
  as before this change. No `icon` warning.
- **Full suite.** Before: `Ran 5358 tests`, `FAILED (failures=46, errors=7, skipped=38)`. After: `Ran 5361 tests`,
  `FAILED (failures=46, errors=7, skipped=38)`. The sorted lists of failing and erroring test ids are identical. They
  are the known native-Windows baseline (`integration.test_m13_def08_runtime_resolution`,
  `integration.test_m13_def12_wsl_interpreter`, `integration.test_m13_def24_write_boundary`,
  `unit.test_m13_def24_hook_decision`, `unit.test_m13_def24_write_classifier`, `unit.test_m14_6_verbatim_handback`).
  All 19 `test_distribution_build` tests pass, including `test_the_committed_package_is_exactly_a_fresh_build`.
- **MCP.** `mcp list`: `plugin:businessops:bops-verifier … ✔ Connected`. `initialize`: `bops-verifier` 1.0.0.
  `tools/list`: `recompute` with the same annotations as on 2026-10-01. Unknown tool: `-32602 invalid params`.
- **Package content.** No `Concept Web World` or `hello@conceptwebworld` text. Both packaged manifests name
  `Prakash Meghani - Krayons Global`. No bytecode, editor or OS files.

## 10. Issues discovered

- `claude plugin validate` does not check that `icon` exists; the build check now covers it.
- The directory's own validator was not run locally. Whether the listing accepts the icon is confirmed only by the
  portal, after the push.

## 11. Next step

Re-run the directory submission validation against plugin path `dist/businessops` (an owner step).
