"""Privacy-preserving aggregation primitives (ADR-0009 Tier 1 foundation).

The reusable building blocks a later intelligence layer will consume to decide whether a
derived statistic may accompany an external query. **Nothing here performs external
research or makes any network call** — that is Milestone 9.

ADR-0009 Tier 1 admits a derived value only if it passes all four checks:

  1. aggregation floor — derived from at least `k` underlying entities (default 5)
  2. banded, not exact — rates and ratios pass as-is; absolute monetary levels never do
  3. whole-query re-identification check — attribute *combinations* can identify a company
     even when each attribute looks harmless on its own
  4. not on the ADR-0009 Tier 3 list

This module implements 1, 2 and 3, plus the banding helpers. Check 4 is the field
classification in `sensitivity.py`.
"""

from decimal import Decimal, ROUND_HALF_UP

from .classes import (
    DEFAULT_CLASS, DERIVED_SAFE, NEVER, PUBLIC, is_externalizable, most_sensitive,
    permitted_at_tier,
)

#: The k-anonymity floor. Owner decision (2026-09-10): this is a **hard minimum**, not a
#: default a caller may lower. Configuration may raise it; nothing may take it below 5.
DEFAULT_K = 5
MINIMUM_K = 5

EXACT = "exact"
BANDED = "banded"
RATE = "rate"

#: The tier a Tier-1 assessment is asking about. Named rather than inlined so the class
#: rule and the four checks are visibly asking the same question.
TIER_1 = 1

#: Sentinel for "sensitivity was never established". Distinct from any real class, so a
#: descriptor that was never classified cannot be mistaken for one that was classified
#: permissively (owner decision, F-4).
UNRESOLVED = "unresolved"


def resolve_k_floor(requested=None):
    """The effective k-floor. Raising it is permitted; lowering it is not.

    A configurable floor that can be configured *downward* is not a floor. Callers that
    pass a smaller value get the hard minimum, not their request, so no configuration path
    and no caller argument can weaken k-anonymity.
    """
    if requested is None:
        return DEFAULT_K
    try:
        value = int(requested)
    except (TypeError, ValueError):
        return DEFAULT_K
    return value if value > MINIMUM_K else MINIMUM_K


def _dec(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


class AggregateDescriptor:
    """A derived statistic and everything needed to judge whether it may be disclosed."""

    __slots__ = ("label", "value", "value_kind", "entity_count", "source_columns",
                 "source_sensitivity", "notes")

    def __init__(self, label, value, value_kind, entity_count,
                 source_columns=(), source_sensitivity=UNRESOLVED, notes=None):
        """`source_sensitivity` is **not** optional in effect.

        It once defaulted to `derived_safe`, which is more permissive than the
        project-wide default of `internal` and meant a caller who simply forgot to classify
        an aggregate got one that passed the Tier-3 check. The default is now `unresolved`,
        which no tier admits: an unclassified aggregate fails closed and must be resolved
        before it can accompany an external query (owner decision, F-4).

        Use `from_fields()` to derive it honestly from the source columns.
        """
        self.label = label
        self.value = value
        self.value_kind = value_kind          # EXACT | BANDED | RATE
        self.entity_count = entity_count
        self.source_columns = list(source_columns)
        self.source_sensitivity = source_sensitivity
        self.notes = list(notes or [])

    @classmethod
    def from_fields(cls, label, value, value_kind, entity_count, field_classes,
                    source_columns=(), notes=None):
        """Build with sensitivity derived from the source fields.

        A derived statistic is exactly as sensitive as the most sensitive field behind it,
        which is what `most_sensitive()` already encodes. Deriving it here means the honest
        answer is also the convenient one. An empty classification is not treated as
        harmless: it resolves to the project default (`internal`), not to `derived_safe`.
        """
        classes = list(field_classes)
        sensitivity = most_sensitive(classes) if classes else DEFAULT_CLASS
        return cls(label, value, value_kind, entity_count,
                   source_columns=source_columns, source_sensitivity=sensitivity,
                   notes=notes)

    @property
    def sensitivity_resolved(self):
        return self.source_sensitivity != UNRESOLVED

    def as_dict(self):
        return {"label": self.label,
                "value": str(self.value) if isinstance(self.value, Decimal) else self.value,
                "value_kind": self.value_kind, "entity_count": self.entity_count,
                "source_columns": self.source_columns,
                "source_sensitivity": self.source_sensitivity, "notes": self.notes}

    def __repr__(self):
        return "AggregateDescriptor(%s=%s, n=%s, %s)" % (
            self.label, self.value, self.entity_count, self.value_kind)


class DisclosureAssessment:
    """Whether one aggregate may be disclosed, and exactly why or why not."""

    __slots__ = ("descriptor", "permitted", "tier", "failed_checks", "reasons")

    def __init__(self, descriptor, permitted, tier, failed_checks, reasons):
        self.descriptor = descriptor
        self.permitted = permitted
        self.tier = tier
        self.failed_checks = list(failed_checks)
        self.reasons = list(reasons)

    def as_dict(self):
        return {"aggregate": self.descriptor.as_dict(), "permitted": self.permitted,
                "tier": self.tier, "failed_checks": self.failed_checks,
                "reasons": self.reasons}

    def __repr__(self):
        return "DisclosureAssessment(%s, permitted=%s, tier=%s)" % (
            self.descriptor.label, self.permitted, self.tier)


def count_entities(rows, key_column):
    """Distinct non-empty entities behind an aggregate — the input to the k floor."""
    return len({row.get(key_column) for row in rows
                if row.get(key_column) not in (None, "")})


def band_count(count):
    """Bucket a headcount or entity count. Bands, never exact figures."""
    for upper, label in ((9, "1-9"), (49, "10-49"), (199, "50-199"), (499, "200-499"),
                         (999, "500-999"), (4999, "1000-4999")):
        if count <= upper:
            return label
    return "5000+"


def band_amount(amount, currency="USD"):
    """Bucket a monetary level onto an order-of-magnitude band."""
    value = abs(_dec(amount))
    bands = [
        (Decimal("100000"), "under 100k"),
        (Decimal("500000"), "100k-500k"),
        (Decimal("1000000"), "500k-1m"),
        (Decimal("5000000"), "1m-5m"),
        (Decimal("10000000"), "5m-10m"),
        (Decimal("50000000"), "10m-50m"),
    ]
    for upper, label in bands:
        if value < upper:
            return "%s %s" % (currency, label)
    return "%s over 50m" % currency


def as_rate(numerator, denominator, places=1):
    """A ratio expressed as a percentage — non-identifying, so Tier 1 accepts it as-is."""
    if denominator in (None, 0):
        return None
    quant = Decimal("1") if places == 0 else Decimal("0." + "0" * places)
    return (_dec(numerator) / _dec(denominator) * Decimal("100")).quantize(
        quant, rounding=ROUND_HALF_UP)


def rate_descriptor(label, numerator, denominator, entity_count,
                    source_columns=(), places=1):
    """Build a rate aggregate — the shape that passes Tier 1 most easily."""
    return AggregateDescriptor(
        label, as_rate(numerator, denominator, places), RATE, entity_count,
        source_columns, DERIVED_SAFE,
        notes=["expressed as a rate, so it carries no absolute monetary level"])


def banded_amount_descriptor(label, amount, entity_count, currency="USD",
                             source_columns=()):
    """Build a banded monetary aggregate. Exact levels are never Tier 1 eligible."""
    return AggregateDescriptor(
        label, band_amount(amount, currency), BANDED, entity_count,
        source_columns, DERIVED_SAFE,
        notes=["banded to an order of magnitude; the exact figure is not disclosed"])


# ---------------------------------------------------------------------------
# Re-identification
# ---------------------------------------------------------------------------

# Attributes that narrow an organisation when combined. Each is harmless alone; together
# they can single out one company, which is why the check runs on the whole query.
NARROWING_ATTRIBUTES = frozenset({
    "industry", "business_model", "size_band", "geographic_market", "region",
    "product_category", "revenue_band", "founding_year", "employee_band",
})

# Attributes so specific that two of them plus an industry is already close to naming a firm.
HIGHLY_NARROWING = frozenset({"revenue_band", "employee_band", "founding_year"})

DEFAULT_MAX_NARROWING = 3


def assess_reidentification(attributes, max_narrowing=DEFAULT_MAX_NARROWING):
    """Judge a *whole* set of query attributes for re-identification risk.

    Evaluating field by field is what makes naive anonymisation fail: industry alone is
    fine, geography alone is fine, and industry + micro-geography + a narrow revenue band
    can be one company.
    """
    present = sorted(a for a in attributes if a in NARROWING_ATTRIBUTES)
    highly = sorted(a for a in present if a in HIGHLY_NARROWING)

    reasons = []
    risky = False

    if len(present) > max_narrowing:
        risky = True
        reasons.append(
            "%d narrowing attributes combined (limit %d): %s"
            % (len(present), max_narrowing, ", ".join(present)))
    if len(highly) >= 2:
        risky = True
        reasons.append("two or more highly narrowing attributes: %s" % ", ".join(highly))
    if not reasons:
        reasons.append("%d narrowing attribute(s); within the limit of %d"
                       % (len(present), max_narrowing))

    return {"risky": risky, "narrowing_attributes": present,
            "highly_narrowing": highly, "reasons": reasons}


# ---------------------------------------------------------------------------
# The Tier 1 gate
# ---------------------------------------------------------------------------

def assess_disclosure(descriptor, k_floor=DEFAULT_K, query_attributes=(),
                      max_narrowing=DEFAULT_MAX_NARROWING, accumulated=None):
    """The authoritative disclosure decision for one aggregate.

    **One decision, not two halves.** This once applied only the four ADR-0009 Tier 1
    checks and then returned `tier = 1` for anything that passed — without asking whether
    the field's *class* is permitted at Tier 1 at all. A `restricted` aggregate, which
    `TIER_FOR_CLASS` says needs Tier 2, therefore came back permitted at Tier 1. The class
    rule and the four checks are two halves of one question and are now joined here (owner
    decision, closing F-2 and F-3). There is no second disclosure decision anywhere.

    Passing therefore requires **both**:

      * every disclosed value's sensitivity class permits the tier being asked about, and
      * all four Tier-1 checks pass.

    `accumulated` is an optional `DisclosureAccumulator` for the active research operation.
    Re-identification is judged against this query *plus everything already disclosed*, so
    a sequence of individually safe queries cannot become collectively identifying.

    `k_floor` may raise the floor but never lower it; see `resolve_k_floor`.
    """
    failed, reasons = [], []
    k_floor = resolve_k_floor(k_floor)

    # 0. An aggregate whose sensitivity was never established is not assumed harmless.
    if not descriptor.sensitivity_resolved:
        return DisclosureAssessment(
            descriptor, False, None, ["sensitivity_unresolved"],
            ["The sensitivity of the source fields was never established. An unclassified "
             "aggregate is not treated as safe; classify it (see "
             "AggregateDescriptor.from_fields) before it may accompany an external query."])

    # 4. Tier 3 material is refused before anything else is considered.
    if not is_externalizable(descriptor.source_sensitivity):
        return DisclosureAssessment(
            descriptor, False, None, ["never_externalizable"],
            ["Source fields are classified %r, which has no approval path at any tier."
             % NEVER])

    # 0b. The class rule. Asked *before* the four checks so a class that cannot reach
    # Tier 1 is never reported as "passed everything, therefore Tier 1".
    if not permitted_at_tier(descriptor.source_sensitivity, TIER_1):
        failed.append("class_not_permitted_at_tier")
        reasons.append(
            "Source fields are classified %r, which requires explicit approval (Tier 2); "
            "Tier 1 carries only public and derived-safe values."
            % descriptor.source_sensitivity)
    else:
        reasons.append("Class %r is permitted at Tier 1."
                       % descriptor.source_sensitivity)

    # 1. aggregation floor
    if descriptor.entity_count is None:
        failed.append("aggregation_floor")
        reasons.append("The number of underlying entities is unknown, so the k>=%d floor "
                       "cannot be verified." % k_floor)
    elif descriptor.entity_count < k_floor:
        failed.append("aggregation_floor")
        reasons.append("Aggregated over only %d entities; the floor is %d. A smaller group "
                       "can expose an individual." % (descriptor.entity_count, k_floor))
    else:
        reasons.append("Aggregated over %d entities, at or above the k>=%d floor."
                       % (descriptor.entity_count, k_floor))

    # 2. banded, not exact
    if descriptor.value_kind == EXACT:
        failed.append("banding")
        reasons.append("The value is an exact figure. Absolute monetary levels never pass "
                       "Tier 1; band it or express it as a rate.")
    else:
        reasons.append("Value is %r, which carries no exact absolute level."
                       % descriptor.value_kind)

    # 3. whole-query re-identification, judged against everything already disclosed in
    # this operation rather than against this query alone.
    effective_attributes = tuple(query_attributes)
    if accumulated is not None:
        effective_attributes = accumulated.combined_with(query_attributes)

    reidentification = assess_reidentification(effective_attributes, max_narrowing)
    if reidentification["risky"]:
        failed.append("reidentification")
        reasons.extend(reidentification["reasons"])
        if accumulated is not None and accumulated.attributes:
            reasons.append(
                "Judged against the %d attribute(s) already disclosed in this research "
                "operation, not this query alone: %s."
                % (len(accumulated.attributes), ", ".join(sorted(accumulated.attributes))))
    else:
        reasons.append(reidentification["reasons"][0])

    permitted = not failed
    # The tier follows the data's own class, never the fact that the checks passed.
    tier = None
    if permitted:
        tier = 0 if descriptor.source_sensitivity == PUBLIC else TIER_1
    return DisclosureAssessment(descriptor, permitted, tier, failed, reasons)


# ---------------------------------------------------------------------------
# Cross-query accumulation
# ---------------------------------------------------------------------------

class DisclosureAccumulator:
    """Narrowing attributes disclosed so far in one active research operation.

    ADR-0009 requires the re-identification check to evaluate a query *as a whole* rather
    than field by field, because industry + micro-geography + a narrow revenue band can
    identify a company even when each part looks harmless. The same reasoning applies one
    level up: three queries carrying two narrowing attributes each disclose six, and an
    attacker - or an ordinary user asking follow-up questions - reads them together.
    Judging every query in isolation would let a sequence of individually safe queries
    become collectively identifying (owner decision, 2026-09-10).

    **What is accumulated.** Only the narrowing attribute *names* that were actually
    disclosed, plus a count of permitted disclosures. No values, no query text, no results,
    no identifiers - nothing that would make this a profile of the user or their business.

    **When it starts.** One accumulator per research operation, created by the caller when
    the operation begins.

    **When it resets.** When the operation ends, or explicitly via `reset()`. It is
    deliberately not persisted: it is in-memory state belonging to one operation, never a
    durable profile carried across unrelated conversations. Nothing here writes to disk.

    **Determinism.** Attributes are held in a set and always read back sorted, so the same
    sequence of disclosures produces the same decisions and the same reasons on every run.
    """

    __slots__ = ("operation", "attributes", "disclosures")

    def __init__(self, operation=None, attributes=(), disclosures=0):
        self.operation = operation
        self.attributes = set(attributes)
        self.disclosures = disclosures

    def combined_with(self, query_attributes):
        """This query's attributes plus everything already disclosed, sorted."""
        return tuple(sorted(self.attributes | set(query_attributes)))

    def would_be_risky(self, query_attributes, max_narrowing=None):
        """Assess a prospective query without recording it."""
        limit = (DEFAULT_MAX_NARROWING if max_narrowing is None else max_narrowing)
        return assess_reidentification(self.combined_with(query_attributes), limit)

    def record(self, query_attributes):
        """Register a disclosure that was actually permitted.

        Only permitted disclosures are recorded. A refused query disclosed nothing, so
        counting it would tighten the gate on the basis of information that never left.
        """
        self.attributes |= {a for a in query_attributes if a in NARROWING_ATTRIBUTES}
        self.disclosures += 1
        return self

    def reset(self):
        """End the operation's accumulated state."""
        self.attributes = set()
        self.disclosures = 0
        return self

    def as_dict(self):
        return {"operation": self.operation,
                "attributes": sorted(self.attributes),
                "disclosures": self.disclosures}

    def __repr__(self):
        return "DisclosureAccumulator(%s, %d attrs, %d disclosures)" % (
            self.operation, len(self.attributes), self.disclosures)
