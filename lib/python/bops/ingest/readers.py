"""CSV and XLSX readers.

XLSX is read through the approved tiers (ADR-0008):

    Tier 1  openpyxl, when importable
    Tier 3  the stdlib parser (zipfile + ElementTree)

All four tiers are implemented (Milestone 3):

    Tier 2  openpyxl in the managed runtime, run out of process
    Tier 4  guided CSV export, when no Python reader is usable

Workbook-level constructs - encryption, macros, external references, shared formulas,
hidden sheets - are established by `workbook.inspect` before any cell is read.

Invariants that hold at every tier:

  * Files are opened **read-only**. Nothing is ever written back.
  * Formulas are **never evaluated**. The cached value is read; a formula cell with no
    cached value produces a warning, never an invented number.
  * A construct the reader cannot resolve produces a warning or a hard failure — never a
    guessed value.
"""

import csv
import datetime
import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET

from ..errors import ConfigError
from ..runtime import tiers as tier_mod
from . import workbook as workbook_mod
from .dataset import Dataset, IngestWarning

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def _q(tag):
    return "{%s}%s" % (NS, tag)


# --------------------------------------------------------------------------
# Number formats
# --------------------------------------------------------------------------

# ECMA-376 built-in formats that denote a date or time. The Tier 3 gap found during the
# architecture review was that these were unresolved; the ids BusinessOps needs are
# enumerated here, and anything outside the known set is reported rather than assumed.
BUILTIN_DATE_IDS = frozenset(list(range(14, 23)) + [27, 30, 36] + list(range(45, 48)) + [50, 57])
BUILTIN_PERCENT_IDS = frozenset([9, 10])
BUILTIN_KNOWN_IDS = frozenset(range(0, 50)) | frozenset(range(50, 59))

CURRENCY_SYMBOLS = "$£€¥₹₩₽₪฿"


def _is_date_format(fmt_id, code):
    if fmt_id in BUILTIN_DATE_IDS:
        return True
    if not code:
        return False
    stripped = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", code)
    return bool(re.search(r"[dmyhs]", stripped, re.I))


def _is_percent_format(fmt_id, code):
    if fmt_id in BUILTIN_PERCENT_IDS:
        return True
    return bool(code) and "%" in re.sub(r'"[^"]*"', "", code)


def _currency_of(code):
    if not code:
        return None
    for literal in re.findall(r'"([^"]*)"', code):
        for char in literal:
            if char in CURRENCY_SYMBOLS:
                return char
    for char in code:
        if char in CURRENCY_SYMBOLS:
            return char
    match = re.search(r"\[\$([^\]\-]+)", code)
    return match.group(1) if match else None


EXCEL_EPOCH_1900 = datetime.date(1899, 12, 30)
EXCEL_EPOCH_1904 = datetime.date(1904, 1, 1)


def serial_to_date(serial, use_1904=False):
    value = float(serial)
    epoch = EXCEL_EPOCH_1904 if use_1904 else EXCEL_EPOCH_1900
    whole = int(value)
    if not use_1904 and whole < 60:          # pre Lotus leap-year bug
        whole += 1
    fraction = value - int(value)
    day = epoch + datetime.timedelta(days=whole)
    if fraction:
        return datetime.datetime.combine(day, datetime.time()) + datetime.timedelta(days=fraction)
    return day


def _coerce_cell(raw, is_date, is_percent, use_1904):
    """Type a numeric cell value. Shared by the ordinary and external-reference paths."""
    if raw is None:
        return None
    if is_date:
        return serial_to_date(raw, use_1904)
    try:
        value = float(raw) if ("." in raw or "e" in raw.lower()) else int(raw)
    except (ValueError, AttributeError):
        return raw
    if is_percent and isinstance(value, (int, float)):
        return float(value)
    return value


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------

def _sniff(sample):
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return ","


def _coerce(value):
    """Type a CSV string, leaving genuinely ambiguous values as text.

    The reader deliberately does not decide whether "1.234" means 1.234 or 1234 - that
    depends on a locale convention the file does not state. Such values stay as text so
    `bops.normalize` can flag them for confirmation instead of a wrong reading passing
    silently into a total.
    """
    if value is None:
        return None
    text = value.strip()
    if text == "":
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            return datetime.date.fromisoformat(text)
        except ValueError:
            return text
    if re.fullmatch(r"[-+]?\d+", text):
        try:
            return int(text)
        except ValueError:
            return text
    if re.fullmatch(r"[-+]?\d*\.\d+([eE][-+]?\d+)?", text):
        if _separator_ambiguous(text):
            return text
        try:
            return float(text)
        except ValueError:
            return text
    return text


def _separator_ambiguous(text):
    """True when a single separator with three trailing digits could go either way."""
    from .. import normalize as _normalize
    body = text.lstrip("+-")
    _cleaned, ambiguity = _normalize._separator_reading(body)
    return ambiguity is not None


def read_csv(path, encoding=None):
    """Read a delimited file into a Dataset. The file is opened read-only."""
    if not os.path.exists(path):
        raise ConfigError("data file not found", source=path)

    warnings = []
    encodings = [encoding] if encoding else ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    text = None
    for candidate in encodings:
        try:
            with open(path, "r", encoding=candidate, newline="") as fh:
                text = fh.read()
            if candidate not in ("utf-8-sig", "utf-8"):
                warnings.append(IngestWarning(
                    "encoding_fallback",
                    "File is not UTF-8; decoded as %s. Verify accented characters." % candidate))
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ConfigError("could not decode file with any supported encoding", source=path)

    delimiter = _sniff(text[:8192])
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration:
        raise ConfigError("file is empty", source=path)

    columns = [h.strip() for h in header]
    if len(set(columns)) != len(columns):
        seen, duplicates = set(), set()
        for name in columns:
            (duplicates if name in seen else seen).add(name)
        warnings.append(IngestWarning(
            "duplicate_headers",
            "Duplicate column names: %s. Later columns shadow earlier ones."
            % ", ".join(sorted(duplicates))))

    rows = []
    for number, raw in enumerate(reader, start=2):
        if not any(cell.strip() for cell in raw):
            continue
        if len(raw) != len(columns):
            warnings.append(IngestWarning(
                "ragged_row",
                "Row has %d fields, header has %d." % (len(raw), len(columns)),
                location="row %d" % number))
        rows.append({columns[i]: _coerce(raw[i]) if i < len(raw) else None
                     for i in range(len(columns))})

    return Dataset(columns, rows, "csv", path, warnings=warnings)


# --------------------------------------------------------------------------
# XLSX — Tier 3, standard library only
# --------------------------------------------------------------------------

def _load_styles(archive):
    """Per cellXf: (is_date, is_percent, currency symbol, unresolved format id)."""
    try:
        root = ET.fromstring(archive.read("xl/styles.xml"))
    except KeyError:
        return []
    custom = {}
    numfmts = root.find(_q("numFmts"))
    if numfmts is not None:
        for entry in numfmts:
            custom[int(entry.get("numFmtId"))] = entry.get("formatCode")

    styles = []
    cellxfs = root.find(_q("cellXfs"))
    if cellxfs is not None:
        for xf in cellxfs:
            fmt_id = int(xf.get("numFmtId", 0))
            code = custom.get(fmt_id)
            unresolved = code is None and fmt_id not in BUILTIN_KNOWN_IDS
            styles.append((_is_date_format(fmt_id, code),
                           _is_percent_format(fmt_id, code),
                           _currency_of(code),
                           fmt_id if unresolved else None))
    return styles


def _load_shared_strings(archive):
    try:
        data = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    return ["".join(t.text or "" for t in si.iter(_q("t")))
            for si in ET.fromstring(data)]


def _sheet_index(archive):
    rels = {rel.get("Id"): rel.get("Target")
            for rel in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
    index = {}
    for sheet in ET.fromstring(archive.read("xl/workbook.xml")).find(_q("sheets")):
        target = (rels.get(sheet.get(REL_NS)) or "").lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        index[sheet.get("name")] = target
    return index


def _uses_1904(archive):
    properties = ET.fromstring(archive.read("xl/workbook.xml")).find(_q("workbookPr"))
    return properties is not None and properties.get("date1904") in ("1", "true")


def _column_of(ref):
    return "".join(ch for ch in (ref or "") if ch.isalpha())


def read_xlsx_stdlib(path, sheet_name=None, facts=None):
    """Tier 3 reader: zipfile + ElementTree, no dependencies.

    Encryption, macros, external references, shared formulas and hidden sheets are
    established by `workbook.inspect` before any cell is read, so an unsupported construct
    fails or warns up front rather than producing a quietly wrong value.
    """
    if not os.path.exists(path):
        raise ConfigError("data file not found", source=path)

    warnings = []
    unresolved_formats = set()
    external_value_cells = 0

    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        raise ConfigError(
            "This file is not a readable .xlsx workbook - the archive is invalid or the "
            "file is corrupt.", source=path)

    facts = facts or workbook_mod.inspect(path)
    for note in facts.notes:
        warnings.append(IngestWarning("workbook_construct", note))

    with archive:
        styles = _load_styles(archive)
        shared = _load_shared_strings(archive)
        sheets = _sheet_index(archive)
        use_1904 = _uses_1904(archive)
        if not sheets:
            raise ConfigError("workbook contains no sheets", source=path)

        if sheet_name:
            target_name = sheet_name
        else:
            visible = [s for s in facts.visible_sheets if s in sheets]
            target_name = visible[0] if visible else next(iter(sheets))
        if target_name not in sheets:
            raise ConfigError("sheet %r not found; available: %s"
                              % (target_name, ", ".join(sheets)), source=path)
        if target_name in facts.hidden_sheets or target_name in facts.very_hidden_sheets:
            warnings.append(IngestWarning(
                "hidden_sheet_read",
                "Sheet %r is hidden and was read only because it was named explicitly."
                % target_name))

        grid = {}
        try:
            handle = archive.open(sheets[target_name])
        except KeyError:
            raise ConfigError(
                "Worksheet part for sheet %r is missing from the package." % target_name,
                source=path)
        with handle:
            current = None
            try:
                events = list(ET.iterparse(handle, events=("start", "end")))
            except ET.ParseError as exc:
                raise ConfigError(
                    "Sheet %r contains malformed XML and cannot be read (%s)."
                    % (target_name, exc), source=path)
            for event, element in events:
                if event == "start" and element.tag == _q("row"):
                    current = int(element.get("r") or 0)
                elif event == "end" and element.tag == _q("c"):
                    ref = element.get("r")
                    cell_type = element.get("t")
                    style_index = element.get("s")
                    is_date = is_percent = False
                    unresolved = None
                    if style_index is not None and int(style_index) < len(styles):
                        is_date, is_percent, _currency, unresolved = styles[int(style_index)]
                    if unresolved is not None:
                        unresolved_formats.add(unresolved)

                    formula = element.find(_q("f"))
                    value_node = element.find(_q("v"))
                    raw = value_node.text if value_node is not None else None

                    # A "[n]Sheet!A1" style reference points at another workbook. Counted
                    # independently of the value branch, since any cell type may carry one.
                    if formula is not None and "[" in (formula.text or ""):
                        external_value_cells += 1

                    if formula is not None and raw is None:
                        # Never evaluate; never invent.
                        warnings.append(IngestWarning(
                            "formula_without_cached_value",
                            "Formula cell has no cached value. BusinessOps does not evaluate "
                            "formulas, so this cell is empty rather than computed.",
                            location=ref))
                        value = None
                    elif cell_type == "inlineStr":
                        node = element.find(_q("is"))
                        value = ("".join(t.text or "" for t in node.iter(_q("t")))
                                 if node is not None else None)
                    elif cell_type == "s":
                        value = shared[int(raw)] if raw is not None else None
                    elif cell_type == "str":
                        value = raw
                    elif cell_type == "b":
                        value = raw == "1"
                    elif cell_type == "e":
                        value = None
                        warnings.append(IngestWarning(
                            "cell_error", "Cell contains an Excel error value (%s)." % raw,
                            location=ref))
                    else:
                        value = _coerce_cell(raw, is_date, is_percent, use_1904)

                    if current:
                        grid.setdefault(current, {})[_column_of(ref)] = value
                    element.clear()
                elif event == "end" and element.tag == _q("row"):
                    element.clear()

    if external_value_cells:
        warnings.append(IngestWarning(
            "external_reference_cached",
            "%d cell(s) reference an external workbook. The external file was not opened "
            "or downloaded; only the value cached in this workbook was used, and it may be "
            "stale." % external_value_cells))

    if unresolved_formats:
        warnings.append(IngestWarning(
            "unresolved_number_format",
            "Number format id(s) %s are outside the set this reader resolves. Affected "
            "cells were read as plain numbers rather than guessed as dates or percentages."
            % ", ".join(str(i) for i in sorted(unresolved_formats))))

    tier = tier_mod.ReaderTier(tier_mod.TIER_STDLIB, "stdlib reader used for this workbook")
    return _grid_to_dataset(grid, path, target_name, list(sheets), tier, warnings)


def _grid_to_dataset(grid, path, sheet, sheets, tier, warnings):
    if not grid:
        raise ConfigError("sheet %r is empty" % sheet, source=path)

    header_row = min(grid)
    header_cells = grid[header_row]
    letters = sorted(header_cells, key=lambda c: (len(c), c))
    columns, mapping = [], {}
    for letter in letters:
        name = header_cells[letter]
        if name is None or str(name).strip() == "":
            continue
        name = str(name).strip()
        columns.append(name)
        mapping[letter] = name

    rows = []
    for number in sorted(k for k in grid if k > header_row):
        cells = grid[number]
        if all(v is None for v in cells.values()):
            continue
        rows.append({mapping[letter]: cells.get(letter)
                     for letter in mapping})

    return Dataset(columns, rows, "xlsx", path, reader_tier=tier,
                   sheet=sheet, sheets=sheets, warnings=warnings)


# --------------------------------------------------------------------------
# XLSX — Tier 1, openpyxl
# --------------------------------------------------------------------------

def read_xlsx_openpyxl(path, sheet_name=None, facts=None):
    """Tier 1 reader.

    `read_only=True` streams rather than materialising the workbook; `data_only=True` reads
    cached values, so formulas are never evaluated and macros never run.
    """
    import openpyxl

    if not os.path.exists(path):
        raise ConfigError("data file not found", source=path)

    facts = facts or workbook_mod.inspect(path)
    warnings = [IngestWarning("workbook_construct", note) for note in facts.notes]

    try:
        workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except Exception as exc:                      # openpyxl raises a wide variety here
        raise ConfigError(
            "openpyxl could not open this workbook (%s). If it is corrupt or protected, "
            "export the sheet to CSV and supply that instead." % exc, source=path)

    try:
        sheets = list(workbook.sheetnames)
        if sheet_name:
            target = sheet_name
        else:
            visible = [s for s in facts.visible_sheets if s in sheets]
            target = visible[0] if visible else sheets[0]
        if target not in sheets:
            raise ConfigError("sheet %r not found; available: %s"
                              % (target, ", ".join(sheets)), source=path)
        if target in facts.hidden_sheets or target in facts.very_hidden_sheets:
            warnings.append(IngestWarning(
                "hidden_sheet_read",
                "Sheet %r is hidden and was read only because it was named explicitly."
                % target))

        worksheet = workbook[target]

        # Merged cells: openpyxl reports the value on the top-left cell only, the rest as
        # None. In read_only mode merged ranges are not exposed, so the honest statement is
        # that only the anchor carries the value.
        merged = getattr(worksheet, "merged_cells", None)
        if merged is not None and getattr(merged, "ranges", None):
            warnings.append(IngestWarning(
                "merged_cells",
                "Sheet contains %d merged range(s). The value is read from the top-left "
                "cell of each range; the remaining cells are empty. Merged headers may "
                "therefore leave columns unnamed." % len(merged.ranges)))

        grid, header_row = {}, None
        for row in worksheet.iter_rows():
            number = row[0].row if row else None
            if number is None:
                continue
            values = {}
            for cell in row:
                value = cell.value
                if isinstance(value, datetime.datetime) and value.time() == datetime.time():
                    value = value.date()
                values[_column_of(cell.coordinate)] = value
            if header_row is None and any(v is not None for v in values.values()):
                header_row = number
            grid[number] = values
    finally:
        workbook.close()

    tier = tier_mod.ReaderTier(tier_mod.TIER_OPENPYXL_SYSTEM,
                               "openpyxl used for this workbook")
    return _grid_to_dataset(grid, path, target, sheets, tier, warnings)


def read_xlsx_managed(path, sheet_name=None, facts=None, interpreter=None):
    """Tier 2 reader: run the Tier 1 reader inside the managed runtime, out of process.

    The managed venv has openpyxl but this interpreter does not, so the read happens in a
    subprocess that emits JSON on stdout. Nothing is installed here - `bootstrap()` is the
    only function that installs, and only with explicit consent.
    """
    import json
    import subprocess

    interpreter = interpreter or tier_mod.managed_python()
    if not interpreter:
        raise ConfigError("the managed runtime is not present", source=path)

    facts = facts or workbook_mod.inspect(path)
    engine_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    worker = os.path.join(os.path.dirname(__file__), "_managed_read.py")

    argv = [interpreter, worker, engine_root, path]
    if sheet_name:
        argv.append(sheet_name)

    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigError("the managed runtime could not be started (%s)" % exc, source=path)

    if result.returncode != 0:
        raise ConfigError(
            "the managed runtime failed to read this workbook: %s"
            % (result.stderr or "").strip(), source=path)

    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ConfigError("the managed runtime returned unreadable output", source=path)

    # Dates survive the JSON hop as ISO strings; restore them so both tiers agree.
    rows = [{k: _revive(v) for k, v in row.items()} for row in payload["rows"]]
    warnings = [IngestWarning(w.get("code"), w.get("message"), w.get("location"))
                for w in payload.get("warnings", [])]
    warnings.append(IngestWarning(
        "tier2_managed_runtime",
        "Read through the managed BusinessOps runtime (openpyxl %s), out of process."
        % tier_mod.OPENPYXL_VERSION))

    tier = tier_mod.ReaderTier(tier_mod.TIER_OPENPYXL_MANAGED,
                               "managed runtime used for this workbook",
                               interpreter=interpreter)
    return Dataset(payload["columns"], rows, "xlsx", path, reader_tier=tier,
                   sheet=payload.get("sheet"), sheets=payload.get("sheets") or [],
                   warnings=warnings)


_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")


def _revive(value):
    """Restore dates that JSON flattened to strings, so tiers agree on types."""
    if not isinstance(value, str):
        return value
    if _ISO_DATE.match(value):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return value
    if _ISO_DATETIME.match(value):
        try:
            return datetime.datetime.fromisoformat(value.replace(" ", "T"))
        except ValueError:
            return value
    return value


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------

def read_xlsx(path, sheet_name=None, prefer_tier=None, allow_bootstrap="ask"):
    """Read a workbook using the highest available tier (or a pinned one).

    Workbook facts are established once and passed down, so encryption and corruption fail
    before a tier is even chosen.
    """
    facts = workbook_mod.inspect(path)
    tier = tier_mod.resolve(allow_bootstrap=allow_bootstrap, prefer=prefer_tier)

    if tier.tier == tier_mod.TIER_OPENPYXL_SYSTEM:
        return read_xlsx_openpyxl(path, sheet_name, facts)

    if tier.tier == tier_mod.TIER_OPENPYXL_MANAGED:
        return read_xlsx_managed(path, sheet_name, facts, tier.interpreter)

    if tier.tier == tier_mod.TIER_STDLIB:
        dataset = read_xlsx_stdlib(path, sheet_name, facts)
        dataset.reader_tier = tier
        warning = tier.quality_warning()
        if warning:
            dataset.warnings.append(IngestWarning("degraded_reader_tier", warning))
        return dataset

    # Tier 4: no usable reader. Explain what to export and what it costs.
    guidance = workbook_mod.csv_export_guidance(
        path, "no usable Python Excel reader is available on this machine")
    raise ConfigError(workbook_mod.format_csv_guidance(guidance), source=path)


def read(path, sheet_name=None, prefer_tier=None, allow_bootstrap="ask"):
    """Read any supported business data file."""
    extension = os.path.splitext(path)[1].lower()
    if extension in (".csv", ".tsv", ".txt"):
        return read_csv(path)
    if extension in (".xlsx", ".xlsm"):
        return read_xlsx(path, sheet_name, prefer_tier, allow_bootstrap)
    raise ConfigError(
        "Unsupported file type %r. BusinessOps reads .csv, .tsv and .xlsx/.xlsm. Export "
        "your data to one of those and supply that file." % extension, source=path)
