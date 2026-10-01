"""The KPI registry and deterministic engine - the only home for numeric formulas."""

from . import catalog, engine, primitives                        # noqa: F401
from .registry import (                                          # noqa: F401
    ALL_IDS, ALL_MODELS, APPROVED_27, AVAILABLE, BEYOND_APPROVED, BUCKETS, BY_ID,
    CATALOGUE, COMPUTED, COUNT, CURRENCY, DAYS, INSUFFICIENT_DATA, KPIDefinition,
    KPIResult, M2_KPI_SET, NOT_APPLICABLE, PARTIAL, PERCENT, RATIO, REGISTRY,
    UNAVAILABLE, VALUE_BEARING, bucket, by_category, calculate, catalogue_as_dict,
    as_document, definition, definitions, explain, load_schema, monthly_totals,
    summary, validate_document,
)

__all__ = ["calculate", "bucket", "summary", "explain", "REGISTRY", "BY_ID", "CATALOGUE",
           "definitions", "definition", "catalogue_as_dict", "by_category",
           "monthly_totals", "as_document", "validate_document", "load_schema", "M2_KPI_SET", "ALL_IDS", "APPROVED_27", "BEYOND_APPROVED",
           "KPIDefinition", "KPIResult", "BUCKETS", "VALUE_BEARING",
           "AVAILABLE", "COMPUTED", "PARTIAL", "UNAVAILABLE", "NOT_APPLICABLE",
           "INSUFFICIENT_DATA", "CURRENCY", "PERCENT", "RATIO", "COUNT", "DAYS",
           "ALL_MODELS", "catalog", "engine", "primitives"]
