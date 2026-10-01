"""The data quality gate: thirteen check families, graded findings, and the CRITICAL halt."""

from . import families                                          # noqa: F401
from .checks import (                                           # noqa: F401
    CHECK_IDS, CRITICAL, CheckResult, CheckSpec, EXHAUSTIVE, FAMILIES, Finding, INFO,
    NOT_RUN, PARTIAL, PASS, QualityReport, WARNING, run, spec_for, specs,
    source_provenance, validate_document,
)
from .report import SCHEMA_PATH, SCHEMA_VERSION, load_schema    # noqa: F401

__all__ = ["run", "QualityReport", "Finding", "CheckResult", "CheckSpec", "FAMILIES",
           "CHECK_IDS", "specs", "spec_for", "families",
           "INFO", "WARNING", "CRITICAL", "PASS",
           "EXHAUSTIVE", "PARTIAL", "NOT_RUN",
           "load_schema", "validate_document", "source_provenance",
           "SCHEMA_PATH", "SCHEMA_VERSION"]
