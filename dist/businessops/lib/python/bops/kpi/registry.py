"""The KPI registry — the authoritative definition of every metric.

This module is the stable entry point. The catalogue lives in `catalog.py`, the arithmetic
primitives in `primitives.py`, and the decision order in `engine.py`; this keeps the M2
call signature working while the implementation behind it grew from 7 metrics to 28.

**Every KPI formula in BusinessOps is declared here or in `primitives.py` and nowhere else.**
"""

from . import catalog, engine
from .catalog import ALL_IDS, APPROVED_27, BEYOND_APPROVED, BY_ID, CATALOGUE  # noqa: F401
from .contract import (                                          # noqa: F401
    ALL_MODELS, AVAILABLE, BUCKETS, COMPUTED, COUNT, CURRENCY, DAYS, DERIVED,
    INSUFFICIENT_DATA, KPIDefinition, KPIResult, NOT_APPLICABLE, PARTIAL, PERCENT,
    PERIOD_OVER_PERIOD, POINT_IN_TIME, RATIO, SUM, UNAVAILABLE, VALUE_BEARING, bucket,
)
from .primitives import period_key, series_by_period                  # noqa: F401

# Retained M2 name: the metric set the vertical slice demonstrates.
M2_KPI_SET = ("revenue", "revenue_growth", "gross_profit", "gross_margin",
              "average_order_value", "inventory_turnover", "net_revenue_retention")

#: Backwards-compatible registry mapping, now the full catalogue.
REGISTRY = BY_ID


def definitions(kpi_ids=None):
    """Every definition, or the named subset, in catalogue order."""
    ids = kpi_ids or ALL_IDS
    return [BY_ID[i] for i in ids if i in BY_ID]


def definition(kpi_id):
    return BY_ID.get(kpi_id)


def catalogue_as_dict():
    """The machine-readable catalogue: what every metric means and requires."""
    return {"count": len(CATALOGUE),
            "approved": list(APPROVED_27),
            "beyond_approved": list(BEYOND_APPROVED),
            "definitions": [d.as_dict() for d in definitions()]}


def by_category():
    grouped = {}
    for item in definitions():
        grouped.setdefault(item.category, []).append(item.kpi_id)
    return {k: sorted(v) for k, v in sorted(grouped.items())}


def calculate(dataset, semantic_map, context=None, config=None, kpi_ids=None,
              canonical=None, quality=None):
    """Compute KPIs.

    The positional signature is the one Milestone 2 established — `context` is the Business
    Context — so existing callers keep working; `canonical` and `quality` are new optional
    arguments that let the engine apply currency safety and the quality gate.
    """
    return engine.calculate(dataset, semantic_map, canonical=canonical,
                            business_context=context, config=config, quality=quality,
                            kpi_ids=kpi_ids)


def monthly_totals(dataset, semantic_map, role):
    """Retained M2 helper: ordered (period, total) pairs for a numeric role."""
    return series_by_period(dataset, semantic_map, role) or []


def as_document(results, **kwargs):
    """The schema-conforming KPI results document."""
    return engine.as_document(results, **kwargs)


def validate_document(document, schema=None):
    return engine.validate_document(document, schema)


def load_schema():
    return engine.load_schema()


def summary(results):
    return engine.summary(results)


def explain(results):
    return engine.explain(results)
