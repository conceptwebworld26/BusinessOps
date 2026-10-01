"""The data quality gate.

Thirteen check families, each declared as a `CheckSpec` and implemented in `families.py`:

     1 missing_values          8 inconsistent_customers
     2 duplicate_records       9 inconsistent_products
     3 invalid_dates          10 currency_consistency
     4 invalid_numbers        11 outliers
     5 negative_values        12 broken_formulas
     6 missing_periods        13 incomplete_dataset
     7 duplicate_transactions

Severity model. Individual findings carry `INFO` / `WARNING` / `CRITICAL`; the report as a
whole carries `PASS` / `WARNING` / `CRITICAL`, the highest finding severity present
(INFO-only being a `PASS`). The two vocabularies describe different things — one finding,
one verdict — so both are kept.

**A `CRITICAL` finding halts the pipeline.** Warnings let analysis continue but must survive
into the final output; they are never dropped during summarisation.

**Source data is never repaired.** Checks observe and report; where a fix exists the finding
carries remediation guidance and the user decides. Normalisation happens in the data layer,
on a derived copy.

This module is the stable entry point. `run()` keeps the signature earlier milestones use.
"""

from . import families as _families
from .contract import (                                          # noqa: F401
    CRITICAL, CheckResult, CheckSpec, EXHAUSTIVE, Finding, INFO, NOT_RUN, PARTIAL,
    PASS, REGISTRY, SEVERITY_RANK, WARNING, register, spec_for, specs,
)
from .report import QualityReport, source_provenance, validate_document  # noqa: F401

# Legacy grouping names, retained so earlier callers and reports stay readable.
FAMILIES = tuple((spec.check_id, function) for spec, function in REGISTRY)

CHECK_IDS = tuple(spec.check_id for spec in specs())


def run(dataset, semantic_map, config, canonical=None, context=None):
    """Run every quality family and return the graded report.

    `canonical` and `context` are optional: families that need them report themselves as
    not run rather than guessing, so a caller without them still gets an honest report.
    """
    check_context = _families.Context(dataset, semantic_map, config, canonical, context)

    results, findings = [], []
    for spec, function in REGISTRY:
        result = function(check_context)
        results.append(result)
        findings.extend(result.findings)

    return QualityReport(
        findings, dataset.row_count,
        check_results=results,
        provenance=source_provenance(dataset, canonical),
        columns_checked=dataset.column_count,
        processing_mode=(canonical.processing_mode if canonical is not None else None),
        completeness=check_context.completeness,
        config=config)
