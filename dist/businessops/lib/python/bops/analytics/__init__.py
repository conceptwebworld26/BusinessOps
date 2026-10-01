"""Deterministic analytical aggregations. Judgement about them belongs to skills.

Four domains — sales, customer, product, financial — each returning an `AnalysisSet`, and
five primitive modules they all draw on: segmentation, concentration, mix, cohorts and the
presentation policy that decides how an entity may be labelled.

The layering is one-way. Primitives know nothing about domains; domains consume KPI results
and never recompute them; skills read the `AnalysisSet` and never do arithmetic.
"""

from .contract import (                                             # noqa: F401
    ASSUMPTION, AVAILABLE, AnalysisError, AnalysisFinding, AnalysisSet, CALCULATION,
    ENGINE_EMITS, EVIDENCE_CLASS, FACT, FINDING_TYPES, INSUFFICIENT_DATA, INTERPRETATION,
    Limitation, NOT_APPLICABLE, RECOMMENDATION, STATUSES, UNAVAILABLE,
)
from .presentation import (                                         # noqa: F401
    DEFAULT_K, LOCAL, LabelPolicy, MODES, SHAREABLE, export_caveat, policy_for,
    restricted_columns,
)
from . import (                                                     # noqa: F401
    cohorts, concentration, customers, domain, financial, mix, products, segmentation,
)
from .findings import build as build_findings, undetermined_example  # noqa: F401
from .sales import (                                                # noqa: F401
    by_dimension, margin_series, movers, period_split, trend,
)
from . import sales                                                 # noqa: F401

#: The four analytical domains, in the order a report reads them.
DOMAINS = (
    ("sales", sales.analyse),
    ("customer", customers.analyse),
    ("product", products.analyse),
    ("financial", financial.analyse),
)


def analyse_all(result, presentation=LOCAL):
    """Run every domain over one pipeline result. Returns `{domain: AnalysisSet}`."""
    return {name: run(result, presentation=presentation) for name, run in DOMAINS}


__all__ = ["by_dimension", "period_split", "trend", "margin_series", "movers",
           "build_findings", "undetermined_example",
           "cohorts", "concentration", "customers", "domain", "financial", "mix",
           "products", "sales", "segmentation",
           "AnalysisSet", "AnalysisFinding", "Limitation", "AnalysisError",
           "FACT", "CALCULATION", "INTERPRETATION", "RECOMMENDATION", "ASSUMPTION",
           "AVAILABLE", "UNAVAILABLE", "NOT_APPLICABLE", "INSUFFICIENT_DATA",
           "LabelPolicy", "LOCAL", "SHAREABLE", "policy_for", "DEFAULT_K",
           "DOMAINS", "analyse_all"]
