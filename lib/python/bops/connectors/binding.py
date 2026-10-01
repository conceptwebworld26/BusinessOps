"""Declaration, measurement and grant must agree exactly (ADR-0037 sections B.1, B.2, B.4, D.4).

Three layers, each necessary and none sufficient:

    A  registry declaration   `registry.py`, plus the server entry BusinessOps ships in `.mcp.json`
    B  Connector Gate record  a dated development record holding one fenced `bops-connector-gate`
                              block, approved by the owner
    C  runtime grant          the `tools` field of `agents/bops-data-profiler.md`

`chain_mismatches()` compares them for one declared capability and names every binding that
differs. An empty result is the only thing that lets an operation be sealed, and it is a
condition recomputed per operation - never an object, flag or token (ADR-0037 section B.2).
`admission_findings()` applies ADR-0038's OD-3 to the whole shipped registry for the static
suite.

**What this module reads.** Only BusinessOps's own repository files, located from this file's
own path: `.mcp.json`, the one agent definition and the Gate records the registry names. Never
the working directory's configuration, the platform's configuration, a credential store,
`~/.claude*`, `.env*` or the environment (ADR-0037 sections B.1 item 10, E.6). It never
enumerates session servers or tools, because Python cannot see them and the model's report of
them is not authority.

**Comparison is byte equality** of the canonical JSON form. Nothing is normalised, case-folded,
trimmed, prefix-matched or repaired to make the layers agree.
"""

import collections
import io
import json
import os
import re

from ..errors import BusinessOpsError
from . import contract
from . import registry as registry_mod

#: The repository root, from this file's own location: lib/python/bops/connectors/binding.py.
PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "..", "..", "..", ".."))
MCP_JSON = ".mcp.json"
AGENT = os.path.join("agents", "bops-data-profiler.md")
VERIFIER_SERVER = "bops-verifier"

#: The fenced block language tag that marks the one machine-readable Gate record in a record.
GATE_FENCE = "bops-connector-gate"
GATE_FIELDS = ("protocol", "connector_id", "capability_placeholder", "server_key", "transport",
               "namespace", "tool_name", "interaction_class", "classification_reasons",
               "object_types", "arguments", "output_fields", "server_instructions",
               "value_free_property", "measured_on", "platform_version", "owner_acceptance")
VALUE_FREE_FIELDS = ("demonstrated", "synthetic_data", "method")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FENCED = re.compile(r"^```%s[ \t]*\r?\n(.*?)\r?\n```[ \t]*$" % re.escape(GATE_FENCE),
                     re.M | re.S)

# -- the binding names a mismatch reports (ADR-0037 section B.2's list, plus missing layers) --

GATE_RECORD = "gate_record"
CONNECTOR = "connector"
PLACEHOLDER = "placeholder"
SERVER_IDENTITY = "server_identity"
TRANSPORT = "transport"
MCP_SERVER = "mcp_server"
NAMESPACE = "namespace"
TOOL_NAME = "tool_name"
INTERACTION_CLASS = "interaction_class"
ARGUMENT_SHAPE = "argument_shape"
OUTPUT_SHAPE = "output_shape"
VALUE_FREE_PROPERTY = "value_free_property"
GRANT = "grant"
SEALED_OPERATION = "sealed_operation"
BINDINGS = (GATE_RECORD, CONNECTOR, PLACEHOLDER, SERVER_IDENTITY, TRANSPORT, MCP_SERVER,
            NAMESPACE, TOOL_NAME, INTERACTION_CLASS, ARGUMENT_SHAPE, OUTPUT_SHAPE,
            VALUE_FREE_PROPERTY, GRANT, SEALED_OPERATION)


class GateRecordError(BusinessOpsError):
    """A Connector Gate record is absent, ambiguous or malformed. Never repaired."""


#: What the repository declares, read fresh for every operation. `grant` is `None` when the
#: agent is not built; `gate_records` maps each path the registry names to its parsed record,
#: or to `None` when that record is absent or malformed.
Layers = collections.namedtuple("Layers", "mcp_servers grant gate_records")


# ---------------------------------------------------------------------------------------------
# Layer B: the Connector Gate record
# ---------------------------------------------------------------------------------------------

def _gate_refuse(message):
    raise GateRecordError("Connector Gate record refused: %s" % message)


def parse_gate_record(text):
    """Parse the one `bops-connector-gate` block of a development record. Closed; never repaired.

    The block is the measured binding of ADR-0037 section B.1 item 7: connector, server and
    transport identity, the platform-derived namespace and exact tool name as observed, the
    classification with its reasons, argument and output shape, the server's instructions
    verbatim, and the value-free property as demonstrated on synthetic data.
    """
    if not isinstance(text, str):
        _gate_refuse("the record must be text")
    blocks = _FENCED.findall(text)
    if len(blocks) != 1:
        _gate_refuse("the record must hold exactly one %s block; it holds %d"
                     % (GATE_FENCE, len(blocks)))
    try:
        record = json.loads(blocks[0])
    except ValueError:
        _gate_refuse("the %s block is not one JSON object" % GATE_FENCE)
    if not isinstance(record, dict) or set(record) != set(GATE_FIELDS):
        _gate_refuse("the block must have exactly the fields %s" % ", ".join(GATE_FIELDS))
    if record["protocol"] != contract.GATE_PROTOCOL:
        _gate_refuse("protocol must be %s" % contract.GATE_PROTOCOL)
    reasons = record["classification_reasons"]
    if (not isinstance(reasons, list) or not reasons
            or not all(isinstance(r, str) and r.strip() for r in reasons)):
        _gate_refuse("classification_reasons must be a non-empty list of text")
    instructions = record["server_instructions"]
    if instructions is not None and not isinstance(instructions, str):
        _gate_refuse("server_instructions must be the verbatim text, or null when none")
    proof = record["value_free_property"]
    if not isinstance(proof, dict) or set(proof) != set(VALUE_FREE_FIELDS):
        _gate_refuse("value_free_property must have exactly %s" % ", ".join(VALUE_FREE_FIELDS))
    if not isinstance(proof["method"], str) or not proof["method"].strip():
        _gate_refuse("value_free_property.method must describe the measurement")
    for field in ("measured_on", "owner_acceptance"):
        if not isinstance(record[field], str) or not _DATE.match(record[field]):
            _gate_refuse("%s must be an ISO date" % field)
    if not isinstance(record["platform_version"], str) or not record["platform_version"].strip():
        _gate_refuse("platform_version must name the measured platform version")
    return record


def load_gate_record(relative_path):
    """Read one Gate record from BusinessOps's own `docs/development/`, or refuse."""
    if not isinstance(relative_path, str) or not registry_mod.GATE_RECORD_PATH.match(
            relative_path):
        _gate_refuse("a Gate record is a dated file under docs/development/")
    path = os.path.realpath(os.path.join(PLUGIN_ROOT, *relative_path.split("/")))
    root = os.path.realpath(os.path.join(PLUGIN_ROOT, "docs", "development"))
    if os.path.dirname(path) != root or not os.path.isfile(path):
        _gate_refuse("the named Gate record does not exist in docs/development/")
    with io.open(path, encoding="utf-8") as handle:
        return parse_gate_record(handle.read())


# ---------------------------------------------------------------------------------------------
# Layers A and C as the repository ships them
# ---------------------------------------------------------------------------------------------

def read_mcp_servers():
    """BusinessOps's own `.mcp.json` server entries, verbatim. Empty when unreadable."""
    try:
        with io.open(os.path.join(PLUGIN_ROOT, MCP_JSON), encoding="utf-8") as handle:
            servers = json.load(handle).get("mcpServers")
    except (OSError, IOError, ValueError, AttributeError):
        return {}
    return servers if isinstance(servers, dict) else {}


def parse_grant(text):
    """The exact tool names an agent definition's `tools` field lists, in order.

    `None` when the frontmatter has no `tools` field: an absent field inherits every tool
    (ADR-0037 section D.1), which is never a grant this layer accepts.
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        return None
    field = re.search(r"^tools:[ \t]*(.*)$", match.group(1), re.M)
    if not field:
        return None
    return tuple(name.strip() for name in field.group(1).split(",") if name.strip())


def read_agent_grant():
    """The connector agent's grant, or `None` when the agent is not built (ADR-0037 D.1)."""
    path = os.path.join(PLUGIN_ROOT, AGENT)
    if not os.path.isfile(path):
        return None
    with io.open(path, encoding="utf-8") as handle:
        grant = parse_grant(handle.read())
    return grant if grant else None


def repository_layers(registry=None):
    """Layers A (server entries) and C, and every Gate record the registry names, read now."""
    registry = registry if registry is not None else registry_mod.REGISTRY
    gate_records = collections.OrderedDict()
    for declaration in registry.connectors.values():
        for capability in declaration["capabilities"]:
            path = capability["gate_record"]
            try:
                gate_records[path] = load_gate_record(path)
            except GateRecordError:
                gate_records[path] = None
    return Layers(read_mcp_servers(), read_agent_grant(), gate_records)


# ---------------------------------------------------------------------------------------------
# Agreement
# ---------------------------------------------------------------------------------------------

def _differs(left, right):
    return registry_mod.canonical(left) != registry_mod.canonical(right)


def chain_mismatches(declaration, capability, layers, registry=None):
    """Every binding on which A, B and C disagree for one declared capability, in fixed order.

    Empty means the chain is complete and agrees exactly, for this operation only. A missing
    layer is itself a mismatch: a declaration with no Gate record, a Gate record with no grant,
    or a grant with neither never authorizes use (ADR-0037 section B.2).
    """
    registry = registry if registry is not None else registry_mod.REGISTRY
    found = set()
    if capability["interaction_class"] != contract.DISCOVERY:
        found.add(INTERACTION_CLASS)

    gate = layers.gate_records.get(capability["gate_record"])
    if not isinstance(gate, dict):
        found.add(GATE_RECORD)
    else:
        for binding, measured, declared in (
                (CONNECTOR, gate["connector_id"], declaration["connector_id"]),
                (PLACEHOLDER, gate["capability_placeholder"],
                 declaration["capability_placeholder"]),
                (SERVER_IDENTITY, gate["server_key"], declaration["server_key"]),
                (TRANSPORT, gate["transport"], declaration["transport"]),
                (NAMESPACE, gate["namespace"], capability["namespace"]),
                (TOOL_NAME, gate["tool_name"], capability["tool_name"]),
                (INTERACTION_CLASS, gate["interaction_class"], contract.DISCOVERY),
                (ARGUMENT_SHAPE, [gate["arguments"], gate["object_types"]],
                 [capability["arguments"], capability["object_types"]]),
                (OUTPUT_SHAPE, gate["output_fields"], capability["output_fields"])):
            if _differs(measured, declared):
                found.add(binding)
        proof = gate["value_free_property"]
        if proof.get("demonstrated") is not True or proof.get("synthetic_data") is not True:
            found.add(VALUE_FREE_PROPERTY)

    entry = layers.mcp_servers.get(declaration["server_key"])
    if not isinstance(entry, dict):
        found.add(MCP_SERVER)
    elif _differs(entry, declaration["transport"]):
        # Byte-identical identity only: an entry that adds `headers`, `env` or anything else
        # differs, and is refused rather than trimmed (ADR-0037 section E.6).
        found.add(TRANSPORT)

    grant = layers.grant
    if (grant is None or capability["tool_name"] not in grant
            or len(set(grant)) != len(grant)
            or set(grant) != set(registry.discovery_tools())):
        found.add(GRANT)
    return tuple(b for b in BINDINGS if b in found)


def admission_findings(registry=None, layers=None):
    """Every way the shipped repository breaks OD-3 or the section D.1 build rule. Empty = sound.

    Checked by the static suite, never at import: a broken chain disables its connector, it
    never breaks BusinessOps (ADR-0038 section 1).
    """
    registry = registry if registry is not None else registry_mod.REGISTRY
    layers = layers if layers is not None else repository_layers(registry)
    findings = []
    complete_tools = []
    for connector_id, declaration in registry.connectors.items():
        admitted = False
        for capability in declaration["capabilities"]:
            mismatches = chain_mismatches(declaration, capability, layers, registry)
            if mismatches:
                findings.append("%s/%s: %s" % (connector_id, capability["capability_id"],
                                               ", ".join(mismatches)))
            else:
                admitted = True
                complete_tools.append(capability["tool_name"])
        if not admitted:
            findings.append("%s: no declared capability has a complete Connector-Gated "
                            "discovery chain, so it may not be registered (OD-3)" % connector_id)
    expected_servers = set((VERIFIER_SERVER,)) | set(registry.server_keys())
    for server in sorted(set(layers.mcp_servers) - expected_servers):
        findings.append(".mcp.json declares %r, which is neither bops-verifier nor a registered "
                        "connector server" % server)
    for server in sorted(expected_servers - set(layers.mcp_servers)):
        findings.append(".mcp.json lacks the declared server %r" % server)
    if not complete_tools and layers.grant is not None:
        findings.append("the connector agent exists but no capability has a complete chain "
                        "(ADR-0037 section D.1: the agent is built only on a complete chain)")
    if complete_tools and (layers.grant is None or set(layers.grant) != set(complete_tools)):
        findings.append("the connector agent's grant differs from the complete discovery tools")
    return findings
