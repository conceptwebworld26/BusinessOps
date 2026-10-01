"""The KPI contract: how a metric declares itself, and how a result explains itself.

A KPI definition is data, not code with a docstring. The registry is the authoritative
statement of what a metric means, what it needs, and when it does not apply — so a skill or
command never has to restate a formula, and a result can always answer *why* it is absent.

Result buckets
--------------
The M5 brief names four:

    available · unavailable · not_applicable · insufficient_data

`architecture.md` section 6 names four slightly different ones:

    computed · partial · unavailable · not_applicable

These are reconciled rather than silently merged, because `partial` and `insufficient_data`
are genuinely different states: `partial` produced a value from incomplete periods, while
`insufficient_data` produced nothing because the history is too short. Both are kept, and
`COMPUTED` is retained as an alias of `AVAILABLE` so earlier callers keep working. The
discrepancy is reported for review rather than resolved here.

A result never returns null or zero to mean "missing". Every non-available bucket carries a
reason naming the specific requirement that failed.
"""

from decimal import Decimal

# -- result buckets ---------------------------------------------------------

AVAILABLE = "available"            # inputs present, model-relevant, value produced
UNAVAILABLE = "unavailable"        # a required input is absent or unusable
NOT_APPLICABLE = "not_applicable"  # inputs may exist, but the business model makes it moot
INSUFFICIENT_DATA = "insufficient_data"   # inputs present, history too short to compute
PARTIAL = "partial"                # value produced, but from incomplete periods

# Retained alias: earlier milestones and the renderer refer to COMPUTED.
COMPUTED = AVAILABLE

BUCKETS = (AVAILABLE, UNAVAILABLE, NOT_APPLICABLE, INSUFFICIENT_DATA, PARTIAL)
VALUE_BEARING = (AVAILABLE, PARTIAL)

ALL_MODELS = "*"

# -- units ------------------------------------------------------------------
#
# A unit names a **quantity type** and nothing else (ADR-0025). It does not carry a
# magnitude, a currency code or a display label: the magnitude lives in the `Decimal`
# value in base units, the currency code lives in a separate `currency` field, and
# formatting lives in `render`. `"USD billion"` is therefore not a unit - it is three
# facts, two of which are already carried elsewhere, and encoding them here is what let a
# value of 3400000000 compare as equal to one of 282.8 under a shared `billion` label.

CURRENCY = "currency"
PERCENT = "percent"
RATIO = "ratio"
COUNT = "count"
DAYS = "days"

#: A change **in** a rate, as opposed to a rate. Margin moving from 37% to 34% is -2.85
#: percentage points and is not -2.85 percent; the analytics layer has always emitted this
#: token, and ADR-0025 homes it here rather than leaving it a bare literal in three modules.
PERCENTAGE_POINTS = "percentage_points"

#: The one closed vocabulary. Every statement that carries a figure, internal or external,
#: draws its unit from this tuple or states no unit at all. There is no second list: a
#: caller-supplied string outside it is refused rather than matched, because two
#: unrecognised labels agreeing with each other is exactly the failure this closes.
QUANTITY_TYPES = (CURRENCY, PERCENT, RATIO, COUNT, DAYS, PERCENTAGE_POINTS)

#: Quantity types that require a currency code to be meaningful.
MONETARY_QUANTITY_TYPES = (CURRENCY,)


def is_quantity_type(value):
    """True for a canonical quantity type. `None` is not one - it means "not stated"."""
    return value in QUANTITY_TYPES


def is_monetary(value):
    """True for a quantity type that needs a currency code alongside it."""
    return value in MONETARY_QUANTITY_TYPES

# -- aggregation semantics --------------------------------------------------

SUM = "sum"                  # additive over the period
DERIVED = "derived"          # computed from other aggregates
POINT_IN_TIME = "point_in_time"   # a balance, not a flow
PERIOD_OVER_PERIOD = "period_over_period"


class KPIDefinition:
    """The authoritative declaration of one metric."""

    __slots__ = ("kpi_id", "name", "description", "formula", "inputs", "optional_inputs",
                 "unit", "aggregation", "applicable_models", "result_semantics",
                 "minimum_periods", "calculation_notes", "calculator", "category",
                 "not_applicable_reason", "assumptions")

    def __init__(self, kpi_id, name, description, formula, inputs, unit, aggregation,
                 calculator, category, optional_inputs=(), applicable_models=ALL_MODELS,
                 result_semantics=None, minimum_periods=1, calculation_notes=None,
                 not_applicable_reason=None, assumptions=()):
        self.kpi_id = kpi_id
        self.name = name
        self.description = description
        self.formula = formula
        self.inputs = tuple(inputs)
        self.optional_inputs = tuple(optional_inputs)
        self.unit = unit
        self.aggregation = aggregation
        self.calculator = calculator
        self.category = category
        self.applicable_models = applicable_models
        self.result_semantics = result_semantics or "A single value for the reporting period."
        self.minimum_periods = minimum_periods
        self.calculation_notes = calculation_notes
        self.not_applicable_reason = not_applicable_reason
        self.assumptions = tuple(assumptions)

    @property
    def requires(self):
        """Alias for `inputs`, the name earlier milestones use."""
        return self.inputs

    def applies_to(self, business_model):
        """Whether this metric is meaningful for a business model.

        With no model known nothing is suppressed — an unknown model is not a licence to
        guess that a metric is irrelevant.
        """
        if self.applicable_models == ALL_MODELS:
            return True
        if business_model is None:
            return True
        return business_model in self.applicable_models

    def as_dict(self):
        return {
            "id": self.kpi_id, "name": self.name, "description": self.description,
            "formula": self.formula, "inputs": list(self.inputs),
            "optional_inputs": list(self.optional_inputs), "unit": self.unit,
            "aggregation": self.aggregation, "category": self.category,
            "applicable_models": (list(self.applicable_models)
                                  if self.applicable_models != ALL_MODELS else "*"),
            "result_semantics": self.result_semantics,
            "minimum_data_requirements": {"periods": self.minimum_periods,
                                          "fields": list(self.inputs)},
            "calculation_notes": self.calculation_notes,
            "assumptions": list(self.assumptions),
        }

    def __repr__(self):
        return "KPIDefinition(%s)" % self.kpi_id


class KPIResult:
    """One metric outcome, in exactly one bucket, always able to explain itself."""

    __slots__ = ("kpi_id", "definition", "status", "value", "unit", "currency",
                 "inputs_used", "periods", "rows_used", "reason", "missing_inputs",
                 "caveats", "assumptions", "series", "provenance")

    def __init__(self, definition, status, value=None, currency=None, inputs_used=None,
                 periods=None, rows_used=None, reason=None, missing_inputs=(),
                 caveats=(), assumptions=(), series=None, provenance=None):
        self.kpi_id = definition.kpi_id
        self.definition = definition
        self.status = status
        self.value = value
        self.unit = definition.unit
        self.currency = currency
        self.inputs_used = dict(inputs_used or {})
        self.periods = periods
        self.rows_used = rows_used
        self.reason = reason
        self.missing_inputs = list(missing_inputs)
        self.caveats = list(caveats)
        self.assumptions = list(assumptions or definition.assumptions)
        self.series = series or []
        self.provenance = dict(provenance or {})

    # -- state ------------------------------------------------------------

    @property
    def available(self):
        return self.status in VALUE_BEARING

    @property
    def inputs(self):
        """Alias for `inputs_used`, the name earlier milestones use."""
        return self.inputs_used

    @property
    def label(self):
        return self.definition.name

    @property
    def formula(self):
        return self.definition.formula

    def as_dict(self):
        record = {
            "kpi_id": self.kpi_id,
            "name": self.definition.name,
            "status": self.status,
            "unit": self.unit,
            "category": self.definition.category,
            "formula": self.definition.formula,
            "classification": "calculated_metric",
        }
        if self.value is not None:
            record["value"] = (str(self.value) if isinstance(self.value, Decimal)
                               else self.value)
        if self.currency:
            record["currency"] = self.currency
        if self.inputs_used:
            record["inputs"] = {k: (str(v) if isinstance(v, Decimal) else v)
                                for k, v in self.inputs_used.items()}
        if self.periods is not None:
            record["periods"] = self.periods
        if self.rows_used is not None:
            record["rows_used"] = self.rows_used
        if self.reason:
            record["reason"] = self.reason
        if self.missing_inputs:
            record["missing_inputs"] = self.missing_inputs
        if self.caveats:
            record["caveats"] = self.caveats
        if self.assumptions:
            record["assumptions"] = self.assumptions
        if self.provenance:
            record["provenance"] = self.provenance
        return record

    def __repr__(self):
        return "KPIResult(%s=%s [%s])" % (self.kpi_id, self.value, self.status)


# ---------------------------------------------------------------------------
# Result constructors — each names the specific requirement that failed
# ---------------------------------------------------------------------------

def available(definition, value, **kwargs):
    return KPIResult(definition, AVAILABLE, value=value, **kwargs)


def partial(definition, value, caveat, **kwargs):
    caveats = list(kwargs.pop("caveats", [])) + [caveat]
    return KPIResult(definition, PARTIAL, value=value, caveats=caveats, **kwargs)


def unavailable(definition, missing_inputs=(), reason=None, unconfirmed_inputs=(),
                **kwargs):
    """A metric that cannot be produced, naming exactly which requirement failed.

    "The field is absent" and "the field is there but its meaning is unconfirmed" are
    different problems with different fixes, so they are never merged into one message.
    """
    missing = list(missing_inputs)
    unconfirmed = list(unconfirmed_inputs)
    if reason is None:
        parts = ["Insufficient data to calculate this metric reliably."]
        if missing:
            parts.append("Missing required field(s): %s." % ", ".join(missing))
        if unconfirmed:
            parts.append("The column(s) for %s are only provisional and must be confirmed."
                         % ", ".join(unconfirmed))
        reason = " ".join(parts)
    return KPIResult(definition, UNAVAILABLE, reason=reason,
                     missing_inputs=missing + unconfirmed, **kwargs)


def not_applicable(definition, reason=None, business_model=None, **kwargs):
    if reason is None:
        reason = definition.not_applicable_reason or (
            "Not meaningful for the %r business model."
            % (business_model or "current"))
    return KPIResult(definition, NOT_APPLICABLE, reason=reason, **kwargs)


def insufficient_data(definition, have, need, unit_label="periods", **kwargs):
    reason = ("Insufficient history: %s %s available, %s required."
              % (have, unit_label, need))
    return KPIResult(definition, INSUFFICIENT_DATA, reason=reason,
                     periods=have, **kwargs)


def calculation_error(definition, detail, **kwargs):
    """A calculation could not complete. Never surfaced as a Python traceback."""
    return KPIResult(definition, UNAVAILABLE,
                     reason="This metric could not be calculated: %s" % detail, **kwargs)


def bucket(results):
    """Group results by bucket, for reporting."""
    grouped = {b: [] for b in BUCKETS}
    for result in results.values():
        grouped.setdefault(result.status, []).append(result)
    return grouped
