"""Field-level sensitivity classification (ADR-0009).

Every column of every ingested dataset gets a sensitivity class, deterministically and with
a recorded reason, so the decision is auditable after the fact.

Two independent signals are used, and **the stricter one always wins**:

  * the column *name* — `email`, `customer`, `api_key`
  * the column *content* — values that look like email addresses, phone numbers, card
    numbers or tokens, whatever the header claims

Content matters because a column called `Notes` full of email addresses is exactly the case
a name-only classifier would leak. Sampling is capped, and a single confirmed hit in the
sample is enough: a rule that needed a majority would let one credential through.

Unclassified columns default to `internal`, never `public`.
"""

import re

from .classes import (
    DEFAULT_CLASS, DERIVED_SAFE, INTERNAL, NEVER, PUBLIC, RESTRICTED,
    most_sensitive, rank,
)

SAMPLE_SIZE = 200

# ---------------------------------------------------------------------------
# Name evidence. Ordered most-sensitive first: the first match wins.
# ---------------------------------------------------------------------------

_NAME_RULES = (
    # Credentials — never, no approval path.
    (NEVER, r"(api[_\s-]?key|secret|password|passwd|token|credential|private[_\s-]?key"
            r"|access[_\s-]?key|auth|bearer)",
     "column name indicates a credential"),
    # Direct personal identifiers — ADR-0009 Tier 3.
    (NEVER, r"(e[-_\s]?mail|phone|mobile|telephone|fax|address|postcode|post[_\s-]?code"
            r"|zip[_\s-]?code|national[_\s-]?insurance|ssn|passport|date[_\s-]?of[_\s-]?birth"
            r"|dob|ip[_\s-]?address)",
     "column name indicates personally identifying information"),
    # Payment instruments.
    (NEVER, r"(card[_\s-]?number|iban|sort[_\s-]?code|account[_\s-]?number|bank[_\s-]?account"
            r"|cvv|pan)",
     "column name indicates payment or bank details"),
    # Customer-level identity — Tier 3 under ADR-0009.
    (NEVER, r"(customer|client|buyer|contact|account[_\s-]?name|company[_\s-]?name"
            r"|first[_\s-]?name|last[_\s-]?name|surname|full[_\s-]?name)",
     "column name identifies an individual customer or contact"),
    # Individual people inside the business.
    (RESTRICTED, r"(salesperson|sales[_\s-]?rep|employee|staff|owner|manager|rep[_\s-]?name"
                 r"|user[_\s-]?name|username)",
     "column name identifies an individual person"),
    # Transaction-level identifiers — a row-level record, not an aggregate.
    (RESTRICTED, r"(order[_\s-]?id|invoice|transaction[_\s-]?id|receipt|reference"
                 r"|order[_\s-]?no|order[_\s-]?number)",
     "column name identifies an individual transaction"),
    # Monetary and margin detail at row level — aggregatable, never exact externally.
    (DERIVED_SAFE, r"(revenue|sales|amount|price|cost|margin|profit|value|turnover|spend"
                   r"|discount|quantity|qty|units|volume)",
     "monetary or volume measure — safe only as an aggregate"),
    # Non-identifying business dimensions.
    (PUBLIC, r"(region|territory|country|market|category|segment|product[_\s-]?category"
             r"|channel|currency|period|month|quarter|year|date)",
     "non-identifying business dimension"),
    # Product/service names sit between: not personal, but they can identify a business.
    (INTERNAL, r"(product|item|sku|service|description|notes?|comment)",
     "business detail that may identify the business"),
)

# ---------------------------------------------------------------------------
# Content evidence. Any confirmed hit escalates, regardless of the header.
# ---------------------------------------------------------------------------

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
# Requires at least 9 digits overall, so an ISO date (8 digits) cannot match.
_PHONE = re.compile(r"^\+?[\d][\d\s().-]{7,}$")
_DATE_LIKE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$|^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$")
_IBAN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$")
_CARD = re.compile(r"^(?:\d[ -]?){13,19}$")
_TOKEN = re.compile(r"^(sk|pk|ghp|xox[baprs]|AKIA|ya29|eyJ)[A-Za-z0-9_\-.]{12,}$")
_UK_POSTCODE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", re.I)

_CONTENT_RULES = (
    (NEVER, _TOKEN, "values look like access tokens or API keys"),
    (NEVER, _EMAIL, "values look like email addresses"),
    (NEVER, _IBAN, "values look like bank account identifiers"),
    (NEVER, _CARD, "values look like payment card numbers"),
    (NEVER, _PHONE, "values look like telephone numbers"),
    (NEVER, _UK_POSTCODE, "values look like postcodes"),
)


def _normalise(name):
    return re.sub(r"[^a-z0-9]+", "_", str(name or "").strip().lower()).strip("_")


def classify_name(column):
    """Classify from the header alone. Returns (class, reason) or (None, None)."""
    normalised = _normalise(column)
    for sensitivity, pattern, reason in _NAME_RULES:
        if re.search(pattern, normalised):
            return sensitivity, reason
    return None, None


def classify_content(values):
    """Classify from the values alone. Returns (class, reason) or (None, None).

    A single confirmed match escalates: requiring a majority would let one leaked
    credential through in a column of otherwise ordinary text.
    """
    sample = [v.strip() for v in list(values)[:SAMPLE_SIZE]
              if isinstance(v, str) and v.strip()]
    # Dates and plain numbers are not personal data, and they collide with the phone
    # pattern. Excluding them keeps date and period columns publicly usable, which Tier 0
    # research depends on.
    sample = [v for v in sample if not _DATE_LIKE.match(v) and not _is_plain_number(v)]
    if not sample:
        return None, None
    for sensitivity, pattern, reason in _CONTENT_RULES:
        hits = sum(1 for value in sample if pattern.match(value))
        if hits:
            if pattern is _PHONE and not _has_enough_digits(
                    [v for v in sample if pattern.match(v)]):
                continue
            return sensitivity, "%s (%d of %d sampled values)" % (reason, hits, len(sample))
    return None, None


def _is_plain_number(text):
    return bool(re.fullmatch(r"[-+]?[\d,. ]+", text)) and not re.search(r"[-/]\d{2,4}$", text)


def _has_enough_digits(values, minimum=9):
    """A real phone number carries at least nine digits."""
    return any(sum(ch.isdigit() for ch in v) >= minimum for v in values)


class FieldSensitivity:
    """One column's classification, with the evidence that produced it."""

    __slots__ = ("column", "sensitivity", "reasons", "name_class", "content_class")

    def __init__(self, column, sensitivity, reasons, name_class=None, content_class=None):
        self.column = column
        self.sensitivity = sensitivity
        self.reasons = list(reasons)
        self.name_class = name_class
        self.content_class = content_class

    @property
    def externalizable(self):
        from .classes import is_externalizable
        return is_externalizable(self.sensitivity)

    @property
    def max_tier(self):
        from .classes import max_tier
        return max_tier(self.sensitivity)

    def as_dict(self):
        return {"column": self.column, "sensitivity": self.sensitivity,
                "max_disclosure_tier": self.max_tier,
                "externalizable": self.externalizable,
                "reasons": self.reasons,
                "name_evidence": self.name_class,
                "content_evidence": self.content_class}

    def __repr__(self):
        return "FieldSensitivity(%s=%s)" % (self.column, self.sensitivity)


def classify_field(column, values=()):
    """Classify one column from both name and content. The stricter signal wins."""
    name_class, name_reason = classify_name(column)
    content_class, content_reason = classify_content(values)

    candidates = [c for c in (name_class, content_class) if c]
    sensitivity = most_sensitive(candidates) if candidates else DEFAULT_CLASS

    reasons = []
    if name_reason:
        reasons.append("name: %s" % name_reason)
    if content_reason:
        reasons.append("content: %s" % content_reason)
    if not reasons:
        reasons.append("no rule matched; defaulted to %s (never public)" % DEFAULT_CLASS)
    elif content_class and name_class and rank(content_class) > rank(name_class):
        reasons.append("content evidence overrode the weaker name evidence")

    return FieldSensitivity(column, sensitivity, reasons, name_class, content_class)


class SensitivityMap:
    """Every column's classification for one dataset."""

    def __init__(self, fields):
        self.fields = {f.column: f for f in fields}

    def of(self, column):
        return self.fields.get(column)

    def sensitivity_of(self, column):
        field = self.fields.get(column)
        return field.sensitivity if field else DEFAULT_CLASS

    def columns_at(self, sensitivity):
        return sorted(c for c, f in self.fields.items() if f.sensitivity == sensitivity)

    def externalizable_columns(self):
        return sorted(c for c, f in self.fields.items() if f.sensitivity == PUBLIC)

    def never_externalizable_columns(self):
        return sorted(c for c, f in self.fields.items() if f.sensitivity == NEVER)

    def dataset_sensitivity(self):
        """The strictest class present — how sensitive the dataset is as a whole."""
        return most_sensitive([f.sensitivity for f in self.fields.values()])

    def summary(self):
        counts = {}
        for field in self.fields.values():
            counts[field.sensitivity] = counts.get(field.sensitivity, 0) + 1
        return {"columns": len(self.fields), "by_class": counts,
                "dataset_sensitivity": self.dataset_sensitivity(),
                "never_externalizable": self.never_externalizable_columns(),
                "public": self.externalizable_columns()}

    def as_dict(self):
        return {"fields": {c: f.as_dict() for c, f in sorted(self.fields.items())},
                "summary": self.summary()}

    def __len__(self):
        return len(self.fields)


def classify_dataset(dataset):
    """Classify every column of a Dataset. Deterministic and repeatable."""
    return SensitivityMap([classify_field(column, dataset.column(column))
                           for column in dataset.columns])
