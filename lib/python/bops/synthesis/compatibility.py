"""Whether two figures measure the same quantity, and may therefore be related at all.

The single most dangerous operation in cross-domain synthesis is putting an internal
number and an external number in the same sentence. "Our revenue grew 12% against a market
growing 4%" is either the most useful line in a report or a fabrication, and which one it
is depends entirely on whether the two figures share a definition, a period, a geography,
a currency, a unit, a scope and a methodology.

So the test here is deliberately strict in one specific way: **an unstated dimension fails
the check on unknown, not on assumed match.** An absent definition is not a matching
definition. This is the same rule `skills/bops-industry-research/SKILL.md` applies to two
published market sizes, applied by code rather than by memory.

Nothing in this module converts anything. There is no currency conversion, no unit
scaling, no period re-basing and no midpoint. A mismatch is reported and the values stay
apart; that is the whole remedy.
"""

from .contract import DIMENSIONS

COMPATIBLE = "compatible"
INCOMPATIBLE = "incompatible"
UNKNOWN = "unknown"

STATUSES = (COMPATIBLE, INCOMPATIBLE, UNKNOWN)

#: Stated once so a test can assert it and a reader cannot miss it: this module never
#: converts a currency, rescales a unit, re-bases a period or interpolates a value.
NEVER_CONVERTS = True

REASON = {
    COMPATIBLE: "All checked dimensions are stated and match; the values measure the "
                "same quantity and may be related.",
    INCOMPATIBLE: "At least one dimension differs. The values measure different "
                  "quantities and are reported separately, never combined.",
    UNKNOWN: "At least one dimension is unstated. The check fails on unknown rather "
             "than assuming a match; an absent definition is not a matching definition.",
}


def _normalise(value):
    """Compare text case- and whitespace-insensitively; compare everything else as-is."""
    if value is None:
        return None
    if isinstance(value, str):
        collapsed = " ".join(value.split()).strip().lower()
        return collapsed or None
    return value


def _dimensions_of(subject):
    """Accept a `SynthesisItem`, a plain mapping, or anything exposing `.dimensions`."""
    if hasattr(subject, "dimensions"):
        return dict(subject.dimensions)
    if isinstance(subject, dict):
        return dict((d, subject.get(d)) for d in DIMENSIONS)
    raise TypeError("cannot read comparability dimensions from %r" % (subject,))


def compare(left, right, dimensions=DIMENSIONS):
    """Test whether two value-bearing statements may be related.

    Returns a record rather than a bool, because the caller has to report *which*
    dimension failed: "not comparable" is unhelpful, "one is global and the other is
    UK-only" is the finding.
    """
    left_dims = _dimensions_of(left)
    right_dims = _dimensions_of(right)

    matched, mismatched, unknown = [], [], []
    for dimension in dimensions:
        a = _normalise(left_dims.get(dimension))
        b = _normalise(right_dims.get(dimension))
        if a is None or b is None:
            unknown.append({"dimension": dimension,
                            "left": left_dims.get(dimension),
                            "right": right_dims.get(dimension),
                            "reason": "not stated on %s" % (
                                "both sides" if a is None and b is None
                                else ("the left value" if a is None
                                      else "the right value"))})
        elif a != b:
            mismatched.append({"dimension": dimension,
                               "left": left_dims.get(dimension),
                               "right": right_dims.get(dimension)})
        else:
            matched.append(dimension)

    if mismatched:
        status = INCOMPATIBLE
    elif unknown:
        status = UNKNOWN
    else:
        status = COMPATIBLE

    return {
        "status": status,
        "checked": list(dimensions),
        "matched": matched,
        "mismatched": mismatched,
        "unknown": unknown,
        "reason": REASON[status],
        "converted": False,
    }


def may_combine(result):
    """True only for a fully checked, fully matching comparison."""
    return result["status"] == COMPATIBLE


def mismatch_summary(result):
    """A one-line, deterministic description of why two values stayed apart."""
    if result["status"] == COMPATIBLE:
        return None
    parts = []
    for entry in result["mismatched"]:
        parts.append("%s differs (%s vs %s)"
                     % (entry["dimension"], entry["left"], entry["right"]))
    for entry in result["unknown"]:
        parts.append("%s %s" % (entry["dimension"], entry["reason"]))
    return "; ".join(parts)
