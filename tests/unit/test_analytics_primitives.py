"""The deterministic analytics primitives (Milestone 6).

Every primitive is tested for the normal case, the edge case, empty input, ties where a
ranking is involved, a zero denominator, insufficient periods, and — because the whole
layer depends on it — deterministic ordering across repeated runs.
"""

import json
import os
import shutil
import tempfile
import unittest
from decimal import Decimal

from bops import mapping as mapping_mod
from bops import privacy
from bops.analytics import (cohorts, concentration, contract, mix, presentation,
                           segmentation)
from bops.ingest import canonical as canonical_mod
from bops.ingest import readers

from fixtures import build_analytics_fixtures as build


class AnalyticsCase(unittest.TestCase):
    """Fixtures are built once; every case reads them, none modifies them."""

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.mkdtemp(prefix="bops-analytics-")
        cls.paths = {
            "full": build.full(cls.directory),
            "ties": build.tied_segments(cls.directory),
            "single_period": build.single_period(cls.directory),
            "two_periods": build.two_periods(cls.directory),
            "empty": build.empty(cls.directory),
            "no_cost": build.without(cls.directory, "CostOfGoods"),
            "no_product": build.without(cls.directory, "Product"),
            "flat": build.flat_revenue(cls.directory),
            "zero_revenue": build.zero_revenue(cls.directory),
            "single_customer": build.single_customer(cls.directory),
        }

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.directory, ignore_errors=True)

    def load(self, key):
        dataset = readers.read(self.paths[key])
        return dataset, mapping_mod.infer(dataset)

    def policy(self, key, mode=presentation.LOCAL):
        dataset = readers.read(self.paths[key])
        return presentation.policy_for(canonical_mod.build(dataset), mode)


# ==========================================================================
# segmentation
# ==========================================================================

class TestSegment(AnalyticsCase):

    def test_groups_and_shares_sum_to_one_hundred(self):
        dataset, semantic_map = self.load("full")
        segments = segmentation.segment(dataset, semantic_map, mapping_mod.PRODUCT)
        self.assertEqual(len(segments), 4)
        total = sum(s.share_pct for s in segments)
        self.assertEqual(total.quantize(Decimal("0.0001")), Decimal("100.0000"))

    def test_totals_agree_with_the_grand_total(self):
        dataset, semantic_map = self.load("full")
        segments = segmentation.segment(dataset, semantic_map, mapping_mod.PRODUCT)
        by_region = segmentation.segment(dataset, semantic_map, mapping_mod.REGION)
        self.assertEqual(segmentation.total_of(segments),
                         segmentation.total_of(by_region))

    def test_unmapped_dimension_returns_empty_not_zero(self):
        dataset, semantic_map = self.load("no_product")
        self.assertEqual(
            segmentation.segment(dataset, semantic_map, mapping_mod.PRODUCT), [])

    def test_empty_dataset_produces_no_segments(self):
        dataset = readers.read(self.paths["empty"])
        semantic_map = mapping_mod.infer(dataset)
        self.assertEqual(
            segmentation.segment(dataset, semantic_map, mapping_mod.PRODUCT), [])

    def test_ties_share_a_rank_and_order_by_key(self):
        dataset, semantic_map = self.load("ties")
        segments = segmentation.segment(dataset, semantic_map, mapping_mod.PRODUCT)
        self.assertEqual([s.key for s in segments], ["Alpha", "Bravo", "Charlie"])
        self.assertEqual([s.rank for s in segments], [1, 1, 1])

    def test_ordering_is_deterministic_across_runs(self):
        dataset, semantic_map = self.load("full")
        first = [s.key for s in
                 segmentation.segment(dataset, semantic_map, mapping_mod.PRODUCT)]
        for _attempt in range(3):
            again = [s.key for s in
                     segmentation.segment(dataset, semantic_map, mapping_mod.PRODUCT)]
            self.assertEqual(first, again)

    def test_zero_total_leaves_share_undefined_rather_than_zero(self):
        dataset, semantic_map = self.load("zero_revenue")
        segments = segmentation.segment(dataset, semantic_map, mapping_mod.PRODUCT)
        self.assertTrue(segments)
        for item in segments:
            self.assertIsNone(item.share_pct)


class TestPeriodSplitting(AnalyticsCase):

    def test_halves_split_evenly_and_cover_every_period(self):
        dataset, semantic_map = self.load("full")
        by_period = segmentation.segment_by_period(dataset, semantic_map,
                                                   mapping_mod.PRODUCT)
        earlier, later = segmentation.halves(by_period)
        self.assertEqual(len(earlier) + len(later), len(by_period))
        self.assertEqual(set(earlier) & set(later), set())

    def test_single_period_yields_no_comparison(self):
        dataset, semantic_map = self.load("single_period")
        by_period = segmentation.segment_by_period(dataset, semantic_map,
                                                   mapping_mod.PRODUCT)
        self.assertEqual(segmentation.halves(by_period), ([], []))

    def test_collapse_sums_the_named_periods_only(self):
        dataset, semantic_map = self.load("full")
        by_period = segmentation.segment_by_period(dataset, semantic_map,
                                                   mapping_mod.PRODUCT)
        earlier, later = segmentation.halves(by_period)
        whole = segmentation.collapse(by_period, earlier + later)
        parts = segmentation.collapse(by_period, earlier)
        rest = segmentation.collapse(by_period, later)
        for key in whole:
            self.assertEqual(whole[key], parts.get(key, Decimal("0"))
                             + rest.get(key, Decimal("0")))


class TestMovements(AnalyticsCase):

    def setUp(self):
        dataset, semantic_map = self.load("full")
        by_period = segmentation.segment_by_period(dataset, semantic_map,
                                                   mapping_mod.PRODUCT)
        earlier, later = segmentation.halves(by_period)
        self.earlier = segmentation.collapse(by_period, earlier)
        self.later = segmentation.collapse(by_period, later)

    def test_ordering_runs_from_largest_decline_to_largest_increase(self):
        moves = segmentation.movements(self.earlier, self.later)
        changes = [m.change for m in moves]
        self.assertEqual(changes, sorted(changes))

    def test_a_member_present_in_only_one_window_is_still_reported(self):
        moves = segmentation.movements({"Gone": Decimal("500")}, {"New": Decimal("300")})
        keys = {m.key: m for m in moves}
        self.assertEqual(keys["Gone"].later, Decimal("0"))
        self.assertEqual(keys["New"].earlier, Decimal("0"))
        self.assertEqual(keys["Gone"].direction, "decrease")

    def test_zero_base_leaves_percentage_undefined(self):
        moves = segmentation.movements({}, {"New": Decimal("300")})
        self.assertIsNone(moves[0].change_pct)
        self.assertEqual(moves[0].change, Decimal("300"))

    def test_empty_inputs_produce_no_movements(self):
        self.assertEqual(segmentation.movements({}, {}), [])

    def test_ordering_is_deterministic_with_equal_changes(self):
        earlier = {"B": Decimal("100"), "A": Decimal("100"), "C": Decimal("100")}
        later = {"B": Decimal("200"), "A": Decimal("200"), "C": Decimal("200")}
        keys = [m.key for m in segmentation.movements(earlier, later)]
        self.assertEqual(keys, ["A", "B", "C"])


class TestMargins(AnalyticsCase):

    def test_margin_by_dimension_matches_a_hand_calculation(self):
        dataset, semantic_map = self.load("full")
        rows = segmentation.margin_by_dimension(dataset, semantic_map,
                                                mapping_mod.PRODUCT)
        self.assertTrue(rows)
        for row in rows:
            # The fixture sets cost at exactly 60% of revenue on every line.
            self.assertEqual(row["margin_pct"].quantize(Decimal("0.01")),
                             Decimal("40.00"))

    def test_no_cost_column_yields_no_margin_rows(self):
        dataset, semantic_map = self.load("no_cost")
        self.assertEqual(
            segmentation.margin_by_dimension(dataset, semantic_map,
                                             mapping_mod.PRODUCT), [])

    def test_margin_by_period_omits_periods_with_zero_revenue(self):
        dataset, semantic_map = self.load("zero_revenue")
        self.assertEqual(segmentation.margin_by_period(dataset, semantic_map), [])

    def test_series_halves_needs_four_periods(self):
        series = [("2025-01", Decimal("10")), ("2025-02", Decimal("20"))]
        self.assertEqual(segmentation.series_halves(series), (None, None))

    def test_first_period_seen_is_the_earliest_record(self):
        dataset, semantic_map = self.load("full")
        first = segmentation.first_period_seen(dataset, semantic_map,
                                               mapping_mod.PRODUCT)
        self.assertEqual(set(first.values()), {"2025-01"})


# ==========================================================================
# concentration
# ==========================================================================

class TestConcentration(AnalyticsCase):

    def segments(self, key="full", role=mapping_mod.PRODUCT):
        dataset, semantic_map = self.load(key)
        return segmentation.segment(dataset, semantic_map, role)

    def test_top_n_share_is_bounded_and_cumulative(self):
        segments = self.segments()
        one = concentration.top_n(segments, 1)
        allof = concentration.top_n(segments, len(segments))
        self.assertLess(one["share_pct"], allof["share_pct"])
        self.assertEqual(allof["share_pct"].quantize(Decimal("0.0001")),
                         Decimal("100.0000"))

    def test_top_n_beyond_the_member_count_returns_every_member(self):
        segments = self.segments()
        summary = concentration.top_n(segments, 99)
        self.assertEqual(summary["count"], len(segments))

    def test_empty_input_has_no_concentration(self):
        self.assertIsNone(concentration.hhi([]))
        self.assertIsNone(concentration.members_for_share([]))
        self.assertEqual(concentration.top_n([], 3)["count"], 0)

    def test_zero_total_leaves_every_measure_undefined(self):
        segments = self.segments("zero_revenue")
        self.assertIsNone(concentration.hhi(segments))
        self.assertIsNone(concentration.members_for_share(segments))

    def test_single_member_is_maximum_concentration(self):
        segments = self.segments("ties", role=mapping_mod.CUSTOMER)
        self.assertEqual(len(segments), 1)
        self.assertEqual(concentration.hhi(segments).quantize(Decimal("1")),
                         Decimal("10000"))
        self.assertEqual(concentration.members_for_share(segments), 1)

    def test_ratios_beyond_the_member_count_are_none_not_one_hundred(self):
        segments = self.segments()
        record = concentration.profile(segments, ratios=(1, 3, 5, 10))
        self.assertIsNotNone(record["cr"][1])
        self.assertIsNone(record["cr"][10])

    def test_profile_is_deterministic(self):
        segments = self.segments()
        first = concentration.profile(segments)
        second = concentration.profile(segments)
        self.assertEqual(first["hhi"], second["hhi"])
        self.assertEqual(first["cr"], second["cr"])


# ==========================================================================
# mix
# ==========================================================================

class TestMix(AnalyticsCase):

    def windows(self, key="full"):
        dataset, semantic_map = self.load(key)
        by_period = segmentation.segment_by_period(dataset, semantic_map,
                                                   mapping_mod.PRODUCT)
        earlier, later = segmentation.halves(by_period)
        return (segmentation.collapse(by_period, earlier),
                segmentation.collapse(by_period, later))

    def test_shares_sum_to_one_hundred(self):
        earlier, _later = self.windows()
        total = sum(mix.shares(earlier).values())
        self.assertEqual(total.quantize(Decimal("0.0001")), Decimal("100.0000"))

    def test_shift_is_measured_in_points_and_nets_to_zero(self):
        earlier, later = self.windows()
        shifts = mix.mix_shift(earlier, later)
        net = sum(s.points_change for s in shifts)
        self.assertEqual(net.quantize(Decimal("0.0001")), Decimal("0.0000"))

    def test_the_growing_line_gains_share(self):
        earlier, later = self.windows()
        shifts = {s.key: s for s in mix.mix_shift(earlier, later)}
        self.assertGreater(shifts["Widget"].points_change, Decimal("0"))
        self.assertEqual(shifts["Widget"].direction, "gaining")

    def test_empty_windows_produce_no_shift(self):
        self.assertEqual(mix.mix_shift({}, {}), [])

    def test_zero_totals_leave_shares_undefined(self):
        earlier, later = self.windows("zero_revenue")
        for item in mix.mix_shift(earlier, later):
            self.assertIsNone(item.points_change)

    def test_contribution_shares_are_undefined_when_the_net_change_is_zero(self):
        earlier, later = self.windows("flat")
        rows, net = mix.contribution_to_change(earlier, later)
        self.assertEqual(net, Decimal("0"))
        for row in rows:
            self.assertIsNone(row["share_of_change_pct"])

    def test_contribution_shares_sum_to_one_hundred_when_the_net_change_is_not_zero(self):
        earlier, later = self.windows()
        rows, net = mix.contribution_to_change(earlier, later)
        self.assertNotEqual(net, Decimal("0"))
        total = sum(r["share_of_change_pct"] for r in rows)
        self.assertEqual(total.quantize(Decimal("0.0001")), Decimal("100.0000"))

    def test_contribution_ordering_is_deterministic(self):
        earlier, later = self.windows()
        first = [r["label"] for r in mix.contribution_to_change(earlier, later)[0]]
        second = [r["label"] for r in mix.contribution_to_change(earlier, later)[0]]
        self.assertEqual(first, second)


# ==========================================================================
# cohorts
# ==========================================================================

class TestCohorts(AnalyticsCase):

    def test_cohorts_are_built_from_first_appearance(self):
        dataset, semantic_map = self.load("full")
        built = cohorts.build(dataset, semantic_map)
        self.assertEqual(built["status"], contract.AVAILABLE)
        self.assertTrue(built["cohorts"])
        for cohort in built["cohorts"]:
            opening = cohort["entries"][0]
            self.assertEqual(opening["offset"], 0)
            self.assertEqual(opening["active"], cohort["size"])
            self.assertEqual(opening["retention_pct"].quantize(Decimal("0.01")),
                             Decimal("100.00"))

    def test_cohort_sizes_account_for_every_customer_exactly_once(self):
        dataset, semantic_map = self.load("full")
        built = cohorts.build(dataset, semantic_map)
        from bops.kpi import primitives as p
        total = sum(size for _period, size in cohorts.cohort_sizes(built))
        self.assertEqual(total,
                         p.distinct_count(dataset, semantic_map, mapping_mod.CUSTOMER))

    def test_insufficient_history_is_reported_not_approximated(self):
        dataset, semantic_map = self.load("two_periods")
        built = cohorts.build(dataset, semantic_map, minimum_periods=3)
        self.assertEqual(built["status"], contract.INSUFFICIENT_DATA)
        self.assertEqual(built["cohorts"], [])
        self.assertIn("periods", built["reason"])

    def test_unmapped_customer_is_unavailable_not_empty(self):
        dataset = readers.read(build.without(self.directory, "Customer",
                                             name="cohort_no_customer.csv"))
        semantic_map = mapping_mod.infer(dataset)
        built = cohorts.build(dataset, semantic_map)
        self.assertEqual(built["status"], contract.UNAVAILABLE)
        self.assertIn("customer", built["reason"])

    def test_the_window_assumption_travels_with_the_result(self):
        dataset, semantic_map = self.load("full")
        built = cohorts.build(dataset, semantic_map)
        self.assertIn(cohorts.WINDOW_ASSUMPTION, built["assumptions"])

    def test_retention_curve_averages_only_over_cohorts_that_reached_the_offset(self):
        dataset, semantic_map = self.load("full")
        curve = cohorts.retention_curve(cohorts.build(dataset, semantic_map))
        self.assertTrue(curve)
        self.assertEqual(curve[0]["offset"], 0)
        counts = [row["cohorts"] for row in curve]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_retention_curve_of_an_unavailable_result_is_empty(self):
        self.assertEqual(cohorts.retention_curve({"status": contract.UNAVAILABLE}), [])


# ==========================================================================
# presentation policy
# ==========================================================================

class TestLabelPolicy(AnalyticsCase):

    def test_local_presentation_shows_labels_verbatim(self):
        policy = self.policy("full", presentation.LOCAL)
        label, redacted = policy.label("Customer", "Acme Ltd",
                                       role=mapping_mod.CUSTOMER, rank=1)
        self.assertEqual(label, "Acme Ltd")
        self.assertFalse(redacted)

    def test_shareable_presentation_pseudonymises_identifying_columns(self):
        policy = self.policy("full", presentation.SHAREABLE)
        label, redacted = policy.label("Customer", "Acme Ltd",
                                       role=mapping_mod.CUSTOMER, rank=3)
        self.assertTrue(redacted)
        self.assertNotIn("Acme", label)
        self.assertEqual(label, "Customer #3")

    def test_shareable_presentation_leaves_non_identifying_columns_alone(self):
        policy = self.policy("full", presentation.SHAREABLE)
        label, redacted = policy.label("Region", "North", role=mapping_mod.REGION, rank=1)
        self.assertEqual(label, "North")
        self.assertFalse(redacted)

    def test_pseudonyms_are_stable_for_the_same_value(self):
        policy = self.policy("full", presentation.SHAREABLE)
        first, _ = policy.label("Customer", "Acme Ltd", rank=1)
        second, _ = policy.label("Customer", "Acme Ltd", rank=9)
        self.assertEqual(first, second)

    def test_classification_is_read_not_redefined(self):
        policy = self.policy("full")
        self.assertEqual(policy.sensitivity_of("Customer"), privacy.NEVER)
        self.assertFalse(policy.externalizable("Customer"))
        self.assertTrue(policy.externalizable("Region"))

    def test_unknown_column_defaults_to_the_conservative_class(self):
        policy = self.policy("full")
        self.assertEqual(policy.sensitivity_of("NoSuchColumn"), privacy.DEFAULT_CLASS)

    def test_small_groups_are_banded_in_every_mode(self):
        for mode in (presentation.LOCAL, presentation.SHAREABLE):
            policy = self.policy("full", mode)
            value, banded = policy.entity_count(2)
            self.assertTrue(banded)
            self.assertEqual(value, "1-9")
            value, banded = policy.entity_count(40)
            self.assertFalse(banded)
            self.assertEqual(value, 40)

    def test_an_unknown_presentation_mode_is_refused(self):
        with self.assertRaises(ValueError):
            presentation.LabelPolicy(presentation="public-broadcast")

    def test_restricted_columns_are_reported_for_export(self):
        policy = self.policy("full")
        restricted = presentation.restricted_columns(
            policy, ["Customer", "Region", "Salesperson"])
        self.assertIn("Customer", restricted)
        self.assertNotIn("Region", restricted)
        self.assertIn("must be pseudonymised", presentation.export_caveat(restricted))


# ==========================================================================
# the output contract
# ==========================================================================

class TestAnalysisContract(unittest.TestCase):

    def finding(self, **kwargs):
        defaults = {"analysis_id": "sales.test", "analysis_type": "sales",
                    "finding_type": contract.CALCULATION, "statement": "A statement.",
                    "basis": "a primitive"}
        defaults.update(kwargs)
        return contract.AnalysisFinding(**defaults)

    def test_unknown_finding_type_is_refused(self):
        with self.assertRaises(contract.AnalysisError):
            self.finding(finding_type="VIBE")

    def test_a_calculation_must_name_its_basis(self):
        with self.assertRaises(contract.AnalysisError):
            self.finding(basis=None)

    def test_the_engine_may_not_emit_judgement(self):
        analysis = contract.AnalysisSet("sales")
        with self.assertRaises(contract.AnalysisError):
            analysis.add(self.finding(finding_type=contract.INTERPRETATION, basis=None))

    def test_unknown_status_is_refused(self):
        with self.assertRaises(contract.AnalysisError):
            contract.AnalysisSet("sales", status="probably_fine")

    def test_a_global_caveat_attaches_to_past_and_future_findings(self):
        analysis = contract.AnalysisSet("sales")
        first = analysis.add(self.finding())
        analysis.add_caveat("Data quality: duplicates present")
        second = analysis.add(self.finding())
        self.assertIn("Data quality: duplicates present", first.caveats)
        self.assertIn("Data quality: duplicates present", second.caveats)

    def test_findings_map_onto_the_ledger_classes(self):
        self.assertEqual(contract.EVIDENCE_CLASS[contract.FACT], 1)
        self.assertEqual(contract.EVIDENCE_CLASS[contract.CALCULATION], 4)
        self.assertEqual(contract.EVIDENCE_CLASS[contract.INTERPRETATION], 5)
        self.assertEqual(contract.EVIDENCE_CLASS[contract.RECOMMENDATION], 7)

    def test_a_calculation_becomes_a_ledger_claim_carrying_its_formula(self):
        claim = self.finding().as_claim()
        self.assertEqual(claim.provenance_class, 4)
        self.assertEqual(claim.formula, "a primitive")
        self.assertEqual(claim.label, "FACT")

    def test_a_set_is_json_serialisable(self):
        analysis = contract.AnalysisSet("sales", currency="GBP")
        analysis.add(self.finding(observed=Decimal("1.23"),
                                  inputs={"total": Decimal("4.56")}))
        analysis.limit("unmapped_role", "region", "No region column.")
        json.dumps(analysis.as_dict())

    def test_limitations_are_counted_in_the_summary(self):
        analysis = contract.AnalysisSet("sales")
        analysis.limit("unmapped_role", "region", "No region column.")
        self.assertEqual(analysis.summary()["limitations"], 1)
        self.assertEqual(analysis.summary()["findings"], 0)


if __name__ == "__main__":
    unittest.main()
