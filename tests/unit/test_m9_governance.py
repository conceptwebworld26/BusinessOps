"""The Milestone 9 owner decisions of 2026-09-10, asserted rather than documented.

Each of these was a gap the M9 architecture review found by executing the code: a
disclosure decision that granted Tier 1 without asking whether the data's class allowed
it, an unclassified aggregate that defaulted to a permissive class, a k-floor a caller
could lower, an external claim that needed no citation, and a re-identification check that
judged every query as though it were the first.

They are tested together because they are one decision: **the boundary fails closed.**
A test here failing means an external query could carry something it should not.

Nothing in this module performs retrieval or builds a query. Those are the M9
implementation; this is the foundation it will stand on.
"""

import unittest
from decimal import Decimal

from bops import evidence
from bops.privacy import aggregation, classes

D = Decimal


def rate(entity_count=40, sensitivity=classes.DERIVED_SAFE, kind=None):
    """A derived rate, the shape most likely to be permitted."""
    return aggregation.AggregateDescriptor(
        "growth rate", D("12.5"), kind or aggregation.RATE, entity_count,
        source_columns=("revenue",), source_sensitivity=sensitivity)


# ==========================================================================
# K-floor: a hard minimum, not a configurable default
# ==========================================================================

class TestKFloorIsAHardMinimum(unittest.TestCase):

    def test_the_default_is_five(self):
        self.assertEqual(aggregation.DEFAULT_K, 5)
        self.assertEqual(aggregation.MINIMUM_K, 5)
        self.assertEqual(aggregation.resolve_k_floor(None), 5)

    def test_five_entities_pass_when_everything_else_passes(self):
        assessment = aggregation.assess_disclosure(
            rate(entity_count=5), query_attributes=("industry",))
        self.assertTrue(assessment.permitted, assessment.reasons)

    def test_four_entities_are_refused(self):
        assessment = aggregation.assess_disclosure(
            rate(entity_count=4), query_attributes=("industry",))
        self.assertFalse(assessment.permitted)
        self.assertIn("aggregation_floor", assessment.failed_checks)

    def test_a_caller_cannot_lower_the_floor(self):
        for requested in (0, 1, 2, 3, 4, -10):
            self.assertEqual(aggregation.resolve_k_floor(requested), 5, requested)

    def test_a_lowered_floor_does_not_admit_a_small_group(self):
        """The floor argument is the obvious bypass; it must not work."""
        for requested in (1, 2, 3, 4):
            assessment = aggregation.assess_disclosure(
                rate(entity_count=4), k_floor=requested,
                query_attributes=("industry",))
            self.assertFalse(assessment.permitted, requested)
            self.assertIn("aggregation_floor", assessment.failed_checks)

    def test_a_non_numeric_floor_falls_back_to_the_minimum(self):
        for requested in ("junk", "", object(), 2.9):
            self.assertGreaterEqual(aggregation.resolve_k_floor(requested), 5)

    def test_the_floor_may_be_raised(self):
        self.assertEqual(aggregation.resolve_k_floor(20), 20)
        assessment = aggregation.assess_disclosure(
            rate(entity_count=10), k_floor=20, query_attributes=("industry",))
        self.assertFalse(assessment.permitted)
        self.assertIn("aggregation_floor", assessment.failed_checks)

    def test_an_unknown_entity_count_is_refused(self):
        assessment = aggregation.assess_disclosure(
            rate(entity_count=None), query_attributes=("industry",))
        self.assertFalse(assessment.permitted)
        self.assertIn("aggregation_floor", assessment.failed_checks)


# ==========================================================================
# Class -> tier composition: one authoritative decision
# ==========================================================================

class TestClassToTierComposition(unittest.TestCase):
    """Passing the four checks is necessary, not sufficient."""

    def assess(self, sensitivity):
        return aggregation.assess_disclosure(
            rate(sensitivity=sensitivity), query_attributes=("industry",))

    def test_public_is_permitted_at_tier_zero(self):
        assessment = self.assess(classes.PUBLIC)
        self.assertTrue(assessment.permitted)
        self.assertEqual(assessment.tier, 0)

    def test_derived_safe_is_permitted_at_tier_one(self):
        assessment = self.assess(classes.DERIVED_SAFE)
        self.assertTrue(assessment.permitted)
        self.assertEqual(assessment.tier, 1)

    def test_internal_is_refused_at_tier_one_though_all_four_checks_pass(self):
        assessment = self.assess(classes.INTERNAL)
        self.assertFalse(assessment.permitted)
        self.assertIsNone(assessment.tier)
        self.assertIn("class_not_permitted_at_tier", assessment.failed_checks)

    def test_restricted_is_refused_at_tier_one(self):
        assessment = self.assess(classes.RESTRICTED)
        self.assertFalse(assessment.permitted)
        self.assertIn("class_not_permitted_at_tier", assessment.failed_checks)

    def test_conditional_is_refused_at_tier_one(self):
        assessment = self.assess(classes.CONDITIONAL)
        self.assertFalse(assessment.permitted)
        self.assertIn("class_not_permitted_at_tier", assessment.failed_checks)

    def test_never_is_refused_before_any_other_check(self):
        assessment = self.assess(classes.NEVER)
        self.assertFalse(assessment.permitted)
        self.assertEqual(assessment.failed_checks, ["never_externalizable"])

    def test_the_decision_agrees_with_the_class_tier_table(self):
        """The two halves must not be able to disagree."""
        for sensitivity in classes.ORDER:
            assessment = self.assess(sensitivity)
            if assessment.permitted:
                self.assertTrue(
                    classes.permitted_at_tier(sensitivity, assessment.tier),
                    "%s permitted at tier %s" % (sensitivity, assessment.tier))

    def test_a_permitted_tier_is_never_below_what_the_class_requires(self):
        for sensitivity in (classes.PUBLIC, classes.DERIVED_SAFE):
            assessment = self.assess(sensitivity)
            self.assertGreaterEqual(assessment.tier,
                                    classes.required_tier(sensitivity))

    def test_every_refusal_states_a_reason(self):
        for sensitivity in (classes.INTERNAL, classes.RESTRICTED, classes.NEVER):
            assessment = self.assess(sensitivity)
            self.assertTrue(assessment.reasons)
            self.assertTrue(assessment.failed_checks)


# ==========================================================================
# Aggregate sensitivity: explicit or safely derived, never assumed
# ==========================================================================

class TestAggregateSensitivity(unittest.TestCase):

    def test_the_constructor_default_is_unresolved(self):
        descriptor = aggregation.AggregateDescriptor("x", D("1"), aggregation.RATE, 40)
        self.assertEqual(descriptor.source_sensitivity, aggregation.UNRESOLVED)
        self.assertFalse(descriptor.sensitivity_resolved)

    def test_the_default_is_not_derived_safe(self):
        """The old default was permissive; that is the regression this guards."""
        descriptor = aggregation.AggregateDescriptor("x", D("1"), aggregation.RATE, 40)
        self.assertNotEqual(descriptor.source_sensitivity, classes.DERIVED_SAFE)

    def test_an_unclassified_aggregate_is_refused(self):
        descriptor = aggregation.AggregateDescriptor("x", D("1"), aggregation.RATE, 40)
        assessment = aggregation.assess_disclosure(
            descriptor, query_attributes=("industry",))
        self.assertFalse(assessment.permitted)
        self.assertIn("sensitivity_unresolved", assessment.failed_checks)

    def test_unresolved_is_refused_before_the_other_checks_can_pass_it(self):
        """Even a perfect aggregate is refused while its sensitivity is unknown."""
        descriptor = aggregation.AggregateDescriptor(
            "x", D("1"), aggregation.RATE, 1000)
        assessment = aggregation.assess_disclosure(descriptor, query_attributes=())
        self.assertFalse(assessment.permitted)

    def test_from_fields_takes_the_most_sensitive_source(self):
        descriptor = aggregation.AggregateDescriptor.from_fields(
            "x", D("1"), aggregation.RATE, 40,
            [classes.PUBLIC, classes.DERIVED_SAFE, classes.RESTRICTED])
        self.assertEqual(descriptor.source_sensitivity, classes.RESTRICTED)

    def test_from_fields_with_no_classification_is_not_treated_as_safe(self):
        descriptor = aggregation.AggregateDescriptor.from_fields(
            "x", D("1"), aggregation.RATE, 40, [])
        self.assertEqual(descriptor.source_sensitivity, classes.DEFAULT_CLASS)
        self.assertEqual(classes.DEFAULT_CLASS, classes.INTERNAL)

    def test_from_fields_carrying_a_never_field_can_never_be_disclosed(self):
        descriptor = aggregation.AggregateDescriptor.from_fields(
            "x", D("1"), aggregation.RATE, 40, [classes.PUBLIC, classes.NEVER])
        assessment = aggregation.assess_disclosure(descriptor)
        self.assertFalse(assessment.permitted)
        self.assertIn("never_externalizable", assessment.failed_checks)

    def test_the_shipped_helpers_still_classify_explicitly(self):
        for descriptor in (
                aggregation.rate_descriptor("churn", 8, 100, entity_count=40),
                aggregation.banded_amount_descriptor("revenue", D("3467850.16"),
                                                     entity_count=40)):
            self.assertTrue(descriptor.sensitivity_resolved, descriptor.label)


# ==========================================================================
# Cross-query re-identification, scoped to the active operation
# ==========================================================================

class TestCrossQueryAccumulation(unittest.TestCase):

    def operation(self, *queries):
        """Run a sequence, recording only what was permitted. Returns (verdicts, acc)."""
        accumulator = aggregation.DisclosureAccumulator("test-operation")
        verdicts = []
        for attributes in queries:
            assessment = aggregation.assess_disclosure(
                rate(), query_attributes=attributes, accumulated=accumulator)
            verdicts.append(assessment.permitted)
            if assessment.permitted:
                accumulator.record(attributes)
        return verdicts, accumulator

    def test_a_single_narrow_query_passes_alone(self):
        assessment = aggregation.assess_disclosure(
            rate(), query_attributes=("product_category",))
        self.assertTrue(assessment.permitted)

    def test_a_sequence_of_individually_safe_queries_becomes_unsafe(self):
        """The requirement: A passes, B passes, C passes, but A+B+C+D does not."""
        verdicts, accumulator = self.operation(
            ("industry",), ("region",), ("size_band",), ("product_category",))
        self.assertEqual(verdicts, [True, True, True, False])
        self.assertEqual(sorted(accumulator.attributes),
                         ["industry", "region", "size_band"])

    def test_the_refusal_names_the_accumulated_state(self):
        _verdicts, accumulator = self.operation(
            ("industry",), ("region",), ("size_band",))
        assessment = aggregation.assess_disclosure(
            rate(), query_attributes=("product_category",), accumulated=accumulator)
        self.assertFalse(assessment.permitted)
        joined = " ".join(assessment.reasons)
        self.assertIn("already disclosed in this research operation", joined)

    def test_without_an_accumulator_each_query_is_judged_alone(self):
        """Accumulation is opt-in per operation; absent one, behaviour is unchanged."""
        for _ in range(5):
            assessment = aggregation.assess_disclosure(
                rate(), query_attributes=("product_category",))
            self.assertTrue(assessment.permitted)

    def test_a_refused_query_records_nothing(self):
        accumulator = aggregation.DisclosureAccumulator("op")
        aggregation.assess_disclosure(
            rate(entity_count=2), query_attributes=("industry", "region"),
            accumulated=accumulator)
        self.assertEqual(accumulator.attributes, set())
        self.assertEqual(accumulator.disclosures, 0)

    def test_only_narrowing_attributes_accumulate(self):
        accumulator = aggregation.DisclosureAccumulator("op")
        accumulator.record(("industry", "period", "currency"))
        self.assertEqual(sorted(accumulator.attributes), ["industry"])

    def test_reset_ends_the_operation(self):
        _verdicts, accumulator = self.operation(
            ("industry",), ("region",), ("size_band",))
        accumulator.reset()
        self.assertEqual(accumulator.attributes, set())
        self.assertEqual(accumulator.disclosures, 0)
        assessment = aggregation.assess_disclosure(
            rate(), query_attributes=("product_category",), accumulated=accumulator)
        self.assertTrue(assessment.permitted)

    def test_the_accumulator_holds_no_values_or_query_text(self):
        """It is operation state, not a profile of the user or their business."""
        _verdicts, accumulator = self.operation(("industry",), ("region",))
        record = accumulator.as_dict()
        self.assertEqual(sorted(record), ["attributes", "disclosures", "operation"])
        for attribute in record["attributes"]:
            self.assertIn(attribute, aggregation.NARROWING_ATTRIBUTES)

    def test_would_be_risky_assesses_without_recording(self):
        _verdicts, accumulator = self.operation(
            ("industry",), ("region",), ("size_band",))
        before = set(accumulator.attributes)
        verdict = accumulator.would_be_risky(("product_category",))
        self.assertTrue(verdict["risky"])
        self.assertEqual(accumulator.attributes, before)

    def test_the_sequence_is_deterministic(self):
        first, _a = self.operation(("industry",), ("region",), ("size_band",),
                                   ("product_category",))
        second, _b = self.operation(("industry",), ("region",), ("size_band",),
                                    ("product_category",))
        self.assertEqual(first, second)

    def test_order_does_not_change_the_final_state(self):
        _v1, a1 = self.operation(("industry",), ("region",))
        _v2, a2 = self.operation(("region",), ("industry",))
        self.assertEqual(a1.attributes, a2.attributes)


# ==========================================================================
# Class-3 provenance: an uncited external claim cannot be built
# ==========================================================================

class TestExternalClaimProvenance(unittest.TestCase):

    def cited(self, **overrides):
        fields = {"source": "Office for National Statistics",
                  "citation": "https://ons.gov.uk/example",
                  "source_date": "2026-02-01",
                  "source_tier": "A"}
        fields.update(overrides)
        return evidence.Claim("Industry churn is 5-7%.", evidence.EXTERNAL_SOURCED,
                              **fields)

    def test_a_bare_external_claim_cannot_be_constructed(self):
        with self.assertRaises(evidence.LedgerError) as caught:
            evidence.Claim("Industry churn benchmark is 5-7%.",
                           evidence.EXTERNAL_SOURCED)
        self.assertIn("citation", str(caught.exception))

    def test_each_required_field_is_individually_required(self):
        for field in evidence.EXTERNAL_FIELDS:
            with self.assertRaises(evidence.LedgerError, msg=field):
                self.cited(**{field: None})

    def test_a_fully_cited_claim_is_accepted(self):
        claim = self.cited()
        self.assertEqual(claim.provenance_class, evidence.EXTERNAL_SOURCED)
        self.assertEqual(claim.label, "SOURCED")

    def test_tier_d_is_excluded_outright(self):
        with self.assertRaises(evidence.LedgerError) as caught:
            self.cited(source_tier="D")
        self.assertIn("excluded", str(caught.exception))

    def test_an_unknown_tier_is_refused(self):
        for tier in ("E", "1", "gold", ""):
            with self.assertRaises(evidence.LedgerError, msg=tier):
                self.cited(source_tier=tier)

    def test_tiers_a_b_and_c_are_accepted(self):
        for tier in evidence.SOURCE_TIERS:
            self.assertEqual(self.cited(source_tier=tier).provenance_class,
                             evidence.EXTERNAL_SOURCED)

    def test_provenance_survives_into_the_record(self):
        record = self.cited().as_dict()
        for field in ("source", "citation", "source_date", "source_tier"):
            self.assertIn(field, record)

    def test_an_external_claim_stays_distinguishable_from_internal_fact(self):
        external = self.cited()
        internal = evidence.Claim("Revenue was 100.", evidence.USER_DATA,
                                  source={"source_name": "sales.csv"})
        self.assertEqual(external.label, "SOURCED")
        self.assertEqual(internal.label, "FACT")
        self.assertNotEqual(external.provenance_class, internal.provenance_class)

    def test_the_other_classes_are_unchanged(self):
        """Tightening class 3 must not have altered classes 1, 4 or 7."""
        with self.assertRaises(evidence.LedgerError):
            evidence.Claim("x", evidence.CALCULATED)
        with self.assertRaises(evidence.LedgerError):
            evidence.Claim("x", evidence.USER_DATA)
        with self.assertRaises(evidence.LedgerError):
            evidence.Claim("x", evidence.RECOMMENDATION)
        self.assertTrue(evidence.Claim("x", evidence.INTERPRETATION))
        self.assertTrue(evidence.Claim("x", evidence.ASSUMPTION))

    def test_an_uncited_claim_cannot_reach_a_ledger(self):
        ledger = evidence.Ledger()
        with self.assertRaises(evidence.LedgerError):
            ledger.record("Market is worth 4bn.", evidence.EXTERNAL_SOURCED)
        self.assertEqual(len(ledger), 0)


if __name__ == "__main__":
    unittest.main()
