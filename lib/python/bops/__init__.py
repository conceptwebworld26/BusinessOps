"""BusinessOps deterministic engine.

Every reported figure is produced here, never by model arithmetic (ADR-0002). The engine
makes no network calls and is stdlib-first; the single managed dependency is the Tier-2
xlsx reader, installed only with explicit user consent (ADR-0008).

Milestone 1 shipped the foundation: configuration precedence, Business Context,
reader-tier resolution and the schema validator. Milestone 2 adds the vertical slice:
ingestion, semantic mapping, the quality gate, the KPI registry, materiality, the evidence
ledger and deterministic sales analytics. Milestone 3 completes the data layer: all four
reader tiers, the canonical dataset, type/date/currency normalization, field-level
sensitivity classification and privacy-preserving aggregation primitives. Forecasting,
anomaly detection and the remaining analysis domains arrive in later milestones.
"""

__version__ = "0.1.0"

from . import evidence, materiality, normalize, privacy, quantity  # noqa: F401
from .errors import (                                            # noqa: F401
    BusinessOpsError,
    ConfigError,
    ConsentRequiredError,
    MissingContextError,
    RuntimeUnavailableError,
    VocabularyError,
)

__all__ = [
    "__version__",
    "evidence",
    "materiality",
    "normalize",
    "quantity",
    "pipeline",
    "privacy",
    "BusinessOpsError",
    "ConfigError",
    "ConsentRequiredError",
    "MissingContextError",
    "RuntimeUnavailableError",
    "VocabularyError",
]
