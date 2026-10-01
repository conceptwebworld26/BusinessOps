"""The data profile (M11, ADR-0036).

One closed request over 1-20 local files produces one `DataProfileResult`: what the Data Layer
already establishes about each file, sheet and column, a closed set of exact structural counts,
and references to what Data Quality, the KPI engine and the command registry decide. It is a
composition module beside `pipeline.py` and imports downward only.

What it is not, and why each line matters:

  * **Not a reader.** Every byte of data arrives through `workbook.inspect()` and
    `readers.read()`. Macros never run, external links are never followed, formulas are never
    evaluated, encryption is never bypassed.
  * **Not a classifier.** Kind, currency, sensitivity and role are M3's, carried verbatim and
    labelled `inferred` with the sample their rule examined.
  * **Not a quality engine or a KPI engine.** Findings are referenced by check id, severity and
    grade; KPI outcomes are reduced to the status bucket M5's own calculation returned. No value,
    reason text, message or evidence survives, because each may carry data.
  * **Not analytics.** No total, mean, minimum, maximum, ranking, forecast or join. Counts are
    exact over every row read; above the distinct cap a count is `null`, never estimated.
  * **Not evidence.** A profile describes data. `SynthesisSet.register_claims()` refuses it.

**No cell value leaves this module** except ISO currency codes and the date bounds of date
columns not classed `restricted` or `never`. The result is content-addressed (`dpr-` + 12 hex)
and bound to the SHA-256 of every source: once a source changes, the result refuses to
serialise. No model computes, edits or authors anything here.
"""

import copy
import hashlib
import io
import json
import os
import re
from decimal import ROUND_HALF_EVEN, Decimal

from . import jsonschema_mini
from . import mapping as mapping_mod
from . import normalize as normalize_mod
from .analytics import presentation as presentation_mod
from .commands import registry as command_registry
from .commands.runner import canonical_json, source_sha256
from .config import load_defaults, resolve as resolve_config
from .context import loader as context_loader
from .errors import BusinessOpsError
from .ingest import canonical as canonical_mod
from .ingest import readers
from .ingest import workbook as workbook_mod
from .kpi import catalog as kpi_catalog
from .kpi import primitives as kpi_primitives
from .kpi import registry as kpi_registry
from .privacy import aggregation as aggregation_mod
from .privacy import classes as classes_mod
from .privacy import sensitivity as sensitivity_mod
from .quality import checks as quality_checks

SCHEMA_VERSION = "1.0.0"
ANALYSIS = "data_profile"
SCHEMA_NAME = "profile.schema.json"
_SCHEMAS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "schemas"))

# -- limits (ADR-0036 sections 4 and 9) -------------------------------------------------------

MAX_SOURCES = 20
DISTINCT_CAP = 100000
#: The sample `canonical.build()` profiles kind, currency and ambiguity from (its default).
KIND_SAMPLE = 1000
#: The sample `sensitivity.classify_content()` examines.
SENSITIVITY_SAMPLE = sensitivity_mod.SAMPLE_SIZE
#: `mapping.semantic._kind_of()` corroborates a header from the first 200 non-empty values.
MAPPING_SAMPLE = 200

EXTENSIONS = (".csv", ".tsv", ".txt", ".xlsx", ".xlsm")
WORKBOOK_EXTENSIONS = (".xlsx", ".xlsm")
REQUEST_FIELDS = ("sources", "sheets", "objective", "presentation")
OBJECTIVE_FIELDS = ("command_id", "kpi_ids")

# -- statuses ---------------------------------------------------------------------------------

COMPLETE = "complete"
COMPLETE_WITH_LIMITATIONS = "complete_with_limitations"
PARTIAL = "partial"
UNAVAILABLE = "unavailable"
STATUSES = (COMPLETE, COMPLETE_WITH_LIMITATIONS, PARTIAL, UNAVAILABLE)

PROFILED = "profiled"
PART_STATUSES = (PROFILED, UNAVAILABLE)

# -- reason codes: why a source or sheet is unavailable (section 10) -------------------------

ENCRYPTED = "encrypted"
UNREADABLE = "unreadable"
MALFORMED = "malformed"
UNSUPPORTED_ENCODING = "unsupported_encoding"
EMPTY_FILE = "empty_file"
NO_COLUMNS = "no_columns"
READER_REFUSED = "reader_refused"
CHANGED_DURING_PROFILE = "changed_during_profile"
REASON_CODES = (ENCRYPTED, UNREADABLE, MALFORMED, UNSUPPORTED_ENCODING, EMPTY_FILE, NO_COLUMNS,
                READER_REFUSED, CHANGED_DURING_PROFILE)

#: The only guidance a refused workbook carries: the existing Tier 4 CSV export guidance.
CSV_EXPORT_GUIDANCE = "csv_export"

# -- limitation codes (section 10) ------------------------------------------------------------

SAMPLED_INFERENCE = "sampled_inference"
DISTINCT_COUNT_CAPPED = "distinct_count_capped"
HIDDEN_SHEET_NOT_PROFILED = "hidden_sheet_not_profiled"
MACRO_ENABLED_NOT_EXECUTED = "macro_enabled_not_executed"
EXTERNAL_LINKS_NOT_FOLLOWED = "external_links_not_followed"
DEGRADED_READER_TIER = "degraded_reader_tier"
MIXED_TYPES = "mixed_types"
NO_ROWS = "no_rows"
NO_DATE_COLUMN = "no_date_column"
INCONSISTENT_HEADERS_ACROSS_SHEETS = "inconsistent_headers_across_sheets"

LIMITATION_TEXT = {
    SAMPLED_INFERENCE:
        "Kind, sensitivity and role are inferred by the Data Layer from the first values of "
        "each column, not from every row; counts remain exact.",
    DISTINCT_COUNT_CAPPED:
        "The column holds more distinct values than the cap, so its distinct count is not "
        "stated and it takes part in no key overlap. Nothing was estimated.",
    HIDDEN_SHEET_NOT_PROFILED:
        "The workbook has hidden sheets that were not named in the request, so they were not "
        "read.",
    MACRO_ENABLED_NOT_EXECUTED:
        "The workbook contains a macro project. Macros were not executed; only cell values "
        "were read.",
    EXTERNAL_LINKS_NOT_FOLLOWED:
        "The workbook references external workbooks. They were not opened or downloaded; "
        "dependent cells were read from their cached values.",
    DEGRADED_READER_TIER:
        "The workbook was read by a degraded reader tier, which refuses rather than guesses "
        "some constructs.",
    MIXED_TYPES:
        "The column holds values of more than one kind.",
    NO_ROWS:
        "The dataset has a header but no data rows.",
    NO_DATE_COLUMN:
        "No column was inferred to hold dates, so no date coverage can be stated.",
    INCONSISTENT_HEADERS_ACROSS_SHEETS:
        "Profiled sheets of this workbook have different column headers.",
}
LIMITATION_CODES = tuple(LIMITATION_TEXT)

# -- fact bases (section 5) -------------------------------------------------------------------

OBSERVED = "observed"
CALCULATED = "calculated"
INFERRED = "inferred"
BASES = (OBSERVED, CALCULATED, INFERRED)

CANDIDATE = "candidate"
UNIQUE_NON_NULL = "unique_non_null"
MAPPED_ROLE = "mapped_role"
#: Roles whose mapping makes a column a key candidate (section 5).
KEY_ROLES = (mapping_mod.ORDER_ID, mapping_mod.CUSTOMER, mapping_mod.PRODUCT)
ABSENT = "absent"

#: Classes whose columns report name, kind, class and counts only (section 6).
WITHHELD_CLASSES = (classes_mod.RESTRICTED, classes_mod.NEVER)
DATE_KINDS = (normalize_mod.DATE, normalize_mod.DATETIME)

TRUST_STATEMENT = (
    "Every fact in this profile describes the structure of the supplied files, is produced by "
    "deterministic engine code and carries its basis: observed, calculated or inferred. It is "
    "not evidence about the business and decides nothing.")
USE_STATEMENT = (
    "Use this profile to see what the files contain and what BusinessOps could analyse with "
    "them. Key candidates and overlaps are proposals for the user to confirm, never joins; "
    "KPI and command entries state readiness, never a figure or an outcome.")

STALE = ("A source changed after this profile was built, so the profile no longer describes "
         "it and is not serialised. Build the profile again.")

_BUILD_TOKEN = object()


class DataProfileError(BusinessOpsError):
    """A refused request, a refused construction, or a stale profile. Carries no data values."""


# ---------------------------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------------------------

def _refuse(message):
    raise DataProfileError("data profile request refused: %s" % message)


def _plain_string(value):
    return isinstance(value, str) and value.strip() != ""


def validate_request(request):
    """Validate the closed request (ADR-0036 section 3). Returns an accepted copy or raises.

    Refuses whole; nothing is truncated or repaired. Messages name fields, never supplied values.
    """
    if not isinstance(request, dict):
        _refuse("the request must be a record with the fields %s" % ", ".join(REQUEST_FIELDS))
    unknown = sorted(str(k) for k in request if k not in REQUEST_FIELDS)
    if unknown:
        _refuse("unknown field(s) %s. Statistics, counts, kinds, classes, roles, grades, "
                "applicability, confidence, scores and profile objects are never accepted"
                % ", ".join(unknown))

    sources = request.get("sources")
    if not isinstance(sources, list) or not sources:
        _refuse("'sources' must be a list of 1-%d local file paths" % MAX_SOURCES)
    if len(sources) > MAX_SOURCES:
        _refuse("'sources' holds %d entries; at most %d are profiled and none is dropped"
                % (len(sources), MAX_SOURCES))
    seen = set()
    for index, source in enumerate(sources):
        where = "sources[%d]" % index
        if not _plain_string(source):
            _refuse("%s must be a non-empty path string" % where)
        if source.strip() == "-" or "://" in source or re.match(r"^[A-Za-z][A-Za-z0-9+.-]+:",
                                                                   source):
            _refuse("%s is not a local file path; URLs, schemes and stdin are refused" % where)
        if any(char in source for char in "*?["):
            _refuse("%s is a glob pattern; name each file" % where)
        if os.path.isdir(source):
            _refuse("%s is a directory; name each file" % where)
        if not os.path.isfile(source):
            _refuse("%s does not name an existing file" % where)
        if os.path.splitext(source)[1].lower() not in EXTENSIONS:
            _refuse("%s has an unsupported extension; the reader accepts %s"
                    % (where, ", ".join(EXTENSIONS)))
        key = os.path.normcase(os.path.abspath(source))
        if key in seen:
            _refuse("%s repeats an earlier source" % where)
        seen.add(key)

    sheets = request.get("sheets")
    if sheets is not None:
        if not isinstance(sheets, dict) or not sheets:
            _refuse("'sheets' must map a source, exactly as written in 'sources', to sheet names")
        for source, names in sheets.items():
            if source not in sources:
                _refuse("'sheets' names a source that is not in 'sources'")
            if os.path.splitext(source)[1].lower() not in WORKBOOK_EXTENSIONS:
                _refuse("'sheets' names a source that is not a workbook")
            if (not isinstance(names, list) or not names
                    or not all(_plain_string(n) for n in names)):
                _refuse("'sheets' entries must be non-empty lists of sheet names")
            if len(set(names)) != len(names):
                _refuse("'sheets' repeats a sheet name for one source")

    objective = request.get("objective")
    if objective is not None:
        if not isinstance(objective, dict) or not objective:
            _refuse("'objective' must be a record with 'command_id' and/or 'kpi_ids'")
        extra = sorted(str(k) for k in objective if k not in OBJECTIVE_FIELDS)
        if extra:
            _refuse("'objective' has unknown field(s) %s; only closed ids are accepted"
                    % ", ".join(extra))
        if "command_id" in objective:
            command_id = objective["command_id"]
            if not isinstance(command_id, str) or command_id not in command_registry.BY_ID:
                _refuse("'objective.command_id' is not a registered command id")
        if "kpi_ids" in objective:
            kpi_ids = objective["kpi_ids"]
            if (not isinstance(kpi_ids, list) or not kpi_ids
                    or not all(isinstance(k, str) and k in kpi_catalog.BY_ID for k in kpi_ids)):
                _refuse("'objective.kpi_ids' must be a non-empty list of catalogue KPI ids")
            if len(set(kpi_ids)) != len(kpi_ids):
                _refuse("'objective.kpi_ids' repeats an id")

    presentation = request.get("presentation", presentation_mod.LOCAL)
    if presentation not in presentation_mod.MODES:
        _refuse("'presentation' must be one of %s" % ", ".join(presentation_mod.MODES))

    accepted = {"sources": list(sources)}
    if sheets is not None:
        accepted["sheets"] = {source: list(sheets[source]) for source in sources
                              if source in sheets}
    if objective is not None:
        accepted["objective"] = {k: copy.deepcopy(objective[k]) for k in OBJECTIVE_FIELDS
                                 if k in objective}
    accepted["presentation"] = presentation
    return accepted


# ---------------------------------------------------------------------------------------------
# Identity helpers
# ---------------------------------------------------------------------------------------------

def _digest_id(prefix, value):
    return prefix + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:12]


def _rate(numerator, denominator):
    """An exact ratio shown to four places. Rounded once, here, at presentation."""
    if not denominator:
        return None
    value = (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0001"),
                                                                 rounding=ROUND_HALF_EVEN)
    return str(value)


def _fact(value, basis, operation, examined):
    return {"value": value, "basis": basis, "operation": operation, "examined": examined}


def _value_key(value):
    """A hashable key that never merges values of different types (True is not 1)."""
    return (type(value).__name__, value)


# ---------------------------------------------------------------------------------------------
# Reading - only through the Data Layer
# ---------------------------------------------------------------------------------------------

#: The Data Layer reports refusals as messages; this closed table maps each known refusal to one
#: reason code. The message itself is never carried (it may name data), and anything unknown is
#: `unreadable`. `tests/unit/test_m11_data_profiler.py` pins every entry against the real reader.
_READER_REASONS = (
    ("could not decode", UNSUPPORTED_ENCODING),
    ("file is empty", EMPTY_FILE),
    ("is encrypted", ENCRYPTED),
    ("not a readable .xlsx", MALFORMED),
    ("malformed", MALFORMED),
    ("missing from the package", MALFORMED),
    ("no workbook part", MALFORMED),
    ("contains no sheets", MALFORMED),
    ("could not open this workbook", MALFORMED),
    ("is empty", NO_COLUMNS),
    ("managed runtime", READER_REFUSED),
    ("Excel could not be processed", READER_REFUSED),
    ("preferred tier", READER_REFUSED),
)


def _reason_for(exc, path):
    if not os.path.isfile(path):
        return UNREADABLE
    # Quoted names (sheets, formats) are removed first, so a sheet called "file is empty" cannot
    # select a reason code.
    text = re.sub(r"'[^']*'|\"[^\"]*\"", "", str(exc))
    for fragment, code in _READER_REASONS:
        if fragment in text:
            return code
    return UNREADABLE


def _guidance_for(reason, extension):
    if extension in WORKBOOK_EXTENSIONS and reason in (READER_REFUSED, MALFORMED, ENCRYPTED):
        return CSV_EXPORT_GUIDANCE
    return None


# ---------------------------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------------------------

class _Builder(object):
    """Holds one build's working state. Never returned; the result carries only the document."""

    def __init__(self, request, config, context, prefer_tier):
        self.request = request
        self.presentation = request["presentation"]
        self.shareable = self.presentation == presentation_mod.SHAREABLE
        self.config = config
        self.context = context
        self.prefer_tier = prefer_tier
        self.limitations = []
        self.bindings = []
        self.key_sets = {}             # column_ref -> (kind, class, distinct key set)

    # -- presentation ------------------------------------------------------------------------

    def count(self, value):
        """Exact in `local`; below the k-anonymity floor banded in `shareable` (section 6)."""
        if (self.shareable and isinstance(value, int) and not isinstance(value, bool)
                and 0 < value < presentation_mod.DEFAULT_K):
            return aggregation_mod.band_count(value)
        return value

    def limit(self, code, subject_ref):
        entry = {"code": code, "subject_ref": subject_ref, "reason": LIMITATION_TEXT[code]}
        if entry not in self.limitations:
            self.limitations.append(entry)

    # -- sources -----------------------------------------------------------------------------

    def inspect_sources(self):
        """Hash, identify and inspect every source before any cell is read.

        A named sheet that does not exist refuses the whole request here, before anything is
        profiled.
        """
        planned, identities = [], set()
        sheets_requested = self.request.get("sheets", {})
        for given in self.request["sources"]:
            path = os.path.abspath(given)
            extension = os.path.splitext(path)[1].lower()
            name = os.path.basename(path)
            digest = source_sha256(path)
            if (name, digest) in identities:
                _refuse("two sources have the same name and identical bytes")
            identities.add((name, digest))
            entry = {"given": given, "path": path, "name": name, "extension": extension,
                     "digest": digest, "ref": _digest_id("src-", [name, digest]),
                     "facts": None, "reason": None, "sheets": [None]}
            if digest is None:
                entry["reason"] = UNREADABLE
            elif extension in WORKBOOK_EXTENSIONS:
                self._inspect_workbook(entry, sheets_requested.get(given))
            planned.append(entry)
        return planned

    def _inspect_workbook(self, entry, named):
        path = entry["path"]
        if workbook_mod.detect_encrypted(path):
            entry["reason"] = ENCRYPTED
            return
        try:
            facts = workbook_mod.inspect(path)
        except BusinessOpsError as exc:
            entry["reason"] = _reason_for(exc, path)
            return
        entry["facts"] = facts
        if named:
            absent = [n for n in named if n not in facts.sheet_names]
            if absent:
                _refuse("a named sheet does not exist in its workbook")
            entry["sheets"] = [s for s in facts.sheet_names if s in named]
        else:
            entry["sheets"] = list(facts.visible_sheets)
        hidden = set(facts.hidden_sheets) | set(facts.very_hidden_sheets)
        if hidden - set(entry["sheets"]):
            self.limit(HIDDEN_SHEET_NOT_PROFILED, entry["ref"])
        if facts.macro_enabled:
            self.limit(MACRO_ENABLED_NOT_EXECUTED, entry["ref"])
        if facts.external_links:
            self.limit(EXTERNAL_LINKS_NOT_FOLLOWED, entry["ref"])
        if not entry["sheets"]:
            entry["reason"] = NO_COLUMNS

    def read_source(self, entry):
        """Read every planned sheet through `readers.read()`, then re-hash the source."""
        reads = []
        if entry["reason"] is None:
            for sheet in entry["sheets"]:
                try:
                    dataset = readers.read(entry["path"], sheet_name=sheet,
                                           prefer_tier=self.prefer_tier)
                    reads.append((sheet, dataset, None))
                except BusinessOpsError as exc:
                    reads.append((sheet, None, _reason_for(exc, entry["path"])))
            after = source_sha256(entry["path"])
            if after != entry["digest"]:
                entry["reason"] = CHANGED_DURING_PROFILE
                return []
        return reads

    # -- datasets ----------------------------------------------------------------------------

    def dataset_record(self, entry, sheet, dataset, reason):
        tier = (dataset.reader_tier.tier if dataset is not None
                and dataset.reader_tier is not None else None)
        ref = _digest_id("dst-", [entry["ref"], sheet, tier])
        if dataset is None:
            return {"dataset_ref": ref, "source_ref": entry["ref"], "sheet": sheet,
                    "reader_tier": None, "status": UNAVAILABLE, "reason_code": reason,
                    "row_count": None, "column_count": None, "processing_mode": None,
                    "rows_examined": None, "complete": None, "warning_codes": None,
                    "duplicate_headers": None, "columns": [], "key_candidates": [],
                    "quality": None, "applicability": None}, None
        if not dataset.columns:
            return self.dataset_record(entry, sheet, None, NO_COLUMNS)

        canonical = canonical_mod.build(dataset, sample=KIND_SAMPLE)
        semantic_map = mapping_mod.infer(dataset)
        quality = quality_checks.run(dataset, semantic_map, self.config, canonical=canonical,
                                     context=self.context)
        rows = dataset.row_count
        read_op = "readers.read"

        if tier is not None and dataset.reader_tier.degraded:
            self.limit(DEGRADED_READER_TIER, ref)
        if rows == 0:
            self.limit(NO_ROWS, ref)
        if rows > min(KIND_SAMPLE, SENSITIVITY_SAMPLE, MAPPING_SAMPLE):
            self.limit(SAMPLED_INFERENCE, ref)

        seen_names, duplicates = set(), []
        for position, name in enumerate(dataset.columns, start=1):
            if name in seen_names:
                duplicates.append(position)
            seen_names.add(name)

        columns, candidates, refs_by_name = [], [], {}
        for position, name in enumerate(dataset.columns, start=1):
            column, candidate = self.column_record(ref, position, name, dataset, canonical,
                                                   semantic_map)
            columns.append(column)
            refs_by_name.setdefault(name, column["column_ref"])
            if candidate is not None:
                candidates.append(candidate)
        if not any(canonical.field(name).kind in DATE_KINDS for name in dataset.columns):
            self.limit(NO_DATE_COLUMN, ref)

        record = {
            "dataset_ref": ref, "source_ref": entry["ref"], "sheet": sheet,
            "reader_tier": _fact(tier, OBSERVED, read_op, None),
            "status": PROFILED, "reason_code": None,
            "row_count": _fact(self.count(rows), OBSERVED, read_op, None),
            "column_count": _fact(dataset.column_count, OBSERVED, read_op, None),
            "processing_mode": _fact(canonical.processing_mode, OBSERVED, "canonical.build",
                                     None),
            "rows_examined": _fact(self.count(canonical.rows_examined), OBSERVED,
                                   "canonical.build", None),
            "complete": _fact(canonical.complete, OBSERVED, "canonical.build", None),
            "warning_codes": _fact(sorted({w.code for w in dataset.warnings}), OBSERVED,
                                   read_op, None),
            "duplicate_headers": _fact(duplicates, CALCULATED, "data_profile.duplicate_headers",
                                       dataset.column_count),
            "columns": columns,
            "key_candidates": candidates,
            "quality": self.quality_reference(quality, refs_by_name),
            "applicability": self.applicability(dataset, semantic_map, canonical, quality),
        }
        return record, list(dataset.columns)

    def column_record(self, dataset_ref, position, name, dataset, canonical, semantic_map):
        field = canonical.field(name)
        profile = field.profile
        sensitivity = field.sensitivity.sensitivity
        withheld = sensitivity in WITHHELD_CLASSES
        column_ref = _digest_id("col-", [dataset_ref, position, name])
        rows = dataset.row_count

        values = [v for v in canonical.column(name, normalized=True) if v is not None]
        non_null = len(values)
        distinct, capped = set(), False
        for value in values:
            distinct.add(_value_key(value))
            if len(distinct) > DISTINCT_CAP:
                capped = True
                break
        distinct_count = None if capped else len(distinct)
        if capped:
            self.limit(DISTINCT_COUNT_CAPPED, column_ref)
        if profile.is_mixed:
            self.limit(MIXED_TYPES, column_ref)

        calc = "canonical.normalized_rows"
        coverage = None
        if field.kind in DATE_KINDS and not withheld:
            dates = [v.date() if hasattr(v, "date") and callable(v.date) else v
                     for v in values if hasattr(v, "isoformat")]
            if dates:
                coverage = _fact(
                    {"first": min(dates).isoformat(), "last": max(dates).isoformat(),
                     "period_count": len({kpi_primitives.period_key(d) for d in dates})},
                    CALCULATED, "kpi.primitives.period_key", self.count(len(dates)))

        mapped = None
        for role, mapping in sorted(semantic_map.mappings.items()):
            if mapping.column == name:
                mapped = mapping
                break

        kind_examined = self.count(min(rows, KIND_SAMPLE))
        facts = {
            "non_null_count": _fact(self.count(non_null), CALCULATED, calc, self.count(rows)),
            "empty_count": _fact(self.count(rows - non_null), CALCULATED, calc,
                                 self.count(rows)),
            "distinct_count": _fact(self.count(distinct_count), CALCULATED, calc,
                                    self.count(non_null)),
            "distinct_at_least": _fact(DISTINCT_CAP + 1 if capped else None, CALCULATED, calc,
                                       self.count(non_null)),
            "uniqueness_rate": _fact(None if capped else _rate(distinct_count, non_null),
                                     CALCULATED, calc, self.count(non_null)),
            "date_coverage": coverage,
            "kind": _fact(field.kind, INFERRED, "normalize.profile_column", kind_examined),
            "kind_counts": _fact({k: self.count(n) for k, n in sorted(profile.kind_counts.items())},
                                 INFERRED, "normalize.profile_column", kind_examined),
            "mixed_types": _fact(profile.is_mixed, INFERRED, "normalize.profile_column",
                                 kind_examined),
            "ambiguous_count": _fact(self.count(profile.ambiguous_count), INFERRED,
                                     "normalize.profile_column", kind_examined),
            "currencies": (None if withheld else
                           _fact(list(profile.currencies), INFERRED, "normalize.profile_column",
                                 kind_examined)),
            "day_first": (None if withheld else
                          _fact(profile.day_first, INFERRED, "normalize.profile_column",
                                kind_examined)),
            "sensitivity": _fact({"class": sensitivity,
                                  "reasons": list(field.sensitivity.reasons)},
                                 INFERRED, "sensitivity.classify_field",
                                 self.count(min(rows, SENSITIVITY_SAMPLE))),
            "role": (None if withheld else _fact(
                None if mapped is None else {"role": mapped.role, "status": mapped.status,
                                             "confidence": round(mapped.confidence, 3)},
                INFERRED, "mapping.infer", self.count(min(non_null, MAPPING_SAMPLE)))),
        }

        shown = name
        if self.shareable and sensitivity == classes_mod.NEVER:
            shown = "column_%d" % position
        column = {"column_ref": column_ref, "position": position, "original_name": shown,
                  "normalized_name": (shown if shown != name else field.name),
                  "facts": facts}

        rule = None
        if rows and distinct_count is not None and non_null == rows and distinct_count == rows:
            rule = UNIQUE_NON_NULL
        elif not withheld and mapped is not None and mapped.role in KEY_ROLES:
            rule = MAPPED_ROLE
        candidate = None
        if rule is not None:
            candidate = {"column_ref": column_ref, "rule": rule, "basis": CALCULATED,
                         "status": CANDIDATE}
            if not withheld and distinct_count:
                self.key_sets[column_ref] = (dataset_ref, field.kind, distinct)
        return column, candidate

    def quality_reference(self, quality, refs_by_name):
        """M4's verdict by reference. Messages, evidence, thresholds and observations dropped."""
        return {
            "grade": quality.grade,
            "halted": quality.halted,
            "completeness": quality.completeness,
            "findings": [
                {"check_id": f.check_id, "family": f.family, "code": f.code,
                 "severity": f.severity, "affected": self.count(f.affected),
                 "fields": [refs_by_name[n] for n in f.fields if n in refs_by_name],
                 "completeness": f.completeness}
                for f in quality.findings],
        }

    def applicability(self, dataset, semantic_map, canonical, quality):
        """What M5 and the command registry decide. No value, no outcome, no reason text."""
        objective = self.request.get("objective")
        if not objective:
            return None
        spec = (command_registry.BY_ID[objective["command_id"]]
                if "command_id" in objective else None)
        kpi_ids = list(objective.get("kpi_ids", []))
        if spec is not None:
            kpi_ids += [k for k in spec.kpi_focus if k not in kpi_ids]

        command = None
        if spec is not None:
            roles = []
            for role in spec.required_roles:
                mapping = semantic_map.mappings.get(role)
                roles.append({"role": role,
                              "status": mapping.status if mapping is not None else ABSENT})
            command = {"command_id": spec.command_id, "required_roles": roles}

        kpis = []
        if kpi_ids:
            results = kpi_registry.calculate(dataset, semantic_map, self.context, self.config,
                                             kpi_ids, canonical=canonical, quality=quality)
            for kpi_id in kpi_ids:
                definition = kpi_catalog.BY_ID[kpi_id]
                result = results.get(kpi_id)
                kpis.append({"kpi_id": kpi_id,
                             "status": result.status if result is not None else None,
                             "inputs": list(definition.inputs),
                             "minimum_periods": definition.minimum_periods})
        return {"command": command, "kpis": kpis}

    # -- relationships -----------------------------------------------------------------------

    def relationships(self, datasets):
        order = [d["dataset_ref"] for d in datasets if d["status"] == PROFILED]
        by_dataset = {}
        for column_ref, (dataset_ref, kind, keys) in self.key_sets.items():
            by_dataset.setdefault(dataset_ref, []).append((column_ref, kind, keys))
        position = {d["dataset_ref"]: {c["column_ref"]: c["position"] for c in d["columns"]}
                    for d in datasets}
        for dataset_ref in by_dataset:
            by_dataset[dataset_ref].sort(key=lambda item: position[dataset_ref][item[0]])

        found = []
        for i, left_ref in enumerate(order):
            for right_ref in order[i + 1:]:
                for left, left_kind, left_keys in by_dataset.get(left_ref, []):
                    for right, right_kind, right_keys in by_dataset.get(right_ref, []):
                        if left_kind != right_kind:
                            continue
                        union = len(left_keys | right_keys)
                        found.append({"left": left, "right": right,
                                      "overlap_rate": _rate(len(left_keys & right_keys), union),
                                      "basis": CALCULATED, "status": CANDIDATE})
        return found


def _resolve_context(project_dir, user_dir, context_overrides, load_context_files):
    """Business Context and configuration, resolved exactly as `pipeline.run()` resolves them."""
    context = context_loader.resolve(project_dir=project_dir, user_dir=user_dir,
                                     overrides=context_overrides, load_files=load_context_files)
    config = resolve_config(defaults=load_defaults(), user_context=None,
                            project_context=context.values or None, command_args=None)
    return context, config


def build(request, project_dir=None, user_dir=None, context_overrides=None,
          load_context_files=True, prefer_tier=None):
    """Profile the requested local files. Returns a `DataProfileResult` or raises.

    An invalid request is refused whole with `DataProfileError`. A source or sheet the Data
    Layer cannot read becomes `unavailable` with one closed reason code; nothing is estimated.
    """
    accepted = validate_request(request)
    context, config = _resolve_context(project_dir, user_dir, context_overrides,
                                       load_context_files)
    config_digest = "sha256:" + hashlib.sha256(
        canonical_json(config.as_dict()).encode("utf-8")).hexdigest()
    business_model = context.get("identity.business_model")
    currency = context.get("reporting.currency")
    context_used = (None if business_model is None and currency is None else
                    {"basis": "context", "business_model": business_model,
                     "currency": currency})

    builder = _Builder(accepted, config, context, prefer_tier)
    planned = builder.inspect_sources()

    sources, datasets, identity_sources, headers_by_source = [], [], [], {}
    for entry in planned:
        reads = builder.read_source(entry)
        records, profiled_sheets, tiers = [], [], []
        for sheet, dataset, reason in reads:
            record, header = builder.dataset_record(entry, sheet, dataset, reason)
            records.append(record)
            if record["status"] == PROFILED:
                profiled_sheets.append(sheet)
                tiers.append(record["reader_tier"]["value"])
                headers_by_source.setdefault(entry["ref"], []).append(header)
        if entry["reason"] is None and records and all(r["status"] == UNAVAILABLE
                                                       for r in records):
            entry["reason"] = records[0]["reason_code"]
        if entry["reason"] == CHANGED_DURING_PROFILE:
            records = []
        datasets.extend(records)
        if entry["reason"] not in (UNREADABLE, CHANGED_DURING_PROFILE):
            builder.bindings.append((entry["path"], entry["digest"], entry["ref"]))
        identity_sources.append([entry["name"], entry["digest"], profiled_sheets, tiers])
        sources.append(_source_record(builder, entry))

    for source_ref, headers in headers_by_source.items():
        if len(headers) > 1 and any(h != headers[0] for h in headers[1:]):
            builder.limit(INCONSISTENT_HEADERS_ACROSS_SHEETS, source_ref)

    # Discard unavailable sources' key sets before relationships are computed.
    profiled_refs = {d["dataset_ref"] for d in datasets if d["status"] == PROFILED}
    builder.key_sets = {c: v for c, v in builder.key_sets.items() if v[0] in profiled_refs}
    relationships = builder.relationships(datasets)

    ref_of = {entry["given"]: entry["ref"] for entry in planned}
    shown_request = {"sources": [ref_of[s] for s in accepted["sources"]]}
    if "sheets" in accepted:
        shown_request["sheets"] = {ref_of[s]: names for s, names in accepted["sheets"].items()}
    if "objective" in accepted:
        shown_request["objective"] = accepted["objective"]
    shown_request["presentation"] = accepted["presentation"]

    if not profiled_refs:
        status = UNAVAILABLE
    elif any(s["status"] == UNAVAILABLE for s in sources) or any(
            d["status"] == UNAVAILABLE for d in datasets):
        status = PARTIAL
    elif builder.limitations:
        status = COMPLETE_WITH_LIMITATIONS
    else:
        status = COMPLETE

    limits = {"max_sources": MAX_SOURCES, "distinct_cap": DISTINCT_CAP,
              "kind_sample": KIND_SAMPLE, "sensitivity_sample": SENSITIVITY_SAMPLE}
    profile_id = _digest_id("dpr-", {
        "schema_version": SCHEMA_VERSION, "limits": limits, "request": shown_request,
        "presentation": accepted["presentation"], "config_digest": config_digest,
        "context_used": context_used, "sources": identity_sources})

    document = {
        "schema_version": SCHEMA_VERSION,
        "analysis": ANALYSIS,
        "profile_id": profile_id,
        "status": status,
        "presentation": accepted["presentation"],
        "config_digest": config_digest,
        "limits": limits,
        "request": shown_request,
        "context_used": context_used,
        "sources": sources,
        "datasets": datasets,
        "relationships": relationships,
        "limitations": builder.limitations,
        "trust_statement": TRUST_STATEMENT,
        "use_statement": USE_STATEMENT,
    }
    return DataProfileResult(document, builder.bindings, _token=_BUILD_TOKEN)


def _source_record(builder, entry):
    facts = entry["facts"]
    workbook = None
    if facts is not None:
        hidden, very_hidden = set(facts.hidden_sheets), set(facts.very_hidden_sheets)
        workbook = {
            "basis": OBSERVED, "operation": "workbook.inspect",
            "sheets": [{"name": name,
                        "visibility": ("very_hidden" if name in very_hidden else
                                       "hidden" if name in hidden else "visible")}
                       for name in facts.sheet_names],
            "encrypted": facts.encrypted, "macro_enabled": facts.macro_enabled,
            "external_link_count": len(facts.external_links),
            "shared_formula_count": facts.shared_formula_count,
            "date_system": "1904" if facts.date_1904 else "1900",
        }
    try:
        size = os.path.getsize(entry["path"])
    except OSError:
        size = None
    reason = entry["reason"]
    return {
        "source_ref": entry["ref"],
        "source_name": entry["name"],
        "source_path": None if builder.shareable else entry["path"],
        "source_type": entry["extension"].lstrip("."),
        "size_bytes": size,
        "source_sha256": entry["digest"],
        "status": UNAVAILABLE if reason is not None else PROFILED,
        "reason_code": reason,
        "guidance": _guidance_for(reason, entry["extension"]),
        "workbook": workbook,
    }


# ---------------------------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------------------------

class DataProfileResult(object):
    """One profile. Built only by `build()`; no setter; refuses to serialise once stale."""

    __slots__ = ("_document", "_bindings")

    def __init__(self, document, bindings, _token=None):
        if _token is not _BUILD_TOKEN:
            raise DataProfileError(
                "a DataProfileResult is produced only by data_profile.build(); a caller-made "
                "profile, count, class or status is never accepted")
        object.__setattr__(self, "_document", copy.deepcopy(document))
        object.__setattr__(self, "_bindings", tuple(bindings))

    def __setattr__(self, name, value):
        raise DataProfileError("a DataProfileResult cannot be modified")

    def __delattr__(self, name):
        raise DataProfileError("a DataProfileResult cannot be modified")

    @property
    def profile_id(self):
        return self._document["profile_id"]

    @property
    def status(self):
        return self._document["status"]

    def stale_sources(self):
        """Source refs whose bytes no longer match the digest this profile was built from."""
        return [ref for path, digest, ref in self._bindings if source_sha256(path) != digest]

    def as_dict(self):
        if self.stale_sources():
            raise DataProfileError(STALE)
        return copy.deepcopy(self._document)

    def to_json(self, indent=2):
        """Deterministic serialisation in contract key order."""
        return json.dumps(self.as_dict(), indent=indent, ensure_ascii=False)


def load_schema():
    with io.open(os.path.join(_SCHEMAS, SCHEMA_NAME), encoding="utf-8") as handle:
        return json.load(handle)


def validate_document(document, schema=None):
    """Schema errors for a serialised profile; an empty list means it conforms."""
    return jsonschema_mini.validate(document, schema if schema is not None else load_schema())


def render(result):
    """The profile as text for the conversation. Structure only; refuses a stale profile."""
    if not isinstance(result, DataProfileResult):
        raise DataProfileError("only a DataProfileResult built by data_profile.build() renders")
    doc = result.as_dict()

    def value(fact):
        return "n/a" if fact is None or fact["value"] is None else fact["value"]

    lines = ["Data profile %s - %s (%s presentation)"
             % (doc["profile_id"], doc["status"], doc["presentation"]), ""]
    names = {}
    for source in doc["sources"]:
        names[source["source_ref"]] = source["source_name"]
        line = "Source %s [%s]: %s" % (source["source_name"], source["source_type"],
                                       source["status"])
        if source["reason_code"]:
            line += " (%s)" % source["reason_code"]
        lines.append(line)
        if source["guidance"] == CSV_EXPORT_GUIDANCE:
            lines.append(workbook_mod.format_csv_guidance(workbook_mod.csv_export_guidance(
                source["source_name"], "the workbook could not be read (%s)"
                % source["reason_code"])))
        if source["workbook"]:
            lines.append("  sheets: %s" % ", ".join(
                "%s (%s)" % (s["name"], s["visibility"]) for s in source["workbook"]["sheets"]))
    for dataset in doc["datasets"]:
        lines.append("")
        label = names.get(dataset["source_ref"], dataset["source_ref"])
        if dataset["sheet"]:
            label += " / %s" % dataset["sheet"]
        if dataset["status"] != PROFILED:
            lines.append("Dataset %s: unavailable (%s)" % (label, dataset["reason_code"]))
            continue
        lines.append("Dataset %s: %s rows, %s columns, reader tier %s, %s processing"
                     % (label, value(dataset["row_count"]), value(dataset["column_count"]),
                        value(dataset["reader_tier"]), value(dataset["processing_mode"])))
        for column in dataset["columns"]:
            facts = column["facts"]
            parts = ["kind %s" % value(facts["kind"]),
                     "class %s" % facts["sensitivity"]["value"]["class"],
                     "non-null %s" % value(facts["non_null_count"]),
                     "empty %s" % value(facts["empty_count"]),
                     "distinct %s" % value(facts["distinct_count"])]
            if facts["date_coverage"] is not None:
                coverage = facts["date_coverage"]["value"]
                parts.append("dates %s to %s over %s months"
                             % (coverage["first"], coverage["last"], coverage["period_count"]))
            if facts["currencies"] is not None and facts["currencies"]["value"]:
                parts.append("currencies %s" % ", ".join(facts["currencies"]["value"]))
            if facts["role"] is not None and facts["role"]["value"] is not None:
                role = facts["role"]["value"]
                parts.append("role %s (%s)" % (role["role"], role["status"]))
            lines.append("  %d. %s: %s" % (column["position"], column["original_name"],
                                           "; ".join(str(p) for p in parts)))
        if dataset["key_candidates"]:
            lines.append("  key candidates (for you to confirm): %s" % ", ".join(
                "column %s" % _position_of(dataset, c["column_ref"])
                for c in dataset["key_candidates"]))
        quality = dataset["quality"]
        lines.append("  data quality grade %s; %d finding(s)"
                     % (quality["grade"], len(quality["findings"])))
        applicability = dataset["applicability"]
        if applicability:
            if applicability["command"]:
                lines.append("  /%s needs: %s" % (applicability["command"]["command_id"], ", ".join(
                    "%s (%s)" % (r["role"], r["status"])
                    for r in applicability["command"]["required_roles"])))
            for kpi in applicability["kpis"]:
                lines.append("  KPI %s: %s" % (kpi["kpi_id"], kpi["status"]))
    if doc["relationships"]:
        lines += ["", "Key overlap candidates (not joins):"]
        for relationship in doc["relationships"]:
            lines.append("  %s ~ %s: overlap %s" % (relationship["left"], relationship["right"],
                                                    relationship["overlap_rate"]))
    if doc["limitations"]:
        lines += ["", "Limitations:"]
        lines += ["  - %s (%s): %s" % (l["code"], l["subject_ref"], l["reason"])
                  for l in doc["limitations"]]
    lines += ["", doc["trust_statement"], doc["use_statement"]]
    return "\n".join(lines)


def _position_of(dataset, column_ref):
    for column in dataset["columns"]:
        if column["column_ref"] == column_ref:
            return column["position"]
    return column_ref
