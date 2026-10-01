"""Cross-domain synthesis: the shared, auditable layer M10's four capabilities read.

SWOT, strategy, decision support and executive reporting all need the same thing - a set
of statements that knows which are facts, which are calculations, which are quotations
from a source, which are readings of those, what each rests on, where the sources
disagree, what could not be done, and how confident any of it is. Building that four
times would produce four subtly different answers to "may these two numbers be compared".
Building it once is this package.

    from bops import synthesis

    result = synthesis.SynthesisSet(subject="FY2026 review", currency="GBP")
    result.register_dataset("ds-2026", label="sales_2026.xlsx")
    synthesis.from_analysis_set(result, sales, synthesis.ORIGIN_SALES,
                                dataset_id="ds-2026")
    synthesis.register_external(result, evidence, synthesis.ORIGIN_INDUSTRY)
    synthesis.sourced_statement(result, synthesis.ORIGIN_INDUSTRY,
                                "Source X reports the industry grew 4% in 2025.",
                                evidence_ids=[...])
    print(result.to_json())

What this package does **not** do is decide anything new. It computes no figure, issues no
recommendation, verifies no claim and promotes nothing. Every judgement it reports was made
by the layer that owns that judgement - materiality by `materiality`, tiering and support
by `research.sources`, provenance classes by `evidence` - and is carried across intact.
"""

from .compatibility import (                                        # noqa: F401
    COMPATIBLE, INCOMPATIBLE, NEVER_CONVERTS, UNKNOWN, compare, may_combine,
    mismatch_summary,
)
from .dimension_provenance import (                                 # noqa: F401
    ADMISSIBLE_BASES, ASSERTED, BASES, CONTEXT, DERIVABLE_DIMENSIONS, DERIVATION_RULES,
    DERIVED, DimensionProvenance, NEVER_INFERS, NON_DERIVABLE_DIMENSIONS, STATED,
    conflicting_dimensions, source_footings,
)
from .confidence import (                                           # noqa: F401
    ConfidenceAssessment, DATA_QUALITY_WARNING, FORECAST_INSTABILITY, HIGH,
    INCOMPARABLE_VALUES, INCOMPLETE_DATASET, INSUFFICIENT_HISTORY, LOW, MEDIUM,
    PARTICIPANT_SOURCED, PROVENANCE_UNAVAILABLE, REASON_CODES, REASON_TEXT, SEVERE,
    SINGLE_SOURCE, STALE_EXTERNAL, STATISTICAL_INTERVAL, TIER_C_ONLY, UNAVAILABLE_KPI,
    UNDATED_EXTERNAL, UNRESOLVED_CONFLICT, UNSUPPORTED_STATEMENT, assess, combine,
    weakest,
)
from .conflicts import (                                            # noqa: F401
    CONFLICT_KINDS, CrossDomainConflict, DEFINITIONAL, INTERNAL_EXTERNAL, KIND_REASON,
    METHODOLOGY, NEVER_RESOLVES, NUMERIC, SCOPE, TEMPORAL, classify, conflict_id,
)
from .contract import (                                             # noqa: F401
    ASSUMPTION, CALCULATION, DEFERRED_KINDS, DEFERRED_NOTE, DIMENSIONS, DOMAINS,
    DOMAIN_OF_ORIGIN, EVIDENCE_CLASS, EXTERNAL, EXTERNAL_KINDS, EXTERNAL_ORIGINS, FACT,
    INSUFFICIENT_EVIDENCE, INTERNAL, INTERNALLY_FOOTED_KINDS, INTERNAL_KINDS,
    INTERNAL_ORIGINS, INTERNAL_PROVENANCE, INTERPRETATION,
    ORIGINS, ORIGIN_ANOMALY, ORIGIN_COMPANY, ORIGIN_COMPETITOR, ORIGIN_CUSTOMER,
    ORIGIN_FINANCIAL, ORIGIN_FORECAST, ORIGIN_INDUSTRY, ORIGIN_KPI, ORIGIN_MARKET,
    ORIGIN_PRODUCT, ORIGIN_QUALITY, ORIGIN_SALES, PARTIALLY_SUPPORTED, PROVENANCE_KINDS,
    P_ANOMALY, P_CALCULATION, P_CLAIM, P_DATASET, P_EVIDENCE, P_FINDING, P_FORECAST,
    P_KPI, P_UNAVAILABLE, ProvenanceRef, RECOMMENDATION, SOURCED, STATEMENT_KINDS,
    SUPPORTED, SUPPORT_FROM_TIER_ASSESSMENT, SUPPORT_STATES, SYNTHESIS_EMITS,
    SynthesisError, SynthesisItem, UNSUPPORTED, UNTRUSTED, synthesis_id, weakest_support,
)
from .limitations import (                                          # noqa: F401
    EXTERNAL_UNSUPPORTED, INCOMPARABLE, Limitation, NEVER_SUPPRESSES, NO_INPUTS,
    as_limitation,
)
from .merge import (                                                # noqa: F401
    assumption, compare_values, from_analysis_set, from_kpi_result, interpretation,
    register_external, sourced_statement,
)
from .research_footing import (                                     # noqa: F401
    FootedStatement, NOT_QUOTABLE, RESERVED_FIELDS, UNIT_DERIVATION, dimension_report,
    evidence_from_retrieval, footed_statement,
)
from .synthesis_set import (                                        # noqa: F401
    SCHEMA_VERSION, SynthesisSet, TRUST_STATEMENT, claim_id, load,
)
from . import (                                                     # noqa: F401
    compatibility, confidence, conflicts, contract, limitations, merge, research_footing,
)

__all__ = [
    "DimensionProvenance", "STATED", "CONTEXT", "DERIVED", "ASSERTED", "BASES",
    "ADMISSIBLE_BASES", "DERIVATION_RULES", "DERIVABLE_DIMENSIONS",
    "NON_DERIVABLE_DIMENSIONS", "NEVER_INFERS", "conflicting_dimensions",
    "source_footings",
    # the canonical result
    "SynthesisSet", "SynthesisItem", "SynthesisError", "SCHEMA_VERSION",
    "TRUST_STATEMENT", "load", "claim_id", "synthesis_id",
    # statement kinds and origins
    "FACT", "CALCULATION", "SOURCED", "INTERPRETATION", "ASSUMPTION", "RECOMMENDATION",
    "STATEMENT_KINDS", "SYNTHESIS_EMITS", "DEFERRED_KINDS", "DEFERRED_NOTE",
    "EVIDENCE_CLASS", "INTERNAL_KINDS", "EXTERNAL_KINDS",
    "INTERNAL", "EXTERNAL", "DOMAINS", "DOMAIN_OF_ORIGIN", "ORIGINS",
    "INTERNAL_ORIGINS", "EXTERNAL_ORIGINS", "UNTRUSTED",
    "INTERNAL_PROVENANCE", "INTERNALLY_FOOTED_KINDS",
    "ORIGIN_KPI", "ORIGIN_SALES", "ORIGIN_CUSTOMER", "ORIGIN_PRODUCT",
    "ORIGIN_FINANCIAL", "ORIGIN_FORECAST", "ORIGIN_ANOMALY", "ORIGIN_QUALITY",
    "ORIGIN_COMPANY", "ORIGIN_MARKET", "ORIGIN_COMPETITOR", "ORIGIN_INDUSTRY",
    # provenance
    "ProvenanceRef", "PROVENANCE_KINDS", "P_DATASET", "P_CALCULATION", "P_KPI",
    "P_FINDING", "P_FORECAST", "P_ANOMALY", "P_EVIDENCE", "P_CLAIM", "P_UNAVAILABLE",
    # support
    "SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "INSUFFICIENT_EVIDENCE",
    "SUPPORT_STATES", "SUPPORT_FROM_TIER_ASSESSMENT", "weakest_support",
    # merging
    "from_analysis_set", "from_kpi_result", "register_external", "sourced_statement",
    "interpretation", "assumption", "compare_values",
    # the research command footing path (M10.2-R.10)
    "footed_statement", "FootedStatement", "evidence_from_retrieval",
    "dimension_report", "UNIT_DERIVATION", "NOT_QUOTABLE", "RESERVED_FIELDS",
    # compatibility
    "compare", "may_combine", "mismatch_summary", "COMPATIBLE", "INCOMPATIBLE",
    "UNKNOWN", "DIMENSIONS", "NEVER_CONVERTS",
    # conflicts
    "CrossDomainConflict", "CONFLICT_KINDS", "DEFINITIONAL", "NUMERIC", "SCOPE",
    "TEMPORAL", "METHODOLOGY", "INTERNAL_EXTERNAL", "classify", "conflict_id",
    "KIND_REASON", "NEVER_RESOLVES",
    # confidence
    "ConfidenceAssessment", "assess", "combine", "weakest", "HIGH", "MEDIUM", "LOW",
    "REASON_CODES", "REASON_TEXT", "SEVERE", "STATISTICAL_INTERVAL",
    "UNRESOLVED_CONFLICT", "UNSUPPORTED_STATEMENT", "PROVENANCE_UNAVAILABLE",
    "DATA_QUALITY_WARNING", "TIER_C_ONLY", "UNDATED_EXTERNAL", "STALE_EXTERNAL",
    "INSUFFICIENT_HISTORY", "INCOMPLETE_DATASET", "UNAVAILABLE_KPI",
    "FORECAST_INSTABILITY", "INCOMPARABLE_VALUES", "SINGLE_SOURCE",
    "PARTICIPANT_SOURCED",
    # limitations
    "Limitation", "as_limitation", "INCOMPARABLE", "EXTERNAL_UNSUPPORTED", "NO_INPUTS",
    "NEVER_SUPPRESSES",
    # submodules
    "contract", "compatibility", "conflicts", "confidence", "limitations", "merge",
    "research_footing",
]
