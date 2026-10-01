"""Business Context — the business's identity, characteristics and preferences (ADR-0011).

First-class rather than configuration, because it decides which KPIs are *relevant*, not
merely how numbers are formatted, and because it is the sanctioned source of public terms
for Tier 0 research queries (ADR-0009).
"""

from .loader import (                                            # noqa: F401
    BusinessContext,
    Contradiction,
    MissingField,
    load_file,
    load_schema,
    resolve,
    validate,
    validate_or_raise,
)
from . import privacy                                            # noqa: F401

__all__ = [
    "BusinessContext", "Contradiction", "MissingField",
    "load_file", "load_schema", "resolve", "validate", "validate_or_raise",
    "privacy",
]
