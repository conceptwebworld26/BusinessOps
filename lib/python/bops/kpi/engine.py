"""The KPI calculation engine.

Order of decision, and it matters:

  1. **Quality gate** — a `CRITICAL` report means no metric is produced at all. Numbers from
     data known to be unusable are worse than no numbers.
  2. **Applicability** — does this metric mean anything for the business model? Telling a
     consultancy "we could not compute inventory turnover" is unhelpful when the honest
     answer is that it does not apply to them.
  3. **Currency safety** — monetary metrics are refused outright when currencies are mixed
     or contradict Business Context. BusinessOps never converts.
  4. **Input contract** — is every required field mapped and confirmed?
  5. **Calculation** — deterministic, Decimal, no network, no mutation.

A calculator that raises is caught and reported as a structured result. A Python traceback
is never a user-facing KPI outcome.
"""

import datetime

from .. import mapping as mapping_mod
from . import catalog, primitives as p
from .contract import (
    AVAILABLE, INSUFFICIENT_DATA, MONETARY_QUANTITY_TYPES, NOT_APPLICABLE, PARTIAL,
    UNAVAILABLE,
    bucket, calculation_error, not_applicable, unavailable,
)

#: Re-exported from the contract so there is one monetary vocabulary, not two
#: (ADR-0025). Kept as a module name because callers already import it from here.
MONETARY_UNITS = MONETARY_QUANTITY_TYPES


class CalculationContext:
    """Everything a calculator may consult. Assembled once, shared by every KPI."""

    __slots__ = ("dataset", "semantic_map", "canonical", "business_context", "config",
                 "quality", "currency", "currency_error", "business_model", "caveats")

    def __init__(self, dataset, semantic_map, canonical=None, business_context=None,
                 config=None, quality=None):
        self.dataset = dataset
        self.semantic_map = semantic_map
        self.canonical = canonical
        self.business_context = business_context
        self.config = config
        self.quality = quality
        self.currency, self.currency_error = p.resolve_currency(
            canonical, business_context, config)
        self.business_model = (business_context.get("identity.business_model")
                               if business_context is not None else None)
        # Quality warnings travel with every figure computed from this data.
        self.caveats = list(quality.caveats()) if quality is not None else []

    def column(self, role):
        return self.semantic_map.column_for(role)

    def provenance(self):
        record = {
            "source": (self.canonical.source.provenance()["source_name"]
                       if self.canonical is not None
                       else self.dataset.provenance().get("source_name")),
            "rows": self.dataset.row_count,
            "calculated_at": datetime.datetime.now().replace(microsecond=0).isoformat(),
        }
        if self.canonical is not None:
            record["processing_mode"] = self.canonical.processing_mode
            record["complete"] = self.canonical.complete
            tier = self.canonical.source.provenance().get("reader_tier")
            if tier:
                record["reader_tier"] = tier.get("tier")
        if self.quality is not None:
            record["quality_grade"] = self.quality.grade
        return record


def calculate(dataset, semantic_map, canonical=None, business_context=None, config=None,
              quality=None, kpi_ids=None):
    """Compute the requested KPIs. Returns {kpi_id: KPIResult}.

    Every requested metric gets a result — never a silent omission — so a caller can always
    show the full picture including what could not be produced and why.
    """
    context = CalculationContext(dataset, semantic_map, canonical, business_context,
                                 config, quality)
    requested = kpi_ids or catalog.ALL_IDS
    results = {}

    # 1. Quality gate: a CRITICAL report suppresses every metric.
    if quality is not None and quality.halted:
        for kpi_id in requested:
            definition = catalog.BY_ID.get(kpi_id)
            if definition is None:
                continue
            results[kpi_id] = unavailable(
                definition,
                reason="Not calculated: the data quality gate halted this analysis. "
                       "Producing figures from data with critical defects would mislead.",
                provenance=context.provenance())
        return results

    for kpi_id in requested:
        definition = catalog.BY_ID.get(kpi_id)
        if definition is None:
            continue
        results[kpi_id] = _calculate_one(definition, context)
    return results


def _calculate_one(definition, context):
    # 2. Applicability comes before availability.
    if not definition.applies_to(context.business_model):
        return not_applicable(definition, business_model=context.business_model,
                              provenance=context.provenance())

    # 3. Currency safety, for monetary metrics only.
    if definition.unit in MONETARY_UNITS and context.currency_error:
        return unavailable(definition, reason=context.currency_error,
                           provenance=context.provenance())

    # 4 and 5: the calculator owns its own input contract and arithmetic.
    try:
        result = definition.calculator(definition, context)
    except Exception as exc:                      # never surface a traceback to a user
        return calculation_error(definition, "%s: %s" % (type(exc).__name__, exc),
                                 provenance=context.provenance())

    if result is None:
        return calculation_error(definition, "the calculator produced no result",
                                 provenance=context.provenance())

    # Attach shared context every result needs.
    result.provenance = dict(result.provenance or {}, **context.provenance())
    if result.available:
        if definition.unit in MONETARY_UNITS and not result.currency:
            result.currency = context.currency
        for caveat in context.caveats:
            if caveat not in result.caveats:
                result.caveats.append(caveat)
        # A partial pass must never look exhaustive.
        if context.canonical is not None and not context.canonical.complete:
            result.status = PARTIAL
            note = ("Computed from %d of %d rows (%s processing)."
                    % (context.canonical.rows_examined, context.canonical.row_count,
                       context.canonical.processing_mode))
            if note not in result.caveats:
                result.caveats.append(note)
    return result


def summary(results):
    """Counts by bucket, for reporting."""
    grouped = bucket(results)
    return {name: len(items) for name, items in grouped.items()}


def explain(results):
    """One line per metric — the honest full picture, including what is absent."""
    lines = []
    for kpi_id in sorted(results):
        result = results[kpi_id]
        value = result.value if result.available else "—"
        lines.append("%-28s %-18s %s" % (kpi_id, result.status,
                                         value if result.available
                                         else (result.reason or "")[:70]))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0.0"


def as_document(results, context=None, currency=None, business_model=None,
                quality_grade=None):
    """The schema-conforming KPI results document.

    Every requested metric appears, including those that could not be produced — hiding an
    absent metric would be the same lie as returning zero for it.
    """
    counts = summary(results)
    ordered = [results[k].as_dict() for k in sorted(results)]
    document = {
        "schema_version": SCHEMA_VERSION,
        "counts": {k: v for k, v in counts.items()},
        "results": ordered,
    }
    if context is not None:
        document["currency"] = context.currency
        document["business_model"] = context.business_model
        document["quality_grade"] = (context.quality.grade
                                     if context.quality is not None else None)
    else:
        if currency is not None:
            document["currency"] = currency
        if business_model is not None:
            document["business_model"] = business_model
        if quality_grade is not None:
            document["quality_grade"] = quality_grade
    return document


def schema_path():
    import os
    return os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
        "schemas", "kpi_results.schema.json")


def load_schema():
    from ..config import load_json
    return load_json(schema_path(), "kpi results schema")


def validate_document(document, schema=None):
    from .. import jsonschema_mini
    schema = schema if schema is not None else load_schema()
    return [str(e) for e in jsonschema_mini.validate(document, schema)]
