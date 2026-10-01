"""The canonical dataset produced by ingestion.

Two rules from the architecture shape this:

  * **The source file is never modified.** Everything here is a derived, in-memory
    representation; readers open files read-only and nothing writes back.
  * **Provenance travels with the data.** A dataset carries how it was read — source type,
    path, reader tier, sheet, warnings — because the evidence ledger needs it and because a
    figure read by a degraded reader must be traceable as such.
"""

import os


class IngestWarning:
    """Something the reader wants downstream to know. Never a silent repair."""

    __slots__ = ("code", "message", "location")

    def __init__(self, code, message, location=None):
        self.code = code
        self.message = message
        self.location = location

    def as_dict(self):
        return {"code": self.code, "message": self.message, "location": self.location}

    def __repr__(self):
        return "IngestWarning(%s: %s)" % (self.code, self.message)


class Dataset:
    """Rows of business data plus the provenance of how they were obtained."""

    def __init__(self, columns, rows, source_type, source_path,
                 reader_tier=None, sheet=None, sheets=None, warnings=None):
        self.columns = list(columns)
        self.rows = rows                       # list of dicts, column -> typed value
        self.source_type = source_type         # "csv" | "xlsx"
        self.source_path = source_path
        self.reader_tier = reader_tier         # ReaderTier record, or None for csv
        self.sheet = sheet
        self.sheets = list(sheets or ([sheet] if sheet else []))
        self.warnings = list(warnings or [])

    # -- shape --------------------------------------------------------------

    @property
    def row_count(self):
        return len(self.rows)

    @property
    def column_count(self):
        return len(self.columns)

    def column(self, name):
        return [row.get(name) for row in self.rows]

    def non_null(self, name):
        return [v for v in self.column(name) if v is not None and v != ""]

    # -- provenance ---------------------------------------------------------

    def provenance(self):
        """The record every downstream claim cites (evidence-ledger class 1)."""
        record = {
            "source_type": self.source_type,
            "source_path": self.source_path,
            "source_name": os.path.basename(self.source_path) if self.source_path else None,
            "sheet": self.sheet,
            "sheets_detected": self.sheets,
            "rows": self.row_count,
            "columns": self.column_count,
            "column_names": self.columns,
            "warnings": [w.as_dict() for w in self.warnings],
        }
        if self.reader_tier is not None:
            record["reader_tier"] = self.reader_tier.as_dict()
        return record

    def describe(self):
        tier = ("tier %d (%s)" % (self.reader_tier.tier, self.reader_tier.name)
                if self.reader_tier else "n/a")
        return "%s: %d rows x %d columns, reader %s" % (
            os.path.basename(self.source_path or "<memory>"),
            self.row_count, self.column_count, tier)

    def __repr__(self):
        return "Dataset(%s)" % self.describe()
