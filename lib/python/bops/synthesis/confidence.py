"""Confidence as a derived verdict with named reasons, never a free-text score.

BusinessOps's confidence vocabulary is qualitative - `HIGH`, `MEDIUM`, `LOW` from
`reference/evidence-ledger.md` - and that is deliberate. None of the inputs here is a
probability: a tier assignment is not a likelihood, an undated source is not a variance,
and a data-quality warning is not a confidence interval. Presenting any of them as a
percentage would be false precision dressed as rigour.

What this module adds is that the verdict must be **explainable**. Every downgrade is a
named code with fixed text, so "why is this MEDIUM" always has an answer that came from
data rather than from prose. A confidence with no reasons is `HIGH`; a confidence with
reasons lists them.

The arithmetic is intentionally crude and intentionally fixed:

    no reasons                        -> HIGH
    one ordinary reason               -> MEDIUM
    two or more ordinary reasons      -> LOW
    any severe reason                 -> LOW

A severe reason is one that undermines the statement's footing rather than qualifying it:
an unresolved conflict, an unsupported statement, absent provenance, or a material
data-quality warning. One of those is enough on its own, because a statement that might
not be true is not a statement held with medium confidence.
"""

from .. import evidence as evidence_mod

HIGH = evidence_mod.HIGH
MEDIUM = evidence_mod.MEDIUM
LOW = evidence_mod.LOW

LEVELS = (LOW, MEDIUM, HIGH)

#: Weakest first, so `min` picks the weakest verdict across a collection.
LEVEL_ORDER = (LOW, MEDIUM, HIGH)

# -- reason codes ------------------------------------------------------------

UNRESOLVED_CONFLICT = "unresolved_conflict"
UNSUPPORTED_STATEMENT = "unsupported_statement"
INSUFFICIENT_EVIDENCE = "insufficient_evidence"
PROVENANCE_UNAVAILABLE = "provenance_unavailable"
DATA_QUALITY_WARNING = "material_data_quality_warning"

TIER_C_ONLY = "tier_c_only_support"
UNDATED_EXTERNAL = "undated_external_evidence"
STALE_EXTERNAL = "stale_external_evidence"
INSUFFICIENT_HISTORY = "insufficient_history"
INCOMPLETE_DATASET = "incomplete_dataset"
UNAVAILABLE_KPI = "unavailable_kpi"
FORECAST_INSTABILITY = "forecast_instability"
INCOMPARABLE_VALUES = "incomparable_values"
SINGLE_SOURCE = "single_source_only"
PARTICIPANT_SOURCED = "participant_sourced_evidence"

REASON_TEXT = {
    UNRESOLVED_CONFLICT: "Sources disagree and the disagreement is unresolved.",
    UNSUPPORTED_STATEMENT: "The linked evidence does not adequately support a material "
                           "statement.",
    INSUFFICIENT_EVIDENCE: "No resolvable supporting material was linked, so support "
                           "could not be assessed.",
    PROVENANCE_UNAVAILABLE: "Provenance for this statement is unavailable.",
    DATA_QUALITY_WARNING: "The contributing dataset carries a material data-quality "
                          "warning.",
    TIER_C_ONLY: "Support rests on tier C sources only, which corroborate but never "
                 "stand alone for a material claim.",
    UNDATED_EXTERNAL: "External evidence carries no publication date and cannot be shown "
                      "to be current.",
    STALE_EXTERNAL: "External evidence is past its staleness window for its claim kind.",
    INSUFFICIENT_HISTORY: "The history available is too short for the analysis "
                          "requested.",
    INCOMPLETE_DATASET: "The dataset is incomplete for the period analysed.",
    UNAVAILABLE_KPI: "A KPI this statement depends on could not be computed.",
    FORECAST_INSTABILITY: "The forecast's backtest error or method stability is poor.",
    INCOMPARABLE_VALUES: "Values that would have been compared were not comparable and "
                         "are reported separately.",
    SINGLE_SOURCE: "Only one source was captured; nothing corroborates it.",
    PARTICIPANT_SOURCED: "Evidence comes from a participant describing its own market, "
                         "which is evidence about that participant rather than "
                         "independent evidence about the subject.",
}

#: Reasons that undermine footing rather than qualify it. One is enough for `LOW`.
SEVERE = frozenset({UNRESOLVED_CONFLICT, UNSUPPORTED_STATEMENT, INSUFFICIENT_EVIDENCE,
                    PROVENANCE_UNAVAILABLE, DATA_QUALITY_WARNING})

REASON_CODES = tuple(sorted(REASON_TEXT))

#: Stated so a test can assert it: these verdicts are qualitative judgements about
#: evidence, not statistical probabilities, and nothing here converts them into one.
STATISTICAL_INTERVAL = False


class ConfidenceAssessment:
    """A level, the codes that produced it, and the sentence each code stands for."""

    __slots__ = ("level", "reasons", "explanations")

    def __init__(self, level, reasons):
        self.level = level
        self.reasons = tuple(reasons)
        self.explanations = tuple(REASON_TEXT.get(code, code) for code in self.reasons)

    @property
    def severe_reasons(self):
        return tuple(code for code in self.reasons if code in SEVERE)

    def as_dict(self):
        return {
            "confidence": self.level,
            "reasons": list(self.reasons),
            "explanations": list(self.explanations),
            "severe_reasons": list(self.severe_reasons),
            "statistical_interval": STATISTICAL_INTERVAL,
            "basis": ("Qualitative, derived from evidence quality, completeness, "
                      "freshness, conflict and data quality. Not a probability."),
        }

    def __repr__(self):
        return "ConfidenceAssessment(%s, %d reasons)" % (self.level, len(self.reasons))


def assess(reasons=()):
    """Derive a confidence level from downgrade reason codes.

    Unknown codes are kept rather than dropped: an unrecognised reason is still a reason
    to be less confident, and silently discarding it would be the one failure mode this
    whole module exists to prevent.
    """
    codes = tuple(sorted(set(code for code in reasons if code)))
    if any(code in SEVERE for code in codes):
        return ConfidenceAssessment(LOW, codes)
    if len(codes) >= 2:
        return ConfidenceAssessment(LOW, codes)
    if len(codes) == 1:
        return ConfidenceAssessment(MEDIUM, codes)
    return ConfidenceAssessment(HIGH, codes)


def weakest(levels):
    """The weakest level in a collection. Empty input is `LOW`, not `HIGH`.

    An empty synthesis is not a confident one: there is nothing to be confident about,
    and defaulting to `HIGH` would make the emptiest possible report the most assured.
    """
    present = [level for level in levels if level in LEVELS]
    if not present:
        return LOW
    return min(present, key=LEVEL_ORDER.index)


def combine(assessments, extra_reasons=()):
    """Roll item-level assessments into one set-level verdict.

    The level is the weakest present rather than a re-assessment of the pooled reasons:
    ten separate `MEDIUM` statements do not make a `LOW` report, but one `LOW` statement
    means the report contains something that may not hold.
    """
    assessments = list(assessments)
    reasons = set(extra_reasons)
    for assessment in assessments:
        reasons.update(assessment.reasons)

    if not assessments:
        # Nothing was synthesised. `LOW` with an explicit reason, because an empty report
        # must not read as the most confident one in the system.
        return ConfidenceAssessment(LOW, sorted(reasons) or [INSUFFICIENT_EVIDENCE])

    level = weakest([a.level for a in assessments])
    if extra_reasons:
        level = weakest([level, assess(extra_reasons).level])
    return ConfidenceAssessment(level, sorted(reasons))
