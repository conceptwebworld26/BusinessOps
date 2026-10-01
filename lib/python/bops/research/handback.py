"""The scout's reply, captured by the harness and handed to the parser verbatim (ADR-0053).

`architecture.md` section 10 requires the scout's reply to reach `close_retrieval()` unedited:
extracting or repairing it would move authorship into the one context that can read business
data. Until M14-6 that text travelled through the orchestrating model, which had to copy the
`Agent` tool result into a scratchpad file. The harness shows that result inside a frame (a
preamble, every line indented, a usage footer). Measured on four live runs, even an explicit
instruction to copy it exactly lost whitespace-only lines and added a final newline. So a model
copy cannot guarantee "verbatim" (M9 criterion 5).

This module takes the model out of that path. Claude Code gives a plugin's `PostToolUse` hook the
subagent's own reply, before any framing, as `tool_response.content`. `capture()` runs in that
hook (`hooks/hooks.json` -> `bops_run.sh --handback`) and writes the text, byte for byte, to one
file per retrieval operation. `reply()` reads it back for `close_retrieval()`. Nothing between
the two trims, strips, decodes differently or reconstructs anything.

**Where the text lives.** Captures are kept under the write guard's own state
(`~/.claude/businessops/guard/handback/`). The guard refuses every tool call that touches that
root and every tool call that invokes this entry (ADR-0051), so a model cannot plant or
overwrite a "reply". Only the harness-run hook writes there.

**What it captures.** A `PostToolUse` event for an `Agent` or `Task` call to
`businessops:bops-research-scout` whose prompt is a gate-issued brief naming an `operation`, and
nothing else. Every other event is ignored silently. A hook that fails must not disturb the
session: a missing capture makes `reply()` raise, and the retrieval then fails closed.

Standard library only.
"""

import io
import json
import os
import re
import tempfile

from ..writeguard import policy as policy_mod

SCOUT_AGENT = "businessops:bops-research-scout"
DISPATCH_TOOLS = ("Agent", "Task")

#: An operation id names a file, so it is held to a closed alphabet before it is ever used as one.
_OPERATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


class HandbackError(Exception):
    """No verbatim capture exists for this operation, or the operation id is not acceptable."""


def root(home=None):
    """`~/.claude/businessops/guard/handback/`: one file per captured retrieval operation."""
    return os.path.join(policy_mod.guard_root(home), "handback")


def _path(operation, home=None):
    if not isinstance(operation, str) or not _OPERATION.match(operation):
        raise HandbackError("not an acceptable operation id: %r" % (operation,))
    return os.path.join(root(home), operation + ".txt")


def _reply_text(tool_response):
    """The subagent's own reply: the text blocks of `tool_response.content`, joined unchanged."""
    if isinstance(tool_response, str):
        return tool_response
    if not isinstance(tool_response, dict):
        return None
    content = tool_response.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    texts = [block.get("text") for block in content
             if isinstance(block, dict) and block.get("type") == "text"]
    if not texts or not all(isinstance(t, str) for t in texts):
        return None
    return "".join(texts)


def capture(event, home=None):
    """Store one scout reply verbatim. Returns the path written, or None when the event is not one.

    The file is written through a temporary file in the same directory and renamed into place, so
    a reader never sees a partial reply. The latest dispatch for an operation replaces an earlier
    one: a retrieval is dispatched once (ADR-0017), and a repeated operation id means the same
    retrieval was asked for again.
    """
    if not isinstance(event, dict) or event.get("hook_event_name") != "PostToolUse":
        return None
    if event.get("tool_name") not in DISPATCH_TOOLS:
        return None
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict) or tool_input.get("subagent_type") != SCOUT_AGENT:
        return None
    try:
        brief = json.loads(tool_input.get("prompt") or "")
    except (TypeError, ValueError):
        return None
    operation = brief.get("operation") if isinstance(brief, dict) else None
    text = _reply_text(event.get("tool_response"))
    if text is None:
        return None
    try:
        path = _path(operation, home)
    except HandbackError:
        return None
    directory = os.path.dirname(path)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=directory, prefix=".capture-", suffix=".tmp")
    try:
        with io.open(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
    return path


def reply(operation, home=None):
    """The captured reply for `operation`, exactly as the scout returned it.

    Read with `newline=""`, so not even a line ending is translated. Raises `HandbackError` when
    no capture exists: the caller must then report a failed retrieval, never supply the text
    itself.
    """
    path = _path(operation, home)
    if not os.path.isfile(path):
        raise HandbackError(
            "no verbatim capture of the scout's reply exists for operation %r. The plugin's "
            "PostToolUse hook records it when the dispatch completes. Without it the retrieval "
            "has failed, and the reply must not be supplied by hand." % operation)
    with io.open(path, "r", encoding="utf-8", newline="") as stream:
        return stream.read()


def main(stream=None):
    """Entry for `bops_run.py --handback`, run by the plugin's `PostToolUse` hook.

    Reads the event JSON from stdin and always returns 0: a capture that cannot be made must not
    disturb the session, and the missing capture already fails the retrieval closed.
    """
    import sys
    try:
        raw = stream.read() if stream is not None else sys.stdin.buffer.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")          # Claude Code sends the event as UTF-8 JSON
        capture(json.loads(raw))
    except Exception:
        pass
    return 0
