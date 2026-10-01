# -*- coding: utf-8 -*-
"""The local `recompute` MCP server behind `bops-analysis-verifier` (ADR-0035 section 3).

A transport and nothing else. It speaks newline-delimited JSON-RPC 2.0 over stdio, exposes
exactly one tool, `recompute`, and hands that tool's raw arguments to
`verification.recompute_request()`, which owns every rule. The platform names the tool
`mcp__plugin_businessops_bops-verifier__recompute` (measured in the M11-A feasibility gate).

What it never does: accept a path, command, URL, configuration or value (the only argument is an
opaque request id); return a figure, path, hash, count, message, exception text or process
output (the only result is the closed `bops.verifier.result/1` envelope); publish MCP
`instructions`; open a network connection; write to stderr. Claude Code copies a failing
server's stderr into its debug log, so this module silences stderr before importing the engine
and keeps anything the engine might print off the protocol channel.

Declared in `.mcp.json` with server identity only (Connector gate approved for M11).
"""

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB = os.path.dirname(_HERE)
_STREAMS = {"out": None}

SERVER_NAME = "bops-verifier"
SERVER_VERSION = "1.0.0"
TOOL_NAME = "recompute"
DEFAULT_PROTOCOL_VERSION = "2025-06-18"

#: The one tool. Its schema is closed: exactly one string key matching the request-id pattern.
TOOL = {
    "name": TOOL_NAME,
    "description": ("Run one sealed BusinessOps verification request, identified only by its opaque "
                    "request id, and return a closed status envelope."),
    "inputSchema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["request_id"],
        "properties": {"request_id": {"type": "string", "pattern": "^rcq-[0-9a-f]{16}$"}},
    },
    # MCP tool annotations, set from what `verification.recompute_request()` does: it creates one
    # new record under ./.businessops/verification/records/ (create-only; an existing record is
    # never overwritten or deleted), so it is not read-only and not destructive, and it opens no
    # network connection.
    "annotations": {
        "title": "Recompute a BusinessOps verification request",
        "readOnlyHint": False,
        "destructiveHint": False,
        "openWorldHint": False,
    },
}

_FIXED_ERRORS = {
    -32700: "parse error",
    -32600: "invalid request",
    -32601: "method not found",
    -32602: "invalid params",
}


def _send(payload):
    out = _STREAMS["out"] or sys.stdout
    out.write(json.dumps(payload) + "\n")
    out.flush()


def _error(message_id, code):
    _send({"jsonrpc": "2.0", "id": message_id,
           "error": {"code": code, "message": _FIXED_ERRORS[code]}})


def _call_tool(params):
    """The envelope for one tool call. Any failure is a fixed code, never text."""
    try:
        from bops import verification
    except Exception:
        return {"protocol": "bops.verifier.result/1", "request_id": None, "status": "failed",
                "record_id": None, "error_code": "execution_error"}
    try:
        return verification.recompute_request((params or {}).get("arguments"))
    except Exception:
        return verification.envelope(None, "failed", error_code="execution_error")


def handle(message):
    """Answer one JSON-RPC message; return the response dict, or `None` for a notification."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return {"jsonrpc": "2.0", "id": None,
                "error": {"code": -32600, "message": _FIXED_ERRORS[-32600]}}
    method = message.get("method")
    message_id = message.get("id")
    if message_id is None:
        return None
    if method == "initialize":
        params = message.get("params") or {}
        version = params.get("protocolVersion")
        return {"jsonrpc": "2.0", "id": message_id, "result": {
            "protocolVersion": version if isinstance(version, str) else DEFAULT_PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": message_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": message_id, "result": {"tools": [TOOL]}}
    if method == "tools/call":
        params = message.get("params") or {}
        if not isinstance(params, dict) or params.get("name") != TOOL_NAME:
            return {"jsonrpc": "2.0", "id": message_id,
                    "error": {"code": -32602, "message": _FIXED_ERRORS[-32602]}}
        body = _call_tool(params)
        return {"jsonrpc": "2.0", "id": message_id, "result": {
            "content": [{"type": "text", "text": json.dumps(body)}], "isError": False}}
    return {"jsonrpc": "2.0", "id": message_id,
            "error": {"code": -32601, "message": _FIXED_ERRORS[-32601]}}


def serve(stream=None):
    source = stream if stream is not None else io.TextIOWrapper(sys.stdin.buffer,
                                                                encoding="utf-8")
    for line in source:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            _error(None, -32700)
            continue
        try:
            response = handle(message)
        except Exception:
            response = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32600, "message": _FIXED_ERRORS[-32600]}}
        if response is not None:
            _send(response)


def main():
    """Run as the MCP process: silence stderr and stdout first, then serve the protocol.

    The protocol channel is the original stdout, kept aside. Everything else the process might
    write - a warning, an engine message, a traceback - goes nowhere, so nothing sensitive can reach
    Claude Code's debug log or corrupt the protocol. Nothing here runs on import.
    """
    _STREAMS["out"] = sys.stdout
    sys.stderr = open(os.devnull, "w")
    sys.stdout = open(os.devnull, "w")
    sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]
    if _LIB not in sys.path:
        sys.path.insert(0, _LIB)
    serve()


if __name__ == "__main__":
    main()
