"""The canonical dataset — a stable representation independent of source format.

A `CanonicalDataset` wraps a raw `Dataset` and adds, per field: the original name, a
normalized name, the inferred kind, currency evidence, missing/ambiguous counts, and a
sensitivity class. It is what every layer above ingestion consumes, so a CSV and an XLSX of
the same business data become indistinguishable downstream.

**Normalization is derived, never destructive.** The source file is untouched; the raw
`Dataset` is retained alongside the normalized view, so any figure can be traced back to
the exact characters the user supplied. Two accessors make the distinction explicit in code:

    raw_rows()         exactly what was read
    normalized_rows()  the derived, typed representation

Processing mode is recorded because a dataset that was sampled or aggregated must never be
presented as if it had been analysed in full.
"""

from .. import normalize as normalize_mod
from ..privacy import sensitivity as sensitivity_mod

# How the data was processed — recorded in provenance, never inferred later.
FULL = "full"                  # every row materialised and analysed
STREAMED = "streamed"          # read in passes without full materialisation
SAMPLED = "sampled"            # only part of the data was examined
AGGREGATED = "aggregated"      # source-side aggregation; rows never retrieved

# The row count above which chunked streaming would be preferable. Streaming is not implemented
# (the M3 deferral): every reader materialises every row. So this no longer chooses the recorded
# mode, which must describe what actually happened (M13-DEF-03, fixed in M14-5).
LARGE_ROW_THRESHOLD = 100000


def normalize_name(name):
    """A stable snake_case field name, independent of source formatting."""
    import re
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", str(name or "").strip())
    cleaned = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", cleaned)
    return re.sub(r"_+", "_", cleaned).strip("_").lower()


class Field:
    """One column: its identity, semantics, quality and sensitivity."""

    __slots__ = ("original_name", "name", "profile", "sensitivity")

    def __init__(self, original_name, name, profile, sensitivity):
        self.original_name = original_name
        self.name = name
        self.profile = profile
        self.sensitivity = sensitivity

    @property
    def kind(self):
        return self.profile.kind

    @property
    def currencies(self):
        return self.profile.currencies

    @property
    def needs_confirmation(self):
        return self.profile.ambiguous_count > 0

    def as_dict(self):
        return {"original_name": self.original_name, "name": self.name,
                "kind": self.kind, "currencies": self.currencies,
                "missing": self.profile.missing_count,
                "ambiguous": self.profile.ambiguous_count,
                "mixed_types": self.profile.is_mixed,
                "warnings": self.profile.warnings,
                "sensitivity": self.sensitivity.as_dict()}

    def __repr__(self):
        return "Field(%s: %s, %s)" % (self.name, self.kind,
                                      self.sensitivity.sensitivity)


class CanonicalDataset:
    """Normalized view of a Dataset, with the raw data retained alongside."""

    def __init__(self, dataset, fields, processing_mode=FULL, rows_examined=None,
                 warnings=None):
        self.source = dataset
        self.fields = {f.original_name: f for f in fields}
        self.processing_mode = processing_mode
        self.rows_examined = (rows_examined if rows_examined is not None
                              else dataset.row_count)
        self.warnings = list(warnings or [])
        self._normalized = None

    # -- identity -----------------------------------------------------------

    @property
    def columns(self):
        return list(self.source.columns)

    @property
    def row_count(self):
        return self.source.row_count

    @property
    def complete(self):
        """False when only part of the data was examined."""
        return (self.processing_mode == FULL
                and self.rows_examined == self.source.row_count)

    def field(self, column):
        return self.fields.get(column)

    def field_by_name(self, normalized):
        for field in self.fields.values():
            if field.name == normalized:
                return field
        return None

    # -- data ---------------------------------------------------------------

    def raw_rows(self):
        """Exactly what was read from the source. Never modified."""
        return self.source.rows

    def normalized_rows(self):
        """The derived, typed representation. Computed once, cached."""
        if self._normalized is None:
            rows = []
            for row in self.source.rows:
                converted = {}
                for column, field in self.fields.items():
                    normalized = normalize_mod.normalize_value(
                        row.get(column), expect=field.kind,
                        day_first=field.profile.day_first)
                    converted[column] = normalized.value
                rows.append(converted)
            self._normalized = rows
        return self._normalized

    def column(self, name, normalized=False):
        rows = self.normalized_rows() if normalized else self.source.rows
        return [row.get(name) for row in rows]

    # -- currency -----------------------------------------------------------

    def currencies(self):
        """Every currency detected anywhere in the dataset."""
        found = set()
        for field in self.fields.values():
            found.update(field.currencies)
        return sorted(found)

    def has_mixed_currency(self):
        return len(self.currencies()) > 1

    # -- sensitivity --------------------------------------------------------

    def sensitivity_map(self):
        return sensitivity_mod.SensitivityMap(
            [f.sensitivity for f in self.fields.values()])

    def never_externalizable_columns(self):
        return self.sensitivity_map().never_externalizable_columns()

    # -- provenance ---------------------------------------------------------

    def provenance(self):
        record = dict(self.source.provenance())
        record.update({
            "processing_mode": self.processing_mode,
            "rows_examined": self.rows_examined,
            "complete": self.complete,
            "currencies": self.currencies(),
            "normalization": "derived representation; source file unmodified",
            "fields": {name: field.as_dict() for name, field in sorted(self.fields.items())},
            "sensitivity": self.sensitivity_map().summary(),
        })
        if self.warnings:
            record["canonical_warnings"] = list(self.warnings)
        return record

    def describe(self):
        return "%s | %s mode, %d/%d rows examined, currencies=%s" % (
            self.source.describe(), self.processing_mode, self.rows_examined,
            self.source.row_count, ",".join(self.currencies()) or "none")

    def __repr__(self):
        return "CanonicalDataset(%s)" % self.describe()


def build(dataset, sample=1000, processing_mode=None, rows_examined=None):
    """Profile and classify every column, producing the canonical view.

    Profiling samples up to `sample` values per column — enough to decide a column's kind
    reliably without walking a very large file. When sampling occurs the processing mode
    reflects it, so nothing downstream can mistake a sample for a full pass.
    """
    warnings = []
    fields = []
    for column in dataset.columns:
        values = dataset.column(column)
        profile = normalize_mod.profile_column(column, values, sample=sample)
        classification = sensitivity_mod.classify_field(column, values)
        fields.append(Field(column, normalize_name(column), profile, classification))
        for warning in profile.warnings:
            if warning not in warnings:
                warnings.append(warning)

    if processing_mode is None:
        # The dataset handed in is fully materialised, whatever its size, so the pass is FULL.
        # STREAMED, SAMPLED and AGGREGATED are recorded only when the caller that processed the
        # data that way says so. Inferring STREAMED from the row count alone once labelled a
        # complete pass of 100,001+ rows as partial, caveating every figure (M13-DEF-03).
        processing_mode = FULL

    canonical = CanonicalDataset(dataset, fields, processing_mode, rows_examined, warnings)

    if canonical.has_mixed_currency():
        canonical.warnings.append(
            "Dataset contains %d currencies (%s). Values in different currencies are not "
            "summed and no conversion is applied."
            % (len(canonical.currencies()), ", ".join(canonical.currencies())))
    return canonical
