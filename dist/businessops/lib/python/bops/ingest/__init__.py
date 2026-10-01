"""Ingestion: read business data into the canonical representation without touching source."""

from . import workbook                                          # noqa: F401
from .canonical import (                                        # noqa: F401
    AGGREGATED, CanonicalDataset, FULL, Field, LARGE_ROW_THRESHOLD, SAMPLED, STREAMED,
    build as build_canonical, normalize_name,
)
from .dataset import Dataset, IngestWarning                     # noqa: F401
from .readers import (                                          # noqa: F401
    read, read_csv, read_xlsx, read_xlsx_managed, read_xlsx_openpyxl, read_xlsx_stdlib,
    serial_to_date,
)

__all__ = ["Dataset", "IngestWarning", "read", "read_csv", "read_xlsx",
           "read_xlsx_openpyxl", "read_xlsx_managed", "read_xlsx_stdlib",
           "serial_to_date", "workbook",
           "CanonicalDataset", "Field", "build_canonical", "normalize_name",
           "FULL", "STREAMED", "SAMPLED", "AGGREGATED", "LARGE_ROW_THRESHOLD"]
