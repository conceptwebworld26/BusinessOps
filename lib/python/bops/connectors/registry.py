"""The fixed connector registry and capability resolution (ADR-0037 sections B.1, C.1, C.2).

**A connector exists for BusinessOps only if it is declared here.** The table is closed, declared
in source, and changed only by a reviewed commit after the Connector Gate (ADR-0037 section B.1
items 1-3, 10). Nothing at runtime adds to it: no argument, configuration key, Business Context
field, relay or model output. The records are deep-frozen and the mappings are read-only
proxies, as in `research/intents.py` (ADR-0021), so there is no write path at all.

**The shipped registry is empty.** ADR-0038's OD-3 admits a connector only when at least one
declared v1 capability has a complete, approved, BusinessOps-owned Connector-Gated chain. No
candidate existed to take through the Connector Gate, so no Gate measurement was taken: the
only vendor server observable in the development session belongs to another plugin and exposes
only authentication tools, and BusinessOps declares no connector server of its own. So `_DECLARATIONS`
holds nothing, every placeholder resolves `not_configured`, and HubSpot stays a designated,
documentation-only future connector (ADR-0038 section 7). M12-B completes this way under
ADR-0037 section L item 1. See `docs/development/2026-09-18-m12-b-connector-registry.md`.

**`configured` is not authorization.** It means *registered and declared*, and asserts nothing
about measurement, grant, reachability, connection or authorization (ADR-0037 section C.2).
Whether a declared capability may actually be used is recomputed per operation by
`binding.chain_mismatches()`; this module never answers that question.

**Identity is exact.** Lookups are byte equality on the declared strings: no prefix, pattern,
alias, case folding, display-name or same-vendor matching (ADR-0037 section B.1).
"""

import collections
import json
import re
import types

from ..errors import BusinessOpsError
from . import contract

#: Fields of one connector declaration and one declared capability. Closed: an unknown field is
#: a defect, and none of them is an enabled flag, authorization, scope, token, header, priority
#: or trust (ADR-0037 section C.1).
CONNECTOR_FIELDS = ("connector_id", "capability_placeholder", "display_name", "server_key",
                    "transport", "file_fallback", "capabilities")
CAPABILITY_FIELDS = ("capability_id", "interaction_class", "namespace", "tool_name",
                     "gate_record", "object_types", "arguments", "output_fields", "max_calls",
                     "max_entries")
ARGUMENT_FIELDS = ("name", "source", "value")
#: Where an argument's value may come from (ADR-0037 section E.3). Nothing else is ever sent.
OBJECT_TYPE_ARGUMENT = "object_type"
PAGE_SIZE_ARGUMENT = "page_size"
CURSOR_ARGUMENT = "cursor"
ARGUMENT_SOURCES = (OBJECT_TYPE_ARGUMENT, PAGE_SIZE_ARGUMENT, CURSOR_ARGUMENT)

#: Transport identity, exactly as `.mcp.json` would declare it: identity only, never `headers`
#: or `env` (ADR-0037 section E.6).
TRANSPORT_FIELDS = {"http": ("type", "url"), "stdio": ("type", "command", "args")}

SERVER_KEY = re.compile(r"^[a-z][a-z0-9-]{1,39}$")
NAMESPACE = re.compile(r"^mcp__[A-Za-z0-9_-]{1,120}$")
TOOL_NAME = re.compile(r"^mcp__[A-Za-z0-9_-]{1,120}__[A-Za-z0-9_-]{1,64}$")
GATE_RECORD_PATH = re.compile(r"^docs/development/\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md$")
#: BusinessOps's own server. It is not a connector and can never be declared as one.
RESERVED_SERVER_KEYS = ("bops-verifier",)
MAX_CALLS = 50
MAX_ENTRIES = 5000
MAX_PAGE_SIZE = 1000


class ConnectorRegistryError(BusinessOpsError):
    """A registry declaration is malformed. Raised when the table is built, never at runtime."""


class ConnectorRequestError(BusinessOpsError):
    """A resolution request is outside the closed vocabulary. Carries the section H code."""

    def __init__(self, message, code=contract.REQUEST_INVALID):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------------------------
# Freezing
# ---------------------------------------------------------------------------------------------

def freeze(value):
    """A deep read-only copy: mappings become proxies, lists become tuples."""
    if isinstance(value, dict):
        return types.MappingProxyType(
            collections.OrderedDict((k, freeze(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    return value


def thaw(value):
    """The plain JSON form of a frozen value, for comparison and serialisation."""
    if isinstance(value, (dict, types.MappingProxyType)):
        return dict((k, thaw(v)) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return [thaw(v) for v in value]
    return value


def canonical(value):
    """The one byte form bindings are compared by."""
    return json.dumps(thaw(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------------------------------------
# Structural validation of a declaration
# ---------------------------------------------------------------------------------------------

def _refuse(message):
    raise ConnectorRegistryError("connector registry refused: %s" % message)


def _exact_fields(record, fields, where):
    if not isinstance(record, dict):
        _refuse("%s must be a record" % where)
    if set(record) != set(fields):
        _refuse("%s must have exactly the fields %s" % (where, ", ".join(fields)))


def _text(value, where, limit=200):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        _refuse("%s must be non-empty text of at most %d characters" % (where, limit))


def _integer(value, where, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        _refuse("%s must be an integer from %d to %d" % (where, low, high))


def _validate_transport(transport, where):
    if not isinstance(transport, dict) or transport.get("type") not in TRANSPORT_FIELDS:
        _refuse("%s must be an http or stdio transport identity" % where)
    _exact_fields(transport, TRANSPORT_FIELDS[transport["type"]], where)
    if transport["type"] == "http":
        url = transport["url"]
        if not isinstance(url, str) or not url.startswith("https://") or len(url) > 200:
            _refuse("%s url must be an https URL" % where)
        if any(part in url for part in ("@", "?", "#")):
            _refuse("%s url must carry no credential, query or fragment" % where)
    else:
        _text(transport["command"], where + ".command")
        args = transport["args"]
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            _refuse("%s args must be a list of strings" % where)


def _validate_arguments(arguments, where):
    if not isinstance(arguments, list):
        _refuse("%s must be a list" % where)
    names, sources = set(), []
    for index, argument in enumerate(arguments):
        at = "%s[%d]" % (where, index)
        _exact_fields(argument, ARGUMENT_FIELDS, at)
        if not isinstance(argument["name"], str) or not contract.IDENTIFIER.match(
                argument["name"]):
            _refuse("%s.name must be an identifier" % at)
        if argument["name"] in names:
            _refuse("%s repeats an argument name" % at)
        names.add(argument["name"])
        if argument["source"] not in ARGUMENT_SOURCES:
            _refuse("%s.source must be one of %s" % (at, ", ".join(ARGUMENT_SOURCES)))
        if argument["source"] == PAGE_SIZE_ARGUMENT:
            _integer(argument["value"], at + ".value", 1, MAX_PAGE_SIZE)
        elif argument["value"] is not None:
            _refuse("%s.value is fixed only for a page size" % at)
        sources.append(argument["source"])
    for source in ARGUMENT_SOURCES:
        if sources.count(source) > 1:
            _refuse("%s declares more than one %s argument" % (where, source))


def _validate_output_fields(output_fields, where):
    if not isinstance(output_fields, dict) or not output_fields:
        _refuse("%s must map entry kinds to field lists" % where)
    for kind, fields in output_fields.items():
        if kind not in contract.ENTRY_KINDS:
            _refuse("%s names an entry kind outside %s" % (where, ", ".join(contract.ENTRY_KINDS)))
        if (not isinstance(fields, list) or len(set(fields)) != len(fields)
                or not set(fields) <= set(contract.ENTRY_FIELDS[kind])):
            _refuse("%s.%s must be distinct fields from %s"
                    % (where, kind, ", ".join(contract.ENTRY_FIELDS[kind])))
        needed = ("kind",) + contract.IDENTIFIER_FIELDS[kind]
        if not set(needed) <= set(fields):
            _refuse("%s.%s must include %s" % (where, kind, ", ".join(needed)))


def _validate_capability(capability, where):
    _exact_fields(capability, CAPABILITY_FIELDS, where)
    if not isinstance(capability["capability_id"], str) or not contract.IDENTIFIER.match(
            capability["capability_id"]):
        _refuse("%s.capability_id must be an identifier" % where)
    if capability["interaction_class"] not in contract.INTERACTIONS:
        _refuse("%s.interaction_class is outside the closed vocabulary" % where)
    if capability["interaction_class"] not in contract.PERMITTED_INTERACTIONS:
        _refuse("%s declares a %s capability; only discovery is declarable in M12-B (read is "
                "M12-C, blocked; write and administrative have no path)"
                % (where, capability["interaction_class"]))
    if not isinstance(capability["namespace"], str) or not NAMESPACE.match(
            capability["namespace"]):
        _refuse("%s.namespace must be an MCP tool namespace" % where)
    if not isinstance(capability["tool_name"], str) or not TOOL_NAME.match(
            capability["tool_name"]):
        _refuse("%s.tool_name must be a fully qualified MCP tool name" % where)
    if not isinstance(capability["gate_record"], str) or not GATE_RECORD_PATH.match(
            capability["gate_record"]):
        _refuse("%s.gate_record must name a dated development record" % where)
    object_types = capability["object_types"]
    if (not isinstance(object_types, list) or not object_types
            or len(set(object_types)) != len(object_types)
            or not all(isinstance(t, str) and contract.IDENTIFIER.match(t)
                       and not contract.value_shaped(t) for t in object_types)):
        _refuse("%s.object_types must be a non-empty list of distinct identifiers" % where)
    _validate_arguments(capability["arguments"], where + ".arguments")
    _validate_output_fields(capability["output_fields"], where + ".output_fields")
    _integer(capability["max_calls"], where + ".max_calls", 1, MAX_CALLS)
    _integer(capability["max_entries"], where + ".max_entries", 1, MAX_ENTRIES)


def validate_declaration(declaration, where="declaration"):
    """Refuse a malformed connector declaration. Structure only: the Gate chain is `binding`'s."""
    _exact_fields(declaration, CONNECTOR_FIELDS, where)
    if not isinstance(declaration["connector_id"], str) or not contract.CONNECTOR_ID.match(
            declaration["connector_id"]):
        _refuse("%s.connector_id must match %s" % (where, contract.CONNECTOR_ID.pattern))
    placeholder = declaration["capability_placeholder"]
    if placeholder not in contract.PLACEHOLDERS:
        _refuse("%s.capability_placeholder is outside the closed vocabulary" % where)
    if placeholder in contract.INELIGIBLE_PLACEHOLDERS:
        _refuse("%s declares %s, which is not eligible in M12" % (where, placeholder))
    _text(declaration["display_name"], where + ".display_name", 64)
    if contract.value_shaped(declaration["display_name"]):
        _refuse("%s.display_name must be a product name" % where)
    server_key = declaration["server_key"]
    if not isinstance(server_key, str) or not SERVER_KEY.match(server_key):
        _refuse("%s.server_key must match %s" % (where, SERVER_KEY.pattern))
    if server_key in RESERVED_SERVER_KEYS:
        _refuse("%s.server_key names BusinessOps's own server, which is not a connector" % where)
    _validate_transport(declaration["transport"], where + ".transport")
    _text(declaration["file_fallback"], where + ".file_fallback", 400)
    capabilities = declaration["capabilities"]
    if not isinstance(capabilities, list) or not capabilities:
        _refuse("%s.capabilities must be a non-empty list" % where)
    seen = set()
    for index, capability in enumerate(capabilities):
        _validate_capability(capability, "%s.capabilities[%d]" % (where, index))
        if capability["capability_id"] in seen:
            _refuse("%s repeats a capability id" % where)
        seen.add(capability["capability_id"])


# ---------------------------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------------------------

class Registry(object):
    """An immutable, validated set of connector declarations, in declaration order."""

    __slots__ = ("_connectors", "_by_placeholder", "_tools")

    def __init__(self, declarations):
        if not isinstance(declarations, (list, tuple)):
            _refuse("the registry must be a sequence of declarations")
        connectors = collections.OrderedDict()
        servers, tools = set(), collections.OrderedDict()
        for index, declaration in enumerate(declarations):
            where = "declarations[%d]" % index
            validate_declaration(declaration, where)
            if declaration["connector_id"] in connectors:
                _refuse("%s repeats connector id %r" % (where, declaration["connector_id"]))
            if declaration["server_key"] in servers:
                _refuse("%s repeats a server key; one server serves one connector" % where)
            servers.add(declaration["server_key"])
            for capability in declaration["capabilities"]:
                if capability["tool_name"] in tools:
                    _refuse("%s repeats a tool name already declared" % where)
                tools[capability["tool_name"]] = declaration["connector_id"]
            connectors[declaration["connector_id"]] = freeze(declaration)
        by_placeholder = collections.OrderedDict((p, ()) for p in contract.PLACEHOLDERS)
        for connector_id, declaration in connectors.items():
            placeholder = declaration["capability_placeholder"]
            by_placeholder[placeholder] = by_placeholder[placeholder] + (connector_id,)
        object.__setattr__(self, "_connectors", types.MappingProxyType(connectors))
        object.__setattr__(self, "_by_placeholder", types.MappingProxyType(by_placeholder))
        object.__setattr__(self, "_tools", types.MappingProxyType(tools))

    def __setattr__(self, name, value):
        raise ConnectorRegistryError("the connector registry cannot be modified")

    def __delattr__(self, name):
        raise ConnectorRegistryError("the connector registry cannot be modified")

    @property
    def connectors(self):
        """Read-only mapping of connector id to its frozen declaration."""
        return self._connectors

    def connector(self, connector_id):
        """The frozen declaration for an exact id, or `None`. No near-miss ever matches."""
        if not isinstance(connector_id, str):
            return None
        return self._connectors.get(connector_id)

    def connectors_for(self, placeholder):
        """Registered connector ids for one placeholder, in registry order."""
        return self._by_placeholder.get(placeholder, ())

    def discovery_tools(self):
        """Every declared discovery tool name, in declaration order."""
        return tuple(name for name, connector_id in self._tools.items()
                     if self._capability_of(connector_id, name)["interaction_class"]
                     == contract.DISCOVERY)

    def server_keys(self):
        """Every declared server key, in declaration order."""
        return tuple(d["server_key"] for d in self._connectors.values())

    def _capability_of(self, connector_id, tool_name):
        for capability in self._connectors[connector_id]["capabilities"]:
            if capability["tool_name"] == tool_name:
                return capability
        return None

    def discovery_capability(self, connector_id):
        """A connector's first declared discovery capability, or `None`."""
        declaration = self.connector(connector_id)
        if declaration is None:
            return None
        for capability in declaration["capabilities"]:
            if capability["interaction_class"] == contract.DISCOVERY:
                return capability
        return None

    def resolve(self, placeholder):
        """Deterministic, local capability resolution (ADR-0037 section C.2)."""
        if not isinstance(placeholder, str) or placeholder not in contract.PLACEHOLDERS:
            raise ConnectorRequestError(
                "the capability must be one of %s; nothing outside that vocabulary resolves"
                % ", ".join(contract.PLACEHOLDERS))
        ids = self.connectors_for(placeholder)
        if not ids:
            status = contract.NOT_CONFIGURED
        elif len(ids) == 1:
            status = contract.CONFIGURED
        else:
            status = contract.AMBIGUOUS
        absence = None
        if status == contract.NOT_CONFIGURED:
            absence = {"code": contract.CONNECTOR_NOT_CONFIGURED,
                       "text": contract.absence_text(placeholder),
                       "file_fallback": contract.file_fallback(placeholder)}
        return {"schema_version": contract.SCHEMA_VERSION,
                "analysis": contract.RESOLUTION_ANALYSIS,
                "capability_placeholder": placeholder,
                "status": status,
                "connectors": list(ids),
                "absence": absence}


#: The shipped declarations. Empty: no connector has a complete, approved Connector-Gated
#: discovery chain (OD-3), so none is admitted. A declaration is added only by a reviewed commit
#: that also adds its approved Gate record, its `.mcp.json` server entry and the agent grant, all
#: agreeing exactly - the static suite refuses anything less.
_DECLARATIONS = ()

#: The registry every runtime path uses. No public entry point - `resolve()`,
#: `request_discovery()`, `close_discovery()` - accepts another; the checks in `binding` take one
#: only so the static suite can prove what they refuse.
REGISTRY = Registry(_DECLARATIONS)


def resolve(placeholder):
    """Resolve one capability placeholder against the shipped registry."""
    return REGISTRY.resolve(placeholder)


def resolve_all():
    """Resolution for every placeholder, in vocabulary order: the capability map."""
    return [REGISTRY.resolve(placeholder) for placeholder in contract.PLACEHOLDERS]
