"""The internal-value boundary: which fragments of a research request came from business data.

The gate used to judge a request by its *shape*. A field called `customer` was refused, a
derived value was judged by the sensitivity class its caller declared, and everything else
- the subject, the public terms, the operation id - was public by construction. That is
where M13-DEF-13 came through: a customer name from the staged dataset arrived as a
*subject*, the shape was fine, and it was briefed to the scout at Tier 0.

The fix is provenance, established by the gate rather than asserted by the caller
(ADR-0050). Sensitivity is already a property of the data from ingestion onward
(`privacy.sensitivity`): every column of every dataset carries a class. This module reads
the business data in the working directory, keeps the values of every column that is not
`public`, and reports any request fragment that carries one. A value found in a `never`
column is Tier 3 wherever it appears in the request; a value found in any other non-public
column is internal and can travel only under Tier 2 approval. Neither is decided by a field
name or by a flag the caller sets.

Three properties the gate depends on:

**Not caller-controlled.** The register is built from the files on disk, by the gate, on
every assessment. No argument, request field or descriptor class can supply, empty or
relabel it.

**Fail-closed.** A data file that cannot be read, or a workspace too large to screen within
the stated bounds, makes the boundary *unverifiable*, and the gate refuses rather than
assuming nothing internal is present.

**Value-free reporting.** A finding names the request field, the column and the file - never
the value - so a refusal cannot repeat what it declined to send.

What it does not do: it is not a global string filter. Values from `public` columns (region,
category, period) are never registered, so ordinary Tier 0 vocabulary is unaffected, and
matching is on whole normalised values, not on fragments of them.
"""

import os
import re
from decimal import Decimal, InvalidOperation

from .. import privacy as privacy_mod
from ..ingest import readers

#: Business data files the boundary reads. `.txt` is deliberately absent: `readers.read`
#: accepts it as CSV, but a workspace's text files are overwhelmingly notes, and reading a
#: note as a table would register its sentences as "values".
DATA_EXTENSIONS = (".csv", ".tsv", ".xlsx", ".xlsm")

#: Directories that hold no user business data. Any other directory whose name starts with
#: a dot is skipped as well.
SKIPPED_DIRECTORIES = frozenset({
    "businessops-output", "node_modules", "__pycache__", "venv", "env", "site-packages",
})

#: Bounds. Exceeding any of them makes the boundary unverifiable, never silently partial.
MAX_ENTRIES = 20000
MAX_FILES = 50
MAX_FILE_BYTES = 100 * 1024 * 1024

#: A registered text value must normalise to at least this many characters. Shorter values
#: ("N", "A1") would match ordinary words and are not identifying on their own.
MIN_VALUE_CHARS = 3

#: Longest registered phrase, in tokens. Longer cell values (free-text notes) are still
#: registered, but matched only when a fragment contains them whole.
MAX_PHRASE_TOKENS = 12

#: The installed plugin. Its files are the synthetic demo dataset and test fixtures
#: (CLAUDE.md §3: "never real data"), not the user's business data, so they are never read.
#: Derived from this file's location, so no caller can move it.
PLUGIN_ROOT = os.path.realpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, os.pardir, os.pardir))

#: Kinds of finding.
INTERNAL_VALUE = "internal_value"            # the fragment carries a registered value
UNATTRIBUTED_FIGURE = "unattributed_figure"  # a figure no public term can carry

_NON_ALNUM = re.compile(r"[\W_]+", re.UNICODE)
_NUMBER = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?")

#: A figure in free text has no public provenance: a Tier 0 term is a vocabulary word, a
#: year or a band, and an exact amount, rate or decimal is none of those. Internal figures
#: travel only as `AggregateDescriptor`s, which the Tier 1 checks judge.
_FIGURE_PATTERNS = (
    re.compile(r"\d\s*%"),                                     # a rate
    re.compile(r"[£$€¥]\s*\d|\d\s*(?:GBP|USD|EUR|JPY)\b", re.I),  # an amount
    re.compile(r"\d\.\d"),                                     # a decimal
    re.compile(r"\d{1,3}(?:,\d{3})+"),                         # a thousands-separated number
)


class BoundaryUnverifiable(Exception):
    """The workspace's business data could not be screened. The gate refuses on this."""


def normalise(text):
    """Case-folded, punctuation-free, single-spaced. How values and fragments are compared."""
    return _NON_ALNUM.sub(" ", str(text).casefold()).strip()


def canonical_number(value):
    """A number as one canonical string ("1,240.00" and 1240.0 are both "1240"), or None."""
    if isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    return "{:f}".format(number.normalize())


def _distinctive_number(canonical):
    """Whether a number identifies anything. Years and small counts do not.

    A year-shaped integer is left alone because Tier 0 queries carry periods ("2026"), and a
    small integer because it collides with everything. Decimals always count: an exact
    amount is exactly what must not leave.
    """
    number = Decimal(canonical)
    if number != number.to_integral_value():
        return True
    number = abs(number)
    return number >= 100 and not (1900 <= number <= 2100)


class Provenance(object):
    """Where a registered value was found. Immutable."""

    __slots__ = ("sensitivity", "column", "source", "_frozen")

    def __init__(self, sensitivity, column, source):
        self.sensitivity = sensitivity
        self.column = column
        self.source = source
        self._frozen = True

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False):
            raise AttributeError("a value's provenance is fixed when it is registered")
        object.__setattr__(self, name, value)


class InternalValueRegister(object):
    """Every non-public value in the workspace's business data, with its provenance.

    Held in memory for one assessment and never persisted: writing the values somewhere to
    speed the next call would make a second copy of the data the boundary exists to protect.
    """

    __slots__ = ("_phrases", "_numbers", "sources", "_frozen")

    def __init__(self, phrases=None, numbers=None, sources=()):
        self._phrases = dict(phrases or {})
        self._numbers = dict(numbers or {})
        self.sources = tuple(sources)
        self._frozen = True

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False):
            raise AttributeError("the internal-value register cannot be changed once built")
        object.__setattr__(self, name, value)

    def __len__(self):
        return len(self._phrases) + len(self._numbers)

    def matches(self, text, numbers=True):
        """Provenance records for every registered value `text` carries, value-free.

        `numbers=False` skips the numeric table, for a descriptor's value: a band or a rate
        is what the governed aggregation produced, and its round edges ("100k") would
        otherwise collide with any row that happens to hold the same round number.
        """
        found = []
        tokens = normalise(text).split()
        for size in range(1, min(len(tokens), MAX_PHRASE_TOKENS) + 1):
            for start in range(0, len(tokens) - size + 1):
                hit = self._phrases.get(" ".join(tokens[start:start + size]))
                if hit is not None:
                    found.append(hit)
        whole = " ".join(tokens)
        if len(tokens) > MAX_PHRASE_TOKENS and whole in self._phrases:
            found.append(self._phrases[whole])
        for raw in (_NUMBER.findall(str(text)) if numbers else ()):
            canonical = canonical_number(raw)
            if canonical is not None and canonical in self._numbers:
                found.append(self._numbers[canonical])
        return found


def _register_value(phrases, numbers, value, provenance):
    def keep(table, key):
        current = table.get(key)
        if current is None or privacy_mod.rank(provenance.sensitivity) > privacy_mod.rank(
                current.sensitivity):
            table[key] = provenance

    if value is None or isinstance(value, bool):
        return
    if isinstance(value, (int, float, Decimal)):
        canonical = canonical_number(value)
        if canonical is not None and _distinctive_number(canonical):
            keep(numbers, canonical)
        return
    if not isinstance(value, str):
        return                              # dates and other typed values identify nothing
    canonical = canonical_number(value)
    if canonical is not None:
        if _distinctive_number(canonical):
            keep(numbers, canonical)
        return
    text = normalise(value)
    if len(text) >= MIN_VALUE_CHARS:
        keep(phrases, text)
    # An identifier's number travels without its prefix ("order 41011" for "SO-41011").
    for raw in _NUMBER.findall(value):
        embedded = canonical_number(raw)
        if embedded is not None and _distinctive_number(embedded):
            keep(numbers, embedded)


def register_dataset(dataset, phrases, numbers, source):
    """Add one dataset's non-public values, classified by the ingestion-time rules."""
    sensitivity_map = privacy_mod.classify_dataset(dataset)
    for column in dataset.columns:
        sensitivity = sensitivity_map.sensitivity_of(column)
        if sensitivity == privacy_mod.PUBLIC:
            continue
        provenance = Provenance(sensitivity, str(column), source)
        for value in dataset.column(column):
            _register_value(phrases, numbers, value, provenance)


def _inside(path, root):
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:                      # different drives on Windows
        return False


def discover(root):
    """The business data files under `root`, sorted. Raises `BoundaryUnverifiable`."""
    root = os.path.realpath(root)
    found, entries = [], 0
    for directory, subdirectories, files in os.walk(root):
        subdirectories[:] = sorted(
            d for d in subdirectories
            if not d.startswith(".") and d not in SKIPPED_DIRECTORIES
            and not _inside(os.path.realpath(os.path.join(directory, d)), PLUGIN_ROOT))
        entries += len(subdirectories) + len(files)
        if entries > MAX_ENTRIES:
            raise BoundaryUnverifiable(
                "the working directory holds more than %d entries, too many to screen for "
                "business data. Run BusinessOps from the folder that holds the business "
                "files." % MAX_ENTRIES)
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() in DATA_EXTENSIONS:
                path = os.path.realpath(os.path.join(directory, name))
                if not _inside(path, PLUGIN_ROOT):
                    found.append(path)
    if len(found) > MAX_FILES:
        raise BoundaryUnverifiable(
            "the working directory holds %d business data files, more than the %d the "
            "boundary screens." % (len(found), MAX_FILES))
    return found


def _read_all(path):
    """Every sheet of a workbook, or the one table of a delimited file."""
    if os.path.getsize(path) > MAX_FILE_BYTES:
        raise BoundaryUnverifiable("a business data file is larger than %d MB"
                                   % (MAX_FILE_BYTES // (1024 * 1024)))
    if os.path.splitext(path)[1].lower() in (".csv", ".tsv"):
        return [readers.read_csv(path)]
    first = readers.read_xlsx_stdlib(path)
    datasets = [first]
    for sheet in first.sheets:
        if sheet != first.sheet:
            datasets.append(readers.read_xlsx_stdlib(path, sheet_name=sheet))
    return datasets


def build_register(root):
    """The register for every business data file under `root`. Raises `BoundaryUnverifiable`."""
    root = os.path.realpath(root)
    if _inside(root, PLUGIN_ROOT):
        return InternalValueRegister()
    phrases, numbers, sources = {}, {}, []
    for path in discover(root):
        source = os.path.relpath(path, root)
        try:
            datasets = _read_all(path)
        except BoundaryUnverifiable:
            raise
        except Exception as error:          # any unreadable file: cannot vouch for it
            raise BoundaryUnverifiable(
                "the business data file %s could not be read (%s), so its values cannot "
                "be kept out of external research" % (source, type(error).__name__))
        for dataset in datasets:
            register_dataset(dataset, phrases, numbers, source)
        sources.append(source)
    return InternalValueRegister(phrases, numbers, sources)


def workspace_register():
    """The register the gate uses: the working directory's business data. No arguments.

    Deliberately parameterless. A caller that could name the root could name an empty one.
    """
    return build_register(os.getcwd())


# -- screening ---------------------------------------------------------------

class Finding(object):
    """One request field that carries internal material. Value-free by construction."""

    __slots__ = ("field", "kind", "sensitivity", "column", "source", "term_key")

    def __init__(self, field, kind, sensitivity, column=None, source=None, term_key=None):
        self.field = field
        #: The public-term key this finding belongs to, for building the alternative. Never
        #: rendered: a key can itself be the internal value.
        self.term_key = term_key
        self.kind = kind
        self.sensitivity = sensitivity
        self.column = column
        self.source = source

    @property
    def in_query_text(self):
        """Whether this field becomes part of the query text a Tier 2 approval shows."""
        return (self.field == "subject" or self.field.startswith("derived context ")
                or (self.term_key is not None and not self.field.startswith("the name of")))

    def describe(self):
        if self.kind == UNATTRIBUTED_FIGURE:
            return ("%s carries an exact figure, which no public term can carry"
                    % self.field)
        return ("%s carries a value from the %r column of %s, classified %s"
                % (self.field, self.column, self.source,
                   privacy_mod.HUMAN_LABEL.get(self.sensitivity, self.sensitivity)))

    def as_dict(self):
        record = {"field": self.field, "kind": self.kind, "sensitivity": self.sensitivity,
                  "column": self.column, "source": self.source}
        return {k: v for k, v in record.items() if v is not None}


_PLAIN_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,39}")


def _term_label(key, register):
    """How a public term is named in a finding: by its key, unless the key is itself suspect."""
    key = str(key)
    if _PLAIN_KEY.fullmatch(key) and not register.matches(key):
        return "public term %r" % key
    return "a public term"


def _fragments(request, register):
    """Every caller-supplied text in the request, with its field name and figure rule.

    Returns (field, text, figures_checked, numbers_checked, term_key). Figures are checked where a Tier 0 term lives -
    the subject, the public terms and a descriptor's label - and not in a descriptor's
    value, which is a band or rate the Tier 1 checks judge, nor in identifiers.
    """
    fragments = [("subject", request.subject, True, True)]
    terms = []
    for key, value in sorted((request.public_terms or {}).items(), key=lambda kv: str(kv[0])):
        label = _term_label(key, register)
        terms.append(("the name of " + label, key, False, True, key))
        figures = not str(key).lower().endswith("_band")
        for item in (value if isinstance(value, (list, tuple, set)) else [value]):
            terms.append((label, item, figures, True, key))
    for index, descriptor in enumerate(request.derived_context):
        fragments.append(("derived context %d label" % index,
                          getattr(descriptor, "label", None), True, True))
        fragments.append(("derived context %d value" % index,
                          getattr(descriptor, "value", None), False, False))
    fragments.append(("operation", request.operation, False, True))
    fragments.append(("purpose", request.purpose, False, True))
    for index, note in enumerate(request.notes or ()):
        fragments.append(("note %d" % index, note, False, True))
    if request.source_requirements is not None:
        fragments.append(("source requirements", request.source_requirements, False, True))
    destination = request.destination
    if destination is not None:
        fragments.append(("destination", getattr(destination, "provider", None), False, True))
        fragments.append(("destination description",
                          getattr(destination, "description", None), False, True))
    fragments = [f + (None,) for f in fragments]
    fragments[1:1] = terms
    return [f for f in fragments if f[1] not in (None, "")]


def screen(request, register):
    """Every finding for this request against this register. Empty means nothing internal."""
    findings = []
    for field, text, figures, numbers, term_key in _fragments(request, register):
        text = text if isinstance(text, str) else str(text)
        seen = set()
        for provenance in register.matches(text, numbers=numbers):
            key = (provenance.column, provenance.source, provenance.sensitivity)
            if key not in seen:
                seen.add(key)
                findings.append(Finding(field, INTERNAL_VALUE, provenance.sensitivity,
                                        provenance.column, provenance.source, term_key))
        if figures and any(p.search(text) for p in _FIGURE_PATTERNS):
            findings.append(Finding(field, UNATTRIBUTED_FIGURE, privacy_mod.DERIVED_SAFE,
                                    term_key=term_key))
    return findings


def text_is_clean(text, register):
    """Whether a proposed query text carries nothing internal. Used to vet alternatives."""
    return not register.matches(text) and not any(p.search(text) for p in _FIGURE_PATTERNS)


def strictest(findings):
    return privacy_mod.most_sensitive([f.sensitivity for f in findings])
