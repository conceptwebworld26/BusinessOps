"""A small JSON Schema (draft-07 subset) validator.

BusinessOps is stdlib-first (CLAUDE.md section 4): the only managed dependency is the
Tier-2 xlsx reader. Pulling in `jsonschema` for config validation would breach that, so
this module implements exactly the keywords BusinessOps's own schemas use:

    type, required, properties, additionalProperties, enum, const,
    minimum, maximum, minLength, maxLength, pattern,
    items, minItems, maxItems, oneOf, anyOf,
    $ref / definitions (local references only)

Anything outside that set is ignored rather than silently "passed" — `unsupported_keywords`
reports what was skipped so a schema cannot quietly stop being enforced.

Errors are returned, never raised, so callers can present all problems at once.
"""

import re

SUPPORTED = frozenset({
    "type", "required", "properties", "additionalProperties", "enum", "const",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
    "minLength", "maxLength", "pattern", "items", "minItems", "maxItems", "contains",
    "oneOf", "anyOf", "$ref", "definitions",
    # annotation-only keywords: carry no constraint, so ignoring them is correct
    "$schema", "$id", "$comment", "title", "description", "default", "examples",
})

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


class ValidationError:
    """One schema violation, located by a JSON-pointer-ish path."""

    __slots__ = ("path", "message")

    def __init__(self, path, message):
        self.path = path or "<root>"
        self.message = message

    def __repr__(self):
        return "ValidationError(%r, %r)" % (self.path, self.message)

    def __str__(self):
        return "%s: %s" % (self.path, self.message)

    def __eq__(self, other):
        return (isinstance(other, ValidationError)
                and (self.path, self.message) == (other.path, other.message))


def _type_ok(value, expected):
    # bool is a subclass of int in Python; JSON Schema treats them as distinct.
    if expected in ("number", "integer") and isinstance(value, bool):
        return False
    py = _TYPES.get(expected)
    return py is not None and isinstance(value, py)


def unsupported_keywords(schema, _path="", _seen=None):
    """Report schema keywords this validator does not enforce.

    Guards against a schema silently losing enforcement when someone adds a keyword
    the validator has never heard of.
    """
    found = set()
    if _seen is None:
        _seen = set()
    if id(schema) in _seen or not isinstance(schema, dict):
        return found
    _seen.add(id(schema))

    for key, sub in schema.items():
        if key.startswith("x-"):          # our own annotations, intentionally inert
            continue
        if key not in SUPPORTED:
            found.add(key if not _path else "%s.%s" % (_path, key))
        if key == "properties" and isinstance(sub, dict):
            for name, psub in sub.items():
                found |= unsupported_keywords(psub, "%s.%s" % (_path, name) if _path else name, _seen)
        elif key in ("items", "additionalProperties", "contains") and isinstance(sub, dict):
            found |= unsupported_keywords(sub, _path, _seen)
        elif key in ("oneOf", "anyOf") and isinstance(sub, list):
            for s in sub:
                found |= unsupported_keywords(s, _path, _seen)
        elif key == "definitions" and isinstance(sub, dict):
            for name, dsub in sub.items():
                found |= unsupported_keywords(dsub, "definitions.%s" % name, _seen)
    return found


def resolve_ref(ref, root):
    """Resolve a local JSON pointer such as `#/definitions/finding`."""
    if not ref.startswith("#/"):
        raise ValueError(
            "only local references are supported; %r would require a network fetch" % ref)
    node = root
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            raise ValueError("reference %r does not resolve" % ref)
        node = node[part]
    return node


def validate(instance, schema, path="", root=None):
    """Validate `instance` against `schema`. Returns a list of ValidationError."""
    errors = []

    if not isinstance(schema, dict):
        return errors

    if root is None:
        root = schema

    if "$ref" in schema:
        try:
            target = resolve_ref(schema["$ref"], root)
        except ValueError as exc:
            return [ValidationError(path, str(exc))]
        merged = {k: v for k, v in schema.items() if k != "$ref"}
        if merged:
            errors.extend(validate(instance, merged, path, root))
        return errors + validate(instance, target, path, root)

    if "type" in schema:
        expected = schema["type"]
        options = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(instance, t) for t in options):
            actual = type(instance).__name__
            errors.append(ValidationError(path, "expected type %s, got %s" % ("/".join(options), actual)))
            return errors  # further checks would be meaningless on the wrong type

    if "const" in schema and instance != schema["const"]:
        errors.append(ValidationError(path, "must equal %r" % (schema["const"],)))

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(ValidationError(
            path, "must be one of %s (got %r)" % (", ".join(map(repr, schema["enum"])), instance)))

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(ValidationError(path, "shorter than minLength %d" % schema["minLength"]))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(ValidationError(path, "longer than maxLength %d" % schema["maxLength"]))
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(ValidationError(path, "does not match pattern %s" % schema["pattern"]))

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(ValidationError(path, "less than minimum %s" % schema["minimum"]))
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(ValidationError(path, "greater than maximum %s" % schema["maximum"]))
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append(ValidationError(path, "not greater than %s" % schema["exclusiveMinimum"]))
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errors.append(ValidationError(path, "not less than %s" % schema["exclusiveMaximum"]))

    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                errors.append(ValidationError(path, "missing required property %r" % name))

        props = schema.get("properties", {})
        for name, value in instance.items():
            child = "%s.%s" % (path, name) if path else name
            if name in props:
                errors.extend(validate(value, props[name], child, root))
            else:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errors.append(ValidationError(child, "unknown property %r is not allowed" % name))
                elif isinstance(extra, dict):
                    errors.extend(validate(value, extra, child, root))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(ValidationError(path, "fewer than minItems %d" % schema["minItems"]))
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(ValidationError(path, "more than maxItems %d" % schema["maxItems"]))
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(instance):
                errors.extend(validate(item, item_schema, "%s[%d]" % (path, i), root))
        contains = schema.get("contains")
        if isinstance(contains, dict):
            # "at least one element matches". Needed to say that a statement's provenance
            # array must hold an internal reference; `items` would demand it of all of
            # them, which is a different and wrong rule.
            if not any(not validate(entry, contains, path, root) for entry in instance):
                errors.append(ValidationError(
                    path, "no element matches the required `contains` schema"))

    if "oneOf" in schema:
        matches = sum(1 for s in schema["oneOf"]
                      if not validate(instance, s, path, root))
        if matches != 1:
            errors.append(ValidationError(path, "must match exactly one of oneOf (matched %d)" % matches))

    if "anyOf" in schema:
        if not any(not validate(instance, s, path, root) for s in schema["anyOf"]):
            errors.append(ValidationError(path, "does not match any of anyOf"))

    return errors
