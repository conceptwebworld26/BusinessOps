"""Privacy: field-level sensitivity classification and aggregation primitives (ADR-0009)."""

from .classes import (                                           # noqa: F401
    CONDITIONAL, DEFAULT_CLASS, DERIVED_SAFE, HUMAN_LABEL, INTERNAL, NEVER,
    NO_APPROVAL_PATH, ORDER, PUBLIC, RESTRICTED, TIER_FOR_CLASS,
    is_externalizable, max_tier, most_sensitive, permitted_at_tier, rank, required_tier,
)
from .aggregation import (                                       # noqa: F401
    AggregateDescriptor, DisclosureAssessment, assess_disclosure,
    assess_reidentification, band_amount, band_count, banded_amount_descriptor,
    count_entities, as_rate, rate_descriptor,
)
from .sensitivity import (                                       # noqa: F401
    FieldSensitivity, SensitivityMap, classify_dataset, classify_field,
    classify_content, classify_name,
)

__all__ = [
    "PUBLIC", "DERIVED_SAFE", "CONDITIONAL", "INTERNAL", "RESTRICTED", "NEVER",
    "ORDER", "TIER_FOR_CLASS", "DEFAULT_CLASS", "NO_APPROVAL_PATH", "HUMAN_LABEL",
    "rank", "most_sensitive", "max_tier", "required_tier", "permitted_at_tier",
    "is_externalizable",
    "classify_field", "classify_dataset", "classify_name", "classify_content",
    "FieldSensitivity", "SensitivityMap",
    "AggregateDescriptor", "DisclosureAssessment", "assess_disclosure",
    "assess_reidentification", "count_entities", "band_count", "band_amount",
    "as_rate", "rate_descriptor", "banded_amount_descriptor",
]
