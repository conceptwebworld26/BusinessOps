"""Write-approval capabilities: requested by the guard, granted only by the user (ADR-0051).

This is the ADR-0010 approval model applied to filesystem writes, in the same shape as the
disclosure gate's `research.contract.Approval`: an approval is not a flag meaning "the user
said yes", it records *which* operation, is single-use, and is spent when used. It differs in
one respect only: a write approval must survive between processes (the hook that asks, the
prompt that grants and the hook that redeems are three separate processes), so it is a record
in a store rather than an object in memory.

The lifecycle, and who may drive each step:

``request``  (the pre-execution hook, or the engine's export API)
    A consequential operation arrives without a capability. A pending record is written with
    the operation's **binding** - the session, the tool, the working directory, the digest of
    the exact tool input, and every operation's kind, canonical target, sources and whether
    the target existed - and a fresh random code, `BOPS-W-XXXXXXXX`. An identical request
    reuses its unexpired code instead of minting another.

``grant``  (only the `UserPromptSubmit` hook, from a prompt the user typed)
    `approve BOPS-W-XXXXXXXX` in the user's own prompt moves that pending record to granted,
    for the same session only, with a ten-minute expiry. The fingerprint is recomputed from the
    stored binding and the description the user is shown is rebuilt from it, so what the user
    reads is what the capability authorises.

``redeem``  (the pre-execution hook, or the export API, immediately before the write)
    The binding of the call about to run is computed afresh and its fingerprint compared.
    Any material change - another target, another operation kind, another command, other
    content, a target that now exists or no longer does - is a different fingerprint and
    redeems nothing. A match is claimed by an atomic rename into `consumed/`, so a capability
    authorises one execution only.

Nothing a tool call supplies can mint or widen a capability: the store lives under
`~/.claude/businessops/guard/`, which the classifier refuses to let any tool call touch, and the
only granting path reads the user's prompt.

Standard library only.
"""

import hashlib
import json
import os
import re
import secrets
import time

from . import policy as P

SCHEMA = "bops.write-approval/1"
PENDING_TTL_SECONDS = 30 * 60
GRANT_TTL_SECONDS = 10 * 60
CONSUMED_RETENTION_SECONDS = 24 * 60 * 60
CODE_PREFIX = "BOPS-W-"
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_PATTERN = re.compile(r"BOPS-W-[A-Z0-9]{8}")
_CODE_EXACT = re.compile(r"BOPS-W-[A-Z0-9]{8}$")
APPROVAL_PHRASE = re.compile(r"(?<![A-Za-z])approve\s+(BOPS-W-[A-Za-z0-9]{8})(?![A-Za-z0-9])",
                             re.IGNORECASE)
_DIRECTORIES = ("pending", "granted", "consumed", "sessions")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def binding(session_id, tool, cwd, digest, operations, origin="hook"):
    """What an approval is bound to. `operations` are `policy.Operation`s or their bindings."""
    ops = [op.binding() if isinstance(op, P.Operation) else dict(op) for op in operations]
    return {"session_id": session_id, "origin": origin, "tool": tool, "cwd": cwd,
            "input_sha256": digest, "operations": ops}


def fingerprint(bound):
    return hashlib.sha256(_canonical(bound).encode("utf-8")).hexdigest()


def describe(bound):
    """The user-facing lines for a binding, rebuilt from its fields and nothing else."""
    lines = []
    for item in bound.get("operations", []):
        op = P.Operation(item.get("kind"), item.get("target"), item.get("sources") or (),
                         item.get("exists"))
        lines.append(op.describe())
    return lines


def new_code():
    return CODE_PREFIX + "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))


def approval_codes(prompt):
    """The codes a prompt explicitly approves, upper-cased, in order, without duplicates."""
    seen = []
    for match in APPROVAL_PHRASE.finditer(prompt or ""):
        code = match.group(1).upper()
        if code not in seen:
            seen.append(code)
    return seen


def _session_key(session_id):
    return hashlib.sha256(str(session_id).encode("utf-8")).hexdigest()[:32]


def valid_session(session_id):
    return isinstance(session_id, str) and 0 < len(session_id) <= 256


class Store:
    """The approval store at `root` (default `~/.claude/businessops/guard/`)."""

    def __init__(self, root=None):
        self.root = root or P.guard_root()

    # -- files -----------------------------------------------------------------------------

    def _dir(self, name, create=True):
        path = os.path.join(self.root, name)
        if create and not os.path.isdir(path):
            os.makedirs(path, mode=0o700, exist_ok=True)
        return path

    def _path(self, state, code):
        if not _CODE_EXACT.match(code or ""):
            raise ValueError("not an approval code: %r" % code)
        return os.path.join(self._dir(state), code + ".json")

    @staticmethod
    def _write_new(path, record):
        with open(path, "x", encoding="utf-8") as handle:
            handle.write(_canonical(record))

    @staticmethod
    def _read(path):
        try:
            with open(path, encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError):
            return None
        return record if isinstance(record, dict) and record.get("schema") == SCHEMA else None

    def _records(self, state):
        directory = self._dir(state, create=False)
        if not os.path.isdir(directory):
            return
        for name in sorted(os.listdir(directory)):
            if name.endswith(".json") and _CODE_EXACT.match(name[:-5]):
                path = os.path.join(directory, name)
                record = self._read(path)
                if record is not None and record.get("code") == name[:-5]:
                    yield path, record

    def _sweep(self, now):
        for state, limit in (("pending", 0), ("granted", 0), ("consumed", CONSUMED_RETENTION_SECONDS)):
            for path, record in list(self._records(state)):
                if now > int(record.get("expires_at", 0)) + limit:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    # -- lifecycle -------------------------------------------------------------------------

    def request(self, bound, now=None):
        """A pending approval for `bound`. Returns its code, reusing an identical request's."""
        now = int(now if now is not None else time.time())
        self._sweep(now)
        print_ = fingerprint(bound)
        for _path, record in self._records("pending"):
            if record.get("fingerprint") == print_ and now <= int(record.get("expires_at", 0)):
                return record["code"]
        for _attempt in range(8):
            code = new_code()
            record = {"schema": SCHEMA, "code": code, "state": "pending", "binding": bound,
                      "fingerprint": print_, "created_at": now,
                      "expires_at": now + PENDING_TTL_SECONDS}
            try:
                self._write_new(self._path("pending", code), record)
                return code
            except FileExistsError:
                continue
        raise RuntimeError("could not allocate an approval code")

    def grant(self, code, session_id, now=None):
        """Grant a pending approval from the user's prompt. Returns (record, None) or (None, why)."""
        now = int(now if now is not None else time.time())
        if not _CODE_EXACT.match(code or ""):
            return None, "not an approval code"
        if not valid_session(session_id):
            return None, "no session"
        pending = os.path.join(self._dir("pending", create=False), code + ".json")
        record = self._read(pending)
        if record is None or record.get("code") != code:
            granted = self._read(os.path.join(self._dir("granted", create=False), code + ".json"))
            if granted is not None and granted.get("binding", {}).get("session_id") == session_id:
                return granted, None          # already granted: approving twice is harmless
            return None, "no pending request with this code"
        bound = record.get("binding") or {}
        if bound.get("session_id") != session_id:
            return None, "the request belongs to another session"
        if now > int(record.get("expires_at", 0)):
            return None, "the request has expired"
        granted = {"schema": SCHEMA, "code": code, "state": "granted", "binding": bound,
                   "fingerprint": fingerprint(bound), "created_at": record.get("created_at"),
                   "granted_at": now, "expires_at": now + GRANT_TTL_SECONDS}
        try:
            self._write_new(self._path("granted", code), granted)
        except FileExistsError:
            return None, "already granted"
        try:
            os.remove(pending)
        except OSError:
            pass
        return granted, None

    def redeem(self, bound, now=None):
        """Consume the granted capability exactly matching `bound`. Returns the record or None."""
        now = int(now if now is not None else time.time())
        print_ = fingerprint(bound)
        for path, record in list(self._records("granted")):
            stored = record.get("binding") or {}
            if fingerprint(stored) != print_ or record.get("fingerprint") != print_:
                continue
            if now > int(record.get("expires_at", 0)):
                continue
            claimed = self._path("consumed", record["code"])
            try:
                os.rename(path, claimed)              # atomic: one redemption wins
            except OSError:
                continue
            record["state"] = "consumed"
            record["consumed_at"] = now
            return record
        return None

    # -- engagement ------------------------------------------------------------------------

    def engage(self, session_id, reason, now=None):
        """Record that this session has used BusinessOps. Permanent for the session."""
        if not valid_session(session_id):
            return False
        path = os.path.join(self._dir("sessions"), _session_key(session_id) + ".json")
        if os.path.exists(path):
            return True
        record = {"schema": SCHEMA, "session_id": session_id, "reason": reason,
                  "engaged_at": int(now if now is not None else time.time())}
        try:
            self._write_new(path, record)
        except FileExistsError:
            pass
        return True

    def engaged(self, session_id):
        if not valid_session(session_id):
            return False
        return os.path.exists(os.path.join(self._dir("sessions", create=False),
                                           _session_key(session_id) + ".json"))
