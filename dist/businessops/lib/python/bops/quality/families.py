"""The thirteen quality-check families.

The taxonomy is the approved one from the product specification's validation list, which is
what `architecture.md` means by "13 check families":

     1 missing_values          8 inconsistent_customers
     2 duplicate_records       9 inconsistent_products
     3 invalid_dates          10 currency_consistency
     4 invalid_numbers        11 outliers
     5 negative_values        12 broken_formulas
     6 missing_periods        13 incomplete_dataset
     7 duplicate_transactions

Every check observes and reports. **Nothing here repairs, fills, converts, renames or
deletes anything** — where a fix exists, the finding carries remediation guidance and the
user decides.

`outliers` is a *data-integrity* check, not business anomaly detection. It looks for values
whose magnitude suggests a data-entry error — a misplaced decimal, a unit mismatch — not for
months where revenue was unusually good. Business anomaly intelligence is a later milestone
and a different thing entirely.
"""

import datetime
import re
from collections import Counter
from decimal import Decimal

from .. import mapping as mapping_mod
from .contract import (
    CRITICAL, CheckResult, CheckSpec, EXHAUSTIVE, Finding, INFO, PARTIAL, WARNING,
    redact_label, register, safe_examples, threshold,
)


class Context:
    """Everything a check may consult, assembled once."""

    __slots__ = ("dataset", "semantic_map", "config", "canonical", "business_context",
                 "sensitivity_map", "completeness")

    def __init__(self, dataset, semantic_map, config, canonical=None,
                 business_context=None):
        self.dataset = dataset
        self.semantic_map = semantic_map
        self.config = config
        self.canonical = canonical
        self.business_context = business_context
        self.sensitivity_map = (canonical.sensitivity_map() if canonical is not None
                                else None)
        # A sampled or streamed pass cannot claim an exhaustive check.
        self.completeness = (EXHAUSTIVE
                             if canonical is None or canonical.complete
                             else PARTIAL)

    def column_for(self, role):
        return self.semantic_map.column_for(role)

    def values(self, column):
        return self.dataset.column(column)

    def numeric(self, column):
        return [v for v in self.values(column)
                if isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)]

    def examples(self, values, column, limit=3):
        return safe_examples(values, self.sensitivity_map, column, limit)

    def label(self, value, column):
        return redact_label(value, self.sensitivity_map, column)


def _pct(part, whole):
    return (part / float(whole) * 100.0) if whole else 0.0


def _ambiguity_is_date_shaped(values, limit=50):
    """Whether a column's ambiguous values are ambiguous *as dates* rather than numbers.

    Decided by re-reading a sample through the normalizer, so the answer comes from the
    same rules the data layer used rather than a second guess.
    """
    from .. import normalize as normalize_mod

    checked = 0
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        checked += 1
        if normalize_mod.normalize_date(value).kind == normalize_mod.AMBIGUOUS:
            return True
        if checked >= limit:
            break
    return False


def _result(spec, findings, context, examined=None):
    return CheckResult(spec, findings, completeness=context.completeness,
                       examined=examined if examined is not None
                       else context.dataset.row_count)


def _skip(spec, reason):
    return CheckResult(spec, [], completeness="not_run", skipped_reason=reason)


# ==========================================================================
# 1. missing_values
# ==========================================================================

SPEC_MISSING = CheckSpec(
    "missing_values", "Missing values",
    "Nulls and blanks in the fields the analysis depends on.",
    "Empty cells in mapped business roles, graded by how much of the column is absent.",
    "INFO below the configured limit; WARNING above it; CRITICAL when a field the analysis "
    "cannot proceed without (date, revenue) exceeds the limit.",
    can_halt=True, thresholds=("quality.max_missing_pct",))


def check_missing_values(context):
    findings = []
    rows = context.dataset.row_count
    if not rows:
        return _result(SPEC_MISSING, findings, context)

    limit, threshold_record = threshold(context.config, "quality.max_missing_pct", 5.0)
    essential = {mapping_mod.DATE, mapping_mod.REVENUE}

    for role, mapping in sorted(context.semantic_map.mappings.items()):
        values = context.values(mapping.column)
        missing = sum(1 for v in values if v is None or v == "")
        if not missing:
            continue
        percent = _pct(missing, rows)
        if role in essential and percent > limit:
            severity, remediation = CRITICAL, (
                "Supply the missing %s values, or restrict the analysis to the rows that "
                "have them. BusinessOps will not infer them." % role)
            message = ("%d of %d rows (%.1f%%) have no %s value, above the %.1f%% limit. "
                       "Period totals would be understated by an unknown amount."
                       % (missing, rows, percent, role, limit))
        else:
            severity = WARNING if percent > limit else INFO
            remediation = ("Fill or remove the blank %s values if the affected rows matter."
                           % role)
            message = ("%d of %d rows (%.1f%%) have no %s value."
                       % (missing, rows, percent, role))
        findings.append(Finding(
            "missing", "missing_%s" % role, severity, message,
            detail="Column %r" % mapping.column, affected=missing,
            check_id=SPEC_MISSING.check_id, fields=[mapping.column],
            evidence={"missing": missing, "rows": rows, "percent": round(percent, 2)},
            threshold=threshold_record, observed=round(percent, 2),
            remediation=remediation, completeness=context.completeness))

    # A column that is entirely empty is worth stating separately.
    for column in context.dataset.columns:
        values = context.values(column)
        if values and all(v in (None, "") for v in values):
            findings.append(Finding(
                "missing", "empty_column", WARNING,
                "Column %r is entirely empty." % column,
                affected=len(values), check_id=SPEC_MISSING.check_id, fields=[column],
                evidence={"rows": len(values)},
                remediation="Remove the column, or supply its values.",
                completeness=context.completeness))
    return _result(SPEC_MISSING, findings, context)


register(SPEC_MISSING, check_missing_values)


# ==========================================================================
# 2. duplicate_records
# ==========================================================================

SPEC_DUPLICATE_RECORDS = CheckSpec(
    "duplicate_records", "Duplicate records",
    "Rows that are exact copies of another row.",
    "Whole-row duplicates, which inflate every total derived from the dataset.",
    "INFO at or below tolerance; WARNING above it; CRITICAL when duplicates exceed the "
    "configured share of the dataset, since totals would be materially wrong.",
    can_halt=True,
    thresholds=("quality.duplicate_tolerance", "quality.max_duplicate_pct"))


def check_duplicate_records(context):
    findings = []
    rows = context.dataset.row_count
    if not rows:
        return _result(SPEC_DUPLICATE_RECORDS, findings, context)

    tolerance, tolerance_record = threshold(
        context.config, "quality.duplicate_tolerance", 0)
    max_pct, pct_record = threshold(context.config, "quality.max_duplicate_pct", 5.0)

    signatures = Counter(
        tuple(sorted((k, str(v)) for k, v in row.items())) for row in context.dataset.rows)
    duplicates = sum(count - 1 for count in signatures.values() if count > 1)

    if duplicates > tolerance:
        percent = _pct(duplicates, rows)
        severity = CRITICAL if percent > max_pct else WARNING
        findings.append(Finding(
            "duplicates", "identical_rows", severity,
            "%d row(s) (%.1f%%) are exact duplicates of another row; every total derived "
            "from this dataset would be inflated." % (duplicates, percent),
            affected=duplicates, check_id=SPEC_DUPLICATE_RECORDS.check_id,
            evidence={"duplicate_rows": duplicates, "rows": rows,
                      "percent": round(percent, 2)},
            threshold=pct_record if severity == CRITICAL else tolerance_record,
            observed=round(percent, 2),
            remediation="De-duplicate at source and re-supply. BusinessOps does not remove "
                        "rows on your behalf.",
            completeness=context.completeness))
    return _result(SPEC_DUPLICATE_RECORDS, findings, context)


register(SPEC_DUPLICATE_RECORDS, check_duplicate_records)


# ==========================================================================
# 3. invalid_dates
# ==========================================================================

SPEC_INVALID_DATES = CheckSpec(
    "invalid_dates", "Invalid dates",
    "Values in the date field that are not usable dates.",
    "Unparseable dates, ambiguous day/month orders, future dates and implausibly old dates.",
    "WARNING for a small proportion or for plausibility concerns; CRITICAL when enough of "
    "the date column is unusable that period analysis cannot be trusted.",
    can_halt=True, thresholds=("quality.max_invalid_pct",),
    requires_roles=(mapping_mod.DATE,))


def check_invalid_dates(context):
    column = context.column_for(mapping_mod.DATE)
    if not column:
        # No date role mapped. Ambiguous date-shaped values are very often the reason, and
        # this is the family a user would look in, so report them here rather than nowhere.
        findings = []
        if context.canonical is not None:
            for candidate, field in sorted(context.canonical.fields.items()):
                if (field.profile.ambiguous_count
                        and _ambiguity_is_date_shaped(context.values(candidate))):
                    findings.append(Finding(
                        "validity", "ambiguous_dates", WARNING,
                        "Column %r holds %d date value(s) that could be read two ways "
                        "(day/month order), so it could not be used as the date column."
                        % (candidate, field.profile.ambiguous_count),
                        detail=(field.profile.warnings[0]
                                if field.profile.warnings else None),
                        affected=field.profile.ambiguous_count,
                        check_id=SPEC_INVALID_DATES.check_id, fields=[candidate],
                        evidence={"ambiguous": field.profile.ambiguous_count},
                        remediation="Re-supply dates in ISO format (YYYY-MM-DD), or state "
                                    "the day/month convention.",
                        completeness=context.completeness))
        if findings:
            return _result(SPEC_INVALID_DATES, findings, context)
        return _skip(SPEC_INVALID_DATES, "no date column is mapped")

    findings = []
    limit, threshold_record = threshold(context.config, "quality.max_invalid_pct", 10.0)
    values = [v for v in context.values(column) if v not in (None, "")]
    if not values:
        return _result(SPEC_INVALID_DATES, findings, context)

    invalid = [v for v in values
               if not isinstance(v, (datetime.date, datetime.datetime))]
    if invalid:
        percent = _pct(len(invalid), len(values))
        severity = CRITICAL if percent > limit else WARNING
        findings.append(Finding(
            "validity", "invalid_dates", severity,
            "%d date value(s) (%.1f%%) could not be read as dates."
            % (len(invalid), percent),
            affected=len(invalid), check_id=SPEC_INVALID_DATES.check_id, fields=[column],
            evidence=dict(context.examples(invalid, column),
                          invalid=len(invalid), checked=len(values)),
            threshold=threshold_record, observed=round(percent, 2),
            remediation="Format the date column consistently (ISO YYYY-MM-DD is safest) "
                        "and re-supply.",
            completeness=context.completeness))

    # Ambiguity is a distinct problem from invalidity: the value is readable two ways.
    if context.canonical is not None:
        field = context.canonical.field(column)
        if field is not None and field.profile.ambiguous_count:
            findings.append(Finding(
                "validity", "ambiguous_dates", WARNING,
                "%d date value(s) could be read two ways and were not interpreted."
                % field.profile.ambiguous_count,
                detail=(field.profile.warnings[0] if field.profile.warnings else None),
                affected=field.profile.ambiguous_count,
                check_id=SPEC_INVALID_DATES.check_id, fields=[column],
                evidence={"ambiguous": field.profile.ambiguous_count},
                remediation="State the day/month convention, or re-supply in ISO format.",
                completeness=context.completeness))

    real = [v.date() if isinstance(v, datetime.datetime) else v
            for v in values if isinstance(v, (datetime.date, datetime.datetime))]
    if real:
        today = datetime.date.today()
        future = [d for d in real if d > today]
        ancient = [d for d in real if d.year < 1990]
        if future:
            findings.append(Finding(
                "validity", "future_dates", WARNING,
                "%d transaction(s) are dated in the future." % len(future),
                detail="Latest: %s" % max(future).isoformat(), affected=len(future),
                check_id=SPEC_INVALID_DATES.check_id, fields=[column],
                evidence={"count": len(future), "latest": max(future).isoformat()},
                remediation="Confirm these are genuine forward-dated records rather than "
                            "typing errors.",
                completeness=context.completeness))
        if ancient:
            findings.append(Finding(
                "validity", "implausible_dates", WARNING,
                "%d transaction(s) are dated before 1990." % len(ancient),
                affected=len(ancient), check_id=SPEC_INVALID_DATES.check_id,
                fields=[column],
                evidence={"count": len(ancient), "earliest": min(ancient).isoformat()},
                remediation="Check for two-digit year or default-date errors.",
                completeness=context.completeness))
    return _result(SPEC_INVALID_DATES, findings, context, examined=len(values))


register(SPEC_INVALID_DATES, check_invalid_dates)


# ==========================================================================
# 4. invalid_numbers
# ==========================================================================

SPEC_INVALID_NUMBERS = CheckSpec(
    "invalid_numbers", "Invalid numbers",
    "Values in numeric fields that cannot be summed.",
    "Non-numeric text in money and quantity columns, ambiguous numeric formats, and "
    "columns that mix types.",
    "WARNING for a small proportion; CRITICAL when enough of a monetary column is "
    "unusable that totals would be wrong.",
    can_halt=True, thresholds=("quality.max_invalid_pct",))


_NUMERIC_ROLES = (mapping_mod.REVENUE, mapping_mod.COST, mapping_mod.QUANTITY,
                  mapping_mod.UNIT_PRICE, mapping_mod.PROFIT)


def check_invalid_numbers(context):
    findings = []
    limit, threshold_record = threshold(context.config, "quality.max_invalid_pct", 10.0)
    examined = 0

    for role in _NUMERIC_ROLES:
        column = context.column_for(role)
        if not column:
            continue
        values = [v for v in context.values(column) if v not in (None, "")]
        if not values:
            continue
        examined += len(values)
        invalid = [v for v in values
                   if not isinstance(v, (int, float, Decimal)) or isinstance(v, bool)]
        if invalid:
            percent = _pct(len(invalid), len(values))
            monetary = role in (mapping_mod.REVENUE, mapping_mod.COST,
                                mapping_mod.PROFIT)
            severity = CRITICAL if (monetary and percent > limit) else WARNING
            findings.append(Finding(
                "validity", "non_numeric_%s" % role, severity,
                "%d %s value(s) (%.1f%%) are not numeric and cannot be summed."
                % (len(invalid), role, percent),
                affected=len(invalid), check_id=SPEC_INVALID_NUMBERS.check_id,
                fields=[column],
                evidence=dict(context.examples(invalid, column),
                              invalid=len(invalid), checked=len(values)),
                threshold=threshold_record, observed=round(percent, 2),
                remediation="Remove text from the %s column (currency symbols and "
                            "thousands separators are handled automatically)." % role,
                completeness=context.completeness))

    numeric_columns = {context.column_for(r) for r in _NUMERIC_ROLES} - {None}
    if context.canonical is not None:
        for column, field in sorted(context.canonical.fields.items()):
            date_shaped = _ambiguity_is_date_shaped(context.values(column))
            if field.profile.ambiguous_count and not date_shaped:
                findings.append(Finding(
                    "validity", "ambiguous_numbers", WARNING,
                    "Column %r has %d value(s) whose numeric format is ambiguous and were "
                    "not interpreted." % (column, field.profile.ambiguous_count),
                    detail=(field.profile.warnings[0] if field.profile.warnings else None),
                    affected=field.profile.ambiguous_count,
                    check_id=SPEC_INVALID_NUMBERS.check_id, fields=[column],
                    evidence={"ambiguous": field.profile.ambiguous_count},
                    remediation="State the decimal convention, or re-supply with an "
                                "unambiguous format.",
                    completeness=context.completeness))
            if field.profile.is_mixed:
                kinds = sorted(k for k in field.profile.kind_counts
                               if k not in ("empty", "ambiguous"))
                findings.append(Finding(
                    "validity", "mixed_types", WARNING,
                    "Column %r mixes value types (%s); it may not mean one thing."
                    % (column, ", ".join(kinds)),
                    affected=field.profile.total_count,
                    check_id=SPEC_INVALID_NUMBERS.check_id, fields=[column],
                    evidence={"kinds": kinds},
                    remediation="Split the column, or make its values consistent.",
                    completeness=context.completeness))
    return _result(SPEC_INVALID_NUMBERS, findings, context, examined=examined)


register(SPEC_INVALID_NUMBERS, check_invalid_numbers)


# ==========================================================================
# 5. negative_values
# ==========================================================================

SPEC_NEGATIVE = CheckSpec(
    "negative_values", "Unexpected negative values",
    "Negative numbers in fields that are normally positive.",
    "Negative revenue or quantity, which may be legitimate refunds or a sign error.",
    "INFO at a small proportion (refunds are normal); WARNING above the configured share. "
    "Never CRITICAL — a negative value is not by itself unusable.",
    can_halt=False, thresholds=("quality.negative_tolerance_pct",))


def check_negative_values(context):
    findings = []
    limit, threshold_record = threshold(
        context.config, "quality.negative_tolerance_pct", 5.0)

    for role in (mapping_mod.REVENUE, mapping_mod.QUANTITY, mapping_mod.UNIT_PRICE):
        column = context.column_for(role)
        if not column:
            continue
        values = context.numeric(column)
        if not values:
            continue
        negative = [v for v in values if v < 0]
        if not negative:
            continue
        percent = _pct(len(negative), len(values))
        severity = WARNING if percent > limit else INFO
        findings.append(Finding(
            "validity", "negative_%s" % role, severity,
            "%d %s value(s) (%.1f%%) are negative. These may be refunds or corrections; "
            "they are included as-is and not removed."
            % (len(negative), role, percent),
            affected=len(negative), check_id=SPEC_NEGATIVE.check_id, fields=[column],
            evidence={"negative": len(negative), "checked": len(values),
                      "percent": round(percent, 2)},
            threshold=threshold_record, observed=round(percent, 2),
            remediation="Confirm these are refunds. If they are sign errors, correct them "
                        "at source.",
            completeness=context.completeness))

    # Cost above revenue on a line implies a negative margin: a business-sanity signal.
    revenue_column = context.column_for(mapping_mod.REVENUE)
    cost_column = context.column_for(mapping_mod.COST)
    if revenue_column and cost_column:
        inverted = 0
        for row in context.dataset.rows:
            revenue, cost = row.get(revenue_column), row.get(cost_column)
            if (isinstance(revenue, (int, float, Decimal))
                    and isinstance(cost, (int, float, Decimal))
                    and not isinstance(revenue, bool) and revenue > 0 and cost > revenue):
                inverted += 1
        if inverted:
            percent = _pct(inverted, context.dataset.row_count)
            findings.append(Finding(
                "validity", "cost_exceeds_revenue", WARNING,
                "%d row(s) (%.1f%%) have cost greater than revenue, implying a negative "
                "gross margin on those lines." % (inverted, percent),
                affected=inverted, check_id=SPEC_NEGATIVE.check_id,
                fields=[revenue_column, cost_column],
                evidence={"rows": inverted, "percent": round(percent, 2)},
                remediation="Check for cost and revenue columns being swapped, or for "
                            "cost recorded against the wrong line.",
                completeness=context.completeness))
    return _result(SPEC_NEGATIVE, findings, context)


register(SPEC_NEGATIVE, check_negative_values)


# ==========================================================================
# 6. missing_periods
# ==========================================================================

SPEC_MISSING_PERIODS = CheckSpec(
    "missing_periods", "Missing periods",
    "Gaps in the time series that would distort period comparison.",
    "Calendar months between the first and last record that contain no data at all.",
    "INFO for a single gap; WARNING above the configured share of the range; CRITICAL "
    "when so much of the range is missing that trend analysis would mislead.",
    can_halt=True,
    thresholds=("quality.max_period_gap_pct", "quality.min_periods"),
    requires_roles=(mapping_mod.DATE,))


def _month_key(value):
    if isinstance(value, datetime.datetime):
        value = value.date()
    if isinstance(value, datetime.date):
        return (value.year, value.month)
    return None


def check_missing_periods(context):
    column = context.column_for(mapping_mod.DATE)
    if not column:
        return _skip(SPEC_MISSING_PERIODS, "no date column is mapped")

    findings = []
    max_gap_pct, gap_record = threshold(
        context.config, "quality.max_period_gap_pct", 20.0)
    min_periods, min_record = threshold(context.config, "quality.min_periods", 2)

    present = sorted({_month_key(v) for v in context.values(column)} - {None})
    if not present:
        return _result(SPEC_MISSING_PERIODS, findings, context, examined=0)

    if len(present) < min_periods:
        findings.append(Finding(
            "periods", "insufficient_periods", WARNING,
            "The data covers only %d period(s); at least %d are needed to compare periods."
            % (len(present), min_periods),
            check_id=SPEC_MISSING_PERIODS.check_id, fields=[column],
            evidence={"periods": len(present)},
            threshold=min_record, observed=len(present),
            remediation="Supply a longer history if period comparison is needed.",
            completeness=context.completeness))
        return _result(SPEC_MISSING_PERIODS, findings, context, examined=len(present))

    (start_year, start_month), (end_year, end_month) = present[0], present[-1]
    expected = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        expected.append((year, month))
        month += 1
        if month > 12:
            year, month = year + 1, 1

    gaps = [p for p in expected if p not in set(present)]
    if gaps:
        percent = _pct(len(gaps), len(expected))
        severity = CRITICAL if percent > max_gap_pct * 2 else (
            WARNING if percent > max_gap_pct else INFO)
        rendered = ", ".join("%04d-%02d" % g for g in gaps[:6])
        findings.append(Finding(
            "periods", "missing_periods", severity,
            "%d of %d months between %04d-%02d and %04d-%02d contain no data (%.1f%%). "
            "Period comparisons will understate the gaps."
            % (len(gaps), len(expected), start_year, start_month, end_year, end_month,
               percent),
            detail="Missing: %s%s" % (rendered, " ..." if len(gaps) > 6 else ""),
            affected=len(gaps), check_id=SPEC_MISSING_PERIODS.check_id, fields=[column],
            evidence={"missing_periods": ["%04d-%02d" % g for g in gaps[:12]],
                      "expected": len(expected), "present": len(present)},
            threshold=gap_record, observed=round(percent, 2),
            remediation="Supply the missing months, or state that the business genuinely "
                        "had no activity in them.",
            completeness=context.completeness))
    return _result(SPEC_MISSING_PERIODS, findings, context, examined=len(expected))


register(SPEC_MISSING_PERIODS, check_missing_periods)


# ==========================================================================
# 7. duplicate_transactions
# ==========================================================================

SPEC_DUPLICATE_TRANSACTIONS = CheckSpec(
    "duplicate_transactions", "Duplicate transactions",
    "Transaction identifiers that appear more than once.",
    "Repeated order or invoice numbers, which may mean double-counted revenue.",
    "INFO at or below tolerance; WARNING above it. Never CRITICAL: a repeated order "
    "number is normal for a multi-line order, and BusinessOps cannot tell that apart from "
    "a duplicated record. Whole-row duplicates are what escalate - see duplicate_records.",
    can_halt=False,
    thresholds=("quality.duplicate_tolerance",),
    requires_roles=(mapping_mod.ORDER_ID,))


def check_duplicate_transactions(context):
    column = context.column_for(mapping_mod.ORDER_ID)
    if not column:
        return _skip(SPEC_DUPLICATE_TRANSACTIONS,
                     "no transaction identifier column is mapped")

    findings = []
    tolerance, tolerance_record = threshold(
        context.config, "quality.duplicate_tolerance", 0)

    counts = Counter(v for v in context.values(column) if v not in (None, ""))
    repeated = {k: n for k, n in counts.items() if n > 1}
    if len(repeated) > tolerance:
        extra = sum(n - 1 for n in repeated.values())
        percent = _pct(extra, context.dataset.row_count)
        findings.append(Finding(
            "duplicates", "duplicate_transaction_id", WARNING,
            "%d transaction identifier(s) appear more than once, affecting %d extra row(s) "
            "(%.1f%%). This is normal for multi-line orders, but if each row is meant to be "
            "one transaction, revenue is double-counted."
            % (len(repeated), extra, percent),
            affected=extra, check_id=SPEC_DUPLICATE_TRANSACTIONS.check_id,
            fields=[column],
            evidence=dict(context.examples(sorted(repeated), column),
                          repeated_ids=len(repeated), extra_rows=extra),
            threshold=tolerance_record, observed=round(percent, 2),
            remediation="Confirm whether these are genuine multi-line orders or duplicated "
                        "records. BusinessOps does not de-duplicate for you.",
            completeness=context.completeness))
    return _result(SPEC_DUPLICATE_TRANSACTIONS, findings, context)


register(SPEC_DUPLICATE_TRANSACTIONS, check_duplicate_transactions)


# ==========================================================================
# 8 & 9. inconsistent_customers / inconsistent_products
# ==========================================================================

def _label_variants(values):
    """Group labels that differ only by case, whitespace or punctuation."""
    groups = {}
    for value in values:
        if value in (None, ""):
            continue
        key = re.sub(r"[^a-z0-9]+", "", str(value).lower())
        if key:
            groups.setdefault(key, set()).add(str(value))
    return {k: v for k, v in groups.items() if len(v) > 1}


def _inconsistent_labels(context, spec, role, noun):
    column = context.column_for(role)
    if not column:
        return _skip(spec, "no %s column is mapped" % noun)

    findings = []
    variants = _label_variants(context.values(column))
    if variants:
        distinct = len({v for group in variants.values() for v in group})
        example_group = sorted(next(iter(variants.values())))
        findings.append(Finding(
            "consistency", "inconsistent_%s_labels" % noun, WARNING,
            "%d %s name(s) appear with inconsistent spelling, casing or punctuation; they "
            "will be counted as separate %ss." % (len(variants), noun, noun),
            detail=("Example: %s"
                    % " / ".join(context.label(v, column) for v in example_group[:3])),
            affected=distinct, check_id=spec.check_id, fields=[column],
            evidence={"variant_groups": len(variants), "distinct_labels": distinct,
                      "example": [context.label(v, column) for v in example_group[:3]]},
            remediation="Standardise %s names at source. BusinessOps will not merge them "
                        "on its own, because two similar names can be two real %ss."
                        % (noun, noun),
            completeness=context.completeness))
    return _result(spec, findings, context)


SPEC_INCONSISTENT_CUSTOMERS = CheckSpec(
    "inconsistent_customers", "Inconsistent customer names",
    "Customer labels that refer to one customer but do not match exactly.",
    "Case, whitespace and punctuation variants that would split one customer into several.",
    "WARNING whenever variants exist. Never CRITICAL — BusinessOps cannot know whether two "
    "similar names are one customer or two.",
    can_halt=False, requires_roles=(mapping_mod.CUSTOMER,))


def check_inconsistent_customers(context):
    return _inconsistent_labels(context, SPEC_INCONSISTENT_CUSTOMERS,
                                mapping_mod.CUSTOMER, "customer")


register(SPEC_INCONSISTENT_CUSTOMERS, check_inconsistent_customers)


SPEC_INCONSISTENT_PRODUCTS = CheckSpec(
    "inconsistent_products", "Inconsistent product names",
    "Product labels that refer to one product but do not match exactly.",
    "Case, whitespace and punctuation variants that would split one product into several.",
    "WARNING whenever variants exist. Never CRITICAL, for the same reason as customers.",
    can_halt=False, requires_roles=(mapping_mod.PRODUCT,))


def check_inconsistent_products(context):
    return _inconsistent_labels(context, SPEC_INCONSISTENT_PRODUCTS,
                                mapping_mod.PRODUCT, "product")


register(SPEC_INCONSISTENT_PRODUCTS, check_inconsistent_products)


# ==========================================================================
# 10. currency_consistency
# ==========================================================================

SPEC_CURRENCY = CheckSpec(
    "currency_consistency", "Currency consistency",
    "Whether every monetary value is in one, known currency.",
    "Multiple currencies in one dataset, and disagreement between the data and Business "
    "Context.",
    "CRITICAL in both cases: summing across currencies, or reporting in the wrong one, "
    "produces figures that are simply wrong. BusinessOps never converts.",
    can_halt=True)


def check_currency_consistency(context):
    if context.canonical is None:
        return _skip(SPEC_CURRENCY, "no canonical view available")

    findings = []
    currencies = context.canonical.currencies()

    if len(currencies) > 1:
        findings.append(Finding(
            "currency", "mixed_currencies", CRITICAL,
            "The dataset contains %d currencies (%s). Totals across different currencies "
            "would be meaningless, and BusinessOps does not convert."
            % (len(currencies), ", ".join(currencies)),
            check_id=SPEC_CURRENCY.check_id,
            evidence={"currencies": currencies},
            remediation="Split the data by currency, or convert it to a single currency "
                        "at a rate you choose and can defend.",
            completeness=context.completeness))

    if context.business_context is not None and currencies:
        stated = context.business_context.get("reporting.currency")
        if stated and stated not in currencies:
            findings.append(Finding(
                "currency", "currency_contradiction", CRITICAL,
                "Business Context states the reporting currency is %s, but the data is "
                "denominated in %s. Monetary figures cannot be trusted until this is "
                "resolved; no exchange rate is applied automatically."
                % (stated, ", ".join(currencies)),
                check_id=SPEC_CURRENCY.check_id,
                evidence={"context_currency": stated, "data_currencies": currencies},
                remediation="Correct Business Context, or supply data in the stated "
                            "currency.",
                completeness=context.completeness))
    return _result(SPEC_CURRENCY, findings, context)


register(SPEC_CURRENCY, check_currency_consistency)


# ==========================================================================
# 11. outliers  (DATA INTEGRITY, not business anomaly detection)
# ==========================================================================

SPEC_OUTLIERS = CheckSpec(
    "outliers", "Suspicious outliers",
    "Values whose magnitude suggests a data-entry error rather than a real figure.",
    "Values thousands of times the column median - the signature of a misplaced decimal "
    "point or a unit mismatch (pence entered as pounds, units as thousands).",
    "INFO or WARNING only. Never CRITICAL, and never described as fraud: an unusual "
    "business value is not a data defect, and distinguishing the two is the user's call.",
    can_halt=False,
    thresholds=("quality.outlier_ratio", "quality.outlier_min_sample"))


def _median(values):
    ordered = sorted(values)
    count = len(ordered)
    if not count:
        return None
    middle = count // 2
    if count % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def check_outliers(context):
    findings = []
    ratio_limit, ratio_record = threshold(context.config, "quality.outlier_ratio", 1000.0)
    min_sample, sample_record = threshold(
        context.config, "quality.outlier_min_sample", 30)

    for role in (mapping_mod.REVENUE, mapping_mod.COST, mapping_mod.QUANTITY,
                 mapping_mod.UNIT_PRICE):
        column = context.column_for(role)
        if not column:
            continue
        values = [abs(float(v)) for v in context.numeric(column) if v]
        if len(values) < min_sample:
            continue
        median = _median(values)
        if not median:
            continue
        extreme = [v for v in values if v > median * ratio_limit]
        if not extreme:
            continue
        findings.append(Finding(
            "outliers", "magnitude_outlier_%s" % role, WARNING,
            "%d %s value(s) are more than %.0fx the column median (%.2f). A gap this large "
            "usually means a misplaced decimal point or a unit mismatch rather than a real "
            "figure." % (len(extreme), role, ratio_limit, median),
            detail="This is a data-integrity signal, not a judgement about business "
                   "performance.",
            affected=len(extreme), check_id=SPEC_OUTLIERS.check_id, fields=[column],
            evidence={"median": round(median, 2), "largest": round(max(extreme), 2),
                      "count": len(extreme), "sample": len(values)},
            threshold=ratio_record, observed=round(max(extreme) / median, 1),
            remediation="Check the units and decimal placement on these rows. If they are "
                        "genuine, no action is needed.",
            completeness=context.completeness))
    return _result(SPEC_OUTLIERS, findings, context)


register(SPEC_OUTLIERS, check_outliers)


# ==========================================================================
# 12. broken_formulas
# ==========================================================================

SPEC_BROKEN_FORMULAS = CheckSpec(
    "broken_formulas", "Broken formulas",
    "Spreadsheet formulas whose results could not be read.",
    "Formula cells with no cached value, Excel error values, and external references whose "
    "cached results may be stale.",
    "WARNING in general; CRITICAL when a field the analysis depends on is largely made of "
    "unreadable formulas, because the totals would be silently short.",
    can_halt=True, thresholds=("quality.max_invalid_pct",))


_FORMULA_CODES = {
    "formula_without_cached_value": (
        "Formula cells had no cached value. BusinessOps never evaluates formulas, so those "
        "cells were read as empty rather than computed."),
    "cell_error": "Cells contain Excel error values such as #DIV/0! or #N/A.",
    "external_reference_cached": (
        "Cells reference another workbook. The external file was not opened, so the value "
        "used is whatever was last cached and may be stale."),
}


def check_broken_formulas(context):
    findings = []
    counts = Counter(w.code for w in context.dataset.warnings)

    for code, explanation in _FORMULA_CODES.items():
        if not counts.get(code):
            continue
        findings.append(Finding(
            "formulas", code, WARNING, explanation,
            detail="%d occurrence(s) reported during ingestion." % counts[code],
            affected=counts[code], check_id=SPEC_BROKEN_FORMULAS.check_id,
            evidence={"occurrences": counts[code]},
            remediation=("Open the workbook, let Excel recalculate, and save it so the "
                         "values are cached; or paste the results as values."),
            completeness=context.completeness))

    # A required numeric field made mostly of unreadable formulas is worse than a warning.
    limit, threshold_record = threshold(context.config, "quality.max_invalid_pct", 10.0)
    if counts.get("formula_without_cached_value"):
        for role in (mapping_mod.REVENUE, mapping_mod.COST):
            column = context.column_for(role)
            if not column:
                continue
            values = context.values(column)
            if not values:
                continue
            empty = sum(1 for v in values if v is None or v == "")
            percent = _pct(empty, len(values))
            if percent > limit:
                findings.append(Finding(
                    "formulas", "formula_gap_in_%s" % role, CRITICAL,
                    "%.1f%% of the %s column is empty, and this workbook contains formulas "
                    "with no cached value. Totals would be silently short."
                    % (percent, role),
                    affected=empty, check_id=SPEC_BROKEN_FORMULAS.check_id,
                    fields=[column],
                    evidence={"empty": empty, "rows": len(values),
                              "percent": round(percent, 2)},
                    threshold=threshold_record, observed=round(percent, 2),
                    remediation="Recalculate and save the workbook, or export the sheet as "
                                "values, then re-supply it.",
                    completeness=context.completeness))
    return _result(SPEC_BROKEN_FORMULAS, findings, context)


register(SPEC_BROKEN_FORMULAS, check_broken_formulas)


# ==========================================================================
# 13. incomplete_dataset
# ==========================================================================

SPEC_INCOMPLETE = CheckSpec(
    "incomplete_dataset", "Incomplete dataset",
    "Whether the dataset is structurally capable of supporting analysis at all.",
    "No rows, too few columns, no identifiable date or revenue field, unconfirmed column "
    "mappings, a degraded reader tier, and partial processing.",
    "CRITICAL when the irreducible minimum (rows, a date field, a revenue field) is "
    "absent; WARNING for degraded reads, unconfirmed mappings and partial processing.",
    can_halt=True)


def check_incomplete_dataset(context):
    findings = []
    dataset = context.dataset

    if dataset.row_count == 0:
        findings.append(Finding(
            "structure", "no_rows", CRITICAL,
            "The dataset contains no data rows.",
            check_id=SPEC_INCOMPLETE.check_id,
            evidence={"rows": 0, "columns": dataset.column_count},
            remediation="Supply a file with at least a header row and one data row.",
            completeness=context.completeness))
        return _result(SPEC_INCOMPLETE, findings, context)

    if dataset.column_count < 2:
        findings.append(Finding(
            "structure", "too_few_columns", CRITICAL,
            "The dataset has fewer than two columns; it cannot be business data.",
            check_id=SPEC_INCOMPLETE.check_id,
            evidence={"columns": dataset.column_count},
            remediation="Check the delimiter - a single column often means the file was "
                        "read with the wrong separator.",
            completeness=context.completeness))

    for role, label in ((mapping_mod.DATE, "date/period"),
                        (mapping_mod.REVENUE, "revenue")):
        if not context.semantic_map.has(role):
            findings.append(Finding(
                "structure", "missing_role_%s" % role, CRITICAL,
                "No %s column could be identified. Insufficient data to analyse this "
                "dataset reliably." % label,
                detail="Columns present: %s" % ", ".join(dataset.columns),
                check_id=SPEC_INCOMPLETE.check_id,
                evidence={"columns": dataset.columns,
                          "explanation": context.semantic_map.explain(role)},
                remediation="Rename the %s column to something recognisable, or confirm "
                            "which column holds it." % label,
                completeness=context.completeness))

    for unconfirmed in context.semantic_map.needs_confirmation():
        findings.append(Finding(
            "structure", "mapping_needs_confirmation", WARNING,
            "Column %r is only provisionally identified as %r (confidence %.2f)."
            % (unconfirmed.column, unconfirmed.role, unconfirmed.confidence),
            detail="Confirm this mapping before relying on any figure derived from it.",
            check_id=SPEC_INCOMPLETE.check_id, fields=[unconfirmed.column],
            evidence={"role": unconfirmed.role, "confidence": unconfirmed.confidence,
                      "explanation": unconfirmed.explain()},
            remediation="Confirm or correct the mapping.",
            completeness=context.completeness))

    # Ingest warnings that are not formula-related belong here (tier, encoding, structure).
    for warning in dataset.warnings:
        if warning.code in _FORMULA_CODES:
            continue
        findings.append(Finding(
            "structure", "ingest_%s" % warning.code, WARNING, warning.message,
            detail=warning.location, check_id=SPEC_INCOMPLETE.check_id,
            evidence={"code": warning.code},
            completeness=context.completeness))

    # A sampled or streamed pass must never look like an exhaustive one.
    if context.canonical is not None and not context.canonical.complete:
        findings.append(Finding(
            "structure", "partial_processing", WARNING,
            "Only %d of %d rows were examined (%s processing). Quality findings describe "
            "the examined portion, not the whole dataset."
            % (context.canonical.rows_examined, context.canonical.row_count,
               context.canonical.processing_mode),
            check_id=SPEC_INCOMPLETE.check_id,
            evidence={"rows_examined": context.canonical.rows_examined,
                      "rows_total": context.canonical.row_count,
                      "processing_mode": context.canonical.processing_mode},
            remediation="Supply a smaller extract if an exhaustive check is required.",
            completeness=context.completeness))
    return _result(SPEC_INCOMPLETE, findings, context)


register(SPEC_INCOMPLETE, check_incomplete_dataset)

