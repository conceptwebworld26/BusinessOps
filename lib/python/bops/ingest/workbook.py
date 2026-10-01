"""Workbook inspection: constructs that must be detected before reading, not during.

Encryption, macros, external references and shared formulas all change what a read *means*,
so they are established up front from the package structure. The rule throughout is the
architecture's: an unsupported construct produces an explicit warning or a clear failure —
**never a guessed value**.
"""

import os
import zipfile
import xml.etree.ElementTree as ET

from ..errors import ConfigError

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

# OLE compound-document magic. An encrypted .xlsx is an OLE container, not a zip.
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class WorkbookFacts:
    """What the package says about itself, before any cell is read."""

    __slots__ = ("encrypted", "macro_enabled", "external_links", "shared_formula_count",
                 "hidden_sheets", "very_hidden_sheets", "sheet_names", "date_1904",
                 "notes")

    def __init__(self, encrypted=False, macro_enabled=False, external_links=(),
                 shared_formula_count=0, hidden_sheets=(), very_hidden_sheets=(),
                 sheet_names=(), date_1904=False, notes=()):
        self.encrypted = encrypted
        self.macro_enabled = macro_enabled
        self.external_links = list(external_links)
        self.shared_formula_count = shared_formula_count
        self.hidden_sheets = list(hidden_sheets)
        self.very_hidden_sheets = list(very_hidden_sheets)
        self.sheet_names = list(sheet_names)
        self.date_1904 = date_1904
        self.notes = list(notes)

    @property
    def visible_sheets(self):
        hidden = set(self.hidden_sheets) | set(self.very_hidden_sheets)
        return [s for s in self.sheet_names if s not in hidden]

    def as_dict(self):
        return {"encrypted": self.encrypted, "macro_enabled": self.macro_enabled,
                "external_links": self.external_links,
                "shared_formulas": self.shared_formula_count,
                "sheets": self.sheet_names, "hidden_sheets": self.hidden_sheets,
                "very_hidden_sheets": self.very_hidden_sheets,
                "date_system": "1904" if self.date_1904 else "1900",
                "notes": self.notes}


def detect_encrypted(path):
    """True if the file is an encrypted OOXML package.

    Encrypted workbooks are OLE containers. BusinessOps does not attempt to open them — no
    password prompting, no cracking, no bypass.
    """
    try:
        with open(path, "rb") as fh:
            return fh.read(8) == _OLE_MAGIC
    except OSError:
        return False


def inspect(path):
    """Establish workbook facts from the package. Raises for files that cannot be read."""
    if not os.path.exists(path):
        raise ConfigError("data file not found", source=path)
    if detect_encrypted(path):
        raise ConfigError(
            "This workbook is encrypted or password-protected. BusinessOps does not attempt "
            "to open protected files. Open it in Excel, save an unprotected copy (or export "
            "the sheet to CSV), and supply that instead.", source=path)

    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        raise ConfigError(
            "This file is not a readable .xlsx workbook — the archive is invalid or the "
            "file is corrupt. If it was renamed from another format, export a genuine "
            ".xlsx or .csv instead.", source=path)

    with archive:
        names = archive.namelist()
        notes = []

        macro_enabled = any(n.startswith("xl/vbaProject") for n in names)
        if macro_enabled:
            notes.append("Workbook contains a VBA project. Macros are never executed; only "
                         "cell values are read.")

        external_links = sorted(n for n in names if n.startswith("xl/externalLinks/")
                                and n.endswith(".xml"))
        if external_links:
            notes.append(
                "Workbook references %d external workbook(s). External references are not "
                "followed and no external file is downloaded; values that depend on them "
                "are read only from their cached results." % len(external_links))

        try:
            workbook_xml = archive.read("xl/workbook.xml")
        except KeyError:
            raise ConfigError(
                "This .xlsx package has no workbook part and cannot be read.", source=path)

        try:
            root = ET.fromstring(workbook_xml)
        except ET.ParseError as exc:
            raise ConfigError(
                "The workbook definition is malformed XML and cannot be parsed (%s)." % exc,
                source=path)

        sheets, hidden, very_hidden = [], [], []
        sheets_node = root.find("{%s}sheets" % NS)
        if sheets_node is not None:
            for sheet in sheets_node:
                name = sheet.get("name")
                sheets.append(name)
                state = (sheet.get("state") or "visible").lower()
                if state == "hidden":
                    hidden.append(name)
                elif state == "veryhidden":
                    very_hidden.append(name)
        if hidden or very_hidden:
            notes.append(
                "Workbook contains %d hidden sheet(s): %s. Hidden sheets are not read "
                "unless named explicitly, because they usually hold working calculations "
                "rather than reportable data."
                % (len(hidden) + len(very_hidden),
                   ", ".join(hidden + very_hidden)))

        properties = root.find("{%s}workbookPr" % NS)
        date_1904 = properties is not None and properties.get("date1904") in ("1", "true")

        shared = 0
        for name in names:
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                try:
                    shared += archive.read(name).count(b't="shared"')
                except KeyError:
                    continue
        if shared:
            notes.append(
                "Workbook uses %d shared-formula cell(s). Formulas are never evaluated; "
                "shared formulas are read from their cached values like any other formula."
                % shared)

    return WorkbookFacts(False, macro_enabled, external_links, shared, hidden,
                         very_hidden, sheets, date_1904, notes)


def csv_export_guidance(path, reason):
    """Tier 4 guidance: what to export and what is lost. Always names the reason."""
    return {
        "reason": reason,
        "source": path,
        "source_untouched": True,
        "action": "Open the workbook and export the sheet holding your transactions as CSV "
                  "(File > Save As > CSV UTF-8), then supply that file instead.",
        "required_structure": [
            "one header row of column names",
            "one row per transaction or per period",
            "a date column",
            "a revenue or amount column",
            "cost, customer, product, region and salesperson columns where available",
        ],
        "information_lost": [
            "multiple sheets — export the one that holds the data, or export each separately",
            "cell number formats, so currency must be stated in Business Context",
            "formulas — CSV export writes the calculated values, which is what BusinessOps "
            "wants anyway",
            "styling, merged cells and hidden columns",
        ],
        "reassurance": "Your original workbook is not modified, moved or opened for writing "
                       "at any point.",
    }


def format_csv_guidance(guidance):
    """Render Tier 4 guidance as user-facing text."""
    lines = [
        "Excel could not be processed: %s" % guidance["reason"],
        "",
        guidance["action"],
        "",
        "The exported file should have:",
    ]
    lines += ["  - %s" % item for item in guidance["required_structure"]]
    lines += ["", "What an export loses:"]
    lines += ["  - %s" % item for item in guidance["information_lost"]]
    lines += ["", guidance["reassurance"]]
    return "\n".join(lines)


def guidation_action(guidance):
    return guidance["action"]
