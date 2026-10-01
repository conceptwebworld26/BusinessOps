"""M10.1 - conflicts, materiality, confidence, limitations and comparability.

Covers matrix sections 5-9 and 53-60. The theme running through all of them is that the
synthesis layer reports what the layers below decided, and that where it cannot decide, it
says so rather than picking.
"""

import os
import sys
import unittest
from decimal import Decimal

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for path in (os.path.join(REPO_ROOT, "lib", "python"),
             os.path.join(REPO_ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bops import config as config_mod                      # noqa: E402
from bops import materiality as materiality_mod            # noqa: E402
from bops import synthesis as S                            # noqa: E402
from bops.analytics import contract as analytics_contract  # noqa: E402
from bops.research import evidence_set as evidence_mod     # noqa: E402
from bops.research import sources as sources_mod           # noqa: E402

from fixtures import build_synthesis_fixtures as build      # noqa: E402
from fixtures.build_synthesis_fixtures import (             # noqa: E402
    TEST_DATASET as DATASET, dataset_ref, demo_evidence, evidence_set_with, new_set,
)


def positions(**overrides):
    """Two positions identical on every dimension but the value.

    Both sides carry every dimension, so overriding one on the right genuinely creates a
    difference. A dimension present on one side only is *unstated* on the other, which is
    a different case and is covered by the comparability tests.
    """
    base = [
        {"evidence_id": "ev-a", "value": 310.0, "unit": "USD bn",
         "source": "DEMO A", "source_tier": "C", "definition": "manufacture only",
         "scope": "global", "period": "2025", "methodology": "top-down"},
        {"evidence_id": "ev-b", "value": 330.0, "unit": "USD bn",
         "source": "DEMO B", "source_tier": "C", "definition": "manufacture only",
         "scope": "global", "period": "2025", "methodology": "top-down"},
    ]
    for key, value in overrides.items():
        base[1][key] = value
    return base


class ConflictKinds(unittest.TestCase):
    """Matrix 24-29."""

    def test_definitional_conflict_is_preserved_and_named(self):
        conflict = S.CrossDomainConflict(
            S.DEFINITIONAL, "industry size",
            positions(definition="manufacture plus aftermarket"))
        self.assertEqual(conflict.kind, S.DEFINITIONAL)
        self.assertTrue(conflict.unresolved)
        self.assertEqual(len(conflict.positions), 2)

    def test_numeric_conflict_is_classified_when_only_values_differ(self):
        self.assertEqual(S.classify(positions()), S.NUMERIC)

    def test_scope_conflict_is_classified(self):
        self.assertEqual(S.classify(positions(scope="United States only")), S.SCOPE)

    def test_temporal_conflict_is_classified(self):
        self.assertEqual(S.classify(positions(period="2023")), S.TEMPORAL)

    def test_methodology_conflict_is_classified(self):
        self.assertEqual(S.classify(positions(methodology="bottom-up")), S.METHODOLOGY)

    def test_definition_outranks_a_numeric_difference(self):
        # Once two sources count different things, the numeric gap is a consequence.
        self.assertEqual(S.classify(positions(definition="includes services")),
                         S.DEFINITIONAL)

    def test_internal_external_conflict_is_representable(self):
        conflict = S.CrossDomainConflict.between_domains(
            "revenue vs external estimate",
            {"synthesis_id": "sy-1", "value": Decimal("1250000"), "unit": "GBP"},
            {"evidence_id": "ev-a", "value": 1400000, "unit": "GBP"})
        self.assertEqual(conflict.kind, S.INTERNAL_EXTERNAL)
        self.assertEqual(set(conflict.domains), {"internal", "external"})
        self.assertTrue(conflict.unresolved)

    def test_a_conflict_needs_two_positions(self):
        with self.assertRaises(S.SynthesisError):
            S.CrossDomainConflict(S.NUMERIC, "x", [positions()[0]])


class ConflictBehaviour(unittest.TestCase):
    """Matrix 30-32."""

    def test_conflicting_values_are_never_averaged(self):
        conflict = S.CrossDomainConflict(S.NUMERIC, "industry size", positions())
        record = conflict.as_dict()
        self.assertEqual(conflict.values(), [310.0, 330.0])
        # No aggregate of any kind appears anywhere in the serialised conflict.
        for forbidden in ("average", "mean", "midpoint", "consensus", "resolved_value",
                          "winner", "preferred"):
            self.assertNotIn(forbidden, record)
        self.assertIsNone(record.get("resolution"))
        self.assertNotIn(320.0, conflict.values())
        self.assertTrue(S.NEVER_RESOLVES)

    def test_there_is_no_api_to_remove_a_conflict(self):
        for name in ("remove_conflict", "resolve", "clear_conflicts", "drop_conflict"):
            self.assertFalse(hasattr(S.SynthesisSet, name))
            self.assertFalse(hasattr(S.CrossDomainConflict, name))

    def test_a_conflict_lowers_support_and_confidence_of_what_it_touches(self):
        result = new_set()
        strong = demo_evidence(tier="A", host="ons.gov.uk", source="DEMO Statistics")
        evidence = evidence_set_with(strong)
        S.register_external(result, evidence, S.ORIGIN_INDUSTRY)
        item = S.sourced_statement(
            result, S.ORIGIN_INDUSTRY, "An official source states the figure.",
            evidence_ids=[strong.id])
        self.assertEqual(item.support, S.SUPPORTED)
        self.assertEqual(item.confidence, S.HIGH)

        result.add_conflict(S.CrossDomainConflict(
            S.DEFINITIONAL, "the figure",
            [{"evidence_id": strong.id, "value": 1, "definition": "narrow"},
             {"evidence_id": "ev-other", "value": 2, "definition": "broad"}]))

        self.assertIn(S.confidence.UNRESOLVED_CONFLICT, item.confidence_detail["reasons"])
        self.assertEqual(item.support, S.PARTIALLY_SUPPORTED)
        self.assertEqual(item.confidence, S.LOW)

    def test_source_tier_never_decides_a_conflict(self):
        conflict = S.CrossDomainConflict(
            S.NUMERIC, "size",
            [{"evidence_id": "ev-a", "value": 1, "source_tier": "A"},
             {"evidence_id": "ev-b", "value": 9, "source_tier": "C"}])
        self.assertEqual(len(conflict.positions), 2)
        self.assertTrue(conflict.unresolved)
        self.assertIn("higher source tier does not make a conflicting source false",
                      conflict.as_dict()["resolution_statement"])

    def test_conflicts_survive_serialisation(self):
        result, _handles = build.build()
        record = result.as_dict()
        self.assertEqual(len(record["conflicts"]), 1)
        entry = record["conflicts"][0]
        self.assertEqual(entry["kind"], S.DEFINITIONAL)
        self.assertTrue(entry["unresolved"])
        self.assertEqual(len(entry["positions"]), 2)

    def test_declared_evidence_conflicts_are_lifted_automatically(self):
        result, _handles = build.build()
        # The fixture never calls add_conflict; the conflict arrives with the evidence set.
        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(result.conflicts[0].kind, S.DEFINITIONAL)

    def test_conflicting_evidence_is_distinct_from_insufficient_evidence(self):
        result = new_set()
        insufficient = result.add(S.SynthesisItem(
            S.ASSUMPTION, S.ORIGIN_FORECAST, "Flat seasonality is assumed.",
            provenance=[S.ProvenanceRef.unavailable("No seasonal history.")]))
        self.assertEqual(insufficient.support, S.INSUFFICIENT_EVIDENCE)
        self.assertNotIn(S.confidence.UNRESOLVED_CONFLICT,
                         insufficient.confidence_detail["reasons"])


class Materiality(unittest.TestCase):
    """Matrix 33-38. The configured policy is the only policy."""

    def setUp(self):
        self.config = config_mod.resolve()

    def test_material_finding_is_preserved_with_its_basis(self):
        result, _handles = build.build(include_external=False)
        revenue = next(i for i in result.items if i.metric == "revenue"
                       and i.origin == S.ORIGIN_SALES)
        self.assertTrue(revenue.is_material)
        self.assertEqual(revenue.materiality["outcome"], materiality_mod.MATERIAL)
        self.assertIn("threshold", revenue.materiality["reason"])
        self.assertIsNotNone(revenue.materiality["observed"])
        self.assertIsNotNone(revenue.materiality["comparison"])

    def test_non_material_finding_is_preserved_not_dropped(self):
        result, _handles = build.build(include_external=False)
        orders = next(i for i in result.items if i.metric == "orders")
        self.assertFalse(orders.is_material)
        self.assertEqual(orders.materiality["outcome"], materiality_mod.NOT_MATERIAL)
        self.assertIn(orders.id, [i.id for i in result.items])
        self.assertNotIn(orders.id, [i.id for i in result.material()])

    def test_configured_absolute_threshold_drives_the_verdict(self):
        verdict = materiality_mod.assess_amount(
            "revenue", Decimal("1070000") + Decimal("180000"), Decimal("1070000"),
            self.config)
        self.assertEqual(verdict.outcome, materiality_mod.MATERIAL)
        self.assertEqual(verdict.threshold_used, "absolute_amount")
        item = self._item_with(verdict)
        self.assertTrue(item.is_material)
        self.assertEqual(item.materiality["threshold_used"], "absolute_amount")

    def test_configured_percentage_threshold_drives_the_verdict(self):
        verdict = materiality_mod.assess_amount(
            "line", Decimal("1060"), Decimal("1000"), self.config)
        self.assertEqual(verdict.outcome, materiality_mod.MATERIAL)
        self.assertEqual(verdict.threshold_used, "percentage")
        item = self._item_with(verdict)
        self.assertEqual(item.materiality["threshold_used"], "percentage")

    def test_margin_percentage_point_threshold_drives_the_verdict(self):
        verdict = materiality_mod.assess_margin(
            "gross margin", Decimal("38.40"), Decimal("35.80"), self.config)
        self.assertEqual(verdict.outcome, materiality_mod.MATERIAL)
        self.assertEqual(verdict.threshold_used, "margin_percentage_points")
        self.assertEqual(verdict.unit, "percentage_points")
        item = self._item_with(verdict)
        self.assertEqual(item.materiality["unit"], "percentage_points")

    def test_a_missing_threshold_does_not_invent_one(self):
        verdict = materiality_mod.assess_amount("revenue", None, Decimal("100"),
                                                self.config)
        self.assertEqual(verdict.outcome, materiality_mod.UNDETERMINED)
        self.assertIsNone(verdict.threshold_used)
        item = self._item_with(verdict)
        self.assertFalse(item.is_material)
        self.assertEqual(item.materiality["outcome"], materiality_mod.UNDETERMINED)
        self.assertIsNone(item.materiality["threshold_used"])

    def test_synthesis_defines_no_second_materiality_policy(self):
        for name in dir(S):
            self.assertNotIn("threshold", name.lower())
        self.assertFalse(hasattr(S, "assess_amount"))
        self.assertFalse(hasattr(S, "MATERIAL"))

    def _item_with(self, verdict):
        result = new_set()
        return result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_FINANCIAL, "A movement was observed.",
            provenance=[dataset_ref()], basis="sum(x)",
            materiality=verdict.as_dict()))


class Confidence(unittest.TestCase):
    """Matrix 39-46."""

    def test_high_confidence_needs_no_downgrade_reason(self):
        assessment = S.assess([])
        self.assertEqual(assessment.level, S.HIGH)
        self.assertEqual(assessment.reasons, ())

    def test_one_ordinary_reason_is_medium(self):
        assessment = S.assess([S.confidence.UNDATED_EXTERNAL])
        self.assertEqual(assessment.level, S.MEDIUM)

    def test_two_ordinary_reasons_are_low(self):
        assessment = S.assess([S.confidence.UNDATED_EXTERNAL, S.confidence.TIER_C_ONLY])
        self.assertEqual(assessment.level, S.LOW)

    def test_one_severe_reason_is_low_on_its_own(self):
        for severe in sorted(S.SEVERE):
            self.assertEqual(S.assess([severe]).level, S.LOW, severe)

    def test_an_unresolved_conflict_lowers_confidence(self):
        self.assertIn(S.confidence.UNRESOLVED_CONFLICT, S.SEVERE)
        self.assertEqual(S.assess([S.confidence.UNRESOLVED_CONFLICT]).level, S.LOW)

    def test_undated_external_evidence_affects_confidence(self):
        result = new_set()
        undated = demo_evidence(publication_date=None)
        evidence = evidence_set_with(undated)
        S.register_external(result, evidence, S.ORIGIN_MARKET)
        item = S.sourced_statement(result, S.ORIGIN_MARKET, "A source says something.",
                                   evidence_ids=[undated.id])
        self.assertIn(S.confidence.UNDATED_EXTERNAL, item.confidence_detail["reasons"])

    def test_stale_external_evidence_is_named_separately_from_undated(self):
        result = new_set()
        old = demo_evidence(publication_date="2019-01-01")
        evidence = evidence_set_with(old)
        S.register_external(result, evidence, S.ORIGIN_MARKET)
        item = S.sourced_statement(result, S.ORIGIN_MARKET, "An old source says so.",
                                   evidence_ids=[old.id])
        self.assertEqual(old.freshness["freshness"], sources_mod.DATED)
        self.assertIn(S.confidence.STALE_EXTERNAL, item.confidence_detail["reasons"])
        self.assertNotIn(S.confidence.UNDATED_EXTERNAL,
                         item.confidence_detail["reasons"])

    def test_insufficient_history_affects_set_confidence(self):
        result = new_set()
        analysis = analytics_contract.AnalysisSet(
            "forecast", status=analytics_contract.INSUFFICIENT_DATA,
            reason="Only two periods of history.")
        result.register_analysis(analysis)
        self.assertIn(S.confidence.INSUFFICIENT_HISTORY, result.confidence().reasons)

    def test_a_material_data_quality_warning_affects_confidence(self):
        from bops.quality import contract as quality_contract
        result = S.SynthesisSet(quality_grade=quality_contract.WARNING)
        result.register_dataset(DATASET, label="test.csv")
        item = result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_KPI, "Revenue totalled 1,250,000.",
            provenance=[dataset_ref()], basis="sum(net_revenue)"))
        self.assertIn(S.confidence.DATA_QUALITY_WARNING,
                      item.confidence_detail["reasons"])
        self.assertEqual(item.confidence, S.LOW)

    def test_an_unavailable_kpi_affects_set_confidence(self):
        from bops.kpi import contract as kpi_contract
        result = new_set()
        definition = kpi_contract.KPIDefinition(
            "dso", "Days sales outstanding",
            "Average days to collect receivables.",
            "(accounts_receivable / revenue) * days_in_period",
            ("accounts_receivable", "revenue"),
            kpi_contract.DAYS, kpi_contract.DERIVED,
            calculator=lambda *a, **k: None, category="working_capital")
        unavailable = kpi_contract.unavailable(
            definition, missing_inputs=("invoice_date",),
            reason="The dataset carries no invoice dates.")
        outcome = S.from_kpi_result(result, unavailable)
        self.assertIsNone(outcome)
        self.assertIn(S.confidence.UNAVAILABLE_KPI, result.confidence().reasons)
        self.assertTrue(any(lim.code.startswith("kpi.")
                            for lim in result.limitations))

    def test_every_confidence_reason_is_traceable_to_fixed_text(self):
        for code in S.REASON_CODES:
            self.assertIn(code, S.REASON_TEXT)
            self.assertTrue(S.REASON_TEXT[code].strip())
        assessment = S.assess([S.confidence.TIER_C_ONLY])
        self.assertEqual(assessment.explanations,
                         (S.REASON_TEXT[S.confidence.TIER_C_ONLY],))

    def test_confidence_is_never_presented_as_a_probability(self):
        self.assertFalse(S.STATISTICAL_INTERVAL)
        record = S.assess([]).as_dict()
        self.assertIs(record["statistical_interval"], False)
        self.assertIn("Not a probability", record["basis"])
        self.assertNotIn("%", record["basis"])

    def test_set_confidence_is_the_weakest_statement(self):
        result = new_set()
        result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_KPI, "A clean calculation.",
            provenance=[dataset_ref()], basis="sum(x)"))
        self.assertEqual(result.confidence().level, S.HIGH)
        result.add(S.SynthesisItem(
            S.ASSUMPTION, S.ORIGIN_FORECAST, "An assumption with no provenance.",
            provenance=[S.ProvenanceRef.unavailable("Nothing supports this.")]))
        self.assertEqual(result.confidence().level, S.LOW)

    def test_many_medium_statements_do_not_pool_into_low(self):
        result = new_set()
        for index in range(4):
            item = demo_evidence(publication_date=None, host="a%d.example.invalid" % index)
            evidence = evidence_set_with(item)
            S.register_external(result, evidence, S.ORIGIN_MARKET)
            S.sourced_statement(result, S.ORIGIN_MARKET,
                                "Source %d states something." % index,
                                evidence_ids=[item.id])
        levels = set(i.confidence for i in result.items)
        self.assertEqual(levels, {S.LOW})
        self.assertEqual(result.confidence().level, S.LOW)


class Limitations(unittest.TestCase):
    """Matrix 47-52."""

    def test_internal_limitations_are_preserved(self):
        result, _handles = build.build(include_external=False)
        codes = [lim.code for lim in result.limitations]
        self.assertIn("sales.dimension_absent", codes)

    def test_forecast_limitations_are_preserved(self):
        result, _handles = build.build(include_external=False)
        codes = [lim.code for lim in result.limitations]
        self.assertIn("forecast.horizon_reduced", codes)

    def test_anomaly_limitations_are_preserved(self):
        result, _handles = build.build(include_external=False)
        codes = [lim.code for lim in result.limitations]
        self.assertIn("anomaly.baseline_short", codes)

    def test_external_limitations_are_preserved(self):
        result, _handles = build.build()
        codes = [lim.code for lim in result.limitations]
        self.assertIn(S.limitations.UNRESOLVED_CONFLICT, codes)

    def test_equivalent_limitations_deduplicate_deterministically(self):
        result = new_set()
        for _ in range(3):
            result.limit("x.code", "subject", "the same reason")
        codes = [lim.code for lim in result.limitations]
        self.assertEqual(codes.count("x.code"), 1)

    def test_limitations_differing_in_any_field_are_kept_apart(self):
        result = new_set()
        result.limit("x.code", "subject", "reason one")
        result.limit("x.code", "subject", "reason two")
        self.assertEqual(len(result.limitations), 2)

    def test_first_seen_order_is_preserved(self):
        result = new_set()
        result.limit("b", "s", "r")
        result.limit("a", "s", "r")
        result.limit("c", "s", "r")
        self.assertEqual([lim.code for lim in result.limitations], ["b", "a", "c"])

    def test_limitations_survive_serialisation(self):
        result, _handles = build.build()
        record = result.as_dict()
        self.assertEqual(len(record["limitations"]), len(result.limitations))
        for entry in record["limitations"]:
            self.assertIn("code", entry)

    def test_limitations_are_never_suppressed_by_surrounding_evidence(self):
        self.assertTrue(S.NEVER_SUPPRESSES)
        for name in ("filter", "suppress", "drop", "prune"):
            self.assertFalse(hasattr(S.limitations, name))


class Comparability(unittest.TestCase):
    """Matrix 53-60."""

    def _pair(self, **right_overrides):
        left = {"metric_definition": "net revenue", "period": "2025",
                "geography": "United Kingdom", "currency": "GBP", "unit": "currency",
                "scope": "whole business", "methodology": "ledger aggregation"}
        right = dict(left)
        right.update(right_overrides)
        return left, right

    def test_compatible_values_may_be_related(self):
        left, right = self._pair()
        result = S.compare(left, right)
        self.assertEqual(result["status"], S.COMPATIBLE)
        self.assertTrue(S.may_combine(result))
        self.assertEqual(result["mismatched"], [])

    def test_incompatible_metric_definitions_stay_separate(self):
        left, right = self._pair(metric_definition="gross revenue")
        result = S.compare(left, right)
        self.assertEqual(result["status"], S.INCOMPATIBLE)
        self.assertFalse(S.may_combine(result))
        self.assertEqual(result["mismatched"][0]["dimension"], "metric_definition")

    def test_incompatible_geography_stays_separate(self):
        left, right = self._pair(geography="Global")
        self.assertEqual(S.compare(left, right)["status"], S.INCOMPATIBLE)

    def test_incompatible_period_stays_separate(self):
        left, right = self._pair(period="2023")
        self.assertEqual(S.compare(left, right)["status"], S.INCOMPATIBLE)

    def test_incompatible_currency_stays_separate(self):
        left, right = self._pair(currency="USD")
        self.assertEqual(S.compare(left, right)["status"], S.INCOMPATIBLE)

    def test_incompatible_units_stay_separate(self):
        left, right = self._pair(unit="percent")
        self.assertEqual(S.compare(left, right)["status"], S.INCOMPATIBLE)

    def test_incompatible_methodology_stays_separate(self):
        left, right = self._pair(methodology="survey estimate")
        self.assertEqual(S.compare(left, right)["status"], S.INCOMPATIBLE)

    def test_an_unstated_dimension_fails_on_unknown_not_on_assumed_match(self):
        left, right = self._pair(methodology=None)
        result = S.compare(left, right)
        self.assertEqual(result["status"], S.UNKNOWN)
        self.assertFalse(S.may_combine(result))
        self.assertEqual(result["unknown"][0]["dimension"], "methodology")

    def test_no_unauthorised_currency_conversion(self):
        self.assertTrue(S.NEVER_CONVERTS)
        left, right = self._pair(currency="USD")
        result = S.compare(left, right)
        self.assertFalse(result["converted"])
        for name in ("convert", "to_currency", "rescale", "normalise_currency"):
            self.assertFalse(hasattr(S.compatibility, name))

    def test_comparison_is_case_and_whitespace_insensitive(self):
        left, right = self._pair(geography="  united   KINGDOM ")
        self.assertEqual(S.compare(left, right)["status"], S.COMPATIBLE)

    def test_comparing_incompatible_values_records_a_limitation_not_a_figure(self):
        result = new_set()
        evidence_item = demo_evidence()
        evidence = evidence_set_with(evidence_item)
        S.register_external(result, evidence, S.ORIGIN_INDUSTRY)

        internal = result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_SALES, "Revenue was 1,250,000 GBP in 2026-Q1.",
            provenance=[dataset_ref()], basis="sum(net_revenue)",
            observed=Decimal("1250000"), currency="GBP", unit="currency",
            period="2026-Q1", geography="United Kingdom",
            metric_definition="net revenue", scope="whole business",
            methodology="ledger aggregation"))
        external = S.sourced_statement(
            result, S.ORIGIN_INDUSTRY, "A source sizes the industry at 310 USD bn.",
            evidence_ids=[evidence_item.id], observed=Decimal("310"),
            source_unit="USD bn", period="2025", geography="global",
            metric_definition="industry output", scope="global",
            methodology="top-down")

        comparison = S.compare_values(result, internal, external,
                                      subject="revenue against industry size")
        self.assertEqual(comparison["status"], S.INCOMPATIBLE)
        codes = [lim.code for lim in result.limitations]
        self.assertIn(S.limitations.INCOMPARABLE, codes)
        self.assertIn(S.confidence.INCOMPARABLE_VALUES,
                      internal.confidence_detail["reasons"])
        # An internal/external mismatch is also recorded as a conflict, unaveraged.
        kinds = [c.kind for c in result.conflicts]
        self.assertIn(S.INTERNAL_EXTERNAL, kinds)
        cross = next(c for c in result.conflicts if c.kind == S.INTERNAL_EXTERNAL)
        self.assertEqual(len(cross.positions), 2)
        self.assertIsNone(cross.as_dict().get("resolution"))

    def test_compatible_values_produce_no_combined_figure(self):
        result = new_set()
        left = result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_SALES, "Revenue was 100 in 2025.",
            provenance=[dataset_ref()], basis="sum(x)", observed=Decimal("100"),
            currency="GBP", unit="currency", period="2025", geography="UK",
            metric_definition="net revenue", scope="whole", methodology="ledger"))
        right = result.add(S.SynthesisItem(
            S.CALCULATION, S.ORIGIN_PRODUCT, "Revenue was 60 in 2025.",
            provenance=[dataset_ref()], basis="sum(x)", observed=Decimal("60"),
            currency="GBP", unit="currency", period="2025", geography="UK",
            metric_definition="net revenue", scope="whole", methodology="ledger"))
        comparison = S.compare_values(result, left, right)
        self.assertEqual(comparison["status"], S.COMPATIBLE)
        # Establishing comparability is not doing the arithmetic.
        self.assertEqual(len(result), 2)
        self.assertNotIn("combined", comparison)
        self.assertNotIn("ratio", comparison)


if __name__ == "__main__":
    unittest.main()
