"""Quality report assembly and schema-conforming serialisation.

The report is the artifact everything downstream consumes and the user reads, so its shape
is fixed by `lib/schemas/quality_report.schema.json` and validated against it.

Determinism matters: the same dataset and configuration must produce the same report, in the
same order, every time. Findings are therefore sorted by (severity, check id, code) rather
than by whatever order the checks happened to run in.
"""

import os

from .. import jsonschema_mini
from .contract import (
    CRITICAL, EXHAUSTIVE, INFO, PASS, SEVERITY_RANK, WARNING,
)

SCHEMA_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
    "schemas", "quality_report.schema.json")

SCHEMA_VERSION = "1.0.0"

_GRADE = {0: PASS, 1: WARNING, 2: CRITICAL}


class QualityReport:
    """The graded verdict, its findings, and everything needed to audit them.

    The M2 constructor signature (`findings`, `rows_checked`) still works; M4's structured
    additions are keyword-only.
    """

    def __init__(self, findings, rows_checked, check_results=None, provenance=None,
                 columns_checked=None, processing_mode=None, completeness=EXHAUSTIVE,
                 config=None):
        self.findings = sorted(
            findings,
            key=lambda f: (-SEVERITY_RANK[f.severity], f.check_id or "", f.code))
        self.rows_checked = rows_checked
        self.check_results = list(check_results or [])
        self.provenance = dict(provenance or {})
        self.columns_checked = columns_checked
        self.processing_mode = processing_mode
        self.completeness = completeness
        self.config = config

    # -- verdict ------------------------------------------------------------

    @property
    def grade(self):
        if not self.findings:
            return PASS
        return _GRADE[max(SEVERITY_RANK[f.severity] for f in self.findings)]

    @property
    def halted(self):
        return self.grade == CRITICAL

    def by_severity(self, severity):
        return [f for f in self.findings if f.severity == severity]

    @property
    def critical(self):
        return self.by_severity(CRITICAL)

    @property
    def warnings(self):
        return self.by_severity(WARNING)

    @property
    def info(self):
        return self.by_severity(INFO)

    def by_check(self, check_id):
        return [f for f in self.findings if f.check_id == check_id]

    def result_for(self, check_id):
        for result in self.check_results:
            if result.check_id == check_id:
                return result
        return None

    @property
    def families_run(self):
        return [r.check_id for r in self.check_results if r.completeness != "not_run"]

    @property
    def families_skipped(self):
        return {r.check_id: r.skipped_reason for r in self.check_results
                if r.completeness == "not_run"}

    def halt_reason(self):
        if not self.halted:
            return None
        return ("Analysis stopped at the data quality gate. %d critical problem(s) mean any "
                "figures produced from this dataset would be misleading:\n%s"
                % (len(self.critical),
                   "\n".join("  - %s" % f.message for f in self.critical)))

    def caveats(self):
        """Warnings that must travel with every downstream figure."""
        caveats = ["Data quality: %s" % f.message for f in self.warnings]
        if self.completeness != EXHAUSTIVE:
            caveats.append(
                "Quality checks were not exhaustive (%s processing); findings describe the "
                "examined portion only." % (self.processing_mode or self.completeness))
        return caveats

    # -- serialisation ------------------------------------------------------

    def as_dict(self):
        """The schema-conforming document. Deterministic for a given input."""
        counts = {INFO: len(self.info), WARNING: len(self.warnings),
                  CRITICAL: len(self.critical)}
        document = {
            "schema_version": SCHEMA_VERSION,
            "grade": self.grade,
            "halted": self.halted,
            "completeness": self.completeness,
            "rows_checked": self.rows_checked,
            "findings": [f.as_dict() for f in self.findings],
            "finding_counts": counts,
            "families_total": len(self.check_results),
            "families_run": len(self.families_run),
        }
        if self.columns_checked is not None:
            document["columns_checked"] = self.columns_checked
        if self.processing_mode:
            document["processing_mode"] = self.processing_mode
        if self.check_results:
            document["checks"] = [r.as_dict() for r in self.check_results]
        if self.provenance:
            document["source"] = self.provenance
        if self.families_skipped:
            document["families_skipped"] = self.families_skipped
        caveats = self.caveats()
        if caveats:
            document["caveats"] = caveats
        if self.halted:
            document["halt_reason"] = self.halt_reason()
        return document

    def validate(self, schema=None):
        """Validate this report against the schema. Returns a list of message strings."""
        return validate_document(self.as_dict(), schema)

    def __repr__(self):
        return "QualityReport(%s, %d findings, %d families)" % (
            self.grade, len(self.findings), len(self.check_results))


def load_schema(path=None):
    from ..config import load_json
    return load_json(path or SCHEMA_PATH, "quality report schema")


def validate_document(document, schema=None):
    schema = schema if schema is not None else load_schema()
    return [str(e) for e in jsonschema_mini.validate(document, schema)]


def source_provenance(dataset, canonical=None):
    """The dataset identity a report must carry, without leaking data."""
    if canonical is not None:
        base = canonical.source.provenance()
        record = {
            "source_name": base.get("source_name"),
            "source_type": base.get("source_type"),
            "sheet": base.get("sheet"),
            "rows": base.get("rows"),
            "columns": base.get("columns"),
            "processing_mode": canonical.processing_mode,
            "rows_examined": canonical.rows_examined,
            "complete": canonical.complete,
        }
        if base.get("reader_tier"):
            record["reader_tier"] = base["reader_tier"].get("tier")
            record["reader_name"] = base["reader_tier"].get("name")
        currencies = canonical.currencies()
        if currencies:
            record["currencies"] = currencies
        return record

    if dataset is None:
        return {}
    base = dataset.provenance()
    record = {"source_name": base.get("source_name"),
              "source_type": base.get("source_type"),
              "sheet": base.get("sheet"), "rows": base.get("rows"),
              "columns": base.get("columns")}
    if base.get("reader_tier"):
        record["reader_tier"] = base["reader_tier"].get("tier")
        record["reader_name"] = base["reader_tier"].get("name")
    return record
