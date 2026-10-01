"""Type, date and currency normalization.

Normalization produces a **derived representation**. It never modifies the source file and
never writes back — the original bytes on disk are untouched by every path here.

The governing rule is the ambiguity protocol's: **never silently reinterpret an ambiguous
value.** `1,234` is unambiguous. `1.234` is not — it is 1234 under a European convention and
1.234 under an Anglo one, and guessing wrong changes a figure by a factor of a thousand. So
ambiguous values are returned unchanged, flagged, and escalated for confirmation.

Money uses `Decimal` throughout. Binary floating point is never used on a path that produces
a reported figure.
"""

import datetime
import re
from decimal import Decimal, InvalidOperation

# Value kinds the normalizer can produce.
TEXT = "text"
INTEGER = "integer"
DECIMAL = "decimal"
PERCENT = "percent"
CURRENCY = "currency"
DATE = "date"
DATETIME = "datetime"
BOOLEAN = "boolean"
EMPTY = "empty"
AMBIGUOUS = "ambiguous"

CURRENCY_SYMBOLS = {
    "$": "USD", "£": "GBP", "€": "EUR", "¥": "JPY", "₹": "INR",
    "₩": "KRW", "₽": "RUB", "₪": "ILS", "฿": "THB",
}
SYMBOL_FOR_CODE = {code: symbol for symbol, code in CURRENCY_SYMBOLS.items()}

ISO_CODE = re.compile(r"\b([A-Z]{3})\b")

_TRUE = {"true", "yes", "y", "1", "t"}
_FALSE = {"false", "no", "n", "0", "f"}

_MISSING = {"", "-", "--", "n/a", "na", "nil", "null", "none", "#n/a", "#null!", "."}


class NormalizedValue:
    """One value after normalization, with its original preserved.

    The original is kept because an ambiguous value must be presentable back to the user
    exactly as they wrote it when asking for confirmation.
    """

    __slots__ = ("value", "kind", "original", "currency", "warning", "confirm_required")

    def __init__(self, value, kind, original, currency=None, warning=None,
                 confirm_required=False):
        self.value = value
        self.kind = kind
        self.original = original
        self.currency = currency
        self.warning = warning
        self.confirm_required = confirm_required

    @property
    def is_missing(self):
        return self.kind == EMPTY

    @property
    def is_ambiguous(self):
        return self.kind == AMBIGUOUS

    def as_dict(self):
        return {"value": (str(self.value) if isinstance(self.value, Decimal)
                          else self.value),
                "kind": self.kind, "original": self.original, "currency": self.currency,
                "warning": self.warning, "confirm_required": self.confirm_required}

    def __repr__(self):
        return "NormalizedValue(%r, %s)" % (self.value, self.kind)

    def __eq__(self, other):
        return (isinstance(other, NormalizedValue)
                and (self.value, self.kind, self.currency)
                == (other.value, other.kind, other.currency))


def _missing(original):
    return NormalizedValue(None, EMPTY, original)


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

def _strip_currency(text):
    """Remove a currency symbol or ISO code; return (remaining text, currency code)."""
    currency = None
    for symbol, code in CURRENCY_SYMBOLS.items():
        if symbol in text:
            currency = code
            text = text.replace(symbol, "")
            break
    if currency is None:
        match = ISO_CODE.search(text.upper())
        if match and match.group(1) in SYMBOL_FOR_CODE:
            currency = match.group(1)
            text = re.sub(r"\b%s\b" % currency, "", text, flags=re.I)
    return text.strip(), currency


def _separator_reading(text):
    """Decide how ',' and '.' are being used. Returns (cleaned, ambiguity reason or None).

    The one genuinely undecidable case is a single separator with exactly three digits
    after it and no other evidence: `1.234` and `1,234`. Those are reported, never guessed.
    """
    has_comma, has_dot = "," in text, "." in text

    if has_comma and has_dot:
        # The rightmost separator is the decimal point; the other groups thousands.
        if text.rfind(",") > text.rfind("."):
            return text.replace(".", "").replace(",", "."), None
        return text.replace(",", ""), None

    if has_comma:
        parts = text.split(",")
        if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]):
            return text.replace(",", ""), None            # 1,234,567
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            return None, ("%r could be 1,234 (thousands) or a decimal comma; the "
                          "convention cannot be determined from this value alone" % text)
        if len(parts) == 2:
            return text.replace(",", "."), None           # 12,5 -> decimal comma
        return text.replace(",", ""), None

    if has_dot:
        parts = text.split(".")
        if len(parts) > 2 and all(len(p) == 3 for p in parts[1:]):
            return text.replace(".", ""), None            # 1.234.567
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            return None, ("%r could be 1.234 (a decimal) or 1234 (European thousands "
                          "separator); the convention cannot be determined from this "
                          "value alone" % text)
        return text, None

    return text, None


def normalize_number(raw, assume_separator=None):
    """Normalize a numeric value. Ambiguity is reported, never resolved by guessing.

    `assume_separator` ('anglo' or 'european') resolves the ambiguous case when the caller
    has independent evidence — from a confirmed column convention, say.
    """
    original = raw
    if raw is None:
        return _missing(original)
    if isinstance(raw, bool):
        return NormalizedValue(raw, BOOLEAN, original)
    if isinstance(raw, Decimal):
        return NormalizedValue(raw, DECIMAL, original)
    if isinstance(raw, int):
        return NormalizedValue(raw, INTEGER, original)
    if isinstance(raw, float):
        return NormalizedValue(Decimal(str(raw)), DECIMAL, original)

    text = str(raw).strip()
    if text.lower() in _MISSING:
        return _missing(original)

    is_percent = text.endswith("%")
    if is_percent:
        text = text[:-1].strip()

    # Accounting negatives: (1,234) means -1234.
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative, text = True, text[1:-1].strip()

    text, currency = _strip_currency(text)
    text = text.replace(" ", "").replace(" ", "")
    if text.startswith("-"):
        negative, text = True, text[1:]
    elif text.startswith("+"):
        text = text[1:]

    if not text:
        return _missing(original)
    if not re.fullmatch(r"[\d.,]+", text):
        return NormalizedValue(raw, TEXT, original)

    cleaned, ambiguity = _separator_reading(text)
    if ambiguity is not None:
        if assume_separator == "anglo":
            cleaned = text.replace(",", "")
        elif assume_separator == "european":
            cleaned = text.replace(".", "").replace(",", ".")
        else:
            return NormalizedValue(raw, AMBIGUOUS, original, warning=ambiguity,
                                   confirm_required=True)

    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return NormalizedValue(raw, TEXT, original)

    if negative:
        value = -value

    if is_percent:
        return NormalizedValue(value, PERCENT, original)
    if currency:
        return NormalizedValue(value, CURRENCY, original, currency=currency)
    if value == value.to_integral_value() and "." not in cleaned:
        return NormalizedValue(int(value), INTEGER, original)
    return NormalizedValue(value, DECIMAL, original)


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

_UNAMBIGUOUS_FORMATS = (
    ("%Y-%m-%d", DATE),
    ("%Y/%m/%d", DATE),
    ("%d %b %Y", DATE),
    ("%d %B %Y", DATE),
    ("%b %d, %Y", DATE),
    ("%B %d, %Y", DATE),
    ("%d-%b-%Y", DATE),
    ("%Y-%m-%dT%H:%M:%S", DATETIME),
    ("%Y-%m-%d %H:%M:%S", DATETIME),
    ("%Y-%m-%d %H:%M", DATETIME),
)

_SLASHED = re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})$")


def normalize_date(raw, day_first=None):
    """Normalize a date. `03/04/2025` is genuinely ambiguous and is reported, not guessed.

    `day_first` resolves it when the caller has evidence — a confirmed locale, or another
    value in the same column where the day exceeds 12.
    """
    original = raw
    if raw is None:
        return _missing(original)
    if isinstance(raw, datetime.datetime):
        if raw.time() == datetime.time():
            return NormalizedValue(raw.date(), DATE, original)
        return NormalizedValue(raw, DATETIME, original)
    if isinstance(raw, datetime.date):
        return NormalizedValue(raw, DATE, original)

    text = str(raw).strip()
    if text.lower() in _MISSING:
        return _missing(original)

    for fmt, kind in _UNAMBIGUOUS_FORMATS:
        try:
            parsed = datetime.datetime.strptime(text, fmt)
            return NormalizedValue(parsed.date() if kind == DATE else parsed, kind, original)
        except ValueError:
            continue

    match = _SLASHED.match(text)
    if match:
        first, second, year = (int(match.group(1)), int(match.group(2)),
                               int(match.group(3)))
        if year < 100:
            year += 2000 if year < 70 else 1900
        # One of the two exceeds 12, so the order is decidable.
        if first > 12 and second <= 12:
            return _build_date(year, second, first, original)
        if second > 12 and first <= 12:
            return _build_date(year, first, second, original)
        if first <= 12 and second <= 12:
            if day_first is True:
                return _build_date(year, second, first, original)
            if day_first is False:
                return _build_date(year, first, second, original)
            return NormalizedValue(
                raw, AMBIGUOUS, original, confirm_required=True,
                warning="%r could be %d %s or %s %d — day/month order cannot be "
                        "determined from this value alone."
                        % (text, first, _month_name(second), _month_name(first), second))
        return NormalizedValue(raw, TEXT, original,
                               warning="%r is not a valid date" % text)

    return NormalizedValue(raw, TEXT, original)


def _month_name(number):
    try:
        return datetime.date(2000, number, 1).strftime("%B")
    except ValueError:
        return str(number)


def _build_date(year, month, day, original):
    try:
        return NormalizedValue(datetime.date(year, month, day), DATE, original)
    except ValueError:
        return NormalizedValue(original, TEXT, original,
                               warning="%r is not a valid calendar date" % (original,))


def infer_day_first(values):
    """Infer day/month order for a whole column from a value where day > 12.

    Column-level evidence resolves what a single value cannot — but only when a value
    actually decides it. Returns None when the column stays ambiguous.
    """
    for value in values:
        if not isinstance(value, str):
            continue
        match = _SLASHED.match(value.strip())
        if not match:
            continue
        first, second = int(match.group(1)), int(match.group(2))
        if first > 12 and second <= 12:
            return True
        if second > 12 and first <= 12:
            return False
    return None


# ---------------------------------------------------------------------------
# Booleans and general dispatch
# ---------------------------------------------------------------------------

def normalize_boolean(raw):
    original = raw
    if raw is None:
        return _missing(original)
    if isinstance(raw, bool):
        return NormalizedValue(raw, BOOLEAN, original)
    text = str(raw).strip().lower()
    if text in _MISSING:
        return _missing(original)
    if text in _TRUE:
        return NormalizedValue(True, BOOLEAN, original)
    if text in _FALSE:
        return NormalizedValue(False, BOOLEAN, original)
    return NormalizedValue(raw, TEXT, original)


def normalize_text(raw):
    original = raw
    if raw is None:
        return _missing(original)
    text = str(raw).strip()
    if text.lower() in _MISSING:
        return _missing(original)
    return NormalizedValue(re.sub(r"\s+", " ", text), TEXT, original)


def normalize_value(raw, expect=None, day_first=None, assume_separator=None):
    """Normalize one value, optionally with an expected kind from the column profile."""
    if expect in (DATE, DATETIME):
        return normalize_date(raw, day_first)
    if expect in (INTEGER, DECIMAL, CURRENCY, PERCENT):
        return normalize_number(raw, assume_separator)
    if expect == BOOLEAN:
        return normalize_boolean(raw)
    if expect == TEXT:
        return normalize_text(raw)

    if raw is None:
        return _missing(raw)
    if isinstance(raw, (datetime.date, datetime.datetime)):
        return normalize_date(raw)
    if isinstance(raw, bool):
        return NormalizedValue(raw, BOOLEAN, raw)
    if isinstance(raw, (int, float, Decimal)):
        return normalize_number(raw)

    text = str(raw).strip()
    if text.lower() in _MISSING:
        return _missing(raw)
    as_date = normalize_date(raw, day_first)
    if as_date.kind in (DATE, DATETIME, AMBIGUOUS):
        return as_date
    as_number = normalize_number(raw, assume_separator)
    if as_number.kind in (INTEGER, DECIMAL, CURRENCY, PERCENT, AMBIGUOUS):
        return as_number
    as_bool = normalize_boolean(raw)
    if as_bool.kind == BOOLEAN:
        return as_bool
    return normalize_text(raw)


# ---------------------------------------------------------------------------
# Column-level profiling
# ---------------------------------------------------------------------------

class ColumnProfile:
    """What a column contains, decided from the column as a whole."""

    __slots__ = ("column", "kind", "currencies", "missing_count", "total_count",
                 "ambiguous_count", "day_first", "warnings", "kind_counts")

    def __init__(self, column, kind, currencies, missing_count, total_count,
                 ambiguous_count, day_first, warnings, kind_counts):
        self.column = column
        self.kind = kind
        self.currencies = sorted(currencies)
        self.missing_count = missing_count
        self.total_count = total_count
        self.ambiguous_count = ambiguous_count
        self.day_first = day_first
        self.warnings = list(warnings)
        self.kind_counts = dict(kind_counts)

    @property
    def missing_pct(self):
        return (self.missing_count / float(self.total_count) * 100.0
                if self.total_count else 0.0)

    @property
    def is_mixed(self):
        substantive = {k: n for k, n in self.kind_counts.items()
                       if k not in (EMPTY, AMBIGUOUS)}
        return len(substantive) > 1

    @property
    def has_mixed_currency(self):
        return len(self.currencies) > 1

    def as_dict(self):
        return {"column": self.column, "kind": self.kind, "currencies": self.currencies,
                "missing": self.missing_count, "total": self.total_count,
                "ambiguous": self.ambiguous_count, "day_first": self.day_first,
                "mixed_types": self.is_mixed, "warnings": self.warnings,
                "kind_counts": self.kind_counts}

    def __repr__(self):
        return "ColumnProfile(%s: %s)" % (self.column, self.kind)


def profile_column(column, values, sample=1000):
    """Profile a column, resolving day/month order from column-wide evidence first."""
    raw_values = list(values)
    day_first = infer_day_first(raw_values[:sample])

    counts, currencies, warnings = {}, set(), []
    missing = ambiguous = 0

    for raw in raw_values[:sample]:
        normalized = normalize_value(raw, day_first=day_first)
        counts[normalized.kind] = counts.get(normalized.kind, 0) + 1
        if normalized.kind == EMPTY:
            missing += 1
        elif normalized.kind == AMBIGUOUS:
            ambiguous += 1
            if normalized.warning and normalized.warning not in warnings:
                warnings.append(normalized.warning)
        if normalized.currency:
            currencies.add(normalized.currency)

    substantive = {k: n for k, n in counts.items() if k not in (EMPTY, AMBIGUOUS)}
    kind = max(substantive, key=substantive.get) if substantive else EMPTY

    # Integers and decimals in one column are a decimal column, not a mixed one.
    if set(substantive) == {INTEGER, DECIMAL}:
        kind = DECIMAL
        substantive = {DECIMAL: sum(substantive.values())}
        counts = dict(counts)
        counts[DECIMAL] = substantive[DECIMAL]
        counts.pop(INTEGER, None)

    if len(currencies) > 1:
        warnings.append(
            "Column mixes %d currencies (%s). Values in different currencies must not be "
            "summed; no conversion is applied." % (len(currencies), ", ".join(sorted(currencies))))

    # Count the remaining missing/ambiguous across the whole column, not just the sample.
    if len(raw_values) > sample:
        for raw in raw_values[sample:]:
            if raw is None or (isinstance(raw, str) and raw.strip().lower() in _MISSING):
                missing += 1

    return ColumnProfile(column, kind, currencies, missing, len(raw_values),
                         ambiguous, day_first, warnings, counts)
