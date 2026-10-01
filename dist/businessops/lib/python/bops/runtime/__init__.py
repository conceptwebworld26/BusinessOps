"""Reader runtime: tier resolution and the consented dependency bootstrap (ADR-0008).

Resolution is pure inspection and never installs. Installing is an explicit, consented
action (ADR-0010).
"""

from .tiers import (                                             # noqa: F401
    OPENPYXL_PIN,
    RUNTIME_DIR,
    TIER_CSV_FALLBACK,
    TIER_OPENPYXL_MANAGED,
    TIER_OPENPYXL_SYSTEM,
    TIER_STDLIB,
    ReaderTier,
    bootstrap,
    bootstrap_possible,
    consent_request,
    managed_python,
    read_state,
    resolve,
    write_state,
)

__all__ = [
    "OPENPYXL_PIN", "RUNTIME_DIR",
    "TIER_OPENPYXL_SYSTEM", "TIER_OPENPYXL_MANAGED", "TIER_STDLIB", "TIER_CSV_FALLBACK",
    "ReaderTier", "bootstrap", "bootstrap_possible", "consent_request",
    "managed_python", "read_state", "resolve", "write_state",
]
