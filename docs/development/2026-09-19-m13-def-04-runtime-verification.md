# M13-DEF-04 Runtime Verification — V-1 / V-2

**Date:** 2026-09-19
**Milestone:** 13 — Test Hardening & Evals, context M13.2. This verifies the platform facts that Proposed ADR-0042
depends on.
**Status on completion:** V-1 PASS, V-2a PASS, V-2b PASS. G-3 remains OPEN. ADR-0042 stays **Proposed**: this
record does not accept it. **M13-DEF-04 remains OPEN**, and M13.2 remains IN PROGRESS/BLOCKED.
**Supersedes:** in `2026-09-19-m13-def-04-remediation-design.md`, only the "unverified" status of V-1 and V-2 (§6, §15).
That record is otherwise unchanged and not edited.

## 1. Scope

This record establishes, at runtime rather than from CLI source, two things:

- **V-1:** whether a plugin command body loaded by Claude Code arrives at the model with the literal
  `${CLAUDE_PLUGIN_ROOT}` already replaced by the absolute path of the plugin actually loaded;
- **V-2:** whether that holds both for an explicit user command invocation (V-2a) and for a skill the model chooses
  to invoke itself (V-2b).

The probe was a **throwaway plugin** created outside the repository. It had:

- no BusinessIQ code, MCP server, network access, tests or data;
- one command, `commands/probe.md`, with marker `V1_MARKER_fdc6f833` and the line
  `ROOT_EXPRESSION=${CLAUDE_PLUGIN_ROOT}/probe-anchor`;
- one skill, `skills/zirconquill-glossary/SKILL.md`, with marker `V2_SKILL_MARKER_fdc6f833` and the same line.

Before runtime, both files held the literal placeholder, confirmed with `grep`. BusinessIQ was not loaded and not
exercised.

## 2. Environment

| Item | Value |
|---|---|
| Claude Code CLI | 2.1.278 (`claude --version`) |
| OS | Windows 11. The shell was Git Bash |
| Plugin loading mechanism | `--plugin-dir <path>` ("Load a plugin from a directory or .zip for this session only", per `claude --help`) |
| Temporary plugin path | `~/AppData/Local/Temp/claude/<session-scratchpad>/v1probe-fdc6f833/plugin`, passed in 8.3 short form |
| Plugin recognised | Yes. Each session's `init` event listed plugin `v1probefdc6f833` (source `v1probefdc6f833@inline`, version `0.0.1`), with slash commands `v1probefdc6f833:probe` and `v1probefdc6f833:zirconquill-glossary`. `claude plugin validate` passed, with one advisory about missing author metadata |
| Session model | `claude-sonnet-5`, the platform default |

**Session invocation.** Each session was a fresh headless session, run from an empty working directory outside the
repository:

```
claude -p "<prompt>" --plugin-dir "<tmp>/plugin" --restricted --strict-mcp-config --tools "Skill" \
       [--no-session-persistence | --session-id <uuid>] --output-format stream-json --verbose
```

What the isolation flags do:

- `--restricted` ignores user, project and local settings, so installed plugins, BusinessIQ included, are not
  enabled;
- `--strict-mcp-config` with no config starts no MCP server;
- `--tools "Skill"` leaves the Skill tool as the only available tool.

Every session's `init` event reported `tools: ['Skill']` and `mcp_servers: []`, and the only plugins were the probe
and the built-in `agents-md`. Every `result` reported `web_search_requests: 0`, `web_fetch_requests: 0` and
`permission_denials: []`, and stderr was empty.

**Evidence sources.** Three sessions ran:

- `v1`: V-1 with no persistence;
- `v1b` and `v2b`: persisted to one-off session transcripts, so that the **exact message content the runtime built
  and delivered** could be read.

The transcripts were copied out, then deleted (§11). Excerpts below are verbatim, with the home directory shown as `~`
and the scratchpad segment elided as `<session-scratchpad>`. Nothing else is altered.

## 3. V-1 — command body substitution

**Setup.** The only user message in a fresh session was `/v1probefdc6f833:probe`. The model was not asked to open any
file, no file-reading tool was available, and none was used.

**Result: PASS.**

**Evidence 1: the delivered content**, from the runtime transcript of session `v1b`. The command-invocation message,
then the command body the runtime delivered to the model:

```
[user] <command-message>v1probefdc6f833:probe</command-message>
       <command-name>/v1probefdc6f833:probe</command-name>
[user, isMeta] Reply with exactly the three lines between BEGIN and END below, copied character for character as they
       appear in this message. Add no commentary and use no tools.
       BEGIN
       V1_MARKER_fdc6f833
       ROOT_EXPRESSION=~/AppData/Local/Temp/claude/<session-scratchpad>/v1probe-fdc6f833/plugin/probe-anchor
       END
```

**Evidence 2: the model's reply** in session `v1`, which had no persistence:

```
BEGIN
V1_MARKER_fdc6f833
ROOT_EXPRESSION=~/AppData/Local/Temp/claude/<session-scratchpad>/v1probe-fdc6f833/plugin/probe-anchor
END
```

**Interpretation.**

- **The substitution was complete.** The file said `${CLAUDE_PLUGIN_ROOT}/probe-anchor`, and the runtime delivered the
  absolute plugin directory, with the placeholder gone.
- **The value is the loaded plugin's own path.** It matches the `--plugin-dir` argument exactly, including its 8.3
  short-form home segment (shown here as `~`), with `/` separators. The session's `init` reported the
  working directory in long form, so the value cannot have been inferred from the working directory.
- **It matches the static reading of ADR-0042:** exact brace form, backslashes normalised to `/`.

## 4. V-2a — explicit command route

**Setup.** As §3. The route is an explicit user slash-command invocation.

**Result: PASS.** V-1's evidence is exactly this route. The runtime recorded the invocation as
`<command-name>/v1probefdc6f833:probe</command-name>` and delivered the substituted body immediately after it.

**Additional observation.** After the body was loaded, the model also called `Skill {"skill": "v1probefdc6f833:probe"}`.
The runtime answered "Skill /v1probefdc6f833:probe is already loaded above; instructions unchanged." and did not
deliver the body a second time. A command can therefore also be reached through the Skill tool. In this run it had
already been expanded, so a model-first expansion of a **command** body was not separately observed.

## 5. V-2b — model-invoked skill route

**Setup.** A fresh session with the same plugin and isolation. The only user message was the natural-language
question "What does the word zirconquill mean?". It names no command or skill, and it does not involve BusinessIQ, real
data or any consequential action. The skill's description, "Use when the user asks what the made-up word
'zirconquill' means", was the only relevant capability. The skill was not changed.

**Model behaviour.** The model selected the skill on its own: `TOOL_USE Skill {"skill":
"v1probefdc6f833:zirconquill-glossary"}` → `TOOL_RESULT Launching skill: v1probefdc6f833:zirconquill-glossary`.

**Result: PASS.**

**Evidence: the delivered skill content**, from the runtime transcript of session `v2b`:

```
[user, isMeta] Base directory for this skill: ~\AppData\Local\Temp\claude\<session-scratchpad>\v1probe-fdc6f833\plugin\skills\zirconquill-glossary

       The word "zirconquill" is a made-up test word with no meaning.
       When you answer, first say that, then copy character for character the two lines between BEGIN and END below,
       exactly as they appear in this message. Use no other tool.
       BEGIN
       V2_SKILL_MARKER_fdc6f833
       ROOT_EXPRESSION=~/AppData/Local/Temp/claude/<session-scratchpad>/v1probe-fdc6f833/plugin/probe-anchor
       END
```

**Interpretation.**

- **Substitution happened on the model-invoked route.** The skill body's own `${CLAUDE_PLUGIN_ROOT}` line arrived as
  the absolute plugin root, not the literal placeholder.
- **It is distinct from the header.** The platform's "Base directory for this skill" header is separate and different:
  it names the skill's directory, with `\` separators. The substituted body line names the plugin root, with `/`
  separators. The evidence concerns the body line only, as this task required.
- **The model's reply is not relied on.** It answered the definition and declined to echo the marker lines, saying the
  embedded copy instruction came from tool content and not from the user. The PASS rests on the runtime's
  delivered-content record, not on the model echoing.

## 6. G-3

**G-3 remains OPEN.** These sessions were ordinary headless Claude Code sessions. They were **not** the
`claude plugin eval` harness or its sandbox, which was not invoked in any form. How the eval sandbox loads a plugin,
whether it substitutes the root, and to what (ADR-0042 V-3), remain unverified.

## 7. Security

- **Nothing out of scope was used.** No BusinessIQ code, command, skill or MCP tool; no MCP server (`mcp_servers: []`);
  no web access (0 requests); no credential; no external service other than the model API the sessions themselves
  use.
- **The probe could not act.** It contained no executable code. The only tool available was Skill, so no shell, file
  or network tool existed. No permission was requested or granted.
- **Nothing was modified or installed.** No installed plugin was modified, no package was installed, no environment
  variable was set, and no BusinessIQ repository file was read by the probe sessions.
- **Cost:** about $0.082 across the three sessions ($0.0393, $0.0244 and $0.0186).

## 8. ADR-0042 impact

The runtime evidence resolves ADR-0042's **V-1 and V-2**:

- `${CLAUDE_PLUGIN_ROOT}` in plugin command and skill bodies is substituted with the loaded plugin's absolute path
  (`/`-separated), on the explicit command route and on the model-invoked skill route, on CLI 2.1.278 under Windows;
- the substituted form suits the ADR's `python -I "${CLAUDE_PLUGIN_ROOT}/lib/python/biq_run.py"` design, including a
  home path containing a space (long form) or a `~` short form.

**Still open, and none of it blocks acceptance:**

- **V-3:** the eval sandbox, part of G-3.
- **V-4:** the minimum CLI version. This record verifies 2.1.278 only.
- **Runtime on Unix-like systems:** not tested here. The static reading gives no Windows-specific path.
- **A model-first expansion of a command body** (§4) was not separately observed. The model-invoked route was shown
  with a skill, and the static reading shows commands and skills share one builder.

**The evidence is sufficient for ADR-0042 to proceed to owner acceptance.** Acceptance itself is the owner's act and
has not been performed.

## 9. M13-DEF-04 impact

**M13-DEF-04 remains OPEN.** The remediation design is complete, and implementation has not occurred. Nothing in
`lib/`, `commands/` or `skills/` was changed.

## 10. M13.2 impact

**M13.2 remains IN PROGRESS/BLOCKED.**

- S3-01 to S3-11 stay blocked until ADR-0042 is accepted, implemented in its own milestone, and its acceptance tests
  (T-A to T-K, including T-J) pass.
- No manual observation was performed.
- No eval was run.

## 11. Cleanup

- **Throwaway plugin:** its directory was deleted, including the plugin, the working directory and the evidence
  copies.
- **Session transcripts:** the two persisted transcripts, and the project directory the platform created for the
  temporary working directory under `~/.claude/projects/`, were deleted. No `v1probe` entry remains under
  `~/.claude/projects`.
- **Configuration files unchanged:**
  - `~/.claude/settings.json`: SHA-256 prefix `55b16e8f5944beca`, before and after;
  - `~/.claude/plugins/installed_plugins.json`: `1cbc4d57741171cc`, before and after;
  - `~/.claude/plugins/known_marketplaces.json`: `37d0bd4777cc499b`, before and after.
- **`~/.claude.json` changed.** The platform added three usage-counter entries for the throwaway plugin:
  - `pluginUsage["v1probefdc6f833@inline"]`;
  - `skillUsage["v1probefdc6f833:probe"]`;
  - `skillUsage["v1probefdc6f833:zirconquill-glossary"]`, each holding `usageCount` and `lastUsedAt`.

  No settings, project entry or permission was added.
- **Why those entries were left in place.** The file is written continuously by the running development session, so
  editing it concurrently risked corrupting it. They are inert usage metadata for a plugin that no longer exists, and
  the owner may delete the three keys at will.
- **No environment variable** was changed (`CLAUDE_PLUGIN*` count in `env`: 0), and **no package** was installed.
