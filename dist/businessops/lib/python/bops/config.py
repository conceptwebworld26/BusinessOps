"""Configuration resolution with provenance.

Precedence (architecture.md section 14), highest wins:

    command argument -> project business context -> user business context -> shipped defaults

Every resolved value records *which layer supplied it*. That is not decoration: BusinessOps
has to be able to tell a user "the 5% materiality threshold came from your project context,
not from our default", and the evidence ledger needs the same information.
"""

import copy
import json
import os

from .errors import ConfigError
from . import jsonschema_mini

# Highest precedence first.
LAYERS = ("command", "project", "user", "default")

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULTS_PATH = os.path.join(_REPO_ROOT, "config", "businessops.defaults.json")
VOCABULARY_PATH = os.path.join(_REPO_ROOT, "config", "vocabulary.json")

PROJECT_DIR_NAME = ".businessops"
USER_DIR = os.path.join(os.path.expanduser("~"), ".claude", "businessops")

# Business Context sections that map onto configuration keys. Business Context IS the
# business-specific configuration layer (ADR-0011), so these sections override defaults.
_CONTEXT_TO_CONFIG = (
    (("reporting", "currency"), ("locale", "currency")),
    (("reporting", "number_format"), ("locale", "number_format")),
    (("reporting", "date_format"), ("locale", "date_format")),
    (("reporting", "fiscal_year_start"), ("locale", "fiscal_year_start")),
    (("reporting", "output_preferences", "directory"), ("output", "directory")),
    (("analysis", "materiality", "absolute_amount"), ("materiality", "absolute_amount")),
    (("analysis", "materiality", "percentage"), ("materiality", "percentage")),
    (("analysis", "materiality", "kpi_deviation"), ("materiality", "kpi_deviation")),
    (("analysis", "materiality", "revenue_percentage"), ("materiality", "revenue_percentage")),
    (("analysis", "materiality", "margin_percentage_points"), ("materiality", "margin_percentage_points")),
)


def load_json(path, what="file"):
    """Read a JSON file, or raise ConfigError naming the file and the problem."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise ConfigError("%s not found" % what, source=path)
    except json.JSONDecodeError as exc:
        raise ConfigError("%s is not valid JSON: %s" % (what, exc), source=path)


def load_defaults(path=None):
    """Load the shipped defaults — the lowest precedence layer."""
    return load_json(path or DEFAULTS_PATH, "shipped defaults")


def load_vocabulary(path=None):
    """Load the controlled vocabulary used by Business Context validation."""
    return load_json(path or VOCABULARY_PATH, "controlled vocabulary")


def _dig(mapping, keys):
    """Walk a nested dict; return None if any level is missing or not a dict."""
    node = mapping
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def _assign(mapping, keys, value):
    node = mapping
    for key in keys[:-1]:
        node = node.setdefault(key, {})
    node[keys[-1]] = value


def _flatten(mapping, prefix=""):
    """Flatten nested dicts to dotted keys. Lists are leaves (replaced, never merged)."""
    flat = {}
    for key, value in mapping.items():
        if key.startswith("$"):
            continue
        dotted = "%s.%s" % (prefix, key) if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, dotted))
        else:
            flat[dotted] = value
    return flat


class ResolvedConfig:
    """Merged configuration plus the layer each value came from."""

    def __init__(self, values, provenance):
        self._values = values
        self._provenance = provenance

    def get(self, dotted, fallback=None):
        node = self._values
        for key in dotted.split("."):
            if not isinstance(node, dict) or key not in node:
                return fallback
            node = node[key]
        return copy.deepcopy(node) if isinstance(node, (dict, list)) else node

    def source_of(self, dotted):
        """Which layer supplied this value: 'command', 'project', 'user' or 'default'."""
        return self._provenance.get(dotted)

    def as_dict(self):
        return copy.deepcopy(self._values)

    def provenance(self):
        return dict(self._provenance)

    def sources_used(self):
        return sorted(set(self._provenance.values()), key=LAYERS.index)

    def __repr__(self):
        return "ResolvedConfig(%d values, layers=%s)" % (len(self._provenance), self.sources_used())


def context_to_config_overrides(context):
    """Project the configuration-bearing parts of a Business Context into config shape."""
    overrides = {}
    if not isinstance(context, dict):
        return overrides
    for ctx_keys, cfg_keys in _CONTEXT_TO_CONFIG:
        value = _dig(context, ctx_keys)
        if value is not None:
            _assign(overrides, cfg_keys, value)
    return overrides


def resolve(defaults=None, user_context=None, project_context=None,
            command_args=None, schema=None):
    """Merge the four layers into a ResolvedConfig.

    `user_context` / `project_context` are Business Context documents; only their
    configuration-bearing fields participate. `command_args` is already in config shape
    (nested dict) and wins outright.
    """
    defaults = defaults if defaults is not None else load_defaults()

    contributions = [
        ("default", defaults),
        ("user", context_to_config_overrides(user_context or {})),
        ("project", context_to_config_overrides(project_context or {})),
        ("command", command_args or {}),
    ]

    merged, provenance = {}, {}
    for layer, payload in contributions:              # lowest precedence applied first
        for dotted, value in _flatten(payload).items():
            _assign(merged, dotted.split("."), value)
            provenance[dotted] = layer

    if schema is not None:
        errors = jsonschema_mini.validate(merged, schema)
        if errors:
            raise ConfigError("resolved configuration is invalid",
                              errors=[str(e) for e in errors])

    return ResolvedConfig(merged, provenance)


def project_context_path(start_dir=None):
    """Where the project-local Business Context lives for `start_dir`."""
    return os.path.join(os.path.abspath(start_dir or os.getcwd()),
                        PROJECT_DIR_NAME, "business_context.json")


def user_context_path():
    """Where the user-level Business Context lives."""
    return os.path.join(USER_DIR, "business_context.json")
