# -*- coding: utf-8 -*-
"""Synthetic enforcement fixture only - non-production, and **not a connector measurement.**

The shipped registry is empty (ADR-0038 OD-3: no connector has a complete, approved
Connector-Gated discovery chain). To prove that the registry, the binding checks and the
catalogue parser refuse what they must - and accept only what a complete chain would permit -
the tests build a *synthetic* connector in memory:

* its identity says so: `synthetic-crm`, server `bops-synthetic-crm`, display name
  `Synthetic CRM`;
* its URL is under the reserved `.invalid` top-level domain (RFC 2606), which never resolves;
* its "Gate record" is a Python dict handed to the checks directly. No Gate record file is
  written, its path names a date in 2099, and nothing here is, or may be presented as, a Connector
  Gate measurement or evidence that any real server behaves this way.

Nothing in this module reaches `lib/python/bops/connectors/registry.py`'s `_DECLARATIONS`, the
repository's `.mcp.json` or any agent definition.
"""

import contextlib
import copy
import os
import shutil
import tempfile
from unittest import mock

from bops.connectors import binding as binding_mod
from bops.connectors import catalogue as catalogue_mod
from bops.connectors import registry as registry_mod

CONNECTOR_ID = "synthetic-crm"
SERVER_KEY = "bops-synthetic-crm"
NAMESPACE = "mcp__plugin_businessops_bops-synthetic-crm"
TOOL_NAME = NAMESPACE + "__describe_schema"
GATE_PATH = "docs/development/2099-01-01-synthetic-fixture-not-a-gate-record.md"
TRANSPORT = {"type": "http", "url": "https://synthetic.invalid/mcp"}
VERIFIER_ENTRY = {"type": "stdio", "command": "sh",
                  "args": ["${CLAUDE_PLUGIN_ROOT}/lib/bops_run.sh", "--verifier"]}
OBJECT_TYPES = ["contacts", "companies", "deals"]


def declaration(connector_id=CONNECTOR_ID, server_key=SERVER_KEY, tool_name=TOOL_NAME,
                namespace=NAMESPACE, placeholder="~~crm", gate_path=GATE_PATH):
    """One synthetic connector declaration with one discovery capability."""
    return {
        "connector_id": connector_id,
        "capability_placeholder": placeholder,
        "display_name": "Synthetic CRM",
        "server_key": server_key,
        "transport": dict(TRANSPORT),
        "file_fallback": "Export the synthetic CRM data to CSV or Excel and supply the file.",
        "capabilities": [{
            "capability_id": "schema_discovery",
            "interaction_class": "discovery",
            "namespace": namespace,
            "tool_name": tool_name,
            "gate_record": gate_path,
            "object_types": list(OBJECT_TYPES),
            "arguments": [
                {"name": "objectType", "source": "object_type", "value": None},
                {"name": "limit", "source": "page_size", "value": 100},
                {"name": "after", "source": "cursor", "value": None}],
            "output_fields": {
                "object": ["kind", "object", "label"],
                "property": ["kind", "object", "property", "label", "data_type", "required"],
                "relationship": ["kind", "object", "related_object", "label"]},
            "max_calls": 10,
            "max_entries": 500,
        }],
    }


def gate_record(decl=None):
    """A synthetic dict in the Gate record's closed shape, agreeing with `decl` exactly."""
    decl = decl or declaration()
    capability = decl["capabilities"][0]
    return {
        "protocol": "bops.connector.gate/1",
        "connector_id": decl["connector_id"],
        "capability_placeholder": decl["capability_placeholder"],
        "server_key": decl["server_key"],
        "transport": copy.deepcopy(decl["transport"]),
        "namespace": capability["namespace"],
        "tool_name": capability["tool_name"],
        "interaction_class": "discovery",
        "classification_reasons": ["SYNTHETIC FIXTURE - not a measurement"],
        "object_types": list(capability["object_types"]),
        "arguments": copy.deepcopy(capability["arguments"]),
        "output_fields": copy.deepcopy(capability["output_fields"]),
        "server_instructions": None,
        "value_free_property": {"demonstrated": True, "synthetic_data": True,
                                "method": "SYNTHETIC FIXTURE - not a measurement"},
        "measured_on": "2099-01-01",
        "platform_version": "synthetic-fixture",
        "owner_acceptance": "2099-01-01",
    }


def gate_text(record):
    """A synthetic record body holding one fenced block, for the parser tests only."""
    import json
    return ("# SYNTHETIC FIXTURE - not a Connector Gate record\n\n```bops-connector-gate\n%s\n```\n"
            % json.dumps(record, indent=2))


def layers(decls=None, grant=None, gates=None, servers=None):
    """Complete, agreeing synthetic layers for `decls` unless a layer is overridden."""
    decls = decls if decls is not None else [declaration()]
    if servers is None:
        servers = {"bops-verifier": dict(VERIFIER_ENTRY)}
        for decl in decls:
            servers[decl["server_key"]] = copy.deepcopy(decl["transport"])
    if grant is None:
        grant = tuple(c["tool_name"] for d in decls for c in d["capabilities"])
    if gates is None:
        gates = dict((c["gate_record"], gate_record(d)) for d in decls for c in d["capabilities"])
    return binding_mod.Layers(servers, grant, gates)


def registry(decls=None):
    return registry_mod.Registry(decls if decls is not None else [declaration()])


@contextlib.contextmanager
def installed(decls=None, layer=None):
    """Run the public API against a synthetic registry and layers, in a temporary directory.

    Patches the two module globals the public functions read at call time; the shipped registry
    and the repository are untouched, and both are restored on exit.
    """
    reg = registry(decls)
    lay = layer if layer is not None else layers(decls)
    previous = os.getcwd()
    directory = tempfile.mkdtemp(prefix="bops-m12b-")
    os.chdir(directory)
    try:
        with mock.patch.object(registry_mod, "REGISTRY", reg), \
                mock.patch.object(binding_mod, "repository_layers",
                                  lambda registry=None: lay):
            yield reg, lay, directory
    finally:
        os.chdir(previous)
        shutil.rmtree(directory, ignore_errors=True)


def obj(name, label=None):
    return {"kind": "object", "object": name, "label": label or name.title()}


def prop(obj_name, name, data_type="string", required=False, label=None):
    return {"kind": "property", "object": obj_name, "property": name,
            "label": label or name.replace("_", " ").title(), "data_type": data_type,
            "required": required}


def rel(obj_name, related, label=None):
    return {"kind": "relationship", "object": obj_name, "related_object": related,
            "label": label or "%s to %s" % (obj_name, related)}


def full_records():
    """A structurally complete synthetic reply covering every requested object type."""
    return [obj("contacts"), prop("contacts", "firstname"), prop("contacts", "lifecyclestage",
                                                                 "enumeration"),
            obj("companies"), prop("companies", "name", required=True),
            prop("companies", "annual_revenue", "currency"),
            obj("deals"), prop("deals", "closedate", "datetime"), rel("deals", "companies")]


def reply(brief, records, outcome="completed", count=None, connector_id=None, tool_name=None):
    """The agent's line reply for a sealed brief, rendered as the protocol requires."""
    text = catalogue_mod.render_reply(brief["operation"], connector_id or brief["connector_id"],
                                      tool_name or brief["tool_name"], records, outcome)
    if count is not None:
        lines = text.splitlines()
        parts = lines[-1].split(" ")
        parts[-1] = str(count)
        lines[-1] = " ".join(parts)
        text = "\n".join(lines)
    return text


def discover(records=None, request=None, **reply_kwargs):
    """Seal, reply and close once under the installed synthetic registry. Returns the result."""
    brief, refusal = catalogue_mod.request_discovery(request or {"capability_placeholder": "~~crm"})
    if refusal is not None:
        return refusal
    records = full_records() if records is None else records
    return catalogue_mod.close_discovery(brief["operation"], reply(brief, records, **reply_kwargs))
