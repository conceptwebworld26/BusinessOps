"""The connector layer's closed vocabularies (ADR-0037 sections C, G and H; ADR-0038 section 8).

Everything a connector request, reply or result may say is enumerated here, and nothing outside
these tables is ever emitted. Three rules decide what the tables contain:

  * **No status means authorized.** There is no `connected`, `authorized`, `verified`,
    `available`, `approved` or `granted` value anywhere. Resolution says `configured`, which
    means *registered and declared* and nothing more (ADR-0037 section C.2). The furthest a
    result goes is that one permitted operation completed (ADR-0038 section 6).
  * **The 19 failure codes are closed** (ADR-0037 section H). None is added here, none is
    renamed, and two materially different situations never share a message.
  * **Runtime text comes from here and from the registry only.** An unregistered vendor is
    never named at runtime (ADR-0038 section 8, state 1); a registered connector is named by its
    registry display name.

The lifecycle states of ADR-0038 section 4 are documentation vocabulary. They are deliberately
not constants here: at runtime BusinessOps reports only the section H codes and result statuses.
"""

import re

SCHEMA_VERSION = "1.0.0"
SCHEMA_NAME = "connector.schema.json"

# -- capability placeholders (ADR-0004's closed vocabulary) -----------------------------------

ACCOUNTING = "~~accounting"
CRM = "~~crm"
COMMERCE = "~~commerce"
WAREHOUSE = "~~warehouse"
SPREADSHEET = "~~spreadsheet"
CHAT = "~~chat"
PLACEHOLDERS = (ACCOUNTING, CRM, COMMERCE, WAREHOUSE, SPREADSHEET, CHAT)

#: Placeholders no connector may be registered for in M12. `~~chat` is write-capable
#: communication (ADR-0037 section A.3).
INELIGIBLE_PLACEHOLDERS = (CHAT,)

#: How a placeholder is named in a named absence. Category words only - never a vendor.
CATEGORY_NAMES = {
    ACCOUNTING: "accounting",
    CRM: "CRM",
    COMMERCE: "commerce",
    WAREHOUSE: "data warehouse",
    SPREADSHEET: "spreadsheet",
    CHAT: "chat",
}

# -- interaction classes (ADR-0037 section G) -------------------------------------------------

DISCOVERY = "discovery"
READ = "read"
WRITE = "write"
ADMINISTRATIVE = "administrative"
INTERACTIONS = (DISCOVERY, READ, WRITE, ADMINISTRATIVE)

#: The only class a declaration, a grant or a brief may carry in M12-B. `read` can be added
#: only by M12-C's own ADR; `write` and `administrative` have no path at all.
PERMITTED_INTERACTIONS = (DISCOVERY,)

# -- resolution (ADR-0037 section C.2) --------------------------------------------------------

NOT_CONFIGURED = "not_configured"
CONFIGURED = "configured"
AMBIGUOUS = "ambiguous"
RESOLUTION_STATUSES = (NOT_CONFIGURED, CONFIGURED, AMBIGUOUS)

# -- failure codes (ADR-0037 section H), in the contract's order ------------------------------

CONNECTOR_NOT_CONFIGURED = "connector_not_configured"
AMBIGUOUS_CONNECTOR = "ambiguous_connector"
CAPABILITY_UNSUPPORTED = "capability_unsupported"
BINDING_MISMATCH = "binding_mismatch"
CONNECTOR_UNAVAILABLE = "connector_unavailable"
CONNECTOR_NOT_AUTHORIZED = "connector_not_authorized"
AUTHENTICATION_FAILURE = "authentication_failure"
AUTHORIZATION_FAILURE = "authorization_failure"
TIMEOUT = "timeout"
TOOL_FAILURE = "tool_failure"
MALFORMED_RESPONSE = "malformed_response"
OPERATION_UNKNOWN = "operation_unknown"
STALE_METADATA = "stale_metadata"
METADATA_CONFLICT = "metadata_conflict"
EXTERNAL_CONTENT_UNAVAILABLE = "external_content_unavailable"
PRIVACY_RESTRICTED = "privacy_restricted"
INSUFFICIENT_DATA = "insufficient_data"
REQUEST_INVALID = "request_invalid"
BLOCKED_PREREQUISITE = "blocked_prerequisite"

FAILURE_CODES = (
    CONNECTOR_NOT_CONFIGURED, AMBIGUOUS_CONNECTOR, CAPABILITY_UNSUPPORTED, BINDING_MISMATCH,
    CONNECTOR_UNAVAILABLE, CONNECTOR_NOT_AUTHORIZED, AUTHENTICATION_FAILURE,
    AUTHORIZATION_FAILURE, TIMEOUT, TOOL_FAILURE, MALFORMED_RESPONSE, OPERATION_UNKNOWN,
    STALE_METADATA, METADATA_CONFLICT, EXTERNAL_CONTENT_UNAVAILABLE, PRIVACY_RESTRICTED,
    INSUFFICIENT_DATA, REQUEST_INVALID, BLOCKED_PREREQUISITE)

#: Outcomes the agent may relay on its terminator line. Relayed codes are untrusted and can only
#: reduce what is shown: each ends the operation with no catalogue. Everything else in section H
#: is decided by Python, never accepted from a reply.
COMPLETED = "completed"
RELAYABLE_CODES = (CONNECTOR_UNAVAILABLE, CONNECTOR_NOT_AUTHORIZED, AUTHENTICATION_FAILURE,
                   AUTHORIZATION_FAILURE, TIMEOUT, TOOL_FAILURE, STALE_METADATA)
RELAY_OUTCOMES = (COMPLETED,) + RELAYABLE_CODES

# -- result statuses (ADR-0036's shape, reused by ADR-0037 section H) -------------------------

COMPLETE = "complete"
COMPLETE_WITH_LIMITATIONS = "complete_with_limitations"
PARTIAL = "partial"
UNAVAILABLE = "unavailable"
STATUSES = (COMPLETE, COMPLETE_WITH_LIMITATIONS, PARTIAL, UNAVAILABLE)

DESCRIBED = "described"
OBJECT_TYPE_STATUSES = (DESCRIBED, UNAVAILABLE)

# -- catalogue entries (ADR-0037 section C.4) -------------------------------------------------

OBJECT = "object"
PROPERTY = "property"
RELATIONSHIP = "relationship"
ENTRY_KINDS = (OBJECT, PROPERTY, RELATIONSHIP)

#: The engine's ceiling on what a reply record may carry, per kind. A declaration's output
#: allowlist is a subset of this; a key outside the declaration's allowlist is dropped and noted.
ENTRY_FIELDS = {
    OBJECT: ("kind", "object", "label"),
    PROPERTY: ("kind", "object", "property", "label", "data_type", "required"),
    RELATIONSHIP: ("kind", "object", "related_object", "label"),
}
#: The identifier fields each kind must carry; one missing is a protocol defect.
IDENTIFIER_FIELDS = {
    OBJECT: ("object",),
    PROPERTY: ("object", "property"),
    RELATIONSHIP: ("object", "related_object"),
}

#: Set by Python on every entry, never accepted from a reply.
RELAYED = "relayed"

#: The closed data-type vocabulary. A vendor spelling outside the map is `unknown`, never
#: guessed.
DATA_TYPES = ("string", "number", "integer", "boolean", "date", "datetime", "enumeration",
              "reference", "unknown")
_DATA_TYPE_MAP = {
    "string": "string", "text": "string", "textarea": "string", "varchar": "string",
    "number": "number", "decimal": "number", "float": "number", "double": "number",
    "currency": "number",
    "integer": "integer", "int": "integer",
    "boolean": "boolean", "bool": "boolean", "booleancheckbox": "boolean",
    "date": "date",
    "datetime": "datetime", "date_time": "datetime", "timestamp": "datetime",
    "enumeration": "enumeration", "enum": "enumeration", "select": "enumeration",
    "picklist": "enumeration", "radio": "enumeration", "checkbox": "enumeration",
    "reference": "reference", "lookup": "reference",
}


def normalise_data_type(value):
    """Map a vendor type name to the closed vocabulary. Only the name is read, never options."""
    return _DATA_TYPE_MAP.get(value.strip().lower(), "unknown")


#: A connector, object-type, property or relationship identifier. Starts with a letter, so a
#: bare record id, a phone number or an amount never passes; no `@`, `:` or `/`, so an email or
#: a URL never passes.
IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,63}$")
CONNECTOR_ID = re.compile(r"^[a-z][a-z0-9-]{1,39}$")
MAX_LABEL = 128

#: Shapes a record value, a date from a record, an amount or a secret takes. A string matching
#: any of them never enters a catalogue: an identifier so shaped drops its entry, a label so
#: shaped is dropped, and a key name so shaped is noted as unnamed. Conservative by design - a
#: false positive costs one label, a false negative would put a value in a model context.
#:
#: **This screen is defence in depth, not the trust boundary.** A reply is read at all only for
#: an operation sealed on a complete chain - a registered discovery capability whose Connector
#: Gate record demonstrated value-free output, agreeing exactly with `.mcp.json` and the grant -
#: and re-checked at close. Its keys pass only through the declaration's closed allowlist, its
#: data types only through a closed vocabulary, and the result through a closed schema. What the
#: screen cannot do is recognise every value: a plain name in a free-text label passes it
#: (ADR-0037 *Consequences*: a residual risk). It has not been measured against any real vendor
#: response; no connector is admitted.
_VALUE_SHAPES = (
    re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+"),                     # email
    re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://|\bwww\."),           # URL
    re.compile(r"\d{6,}"),                                        # phone, record id, amount
    re.compile(r"\d{4}-\d{2}-\d{2}"),                             # ISO date
    re.compile(r"[$€£¥₹]\s?\d"),              # currency amount
    re.compile(r"\d[\d,]*\.\d{2}\b"),                             # decimal amount
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}"),                         # JWT
    re.compile(r"(?i)\b(?:sk|pk|pat|ghp|gho|xox[abpr])[-_][A-Za-z0-9]{8,}"),   # API key
    re.compile(r"(?i)\b(?:sk|pk|rk)[-_](?:live|test)[-_]\w{4,}"),  # payment API key
    re.compile(r"(?i)\bbearer\s+\S"),                             # authorization header
    re.compile(r"[0-9a-fA-F]{32,}"),                              # long hex secret
)
#: A long base64-alphabet run is a secret only when it mixes upper case, lower case and digits:
#: a key or token does, while a long snake_case field name such as
#: `hs_analytics_first_touch_converting_campaign` does not and must stay describable.
_LONG_RUN = re.compile(r"[A-Za-z0-9+/=_-]{32,}")


def _secret_run(run):
    return (any(c.isupper() for c in run) and any(c.islower() for c in run)
            and any(c.isdigit() for c in run))


def value_shaped(text):
    """Whether a string looks like a record value, a business date or amount, or a secret."""
    if any(pattern.search(text) for pattern in _VALUE_SHAPES):
        return True
    return any(_secret_run(run) for run in _LONG_RUN.findall(text))


# -- keys a request may never carry, and a reply record has dropped -------------------------

#: Authority and identity keys (ADR-0037 sections B.3 and E.9; ADR-0038 section 2). No request
#: may carry one, and a reply record carrying one has it dropped and noted. `connected` and
#: `available` join the contract's list because ADR-0038 makes both facts a model may never
#: declare.
AUTHORITY_KEYS = frozenset((
    "source_tier", "trust", "verified", "authorized", "authorised", "approved", "granted",
    "scope", "connected", "available", "availability", "authorization", "permission",
    "permissions", "operation", "basis", "connector", "connector_id", "capability",
    "capability_placeholder", "tool", "tool_name", "server", "server_key", "namespace",
    "interaction", "interaction_class", "status", "evidence", "evidence_class", "class",
    "provenance_class"))

#: Section C.6's prohibited content by key name: values, samples, options, counts, identities
#: and secrets, plus analysis vocabulary. A request carrying one is refused
#: (`privacy_restricted`); a reply record carrying one has it dropped and noted.
_PROHIBITED_PARTS = ("value", "sample", "option", "picklist", "choice", "count", "total",
                     "record", "row", "owner", "user", "team", "email", "phone", "address",
                     "token", "secret", "password", "credential", "api_key", "apikey",
                     "header", "cookie", "oauth", "code", "error", "message", "example",
                     "default", "confidence", "priority", "score", "rank", "recommend",
                     "revenue", "amount")


def prohibited_key(name):
    """Whether a key names section C.6 content."""
    lowered = name.lower()
    return any(part in lowered for part in _PROHIBITED_PARTS)


#: Why a reply key was dropped. Names only are ever recorded, never a value.
NOTE_AUTHORITY = "authority"
NOTE_PRIVACY = "privacy_restricted"
NOTE_NOT_ALLOWLISTED = "not_allowlisted"
NOTE_LENGTH = "length_bound"
NOTE_OUT_OF_SCOPE = "out_of_scope"
NOTE_REASONS = (NOTE_AUTHORITY, NOTE_PRIVACY, NOTE_NOT_ALLOWLISTED, NOTE_LENGTH,
                NOTE_OUT_OF_SCOPE)
#: Recorded in place of a key name that is itself malformed or value-shaped.
UNNAMED_KEY = "<unnamed>"
_KEY_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")


def safe_key_name(name):
    """A reply key name as it may be recorded, or `UNNAMED_KEY`. A key name is external text."""
    if isinstance(name, str) and _KEY_NAME.match(name) and not value_shaped(name):
        return name
    return UNNAMED_KEY


# -- the line protocol (ADR-0037 section D.2) -------------------------------------------------
#
# Distinct from the research scout's `BOPS-REC/1` / `BOPS-END/1`, so a research reply can never
# parse as a catalogue reply or the reverse. Neither token is a prefix of the other's lines:
# every line prefix includes the version slash and a following space.

RECORD_TOKEN = "BOPS-CAT/1"
END_TOKEN = "BOPS-CAT-END/1"
BRIEF_PROTOCOL = "bops.connector.brief/1"
GATE_PROTOCOL = "bops.connector.gate/1"
OPERATION_ID = re.compile(r"^cop-[0-9a-f]{24}$")
CATALOGUE_ID = re.compile(r"^cat-[0-9a-f]{12}$")

ANALYSIS = "connector_catalogue"
RESOLUTION_ANALYSIS = "connector_resolution"

# -- fixed text -------------------------------------------------------------------------------

TRUST_STATEMENT = ("Connector-reported structure, relayed by a model, unverified. It is not "
                   "evidence and it authorizes nothing.")
USE_STATEMENT = ("This describes what a connected system structurally holds - object types, "
                 "properties, data types, required flags and relationships. It carries no "
                 "record, value, count, option or identity, it computes nothing, and it never "
                 "enters analysis, synthesis or verification.")


def absence_text(placeholder):
    """ADR-0038 section 8, state 1. Names the category only - never a vendor."""
    return ("No %s connector is available in this version of BusinessOps."
            % CATEGORY_NAMES[placeholder])


def file_fallback(placeholder):
    """The file-export alternative every named absence and failure ends with."""
    return ("Export the %s data to CSV or Excel and supply the file: the same analysis runs "
            "through bops-data-ingestion, the Data Layer's quality gate and the engines, with "
            "no connector." % CATEGORY_NAMES[placeholder])


GENERIC_FALLBACK = ("Export the data to CSV or Excel and supply the file: the same analysis runs "
                    "through bops-data-ingestion with no connector.")

#: One sentence per failure code, never shared between codes. `{name}` is the registry display
#: name of a registered connector and is filled only for codes that can arise after resolution.
#: No sentence says that anything is connected, authorized, verified or available.
MESSAGES = {
    CONNECTOR_NOT_CONFIGURED:
        "No connector is registered for this capability, so nothing was retrieved.",
    AMBIGUOUS_CONNECTOR:
        "More than one connector is registered for this capability. Choose one; BusinessOps "
        "never chooses by order, vendor, recency or availability.",
    CAPABILITY_UNSUPPORTED:
        "{name} is an optional connector BusinessOps supports, but the capability asked for is "
        "not available in this version.",
    BINDING_MISMATCH:
        "{name}'s registry declaration, Connector Gate record, server declaration and tool "
        "grant do not agree exactly, so it was not used. Nothing was repaired.",
    CONNECTOR_UNAVAILABLE:
        "{name} could not be reached in this session. Nothing was retried or substituted.",
    CONNECTOR_NOT_AUTHORIZED:
        "{name} is an optional supported connector, but it is not connected. Connecting it is "
        "your choice and happens through your Claude platform's own connection mechanism for "
        "the server BusinessOps declares; BusinessOps does not start the sign-in or handle any "
        "credential.",
    AUTHENTICATION_FAILURE:
        "{name} rejected the sign-in. No message text from the system is carried.",
    AUTHORIZATION_FAILURE:
        "{name} did not accept the request for this account. BusinessOps does not request "
        "broader access.",
    TIMEOUT:
        "No reply arrived for this discovery operation within its bound.",
    TOOL_FAILURE:
        "The discovery tool failed without a code BusinessOps recognises. No message text is "
        "carried.",
    MALFORMED_RESPONSE:
        "The discovery reply did not follow the protocol for this operation, so the whole "
        "reply was refused and no partial catalogue was built.",
    OPERATION_UNKNOWN:
        "The reply names an operation that was never sealed or was already closed, so it was "
        "refused.",
    STALE_METADATA:
        "{name}'s discovery tool no longer matches its Connector Gate record, so the capability "
        "is unusable until it is measured and approved again.",
    METADATA_CONFLICT:
        "The system described one identifier in more than one way. Every variant is kept and "
        "flagged; none was chosen.",
    EXTERNAL_CONTENT_UNAVAILABLE:
        "At least one requested object type was not described by the system.",
    PRIVACY_RESTRICTED:
        "Content that a value-free catalogue may not hold was refused or dropped, and is noted "
        "by key name only.",
    INSUFFICIENT_DATA:
        "The system returned no catalogue entries for this scope. That is an absence of "
        "entries, never evidence that the system holds nothing.",
    REQUEST_INVALID:
        "The request was refused before any dispatch: it named something outside the closed "
        "vocabulary, an unregistered identity, or authority no caller may supply.",
    BLOCKED_PREREQUISITE:
        "Reading records from a connected system is not available in BusinessOps: it is blocked "
        "until its platform prerequisites are measured and its own decision is accepted.",
}

#: The refusal sentence for a write or administrative request. It rides on `request_invalid`
#: because no section H code describes an interaction that has no path at all, and it is worded
#: so that it cannot be read as the forged-request case it shares a code with.
NO_WRITE_PATH = ("BusinessOps has no write or administrative connector interaction. None exists "
                 "in v1, and no approval can unlock one.")


def message(code, name=None):
    """The fixed sentence for one failure code."""
    return MESSAGES[code].replace("{name}", name or "The connector")
