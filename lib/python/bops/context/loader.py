"""Loading, validating and resolving Business Context (ADR-0011).

The governing rule is CLAUDE.md's: **never guess**. Absent context is represented
explicitly as a `MissingField` so a command can ask a precise question or narrow its
scope. Nothing here infers a business model from column names or fills a default that
pretends to be a fact.
"""

import copy
import os

from .. import config as config_mod
from .. import jsonschema_mini
from ..errors import ConfigError, MissingContextError, VocabularyError
from . import privacy

SCHEMA_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
    "schemas", "business_context.schema.json")

SCHEMA_VERSION = "1.0.0"

# Fields whose absence changes what BusinessOps can do, and what each unlocks.
CAPABILITY_FIELDS = {
    "identity.business_model": "KPI relevance filtering",
    "identity.industry": "external benchmark queries",
    "reporting.currency": "monetary formatting",
    "reporting.fiscal_year_start": "period alignment",
}


class MissingField:
    """An explicitly absent context field. Never a substitute value."""

    __slots__ = ("path", "unlocks")

    def __init__(self, path, unlocks=None):
        self.path = path
        self.unlocks = unlocks

    def __repr__(self):
        return "MissingField(%r)" % self.path

    def __eq__(self, other):
        return isinstance(other, MissingField) and other.path == self.path

    def __hash__(self):
        return hash(self.path)


class Contradiction:
    """A conflict between stated context and observed data.

    Surfaced as a quality finding; never silently resolved in either direction.
    """

    __slots__ = ("field", "context_value", "observed_value", "detail")

    def __init__(self, field, context_value, observed_value, detail=None):
        self.field = field
        self.context_value = context_value
        self.observed_value = observed_value
        self.detail = detail

    def __repr__(self):
        return "Contradiction(%s: context=%r observed=%r)" % (
            self.field, self.context_value, self.observed_value)

    def message(self):
        base = ("Business Context says %s is %r, but the data indicates %r."
                % (self.field, self.context_value, self.observed_value))
        return "%s %s" % (base, self.detail) if self.detail else base


def load_schema(path=None):
    return config_mod.load_json(path or SCHEMA_PATH, "business context schema")


def _dig(mapping, keys):
    node = mapping
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def _vocabulary_paths(schema, _prefix="", _out=None):
    """{dotted field path: vocabulary name} from the schema's x-vocabulary annotations."""
    out = {} if _out is None else _out
    props = schema.get("properties") if isinstance(schema, dict) else None
    if isinstance(props, dict):
        for name, sub in props.items():
            path = "%s.%s" % (_prefix, name) if _prefix else name
            if isinstance(sub, dict):
                if "x-vocabulary" in sub:
                    out[path] = sub["x-vocabulary"]
                _vocabulary_paths(sub, path, out)
    return out


def _allowed_values(vocabulary, name):
    entry = vocabulary.get(name)
    if not isinstance(entry, dict):
        return None
    values = entry.get("values")
    if isinstance(values, dict):
        return sorted(values.keys())
    if isinstance(values, list):
        return sorted(values)
    return None


def validate(context, schema=None, vocabulary=None, source=None):
    """Validate a Business Context. Returns a list of message strings (empty = valid).

    Structural errors and vocabulary violations are reported together so the user sees
    every problem at once rather than one per round trip.
    """
    schema = schema if schema is not None else load_schema()
    vocabulary = vocabulary if vocabulary is not None else config_mod.load_vocabulary()

    if not isinstance(context, dict):
        return ["business context must be a JSON object, got %s" % type(context).__name__]

    messages = [str(e) for e in jsonschema_mini.validate(context, schema)]

    for path, vocab_name in sorted(_vocabulary_paths(schema).items()):
        value = _dig(context, path.split("."))
        if value is None:
            continue
        allowed = _allowed_values(vocabulary, vocab_name)
        if allowed is None:
            messages.append("%s: vocabulary %r is not defined" % (path, vocab_name))
        elif value not in allowed:
            messages.append(
                "%s: %r is not in the controlled vocabulary %r. Allowed: %s. "
                "Ask the user rather than choosing the nearest match."
                % (path, value, vocab_name, ", ".join(allowed)))
    return messages


def validate_or_raise(context, schema=None, vocabulary=None, source=None):
    messages = validate(context, schema, vocabulary, source)
    if messages:
        vocab_issue = any("controlled vocabulary" in m for m in messages)
        error_cls = VocabularyError if vocab_issue else ConfigError
        raise error_cls("business context is invalid", errors=messages, source=source)
    return True


def load_file(path, schema=None, vocabulary=None):
    """Load and validate one context file. Returns None if the file does not exist."""
    if not os.path.exists(path):
        return None
    context = config_mod.load_json(path, "business context")
    validate_or_raise(context, schema, vocabulary, source=path)
    return context


def _deep_merge(base, overlay):
    merged = copy.deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


class BusinessContext:
    """A resolved Business Context, with provenance, gaps and privacy classification."""

    def __init__(self, values, provenance, class_map, sources):
        self.values = values
        self.provenance = provenance
        self.class_map = class_map
        self.sources = sources

    # -- access -------------------------------------------------------------

    def get(self, dotted, default=None):
        value = _dig(self.values, dotted.split("."))
        return default if value is None else value

    def source_of(self, dotted):
        """'command', 'project' or 'user' — or None if the field is absent."""
        return self.provenance.get(dotted)

    def has(self, dotted):
        return _dig(self.values, dotted.split(".")) is not None

    # -- gaps ---------------------------------------------------------------

    def missing(self, fields=None):
        """Explicitly absent capability fields, as MissingField markers."""
        paths = fields if fields is not None else sorted(CAPABILITY_FIELDS)
        return [MissingField(p, CAPABILITY_FIELDS.get(p)) for p in paths if not self.has(p)]

    def require(self, fields, purpose=None):
        """Raise MissingContextError unless every field is present."""
        absent = [f for f in fields if not self.has(f)]
        if absent:
            raise MissingContextError(absent, purpose)
        return True

    def relevance_filtering_enabled(self):
        """KPI relevance filtering needs a business model. Without it, nothing is
        suppressed and the output says so (ADR-0011)."""
        return self.has("identity.business_model")

    # -- privacy ------------------------------------------------------------

    def privacy_class(self, dotted):
        return privacy.classify(dotted, self.class_map)

    def externalizable(self, include_business_name=False):
        """Values a Tier 0 research query may use (ADR-0009)."""
        return privacy.externalizable_subset(
            self.values, self.class_map, include_conditional=include_business_name)

    def redacted(self, max_class=privacy.PUBLIC):
        return privacy.redact(self.values, self.class_map, max_class)

    # -- data cross-check ---------------------------------------------------

    def detect_contradictions(self, observations):
        """Compare stated context against observed data facts.

        `observations` maps a context field path to what the data actually shows, e.g.
        {"reporting.currency": "USD"}. Returns Contradiction objects; the caller raises
        them as quality findings. Context is never silently overridden by data, nor data
        by context.
        """
        found = []
        for path, observed in sorted(observations.items()):
            stated = _dig(self.values, path.split("."))
            if stated is None or observed is None:
                continue
            if isinstance(stated, str) and isinstance(observed, str):
                if stated.strip().lower() == observed.strip().lower():
                    continue
            elif stated == observed:
                continue
            detail = None
            if path == "reporting.currency":
                detail = ("Monetary figures cannot be trusted until this is resolved; "
                          "no conversion is applied automatically.")
            found.append(Contradiction(path, stated, observed, detail))
        return found

    def summary(self):
        return {
            "sources": list(self.sources),
            "fields_set": len(self.provenance),
            "missing": [m.path for m in self.missing()],
            "relevance_filtering": self.relevance_filtering_enabled(),
            "externalizable_fields": sorted(self.externalizable().keys()),
        }


def resolve(project_dir=None, user_dir=None, overrides=None,
            schema=None, vocabulary=None, load_files=True):
    """Resolve Business Context across its layers.

    Precedence, highest first: command overrides -> project-local -> user-level.
    Project-local wins because context belongs with the data it describes, and a
    consultant analysing several businesses must not have one bleed into another.
    """
    schema = schema if schema is not None else load_schema()
    vocabulary = vocabulary if vocabulary is not None else config_mod.load_vocabulary()
    class_map = privacy.classification_map(schema)

    user_ctx = project_ctx = None
    if load_files:
        user_path = (os.path.join(user_dir, "business_context.json")
                     if user_dir else config_mod.user_context_path())
        project_path = config_mod.project_context_path(project_dir)
        user_ctx = load_file(user_path, schema, vocabulary)
        project_ctx = load_file(project_path, schema, vocabulary)

    if overrides:
        validate_or_raise(overrides, schema, vocabulary, source="command override")

    merged, provenance, sources = {}, {}, []
    for layer, payload in (("user", user_ctx), ("project", project_ctx), ("command", overrides)):
        if not payload:
            continue
        sources.append(layer)
        merged = _deep_merge(merged, payload)
        for dotted in config_mod._flatten(payload):
            provenance[dotted] = layer

    return BusinessContext(merged, provenance, class_map, sources)
