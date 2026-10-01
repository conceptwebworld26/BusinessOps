"""One value-free discovery operation (ADR-0037 sections C.3-C.6, D.2, E, H; ADR-0038 section 5).

Two Python halves joined by an agent, as for research retrieval (ADR-0015) and blind
recomputation (ADR-0035):

    request_discovery(request)      evaluate; if every static fact permits it, seal one brief
                                    and return it - otherwise return a named refusal
    close_discovery(operation, reply)
                                    consume the sealed brief once, re-check every binding,
                                    parse the agent's `BOPS-CAT/1` lines fail-closed, and
                                    build the catalogue

**Evaluation order** (ADR-0038 section 5), stopping at the first that holds:

    1. the request's shape            request_invalid / privacy_restricted
    2. the interaction class          read -> blocked_prerequisite; write, administrative ->
                                      refused with no approval offered
    3. supported                      connector_not_configured / ambiguous_connector
    4. verified capability            capability_unsupported / binding_mismatch
    5. only then is a brief sealed; the relayed outcome can only reduce what is shown

Static facts come from BusinessOps's own repository alone. **BusinessOps never probes for a
connection**: it learns that a connector is not connected only from the outcome of an operation
it was already permitted to dispatch, and it records nothing about it afterwards.

**No generic execution.** There is no function that takes a tool name, a server or arbitrary
arguments. A brief names one registered tool; its arguments are drawn only from the
declaration's closed object types, its fixed page size and a continuation cursor the same tool
returned in the same operation (ADR-0037 section E.3). No record-read, write or administrative
path exists here at all.

**Nothing from a reply is trusted.** Record lines count only when they carry this operation;
the terminator's echo of connector and tool must be the brief's; the declared count must equal
the lines; each record passes a closed allowlist. Any structural defect refuses the whole reply
with no partial catalogue (ADR-0017). Keys outside the allowlist are dropped and noted by name
only, and a value-shaped identifier, label or key name never enters the result.
"""

import copy
import hashlib
import io
import json
import os
import re
import secrets

from .. import jsonschema_mini
from ..errors import BusinessOpsError
from . import binding as binding_mod
from . import contract
from . import registry as registry_mod

REQUEST_FIELDS = ("capability_placeholder", "connector_id", "interaction", "object_types")
BRIEF_FIELDS = ("protocol", "operation", "connector_id", "capability_placeholder", "server_key",
                "tool_name", "object_types", "calls", "cursor_argument", "max_calls",
                "max_entries", "record_token", "end_token")
_SCHEMAS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "schemas"))
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_BUILD_TOKEN = object()


class CatalogueError(BusinessOpsError):
    """A caller-made result, a modification, or a render of something that is not a result."""


# ---------------------------------------------------------------------------------------------
# The result
# ---------------------------------------------------------------------------------------------

class CatalogueResult(object):
    """One outcome of a discovery request. Built only here; no setter; never evidence."""

    __slots__ = ("_document",)

    def __init__(self, document, _token=None):
        if _token is not _BUILD_TOKEN:
            raise CatalogueError(
                "a CatalogueResult is produced only by the catalogue engine; a caller-made "
                "catalogue, status, entry or outcome is never accepted")
        object.__setattr__(self, "_document", copy.deepcopy(document))

    def __setattr__(self, name, value):
        raise CatalogueError("a CatalogueResult cannot be modified")

    def __delattr__(self, name):
        raise CatalogueError("a CatalogueResult cannot be modified")

    @property
    def status(self):
        return self._document["status"]

    @property
    def reason_code(self):
        return self._document["reason_code"]

    def as_dict(self):
        return copy.deepcopy(self._document)

    def to_json(self, indent=2):
        """Deterministic serialisation in contract key order."""
        return json.dumps(self._document, indent=indent, ensure_ascii=False)


def _file_fallback(placeholder, declaration):
    if declaration is not None:
        return declaration["file_fallback"]
    if placeholder in contract.PLACEHOLDERS:
        return contract.file_fallback(placeholder)
    return contract.GENERIC_FALLBACK


def _document(placeholder, declaration, status, reason_code, message, object_types=(),
              entries=(), conflicts=(), limitations=(), dropped_keys=()):
    entries = list(entries)
    catalogue_id = None
    if entries:
        seed = registry_mod.canonical({
            "connector_id": declaration["connector_id"],
            "capability_placeholder": placeholder,
            "object_types": [o["object_type"] for o in object_types],
            "entries": entries})
        catalogue_id = "cat-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
    return {
        "schema_version": contract.SCHEMA_VERSION,
        "analysis": contract.ANALYSIS,
        "catalogue_id": catalogue_id,
        "connector_id": declaration["connector_id"] if declaration is not None else None,
        "capability_placeholder": placeholder if placeholder in contract.PLACEHOLDERS else None,
        "status": status,
        "reason_code": reason_code,
        "message": message,
        "object_types": list(object_types),
        "entries": entries,
        "conflicts": list(conflicts),
        "limitations": list(limitations),
        "dropped_keys": list(dropped_keys),
        "file_fallback": _file_fallback(placeholder, declaration),
        "trust_statement": contract.TRUST_STATEMENT,
        "use_statement": contract.USE_STATEMENT,
    }


def _refusal(code, placeholder=None, declaration=None, text=None, subjects=()):
    """A named failure with no catalogue. `subjects` are binding or key names, never values."""
    name = declaration["display_name"] if declaration is not None else None
    if text is None:
        if code == contract.CONNECTOR_NOT_CONFIGURED and placeholder in contract.PLACEHOLDERS:
            text = contract.absence_text(placeholder)
        else:
            text = contract.message(code, name)
    limitations = [{"code": code, "subject": s} for s in subjects]
    return CatalogueResult(_document(placeholder, declaration, contract.UNAVAILABLE, code, text,
                                     limitations=limitations), _token=_BUILD_TOKEN)


# ---------------------------------------------------------------------------------------------
# Evaluation (ADR-0038 section 5)
# ---------------------------------------------------------------------------------------------

def _shape_problem(request):
    """The code refusing a malformed request, or `None`. Authority keys outrank everything."""
    if not isinstance(request, dict):
        return contract.REQUEST_INVALID
    unknown = [k for k in request if k not in REQUEST_FIELDS]
    if any(not isinstance(k, str) or k.lower() in contract.AUTHORITY_KEYS for k in unknown):
        return contract.REQUEST_INVALID
    if any(contract.prohibited_key(k) for k in unknown):
        return contract.PRIVACY_RESTRICTED
    if unknown:
        return contract.REQUEST_INVALID
    if request.get("capability_placeholder") not in contract.PLACEHOLDERS:
        return contract.REQUEST_INVALID
    if request.get("interaction", contract.DISCOVERY) not in contract.INTERACTIONS:
        return contract.REQUEST_INVALID
    if "connector_id" in request and not isinstance(request["connector_id"], str):
        return contract.REQUEST_INVALID
    if "object_types" in request:
        object_types = request["object_types"]
        if (not isinstance(object_types, list) or not object_types
                or len(set(map(repr, object_types))) != len(object_types)
                or not all(isinstance(t, str) and contract.IDENTIFIER.match(t)
                           for t in object_types)):
            return contract.REQUEST_INVALID
    return None


def _calls(capability, object_types):
    """The closed argument sets, one per call. Nothing but declared sources ever fills one."""
    names = dict((a["source"], a["name"]) for a in capability["arguments"])
    fixed = dict((a["name"], a["value"]) for a in capability["arguments"]
                 if a["source"] == registry_mod.PAGE_SIZE_ARGUMENT)
    if registry_mod.OBJECT_TYPE_ARGUMENT not in names:
        return [{"arguments": dict(fixed)}]
    calls = []
    for object_type in object_types:
        arguments = dict(fixed)
        arguments[names[registry_mod.OBJECT_TYPE_ARGUMENT]] = object_type
        calls.append({"arguments": arguments})
    return calls


def _plan(declaration, capability, object_types):
    """The brief minus its operation: everything the seal binds, derived from the registry."""
    return {
        "protocol": contract.BRIEF_PROTOCOL,
        "connector_id": declaration["connector_id"],
        "capability_placeholder": declaration["capability_placeholder"],
        "server_key": declaration["server_key"],
        "tool_name": capability["tool_name"],
        "object_types": list(object_types),
        "calls": _calls(capability, object_types),
        "cursor_argument": next((a["name"] for a in capability["arguments"]
                                 if a["source"] == registry_mod.CURSOR_ARGUMENT), None),
        "max_calls": capability["max_calls"],
        "max_entries": capability["max_entries"],
        "record_token": contract.RECORD_TOKEN,
        "end_token": contract.END_TOKEN,
    }


def _evaluate(request, registry, layers):
    """Steps 1-4 of the evaluation order. Returns `(plan, None)` or `(None, refusal)`.

    Pure: reads nothing, writes nothing. `request_discovery()` is the only production caller and
    passes the shipped registry and the repository's layers, read now.
    """
    problem = _shape_problem(request)
    if problem is not None:
        placeholder = request.get("capability_placeholder") if isinstance(request, dict) else None
        return None, _refusal(problem, placeholder)
    placeholder = request["capability_placeholder"]

    # Interaction class, before anything else (ADR-0038 section 5, state 7). A record read is the
    # one class section H names a prerequisite for, so it alone is `blocked_prerequisite`. Write
    # and administrative requests have no path to unblock: they are outside what an M12-B request
    # may ask for, which is section H's `request_invalid`, and the class is carried as the
    # limitation subject so the refusal is never mistaken for a forged request. A value outside
    # the four classes never reaches here: `_shape_problem` refuses it as `request_invalid`.
    interaction = request.get("interaction", contract.DISCOVERY)
    if interaction == contract.READ:
        return None, _refusal(contract.BLOCKED_PREREQUISITE, placeholder, subjects=(interaction,))
    if interaction in (contract.WRITE, contract.ADMINISTRATIVE):
        return None, _refusal(contract.REQUEST_INVALID, placeholder, text=contract.NO_WRITE_PATH,
                              subjects=(interaction,))

    if "connector_id" in request:
        declaration = registry.connector(request["connector_id"])
        if declaration is None or declaration["capability_placeholder"] != placeholder:
            return None, _refusal(contract.REQUEST_INVALID, placeholder)
    else:
        ids = registry.connectors_for(placeholder)
        if not ids:
            return None, _refusal(contract.CONNECTOR_NOT_CONFIGURED, placeholder)
        if len(ids) > 1:
            return None, _refusal(contract.AMBIGUOUS_CONNECTOR, placeholder)
        declaration = registry.connector(ids[0])

    capability = registry.discovery_capability(declaration["connector_id"])
    if capability is None:
        return None, _refusal(contract.CAPABILITY_UNSUPPORTED, placeholder, declaration)
    object_types = list(request.get("object_types") or capability["object_types"])
    if not set(object_types) <= set(capability["object_types"]):
        return None, _refusal(contract.CAPABILITY_UNSUPPORTED, placeholder, declaration)
    plan = _plan(declaration, capability, object_types)
    if len(plan["calls"]) > capability["max_calls"]:
        return None, _refusal(contract.CAPABILITY_UNSUPPORTED, placeholder, declaration)
    mismatches = binding_mod.chain_mismatches(declaration, capability, layers, registry)
    if mismatches:
        return None, _refusal(contract.BINDING_MISMATCH, placeholder, declaration,
                              subjects=mismatches)
    return plan, None


# ---------------------------------------------------------------------------------------------
# The sealed, consumed-once brief (ADR-0037 section E.9, ADR-0035's request pattern)
# ---------------------------------------------------------------------------------------------

def operations_directory():
    """`./.businessops/connectors/operations/`, inside the existing gitignored runtime state."""
    return os.path.join(os.getcwd(), ".businessops", "connectors", "operations")


def _brief_path(operation):
    return os.path.join(operations_directory(), operation + ".json")


def _seal(plan):
    """Mint a cryptographic operation id, write the brief exclusively, return it."""
    brief = dict(plan)
    brief["operation"] = "cop-" + secrets.token_hex(12)
    brief = dict((field, brief[field]) for field in BRIEF_FIELDS)
    directory = operations_directory()
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with io.open(_brief_path(brief["operation"]), "xb") as handle:
        handle.write(registry_mod.canonical(brief).encode("utf-8"))
    return brief


def _consume(operation):
    """Claim and delete the sealed brief. `None` for an unsealed or already-consumed operation."""
    path = _brief_path(operation)
    claimed = path + ".closing"
    try:
        os.rename(path, claimed)
    except OSError:
        return None
    try:
        with io.open(claimed, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, IOError):
        text = None
    finally:
        try:
            os.remove(claimed)
        except OSError:
            pass
    try:
        brief = json.loads(text) if text is not None else {}
    except ValueError:
        return {}
    # An unreadable or reshaped store still consumes the operation, and fails the seal check.
    return brief if isinstance(brief, dict) else {}


def request_discovery(request):
    """Evaluate one discovery request and seal its brief. Returns `(brief, None)` or
    `(None, refusal)`.

    The brief is the only thing passed to the connector agent. With the shipped registry empty,
    every request ends in a named refusal before anything is sealed.
    """
    registry = registry_mod.REGISTRY
    plan, refusal = _evaluate(request, registry, binding_mod.repository_layers(registry))
    if refusal is not None:
        return None, refusal
    return _seal(plan), None


# ---------------------------------------------------------------------------------------------
# The reply (ADR-0037 section D.2)
# ---------------------------------------------------------------------------------------------

def render_reply(operation, connector_id, tool_name, records, outcome=contract.COMPLETED):
    """Produce the line form. Used to build deterministic fixtures, never in production."""
    lines = ["%s %s %s" % (contract.RECORD_TOKEN, operation, json.dumps(r, sort_keys=True))
             for r in records]
    lines.append("%s %s %s %s %s %d" % (contract.END_TOKEN, operation, connector_id, tool_name,
                                        outcome, len(records)))
    return "\n".join(lines)


def _unique_keys(pairs):
    """A JSON object whose keys are distinct. A repeated key is ambiguous, never resolved."""
    record = {}
    for key, value in pairs:
        if key in record:
            raise ValueError("repeated key")
        record[key] = value
    return record


def _no_constant(name):
    """`NaN` and `Infinity` are not JSON; a record carrying one is malformed."""
    raise ValueError("non-JSON constant")


def parse_lines(reply, brief):
    """`(records, outcome)` or `None` for any structural defect. Never repairs, never raises.

    Lines are `BOPS-CAT/1 <operation> {json}` and exactly one
    `BOPS-CAT-END/1 <operation> <connector_id> <tool_name> <outcome> <count>`. Prose around them
    is content. A line for another operation is not ours and is ignored; nothing inside a record
    can create a line, because a record is one line of JSON.
    """
    if isinstance(reply, bytes):
        try:
            reply = reply.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if not isinstance(reply, str):
        return None
    record_prefix = "%s %s " % (contract.RECORD_TOKEN, brief["operation"])
    end_prefix = "%s %s " % (contract.END_TOKEN, brief["operation"])
    records, terminator = [], None
    for line in reply.splitlines():
        line = line.strip()
        if line.startswith(record_prefix):
            try:
                parsed = json.loads(line[len(record_prefix):].strip(),
                                    object_pairs_hook=_unique_keys, parse_constant=_no_constant)
            except ValueError:
                return None
            if not isinstance(parsed, dict):
                return None
            records.append(parsed)
        elif line.startswith(end_prefix):
            if terminator is not None:
                return None
            terminator = line[len(end_prefix):].split()
    if terminator is None or len(terminator) != 4:
        return None
    connector_id, tool_name, outcome, count = terminator
    if connector_id != brief["connector_id"] or tool_name != brief["tool_name"]:
        return None
    if outcome not in contract.RELAY_OUTCOMES or not re.match(r"^(0|[1-9][0-9]*)$", count):
        return None
    if int(count) != len(records) or len(records) > brief["max_entries"]:
        return None
    if outcome != contract.COMPLETED and records:
        return None
    return records, outcome


def _clean_label(value):
    """`(label, note_reason)`: control characters removed; bounded; never value-shaped."""
    label = _CONTROL.sub("", value).strip()
    if not label:
        return None, None
    if len(label) > contract.MAX_LABEL:
        return None, contract.NOTE_LENGTH
    if contract.value_shaped(label):
        return None, contract.NOTE_PRIVACY
    return label, None


def _key_reason(key, kind):
    """Why a key outside the declaration's allowlist is dropped."""
    if not isinstance(key, str):
        return contract.NOTE_NOT_ALLOWLISTED
    if key in contract.ENTRY_FIELDS[kind]:
        return contract.NOTE_NOT_ALLOWLISTED
    if key.lower() in contract.AUTHORITY_KEYS:
        return contract.NOTE_AUTHORITY
    if contract.prohibited_key(key) or contract.value_shaped(key):
        return contract.NOTE_PRIVACY
    return contract.NOTE_NOT_ALLOWLISTED


class _Malformed(Exception):
    pass


def _entry(record, capability, scope):
    """`(entry or None, notes)` for one record; raises `_Malformed` on a structural defect."""
    kind = record.get("kind")
    if kind not in contract.ENTRY_KINDS or kind not in capability["output_fields"]:
        raise _Malformed()
    allowed = capability["output_fields"][kind]
    notes = []
    for key in record:
        if key not in allowed:
            notes.append((contract.safe_key_name(key), _key_reason(key, kind)))
    entry = {"kind": kind, "object": None, "property": None, "related_object": None,
             "label": None, "data_type": None, "required": None, "basis": contract.RELAYED}
    for field in contract.IDENTIFIER_FIELDS[kind]:
        value = record.get(field)
        if not isinstance(value, str) or not contract.IDENTIFIER.match(value):
            raise _Malformed()
        entry[field] = value
    for field in contract.IDENTIFIER_FIELDS[kind]:
        if contract.value_shaped(entry[field]):
            notes.append((field, contract.NOTE_PRIVACY))
            return None, notes
    if "label" in allowed and record.get("label") is not None:
        if not isinstance(record["label"], str):
            raise _Malformed()
        entry["label"], reason = _clean_label(record["label"])
        if reason is not None:
            notes.append(("label", reason))
    if "data_type" in allowed and record.get("data_type") is not None:
        if not isinstance(record["data_type"], str):
            raise _Malformed()
        entry["data_type"] = contract.normalise_data_type(record["data_type"])
    if "required" in allowed and "required" in record:
        if not isinstance(record["required"], bool):
            raise _Malformed()
        entry["required"] = record["required"]
    if entry["object"] not in scope:
        notes.append((entry["kind"], contract.NOTE_OUT_OF_SCOPE))
        return None, notes
    return entry, notes


def _identity(entry):
    return (entry["kind"], entry["object"], entry["property"], entry["related_object"])


def _sort_key(entry):
    return (contract.ENTRY_KINDS.index(entry["kind"]), entry["object"], entry["property"] or "",
            entry["related_object"] or "", registry_mod.canonical(entry))


def _build(records, brief, declaration, capability):
    """The catalogue from accepted records. Deterministic; raises `_Malformed` on any defect."""
    scope = brief["object_types"]
    entries, notes = {}, set()
    for record in records:
        entry, entry_notes = _entry(record, capability, scope)
        notes.update(entry_notes)
        if entry is not None:
            key = registry_mod.canonical(entry)
            # The same entry twice is a relay defect, not an answer, and collapsing it would be
            # a repair (ADR-0017). One identifier with *differing* attributes is different: it
            # is kept and flagged as `metadata_conflict` below (ADR-0037 section H).
            if key in entries:
                raise _Malformed()
            entries[key] = entry
    entries = sorted(entries.values(), key=_sort_key)

    variants = {}
    for entry in entries:
        variants.setdefault(_identity(entry), []).append(entry)
    conflicts = [{"kind": key[0], "object": key[1], "property": key[2],
                  "related_object": key[3], "variants": len(found)}
                 for key, found in sorted(variants.items(),
                                          key=lambda item: _sort_key(item[1][0]))
                 if len(found) > 1]

    described = set(e["object"] for e in entries)
    object_types = [{"object_type": o,
                     "status": contract.DESCRIBED if o in described else contract.UNAVAILABLE}
                    for o in scope]
    dropped = [{"key": key, "reason": reason} for key, reason in sorted(notes)]

    limitations = []
    for item in object_types:
        if item["status"] == contract.UNAVAILABLE and entries:
            limitations.append({"code": contract.EXTERNAL_CONTENT_UNAVAILABLE,
                                "subject": item["object_type"]})
    for conflict in conflicts:
        limitations.append({"code": contract.METADATA_CONFLICT, "subject": conflict["object"]})
    for key in sorted(set(n["key"] for n in dropped if n["reason"] == contract.NOTE_PRIVACY)):
        limitations.append({"code": contract.PRIVACY_RESTRICTED, "subject": key})

    placeholder = declaration["capability_placeholder"]
    if not entries:
        status, code = contract.UNAVAILABLE, contract.INSUFFICIENT_DATA
        limitations.insert(0, {"code": code, "subject": None})
    elif any(o["status"] == contract.UNAVAILABLE for o in object_types):
        status, code = contract.PARTIAL, contract.EXTERNAL_CONTENT_UNAVAILABLE
    elif conflicts:
        status, code = contract.COMPLETE_WITH_LIMITATIONS, contract.METADATA_CONFLICT
    elif any(n["reason"] == contract.NOTE_PRIVACY for n in dropped):
        status, code = contract.COMPLETE_WITH_LIMITATIONS, contract.PRIVACY_RESTRICTED
    else:
        status, code = contract.COMPLETE, None
    text = contract.message(code, declaration["display_name"]) if code else None
    return CatalogueResult(_document(placeholder, declaration, status, code, text, object_types,
                                     entries, conflicts, limitations, dropped),
                           _token=_BUILD_TOKEN)


def _close(operation, reply, registry, layers):
    """Close one operation against a registry and layers. `close_discovery()` is the caller."""
    if not isinstance(operation, str) or not contract.OPERATION_ID.match(operation):
        return _refusal(contract.OPERATION_UNKNOWN)
    brief = _consume(operation)
    if brief is None:
        return _refusal(contract.OPERATION_UNKNOWN)

    # The seal: the stored brief must be exactly what the registry would seal now for the same
    # connector and scope. A tampered store or a registry that changed since is a mismatch.
    declaration = registry.connector(brief.get("connector_id"))
    capability = (registry.discovery_capability(declaration["connector_id"])
                  if declaration is not None else None)
    placeholder = brief.get("capability_placeholder")
    if (declaration is None or capability is None or set(brief) != set(BRIEF_FIELDS)
            or brief.get("operation") != operation
            or not isinstance(brief.get("object_types"), list)
            or registry_mod.canonical(dict((k, v) for k, v in brief.items() if k != "operation"))
            != registry_mod.canonical(_plan(declaration, capability, brief["object_types"]))):
        return _refusal(contract.BINDING_MISMATCH, placeholder, declaration,
                        subjects=(binding_mod.SEALED_OPERATION,))
    mismatches = binding_mod.chain_mismatches(declaration, capability, layers, registry)
    if mismatches:
        return _refusal(contract.BINDING_MISMATCH, placeholder, declaration, subjects=mismatches)

    if reply is None:
        return _refusal(contract.TIMEOUT, placeholder, declaration)
    parsed = parse_lines(reply, brief)
    if parsed is None:
        return _refusal(contract.MALFORMED_RESPONSE, placeholder, declaration)
    records, outcome = parsed
    if outcome != contract.COMPLETED:
        return _refusal(outcome, placeholder, declaration)
    try:
        return _build(records, brief, declaration, capability)
    except _Malformed:
        return _refusal(contract.MALFORMED_RESPONSE, placeholder, declaration)


def close_discovery(operation, reply):
    """Close one sealed operation with the agent's reply text, verbatim. Always a result.

    `reply` is the agent's final text exactly as delivered, or `None` when no reply arrived
    within the bound. The brief is consumed whatever the outcome: there is one dispatch per
    operation and no retry.
    """
    registry = registry_mod.REGISTRY
    return _close(operation, reply, registry, binding_mod.repository_layers(registry))


# ---------------------------------------------------------------------------------------------
# Schema and presentation
# ---------------------------------------------------------------------------------------------

def load_schema():
    with io.open(os.path.join(_SCHEMAS, contract.SCHEMA_NAME), encoding="utf-8") as handle:
        return json.load(handle)


def validate_document(document, schema=None):
    """Schema errors for a serialised result; an empty list means it conforms."""
    return jsonschema_mini.validate(document, schema if schema is not None else load_schema())


def render_resolution(resolution):
    """One resolution as text: the status, registered ids, and any named absence."""
    placeholder = resolution["capability_placeholder"]
    if resolution["status"] == contract.NOT_CONFIGURED:
        absence = resolution["absence"]
        return "%s: %s %s" % (placeholder, absence["text"], absence["file_fallback"])
    return "%s: %s (%s). Registered and declared only; this says nothing about connection, " \
           "authorization or availability." % (placeholder, resolution["status"],
                                              ", ".join(resolution["connectors"]))


def render(result):
    """The result as text for the conversation. Structure only, always with its statements."""
    if not isinstance(result, CatalogueResult):
        raise CatalogueError("only a CatalogueResult built by the catalogue engine renders")
    doc = result.as_dict()
    head = "Connector catalogue - %s" % doc["status"]
    if doc["connector_id"]:
        head += " (%s, %s)" % (doc["connector_id"], doc["capability_placeholder"])
    elif doc["capability_placeholder"]:
        head += " (%s)" % doc["capability_placeholder"]
    lines = [head]
    if doc["message"]:
        lines.append(doc["message"])
    for item in doc["object_types"]:
        lines.append("")
        lines.append("Object type %s: %s" % (item["object_type"], item["status"]))
        for entry in doc["entries"]:
            if entry["object"] != item["object_type"]:
                continue
            label = " - %s" % entry["label"] if entry["label"] else ""
            if entry["kind"] == contract.OBJECT:
                lines.append("  object%s" % label)
            elif entry["kind"] == contract.PROPERTY:
                lines.append("  property %s: %s%s%s" % (
                    entry["property"], entry["data_type"] or "type not stated",
                    ", required" if entry["required"] else "", label))
            else:
                lines.append("  relationship to %s%s" % (entry["related_object"], label))
    if doc["limitations"]:
        lines += ["", "Limitations:"]
        lines += ["  - %s%s" % (l["code"], " (%s)" % l["subject"] if l["subject"] else "")
                  for l in doc["limitations"]]
    if doc["dropped_keys"]:
        lines.append("Dropped keys (names only): %s" % ", ".join(
            "%s [%s]" % (d["key"], d["reason"]) for d in doc["dropped_keys"]))
    if doc["status"] != contract.COMPLETE:
        lines += ["", doc["file_fallback"]]
    lines += ["", doc["trust_statement"], doc["use_statement"]]
    return "\n".join(lines)
