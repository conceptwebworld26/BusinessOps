"""Privacy classification of Business Context fields (ADR-0009, ADR-0011).

Classification is a property of the *data*, not of the query, so it is read straight from
the schema's `x-privacy` annotations rather than duplicated here. That keeps one home for
the rule: change the schema and the classification follows.

The class vocabulary is defined once in `bops.privacy.classes` and shared with dataset field
classification, so Business Context and ingested data cannot drift apart. See that module
for the six classes and how each maps to an ADR-0009 disclosure tier.

Business Context is not where credentials or customer records live, so the strictest classes
are rarely used here; they matter for dataset fields, classified in
`bops.privacy.sensitivity` from Milestone 3 onward.
"""

# The vocabulary itself lives in bops.privacy.classes so Business Context fields and dataset
# fields share one definition (ADR-0012). Re-exported here for the existing call sites.
from ..privacy.classes import (                                   # noqa: E402
    CONDITIONAL, DERIVED_SAFE, INTERNAL, NEVER, ORDER, PUBLIC, RESTRICTED,
    TIER_FOR_CLASS, rank,
)

DEFAULT_CLASS = INTERNAL   # anything unannotated is internal, never public


def classification_map(schema, _prefix="", _out=None):
    """Walk a JSON Schema and return {dotted field path: privacy class}.

    Inherits a parent object's class to its children unless the child overrides it.
    """
    out = {} if _out is None else _out
    if not isinstance(schema, dict):
        return out

    props = schema.get("properties")
    if isinstance(props, dict):
        for name, sub in props.items():
            path = "%s.%s" % (_prefix, name) if _prefix else name
            if isinstance(sub, dict):
                if "x-privacy" in sub:
                    out[path] = sub["x-privacy"]
                elif _prefix and _prefix in out:
                    out[path] = out[_prefix]
                classification_map(sub, path, out)
    return out


def classify(field_path, class_map):
    """Class for `field_path`, inheriting from the nearest classified ancestor."""
    if field_path in class_map:
        return class_map[field_path]
    parts = field_path.split(".")
    for cut in range(len(parts) - 1, 0, -1):
        parent = ".".join(parts[:cut])
        if parent in class_map:
            return class_map[parent]
    return DEFAULT_CLASS


def externalizable_fields(class_map):
    """Field paths safe to place in a Tier 0 research query."""
    return sorted(p for p, c in class_map.items() if c == PUBLIC)


def _dig(mapping, keys):
    node = mapping
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def externalizable_subset(context, class_map, include_conditional=False):
    """Extract only the values a Tier 0 query may use.

    `include_conditional` admits `conditional` fields (in practice `business_name`) and is
    set by the caller only for the named case that justifies it — analysing the user's own
    public company. It never defaults to true.
    """
    allowed = {PUBLIC} | ({CONDITIONAL} if include_conditional else set())
    subset = {}
    for path, cls in sorted(class_map.items()):
        if cls not in allowed:
            continue
        value = _dig(context, path.split("."))
        if value not in (None, [], {}, ""):
            subset[path] = value
    return subset


def redact(context, class_map, max_class=PUBLIC):
    """Return `context` with anything more sensitive than `max_class` removed.

    Used when a context needs to be shown, logged or passed to a component that must not
    see internal detail.
    """
    limit = rank(max_class)

    def _walk(node, prefix):
        if not isinstance(node, dict):
            return node
        kept = {}
        for key, value in node.items():
            path = "%s.%s" % (prefix, key) if prefix else key
            if isinstance(value, dict):
                child = _walk(value, path)
                if child:
                    kept[key] = child
            else:
                if rank(classify(path, class_map)) <= limit:
                    kept[key] = value
        return kept

    return _walk(context, "")
