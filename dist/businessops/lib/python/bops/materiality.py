"""Materiality: is a change worth a decision-maker's attention?

Implements `reference/materiality-policy.md`. Thresholds always come from the resolved
config, never hard-coded, so a user's setting wins even when it looks too loose or tight.

Materiality **filters and prioritises**; it never halts a workflow. And a third outcome is
needed alongside material/immaterial: `UNDETERMINED`, for when the inputs to judge simply
are not there. Calling an unmeasurable change "not material" would be a quiet lie.
"""

from decimal import Decimal, ROUND_HALF_UP

from .kpi import contract as kpi_contract

MATERIAL = "material"
NOT_MATERIAL = "not_material"
UNDETERMINED = "undetermined"


def _dec(value):
    return value if isinstance(value, Decimal) else Decimal(str(value))


class MaterialityVerdict:
    """The judgement, plus which threshold produced it and where that came from."""

    __slots__ = ("subject", "outcome", "reason", "threshold_used", "threshold_source",
                 "absolute_change", "relative_change", "unit")

    def __init__(self, subject, outcome, reason, threshold_used=None,
                 threshold_source=None, absolute_change=None, relative_change=None,
                 unit=None):
        self.subject = subject
        self.outcome = outcome
        self.reason = reason
        self.threshold_used = threshold_used
        self.threshold_source = threshold_source
        self.absolute_change = absolute_change
        self.relative_change = relative_change
        self.unit = unit

    @property
    def is_material(self):
        return self.outcome == MATERIAL

    def as_dict(self):
        return {
            "subject": self.subject, "outcome": self.outcome, "reason": self.reason,
            "threshold_used": self.threshold_used,
            "threshold_source": self.threshold_source,
            "absolute_change": (str(self.absolute_change)
                                if self.absolute_change is not None else None),
            "relative_change": (str(self.relative_change)
                                if self.relative_change is not None else None),
            "unit": self.unit,
        }

    def __repr__(self):
        return "MaterialityVerdict(%s: %s)" % (self.subject, self.outcome)


def assess_amount(subject, current, prior, config, unit=kpi_contract.CURRENCY):
    """Judge a monetary movement against the absolute and percentage thresholds.

    Both are tested because either alone misleads: a 40% rise on a tiny line is noise, and
    a fixed cash threshold is trivial for a large business and existential for a small one.
    """
    if current is None or prior is None:
        return MaterialityVerdict(
            subject, UNDETERMINED,
            "Cannot determine materiality: %s is missing."
            % ("the prior-period value" if prior is None else "the current value"),
            unit=unit)

    current, prior = _dec(current), _dec(prior)
    absolute = current - prior
    absolute_threshold = _dec(config.get("materiality.absolute_amount", 10000))
    percent_threshold = _dec(config.get("materiality.percentage", 5.0))

    if prior == 0:
        if absolute.copy_abs() >= absolute_threshold:
            return MaterialityVerdict(
                subject, MATERIAL,
                "Movement of %s from a zero base exceeds the absolute threshold %s."
                % (absolute, absolute_threshold),
                threshold_used="absolute_amount",
                threshold_source=config.source_of("materiality.absolute_amount"),
                absolute_change=absolute, unit=unit)
        return MaterialityVerdict(
            subject, UNDETERMINED,
            "Prior period is zero, so a percentage change cannot be computed; the absolute "
            "movement is below the threshold.",
            absolute_change=absolute, unit=unit)

    relative = absolute / prior * Decimal("100")

    if absolute.copy_abs() >= absolute_threshold:
        return MaterialityVerdict(
            subject, MATERIAL,
            "Absolute movement %s meets the %s threshold." % (absolute, absolute_threshold),
            threshold_used="absolute_amount",
            threshold_source=config.source_of("materiality.absolute_amount"),
            absolute_change=absolute, relative_change=relative, unit=unit)

    if relative.copy_abs() >= percent_threshold:
        return MaterialityVerdict(
            subject, MATERIAL,
            "Relative movement %.2f%% meets the %s%% threshold." % (relative, percent_threshold),
            threshold_used="percentage",
            threshold_source=config.source_of("materiality.percentage"),
            absolute_change=absolute, relative_change=relative, unit=unit)

    return MaterialityVerdict(
        subject, NOT_MATERIAL,
        "Movement of %s (%.2f%%) is below both the %s absolute and %s%% relative thresholds."
        % (absolute, relative, absolute_threshold, percent_threshold),
        absolute_change=absolute, relative_change=relative, unit=unit)


def _points_text(points):
    """Percentage points at two places, half up: the presentation rounding used everywhere (R-16)."""
    return points.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def assess_margin(subject, current_pct, prior_pct, config):
    """Judge a margin movement in **percentage points**, never as a percentage change."""
    if current_pct is None or prior_pct is None:
        return MaterialityVerdict(
            subject, UNDETERMINED,
            "Cannot determine materiality: margin for one of the periods is unavailable.",
            unit=kpi_contract.PERCENTAGE_POINTS)

    current_pct, prior_pct = _dec(current_pct), _dec(prior_pct)
    points = current_pct - prior_pct
    threshold = _dec(config.get("materiality.margin_percentage_points", 2.0))

    if points.copy_abs() >= threshold:
        return MaterialityVerdict(
            subject, MATERIAL,
            "Margin moved %spp, meeting the %spp threshold." % (_points_text(points), threshold),
            threshold_used="margin_percentage_points",
            threshold_source=config.source_of("materiality.margin_percentage_points"),
            absolute_change=points, unit=kpi_contract.PERCENTAGE_POINTS)

    return MaterialityVerdict(
        subject, NOT_MATERIAL,
        "Margin moved %spp, below the %spp threshold." % (_points_text(points), threshold),
        absolute_change=points, unit=kpi_contract.PERCENTAGE_POINTS)


def assess_share_of_revenue(subject, amount, total_revenue, config):
    """Judge whether a line is a material share of total revenue."""
    if amount is None or total_revenue in (None, 0):
        return MaterialityVerdict(
            subject, UNDETERMINED,
            "Cannot determine materiality: total revenue is unavailable or zero.",
            unit=kpi_contract.PERCENT)

    share = _dec(amount) / _dec(total_revenue) * Decimal("100")
    threshold = _dec(config.get("materiality.revenue_percentage", 1.0))
    outcome = MATERIAL if share.copy_abs() >= threshold else NOT_MATERIAL
    return MaterialityVerdict(
        subject, outcome,
        "Represents %.2f%% of total revenue (threshold %s%%)." % (share, threshold),
        threshold_used="revenue_percentage",
        threshold_source=config.source_of("materiality.revenue_percentage"),
        relative_change=share, unit=kpi_contract.PERCENT)


def filter_material(verdicts):
    """Keep material findings; immaterial ones are excluded from headlines, not deleted."""
    return [v for v in verdicts if v.is_material]
