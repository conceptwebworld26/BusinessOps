"""BusinessOps's filesystem write boundary (ADR-0051).

Two layers, one policy:

1. **Before a tool runs** (`hook`): the plugin-wide Claude Code `PreToolUse` hook classifies
   the exact `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit` or `PowerShell` call about to
   execute (`classify`, `shell`, `pyscan`) and denies a consequential write that holds no
   approval capability.
2. **While the engine runs** (`engine`, `export`): the engine launcher installs an audit hook
   that stops any write outside BusinessOps's own state, and `export.write_text()` is the one
   user-file write path, which asks for approval first.

Both decide with `policy` and both approve through `capability`: a code the user sends in
their own prompt, bound to the exact operation, single-use and short-lived.
"""
