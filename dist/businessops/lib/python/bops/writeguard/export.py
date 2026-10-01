"""The engine's one user-file write path: an export that asks first (ADR-0051).

The engine had no way to write a user's file, and it gains exactly one: `write_text()`. It
applies the same zone policy as the pre-execution hook (`writeguard.policy`) and the same
approval store (`writeguard.capability`):

- a new file under `./businessops-output/` is written at once (`CLAUDE.md` section 9: no
  approval, state the path);
- a prohibited target (the approval store, the plugin, an existing business data file) is
  refused with no approval path;
- anything else raises `WriteApprovalRequired` carrying a code, and writes nothing. After the
  user replies `approve <code>`, the identical call - same path, same content, same mode,
  same session, and the target in the same existence state - redeems the capability once and
  writes.

The binding includes a digest of the content, so an approval to write one text into
`README.md` does not cover another. The session comes from `CLAUDE_CODE_SESSION_ID`, which
Claude Code sets for the tool's shell (observed on 2.1.283) and which the pre-execution hook
refuses to let a command line override; without it no approval can be granted, so the export
fails closed.

When the engine's execution guard is installed, the write itself is admitted by a one-shot
authorisation for exactly this path and operation, issued only after the capability was
redeemed.

Standard library only.
"""

import hashlib
import json
import os

from ..errors import WriteApprovalRequired, WriteBlockedError
from . import capability as C
from . import engine as E
from . import policy as P

TOOL = "bops.export"
SESSION_VARIABLE = "CLAUDE_CODE_SESSION_ID"


def _digest(path, text, encoding, append):
    payload = json.dumps([TOOL, path, text, encoding, bool(append)], sort_keys=True,
                         ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_text(path, text, append=False, encoding="utf-8"):
    """Write `text` to `path` if policy and approval allow; otherwise raise and write nothing.

    Returns ``{"status": "written", "path", "operation", "bytes"}``. The store and the session
    are not parameters: a caller that could choose them could approve its own write.
    """
    return _write(path, text, append, encoding)


def _write(path, text, append, encoding, store=None, session_id=None):
    """`write_text`, with the store and session injectable for the deterministic tests only."""
    if not isinstance(text, str):
        raise TypeError("write_text needs text (str)")
    cwd = os.getcwd()
    policy = P.Policy(cwd, temp_roots=(), engaged=True,
                      guard=store.root if store is not None else None)
    target = policy.resolve(path)
    exists = os.path.lexists(target)
    kind = (P.APPEND if append else P.OVERWRITE) if exists else P.CREATE
    op = P.Operation(kind, target, (), exists, "BusinessOps export")
    decision = policy.decide(op)
    if decision == P.PROHIBITED:
        raise WriteBlockedError("BusinessOps refused to %s: %s. No approval can unlock this."
                                % (op.describe(), op.reason))
    if decision == P.APPROVAL:
        store = store or C.Store()
        session = session_id if session_id is not None else os.environ.get(SESSION_VARIABLE)
        bound = C.binding(session, TOOL, policy.cwd, _digest(target, text, encoding, append),
                          [op], origin="engine")
        if not C.valid_session(session):
            raise WriteApprovalRequired(
                op.describe(), operations=[op.binding()],
                detail="Nothing was written. No Claude Code session is identifiable, so no "
                       "approval can be granted for this export.")
        if store.redeem(bound) is None:
            code = store.request(bound)
            raise WriteApprovalRequired(
                op.describe(), code=code, operations=[op.binding()],
                detail="Nothing was written. Ask the user to reply with exactly: approve %s\n"
                       "then run the identical export again. The approval is single-use and "
                       "covers only this path, this content and this operation." % code)
    audit_kind = "create" if not exists else "overwrite"
    E._authorise(audit_kind, target)
    try:
        with open(target, "a" if append else "w", encoding=encoding) as handle:
            handle.write(text)
    finally:
        E._revoke(audit_kind, target)
    return {"status": "written", "path": target, "operation": kind,
            "bytes": len(text.encode(encoding))}
