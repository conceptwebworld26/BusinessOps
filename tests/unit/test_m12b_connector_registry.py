# -*- coding: utf-8 -*-
"""M12-B connector registry, resolution and value-free catalogue (ADR-0037; ADR-0038).

The shipped registry is empty, because no connector has a complete, approved Connector-Gated
discovery chain (OD-3). These tests therefore do two things:

* pin the **shipped** state: every placeholder resolves to a named absence with the file
  alternative, HubSpot is nowhere in the runtime, `.mcp.json` and the agent set are exactly what
  an empty registry requires, and the file workflow never touches the connector layer;
* drive the engine with a **synthetic** connector (`tests/connector_fixtures.py`) to prove the
  evaluation order, the sealed consumed-once brief, the fail-closed parser, the closed failure
  model and determinism. The synthetic connector is labelled as such everywhere and is never a
  Connector Gate measurement.

Security categories (ADR-0037 section J) live in `tests/negative/test_m12b_connector_security.py`.
"""

import copy
import io
import json
import os
import re
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"), os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import jsonschema_mini                                   # noqa: E402
from bops.connectors import binding as B                           # noqa: E402
from bops.connectors import catalogue as C                         # noqa: E402
from bops.connectors import contract as K                          # noqa: E402
from bops.connectors import registry as R                          # noqa: E402

import connector_fixtures as F                                    # noqa: E402

SCHEMA = C.load_schema()


def valid(document, definition=None):
    """Schema errors for a document, optionally against one named definition."""
    schema = SCHEMA if definition is None else {"$ref": "#/definitions/%s" % definition,
                                                "definitions": SCHEMA["definitions"]}
    return jsonschema_mini.validate(json.loads(json.dumps(document)), schema)


# =================================================================================================
# A. The shipped registry and resolution
# =================================================================================================

class ShippedRegistry(unittest.TestCase):

    def test_the_shipped_registry_admits_no_connector(self):
        self.assertEqual(R._DECLARATIONS, ())
        self.assertEqual(dict(R.REGISTRY.connectors), {})
        self.assertEqual(R.REGISTRY.discovery_tools(), ())
        self.assertEqual(R.REGISTRY.server_keys(), ())

    def test_every_placeholder_resolves_to_a_named_absence_with_the_file_path(self):
        for resolution in R.resolve_all():
            self.assertEqual(resolution["status"], K.NOT_CONFIGURED)
            self.assertEqual(resolution["connectors"], [])
            self.assertEqual(resolution["absence"]["code"], K.CONNECTOR_NOT_CONFIGURED)
            self.assertIn("No ", resolution["absence"]["text"])
            self.assertIn("CSV or Excel", resolution["absence"]["file_fallback"])
            self.assertEqual(valid(resolution, "resolution"), [])
        self.assertEqual([r["capability_placeholder"] for r in R.resolve_all()],
                         list(K.PLACEHOLDERS))

    def test_resolution_is_deterministic(self):
        self.assertEqual(json.dumps(R.resolve_all()), json.dumps(R.resolve_all()))
        self.assertEqual(R.resolve("~~crm"), R.resolve("~~crm"))

    def test_resolution_never_names_an_unregistered_vendor(self):
        text = json.dumps(R.resolve_all()).lower()
        for vendor in ("hubspot", "salesforce", "quickbooks", "xero", "slack", "shopify",
                       "stripe", "snowflake", "bigquery"):
            self.assertNotIn(vendor, text)

    def test_resolution_outside_the_vocabulary_is_refused(self):
        for value in ("crm", "~~CRM", " ~~crm", "~~crm ", "~~hubspot", "hubspot", "", None, 2,
                      ["~~crm"], "~~crm*", "~~"):
            with self.assertRaises(R.ConnectorRequestError) as caught:
                R.resolve(value)
            self.assertEqual(caught.exception.code, K.REQUEST_INVALID)

    def test_configured_means_registered_only(self):
        reg = F.registry()
        resolution = reg.resolve("~~crm")
        self.assertEqual(resolution["status"], K.CONFIGURED)
        self.assertEqual(resolution["connectors"], [F.CONNECTOR_ID])
        self.assertIsNone(resolution["absence"])
        rendered = C.render_resolution(resolution)
        self.assertIn("Registered and declared only", rendered)
        self.assertIn("nothing about connection, authorization or availability", rendered)

    def test_two_connectors_for_one_capability_are_ambiguous_in_registry_order(self):
        second = F.declaration(connector_id="synthetic-crm-two", server_key="bops-synthetic-two",
                               tool_name="mcp__plugin_businessops_bops-synthetic-two__describe",
                               namespace="mcp__plugin_businessops_bops-synthetic-two")
        reg = F.registry([F.declaration(), second])
        resolution = reg.resolve("~~crm")
        self.assertEqual(resolution["status"], K.AMBIGUOUS)
        self.assertEqual(resolution["connectors"], [F.CONNECTOR_ID, "synthetic-crm-two"])


class ExactIdentity(unittest.TestCase):

    def setUp(self):
        self.reg = F.registry()

    def test_only_the_exact_connector_id_matches(self):
        self.assertIsNotNone(self.reg.connector(F.CONNECTOR_ID))
        for near in ("Synthetic-CRM", "SYNTHETIC-CRM", "synthetic-crm ", " synthetic-crm",
                     "synthetic", "synthetic-crm-2", "synthetic_crm", "synthetic-cr",
                     "Synthetic CRM", None, 1, ["synthetic-crm"]):
            self.assertIsNone(self.reg.connector(near), near)

    def test_only_the_exact_placeholder_lists_the_connector(self):
        self.assertEqual(self.reg.connectors_for("~~crm"), (F.CONNECTOR_ID,))
        for other in ("~~CRM", "crm", "~~crm ", "~~accounting"):
            self.assertEqual(self.reg.connectors_for(other), ())


# =================================================================================================
# A. Malformed registries
# =================================================================================================

class MalformedRegistry(unittest.TestCase):

    def refused(self, mutate, decls=None):
        decls = decls if decls is not None else [F.declaration()]
        mutate(decls)
        with self.assertRaises(R.ConnectorRegistryError):
            R.Registry(decls)

    def cap(self, decls):
        return decls[0]["capabilities"][0]

    def test_a_sound_synthetic_declaration_builds_and_matches_the_schema(self):
        R.Registry([F.declaration()])
        self.assertEqual(valid(F.declaration(), "declaration"), [])
        self.assertEqual(valid(F.gate_record(), "gate_record"), [])

    def test_a_registry_must_be_a_sequence(self):
        for value in (None, {}, "x", F.declaration()):
            with self.assertRaises(R.ConnectorRegistryError):
                R.Registry(value)

    def test_missing_and_extra_fields_are_refused(self):
        for field in R.CONNECTOR_FIELDS:
            self.refused(lambda d, f=field: d[0].pop(f))
        for field in R.CAPABILITY_FIELDS:
            self.refused(lambda d, f=field: self.cap(d).pop(f))
        for extra in ("enabled", "authorized", "verified", "approved", "trust", "scope", "token",
                      "headers", "priority", "connected", "available"):
            self.refused(lambda d, e=extra: d[0].__setitem__(e, True))
            self.refused(lambda d, e=extra: self.cap(d).__setitem__(e, True))

    def test_duplicate_or_ambiguous_identities_are_refused(self):
        self.refused(lambda d: None, [F.declaration(), F.declaration()])
        self.refused(lambda d: None, [F.declaration(), F.declaration(
            connector_id="synthetic-other", tool_name=F.NAMESPACE + "__other")])
        self.refused(lambda d: None, [F.declaration(), F.declaration(
            connector_id="synthetic-other", server_key="bops-synthetic-other")])
        self.refused(lambda d: self.cap(d)["arguments"].append(
            {"name": "objectType2", "source": "object_type", "value": None}))
        self.refused(lambda d: d[0]["capabilities"].append(copy.deepcopy(self.cap(d))))

    def test_identity_fields_are_validated(self):
        for bad in ("Synthetic", "s", "1crm", "crm_x", "a" * 41, "", "crm crm"):
            self.refused(lambda d, b=bad: d[0].__setitem__("connector_id", b))
        for bad in ("~~CRM", "crm", "~~x", None):
            self.refused(lambda d, b=bad: d[0].__setitem__("capability_placeholder", b))
        for bad in ("Bops", "bops-verifier", "x", "bops_verifier"):
            self.refused(lambda d, b=bad: d[0].__setitem__("server_key", b))
        for bad in ("describe", "mcp__only", "MCP__a__b", "mcp__a b__c", "mcp__a__b.c"):
            self.refused(lambda d, b=bad: self.cap(d).__setitem__("tool_name", b))
        for bad in ("namespace", "mcp_x", ""):
            self.refused(lambda d, b=bad: self.cap(d).__setitem__("namespace", b))
        self.refused(lambda d: d[0].__setitem__("display_name", "jane@example.com"))

    def test_chat_is_not_eligible(self):
        self.refused(lambda d: d[0].__setitem__("capability_placeholder", "~~chat"))

    def test_only_discovery_is_declarable(self):
        for interaction in ("read", "write", "administrative", "discover", "Discovery", None):
            self.refused(lambda d, i=interaction: self.cap(d).__setitem__("interaction_class", i))

    def test_transport_is_identity_only(self):
        for transport in ({"type": "http", "url": "https://synthetic.invalid/mcp",
                           "headers": {"Authorization": "x"}},
                          {"type": "http", "url": "https://user:pw@synthetic.invalid/mcp"},
                          {"type": "http", "url": "https://synthetic.invalid/mcp?key=1"},
                          {"type": "http", "url": "http://synthetic.invalid/mcp"},
                          {"type": "stdio", "command": "x", "args": [], "env": {"K": "v"}},
                          {"type": "sse", "url": "https://synthetic.invalid/mcp"},
                          {"url": "https://synthetic.invalid/mcp"}):
            self.refused(lambda d, t=transport: d[0].__setitem__("transport", t))

    def test_gate_record_must_be_a_dated_development_record(self):
        for path in ("docs/decisions/ADR-0037-m12-connector-layer-contract.md",
                     "../secrets.md", "docs/development/../../x.md", "/etc/passwd",
                     "docs/development/gate.md", "~/.claude/settings.json"):
            self.refused(lambda d, p=path: self.cap(d).__setitem__("gate_record", p))

    def test_argument_and_output_shapes_are_closed(self):
        self.refused(lambda d: self.cap(d)["arguments"].append(
            {"name": "query", "source": "free_text", "value": None}))
        self.refused(lambda d: self.cap(d)["arguments"][1].__setitem__("value", 0))
        self.refused(lambda d: self.cap(d)["arguments"][1].__setitem__("value", 1001))
        self.refused(lambda d: self.cap(d)["arguments"][0].__setitem__("value", "contacts"))
        self.refused(lambda d: self.cap(d)["output_fields"]["property"].append("options"))
        self.refused(lambda d: self.cap(d)["output_fields"]["property"].remove("property"))
        self.refused(lambda d: self.cap(d)["output_fields"].__setitem__("record", ["kind"]))
        self.refused(lambda d: self.cap(d).__setitem__("object_types", []))
        self.refused(lambda d: self.cap(d).__setitem__("object_types", ["contacts", "contacts"]))
        self.refused(lambda d: self.cap(d).__setitem__("object_types", ["0-1"]))
        self.refused(lambda d: self.cap(d).__setitem__("max_calls", 0))
        self.refused(lambda d: self.cap(d).__setitem__("max_entries", True))


class Immutability(unittest.TestCase):
    """ADR-0037 section J-18: nothing at runtime adds a connector, server, tool or class."""

    def test_the_registry_and_its_records_cannot_be_changed(self):
        reg = F.registry()
        with self.assertRaises(TypeError):
            reg.connectors["new"] = {}
        with self.assertRaises(R.ConnectorRegistryError):
            reg._connectors = {}
        with self.assertRaises(R.ConnectorRegistryError):
            R.REGISTRY.extra = 1
        declaration = reg.connector(F.CONNECTOR_ID)
        with self.assertRaises(TypeError):
            declaration["server_key"] = "other"
        with self.assertRaises(TypeError):
            declaration["capabilities"][0]["tool_name"] = "other"
        with self.assertRaises((TypeError, AttributeError)):
            declaration["capabilities"].append({})

    def test_building_a_registry_does_not_retain_the_callers_data(self):
        source = [F.declaration()]
        reg = R.Registry(source)
        source[0]["server_key"] = "bops-changed"
        source[0]["capabilities"][0]["object_types"].append("tickets")
        self.assertEqual(reg.connector(F.CONNECTOR_ID)["server_key"], F.SERVER_KEY)
        self.assertEqual(list(reg.connector(F.CONNECTOR_ID)["capabilities"][0]["object_types"]),
                         F.OBJECT_TYPES)

    def test_no_public_function_accepts_a_registry_tool_or_server(self):
        import inspect
        for module in (R, C):
            for name in ("resolve", "resolve_all", "request_discovery", "close_discovery"):
                function = getattr(module, name, None)
                if function is None:
                    continue
                parameters = set(inspect.signature(function).parameters)
                self.assertFalse(parameters & {"registry", "layers", "tool", "tool_name",
                                               "server", "server_key", "namespace", "arguments",
                                               "declaration"}, name)

    def test_the_connector_layer_reads_no_configuration_or_context(self):
        for name in os.listdir(os.path.join(REPO_ROOT, "lib", "python", "bops", "connectors")):
            if name.endswith(".py"):
                with io.open(os.path.join(REPO_ROOT, "lib", "python", "bops", "connectors", name),
                             encoding="utf-8") as handle:
                    source = handle.read()
                for token in ("from ..config", "from ..context", "business_context",
                              "load_defaults", "os.environ", "getenv"):
                    self.assertNotIn(token, source, "%s: %s" % (name, token))


# =================================================================================================
# The sealed, consumed-once brief
# =================================================================================================

class SealedBrief(unittest.TestCase):

    def test_a_brief_is_sealed_only_on_a_complete_chain_and_names_one_tool(self):
        with F.installed() as (_reg, _lay, directory):
            brief, refusal = C.request_discovery({"capability_placeholder": "~~crm"})
            self.assertIsNone(refusal)
            self.assertEqual(valid(brief, "brief"), [])
            self.assertEqual(brief["tool_name"], F.TOOL_NAME)
            self.assertEqual(brief["object_types"], F.OBJECT_TYPES)
            self.assertEqual([c["arguments"] for c in brief["calls"]],
                             [{"objectType": o, "limit": 100} for o in F.OBJECT_TYPES])
            self.assertEqual(brief["cursor_argument"], "after")
            self.assertRegex(brief["operation"], r"^cop-[0-9a-f]{24}$")
            stored = os.path.join(directory, ".businessops", "connectors", "operations",
                                  brief["operation"] + ".json")
            self.assertTrue(os.path.isfile(stored))

    def test_a_scope_selects_declared_object_types_only(self):
        with F.installed():
            brief, _ = C.request_discovery({"capability_placeholder": "~~crm",
                                            "object_types": ["deals"]})
            self.assertEqual(brief["object_types"], ["deals"])
            self.assertEqual(len(brief["calls"]), 1)

    def test_operation_ids_are_random_and_distinct(self):
        with F.installed():
            ids = set(C.request_discovery({"capability_placeholder": "~~crm"})[0]["operation"]
                      for _ in range(20))
            self.assertEqual(len(ids), 20)

    def test_a_brief_is_consumed_once_whatever_the_outcome(self):
        with F.installed() as (_reg, _lay, directory):
            brief, _ = C.request_discovery({"capability_placeholder": "~~crm"})
            first = C.close_discovery(brief["operation"], "no protocol lines at all")
            self.assertEqual(first.reason_code, K.MALFORMED_RESPONSE)
            replay = C.close_discovery(brief["operation"], F.reply(brief, F.full_records()))
            self.assertEqual(replay.reason_code, K.OPERATION_UNKNOWN)
            self.assertEqual(os.listdir(os.path.join(directory, ".businessops", "connectors",
                                                     "operations")), [])

    def test_nothing_is_sealed_or_written_on_any_refusal(self):
        with F.installed() as (_reg, _lay, directory):
            for request in ({"capability_placeholder": "~~accounting"},
                            {"capability_placeholder": "~~crm", "interaction": "read"},
                            {"capability_placeholder": "~~crm", "interaction": "write"},
                            {"capability_placeholder": "~~crm", "object_types": ["tickets"]},
                            {"capability_placeholder": "~~crm", "authorized": True}):
                brief, refusal = C.request_discovery(request)
                self.assertIsNone(brief)
                self.assertEqual(refusal.status, K.UNAVAILABLE)
            self.assertFalse(os.path.exists(os.path.join(directory, ".businessops")))


# =================================================================================================
# C. The value-free catalogue
# =================================================================================================

class Catalogue(unittest.TestCase):

    def test_a_complete_reply_builds_a_value_free_catalogue(self):
        with F.installed():
            result = F.discover()
        doc = result.as_dict()
        self.assertEqual(valid(doc), [])
        self.assertEqual(doc["status"], K.COMPLETE)
        self.assertIsNone(doc["reason_code"])
        self.assertRegex(doc["catalogue_id"], r"^cat-[0-9a-f]{12}$")
        self.assertEqual([o["status"] for o in doc["object_types"]], ["described"] * 3)
        kinds = [e["kind"] for e in doc["entries"]]
        self.assertEqual(kinds, sorted(kinds, key=K.ENTRY_KINDS.index))
        self.assertTrue(all(e["basis"] == "relayed" for e in doc["entries"]))
        by_property = dict((e["property"], e) for e in doc["entries"] if e["kind"] == "property")
        self.assertEqual(by_property["lifecyclestage"]["data_type"], "enumeration")
        self.assertEqual(by_property["annual_revenue"]["data_type"], "number")
        self.assertEqual(by_property["closedate"]["data_type"], "datetime")
        self.assertIs(by_property["name"]["required"], True)
        self.assertEqual(doc["trust_statement"], K.TRUST_STATEMENT)
        self.assertEqual(doc["use_statement"], K.USE_STATEMENT)
        self.assertEqual(doc["connector_id"], F.CONNECTOR_ID)
        self.assertNotIn("operation", json.dumps(doc))

    def test_unknown_data_types_are_unknown_never_guessed(self):
        with F.installed():
            doc = F.discover([F.obj("contacts"), F.prop("contacts", "x", "hs_weird_type")],
                             request={"capability_placeholder": "~~crm",
                                      "object_types": ["contacts"]}).as_dict()
        self.assertEqual([e["data_type"] for e in doc["entries"] if e["property"]], ["unknown"])

    def test_the_rendered_catalogue_states_its_trust(self):
        with F.installed():
            text = C.render(F.discover())
        self.assertIn("Object type contacts: described", text)
        self.assertIn("property firstname: string", text)
        self.assertIn("relationship to companies", text)
        self.assertIn(K.TRUST_STATEMENT, text)
        self.assertIn(K.USE_STATEMENT, text)

    def test_a_result_cannot_be_made_or_changed_by_a_caller(self):
        with self.assertRaises(C.CatalogueError):
            C.CatalogueResult({"status": "complete"})
        with F.installed():
            result = F.discover()
        with self.assertRaises(C.CatalogueError):
            result.status = "complete"
        with self.assertRaises(C.CatalogueError):
            C.render(result.as_dict())
        mutated = result.as_dict()
        mutated["entries"] = []
        self.assertNotEqual(result.as_dict(), mutated)


# =================================================================================================
# E. The closed failure model
# =================================================================================================

class FailureModel(unittest.TestCase):

    def test_exactly_the_nineteen_codes_of_section_h(self):
        self.assertEqual(K.FAILURE_CODES, (
            "connector_not_configured", "ambiguous_connector", "capability_unsupported",
            "binding_mismatch", "connector_unavailable", "connector_not_authorized",
            "authentication_failure", "authorization_failure", "timeout", "tool_failure",
            "malformed_response", "operation_unknown", "stale_metadata", "metadata_conflict",
            "external_content_unavailable", "privacy_restricted", "insufficient_data",
            "request_invalid", "blocked_prerequisite"))
        self.assertEqual(SCHEMA["definitions"]["failure_code"]["enum"], list(K.FAILURE_CODES))
        self.assertEqual(set(K.MESSAGES), set(K.FAILURE_CODES))

    def test_no_two_codes_share_a_message(self):
        self.assertEqual(len(set(K.MESSAGES.values())), len(K.FAILURE_CODES))
        self.assertNotIn(K.NO_WRITE_PATH, K.MESSAGES.values())

    def outcome(self, request=None, records=None, **reply_kwargs):
        with F.installed():
            return F.discover(records, request, **reply_kwargs)

    def test_every_code_is_produced_deterministically_by_the_engine(self):
        """Engine behaviour, not runtime proof. The five codes reachable with the shipped
        (empty) registry are produced against it; the other fourteen need a sealed operation,
        so they are produced against the synthetic enforcement fixture, and the seven relayed
        codes are relay lines this test writes itself - no agent or vendor produced any of them.
        """
        second = F.declaration(connector_id="synthetic-crm-two", server_key="bops-synthetic-two",
                               tool_name="mcp__plugin_businessops_bops-synthetic-two__describe",
                               namespace="mcp__plugin_businessops_bops-synthetic-two")
        produced = {}
        produced[K.CONNECTOR_NOT_CONFIGURED] = C.request_discovery(
            {"capability_placeholder": "~~crm"})[1]
        with F.installed([F.declaration(), second]):
            produced[K.AMBIGUOUS_CONNECTOR] = C.request_discovery(
                {"capability_placeholder": "~~crm"})[1]
        produced[K.CAPABILITY_UNSUPPORTED] = self.outcome(
            {"capability_placeholder": "~~crm", "object_types": ["tickets"]})
        with F.installed(layer=F.layers(grant=())):
            produced[K.BINDING_MISMATCH] = C.request_discovery(
                {"capability_placeholder": "~~crm"})[1]
        for code in K.RELAYABLE_CODES:
            produced.setdefault(code, self.outcome(records=[], outcome=code))
        with F.installed():
            brief, _ = C.request_discovery({"capability_placeholder": "~~crm"})
            produced["timeout(no reply)"] = C.close_discovery(brief["operation"], None)
        produced[K.MALFORMED_RESPONSE] = self.outcome(count=99)
        produced[K.OPERATION_UNKNOWN] = C.close_discovery("cop-" + "a" * 24, "")
        produced[K.METADATA_CONFLICT] = self.outcome(records=[
            F.obj("contacts"), F.obj("companies"), F.obj("deals"),
            F.prop("deals", "amount", "number"), F.prop("deals", "amount", "string")])
        produced[K.EXTERNAL_CONTENT_UNAVAILABLE] = self.outcome(records=[F.obj("contacts")])
        produced[K.PRIVACY_RESTRICTED] = self.outcome(records=[
            F.obj("contacts"), F.obj("companies"),
            dict(F.obj("deals"), sample_values=["Acme"])])
        produced[K.INSUFFICIENT_DATA] = self.outcome(records=[])
        produced[K.REQUEST_INVALID] = C.request_discovery({"capability_placeholder": "~~crmx"})[1]
        produced[K.BLOCKED_PREREQUISITE] = C.request_discovery(
            {"capability_placeholder": "~~crm", "interaction": "read"})[1]

        self.assertEqual(produced["timeout(no reply)"].reason_code, K.TIMEOUT)
        for code in K.FAILURE_CODES:
            result = produced[code]
            self.assertEqual(result.reason_code, code, code)
            self.assertEqual(valid(result.as_dict()), [], code)
            self.assertIn(result.status, K.STATUSES)
        self.assertEqual(produced[K.METADATA_CONFLICT].status, K.COMPLETE_WITH_LIMITATIONS)
        self.assertEqual(produced[K.PRIVACY_RESTRICTED].status, K.COMPLETE_WITH_LIMITATIONS)
        self.assertEqual(produced[K.EXTERNAL_CONTENT_UNAVAILABLE].status, K.PARTIAL)
        for code in (K.CONNECTOR_NOT_CONFIGURED, K.AMBIGUOUS_CONNECTOR, K.MALFORMED_RESPONSE,
                     K.INSUFFICIENT_DATA, K.BLOCKED_PREREQUISITE, K.OPERATION_UNKNOWN) \
                + K.RELAYABLE_CODES:
            self.assertEqual(produced[code].status, K.UNAVAILABLE, code)
            self.assertEqual(produced[code].as_dict()["entries"], [], code)

    def test_a_relayed_code_never_grants_and_never_builds_a_catalogue(self):
        for code in K.RELAYABLE_CODES:
            doc = self.outcome(records=[], outcome=code).as_dict()
            self.assertEqual((doc["status"], doc["catalogue_id"], doc["entries"]),
                             (K.UNAVAILABLE, None, []))
            self.assertIn("CSV or Excel", doc["file_fallback"])

    def test_a_relayed_failure_carrying_records_is_malformed(self):
        result = self.outcome(outcome=K.CONNECTOR_NOT_AUTHORIZED)
        self.assertEqual(result.reason_code, K.MALFORMED_RESPONSE)

    def test_zero_records_is_insufficient_data_not_malformed(self):
        result = self.outcome(records=[])
        self.assertEqual(result.reason_code, K.INSUFFICIENT_DATA)
        self.assertIn("never evidence that the system holds nothing", result.as_dict()["message"])

    def test_the_connector_named_in_a_message_comes_from_the_registry(self):
        doc = self.outcome(records=[], outcome=K.CONNECTOR_NOT_AUTHORIZED).as_dict()
        self.assertTrue(doc["message"].startswith("Synthetic CRM is an optional supported "
                                                  "connector, but it is not connected."))


# =================================================================================================
# H. Determinism
# =================================================================================================

class Determinism(unittest.TestCase):

    def test_the_same_reply_in_any_order_gives_the_same_bytes(self):
        records = F.full_records()
        with F.installed():
            first = F.discover(records)
            second = F.discover(list(reversed(records)))
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.as_dict()["catalogue_id"], second.as_dict()["catalogue_id"])

    def test_a_repeated_record_is_refused_not_collapsed(self):
        """Collapsing a repeated line would be a silent repair of the relay (ADR-0017)."""
        records = F.full_records()
        with F.installed():
            result = F.discover(records + [records[0]])
        self.assertEqual(result.reason_code, K.MALFORMED_RESPONSE)
        self.assertEqual(result.as_dict()["entries"], [])

    def test_identity_excludes_the_operation_and_time(self):
        with F.installed():
            documents = [F.discover().as_dict() for _ in range(3)]
        self.assertEqual(len(set(d["catalogue_id"] for d in documents)), 1)
        text = json.dumps(documents[0])
        self.assertIsNone(re.search(r"cop-[0-9a-f]{24}", text))
        for key in ("timestamp", "time", "created_at", "retrieved_at", "pulled_at", "date"):
            self.assertNotIn('"%s"' % key, text)

    def test_the_identity_changes_with_scope_or_entries(self):
        with F.installed():
            base = F.discover().as_dict()["catalogue_id"]
            fewer = F.discover(F.full_records()[:-1]).as_dict()["catalogue_id"]
            scoped = F.discover([F.obj("deals")], request={
                "capability_placeholder": "~~crm", "object_types": ["deals"]}).as_dict()
        self.assertNotEqual(base, fewer)
        self.assertNotEqual(base, scoped["catalogue_id"])

    def test_serialisation_is_stable_and_schema_valid(self):
        with F.installed():
            result = F.discover()
        self.assertEqual(result.to_json(), result.to_json())
        self.assertEqual(json.loads(result.to_json()), result.as_dict())
        self.assertEqual(jsonschema_mini.unsupported_keywords(SCHEMA), set())


# =================================================================================================
# B / F. Admission (OD-3) and optionality in the shipped repository
# =================================================================================================

class ShippedAdmission(unittest.TestCase):

    def test_the_shipped_repository_satisfies_od3_and_the_build_rule(self):
        self.assertEqual(B.admission_findings(), [])

    def test_mcp_json_is_bops_verifier_plus_registered_connector_servers_exactly(self):
        with io.open(os.path.join(REPO_ROOT, ".mcp.json"), encoding="utf-8") as handle:
            servers = json.load(handle)["mcpServers"]
        self.assertEqual(set(servers), {"bops-verifier"} | set(R.REGISTRY.server_keys()))
        for key, entry in servers.items():
            self.assertFalse(set(entry) & {"headers", "env", "token", "apiKey"}, key)

    def test_the_connector_agent_exists_only_on_a_complete_chain(self):
        agent = os.path.join(REPO_ROOT, "agents", "bops-data-profiler.md")
        self.assertEqual(os.path.exists(agent), bool(R.REGISTRY.discovery_tools()))
        self.assertIsNone(B.read_agent_grant())
        self.assertEqual(sorted(n[:-3] for n in os.listdir(os.path.join(REPO_ROOT, "agents"))
                                if n.endswith(".md")),
                         ["bops-analysis-verifier", "bops-research-scout"])

    def test_no_gate_record_block_exists_in_the_repository(self):
        """No Connector Gate has been approved, so no development record carries a Gate block."""
        directory = os.path.join(REPO_ROOT, "docs", "development")
        for name in os.listdir(directory):
            with io.open(os.path.join(directory, name), encoding="utf-8") as handle:
                self.assertNotIn("```" + B.GATE_FENCE, handle.read(), name)

    def test_the_gate_record_loader_reads_only_dated_development_records(self):
        for path in ("docs/development/2099-01-01-synthetic-fixture-not-a-gate-record.md",
                     "docs/decisions/ADR-0037-m12-connector-layer-contract.md", ".mcp.json",
                     "../x.md", None):
            with self.assertRaises(B.GateRecordError):
                B.load_gate_record(path)


class GateRecordForm(unittest.TestCase):

    def test_a_record_in_the_closed_form_parses(self):
        record = F.gate_record()
        self.assertEqual(B.parse_gate_record(F.gate_text(record)), record)

    def test_zero_or_two_blocks_and_open_shapes_are_refused(self):
        record = F.gate_record()
        for text in ("no block", F.gate_text(record) + F.gate_text(record),
                     F.gate_text(record).replace("bops-connector-gate", "json"),
                     "```bops-connector-gate\nnot json\n```\n", None):
            with self.assertRaises(B.GateRecordError):
                B.parse_gate_record(text)
        for mutate in (lambda r: r.pop("server_instructions"),
                       lambda r: r.__setitem__("authorized", True),
                       lambda r: r.__setitem__("protocol", "bops.connector.gate/2"),
                       lambda r: r.__setitem__("classification_reasons", []),
                       lambda r: r.__setitem__("measured_on", "yesterday"),
                       lambda r: r["value_free_property"].pop("method"),
                       lambda r: r.__setitem__("server_instructions", 7)):
            broken = copy.deepcopy(record)
            mutate(broken)
            with self.assertRaises(B.GateRecordError):
                B.parse_gate_record(F.gate_text(broken))


if __name__ == "__main__":                                   # pragma: no cover
    unittest.main()
