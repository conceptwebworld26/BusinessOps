"""How an analytical result may be shown, given what the underlying fields are.

Milestone 3 classified every field's sensitivity; Milestone 4 established privacy-safe
reporting. This module is the join between those and the analytics layer. It does **not**
introduce a second classification — it reads the one the canonical dataset already carries.

Two presentation modes, because the honest answer differs by destination:

    LOCAL       the analysis stays on this machine, for the person whose data it is.
                Entity labels are shown, because "your third-largest customer" is useless
                to the owner of the business who wants to phone them.
    SHAREABLE   the result may be read by someone outside the business. Labels drawn from
                fields that identify an individual person or account are replaced with a
                stable, rank-based pseudonym.

Two rules hold in **both** modes, because they are not presentation choices:

  * an individual transaction row is never emitted — the primitives aggregate, always;
  * a group smaller than the k-anonymity floor reports a banded count, never an exact one,
    since "1 customer" plus a revenue figure is a single customer's revenue.

Nothing here weakens a sensitivity classification. A field classified `never` is still
never externalizable; this module only decides how its *label* is rendered.
"""

from .. import privacy
from ..privacy import aggregation as privacy_aggregation

#: The k-anonymity floor Milestone 3 established. Re-exported, never redefined.
DEFAULT_K = privacy_aggregation.DEFAULT_K

LOCAL = "local"
SHAREABLE = "shareable"

MODES = (LOCAL, SHAREABLE)

#: Classes whose values name an individual person, customer or transaction. In a shareable
#: result these are pseudonymised; the classification itself is unchanged.
IDENTIFYING = frozenset({privacy.RESTRICTED, privacy.NEVER})


class LabelPolicy:
    """Decides, per column, whether a dimension value may be shown as itself."""

    __slots__ = ("sensitivity_map", "presentation", "k_floor", "_counters")

    def __init__(self, sensitivity_map=None, presentation=LOCAL,
                 k_floor=DEFAULT_K):
        if presentation not in MODES:
            raise ValueError("unknown presentation mode %r" % (presentation,))
        self.sensitivity_map = sensitivity_map
        self.presentation = presentation
        self.k_floor = k_floor
        self._counters = {}

    # -- classification lookup ---------------------------------------------

    def sensitivity_of(self, column):
        """The recorded class for a column, or the conservative default."""
        if column is None:
            return privacy.DEFAULT_CLASS
        if self.sensitivity_map is None:
            return privacy.DEFAULT_CLASS
        return self.sensitivity_map.sensitivity_of(column)

    def identifies_individuals(self, column):
        return self.sensitivity_of(column) in IDENTIFYING

    def exact_permitted(self, column):
        """Whether a value from this column may appear verbatim in the output."""
        if self.presentation == LOCAL:
            return True
        return not self.identifies_individuals(column)

    def externalizable(self, column):
        """Unchanged from Milestone 3 — recorded here so a caller need not re-derive it."""
        return privacy.is_externalizable(self.sensitivity_of(column))

    # -- rendering ----------------------------------------------------------

    def label(self, column, value, role=None, rank=None):
        """Return (label, redacted). Deterministic: the same value maps to the same label.

        Pseudonyms are assigned by first appearance in the caller's ordering, which is
        itself deterministic, so two runs over the same data produce the same labels.
        """
        text = "" if value is None else str(value)
        if self.exact_permitted(column):
            return text, False
        prefix = (role or column or "entity").replace("_", " ").strip().title()
        bucket = self._counters.setdefault(column, {})
        if text not in bucket:
            bucket[text] = rank if rank is not None else len(bucket) + 1
        return "%s #%d" % (prefix, bucket[text]), True

    def entity_count(self, count):
        """Return (value, banded). Small groups are banded in every mode."""
        if count is None:
            return None, False
        if count < self.k_floor:
            return privacy.band_count(count), True
        return count, False

    def small_group(self, count):
        return count is not None and count < self.k_floor

    def describe(self):
        return {"presentation": self.presentation, "k_anonymity_floor": self.k_floor}


def policy_for(canonical=None, presentation=LOCAL, config=None):
    """Build the policy for one analysis from the canonical dataset's classification."""
    sensitivity_map = None
    if canonical is not None:
        try:
            sensitivity_map = canonical.sensitivity_map()
        except Exception:                      # a dataset without classification is not fatal
            sensitivity_map = None
    k_floor = DEFAULT_K
    if config is not None:
        k_floor = int(config.get("research.disclosure.k_anonymity_floor",
                                 DEFAULT_K))
    return LabelPolicy(sensitivity_map, presentation=presentation, k_floor=k_floor)


def restricted_columns(policy, columns):
    """Columns whose values identify individuals, so an export must pseudonymise them."""
    return [c for c in columns if c and policy.identifies_individuals(c)]


def export_caveat(columns):
    """The caveat that must travel with any result built from identifying fields."""
    if not columns:
        return None
    return ("Findings below are grouped by %s, which identif%s individuals; this result is "
            "for local use and must be pseudonymised before it is shared outside the "
            "business." % (", ".join(sorted(columns)),
                           "ies" if len(columns) == 1 else "y"))
