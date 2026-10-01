"""Turning a source's published magnitude notation into a canonical quantity (ADR-0025).

A published figure arrives as notation - "USD 282.80 billion", "$3,400 million" - and a
canonical quantity is three separate facts: a quantity type, a currency code, and a value in
base units. This module performs that decomposition, once, at the point a statement is
constructed, and nowhere else.

**This is not conversion.** `USD 3.4 billion` and `USD 3,400,000,000` are one quantity in two
notations: the operation is decimal-exact, needs no external data, no rate and no reference
date, and is reversible. `GBP 3.4 billion` and `USD 3.4 billion` are two quantities, and
relating them needs an exchange rate this codebase does not hold and will not acquire. The
first is a change of notation; the second is a change of meaning. Nothing here converts a
currency, and there is no rate table, no lookup and no hook for one.

**Nothing here runs inside `synthesis.compatibility.compare()`**, and that is the whole
placement argument. `compare()` reports *which* dimension failed and why, and that report is
the audit artefact; a module that reconciled its inputs before testing them could not also be
the record of what did not reconcile. Canonicalisation happens first, `compare()` then sees
canonical quantities on both sides and needs no change at all.

Scale words are a **closed** set. An unrecognised one is refused rather than guessed at,
because guessing is how a factor of a thousand enters a report.
"""

from decimal import Decimal, InvalidOperation

from .errors import BusinessOpsError
from .kpi import contract as kpi_contract


class QuantityError(BusinessOpsError):
    """A magnitude could not be canonicalised safely, so no value was produced."""


#: Scale words and their exact decimal factors. Spelled out rather than computed so the
#: table is the specification: a reader checks six entries, not an exponent expression.
SCALES = {
    "unit": Decimal(1),
    "thousand": Decimal(10) ** 3,
    "million": Decimal(10) ** 6,
    "billion": Decimal(10) ** 9,
    "trillion": Decimal(10) ** 12,
}

#: Aliases a source may actually publish. Deliberately short: `bn`, `m` and `k` are the
#: forms that appear in financial copy. Ambiguous forms are **absent on purpose** - `b` is
#: not here because it reads as billion in one market and is a bare token in another, and
#: `mm` is not here because it means million in US banking and nothing elsewhere. An absent
#: alias refuses; a wrong alias silently misstates a figure by three orders of magnitude.
SCALE_ALIASES = {
    "k": "thousand", "thousands": "thousand",
    "m": "million", "mn": "million", "millions": "million",
    "bn": "billion", "billions": "billion",
    "tn": "trillion", "trillions": "trillion",
    "": "unit", "units": "unit", "ones": "unit",
}

#: Currency codes this module will accept from source notation. Three uppercase letters is
#: the ISO 4217 shape; the check is structural, because a closed list of world currencies
#: is a maintenance burden that buys nothing here - the currency is carried verbatim and is
#: never used to convert anything.
_CURRENCY_LENGTH = 3


def scale_factor(word):
    """The exact `Decimal` factor for one scale word. Refuses anything unrecognised."""
    if word is None:
        return SCALES["unit"]
    if not isinstance(word, str):
        raise QuantityError("a scale is a word, not %s" % type(word).__name__)
    key = " ".join(word.split()).strip().lower()
    key = SCALE_ALIASES.get(key, key)
    if key not in SCALES:
        raise QuantityError(
            "%r is not a recognised scale. Accepted: %s (and the documented aliases). An "
            "unrecognised scale is refused rather than guessed at, because a guess here "
            "misstates a figure by orders of magnitude."
            % (word, ", ".join(sorted(SCALES))))
    return SCALES[key]


def _as_decimal(value):
    """Accept a `Decimal`, an int, or a string of digits. Never a float."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):                       # bool is an int; refuse it explicitly
        raise QuantityError("a boolean is not a magnitude")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        raise QuantityError(
            "a float cannot carry a monetary magnitude without drift; pass a Decimal, an "
            "int, or the source's digits as a string")
    if isinstance(value, str):
        text = value.strip().replace(",", "").replace(" ", "")
        if not text:
            raise QuantityError("an empty string is not a magnitude")
        try:
            return Decimal(text)
        except InvalidOperation:
            raise QuantityError("%r is not a number this module will read" % (value,))
    raise QuantityError("%s is not a magnitude" % type(value).__name__)


def parse_source_unit(text):
    """Split a source's unit notation into `(quantity_type, currency, scale_factor)`.

    Reads the forms a published figure actually uses - `"USD billion"`, `"EUR million"`,
    `"USD"`, `"billion"` - and refuses everything else. A currency is recognised only from
    an explicit three-letter code: a bare `"$"` establishes nothing (it is used by at least
    four currencies), so it yields `currency=None`, which leaves the currency dimension
    unstated and therefore rejecting. Not guessing is the point.
    """
    if text is None:
        raise QuantityError("no unit notation was supplied")
    if not isinstance(text, str):
        raise QuantityError("unit notation is text, not %s" % type(text).__name__)

    tokens = [t for t in " ".join(text.split()).strip().split(" ") if t]
    if not tokens:
        raise QuantityError("empty unit notation")

    # A bare canonical quantity type is already canonical; say so rather than re-deriving.
    if len(tokens) == 1 and kpi_contract.is_quantity_type(tokens[0].lower()):
        return tokens[0].lower(), None, SCALES["unit"]

    currency, scale_words = None, []
    for token in tokens:
        stripped = token.strip(".")
        if (currency is None and len(stripped) == _CURRENCY_LENGTH
                and stripped.isalpha() and stripped.isupper()):
            currency = stripped
            continue
        scale_words.append(stripped)

    if len(scale_words) > 1:
        raise QuantityError(
            "%r carries more than one scale word, which is ambiguous and is refused"
            % (text,))

    factor = scale_factor(scale_words[0] if scale_words else None)

    if currency is None and not scale_words:
        raise QuantityError(
            "%r states neither a currency code nor a scale, so no quantity type can be "
            "established from it" % (text,))

    # A currency code, or a scale applied to money, both describe a monetary quantity.
    return kpi_contract.CURRENCY, currency, factor


def canonical_amount(value, unit_text=None, scale=None, currency=None):
    """Canonicalise one published figure. Returns `(Decimal, quantity_type, currency)`.

    Give it either the source's unit notation (`unit_text="USD billion"`) or an explicit
    `scale`/`currency` pair, never both. The returned value is in **base units** - whole
    currency units, not thousands and not billions - and the caller stores exactly that.

    Refuses rather than repairs. A malformed magnitude, an unrecognised scale or two scale
    words in one notation all raise, because a statement built on a magnitude nobody could
    read is worse than no statement.
    """
    if unit_text is not None and (scale is not None or currency is not None):
        raise QuantityError(
            "supply either the source's unit notation or an explicit scale/currency, not "
            "both; two descriptions of one magnitude can disagree")

    if unit_text is not None:
        quantity_type, parsed_currency, factor = parse_source_unit(unit_text)
    else:
        quantity_type = kpi_contract.CURRENCY
        parsed_currency = currency
        factor = scale_factor(scale)
        if parsed_currency is not None:
            if not isinstance(parsed_currency, str) or \
                    len(parsed_currency) != _CURRENCY_LENGTH or \
                    not parsed_currency.isalpha() or not parsed_currency.isupper():
                raise QuantityError(
                    "%r is not an ISO-style three-letter currency code. A currency is "
                    "recorded only when the source states one; it is never inferred."
                    % (parsed_currency,))

    amount = _as_decimal(value) * factor

    # `Decimal("3.4") * Decimal(10) ** 9` is exactly 3400000000 but carries the exponent
    # `3400000000.0`, and two paths reaching the same quantity by different scales would
    # then serialise to different strings. Tidying an integral result to its integral form
    # is not rounding - the value is unchanged, and a non-integral amount is left alone.
    if amount == amount.to_integral_value():
        amount = amount.quantize(Decimal(1))

    return amount, quantity_type, parsed_currency
