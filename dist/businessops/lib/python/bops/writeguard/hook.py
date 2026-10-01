"""The plugin-wide Claude Code hook: BusinessOps's pre-execution write boundary (ADR-0051).

`hooks/hooks.json` runs this, through the one engine launcher, for three events:

``PreToolUse`` (matcher: `Bash|Write|Edit|MultiEdit|NotebookEdit|PowerShell|Skill` and the
prompt-injecting tools)
    Runs before the tool body. For a write-capable tool in a session that has engaged
    BusinessOps, it classifies the exact `tool_input` about to execute and returns
    `permissionDecision: "deny"` for anything prohibited, and for anything that needs approval
    and holds no matching capability. It never returns `allow`: a call it lets through still
    meets the user's own permission settings.

``UserPromptSubmit``
    The only place a write approval is granted: `approve BOPS-W-XXXXXXXX` in a prompt the user
    submitted grants that pending request, for that session.

``UserPromptExpansion``
    A BusinessOps slash command engages the session.

**Scope.** Claude Code 2.1.283's hook input names the session, the working directory, the tool
and its input, and (in a subagent) the agent; it does not say which plugin a tool call serves.
BusinessOps therefore scopes itself by *engagement*, established only from facts the runtime
reports: a `Skill` call to a BusinessOps skill or command, a BusinessOps slash command, a
BusinessOps subagent, or a call of the BusinessOps engine launcher. From that moment the session
is engaged for the rest of its life and every write-capable tool call in it is governed. A
session that never engages BusinessOps is left alone, except that no tool call anywhere may
touch the approval store or invoke the guard itself.

**Fail-closed.** An unreadable hook input, or an internal error while the session is engaged
or its engagement is unknown, denies the call. `hooks/bops_guard.sh` turns a guard that cannot
start at all into a blocking exit status.

Standard library only.
"""

import json
import os
import sys
import tempfile

from . import capability as C
from . import classify as K
from . import policy as P

PRE_TOOL_USE = "pre-tool-use"
USER_PROMPT_SUBMIT = "user-prompt-submit"
USER_PROMPT_EXPANSION = "user-prompt-expansion"
EVENTS = (PRE_TOOL_USE, USER_PROMPT_SUBMIT, USER_PROMPT_EXPANSION)
PLUGIN_PREFIX = "businessops:"
# Test seam: the store location for the hook process only. The hook's environment is Claude
# Code's own, never a tool call's; the engine and the export API do not read it.
STORE_VARIABLE = "BOPS_GUARD_ROOT"
MAX_LISTED = 12
# Prompt sources the runtime may report that no user typed (2.1.283 does not report any yet).
INJECTED_SOURCES = frozenset(("system", "loop_wakeup", "schedule_wakeup", "poll_event"))


def plugin_names(root=None):
    """Every command, skill and agent name this plugin ships, bare and plugin-qualified."""
    root = root or P.plugin_root()
    names = set()
    for sub, suffix in (("commands", ".md"), ("agents", ".md"), ("skills", "")):
        directory = os.path.join(root, sub)
        try:
            entries = os.listdir(directory)
        except OSError:
            continue
        for entry in entries:
            if suffix and entry.endswith(suffix):
                names.add(entry[:-len(suffix)])
            elif not suffix and os.path.isfile(os.path.join(directory, entry, "SKILL.md")):
                names.add(entry)
    return names | {PLUGIN_PREFIX + name for name in names}


def is_businessops(name, names=None):
    if not isinstance(name, str) or not name:
        return False
    name = name.strip().lstrip("/")
    return name.startswith(PLUGIN_PREFIX) or name in (names if names is not None else plugin_names())


def _deny(reason, user_message):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": reason},
            "systemMessage": user_message}


def _listed(ops):
    lines = ["  - %s" % op.describe() + (" — %s" % op.reason if op.reason else "")
             for op in ops[:MAX_LISTED]]
    if len(ops) > MAX_LISTED:
        lines.append("  - … and %d more" % (len(ops) - MAX_LISTED))
    return lines


def prohibited_response(tool, ops):
    head = "BusinessOps write guard blocked this %s call before it ran. Nothing was written or changed." % tool
    reason = "\n".join([head, "It is prohibited, and no approval can unlock it:"] + _listed(ops))
    user = "BusinessOps blocked a prohibited %s call before it ran (nothing was changed): %s" % (
        tool, "; ".join(op.describe() for op in ops[:3]))
    return _deny(reason, user)


def approval_response(tool, ops, code):
    head = "BusinessOps write guard blocked this %s call before it ran. Nothing was written or changed." % tool
    reason = "\n".join(
        [head, "It needs the user's explicit approval (see the BusinessOps README, "
               "\"Approval and write safety\"):"] + _listed(ops) + [
            "To proceed, ask the user to approve it by replying with exactly:",
            "  approve %s" % code,
            "then repeat this identical %s call. The approval is single-use, expires %d minutes after "
            "it is given, and covers only this exact call: any change to the command, target, "
            "content or operation needs a new approval. Do not attempt the change another way."
            % (tool, C.GRANT_TTL_SECONDS // 60)])
    user = ("BusinessOps blocked a %s call before it ran (nothing was written): %s. "
            "To allow exactly this call once, reply: approve %s"
            % (tool, "; ".join(op.describe() for op in ops[:3]), code))
    return _deny(reason, user)


def _policy(payload, cwd, engaged, store):
    roots = [tempfile.gettempdir()]
    scratch = payload.get("scratchpad_dir")
    if isinstance(scratch, str) and os.path.isabs(scratch):
        roots.append(scratch)
    return P.Policy(cwd, temp_roots=roots, engaged=engaged, guard=store.root)


def pre_tool_use(payload, store, names=None):
    """The decision for one PreToolUse event: a deny response, or None to let the call proceed."""
    names = plugin_names() if names is None else names
    session = payload.get("session_id")
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    if tool == "Skill":
        if is_businessops(tool_input.get("skill"), names):
            store.engage(session, "skill %s" % tool_input.get("skill"))
        return None
    if is_businessops(payload.get("agent_type"), names):
        store.engage(session, "agent %s" % payload.get("agent_type"))
    if tool in K.INJECTION_TOOLS:
        if K.carries_approval_phrase(tool_input):
            op = P.Operation(P.GUARD_ENTRY, detail="%s carrying an approval phrase" % tool)
            op.reason = "an approval may only come from the user's own prompt"
            return prohibited_response(tool, [op])
        return None
    if tool not in K.WRITE_TOOLS:
        return None
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not os.path.isabs(cwd):
        cwd = os.getcwd()
    # No session id means engagement cannot be known, so the call is governed (fail-closed).
    engaged = store.engaged(session) or not C.valid_session(session)
    policy = _policy(payload, cwd, engaged, store)
    result = K.classify_tool_call(tool, tool_input, policy)
    if result.engine and not engaged:
        store.engage(session, "engine launcher")
        engaged = True
        policy = _policy(payload, cwd, engaged, store)
        result = K.classify_tool_call(tool, tool_input, policy)
    prohibited = result.needing(P.PROHIBITED)
    if not engaged:
        guard_ops = [op for op in prohibited if op.kind == P.GUARD_ENTRY or
                     any(P.within(p, policy.guard) for p in (op.target,) + op.sources if p)]
        return prohibited_response(tool, guard_ops) if guard_ops else None
    if prohibited:
        return prohibited_response(tool, prohibited)
    needing = result.needing(P.APPROVAL)
    if not needing:
        return None
    bound = C.binding(session, tool, os.path.realpath(cwd), K.input_digest(tool, tool_input),
                      result.operations)
    if C.valid_session(session) and store.redeem(bound) is not None:
        return None
    if not C.valid_session(session):
        return approval_response(tool, needing, "(unavailable: the runtime gave no session id)")
    return approval_response(tool, needing, store.request(bound))


def user_prompt_submit(payload, store, names=None):
    """Grant the approvals the user's prompt names; engage on a BusinessOps slash command."""
    if payload.get("agent_id") or payload.get("source") in INJECTED_SOURCES:
        return None
    session = payload.get("session_id")
    prompt = payload.get("prompt") if isinstance(payload.get("prompt"), str) else ""
    first = prompt.strip().split(None, 1)[0] if prompt.strip() else ""
    if first.startswith("/") and is_businessops(first, plugin_names() if names is None else names):
        store.engage(session, "slash command %s" % first)
    codes = C.approval_codes(prompt)
    if not codes:
        return None
    context, shown = [], []
    for code in codes:
        record, why = store.grant(code, session)
        if record is None:
            context.append("BusinessOps did NOT grant %s: %s. Nothing is approved by it." % (code, why))
            shown.append("%s not granted (%s)" % (code, why))
            continue
        lines = C.describe(record["binding"])
        context.append(
            "The user approved %s for this %s call only: %s. It is single-use and expires in %d "
            "minutes. Repeat the identical call now; any change to it needs a new approval."
            % (code, record["binding"].get("tool"), "; ".join(lines), C.GRANT_TTL_SECONDS // 60))
        shown.append("%s approved once: %s" % (code, "; ".join(lines[:3])))
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                   "additionalContext": "\n".join(context)},
            "systemMessage": "BusinessOps: " + " | ".join(shown)}


def user_prompt_expansion(payload, store, names=None):
    if is_businessops(payload.get("command_name"), plugin_names() if names is None else names):
        store.engage(payload.get("session_id"), "slash command %s" % payload.get("command_name"))
    return None


_HANDLERS = {PRE_TOOL_USE: pre_tool_use, USER_PROMPT_SUBMIT: user_prompt_submit,
             USER_PROMPT_EXPANSION: user_prompt_expansion}


def handle(event, raw, store=None):
    """The response object for one event's raw stdin, or None. Fails closed for PreToolUse."""
    store = store or C.Store()
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("hook input is not an object")
    except ValueError:
        if event == PRE_TOOL_USE:
            return _fail_closed("the hook input could not be read")
        return None
    engaged = None
    try:
        if event == PRE_TOOL_USE:
            engaged = store.engaged(payload.get("session_id"))
        return _HANDLERS[event](payload, store)
    except Exception as error:                      # noqa: BLE001 - the boundary must not open on a bug
        sys.stderr.write("bops write guard: %s: %s\n" % (error.__class__.__name__, error))
        if event == PRE_TOOL_USE and engaged is not False:
            return _fail_closed("an internal error (%s)" % error.__class__.__name__)
        return None


def _fail_closed(why):
    reason = ("BusinessOps write guard blocked this call before it ran, because of %s. Nothing was "
              "written. The guard fails closed: while BusinessOps is in use, a call it cannot "
              "check does not run." % why)
    return _deny(reason, "BusinessOps blocked a tool call it could not check (%s)." % why)


def main(event, stdin=None, stdout=None):
    """Entry from `bops_run.py --guard <event>`. Always exits 0; the decision is in the JSON."""
    if event not in EVENTS:
        sys.stderr.write("bops write guard: unknown event %r\n" % event)
        return 2
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    override = os.environ.get(STORE_VARIABLE)
    store = C.Store(override) if override and os.path.isabs(override) else C.Store()
    response = handle(event, stdin.read(), store)
    if response is not None:
        stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    return 0
